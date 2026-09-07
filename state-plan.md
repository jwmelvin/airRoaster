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
| widen/narrow `positiveTargetMin/Max` to shrink the integrator's swing | pure reparameterisation — the map rescales `Kp` and `Ki` together in physical units, so `e_ss = (dI/dt)/Ki` is invariant. No free lunch |
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

**The 1:30 circulation bump is a free fan step on every real roast.** 64 -> 60 at
400 g, 5-8 % of heat against 0.4-1.5 % noise, and `HT` is recorded from v0.19.0
on. It is messier than a flat-inlet step — BT and SV are both moving — but the
2 s response means a ±10 s window is nearly all fan. Averaged over a few normal
roasts it is an independent read on the loaded slope for no beans at all.

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

**Roast 50 (2026-09-06) took a run at this from a different direction and it
changes the design rather than closing it** — state-history.md § Roast 50. It
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
  (`tools/analysis/charge_dip.py`, `phi` 0.658 at 400 g), not from roast 50.
- **The cheapest outstanding measurement is a repeat of roast 50's *warm* arm
  with a burst.** Only the frozen arm got one, so there is one bed reading and
  not two, which is most of why its joint fit is under-determined. One preheat,
  no beans consumed, no roast.

**Then run the pair.** Two 400 g batches of the same lot, everything else held
identical, one straight from the freezer and one equilibrated at room
temperature for >= 12 h. Roast 49 is already a usable warm arm, so if only one
batch can be spared, **make it the frozen one** and pair it against roast 49 —
but a deliberate pair is worth much more, because roast 49's preheat was 28 degC
hotter than the group's and that had to be corrected for rather than avoided.

What has to be held fixed, and why each one:

- **`greens_temp` recorded on both.** Probe the bean mass, not the air, and enter
  it in Roast Properties. It is `0.0` on all of roasts 43-50, which is the only
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
break. It also carries the one open disagreement: roast 50's still-air fit wants
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
2. **Backgrounds generated from (mass, greens temp)** — step 1b generalised from
   one authored `profile_004` to a computed dip. This is what removes the
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
