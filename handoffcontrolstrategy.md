# Handoff: Artisan control-strategy research for the airRoaster cascade

## Read first
Repo `/Users/jwmelvin/airRoaster`, branch `feature/artisan-pid`.
Read `state-current.md`, then `state-plan.md` § "Artisan cascade PID" and all its
subsections. They carry every finding so far with `file:line` citations into
Artisan's source. **Do not re-derive what is recorded there.**

## Architecture
A cascade, firmware unchanged:

```
background BT curve (profile_002.alog, Artisan Designer)
  -> Artisan software PID   (outer loop, PV = BT, 1 Hz)
  -> duty 0-100% mapped onto slider 3's subrange [140, 300] degC
  -> slider action: send({"command":"INLET","value":{}})
  -> ESP32 firmware controlStep() (inner loop, 250 ms) holds that inlet air
     temperature by modulating heater duty
```

The inner loop is verified healthy and is **not** the limiting factor: tracking
error rms 2.9 degC, heat peaked at 91% and never saturated. Everything below is
about the outer (Artisan) loop.

## Current config
`artisan/airRoaster_cascadePID.aset` (canonical, committed), background
`artisan/profile_002.alog`.

```
pidSource=1 (BT)          pidPositiveTarget=3 (INLET slider)
positiveTargetRangeLimit=true, positiveTargetMin=140, positiveTargetMax=300
pidKp=3   pidKi=0.04   pidKd=0
svMode=2 (follow background)   svLookahead=0
duty_filter=1  dutySteps=1  dutyMin=0  dutyMax=100
PoE beta=1.00   DoM gamma=0.00   derivative_filter=0   Dlimit=500
IWP=on   IRoC=off (threshold 30)   ILF=1.00   gain scheduling=off
Controlbuttonflag=true   pidOnCHARGE=true   pidOffDROP=true
```

profile_002: CHARGE BT 127.8, DRYe 3:20, FCs 6:30, DROP 6:51 at BT 201.2.

## Artisan source
The shipped `.app` is compiled — no Python in the bundle. A clone already exists
at **`~/src/artisan`, checked out at tag `v4.2.0`** (the installed version).
**Do not re-download it and do not read `master`.** Every citation below is a
v4.2.0 line number; master is ahead by hundreds of lines in `main.py` and
`canvas.py` and reading it has already produced a full round of wrong citations
in this project. See state-current.md § Referencing the Artisan source.

## Established mechanics (verified; reuse, don't re-derive)
- **Output mapping**: PID duty 0-100 is linearly interpolated onto
  `[positiveTargetMin, positiveTargetMax]` (`pid_control.py` `setEnergy`). With
  140/300, **1 duty unit = 1.6 degC of inlet setpoint**, and gains are in
  duty-per-degC-of-BT-error. The fractional value reaches the command
  (`addEvent_internal` passes `raw_value` to the slider action).
- **Integral limits are one-sided [0, 100]**: `integral_min = 0.0` whenever
  `outMin >= 0`, and `integral_max` stays 100 because `beta = 1` zeroes the
  adjustment term (`_calculate_integral_limits`, `pid.py:43-61`;
  `applyIntegralLimits`, `pid.py:360-365`). The integral can never go negative.
- **IWP is two mechanisms in one flag**: conditional integration — integration
  stops once the *unclamped* output exceeds `outMax` (`_should_integrate`,
  `pid.py:286-299`) — *and* back-calculation on every clamped cycle
  (`_back_calculate_integral`, `pid.py:314-333`), which at the **low** clamp
  drives `Iterm` **up**, converging on `Kp*|err|` in seconds with no `Ki` in the
  path. Consequence: the integrator fills fast (either way) and drains only at
  `Ki*err`.
- **The PID does *not* integrate while switched off** (corrected 2026-09-03; an
  earlier version of this doc claimed the opposite). `update()` snaps the target
  to the PV on every inactive sample — `if i is not None and not
  self.isActive(): self.target = i` (`pid.py:406-408`) — so `err = 0` and the Ki
  path adds nothing. At `beta = 1` and `Kd = 0` the P and D terms are zero too,
  the output never clamps, and `Iterm` is **frozen**. It is true that `update()`
  runs regardless of `pidActive` (`canvas.py:5016`; the `if self.active:` guard
  at `pid.py:480` gates only dispatch) and that the SV keeps updating in
  `svMode=2` (`canvas.py:5191`) — the snap overwrites that SV before the error is
  formed. **Caveat:** with `beta < 1` or `Kd > 0` the output *does* rail while
  off and back-calculation winds `Iterm` up. The freeze holds only for
  `beta = 1, Kd = 0`.
- **Nothing clears `Iterm` except monitor ON**: `confSoftwarePID(reset=True)` ->
  `pid.reset()` -> `init()`, from `OnMonitor()` alone (`pid_control.py:1472`,
  `canvas.py:13439`). Not PID ON (`pidOn()` uses the default `reset=False` and
  `setTarget(..., init=False)`, `pid_control.py:1519-1526`; `on()` deliberately
  does not init, `pid.py:335-341`), not RESET, not DROP, not the PID dialog, not
  loading settings. There is no `pidReset()` Artisan command. Operating
  procedure is therefore: press ON, turn the PID on, preheat under PID control,
  then CHARGE — **one PID on/off cycle per monitor ON/OFF cycle**, and a fresh
  OFF -> ON between roasts (RESET alone carries the integrator over).
- **`svLookahead` also bounds the control window**: `calcSV` returns None once
  `tx + svLookahead > timeB[timeindexB[6]]` (the background's DROP), which
  deactivates follow-background and leaves the PID on a stale target.
- Auto-DROP is handled by an alarm (From DRY END, offset 0, DeltaBT below -25 ->
  DROP) and works. Not in scope here.

## The open problem
Roast 44 tracks the background with a persistent **positive** error (target above
actual) that scales with the background's ramp rate:

| tau | bg RoR degC/min | error degC | error/RoR |
|---|---|---|---|
| 2:00 | 34.2 | +2.6 | 4.6 s |
| 2:45 | 23.9 | +4.2 | 10.5 s |
| 3:30 | 19.2 | +3.9 | 12.2 s |
| 4:15 | 16.5 | +3.7 | 13.4 s |
| 5:00 | 14.1 | +3.1 | 13.1 s |
| 5:45 | 11.9 | +2.7 | 13.6 s |
| 6:30 |  9.8 | +1.6 |  9.8 s |

The near-constant ratio (~12 s median) is the signature of **ramp-following
(velocity) lag**, not a static offset and not instability. Marks came in at
DRYe 3:23 / FCs 6:39 / DROP 7:03 against the profile's 3:20 / 6:30 / 6:51;
CHARGE_BT 128.3 against a 127.8 target; DROP BT 200.7 vs 201.2.

**The operator's judgement is that this is not close enough yet**, and asks
whether it simply needs more integral or whether a different control mode fits
better. Treat "more Ki" as a hypothesis to test, not the answer.

## Task

**Analyze only roast 44.** `/Users/jwmelvin/Documents/artisan/airRoaster_44.alog`
and `/Users/jwmelvin/Downloads/airRoaster_data_2026-09-03-01-22-32.csv` (firmware
telemetry: time, IN, BT, SV, heat, fan, mode, P, I, D, FF — note P/I/D/FF there
are the *inner* loop's terms, not Artisan's). Use `downsample_logs.py` at the
repo root. Earlier roasts are analysed in `state-plan.md`; do not redo them.

**Output in this order.**

1. **A concrete PID tuning proposal, staying inside the current simple-PID
   structure.** Specific numbers for `pidKp` / `pidKi` / `pidKd` / `svLookahead`
   and any of `ILF`, `Dlimit`, `dutySteps`, `duty_filter`, `sv_filter`. Tie each
   to the measured lag rather than to rules of thumb, and state what each change
   trades away. Address explicitly:
   - whether raising Ki is the right lever for velocity lag, and what it costs on
     the charge transient (BT falls ~128 -> ~64 in ~30 s);
   - `svLookahead` as ramp feedforward — the natural value is the loop's own lag
     (~12 s) rather than 0 or 20 — against its cost of truncating the control
     window at background DROP minus lookahead (profile_002 DROP is 6:51, roasts
     end ~7:03);
   - why derivative is or is not useful here (with DoM and a rising PV, D opposes
     the ramp).

2. **Then research Artisan's other control options in source and propose an
   alternative strategy.** Evaluate at least: gain scheduling
   (`pidGainScheduling`, `pidGainSchedulingSV`, `pidGainSchedulingQuadratic`,
   `pidSchedule0/1/2`, the Kp1/Ki1/Kd1 and Kp2/Ki2/Kd2 sets — see `getKp`/`getKi`/
   `getKd` and `_getParameterLinearFit` / `_getParameterQuadraticFit` in
   `pid.py`); setpoint weighting PoE/PoM (beta) and DoE/DoM (gamma); derivative
   with `Dlimit` and `derivative_filter`; `IRoC` + `pidIRoCthreshold`; `ILF`;
   Ramp/Soak (`svMode=1`, the RS1/RS2/RS3 tabs) versus Follow Background; the
   `sv_filter` / `duty_filter` smoothing; and whether the outer loop should
   control **BT RoR** instead of BT. For each, say whether it addresses
   ramp-following lag *specifically* — several will not.
   Deliver a recommended strategy: the config changes it needs, what it fixes,
   its risks, and how to validate it in a single roast.

## Constraints
- **Artisan configuration only.** Firmware is out of scope. Do not modify
  `artisan/make_inlet_background.py`.
- **Verify against source with file:line. Do not trust setting names.** The prior
  context was caught out three times: `dutyMin`/`dutyMax` are duty percentages
  not degC (setting 120 there would have pinned the setpoint at maximum
  permanently); `PID_OFF_action` never fires for the software PID; alarm time and
  temperature conditions are OR'd, not AND'd.
- Settled decisions — BT as the PV, follow-background SV, the 140/300 subrange,
  the PID-driven preheat, the DROP alarm — may be revisited, but only with an
  explicit reason; the rationale for each is in `state-plan.md`.
- State-docs discipline: read `state-current.md` first; record outcomes in
  `state-current.md` and `state-plan.md`. Commit per phase, staging files
  explicitly (the operator's `artisan/*.aset` and `*.alog` churn must not be
  swept in).
