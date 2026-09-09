# state-plan — planned work and specifications in force

> Companion to [state-current.md](state-current.md) (what is active now),
> [state-history.md](state-history.md) (the roast-by-roast reasoning that
> produced the decisions below) and [state-archive.md](state-archive.md) (what
> is done, and the review findings these phases answer). Findings are
> referenced as F-numbers from the archive.
>
> **What belongs here: work not yet done, and the specifications currently in
> force.** Every configuration key, file, alarm and firmware command described
> below is either something to build or something to load. The evidence for
> *why* each value is what it is — the roasts, refits, sweeps and the
> conclusions that were later overturned — lives in state-history.md and is
> referenced as `state-history.md § …`. If a section here reads as a record of
> what happened rather than a statement of what to do, it is in the wrong file.

## Bean reference — the first-crack temperature each lot cracks at

**A specification in force**, because it is the `--fcs <s>:<BT>` argument
`tools/make_background.py` is handed and nothing else supplies it — but it is
**derived, not recorded**. Every `.alog` carries `plus_coffee` (the artisan.plus
hr_id), `plus_coffee_label` and the crack mark, so the table is read out of the
logs:

```
.venv/bin/python tools/analysis/beans.py               # every coffee
.venv/bin/python tools/analysis/beans.py --coffee C1043
```

It prints the `--fcs` and `--ror-at-fcs` arguments to hand `make_background.py`.
**Do not maintain a copy by hand** — the snapshot below is illustrative and the
tool is authoritative.

**Artisan cannot store this.** The `Coffee` record artisan.plus syncs down
(`~/src/artisan/src/plus/stock.py:82-94` at v4.2.0) carries `label`, `origin`,
`varietals`, `grade`, `stock`, `default_unit`, `moisture`, `density`,
`screen_size`, `processing` and `crop_date` — and no temperature field of any
kind. There is nowhere to put it and nothing that would apply it forward.

Snapshot at roast 57, cascade-era only (roast ≥ 40, ≥ 380 g, `roastertype`
`airRoaster`):

| `plus_coffee` | coffee | roasts | FCs BT median | spread |
|---|---|---|---|---|
| `C1043` | Ethiopia, Crown Jewel Sidama Daye Bensa Washed | 43, 44, 46, 49, 56, **57** | **197.6** | 195.3-197.9 |
| `C1062` | Kenya, CJ Ichamama Factory Othaya Town | 53, 54, 55 | **197.4** | 197.3-198.7 |
| `C1074` | Colombia, Crown Jewel Carbonic Honey Peach Co-Ferment | 50, 51, 52 | **200.1** | 198.1-201.2 |

**Never pool across coffees.** This is the error the roast-56 background was
built on: a "mean over roasts 50-55" of 198.8 degC is a mean over `C1074` and
`C1062` and describes neither. Within a lot the spread is 1.6-3.1 degC and most
of that is mark subjectivity; between lots it is real. state-history.md § The FC
temperature is a property of the lot has the full correction, including that
`profile_003`'s original **197.5** was right for both coffees it was ever run
against.

**One roast does not characterise a lot, but four in a 0.5 degC band do — and
roast 57 closed this one.** `C1043` reads 197.4 / 197.7 / 197.8 / 197.9 across
roasts 43, 44, 46 and 49, **195.3** on roast 56, and **197.40 on roast 57**. Five
readings inside 0.5 degC and one 1.2 degC below the rest: **195.3 is a mark made
early by ear, not a new bag**, and the lot's number is **197.6**. The tool now
prints `--fcs <s>:197.6 --ror-at-fcs 9.4`, and
`artisan/profile_400g_m5C_fc195_v5.alog` — which was parked on that single
reading — **is retired.**

The general caution stands for the next lot: artisan.plus identifies the
*coffee*, not the crop or the bag, so a new bag under the same hr_id is
invisible; that is the one thing the tool cannot tell you. **The way to tell them
apart is a second roast**, which is what roast 57 was.

**Regenerating for a new FC temperature used to be a change to the first
minute; since 2026-09-08 it is barely one.** The old behaviour was a defect, not
a property of a global fit — the exponential spec has **four** free parameters
(`tau_r, R0, R_inf, tau_d`) and DRY END / FCs / RoR@FCs supply **three**, so the
ramp was undetermined and the optimizer chose it off floating-point noise. At
400 g / −5 degC, BT at 60 s:

| `--fcs` | 198.8 | 197.7 | 197.4 | 195.5 | spread |
|---|---|---|---|---|---|
| **before** — ramp free | 80.6 | 74.8 | 78.1 | 73.4 | 7.2 degC, non-monotone |
| **now** — `--ror-peak-at 53` | 78.4 | 78.7 | 78.8 | 79.3 | 0.8 degC, monotone |

### The RoR-peak pin is a specification in force

`make_background.py --ror-peak-at <s since CHARGE>`, **default 53**, is the
fourth constraint that makes the fit square. Rules:

- **Leave it at 53 unless you are deliberately testing it.** 53 s is where
  `profile_400g_m5C_v4.alog` (roast 56's background, the only curve to pass all
  four checks) happens to peak, so the fix reshapes nothing silently. It is a
  lottery draw promoted to a spec, **not a measurement of the machine.**
- **It is a design number now, so it can be swept** — one roast at a time, like
  any other. Earlier peak = more rate demanded while the loop is still
  recovering from the charge and `Ki` is gated; later = the reverse. Reachable
  band at 400 g / −5 degC is about **45-80 s**; outside it the tool says the
  constraint is not satisfied and the ramp is unpinned again.
- **The peak's *time* is pinned, not its height.** Height varies only 48.2 to
  43.5 degC/min along the whole old null manifold, so it identifies the missing
  parameter ~8× worse (−0.10 degC/min/s against +0.85 s/s).
- **`--decline linear` takes no pin** — three parameters, always square.
  `--free-ramp` reproduces the pre-fix behaviour for comparing against an old
  file, and warns that it is doing so.
- **Verified** to 1e-14 with RoR monotone across −24…+25 degC and 250…500 g, in
  both `--development` and `--drop` mode.

**Still never run a regenerated background and a control change in the same
roast**, and print the 30-120 s column before loading one — the 0.8 degC has
been demonstrated in the fit, not yet on the machine.

**Cheapest reading of all this**: the FCs mark is a *label*. Nothing in the
cascade reads it — `calcSV` reads only `BT(t + svLookahead)` and `drop_t`
(`pid_control.py:1658-1717`) — so a curve marked 198.8 at 399 s that passes
195.4 at 375.8 s still puts a 195.4-cracking bean at a repeatable 375 s.
Regenerate when you want the crack at a different **time**, not merely to make
the label true.

## NEXT — remaining on-roaster validation

The live sessions of 2026-07-02/03/04 (see the archive's v0.12–v0.15 entries)
validated much of the original checklist; items are marked accordingly.
Remaining drills, roughly in commissioning order:

1. ~~**Boot sync sanity**~~ — **done/superseded.** Heat-zero at boot stands;
   fan-level adoption via `getLevel()` was replaced by the RTC no-init shadow
   (v0.15.0, reads lie while firing). Fan-through-reboot validated 2026-07-04
   via a live OTA update with the fan running.
2. **Sensor path**: BT read sane in live sessions, but the specific checks are
   unrecorded — `STAT` after a few minutes (`loopMaxUs` should be dominated by
   the ~30 ms display push, not sensor reads); compare RTD fault frequency in
   the log against pre-v0.8.0 roasts (emi.md addendum says what to expect).
3. **Failsafe drills** (roaster cold, heat low): engage `INLET`, unplug the
   inlet TC → expect `inlet failsafe: inlet PV stale` within ~3 s, heat 0,
   mode manual. Confirm a TUNE aborts the same way.
4. **Telemetry + dashboard** — **mostly done**: the commissioning sequence
   (TUNE → APPLY → FF cal → INLET) ran end-to-end in the 2026-07-03 session.
   Still unchecked: kill/restore WiFi to see auto-reconnect on both sides.
5. **WDT confidence**: none of the normal paths (tune, big display repaints,
   WS bursts) should approach 8 s — `loopMaxUs` gives the margin number.
6. ~~**DimmerLink reset escalation**~~ — **superseded.** v0.13.0 removed
   autonomous resets entirely (soft reset drives the output full-on for
   ~3–4 s); resets are operator-only via `DLRESET`. The fw-version line at
   boot is still worth a glance.
7. **Interlock config (v0.10.0)**: from the dashboard panel set soft mode and
   custom limits, confirm the heat cap follows the fan slider accordingly, then
   power-cycle and confirm the values and mode survive (NVS). Try an invalid
   set (`IL 0 55 30`) and confirm it is rejected.
8. ~~**Power linearization (v0.11.0)**~~ — **done.** TUNE and FF calibration
   were re-run post-map; closed loop settles on SV and FF compensates fan
   steps (validated 2026-07-03, v0.14.1).
9. **OTA idle gate (v0.12.0)**: an OTA push with heat > 0 should time out on
   the host, then succeed again at heat 0. The happy path (idle OTA push,
   reboot, fan preserved) is validated.
10. **Curve experiments** (`CURVE FAN 0|2`, optional): compare fan response per
    level step on the dashboard chart; expectation is RMS (1) remains best.
    Reboot restores RMS automatically.
11. **Cooldown guard (v0.16.0)** — *mostly validated 2026-07-05*: deferral,
    hold, auto-release, and soak-back re-enforcement all observed working on
    the roaster. The 30 s dwell released early into soak-back (two re-enforce
    cycles), so the dwell is now adjustable (`COOL DWELL <s>`, NVS): find the
    dwell that makes one release stick (start ~90–120 s) and set it. Still
    unchecked: `COOL MIN`/`COOL DWELL` surviving a power cycle (NVS), and
    `COOL OFF` releasing a held fan immediately.
12. **Ambient reporting (v0.17.0)** — on a cold roaster, power up and check the
    serial log for `ambient: cold-start capture` with a sane room temp (BT vs
    CJ within 8 °C); dashboard Ambient panel should show it. Then run the
    roaster hot, power-cycle, and confirm the log says `warm boot … keeping`
    and the stored capture is unchanged. Check `AMB SRC`/`AMB <degC>` survive
    a power cycle (NVS). In Artisan: map the `AT` node to an extra WebSocket
    channel, select it on Config › Device › Ambient, and confirm Roast
    Properties picks up the ambient temperature at CHARGE (README § Ambient
    temperature has the click-path).
13. **Command auth (v0.18.0)** — with `AUTH_KEY` in secrets.h: dashboard
    authenticates automatically (key field) and `AUTH` reports authed; set
    `AUTH MODE CONFIG` and confirm an *unkeyed* browser gets "AUTH required"
    for `PID`/`IL`/`COOL MIN` but can still run `OT1 60`, `OT1 0`, `INLET
    OFF`, `COOL ON`; set `AUTH MODE FULL` and confirm `OT1 60` is refused
    unkeyed while `OT1 0` still works; run `tools/roaster_proxy.py` with the
    key and confirm live Artisan drives sliders through it in FULL mode;
    wrong-key proxy → refused; mode survives a power cycle (NVS); serial
    stays fully trusted. Also confirm a keyless build (empty AUTH_KEY)
    behaves exactly as v0.17.
14. **`INLET TRIM` (v0.19.0, second item)** — bench drill, heater cold, fan at
    a level that clears the interlock; watch the dashboard Setpoint panel and
    the serial log. (a) `INLET 200`, then `INLET TRIM 20` → readout `base 200.0
    + trim +20.0 = SV 220.0`, OLED `Inlet SV:220`, and the PID `I` term must
    carry on from where it was rather than jump — a trim is a retarget on an
    already-engaged loop, and a retarget must never re-seed the integrator.
    (b) `INLET TRIM -20` → effective 180. (c) bare `INLET TRIM` →
    reports all three. (d) stop sending for 15 s → `inlet trim stale: ramping to
    0` appears **once**, the effective SV walks back to the base at 2 °C/s
    (10 s from ±20), and one status push lands when it arrives; confirm the base
    is untouched and the loop is still engaged. (e) `INLET TRIM 20` again, then
    each of `INLET OFF`, `INLET 0`, `TUNE` (then `TUNE ABORT`), and a forced
    failsafe (unplug the inlet TC, as in item 3) → `INLET TRIM` must read
    `trim 0.0` after every one.
    (f) bounds: `INLET TRIM 500` clamps to +80, `INLET TRIM -500` to −80,
    `INLET TRIM abc` replies `invalid argument` and changes nothing.
    (g) auth: with `AUTH MODE FULL` and an unkeyed browser, **every** form —
    `INLET TRIM 20`, `INLET TRIM 0`, and bare `INLET TRIM` — must be refused,
    while `INLET OFF` and `INLET 0` still work. (h) regression: run a normal
    `INLET <degC>` session start to finish without ever sending `INLET TRIM` and
    confirm nothing differs from v0.18 behaviour.

## Artisan cascade PID — outer BT loop driving the inlet setpoint

*Active effort, branch `feature/artisan-pid` (off `main` at v0.18.0).
Artisan configuration + docs + commissioning; **no firmware change**.*

**Shape.** Artisan's software PID becomes the *outer* loop of a cascade: it
controls BT against a background curve, and its output is the **inlet
setpoint** that the firmware's existing `MODE_INLET` loop holds.

```
background BT curve (authored in Artisan's Designer)
  -> Artisan software PID (PV = BT, pidCycle 1000 ms)
  -> duty 0-100% mapped onto the slider-3 subrange [140, 300] degC
  -> slider 3 action: send({"command":"INLET","value":{}})
  -> firmware controlStep() (250 ms) modulates heat to hold that inlet temp
```

The firmware needs nothing new: `INLET <degC>` is already the entry point,
`engageInlet()` is already bumpless on retarget (keeps the integrator across a
gradually-moving setpoint), and the JSON envelope already preserves the
fraction (airRoaster.ino:1141). Time-constant separation is why this should
work — inlet air responds in seconds, BT in tens of seconds.

**Why not the flat loop.** Today `pidSource=3` points Artisan's software PID at
the *Inlet* channel with output to slider 4 (OT1 heat): Artisan duplicating the
firmware's own inner loop across a 1 Hz WebSocket link. The cascade keeps the
fast inner loop on-device and hands Artisan the slow outer job it is good at —
profile following against a background curve.

**Design decisions (operator-confirmed 2026-09-02).**

- Outer PV = **BT**, which is `pidSource=1` (see § Verified against source).
- Outer SV = **follow background** (`svMode=2`, already set); curves authored in
  Artisan's **Designer**.
- `artisan/make_inlet_background.py` is **out of scope and unchanged.** It
  remains the tool for the *inner*-loop event-playback path (README § Driving
  the setpoint from a roast profile), which stays available as the non-cascade
  alternative. The cascade does not generate inlet curves at all — the inlet
  setpoint is computed live by the outer loop.
- Output target = **slider 3** (`pidPositiveTarget=3`), the existing `INLET`
  slider.
- Setpoint range **140-300 degC via `positiveTargetRangeLimit=true`,
  `positiveTargetMin=140`, `positiveTargetMax=300`** — see § The floor for why
  this, and not `dutyMin`/`dutyMax`.
- `pidOnCHARGE=true`, `pidOffDROP=true`.
- **Heat-off at drop needs an Artisan alarm**, not `PID_OFF_action` — see
  § Heat-off at drop.
- Inner loop **not retuned** — Kp 1.5 / Ki 0.05 / Kd 0 stand (roast-validated).
  Revisit only if commissioning shows the inner loop is the limiting factor.
- The alternate gain sets (`pidKp1/2` etc.) were leftovers of unknown
  provenance; they are overwritten to match the new single set.
  `pidGainScheduling` stays false.

**Deliverable.** **`artisan/airRoaster_cascadePID.aset`** — the single canonical
config. It was briefly split into an `_edit` variant while the operator added the
alarms in Artisan; that content was folded back onto this filename 2026-09-02
and the `_edit` file removed (recoverable from commit 90c9c46). The background is now
**`artisan/profile_002.alog`** (CHARGE BT 127.8, DRYe 3:20, FCs 6:30, DROP 6:51
at BT 201.2 — a gentler middle ramp than `profile_001` to the same endpoint,
reached sooner). Both backgrounds carry zero special events, so neither can
conflict with the PID over slider 3.

*Superseded:* `artisan/airRoaster_cascadePID.aset`, derived from
**`artisan/airRoaster_inletPoints.aset`** (the operator's live config as saved
2026-09-02, which supersedes the older `airRoaster.aset` in the repo). Both
originals are left untouched so the playback setup stays loadable.

`airRoaster.aset` and `airRoaster_inletPoints.aset` differ in batch counters,
`RoRlimit`, `autotimex`, three new playback event buttons (17-19), and a new
alarm — but their **`[ArduinoPID]` and `[Sliders]` sections are byte-identical**,
so the PID delta below applies to either base. `inletPoints` is the right base
because it carries the operator's refined playback/event wiring.

| Key (`[ArduinoPID]`) | From | To |
|---|---|---|
| `pidSource` | 3 (Inlet) | 1 (BT) |
| `pidPositiveTarget` | 4 (OT1 heat) | 3 (INLET) |
| `positiveTargetRangeLimit` | false | true |
| `positiveTargetMin` / `positiveTargetMax` | 0 / 4 | 140 / 300 |
| `pidKp` / `pidKi` / `pidKd` | 0.18 / 0.054 / 0.09 | 3.0 / 0.04 / 0 |
| `pidKp1,2` / `pidKi1,2` / `pidKd1,2` | 27 / 0.018 / 36 | 3.0 / 0.04 / 0 |
| `svLookahead` | 0 | 20 s |
| `pidDsetpointWeight` | 1 | 0 (derivative on measurement) |
| `pidOnCHARGE` / `pidOffDROP` | false / false | true / true |

`dutyMin`/`dutyMax` stay **0 / 100** and `[Sliders]` is **unchanged** — both
deliberate, see below.

### Verified against source

Read from `artisanlib/{pid,pid_control,main,canvas}.py` at
github.com/artisan-roaster-scope/artisan (the shipped .app is compiled, so the
bundle cannot answer these). This settles all four items previously listed as
open, and corrects two earlier assumptions.

1. **`pidSource` numbering is 1=BT, 2=ET, >2=extra curves** with
   `n = pidSource-3`, `c = n//2`, even `n` = channel A / odd = channel B
   (`pid_control.py:1432`). So BT is **1**, not 2. The earlier inference of
   1=ET/2=BT was backwards. The identification of `pidSource=3` as extra1A
   ("Inlet") was right, since extras start at 3 either way.
2. **The PID output is a duty in [0,100] that is linearly mapped onto the
   target slider's range** (`pid_control.py` `setEnergy`):
   `raw = numpy.interp(v, [0,100], [heat_min, heat_max])`, where `heat_min/max`
   come from the slider's own min/max, narrowed to
   `[positiveTargetMin, positiveTargetMax]` when `positiveTargetRangeLimit`.
   So the slider range governs the commanded degC entirely.
3. **The fractional value does reach the command.** `setEnergy` emits both the
   rounded int and `raw_heat`; `addEvent_internal` uses the int only for the
   slider position and change-detection, and passes `raw_value` to the slider
   action ("if raw_value is not None, it is send to the slider action instead
   of the integer value"). No 1 degC quantization on the wire — the earlier
   concern about `dutySteps` re-introducing what airRoaster.ino:1141 removed
   does not apply to the *value*. It does bound the update *cadence*: an update
   is emitted when the duty moves by `dutySteps` (1 duty unit = 1.6 degC over
   the 160 degC span) or the integer slider position changes.
4. **Slider action type**: stored `slideractions=18` maps through
   `eventactionx` (`a+2` for `21 > a > 5`) to action 20 = "Artisan Command",
   which is what accepts the `send({...})` form. Unchanged by this work.

### The floor — and the correction that matters

`INLET <= 0` means *disengage*, not *setpoint 0* (v0.15.1, README § Inlet
temperature control): Artisan's SV slider parks at 0 after a background
playback, and a 0 degC target would leave the loop railed with heat pinned at
0. In a cascade, an outer loop that saturates low would kick the inner loop to
`MODE_MANUAL` at heat 0 and then, next tick, re-engage through `engageInlet()`
— which reseeds the integrator from the now-zero heat level. Not mere mode
chatter: a full inner-loop reset plus a heat kill, once per tick. The output
must therefore be structurally unable to reach 0.

**`dutyMin=120` was the wrong mechanism and would have been dangerous.**
`dutyMin`/`dutyMax` are *duty percentages*, not degC: `pid.py:473` clamps
`final_output = min(dutyMax, max(dutyMin, output))` where `output` is already
bounded by `outMin=0`/`outMax=100`. Setting `dutyMin=120` would pin
`final_output` at 120 every cycle, and `numpy.interp(120, [0,100], ...)` clamps
above the input range and returns `heat_max` — i.e. **the inlet setpoint would
sit at its maximum permanently, with the outer loop having no effect at all.**
A runaway-heat configuration. (`pid_control.py:1502` separately re-clamps
`dutyMin/Max` into 0-100 on the ArduinoTC4 path, confirming the intended
domain.)

The correct mechanism is the one Artisan documents for exactly this:
`positiveTargetRangeLimit=true` with `positiveTargetMin=140`,
`positiveTargetMax=300` — "the duty is mapped to the target slider subrange"
(`pid_control.py:1196`). Duty 0% -> 140 degC, duty 100% -> 300 degC. (120 until
roast 40, briefly 170, then 140 to allow a PID-driven preheat; see below.)

**`[Sliders]` is deliberately left alone.** Artisan's own stated assumption is
`slider_min < positiveTargetMin < positiveTargetMax < slider_max`
(`pid_control.py:1302`). Slider 3's existing 0-320 satisfies
`0 < 140 < 300 < 320`. The earlier plan to tighten `slidermax` to 300 would
violate it — so the 320/300 mismatch against `INLET_SV_MAX_C` stays, and
remains harmless (the firmware clamps, and the cascade never asks above 300).

Note the floor is a *heating* floor: on a BT overshoot the coolest the cascade
can ask for is 140 degC inlet. The operator's path below that is to turn the
PID off, which is also what `pidOffDROP` does at the drop.

### Heat-off at drop — already wired, no alarm needed

**This is already configured in `airRoaster_inletPoints.aset`** and needs no new
work. `buttonactions=0,0,0,0,0,0,20,0` with
`buttonactionstrings[6]="16,15,11"`: index 6 is DROP (canvas.py `markDrop` calls
`eventactionx(self.buttonactions[6], ...)` at canvas.py:15542), and stored 20
maps through `eventactionx` to action 3 = Multiple Event, which presses extra
event buttons 16, 15 and 11:

| Button | Label | Effect |
|---|---|---|
| 16 | `playback_OFF` | `playbackmode(0)` |
| 15 | `inlet_OFF` | `send({"command":"INLET","value":0})` -> firmware manual, heat 0 |
| 11 | `heatSlider_OFF` | event type 3 value 0 -> slider 3 to 0, same INLET 0 (redundant, harmless) |

`INLET 0` is exactly the v0.15.1 cooldown path: `MODE_MANUAL`,
`requestedHeatLevel = 0`, `applyInterlock()`.

**The ordering against `pidOffDROP` is safe.** In `markDrop`,
`pidcontrol.pidOff()` runs at canvas.py:15424, *before* the button action at
canvas.py:15542 — so the PID is already stopped when `INLET 0` is sent and
cannot re-command a setpoint afterwards. (CHARGE mirrors this: `pidOn()` at
canvas.py:14656 precedes `eventactionx(buttonactions[0])`.)

**An earlier draft of this plan was wrong twice here** and both errors are
retracted: first that `PID_OFF_action` could carry `INLET 0` (it fires only for
external MODBUS/S7 PID control, `pid_control.py:1538-1545`; this is a WebSocket
device so `externalPIDControl()` returns 0), and then that an Artisan **alarm**
should send the WebSocket command instead — alarm actions have their own
numbering that tops out at 25 (`canvas.py:6153-6335`: 0=popup, 2=event button,
3-6=sliders, 13=DROP, 22=Playback ON, 23=Playback OFF, 24/25=canvas colour) and
include **no** WebSocket or Artisan Command action at all. An alarm could only
have reached the firmware indirectly via action 2 (press an event button). None
of that is needed, because the DROP button action already does it directly.

### Background event playback must be off

The one genuine conflict. In `airRoaster_inletPoints.aset`,
`specialeventplayback=false, false, true, false` and
`specialeventplaybackramp=false, false, true, false` enable replay of the
**T_inlet** event type — which drives **slider 3**. The cascade's outer PID
drives that same slider. Both writing it would fight.

The live config also carries an alarm that turns playback on automatically:
enabled, source -3 (no temperature source, so time-only), `alarmtime=0`
(after CHARGE), `alarmoffset=1` (1 s), `alarmaction=22` = **Playback ON**
(`turn_playback_event_ON()`), empty command string. It must not fire in the
cascade config.

So `airRoaster_cascadePID.aset` additionally sets, outside `[ArduinoPID]`:

| Key | From | To |
|---|---|---|
| `specialeventplayback` | `false, false, true, false` | all `false` |
| `specialeventplaybackramp` | `false, false, true, false` | all `false` |
| `alarmflag` | QVariantList[int] = 1 | 0 (alarm disabled) |
| `buttonactionstrings[0]` (CHARGE, `[DefaultButtons]`) | `"17,18,19"` | *(empty)* |
| `Controlbuttonflag` (`[Device]`) | false | **true** |

The CHARGE row is the third playback trigger in the live config: buttons 17-19
are `playback_time` / `playback_ON` / `playback_ramp`. It was already inert
there — `buttonactions[0]=0` (None) means `eventactionx` never runs the string —
but leaving the string in place is a trap: setting the action type would
silently start playback fighting the PID for slider 3. Cleared in the cascade
config.

### Config > Device > Control must be ticked

`Controlbuttonflag` (Config > Device > "Control") gates the software PID
itself, not just the visibility of the CONTROL button. `pidOn()`'s software-PID
branch is `elif self.aw.qmc.Controlbuttonflag:` (pid_control.py:1519), so with
the flag false `pidOn()` falls through and never activates the PID — meaning
`pidOnCHARGE` would silently do nothing. Monitor start likewise skips
`confSoftwarePID(reset=True)` unless `externalPIDControl() == 0 and
Controlbuttonflag` (canvas.py:13438), so the PID would never even be configured
with the current gains and sampling rate.

The live config has it **false**, so this is a required change, not a
convenience. It also surfaces the CONTROL button, which is the operator's
manual PID on/off — the escape hatch for dropping below the floor
mid-roast. (`PIDbuttonflag` is a different flag, for TC4/Fuji hardware PID
control; left as-is.)

**CHARGE still arms the outer loop**, without a button action:
`pidOnCHARGE=true` makes `markCharge` call `pidcontrol.pidOn()` directly
(canvas.py:14656), before any button action runs — mirroring `pidOffDROP` at
canvas.py:15424. This is also the moment the charge-aligned background SV curve
becomes meaningful. The remaining `[DefaultButtons]` rows (DRY, FCs, FCe, SCs,
SCe, COOL) are all action 0 with empty strings and need nothing.

These are exactly what to re-enable when switching back to the inner-loop
playback workflow — which is why the two configs stay separate files rather
than one file with a mode switch.

### Auto-DROP detection (operator requirement 2026-09-02)

DROP is the trigger for the whole heat-off chain — `pidOffDROP` stops the outer
loop and `buttonactions[6]` sends `INLET 0` — so a missed DROP leaves the heater
running. The operator wants it detected from the lever pull, which is plainly
visible in the traces (BT falls, RoR plummets).

**Artisan's built-in auto-DROP cannot do it.** `canvas.py:5151-5153` gates the
BT-break detector on `(sample_timex[-1] - sample_timex[timeindex[0]]) > 7*60` —
**auto-DROP cannot fire until 7:00 after CHARGE**, and these roasts drop at
6:20-6:31. `7*60` is a literal, so the Standard/Sensitive `autoDropMode` switch
is never consulted. (For the record, at 1 s sampling Sensitive only changes
`d_drop` from -0.34 to 0.00; `offset_drop` is identical at 0.2.)

**The background path is a scheduled drop, not detection.** `playbackdrop()`
(canvas.py:6345-6356) has a 4-minute gate (`playbackdrop_min_roasttime = 4*60`)
and its own flag `backgroundPlaybackDROP`, independent of event playback
(canvas.py:5384) — so it could be enabled without reintroducing the slider
conflict, via the Artisan Command `playbackdropmode(<n>)` (0 off, 1 by time,
2 by BT, 3 by ET). But it fires on the profile's schedule: by BT it needs the
background's DROP BT to sit *below* where the operator actually pulls (roast 42
peaked at 201.0 against a 202.0 background DROP, so it would never have fired),
and by time it fires at the profile's DROP regardless of the lever. Left off.

**The solution: an alarm on the RoR collapse.** Alarm action 13 = DROP
(canvas.py:6260-6263) with no time gate. Threshold sized from the traces
(10 s RoR span, degC/min):

| | roast 41 | roast 42 |
|---|---|---|
| min during DRYe..DROP (armed window) | -4.9 | **+5.4** |
| after the dump | -24.6 | **-43.6** |
| **charge dip** (for contrast) | **-266.7** | **-267.0** |

`-25` never occurs while roasting (tightest margin ~20 degC/min) and is crossed
within ~3 s of the BT peak at the dump. The charge dip at -267 is why the alarm
**must not be armed from CHARGE** — it would fire at turning point every roast.
DRYe (~2:36-3:20) is safely past TP (~0:30).

As entered and verified in `airRoaster_cascadePID.aset`:

```
alarm 1: off  From=CHARGE   offset=1s  Source=(none/time)  above    0  -> Playback ON
alarm 2: ON   From=DRY END  offset=0s  Source=DeltaBT      below  -25  -> DROP
```

**`Time` must be 00:00.** The alarm's time and temperature conditions are OR'd,
not AND'd — `if alarm_time >= alarmoffset: alarm_ready = True` (canvas.py:5286)
and the temperature block each set the flag independently. A non-zero offset
makes the alarm fire on the clock alone, ignoring the RoR entirely.

Safe alongside a manual press: the DROP action is guarded by
`timeindex[6] == 0`, so whichever comes first wins and there is no double-mark.
Artisan's own `autoDrop` can stay on; its 7-minute gate makes it inert at these
roast lengths.

**Still wanted eventually** (operator): instrument the dump lever so the pull
sends a real signal. The clean path needs no new Artisan capability — expose the
lever as an extra channel in `handleArtisanRequest()` (README § adding a
channel), then an alarm with Source = that channel, condition above 0.5, action
DROP. Same alarm mechanism, a measured event instead of an inferred one.

### Files for the characterisation runs (2026-09-02, procedure revised 2026-09-06)

Both are ordinary background profiles carrying the test's inlet schedule as
**T_inlet events**.

| file | test | schedule |
|---|---|---|
| `artisan/charstep_empty_fan.alog` | **A** - empty roaster, no beans, 17 min | the original inlet steps crossed with a **fan sweep 58-80** on an offset grid (`tools/gen_char_empty.py`) |
| `artisan/chardoublet_fan60.alog` | **B/C** - loaded, sacrificial, 9 min | fan 64 to 1:30, ramp at **60**, inlet doublet 3:00-5:00, plateau, fan 70/60/70 over 6:00-9:00 |
| `artisan/chardoublet_fan68.alog` | **B/C** - loaded, sacrificial, 9 min | the same with the ramp at **68** and the square wave phase-reversed (60/70/60) |
| `artisan/charstep_empty.alog`, `artisan/chardoublet_loaded.alog` | superseded | the 12- and 7-minute originals the three above are generated from |

**They are replayed, not hand-driven** (revised 2026-09-06; the original
procedure was to follow the curve on slider 3 by hand). `specialeventplayback`
is a **per-event-type** 4-element list (canvas.py:1848) and the master switch
`backgroundPlaybackEvents` is separate, so enabling types 0 (`Air`, slider 1) and
2 (`T_inlet`, slider 3) replays the inlet *and* fan schedules and touches nothing
else. The collision that
forced playback off for the cascade (§ Background event playback must be off) is
*specifically* that playback and the PID both want slider 3 — which cannot arise
here, because these runs are open-loop by construction. Replaying instead of
hand-driving makes the excitation identical between runs (which is what turns
the fan comparison into a difference of one variable rather than of two) and
**rehearses the exact machinery step 9 depends on** at zero extra cost.

**File: `artisan/airRoaster_cascadePID_char.aset`**, generated by
`tools/gen_pid_alarm_asets.py` as a key-override variant of the canonical config
— no buttons, no alarms, four keys:

```
pidOnCHARGE = false                        # the PID must never arm
backgroundPlaybackEvents = true            # master playback switch
replayType = 0                             # replay by time
specialeventplayback = true, false, true, false    # Air + T_inlet
alarmflag = 0, 0                           # the DeltaBT auto-DROP alarm
autoDrop = false                           # *and* Artisan's built-in detector
```

**`autoDrop` is the one roast 47 was missing, and it is not an alarm.** Artisan's
built-in DROP detector (canvas.py:5151) is gated on `autoDropFlag`, BT > 160 degC
and **more than 7 minutes since CHARGE**, and `alarmflag` does not touch it. That
7-minute gate is why it has never been seen here — these roasts drop at 6:20-6:31,
which is the whole reason the DeltaBT alarm exists (§ Auto-DROP detection) — but
**every characterisation run is longer than 7 minutes and above 160 degC**. On
roast 47 it fired on the 10:01 inlet step-down and cost 88 s and one steady
window; it would have taken the last third of the fan measurement out of both
loaded doublets.

**Procedure, all three tests: press ON, load the file as background, press START,
then press CHARGE.** CHARGE is now required rather than forbidden — `playbackevent()`
runs only once the foreground CHARGE is marked (canvas.py:5381) — and it is safe
because `pidOnCHARGE` is forced off in the file rather than avoided by not
pressing the button. Everything after that is automatic; the operator's job is
the fan level and DROP.

**Why the DeltaBT alarm is disabled too.** `autoDRY` can mark DRY END on an
*empty* roaster — the empty-run background takes BT to 168 degC, past the 149 degC
Phases threshold — which would arm the DeltaBT auto-DROP in the middle of a step
test and end the run through the `INLET 0` chain. Press DROP by hand on these
runs.

**Why a doublet rather than a step for Test B**: its net energy is ~zero, so the
batch lands near where it would have; and a 60 s half-period places the peak
excitation near a 240 s period, inside the loop's 250-330 s crossover band.

**Test B is subsumed into Test C (2026-09-06).** Test C was specified as Test B
repeated at fan 58 and fan 65, i.e. three sacrificial batches in total. Two
batches at fan 58 and fan 65 deliver both purposes — each is an independent
deliberate doublet (test B's remaining job, since roast 46 already gave theta and
tau) and the pair is the fan contrast (test C's job). **The residual weakness is
that a two-batch fan contrast confounds fan with batch**, which roast 46 showed
is not a small effect; closing that needs fan excitation *within* a batch, and
therefore a new background file, not a fourth run.

### The lookahead-switching config (2026-09-02)

`artisan/airRoaster_cascadePID_lookahead.aset` — the canonical config plus the
runtime lookahead switch from state-history.md § Scheduling. **A separate file
deliberately**: it is an experiment and should not ride along with the `pidKi`
and profile_003 changes on the next roast.

Two new event buttons appended after the existing ones — action 20 = Artisan
Command, hidden, recording no event — the first running `pidLookahead(0)` and
the second `pidLookahead(6)`. As of 2026-09-03 the canonical config has 19 event
buttons, so they are user-facing **20** and **21**.

> **The button numbers are positional and will drift.** They were 22/23, then
> 23/24 when a "Fan Mid" button was added, then 20/21 when the canonical config
> was reworked from 22 buttons down to 19. `alarmstrings` holds the **1-based
> index**, so adding or removing an event button silently re-points these
> alarms. **Never hand-edit this variant.** Regenerate it with
> [tools/gen_pid_alarm_asets.py](tools/gen_pid_alarm_asets.py), which derives the
> button numbers from `len(extraeventslabels)` in the canonical file and appends
> the buttons and alarms to a fresh copy of it.

```bash
python3 tools/gen_pid_alarm_asets.py
```

and two new alarms, both **time-only from CHARGE** (`alarmsource = -3`, so the
temperature branch never evaluates and the OR'd conditions cannot misfire),
action **2** = press an event button, whose `alarmstrings` entry is the
**1-based** button number (canvas.py:6194-6211):

```
alarm 3: From CHARGE, offset  1 s, source -3 -> button 20 -> pidLookahead(0)
alarm 4: From CHARGE, offset 90 s, source -3 -> button 21 -> pidLookahead(6)
```

So the dip runs at lookahead 0 — no manufactured error, no SV floor at turning
point (state-history.md § profile_003) — and the ramp gets 6 s of feedforward,
which costs no phase margin. 90 s is past turning point and where the background
RoR has fallen enough that the switch is a ~+3.5 degC target step rather than
+4.6.

### Step 9 — the inlet feedforward schedule with the PID as a trim (design)

*The design that runbook step 9 executes. It came out of the strategy search of
2026-09-06 (state-history.md § Dip strategies), which is where the sweep numbers
and the discarded alternatives are.*

> **A cheaper relative was proposed 2026-09-08** — commanding `Temp_Drive =
> Inlet − BT` instead, which is this design with the base supplied by
> measurement rather than by a schedule. It is weaker on tracking and stronger
> on nearly everything else; see § Temp_Drive as the effort variable below, and
> settle the preheat measurement before deciding between them.

> **Status after roast 56 (2026-09-07): the tracking case for this is dead.**
> The premise below — that `e_ss = (dI/dt)/Ki` is a limiting error and that
> `svLookahead` exists to hide it — was written when the loop tracked to several
> degC. Roast 56 tracks its background at rms **0.94 degC over 30-90 s**, **0.41
> over 95-120 s** and **1.26 over the whole roast**, with the inner loop at rms
> **0.91 from 50 s to DROP** (state-history.md § Roast 56). The simulated
> "steady rms 0.11-0.14 degC" is no longer an improvement worth the two open
> config problems below. **What survives is the robustness argument** — that a
> feedforward base degrades more gracefully than an integrator carrying the
> whole operating point when the plant moves or the inner loop is disturbed —
> **and that has to be argued on its own terms, with a stated test, or step 9
> should be dropped.** The residual roast 56 does leave (−2.9 degC at 140-200 s,
> the integrator's fill rate against the drying ramp) is a *phase* deficit and
> is being attacked with lookahead first; see state-current.md § HANDOFF.

#### The structural fix: an inlet feedforward schedule with the PID as a trim

**The root defect has been on the table since roast 40 and has never been
addressed: the outer loop's output is an absolute setpoint, so its integrator has
to supply the entire operating point** — a job the inner loop gives to
`feedforward()`. That is why `I` climbs 8 → 63 across a roast at 0.09 duty/s, why
`e_ss = (dI/dt)/Ki` exists at all, why `svLookahead` is needed, and why the value
handed over at 1:30 matters in the first place. Every option above rearranges
that burden. This one removes it.

Give the firmware a **base inlet schedule** and make Artisan's PID output a
**bounded trim** on it:

```
INLET = ff(t since CHARGE) + trim,        trim in [-80, +80] degC
ff(t) = bg(t+theta) + (dbg/dt(t+theta) - loss(t+theta)) / a
```

— the plant inverted on the background, `a = 0.0049`, `theta = 13.5 s`, with the
loss term a cubic fitted over 45 s..DROP. **The schedule deliberately knows
nothing about the charge dip**, which is the honest case: the dip is the one part
that is not repeatable, so it is left entirely to the trim.

What that buys, from the table above:

- **`dI/dt` collapses from 0.09 to 0.01 duty/s** and `I@DROP` from 63 to 50 — the
  trim sits mid-range instead of ramping, so the type-1 error is **structurally**
  gone rather than cancelled. Steady rms **0.11-0.14 degC** against 0.26-0.38.
- **`svLookahead` becomes unnecessary** — every FF row runs `L = 0`. The whole
  lookahead-versus-dip tension (state-history.md § Roast 44 outer-loop analysis:
  `L > 4` winds the integrator through the dip) disappears with it.
- **the handover value stops mattering**: with the gate, `I@1:30` is 49.9 at every
  charge state and `dt150` is +1.6 s at every charge state — spreads of **0.0 and
  0.1**, against 1.2 and 4.2 for `lookahead_kigate`. The dip becomes a bounded
  trim excursion instead of an integrator re-seeding event.
- and the gate now **helps** rather than trading: worst error over 1:30-3:20 goes
  +2.25 → **-0.87**, because there is no longer an operating point for the frozen
  integrator to be behind on.
- **±20% of error in the assumed plant gain** costs `dt150` +6.4 s or -1.1 s and
  leaves steady rms at 0.15-0.16 — still better than anything else in the table.
  A 30% error in the loss term costs about the same.

**It needs one small firmware command and no new Artisan machinery.**
`specialeventplayback` is **per event type** (canvas.py:1848) and
`pidPositiveTarget` selects **any of sliders 1-4** (pid_control.py:1252), so
background event playback can drive the base on one slider while the PID drives
the trim on another — the collision that forced playback off for the cascade
(§ Background event playback must be off) was specifically that both wanted
slider 3. So:

- **Artisan**: re-enable playback for the inlet-base event type only; point
  `pidPositiveTarget` at the trim slider; map that slider's target subrange onto
  the trim range. The base curve goes into the background `.alog` as replayable
  events — **but `artisan/make_inlet_background.py` does not currently emit a
  file of that shape**; see § The base-curve authoring gap below.
- **Firmware**: one new command, `INLET TRIM <degC>`, bounded, defaulting to 0,
  cleared on disengage and on `INLET 0`. The inner loop's setpoint becomes
  base + trim. Everything else, including the `INLET 0` DROP chain and the
  cooldown guard, is untouched.

**What it needs characterised before it is worth roasting**, and this is the
honest weakness of the simulation: `ff` here is built from roast 46's own fitted
plant and disturbance, so the exact-FF rows are partly circular. The ±20% gain
and -30% loss rows are the answer to that and they hold up, but the real
confirmation is Test A/B/C — **which have just recovered their priority**, since
the FF schedule is exactly `1/a` and the loss curve, and the loss curve is where
the fan enters. A schedule that is wrong in the *loss* term is wrong in the same
direction for the whole roast, which the trim absorbs; a schedule wrong in `a` is
wrong in proportion to the ramp rate, which it also absorbs, at 6 s of timing.

**Risks to close before this is run.** The base schedule runs open-loop, so a
stalled Artisan leaves the firmware holding base + last trim rather than a single
frozen setpoint — the same exposure as today but with two stale numbers instead
of one, and it argues for a trim staleness timeout in the firmware. The trim
range must be bounded on the device, not only in the Artisan mapping. And an
authoring error in the base curve is a whole-roast error rather than a transient,
so the base must be regenerated from the background whenever the background
changes.

#### Temp_Drive as the effort variable — a cheaper relative of step 9 (operator, 2026-09-08)

**The idea.** Let the outer loop command `Temp_Drive = Inlet − BT` instead of an
absolute inlet setpoint. The firmware owns `btTemp`, so the inner loop's target
becomes `btTemp + drive`. Structurally this is step 9 **with the base supplied by
measurement instead of by a schedule**:

```
step 9:      INLET = bg(t+theta) + (dbg/dt(t+theta) - loss(t+theta))/a  +  trim
Temp_Drive:  INLET = BT(t)       +  drive                    <- the PID's output
```

Step 9's feedforward carries two terms — the **operating point** `bg` and the
**rate** `(dbg/dt − loss)/a`. Temp_Drive cancels the first and leaves the second
to the PID. That is the whole comparison, and it decides everything below.

##### What the logs already say — and it is less than the algebra promises

The drift in the loop's own output is what sets the type-1 ramp error
(`e_ss = (dU/dt)/Ki`). Measured on the cascade roasts, smoothed 11 s:

| | inlet SV, drift | Temp_Drive, drift | ratio |
|---|---|---|---|
| **40 s → DROP** 53 / 54 / 55 / 56 | +0.267 / +0.243 / +0.282 / +0.290 | −0.051 / −0.103 / −0.074 / −0.087 | 5.3 / 2.4 / 3.8 / 3.3× |
| **120 s → DROP** 53 / 54 / 55 / 56 | +0.181 / +0.141 / +0.138 / +0.201 | −0.080 / −0.133 / −0.140 / −0.094 | **2.3 / 1.1 / 1.0 / 2.1×** |

degC/s. **Over the whole roast Temp_Drive drifts 2.4-5.3× less; over the drying
ramp — the window the −2.9 degC residual actually lives in — it is 1.0-2.3×, and
on roasts 54 and 55 it is no better at all.**

The reason is visible in the sign. BT rising pushes the inlet **up**; the
background's RoR declining (46 → 9 degC/min) pushes the required drive **down**.
Over the whole roast the BT rise dominates. Over the drying ramp the two are the
same size, so cancelling only the first leaves a drift of comparable magnitude
pointing the other way. **Step 9 cancels both terms and Temp_Drive cancels one —
and in the window that matters, it is the smaller one.**

**So: do not adopt this for tracking.** On that metric it is a weaker step 9, and
step 9's own tracking case is already dead (roast 56, rms 0.94 over 30-90 s).

##### Where it is genuinely better than step 9, and it is not a small list

All of these are robustness arguments, which is the only ground step 9 still has:

- **No base curve to author.** § The base-curve authoring gap is step 9's open
  blocker — `make_inlet_background.py` does not emit a file of the right shape.
  Temp_Drive needs no file.
- **No open-loop whole-roast failure mode.** Step 9 warns that "an authoring
  error in the base curve is a whole-roast error rather than a transient". The
  Temp_Drive base is BT. It cannot be authored wrong.
- **No plant card, so no circularity.** Step 9's `ff` is built from `1/a` and
  roast 46's loss cubic, which the section itself calls "partly circular" and
  gates on the characterisation runs. `INLET = BT + drive` needs neither `a` nor
  `loss`, because the operating-point term is exact by construction. **It is not
  blocked on Tests A/B/C.**
- **Background-independent.** Step 9's base must be regenerated whenever the
  background changes. Temp_Drive composes with any background — including a
  regenerated one, which is the whole point of the peak pin.
- **The floor stops being scale-dependent, and this may be the best argument.**
  `positiveTargetMin = 100` means `TD ≥ +41` at the turning point (BT 59) and
  `TD ≥ −100` at DROP (BT 200): the *same config number* is "still heating hard"
  early and "cool as hard as you can" late. That is why the floor has been
  retuned four times (120 → 170 → 140 → 100) and why roast 54 sat **40 s
  saturated at its own floor** — an absolute floor is the wrong shape of
  constraint. A drive floor means one thing all roast.

##### Three risks, one of them a genuine safety regression

1. **A stale command runs away.** A frozen absolute SV is self-limiting — BT
   converges to it. A frozen *drive* keeps ramping: at the observed TD ≈ 70 that
   is ~20 degC/min, indefinitely. **This is worse than today and must be
   designed for**, not noticed later. v0.19.0's `INLET_TRIM_STALE_MS` pattern is
   the right shape; here it is load-bearing rather than hygiene, and the safe
   fallback is to latch the last *absolute* setpoint, not to zero the drive.
2. **BT enters its own setpoint with gain 1.** Probe noise, drop spikes and RTD
   faults go straight into the inner loop. Use the filtered `btTemp`, rate-limit
   the base, and hold the last good value across an RTD fault.
3. **It must not be engaged through the dip.** `INLET = BT + drive` would chase
   BT down from 130 to 59 and cut the inlet exactly when the bed needs it. It has
   to engage with the PID at CHARGE+15 s and hold an absolute setpoint before
   that — which is what § The charge gate already does, so this costs nothing.

##### What it would take

Small, and mostly config. The slider already sends
`send({"command":"INLET","value":{}})`; a drive mode is one firmware command
alongside the existing `inletBase`/`inletTrim` pair, plus
`positiveTargetMin`/`Max` remapped onto a drive range. Note Artisan asserts
`slider_min < positiveTargetMin` (pid_control.py:1302), so a drive range
starting at 0 needs slider 3's minimum moved below it.

##### The development plan — five stages, and only one of them costs beans

Gated on the preheat characterisation (state-current.md § HANDOFF § 0 and § 1),
because stage A's design constants come out of it.

**A. Bench, no beans — the Temp_Drive ladder. DONE 2026-09-08, and it passes.**
`artisan/airRoaster_empty_BT-target-steps.alog`, six settled rungs at BT 130 /
140 / 145 / 152 / 130 / 145. **`d(TD)/d(BT) = +0.025`** — DC gain near 40, so the
drive→BT loop is very nearly an integrator, and the kill criterion below is
cleared by **20×**. Even the most adverse pairing in the data gives 0.17.
**Go to stage B.** Two cautions carried in state-history.md § Phase 0: the slope
is *bounded*, not measured (Temp_Drive moved 0.6 degC across the ladder while
same-BT repeats disagreed by −1.51 and +1.02), and **heater duty repeats 6× better
than `Inlet − BT`** because the BT probe carries a slow local-metal component.
The original scheduling note follows.

This was § 0 of roast 57. It yields `d(TD)/d(BT)`, which is the **DC gain of the
drive→BT loop** and therefore decides whether this design is nearly an integrator
(type-2, no ramp error) or a high-gain type-0. It also gives the settling ceiling
at fan 60, which bounds the drive range.

*Kill criterion:* if `d(TD)/d(BT)` comes back **above ~0.5**, the drive→BT loop
has a DC gain under 2 and a time constant near today's — the structural benefit
is mostly gone, and the measured drift table above (1.0-2.3× over the drying
ramp) is then the whole story. **Stop here and reconsider.**

**B. Desk — settle the four design questions.** None need hardware.

1. **The staleness fallback.** A frozen drive keeps ramping; a frozen absolute SV
   does not. The fallback must **latch the last effective absolute SV**, not zero
   the drive and not hold the drive. `INLET_TRIM_STALE_MS`'s 15 s and its
   "logged once per stale run" pattern are the shape; the *action* is different
   and this is the one place the existing code must not simply be copied.
2. **The BT path into the setpoint.** BT enters its own setpoint with gain 1.
   Decide: which filtered `btTemp`, what slew limit on the base, and what happens
   across an RTD fault (hold last good, and for how long before the failsafe).
3. **The mode transition at CHARGE+15.** The gate holds an absolute SV through
   the dip and drive engages with the PID. That handover must be bumpless in
   *both* directions — the firmware seeds `drive = inletSV − btTemp` on entry,
   and Artisan's PID integrator must map to that same drive. This is the same
   integrator-handover problem the cascade already has at CHARGE+15, at a
   different scale; § Roast 44 outer-loop analysis and § Roast 53 are the prior
   art.
4. **The drive range and the slider assumption.** Map
   `positiveTargetMin`/`Max` onto a drive range — roasts 53-57 ran
   Temp_Drive **29-94 degC**, so something like 0-160 covers it with margin.
   **Every one of those figures carries ±1.5 degC of probe history** (§ Phase 0),
   which is an argument for the margin, not against the range. **Never tune on a
   Temp_Drive difference under ~2 degC.**
   Artisan asserts `slider_min < positiveTargetMin < positiveTargetMax <
   slider_max` (`pid_control.py:1302`), so slider 3's minimum has to move below
   the drive floor. **Do not leave the 0-320 slider range and a 0 floor: that
   violates the assertion Artisan states.**

**C. Firmware — `INLET DRIVE <degC>`, and a bench drill.** One command beside the
existing `inletBase`/`inletTrim` pair (`inletEffectiveSV()`, airRoaster.ino:2543
is the single place that assigns `inletSV`, so this is a small change in a place
already designed for it). Drill it exactly like § NEXT 14: bounds, `INLET DRIVE
0`, bare `INLET DRIVE` reporting, the staleness ramp, clearing on `INLET OFF` /
`INLET 0` / `TUNE` / failsafe, auth under `AUTH MODE FULL`, and a regression run
that never sends the command. **Add one drill § NEXT 14 has no analogue for: with
the drive engaged, spoof an RTD fault and confirm the setpoint holds rather than
following BT to zero.**

**D. Empty chamber, no beans — first light.** Run the whole cascade against a
background with no charge in the drum, exactly as roast 47's grid did. The plant
is wrong (no bed) so tracking numbers mean nothing, but **every failure mode
worth finding is structural**: the CHARGE+15 handover, the staleness fallback,
the drive range mapping, whether BT noise reaches the heat, and whether the loop
is stable at all with BT inside its own setpoint. **This stage is free and it is
where the design should break if it is going to.**

**E. One roast — and not on `C1043`.** By the time this runs it is a
single-variable change against a known-good baseline. Score it on the four checks
plus the 120 s→DROP tracking rms and, specifically, **the drift in the loop's own
output** — the quantity the whole design is about. Predicted: the same tracking
as roast 56 with 2-3× less effort drift over the drying ramp, and **no floor
saturation at any BT**, which is the claim that is most worth checking because it
is the one the measured drift table does not already answer.

**Where LA 12 sits.** Deferred (state-history.md § The LA 12 plan, deferred).
If stage E lands, a lookahead patch on a type-1 ramp error is treating a symptom
the loop no longer has — so **decide LA 12 after E, not before.** If A's kill
criterion fires, LA 12 comes straight back as the cheap fix it was.

##### The unmeasured number is the same one the preheat work needs

`d(TD)/d(BT)` — how much more drive it takes to hold a hotter BT — is the DC gain
of the drive→BT loop, and it decides whether this is nearly an integrator
(type-2, no ramp error) or a high-gain type-0. **Measured 2026-09-08: +0.025**,
an order of magnitude below the 0.10-0.38 bracket this section carried. The
paragraphs below were written before that and are kept for the reasoning; the
bracket itself is superseded. **It is also exactly the number § Normalize the
charge with the PREHEAT needs**, and for a third reason too: the plant card's
`loss(t)` is a function of *time* only because BT(t) is monotone on a roast, so a
BT-dependent loss is aliased into it and `plant_roast46.json` cannot separate the
two. A settled Temp_Drive at two preheats is a **steady-state** measurement with
no time axis to alias against.

**One preheat step measures all three.** That is the strongest reason to run the
preheat characterisation before either this or step 9 is decided.

#### The base-curve authoring gap — `make_inlet_background.py` does not emit this file (2026-09-06)

The structural fix above needs **one** background carrying three things at once:
profile_003/004's **BT curve** (the outer PID's target — `pidSource = 1`), the
**base schedule as replayable special events** on the base slider, and the real
**`timeindex` marks**. Neither of the script's two output modes is that file,
and it is not a matter of flags:

- **default mode** writes the continuous curve into `extradevices = [58, 22]`
  (channel B3) for *Follow-Background* mode. That is a different mechanism —
  no special events at all, so nothing for `playbackevent` to replay.
- **`--events N` mode** (`build_events_alog`) does emit the events, and on the
  right type — but it **hard-codes `temp2 = [-1.0] * len(timex)`**, blanks
  `extradevices`, puts the mirrored playback polyline in the *ET* slot
  (`temp1`), and sets `timeindex = [0, 0, 0, 0, 0, 0, len-1, 0]`: CHARGE at
  sample 0, DROP at the last sample, **no DRY END and no FCs**. It is an
  inlet-only background by construction, which is exactly right for the
  inner-loop event-playback path it was written for and gives the outer PID
  nothing to follow.

Measured on the files in the repo: `bkgd_inlet_150+25-255@420.alog` has
`temp2 = -1.0` for all 421 samples and 8 type-2 events; `profile_003.alog` has
BT 67.4-201.6 degC over 427 samples and **zero** special events.

**So the step-9 background is a merge, not a generation.** Take profile_003 (or
004) and add the four `specialevents` / `specialeventstype` /
`specialeventsvalue` / `specialeventsStrings` arrays to it. That is additive to a
recorded profile and disturbs nothing: profile_003 already carries
`etypes[2] = 'T_inlet'`, its own `extradevices = [112, 25]`, and
`timeindex = [0, 192, 399, 0, 0, 0, 425, 0]`. The two pieces the script already
has and the merge should reuse are `events_ext_to_internal` (the
`specialeventsvalue` encoding, whole-degree quantised, and it already handles
negatives) and `place_event_times`.

**Two assumptions corrected against v4.2.0 while checking this.**

1. **Playback does not match event-type *names*.** The script's inline comment
   says *"playback only fires when the background's event-type name matches the
   foreground's (canvas.py:playbackevent)"*. It does not: `playbackevent`
   reads `event_type = self.backgroundEtypes[i]` (canvas.py:6436), admits it on
   `0 <= event_type < 4` (:6438), and gates it on `end_reached[event_type]`
   (:6443), which is seeded as `[not flag for flag in self.specialeventplayback]`
   (:6420) — a 4-element per-type bool list (canvas.py:1848). **No name is
   compared anywhere in the function.** So the merged background does not need its
   `etypes` list aligned with the `.aset`'s — only the numeric type index has to
   agree. Names still drive labels and annotations. This *simplifies* the merge;
   it also means a mismatched name will not save you from a wrong index.
2. **Events after the background's DROP are never replayed** —
   `(self.timeindexB[6]==0 or bge <= self.timeindexB[6])`, canvas.py:6444.
   With profile_003 that caps the base schedule at index **425 (~416 s)**, the
   same window constraint § Auto-DROP detection found for `svLookahead`. It bites
   harder here: `ff(t) = bg(t+theta)` reads the background **ahead** by
   `theta = 13.5 s`, so the last ~14 s of the schedule has no background left to
   read and needs an explicit tail rule rather than the script's flat-outside-
   range `_interp`.

**One thing to choose rather than inherit: the event count.** Playback
interpolates linearly between successive events, so `N` events is an
`(N-1)`-segment polyline. The script's default of 8, tail-biased, was tuned for
the smooth inner-loop ramp; `ff(t) = bg(t+theta) + (dbg/dt - loss)/a` carries a
curvature term the ramp did not have. Pick `N` from the residual of the polyline
against `ff` — a free offline check once `ff` exists — not from the default.
The whole-degree quantisation is not the constraint: 1 degC of base against
`a = 0.0049` is ~0.005 degC/s of BT rate.

**~~Do not build this yet~~ — the gap is closed (2026-09-06, operator request).**
`tools/merge_inlet_base.py` is the merge; `make_inlet_background.py` is untouched,
as its 2026-09-02 scope boundary requires. It is standard-library only, like the
other tools in `tools/`, and it reads the plant from a **card** —
`tools/analysis/plant_roast46.json`, written by
`tools/analysis/roast46_refit.py --emit-plant`. That is the seam the steps-3-5
gate needs: when the characterisation runs land, re-run `--emit-plant` and re-run
the merge, and nothing else in the chain changes.

```bash
python3 tools/merge_inlet_base.py --into artisan/profile_003.alog --dry-run
```

On `profile_003` and the roast-46 card (`a` 0.004897, `theta` 13.5 s, loss cubic
over 45 s..DROP) it emits **7 type-2 events**, base **199 → 256 degC**, max replay
error **0.87 degC of base = 0.0042 degC/s of BT rate**. The output is the input
profile plus the four `specialevents*` arrays: BT, `timex`, `timeindex`,
`extradevices` and everything else pass through byte-identical, and only the
source roast's identity (`roastUUID`, `plus_*`, `hash`, `signature`, `computed`)
is blanked so a doctored background cannot be mistaken for, or re-synced as, a
roast. **The file itself is generated on demand, not committed** — there is no
`ff(t)` worth roasting until steps 3-5 run, and a stale one on disk is a thing to
load by accident.

**Five things the implementation found that this section did not have.**

1. **The name check is not absent, it is broken.** The claim above — "no name is
   compared anywhere in the function" — is wrong as stated. `canvas.py:6530` does
   compare, as `str(self.etypesf(t) == str(self.Betypesf(t)))`: `str(bool)`, always
   a non-empty truthy string. The *conclusion* holds for v4.2.0 and the same
   expression guards the ramp branch at :6546 — but it holds by accident, and an
   Artisan that fixes the parenthesis would start enforcing it. So the tool aligns
   `etypes[type]` deliberately rather than relying on the bug.
2. **The `bg(t+theta)` lead reads into the cooling phase, not just off the end.**
   `profile_003` happens to end one sample after DROP, which hides this; any
   ordinary recorded roast continues down through cooling, and inverting that fall
   rails the base to the floor over *exactly* the last `theta` seconds of the
   roast. The window therefore ends at `timeindex[6]`, and the background is
   **blended** into its own terminal RoR fit over `--tail-window` rather than
   butt-joined to it: `dbg/dt` is divided by `a`, so a 0.005 degC/s kink at the
   seam is a 1 degC step in the base. Blending took the schedule from 10 events to
   7 and removed a 1.5 degC bump 14 s before DROP.
3. **The tolerance has a floor at ~0.5 degC of base and it is quantisation.** The
   knot chooser measures the residual of the *quantised, index-snapped* polyline,
   so at a knot the error is the whole-degree rounding. `--tol 0.3` therefore
   stops early and says so. § above is right that this does not matter
   (0.5 degC → 0.0024 degC/s of BT rate); what is worth having is that the number
   the tool reports is a promise about the delivered schedule.
4. **`--dip` is a real choice and the default is not what was simulated.** Raw
   `ff` at CHARGE on `profile_003` is **-432 degC** — the background falls at
   3.5 degC/s through the dip and `/a` multiplies it by 204. `dip_strategies.py`
   clipped that to `[120, 300]`, so the FF-trim rows in the table above describe a
   base that **dives to the floor and climbs back out**. The operator's choice
   (2026-09-06) is instead to back-extrapolate the ramp to CHARGE, which on
   `profile_003` is a nearly flat **198.7 → 200.9 degC**, leaving the whole dip
   excursion to the trim. `--dip follow` reproduces the simulated variant. **The
   two differ by ~80 degC of base over the first 40 s and that difference has not
   been through the closed loop** — closing it is the first thing to do when step 9
   comes up the runbook.
5. **The base peaks at 256 degC, which eats half the positive trim range.** With
   `INLET_SV_MAX_C = 300` the effective setpoint clamps, so the top of the roast
   has only +44 of the +80 trim available. Not a problem at roast-46 duty (the trim
   sits mid-range by construction), but it is the reason the tool reports the base
   range, and it is a thing to watch if a hotter profile is authored.

The tool also refuses, rather than producing a plausible-looking file: a
background whose BT is blank between CHARGE and DROP (which is exactly what
`make_inlet_background.py --events` writes, and what makes it the wrong starting
point); a profile in Fahrenheit (event values are **not** unit-converted on
background load, `main.py:14474-14477`); a missing DROP mark (`timeindex[6] == 0`
disables the replay window entirely); a CHARGE index that is not a sample (such a
background replays from **START**, driving INLET through the preheat); and
pre-existing events of the target type without `--replace`. It round-trips the
`external → internal → external` encoding on the file it just wrote before
reporting success.

**Still not built, and still gated on steps 3-5**: the `.aset` half — the trim
slider (`INLET TRIM` on slider 2 with `slideroffsets` -80 over a 0-160 range,
`pidPositiveTarget = 2`) and `specialeventplayback`/`...ramp` enabled for event
type 2 alone. And the closed-loop check of the emitted file, which is what would
settle item 4 above.

#### Ruled out, so they are not proposed again

| approach | verdict |
|---|---|
| dose the integrator at handover (short high-`Ki` burst) | overshoots 10-30 s on `dt150`; the loop is short of anticipation, not integral |
| temporary large `svLookahead` over 1:30-3:00 | same failure, same direction |
| **relative setpoint** — `INLET = BT + trim`, the PID commanding a lead over BT | **worse, for a principled reason**: it converts the plant from a self-regulating first-order lag into an *integrator* with 13.5 s of delay, so the standing ramp error moves from integrator-rate-limited to gain-limited and the delay caps the gain. Best steady rms 1.17 against 0.24; `worst` +12 to +18. Feedforward on a *known* trajectory (above) gets the same structural benefit with none of it |
| widen/narrow `positiveTargetMin/Max` to shrink the integrator's swing | pure reparameterisation — the map rescales `Kp` and `Ki` together in physical units, so `e_ss = (dI/dt)/Ki` is invariant. No free lunch — **but read the next row before citing this to refuse a floor change** |
| lower `positiveTargetMin` **to add authority** *(not the same thing)* | **not** a reparameterisation, and this entry was misread as forbidding it for four roasts. When the loop is *saturated* the gain argument does not apply: roast 54 sat 36 s at `SV = 140` with the heater still at **46%**, unable to act on a bed above the background. Lowering the floor and scaling `Kp`/`Ki` by `160/(max-min)` holds `dSV/derror` **exactly** and changes behaviour only where the old config was clamped. The cost is that `Iterm` must carry a larger operating point (20.2 rather than 0.3 to hold the preheat's 140.4), which the preheat builds — so **a short preheat now starts the roast cold** |
| `PIDoff` at CHARGE / `PIDon` at 1:30 (freeze at the preheat operating point) | `pidOn` does not reset `Iterm` (pid_control.py:1521-1527), so it is mechanically sound and gives `I@1:30` spread 0.8 — but the SV is frozen for 90 s, and `dt150` swings **14.6 s** across the charge sweep. Open-loop where the disturbance is |
| `pidIRoC` (integral reset on large setpoint change) | inert here: the threshold is compared against the *per-sample* target change, which never exceeds ~5.5 degC even through the dip |
| `pidIlimitFactor` < 1 to bound windup instead of freezing it | fatal on its own — the ramp needs `I` ≈ 63 and the cap is global. Becomes usable only under the FF trim, where `I` stays near 50 |
| lower `Kp` through the dip | already ruled out in state-history.md § The dip is a different control problem (handover spread 91.5); `beta < 1` via `pidWeights()` is the same move on the target path and no better |
| the fan as a second actuator in the dip | not needed, and the operator now holds it constant deliberately; the ~0.99 %heat/fan-unit sensitivity is a loss-term effect, which the FF schedule and the trim both absorb |

#### The one adaptive idea that is still open, and costs nothing to keep

`(CHARGE_BT - BT at CHARGE+13 s) / mass` is a **free, control-independent proxy
for the charge state** (state-history.md § Charge temperature) and it is
available at 13 s — well before any handover. Artisan can act on it without a
new process step: an alarm *from CHARGE, offset 13 s, source BT, below/above a
threshold* can fire `loadBackground(<path>)` (main.py:10879),
`moveBackground(<dir>,<step>)` (main.py:10923), `alarmset(<n>)` (main.py:10898)
or `palette(<n>)` (main.py:10863) — so a whole tuning set or background can be
selected on the measured charge state. **Do not build this yet.** It is the
fallback if the FF trim leaves a charge-dependent residual worth chasing; on the
present numbers it would be chasing 1.6 s.

### Open firmware ideas

*Neither is scheduled. The v0.19.0 items that came out of the same discussion
are built and are recorded in state-history.md § Firmware now in scope.*

#### The one big idea, gated on the characterisation runs

**Publish a *predicted* BT as an extra channel and point the PID at it.** The
loop is deadtime-limited — margin ~30 deg at Ki 0.07 solely because of theta —
and a Smith predictor is the standard answer. It does **not** require moving the
outer loop into firmware: the firmware can run the identified model forward from
the measured inlet and publish `BTP`, and Artisan's `pidSource` can select that
extra channel instead of BT (the PID input list offers exactly the extra device
channels, pid_dialogs.py:1251-1258). The loop then sees a fraction of the
deadtime and Ki could rise several-fold at the same margin.

Two conditions before attempting it:

1. **Trustworthy theta, tau and gain.** The current values come from a flat
   ridge (state-history.md § Scheduling) and are not good enough to predict
   with. Run Tests A and B first.
2. **A bound on the correction.** Clamp `|BTP - BT|` to something like 10 degC so
   a diverging model degrades to plain BT rather than running the roaster open
   loop on a wrong prediction.

**Not worth doing: moving the outer loop into firmware.** The only reason would
be to enable the predictor, and the channel route achieves that without it. The
1 Hz WebSocket link is not a limitation — 1 s against 17 s of deadtime — and the
background curve authoring belongs in Artisan's Designer.

#### Normalize the charge with the PREHEAT, not the background (operator, 2026-09-08)

> **WITHDRAWN by roast 57 (2026-09-08). Do not build on this section.** The lever
> rests on `d(TP)/d(preheat) ≈ 0.415`, and the measurement is **0.100**: roast 57
> stepped the preheat 130.2 → 145.24, one variable, and the turning point moved
> **+1.50 degC** where the model said +6.24. The lever the measurement implies is
> `0.60 / 0.100` = **6.0 degC of preheat per degC of greens**, which the machine
> does not have. Every table below is model output that assumes the trade it was
> being asked about; the "two thirds store, one third flow" decomposition is the
> specific claim that failed. `tools/analysis/preheat_lever.py` is kept — it now
> reads 6.0 and says so. **The preheat is not inert, it is a slow lever aimed at
> the wrong window**: it moves 30-120 s by *more* than the model predicts (+9.10
> at 70 s against +4.58) and the turning point by almost nothing. Full record in
> state-history.md § Roast 57; the mechanism is in state-history.md § Phase 0 —
> the BT probe sits on the non-flow side and carries a slow local-metal
> component, so "preheat BT 145" is not 15 degC of energy the beans can reach.


**The idea.** Instead of authoring a different roast for every greens
temperature, preheat *hotter* for a cold charge and *cooler* for a warm one, so
every batch arrives at the same post-dip state and the loop sees the same job.
Modelled in `tools/analysis/preheat_lever.py`; run it rather than trusting the
summary here.

**It works in the model, and the lever is small enough to be practical.**

```
preheat BT = 124.4 − 1.17 × greens_temp        (400 g, operator's thermometer scale)
```

| spread over greens −24…+25 degC, 400 g | TP | BT@60 | BT@90 | rms 30-90 s |
|---|---|---|---|---|
| preheat fixed at 130.2 (today) | 29.2 | 27.5 | 23.8 | 1.11-16.71 |
| compensated | **5.3** | **0.9** | **7.6** | **0.18-2.71** |

Roast 56 tracked its own background at rms 0.94 degC over 30-90 s, so the
compensated residual is at the noise floor of what the machine achieves.

**The prize is not the tracking number, it is what the loop is asked for.**
Regenerating the background at each charge temperature with the RoR peak pinned
at 53 s, the *demanded* peak RoR spans **33.5-55.4 degC/min** today and
**42.8-49.0** compensated — spread 21.9 falling to 6.2, against a machine
ceiling of 72. Nearly a third of the demonstrated rate range is currently spent
on charge temperature alone.

**Why it works is not the phrase "retained energy".** `phi = 0.712` at 400 g
implies `C_chamber = 276` against `m·c_b = 680` — **the chamber is worth about
162 g of coffee**, 41% of the charge. It is not a flywheel, so raising the
preheat by 1 degC hands the bed only `(1 − phi) = 0.29`. The lever reaches
0.40-0.47 because a *settled* preheat is two things: a hotter store and a hotter
inlet. The deficit is spent once; the inlet keeps delivering. **Two thirds
store, one third flow.**

Consequences worth keeping:

- **Match the loop's window, not the turning point.** TP-matching is the obvious
  target and it is wrong — it lands the TP exactly and then over-drives the
  recovery (BT@90 spread 14.4 against 7.6). Fit the preheat over 30-90 s.
- **The lever is mass-dependent** — 0.85 at 250 g to 1.33 at 500 g, because
  `phi` saturates. **Never scale it**, same rule as the background itself.
- **The inlet floor binds at the WARM end, and 100 clears it.** Greens +25 needs
  preheat 95.2 / inlet 102.0; the old 140 floor would have blocked everything
  above about greens −5. `floor100.aset` is what makes this possible at all.
- **The region compensation changes is the region the loop is gated out of.**
  PID is OFF from CHARGE and its first correction lands ~28.5 s, just past the
  TP (§ The charge gate). Compensation reshapes 0..TP and normalizes TP onward.
- **Keep regenerating the dip.** A compensated roast starts at its own preheat,
  so BT at CHARGE is up to ±27 degC from a fixed file — the 0-30 s check would
  blow up. `make_background.py` already redraws the dip for free; what becomes
  invariant is the *design* half, which is the half that matters.

##### THE HALF THAT IS NOT MEASURED — this gates the whole idea

`charge_dip`'s calibration roasts 50/51/53/54 charged at BT **129.7, 131.0,
130.5, 129.8**. A spread of **1.3 degC**. Nobody has ever preheated this machine
anywhere but 130.

- `d(TP)/d(greens)` = **0.60** is a measurement — roast 50 at room temperature
  against 51/53/54 out of the freezer.
- `d(TP)/d(preheat)` = **0.40** is **structure, not data.** It follows from
  `dT_mix = phi·(BT_c − T_bean)` putting the two temperatures in one bracket.

**So the model cannot falsify the idea; it assumes the trade it is being asked
about.** Do not ship the rule on the model alone.

**The experiment is one roast** (`preheat_lever.py --experiment`). Hold the mass
and the greens temperature, step the **preheat** by 10-15 degC, regenerate the
background at the new preheat (`--charge-bt`, `--inlet-precharge`) so the loop is
not asked to fight the step, and read the TP off the log. The 130.2 baseline is
already four roasts deep, so one point gives the gain.

| preheat | inlet | predicted TP | predicted BT@60 |
|---|---|---|---|
| 130.2 (baseline) | 140.4 | 59.25 | 73.21 |
| 140.2 | 151.4 | 63.40 (+4.15) | 77.86 (+4.65) |
| 145.2 | 156.9 | 65.48 (+6.23) | 80.19 (+6.98) |

A 10 degC step clears the dip model's 1.31 degC calibration rms and the −12
group's 2.7 degC scatter. **A measured gain below ~0.3 or above ~0.55 moves the
lever enough to matter; inside that band, ship the rule.** The same roast also
tests the two things the model has nothing to say about: whether **fan 60 still
settles** at the higher preheat, and what **Temp_Drive** does there (predicted
11.8 at BT 145 on a linear-loss slope, 16.0 on roast 47's empty-chamber slope —
that spread is itself the measurement).

**Three ways it could fail on the machine, none of them in the model:**

1. **`phi` may not be constant in preheat.** The BT probe is not the chamber
   wall. If a hotter preheat stores energy the probe reads differently, `phi`
   moves and the lever with it.
2. **Losses look super-linear.** Roast 47's grid implies ~0.38 degC of
   Temp_Drive per degC of BT against 0.10 for a loss linear in (BT − ambient).
   A 152 degC preheat may not settle at fan 60, and the walls may give more back
   during the pour.
3. **Scorching.** Tipping into 152 degC is not tipping into 130 degC. Operator
   judgement, and it caps the cold end of the range independently of the model.

**Ordering.** This is *not* roast 57's or 58's — 57 is `LA 12` and 58 is the FC
mark, both already single-variable. It slots after them, and the preheat step is
itself a clean single variable.

#### Measure the charge temperature instead of inferring it (operator, 2026-09-06)

**Charge with the fan off, read the incoming bean temperature off the BT probe's
cooling curve, then start the fan to loft the bed and begin profiling.** The
system is already preheated, so the beans are not scorched while they are being
measured, and the probe starts from a known temperature — the preheat BT, ~129
degC — so the *shape* of the fall carries the bean temperature without waiting
for equilibrium. Once enough of the curve has been observed, the fan starts and
the roast begins.

**Why this is worth more than it looks.** `greens_temp` is `0.0` on every roast on
record, and the charge state has had to be inferred (state-history.md § Charge
temperature) — from the fall over 0-13 s per 100 g, which is only a *proxy*, and
one that has to assume the plant delay to be interpretable. Charge state is the
single largest source of run-to-run variation the strategy search found: it is
what the `Ki` gate was invented for, what makes the handover integrator matter,
and what § Step 9 has to be shown robust against. Measuring it directly turns a
sensitivity study into a known input.

**It also composes with something already required.** The fan has to be at ~64 to
loft a 400 g charge and cannot start at the ramp base anyway (§ Files for the
characterisation runs), so the charge already has a distinct fan phase. This
would make that phase carry information instead of only lofting the bed.

**What has to be settled before it is worth building.**

- **Is the probe reading beans or stagnant air?** With the fan off the bed is not
  circulating, so the heat path to the probe is contact and natural convection.
  If the probe is not buried in the bed the curve reads chamber air and the
  measurement is of the wrong thing. This is checkable on the bench in one
  charge with no roast attached: fan off, watch the BT fall, then loft and see
  whether the settled temperature is consistent with the extrapolation.
- **How long does it take, and what does the delay cost?** Every second with the
  fan off is a second the profile has not started and the chamber is cooling. The
  cascade's whole clock is CHARGE, so a variable-length measure phase moves the
  reference; either the phase is fixed-length or CHARGE is marked at loft rather
  than at the dump.
- **The heater must be off throughout**, which the interlock already enforces
  below fan 48 — so this is safe by construction rather than by new code, and
  that is worth keeping true.
- **The free proxy already exists.** `(CHARGE_BT - BT at CHARGE+13 s) / mass`
  costs no process change at all (§ The one adaptive idea). The new routine is
  better but not free; the honest comparison is *measured `greens_temp` versus
  the proxy on the same charges*, which the runs in the table can supply for
  nothing if `greens_temp` is filled in by hand each time.

**Not scheduled.** It is a firmware routine plus a change to how a roast starts,
and it sits behind step 9. But it is the first idea on this list that would
remove a variable rather than compensate for one.

#### Still wanted, independent of the control problem

**Instrument the dump lever** (already noted in § Auto-DROP detection): expose it
as an extra channel and alarm on it, turning DROP from an RoR-collapse inference
into a measured event. The RoR margin is currently ample but roast-dependent
(-10.4 to +5.4 across the armed windows seen so far), and DROP drives the whole
heat-off chain.

### Runbook — the agreed order of work (2026-09-02, re-pointed 2026-09-05)

One variable per roast. Order after roast 46, the refit, the charge-temperature
finding and the strategy search: **step 6, then steps 3-5 (the characterisation
runs), then step 9.** Steps 2 and 7-8 are independent. **Steps 1b and 1c are
demoted** — state-history.md § Dip strategies finds that over the *reachable*
(warm-side only) charge range the `Ki` gate makes every metric worse than step 6
alone, and that both of them are rearranging a burden that step 9 removes. **The
characterisation runs have recovered their priority**, because step 9's
feedforward schedule is built from `1/a` and the loss curve, and the loss curve
is where the fan enters.

**The schedule that runs the rest of this list in the fewest sessions
(2026-09-06).** Five recordings, of which two are real coffee, two are
sacrificial and one uses no beans at all.

| # | what | runs | file |
|---|---|---|---|
| bench | flash v0.19.0, confirm the `SV`/`HT` curves, `INLET TRIM` drill (§ NEXT 14) | — | any cascade `.aset` |
| **1** | ~~**step 6** — the lookahead switch, *and step 7 for free*~~ **DONE, roast 49** — tracking error +0.40 degC / 1.84 s, and step 7 came with it: fan held at **64** for the whole recording | 1 real batch | `airRoaster_cascadePID_lookahead.aset` + `profile_003` |
| **2** | ~~**step 3** — Test A empty~~ **DONE, roast 47** — it measured the FF coefficients step 8 needs | free | `airRoaster_cascadePID_char.aset` + `charstep_empty_fan` |
| bench | ~~**step 8** — `feedforward()`~~ **DONE, v0.20.0** — measured coefficients, enabled; flash before the loaded runs | — | firmware |
| **3** | ~~**steps 4-5** — one 400 g loaded run~~ **DONE, roast 48** — the empty FF map transfers; the plant refit is still owed | 1 sacrificial | `airRoaster_cascadePID_char.aset` + `charsingle_400g` |
| bench | ~~untick **Drop Spikes**, set **Sampling** to 0.5 s~~ **DONE in the files** — load the `.aset` before the next run, the live session is still on the old values | — | `gen_pid_alarm_asets.py` |
| desk | ~~refit roast 48 for `a`/`theta`~~ **DONE** — `kf = 0`, but `a`/`theta` are not stationary, so `plant_roast46.json` stays the source. Left: `merge_inlet_base.py`, the `.aset` half, settle `--dip` | — | — |
| **5** | **step 9** — the FF schedule with the PID as a trim | 1 real batch | new |

**Roast 49 added an item that is not in this table yet** — a deliberate
ambient-vs-freezer charge pair, of which roast 49 is already the warm arm.
It is a proposal awaiting the operator's decision, not scheduled work; the
case for it and where it would sit is § The charge-temperature experiment.

**Two orderings in that table are load-bearing, and roast 47 sharpened the
second.** Step 6 comes **before** step 8: its whole value is a one-variable
comparison against roast 46, and step 8 changes the inner loop underneath it.
Step 8 comes **before the loaded doublets** — the fan is their subject and
`feedforward()` is the fan compensation that is currently dead — but **after**
Test A, which is what measures the coefficients step 8 installs. Test A being
empty and PID-off is exactly why it can sit on the wrong side of a firmware
change without costing anything. **Flashing
v0.19.0 first confounds nothing**: both of its items are inert on the present
cascade path (`INLET TRIM` is never sent, the `SV`/`HT` nodes are additive), and
it is what makes roast 1 self-contained for analysis.

**Steps 1b and 1c are not in the table and should not be run**, for the reason
in the paragraph above; the sections below keep their detail for the record.

**Do this on every roast from now on, it costs nothing: fill in `greens_temp`**
(Artisan Roast Properties). It is `0.0` on every roast on record — roast 48
included, so this is still not being done — which is why the charge state of the
existing set had to be inferred rather than read (state-history.md § Charge
temperature).

**Two Artisan settings changes are now queued ahead of the desk work, both from
roast 48** (state-history.md § Roast 48, § Two Artisan settings). **Untick "Drop
Spikes"** (Config › Curves › Filters): with it on — and it is on in every cascade
`.aset` — Artisan destructively rewrites the two samples before every step in a
constant-valued channel, which `SV` and `HT` are by construction. And **set
Sampling to 0.5 s** (Config › Sampling; `min_delay` is 100 ms, and the outer
loop's `Kp`/`Ki`/`svLookahead` are all rate-independent, so nothing is retuned).
Both live in the `.aset`, as `dropSpikes` and `Delay`, and **both are now applied
to all five files** — `dropSpikes=false`, `Delay=500`, propagated by
`tools/gen_pid_alarm_asets.py`. `curvefilter` stays at 3 on purpose: it is the
one setting whose *time* constant moves with the sampling rate (the PID's own PV
filter, 0.67 s of lag -> 0.33 s), and changing it in the same step would put two
variables in one roast. RoR is unaffected — `deltaBTsamples` is derived from the
stored `deltaBTspan` (20 s) and the interval (canvas.py:2796). **The live Artisan
session is still on the old values; load the file before the next run.**

**~~Step 1 — validate `pidKi` 0.07 + profile_003.~~ DONE — roast 46,
2026-09-05.** Five of the six checks pass, item 5 (floor time) fails on batch
size rather than on the loop, and the mid-roast ring is gone. Full reading in
state-history.md § Roast 46. Two things came out of it that set the order below:

- The residual above DRY END is **pure type-1 ramp error, ~1.0 degC / 4-5 s**,
  and the **measured optimum `svLookahead` is 6.3 s** — the value the step-6 file
  already carries. That makes **step 6 the next roast**, not an afterthought.
- profile_003's dip is matched to a **345 g** batch and roast 46 was **400 g**,
  which cost 30 degC of manufactured error, a rail-to-rail SV excursion and 11 s
  on the floor in the first minute. That is **new step 1b, profile_004**.

**Step 1b — profile_004, a 400 g dip. Run it *after* step 6 and step 1c, and
only with the lookahead-switching config.** Its value drops sharply once `Ki` is
gated (step 1c does the same job without an authoring step, and does it for
every charge state rather than one) — and note that roast 46 was a **frozen**
charge, so profile_004 would encode a frozen dip and would be wrong in the
*dangerous* direction (floor plus windup) for a warm one. Keep it on the list,
but as a refinement rather than a fix. Take 0:00-1:30 from roast 46's own
measured BT, keep profile_003's ramp and finish unchanged (the same operation
that produced profile_003 from profile_002 — state-history.md § profile_003,
state-history.md § Roast 46). Simulated in state-history.md § Roast 46 refit:
paired with the step-6 file it is the best configuration found — **0 s at the
floor**, dip error -2.6 degC against -8.8, handover `Iterm` 30, steady error
+0.18 degC — but at the present constant `svLookahead = 3` the same background
is *worse* than profile_003 (`Iterm` 41 at 1:30, a 9.1 degC undershoot over
1:30-3:00), because three seconds of lead against a steeper, earlier dip
manufactures a bigger negative error. The two changes are not independent.

**Step 1c — gate `Ki` off through the charge dip.** Two more hidden
Artisan-Command buttons and two more time-from-CHARGE alarms, regenerated the
same way as the lookahead pair: `p-i-d(3,0,0)` at CHARGE+1 s and
`p-i-d(3,0.07,0)` at CHARGE+90 s. `Ki = 0` closes both windup paths at once —
the integral term and, because `_back_calculate_integral` is gated on `getKi(PV)
!= 0` (pid.py:314-333), back-calculation as well — so `Iterm` is frozen through
the dip and handed to the ramp at a known value. Simulated over a 62 degC swing
in charge temperature the handover integrator goes from a spread of **36.5 to
0.3**, and time-to-BT-150 from 9.2 s of range to 1.8 s (state-history.md § The
dip is a different control problem). Expect the SV to sit on the 140 floor
longer and not lift off it before 1:30 — that is the mechanism working, not
failing. Watch the two traps: `p-i-d()` is sticky, so a Save Settings before
1:30 writes `pidKi = 0` into the `.aset`; and if the 1:30 alarm misses, the loop
is P-only for the rest of the roast (roast 40's failure mode, CONTROL button to
escape).

File: **`artisan/airRoaster_cascadePID_kigate.aset`**, or
`..._lookahead_kigate.aset` to run it together with step 6 — both generated by
`tools/gen_pid_alarm_asets.py`. Predicted outturn and the five things to check
are in state-history.md § The dip is a different control problem. Note that at
the usual charge state this is close to a **null experiment** on roast quality:
check the mechanism (`I@1:30` near 8, SV parked on the floor until 1:30), not
the outcome.

**Demoted 2026-09-06 — do not run this with step 6.** state-history.md § Dip
strategies reconstructs the charge sweep as a reproducible tool
(`tools/analysis/dip_strategies.py`), restricted to the warm side that a frozen
roast 46 leaves reachable, and finds the gate costs more than it buys there:
worst error over 1:30-3:20 +5.79 against step 6's -4.01, steady rms 0.38 against
0.26, and `dt150` spread 4.2 s against 0.4. The mechanism is real, its magnitude
is not settled, and the earlier sweep's code no longer exists to reconcile. **If
the gate is run at all, run it as gain scheduling rather than alarms** — `Ki` 0
→ 0.07 across BT 70 → 95, which is the same gate with no missed-alarm failure
mode, no sticky-`p-i-d()` trap, and a worst error of +2.95.

**Step 2 — flash v0.19.0 and wire up the new channels.** After step 1, so that
roast stays clean. **v0.19.0 now carries two items**: the `SV`/`HT` `getData`
nodes (done, below) and the `INLET TRIM` command that step 9 needs
(state-history.md § Firmware now in scope). `INLET TRIM` is inert until Artisan
is reconfigured, so flashing it changes nothing about the present cascade — but
it means step 9 needs no second flash. `./verify.sh upload`, then bench-drill
`INLET TRIM` (§ NEXT item 14) before any roast.

**The extra device is now in the `.aset` files and no longer a click-path
(2026-09-06).** The device id was previously left unresolved — *"not guessed here
because a wrong one silently mis-maps a curve"* — and it is **113 = `WS_56`**
(comm.py:491; 112 = `WS_34`, already in use for `IN`/`AT`). It is appended as a
**third** extra device rather than replacing the existing virtual `Temp_Drive`
(`Y3-Y2`), which survives: the ws channel index comes from the *device function*,
not from the device's position in the table, so `WS_56` reads
`channel_nodes[4..5]` = `SV`, `HT` wherever it sits. It also costs no extra
traffic — `WSread(0)` on the main device fills every channel from the single
`getData` reply and the extra devices return the cached readings (comm.py:1922-1951).

```
extradevices = 112, 25, 113      extraname1 = Inlet, Temp_Drive, SV
                                 extraname2 = amb, Extra 2, HT
```

All five `.aset` files carry it (the four variants are regenerated from the
canonical). Confirm the two curves appear and track — `SV` should read the
commanded inlet setpoint and `HT` the heat percent — then set **`createEvents`
back to false**; it is only the fallback, and it is deliberately left `true` for
the first roast that uses the new channels so the outer loop's output is recorded
twice. From there every roast is self-contained and no CSV is needed.

**Steps 3-5 — the characterisation runs. Three recordings, two sacrificial
batches, one session.** All of them load
**`artisan/airRoaster_cascadePID_char.aset`**, which forces the PID off at CHARGE
and replays the test schedule onto slider 3 from the background — press ON, load
the background, START, CHARGE, and the run drives itself (§ Files for the
characterisation runs). Run them back to back off one warm-up.

**~~Step 3 — Test A, empty roaster.~~ DONE — roast 47, 2026-09-06.** The
schedule replayed correctly (all 13 events on time), the inner loop held rms
1.12 degC, the `SV`/`HT` channels are live, and `feedforward()` is refitted —
**the coefficients step 8 was going to use are wrong, the `SV` term by 26x**
(state-history.md § Roast 47, and step 8 below). One failure: Artisan's built-in
`autoDrop` fired at 10:05 and cost 88 s and one steady window; the char config
now disables it. Re-running Test A would recover the fan 80 / SV 145 corner, but
the fit does not need it.

*The specification, for the re-run if it is ever wanted.* Background
`artisan/charstep_empty_fan.alog`
(`tools/gen_char_empty.py`): the original inlet sequence 145 -> **185 at 2:00** ->
**145 at 5:00** -> **185 at 7:00** -> **145 at 10:00**, extended with **185 at
12:00** and **145 at 15:00**, crossed against a fan sweep **64 -> 72 at 2:30 ->
58 at 5:50 -> 80 at 9:10 -> 64 at 12:30 -> 72 at 15:50**. The two grids are
offset so no fan step lands within 30 s of an inlet step and the regression can
separate them. Set fan 64 before CHARGE; the schedule replays both sliders. DROP
by hand at 17:00.

With no beans there is no circulation floor and no ceiling, so this is the only
run in the set that can sweep the fan widely — which is what **step 8** needs:
the affine `feedforward()` currently rests on five preheat fan steps spanning
0.81-1.11 %heat/unit, and this is the same regression with a real lever arm. It
does **not** replace Test C; an empty chamber measures the machine's heat demand
against airflow, not the bean-bed loss term that step 9's schedule is built
from.

**Step 4/5, the 617 g variant — one 400 g batch instead of two
(operator, 2026-09-06).** The sacrificial stock is 617 g, which is one 400 g
batch or two 308 g ones. **Two 308 g batches are the wrong answer**: charge mass
sets both quantities these runs measure — the bed's pressure drop, hence the flow
a fan level delivers (what `FF SLOPE` corrects), and the thermal mass in the
plant fit — so a 308 g pair would characterise a roaster the operator does not
run, with a single mass and nothing to extrapolate from.

Background **`artisan/charsingle_400g.alog`** (`tools/gen_char_single.py`), 12:15,
DROP by hand, same `airRoaster_cascadePID_char.aset`:

```
0:00  fan 64 (circulation), roast 45's ramp replayed
1:30  fan 60
2:45  SV 245 flat   3:15 fan 66   4:00 fan 60     slope @ 245, BT 145 -> 182
4:30  SV 150        valley -- pulls BT back down
5:30  SV 215 flat   6:00 fan 66   6:45 fan 60     slope @ 215
7:15  SV 150        valley
8:15  SV 190 flat   8:45/9:45/10:45/11:45 fan 70/60/70/60
                                                  slope @ 190 + the outer fan gain
```

**It measures strictly more than the two-batch plan could.** Roast 47 showed
heat reaches 95 % of its final value **within 2 s** of a fan step, so a slope
costs ~45 s rather than a plateau, and can be taken at several setpoints. The
model's fan sensitivity is a line in the setpoint,
`slope(sv) = cfan + cfansv*sv/100`; one setpoint only supports `FF SLOPE`
(rescaling both terms together, since their split is not identifiable from a
single point), while **three flat setpoints — 190, 215, 245 — identify `cfan`
and `cfansv` separately, loaded.** The two-batch plan had one, at SV 200.

Three things shape the schedule and the tool enforces them:

- **Every fan step sits at a dead-flat inlet**, ≥20 s from any inlet change.
  Heat depends on fan and setpoint and essentially *not* on BT — the inlet
  thermocouple is upstream of the bed — so BT climbing through a block does not
  contaminate the slope. What BT constrains is only how long a block can last.
- **The valleys are not filler.** A steady inlet drags BT to within ~`loss/a`
  (~15 degC) of itself, so SV 245 cannot simply be held — the plateau would be
  BT ~230, deep into second crack. Dropping to 150 pulls BT back at ~0.2 degC/s,
  and those up-and-down inlet steps *are* the plant-identification excitation,
  which is why this file needs no separate 3:00-5:00 doublet. Simulated BT peaks
  at **185.7 degC**; the tool refuses to write a schedule that reaches 196.
- **Block C steps ±10, not ±6.** The small pulses are sized for the heat signal
  (resolved to 0.4-1.5 %); the outer plant's fan gain is read from *BT* and needs
  a much larger push, so block C doubles as slope point and BT excitation.

What is given up: the between-batch fan-level contrast, and with it the
moisture-loss question — a roast-quality question, not a characterisation one,
and answerable later with two real roasts. And there is **no retry**: 217 g is
left, under the 250 g minimum. Roast 47 was the first outing of a new schedule
and hit an unforeseen trap, so if 800 g of other sacrificial beans can be found,
prefer the two-batch pair below and keep this as the fallback.

**The 1:30 circulation bump is a free fan step on every real roast — and it has
now been read (2026-09-08).** The step lives at **2:00**, not 1:30. Duty over
100-118 s against 126-146 s, detrended on the 60-118 s slope, gives **0.9-1.0 %
of heat per fan unit over 64 → 60** on roasts 56 and 57 — matching the empty
preheat regression's **0.992** exactly. **The loaded fan gain equals the empty
one**, and Test C's fan question is answered for this step without spending a
batch.

**But only two roasts are readable, and the reason is the caution.** Roasts 53-55
had SV ramping at **1.0-1.6 degC/s** through the window, so there is no flat
baseline to difference against and the detrend extrapolates nonsense (−14 to
−19 % of duty). It works on 56 and 57 because the lookahead switch moved to 45 s
and left the 100-145 s SV flat. **Read this step only where `dSV/dt` is under
~0.2 degC/s over 60-110 s**, and check that before quoting a number.

**The same step is now the leading suspect for the −2.9 degC residual at 170 s**
— see state-current.md § HANDOFF § 2. The duty step reads a **6.6-7.4 % flow
reduction**, which the outer loop must make up as delivered power.

**Step 4/5, the 800 g version — Test B and Test C, merged: two loaded 9-minute
runs.** Backgrounds
`artisan/chardoublet_fan60.alog` then `artisan/chardoublet_fan68.alog`
(`tools/gen_char_doublet.py`). Each opens at **fan 64 for circulation**, drops to
its ramp base at 1:30, carries the inlet doublet over 3:00-5:00, holds the inlet
from 5:20 so BT levels off near 185 degC, and runs a **fan square wave 60/70**
over 6:00-9:00, phase-reversed between the two files. Set **fan 64** before
CHARGE; the schedule replays every change from there. **DROP by hand at 9:00**
(both alarms are off in the char config). **Fill in `greens_temp`, weigh both
batches the same, and record both out-weights.**

**The fan excitation is inside each batch, not only between them** (operator
decision 2026-09-06). A between-batch comparison at n=2 confounds the fan with
everything else that differs between two batches, and roast 46 is the standing
proof that batch differences are not small (55 g manufactured a 30 degC error
swing). `tools/gen_char_doublet.py` therefore extends the original doublet to
nine minutes: **fan 64 to 1:30** for circulation, then the ramp at this batch's
**base**, **0:00-5:00 of inlet unchanged**, the inlet then stepped down to a
**200 degC hold** so BT levels off near 185 degC, and a **fan square wave 60/70
over 6:00-9:00**, phase-reversed between the two files. The ramp bases are **60
and 68**. So the level contrast lives in the ramp and the modulation lives in the
plateau, six transitions across the pair in both directions, and slow drift
common to the two runs cancels in the difference.

Four constraints shaped it, and each is a way the run could have been wasted
rather than merely noisy:

- **A charge does not circulate at 60.** It takes ~64 to loft the bed, after
  which 60 sustains (operator, 2026-09-06) — and roast 46's own events are that
  pattern, not the constant 60 state-current.md had summarised: 60 at CHARGE+2 s,
  **64 at +7 s**, 63 at +11 s, 60 at +85 s. **A constant fan from CHARGE is not a
  schedule this roaster can run**, so both files open at 64 until 1:30. Identical
  in both, so it differences out, and a step rather than a level, which is
  excitation rather than a confound.
- **Fan floor 55, and 58-59 in practice.** Below `IL_FAN_FULL_DFLT`
  (airRoaster.ino:111) the interlock stops giving the heater full authority, the
  heat clips, and the inner loop stops holding the inlet — the one thing that
  invalidates an open-loop identification run. The operator's own floor is higher
  (58-59 is the lowest reachable at all), so the schedule never goes below **60**
  and the tool refuses under 57.
- **There is no blow-out ceiling** (operator, 2026-09-06). The concerns above the
  usual band are *moisture loss at higher Reynolds number* and *bed uniformity* —
  chuffing drives local circulations that short-cut the asymmetric expansion
  funnel — neither of which rules out **70** for 60 s at a time on a sacrificial
  batch.
- **Stay below first crack.** Replaying roast 45's SV to 9:00 would run BT into
  second crack. The plateau at ~185 degC keeps the fan modulation clear of the
  bean exotherm, which would otherwise sit on top of exactly the signal being
  measured. The batches come out underdeveloped rather than burnt.

**The 60-vs-68 ramp bases also answer a question the operator has open
independently**: the standing preference is the *minimum* airflow that sustains
circulation, for efficiency, and it has never been compared against a higher one.
**Weigh in and out on both batches.** The comparison is indicative rather than
definitive, since the two runs share the plateau and the charge segment.

The background's BT column is replaced from 3:00 by a forward simulation of the
plant card, so it is an honest prediction rather than roast 45's closed-loop BT
(which stopped being a prediction the moment the doublet was spliced in). It
predicts **the same BT for both files**, because the card has no fan term — which
is the whole point of the runs: the measured difference between the pair is the
coefficient the card is missing.

~~After 3-5 the theta/tau ridge (state-history.md § Scheduling) collapses to
real numbers~~ — **superseded**: roast 46's involuntary rail-to-rail SV
excursion in the charge recovery did that job already (theta 13 +5/-1 s, tau 205
s, state-history.md § Roast 46 refit), and the Ki retune it was to enable has
been done — 0.07 is optimal, not a compromise. What 3-5 are still for is the
**fan** (Test C) and an independent check of the plant under a deliberate rather
than an accidental doublet. The **predicted-BT channel** (state-history.md §
Firmware now in scope) is a separate decision.

**~~Step 6 — the lookahead switch.~~ DONE — roast 49, 2026-09-06.** Rows 1-3
of the table below pass: steady tracking error **+0.40 degC / 1.84 s** against
roast 46's +1.06 / 4.73, time-to-BT **-0.9 / +2.2 / +2.0 s**, and the 1:30 switch
delivering +21.2 degC of commanded SV inside two samples with 95% of the
excursion in 12 s and no ring afterwards. Rows 4-5 miss — 29.2 s on the floor
against 16, a 7.7 degC SV reversal against 3.2 — and **both are the charge state,
not the loop**: roast 49's charge was 33-35 degC warmer than roast 46's, so the
dip ran 12 degC *above* the background rather than 9.8 below. Those two rows are
not a one-variable comparison and must not be read as one. Full reading in
state-history.md § Roast 49.

*The specification, for the record.* Load
`artisan/airRoaster_cascadePID_lookahead.aset` **unmodified** with background
profile_003 and roast normally. Roast 46 is the clean baseline it needed and
measures the required lead at 6.3 s against the file's 6; the validated
simulator in state-history.md § Roast 46 refit then predicts, against roast 46's
own numbers in brackets:

| | predicted | roast 46 as run |
|---|---|---|
| steady tracking error, 3:00-7:00 | **+0.05 degC / 0.44 s** | +0.75 degC / 3.4 s |
| time to BT 150 / 180 / 196.5 vs profile | -1.9 / +3.2 / +0.9 s | +3.5 / +5.0 / +4.4 |
| at 1:30: target step -> commanded SV | +4.0 degC -> **+24.7 degC**, settled in ~15 s | — |
| floor time in the charge dip | 16 s | 4 s simulated, 11 s measured |
| SV max / worst reversal after 1:00 | 296 / 3.2 degC | 289 / 0.3 |

So the answer to *"does the 1.0 degC / 4-5 s lag go to ~0?"* is yes, by
construction of the feedforward. Two expectations to correct: the SV kick at
1:30 is a quarter larger than state-history.md § Roast 46 estimated, and the
`pidLookahead(0)` leg makes the dip **worse** against profile_003 (16 s on the
floor, not better than L=3's 4) — leave it in anyway, because it is what makes
step 1b work. **Do not take the two-stage alternative**: swept against three-
and four-stage schedules it gains under 0.1 degC of rms and costs two buttons
and an alarm.

**~~Step 7 — a fixed fan, independent.~~ DONE — roast 49, and more cleanly than
specified.** The fan sat at **64 for the entire recording** — two `Air` events,
both 64, one at -1:48 and one at CHARGE — so preheat, the charge circulation bump
and the roast body all ran at one level and there is no air schedule anywhere in
the trace. The tracking result is therefore attributable to the loop with nothing
to subtract. Taken with roast 48's `kf = 0`, the air schedule has now failed to
earn its disturbance twice. The level was 64 rather than the specified 60, which
costs nothing here: `kf = 0` says the BT plant has no fan term, and
`feedforward()` covers the extra heat demand.

*The original statement.* state-history.md § Fan vs batch size says
the level does not depend on charge mass and the loop barely notices the level,
only the step. One roast at a flat **fan 60** with no changes tests whether the
ramp is earning its disturbance. Roast 46 already went most of the way: the fan
was held at 60 through the roast body — bar the mandatory 63-64 charge
circulation bump over 0:09-1:26, which is not optional and cannot be designed
out — and the trace shows no air-schedule signature at all (state-history.md § Roast 46), which is the cleanest evidence
yet that the ramp is not earning it. What is left is a roast that keeps 60
through preheat too.

**~~Step 8 — the feedforward term.~~ DONE — v0.20.0, 2026-09-06.** The map
becomes `heat_ff = c0 + cfan*fan + csv*sv + cfansv*fan*sv/100`, replacing the
single-product `ffK*fan*(sv-ambient)` that was clamped at 100 for 430 of 430
samples of roast 46 — inert rather than merely miscalibrated, with
`d(FF)/d(fan) = 0`, and collapsing the anti-windup bound to `[-100, 0]`.
Coefficients are roast 47's measured fit (69.8685 / -0.8570 / -0.5101 / 1.1423,
rms 0.68 % over nine steady windows), enabled by default, compile-verified.
README § Feedforward and the v0.20.0 version-history entry carry the detail.

**The affine model this step was going to install is retracted**
(`-30.62 + 0.99*fan + 0.0096*sv`): it under-predicts the measured grid by
11-26 % with its `sv` coefficient 26x too small, because the five preheat fan
steps behind it held the setpoint nearly constant. Recorded because it is the
generalisable lesson — a coefficient is only as good as the range its input
moved over — and `tools/analysis/roast47_ff.py` now cards the fitted box next to
the coefficients so an extrapolation is visible as one.

**What is NOT done, and it is deliberate: the map is empty-chamber.** A bean bed
changes the pressure drop and so the flow a fan level delivers, so the fan terms
are expected to move once loaded (operator, 2026-09-06). Every coefficient is
therefore runtime-settable and NVS-persisted, and **a loaded refit is a command,
not a reflash**. Two routes, in increasing cost:

1. **Free, from the runs already scheduled.** Each loaded doublet holds SV 200
   through a 60/70 fan square wave over 6:00-9:00, which is `d(heat)/d(fan)`
   loaded at the roast setpoint — the single number the bean load moves most.
   Feed it to `FF SLOPE <m>`: the firmware rescales *both* fan terms by
   `m / current_slope` while holding `heat_ff` at the present `(fan, sv)` fixed,
   which is exactly "the flow this fan level delivers changed by a factor". The
   split between `cfan` and `cfansv` is not identifiable from one setpoint, so
   they scale together.
2. **A loaded FF grid — only if 1 disagrees materially.** Test A's schedule with
   beans in would give a full loaded refit, but it costs a batch and carries its
   own confound: the bed's flow resistance drifts as the beans dry, so a 17-minute
   loaded grid is not measuring one plant. Justify it with evidence from route 1,
   not speculatively.

The dashboard's **FF step cal** panel is route 1 made one-click, and it got
simpler in the process: with the map carrying its own intercept it reports the
raw slope `dheat/dfan` and no longer needs an ambient at all.

**Step 9 — the inlet feedforward schedule with the PID as a trim.** The
structural fix, and the reason steps 1b/1c are demoted rather than deleted:
today the outer integrator has to supply the entire operating point, so it ramps
at 0.09 duty/s all roast, `e_ss = (dI/dt)/Ki` exists, `svLookahead` is needed to
hide it, and the value handed over at 1:30 matters. Give the firmware a base
inlet schedule (`ff(t) = bg(t+theta) + (dbg/dt - loss)/a`, merged into the
background as replayable events and replayed through Artisan's per-event-type
background playback on its own slider — **the authoring step now exists**:
`tools/merge_inlet_base.py --into artisan/profile_003.alog`, reading
`tools/analysis/plant_roast46.json`; § The base-curve authoring gap) and make
the PID's output a bounded trim on it via a new `INLET TRIM <degC>` firmware
command. Simulated: `dI/dt` 0.09 -> 0.01, `I@DROP` 63 -> 50, steady rms
**0.11-0.14 degC**, `svLookahead` 0, and with the `Ki` gate the handover
integrator and `dt150` are **identical at every charge state**. Survives +-20%
of error in the assumed plant gain. **Run steps 3-5 first** — the schedule is
exactly `1/a` and the loss curve, which is what those runs measure; then
`roast46_refit.py --emit-plant` to refresh the plant card and re-run the merge.
Two things are still open before this is roastable: the `.aset` half (the trim
slider, `pidPositiveTarget`, per-event-type playback), and the `--dip` question
— the merge tool's default back-extrapolated base is **not** the clipped,
dipping base that state-history.md § Dip strategies simulated (§ The base-curve
authoring gap, item 4). Full design, the source citations for the
playback/slider arrangement, and the risks to close are in § Step 9 above; the
strategy sweep that produced it is state-history.md § Dip strategies.

### What roasts 47-49 jointly say, and what to do next (proposal, 2026-09-06)

**Not decided. This section is a recommendation for the operator to accept,
reorder or reject**; nothing above it has been re-pointed at it.

**The through-line.** Three runs in one day closed three different things and
they point the same way. Roast 47 measured `feedforward()` over a real fan x SV
box; roast 48 showed that map transfers to a loaded chamber (bias +1.07%, rms
1.61%) and that the BT plant has **no fan term at all** (`kf = 0.0000`); roast 49
showed the outer loop tracking `profile_003` to **+0.40 degC / 1.84 s** with the
error inside -1.94 .. +0.93 degC for the whole ramp. Inner loop rms is 0.40-0.52
degC. **The controller is no longer the limiting error.**

What is left is almost entirely in the *reference*. Roast 49's worst excursion of
the whole roast was **-16 degC in the first minute**, and it was not the loop
failing — it was `profile_003`'s dip being authored for a 345 g frozen charge
while the batch was 400 g and ~33 degC warmer. Roast 46 had the same defect with
the opposite sign. Neither is fixable by tuning: at a warm charge the output
floor is a *lower* bound on inlet, so the loop physically cannot pull BT back
down, and it spends the minute saturated at an error it cannot act on.

That reframes the remaining work. **More control effort has low marginal value;
generating the reference for the batch in hand has high marginal value; and the
one measurement that unlocks it is the charge state** — which is what the
operator proposed independently.

#### The charge-temperature experiment

**The charge-thermal test (2026-09-06) took a run at this from a different direction and it
changes the design rather than closing it** — state-history.md § The charge-thermal test. It
measured the charge decay with **no flow**, and the result is that a still-air BT
decay **cannot** read bean temperature: the probe's expansion zone is narrow and
the preheated chamber holds a lot of heat, so BT weights 0.34 onto the walls with
a 36 s time constant, and the charge temperature trades against that freely
enough that the best-fitting solution puts a room-temperature charge at −2 degC.
It did **not** deliver the `C_chamber` calibration it was run for.

**Three things it did settle, and they all feed this run:**

- **Add a nine-second fan burst to any charge-state measurement.** It removes
  3.9 degC of still-air bias and takes BT below the temperature of the air being
  drawn in, which no reading of walls or air can do. It is the only
  charge-temperature instrument this project has that works.
- **The still-air arms are not interchangeable with a roast.** Under flow the
  mixing fraction is fitted from the roasts themselves
  (`tools/analysis/charge_dip.py`, `phi` 0.712 at 400 g, on the operator's
  temperature scale), not from the charge-thermal test.
- **The cheapest outstanding measurement is a repeat of the charge-thermal test's *warm* arm
  with a burst.** Only the frozen arm got one, so there is one bed reading and
  not two, which is most of why its joint fit is under-determined. One preheat,
  no beans consumed, no roast.

#### The preheat protocol, and why a throwaway roast is not one

**A roast is not a reset** (operator, 2026-09-07). The between-batch protocol —
cooldown duration, fan level, how long before the next preheat starts — is not
defined, so "run a batch first" leaves the machine in a state of unknown
magnitude. A **defined temperature held for a defined time** is an actual
boundary condition; that is what the runs use.

**And the state cannot be detected, only imposed.** The charge-thermal test's two preheats
converged to the *same* shallow state from opposite histories — cold-start
5.6 min ended at inlet 140.43 / heat 44.66%, warm-start 2.5 min at inlet
141.20 / 44.57% — and yet their plenums differed by **4.5 degC** through the
whole soak afterwards. The loop holds BT, so it absorbs the deep-mass difference
into a heat demand no operator can read. Fitting cycle 1's inlet approach gives a
**shallow time constant of ~46 s**, converged in ~4 minutes and informative about
nothing that matters. Worth roughly **2-4 degC of apparent bean temperature**
(`d(T_bean)/d(drop) = -1/4k = -2.45`), or 5-10% of the ~47 degC the pair creates.

**The protocol is therefore an elevated pre-preheat, then a fixed settle.**
Saturation at the elevated drive is a *fixed point* — once there, more time
changes nothing — so it erases whether the machine started cold or off a previous
batch, and it stops the result depending on how accurately the phase is timed.
The settle is then a fixed decay from a fixed start: same start plus same
duration gives the same end, by construction.

| phase | what | duration |
|---|---|---|
| elevated | `INLET 200`, fan 64, **PID off** | 10 min |
| settle | cascade on, BT 130 | 10 min from BT first within 1 degC |

**Superseded on the bench, 2026-09-07 -- see the next section.** The elevated
phase is dropped and the preheat runs at **fan 60** with a Temp_Drive criterion
instead of a stopwatch: at fan 64 the settle cannot reach BT 130 at all.

Sizing: the chamber mass that takes part in the charge mix is `C ~ 353 J/K`
against `UA >= 3.3 W/K` (the plant's own `a` on a 680 J/K bed), so **tau <= ~2
min** for that one; the deeper reservoir is the charge-thermal test's 510-557 s *no-flow* decay
and its driven constant is unmeasured. Ten and ten is ~5 constants of the fast
one and ~2 of the pessimistic one, and identical on both runs. **Lengthen the
elevated phase rather than the settle** if hedging — that is the one where extra
time is free.

**Accept that repeatable is not the same as comparable to roasts 43-49.** Those
were charged from uncontrolled machine states; roast 49 was not even settled (its
recording starts 71 s before CHARGE with BT still climbing 115.8 -> 128.1 and the
inlet falling 225.7 -> 175.8, which is why its `inlet_pre` reads 168.6 against the
group's 140-152 — an unsettled machine, not a hotter one). Let the pair define
its own baseline and adopt the protocol going forward.

**A free retrospective check exists.** With no flow the plenum never sees the bed
(state-history.md § The charge-thermal test), so the **post-DROP inlet decay is a
bean-independent readout of stored heat**. Record through the cooldown on both
runs and overlay the two curves: if they sit on top of each other the protocol
worked, and if they are offset the difference is correctable — and it yields the
driven time constant.

#### The preheat runs at fan 60, because BT 130 is unreachable at 64

**Found on the bench, 2026-09-07, and it corrects two things in these notes.**
The first attempt at the protocol above ran the elevated phase at `INLET 200`
with fan 64 and then could not settle: with the PID clamped at
`positiveTargetMin = 140` the inlet pinned to its floor and **BT stalled at
137**, Temp_Drive (`Inlet - BT`, the `Y3-Y2` virtual channel) reading ~3.

**It is the fan, not the walls.** Roast 47's empty-chamber grid at a constant
SV 185 gives Temp_Drive **25.4 / 15.4 / 14.5 / 13.3** at fan **58 / 64 / 72 /
80** -- steep through 58-64 at about **-1.7 degC per fan unit**, then flat.
(Those windows are ~25 s against a ~45 s empty-chamber time constant, so the
trend is the result and the absolute values are not.) That matches the two
settled points on record: the charge-thermal test at fan 60 sat at Temp_Drive **10.6**, the
bench at fan 64 at **~3** -- -1.9 per unit over the same span.

So at fan 64 holding BT 130 needs **inlet ~133**, below the 140 floor. It is an
equilibrium, not a transient, and no amount of waiting reaches it.

**This explains roast 49's preheat, which § Roast 49 records as an oddity.** It
was not impatience: roast 49 held fan 64 throughout, so there *was* no settled
BT 130 to charge from, and it was charged mid-ramp because that is the only way
to cross 130 at that fan. Every roast that settled -- 43, 44, 45, 46 and both
the charge-thermal test cycles -- preheated at **fan 60**, where the required inlet is
140.4-140.8, just above the floor.

**And it corrects the paragraph above**: the machine state *is* observable, but
Temp_Drive reads it only at a **fixed fan**. The 23.2 / 17.2 / 15.0 / 11.4 spread
across roasts 43/44/45/46 is settling state at a common fan 60; the bench's 0.9
was an over-charged wall on top of a fan-64 offset, and the persistent part was
the fan.

**The protocol is therefore:** preheat at **fan 60** under the PID; hold until
**Temp_Drive settles into 10-12** with BT flat at 130 and the inlet **off** the
140 floor; press fan **64** immediately before tipping and leave it there. That
is roasts 43-46's own schedule, so the pair lands on the historical state rather
than only on each other, and a 400 g charge needs ~64 to loft in any case. **The
elevated pre-preheat is dropped** -- the settling criterion handles machine
history from either side without it.

**None of this reaches the measurement.** The proxy is read over `0..theta` and
nothing the heater does arrives before ~13.5 s, so the floor, the lookahead
switch and the fan step at CHARGE are all control, not signal, as long as both
runs are identical.

#### The charge gate — the outer loop must not act through the dip

**Roast 52 found the mechanism, and it is in Artisan's source, not in the
tuning.** `pid_control.py:1687`: *before CHARGE, the CHARGE temp of the
background profile is returned* — until `timeindex[0]` is set, Follow Background
targets **one constant**, the background's BT at its own CHARGE, and not the
curve. autoCHARGE needs about five samples of BT-break evidence, so for **~3.5 s
after the beans go in** the target is pinned at 130.2 while BT is already through
116.

That **inverts the sign of the error**: live tracking wants `bg - BT =
105.8 - 116.0 = -10.2` and would cut the heat, while the frozen target says
`130.2 - 116.0 = +14.2`. Roast 52 answered it by stepping `T_inlet` **140 -> 224
in a single 0.5 s sample** at +3.5 s, then on to 275, with heat at **100% for
22.5 s**. The energy arrives 13.5 s later — at 17-30 s, **the turning point** —
so the loop's hardest push lands exactly when the bed is already recovering. BT
then overshot to **+20.1 degC at 58 s** and the loop sat **37.5 s on the 140
floor** undoing it.

**Roast 53 corrected this: the frozen target is real but it is not the dominant
term.** Its own frozen window was ~1 s and it still commanded SV 238. Replaying
the port against roast 53 — `rms 2.1 degC over 0-30 s`, peak 238 against a
measured 238 — puts the kick on the **lookahead** instead:

1. `calcSV` **ignores `svLookahead` before CHARGE** (pid_control.py:1690 returns
   the background's CHARGE BT, one constant), so `svLookahead = 3` first takes
   effect *on the sample CHARGE is marked*.
2. The bed is falling ~6 degC/s there, so a target 3 s ahead sits **15-20 degC
   below** BT. The output floors.
3. `_back_calculate_integral` (pid.py:314-333) turns the clamped excess into
   stored integral — **`Iterm` 1.2 → 37.8 in two samples** — and `Ki = 0.07`
   cannot unwind it. It is the *integral*, not the P term, that holds `T_inlet`
   at 200-238 for the next 30 s.
4. The `LA 0` alarm closes the window ~2.5 s after CHARGE, about 2.5 s too late.

Both readings point at the same window and the same fix, and the port says the
correctly-targeted loop wants **174-181** there. Detail in
state-history.md § Roast 53.

**The fix costs nothing, because the loop has no authority there.** Nothing the
heater does reaches BT before ~13.5 s, so the outer loop cannot affect `0..theta`
at all and its actions there land where they do harm. `airRoaster_cascadePID_chargetemp.aset`
now carries:

- a visible **`CHARGE`** button, Multiple Event → **Fan FULL (64) + PID OFF**, so
  the gate cannot be forgotten or mistimed;
- an alarm at **CHARGE+15 s → PID ON** (its first correction then lands ~28.5 s,
  just past the turning point);
- **`pidOnCHARGE = false`**;
- **`svLookahead = 0`** as the file default.

`PID OFF` *cannot* be an alarm: alarms fire from CHARGE, which is the mark that
arrives too late. It has to be the same press that tips the beans.

**The last two are what roast 53 cost, and neither is optional.**

`pidOnCHARGE = true` makes the gate a no-op: `markCharge` calls `pidOn()` whenever
it is set and the PID is not already active (**canvas.py:14656**), so the button's
`PID OFF` is undone by the CHARGE mark, ~1 s later and still before the beans
reach the sensor. It had never mattered before because the preheat runs with the
PID already active; adding a deliberate `PID OFF` is what exposed it.

`svLookahead = 0` removes the window at (2) above rather than racing it, and costs
nothing — the `LA 0` alarm sets the same 0 at CHARGE+1 s either way, and the value
is unused before CHARGE. It is also what makes the gate **robust to the operator**:
if the `CHARGE` button is missed, the lookahead window no longer bites. On the
replay, either fix alone drops the peak from 238 to 174-179.

**And it makes both halves agree.** `make_charge_background.py` builds the dip
with the inlet **held at its pre-charge value**; the gate is what makes the plant
actually do that. The same assumption on both sides, which is why this should
close rather than trade one error for another.

**Verified by roast 54 (2026-09-07).** `T_inlet` carried nothing between CHARGE+1 s
and the `PID ON` alarm at +15.5 s, inlet sat at 143-145 through the dip, peak SV
fell to **193**, 100% heat to **3.0 s**, worst BT error 30-90 s to **+5.5 degC**,
and peak `Iterm` to **17.3** against roast 53's 44.1. The port reproduces the
roast to rms 0.74 degC over 120-240 s. **The loop is closed; what remains is the
dip model** — see state-current.md § HANDOFF.

**One diagnostic in the roast-53 write-up above is wrong.** The duplicate
`T_inlet` event at CHARGE+1 s is not `pidOn()`'s signature: `markCharge`
re-records every visible non-zero slider at CHARGE (canvas.py:14694-14709) and
`EventRecordAction`'s guard (canvas.py:15854-15856) compares only against the
single most recent event *of any type*, which the CHARGE button's own `Air -> 64`
has already displaced. It appears on every roast including the gated one. The
`pidOnCHARGE` conclusion is unaffected — that rests on the flag's value in the
file and on canvas.py:14656.

#### The dip model's joint refit — DONE 2026-09-07

Superseded by state-history.md § The dip model's joint refit. The ramp is in
(`charge_dip.mix_kernel`, `w_c = 2.10 s`), the calibration group moved to the
roasts with an *entered* greens temperature (`phi400` 0.7116, `tau_mix` 10.84),
and the generated background's worst error against roast 54's free dip fell from
22.6 to 2.6 degC. Two things it left behind, both live:

- **The turning point is still ~6 s late** and that is residual model error, not
  the expected offset this file used to claim. It costs under 2.6 degC because
  the minimum is flat. Do not fit it away.
- **`phi` is depth per degC on the operator's temperature scale, not physics.**
  Anything fitted or evaluated against a charge temperature must stay on one
  scale; settling it needs a measured *core* temperature.

#### The fan step is timed, not hand-pressed

Also in the file: an alarm at **CHARGE+120 s** firing a hidden `Fan 60` button
(event type 0, value 7.0, the same `OT2` send the hand buttons use, so a replayed
step is indistinguishable from a pressed one). 2:00 is the quietest window in the
roast — the dip is long over, the 1:30 lookahead switch has settled (95% in 12 s
on roast 49) and DRY END is still ~60 s away. The plant has **no fan term**
(`kf = 0`, roast 48), so this moves the operating point and not the dynamics:
holding BT needs about **3.5 degC more inlet** at fan 60 than at 64.

#### autoCHARGE must be disarmed through the settle

The settle descends BT from ~185 degC (empty chamber at `INLET 200` sits ~10 degC
under the inlet) to 130. Artisan's autoCHARGE fires on a BT break of `d = -0.34`
degC per sample over two consecutive legs at `Delay=500` — **0.68 degC/s**, above
77 degC (canvas.py:5121, main.py:24306, params canvas.py:548). The empty-chamber
time constant is **40-50 s** (the charge-thermal test's reheat: BT 57 -> 129 at inlet ~235 gives
`a ~ 0.02 /s`), so a 55 degC descent runs at **1.1-1.3 degC/s** and trips it
within seconds. A gentler overshoot does not help: 30 degC gives 0.67 degC/s,
exactly on the boundary. **Disarm it; do not try to stay under the threshold.**

`autoCHARGE(<bool>)` is an **Artisan Command** (action 20, main.py:10286) and
sets `qmc.autoChargeFlag`; `autoDROP(<bool>)` is its sibling at :10298. **Alarms
cannot issue one** — their action list is 26 fixed entries and "Artisan Command"
is not among them (alarms.py:898) — so the route is alarm -> **Event Button** ->
command, the pattern `gen_pid_alarm_asets.py` already uses for the timed levers.
**`artisan/airRoaster_cascadePID_chargetemp.aset`** is that file: `lookahead`
unchanged, plus `autoCharge=false`, a visible `ARM CHG` button carrying
`autoCHARGE(1)`, and a backstop alarm (ON+960 s **and** BT < 131) pressing a
hidden twin. The temperature gate is what makes the backstop safe — BT crosses
131 about three time constants into the settle, drifting at ~0.02 degC/s.

**Trap:** `autoChargeFlag` is persisted as `autoCharge=` in the `.aset`, so a
*Save Settings while disarmed* bakes `autoCharge=false` into the file and the
next roast silently never marks CHARGE. Same sticky-config class as `p-i-d()`.
Re-load the file rather than saving over it.

**Then run the pair.** Two 400 g batches of the same lot, everything else held
identical, one straight from the freezer and one equilibrated at room
temperature for >= 12 h. Roast 49 is already a usable warm arm, so if only one
batch can be spared, **make it the frozen one** and pair it against roast 49 —
but a deliberate pair is worth much more, because roast 49's preheat was 28 degC
hotter than the group's and that had to be corrected for rather than avoided.

What has to be held fixed, and why each one:

- **`greens_temp` recorded on both.** Probe the bean mass, not the air, and enter
  it in Roast Properties. It is `0.0` on all of roasts 43-49, which is the only
  reason any of this is inference. This is the whole point of the run, and it is
  now the *only* thing standing between this project and a measured charge
  temperature under flow: `charge_state.py`'s `k`, roast 48's +12.8, roast 49's
  +15.5 and `charge_dip.py`'s `phi` all rest on roasts 43/44/46 having been at
  −18 degC, and nothing has yet tested that.
- **The preheat trajectory, not just CHARGE_BT.** Inlet air from
  `t in [-theta, 0]` arrives inside the mixing window, so a hotter preheat makes
  the beans look warmer. Hold the inlet flat within +-2 degC for 60 s before
  CHARGE on both.
- **Mass, to the gram.** The proxy is not linear in mass
  (`dBT = m*c*(BT_c - T_b)/(C_chamber + m*c)`), so a mass difference does not
  divide out.
- **Fan constant, as roast 49 already did**, and the same config and background
  (`airRoaster_cascadePID_lookahead.aset` + `profile_003`) so the run is also a
  second step-6 sample.

What it measures: `k` and `C_chamber` in the mixing model, and — the part no
existing run can give — whether the dip *shape* (depth, turning-point time, the
recovery slope out of it) is a function of the same variable, or whether bean
temperature moves more than one thing. `tools/analysis/charge_state.py` runs the
proxy and prints the band; `tools/analysis/charge_dip.py` now predicts the whole
0-90 s arc from `(mass, greens temp)` and is what this run would confirm or
break. It also carries the one open disagreement: the charge-thermal test's still-air fit wants
a fusion enthalpy and the roasts want none, and a pair with `greens_temp`
actually recorded is what separates `phi` from `h_fus`.

**Expect the warm run to roast differently, and let it.** Roast 49 finished with
a 19 s development window against roast 46's 25 s and the background's 26 s, at
the same DROP BT. If that difference survives a controlled pair it is a real
outturn consequence of charge state, not a tracking artefact, and it is the
argument for doing anything about the dip at all.

#### What it unblocks, and the revised ranking

1. **The charge-temperature pair** (above). Cheap, no firmware, no Artisan
   reconfiguration, no new failure mode, and useful under every path below.
2. ~~**Backgrounds generated from (mass, greens temp)**~~ **— tool written
   2026-09-07, `tools/make_charge_background.py`, awaiting its first roast.**
   It *merges* rather than generates: the dip is physics and is computed, the ramp
   is the roast design and stays the operator's, and only `temp2` from CHARGE to
   the join is rewritten so `timeindex`, DRY END, FCs and DROP survive exactly.
   The inlet is **held at its pre-charge value** through the dip rather than taken
   from a measured roast — that trace is the loop reacting to the very background
   being replaced, so using it would bake the overshoot in. Acceptance is scored on
   `0..18 s` alone, the window in which nothing the heater does has arrived yet:
   worst error against roast 50 goes 4.9 -> 4.3 degC and against roast 51
   **18.2 -> 6.7**, the turning point moves from `profile_003`'s 37 s to 27-29 s,
   and the curve asks for 32-43 degC/min where the machine delivered 60-120.
   **The turning point lands 5-8 s later than roasts 50 and 51 measured, and that
   is correct**: those turned early *because* the loop kicked, and a background the
   loop does not fight leaves the inlet where the preheat put it. Generated on
   demand and not committed, like the merged inlet backgrounds. Step 1b generalised
   from one authored `profile_004` to a computed dip. This is what removes the
   -16/+9 degC first-90 s error at its root, for every charge state, rather than
   for the one that was authored. It needs (1) and nothing else.
3. **Step 9, after (1) and (2), and reframed.** Its headline claim — steady rms
   0.11-0.14 degC against 0.26-0.38 — is now a marginal gain over a measured
   +0.40 degC, so *tracking* is no longer the case for it. Two arguments survive
   and both are about robustness: it stops the integrator being a ramp-follower
   (`dI/dt` 0.09 -> 0.01), and it decouples the loop from the profile's shape, so
   a differently-shaped profile does not need `svLookahead` re-derived. It also
   has a live cost that roast 48 raised: the base schedule is `bg(t+theta) +
   (dbg/dt - loss)/a`, and roast 48 found `a` and `theta` **not stationary within
   one roast** (`a` 0.0062-0.0085, `theta` 7.8-14.5). The trim absorbs that — the
   simulation survives +-20% of gain error — but it caps how good the base can
   be. **Half of that is now retracted** (item 4 below): `theta`'s spread was a
   structural artefact and goes to 0.0-1.0 s under the two-lag fit, and the lead
   term is sound as written. `a`'s spread is real and, under two lags, slightly
   wider. (1) and (2) also settle its open `--dip` question outright: with a charge
   model the dip can be *computed* into the base rather than back-extrapolated
   around.
4. ~~**Desk: settle the deadtime-versus-lag question.**~~ **Done, 2026-09-06**
   (`tools/analysis/deadtime_vs_lag.py`; state-history.md § Deadtime versus lag).
   The answer changes a claim rather than a number, so nothing below it moves.
   Roast 49 was checked and **cannot support the fit** — closed-loop, one 1:30
   step, and its two-lag fit runs away to a negative gain on the tau2 grid
   `roast48_plant.py` uses. Roast 48's steps identify the split as **all lag**
   (`theta` 0-2 s, pure deadtime costs 42-131% more residual); roast 46 is a
   ridge in which only **`theta + tau2` is determined**, at 12-14 s — and that
   sum *is* the single-lag `theta` both cards report. So the 13.5 s is total
   apparent lag, not transport. Consequences: the phase margin at Kp 3.0 /
   Ki 0.07 moves 32.8 -> 37.7 deg across the **entire** ridge, so **`pidKi` 0.07
   stands**; and the `bg(t+theta)` lead is a valid first-order stand-in for the
   lag inversion `X + tau2*dX/dt`, differing by rms 0.83 degC on profile_003, so
   **`plant_roast46.json` and `merge_inlet_base.py` need no change** and (3)
   loses the "live cost roast 48 raised" caveat below. What is *not* settled is
   `a`, which is non-stationary under both structures and slightly worse under
   two lags; that is a separate question and no run is proposed for it.
5. **Drop the remaining characterisation runs.** Test C's two loaded doublets
   existed to measure the fan; roast 48 measured it (`kf = 0` in the plant, and
   the loaded FF check needs no correction, so `FF SLOPE` has nothing to do). A
   loaded FF grid stays unjustified. Step 1c stays demoted.

#### The dump-lever switch

**Yes — ground against a pin with `INPUT_PULLUP` is exactly right.** The ESP32-S3
has ~45 kOhm internal pull-ups, so `pinMode(pin, INPUT_PULLUP)` reads HIGH when
open and LOW when the lever closes it to GND. Specifics for this board:

- **Pin: GPIO 14 (A4).** From [hardware/pins.md](hardware/pins.md) § Free GPIOs.
  It avoids the ESP32-S3 strapping pins (0, 3, 45, 46 — none are on the free
  list anyway), leaves GPIO 38/39 for Serial1 and 42 for SPI SS, and keeps
  GPIO 5/6 (A8/A9) together for the planned BME688 pump driver.
- **Add an external 10 kOhm pull-up to 3V3** rather than relying on the internal
  one. A metre of wire to a mechanical switch beside two AC dimmers is an
  antenna, and this project has an EMI history worth respecting
  ([hardware/emi.md](hardware/emi.md)). A 100 nF capacitor across the switch
  terminals at the *board* end damps the rest. Route the wire away from the
  dimmer AC leads.
- **Debounce in firmware**, 20-50 ms, and act on the **edge** (open -> closed),
  not the level, so a lever left down does not re-trigger.
- **Publish it as `DL`** (0 or 1) in the `getData` reply beside `SV` and `HT`,
  and map it to `channel_nodes` slot 7 with `channel_modes` 0 (not a
  temperature). Then the DROP alarm becomes **Source = that channel, condition
  above 0.5, action DROP** — the same alarm mechanism as today, on a measured
  event instead of an inferred RoR collapse (§ Auto-DROP detection). Keep the
  RoR alarm as a backstop until the switch has proven itself over several roasts.

### Commissioning order

0. **Every roast: press ON (zeroes the integrator), turn the PID on, preheat
   under PID control, then CHARGE — one PID on/off cycle per monitor ON/OFF
   cycle.** ON is the only thing that clears Iterm; **RESET does not**, so cycle
   OFF -> ON between roasts rather than reusing a session (state-history.md §
   Roast 41). Preheating under the PID hands the roast an integrator already at
   the empty-roaster operating point (state-history.md § PID-driven preheat).
1. **Bench, heater cold.** Load `airRoaster_cascadePID.aset`. PID on -> confirm
   `INLET` traffic on the dashboard, that the commanded value floors at 140 and
   never reaches 0, that it carries a fraction, and that firmware `mode` reads
   `inlet`. Mark DROP -> confirm the existing button chain sends `INLET 0` and
   the firmware returns to `manual` at heat 0. Confirm no T_inlet playback
   traffic appears on the slider.
2. **First roast, conservative gains.** Watch for outer-loop overshoot and for
   the inner loop saturating (heat pinned at 0 or 100 for long stretches means
   the outer loop is asking for something unreachable).
3. Retune Kp/Ki from the log; only then consider Kd and `svLookahead`
   (currently 0; a few seconds of lead may help against thermal lag).

Optional tuning aid: `createEvents=true` records the commanded inlet SV into
the profile as events, which makes the outer loop's output reviewable
afterwards at the cost of a cluttered profile.

No bundled machine profile in Artisan's own `Machines/` directory does a
cascade: all 35 with a configured software PID target slider 4 (heat), the
Giesens included, even though they too put a temperature slider on 3. There is
no vendor precedent to copy here.

## Later / not scheduled

- **Vision module — camera-based fan trim for bean circulation** (idea opened
  2026-08-24). Fan setting isn't repeatable across beans/loads, but circulation
  quality is visually observable; a vision process would quantify it and send
  bounded `FANTRIM` adjustments over the authenticated WebSocket, with
  firmware-side clamp + timeout decay so vision is advisory, never fan
  authority. **Leading architecture: the Mac hosts it** — it already runs
  Artisan and the auth proxy every roast, which deletes the coprocessor, its
  power rail, its EMI cell, and any dev/deploy transfer risk; a Pi 5 stays on
  the shelf as the later path to a self-contained roaster. Firmware exposure is
  one command (`FANTRIM`, default off). Full plan, camera trade study, metric
  candidates, and phased rollout (observation → offline metric → camera
  decision → live display → advisory → closed loop): [vision.md](vision.md).
  Phase 0 (label clips from existing webcam/phone + synced telemetry) costs
  nothing and gates all spending. The gating unknown is manual exposure control
  on macOS (OpenCV's `CAP_PROP_EXPOSURE` no-ops on UVC webcams there); vision.md
  carries a **§ UVC probe procedure** — a runnable `uvcc`/libusb runbook that
  settles it on hardware already on hand before any purchase. Camera screening
  done: **Basler dart daA1440-220um** (IMX273, mono global shutter, 227 fps) is
  the pick — pylon/pypylon covers macOS Intel *and* Apple Silicon *and* Linux
  ARM, so one camera serves the current laptop, a future one, and an Option B
  Pi. Teledyne FLIR ruled out (macOS builds stuck at Mojave).
- **Evaluate moving the DimmerLink link from I2C back to UART serial.** The
  modules ship UART-by-default and were switched to I2C during provisioning
  (see [config.md](config.md) § 3); on this project's questionable wiring the
  serial link has looked *at least as noise-tolerant* as I2C. Worth a
  controlled comparison — if serial holds up, it may be the more robust
  transport here. Would touch the DimmerLink transport layer in
  `airRoaster.ino` (register reads/writes, `initDL`/`assertDLState`,
  boot sync) but not the control law; keep the commit-on-ack + re-assert
  robustness shape (v0.13). Cross-reference the EMI history in
  [hardware/emi.md](hardware/emi.md).
- **Auto-provision a fresh DimmerLink module in place (UART→I2C on the I2C
  pins).** A factory module ships on UART at the default I2C address `0x50`
  ([config.md](config.md) § 3); today that switch is a separate bench sketch.
  Idea: do it in-firmware without rewiring by temporarily driving the I2C pins
  (SDA `GPIO3` / SCL `GPIO4`) as a UART through the ESP32-S3 GPIO matrix. Flow:
  on boot (or a `DLPROVISION HEAT|FAN` command), if the expected address does
  not ACK, tear down `Wire`, bring a UART peripheral up on those pins, send
  `SWITCH_I2C` (`0x5B`), wait for the mode to persist, tear the UART down,
  `Wire.begin()`, write the target address to reg `0x30`, verify `VERSION`.
  Open questions to resolve first: (a) confirm the module's UART TX/RX land on
  the *same* two physical pins as its I2C SDA/SCL (the "two-bus" connector) —
  this is the crux; (b) confirm the DimmerLink UART baud/framing from the UART
  protocol docs; (c) collision — two fresh modules both answer `0x50`, so this
  only works with a single unaddressed module on the bus (provision one at a
  time, or before the second is wired); (d) safety — only with heat off and the
  boot heat-zero intact. Payoff: plug in a replacement dimmer and it
  self-provisions.
- **Data-driven device registry (add a device via a `.json` change) — all
  buses.** Make adding an *auxiliary* peripheral a config edit, not a code
  edit: a small JSON manifest of `{bus, addressing, type, role, options}` the
  firmware reads at boot to instantiate/parse the device. The idea is not
  I2C-specific — it applies the same way across **all three buses**, with the
  bus deciding the addressing field: I2C → device address, SPI → chip-select
  pin (+ SPI mode/clock), serial/UART → port + baud/framing. Candidate
  storage: a compiled-in JSON string, an NVS blob, or a LittleFS/SPIFFS file
  flashed with the firmware (or pushed from the dashboard). Scope guard: keep
  the **safety-critical core** devices (both dimmers, inlet TC, the RTDs)
  hardcoded and interlocked — the registry is for optional sensors first (the
  BME688 ambient below, an extra RTD, environmental sensors) whose presence and
  wiring vary. A full driver-plugin system is a large refactor; a lighter first
  cut is a table of *known* optional device types keyed by bus+address. Ties
  into the dimmer auto-provision above (address assignment) and the BME688 item
  below.
- **Cryptographic authentication of the command interface (safety/security).**
  **→ PROMOTED 2026-07-10: in development as v0.18.0 on `feature/auth-proxy`**
  (see state-current.md). The notes below are the original design record.
  Today the WebSocket server on `:81` accepts plaintext commands from anyone on
  the network — `OT1`/`OT2`/`INLET`, and the safety config (`IL`, `COOL`,
  `DLRESET`, `PID`, `FF`, `CURVE`, `AMB`). On a private WLAN the risk is low,
  but this drives a **heating element**, so an unauthenticated write path is the
  standing exposure. Goal: only authorized clients can issue state-changing
  commands. **The hard constraint is Artisan**: its WebSocket client speaks
  plain `ws://` with no auth header, token, or `wss` client-cert support, so
  mandatory auth would break the primary use. Design has to be layered:
  - Keep the *read* path (`getData`, telemetry, `LOG`, `STAT`) and the Artisan
    *slider* commands usable, and authenticate the privileged/mutating commands
    — or gate privileged commands to the dashboard only while Artisan keeps a
    reduced, network-trust-scoped surface.
  - Candidate mechanisms, lightest first: **HMAC-signed command envelope**
    (shared key + monotonic nonce/timestamp for replay protection) — cheap, no
    TLS handshake, fits the existing JSON envelope; **challenge–response
    session auth** on connect (device issues a nonce, client proves the shared
    key, session trusted thereafter); or full **`wss`/TLS** via mbedTLS (heavier
    on RAM/latency, and still doesn't solve Artisan). OTA already carries a
    shared password (`OTA_PASS`) — precedent for a secret in `secrets.h` + NVS.
  - Dashboard gotcha to verify early: the browser HMAC needs Web Crypto
    (`crypto.subtle`), which requires a **secure context** — `file://` and
    `localhost` qualify, but a dashboard served over `http://<lan-ip>` may not,
    which would block signing. Confirm before committing to a browser-HMAC
    design.
  - **Parked (2026-07-10, operator decision):** mandatory auth stays off the
    table for now because Artisan must keep sending commands or the setup
    doesn't work. The workable shape, if/when revisited, is a **localhost
    signing proxy**: Artisan connects to `ws://127.0.0.1:<port>` on the
    operator's machine (unauthenticated but localhost-bound), and the proxy
    holds the shared key and signs traffic to the roaster, which rejects
    unsigned writes. Artisan needs no changes beyond the Host field. The
    "laptop becomes the sole operator" concern is softer than it sounds:
    *keyed devices* are operators (any machine with the key can run the proxy;
    the dashboard could HMAC directly), and the Artisan machine is already the
    operator console — the proxy co-locates with it. What's lost is ad-hoc
    access from unkeyed devices; the fix is an unauthenticated **safe subset**
    in firmware — reads plus safety-increasing commands only (`OT1 0`,
    `INLET OFF`, `COOL ON`) — so anything on the network can still stop the
    roaster, never start it. **Operator-approved (2026-07-10): the safe subset
    is a requirement of any future auth design**, not an optional mitigation.
    A proxy crash mid-roast is no worse than
    Artisan crashing: the firmware failsafes are client-independent.
  - Open questions: which exact commands are "privileged" vs open; replay/nonce
    persistence across reboot; key provisioning + rotation; and whether to pair
    this with network-level isolation (roaster VLAN) as the pragmatic near-term
    mitigation while the crypto path is built.
- **OTA hardening beyond the dedicated password** (first-order fix shipped
  2026-07-11: `auth_key.py ota` generates a random `OTA_PASS`, closing the
  WIFI_PASS fallback where anyone on the WLAN could push firmware). Two
  further layers, deliberately deferred: (a) **OTA arming** — only call
  `ArduinoOTA.handle()` for ~5 min after an authenticated `OTA ARM` command
  (TIER_CONF or serial), so a push needs both secrets and accidental pushes
  are impossible; cheap (a flag + timeout + one command) and consistent with
  the existing idle gate — do this one first if OTA exposure ever worries us
  again. (b) **Signed images / ESP32 Secure Boot** — defends adversaries who
  already hold the passwords; Secure Boot burns irreversible eFuses and the
  ESP32 Arduino core lacks built-in update signing (unlike ESP8266), so this
  is real toolchain work for a threat beyond the stated LAN model. espota
  transport remains cleartext either way — key-bearing flashes stay on USB.
- ET RTD probe installation → set `RTD_ET_ENABLED 1` (sensor code is ready).
- BME688 ambient sensor on STEMMA QT (`0x76/0x77`) — would give a true room
  ambient for feedforward instead of the cold-junction estimate.
- DimmerLink curve-mode experiments: curve is set to RMS (mode 1) at
  startup; LINEAR/LOG untested.
- Move `controlStep()` to a pinned FreeRTOS task if `STAT` evidence (post
  Phase 2, when the metric is honest) ever shows the cooperative loop failing
  its cadence.
- String→char parsing in hot paths if heap fragmentation ever shows (low
  priority on the S3 with PSRAM).
