# Vision module — camera-based fan trim for bean circulation

Planning document, started 2026-08-24. Not yet scheduled; pointer lives in
[state-plan.md](state-plan.md) § Later. Nothing here is built.

## Problem statement

The correct fan setting during a roast is not repeatable from OT2 alone — it
depends on bean density/size and load mass, and both change as the roast
progresses (beans lose ~15 % mass and expand). But the *circulation pattern is
directly observable*: the operator watches the bed and adjusts the fan until
the fountain looks smooth. Goal: a vision module that quantifies circulation
quality and supplies the primary processor with bounded fan-speed trim to hold
it.

**Two cameras** are planned from the start (operator observation: the system's
asymmetry means the useful information is often in one view but not the
other), but the metric gets validated with one camera first — the second is a
hypothesis to test, not an assumption to build on.

**Scope constraints (operator, 2026-08-24):**
- A roast is **under 10 minutes, usually under 8**.
- **Only instantaneous behavior matters.** The deployed system does not record
  video — frames are processed and discarded. (Development still wants short
  recorded segments; see § Recording.)

## Architecture

The vision processor is not the ESP32-S3: real-time optical flow is far beyond
it, the firmware's safety posture stays untouched, and the vision stack can
iterate in Python without reflashing. But that leaves *which* processor open,
and the answer is probably one already present.

```
cameras ──USB──> vision processor ──WebSocket (keyed client)──> ESP32-S3
                 (metric + slow trim loop)   FANTRIM ±n         (clamp,
                                                             timeout decay)
```

### Option A — the Mac does it (leading candidate)

**The Mac is already in the loop for every roast**: it runs Artisan, and under
FULL auth it runs `tools/roaster_proxy.py` as the signing proxy. Adding a
vision process to a machine that is already present, already authenticated,
and already the operator console is close to free.

What this deletes outright: the coprocessor purchase, its power rail, its
thermal enclosure, its EMI quarantine cell, the NVMe storage question, the
cross-compile/deploy cycle — and, most importantly, **any difference between
the development and deployment environment**. A vision metric depends on
exposure, shutter behavior, and sensor noise; validating it on one camera and
deploying on another is a real transfer risk (§ Camera continuity). Option A
makes that risk structurally impossible.

Costs and caveats:

- **Cable reach.** USB3 passive cables are good to ~3–5 m; beyond that needs
  active/optical extension. Measure the Mac-to-roaster distance early.
- **The Mac must be present and awake.** Already true — it is logging the
  roast in Artisan. Disable App Nap / sleep for the vision process.
- **The roaster stops being self-contained.** It already isn't: Artisan
  logging and the auth proxy both live on the Mac. If standalone operation
  ever becomes a goal, Option B is the upgrade path and the metric code ports
  (both are Python/OpenCV).

### Option B — Raspberry Pi coprocessor (deferred, not rejected)

Kept as the path to a self-contained roaster. **Decide this only after the
metric works** — if Option A proves sufficient, Option B may never be needed.

Prior trade study, retained so it need not be redone:

| Option | Verdict |
|--------|---------|
| **Raspberry Pi 5 (4 GB)** | Best coprocessor if one is wanted. Two native MIPI CSI ports (Pi 4 has one), ample CPU for dense flow on two low-res streams, `picamera2` gives full manual exposure/gain control. |
| Jetson Orin Nano | Only if the metric turns out deep-learning-heavy. Revisit after Phase 1. |
| Luxonis OAK | Viable; ecosystem friction vs. classical CV on a general-purpose host. |
| ESP32-CAM / OpenMV | Underpowered for two streams + flow. Rejected. |

- **4 GB, not 8 GB.** Same BCM2712 either way, so it is purely a RAM question.
  Runtime budget: OS Lite ~250 MB + Python/OpenCV/picamera2 ~350 MB + shallow
  camera buffer queues ~25–100 MB + flow at 320×240 (a few MB) — under 1.5 GB.
  Buffer queues are shallow and flow runs downsampled, so capture resolution
  drives disk, not memory. The one case for 8 GB was holding a roast's frames
  in memory for offline experimentation, and that work is on the Mac.
- **No hardware H.264 encoder** (VideoCore VII dropped the Pi 4's encode
  block). Would have made recording expensive — moot now that the deployed
  system doesn't record, and doubly moot under Option A.
- Power would need its **own supply**, never the existing 5 V rail
  ([hardware/power.md](hardware/power.md) is already over budget on the
  R-78W-0.5): size for the full 5 A, since an undervolting Pi throttles and
  would present as a metric that degrades under load rather than an obvious
  power fault.

### Firmware side (identical under either option)

- The vision process connects to the existing `:81` WebSocket as an
  **authenticated keyed client** — the HMAC challenge–response client in
  `tools/roaster_proxy.py` is directly reusable Python. Vision is a mutating
  client, so it authenticates under CONFIG/FULL like any other.
- **Division of labor:** the host computes the metric and runs the slow trim
  loop; the firmware enforces safety — it treats vision input as *advisory
  trim on the operator's base OT2*, never as fan authority.

## Cameras

### Manual exposure control is the gating requirement

Auto-exposure and auto-gain must be **off and fixed**, or the metric moves when
the image pipeline moves rather than when the beans do. This is the same
repeatability argument as everywhere else in this project, and it is the single
constraint that decides the camera.

**Verified gotcha (2026-08-24):** on macOS, OpenCV's `CAP_PROP_EXPOSURE` is
widely reported not to work with UVC webcams — reads return 0 and writes
silently no-op. macOS exposes far less UVC control through AVFoundation than
Linux does through V4L2. **Confirm exposure control on the actual camera before
building anything on it** — the same "verify the platform gotcha early" posture
the auth plan took with Web Crypto secure contexts.

Options, cheapest first:

1. **Existing webcam / phone.** Fine for Phase 0, where the question is "where
   can a camera see the bed and what does good vs. bad circulation look like."
   Do not tune a metric on it.
2. **UVC webcam + `uvcc`** (USB Video Class configurator) to set controls
   out-of-band when OpenCV cannot. Works on *some* cameras; cheap to test.
   Industrial UVC modules (Arducam, e-con See3CAM) generally expose honest
   manual controls where consumer webcams do not.
3. **USB3 machine-vision camera** (Basler ace / pylon, FLIR / Spinnaker) —
   full manual control, global shutter options, and **cross-platform SDKs that
   cover both macOS and Linux**, so one camera serves development *and* either
   deployment option. ~$300–600 each is the real cost. Caution: Basler's
   published macOS pylon download lags the Windows/Linux line — verify current
   macOS support before purchase.
4. **Pi CSI cameras** (Global Shutter IMX296, or Camera Module 3 IMX708) —
   excellent control via `picamera2`, cheapest good option, but **Pi-only**, so
   they force Option B and forfeit dev/deploy continuity.

### Camera continuity, dev → deploy

If Phase 1 tunes a metric on camera A and Phase 2 deploys camera B, the metric
may not transfer: rolling vs. global shutter changes how fast motion is
rendered, and exposure/noise characteristics shift the flow field. Options 3
and 4 above sit on opposite sides of this — a USB3 MV camera costs more but is
the same instrument throughout; CSI is cheap but only exists on the Pi. **This
is the main reason to prefer Option A + a USB camera.**

For motion analysis, **frame rate and exposure control beat resolution** —
processing runs around 320×240 regardless. Short exposures (≲1 ms) to freeze
beans are the real requirement, which drives lighting.

### Lighting — part of the instrument, not an accessory

- Dedicated **DC-driven (flicker-free) high-output LED**, diffused, fixed
  geometry. Mains-PWM or dimmed LEDs would beat against the frame rate.
- Short exposure + strong fixed light makes the metric immune to ambient
  (room lights, daylight).
- Glare off the chamber glass is the expected nuisance: plan for angled
  mounting, and try cross-polarization (film on the LED, polarizer on the
  lens) if angle alone doesn't kill it.

### Mounting / thermal / contamination (open — survey the roaster first)

- Where can each camera actually see the bed, at what standoff? (Phase 0
  answers this with a temporary mount before anything is fabricated.)
- Board cameras are typically rated ≤ 50–70 °C ambient: expect standoff
  mounting, a heat shield, and possibly a small purge fan. Measure the
  temperature at candidate mount points during a real roast **before**
  ordering mounts.
- Chaff dust and smoke deposition on the chamber exterior / camera window —
  needs an observation period, may force a periodic-cleaning norm or an air
  purge across the window.
- USB cameras are bus-powered, so mounting needs no separate supply — one more
  simplification from Option A.

## Recording — development only

The deployed system records nothing (operator constraint above): frames in,
metric out, frames discarded. **Development is the exception, and it matters.**
Without recorded footage every metric experiment costs a whole roast — beans,
time, and a cadence of a few per week. With a corpus, an evening yields
hundreds of experiments against *identical* circulation events, which is the
only way to compare two feature designs honestly.

The burden is small, and smaller than first planned:

- **Short labeled segments, not whole roasts.** 30–60 s clips of good /
  sluggish / surging is a corpus. A dozen clips covers the space.
- On the Mac, encoding is hardware-accelerated (VideoToolbox), so recording is
  nearly free — the Pi's missing H.264 encoder never enters the picture.
- Even uncompressed is tractable: an 8 min roast at 60 fps is ~28,800 frames;
  at 320×240 grayscale that is ~2.2 GB per view (~4.4 GB for two). Fits a
  Mac's RAM comfortably for interactive work — and notably would *not* fit a
  4 GB Pi, which is why Phase 1 belongs on the laptop.
- Record with **exposure fixed and noted**, at known fps. Phase 1 can always
  downsample; it cannot un-blur a frame or undo an auto-exposure step
  mid-roast.

## The metric (the actual hard problem)

"Smooth circulation" must become a number before anything closes a loop.
Constraints on the feature design:

- **Motion-based, not appearance-based.** Bean color darkens through the
  roast, oils surface, chaff releases, smoke hazes late — any
  appearance-keyed feature drifts. Optical-flow / temporal-statistics
  features are first-order immune.
- Candidate features (Phase 1 evaluates these offline against labeled video):
  - Dense optical flow (OpenCV DIS/Farnebäck at low res): mean speed,
    vertical-velocity profile through the fountain, **stagnant-area fraction**
    (fraction of bed ROI below a motion threshold — likely the single most
    direct "not circulating" signal).
  - Temporal spectrum of per-region activity: smooth fountaining is a steady
    broadband signature; surging/slugging shows a low-frequency (order 1–5 Hz)
    pulsation peak; a stalled bed shows low total activity.
  - **Cross-view asymmetry** between the two cameras — the operator's stated
    reason for two views; quantifies "the fountain collapsed to one side."
- A learned regressor (small CNN or gradient-boosted model on the classical
  features, labels from operator judgment) is the *fallback* if hand-built
  features plateau.

## Control shape

- The host runs a **slow, integral-only trim loop**: metric sampled at a few
  Hz, trim adjusted every few seconds in small steps with hysteresis. Slow on
  purpose — the measurement is noisy, and fan changes perturb the
  inlet-temperature loop (airflow ↔ heat transfer coupling); a slow outer trim
  keeps the two loops decoupled in time. Note an 8 min roast leaves room for
  only tens of trim decisions: the loop must be slow but not timid.
- Firmware side is deliberately small — one new command and its safeguards:
  - `FANTRIM <±pts>` — signed trim applied on top of the operator's OT2,
    **clamped** (e.g. ±10 points, NVS-configurable), never below the cooldown
    guard's `coolFanMin`, interlock logic untouched.
  - **Timeout decay**: trim not refreshed within N seconds decays to zero —
    the stale-source failsafe pattern the sensors already follow. A vision
    crash mid-roast leaves the operator's base setting, not a stuck trim.
  - `FANTRIM ON|OFF` (default OFF), trim value in telemetry and on the
    dashboard, `trim` push on change. Effective fan = base + trim is what
    `setFanLevel()` commits.
- Operator's OT2 always remains the base; slider moves are never fought.

## Phases

**Phase 0 — instrumented observation (no purchase).** Existing webcam or a
phone on a tripod + provisional lighting on the assembled roaster. Record a
few roasts: video synced with the WebSocket telemetry log (fan level, temps,
events; load mass noted per batch). Operator narrates/labels segments good /
sluggish / surging. Deliverables: camera-placement + thermal survey, lighting
lessons, a labeled clip corpus, and the Mac-to-roaster cable-reach
measurement. *De-risks everything downstream at zero cost.*

**Phase 1 — metric development, offline, on the Mac.** Replay the corpus,
implement the candidate features, score them against the labels. Success
criterion: a metric that ranks segments consistently with operator judgment
**across load sizes and roast stages**. Test the two-camera hypothesis here if
Phase 0 captured paired views. No hardware beyond Phase 0's.

**Phase 1.5 — camera decision.** Only now, knowing what the metric needs
(frame rate, shutter type, whether view 2 earns its slot), buy the real
camera(s) + lighting. Verify manual exposure control on macOS *first*
(§ Manual exposure control).

**Phase 2 — live metric, human in the loop.** Vision process runs live on the
Mac; metric pushed to the dashboard as a curve next to fan level. Operator
drives the fan manually and checks the metric tracks their perception, live,
over several roasts. (This alone is already useful: a repeatable circulation
readout.)

**Phase 3 — advisory.** The trim loop runs but only *displays* its suggested
trim on the dashboard; the operator applies it by hand. Validates the loop's
sign, gain, and cadence with zero authority.

**Phase 4 — closed loop.** `FANTRIM` firmware work lands (clamp, decay,
telemetry, default-off); the vision process sends trim. On-roaster drills in
the established style: kill the vision process mid-roast (trim decays),
saturate the clamp, verify cooldown-guard precedence and interlock
independence.

**Phase 5 (optional, only if wanted) — migrate to a Pi** for a self-contained
roaster, per Option B.

## Open questions

1. Optical access: where do two useful views of the bed exist, and what do
   those locations see thermally during a roast? (Phase 0.)
2. Chamber-glass glare and fouling over a full roast + session. (Phase 0.)
3. Does the second view add information the first lacks, per the asymmetry
   hypothesis? (Phase 1 — decides whether camera 2 is permanent or optional.)
4. Is there a load-size/bean-independent setpoint for the metric, or does the
   operator set the target per roast (e.g. "hold circulation where I put it
   at charge")? The latter is the safer initial design — repeatability within
   a roast first, absolute targets later.
5. Which camera clears the macOS manual-exposure bar at acceptable cost?
   (Phase 1.5, but test a candidate early — it gates Option A.)
6. Mac-to-roaster USB cable reach, and whether active extension is needed.
