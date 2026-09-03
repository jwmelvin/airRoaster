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
   (`pid_control.py:1447`). So BT is **1**, not 2. The earlier inference of
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
`dutyMin`/`dutyMax` are *duty percentages*, not degC: `pid.py:490` clamps
`final_output = min(dutyMax, max(dutyMin, output))` where `output` is already
bounded by `outMin=0`/`outMax=100`. Setting `dutyMin=120` would pin
`final_output` at 120 every cycle, and `numpy.interp(120, [0,100], ...)` clamps
above the input range and returns `heat_max` — i.e. **the inlet setpoint would
sit at its maximum permanently, with the outer loop having no effect at all.**
A runaway-heat configuration. (`pid_control.py:1525` separately re-clamps
`dutyMin/Max` into 0-100 on the ArduinoTC4 path, confirming the intended
domain.)

The correct mechanism is the one Artisan documents for exactly this:
`positiveTargetRangeLimit=true` with `positiveTargetMin=140`,
`positiveTargetMax=300` — "the duty is mapped to the target slider subrange"
(`pid_control.py:1211`). Duty 0% -> 140 degC, duty 100% -> 300 degC. (120 until
roast 40, briefly 170, then 140 to allow a PID-driven preheat; see below.)

**`[Sliders]` is deliberately left alone.** Artisan's own stated assumption is
`slider_min < positiveTargetMin < positiveTargetMax < slider_max`
(`pid_control.py:1317`). Slider 3's existing 0-320 satisfies
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
`eventactionx(self.buttonactions[6], ...)` at canvas.py:15130), and stored 20
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
`pidcontrol.pidOff()` runs at canvas.py:15012, *before* the button action at
canvas.py:15130 — so the PID is already stopped when `INLET 0` is sent and
cannot re-command a setpoint afterwards. (CHARGE mirrors this: `pidOn()` at
canvas.py:14206 precedes `eventactionx(buttonactions[0])`.)

**An earlier draft of this plan was wrong twice here** and both errors are
retracted: first that `PID_OFF_action` could carry `INLET 0` (it fires only for
external MODBUS/S7 PID control, `pid_control.py:1570-1580`; this is a WebSocket
device so `externalPIDControl()` returns 0), and then that an Artisan **alarm**
should send the WebSocket command instead — alarm actions have their own
numbering that tops out at 25 (`canvas.py:5928-6110`: 0=popup, 2=event button,
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
branch is `elif self.aw.qmc.Controlbuttonflag:` (pid_control.py:1548), so with
the flag false `pidOn()` falls through and never activates the PID — meaning
`pidOnCHARGE` would silently do nothing. Monitor start likewise skips
`confSoftwarePID(reset=True)` unless `externalPIDControl() == 0 and
Controlbuttonflag` (canvas.py:12962), so the PID would never even be configured
with the current gains and sampling rate.

The live config has it **false**, so this is a required change, not a
convenience. It also surfaces the CONTROL button, which is the operator's
manual PID on/off — the escape hatch for dropping below the floor
mid-roast. (`PIDbuttonflag` is a different flag, for TC4/Fuji hardware PID
control; left as-is.)

**CHARGE still arms the outer loop**, without a button action:
`pidOnCHARGE=true` makes `markCharge` call `pidcontrol.pidOn()` directly
(canvas.py:14206), before any button action runs — mirroring `pidOffDROP` at
canvas.py:15012. This is also the moment the charge-aligned background SV curve
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
`int(dutyFilterFlag.isChecked())`, pid_dialogs.py:1650). `dutyMin`/`dutyMax`
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
adjustment term (pid.py:52-66, 377-382). Two independent derivations agree — the
0:40 row comes from the output hitting its floor, the others from mid-roast
setpoints.

Pinned near the ceiling with no way to unwind at Ki=0.003, the only thing able to
reduce output was a large negative P term. **That is why Kp=8.5 appeared to give
control effort**: with I railed, P was the only actuator left.

**Mirror image of roast 40.** There I ~ 14 and the loop could not push up; here
I ~ 90 and it could not come down. One root cause: at Ki=0.003 the integrator is
far too slow to be the operating-point supplier, so it parks wherever history
left it and P does all the work. This is the strongest argument for the Ki raise.

**Resolved (operator confirmed the PID was *not* enabled during a manual 150 degC
preheat): Artisan's software PID keeps integrating while switched off.** Three
source facts in a chain:

1. The target keeps updating when inactive. `canvas.py:4946` gates on
   `(pidActive and svMode == 1) or svMode == 2` — comment: *"in BackgroundFollow
   mode we update the SV even if not active, just we do not move the SV
   slider."* This config is `svMode=2`.
2. `update()` integrates unconditionally. Pterm, Iterm, clamping and
   `final_output` are all computed before the only `if self.active:` guard,
   which merely gates dispatching the output to the slider (pid.py:497-500).
3. `on()` deliberately does not reset: *"we keep the PID running always, even if
   inactive, and do not disturb it with an init on switching it active"*
   (pid.py:355).

So through the manual preheat the PID silently integrated against the
background's CHARGE temperature (129.4 degC) while BT was still cold.

**Why it parks near 90 instead of running away.** `pidIWP=true` gives
conditional integration: integration stops once the *unclamped* output exceeds
`outMax` (pid.py:313). Iterm therefore rises until `P + I ~ 100`, i.e.
`I ~ 100 - Kp*err` — about 89 at err ~ +1.3 with Kp=8.5. The integrator fills
quickly through saturation and drains only at `Ki*err`: at Ki=0.003 with
err ~ -3 that is 0.009/s, roughly three hours to unwind. **That asymmetry —
fast fill, glacial drain — is the actual defect**, and it is a further argument
for the Ki raise.

**The only thing that clears Iterm** is `confSoftwarePID(reset=True)` ->
`pid.reset()` -> `init()` -> `Iterm = 0.0` (pid_control.py:1487, pid.py:515,
532). That is called from exactly one place: **monitor start, the ON button**
(canvas.py:12962). `pidOn()` calls `confSoftwarePID()` with the default
`reset=False`, so arming the PID does *not* clear it; neither does DROP, RESET,
nor loading a settings file. Iterm therefore persists across roasts for the
whole Artisan session.

**Operating procedure (required, not optional):** **press ON to start
monitoring — that zeroes the integrator — then turn the PID on and preheat under
its control, then CHARGE.** See § PID-driven preheat. Without the ON, every
roast inherits whatever the previous one left in the integrator; without the PID
on during preheat, the integrator winds blind.

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
returns the background profile's **CHARGE BT** (pid_control.py:1731-1740) —
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
pid_dialogs.py:1979-1983). Note **the PID SV is a BT target in this cascade, not
an inlet temperature** — the PID's *output* is the inlet setpoint. The
equivalent of the old manual "preheat at inlet 150" is an SV of ~130, not 150.
The Artisan Command **`pidSV(<n>)`** (main.py:10431) sets it from any event
button or slider; the existing button 9 ("SV off") already uses `pidSV(0)`.

Both are overridden within ~1 s in Follow Background: canvas.py:4946 recomputes
the SV every sample and calls `setSV` whenever it differs, so a manual SV only
sticks in `svMode=0`. For preheat this does not matter — `calcSV` already
returns the background's CHARGE BT automatically. The slider's real value here
is as a **live readout of the BT target** (with `svSlider` true, `setSV` moves
it, pid_control.py:1816-1818), plus a manual escape in Manual SV mode.

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

**Artisan's built-in auto-DROP cannot do it.** `canvas.py:4913-4915` gates the
BT-break detector on `(sample_timex[-1] - sample_timex[timeindex[0]]) > 7*60` —
**auto-DROP cannot fire until 7:00 after CHARGE**, and these roasts drop at
6:20-6:31. `7*60` is a literal, so the Standard/Sensitive `autoDropMode` switch
is never consulted. (For the record, at 1 s sampling Sensitive only changes
`d_drop` from -0.34 to 0.00; `offset_drop` is identical at 0.2.)

**The background path is a scheduled drop, not detection.** `playbackdrop()`
(canvas.py:6120-6131) has a 4-minute gate (`playbackdrop_min_roasttime = 4*60`)
and its own flag `backgroundPlaybackDROP`, independent of event playback
(canvas.py:5146) — so it could be enabled without reintroducing the slider
conflict, via the Artisan Command `playbackdropmode(<n>)` (0 off, 1 by time,
2 by BT, 3 by ET). But it fires on the profile's schedule: by BT it needs the
background's DROP BT to sit *below* where the operator actually pulls (roast 42
peaked at 201.0 against a 202.0 background DROP, so it would never have fired),
and by time it fires at the profile's DROP regardless of the lever. Left off.

**The solution: an alarm on the RoR collapse.** Alarm action 13 = DROP
(canvas.py:6035-6038) with no time gate. Threshold sized from the traces
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
not AND'd — `if alarm_time >= alarmoffset: alarm_ready = True` (canvas.py:5048)
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
target (CHARGE-aligned, as `timealign` does it, canvas.py:5706-5721 — note it
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
| BT smoothing (`curvefilter=3`, weights 1:2:3, canvas.py:4720-4738) | 0.67 s |
| `pid.update()` at canvas.py:4778 runs *before* the SV update at canvas.py:4946 | 1 s |
| plant transport delay (open-loop replay best fit) | **0 s** (2 s already doubles the residual) |

Under 3 s of genuine lag against 12-15 s of apparent lag. The inner loop is
confirmed a non-factor for the third time.

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

`_back_calculate_integral` (pid.py:330-348) runs on **every clamped cycle**
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
  matters — it protects the **preheat**, where a wound-up integrator rails the
  SV and lands the wrong CHARGE_BT — but it does not reach into the roast body.
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
| `dutySteps` | 1 | **1** unchanged | the value is fractional; this only sets cadence, and `force_duty=3` (pid.py:210) already guarantees an update every 3 s |
| `sv_filter` | 0 | **0** unchanged | the background is a Designer curve, already smooth; it would cost 1.33 s of the lookahead |
| `pidDlimit` | 500 | **500** unchanged | inert at `Kd=0`; note it limits `derror` in **degC/s**, before multiplication by Kd (pid.py:275-277), so 500 is effectively infinite against a BT RoR of ~1 degC/s |

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
`_should_integrate` (pid.py:301-316) blocks Ki-driven integration in exactly
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
(pid_control.py:1750), i.e. at 6:48 for a 6:51 background DROP, and canvas.py:4946
only calls `setSV` when `sv is not None`, so **the target simply freezes at its
last value — which is `tgt(6:48 + 3) = tgt(6:51) = 201.2 degC, the profile's DROP
BT.** The loop spends its last ~5 s holding exactly the right final target. At
`L=12` the freeze would start at 6:39 with 25 s to coast; even that is benign
for the same reason. The lookahead cliff, not the window, is what caps `L`.

**Why derivative is not useful here.**

- **DoM (`gamma=0`, current).** `_calculate_derivative` (pid.py:264-274) computes
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
| **Gain scheduling** (`pidGainScheduling`, `...SV`, `...Quadratic`, `pidSchedule0/1/2`, Kp/Ki/Kd sets 1 and 2) | **yes, indirectly** | `getParameter` (pid.py:387-404) fits a line through `(Schedule0, Kp)` and `(Schedule1, Kp1)` — the *base* gains are the value at `Schedule0` — evaluates it at `self.target` when `pidGainSchedulingSV` (the default), and clamps to `[min, max]` of the two. Since `e_ss = (du_req/dt)/Ki` and `du_req/dt` is not constant over the roast, a Ki schedule can flatten the error where a single Ki cannot. Simulated, `Ki 0.18 @ SV 130 -> 0.06 @ SV 200` gives mean **+0.23**, rms **0.31**, max +0.54, min -0.57 — better than any flat Ki. The reverse slope is worse (rms 1.37), so the direction matters. **Gotcha: one schedule serves all three gains**, so `pidKp1` must be set equal to `pidKp` and `pidKd1` to `pidKd` or Kp and Kd get scheduled too. |
| **PoE/PoM, `beta`** (`pidPsetpointWeight`) | **yes — and the wrong way** | `Pterm = Kp*(beta*SP - PV)`. Correcting the first version of this row: beta does *not* merely shift the offset, it enters the velocity error directly as `e_ss = [du_req/dt + Kp*(1-beta)*R] / Ki`, so **any beta below 1 makes ramp lag worse**, and beta above 1 — the direction that would help — is blocked by the integral limits. Derivation, sweep and source in § Proportional on Measurement below. **Must stay 1.0.** |
| **DoE/DoM, `gamma`** (`pidDsetpointWeight`) | **no** | Inert at `Kd=0`; see above for both settings. |
| **`pidDlimit`, `derivative_filter`** | **no** | Inert at `Kd=0`. `Dlimit` clamps `derror` in degC/s **before** the Kd multiply (pid.py:275-277) — 500 is unreachable. `derivative_filter` is a boolean, not a level: `_calculate_derivative` only tests `> 0`, and the filter is a fixed 0.1 Hz first-order lowpass (pid.py:657-661). |
| **`pidIRoC` + `pidIRoCthreshold`** | **no, and it would misfire** | `_handle_setpoint_change_integral` (pid.py:318-328) compares the **per-sample** target change, not a cumulative one. The background's largest per-sample step is **5.48 degC** (in the charge dip), so at threshold 30 it can never fire — the setting is inert, correctly. Lowering the threshold to reach it would zero `Iterm` in the middle of the charge dip, destroying the useful re-seed. Leave off. |
| **`pidIlimitFactor` (ILF)** | **no** | Caps `Iterm` at `100*ILF` (pid.py:52-70). `Iterm` legitimately reaches ~70 mid-roast, so anything below ~0.75 would clip the operating point and reintroduce roast 40's standing deficit. It is a safety cap, not a tuning knob. Keep 1.0. |
| **`pidIWP`** | **no, but load-bearing** | Two mechanisms in one flag: conditional integration *and* back-calculation. Turning it off drains `Iterm` to 0 through the charge dip (simulated I0 = 0.0) and costs 1.6 degC of early tracking. **Keep on.** |
| **`sv_filter` / `duty_filter`** | **no** | `smooth_sv` (pid_control.py:1690-1702) is a 5-tap decay average = **1.33 s of group delay on the target**, i.e. it subtracts 1.33 s from the effective lookahead. `duty_filter` is a 0.35 Hz first-order lowpass on P+I+D, ~0.25 s — measurably nil (rms 0.48 either way). Useful only as a way to blunt the charge dip if a larger lookahead were ever wanted. |
| **Ramp/Soak (`svMode=1`)** vs Follow Background | **no** | `svRampSoak` (pid_control.py:1640-1685) is 8 linear ramp/soak segments starting from `source_reading_pidON`. Same type-1 loop, same velocity error, and it loses charge alignment, the Designer curve's shape, and any representation of the charge dip. Its only structural advantage — no DROP-bounded control window — is worth nothing at `L=3`. **Stay on Follow Background.** |
| **Outer loop on BT RoR** | would remove it, but **not reachable in configuration** | `getCurveNames` (pid_dialogs.py:1262-1269) populates the Input list with ET, BT and the *extra device channel names* only — delta/RoR curves are not offered, and `canvas.py:4762-4777` reads `pidSource` from the raw channel arrays. Controlling RoR needs the firmware to publish RoR as an extra channel (out of scope), plus an RoR background curve for `backgroundXTat`. And on its own it is the wrong control: zero *rate* error leaves BT *position* free to drift, so it would need a BT trim on top — a three-level cascade. Not now. |

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
### Roast 45 (2026-09-02, 21:53) — step 1 applied; the droop is gone, the air schedule is what is left

First run of `pidKi=0.10`, `svLookahead=3` (both confirmed in the alog), same
background `profile_002`, same procedure. Operator's reading: "better again but
still slow and wandering." Both halves have answers, and neither is the outer
loop's gain.

**Read the marks with care — they are not profile crossings.** DRYe and FCs are
fired by `autoDRY`/`autoFCs` on the fixed BT thresholds in the Phases dialog
(`phases=[38, 149, 196, 218]`, canvas.py:4920-4926), while `profile_002`'s own
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

**Artisan no longer has PoM.** `pid_control.py:1252-1253` carries that exact URL
followed by `=> PoM removed in v3.1.2`. What survives is the **PoE/PoM radio
pair in the PID dialog, which only writes `pidPsetpointWeight` (beta)** — PoE
sets beta 1, PoM sets beta 0 (pid_dialogs.py:1199-1210), and the beta spin box
takes anything in `[0, pidPsetpointWeightMax=2]`. Beta feeds plain **setpoint
weighting**, `Pterm = getKp(i) * (beta*target - i)` (pid.py:459), evaluated fresh
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
`applyIntegralLimits` (pid.py:377-382) sets
`integral_max = 100*ILF + getKp(PV)*(1-beta)*target`, so for beta > 1 the ceiling
*shrinks* (to 19 at SP 180, beta 1.15) at precisely the moment the required
`Iterm` turns negative — and `integral_min` is pinned at **0** whenever
`outMin >= 0` (pid.py:59-63). The integrator rails at zero and the roast runs
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

### Commissioning order

0. **Every roast: press ON (zeroes the integrator), turn the PID on, preheat
   under PID control, then CHARGE.** ON is the only thing that clears Iterm
   (§ Roast 41); preheating under the PID stops it winding blind
   (§ PID-driven preheat).
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
