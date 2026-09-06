# state-plan — planned work and phase specifications

> Companion to [state-current.md](state-current.md) (what is active now) and
> [state-archive.md](state-archive.md) (what is done, and the review findings
> these phases answer). Findings are referenced as F-numbers from the archive.

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

### Roast 40 (2026-09-02) — first cascade run, and the gains it produced

First live run. `airRoaster_40.alog` (in ~/Documents/artisan) with background
`artisan/profile_001.alog`. **The cascade ran correctly — the failure was
tuning, not configuration.** Replaying the recorded BT error through the PID
with the as-shipped gains reproduces the measured inlet to within ~5 degC for
the whole roast, which is the proof that the plumbing did what it was told:

| t | err (target-BT) | P | I | sim inlet | measured |
|---|---|---|---|---|---|
| 1:30 | +10.9 | 27.3 | 1.5 | 171.9 | 177.0 |
| 3:00 | +14.0 | 34.9 | 4.8 | 191.5 | 196.2 |
| 4:30 | +18.6 | 46.5 | 9.3 | 220.4 | 224.2 |
| 6:00 | +17.0 | 42.5 | **14.2** | 222.0 | 228.5 |

**`Ki = 0.003` was 10-20x too small.** After six minutes the integrator had
contributed 14 duty out of ~60, so the loop ran on proportional action alone —
and a P-only loop needs a standing error to produce output. It settled at the
error required to hold ~228 degC inlet: about **+17 degC of BT deficit for the
entire roast**. BT never caught the target; DROP came at 8:02 against the
background's 7:11.

**The structural reason, which the original gain estimate missed:** the outer
loop's output is an *absolute setpoint*, so the integrator must supply the whole
operating point (~228 degC of inlet), not merely trim it. The firmware's inner
loop has `feedforward(sv, fanLevel)` for exactly that job; Artisan's software
PID has no feedforward term, so Ki has to do all of it. The starting gains were
sized as if for a trim loop.

Two further readings from the log:

- **Not a plant limit.** The inlet reached 300.2 degC at 7:00, so the 228 degC
  mid-roast plateau was the commanded setpoint, not the roaster running out of
  heat.
- **The loop backed off exactly when it should not.** At TP (0:30) target and
  actual both read 52.2 degC, so error was ~0, output fell to the floor and the
  measured inlet dropped to 124 degC. The roast spent the next seven minutes
  climbing out of that hole. This is the direct argument for raising the floor.

Mid-roast the operator raised `pidKp` to 8.5 and unchecked
`positiveTargetRangeLimit`. The Kp change is what produced the visible control
effort (at err ~16 that is 136 duty, saturating to 300 degC) but it was already
ringing — inlet went 300 -> 189 -> 236 over the following minute. Unchecking the
range limit is the more serious of the two: it reverts `heat_min` to the
slider's own minimum of 0, so a low PID output commands `INLET 0`, which the
firmware reads as *disengage* — manual, heat 0, inner integrator reset. That is
precisely the hazard § The floor exists to prevent. It did not trigger (output
never got that low) but it was live for the last 90 s. Both were reverted.

**Gains after roast 40** (in duty units per degC of BT error; with the 170-300
subrange, 1 duty unit = 1.3 degC of inlet SV):

| | roast 40 | now |
|---|---|---|
| `pidKp` | 2.5 (raised to 8.5 mid-roast) | **3.0** |
| `pidKi` | 0.003 | **0.02** |
| `positiveTargetMin` | 120 | **170** |
| `svLookahead` | 0 | **20 s** |

Raising the floor to 170 degC is a crude feedforward: duty 0 becomes a working
inlet temperature, so the integrator covers ~40 duty instead of ~60 and the TP
collapse cannot recur. `duty_filter` stays 1 (enabled; it is a boolean,
`int(dutyFilterFlag.isChecked())`, pid_dialogs.py:1639). `dutyMin`/`dutyMax`
stay 0/100 — they are duty percentages and are *not* the floor mechanism.

**Caveat on Ki = 0.02**: the replay above is open-loop against the *recorded*
error. Once the loop actually corrects, the error shrinks and the integral stops
growing, so overshoot cannot be bounded from this data. 0.02 is a deliberate
first step, not a computed optimum.

**What the next run needs**: the `.alog` carries no firmware telemetry, so heat
level and control mode are invisible to this analysis and it cannot be shown
whether the inner loop ever saturated. Capture a dashboard CSV alongside the
next roast and run both through `downsample_logs.py`.

### Roast 41 (2026-09-02, 23:15 UTC) — inner loop validated, outer loop ringing

Dashboard telemetry only (`airRoaster_data_2026-09-02-23-27-01.csv`; no .alog
captured, so the background target and the outer-loop error are not
reconstructable). A separate, later roast — it starts 28.5 min after roast 40's
charge epoch and reaches BT 205.5 vs 197.4. Ran with the floor still at 120,
`positiveTargetRangeLimit` re-checked and `duty_filter` on. Artisan's gains are
not in this file; `airRoaster_41.alog` later confirmed `pidKp` was still 8.5.

**The inner loop is not the limitation — this closes the open question.** On the
SV 150 preheat plateau (1:30-2:05) the tracking error is mean +0.0 degC,
**rms 0.3 degC**, max +1.2. Over the whole closed-loop span (0:38-10:11) mean
-0.7, rms 8.5, with the rms entirely from transients (max -102 degC at 2:06, the
charge). Heat reached 100% for **16 s total** across 9.5 min and never hit 0.
One clean engage/disengage, no mode chatter. The firmware tracks whatever the
outer loop asks, with headroom.

**Root cause: integral windup against a one-sided integrator** (established
2026-09-02 once `airRoaster_41.alog` was available; the ringing below is a
symptom, not the fault). The alog confirms `pidKp=8.5`, `pidKi=0.003`,
`svLookahead=0`, background `profile_001.alog`, `pidSource=1`.

BT ran *above* the background target for the entire roast — every milestone came
early (DRYe 2:48 vs 3:00, FCs 5:56 vs 6:20, DROP 6:31 vs 7:11) — so the error was
**negative** (-2 to -4 degC) and a healthy loop would have been backing off.
Instead SV sat at 240-250 degC. Solving `duty = Kp*err + I` with the real error
recovers the integral term:

| tau | err | P = 8.5*err | duty | required I |
|---|---|---|---|---|
| 0:40 | -10.5 | -89.3 | 0.0 | **89.3** |
| 2:00 | -4.0 | -33.8 | 53.6 | **87.3** |
| 4:00 | -2.4 | -20.4 | 70.9 | **91.3** |
| 6:00 | -3.5 | -29.7 | 64.8 | **94.5** |

The integrator sat at **83-95 the whole roast**, against a clamp of **[0, 100]**:
`_calculate_integral_limits` sets `integral_min = 0.0` whenever `outMin >= 0`,
and `integral_max` stays 100 because `beta = pidPsetpointWeight = 1` zeroes the
adjustment term (pid.py:43-57, 377-382). Two independent derivations agree — the
0:40 row comes from the output hitting its floor, the others from mid-roast
setpoints.

Pinned near the ceiling with no way to unwind at Ki=0.003, the only thing able to
reduce output was a large negative P term. **That is why Kp=8.5 appeared to give
control effort**: with I railed, P was the only actuator left.

**Mirror image of roast 40.** There I ~ 14 and the loop could not push up; here
I ~ 90 and it could not come down. One root cause: at Ki=0.003 the integrator is
far too slow to be the operating-point supplier, so it parks wherever history
left it and P does all the work. This is the strongest argument for the Ki raise.

**Corrected 2026-09-03 — the earlier attribution was wrong.** This section
previously read *"Artisan's software PID keeps integrating while switched off"*
and blamed the manual 150 degC preheat. That mechanism does not exist at
`beta = 1`, and it could not have produced 89 in any case. The real path is
back-calculation at the **low** clamp — a path with no `Ki` in it
(§ The mechanism the earlier notes missed).

**1. The integrator cannot wind while the PID is off — not in this config.**
`update()` opens with a bumpless-transfer snap:

```python
if i is not None and not self.isActive():
    # bumpless transfer
    self.target = i                      # pid.py:406-408
```

While inactive the target is slammed to the PV on *every* sample, so `err = 0`
identically and `Iterm += Ki*err*dt` adds exactly zero. With `beta = 1` the P
term is `Kp*(beta*target - i) = 0`; with `Kd = 0` the D term is 0; so
`output = Iterm`, which sits inside `[0, 100]` and never clamps, so
back-calculation does not fire either. **`Iterm` is frozen while off, not
growing.** The two facts the old text leaned on are individually true and
jointly harmless: `update()` does run regardless of `pidActive` (canvas.py:5016;
the `if self.active:` guard at pid.py:480 gates only *dispatch* of the duty),
and the SV does keep updating in `svMode=2` (canvas.py:5191) — but the snap
overwrites that SV before the error is formed.

*The caveat that makes this config-specific.* With `beta < 1` the P term while
off is `Kp*(beta-1)*PV` — at `beta=0.5, Kp=8.5, PV=150` that is **-637** — and
with `Kd > 0` the D term while off is `-Kd*RoR` (gamma=0 makes the snapped
target drop out). Either rails the output at the low clamp, and back-calculation
then drives `Iterm` **up** while the PID is off, to the `applyIntegralLimits`
cap. The freeze guarantee holds only while **`beta = 1` and `Kd = 0`**, which is
the committed config (`pidPsetpointWeight=1.0` confirmed in both
`airRoaster_41.alog` and `airRoaster_44.alog`). Revisit if either changes —
and note the `.alog` does **not** record `pidKd` at all, only `pidKd1`/`pidKd2`.

**2. `Ki = 0.003` is far too slow to have built 89 anyway.** At `err = +10` the
Ki path supplies `0.003*10 = 0.03` duty/s — about 50 minutes to reach 89.
Whatever filled the integrator was not integration.

**What actually filled it: back-calculation at the output floor.** The 0:40 row
in the table above *is* the floor — `err = -10.5`, `duty = 0.0`. With
`Pterm = -89.3` the unclamped output is -89.3, clamped to 0, so
`excess = -89.3` and `Iterm -= 0.5*excess` drives `Iterm` **up**, converging
geometrically on `Iterm = -Pterm = Kp*|err| = 89.3` — the derived value,
exactly. Same mechanism, same arithmetic as the roast 44 charge-dip re-seed
(`3 * 8.4 = 25` against a measured 24.6). It simply had not been found when this
section was first written.

**Once there it drains only at `Ki*err`**: at Ki=0.003 with err ~ -3 that is
0.009/s, roughly three hours to unwind. **That asymmetry — a `Kp`-scaled fill in
seconds, a `Ki`-scaled drain over hours — is the actual defect**, and it is a
further argument for the Ki raise. `pidIWP`'s conditional integration caps the
*Ki* path at `P + I ~ 100` (pid.py:296) but is not what put the 89 there.

**The only thing that clears Iterm** is `confSoftwarePID(reset=True)` ->
`pid.reset()` -> `init()` -> `Iterm = 0.0` (pid_control.py:1472, pid.py:498,
532). It is called from exactly one place: `OnMonitor()`, **the ON button**
(canvas.py:13439). Everything else leaves it alone:

| path | clears Iterm? |
|---|---|
| monitor **ON** | **yes** — the only one |
| PID ON / `pidOn()` | no — `confSoftwarePID()` with the default `reset=False`, then `setTarget(svValue, init=False)` (pid_control.py:1519-1526); `on()` says so outright: *"we keep the PID running always ... and do not disturb it with an init on switching it active"* (pid.py:335-341) |
| **RESET** | no |
| DROP / `pidOffDROP` | no |
| OK/Apply in the PID dialog | no — `confSoftwarePID()` without `reset` (pid_dialogs.py:1599, 1685) |
| loading a settings file | no |
| `pidSV()`, `pidSVC()`, `p-i-d()` | no — `setSV(..., init=False)`; `setPID()` touches gains only |

There is no `pidReset()` Artisan command and no reset control in the PID dialog.
`Iterm` therefore persists for the whole monitor session.

**Operating procedure (required, not optional):** press **ON** to start
monitoring — that zeroes the integrator — then turn the PID on, preheat under
its control, then CHARGE. **One PID on/off cycle per monitor ON/OFF cycle.**

The trap is **RESET**: it is the natural between-roasts button and it does not
clear `Iterm`, so a second roast started that way inherits whatever the first
left — and `pidOffDROP` guarantees the first ended with the integrator at its
mid-roast value, 55-70. Cycle OFF -> ON between roasts. `pidOnCHARGE` adds no
second cycle: both it (canvas.py:14656) and `pidOn()`'s software branch are
guarded by `not pidActive`, so arming the PID during preheat makes the CHARGE
trigger a no-op. See § PID-driven preheat — which is still the right procedure,
now for the positive reason that it hands the roast an integrator already at the
empty-roaster operating point (~5 duty) rather than at zero, not because an
idle PID would otherwise wind blind.

**The outer loop rings.** SV direction reversals over 15 degC: 2:08 (257->185),
2:09 (185->228), 2:43 (245->123), 3:08 (123->225), 3:36 (225->184), 4:19
(184->228) — swings of +/-50-60 degC at a 30-50 s period through the charge
transient, settling around 4:19, then ringing again 8:46-9:10 (239 -> 286 ->
202 -> 255). Consistent with excessive proportional gain.

**The floor earned its keep, measurably.** SV sat at 120 for 19 s (2:24-2:42),
in the charge dip. With `positiveTargetRangeLimit` unchecked, `heat_min` reverts
to the slider minimum of 0, so the output would instead have commanded
`INLET 0` — firmware to manual at heat 0 with the inner integrator reset, two
and a half minutes into the roast. SV also touched the 300 ceiling for 5 s at
8:41.

**The TP collapse is systematic, not a one-off.** As in roast 40, at turning
point the background target and actual BT converge, error goes to ~0, and a
P-dominated loop drops to its floor. This is the direct evidence for the
`positiveTargetMin` 120 -> 170 raise and `Ki` 0.003 -> 0.02; both target exactly
this failure.

**Separate finding, outside this phase.** `FF` is railed at 100 for essentially
the whole run (range 94-100) while actual heat is ~55%, with the inner
integrator holding -40 to -50 to cancel it. The feedforward is over-predicting
by roughly 2x at these setpoints and fan levels, so it contributes a constant
bias rather than shaping the response — the operating-point job it exists for is
being done by the integrator instead. Stable, not urgent, but worth its own
look.

### PID-driven preheat (operator decision 2026-09-02)

The windup above is fixed at its source by **running the preheat under the PID**
rather than driving the slider by hand, so the integrator always reflects a
closed loop instead of accumulating with its output disconnected.

Artisan supplies the preheat target automatically: before CHARGE, `calcSV`
returns the background profile's **CHARGE BT** (pid_control.py:1687-1740) —
129.4 degC for `profile_001.alog`. No "default temperature" setting is needed.

The operator's manual 150 degC preheat was already calibrated to almost exactly
that. Fitting the preheat segment of roast 41 (SV pinned at 150, empty roaster):

```
dBT/min = -1.375 * BT + 180.2   ->  inlet 150 degC equilibrates BT at 131.0 degC
background CHARGE BT (the pre-CHARGE PID target)   =  129.4 degC
```

So the loop settles near **inlet 148** to hold 129.4.

**This is why the floor came back down to 140.** At `positiveTargetMin=170` the
PID cannot command 148 — it would sit on its floor, drive BT to roughly 148, and
charge ~19 degC hot against a background built for a 129 degC charge. 140 leaves
about 8 degC of room below the preheat operating point for the loop to trim.

**And why Ki went to 0.04.** A PID-driven preheat leaves the integrator at the
*empty-roaster* operating point — about 5 duty — whereas mid-roast needs ~55. The
loop must climb ~50 duty during the roast. At Ki=0.02 with err ~ +10 that takes
~250 s, most of the roast; at 0.04 it is ~125 s. Ki=0.02 was sized for a
wound-up start, which is no longer the starting condition.

**SV slider / SV buttons** (`svSlider=true`, `svButtons=true`, `svSliderMax`
316 -> 250; the "SV Slider"/"SV Buttons" checkboxes in the PID dialog,
pid_dialogs.py:1968-1972). Note **the PID SV is a BT target in this cascade, not
an inlet temperature** — the PID's *output* is the inlet setpoint. The
equivalent of the old manual "preheat at inlet 150" is an SV of ~130, not 150.
The Artisan Command **`pidSV(<n>)`** (main.py:10820) sets it from any event
button or slider; the existing button 9 ("SV off") already uses `pidSV(0)`.

Both are overridden within ~1 s in Follow Background: canvas.py:5184 recomputes
the SV every sample and calls `setSV` whenever it differs, so a manual SV only
sticks in `svMode=0`. For preheat this does not matter — `calcSV` already
returns the background's CHARGE BT automatically. The slider's real value here
is as a **live readout of the BT target** (with `svSlider` true, `setSV` moves
it, pid_control.py:1769-1771), plus a manual escape in Manual SV mode.

**This also removes the reason the floor was raised.** With Ki=0.04 the
integrator is already near 45 by TP (~25 s of large positive error after CHARGE),
putting SV near 210 rather than collapsing onto the floor. Adequate integral
action, not a high floor, is what carries the loop through turning point.

### Roast 42 (2026-09-02, 20:09) — the retune works

First run of the retuned config (`.alog` confirms `pidKp=3.0`, `pidKi=0.04`,
`svLookahead=20` loaded) with a PID-driven preheat. Every failure mode from
roasts 40 and 41 is resolved.

| | roast 40 | roast 41 | roast 42 |
|---|---|---|---|
| outer integral | ~14 (stuck low) | ~90 (railed) | **53-65, settled** |
| tracking error | +17 degC standing | -3 with railed I | **+1.6 ... -0.9** |
| inner-loop rms | - | 8.5 degC | **2.9 degC** |
| heat at 100% | - | 16 s | **0 s** (max 91%) |
| SV reversals >15 degC | - | 12+, +/-50-60 degC | **4**, all in the charge dip |
| rails | floor 19 s | floor 19 s | **floor 8 s**, ceiling never (max 276.9) |

The integrator settles at 53-65 and stays there, carrying the operating point
while P trims within +/-5 duty — exactly the intended division of labour. The
PID-driven preheat landed too: **CHARGE_BT 129.7** against the 129.4 target
(§ PID-driven preheat predicted the loop would settle near inlet 148; it settled
near 153, still trending down at CHARGE).

**Remaining offset is the lookahead, and it is a spec error not a tuning one.**
The roast ran ahead — DRYe 2:36 vs the background's 3:00, DROP 6:21 vs 7:11 —
yet the error against the *lookahead-shifted* target is ~0 from 3:00 onward
(+1.6, +2.6, +1.7, +1.3, +0.3, -0.2, -0.9). `svLookahead=20` targets where the
profile will be in 20 s, so `BT(t) ~ profile(t+20)`: **the roast runs 20 s ahead
by construction**, and on a curve rising ~15 degC/min that is also ~+5 degC of
target at any instant.

Lookahead exists to cancel plant lag. 20 s was chosen before the cascade's
tightness was known; with the inner loop at rms 2.9 degC the effective lag is
near zero, so the lead became a pure time advance. **`svLookahead` is now 0**
(operator decision 2026-09-02).

That change became urgent rather than cosmetic with `profile_002`, because the
background's DROP also bounds the control window — `calcSV` returns None once
`tx + svLookahead > timeB[timeindexB[6]]`, deactivating follow-background. With
a 6:51 DROP and a 20 s lookahead the SV would have stopped updating at **6:31**,
while the lookahead simultaneously pushed the roast ~20 s early, so the loop
would have coasted on a stale target through the end of the roast.
`profile_001`'s 7:11 DROP had 40 s of slack absorbing this; `profile_002` does
not.

Unchanged: `FF` still railed at 100 with the inner integrator at -40 to -50
cancelling it (§ Roast 41, separate finding).

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

### Roast 44 (2026-09-02) — clean validation run; phase complete

First fully clean run: config loaded from the file (alog confirms `pidKp=3.0`,
`pidKi=0.04`, `svLookahead=0`), background `profile_002`, PID-driven preheat, no
mid-roast intervention.

```
CHARGE_BT  128.3   (target = profile_002 CHARGE BT 127.8)
DRYe  3:23  vs profile 3:20      <- 3 seconds
FCs   6:39  vs 6:30
DROP  7:03  vs 6:51   at BT 200.7 vs 201.2
```

Tracking error against the background, converging throughout:
`+0.9, +3.7, +4.0, +3.8, +3.5, +3.0, +2.4, +1.7`.

**DRYe within 3 s of the profile confirms the lookahead diagnosis** — roast 42
with `svLookahead=20` was 24 s early. The residual is a small positive error
(BT ~2-4 degC under the curve mid-roast, finishing ~12 s late) — ordinary
proportional droop, and still shrinking at DROP, so the integrator was still
catching up rather than having settled short. No change made; watch it over a
few more roasts before touching Ki.

**The auto-DROP alarm works** (operator confirmed it fired in roast 43). Roast 44
shows the same signature: BT peaks 201.0 at 7:01, DROP marked 7:03, RoR crosses
-25 at 7:04 — the mark lands just after the peak, where a manual press had
consistently landed *before* it (roast 42: 8 s early; roast 41: ~47 s early).
Margin was ample: minimum RoR in the armed window was **+1.2**, against -10.4 in
roast 43 and -4.9/+5.4 in roasts 41/42. That spread (-10.4 to +5.4) is the
number to watch; a roast that dips near -25 while still roasting would
false-trigger.

**Control settings verified against the PID dialog** (2026-09-02): Input BT;
Scheduling off; kp 3.000 / ki 0.040 / kd 0.000; Output Positive -> slider
T_inlet with Limit ticked at 140/300, Negative none, Invert off; Mode Back,
Lookahead 0 s, SV slider 0-250; Duty Filter on, Steps 1%, Clamp 100/0 %;
PoE (beta 1.00), DoM (gamma 0.00), derivative filter 0, ILF 1.00, Dlimit 500,
IWP on, IRoC off.

Note the two easily-confused pairs: the **Duty Clamp Max/Min (100/0 %)** are duty
percentages — the original `dutyMin=120` error — while the actual degC floor is
the **Output Limit Min/Max (140/300)**. And with `kd=0`, DoM / gamma /
derivative filter / Dlimit are all inert.
### Roast 44 outer-loop analysis — the droop is integrator-rate-limited (2026-09-02)

**Method.** The outer loop is reconstructed from the two logs.
`airRoaster_44.alog` gives BT and the CHARGE index; `profile_002.alog` gives the
target (CHARGE-aligned, as `timealign` does it, canvas.py:5931-5946 — note it
shifts `timeB` in whole seconds); the firmware CSV gives the commanded `SV`,
which is the PID's output: `duty = (SV - 140) / 1.6`. The CSV is charge-aligned
by cross-correlating its `IN` column against the alog's `Inlet` extra channel —
best offset `roastepoch + 120.5 s`, residual rms 0.96 degC, i.e. `roastepoch` is
the *recording* start and CHARGE sits 119-121 s into it. Then `P = Kp*err` and
`I = duty - P`.

**1. The integrator never settles.** It climbs monotonically for the whole
roast — nothing in roast 44 is a steady state:

| t | 1:15 | 2:00 | 2:45 | 3:30 | 4:15 | 5:15 | 6:00 | 6:45 |
|---|---|---|---|---|---|---|---|---|
| err (degC) | +1.2 | +4.3 | +4.2 | +4.1 | +3.8 | +3.2 | +2.4 | +1.8 |
| Iterm (duty) | 21 | 33 | 45 | 53 | 60 | 65 | 68 | 70 |

`dI/dt` runs 0.10-0.19 duty/s and `e = (dI/dt)/Ki` holds to within 0.2 degC at
every point. **This is the signature of a type-1 loop tracking a ramp**: the
operating point the plant demands keeps rising, only the integrator can supply
it, and the integrator only climbs by integrating error. The error *is* the fuel.

**2. The controlling relation.** Fitting roast 44's body (1:10-6:45) gives a
first-order plant `dBT/dt = 0.0145*(Inlet - BT) - 0.68 + w(t)`, i.e. **tau =
69 s**, with `w(t)` the smoothed residual standing in for drying/exotherm/fan.
Inverting it, the duty required to hold a BT ramp of rate `R` is
`u_req = (BT + 69*R - 93)/1.6`, so

```
du_req/dt = (R + 69*dR/dt) / 1.6          and          e_ss = (du_req/dt) / Ki
```

`Kp does not appear.` Sweeping Kp 2 -> 6 at fixed Ki moves the droop by less
than 0.3 degC while SV ripple goes 1.6 -> 3.4 degC. **Proportional gain cannot
fix this error; only Ki or feedforward can.**

**3. The "12 s lag" is not a lag.** Because `du_req/dt` is proportional to `R`,
the ratio `e/R` is nearly RoR-independent — which is what produced the
near-constant 12 s in the handoff table. But it decomposes as
`(du_req/dBT)/Ki = 0.505/0.04 = 12.6 s`: **it is one over the integrator rate,
not a transport delay.** The real delays in the loop are small and measurable:

| stage | measured |
|---|---|
| inner loop (Inlet vs commanded SV, 1:00-6:45) | best fit **1 s**, rms **0.7 degC** |
| BT smoothing (`curvefilter=3`, weights 1:2:3, canvas.py:4958-4976) | 0.67 s |
| `pid.update()` at canvas.py:5016 runs *before* the SV update at canvas.py:5184 | 1 s |
| plant transport delay (open-loop replay best fit) | **0 s** (2 s already doubles the residual) |

Under 3 s of genuine lag against 12-15 s of apparent lag. The inner loop is
confirmed a non-factor for the third time.

> **Corrected.** That table counts the *instrumentation* delay and misses the
> process: between inlet air temperature and what the BT probe reads sits the
> bean mass, worth ~15-20 s. The "plant transport delay 0 s" row is an artefact
> of a circular fit and is retracted — see § Correction: roast 45's error is the
> loop, not the air. The velocity-error derivation and the roast 44 tuning
> conclusions are unaffected; the *stability margins* quoted later in that
> section are far too optimistic.

**4. A validated simulator.** Artisan's `PID.update()` was reimplemented
faithfully (PoE, conditional integration, back-calculation, `[0, 100*ILF]`
integral limits, the 0.35 Hz first-order duty filter, the 1-sample target
ordering, decay-averaged PV) and run against the fitted plant.

```
open-loop replay (measured SV -> BT):        mean -0.42  rms 0.59  max -1.40 degC
closed-loop replay (Kp 3, Ki 0.04, L 0):     mean -0.13  rms 0.33  max -1.32 degC
```

Every number below is from that simulator. It reproduces roast 44 to a third of
a degree, so differences of a degree between tunings are meaningful.

#### The mechanism the earlier notes missed: back-calculation anti-windup

This also supersedes the roast-41 root cause as first written; see the
correction there.

`_back_calculate_integral` (pid.py:314-333) runs on **every clamped cycle**
whenever `pidIWP` is on — it is not part of the conditional-integration logic
already recorded, it is a second, separate anti-windup:

```python
if abs(output_before_clamp - output_after_clamp) > 0.001:
    excess = output_before_clamp - output_after_clamp
    self.Iterm -= excess * self.back_calculation_factor   # factor = 0.5, hard-coded
    self.Iterm = self.applyIntegralLimits(PV, self.Iterm)
```

At the **low** clamp `excess` is negative, so `Iterm` is driven **up**. The
recursion `I <- 0.5*I + 0.5*(-Pterm)` converges geometrically on
`Iterm = -Pterm = Kp*|err|` (capped at `100*ILF`), halving the residual each
second. Three consequences, all confirmed against roast 44:

- **The charge dip re-seeds the integrator** to `Kp * |worst dip error|`. Roast
  44: worst dip error -8.4 degC, `3 * 8.4 = 25`, measured `Iterm` at 0:45 was
  **24.6**. This is why the loop recovers as well as it does after turning point.
- **Whatever the preheat left in `Iterm` is forgotten** within a few seconds of
  the floor (half per second). Simulating handovers of `Iterm` = 0, 3, 7, 15 and
  30 gives *bit-identical* roasts. The ON-button procedure (§ Roast 41) still
  matters — it protects the **preheat**, where an integrator carried over from a
  previous ON cycle rails the SV and lands the wrong CHARGE_BT — but it does not
  reach into the roast body.
- **It is what makes a large `svLookahead` dangerous** (below). This, not the
  DROP-window truncation, is the binding constraint on lookahead.

#### 1. Proposal, inside the current simple-PID structure

| key | now | proposed | why |
|---|---|---|---|
| `pidKp` | 3.0 | **3.0** unchanged | absent from `e_ss`; raising it only adds ripple |
| `pidKi` | 0.04 | **0.10** | `e_ss = (du_req/dt)/Ki`; 2.5x the integrator rate cuts the droop 2.5x |
| `pidKd` | 0 | **0** unchanged | see below |
| `svLookahead` | 0 | **3** | ramp feedforward; free in stability terms |
| `pidIlimitFactor` | 1.0 | **1.0** unchanged | `Iterm` must reach ~70; anything below 0.75 clips the operating point |
| `pidIWP` | on | **on** unchanged | the charge-dip re-seed above depends on it |
| `duty_filter` | 1 | **1** unchanged | measured effect on tracking: 0.00 degC; keep for wire noise |
| `dutySteps` | 1 | **1** unchanged | the value is fractional; this only sets cadence, and `force_duty=3` (pid.py:197) already guarantees an update every 3 s |
| `sv_filter` | 0 | **0** unchanged | the background is a Designer curve, already smooth; it would cost 1.33 s of the lookahead |
| `pidDlimit` | 500 | **500** unchanged | inert at `Kd=0`; note it limits `derror` in **degC/s**, before multiplication by Kd (pid.py:265-267), so 500 is effectively infinite against a BT RoR of ~1 degC/s |

Predicted against `profile_002` (target DRYe 3:20, DROP 6:51):

| | roast 44 as run | proposed |
|---|---|---|
| tracking error, 2:00-6:50 | mean **+3.42**, rms 3.51 | mean **+0.62**, rms 0.79 |
| worst error after 1:15 | +4.50 | +1.68 / -0.18 |
| DRYe | 3:33 *(measured 3:24)* | **3:22** |
| DROP | 7:13 *(measured 7:04)* | **6:54** |
| SV max / ripple | 253.8 / 2.1 | 254.2 / 2.7 |

**Is more Ki the right lever for velocity lag?** Yes — it is the *only* lever
inside a plain PID, because `e_ss = (du_req/dt)/Ki` and neither Kp nor Kd
appears in it. Sweep at `L=0`:

| `pidKi` | 0.04 | 0.06 | 0.08 | 0.10 | 0.12 | 0.16 | 0.24 |
|---|---|---|---|---|---|---|---|
| mean error (degC) | +3.42 | +2.46 | +1.88 | +1.50 | +1.23 | +0.90 | +0.60 |
| rms | 3.51 | 2.63 | 2.07 | 1.69 | 1.41 | 1.05 | 0.71 |
| rms at +10 s deadtime | 3.53 | 2.60 | 2.02 | 1.65 | 1.49 | 2.07 | **8.02** |
| SV ripple at +10 s deadtime | 3.1 | 3.7 | 4.4 | 5.3 | 6.8 | 11.7 | **43.1** |

Pure-Ki tuning is monotone and never overshoots — the residual is one-sided all
the way to Ki 0.24. What it costs is **stability margin**: the plant's measured
deadtime is ~0 s, but batch size, bean moisture and fan setting all move the
plant, so the +10 s column is the margin being spent. Ki 0.10 keeps a factor of
two in hand; 0.24 does not.

**What it costs on the charge transient: nothing.** This is the useful surprise.
Through the dip the output is on its floor with a negative error, and
`_should_integrate` (pid.py:286) blocks Ki-driven integration in exactly
that case (`output_before_clamp < outMin and error < 0`), while back-calculation
takes over and drives `Iterm` to `Kp*|err|` — a path with **no Ki in it**. The
simulated handover value only moves from 20.1 (Ki 0.04) to 22.8 (Ki 0.10), and
floor time from 19 s to 26 s. The BT 128 -> 64 plunge is absorbed by the floor,
not by the integrator.

**`svLookahead` as ramp feedforward.** With lead `L` the target becomes
`tgt(t) + L*R`, so the standing error is cancelled when `L = e_ss/R =
(du_req/dBT)/Ki` — the same 12.6 s, and *RoR-independent*, which is why one
constant works across the whole curve. Lookahead is **pure feedforward: it
changes the reference, not the loop gain, so it costs no stability margin at
all.** That makes the handoff's "natural value is the loop's own lag (~12 s)"
arithmetically right and operationally wrong, for a reason that only shows up
in the source:

| `svLookahead` | 0 | 2 | 3 | **4** | 5 | 6 | 9 | 12 |
|---|---|---|---|---|---|---|---|---|
| worst charge-dip error (degC) | -10.0 | -11.2 | -15.9 | -20.4 | -24.7 | -28.7 | -39.7 | -49.4 |
| `Iterm` handed to the roast | 20.1 | 17.3 | 16.4 | 22.8 | **33.3** | **43.6** | **60.8** | **70.3** |
| worst *early* error, 1:15 on | +3.11 | +2.15 | +1.68 | -1.60 | **-4.61** | -8.3 | -13.8 | -19.8 |

The background falls at up to **5.5 degC/s** through the charge dip, so every
second of lead adds ~4 degC to the dip error, back-calculation converts that
into integrator preload, and past `L=4` the roast starts with the integrator
already near its mid-roast value and **overshoots the profile by 5-20 degC in
the first two minutes**. `L=3` sits below the cliff with margin; `L=4` is the
best single number on paper (mean +0.31, rms 0.48) but is one second from it.
**Take 3.**

The truncation cost the handoff asked about is real but negligible at this
value. `calcSV` returns `None` once `tx + svLookahead > timeB[timeindexB[6]]`
(pid_control.py:1703), i.e. at 6:48 for a 6:51 background DROP, and canvas.py:5184
only calls `setSV` when `sv is not None`, so **the target simply freezes at its
last value — which is `tgt(6:48 + 3) = tgt(6:51) = 201.2 degC, the profile's DROP
BT.** The loop spends its last ~5 s holding exactly the right final target. At
`L=12` the freeze would start at 6:39 with 25 s to coast; even that is benign
for the same reason. The lookahead cliff, not the window, is what caps `L`.

**Why derivative is not useful here.**

- **DoM (`gamma=0`, current).** `_calculate_derivative` (pid.py:249-259) computes
  `derror = ((gamma*SP - PV) - (gamma*lastSP - lastPV))/dt`, which at `gamma=0`
  is `-dPV/dt = -RoR`. On a rising PV that is a **constant brake proportional to
  the ramp**: at RoR 16 degC/min and Artisan's default `Kd=20` it is -5.3 duty
  = -8.5 degC of inlet, held all roast, which the integrator must cancel — so it
  *raises* `du_req` and makes the velocity error worse, not better. The
  simulator does show `Kd=20` DoM improving rms 0.79 -> 0.44, but the improvement
  comes entirely from a larger charge-dip preload (I0 16.4 -> 26.4), not from D's
  action, and with 0.35 degC of BT noise the SV ripple goes 2.8 -> 6.0 and mean
  |dSV| triples. Not a trade worth making.
- **DoE (`gamma=1`).** `derror` becomes `d(err)/dt`, which is **zero in steady
  ramp-following** — D contributes nothing to the standing error by
  construction. It is genuine damping, and it does buy margin: at Ki 0.24 with
  10 s of deadtime, `Kd=30` DoE turns rms 7.84 (oscillating, ripple 43) into rms
  0.47. But it also differentiates BT noise, and at `Kd=20` DoE the charge dip
  preloads `Iterm` to 63.9 and the roast undershoots by 8.6 degC. **D is the
  right tool only if you want Ki above ~0.15, and lookahead gets the same
  tracking without it.** Keep `Kd=0`.

#### 2. Artisan's other control options, and the alternative strategy

Every row checked in source; the middle column is the question the brief asks —
does it address **ramp-following lag specifically**.

| option | addresses ramp lag? | finding |
|---|---|---|
| **Gain scheduling** (`pidGainScheduling`, `...SV`, `...Quadratic`, `pidSchedule0/1/2`, Kp/Ki/Kd sets 1 and 2) | **yes, indirectly** | `getParameter` (pid.py:370-387) fits a line through `(Schedule0, Kp)` and `(Schedule1, Kp1)` — the *base* gains are the value at `Schedule0` — evaluates it at `self.target` when `pidGainSchedulingSV` (the default), and clamps to `[min, max]` of the two. Since `e_ss = (du_req/dt)/Ki` and `du_req/dt` is not constant over the roast, a Ki schedule can flatten the error where a single Ki cannot. Simulated, `Ki 0.18 @ SV 130 -> 0.06 @ SV 200` gives mean **+0.23**, rms **0.31**, max +0.54, min -0.57 — better than any flat Ki. The reverse slope is worse (rms 1.37), so the direction matters. **Gotcha: one schedule serves all three gains**, so `pidKp1` must be set equal to `pidKp` and `pidKd1` to `pidKd` or Kp and Kd get scheduled too. |
| **PoE/PoM, `beta`** (`pidPsetpointWeight`) | **yes — and the wrong way** | `Pterm = Kp*(beta*SP - PV)`. Correcting the first version of this row: beta does *not* merely shift the offset, it enters the velocity error directly as `e_ss = [du_req/dt + Kp*(1-beta)*R] / Ki`, so **any beta below 1 makes ramp lag worse**, and beta above 1 — the direction that would help — is blocked by the integral limits. Derivation, sweep and source in § Proportional on Measurement below. **Must stay 1.0.** |
| **DoE/DoM, `gamma`** (`pidDsetpointWeight`) | **no** | Inert at `Kd=0`; see above for both settings. |
| **`pidDlimit`, `derivative_filter`** | **no** | Inert at `Kd=0`. `Dlimit` clamps `derror` in degC/s **before** the Kd multiply (pid.py:265-267) — 500 is unreachable. `derivative_filter` is a boolean, not a level: `_calculate_derivative` only tests `> 0`, and the filter is a fixed 0.1 Hz first-order lowpass (pid.py:640-644). |
| **`pidIRoC` + `pidIRoCthreshold`** | **no, and it would misfire** | `_handle_setpoint_change_integral` (pid.py:301-311) compares the **per-sample** target change, not a cumulative one. The background's largest per-sample step is **5.48 degC** (in the charge dip), so at threshold 30 it can never fire — the setting is inert, correctly. Lowering the threshold to reach it would zero `Iterm` in the middle of the charge dip, destroying the useful re-seed. Leave off. |
| **`pidIlimitFactor` (ILF)** | **no** | Caps `Iterm` at `100*ILF` (pid.py:43). `Iterm` legitimately reaches ~70 mid-roast, so anything below ~0.75 would clip the operating point and reintroduce roast 40's standing deficit. It is a safety cap, not a tuning knob. Keep 1.0. |
| **`pidIWP`** | **no, but load-bearing** | Two mechanisms in one flag: conditional integration *and* back-calculation. Turning it off drains `Iterm` to 0 through the charge dip (simulated I0 = 0.0) and costs 1.6 degC of early tracking. **Keep on.** |
| **`sv_filter` / `duty_filter`** | **no** | `smooth_sv` (pid_control.py:1643-1655) is a 5-tap decay average = **1.33 s of group delay on the target**, i.e. it subtracts 1.33 s from the effective lookahead. `duty_filter` is a 0.35 Hz first-order lowpass on P+I+D, ~0.25 s — measurably nil (rms 0.48 either way). Useful only as a way to blunt the charge dip if a larger lookahead were ever wanted. |
| **Ramp/Soak (`svMode=1`)** vs Follow Background | **no** | `svRampSoak` (pid_control.py:1593-1638) is 8 linear ramp/soak segments starting from `source_reading_pidON`. Same type-1 loop, same velocity error, and it loses charge alignment, the Designer curve's shape, and any representation of the charge dip. Its only structural advantage — no DROP-bounded control window — is worth nothing at `L=3`. **Stay on Follow Background.** |
| **Outer loop on BT RoR** | would remove it, but **not reachable in configuration** | `getCurveNames` (pid_dialogs.py:1251-1258) populates the Input list with ET, BT and the *extra device channel names* only — delta/RoR curves are not offered, and `canvas.py:5000-5015` reads `pidSource` from the raw channel arrays. Controlling RoR needs the firmware to publish RoR as an extra channel (out of scope), plus an RoR background curve for `backgroundXTat`. And on its own it is the wrong control: zero *rate* error leaves BT *position* free to drift, so it would need a BT trim on top — a three-level cascade. Not now. |

**Recommended strategy: keep the structure, take the two changes above, then a
Ki gain schedule as a second step.**

The cascade's architecture is not the problem — a validated simulator says the
existing structure reaches mean +0.6 degC and DRYe within 2 s of the profile
with two number changes. Nothing in the alternatives justifies restructuring.
The one option that beats a flat retune is gain scheduling on Ki, and it is a
refinement of the same loop, not a replacement.

*Step one (one roast).* `pidKi = 0.10`, `svLookahead = 3`, everything else
untouched.

*Step two, only if step one validates and the residual still bothers.*
`pidGainScheduling=true`, `pidGainSchedulingSV=true`,
`pidGainSchedulingQuadratic=false`, `pidSchedule0=130`, `pidSchedule1=200`,
`pidKi=0.18`, `pidKi1=0.06`, **`pidKp1=3.0`**, **`pidKd1=0`**.

**Risks.** (1) Ki 0.10 spends stability margin: the failure mode is SV ringing
with a 30-60 s period, as in roast 41 — visible immediately in the SV trace, and
the CONTROL button is the escape. (2) `svLookahead` is 1 s from a cliff; if the
background's charge dip is ever re-authored steeper, re-check the table above
before keeping 3. (3) The simulator's plant is fitted to *one* roast at one batch
size; ±25% plant gain, ±30% tau, +10 s deadtime and 1.0 degC of BT noise were all
tested and the proposal holds (worst case mean +0.72, rms 0.94, max +4.60), but a
much smaller or larger charge is outside that envelope.

**How to validate in a single roast.** Same procedure as roast 44 — ON, PID on,
PID-driven preheat, CHARGE, no intervention — with the dashboard CSV captured
alongside the `.alog` (the CSV is what carries `SV`; without it the outer loop
cannot be reconstructed). Then check, in order:

1. **DRYe within ~5 s of 3:20 and DROP within ~5 s of 6:51.** These are the
   headline numbers; roast 44 was +4 s and +13 s.
2. **Tracking error under +1.5 degC from 2:00 on**, and *not* one-sided —
   if it is still monotone positive, Ki is still short.
3. **`Iterm` reaching ~70 by 6:45 but flattening**, from `I = (SV-140)/1.6 - 3*err`.
   Still climbing linearly at DROP means the loop never caught up.
4. **`Iterm` at 0:45 near 16** (`Kp * |worst dip error|` at `L=3`). Much above 30
   means the lookahead cliff was hit and the early roast will overshoot.
5. **No SV direction reversal over 15 degC after 2:00.** That is the Ki-too-high
   signature.
6. Inner loop unchanged: heat below 100%, tracking rms of a few degC.

Failure responses, in order of preference: overshoot early -> `svLookahead` to 2;
ringing -> `pidKi` to 0.07; still droopy and one-sided -> `pidKi` to 0.13 before
touching anything else.
### Roast 45 (2026-09-02, 21:53) — step 1 applied; the droop is gone

> **Partly superseded.** The tracking findings below stand. The attribution of
> the error *shape* to the air schedule, and the Ki 0.15 step-2 recommendation,
> are **retracted** — see § Correction: roast 45's error is the loop, not the
> air. Note also that this roast ran at **Ki 0.10**, not the 0.15 the re-saved
> alog now records.

First run of `pidKi=0.10`, `svLookahead=3` (both confirmed in the alog), same
background `profile_002`, same procedure. Operator's reading: "better again but
still slow and wandering." Both halves have answers, and neither is the outer
loop's gain.

**Read the marks with care — they are not profile crossings.** DRYe and FCs are
fired by `autoDRY`/`autoFCs` on the fixed BT thresholds in the Phases dialog
(`phases=[38, 149, 196, 218]`, canvas.py:5158-5164), while `profile_002`'s own
DRYe sits at **BT 152.0** and its FCs at **BT 197.9**. Comparing mark time to
mark time therefore compares two different temperatures and always reads early.
**The valid yardstick is the time to reach the same BT:**

| BT | 100 | 120 | 140 | 150 | 160 | 170 | 180 | 190 | 196.5 |
|---|---|---|---|---|---|---|---|---|---|
| profile_002 | 1:31 | 2:03 | 2:46 | 3:14 | 3:45 | 4:20 | 4:59 | 5:46 | 6:21 |
| roast 45 | 1:31 | 2:08 | 2:48 | 3:14 | 3:45 | 4:23 | 5:06 | 5:49 | 6:19 |
| behind | 0 s | +5 s | +2 s | 0 s | 0 s | +3 s | +7 s | +4 s | -2 s |

**Roast 45 is on the curve to within 0-7 s all the way through**, against roast
44's uniform 11 s. (Roast 44 on the same yardstick: BT 149.2 at 3:23 vs the
profile's 3:12; BT 197.7 at 6:39 vs 6:29.) Step 1 did what the model said it
would; the prediction "DRYe 3:22" was a *BT-152.0 crossing*, and roast 45
crossed 152.0 at 3:20.

```
tracking error vs the profile, 1:10-6:45   mean +0.85  rms 1.19  range -0.43 .. +2.77
  in the quiet windows (3:10-4:20, 5:40-6:40)                    mean +0.19
inner loop (Inlet vs commanded SV, 1:00-6:45)   mean -0.12  rms 0.91 degC
heat 46-59% throughout — never saturated, never floored; SV never touched 140 or 300
SV ripple vs a 61 s mean, 2:30-6:30            max 4.5  rms 1.19 degC
SV direction reversals over 10 degC after 1:00  none
```

**The steady droop is essentially gone.** +0.19 degC in the quiet windows,
against +3.4 degC in roast 44. `Iterm` still climbs (44.5 at 3:30 -> 65.4 at
6:30, 0.116 duty/s), so `e_ss = 0.116/0.10 = 1.16 degC` against the
lookahead-shifted target, of which 3 s of lead returns ~0.7 degC — leaving the
~0.5 degC that the quiet windows show. The mechanism from § Roast 44 outer-loop
analysis is intact and now nearly exhausted.

**The "wandering" is the operator's own air schedule.** Refitting the plant on
roast 45 with a fan term halves the model residual (3.59 -> 1.98 degC/min):

```
dBT/dt = (0.00970 + 0.02877*(fan-60)/60) * (Inlet - BT) - 0.274 + w(t)
      => plant gain moves ~49% per 10 fan units
```

So the `65 -> 62 -> 60` cut at **1:31-1:34** removes about a **quarter of the
plant gain in three seconds**, and the `60 -> 59 -> 58` cut at **4:26-4:32**
another tenth. The error follows each one:

| | air step | error before | peak | recovered |
|---|---|---|---|---|
| first | 1:31, 5 units | -0.24 at 1:30 | **+2.59 at 2:10** | ~0 by 3:20 |
| second | 4:26, 2 units | +0.83 at 4:30 | **+1.50 at 5:20** | -0.40 by 6:30 |

Amplitude is linear in step size (0.56 and 0.45 degC per fan unit), each
excursion is locked to a step, and the error is flat between them (+0.29 to
+0.86 across 3:10-4:20). **That is load-disturbance rejection, not a limit
cycle** — confirmed by the absence of any ringing signature above.

The first cut also lands at the worst possible moment: 1:31 is the steepest part
of the curve (background RoR ~46 degC/min) with the integrator still climbing
hard out of the charge dip.

#### What is left, and what it is worth

A roast-45 simulator (same construction as § Roast 44 outer-loop analysis, with
the fan term added) reproduces the roast at rms 1.09 degC and under-predicts the
two bumps by ~25%, so the ranking below is trustworthy and the absolute numbers
are indicative.

| change | quiet droop | bump 1 | bump 2 | rms | ripple at +10 s deadtime |
|---|---|---|---|---|---|
| **as run** (Ki 0.10) | +0.04 | +2.08 | +1.25 | 1.11 | 2.3 |
| Ki 0.13 | -0.25 | +1.81 | +0.90 | 0.89 | 2.9 |
| **Ki 0.16** | -0.36 | +1.66 | +0.63 | 0.76 | 5.3 |
| Ki 0.20 | -0.39 | +1.43 | +0.37 | 0.67 | **12.2** |
| Ki 0.26 | -0.41 | +0.99 | +0.16 | 0.61 | **34.5** |
| air cut moved to 0:25 (Ki 0.10) | +0.03 | **+1.31** | +1.20 | **0.72** | 1.3 |
| air cut ramped over 60 s (Ki 0.10) | +0.27 | +2.11 | +1.21 | 1.06 | 2.7 |
| no air changes at all (Ki 0.10) | +0.10 | +0.83 | +0.71 | 0.53 | 1.2 |
| Ki 0.16 + air cut ramped | -0.28 | +1.07 | +0.65 | **0.57** | — |

Reading it:

- **The air schedule is now the dominant error term.** Removing it entirely
  takes rms from 1.11 to 0.53 — more than any gain change achieves.
- **Moving the first cut earlier beats every Ki value**, at zero stability cost.
  In the charge dip the output is on its floor and the back-calculation re-seed
  (§ Roast 44 outer-loop analysis) absorbs the gain change for free, whereas at
  1:31 the loop has to find a new operating point during its steepest climb.
  **But this is a real roast change, not a control tweak** — airflow drives
  drying rate and chaff clearance, so whether a 5-unit cut a minute earlier is
  acceptable is the operator's judgement, not the model's.
- **Ramping the cut over 60 s barely helps the bump** (2.11 vs 2.08). The
  disturbance is a *gain* change, not a transient; the loop has to relocate its
  operating point either way. It does trim the time-behind (3.3 s vs 5.1 s).
- **Ki 0.16 is the last value with margin.** 0.20 triples the ripple under a
  10 s deadtime stress and 0.26 breaks — the same wall found in roast 44's sweep,
  now confirmed against a second roast's plant fit.

#### Step 2

**`pidKi` 0.10 -> 0.15. Keep `svLookahead` at 3. Nothing else in the PID.**
Expected: quiet droop stays under 0.5 degC, first bump 2.6 -> ~1.8 degC,
time-behind at 5:00 from ~5 s to ~3 s, ripple unchanged at the real plant's
~0 s deadtime.

Separately, and as a roast decision rather than a control one, **one of**:

1. Move the `65 -> 60` air cut from 1:31 into the charge dip (~0:25). Largest
   single improvement, free in stability terms, but it changes the roast.
2. Leave the air schedule alone and **re-author the background from a real roast
   instead of the Designer.** The Designer curve contains no trace of the air
   schedule, so the loop is being asked to hold a shape the airflow is actively
   removing; a background taken from a good roast with the same air moves puts
   the flat spot *in the target*, and the disturbance stops being an error at
   all. Cheapest option that changes nothing about the roast itself.
3. Accept a ~2 degC / ~8 s excursion at 2:00 as the cost of the air schedule.

Do **not** chase the bumps with more Ki past 0.16 — the sweep shows what that
buys and what it costs.

#### The Ki 0.15-0.20 band, examined (operator question 2026-09-02)

Nothing qualitative happens anywhere in that band — no ringing onset, no new
overshoot, SV traces nearly identical after 2:30. Tracking improves monotonically
and modestly:

| `pidKi` | 0.10 | 0.12 | 0.14 | **0.15** | 0.16 | 0.18 | **0.20** | 0.22 | 0.24 |
|---|---|---|---|---|---|---|---|---|---|
| quiet droop (degC) | +0.04 | -0.19 | -0.30 | **-0.33** | -0.36 | -0.38 | **-0.39** | -0.39 | -0.40 |
| first air bump (degC) | +2.08 | +1.90 | +1.74 | **+1.70** | +1.66 | +1.56 | **+1.43** | +1.28 | +1.14 |
| rms (degC) | 1.11 | 0.95 | 0.84 | **0.80** | 0.76 | 0.70 | **0.67** | 0.64 | 0.62 |
| time behind at 5:00 | +5.1 s | +4.2 s | +3.4 s | **+3.0 s** | +2.7 s | +2.1 s | **+1.6 s** | +1.2 s | +0.9 s |
| SV ripple (nominal) | 2.2 | 2.4 | 2.4 | **2.3** | 2.3 | 2.1 | **1.9** | 2.0 | 2.1 |

**But the error changes character, and it works against the complaint.** At Ki
0.10 the trace is one-sided — BT behind the profile, decaying back to zero after
each air cut. From ~0.14 up it starts crossing zero and the loop **overshoots
after each bump**:

| t | 1:40 | 1:55 | 2:10 | 2:25 | 2:40 | 2:55 | 3:10 | 5:10 | 5:55 | 6:10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Ki 0.10 | +0.36 | +1.62 | +2.06 | +1.92 | +1.30 | +0.52 | -0.06 | +1.25 | +0.33 | -0.15 |
| Ki 0.15 | +1.15 | +1.68 | +1.40 | +0.79 | -0.01 | -0.67 | -0.95 | +0.70 | -0.25 | -0.61 |
| Ki 0.20 | +1.20 | +1.18 | +0.51 | -0.18 | -0.77 | -1.11 | -1.08 | +0.35 | -0.49 | -0.74 |

Peak-to-peak across the first air cut goes **3.35 -> 2.63 -> 2.31 degC** for
Ki 0.10 / 0.15 / 0.20. The *mean* and rms improve substantially; the **swing
barely does — the loop mostly re-centres around the disturbance rather than
rejecting it.** If the objection is "wandering" rather than "slow", Ki past
~0.15 does not answer it. The air schedule does (see the option table above).

**Margin cost, expressed as the extra plant lag at which SV ripple reaches
5 degC:**

| `pidKi` | 0.10 | 0.13 | **0.15** | 0.16 | 0.18 | **0.20** | 0.22 | 0.24 |
|---|---|---|---|---|---|---|---|---|
| tolerable extra deadtime | 13.7 s | 11.7 s | **10.5 s** | 10.0 s | 9.0 s | **8.0 s** | 7.2 s | 6.5 s |

No cliff separates 0.15 from 0.20 — the cliff is at 12-16 s for both, and the
measured plant deadtime is **under 2 s** (2 s of assumed deadtime already
doubles the open-loop replay residual). So 0.20 keeps a factor of four.

**Read the gain-stress result with care.** Scaling plant gain x0.8 ... x1.5 does
not raise ripple at any Ki in this band — it lowers it. That is a *property of
the model*, not evidence of safety: an integrator plus a first-order lag cannot
be destabilised by gain alone. The only stability information this model carries
is the deadtime column, and deadtime is a proxy for the high-order dynamics a
two-roast fit cannot resolve. Treat the margin numbers as ordinal, not absolute.

**Conclusion.** 0.15-0.16 is the sensible stopping point: it takes the bulk of
the available improvement (rms 1.11 -> 0.80) while keeping five times the
measured lag in hand, and beyond it the returns are ~0.15 degC of rms and ~1.4 s
of time-behind for a third of the margin. **0.20 is not dangerous**, and if the
question is worth settling empirically it settles in one roast: run 0.20 and read
the SV ripple against a 61 s mean. If it stays at 2-3 degC the plant has under
8 s of lag and 0.20 can be kept with confidence; if it reaches 5-6 degC, fall
back to 0.15 and the margin question is answered for good.

#### Validation for the next roast

Same procedure and capture as roast 45 (the dashboard CSV is required — it is
what carries `SV`). Check, in order:

1. **Time to reach BT 120 / 150 / 180 / 196.5** against 2:03 / 3:14 / 4:59 /
   6:21. Ignore the DRYe and FCs mark times; they are BT thresholds.
2. **Error in the quiet windows (3:10-4:20, 5:40-6:40) under 0.5 degC.**
3. **Peak error in 1:31-3:20** — this is the first air cut's bump; roast 45 was
   +2.59 and Ki 0.15 should give ~1.8. If it is unchanged, the bump is not
   disturbance-limited and the air schedule needs the fix instead.
4. **No SV reversal over 10 degC after 1:00**, and SV ripple against a 61 s mean
   under ~6 degC (roast 45: max 4.5, rms 1.19). Above that, Ki has gone too far.
5. Inner loop rms of ~1 degC and heat off both rails, as in roast 45.
### Proportional on Measurement (operator question 2026-09-02)

Raised against Beauregard's article
(`brettbeauregard.com/blog/2017/06/introducing-proportional-on-measurement/`),
which is the reference Artisan itself cites. Two separate things have to be
answered: what Artisan's PoM button actually does, and whether the real
algorithm would help.

**Artisan no longer has PoM.** `pid_control.py:1237-1238` carries that exact URL
followed by `=> PoM removed in v3.1.2`. What survives is the **PoE/PoM radio
pair in the PID dialog, which only writes `pidPsetpointWeight` (beta)** — PoE
sets beta 1, PoM sets beta 0 (pid_dialogs.py:1188-1199), and the beta spin box
takes anything in `[0, pidPsetpointWeightMax=2]`. Beta feeds plain **setpoint
weighting**, `Pterm = getKp(i) * (beta*target - i)` (pid.py:442), evaluated fresh
each cycle. Beauregard's PoM is not that: it *accumulates*
`outputSum -= Kp*(PV - lastPV)` into the same variable as the integral, making
the proportional path an integrator of measurement change. **The button labelled
PoM in the dialog is not the algorithm in the blog.**

**Both make this loop worse, for one structural reason.** PoM's premise is a
regulation problem where the PV settles, so `sum(Kp*dPV)` stays near zero. A
roast is the opposite: BT rises monotonically by ~136 degC, so that term
integrates to `-3 * 136 = -408 duty` which the integrator has to claw back — and
it can only do that by running a standing error. Setpoint weighting reaches the
same place analytically. Redoing the § Roast 44 derivation with beta:

```
u  = Kp*(beta*SP - PV) + I = Kp*(beta-1)*PV + Kp*beta*e + I
du/dt = Kp*(beta-1)*R + Ki*e      =>    e_ss = [ du_req/dt + Kp*(1-beta)*R ] / Ki
```

So **beta below 1 adds `Kp*(1-beta)*R/Ki` of velocity error** — at beta 0,
Kp 3, R 0.25 degC/s, Ki 0.15 that is **+5.0 degC** on top of the existing lag.
Simulated on roast 45's plant at Ki 0.15, `svLookahead` 3:

| beta | 0.00 *(the PoM button)* | 0.50 | 0.90 | **1.00** *(PoE, current)* | 1.15 | 1.50 |
|---|---|---|---|---|---|---|
| quiet droop (degC) | +4.90 | +2.28 | +0.19 | **-0.34** | -6.54 | -53.90 |
| rms (degC) | 7.87 | 4.41 | 1.37 | **0.82** | 6.37 | 49.61 |
| behind at 5:00 | +23.9 s | +13.6 s | +5.2 s | **+3.0 s** | -27.1 s | -111 s |
| `Iterm` at DROP | 666 | 366 | 125 | **65** | 0 (railed) | 0 (railed) |

beta 0 is *worse than roast 44's original tuning*. And the direction that would
help — **beta above 1, which subtracts `Kp*(beta-1)*R` from the velocity error
and at beta ~1.15 would cancel it exactly — is structurally blocked.**
`applyIntegralLimits` (pid.py:360-365) sets
`integral_max = 100*ILF + getKp(PV)*(1-beta)*target`, so for beta > 1 the ceiling
*shrinks* (to 19 at SP 180, beta 1.15) at precisely the moment the required
`Iterm` turns negative — and `integral_min` is pinned at **0** whenever
`outMin >= 0` (pid.py:50-54). The integrator rails at zero and the roast runs
27 s fast. **beta = 1.0 is therefore not merely the safe default, it is the
unique optimum in this structure.**

**True PoM, implemented properly, behaves the same way** (simulated as
`sum += Ki*err - Kp*dPV`, clamped `[0,100]`):

| | Kp 3 / Ki 0.15 | Kp 3 / Ki 0.40 | Kp 3 / Ki 1.00 | Kp 0.5 / Ki 0.15 |
|---|---|---|---|---|
| quiet droop | +4.91 | +1.42 | +0.19 | +0.53 |
| rms | 7.73 | 2.63 | **0.66** | 3.78 |
| behind at 5:00 | +23.9 s | +7.4 s | +1.0 s | +2.1 s |

At the current gains it lands within 0.15 degC of beta 0 — same cause, same
result. It *can* be made to track (Kp 3 / Ki 1.00, rms 0.66, comparable to the
best flat tuning) but only with Ki **seven times** the current value, and at that
point the `-Kp*dPV` term is doing the stabilising, not the proportional job:
**`-Kp*dPV` is derivative-on-measurement folded into the accumulator.** That is
the same result as the Kd/DoE test in § Roast 44 outer-loop analysis — D buys
margin for a larger Ki — reached by a more obscure route. If that trade is ever
wanted, take it explicitly with `pidKd` under DoE, where `Dlimit` and
`derivative_filter` still apply, rather than by moving beta.

**Why the instinct is still reasonable.** PoM is the right tool for the problem
it was invented for: proportional kick and overshoot on a *setpoint step*. This
loop does not have that problem — the background is a smooth Designer curve whose
largest per-sample step is **5.48 degC**, and that one occurs inside the charge
dip where the output is floored anyway. There is no kick to suppress, and the
error that does exist is a ramp-following error, which PoM structurally worsens.

**Verdict: leave `pidPsetpointWeight` at 1.0.** Nothing in the PoM family
addresses ramp lag; `svLookahead` is the feedforward that does, and Ki is the
gain that does.
### Correction: roast 45's error is the loop, not the air (operator challenge 2026-09-02)

The operator's objection: *"BT was low before the second change and got worse
after it. Right before the change should have been the minimal error if the loop
were recovering from the first air change."* **Checked and upheld.** The
air-change attribution in § Roast 45 above is **retracted**, and the Ki 0.15
recommendation with it.

**The objection, verified.** The error minimum is at **3:26**, not just before
the 4:26 cut, and the error was already climbing for a full minute before the
cut — slightly *faster* before it than after:

| window | 3:20-3:50 | 3:50-4:26 | *air cut 4:26-4:32* | 4:26-5:00 | 5:00-5:30 |
|---|---|---|---|---|---|
| error slope (degC/s) | +0.0117 | +0.0130 | | +0.0176 | -0.0046 |

A disturbance response would start at the step. This one was 60 s underway
before it.

**What it actually is: a lightly-damped loop.** The error's extrema are
2:12 (+2.61), 3:26 (-0.21), 5:10 (+1.50), 6:22 (-0.36) — a **177 s period** with
peak-to-peak decaying 2.82 -> 1.86 degC. Log decrement 0.42, so
**zeta ~ 0.07**, a phase margin in the single digits to low twenties. Entirely
model-free, and it explains both excursions with one mechanism instead of two
coincidences. (The first cut at 1:31 happens to land on the first zero crossing,
which is what made the air story look convincing.)

**The plant identification was circular, and that is the root error.** The
original fit modelled the disturbance as `w(t)`, a *free per-sample time-domain
residual*. Such a term absorbs precisely the mismatch a transport delay creates,
so the "plant deadtime ~0 s, each 2 s doubles the residual" result could not have
found a delay even if one were there. Refitting with the disturbance restricted
to a **low-order polynomial in t**, which cannot absorb a lag, and letting the
delay float:

```
dBT/dt = a*(Inlet(t - theta) - BT) + slow(t)
   roast 45:  theta = 17 s   (a = 0.00364, tau 275 s)   resid 0.0160 degC/s
   roast 44:  theta = 17 s   (a = 0.00829, tau 121 s)   resid 0.0131 degC/s
```

**Two independent roasts land on the same 17 s.** The minimum is shallow (0.019
at theta 0 falling to 0.016 at 17) and tau is poorly separated between the two
fits — the classic theta/tau trade in a first-order-plus-deadtime fit — so treat
17 s as "of order 15 s", not a precise figure. The direction, though, is not in
doubt, and the model-free 177 s oscillation corroborates it.

Physically this is not surprising: the inner loop is genuinely fast (Inlet
tracks SV within 1 s at 0.9 degC rms), but between *inlet air temperature* and
*what the BT probe reads* sits the bean mass and its mixing — 15-20 s of it.
The earlier claim that "genuine loop delay is under 3 s in total" counted the
instrumentation and ignored the process.

**Phase margin against the identified plant** (`L = 1.6*a/(s+a)*e^-17s * (Kp + Ki/s)`):

| `pidKi` | 0.04 | 0.06 | 0.08 | **0.10** | 0.12 | **0.15** | 0.20 |
|---|---|---|---|---|---|---|---|
| PM, roast 45 fit | 47 deg | 36 deg | 27 deg | **20 deg** | 15 deg | **8 deg** | **negative** |
| PM, roast 44 fit | 44 deg | 34 deg | 26 deg | **18 deg** | 12 deg | **4 deg** | **negative** |
| predicted period | 307/153 s | 275/146 | 250/139 | **230/132 s** | 214/125 | 196/117 | 173/106 |

Roast 45 at Ki 0.10 measured **zeta 0.07 at a 177 s period** against a predicted
18-20 deg margin at 132-230 s. The model and the roast agree. Roasts 42/44 at
Ki 0.04 sat at 44-47 deg, which is why their error traces are smooth and
monotone — the droop was large but there was nothing oscillatory in them.

**So Ki 0.10 was already at the edge, and 0.15 is past it.** The step-2
recommendation is withdrawn. Note the alog currently on disk records
`pidKi = 0.15`, so if that is what is loaded, the next roast should be expected
to ring at a ~2-3 minute period with several degC of swing.

**Lowering Kp makes it worse, not better** — Kp 2.0 at Ki 0.10 gives PM 10 deg,
Kp 1.5 gives 5 deg. Counterintuitive but standard for a delay-limited loop: near
crossover the proportional term is what supplies phase lead, and removing it
leaves the integrator's -90 deg exposed. **Do not respond to ringing by dropping
Kp.**

**What does buy margin: derivative on error.**

| | Ki 0.10, Kd 0 | Ki 0.10, **Kd 40** | Ki 0.15, Kd 40 | Ki 0.15, Kd 60 |
|---|---|---|---|---|
| PM (roast 45 / roast 44 fit) | 20 / 18 deg | **29 / 46 deg** | 16 / 29 deg | 19 / 40 deg |

This is the same conclusion the earlier `Kd`/DoE sweep reached empirically
(§ Roast 44 outer-loop analysis: Kd 30 DoE rescued Ki 0.24 under a 10 s deadtime
stress) — now with the reason attached. It needs `pidDsetpointWeight = 1` (DoE);
under DoM it would brake the ramp instead. Affordable on noise: measured BT
high-frequency residual is **0.064 degC rms**, so Kd 40 costs ~3.6 duty = 5.8 degC
of SV jitter, and `derivative_filter` (a fixed 0.1 Hz lowpass, pid.py:640-644)
cuts that roughly fivefold.

#### Tested and not upheld: the early floor / minimum inlet temperature

Operator hypothesis: the 140 degC output floor early in the roast winds the
integrator down and disturbs the loop. **Half right on the facts, but it is not
what drives the ring.**

**The floor episode is real and long.** In roast 45 the output sat at
`SV = 140` (duty 0) from **0:05 to 0:47, 39 s**, with the error at -12 to
-16 degC throughout. The cause is a **profile authoring defect**: the
background's charge dip is deeper than the roaster can reach.

| | profile_002 | roast 43 | roast 44 | roast 45 |
|---|---|---|---|---|
| minimum BT after CHARGE | **52.0** at 32 s | 58.8 at 23 s | 60.2 at 25 s | 67.3 at 28 s |
| profile is deeper by | — | 6.8 degC | 8.2 degC | **15.3 degC** |

**The integrator is genuinely whipsawed** — but *upward* first, not down.
Reconstructed from roast 45: `Iterm` ~46 at 0:30 (back-calculation pinning it at
`Kp*|err|` while floored), then draining hard to **15 by 1:20** as the loop
unsaturates with the error still negative, then climbing back past 50. A 30-duty
swing in the first two minutes. That is the disturbance the hypothesis points at,
and it is real.

**But removing it does not remove the ring.** Re-running the corrected model with
the background's dip raised to an achievable minimum, everything else fixed:

| background dip minimum | 52.0 (as authored) | 60 | 64 | 67 |
|---|---|---|---|---|
| floor time | 55 s | 39 s | 33 s | 26 s |
| `Iterm` handed to the roast | 26.0 | 25.4 | 23.5 | 24.6 |
| ring rms / swing (from 1:50) | 1.64 / 3.85 | 1.66 / 3.94 | 1.74 / 4.26 | 1.69 / 4.06 |

Floor time halves; the ring does not move. The reason is back-calculation again:
it converges on `Iterm = Kp*|err|` *while* floored and then the drain as the
error returns to zero dominates, so the handover lands near 24-26 almost
regardless of how deep the target dip was. The excitation that rings the loop is
the charge transient itself, which is unavoidable — **the ring is a damping
problem, and damping is set by the gain.**

**Fix the dip anyway, on its own merits.** Forty seconds of saturated,
open-loop operation every roast, with the loop's entry state decided by an
anti-windup side effect rather than by control, is not a good place to start
from — and it is what caps `svLookahead` near 4 s (§ Roast 44 outer-loop
analysis), which matters now that Ki is margin-limited and lookahead is the only
free tracking lever. Just do not expect it to quiet the roast.

**Derivative is unproven — do not take it yet.** The frequency-domain table
above says `Kd 40` under DoE should lift phase margin from 20 to 29-46 deg. Run
in the time domain on the *same* plant it does not: ring rms 1.65 vs 1.64 at
`Kd 0`, and the swing worsens 3.85 -> 4.67. The likely reason is that DoE
differentiates the *reference* as well as the measurement, and the background's
own RoR is a large varying signal, so the lead the margin calculation assumes is
partly spent re-injecting profile curvature. `pidDlimit` does not rescue it
(1.5 degC/s and 500 degC/s give identical results — steady-state `dErr/dt`
rarely reaches the limit). The two analyses disagree; until one roast settles it,
**`pidKd` stays 0.**

**Model caveat.** The rebuilt model reproduces the ringing that the first one
could not — extrema +3.67 / -0.17 / +1.81 against a measured +2.61 / -0.21 /
+1.50 — but its period is 234 s against the measured 177 s, roughly 30% long
(`tau` is the poorly-determined parameter: 275 s from roast 45, 121 s from
roast 44). Use it for direction and ranking, not for absolute numbers.

#### Revised recommendation

1. **Set `pidKi` to 0.07 and leave `svLookahead` at 3.** PM ~30 deg on both
   fits. Expect roughly half of roast 44's droop with none of roast 45's swing.
   Treat **Ki 0.10 as the measured stability edge**, not a target.
2. **`pidKp` stays 3.0.** Do not lower it.
3. **`svLookahead` is now the *only* free tracking lever** — it is feedforward,
   so it costs no phase margin, whereas Ki is margin-limited. It is still capped
   near 4 s by the charge-dip preload (that analysis used measured BT, so it
   stands). If more lead is wanted, `sv_filter=1` blunts the dip at the cost of
   1.33 s of its own delay — worth one roast's experiment, but only after the
   gain is safe.
4. **If roast 45's tracking is wanted back, the route is `pidKd`, not `pidKi`:**
   `pidKd = 40`, `pidDsetpointWeight = 1.0` (DoE), `derivative_filter = 1`,
   with `pidKi` at 0.10. Predicted PM 29-46 deg. This is a genuine experiment,
   not a settled recommendation — change it on its own roast.

**What survives of the air-change finding.** The fan sensitivity is a real
measurement — a fan term halves the plant-model residual and implies ~49% of
plant gain per 10 fan units, so the 65 -> 60 cut does remove about a quarter of
the gain. What is retracted is the claim that it *shapes roast 45's error trace*.
It is a real disturbance riding on a loop that was too lightly damped to reject
it cleanly, and the loop is the thing to fix first. Whether moving the cut helps
is now an open question, not a finding.

**Method note for future work.** Two traps caught here, both worth remembering:
never let a disturbance term be a free function of time when a plant delay is
also in question, and check identified delays on more than one roast. Also:
**Artisan stamps the PID settings into a profile at *save* time, not roast time.**
`airRoaster_45.alog` was re-saved at 23:24 and now reads `pidKi = 0.15` although
the roast ran at 0.10; the roast data is byte-identical. The reliable check is
empirical — `dI/dt = Ki*err` while the output is unclamped, which recovers
**Ki = 0.101 (r = 0.97, n = 311)** for roast 45.

### The output floor / range analysed (operator request 2026-09-02)

`positiveTargetMin` / `positiveTargetMax` are **two things at once**, and only
one of them is a clamp.

**1. They set the actuator gain.** `setEnergy` maps duty onto the subrange
linearly, so `SV = min + (max-min)*duty/100` and **1 duty unit = (max-min)/100
degC**, currently 1.60. Moving either endpoint rescales the loop's actuator gain
and is *exactly equivalent* to scaling `pidKp` and `pidKi` together:

| min/max | span | degC per duty | equivalent gains at the present physical loop gain | PM at Kp 3 / Ki 0.07 (r45 fit / r44 fit) |
|---|---|---|---|---|
| **140/300** *(current)* | 160 | **1.60** | Kp 3.00, Ki 0.0700 | **31 / 30 deg** |
| 120/300 | 180 | 1.80 | Kp 2.67, Ki 0.0622 | 31 / 27 deg |
| 100/300 | 200 | 2.00 | Kp 2.40, Ki 0.0560 | 30 / 23 deg |
| 160/300 | 140 | 1.40 | Kp 3.43, Ki 0.0800 | 31 / 33 deg |
| 140/270 | 130 | 1.30 | Kp 3.69, Ki 0.0862 | 31 / 34 deg |
| 130/290 or 150/310 | 160 | 1.60 | unchanged | 31 / 30 deg |

Note the last row: **sliding the window without changing its width changes the
gain not at all.** And since the gain effect is redundant with `pidKp`/`pidKi`,
the *only* reasons to move these keys are the saturation limits themselves.

**2. The floor is not the saturation point.** `pid_control.py:1454` calls
`setLimits((-100 if pidNegativeTarget else 0), (100 if pidPositiveTarget else 0))`
— with no negative target the PID clamps the **duty** at 0 and 100 *regardless*
of `positiveTargetMin`, and `_calculate_integral_limits(0, 100, ILF)` gives
`[0, 100]` with it. So moving the floor changes neither **when** nor **for how
long** the loop saturates, nor the back-calculation behaviour that sets the
integrator handover (§ Correction). It changes only what inlet temperature
"duty 0" *means* — how much heat still flows while saturated.

**Raising it is blocked by the preheat, and there is less room than assumed.**
Measured on roast 45's PID-driven preheat, the loop settles at **SV 145** to hold
BT ~128-129 against the background's 127.8 CHARGE BT:

```
t -70  SV 159.8   t -50  SV 151.4   t -30  SV 147.0   t -10  SV 144.2
settled over the last 30 s before CHARGE: SV 145.0, floor 140
```

That is **5 degC of downward authority at the charge point**, not the 8 degC
§ PID-driven preheat assumed. A floor above ~142 puts the preheat on its own
floor and charges hot — the failure that killed the 170 experiment.

**And it would buy very little.** Over the ~40 s the floor binds, the TP
sensitivity is `a * dIN * 40`:

| floor change | -20 | -10 | +10 | +20 |
|---|---|---|---|---|
| TP moves (roast 45 fit, a=0.00364) | -2.9 | -1.5 | +1.5 | +2.9 degC |
| TP moves (roast 44 fit, a=0.00829) | -6.6 | -3.3 | +3.3 | +6.6 degC |

With only ~2 degC of usable headroom (140 -> 142) that is **+0.3 to +0.7 degC of
TP**. Not worth a config change.

**Lowering it goes the wrong way** — deeper TP by 1.5-3.3 degC per 10 degC, the
opposite of what is wanted, while raising the actuator gain (180 span = 1.8
degC/duty, i.e. Kp 3.38 / Ki 0.079 in present-range terms) and costing up to
7 deg of phase margin on the roast 44 fit.

**The ceiling should stay at 300.** It has never bound — in-roast maximum SV was
**251.2** (roast 45) and **251.9** (roast 44), about 48 degC spare — and 300 is
exactly the firmware clamp `INLET_SV_MAX_C = 300.0f` (airRoaster.ino:192), so the
two agree by construction. Narrowing to 270 is merely `Kp 2.44 / Ki 0.057` by
another name, and it would remove the headroom that a cold start or a heavy
batch needs.

**`positiveTargetRangeLimit` must stay ticked.** Unticked, `heat_min` reverts to
the slider minimum of 0 (`slidermin=0, 0, 0, 0`), the loop commands `INLET 0`,
and the firmware disengages with heat off mid-roast (§ The floor).

**Conclusion: leave `positiveTargetMin` at 140 and `positiveTargetMax` at 300.**
The floor is already within 5 degC of the preheat operating point, so it is
close to its ceiling; the range's only other effect is a gain rescale better
done with `pidKp`/`pidKi` directly.

**Interaction with raising the profile's TP — they work together.** A shallower
background dip shrinks the dip error (roast 45 bottomed at -15.3 degC against the
profile), and a smaller error means the loop commands *more* inlet through the
dip, moving **away** from the floor: roast 45's 39 s of saturation should shrink
or disappear. So the TP fix reduces the floor's relevance rather than requiring
it to be co-tuned. Two cautions: set the profile's TP to what the roaster
actually reaches rather than above it, or the loop will add heat to meet it and
warm the whole early roast; and the achieved minimum is batch-dependent —
**58.8 / 60.2 / 67.3 degC in roasts 43 / 44 / 45**, an 8.5 degC spread with
`last_batchsize` moving 400 -> 345 g — so no single value fits every batch.
Match the size roasted most often and expect a residual dip error of a few degC
rather than fifteen.

### profile_003 — the TP correction, and what it does to the lookahead (2026-09-02)

New background, TP raised to match what the roaster actually reaches.

| | profile_002 | **profile_003** |
|---|---|---|
| CHARGE BT | 127.83 | **128.02** |
| TP minimum | 51.96 at 0:32 | **67.39 at 0:37** |
| steepest dip fall | 5.48 degC/s | **3.74 degC/s** |
| DRYe | 3:20 at BT 151.95 | **3:12 at BT 149.55** |
| FCs | 6:30 at BT 197.90 | 6:39 at BT 197.54 |
| DROP | 6:51 at BT 201.18 | **7:05 at BT 201.45** |

The TP now matches roast 45's achieved 67.3 degC almost exactly, and CHARGE BT is
unchanged, so the preheat operating point (SV ~145) and the 5 degC of floor
headroom from § The output floor stand as analysed.

**The saturation is gone.** Replaying roast 45's measured BT against the new
background at `svLookahead=0`: worst dip error **-3.1 degC** (was -15.8),
`Iterm` handed to the roast **13.0** (was 34.2), floor time **0 s** (was 39 s).
The 40 s of open-loop operation every roast is eliminated, and the loop enters
the ramp in linear control with a state set by integration rather than by an
anti-windup side effect.

**But it tightens the lookahead trade rather than relaxing it — the opposite of
what § The output floor predicted.** The earlier reasoning was that a gentler dip
means each second of lead injects less error. That is true per second, but it
misses the dominant term: with profile_002 the target and BT disagreed by 15 degC
at the dip *anyway*, so the lead was a small addition to a large existing error.
Now that they agree, **every second of lead is pure manufactured error**:

| `svLookahead` | 0 | 1 | 2 | **3** *(current)* | 4 |
|---|---|---|---|---|---|
| worst dip error (degC) | -3.1 | -4.8 | -8.3 | **-11.6** | -14.8 |
| `Iterm` handed to the roast | 13.0 | 18.7 | 26.0 | **33.4** | 40.7 |
| floor time | 0 s | 3 s | 4 s | **5 s** | 6 s |
| droop at Ki 0.07, mid-roast (degC) | +1.34 | +1.09 | +0.84 | **+0.59** | +0.34 |

So `L=3` re-creates about -11.6 degC of exactly the dip error the new profile just
removed, and puts the SV on its floor for 5 s at turning point — worth roughly
1-2.5 degC of extra TP depth by the sensitivity in § The output floor, partly
undoing the change. What it buys is 0.75 degC of droop.

**Recommendation: keep `svLookahead` at 3 for the next roast anyway.** Two
things already change — `pidKi` 0.10 -> 0.07 and profile_002 -> profile_003 — and
a third would make the result unreadable. **`L=2` is the likely follow-up** once
the pair has been seen; L=0 is the choice if a completely clean dip is worth
+1.34 degC of droop.

**Two things improve for free.**

- **The control window is healthier.** `calcSV` deactivates at background DROP
  minus lookahead: 7:02 with profile_003 at `L=3`, against 6:48 with
  profile_002. Roasts have been dropping at 6:49-7:04, so the old margin was
  negative on a fast roast and is now positive.
- **Mark times become meaningful again.** profile_003's DRYe sits at BT 149.55
  against the Phases DRY threshold of 149 (`phases=[38, 149, 196, 218]`), so
  `autoDRY` will now fire within ~0.5 degC of the profile's own DRYe. With
  profile_002's DRYe at BT 151.95 the two were 2.4 degC apart, which is what made
  roast 45's marks read 9-11 s early (§ Roast 45). Still prefer the
  time-to-reach-a-given-BT comparison, but the mark is no longer misleading.

**Caveat: the TP match is batch-specific.** profile_003 is matched to roast 45
(345 g, TP 67.3). Roasts 43/44 at 400 g bottomed at 58.8/60.2. Replaying a 7 degC
lower BT against profile_003 at `L=0` flips the dip error positive (-1.7 becomes
BT *below* target), the loop adds heat through the dip, and the handover rises to
39 by ordinary integration. Not harmful — but a heavier charge will run the early
roast warmer against this background, and the dip error will not be near zero the
way it is for a 345 g batch.

**Also a real roast change beyond TP**: the back half is 0.4-1.8 degC cooler from
4:00 on and DROP is 14 s later at the same BT, so profile_003 is a slightly
gentler finish, not only a shallower dip.

**Auto-DROP alarm margin is ample.** profile_003's RoR over the armed window
(DRYe 3:12 to DROP 7:05) runs +8.6 to +19.6 degC/min against the -25 threshold;
the charge dip reaches -220, which is why the alarm must stay armed from DRY END
and not CHARGE (§ Auto-DROP detection).

**The background is not carried in the settings file.** There is no
`backgroundpath` key in `airRoaster_cascadePID.aset` — the reference lives in
each saved profile. profile_003 has to be loaded as background per session.

### Scheduling, characterisation runs, and the fan (operator questions 2026-09-02)

#### 1. Gain scheduling / partitioning

**Artisan's *built-in* gain scheduling cannot key on error**: `getParameter`
evaluates the schedule at `self.target if self.gain_scheduling_on_SV else PV`
(pid.py:382) — SV or PV, never the error.

> **Correction (operator, from the Artisan help).** An earlier version of this
> section claimed there is no command to set the gains at runtime. That was
> wrong — it came from grepping only for command names beginning with `pid`.
> **`p-i-d(<p>,<i>,<d>)` exists** (main.py:10759). For any device that is not
> Fuji/Delta it falls through to `self.pidcontrol.confPID(kp,ki,kd)`
> (main.py:10791), whose last branch — `elif self.aw.qmc.Controlbuttonflag:`
> (pid_control.py:1914) — calls `self.aw.qmc.pid.setPID(kp,ki,kd)` and updates
> `pidKp`/`pidKi`/`pidKd`. This is a WebSocket device with `Controlbuttonflag`
> ticked, so **it reaches the software PID.**

So gains *can* be changed mid-roast, from an event button or an alarm-triggered
button, and keyed on **time, BT, ET or DeltaBT** through the alarm conditions —
a superset of the built-in schedule, which only fits a line or parabola in SV/PV.

Four properties of `p-i-d()` worth knowing before using it:

- **It is bumpless in the integrator.** `setPID` (pid.py:554-564) only assigns
  `Kp`/`Ki`/`Kd` (each clamped to `max(x, 0)`, so no negative gains); `Iterm` is
  untouched. Changing `Ki` therefore has *no* instantaneous effect at all, only
  on the rate of climb. Changing `Kp` steps the output by `dKp * err` — at a
  1 degC error, Kp 3 -> 1.5 moves the SV by 2.4 degC. Small.
- **It does not call `confSoftwarePID()`**, so filters, IWP, ILF, `Dlimit` and
  the gain-schedule sets are left alone. `confPID` does re-apply
  `setLimits(0, 100)`, which is already the running value.
- **It writes only the base gains**, not `pidKp1/Ki1/Kd1` or the `2` set. If gain
  scheduling were ever enabled, `p-i-d()` would move only the `Schedule0` anchor.
- **It is sticky.** The values land on `self.pidcontrol.pidKp/Ki/Kd`, so a
  **Save Settings after a roast writes whatever the last alarm set** into the
  `.aset`. An alarm-driven Ki change silently becomes the new default. Same class
  of trap as the profile stamping settings at save time (§ Correction).

**But the loop still does not need varying gains.** Recomputed against the corrected plant
(theta 17 s), the fan is the only thing that moves the plant materially through a
roast — refitting with theta fixed at 17 gives `a = 0.00288 + 0.01168*(fan-60)/60`,
a 1.55x bandwidth range over the fan settings actually used. The margin barely
notices:

| fan | 58 | 60 | 62 | 65 |
|---|---|---|---|---|
| `a_eff` (tau) | 0.00249 (402 s) | 0.00288 (347 s) | 0.00327 (306 s) | 0.00385 (260 s) |
| phase margin at Ki 0.07 | 28 deg | 29 deg | 30 deg | 31 deg |
| Ki that would hold PM = 30 deg | 0.066 | 0.068 | 0.070 | **0.074** |

A **+-6% gain trim** across the whole operating range is not worth scheduling,
by either mechanism. The capability is now known to exist; the case for using it
on the *gains* still does not.
The reason it is so flat: the plant is nearly integrating in the crossover band
(tau 260-400 s against a 250-330 s oscillation period), so a change in tau moves
gain and phase in compensating directions. **The earlier enthusiasm for a Ki
schedule (§ Roast 44 outer-loop analysis) is retracted** — it was computed on the
discredited theta = 0 plant.

Two further obstacles if it were ever wanted: the schedule variable is
**non-monotone in time** (target 128 at preheat, 67 at TP, 201 at DROP, so
target = 128 occurs twice and gets the same gains both times); and one schedule
serves all three gains, so `pidKp1`/`pidKd1` must be set equal to their bases.

**The windup half of the question is already done, automatically and
error-dependently.** `_should_integrate` (pid.py:286) blocks integration
whenever the unclamped output is saturated in the direction the error would
worsen, and `_back_calculate_integral` (pid.py:314-333) bleeds the integrator
whenever the output clamps. Both are live via `pidIWP=true`. That *is*
error-keyed windup management; there is nothing to add. `pidIRoC` keys on
per-sample *setpoint change*, not error, and cannot reach its threshold here.

**The switching that is worth doing is the lookahead, not the gains.**
`pidLookahead(<n>)` sets `svLookahead` at runtime (main.py:10936, gated on
`Controlbuttonflag`, which the cascade requires anyway). That resolves the
profile_003 trade instead of compromising it: lookahead is *harmful* at the dip
(manufactured error, SV on the floor at TP) and *helpful* on the ramp, and it is
feedforward, so it costs no phase margin — which matters now that Ki is
margin-limited. Wiring:

```
CHARGE button action (buttonactions[0], currently empty) -> a button with pidLookahead(0)
alarm: From CHARGE, offset ~90 s, source -3 (time only)  -> a button with pidLookahead(6)
```

> **Corrected 2026-09-05.** This paragraph previously listed `pidILF`, `pidIWP`,
> `pidIRoC`, `pidDerivativeLimit` and `pidDerivativeFilter` as runtime-settable
> Artisan Commands. **None of them exist.** Enumerating every
> `cs.startswith('...(')` branch in `main.py`'s Artisan Command handler, the
> complete PID-related set is `p-i-d(p,i,d)` (10759), `pidWeights(beta,gamma)`
> (10796), `pidLookahead(n)` (10936), `pidSource(n)` (10851), `pidSV`/`pidSVC`/
> `pidRS`/`pidSVbuttons` (10811-10841, 10599) and `pidmode(...)` (10359). The
> PID object *has* `setIntegralLimitFactor` and friends, but nothing in the
> command surface reaches them — ILF, IWP, IRoC, `Dlimit` and the derivative
> filter can only be changed in the dialog, i.e. between roasts.

So the runtime levers are **the three gains, the two setpoint weights and the
lookahead** — and that turns out to be enough (§ The dip is a different control
problem). One good use for `p-i-d()` that is *not* scheduling: a panic button
carrying a known-safe gain set, for the characterisation runs below.

Cautions: alarm time and temperature conditions are **OR'd** (§ Auto-DROP
detection), so a time-only alarm needs source -3 and the temperature row left
inert. And the switch is a step in the target of `L * RoR` — at 1:00 the
background runs ~46 degC/min, so 6 s of lead is a +4.6 degC target step and about
+22 degC of SV. Apply it at 1:30-2:00 where the RoR is lower, or in two steps
(0 -> 3 -> 6). **Introduce on its own roast.**

#### 2. Characterisation runs — yes, and this is the highest-value thing available

**The accumulating roasts are not sufficient, and more of the same will not
help.** Everything so far is closed-loop against a smooth reference, where the
input is a deterministic function of the output, so there is no independent
excitation. The consequence is visible directly — the theta/tau ridge on roast 45:

| theta | 0 s | 5 | 10 | 15 | **17** | 20 | 25 | 30 |
|---|---|---|---|---|---|---|---|---|
| best-fit tau | 1071 s | 426 | 310 | 286 | **275** | 293 | 327 | 402 |
| residual (degC/s) | 0.0186 | 0.0178 | 0.0168 | 0.0163 | **0.0160** | 0.0162 | 0.0165 | 0.0170 |

**tau moves fourfold while the residual moves 14%.** That is a flat ridge: the
parameters are not separately identifiable from this data, which is exactly why
roasts 44 and 45 agreed on theta = 17 s but gave tau 121 s and 275 s. **What is
missing is excitation, not data.**

Signal-to-noise is not the obstacle. Measured BT high-frequency residual is
**0.064 degC rms**, and a 30 degC inlet step changes `dBT/dt` by 0.075-0.116
degC/s — **3.4 to 5.2 degC of BT deflection over 45 s, SNR 50-80.**

**Test A — preheat plateau step. Free, no beans, ~10 minutes.** PID off, SV
manual at 145, let BT settle near 129. Step SV to 185, hold 180 s, step back,
hold 180 s. Gives theta and the empty-roaster bandwidth cleanly. It will not give
the *loaded* tau, but it anchors theta — the parameter the closed-loop data
cannot resolve and the one the stability margin depends on.

**Test B — mid-roast doublet. One degraded (not ruined) batch.** Normal roast on
profile_003. At 3:00 press CONTROL to drop the PID out, leaving SV frozen near
215. Settle 15 s. Then SV +30 for 60 s, SV -30 (i.e. 30 below the frozen value)
for 60 s, back to the frozen value, PID back on around 5:30. **A doublet rather
than a step** for two reasons: its net energy is ~zero, so the roast lands near
where it would have; and a 60 s half-period puts the peak excitation near a 240 s
period, right in the loop's 250-330 s crossover band.

**Test C — the fan, properly.** Repeat Test B at fan 58 and at fan 65. The fan
sensitivity is currently a single weakly-identified regression coefficient from
one roast; two doublets would measure it.

#### 3. The fan

**From the loop's point of view the fan level is nearly free** — 28 deg to 31 deg
of phase margin across 58-65 (table above). What disturbs the loop is the *step*,
not the level. So there is no control-side reason to abandon choosing fan by bean
circulation; the useful discipline is to make the changes at repeatable times, or
to ramp them, so the disturbance is the same roast to roast.

On predicting the setting from load: the operator is right that mass is not
sufficient. Minimum fluidisation velocity is set by particle diameter, density
and shape (Ergun / Wen-Yu), while charge mass sets bed pressure drop and hence
where the fan sits on its own curve — two different dependencies. No closed form
will beat an empirical fit on this machine. The practical route is to log, per
batch, the fan setting judged adequate together with charge mass, bean screen
size and density; 15-20 batches gives a usable regression and a defensible
automation rule. That is a data-collection project rather than an analysis one,
and it is independent of the control work.

### Fan vs batch size: no relationship (2026-09-02)

Scanned every `.alog` in `~/Documents/artisan`, restricted to the current machine
and to **roast 16 onward** (operator: earlier probe issues). For each roast, the
fan level held through the roast body (step-interpolated from the Air events,
sampled 1 Hz from CHARGE to DROP, median).

**First cut was a trap.** Over the unfiltered set the correlation looked real —
`fan = 0.054*g + 34.7`, r = 0.56. It is entirely a population split: batch
numbers >= 400 (Jan-Jun 2026, n=127) all sit at **fan 43** with 7-13 minute
roasts — a different machine/era — while the airRoaster series runs 53-62. Small
batches happen to be dominated by the former. The correlation is the split, not
a fan/mass relationship.

**Within the airRoaster, roast 16 onward, there is nothing there.**

| batch size | n | fan level |
|---|---|---|
| 250-286 g | 16 | 59.6 +- 1.1 |
| 345 g | 1 | 60.0 |
| 400-428 g | 7 | 59.4 +- 1.4 |
| 450-459 g | 4 | 58.8 +- 0.8 |

```
n = 29, 161-459 g       fan = -0.0020*g + 60.05      r = -0.15,  r^2 = 0.023
slope -0.20 +- 0.25 fan units per 100 g  ->  0.8 sigma, indistinguishable from zero
predicted change across the whole 250-460 g range: -0.4 units, against a
scatter of +-1.1 units at fixed mass
```

**The operator's own controlled pair says the same.** Roasts 37 and 38, same
day, same bean (Panama Elida natural), same intended roast, 450 g against 250 g:
**fan 58 against 57.** A 200 g difference moved the setting by one unit.

**This is physically the expected answer.** Minimum fluidisation velocity is a
property of the *particle* — diameter, density, shape — not of the bed mass.
Charge mass changes bed depth and hence pressure drop, which moves a fixed-duty
blower along its system curve, but that is a second-order effect and the data
puts it at about one fan unit over 200 g.

**Consequences.**

- **A fixed fan setting is defensible**, ~59-60 across 228-575 g. That removes
  the within-roast disturbance entirely, which is the thing that was perturbing
  the loop, and it costs nothing in stability terms (§ Scheduling: margin runs
  28-31 deg across the whole fan range).
- **The within-roast ramp is a different question and has a real basis.** The
  same roasts start at a mean of 62.0 at charge and settle at 59.4, min 58.5 — a
  deliberate ~3 unit reduction. That tracks the *bean's* changing density as
  moisture leaves and the bean expands, which is a within-roast property, not a
  charge-mass one. If it is kept, making it a smooth repeatable ramp rather than
  3 s steps is what the loop would prefer.
- **The screen-size data the operator does not have is not the missing piece.**
  Mass is not predictive here at all, so no mass-based rule needs the density
  correction. If bean-to-bean variation matters it will show up as scatter in the
  fan setting at *fixed* mass, which is presently +-1.1 units — about the
  resolution of the judgement being made.

### Logging the control effort in one file (operator request 2026-09-02)

The analyses so far have needed the dashboard CSV alongside the `.alog`, aligned
by cross-correlating `Inlet` against `IN`, because the commanded SV is not in the
profile. Two routes were checked:

> **Superseded 2026-09-02** once firmware came into scope: **v0.19.0 adds `SV`
> and `HT` to the Artisan `getData` reply**, so the commanded inlet setpoint and
> the applied heat duty are logged as 1 Hz *curves* at full resolution. See
> § Firmware now in scope below. `createEvents` stays on as the fallback until
> the device is flashed, and can be turned off afterwards.

- **Artisan cannot log it as a curve.** The PID source list offers only ET, BT
  and the extra *device* channels (pid_dialogs.py:1251-1258), and the symbolic
  expression evaluator's dictionary has no slider or event variable
  (canvas.py:6967-7090) — so a virtual extra device cannot read slider 3 either.
  The firmware's Artisan `getData` reply carries `BT`, `ET`, `IN`, `AT` and no
  SV (airRoaster.ino:1232); `inSV` exists only on the `status` push, which
  Artisan does not map to a channel. Adding SV to `getData` would be the clean
  fix and is a firmware change, so out of scope here.
- **`createEvents=true` does it within Artisan, and is now set.**
  `setEnergy` passes the flag to `addRawEventSignal` (pid_control.py:1308), and
  `addEvent_internal` records the slider move into the profile when it is set
  (main.py:17976-17997). The commanded inlet SV then lands in the `.alog` as
  **T_inlet events**, in the same file as BT and the background.

Two properties to know: the value recorded is the **integer** slider value
(`nv = eventsExternal2InternalValue(new_value)`), so ~1 degC resolution on a
140-300 degC span — the fraction still reaches the wire, it is just not logged;
and the cadence follows `dutySteps` and `force_duty = 3` (pid.py:197), so an
event lands every 1-3 s, roughly 200-400 per roast. The profile plot gets busy.
That is the whole cost, and it makes every future roast self-contained for
analysis.

### Files for the characterisation runs (2026-09-02)

Both are ordinary background profiles carrying the test's inlet schedule as
**T_inlet events**, so they serve as an on-screen guide. Precise timing is *not*
required — the identification uses the recorded SV as its input, so hand-driving
slider 3 is adequate. (They can also drive slider 3 automatically via event
playback, but that fights the PID for the same slider, so only with the PID off
and playback deliberately enabled — see § Background event playback must be off.)

| file | test | schedule |
|---|---|---|
| `artisan/charstep_empty.alog` | **A** - empty roaster, no beans | inlet 145 -> 185 at 2:00 -> 145 at 5:00 -> 185 at 7:00 -> 145 at 10:00 |
| `artisan/chardoublet_loaded.alog` | **B** - loaded doublet, one sacrificial batch | roast 45's own commanded SV replayed, with **+30 degC over 3:00-4:00 and -30 degC over 4:00-5:00** |

**Procedure, both tests: the PID must be OFF.** Press ON, load the file as
background, do *not* press CHARGE (which would arm `pidOnCHARGE`), press START to
record, and drive slider 3 to follow the guide curve. Test B is run as a normal
charge with the PID left off throughout, so the whole roast is open-loop on the
replayed schedule plus the doublet.

**Why a doublet rather than a step for Test B**: its net energy is ~zero, so the
batch lands near where it would have; and a 60 s half-period places the peak
excitation near a 240 s period, inside the loop's 250-330 s crossover band.

Test C is Test B repeated at fan 58 and fan 65, which measures the fan
sensitivity that is currently one weakly-identified regression coefficient.

### The lookahead-switching config (2026-09-02)

`artisan/airRoaster_cascadePID_lookahead.aset` — the canonical config plus the
runtime lookahead switch from § Scheduling. **A separate file deliberately**:
it is an experiment and should not ride along with the `pidKi` and profile_003
changes on the next roast.

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
point (§ profile_003) — and the ramp gets 6 s of feedforward, which costs no
phase margin. 90 s is past turning point and where the background RoR has fallen
enough that the switch is a ~+3.5 degC target step rather than +4.6.

### Firmware now in scope (operator 2026-09-02)

The firmware constraint is lifted. Reassessing what firmware can actually do for
the outer loop, in order of confidence.

#### Measured first: how much of the 17 s is the probe?

If the BT probe were slow, its lag would be inside the loop and a firmware lead
filter would recover margin directly. It is not the main term. From the **dump
transient** — at DROP the beans leave in about a second and the probe is suddenly
in air alone, which is the closest thing to a step this machine offers:

| roast | 41 | 43 | 44 | 45 |
|---|---|---|---|---|
| max \|dBT/dt\| after the dump | -68.4 | -26.3 | -43.5 | -56.1 degC/s |

For a first-order probe the initial rate is `dT/tau_p`, and with a ~150 degC
excursion those rates imply **tau_p ~ 2-6 s**. (The 63% times, 28-45 s, are much
longer but meaningless here — the chamber air is cooling too, so the probe is
tracking a moving target rather than a step.) The inlet thermocouple on the same
event gives a comparable 5-6 s.

**So roughly 2-6 s of the ~17 s is instrumentation and the remaining 11-15 s is
genuine process** — air-to-bean heat transfer and bed mixing. A firmware lead
filter on BT would buy a few seconds at the cost of amplifying noise, and is
**not worth doing**. The step test should confirm this before it is dismissed
for good.

#### v0.19.0, first item (done): `SV` and `HT` in `getData`

```c
"{\"id\":%s,\"data\":{\"BT\":%.1f,\"ET\":%.1f,\"IN\":%.1f,\"AT\":%.1f,"
"\"SV\":%.1f,\"HT\":%u}}"
```

`SV` is `inletSV` (0 outside `MODE_INLET`), `HT` is `heatLevel`. Buffer 128 ->
192. Purely additive — Artisan ignores nodes it is not configured for and no
control path is touched. Compile-verified.

Artisan side, already applied to both `.aset` files:
`channel_nodes = BT, ET, IN, AT, SV, HT, ...` and
`channel_modes = 1, 1, 1, 1, 1, 0, ...` (mode 0 marks a non-temperature, which
is what `HT` is — canvas.py:13220 reads it as `extraNoneTempHint`). **The
remaining step is manual**: add a further WebSocket extra device in Config >
Device > Extra Devices so channels 5 and 6 become curves. The device id is not
guessed here because a wrong one silently mis-maps a curve.

This retires the dashboard-CSV cross-correlation that every analysis in this
document has depended on, and beats `createEvents` (integer degC, 200-400 events
a roast). Turn `createEvents` off once the device is flashed.

#### v0.19.0, second item (done): `INLET TRIM` — the feedforward-plus-trim command

Added to v0.19.0 rather than a version of its own (operator, 2026-09-06) so the
outer-loop instrumentation and the outer-loop restructuring land in **one flash**.
It is the firmware half of § Dip strategies § The structural fix / runbook step 9,
and it is inert until Artisan is reconfigured to use it — nothing about the
present cascade changes when it is flashed.

**What it is.** The inlet setpoint becomes a **sum of two independently
commanded numbers**: a *base*, which Artisan replays open-loop from the
background as the feedforward schedule, and a *trim*, which the outer PID drives.
The firmware adds them; neither side needs to know about the other.

```
INLET <degC>        sets the base   (unchanged command, unchanged semantics)
INLET TRIM <degC>   sets the trim   (new; -INLET_TRIM_MAX_C .. +INLET_TRIM_MAX_C)
INLET TRIM          reports base, trim and the effective setpoint
effective SV = clamp(base + trim, INLET_SV_MIN_C, INLET_SV_MAX_C)
```

**Shape of the change.** `inletSV` keeps its present meaning — *the effective
setpoint* — so `controlStep()`, `feedforward()`, the OLED, `STAT`, the status
push and the `getData` `SV` node all keep working untouched. What is new is
`inletBase` and `inletTrim` upstream of it, plus one place that recomputes
`inletSV` from the pair. `engageInlet()` currently returns early when already in
`MODE_INLET` (deliberately, so a retarget does not re-seed the integrator); that
early return is the natural home for the recompute, but the bumpless-transfer
seeding must use the **effective** setpoint, not the base.

**Zeroing, and why it is not optional.** A stale trim is a stuck heat offset.
`inletTrim` returns to 0 on `INLET OFF`, on `INLET <= 0`, in `inletFailsafe()`,
on entry to `MODE_TUNE`, and at boot — everywhere `MODE_INLET` is left or the
loop lets go.

**Staleness timeout.** In `MODE_INLET`, if the trim has not been refreshed for
`INLET_TRIM_STALE_MS` (15 s, against a 1 Hz outer loop), `controlStep()` ramps it
toward 0 at `INLET_TRIM_DECAY_CPS` (2 degC/s) and logs once. **Toward zero is the
correct direction and it is not the same as "safe"**: the base schedule keeps
running, so the roaster falls back to open-loop feedforward rather than to no
heat — which is the intended degraded mode, and is why the ramp is gentle rather
than a snap. Note the trim can be *negative*, so decaying it can raise the
effective setpoint; the clamp and the existing inlet failsafes are what bound
that, not the sign of the decay. **Command staleness on the *base* is
deliberately out of scope** — the firmware holds the last `INLET` indefinitely
today and changing that is a roast-safety decision of its own, not something to
smuggle into this change.

**Auth tier: all forms of `INLET TRIM` are `TIER_DRIVE`.** `INLET TRIM 0` looks
safety-increasing and is not — a negative trim removed raises the setpoint — so
it does not get the `INLET 0` / `INLET OFF` exemption. `cmdTier()` already falls
through to `TIER_DRIVE` for an unparseable `tokens[1]`, so the correct behaviour
is the default; make it explicit anyway so the reasoning survives.

**Telemetry.** `base` and `trim` join the status push and `STAT`. The `getData`
`SV` node keeps reporting the **effective** setpoint, so no Artisan-side change
is needed and the v0.19.0 `SV` channel keeps meaning what § Roast 46 refit
assumes it means. Check every `snprintf` buffer that grows.

**Artisan side, for reference — no firmware dependency.** `specialeventplayback`
is per event type (canvas.py:1848), so background playback drives the base on one
slider while `pidPositiveTarget` (any of sliders 1-4, pid_control.py:1252) points
the PID at a second slider bound to `INLET TRIM {}`. That is the collision that
forced playback off for the cascade (§ Background event playback must be off),
and putting the two on different sliders is what dissolves it. The base curve is
authored by `artisan/make_inlet_background.py`, kept unmodified for exactly this
path. **Do not configure any of this until steps 3-5 have measured `1/a` and the
loss curve** — the schedule *is* those two things.

**Acceptance.** Compile-verified via `./verify.sh`; bench-checkable with the
heater cold — `INLET 200` then `INLET TRIM 20` must show an effective 220 with no
integrator step, `INLET TRIM -20` an effective 180, `INLET TRIM` alone must
report all three, silence for 15 s must ramp the trim out, and `INLET OFF`,
`INLET 0` and a forced failsafe must each leave the trim at 0. No behaviour
change on any path that does not send `INLET TRIM`.

**As built (2026-09-06).** `inletBase` / `inletTrim` sit upstream of `inletSV`
and `inletEffectiveSV()` is the single place the two are combined — every
assignment to `inletSV` goes through it, so the pair can never disagree with the
setpoint the loop is holding. `engageInlet()` takes the base, and its
already-in-`MODE_INLET` early return is where the recompute lives; the
bumpless-transfer seed on the manual→inlet edge uses the effective setpoint.
`clearInletTrim()` is called from `INLET OFF`, `INLET <= 0`, `inletFailsafe()`
and `startTune()`; the boot value is the static 0. The staleness ramp sits in
`controlStep()` after the `dt` clamp and before the error is formed, logs once
via `logError()`, and broadcasts status once when the trim reaches 0 rather than
on every 4 Hz tick. `cmdTier()` returns `TIER_DRIVE` for `a1 == "TRIM"`
explicitly (the fall-through already did, since `"TRIM"` does not parse as a
float). Buffers: status push 176 → 224 (worst case 168), `STAT` 112 → 176
(worst case 127), the new `inlet` report 128 (worst case 86). Dashboard gains a
`base + trim = SV` readout and a trim entry/0/Read row in the Setpoint panel,
fed by the status push (no connect-time `INLET TRIM` prefill — that command is
`TIER_DRIVE`, and the device already broadcasts status on connect). README:
command table, tunables table, status-push field table, `STAT`, the auth safe
subset, and a new § Base + trim. **Bench drill: § NEXT item 14** — the
acceptance list above has not been run on hardware.

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

1. **Trustworthy theta, tau and gain.** The current values come from a flat ridge
   (§ Scheduling) and are not good enough to predict with. Run Tests A and B
   first.
2. **A bound on the correction.** Clamp `|BTP - BT|` to something like 10 degC so
   a diverging model degrades to plain BT rather than running the roaster open
   loop on a wrong prediction.

**Not worth doing: moving the outer loop into firmware.** The only reason would
be to enable the predictor, and the channel route achieves that without it. The
1 Hz WebSocket link is not a limitation — 1 s against 17 s of deadtime — and the
background curve authoring belongs in Artisan's Designer.

#### Still wanted, independent of the control problem

**Instrument the dump lever** (already noted in § Auto-DROP detection): expose it
as an extra channel and alarm on it, turning DROP from an RoR-collapse inference
into a measured event. The RoR margin is currently ample but roast-dependent
(-10.4 to +5.4 across the armed windows seen so far), and DROP drives the whole
heat-off chain.

### Roast 46 (2026-09-05, 19:48) — step 1 passes; the ramp is solved, the dip is not

Step 1 of the runbook, run exactly as specified: `airRoaster_cascadePID.aset`
unmodified (`pidKp` 3.0, `pidKi` **0.07**, `pidKd` 0, `svLookahead` **3**, floor
140 / ceiling 300, `createEvents` true), background **profile_003**, ON -> PID on
-> PID-driven preheat -> CHARGE, no intervention. 400 g in / 355 g out. The only
config drift in the saved `.aset` is `batchcounter`. Dashboard CSV captured;
aligned to the `.alog` by cross-correlating CSV `BT` against profile `BT`,
**residual rms 0.13 degC**, CHARGE at 23:48:07.85Z.

**Fan was deliberately held constant through the roast** (60, with the operator's
usual 63-64 blip over 0:09-1:26), so nothing in the trace below is air-schedule
disturbance. The fan steps the operator did make are all in preheat and are
analysed separately at the end.

#### Scorecard against the step-1 checklist

| # | criterion | result | |
|---|---|---|---|
| 1 | time to BT 120/150/180/196.5 vs profile | **+8.5 / +3.4 / +4.9 / +4.8 s** | pass |
| 2 | quiet-window error 3:10-4:20, 5:40-6:40 under ~1 degC | **-1.02, -0.80 degC** | pass |
| 3 | is the 177 s ring still there? | **no** | pass |
| 4 | no SV reversal over 10 degC after 1:00 | SV **monotone**, worst drawdown 0.7 degC | pass |
| 5 | floor time at the charge dip, predicted 0 s | **11 s** (0:00-1:04) | **fail** |
| 6 | inner loop rms ~1 degC, heat off both rails | **1.25 degC** after 1:00; 4 s at 100%, 1 s at 0% of 430 | pass |

Item 1 is the yardstick that matters, and the comparison is with **roast 44**,
the other 400 g batch: roast 44 lagged profile_002 by +8.9 to +13.9 s over the
same BT range, roast 46 lags profile_003 by **+3.4 to +5.9 s**. (Roast 45 is not
a fair comparison — 345 g.) Marks: DRYe 3:14 vs the profile's 3:12, FCs 6:44 vs
6:39, DROP 7:09 vs 7:05 at BT 200.8 vs 201.5.

**Item 3 is emphatic.** The PID error (`target(t+3) - BT`) peaks at **+6.12 at
2:10** and then decays **monotonically** to +1.06 at 6:40. Extremum-finding on the
15 s-smoothed trace after 3:30 returns only quantisation wiggle at **+/-0.05
degC** — against roast 45's 2.82 degC peak-to-peak at a 177 s period. Ki 0.07
bought the predicted ~30 deg of margin and the lightly-damped mode is gone.

#### The residual above DRY END is pure type-1 ramp error, and Kp is not in it

From 3:00 on the tracking error is remarkably flat: BT sits **1.0 degC below**
the background (mean -1.02 in 3:10-4:20, -0.80 in 5:40-6:40), equivalently **4-5
s behind**. Reconstructing the outer loop's integrator from the commanded SV
(`duty = (SV-140)/1.6`, `Iterm = duty - Kp*err`) shows `Iterm` climbing 41.9 ->
61.8 over 3:30-7:00, i.e. **dI/dt = 0.095 duty/s**, still monotone — the loop is
tracking a ramp, exactly as § Roast 44 outer-loop analysis found.

```
e_ss = (dI/dt) / Ki = 0.095 / 0.07 = 1.36 degC of PID error
```

`svLookahead = 3` already cancels `3 x 0.2275 = 0.68 degC` of that at the
mid-roast background slope, leaving **~1.0 degC** — which is what the profile
comparison measures. The prediction in § profile_003 was +0.59 degC at Ki 0.07 /
L=3; the outturn is 1.0 because a 400 g batch demands a steeper `dI/dt` than the
roast-45-fitted plant. **Kp appears nowhere in `e_ss`.**

#### The measured optimum lookahead is 6 s — the step-6 file is already right

Required lead is `L = e_ss(t) / (background slope at t)`, evaluated per sample:

| t | 3:00 | 3:40 | 4:00 | 4:40 | 5:20 | 6:00 | 6:40 |
|---|---|---|---|---|---|---|---|
| background slope (degC/s) | 0.343 | 0.296 | 0.276 | 0.240 | 0.208 | 0.180 | 0.157 |
| `e_ss = (dI/dt)/Ki` (degC) | 2.51 | 1.60 | 1.46 | 1.66 | 1.51 | 1.17 | 0.94 |
| **L needed (s)** | 7.3 | 5.4 | 5.3 | 6.9 | 7.3 | 6.5 | 6.0 |

Mean **6.3 s** over 3:00-7:00. `artisan/airRoaster_cascadePID_lookahead.aset`
switches 0 -> **6** at CHARGE+90 s (§ The lookahead-switching config). That value
was chosen before this roast on margin grounds and the data independently picks
it out. Nothing needs re-deriving; the file needs running.

**A constant L=6 is not an option**, which is why the switch exists. Replaying
roast 46's own BT against the background at each L:

| L | 0 | 1 | 2 | **3** *(run)* | 4 | 6 |
|---|---|---|---|---|---|---|
| worst dip error (degC) | -9.9 @0:56 | -9.1 @0:56 | -10.6 @0:01 | **-13.9 @0:01** | -17.1 @0:01 | -23.0 @0:01 |
| `Kp*|e|` back-calculation preload | 29.7 | 27.4 | 31.7 | **41.7** | 51.2 | 69.1 |

Below L=2 the worst error is no longer the charge cliff at all — it is the 400 g
dip mismatch at 0:56 (below). **L=0 is genuinely the best choice through the
dip**, so the switching config improves the dip as well as the ramp.

**One thing to expect when it runs.** At CHARGE+90 s the background slope is
0.680 degC/s, so the 0 -> 6 switch is a **+4.08 degC target step -> +12.2 duty of
P -> a ~+20 degC jump in the commanded inlet SV**, in one 1 Hz tick. The inner
loop swallows a 20 degC setpoint step in about 5 s (see item 6), so this is a
visible bump, not a hazard. If it reads badly on the roast, the gentler shape is
**0 -> 3 at 1:30 (a +9.8 degC SV step) and 3 -> 6 at 3:00 (+4.9 degC)** — three
buttons and three alarms instead of two, regenerated the same way with
`tools/gen_pid_alarm_asets.py`. Run the file as generated first; one variable.

#### Item 5 failed, and the cause is the batch size, not the loop

profile_003's TP was matched to **roast 45 at 345 g**. Roast 46 was **400 g**:

| | profile_003 | roast 46 |
|---|---|---|
| TP | 67.4 degC at 0:37 | **57.6 degC at 0:21** |

9.8 degC deeper and 16 s earlier. § profile_003 predicted this in the box headed
*"the TP match is batch-specific"* (roasts 43/44 at 400 g bottomed at 58.8/60.2)
and roast 46 lands right on that prediction. The consequences are the whole of
the first three minutes:

- PID error swings **+16.6 at 0:17 to -13.9 at 0:01** — a 30.5 degC swing in
  twenty seconds, essentially all of it manufactured by the profile mismatch.
- Commanded SV goes **rail to rail, 261 degC at 0:20 down to the 140 floor at
  0:56-1:04** (the 11 s of item 5).
- At the floor, `_back_calculate_integral` re-seeds `Iterm` to `Kp*|err|` ~ 30
  (pid.py:314-333) — the mechanism from § Roast 44 outer-loop analysis, now
  observed a third time.
- BT consequently overshoots the background by **+9.3 degC at 1:00**, then the
  unwind puts it **4.0 degC behind at 2:00-2:20**, and the loop only recovers to
  its steady 1 degC lag by 3:00.

So the ramp is solved and the dip is not. **The fix is a background whose dip is
a 400 g dip**: profile_004, taking 0:00-1:30 from roast 46's own measured BT and
keeping profile_003's ramp and finish unchanged. That removes ~30 degC of
manufactured error, the rail-to-rail SV excursion, the floor time and the
preload, in one edit, and it is the same operation that produced profile_003 from
profile_002.

#### The firmware's feedforward is saturated and has been doing nothing

New, and unrelated to the outer loop. The dashboard CSV reports `FF = 100.0` for
**430 of 430 samples** from CHARGE to DROP, and for all of preheat above SV ~140.
Fitting `feedforward()`'s model to the three unclamped samples (fan 53, SV
130/140.5/144 -> FF 84.7/93.1/96.0) recovers **`ffK` ~ 0.0151, `ffAmbient` ~
24.1 degC** — which at roast conditions (fan 60, SV 240) predicts **196% heat**
against an actual demand of 55%.

Consequences, none of them fatal but all of them worth clearing before Tests A-C:

- The term is a **constant +100** for the entire roast, so `pidITerm` sits at
  **-45 to -64** to cancel it, and the anti-windup bound `I ∈ [-ff, 100-ff]`
  collapses to `[-100, 0]` — the integrator can never be positive.
- **The fan compensation it exists for is dead.** `d(FF)/d(fan) = 0` while
  clamped, so every fan step is absorbed by the integrator instead. This is
  precisely the mechanism Test C is meant to measure.

The model form is also wrong for this roaster, not just the gain — see the
preheat measurement below.

#### The preheat fan steps: 0.99 % heat per fan unit

Five clean fan steps during preheat, empty roaster, inner loop closed, inlet SV
140-165. Heat before (20 s mean) vs after (the 25-45 s window):

| t | fan | heat | d(heat)/d(fan) | worst \|IN-SV\| in the 30 s after |
|---|---|---|---|---|
| -4:22 | 53 -> 64 | 37.3 -> 46.2 | 0.81 %/unit | 7.2 degC |
| -3:16 | 64 -> 60 | 46.2 -> 42.4 | 0.97 | 1.5 |
| -2:20 | 60 -> 53 | 42.5 -> 36.5 | 0.86 | 3.6 |
| -1:33 | 53 -> 55 | 36.5 -> 38.7 | 1.11 | 1.3 |
| -0:51 | 55 -> 60 | 37.8 -> 42.3 | 0.89 | 2.1 |

OLS over the whole preheat window (n = 300 s, inlet mode):

```
heat = -30.62 + 0.992*fan + 0.0096*SV        residual rms 1.85 %
```

**0.99 % heat per fan unit** — five independent steps spanning 0.81-1.11 agree
with the regression to within the noise. This is the first properly measured fan
number in the project; § Fan vs batch size and § Correction had only a regression
coefficient inside a loaded-roast fit.

The SV coefficient is weakly identified (SV moved only 140-165, and the outer
loop moved it *in response to* the fan) but its magnitude is the point:
**~1 % of heat per 10 degC of inlet setpoint**, against the feedforward model's
`ffK*fan = 0.0151*60 = 9.1 %` per 10 degC. The model form
`ffK * fan * (SV - ambient)` is **~9x too steep in SV and ~1.8x too steep in
fan**, and cannot represent a fit with a large negative intercept. Recalibrating
`ffK` alone cannot fix it; either the term needs the affine form
`a + b*fan + c*SV`, or `FF OFF` (`ffK = 0`) is the honest setting until it does —
which costs nothing today, since the term is a constant.

**The inner loop absorbed every one of these steps**, worst case 7.2 degC on the
largest (11-unit) step and 1.3-3.6 degC on the rest, with no outer-loop
involvement — the inlet was back on setpoint before the outer loop's next tick
mattered. That is the answer to whether the fan schedule needs feedforward help
at all: at these step sizes, no.

### Roast 46 refit — the plant, a validated simulator, and what to run next (2026-09-05)

Everything below comes from `tools/analysis/` (numpy + scipy; `roast46_refit.py`
reproduces the headline numbers). Inputs: `airRoaster_46.alog`, the dashboard CSV
`airRoaster_data_2026-09-05-23-57-34.csv`, background `profile_003.alog`, with
`airRoaster_4{4,5}.alog` for cross-checks. CSV aligned to the `.alog` by
cross-correlating BT: **CHARGE = 23:48:07.83Z, residual rms 0.112 degC** (the
figure in § Roast 46 was 23:48:07.85 / 0.13 on a coarser grid; same answer).

**Sign convention here**: tracking `error = background_BT(t) - BT(t)`, with *no*
lookahead in it, so **positive means BT is behind the background**. § Roast 46
quoted the same quantity with the opposite sign (`-1.02, -0.80 degC`).

#### 1. The refit, and why roast 46 could carry it when 44 and 45 could not

Model, as before, with the disturbance restricted to a low-order polynomial in
`t` and the delay floating:

```
dBT/dt = a * (Inlet(t - theta) - BT) + slow(t)
```

Two changes of method. First the estimator is **integral, not differential** --
integrate the model instead of differentiating BT, so the fit residual is in
degC of BT (noise 0.071 degC rms) rather than degC/s of a numerical derivative.
Second the fit window **starts after turning point but keeps the charge
recovery**, which is where the excitation is.

```
primary fit, window CHARGE+45 s .. DROP, disturbance order 4:

    a = 0.00490      tau = 204 s      theta = 13.5 s      residual 0.116 degC
```

**Uncertainty.** Two kinds, and the second dominates.

| | theta | a | tau |
|---|---|---|---|
| block bootstrap (60 s blocks, 200 draws, primary window) | 12.0 - 15.0 s | 0.00443 - 0.00540 | 185 - 226 s |
| across every well-conditioned window x order | **12.8 - 18.2 s** | **0.0034 - 0.0052** | **193 - 291 s** |

"Well-conditioned" means the residual at `theta = 0` is more than 2.5x the
residual at the minimum -- 11 of the 24 window/order combinations qualify, all of
them windows starting at or before 60 s. The primary fit's ridge depth is **3.9x**,
which is the difference from every previous attempt: the theta/tau ridge in
§ Scheduling moved tau fourfold for a 14% change in residual, this minimum is
sharp. Quote the plant as **theta 13 (+5, -1) s, tau 205 (+85, -15) s**.

**Roast 46 is the only one of the three that identifies anything**, and the
reason is the thing that failed check 5. The 400 g batch against a 345 g dip
drove the commanded SV rail to rail -- Inlet 141 -> 265 -> 140 -> 199 over the
first two minutes -- which is a large, fast, involuntary doublet. Roasts 44 and
45 recovered smoothly (Inlet 140 -> 160 -> 183 -> 195) and their fits collapse:
run through the same code they return `a < 0` at orders 3-5 on the 25 s window,
or pin theta at a grid edge. **The profile mismatch bought the excitation that
§ Scheduling proposed Tests A and B to obtain.** The 90 s-onward window of roast
46 collapses the same way (theta 7-9 s, `a` 0.0057-0.0105, ridge depth 1.1), so
the identifiability warning in § Scheduling stands for closed-loop body data --
it is the charge recovery that carries the information, not the roast.

**Against the earlier numbers.** theta 13-18 s brackets the 17 s that roasts 44
and 45 agreed on, so § Correction's central claim survives. What moves is `a`:
roast 44's 0.00829 (tau 121 s) and roast 45's 0.00364 (tau 275 s) straddle
0.00490 (tau 204 s), and the retracted `a = 0.0145 / tau 69 / theta 0` model is
4x worse on residual than the refit at the same window.

**No fan term is identifiable from roast 46 and none is needed** -- the fan sat
at 60 for the whole roast bar the operator's 63-64 blip over 0:09-1:26, which is
inside the charge transient. The ~49% of plant gain per 10 fan units from
§ Correction is untouched by this work; Test C is still the way to measure it.

#### 2. Artisan's PID, reimplemented and validated

`tools/analysis/artisan_pid.py` ports, function by function against v4.2.0:
`update` (pid.py:394-492), `_should_integrate` (286-297),
`_back_calculate_integral` (314-333), `applyIntegralLimits` (359-364),
`_calculate_derivative` (249-278), `getParameter` (370-387),
`_calculate_integral_limits` (44-63), `calcSV` (pid_control.py:1658-1717),
`smooth_sv` (1643-1655), `setEnergy` (1292-1324), the `decay_average` PV
(canvas.py:4613-4640), the background's own decay smoothing
(canvas.py:9878 -> `smooth_slice`, `decay_smoothing_p = (not optimalSmoothing)
or flagon`, so **the background target is itself delayed 0.667 s** at
`curvefilter = 3`), and the ordering that gives the loop a sample of its own
(`pid.update()` at canvas.py:5016, `calcSV`/`setSV` at canvas.py:5184). The
LiveSosFilter is rewritten rather than imported -- Artisan is AGPL and this
repository is MIT.

Two mechanisms had to be added before the replay would close, and both are new
to these notes.

**(a) The commanded SV is gated on an integer.** `setEnergy` computes
`raw_heat` (a float), rounds it, and emits `addRawEventSignal(heat, raw_heat, ...)`.
In `addEvent_internal` the slider action fires only when that **integer**
differs from the last one (`force` is `slider_force_move`, true only on PID ON),
and it is then the **float** that goes down the WebSocket. So the inlet setpoint
is a 1 degC staircase in *when* it updates, carrying full precision in *what* it
sends -- which is exactly what the CSV shows (213.50 held for 29 s, then 214.80).
Combined with `dutySteps = 1` and `force_duty = 3` (pid.py:197), that is the
whole update cadence.

**(b) autoCHARGE backdates CHARGE by three samples, and the target does not
move for those three seconds.** `autoCharge=true` in the `.aset`. At
canvas.py:5121-5126 the detection sets `autoChargeIdx = length_of_qmc_timex - b`
with `b` from `BTbreak` -- 3 for a tight break, 5 for a loose one (`btbreak_params`,
canvas.py:558-559). `timeindex[0]` is therefore written *retroactively*, but
`calcSV`'s pre-CHARGE branch (pid_control.py:1690) was still returning the
background's CHARGE BT while the detector was making up its mind. Roast 46 shows
it plainly: backing the required target out of the recorded T_inlet events gives
**128.3 - 129.1 degC for ticks 0-3** -- flat, and equal to `profile_003`'s CHARGE
BT of 128.0 -- and only from tick 4 does it follow the background. `b = 3` fits;
`b = 5` does not.

Without (b) the SV replay carries a **constant +21 degC** error for the entire
roast, because the three seconds of frozen target let the output clamp at the
floor, and `_back_calculate_integral` pumps `Iterm` to `Kp*|err|` and it never
comes back. With it:

```
measured BT + profile_003 -> commanded SV,  Kp 3.0 / Ki 0.07 / L 3 / Iterm(0) = 8

     0-30 s   mean  +7.19   rms 12.08     (the charge cliff; SV slews 30 degC/s)
    30-120    mean  -0.34   rms  1.23
   120-240    mean  -0.05   rms  0.58
   240-430    mean  +0.07   rms  0.45
    30-430    mean  -0.06   rms  0.73 degC
```

0.73 degC of SV is 0.46 duty, and the slider's own 1 degC integer gate is worth
0.29 rms on its own -- **the replay is at the resolution of the data.** The
0-30 s window cannot be checked at this level and never will be: one second of
alignment error there is 30 degC of SV.

The same replay recovers the loop's own arithmetic: `Iterm` climbs at **0.0946
duty/s** over 3:30-7:00, so `e_ss = (dI/dt)/Ki = 1.35 degC`, against § Roast 46's
0.095 and 1.36 read off the reconstruction. Nothing there changes.

#### 3. Closed loop: the simulator reproduces roast 46 to 0.16 degC

`sim.py` closes the loop -- background -> PID -> inlet SV -> inner loop -> plant --
with the inner loop identified from the CSV as **tau 0.76 s, delay 0.25 s**
(rms 1.19 degC, essentially all ripple rather than lag, which is the fourth
independent confirmation that the inner loop is not a factor). The disturbance
comes from `fit_disturbance`, which relaxes `slow(t)` onto a cubic B-spline
**with `a` and `theta` held at the values fitted above** -- the plant estimate
stays non-circular, the simulator gets a full-roast disturbance including the
charge recovery.

```
closed-loop replay of roast 46 from CHARGE+2 s:

   BT   mean -0.033   rms 0.159   max 0.96 degC        (whole roast)
          2-30 s  rms 0.33     60-120 s  rms 0.16
         30-60 s  rms 0.30    120-240 s  rms 0.15    240-430 s  rms 0.07
   SV   rms 1.00 degC (t >= 30 s);  TP 57.4 vs 57.6;  SV max 262.2 vs 261.2
```

For comparison the roast-44 simulator managed rms 0.33 degC on the body alone.

**The cross-check that matters: it also produces roast 45's ring.** Take the
roast-46 plant unchanged, refit only the disturbance to roast 45, run the loop at
**Ki 0.10** against `profile_002`:

| | 1st extremum | 2nd | 3rd | 4th | period |
|---|---|---|---|---|---|
| measured roast 45 | 127 s, +3.70 | 209 s, +0.53 | 303 s, +1.94 | 384 s, +0.03 | 177 s |
| simulated | 128 s, +3.62 | 210 s, +0.42 | 306 s, +2.05 | 384 s, -0.10 | ~170 s |

Closed-loop BT rms 0.28 degC over roast 45. So **one plant explains both roasts**:
the ring at Ki 0.10 and its absence at Ki 0.07. The earlier §-Correction plant
(`a` 0.00364, theta 17) predicted a 230 s period, 30% long; this one is 4% short.

Two consequences for § Correction. Its frequency-domain table is superseded (the
new margins are in the next section, and they are **more** generous, not less).
And the `zeta ~ 0.07` read off the log decrement was an underestimate of the
loop's damping -- the simulator reproduces the same extrema with a plant whose
linear zeta at Ki 0.10 is 0.27, because most of what decays in that trace is the
charge transient, not a self-sustained mode.

#### 4. Phase margin against the refitted plant

`L(s) = (Kp + Ki/s) * 1.6 * a/(s+a) * exp(-(theta + 2.67) s)`. The 2.67 s is the
inner loop (1 s), BT decay smoothing (0.67 s) and the one-sample `update`/`setSV`
ordering (1 s), all outside the identified `theta`. Actuator gain 1.6 degC of
inlet per duty unit, confirmed from the `.aset`: `positiveTargetMin/Max` 140/300
against `slidermin/max` 0/320 for slider 3, so `setEnergy`'s
`heat_min/heat_max` are 140 and 300.

| `pidKi` | 0.05 | **0.07** | 0.09 | 0.10 | 0.12 | 0.15 |
|---|---|---|---|---|---|---|
| PM, primary fit (a .00490, th 13.5) | 43.5 | **33.7** | 25.9 | 22.6 | 16.6 | 9.2 |
| PM, low-delay edge (a .00589, th 10) | 49.9 | 40.7 | 33.3 | 30.1 | 24.4 | 17.3 |
| PM, high-delay edge (a .00386, th 18) | 36.5 | 26.1 | 18.0 | 14.6 | 8.5 | 0.9 |
| crossover period, primary (s) | 231 | 213 | 197 | 190 | 178 | 164 |

**Ki 0.07 buys 26-41 deg depending on where in the envelope the plant sits**,
against § Correction's 27-30 deg -- the same answer, now with a fit that also
reproduces the time domain. Ki 0.10 is 15-30 deg, which is where roast 45 rang.

#### 5. Predictions

All from the validated simulator, roast 46 conditions (400 g, fan 60, Kp 3.0,
Ki 0.07 unless stated), disturbance from roast 46, run from CHARGE+2 s. The
baseline row is the check: it reproduces roast 46's measured
`dt150/dt180/dt196.5 = +3.4/+4.9/+4.8 s` and its steady error.

##### (a) svLookahead -- yes, the lag goes to zero, and run the file as generated

Constant lead, and the switching schedules. `dt` is time to that BT minus
`profile_003`'s own; `ss` is the steady tracking error over 3:00-7:00;
`Idip` is the peak `Iterm` reached in the charge dip.

| config | dt150 | dt180 | dt196.5 | ss mean/rms | lag | floor | Idip | SV reversal |
|---|---|---|---|---|---|---|---|---|
| **roast 46 as run, L=3** | +3.5 | +5.0 | +4.4 | +0.75 / 0.77 | +3.4 s | 4 s | 34.4 | 0.3 |
| L=4 constant | +2.8 | +4.0 | +3.3 | +0.57 / 0.59 | +2.6 s | 1 s | 35.8 | 0.0 |
| L=6 constant | +1.5 | +2.2 | +1.0 | +0.22 / 0.28 | +0.9 s | 2 s | 41.1 | 0.0 |
| L=8 constant | +0.7 | +0.2 | -1.2 | -0.10 / 0.31 | -0.7 s | 2 s | 49.1 | 0.6 |
| **the step-6 file: 0 @ 1 s, 6 @ 90 s** | -1.9 | +3.2 | +0.9 | **+0.05 / 0.49** | **+0.44 s** | 16 s | 43.3 | 3.2 |
| 6 @ 90 s only (keep L=3 in the dip) | -1.4 | +3.1 | +1.1 | -0.01 / 0.46 | +0.26 s | 4 s | 34.4 | 3.5 |
| two-stage 0 @ 1, 3 @ 90, 6 @ 180 | +3.2 | +1.1 | +1.8 | +0.12 / 0.31 | +0.53 s | 16 s | 43.3 | 0.0 |

**The 1.0 degC / 4-5 s steady lag goes to +0.05 degC / 0.44 s.** That is the
headline and it holds across the whole plant envelope (theta 10 -> 18, `a` +-12%
move `ss` by less than 0.05 degC, because `e_ss = (dI/dt)/Ki` barely involves the
plant).

**The transient at 1:30, measured against the un-switched counterfactual:**
target step **+4.01 degC**, commanded SV **+24.7 degC** above where it would have
been, peaking at 1:46 and settled by ~1:42-2:00; BT ends up +4.2 degC higher than
without the switch, by 2:50. § Roast 46 predicted +4.1 degC and ~+20 degC; the
target step is exact and the SV excursion is a quarter larger. Not a hazard --
the inner loop swallows a 20 degC step in about 5 s -- but it is a visible kick.

**Is the two-stage alternative meaningfully better? No.** It halves the one-tick
jump (8.3 vs 14.8 degC) and removes the 3.2 degC SV drawdown, and its steady rms
is 0.31 against 0.49, but its *mean* steady error is no better and it costs two
more buttons and one more alarm. Three- and four-stage schedules
(`0,4@90,7@240`; `0,6@90,9@300`; `0,3@90,6@180,9@300`) were swept and none beats
the single switch by more than 0.1 degC rms. **Run the file as generated.**

**One thing in the file is pointed the wrong way against `profile_003`.** The
`pidLookahead(0)` alarm at CHARGE+1 was justified in § Roast 46 by a static
replay that put the worst dip error at 0:01, on the charge cliff. In closed loop,
and with autoCHARGE's three-second backdate removing most of that cliff, L=0 is
the *worse* choice through the dip: the target then lags a background that is
still falling, so the SV is held low longer -- floor time 16 s against 4 s,
Idip 43.3 against 34.4, and BT ends up 14.2 degC below the background instead of
10.5. It costs nothing after 1:30 and it does not change the headline. It is also
**exactly right once `profile_004` exists** (below), which is why the file should
be run unchanged rather than edited.

The required lead is not constant, which is why no single number is right:
`L = e_ss/slope` is 3.9 s at 3:00, 4.9 at 4:00, 6.0 at 5:00, 7.5 at 6:00, 9.2 at
7:00 (mean 6.3 over 3:00-7:00, reproducing § Roast 46's table). L=6 is exact at
5:00, short at the end, long at the start.

##### (b) Ki -- 0.07 is both the ceiling and the optimum; there is no room above it

With the lookahead carrying the tracking (L 3 -> 6 @ 90 s):

| `pidKi` | 0.05 | **0.07** | 0.09 | 0.10 | 0.12 | 0.15 |
|---|---|---|---|---|---|---|
| ss mean / rms (degC) | +0.75 / 0.80 | **-0.01 / 0.46** | -0.44 / 0.87 | -0.59 / 1.07 | -0.88 / 1.49 | -1.17 / 2.04 |
| error peak-to-peak | 2.91 | 3.93 | 4.82 | 5.19 | 5.88 | 6.54 |
| SV reversal (degC) | 1.4 | 3.5 | 7.7 | 12.2 | 19.4 | 32.0 |
| rms with theta +14 s | 1.36 | **1.14** | 1.87 | 2.72 | 4.50 | 7.59 |
| rms with gain +50% | 0.84 | **0.23** | 0.63 | 0.87 | 1.37 | 2.26 |

**No.** Once L=6 is doing the feedforward the standing error is already zero at
Ki 0.07, so more integral gain does not remove a lag -- it *overshoots* (`ss` goes
negative), and it degrades under every plant perturbation tested. Ki 0.07 is the
best value in the table on the nominal plant, under +14 s of extra delay and
under +50% of plant gain. **Treat 0.07 as settled, not as a compromise.**

##### (c) Kp 3.0 stands

| `pidKp` | 1.5 | 2.0 | 2.5 | **3.0** | 4.0 | 5.0 |
|---|---|---|---|---|---|---|
| ss rms, nominal | 0.40 | 0.29 | 0.33 | **0.46** | 0.56 | 0.50 |
| ss rms, theta +14 s | 1.14 | 0.54 | 0.52 | **1.14** | 2.41 | 4.32 |
| ss rms, gain +50% | 1.69 | 0.85 | 0.38 | **0.23** | 0.19 | 0.39 |
| ss rms, gain +50% and theta +7 s | 3.15 | 1.67 | **0.52** | 0.56 | 1.44 | 3.32 |
| dip preload `Idip` | 36.1 | 35.4 | 34.9 | 34.4 | 42.5 | 53.4 |
| PM at Ki 0.07 (deg) | 16.2 | 23.2 | 29.1 | **33.7** | 39.1 | 39.9 |

**Confirmed, with one refinement.** § Correction's rule -- lowering Kp makes a
delay-limited loop worse -- holds for Kp <= 2.0, which is worst in the two
gain-error columns and has the least phase margin. It is *overstated* for 2.5:
on this plant Kp 2.5 is the single most robust value across the four stress
cases. The margin between 2.5 and 3.0 (0.52 vs 0.56 rms on the worst case) is
inside the model error, and 3.0 is roast-validated. **Keep 3.0. Do not lower it
below 2.5, and do not raise it above 4.**

##### (d) pidKd 40 with DoE -- no, and this settles the disagreement

`pidKd` swept with `pidDsetpointWeight = 1` (DoE) and `derivative_filter = 1`:

| `pidKd` / gamma / filter | ss mean/rms | p2p | `Idip` | floor | rms, theta +14 | SV ripple at 0.35 degC BT noise |
|---|---|---|---|---|---|---|
| **0 / 0 / 0 (as run)** | -0.01 / 0.46 | 3.93 | 34.4 | 4 s | 1.14 | **1.93 degC** |
| 20 / 1 / 1 | +0.09 / **0.20** | **1.69** | 33.1 | 1 s | 1.36 | 2.4 |
| **40 / 1 / 1** | +0.37 / 0.61 | 4.58 | **51.8** | 11 s | **2.56** | **10.25 degC** |
| 60 / 1 / 1 | +0.78 / 1.41 | 11.23 | 80.2 | 13 s | 3.15 | 26 |
| 40 / 1 / 0 | +0.28 / 0.46 | 2.94 | 98.6 | 11 s | 2.45 | 26.41 |

**`pidKd = 40` is not worth a roast, and the frequency-domain prediction that it
buys margin (29-46 deg in § Correction, 48 deg here) is an artefact.** In the
time domain it makes tracking worse, deepens the dip preload by half, puts 11 s
back on the floor, is the worst row but one under extra delay, and multiplies SV
ripple fivefold. § Correction already recorded that the two analyses disagreed
and refused to take it on that basis; the disagreement is now resolved against
`Kd = 40`, on a simulator that reproduces two roasts.

**`pidKd = 20` under DoE with the filter is the interesting row** -- best steady
rms in the whole study (0.20), least ringing (1.69), lower dip preload, and only
a quarter more SV ripple. It is still slightly worse than `Kd = 0` under extra
delay. Park it: it is a candidate for a later single-variable roast, well behind
the lookahead and `profile_004`, and it must not be combined with either.

##### (e) profile_004 -- it and the `pidLookahead(0)` leg belong together

> **Partly superseded, 2026-09-05.** Two things landed after this was written.
> Roast 46 was a **frozen** charge, so profile_004 encodes a frozen dip and its
> fragility points at *warm* charges, not cold ones (§ Charge temperature). And
> gating `Ki` off through the dip removes the sensitivity that made the dip shape
> matter at all (§ The dip is a different control problem). The ranking below is
> still right *at a fixed charge state*; it is no longer the thing to fix first.

`profile_004` simulated as specified in runbook step 1b: roast 46's own measured
BT for 0:00-1:30, blended into `profile_003`'s unchanged ramp over the following
20 s. TP becomes **57.6 degC at 0:22** instead of 67.4 at 0:37.

| background / lookahead | dip PID error | SV min | floor | `Idip` | `Iterm` at 1:30 | 1:30-3:00 error | ss mean/rms |
|---|---|---|---|---|---|---|---|
| profile_003, L=3 *(roast 46)* | -8.8 | 140.0 | 4 s | 34.4 | 15.8 | +4.09 / -1.68 | +0.75 / 0.77 |
| profile_003, file (0 @ 1, 6 @ 90) | -14.7 | 140.0 | 16 s | 43.3 | 23.4 | +1.47 / -4.01 | +0.05 / 0.49 |
| profile_004, L=3 | -11.9 | 140.0 | 3 s | 45.2 | **41.0** | +2.06 / **-9.13** | +1.21 / 1.47 |
| **profile_004, file (0 @ 1, 6 @ 90)** | **-2.6** | **143.9** | **0 s** | **30.4** | 29.7 | -0.64 / -3.61 | **+0.18 / 0.39** |

Read the last two rows together: **`profile_004` on its own, at the present
`svLookahead = 3`, makes the roast worse** -- its dip is steeper and 15 s earlier,
so three seconds of lead against a fast-falling curve manufactures a bigger
negative error, hands over `Iterm = 41` instead of 16, and puts a 9.1 degC
undershoot into 1:30-3:00. With `L = 0` through the dip, which is what the step-6
file already does, the same background is the best configuration in this whole
study: **the output never reaches the floor at all**, the worst dip error falls
from -8.8 to -2.6 degC, the preload falls to 30, and the steady error is
+0.18 degC / 0.39 rms with no SV reversal anywhere.

So the two changes are not independent and the order matters:

- **`profile_004` must not be run at a constant `svLookahead = 3`.** Run it only
  with the lookahead-switching config.
- Equally, the `pidLookahead(0)` leg of that config is mildly counterproductive
  against `profile_003` (16 s on the floor instead of 4) and clearly right
  against `profile_004`. Leaving it in place is what lets step 6 and step 1b
  compose.

#### 6. Ranked recommendation

1. **Run step 6 exactly as the runbook has it** -- `airRoaster_cascadePID_lookahead.aset`
   unmodified, background `profile_003`, everything else at roast 46's settings.
   Predicted: `dt150/dt180/dt196.5 = -1.9 / +3.2 / +0.9 s`, steady error
   **+0.05 degC (0.44 s)** against roast 46's +0.75 degC (3.4 s), a +4.0 degC
   target step and ~+25 degC of SV at 1:30 settling within ~15 s, 16 s at the
   140 floor in the charge dip (roast 46 had 11 s), SV max ~296, no reversal
   over 3.3 degC after 1:00. One variable, and it is the one with the largest
   predicted improvement.
2. **Then `profile_004`, with the same lookahead config.** Predicted: floor time
   **0 s**, dip error -2.6 degC, handover `Iterm` 30, steady error +0.18 degC /
   0.39 rms, `dt150/dt180/dt196.5 = -0.3 / +2.7 / +0.7 s`. This is the best
   configuration found. Do not run it at `svLookahead = 3`.
3. **Leave `pidKi` at 0.07 and `pidKp` at 3.0.** Both are now optimal rather than
   compromises, on the nominal plant and under every perturbation tested. The
   open question in § Roast 46 -- whether there is room above 0.07 once the
   lookahead carries the tracking -- is answered: no, and no need.
4. **Drop `pidKd = 40` from the plan.** Keep `pidKd = 20` under DoE with
   `derivative_filter = 1` on the list as a low-priority single-variable
   experiment, after 1 and 2.
5. **Tests A/B/C keep their value, for a reason that has changed.** They are no
   longer needed to *find* theta -- roast 46 pins it to 13 (+5, -1) s with a
   sharp minimum. They are needed for the fan (Test C is still the only way to
   turn ~49% of plant gain per 10 fan units into a measurement) and to check that
   the plant identified from one involuntary doublet holds under a deliberate
   one. Their priority drops below steps 6 and 1b.

#### 7. Caveats

- The charge dip is the weak part of the simulation. The 0-30 s SV replay is out
  by up to 33 degC (one second of alignment error is 30 degC there), floor times
  are good to about +-10 s (the sim gives 4 s where roast 46 measured 11), and the
  disturbance through the recovery is a spline fitted to roast 46 rather than
  anything physical. Dip *rankings* in the tables above are trustworthy; dip
  absolute numbers are not.
- Everything is fitted to a single 400 g batch of one coffee at fan 60. The
  plant envelope tested (theta 10-18 s, `a` +-12%, plus the +50%-gain and
  +14 s-delay stress cases) is wider than the fit uncertainty, and the ranking of
  the options does not change inside it -- but a much smaller charge is outside
  it, as § Roast 46 already found the hard way.
- `slow(t)` absorbs drying, exotherm and probe/bed equilibration together. It is
  exogenous to the controller, so using it in a closed-loop what-if is sound, but
  it is roast-46's disturbance, not a general one.

### The dip is a different control problem — gate Ki through it (operator, 2026-09-05)

Operator question: *"there must be a way to let some coarse parameters ride
through the initial stage, and then change tuning after the initial
equalization."* **Yes, and it is the single most valuable change found so far.**
The earlier "no" in § Scheduling was to *gain scheduling for the ramp*, on the
grounds that the plant moves by only +-6% across a roast. That answer stands and
it is not this question. The dip and the ramp are not two operating points of one
control problem, they are two different problems, and the thing that connects
them — the integrator handed over at 1:30 — is exactly what has been going wrong.

#### The mechanism: `Ki = 0` freezes the integrator completely

`_back_calculate_integral` (pid.py:314-333) is gated on **`if self.getKi(PV) != 0`**.
So setting `Ki = 0` closes *both* windup paths at once: the `Ki*err*dt` term
contributes nothing, and back-calculation does not run, so the output can sit on
the floor or the ceiling for as long as it likes without `Iterm` moving. With
`beta = 1` and `Kd = 0` the loop through the dip is then **pure proportional with
a frozen bias** — which is what "coarse parameters riding through the initial
stage" should mean.

`p-i-d(<p>,<i>,<d>)` (main.py:10759 -> `confPID` -> `pid.setPID`) only assigns the
three gains; `Iterm` is untouched, so both switches are bumpless. Wiring is the
same pattern `tools/gen_pid_alarm_asets.py` already generates:

```
alarm, from CHARGE, offset  1 s, source -3 (time only) -> button: p-i-d(3,0,0)
alarm, from CHARGE, offset 90 s, source -3 (time only) -> button: p-i-d(3,0.07,0)
```

#### What it does: the roast stops caring about the charge state

Simulated on the validated model, step-6 lookahead in place, sweeping the charge
temperature over a **62 degC range** (the sweep is relative to roast 46's own
charge, so it brackets freezer-to-room whichever end that sat at). `I@1:30` is the
integrator handed to the ramp:

**profile_004, `Ki` as now (0.07 throughout):**

| charge, relative | +20 warmer | roast 46 | 22 colder | 42 colder |
|---|---|---|---|---|
| `I@1:30` | 22.7 | 29.7 | **59.2** | 54.0 |
| worst error 1:30-3:00 | -6.41 | -3.61 | **-14.50** | -7.38 |
| steady error mean/rms | +0.25 / 0.37 | +0.18 / 0.39 | +0.68 / 1.18 | +0.39 / 1.07 |
| time to BT 150 vs profile | +3.5 s | -0.3 s | +5.3 s | -3.9 s |

**profile_004, `Ki = 0` until 1:30:**

| charge, relative | +20 warmer | roast 46 | 22 colder | 42 colder |
|---|---|---|---|---|
| `I@1:30` | **7.9** | **8.1** | **8.1** | **8.2** |
| worst error 1:30-3:00 | -1.54 | +0.30 | +0.25 | +0.05 |
| steady error mean/rms | +0.01 / 0.36 | -0.03 / 0.41 | -0.03 / 0.42 | -0.04 / 0.44 |
| time to BT 150 vs profile | +1.3 s | +0.1 s | -0.0 s | -0.5 s |

**The spread in the handover integrator collapses from 36.5 to 0.3**, and
`dt150` from 9.2 s of range to 1.8 s. `Iterm` at DROP is 71.2 in every single
run, so the loop still reaches the same operating point — it just stops arriving
there from a random starting point. Against `profile_003` the same switch takes
the `I@1:30` spread from 20.8 to 3.7.

That is a better answer than matching the background's dip to the charge, because
it removes the *sensitivity* rather than trying to cancel one instance of it.

#### The alternatives, all worse

| variant | `I@1:30` spread over the 62 degC sweep | steady rms | verdict |
|---|---|---|---|
| baseline, `Ki` 0.07 throughout | 36.6 | 0.37 - 1.18 | the problem |
| **`Ki = 0` to 1:30, then 0.07** | **0.3** | **0.36 - 0.44** | **take this** |
| `Ki = 0` to 1:30, 0.20 to 3:00, then 0.07 | 0.9 | 2.89 - 3.12 | over-integrates; no |
| `Kp = 1` to 1:30, `Ki` left at 0.07 | 91.5 | 0.48 - 2.52 | *worse* — a soft P term leaves a big error for Ki to chew on |
| `Kp = 1` and `Ki = 0` to 1:30 | 1.6 | 0.35 - 3.28 | tight handover but the dip is under-driven |

Note the fourth row: **lowering Kp in the dip is actively harmful**, for the same
reason § Correction gives for the ramp. Keep `Kp = 3.0` everywhere.

#### The one behaviour change to expect, and the traps

- **The SV will sit on the 140 floor for longer in the dip, and stay there.**
  With `Ki = 0` there is no back-calculation to lift the output off the floor, so
  if the background's dip is deeper than the BT actually achieved, the loop is
  open-loop at the floor until 1:30 — 40-64 s in the warm-charge simulations
  against 16-23 s ungated. That is the objection § profile_003 raised to
  profile_002's 39 s of saturation, and the answer is that the objection was
  really about the *entry state being set by an anti-windup side effect*, which is
  precisely what this fixes. The floor time is now cosmetic; `I@1:30` is 8
  regardless.
- **`p-i-d()` is sticky.** It writes `pidcontrol.pidKp/Ki/Kd`, so a **Save
  Settings while `Ki = 0` is in force writes `pidKi = 0` into the `.aset`** — and
  an abandoned roast, or a save before 1:30, does exactly that. Same trap class as
  Artisan stamping settings at save time (§ Correction). Check `pidKi` in the
  dialog before every roast, or re-load the `.aset` from file.
- **If the 1:30 alarm fails to fire the loop is P-only for the whole roast** —
  roast 40's failure mode, a large standing BT deficit. Visible immediately: SV
  flat and low while BT falls behind. The CONTROL button is the escape. The
  CHARGE+1 alarm failing is harmless (`Ki` stays 0.07, i.e. today's behaviour).
- It composes with the lookahead switch: both are time-from-CHARGE alarms driving
  hidden Artisan-Command buttons, and `gen_pid_alarm_asets.py` already builds
  exactly that structure. Four buttons and four alarms in total.

#### The files, and why the restore is at 90 s

`tools/gen_pid_alarm_asets.py` (which replaces `gen_lookahead_aset.py` and
regenerates the lookahead variant byte-identically bar the batch counters) emits
three variants of the canonical config, each adding only hidden Artisan-Command
buttons and time-only alarms:

| file | added | what it does |
|---|---|---|
| `airRoaster_cascadePID_lookahead.aset` | 2 buttons, 2 alarms | `svLookahead` 0 at CHARGE+1 s, 6 at CHARGE+90 s |
| **`airRoaster_cascadePID_kigate.aset`** | 2 buttons, 2 alarms | **`p-i-d(3,0,0)` at CHARGE+1 s, `p-i-d(3,0.07,0)` at CHARGE+90 s** |
| `airRoaster_cascadePID_lookahead_kigate.aset` | 4 buttons, 4 alarms | both |

**Restoring at 90 s and not earlier is what makes it work.** The insensitivity
comes from `Iterm` not moving at all during the dip, so it is bought by the
length of the gate:

| `Ki` restored at | none | 30 s | 45 s | 60 s | 75 s | **90 s** | 120 s |
|---|---|---|---|---|---|---|---|
| `I@1:30` spread over the 62 degC charge sweep | 32.7 | 34.9 | 29.5 | 15.7 | 5.9 | **0.6** | — |
| above-DRYe rms, coldest case | 1.37 | 1.38 | 1.30 | 1.10 | 0.96 | **0.79** | — |
| `dt150` at the nominal charge | +3.5 | +0.7 | +0.6 | +0.6 | +0.7 | +1.4 | **+7.2** |

Earlier restores track the nominal roast marginally better and buy almost no
robustness; 120 s starts costing real time. 90 s also coincides with the
lookahead switch, so the combined file needs only two alarm offsets.

#### Predicted, and how to read the roast

profile_003, 400 g, charge as roast 46. The first row is the validation: the
simulator reproduces the measured roast's `+0.77/0.78` and `+0.69/0.71` in the
two windows above DRY END.

| | TP | floor | `I@1:30` | 1:30-DRYe worst | DRYe-5:00 | 5:00-7:00 | dt150 | dt196.5 |
|---|---|---|---|---|---|---|---|---|
| roast 46 as run *(measured)* | 57.6 | 11 s | 15.8 | +4.19 | +0.77 / 0.78 | +0.69 / 0.71 | +3.4 | +4.8 |
| **`kigate`** | 57.4 | 18 s | **8.3** | +6.14 | +0.34 / 0.61 | +0.83 / 0.86 | +1.4 | +4.3 |
| `lookahead` | 58.1 | 16 s | 23.4 | +1.47 | +0.00 / 0.59 | +0.19 / 0.26 | -1.9 | +0.9 |
| `lookahead_kigate` | 58.0 | 40 s | **8.1** | +5.79 | -0.61 / 1.07 | **+0.32 / 0.38** | -3.3 | +1.2 |

**At the nominal charge state `kigate` on its own is close to a null experiment.**
The roast lands within a degree of roast 46 either way, because the gate buys
*robustness*, not nominal performance, and one roast at the usual charge state
cannot show robustness. What it can show, and what to check, is the mechanism:

1. **`I@1:30` near 8, not 16-24.** From `I = (SV-140)/1.6 - 3*err`, or read `SV`
   directly once v0.19.0 is flashed. This is the whole point of the change.
2. **SV reaches the 140 floor and stays there until 1:30** — around 18 s against
   roast 46's 11, and it will not lift off under its own steam. That is the
   mechanism working: with `Ki = 0` there is no back-calculation to raise `Iterm`.
3. **A slightly worse 1:30-DRYe window**, worst error about +6 degC against roast
   46's +4.2, while the integrator climbs from 8 to its operating value.
4. **Everything above DRY END unchanged** from roast 46 (+0.3 to +0.8 degC).
5. **`pidKi` back at 0.07 in the PID dialog afterwards.** If it reads 0, the
   1:30 alarm never fired.

**On combining with the lookahead** (operator's question — is the lookahead
really only above DRY END?). Not quite: the switch fires at 1:30 and DRY END is
at 3:12, so it acts over that window too. But the effects separate cleanly and a
combined roast is readable if the windows are read separately:

- the **dip and `I@1:30`** attribute to the gate — the gate moves `I@1:30`
  15.8 -> 8.3 while the lookahead leaves the above-DRYe error almost alone
  (+0.71 -> +0.60 in isolation);
- the **steady error over 5:00-7:00** attributes to the lookahead — the gate
  leaves it at +0.83 against roast 46's +0.73, the lookahead takes it to +0.32;
- **do not read DRYe-5:00 in a combined roast.** Its rms goes 0.59 -> 1.07 purely
  because the integrator is still climbing out of the gate, and it would make the
  lookahead look worse than it is.

### Charge temperature — roast 46 was frozen, and what that does and does not change (2026-09-05)

**Operator, correcting the assumption underneath the section above: roast 46 was
a frozen charge.** Green beans arrive anywhere between freezer (-20 degC) and room
temperature, a ~42 degC range.

**`greens_temp` is `0.0` in every roast on record.** Artisan has the field
(Roast Properties) and it has never been filled in, so the existing dataset cannot
tell a cold-charge roast from a warm one, and nothing below can be checked
retrospectively. **Start recording it.** One number per roast.

#### All four of roasts 43-46 were at the same charge state

There is a clean control-independent measurement available, and it exists because
of the refit: **the identified plant delay is 13.5 s, so nothing the heater does
can reach BT before ~14 s after CHARGE.** The BT trajectory over 0-13 s is charge
mixing alone. Normalised by charge mass (all four are the same lot C1043, same
density 745.2, CHARGE_BT within 1.2 degC, and the preheat inlet differences are
worth under 0.7 degC of BT over that window):

| | #43 400 g | #44 400 g | #45 345 g | #46 400 g |
|---|---|---|---|---|
| BT fall over 0-13 s | 59.2 | 57.2 | 47.8 | 59.6 degC |
| per 100 g of charge | 14.80 | 14.30 | 13.86 | **14.90** |

**14.46 +- 0.48, a 3.3% spread.** If the fall scales with `CHARGE_BT - T_charge`,
a room-temperature batch should read about **28% lower** than a freezer one — so
the metric has a signal-to-noise of roughly 8, and it says these four roasts were
all at the same charge temperature. Roast 46 is confirmed frozen, so **roasts
43, 44 and 45 were frozen too** (same lot, same storage, three of them
back-to-back within an hour). Corroborating: the heat draw `-slow(t)` evaluated
at matched BT shows no systematic excess for roast 46 over roast 44 — and a 42
degC charge difference at 400 g is 29 kJ, which would have to appear somewhere.

**Keep this diagnostic.** `(CHARGE_BT - BT at CHARGE+13 s) / mass` is a free,
control-independent proxy for the charge's thermal state, computable from any
`.alog`, and it becomes a calibrated thermometer as soon as a few roasts carry a
real `greens_temp`.

#### What this changes

- **The batch-size diagnosis of roast 46 stands.** Roasts 45 and 46 were at the
  same charge temperature, so profile_003's TP being matched to 345 g and roast 46
  running 400 g is the whole of that story, exactly as § Roast 46 has it.
- **The plant fit stands.** Its window starts at CHARGE+45 s and charge
  temperature enters as an initial condition, not as a plant property.
- **profile_004 encodes a *frozen* 400 g dip**, not a warm one. So the fragility
  is pointed the other way from the first reading of it: a *warmer* charge would
  make the actual dip shallower than the authored one, which puts BT above the
  target, drives the error negative, and floors the output — the profile_002
  failure mode. **With `Ki` gated off through the dip that no longer matters**,
  which is the main reason the gate is worth more than the profile.
- **A calibrated `TP = T_charge + Q/(m*c)` is withdrawn.** Fitting `Q` and
  `T_charge` jointly to the four `(mass, TP)` pairs gives `T_charge = +6 degC,
  Q = 36.2 kJ`, but shifting the three 400 g turning points by one standard
  deviation of their own scatter (1.3 degC) moves that to `-3.5 degC / 41.8 kJ`
  or `+15.4 degC / 30.6 kJ`. With only two distinct batch sizes and no recorded
  charge temperature, **the data cannot pin either number**, and any figure of the
  form "TP moves 1:1 with charge temperature" is a model statement, not a
  measurement. It is also not needed now that the loop is being made insensitive
  to it.

### Dip strategies — a wider search, and the one that changes the structure (2026-09-06)

**Operator, on the combined `lookahead_kigate` file:** *"by addressing the dip,
the approach leaves the integrator a little behind and it needs to build to
reduce error slowly … think about a variety of approaches."* The complaint is
correct, the obvious repair (dose the integrator back up at handover) is
**wrong**, and the search turned up one structural change that dissolves the
problem instead of trading it around — plus a correction to how much the `Ki`
gate is actually worth.

The sweep is now **reproducible**: `tools/analysis/dip_strategies.py`. The one
behind § The dip is a different control problem was ad hoc and is not in the
repository, and **the two disagree** (below).

#### The sweep, and why it is one-sided now

Roast 46 was a frozen charge (§ Charge temperature), so the reachable variation
is **warmer only**, up to ~42 degC. A warmer charge is injected as an extra
mixing term in the plant disturbance, `d(t) = (0.386*dT/tau) * exp(-(t-2)/tau)`,
`tau = 5 s` — integral `0.386 degC of BT dip per degC of charge`, which is what
the measured 0-13 s fall implies (59.6 degC on 400 g frozen; a room-temperature
batch should fall ~28% less). Mixing is complete by 13 s, which is where the
13.5 s plant delay first lets the heater vote.

| strategy | `I@90` | `I@DROP` | worst 1:30-3:20 | steady 5:00-7:00 mean/rms | dt150 | dI/dt |
|---|---|---|---|---|---|---|
| base (roast 46 as run) | 15.8 → 19.4 | 63 | +4.09 → +3.21 | +0.73 / 0.74 | +2.5 → +2.9 | 0.083 |
| **`lookahead` (step 6)** | 23.4 → 23.4 | 63 | **-4.01 → -3.90** | **+0.19 / 0.26** | -2.9 → -3.0 | 0.082 |
| `lookahead_kigate` | 8.1 → 9.1 | 63 | +5.79 → +4.39 | +0.32 / 0.38 | -4.3 → -0.1 | 0.092 |
| `lookahead` + gain-scheduled `Ki` | 20.2 → 23.2 | 63 | +2.95 → -3.57 | +0.25 / 0.28 | -5.6 → -3.3 | 0.086 |
| **FF trim** | 42.5 → 31.7 | **50** | +2.25 → +4.80 | **-0.08 / 0.11** | +1.6 → +2.9 | **-0.008** |
| **FF trim + `Ki` gate** | **49.9 → 49.9** | **49** | **-0.87 → -1.23** | **-0.12 / 0.14** | **+1.6 → +1.6** | **-0.012** |
| FF trim + gate, FF gain -20% | 49.6 | 42 | -4.95 → -5.16 | -0.13 / 0.15 | +6.4 → +6.3 | -0.013 |
| FF trim + gate, FF gain +20% | 50.1 | 54 | +2.83 → +2.84 | -0.12 / 0.15 | -1.1 → -0.9 | -0.011 |

Each pair is `dT = 0 → +42 degC`. `worst` is the largest signed background error
over 1:30-3:20; `dI/dt` is duty/s over 5:00-7:00, i.e. the type-1 ramp error
divided by `Ki`.

#### Correction: over the reachable range the `Ki` gate does not pay for itself

**§ The dip is a different control problem sweeps ±62 degC around roast 46 and
half of that is unreachable** — roast 46 was already frozen, so "22 colder" and
"42 colder" are not charge states this roaster will see. Read on the warm side
only, this reconstruction says:

- the **baseline is far less charge-sensitive than reported**: `I@1:30` spread
  **3.6**, not 20.8, and `dt150` spread 0.9 s;
- **`lookahead` alone is the most charge-insensitive of the Artisan-only
  options** — `I@1:30` spread **0.9**, `dt150` spread **0.4 s** — because six
  seconds of lead is feedforward, and feedforward does not care what the
  integrator was doing;
- adding the gate to it makes **every** metric worse: worst error +5.79 against
  -4.01, steady rms 0.38 against 0.26, and `dt150` spread **4.2 s against 0.4**.

That is precisely the operator's observation, and it is not a small residual —
in this model the gate's robustness purchase is negative. The disagreement with
the earlier tables cannot be closed (that code is gone), so treat the *direction*
of the gate mechanism as established and its *magnitude* as unsettled, and note
that this sweep is parameterised by a measured quantity while the earlier one was
not. **Step 1c is demoted below step 6 rather than run with it.**

#### The repair that does not work: dosing the integrator at handover

The natural reading of "the integrator is left behind" is that it should be
topped up at 1:30, and `p-i-d()` gives a way to do it — a short high-`Ki` burst,
which with the gate in place starts from a repeatable state so the dose is
repeatable. It **overshoots badly**: `Ki = 0.20` for 30 s takes `dt150` to
**-20.9 s**, `Ki = 0.15` for 60 s to -20.4 s, and steady rms roughly triples. The
loop is not short of integral — the `lookahead_kigate` file already runs *ahead*
of the profile (`dt150 = -4.3`). What it is short of during 1:30-3:20 is
**anticipation**, and integral is the wrong term for that. A temporary large
`svLookahead` fails for the same reason and in the same direction (`L = 12` over
1:30-3:00 → `dt150 -14.6`; `L = 16` → -20.5; `L = 20` → -26.3).

#### Free improvement: build the gate out of gain scheduling, not alarms

Artisan's software PID has **native gain scheduling** and it is not used.
`getParameter` (pid.py:370-386) maps a linear fit through `(Schedule0, K)` and
`(Schedule1, K1)` onto the PV — or onto the SV with `gain_scheduling_on_SV` —
and **clamps the result to `[min, max]` of the two values** (pid.py:384-386), so
it is a saturated ramp, not an extrapolation. All of it persists in the `.aset`
(`pidKi1`, `pidSchedule0/1`, `gain_scheduling*`; main.py:13944-13982, 17229-17240)
and it is applied through `confSoftwarePID` (pid_control.py:1470).

`Ki` ramping 0 → 0.07 across **BT 70 → 95** is the same gate with better
properties:

- **no alarms and no buttons**, so no missed-alarm P-only failure mode, and no
  sticky-`p-i-d()` trap — a Save Settings mid-roast writes nothing harmful,
  because the gate is not a runtime gain change;
- **self-scheduled on the recovery** rather than on a clock, so integral action
  returns as fast as the beans actually recover;
- and it removes the handover discontinuity the operator objected to: worst error
  over 1:30-3:20 falls to **+2.95** against the timed gate's +5.79, and steady rms
  to 0.28-0.36 against 0.38.

It keeps most of the robustness (`I@1:30` spread 3.0 against the timed gate's 1.2)
and it is strictly better than the timed gate on everything else. Three caveats:
**v4.2.0 lacks master's guard against an all-zero schedule** (§ Development
framework), so `pidSchedule0`/`pidSchedule1` must be set to distinct non-zero
values *before* `pidGainScheduling` is ticked, or the fit is degenerate;
`p-i-d()` still overrides the *base* gain `y1` if a runtime command is also used,
so use one mechanism or the other; and the lower breakpoint must sit under the
warmest plausible TP or the gate never engages — at `dT = +42` TP is 72.5, so
70/95 is already marginal and 75/105 or 80/115 buys engagement at the cost of
`I@1:30` spread (4.3 and 7.5 respectively).

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
  lookahead-versus-dip tension (§ Roast 44 outer-loop analysis: `L > 4` winds the
  integrator through the dip) disappears with it.
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
  the trim range. `artisan/make_inlet_background.py` — kept for exactly this path
  and never modified — authors the base curve into the background `.alog`.
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
| lower `Kp` through the dip | already ruled out in § The dip is a different control problem (handover spread 91.5); `beta < 1` via `pidWeights()` is the same move on the target path and no better |
| the fan as a second actuator in the dip | not needed, and the operator now holds it constant deliberately; the ~0.99 %heat/fan-unit sensitivity is a loss-term effect, which the FF schedule and the trim both absorb |

#### The one adaptive idea that is still open, and costs nothing to keep

`(CHARGE_BT - BT at CHARGE+13 s) / mass` is a **free, control-independent proxy
for the charge state** (§ Charge temperature) and it is available at 13 s — well
before any handover. Artisan can act on it without a new process step: an alarm
*from CHARGE, offset 13 s, source BT, below/above a threshold* can fire
`loadBackground(<path>)` (main.py:10879), `moveBackground(<dir>,<step>)`
(main.py:10923), `alarmset(<n>)` (main.py:10898) or `palette(<n>)`
(main.py:10863) — so a whole tuning set or background can be selected on the
measured charge state. **Do not build this yet.** It is the fallback if the FF
trim leaves a charge-dependent residual worth chasing; on the present numbers it
would be chasing 1.6 s.

### Runbook — the agreed order of work (2026-09-02, re-pointed 2026-09-05)

One variable per roast. Order after roast 46, the refit, the charge-temperature
finding and the strategy search: **step 6, then steps 3-5 (the characterisation
runs), then step 9.** Steps 2 and 7-8 are independent. **Steps 1b and 1c are
demoted** — § Dip strategies finds that over the *reachable* (warm-side only)
charge range the `Ki` gate makes every metric worse than step 6 alone, and that
both of them are rearranging a burden that step 9 removes. **The characterisation
runs have recovered their priority**, because step 9's feedforward schedule is
built from `1/a` and the loss curve, and the loss curve is where the fan enters.

**Do this on every roast from now on, it costs nothing: fill in `greens_temp`**
(Artisan Roast Properties). It is `0.0` on every roast on record, which is why
the charge state of the existing set had to be inferred rather than read
(§ Charge temperature).

**~~Step 1 — validate `pidKi` 0.07 + profile_003.~~ DONE — roast 46, 2026-09-05.**
Five of the six checks pass, item 5 (floor time) fails on batch size rather than
on the loop, and the mid-roast ring is gone. Full reading in § Roast 46. Two
things came out of it that set the order below:

- The residual above DRY END is **pure type-1 ramp error, ~1.0 degC / 4-5 s**,
  and the **measured optimum `svLookahead` is 6.3 s** — the value the step-6 file
  already carries. That makes **step 6 the next roast**, not an afterthought.
- profile_003's dip is matched to a **345 g** batch and roast 46 was **400 g**,
  which cost 30 degC of manufactured error, a rail-to-rail SV excursion and 11 s
  on the floor in the first minute. That is **new step 1b, profile_004**.

**Step 1b — profile_004, a 400 g dip. Run it *after* step 6 and step 1c, and only
with the lookahead-switching config.** Its value drops sharply once `Ki` is gated
(step 1c does the same job without an authoring step, and does it for every charge
state rather than one) — and note that roast 46 was a **frozen** charge, so
profile_004 would encode a frozen dip and would be wrong in the *dangerous*
direction (floor plus windup) for a warm one. Keep it on the list, but as a
refinement rather than a fix. Take 0:00-1:30 from roast 46's own measured BT,
keep profile_003's ramp and finish unchanged (the same operation that produced
profile_003 from profile_002 — § profile_003, § Roast 46). Simulated in
§ Roast 46 refit: paired with the step-6 file it is the best configuration found
— **0 s at the floor**, dip error -2.6 degC against -8.8, handover `Iterm` 30,
steady error +0.18 degC — but at the present constant `svLookahead = 3` the same
background is *worse* than profile_003 (`Iterm` 41 at 1:30, a 9.1 degC undershoot
over 1:30-3:00), because three seconds of lead against a steeper, earlier dip
manufactures a bigger negative error. The two changes are not independent.

**Step 1c — gate `Ki` off through the charge dip.** Two more hidden
Artisan-Command buttons and two more time-from-CHARGE alarms, regenerated the
same way as the lookahead pair: `p-i-d(3,0,0)` at CHARGE+1 s and
`p-i-d(3,0.07,0)` at CHARGE+90 s. `Ki = 0` closes both windup paths at once —
the integral term and, because `_back_calculate_integral` is gated on
`getKi(PV) != 0` (pid.py:314-333), back-calculation as well — so `Iterm` is
frozen through the dip and handed to the ramp at a known value. Simulated over a
62 degC swing in charge temperature the handover integrator goes from a spread of
**36.5 to 0.3**, and time-to-BT-150 from 9.2 s of range to 1.8 s
(§ The dip is a different control problem). Expect the SV to sit on the 140 floor
longer and not lift off it before 1:30 — that is the mechanism working, not
failing. Watch the two traps: `p-i-d()` is sticky, so a Save Settings before 1:30
writes `pidKi = 0` into the `.aset`; and if the 1:30 alarm misses, the loop is
P-only for the rest of the roast (roast 40's failure mode, CONTROL button to
escape).

File: **`artisan/airRoaster_cascadePID_kigate.aset`**, or
`..._lookahead_kigate.aset` to run it together with step 6 — both generated by
`tools/gen_pid_alarm_asets.py`. Predicted outturn and the five things to check
are in § The dip is a different control problem. Note that at the usual charge
state this is close to a **null experiment** on roast quality: check the
mechanism (`I@1:30` near 8, SV parked on the floor until 1:30), not the outcome.

**Demoted 2026-09-06 — do not run this with step 6.** § Dip strategies
reconstructs the charge sweep as a reproducible tool
(`tools/analysis/dip_strategies.py`), restricted to the warm side that a frozen
roast 46 leaves reachable, and finds the gate costs more than it buys there:
worst error over 1:30-3:20 +5.79 against step 6's -4.01, steady rms 0.38 against
0.26, and `dt150` spread 4.2 s against 0.4. The mechanism is real, its magnitude
is not settled, and the earlier sweep's code no longer exists to reconcile.
**If the gate is run at all, run it as gain scheduling rather than alarms** —
`Ki` 0 → 0.07 across BT 70 → 95, which is the same gate with no missed-alarm
failure mode, no sticky-`p-i-d()` trap, and a worst error of +2.95.

**Step 2 — flash v0.19.0 and wire up the new channels.** After step 1, so that
roast stays clean. **v0.19.0 now carries two items**: the `SV`/`HT` `getData`
nodes (done, below) and the `INLET TRIM` command that step 9 needs
(§ Firmware now in scope). `INLET TRIM` is inert until Artisan is reconfigured,
so flashing it changes nothing about the present cascade — but it means step 9
needs no second flash. `./verify.sh upload`, then in Artisan **Config > Device >
Extra Devices** add a further WebSocket device so channel slots 5 and 6 become
curves, and name them `SV` and `HT`. The `channel_nodes`/`channel_modes` entries
are already in both `.aset` files. Confirm the two curves appear and track, then
set **`createEvents` back to false** — it is only the fallback. From here every
roast is self-contained and no CSV is needed.

**Step 3 — Test A, empty roaster. No beans, ~12 minutes, free.** Same `.aset`,
background `artisan/charstep_empty.alog`. **PID OFF** (CONTROL button). Press ON,
then START to record — **do not press CHARGE**, which would arm `pidOnCHARGE`.
Drive slider 3 by hand along the guide: 145 -> **185 at 2:00** -> **145 at 5:00**
-> **185 at 7:00** -> **145 at 10:00**. Timing precision does not matter; the
identification uses the recorded SV. Save the profile.

**Step 4 — Test B, loaded doublet. One sacrificial batch.** Background
`artisan/chardoublet_loaded.alog`, **PID OFF throughout**. Charge normally and
drive slider 3 along the guide curve, which is roast 45's own commanded SV plus
**+30 degC over 3:00-4:00 and -30 degC over 4:00-5:00**. Net energy is ~zero so
the batch lands near a normal roast. Save.

**Step 5 — Test C, the fan.** Test B repeated at **fan 58** and at **fan 65**.
Two batches. This is what turns the fan sensitivity from one weakly-identified
coefficient into a measurement.

~~After 3-5 the theta/tau ridge (§ Scheduling) collapses to real numbers~~ —
**superseded**: roast 46's involuntary rail-to-rail SV excursion in the charge
recovery did that job already (theta 13 +5/-1 s, tau 205 s, § Roast 46 refit), and
the Ki retune it was to enable has been done — 0.07 is optimal, not a compromise.
What 3-5 are still for is the **fan** (Test C) and an independent check of the
plant under a deliberate rather than an accidental doublet. The
**predicted-BT channel** (§ Firmware now in scope) is a separate decision.

**Step 6 — the lookahead switch. This is the next roast (2026-09-05).**
Load `artisan/airRoaster_cascadePID_lookahead.aset` **unmodified** with background
profile_003 and roast normally. Roast 46 is the clean baseline it needed and
measures the required lead at 6.3 s against the file's 6; the validated simulator
in § Roast 46 refit then predicts, against roast 46's own numbers in brackets:

| | predicted | roast 46 as run |
|---|---|---|
| steady tracking error, 3:00-7:00 | **+0.05 degC / 0.44 s** | +0.75 degC / 3.4 s |
| time to BT 150 / 180 / 196.5 vs profile | -1.9 / +3.2 / +0.9 s | +3.5 / +5.0 / +4.4 |
| at 1:30: target step -> commanded SV | +4.0 degC -> **+24.7 degC**, settled in ~15 s | — |
| floor time in the charge dip | 16 s | 4 s simulated, 11 s measured |
| SV max / worst reversal after 1:00 | 296 / 3.2 degC | 289 / 0.3 |

So the answer to *"does the 1.0 degC / 4-5 s lag go to ~0?"* is yes, by
construction of the feedforward. Two expectations to correct: the SV kick at
1:30 is a quarter larger than § Roast 46 estimated, and the `pidLookahead(0)`
leg makes the dip **worse** against profile_003 (16 s on the floor, not better
than L=3's 4) — leave it in anyway, because it is what makes step 1b work.
**Do not take the two-stage alternative**: swept against three- and four-stage
schedules it gains under 0.1 degC of rms and costs two buttons and an alarm.

**Step 7 — a fixed fan, independent.** § Fan vs batch size says the level does
not depend on charge mass and the loop barely notices the level, only the step.
One roast at a flat **fan 60** with no changes tests whether the ramp is
earning its disturbance. Roast 46 already went most of the way: the fan was held
at 60 through the whole roast and the trace shows no air-schedule signature at
all (§ Roast 46), which is the cleanest evidence yet that the ramp is not earning
it. What is left is a roast that keeps 60 through preheat too.

**Step 8 — the feedforward term, firmware, bench only.** `feedforward()` is
clamped at 100 for every sample of a roast and its model form is ~9x too steep in
SV and ~1.8x too steep in fan (§ Roast 46). It is doing nothing except holding
`pidITerm` at -45..-64 and forcing the anti-windup bound to `[-100, 0]`. Either
give it the affine form the preheat measurement supports
(`heat = -30.6 + 0.99*fan + 0.0096*SV`, resid rms 1.85 %) or set `FF OFF` until
it has one. Bench-testable; no roast needed. **Do it before Test C**, whose whole
subject is the fan compensation this term is supposed to provide.

**Step 9 — the inlet feedforward schedule with the PID as a trim.** The
structural fix, and the reason steps 1b/1c are demoted rather than deleted:
today the outer integrator has to supply the entire operating point, so it ramps
at 0.09 duty/s all roast, `e_ss = (dI/dt)/Ki` exists, `svLookahead` is needed to
hide it, and the value handed over at 1:30 matters. Give the firmware a base
inlet schedule (`ff(t) = bg(t+theta) + (dbg/dt - loss)/a`, authored by
`artisan/make_inlet_background.py` and replayed through Artisan's per-event-type
background playback on its own slider) and make the PID's output a bounded trim
on it via a new `INLET TRIM <degC>` firmware command. Simulated: `dI/dt` 0.09 ->
0.01, `I@DROP` 63 -> 50, steady rms **0.11-0.14 degC**, `svLookahead` 0, and with
the `Ki` gate the handover integrator and `dt150` are **identical at every charge
state**. Survives +-20% of error in the assumed plant gain. **Run steps 3-5
first** — the schedule is exactly `1/a` and the loss curve, which is what those
runs measure. Full design, the source citations for the playback/slider
arrangement, and the risks to close are in § Dip strategies.

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
   OFF -> ON between roasts rather than reusing a session (§ Roast 41).
   Preheating under the PID hands the roast an integrator already at the
   empty-roaster operating point (§ PID-driven preheat).
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

## Completed phases (specs kept for reference; details in the archive)

## Phase 1 — firmware safety (FW 0.7.0) — DONE 2026-07-02

*Answers F1 (boot level mismatch), F3 (closed-loop sensor failsafe), F6
(unchecked dimmer writes), F8 (no watchdog).*

1. **Boot dimmer sync.** After `initDL()` for both modules: force heat to 0
   (`setLevel(HEAT_ADDR, 0)`, retried); read the fan's actual level with
   `getLevel(FAN_ADDR)` and adopt it into `fanLevel` — after a crash mid-roast
   the fan keeps cooling the hot roaster while the heat is killed. Log if the
   sync fails.
2. **Inlet-loop failsafe.** Track inlet-PV freshness (`inLastGoodMs` stamped in
   `updateSensors()` on every accepted MAX31855 read). In `MODE_INLET`:
   - PV stale (> `INLET_PV_STALE_MS`, 3000 ms) → drop to `MODE_MANUAL`,
     heat 0, `logError`, broadcast. A frozen hold-last-good PV must never keep
     feeding the integrator.
   - Over-temp (`inTemp > INLET_OVERTEMP_C`, reuse 280 °C) → same action.
   - `MODE_TUNE` gains the same stale-PV abort (it already has over-temp).
3. **Checked dimmer writes.** `applyInterlock()` and the OT2 path only update
   the cached level when `setLevel()` returns true; on failure the cache keeps
   the old value so the next loop retries, with a rate-limited log entry. Add a
   **readback audit** to the existing 5 s DimmerLink error poll: `getLevel()`
   both channels; mismatch against the cached value → log + rewrite.
4. **Task watchdog.** `esp_task_wdt` (IDF 5 API: `esp_task_wdt_reconfigure` /
   `_init` with `esp_task_wdt_config_t`, `trigger_panic = true`, ~8 s), add the
   loop task, `esp_task_wdt_reset()` each loop; feed it inside the WiFi connect
   wait until Phase 3 makes that non-blocking. Safe only because of item 1.

## Phase 2 — MAX31865 direct-register driver (FW 0.8.0) — DONE 2026-07-02

*Answers F2 (blocking one-shot reads / defeated continuous-mode design) and
F10 (blind jitter metric). Datasheet traceability in state-archive.md.*

1. New local header `max31865_direct.h`, small class, no external deps:
   - Own SPI transactions: `SPISettings(1_000_000, MSBFIRST, SPI_MODE1)`,
     manual CS. Registers: read `0x0N`, write `0x8N`, MSB first, auto-increment
     multibyte.
   - `begin()`: config = `VBIAS(0x80) | AUTO(0x40)` (+3-wire/50 Hz bits if ever
     needed; we run 4-wire, 60 Hz ⇒ 0xC0), thresholds armed (below), faults
     cleared. Filter bit set before enabling auto mode (datasheet forbids
     changing the notch while converting).
   - `reassert()`: rewrite the config byte — this makes the existing
     `RTD_REASSERT_MS` stall guard actually meaningful.
   - `readRaw(bool &fault)`: one 2-byte read at 0x01; bit 0 of the pair is the
     per-sample fault flag; value is the 15-bit ratio.
   - `readFault()` / `clearFault()`: plain register read of 07h (no
     master-initiated fault cycle — the Adafruit default knocks the chip out of
     auto mode); clear via config D1 with D5/D3/D2 zero.
   - Temperature from raw via Callendar–Van Dusen (same math as the Adafruit
     `calculateTemperature`, implemented locally).
   - Threshold arming: convert `RTD_VALID_MIN_C`/`RTD_VALID_MAX_C` to raw via
     forward CVD `R = R0(1 + AT + BT²)` (B-term adequacy at −20 °C is fine for
     a fault threshold), write as 15-bit << 1. The chip then latches D7/D6 on
     every out-of-window conversion — on-silicon EMI evidence.
2. Rework `serviceRtd()` to use the driver: the two-read disagree check
   becomes two cheap register reads (a true SPI-glitch detector), fault
   evidence is no longer destroyed by the read path, and per-sample fault bits
   feed the debounce. Median filter, debounce, hold-last-good, rate-limited
   logging all stay as-is.
3. Remove the `Adafruit_MAX31865` dependency (keep MAX31855 — verified
   non-blocking and correct).
4. **Honest load metric**: track worst single `loop()` duration (µs) alongside
   the control-jitter watch; report and reset both via `STAT`
   (`loopMaxUs` field). The old metric couldn't see in-pass blocking.

## Phase 3 — protocol hardening + telemetry (FW 0.9.0) — DONE 2026-07-02

*Answers F4 (garbage parses as zero), F5 (JSON envelope int-rounds the ramped
setpoint), F7 (WiFi), F9 (DimmerLink extras), tune-settled flag, and adds the
telemetry channel the dashboard needs.*

1. **Strict numeric parsing** (`parseFloatStrict`/`parseIntStrict`): `OT1 x`
   or `PID a b c` is rejected with a reply to the sender, never treated as 0,
   and never persisted to NVS.
2. **JSON envelope keeps floats**: `{"command":"INLET","value":183.4}` becomes
   `INLET 183.40` (currently rounded to int — quantizes Artisan's ramped
   playback to 1 °C steps).
3. **WiFi**: bounded connect wait (~15 s, WDT-fed, display progress), then boot
   proceeds regardless; `setAutoReconnect(true)` plus a rate-limited reconnect
   check in loop; display already shows state. Roaster must be fully usable
   over serial with no WiFi.
4. **TUNE result gains `"settled":true|false`** — a timeout fit underestimates
   dT and suggests too-hot gains; the flag says whether to trust it.
5. **DimmerLink extras**: log VERSION (reg 0x03) at init; escalate to COMMAND
   RESET (reg 0x01 ← 0x01) after N consecutive error-poll failures, then
   re-init (re-assert curve, restore level). Level readback audit came in
   Phase 1.
6. **`FF AMB` with no value** seeds `ffAmbient` from the MAX31855 cold-junction
   temperature (`readInternal()`), with the enclosure-warmer-than-room caveat
   documented.
7. **Telemetry push**: every `TELEM_PERIOD_MS` (default 1000 ms; 500 ms during
   TUNE) broadcast
   `{"pushMessage":"telem","data":{"t":<ms>,"IN":..,"BT":..,"ET":..,"sv":..,"heat":..,"heatReq":..,"fan":..,"ilCap":..,"mode":"..","p":..,"i":..,"d":..,"ff":..,"fltIN":0|1,"fltBT":0|1}}`
   — the PID terms come from the last `controlStep()`. `TELEM <ms>|OFF` command
   (clamped 100–10000). Skip building the string when no client is connected.

## Phase 4 — dashboard rebuild — DONE 2026-07-02

Single file, zero dependencies, works from `file://`. Grouped panels:

1. **Connection** — IP (remembered), connect/disconnect, auto-reconnect with
   backoff, status dot.
2. **Status** — mode badge (manual/inlet/tune), heat bar showing applied vs
   requested, fan bar, interlock state/cap, inlet SV.
3. **Temperatures** — large IN/BT/ET readouts, per-channel fault badges from
   telemetry flags.
4. **Inlet tuning** (the centerpiece) —
   - Canvas strip chart: IN (PV) and SV on the temperature axis, heat on a
     0–100 % axis; rolling buffer (≥30 min at 1 Hz), pause, window selector,
     CSV export of the buffer.
   - PID editor prefilled from `pid` pushes; FF editor (`ffK`, ambient, CAL,
     OFF); live P/I/D/FF term readout.
   - TUNE workflow: start (step % field), abort; on result show the model
     (Kp/tau/theta/dT, settled flag) and both gain sets with **Apply tight**
     and **Apply cons** buttons (cons applies via `PID <kp> <ki> 0`).
5. **Console + log** — every message timestamped into a capped capture buffer;
   per-class filter checkboxes (status/telem/error/log/tune-pid-ff-stat/sent/
   other; telem hidden by default), free-text filter, **Save log** (.txt
   download) — the device log is 8 RAM entries, so the browser is the real
   archive; `LOG` requested on connect.
6. **Commissioning** — existing sequence panel, retained and updated.

## Phase 5 — docs sync — DONE 2026-07-02

- README: interlock constants (code says 48/55/30, README says 23/30/30),
  dashboard path (repo root, not `artisan/`), delete the stale "BT/ET stubbed
  at 0.0" paragraph, document new commands (`TELEM`, no-arg `FF AMB`), boot
  dimmer sync, watchdog, WiFi behavior, `settled` flag, direct-driver sensor
  path.
- emi.md addendum: the library one-shot discovery — unbiased auto-convert
  windows between polls were a plausible contributor to spurious `0x60`
  faults; continuous mode changes the experiment. Note what to watch in the
  next roast's fault log.
- Keep state docs current per the update discipline in state-current.md.

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
