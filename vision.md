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
Linux does through V4L2. The problem is narrower than "UVC is unusable,"
though: it is *OpenCV's macOS backend* that cannot reach the controls. Talking
to the device directly over libusb does work — see § UVC probe procedure.

### Vendor screening for macOS (2026-08-25)

Machine vision is a Windows-first industry and macOS support is where most
vendors quietly give up. Screened before comparing any specs:

| Vendor | macOS verdict |
|--------|---------------|
| **Basler** (pylon) | **Clears it.** pylon runs natively on macOS **Intel and Apple Silicon**; `pypylon` ships prebuilt PyPI wheels for both (macOS ≥ 14.0). pylon also supports **Linux ARM**. |
| Teledyne FLIR (Spinnaker) | **Ruled out.** Maintenance policy builds macOS against **Mojave 10.14** (2018); newer requires contacting sales. |
| IDS, Allied Vision, Daheng, The Imaging Source | Not pursued — macOS support ranges from absent to worse, and Basler already works. |

Basler's reach is the decisive property, not merely a convenience: **one camera
covers the current Intel Mac, a future Apple Silicon Mac, and an Option B Pi**
(pylon on Linux ARM). That closes § Camera continuity outright rather than
managing it.

Wrinkle, currently in our favor: the pylon Viewer GUI is not native on Apple
Silicon (needs Rosetta + pylon 6.2), but **runs natively on Intel** — and it is
genuinely useful for first-time focus and exposure setup.

### Recommended camera — Basler dart daA1440-220um (CS-mount)

Sony IMX273, 1440×1080, 227 fps, **global shutter, mono**, USB3, 1/2.9" format,
3.45 µm pixels, 0–50 °C rated. Specs from Basler's product page.

Why it fits this problem almost exactly:

- **Global shutter** freezes bean motion with no rolling-shutter skew
  corrupting the flow field.
- **227 fps** is large headroom; expect to run 60–100 and crop for more.
- **Mono is an upgrade, not a compromise.** No Bayer filter means ~3× the light
  per pixel, which is exactly what buys the ≲1 ms exposures needed to freeze
  beans. No debayer cost, and optical flow ignores color anyway. Cheaper than
  the color `-220uc`.
- 1.6 MP is ample when processing runs at 320×240, while the spare pixels help
  framing and focus.
- IMX273 is the same Sony Pregius generation and pixel pitch as the Pi GS
  camera's IMX296, so Option B stays familiar — though no camera change would
  be needed.

**Take CS-mount** (not S-mount or bare board): CS lenses mount directly and
C-mount lenses fit with a 5 mm adapter, giving the widest optical choice.
S-mount (M12) is smaller and cheaper but optically limiting.

The `ace` line is the tier above and buys features this project does not need
(housing, I/O, higher-end sensors). `dart` is the correct tier.

**Pricing unverified** — Basler gates shop pricing by region and the retail
listing refused automated fetch. Get a quote from Edmund Optics or Graftek.
Rough expectation only: ~$250–350 per body, ~$50–150 per lens.

**Buy one, not two.** Open question 3 (does the second view add information?) is
precisely what Phase 1 answers; buying the pair now spends real money on an
untested hypothesis.

### Lens

Separate purchase, **not specifiable until Phase 0** yields standoff distance
and desired field of view.

    focal length ≈ sensor width × (working distance ÷ field width)

Sensor width here is ~5.0 mm (1440 × 3.45 µm). A 300 mm standoff viewing a
150 mm bed wants ≈ 10 mm. Expect 6–16 mm for plausible roaster geometry.

Two requirements beyond focal length: a **fast lens** (f/1.4–f/2.0), because
short exposures are light-starved; and **manual focus and iris that lock** —
autofocus drifts exactly the way auto-exposure does.

### Camera continuity, dev → deploy

If Phase 1 tunes a metric on camera A and Phase 2 deploys camera B, the metric
may not transfer: rolling vs. global shutter changes how fast motion is
rendered, and exposure/noise characteristics shift the flow field. **Choosing
Basler dissolves this** — the same camera and the same SDK serve the Intel Mac
now, an Apple Silicon Mac later, and a Pi under Option B. Any cheaper path
(§ UVC probe procedure) reintroduces the risk and must be treated as
provisional: a metric validated on a probed webcam needs re-checking on the
final camera.

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

## UVC probe procedure — run before buying a camera

**Purpose.** Determine whether a UVC camera already on hand can hold a *fixed*
exposure and gain on macOS. Pass → Phase 1 proceeds at zero hardware cost.
Fail → order the dart (§ Recommended camera). Either way this costs an evening
and gates a several-hundred-dollar decision.

**Why readback alone is not enough.** A camera can accept a control write and
still auto-adjust underneath. Step 6 is the decisive test; steps 3–5 only
establish that the control surface exists.

### Prerequisites

    brew install node libusb
    npm install --global uvcc
    pip install opencv-python

Optional GUI cross-check: "Webcam Settings" (Mac App Store).

### 1. Enumerate cameras

    system_profiler SPCameraDataType
    ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | sed -n '/video devices/,/audio devices/p'

### 2. Get vendor / product IDs

`uvcc` addresses devices by USB ID, not by name:

    system_profiler SPUSBDataType | grep -B 2 -A 12 -iE 'camera|webcam|imaging'

Record `Vendor ID: 0x____` and `Product ID: 0x____`. Note the built-in FaceTime
camera is generally **not** UVC-controllable — use an external USB camera.

### 3. Dump the control surface (the key discovery step)

    uvcc --vendor 0xVVVV --product 0xPPPP export

Prints every control the camera actually exposes, with current values. Save the
output into this doc.

### 4. Confirm the required controls exist

Minimum set:

- `autoExposureMode` — must accept **1 = manual** (UVC: 1 manual, 2 auto,
  4 shutter priority, 8 aperture priority).
- `absoluteExposureTime` — units are **100 µs**, so `10` = 1 ms, `1` = 0.1 ms.
- `gain` — auto-gain is as damaging as auto-exposure; must be settable and stay put.

Lock these too if present: `autoWhiteBalance`, `whiteBalanceTemperature`,
`brightness`, `contrast`, `powerLineFrequency`.

If `autoExposureMode` or `gain` is absent → **camera fails, stop here.**

### 5. Set, then read back

    uvcc --vendor 0xVVVV --product 0xPPPP set auto_exposure_mode 1
    uvcc --vendor 0xVVVV --product 0xPPPP set absolute_exposure_time 10
    uvcc --vendor 0xVVVV --product 0xPPPP set gain <mid-range>
    uvcc --vendor 0xVVVV --product 0xPPPP export

Readback must match what was written, give or take one quantization step.

**Control names are snake_case** in uvcc v8 (`auto_exposure_mode`), not the
camelCase used in the UVC spec. `export` is more useful than repeated `get`,
which needs one process per control.

**In zsh, do not stash the flags in a plain variable** — `V="--vendor 0x046d
--product 0x082d"; uvcc $V ...` does not word-split and uvcc prints its usage
banner instead. Use an array: `V=(--vendor 0x046d --product 0x082d)`.

### 6. The decisive behavioral test

Open an OpenCV capture on a fixed scene, then **change scene luminance
substantially** (switch a lamp, or shade half the field). Log mean frame
intensity per frame rather than eyeballing it.

Three traps, each of which silently produces a confident wrong answer:

1. **Confirm which camera OpenCV opened.** Its index order need not match
   `ffmpeg -list_devices`. Identify it positively: toggle the UVC exposure
   register and see which index's brightness *responds*. Reading a built-in
   camera while writing registers to the USB one looks exactly like "registers
   hold but the image auto-corrects."
2. **Apply the lock after the capture opens** (§ 7) — otherwise the run tests
   whatever macOS chose, not what was set.
3. **Check the baseline is actually lit.** A black frame compared against a
   covered lens is black-vs-black and proves nothing.

A monotonic exposure→brightness ramp is the strongest single check: an
auto-exposing camera cannot produce one, because it compensates each step back
toward a constant mean.

- **Pass (auto-exposure genuinely off):** mean brightness steps with the
  lighting change and *stays* changed.
- **Fail (auto-exposure still active):** mean brightness dips, then drifts back
  toward its prior value over ~1 s.

### 7. Verify the lock survives capture start

macOS may reset UVC state when AVFoundation opens the device. With OpenCV still
streaming, re-run the step 5 `get` commands and confirm nothing changed. If the
values reset, retry setting them *after* the capture opens; if they still reset,
the camera fails.

### 8. Measure the exposure floor and frame rate

Confirm the camera reaches ≲1 ms exposure *while* delivering the wanted frame
rate under the lighting actually available. Short exposure plus weak light gives
a dark, noisy image — this is where § Lighting stops being optional.

### Record here

**Result 2026-08-25 — Logitech C920: PASS. Phase 1 proceeds at zero hardware
cost; the dart is not required.**

| Item | Value |
|---|---|
| Camera | Logitech HD Pro Webcam C920 |
| Vendor / product | `0x046d` / `0x082d` |
| OpenCV index | **0** (`cv2.CAP_AVFOUNDATION`) — *not* the ffmpeg index |
| Exposure range | `3`–`2047` → 0.3–204.7 ms; gain `0`–`255` |
| Frame rate | **30.0 fps @ 1280x720**, 1351 frames, no drops |
| Step 4 controls | `auto_exposure_mode`, `absolute_exposure_time`, `gain` all present |
| Step 5 readback | exact while idle; ±1 quantization once streaming |
| Step 6 | **PASS** — luminance step of −21.06 (18.2%) held 28 s; registers pinned at `(155, 127, 1)` |
| Step 7 | **PASS via post-open re-apply** — held 32 s |
| Step 8 | frame rate ✅; exposure floor vs real roaster lighting **still open** |

Exported control set (16): `absolute_exposure_time`, `absolute_focus`,
`absolute_pan_tilt`, `absolute_zoom`, `auto_exposure_mode`,
`auto_exposure_priority`, `auto_focus`, `auto_white_balance_temperature`,
`backlight_compensation`, `brightness`, `contrast`, `gain`,
`power_line_frequency`, `saturation`, `sharpness`, `white_balance_temperature`.

**The finding that matters for the vision module.** Opening the capture runs an
auto-exposure pass that overwrites the lock — observed jumping `exposure
10 → 415, gain 128 → 255` against a dark scene. Re-applying *while streaming*
sticks and stays stable. Any code that configures the camera at init and trusts
it is silently running at gain 255. Order is: open capture → set controls →
verify by readback.

**Lighting, measured.** At 1 ms in a normally lit room the C920 gives mean
**0.47** — no usable image. The ramp at gain 127:

| exposure | 1.0 ms | 2.0 ms | 4.0 ms | 8.0 ms | 15.6 ms |
|---|---|---|---|---|---|
| mean | 0.47 | 5.29 | 26.16 | 66.08 | 115.52 |

Reaching a usable mean at 1 ms therefore needs roughly **16x** that room's
illumination, or ~8x at gain 255 with the attendant noise. This is a lighting
spec, not a camera problem — see § Lighting. Step 8 remains to be run into the
drum under real conditions before the exposure/lighting pair is settled.

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

**Phase 1.5 — camera decision.** Ordering:
1. Run the **§ UVC probe procedure** on a webcam already on hand. Pass → carry
   Phase 1 on it at zero cost, treating the result as provisional
   (§ Camera continuity). Fail → proceed to buy.
2. Knowing what the metric needs (frame rate, shutter type, whether view 2
   earns its slot), buy **one** Basler dart daA1440-220um (CS-mount) + a fast
   manual lens + lighting (§ Recommended camera, § Lens).
3. Re-validate the metric on the final camera if Phase 1 was tuned on a probed
   webcam — different shutter and noise characteristics shift the flow field.

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
5. Does a webcam already on hand clear the macOS manual-exposure bar, or is
   the Basler purchase required? (§ UVC probe procedure — run early, it gates
   Option A and a several-hundred-dollar decision. Answered as of: not yet run.)
6. Mac-to-roaster USB cable reach, and whether active extension is needed.
