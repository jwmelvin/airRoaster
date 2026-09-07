# state-history — the cascade PID investigation record

> Companion to [state-current.md](state-current.md) (what is active now),
> [state-plan.md](state-plan.md) (what is planned, and the specifications in
> force) and [state-archive.md](state-archive.md) (completed work and the
> F-numbered review findings).
>
> **What this file is.** The roast-by-roast reasoning behind the Artisan
> cascade PID — measurements, refits, operator questions and the answers they
> produced, including the ones later overturned. It was split out of
> state-plan.md on 2026-09-06, which had grown to 3,900 lines of which the
> greater part was superseded narrative rather than plan.
>
> **Read it in order.** Unlike state-archive.md this file is **chronological,
> oldest first**, because later sections routinely correct earlier ones — the
> loop's plant identification, the source of roast 45's ringing, and the value
> of the `Ki` gate were each revised at least once. A finding here is only
> current if nothing below it says otherwise, and the settled conclusions live
> in state-plan.md, not here.
>
> Sections that are still *in force* — the `.aset` specifications, the
> characterisation-run files, the step-9 feedforward design, the ruled-out
> list, and the runbook — stayed in state-plan.md and are referenced from here
> as `state-plan.md § …`.

## Contents

- [Roast 40](#roast-40) — first cascade run, and the gains it produced
- [Roast 41](#roast-41) — inner loop validated, outer loop ringing
- [PID-driven preheat](#pid-driven-preheat) — the operator decision that moved the floor to 140
- [Roast 42](#roast-42) — the retune works
- [Roast 44](#roast-44) — clean validation run; phase complete
- [Roast 44 outer-loop analysis](#roast-44-outer-loop-analysis) — the droop is integrator-rate-limited
- [Roast 45](#roast-45) — step 1 applied; the droop is gone
- [Proportional on Measurement](#proportional-on-measurement) — asked, examined, rejected
- [Correction: roast 45's error is the loop, not the air](#correction) — the plant identification was circular
- [The output floor / range analysed](#the-output-floor)
- [profile_003](#profile_003) — the TP correction and the lookahead trade
- [Scheduling, characterisation runs, and the fan](#scheduling)
- [Fan vs batch size: no relationship](#fan-vs-batch-size)
- [Logging the control effort in one file](#logging-the-control-effort)
- [Firmware now in scope](#firmware-now-in-scope) — the probe measurement and the v0.19.0 items as built
- [Roast 46](#roast-46) — step 1 passes; the ramp is solved, the dip is not
- [Roast 46 refit](#roast-46-refit) — the plant, a validated simulator
- [The dip is a different control problem](#the-dip) — gate Ki through it
- [Charge temperature](#charge-temperature) — roast 46 was frozen
- [Dip strategies](#dip-strategies) — the wider search
- [Roast 47](#roast-47) — Test A: the schedule replays, `feedforward()` refitted
- [Roast 48](#roast-48) — the loaded characterisation; the empty map transfers, `kf = 0`
- [Roast 49](#roast-49) — step 6 passes, and the charge was not frozen
- [Deadtime versus lag](#deadtime-vs-lag) — the 13.5 s is total apparent lag, not transport; the tuning and the base schedule both stand

## Cascade PID — the investigation record

<a id="roast-40"></a>

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
precisely the hazard state-plan.md § The floor exists to prevent. It did not
trigger (output never got that low) but it was live for the last 90 s. Both were
reverted.

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

<a id="roast-41"></a>

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

<a id="pid-driven-preheat"></a>

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

<a id="roast-42"></a>

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

<a id="roast-44"></a>

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
<a id="roast-44-outer-loop-analysis"></a>

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
<a id="roast-45"></a>

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
<a id="proportional-on-measurement"></a>

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
<a id="correction"></a>

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

<a id="the-output-floor"></a>

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
and the firmware disengages with heat off mid-roast (state-plan.md § The floor).

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

<a id="profile_003"></a>

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
and not CHARGE (state-plan.md § Auto-DROP detection).

**The background is not carried in the settings file.** There is no
`backgroundpath` key in `airRoaster_cascadePID.aset` — the reference lives in
each saved profile. profile_003 has to be loaded as background per session.

<a id="scheduling"></a>

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

Cautions: alarm time and temperature conditions are **OR'd** (state-plan.md §
Auto-DROP detection), so a time-only alarm needs source -3 and the temperature
row left inert. And the switch is a step in the target of `L * RoR` — at 1:00
the background runs ~46 degC/min, so 6 s of lead is a +4.6 degC target step and
about +22 degC of SV. Apply it at 1:30-2:00 where the RoR is lower, or in two
steps (0 -> 3 -> 6). **Introduce on its own roast.**

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

<a id="fan-vs-batch-size"></a>

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

<a id="logging-the-control-effort"></a>

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

<a id="firmware-now-in-scope"></a>

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
outer-loop instrumentation and the outer-loop restructuring land in **one
flash**. It is the firmware half of state-plan.md § Step 9 — the inlet
feedforward schedule with the PID as a trim — and of runbook step 9, and it is
inert until Artisan is reconfigured to use it — nothing about the present
cascade changes when it is flashed.

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
is per event type (canvas.py:1848), so background playback drives the base on
one slider while `pidPositiveTarget` (any of sliders 1-4, pid_control.py:1252)
points the PID at a second slider bound to `INLET TRIM {}`. That is the
collision that forced playback off for the cascade (state-plan.md § Background
event playback must be off), and putting the two on different sliders is what
dissolves it. The base curve goes into the background as replayable events —
**not** something `artisan/make_inlet_background.py` emits today; see § Dip
strategies § The base-curve authoring gap. **Do not configure any of this until
steps 3-5 have measured `1/a` and the loss curve** — the schedule *is* those two
things.

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
float). Buffers: status push 176 → 224 (worst case 168), `STAT` 112 → 176 (worst
case 127), the new `inlet` report 128 (worst case 86). Dashboard gains a `base +
trim = SV` readout and a trim entry/0/Read row in the Setpoint panel, fed by the
status push (no connect-time `INLET TRIM` prefill — that command is
`TIER_DRIVE`, and the device already broadcasts status on connect). README:
command table, tunables table, status-push field table, `STAT`, the auth safe
subset, and a new § Base + trim. **Bench drill: state-plan.md § NEXT item 14** —
the acceptance list above has not been run on hardware.

> **The two forward-looking parts of this section stayed in the plan**: the
> predicted-BT (`BTP`) channel and the dump-lever instrumentation are in
> state-plan.md § Open firmware ideas. What remains here is the probe
> measurement and the two v0.19.0 items as built.

<a id="roast-46"></a>

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
switches 0 -> **6** at CHARGE+90 s (state-plan.md § The lookahead-switching
config). That value was chosen before this roast on margin grounds and the data
independently picks it out. Nothing needs re-deriving; the file needs running.

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

<a id="roast-46-refit"></a>

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

<a id="the-dip"></a>

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

<a id="charge-temperature"></a>

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

<a id="dip-strategies"></a>

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

> **The rest of § Dip strategies stayed in the plan.** The structural fix it
> arrived at — the inlet feedforward schedule with the PID as a trim — is
> state-plan.md § Step 9; the authoring gap and its closure are
> state-plan.md § The base-curve authoring gap; the rejected approaches are
> state-plan.md § Ruled out; and the charge-state proxy that is still open is
> state-plan.md § The one adaptive idea that is still open.


<a id="roast-47"></a>

### Roast 47 (2026-09-06) — Test A: the schedule replays, and `feedforward()` is refitted

Runbook step 3, the first characterisation run and the first use of the replayed
schedule: empty roaster, PID off, background `charstep_empty_fan.alog`, config
`airRoaster_cascadePID_char.aset`. 1064 samples, CHARGE at index 2, run to 17:00.

**The mechanism works.** Every one of the 13 scheduled events fired at its
authored time — seven `T_inlet` and six `Air` — and the inner loop held the
commanded setpoint to **rms 1.12 degC over 619 quiet samples, mean +0.00**. The
PID never armed, which is the check that matters on `pidOnCHARGE = false`: had it
armed it would have driven slider 3 against playback and the event list would be
hundreds of entries, not thirteen. **v0.19.0's `SV` and `HT` channels are live**
and this is the first roast whose commanded setpoint and heat percent are in the
profile itself; no dashboard CSV was needed and none was taken.

#### The one failure: Artisan's *built-in* auto-DROP, which is not an alarm

At 605 s the DROP button chain ran on its own — `T_inlet 0` and `Heater 0` in the
event list — and the operator's cooldown took the fan to 100 at 633 s. Inlet fell
184 -> 45 degC and BT 175 -> 82 before it was put back together by 647 s; the
721 s leg of the schedule then fired on time and the run finished normally.
**88% of the run is usable and one steady window was lost** (fan 80 / SV 145).

The cause is **`autoDrop`, Artisan's own DROP detector** (canvas.py:5151), and
the important thing about it is that **it is not an alarm and `alarmflag` does
not touch it**. Its gate is `autoDropFlag` and BT > 160 degC and **more than
7 minutes since CHARGE**, after which any `BTbreak` marks DROP. The 601 s inlet
step-down from 185 to 145 is exactly such a break, at 10:01.

That gate is why it has never been seen before: these roasts drop at 6:20-6:31,
which is the whole reason the DeltaBT alarm exists (state-plan.md § Auto-DROP
detection). **Every characterisation run is longer than 7 minutes and sits above
160 degC**, so it fires on all of them. `airRoaster_cascadePID_char.aset` now
also carries `autoDrop = false`. It would have fired on both loaded doublets too
— they plateau at BT ~185 and the fan square wave steps at 7:00 and 8:00 — and
would have cost the last third of the fan measurement, which is the part those
runs exist for.

#### `feedforward()` refitted — the proposed coefficients were badly wrong

Nine steady windows, fan **58-80** crossed against SV **145** and **185**, each
averaged over the 30 s before the next slider change (`tools/analysis/roast47_ff.py`):

| fan | 145 degC | 185 degC |
|---|---|---|
| 58 | 41.5 | 48.1 |
| 64 | 48.5 / 47.1 | 56.6 |
| 72 | 52.8 / 53.5 | 65.2 |
| 80 | *(lost to the DROP)* | 76.3 |

Within-window sd is 0.39-1.50%, so the grid is well resolved. Three models:

```
affine      heat = -60.66 + 1.0992*fan + 0.2536*SV                       rms 1.63 %
mass-flow   heat =  +6.31 + 0.5295*fan*(SV-28)/100                       rms 2.99 %
+product    heat = +69.87 - 0.8570*fan - 0.5101*SV + 1.1423*fan*SV/100   rms 0.68 %
            = 0.011423*(fan - 44.7)*(SV - 75.0) + 31.6
```

**The model runbook step 8 proposed — `heat = -30.62 + 0.99*fan + 0.0096*SV` —
under-predicts by 10.8 to 25.9% across the whole grid, and its `SV` coefficient
is 26x too small.** The fan coefficient survives (0.99 against a measured 1.099);
it is the setpoint term that was never identified, because the five preheat fan
steps it came from held SV nearly constant. This is precisely the short-lever-arm
failure the run was designed to fix, and it means **step 8 as written would have
replaced a saturated feedforward with a badly biased one** — better, but still
leaving `pidITerm` to supply 10-26 duty of standing offset.

**The product term is worth its multiply.** It more than halves the residual, it
is the physically right shape (power = mass flow x temperature rise), and it
**extrapolates better**: at roast 46's own preheat point of fan 60 / SV 240 —
55% measured, well outside the fitted box — the product form predicts 60.5 and
the affine form 66.1. Nine points and four parameters is close to the noise
floor, so the affine form remains the conservative choice; the product form is
the recommendation. Coefficients are carded in `tools/analysis/ff_roast47.json`.

**Two caveats on the fit.** It is an *empty* chamber. The inlet thermocouple sits
upstream of the bed, so the heat needed to reach a given inlet temperature should
not depend on a load — but that is an argument, not a measurement, and the loaded
doublets are the check. And the fitted box is fan 58-80 / SV 145-185, while the
roast runs to SV ~270; the roast-46 extrapolation check is the only evidence
beyond it.

#### What the fan steps cost the inner loop, with the feedforward dead

Worst inlet excursion in the 40 s after each fan step, all of them at +2 s:

| step | 64->72 | 72->58 | 58->80 | 80->64 | 64->72 |
|---|---|---|---|---|---|
| degC | -4.8 | +5.5 | **-13.2** | +8.0 | -3.0 |

Roughly 0.6 degC per fan unit, recovered within seconds by the integrator. This
is the disturbance `feedforward()` exists to cancel and currently does not
(state-history.md § Roast 46: `FF = 100.0` for 430 of 430 samples, so
`d(FF)/d(fan) = 0`). It also sets the scale for the loaded runs: their 60/70
square wave should show ~6 degC of inlet transient per transition until step 8
lands.

<a id="roast-48"></a>

### Roast 48 (2026-09-06, 14:59) — the loaded characterisation, and the empty map transfers

Runbook steps 4-5, and the first roast on **v0.20.0**. Not the two-batch doublet
pair: with 617 g of sacrificial stock the operator ran **Test A's design over
again with beans in it** — `tools/gen_char_single.py`'s one 400 g batch, the
inlet parked at three flat setpoints with a fan step taken inside each, rather
than the 3:00-5:00 doublet plus a 60/70 square wave. Background
`charsingle_400g.alog`, config `airRoaster_cascadePID_char.aset`, DROP by hand at
12:30. 400 g in, 350 g out (12.5% loss), BT peaked at **184.6 degC** against the
generator's simulated 185.7 and never approached first crack, as designed for a
sacrificial batch. Analysis: `tools/analysis/roast48_ff.py`, card
`tools/analysis/ff_roast48_loaded.json`.

**The mechanism replayed again and `autoDrop = false` held.** All 45 scheduled
events fired at their authored times — every fan step (0/64, 90/60, 195/66,
240/60, 360/66, 405/60, 525/70, 585/60, 645/70, 705/60) and every inlet step
(165/245, 270/150, 330/215, 435/150, 495/190). The 7:15 inlet step-down from 215
to 150 is precisely the `BTbreak` at BT 184 and CHARGE+7:15 that took 88 s out of
roast 47, and **it did not fire**: the `autoDrop = false` the char config gained
after roast 47 is confirmed on the run it was written for. Heat touched 100% for
3 samples of 751 and 0% for 3, both inside inlet step transitions.

#### The bean bed does not move the feedforward map

Fourteen steady windows, fan 60-70 crossed against SV 140-245, each averaged over
the 30 s before the next slider change and starting 12 s after the previous one.
Against the **empty-chamber** map now flashed in v0.20.0
(`heat = 69.8685 - 0.8570*fan - 0.5101*SV + 1.1423*fan*SV/100`):

| | measured | empty map | error |
|---|---|---|---|
| fan 60 / SV 150 | 42.3, 42.6 | 44.7 | +2.45, +2.10 |
| fan 60 / SV 190 | 50.6, 49.5, 49.7 | 51.7 | +1.18, +2.28, +2.04 |
| fan 70 / SV 190 | 64.1, 64.0 | 64.9 | +0.82, +0.91 |
| fan 60 / SV 215 | 55.8, 54.4 | 56.1 | +0.37, +1.74 |
| fan 66 / SV 215 | 64.9 | 65.7 | +0.77 |
| fan 60 / SV 245 | 60.1, 59.8 | 61.4 | +1.32, +1.54 |
| fan 66 / SV 245 | 75.4 | 73.0 | **-2.38** |
| fan 64 / SV 140 | 46.1 | 46.0 | -0.14 |

**Bias +1.07%, rms 1.61%, worst +2.45%** — against the empty run's own residual
of 0.68%, and with every row but the last two *extrapolated* in SV, since roast
47's fitted box stops at SV 185. That is the open question in state-current.md
§ Step 8 answered: **a 400 g bed does not change the heat a given fan level and
setpoint cost**, and `FF SLOPE` has nothing to correct. The argument the card's
note rested on — the inlet thermocouple sits upstream of the bed — now has a
measurement behind it.

#### The fan slope, which is the part that would have mattered

`FF SLOPE` exists because a bed changes the pressure drop and so the flow a fan
level delivers. Eight step pairs, each a step up and the matching step down:

| SV | steps | measured %/fan-unit | empty map | ratio |
|---|---|---|---|---|
| 190 | 60↔70, twice | 1.35, 1.46, 1.45, 1.43 | 1.313 | 1.03-1.11 |
| 215 | 60↔66 | 1.53, 1.76 | 1.599 | 0.96-1.10 |
| 245 | 60↔66 | 2.56, 2.59 | 1.942 | **1.32-1.34** |

Mean ratio 1.130. **Do not read the SV 245 row as a load effect.** Roast 47's fit
box is SV 145-185, so at SV 245 the "empty map" column is an extrapolation 60 degC
beyond its data, and the measured column is one end of roast 48's own three-point
line. The two agree where they overlap and diverge only where each is guessing.
The honest statement is the pooled one below.

Three setpoints is the smallest design that can see curvature in
`slope(SV) = c_fan + c_fansv*SV/100`, and this is the first data that has it.
The line through the three loaded points is `-2.740 + 2.133*SV/100`, rms 0.141
%/fan-unit — steeper than the empty map's `-0.857 + 1.142*SV/100`, but on one
degree of freedom and over a range where the two designs barely overlap. Not
enough to act on.

#### Pooled, the flashed map is right to under 2% everywhere the cascade runs

The two characterisation runs cover boxes the other does not — roast 47 spans
fan **58-80** at SV 145/185, roast 48 spans SV **140-245** at fan 60-70 — so put
through one estimator and fitted together they cover the box a roast actually
uses. 25 windows:

```
pooled   heat = 82.71 - 1.0774*fan - 0.6255*SV + 1.3294*fan*SV/100    rms 1.21 %
```

Against the coefficients flashed in v0.20.0, over fan 58/64/70 × SV 150/200/250,
the largest disagreement anywhere is **1.65%** (-1.7 at fan 58 / SV 250, +1.3 at
fan 70 / SV 250). **There is nothing to reflash.** Adding a load *offset* to the
pooled fit gives -1.67% and takes the residual 1.21 -> 1.02; adding a
load × fan × SV term gives -0.0137 and 1.05. Both are small, both are weakly
separable from the fact that the loaded run is the only source of SV > 185 and
the empty run the only source of fan outside 60-70 — and an offset is absorbed by
the inner loop's integral trim within seconds anyway. Only a change in the fan
*sensitivity* would survive, and that is the row that does not clear the noise.
The pooled coefficients are carded under `pooled` in `ff_roast48_loaded.json` as
the fit to flash if `feedforward()` is ever recalibrated.

#### The feedforward works — fan-step rejection is 4x better than roast 47

This is the first roast with `feedforward()` live rather than clamped at 100.
Worst inlet excursion in the 40 s after each fan step at a flat setpoint, with the
window closed before the next inlet step:

| step | 60→66 | 66→60 | 60→66 | 66→60 | 60→70 | 70→60 | 60→70 | 70→60 |
|---|---|---|---|---|---|---|---|---|
| degC | -1.5 | +1.0 | -0.5 | +1.0 | -0.8 | -1.0 | -1.5 | +1.0 |

**About 0.13 degC per fan unit, against roast 47's 0.50** (-4.8 on 8 units, +5.5
on 14, -13.2 on 22, +8.0 on 16, -3.0 on 8, all at +2 s, with `d(FF)/d(fan) = 0`).
The largest disturbance in the whole run is 1.5 degC on a 10-unit step. Roast
47's own prediction was that the loaded runs "should show ~6 degC of inlet
transient per transition until step 8 lands"; step 8 landed, and they show 1.5.
The heat channel shows why: it moves 59 -> 76 within 5 s of the step, which is the
map stepping, not an integrator climbing.

**Inner-loop tracking is rms 0.40 degC over 226 quiet samples, mean +0.00**
(roast 47: 1.12 over 619), and all 14 steady windows sit inside ±0.30 degC of the
commanded setpoint. Commanded inlet steps of -95, +65, -65 and +40 degC settle to
within 2 degC in **3-6 s**.

#### Two Artisan settings this run exposed, and both should change

**Artisan destructively rewrites the two samples before every step in a
constant-valued channel, and it is a settings problem, not a fact of life.**
This was first read here as a 3-sample moving average; it is not. `inputFilter`
(canvas.py:4535) ends with an *"improve a previously corrected reading"* repair
that assumes any run of equal readings was produced by drop-out replacement and
un-sticks it by linear interpolation toward the new value — in the array that
gets **saved**:

```python
if (self.minmaxLimits or self.dropSpikes or self.dropDuplicates):
    if len(tempx) > 2 and tempx[-1] == tempx[-2] == tempx[-3] != temp:
        delta = (tempx[-3] - temp) / 3.0
        tempx[-1] = tempx[-3] - 2*delta;  tempx[-2] = tempx[-3] - delta
    elif len(tempx) > 1 and tempx[-1] == tempx[-2] != temp:
        tempx[-1] = (tempx[-2] + temp) / 2.0
```

The gate is *any* of the three filters and no spike need ever have been detected.
`dropDuplicates` ("Interpolate Duplicates") and `minmaxLimits` are **false** in
every cascade `.aset`; **`dropSpikes` ("Drop Spikes", Config › Curves › Filters)
is `true`, and on its own it opens the gate.** So a channel that is constant
*by construction* — which is exactly what `SV` and `HT` are — trips a repair
written for a stuck sensor. SV 245 → 150 is stored as 245, **213.33, 181.67**,
150; the integer heat channel carries thirds (59.7, 75.3, 64.7); `amb` reads
28.36666667.

**It does not damage this run's conclusions, and it does damage transient
timing.** The substituted ramp is nearly mean-preserving: dropping every
non-integer heat sample moves the 14 window means by at most **0.10%**, against
a fit residual of 0.68-1.6%, so the feedforward numbers above stand as measured.
What it corrupts is anything read across a transition. Read naively this run's
inner-loop tracking is rms 2.79 degC with a worst sample of +29.6; the whole
difference from the true 0.40 is four fabricated samples sitting before inlet
steps. `roast48_ff.py` opens every guard `FILTER = 3` seconds *before* a step,
not after it.

**The fix is to untick "Drop Spikes"**, and it should be done before the next
characterisation run. The repair is not separately switchable, so there is no way
to keep spike rejection and lose the fabrication. The cost is real but small
here: the firmware already rejects faulted and stale RTD samples on-device
(hardware/emi.md), which is where this project's spikes come from, and Artisan's
own tooltip scopes the feature to "large spikes".

**And Artisan can sample much faster than 1 Hz — `min_delay` is 100 ms**
(canvas.py:608; `default_delay` is 2000). Config › Sampling accepts 0.10-999.99 s
in hundredths and only warns below 2 s. **Critically, the outer loop's tuning
does not depend on it**: `Iterm += getKi(i) * err * dt` with `dt = now -
lastTime` in real seconds (pid.py:439), `Kp` is rate-free, and `svLookahead` is
added to `tx` in **seconds** (pid_control.py:1707, and the comment at :50). So
`Kp 3.0 / Ki 0.07 / svLookahead 3` carry over unchanged to a faster rate. Two
things do move. Every sample is one `getData` round trip, so the WebSocket load
scales. And `curvefilter` is a count of *samples* (3), so its time span halves —
including the decay-average that produces the PID's own PV, which
state-current.md § Roast 44 costs at 0.67 s of lag; at 0.5 s that becomes 0.33 s,
which is less phase lag and slightly more noise into the loop. **RoR is not
affected**: `deltaBTsamples` is *derived* from `deltaBTspan` (20 s, stored in the
`.aset`) and the interval by `updateDeltaSamples` (canvas.py:2796), so the RoR
span in seconds is preserved automatically. Below **0.25 s** there is nothing
left to gain: that is the firmware's `controlStep()` period, so Artisan would be
resampling the same control decision.

**Both changes are made**: `Delay` 1000 -> 500 and `dropSpikes` true -> false in
`artisan/airRoaster_cascadePID.aset`, propagated to all four variants by
`tools/gen_pid_alarm_asets.py` (operator decision 2026-09-06). `curvefilter` is
left at 3 deliberately — it is the one setting whose *time* constant moves, and
changing it in the same step would put two variables in one roast.

**A slope measurement costs ~45 s, and this run confirms it at load.** Roast 47
measured heat reaching 95% of its final value within 2 s of a fan step; roast 48
shows it settling in 3-6 s with beans in the chamber and then holding flat, which
is what let the SV 245 and SV 215 blocks be only 30 s long. That is the assumption
`gen_char_single.py` was built on and it held.

#### What the run did not give

`greens_temp` is still `0.0` — the runbook asks for it on every roast from now on
and it was not filled in. The charge-state proxy `(CHARGE_BT - BT at CHARGE+13 s)
/ mass` reads **7.47 degC/100 g** against the 14.46 ± 0.48 of the frozen roasts
43-46, but it is **not comparable**: those charged into a chamber at BT ~128 under
PID-driven preheat, and this one charged at BT 84.3 with the schedule starting
from inlet 129, so the driving temperature difference is not the same. It is
evidence of a warm charge, not a measurement of one.

#### The plant refit: the fan is settled, the deadtime is questioned, `a` is not

`tools/analysis/roast48_plant.py`, card `tools/analysis/plant_roast48.json`. This
is the first run whose excitation was *designed* — roast 46 identified a plant by
accident, when a 400 g batch against a 345 g dip drove the commanded inlet rail
to rail. Roast 48 steps the inlet by -95, +65, -65 and +40 degC at
270/330/435/495 s with the PID off, so there is no controller correlating input
with output. There is no PID-replay or closed-loop section here for that reason.

**The fan term in the plant is 0, and that is the run's clean result.** Fitting
`dBT/dt = a*(1 + kf*(fan-60))*(Inlet(t-theta) - BT) + loss(t)` over the whole
window puts `kf` at **+0.0000**, with the 1%-of-residual band running -0.004 to
+0.002. Forcing it up costs residual monotonically:

| `kf` | % of plant gain per 10 fan units | residual | × best |
|---|---|---|---|
| 0.000 | 0 | 0.5804 | 1.000 |
| 0.005 | 5 | 0.5894 | 1.016 |
| 0.010 | 10 | 0.6111 | 1.053 |
| 0.020 | 20 | 0.6818 | 1.175 |
| 0.030 | 30 | 0.7740 | 1.334 |
| **0.049** | **49** | 0.9692 | **1.670** |

The 49% figure is the one § Correction measured from roast 45 and that
state-current.md later retracted for circularity — the disturbance had been a
free `w(t)`, which absorbs whatever it is asked to. **This replaces the retraction
with a bound**: at a fixed inlet temperature, airflow over 60-70 does not change
the rate at which the bed heats, to within about 5% of plant gain per 10 units.
That closes the last item state-current.md § Tests A/B/C kept the characterisation
runs alive for — "the fan, still a single weakly-identified coefficient".

Physically it is worth stating what this does and does not say. It is **not** that
airflow does not matter; `roast48_ff.py` measures 1.3-2.6% more *heat* per fan
unit to hold the same inlet temperature, which is the same air carrying more
enthalpy past the element. It is that once the inlet air is at a given
temperature, delivering 17% more of it does not measurably speed the bed up over
this range. The bed is not flow-limited here.

**`a` and `theta`, on the other hand, are not stationary, and roast 48 does not
supersede roast 46's card.** The whole-window fit reads `theta 8.5 s, a 0.00802,
tau 125 s` against roast 46's `13.5 / 0.00490 / 204` — a 1.64x gap. But refit on
sub-windows of roast 48 itself:

| window | theta | `a` | tau | resid |
|---|---|---|---|---|
| 45-300 | 5.50 | 0.00249 | 401 | 0.124 |
| 45-430 | 8.50 | 0.00729 | 137 | 0.479 |
| 165-450 | 7.75 | 0.00615 | 163 | 0.309 |
| 300-750 | 10.50 | 0.00846 | 118 | 0.437 |
| 450-750 | 14.50 | 0.00695 | 144 | 0.254 |

45-300 is under-excited — it holds one inlet step, at its very end — and is the
outlier. The rest still spread `a` 0.0062-0.0085 and `theta` 7.8-14.5, **as wide
as the disagreement with roast 46**. So the gap is not evidence that roast 46 is
wrong. The two runs also measured different roasters in a real sense: roast 46 is
a closed-loop real roast on a frozen charge running to BT 200+, roast 48 a warm
sacrificial batch held under 185 by a schedule that parks the inlet 20-70 degC
above BT for minutes at a time. **`plant_roast46.json` stays the authoring source
for `merge_inlet_base.py`**, and `plant_roast48.json` carries
`supersedes_plant_roast46: false` and a note saying so.

**What the instability does point at is the model, not the data.** The two-lag
estimator — `Inlet -> 1/(1+tau2 s) -> a/(s+a) -> BT`, which
`plantfit.fit_integral_2lag` has carried unused since roast 46 — fits the same
windows with **`theta` collapsing to ~0** and a 10-25 s first lag in its place,
and takes about a third off the residual on every well-excited window
(45-430: 0.353 against 0.479; 165-450: 0.188 against 0.309; 300-750: 0.217
against 0.437). **The 13.5 s "deadtime" carried since roast 46 is at least partly
a lag**, which matters because a lag and a delay cost very different amounts of
phase margin. `a` still drifts (0.0074-0.0139 two-lag), so this is a better
structure rather than a finished one.

**None of this reopens the tuning, and the reason is empirical.** Against roast
48's plant, Kp 3.0 / Ki 0.07 has 44.5 deg of phase margin and Ki 0.15 still has
21.5, which would say there is room above 0.07; against roast 46's the same gains
give 33.7 and 9.2. The tie-breaker is the one closed-loop behaviour actually on
record: **roast 45 rang at 177 s at Ki 0.10**, and roast 46's plant predicts
190 s there while roast 48's predicts 135 s. The card fitted to a real roast
predicts the real roast. **`pidKi` 0.07 stands.**

<a id="roast-49"></a>

### Roast 49 (2026-09-06, 15:51) — step 6 passes, and the charge was not frozen

Runbook roast 1, at last: `airRoaster_cascadePID_lookahead.aset` loaded
unmodified with background `profile_003`, 400 g of the same Ethiopia the whole
series has used, PID-driven preheat, no intervention. 1032 samples at **0.511 s**
— the first roast at the new sampling rate — DROP by the DeltaBT alarm at 7:03,
400 g in, 353.2 g out. Analysis: `tools/analysis/roast49_step6.py` and
`tools/analysis/charge_state.py`.

**The lookahead switch fired and did what the simulator said it would.** Against
state-plan.md § Step 6's predictions, with roast 46 as the one-variable baseline
in the third column:

| | predicted | roast 49 | roast 46 |
|---|---|---|---|
| steady tracking error, 3:00-DROP-10 | +0.05 degC / 0.44 s | **+0.40 degC / 1.84 s** (rms 0.47) | +1.06 / 4.73 (rms 1.09) |
| time to BT 150 / 180 / 196.5 vs profile | -1.9 / +3.2 / +0.9 s | **-0.9 / +2.2 / +2.0 s** | +3.4 / +4.9 / +4.8 |
| at 1:30: target step -> commanded SV | +4.0 -> +24.7 degC, ~15 s | **+3.96 -> +21.2 in 2 s, +31.6 peak, 95% in 12 s** | — |
| floor time in the charge dip | 16 s | **29.2 s** (last at 0:59) | 11 s |
| SV max / worst reversal after 1:00 | 296 / 3.2 degC | **232 / 7.7 degC at 2:24** | 289 / 0.3 |

Rows 1-3 are the experiment and they pass. The standing lag is **2.6x smaller**
than roast 46's and the roast now runs within ±2.2 s of the profile at every
BT — the type-1 ramp error that `svLookahead` exists to cancel is, for practical
purposes, cancelled. The switch itself behaves as designed: a +3.96 degC target
step, +21.2 degC of commanded SV inside two samples and 95% of the excursion
within 12 s, with the +31.6 degC peak being the two-sample jump plus the
integrator's normal climb. There is no ring: after 1:40 the tracking error stays
inside **-1.94 .. +0.93 degC** for the rest of the roast, the -1.94 being the
mild overshoot the kick manufactures and which is gone by 3:20.

Rows 4 and 5 miss, and **both misses are the charge state, not the loop** — see
below. The dip ran BT 12 degC *above* the background instead of roast 46's 9.8
below, so the error went to -16 degC, the output floored for 29 s and
`_back_calculate_integral` seeded `Iterm` to 49 at 0:45 (it had drained to 25.0
by 1:30, and reached 54.5 at DROP). The "reversal" is the settle after the 1:30
kick, one monotone decay from SV 196.1 at 1:50 to 188.6 at 2:24, not an
oscillation. Note the floor never killed heat: the inner loop held inlet 140 at
44-48% heat throughout.

**The simulator carries over to 0.5 s sampling unchanged.** Replaying the
measured BT through the ported `PID.update()` at `sampling_rate = 2` reproduces
the commanded SV to **rms 0.83 degC over 0:30-DROP and 0.44 after 4:00** — the
same numbers as roast 46 at 1 Hz, and the same 1 degC slider-gate resolution
floor. `LoopConfig` gains a `sampling_rate` field for this; the gains genuinely
are rate-independent, only the two IIR filters and the `curvefilter` window move.
`Iterm` climbs at 0.0995 duty/s over 3:20-6:40, so `e_ss = (dI/dt)/Ki =
1.42 degC` and six seconds of lead against a ~0.22 degC/s background cancels
~1.3 of it — which is the +0.4 degC that is left, arithmetic rather than luck.

**Both Artisan settings changes landed and are visible in the file.** Sampling is
0.511 s, and the largest `SV` step reads `232.1 232.1 232.1 231.3 0.0` — one
sample wide. Roast 48's same step reads `190 190 190 126.67 63.33 0.0`, the
destructive equal-run repair. Drop Spikes is off.

**Step 7 came for free, and in a stronger form than specified.** The fan sat at
**64 for the entire recording** — two `Air` events, both 64, one at -1:48 and one
at CHARGE — through preheat, the charge bump and the whole roast body. So there
is no air schedule anywhere in this trace, and the tracking result above is
attributable to the loop with nothing to subtract. Combined with roast 48's
`kf = 0`, the air schedule has now failed to earn its disturbance twice.

#### The charge was ~33 degC warmer than roasts 43-46

The dip is the wrong sign, and the reason is the beans. The plant's transport
delay means nothing the heater does reaches BT before ~13.5 s, so the BT fall
over `0 .. theta` is charge mixing alone — the control-independent measurement
state-history.md § Charge temperature used to conclude roasts 43-46 were frozen.
`tools/analysis/charge_state.py` now runs it as a tool and adds the correction
roast 49 forced: **the air already in flight counts**, since inlet air from
`t in [-theta, 0]` arrives inside the mixing window, and roast 49's preheat sat
at 168.6 degC against roasts 43-46's 140-150. That is worth +0.39 degC/100 g and
it is applied.

```
roast  mass   BT@0  BT@13.5   drop   /100g    air    corr  inlet_pre
   43   400  127.8     67.5  60.25   15.06  +0.08   15.14      149.9
   44   400  128.3     70.1  58.20   14.55  +0.02   14.57      146.2
   45   345  128.7     79.8  48.85   14.16  -0.03   14.13      143.7
   46   400  129.0     68.1  60.90   15.23  -0.07   15.15      140.6
   49   400  131.1     85.4  45.70   11.43  +0.39   11.81      168.6
```

Roast 49 reads **22% below** the 400 g frozen group, which holds to 2.2%. Under
`proxy = k*(BT_charge - T_bean)` that is **T_bean ≈ +15 degC (band +13 .. +18)**
if 43/44/46 were at -18. The **difference** is the robust part and is
anchor-free: whatever the freezer actually held, roast 49's charge was
**33-35 degC warmer**, because the anchor cancels out of the difference. Roast 48,
the sacrificial stock, reads +12.8 on the same estimator — consistent, though its
low CHARGE_BT of 84.3 gives it a shorter lever and a correspondingly softer
number.

Two cautions the tool encodes. **The proxy is not linear in mass** — the mixing
settles at `dBT = m*c*(BT_c - T_b)/(C_chamber + m*c)`, so dividing by mass only
removes the leading term, and roast 45 at 345 g reads ~7% low against the 400 g
runs for that reason alone; compare like masses. And **the preheat trajectory is
part of the measurement**, so a charge-temperature experiment has to hold it
fixed, not merely hit the same CHARGE_BT.

**What this does to the step-6 verdict: nothing, and it is worth being explicit
why.** The tracking window is 3:00 onward, long after the integrator has
re-converged, and `svLookahead`'s effect on `e_ss` has no charge term in it. What
is confounded is only the dip comparison — rows 4 and 5 of the table are **not**
a one-variable comparison against roast 46 and should not be read as one.

**And it hands the project the warm arm of an experiment nobody ran.** The
operator's proposed ambient-vs-freezer pair now needs one deliberate frozen
batch to close, with `greens_temp` recorded on both — which it was not here, for
the fourth roast running.

<a id="deadtime-vs-lag"></a>

### Deadtime versus lag — settled at the desk from roasts 46 and 48 (2026-09-06)

state-plan.md § What roasts 47-49 jointly say, item 4. Tool:
`tools/analysis/deadtime_vs_lag.py`; `plantfit.py` gains a shared `lag1`,
`tau2` on `fit_disturbance` and `replay`, `block_bootstrap_2lag` and `neff`;
`margins.py` gains `tau2` on `loop_tf`, `margins` and `closed_loop_modes`. No
roast was needed and none is proposed. Every number below reproduces from
`deadtime_vs_lag.py` with no arguments; existing drivers are unaffected
(`roast46_refit.py` and `roast48_plant.py` reproduce their published figures
exactly).

**The question.** `plant_roast46.json` carries `theta = 13.5 s` of pure
transport delay and is the authoring source for `tools/merge_inlet_base.py`.
§ Roast 48 found that `fit_integral_2lag` fits the same windows with `theta`
collapsing to ~0 and a 10-25 s first lag in its place, at about a third less
residual, and left it there. It matters twice: a lag contributes
`-arctan(w*tau2)`, bounded at 90 deg, where a delay contributes `-w*theta`,
unbounded — so the phase-margin arithmetic is not the same; and step 9's base
schedule is `ff(t) = bg(t+theta) + (dbg/dt - loss)/a`, whose lead term is built
directly on whichever structure is right.

#### Roast 49 cannot contribute, and this is the check that says so

Roast 49 is closed-loop with one large SV step at 1:30, so it had to be tested
before being trusted. It fails.

| | roast 46 | roast 48 | roast 49 |
|---|---|---|---|
| independent inlet motion (order-5 poly removed) | 5.50 degC | **23.68** | 5.08 |
| single-lag ridge depth `resid(0)/resid(min)` | 3.95 | 2.47 | 2.52 |
| two-lag `a`, tau2 grid 0-60 s | 0.00598 | 0.00836 | 0.00857 |
| two-lag `a`, tau2 grid 0-120 s (roast48_plant.py's own) | 0.00652 | 0.00845 | **-0.06318** at tau2 100 |

On the grid the existing driver uses, roast 49's two-lag fit runs away to the
edge and returns a **negative gain**, which is not a plant; it only looks sane
because a 60 s grid truncates the runaway. Its sub-window `a` then spans a factor
of three (0.0076 to 0.0250) and on 200-423 s its delay-scan ridge depth is 1.04,
meaning no delay at all fits as well as the best one. **One step inside a
controller that is correcting for it is not excitation.** Roast 49 is excluded
from every conclusion below.

#### The residual does not settle it, and it is worth knowing why

| roast | window | resid 1 lag | resid 2 lag | ratio | n | n_eff | F | p |
|---|---|---|---|---|---|---|---|---|
| 48 | 45-430 | 0.4794 | 0.3387 | 0.706 | 386 | 6 | 1.0 | 0.50 |
| 48 | 165-450 | 0.3090 | 0.1880 | 0.608 | 286 | 9 | 2.2 | 0.33 |
| 48 | 300-750 | 0.4362 | 0.1886 | 0.432 | 451 | 5 | 4.3 | 0.28 |
| 48 | 450-750 | 0.2559 | 0.1405 | 0.549 | 301 | 6 | 2.3 | 0.37 |
| 46 | 45-429 | 0.1155 | 0.1050 | 0.909 | 385 | 120 | 23.5 | 0.0000 |
| 46 | 60-429 | 0.1053 | 0.1043 | 0.990 | 370 | 141 | 2.6 | 0.11 |

Roast 48's residuals are correlated at rho > 0.99, so the AR(1) effective sample
size of a 300-450 sample window is **5 to 9**. With one extra parameter and a
6-column design matrix there is nothing left to test against: **no residual
reduction of any size clears an honest F-test on roast 48.** The residual there
is structured model error, not noise, and a test that assumes independent noise
is the wrong instrument. Roast 46's residuals are far less correlated (n_eff
120-141) so the test has power there — and it splits, 45-429 clearing easily at
a 9% improvement and 60-429 not clearing at 1%. That split is itself the answer:
once the last of the charge recovery leaves roast 46's window, what is left is a
smooth ramp, and a smooth ramp cannot tell a lag from a delay.

#### What settles it is identifiability, and the two roasts differ for a reason

The residual surface over `(theta, tau2)`, as the 1%- and 5%-of-minimum contours:

| window | min | 1% band theta | 1% band tau2 | 1% band sum | pure deadtime | pure lag |
|---|---|---|---|---|---|---|
| r48 45-430 | (0.0, 12.0) | 0.0..0.0 | 12.0..13.0 | 12.0..13.0 | **1.416x** | 1.000x |
| r48 165-450 | (0.0, 10.0) | 0.0..0.0 | 10.0..10.5 | 10.0..10.5 | **1.648x** | 1.000x |
| r48 300-750 | (0.0, 13.5) | 0.0..0.0 | 13.5..13.5 | 13.5..13.5 | **2.313x** | 1.000x |
| r46 45-429 | (5.0, 8.0) | 3.5..6.5 | 6.5..9.5 | 12.5..13.5 | 1.100x | 1.068x |
| r46 60-429 | (9.5, 4.5) | 7.0..13.5 | 0.0..7.0 | 13.5..14.5 | 1.010x | 1.065x |

**On roast 48 the split is identified and it is all lag.** The 1% contour is one
or two grid cells, `theta` sits hard on 0, and forcing pure deadtime costs 42 to
131% more residual.

**On roast 46 it is a ridge along `theta + tau2 = const`.** The *sum* is pinned to
a 1-2 s band at 13-14 s while `theta` and `tau2` each range over 6-13 s, pure
deadtime and pure lag both land within 1-10% of the mixed optimum, and *which of
the two is better flips between windows*.

That is not a contradiction, and the reason is physical. Roast 48 steps the inlet
by -95/+65/-65/+40 degC with the PID off, and **a step is the only excitation
that separates the two**: a delay holds the output flat and then moves it, a lag
moves it immediately and slowly. Roast 46's excitation is the smooth closed-loop
charge recovery, whose content sits far below the corner where `exp(-theta s)`
and `1/(1 + theta s)` part company — below it they are the same function to first
order, which is exactly why 13.5 s of "deadtime" fitted so well.

Moving-block bootstrap, 200 resamples, 60 s blocks:

| roast | window | theta 95% | tau2 95% | **sum 95%** | a 95% |
|---|---|---|---|---|---|
| 48 | 165-450 | 0.0..2.0 | 7.0..11.0 | **9.0..11.0** | 0.00679..0.00780 |
| 48 | 300-750 | 0.0..2.0 | 11.0..15.0 | **13.0..15.0** | 0.00934..0.01021 |
| 46 | 45-429 | 2.0..9.0 | 5.0..11.0 | **12.0..14.0** | 0.00513..0.00688 |

Roast 48 bounds `theta` at 0-2 s — the 8.5 s of its own single-lag fit is outside
the interval. Roast 46 bounds it at 2-9 s, so **roast 46's own data also reject
13.5 s of pure transport**; they simply cannot say how much of the 13 s is delay.

#### The answer, and the one number to carry forward

**What is identified everywhere is the sum.** `theta + tau2` bootstraps to 9-11,
13-15 and 12-14 s on the three well-excited windows, and the single-lag `theta`
the deadtime fits report — 8.5 s on roast 48, 13.5 s on roast 46 — **is that
sum**. So the 13.5 s in `plant_roast46.json` was never 13.5 s of transport. It is
13.5 s of *total apparent lag* with the split unresolved, and the roaster's real
transport delay is small — 0-2 s where roast 48 can see it.

**And it fixes `theta`'s non-stationarity, which was a structural artefact.**
Across roast 48's excited sub-windows the single-lag `theta` spreads 7.8-14.5 s;
under two lags it sits at 0.0-1.0 s on every one of them. What does *not* settle
down is `a`, and it settles down **less**: 0.0074-0.0142 under two lags against
0.0062-0.0085 under one, with `tau2` tracking it 9-26 s, because a late window can
now buy a slow response with a long lag and a large gain instead of a small gain.
**Better structure, not a finished plant** — which is the same verdict § Roast 48
reached, for a sharper reason.

#### The tuning does not move, and the ring says which end of the ridge we are on

Phase margin at Kp 3.0, with the second lag added to `margins.loop_tf`:

| card | `a` | theta | tau2 | Ki 0.05 | Ki 0.07 | Ki 0.10 | Ki 0.15 |
|---|---|---|---|---|---|---|---|
| roast 46, 1 lag | 0.00490 | 13.5 | — | 43.5 | **33.7** | 22.6 | 9.2 |
| roast 46, 2 lag | 0.00598 | 5.0 | 8.0 | 45.1 | **35.6** | 24.5 | 11.1 |
| roast 48, 1 lag | 0.00789 | 8.5 | — | 52.8 | **44.6** | 34.3 | 21.5 |
| roast 48, 2 lag | 0.00836 | 1.0 | 9.0 | 51.0 | **42.6** | 32.4 | 19.6 |

**The structure barely moves the margin at all** — under a degree and a half on
roast 46, two on roast 48. The strongest form of that is the ridge walk: hold
`theta`, refit `tau2` and `a`, and sweep the whole ridge from all-delay to
all-lag. The phase margin at the tuning in force moves **32.8 to 37.7 deg** over
a span across which the residual moves only 11%. Five degrees is inside the model
error these cards already carry. **`pidKi` 0.07 stands, and nothing here argues
for changing it.**

What *does* move along the ridge is the closed-loop period, 156 to 196 s, so the
one closed-loop behaviour on record is informative where the open-loop residual
is not. Roast 45 rang at **177 s** at Ki 0.10 (§ Correction: extrema at 2:12 /
3:26 / 5:10 / 6:22, so two full cycles at 178 and 176 s). Against the least-damped
closed-loop mode — *not* the crossover period, which is what the earlier
comparisons quoted; they are different quantities and the gap is 4-16 s:

| card | PM | crossover T | **closed-loop T** | zeta | vs 177 s |
|---|---|---|---|---|---|
| roast 46, 1 lag | 22.6 | 190 | 194 | 0.272 | +9% |
| roast 46, 2 lag | 24.5 | 171 | **173** | 0.291 | **-2%** |
| roast 48, 1 lag | 34.3 | 136 | 152 | 0.491 | -14% |
| roast 48, 2 lag | 32.4 | 139 | 143 | 0.399 | -19% |

The ridge walk resolves it further: 177 s picks out `theta` 6-7 / `tau2` 6.5-7,
which is within 1% of roast 46's own residual minimum at `theta` 5. **The
open-loop fit and the closed-loop measurement agree, and what the ring disfavours
is either extreme** — the all-delay end predicts 196 s and the all-lag end 156 s.
Treat that as corroboration, not a third significant figure: it is one ring, in
one roast, at a Ki no longer in use, and the Padé approximation of the delay is
itself doing work in the comparison. **The ranking § Roast 48 drew survives and
improves: the card fitted to a real roast still predicts the real roast.**

#### What it does to `plant_roast46.json` and to the `bg(t+theta)` lead: nothing

This was the part expected to break, and it does not. Under two lags the plant
inversion is

```
X_req(t) = bg(t) + (dbg/dt - loss)/a          the lagged inlet the bed needs
ff(t)    = X_req(t + theta) + tau2 * dX_req/dt(t + theta)
```

— invert the lag as well as the gain, then apply whatever delay is left. Built
that way from roast 46's own two-lag card (`a` 0.00598, `theta` 5.0, `tau2` 8.0,
loss cubic refitted under the matching structure) against `profile_003`, with
`merge_inlet_base.py`'s `--tail ror` blend and `--ramp-start 90`:

| t (s) | bg | 1 lag | 2 lag | diff |
|---|---|---|---|---|
| 90 | 101.9 | 200.9 | 197.7 | **-3.25** |
| 150 | 134.0 | 202.1 | 202.8 | +0.75 |
| 210 | 155.0 | 215.6 | 216.3 | +0.71 |
| 270 | 171.7 | 226.2 | 226.5 | +0.28 |
| 330 | 185.1 | 234.5 | 234.4 | -0.04 |
| 390 | 196.0 | 244.3 | 244.6 | +0.34 |
| 425 | 201.4 | 255.9 | 254.4 | -1.51 |

**Difference over the ramp: mean -0.04, rms 0.84, worst 3.25 degC**, on a base
running 200-256 degC — against the ~0.5 degC floor whole-degree event
quantisation already puts on the replay, and the 0.87 degC replay error
`merge_inlet_base.py` reports on this profile today. The worst case is at the
ramp start, where the `--dip` rule joins on. (The driver imports the tool's own
`decay_smooth`, so the 1-lag column reproduces `merge_inlet_base.py --dry-run`
exactly, raw `ff(0) = -432 degC` included — against -326 under two lags.)

**The reason is arithmetic, not luck.** On a ramp of slope `r`, advancing the
background by `theta` adds `theta*r` and the lag inversion adds `tau2*r`; roast
46 puts `theta + tau2 = 13 s` against the single-lag 13.5. **The two
constructions are the same lead written two ways**, and the 22% larger `a` and
the loss curve refitted against it cancel the rest. Raw unclamped `ff` at CHARGE
is -432 degC (1 lag) against -326 (2 lag) — both absurd, for the same reason —
so the `--dip` rule is unaffected in kind.

**So `plant_roast46.json` stands unchanged and `merge_inlet_base.py` needs no
rewrite.** What changes is the *claim attached to the number*: `theta` is 13.5 s
of total apparent lag, and the tool is using it as a first-order lead
approximation to `tau2*d/dt`, which is valid on a smooth ramp. Two caveats for
whoever does eventually rewrite it:

- the two-lag lead carries `tau2/a * d²bg/dt²`, so a rough or kinked background
  costs far more than it does today. `profile_003` is authored and smooth; a
  background merged from a recorded roast is not, and the tail blend would have
  to be C1 rather than merely C0.
- `a`, `theta`, `tau2` and the loss curve are **one set**. `a` is 22% larger under
  two lags and the loss cubic refitted against it differs (loss(60) +0.193 against
  +0.272 degC/s); the numbers are not interchangeable between structures. That is
  why this pass emits no card and changes no authoring tool.

#### `charge_state.py` is unaffected, and here is the number

The charge-state proxy reads the BT fall over `0 .. theta` as charge mixing alone
on the grounds that nothing the heater does reaches BT before then. Under two
lags that is not a hard cutoff. Over `0 .. 13.5 s`, with each structure's own
`a`:

| roast | BT fall | 1 lag | 2 lag | diff | diff/100 g |
|---|---|---|---|---|---|
| 43 | 60.25 | +3.73 | +4.67 | +0.94 | +0.236 |
| 44 | 58.20 | +3.32 | +4.28 | +0.97 | +0.242 |
| 46 | 60.90 | +2.83 | +3.63 | +0.80 | +0.201 |
| 49 | 45.70 | +4.22 | +4.98 | +0.76 | +0.189 |

The modelled heater contribution is 3-5 degC of a 46-61 degC fall under *either*
structure, and the difference between structures is **0.19-0.24 degC/100 g with a
spread of 0.05** — against the 3.3 degC/100 g gap the proxy is being used to
measure. It is common-mode and **`charge_state.py` needs no change**. What is now
known to be loose is the *shape* of its air-in-flight correction:
`a*(inlet_pre - INLET_REF)*theta` is a rectangular window where the two-lag
reading gives an exponential tail. A line in that tool's docstring, not a
rewrite.

#### What would resolve what is left

The split is settled for roast 48's operating range and *inferred* for roast 46's
by the sum plus one ring. What is genuinely unresolved is **`a`**, which is
non-stationary under both structures and more so under two lags. Nothing in the
data in hand fixes that, and it is not a deadtime-versus-lag question. The
excitation that would settle it is a **step of the same size taken at two or
three points along one roast's own trajectory** — roast 48's steps are all large
and all at different BT, so gain and lag are confounded with where in the roast
they were taken. That is a characterisation-run design change, not a new run to
schedule now: `kf = 0` closed the standing reason for those runs and this does
not reopen it.

### The charge-thermal test (2026-09-06, 20:27) — the charge-thermal test, and what a still-air probe cannot see

Not a roast. Two cycles of *preheat the empty chamber to BT 130, cut the heat and
the fan together with the cooldown guard disabled, tip 400 g in, and watch BT for
150 s* — arm 1 at room temperature, arm 2 straight out of the freezer. The
operator's own numbers: the freezer is a real **−18 degC** and the room was
**about 29 degC**; both charges were **400 g**. `greens_temp` is `0.0` for the
fifth run running, which is why those had to be supplied by hand.

The two preheat end-states are as close to identical as this machine gets — BT
129.8/129.7, inlet 140.4/140.8, heat 44-46%/43-46% — which is what makes the pair
worth anything. Tools: `tools/analysis/charge_thermal.py` (the fit and the
identifiability report) and `tools/analysis/charge_dip.py` (the predictor built
on top of it).

| | arm 1, warm | arm 2, frozen |
|---|---|---|
| cut | 5:37.6 | 11:51.6 |
| BT minimum | **45.6 degC at +150 s** | **19.5 degC at +145 s** |
| mixing burst | none | **fan 64 over +135.4 .. +144.4 s** |

**The chamber was empty for both preheats**, so each cycle is self-contained: the
reheat from 65 to 129 degC in 20 s at inlet ~260 is three times faster than
`plant_roast46.json` allows with 400 g in the chamber, so arm 1's beans came out
before arm 2 went in.

#### The headline is a negative result, and it is the answer to the question the run asked

**The still-air decay does not measure the charge temperature.** Left free, the
joint fit puts the *room-temperature* arm at **−2.2 degC** and the freezer arm at
its **−45 degC bound**, and buys a **16 kJ/K** chamber to pay for it. That fit is
*better* than the one with the temperatures held at their measured values —
rms 1.64 against 2.21 — on residuals whose effective sample size
(`plantfit.neff`) is **0.3 to 1.1 per arm**. So the residual gap is not evidence
of anything, and what settles it is identifiability: `T_b0` trades against
`beta`, `rho` and `tau_p` freely enough that the estimator will spend 30 degC of
charge temperature to buy a fraction of a degree of fit.

**The cause is structural and the operator named it** (2026-09-06): the preheated
chamber holds a lot of heat and the expansion zone the BT probe sits in is
narrow. In still air the probe is therefore an instrument pointed at the
*chamber*, not at the beans — the fit puts **`beta` 0.34** of its coupling onto
the walls with a **36 s** time constant, and those two are the only parameters
stable across every configuration tried.

**`C_chamber` is not identified either**, which is what the run was designed to
calibrate. `rho = C_w/C_bed` walks to whatever bound it is given — 29.7 against a
bound of 30 — *even with the charge temperatures held at their measured values*,
and `c_b` goes to a bound with it. So the charge-thermal test does **not** supply the
`C_chamber` in `charge_state.py`'s mixing model, and nothing downstream should
pretend it does.

#### The nine-second burst is the measurement that does work

Arm 2 got a fan-64 burst at +135 s and arm 1 did not. Across it **BT falls
23.5 → 19.5 degC in 9 s** and flattens one second after the fan stops. Two things
follow:

- **3.9 degC of still-air bias**, removed by nine seconds of circulation. That is
  the probe's wall coupling being switched off, measured rather than fitted.
- **The trough is the bean bed, near enough directly.** The air being drawn in is
  the room at 29 degC and BT went to 19.5 — *below the inflow*. Nothing in that
  chamber but the bean bed is colder than the air entering it.

So the logistical answer is: **charge, wait, then a short burst, and read the
trough.** The wait on its own does not work, and the reason it does not is the
narrow expansion zone. It also means the two arms are **not** a like-for-like
pair as recorded — only one of them has a bed measurement, which is a large part
of why the joint fit is under-determined. **The cheap follow-up is to repeat the
warm arm with a burst**; it costs one preheat and no beans that are not reusable.

#### Three more things the recording measures outright, with no model in the path

**The plenum decouples from the bed with no flow.** Inlet in the frozen arm runs
**4-5 degC warmer** than the warm arm at +60/+90/+120 s (103.2/99.0/95.6 against
98.2/94.0/91.0) *despite* a 47 degC colder charge. With the fan off, the bean
charge never reaches the inlet RTD at all.

**The machine's own store decays with a ~510-557 s time constant**, fitted to the
Inlet channel from +25 s (before that it is the RTD's own dynamics, not the
reservoir). `charge_thermal.py` uses that as a measured boundary condition rather
than a fitted node — a three-node model with no source matches 0-100 s and then
fails twice over, flattening where the data keeps falling and unable to rebound
at all (+4.7 and +6.1 degC at the minima, −5.7 and −8.7 at +210 s).

**The frozen arm's plenum artefact is why the reservoir is fitted rather than
read raw**: the burst takes the Inlet RTD 94 → 57 degC and back, which is the
sensor and not the store, and reading the channel raw shortens the fitted time
constant on that arm alone from 557 s to 364 s.

#### Bypassing the cooldown guard: benign here, and the limit is worth stating

- Inlet falls **140 → 97 degC in about 4 s** as forced convection is lost, then
  **soaks back to only 109-111 degC** at +12-18 s — **30 degC below the running
  setpoint** — before decaying. There is no excursion anywhere in the trace.
- **The interlock held.** Heat was 0 from 1.5 s after the fan cut in arm 1 and
  never came on at all in arm 2.
- **One 0.5 s sample of `HT 50` at 5:38.6**, and it is not a firmware fault. The
  operator sent inlet-off (`SV` 0), Artisan's PID re-sent `INLET 140.1` on its
  next tick, the inner loop re-engaged on feedforward while the fan was still at
  60, and `interlockCap()` zeroed it the moment the fan reached 0. **Procedure:
  kill the outer PID before the inlet**, which is what arm 2 did — its `SV` stays
  0 for the whole decay. About 375 J, thermally nothing.
- **The `COOL` guard is correctly sized for exactly this soak** and would not
  have released for over four minutes (`COOL_FAN_OFF_C` is 70 degC and the inlet
  is still at 82 degC at +220 s), which is why the test had to disable it. That
  is not an argument for leaving it disabled.
- **The limit:** this was a cut from a *preheat* state — 140 degC inlet, 45%
  duty — and the element itself is unmeasured; the Inlet RTD is a downstream
  proxy. It says nothing about a cut from mid-roast at 250 degC inlet and high
  duty.

#### What the dip predictor took from it, and what it took from the roasts instead

`charge_dip.py` puts a mixing term in front of the existing plant card:

```
mixing:  dBT/dt = -(dT_mix / tau_mix) * exp(-t / tau_mix)
plant:   dBT/dt =  a*(Inlet(t - theta) - BT) + loss(t)
dT_mix = phi*(BT_c - T_bean) + fusion
```

**Mixing is a finite quantity of heat, not a setpoint, and getting that wrong is
worth 40 degC.** Written the obvious way — `dBT/dt = -(BT - BT_mix)/tau` — the
charge becomes a permanent attractor that goes on fighting the heater for the
whole roast: the model flatlines near 62 degC while roasts 43 and 46 turn at
58 degC at 23 s and are back through 100 degC by 60 s. As a decaying *rate* it
integrates to exactly `dT_mix` and then stops, and the plant takes the roast
back — turning point **23-25 s** against a measured 22-23.5, dip depth within
about 1.5 degC.

**`phi` is fitted to the roasts, not to the charge-thermal test**: 0-40 s of measured BT on
roasts 43/44/46 at the assumed −18 degC gives **`phi`(400 g) = 0.658,
`tau_mix` = 12.2 s, rms 3.08 degC**, hence `C_chamber` 353 J/K and a capacity
ratio of 0.52. Held out, roast 48 reads rms 6.19 and roast 49 rms 3.11 — but
their charge temperatures came from the same proxy and the same −18 degC
assumption, so they test the *shape* and not the physics.

**`charge_state.py`'s `k` is not `phi`, and this cost a wrong answer once.**
`4k = 0.409` is the drop measured at `+theta`; it already folds in how far the
mix has got by 13.5 s *and* the heat the plant put back over the same window.
Equating it with the asymptotic mixing fraction under-predicts every charge drop
by **7-10 degC**. No change is needed in `charge_state.py` — the error was in
reading its constant as a physical fraction.

#### The one disagreement in the set: the fusion enthalpy

A frozen 400 g charge at 10.5% moisture carries up to **14 kJ** of fusion
enthalpy on top of about 26 kJ of sensible heat, and how much of that water is
freezable at all is a real question — bound water in a cellular matrix does not
all freeze.

- **The charge-thermal test says some is needed and cannot say how much.** `r_fus = 0` costs
  **20%** of residual, so the frozen arm does want extra cold-side thermal mass;
  but 5 to 25 degC-equivalent all cost **under 3%**, and the point estimate comes
  out **above 35 J/g**, which is *all* the fusion enthalpy such a charge has.
- **The roasts say none.** On a frozen-only calibration group `phi` and `h_fus`
  are the same parameter — the calibration rms is **3.08 at every value from 0 to
  35 J/g**, exactly absorbed. The only lever is the held-out warm pair, and it
  gets monotonically worse as `h_fus` rises: roast 48 from **6.19 to 10.22**,
  roast 49 from **3.11 to 9.45**.

`charge_dip.py` defaults to **0** and follows the roasts, with `--fusion`
printing the table. The disagreement is real, unresolved, and cannot be closed by
either dataset in hand.

#### What is still resting on one assumption

**Nothing in this project has yet measured a charge temperature under flow.** The
whole chain — `charge_state.py`'s `k`, roast 48's +12.8, roast 49's +15.5, and
now `charge_dip.py`'s `phi` — rests on roasts 43/44/46 having been at −18 degC.
The charge-thermal test could have broken that dependency and does not, because it has no flow.
The fix has been in the runbook since 2026-09-05 and costs nothing: **record
`greens_temp`.**

### Roasts 50 and 51 (2026-09-07) — the charge-temperature pair, with `greens_temp` measured

**The first two roasts in this project whose charge temperature is a measurement
rather than an inference.** `greens_temp` **+25.0** (roast 50) and **−12.0** degC
(roast 51), 400 g in / 349 and 351 g out, moisture 10.9%, same lot, same session,
`airRoaster_cascadePID_chargetemp.aset` + `profile_003`, no intervention.

**Note the batch-number collision**: `airRoaster_50.alog` is now roast 50, the
*warm* arm. The 2026-09-06 no-flow bench run that used to hold that name is
§ The charge-thermal test, and its raw log was **overwritten with no backup** —
`tools/analysis/charge_thermal.json` is the only surviving record and
`charge_thermal.py` now refuses to run rather than analyse the wrong file.

#### The preheat protocol works, and fan 58 is the right level

Pre-charge Temp_Drive **9.85** and **9.02**, BT 129.7 and 131.0 — settled, off the
floor, and matching the historical state. The dashboard log measures why, at a
constant inlet 140.4 in an empty chamber **at equilibrium**:

| fan | BT | Temp_Drive | heat |
|---|---|---|---|
| 64 | 136.9 | 3.50 | 49.4% |
| 60 | 133.4 | 7.02 | 45.3% |
| 58 | **130.2** | **10.25** | 42.6% |

−0.88 degC of Temp_Drive per fan unit over 60-64, steepening to **−1.62** over
58-60. So **fan 58 puts the equilibrium exactly on the background's CHARGE_BT**,
and its Temp_Drive of 10.25 is the same 10.5-11.4 roasts 46 and the charge-thermal
test read — *those were transients at fan 60 caught on the way down*, and fan 58
reaches the same state as a fixed point. That is what makes it repeatable.

#### `k` is measured, and the proxy's linear form survives a 37 degC span

    k = proxy_corr / (BT_charge - T_bean)      degC per 100 g per degC

| roast | T_bean | BT@0 | BT@+13.5 s | drop | proxy/100 g | k |
|---|---|---|---|---|---|---|
| 50 | +25.0 | 129.7 | 85.4 | 44.30 | 11.08 | **0.10578** |
| 51 | −12.0 | 131.0 | 70.7 | 60.30 | 15.07 | **0.10542** |

**0.34% apart across a 37 degC span.** That is the strongest validation the
charge proxy has had, and it was previously calibrated on an *assumption*.
The measured `k` is **3.4% above** `charge_state.py`'s 0.10217, so the whole
historical set re-reads warmer:

| roast | T_bean (old, assumed −18) | T_bean (measured k) |
|---|---|---|
| 43 | −20.4 | **−15.6** |
| 44 | −14.3 | **−9.7** |
| 46 | −19.3 | **−14.5** |
| 48 | +12.9 | **+15.2** |
| 49 | +15.5 | **+19.3** |

So the "frozen" group was never at −18: it arrives at about **−10 to −16**, which
is exactly where roast 51's measured −12.0 sits. Beans warm on the way from the
freezer to the chamber, and the freezer temperature was never the charge
temperature.

#### The fusion enthalpy question is closed, against the charge-thermal test

A frozen charge crosses the melt band and a warm one does not, so any real fusion
enthalpy inflates the frozen roast's apparent `k`. At `h_fus` of 5 / 10 / 20 /
35 J/g it would read **2.2 / 4.3 / 8.6 / 15.1%** high. **Measured, it reads 0.34%
*low*.** So `h_fus` is under ~1 J/g. The charge-thermal test's still-air fit
wanted 7-35 J/g and could not size it; the roasts settle it, and
`charge_dip.py`'s default of zero was right.

#### The early stage: the loop has authority to spare and spends it on the wrong target

The operator's reading — *"plenty of control effort in the early stage, it just
overacts"* — is correct, and the traces say why.

| t | bg | r50 BT / err / SV / HT | r51 BT / err / SV / HT |
|---|---|---|---|
| 5 | 110.7 | 108.7 / −2.0 / 194 / 100 | 104.9 / −5.8 / 245 / 100 |
| 10 | 96.8 | 91.9 / −4.9 / 214 / 86 | 80.3 / −16.5 / **300** / 100 |
| 20 | 77.9 | 80.6 / +2.7 / 181 / 52 | 63.9 / −14.0 / 292 / 100 |
| 40 | 67.7 | 84.9 / **+17.2** / **140** / 47 | 79.3 / +11.6 / 166 / 43 |
| 50 | 71.9 | 89.4 / **+17.5** / **140** / 47 | 88.1 / **+16.2** / **140** / 44 |
| 90 | 102.4 | 106.3 / +3.9 / 158 / 54 | 107.0 / +4.6 / 154 / 48 |
| 180 | 145.5 | 145.9 / +0.4 / 192 / 60 | 145.9 / +0.4 / 193 / 62 |

Roast 51 railed SV to its **300 ceiling for 9 s** with heat at **100% for
24.5 s**; roast 50 reached SV 214 and 100% for 5 s. Then both sat on the **140
floor** — 36.5 s and 22.5 s — while BT ran **+17 degC above the background**.
There is no shortage of authority in either direction; the loop hits both rails.

**The overshoot is charge-state-independent**, which is the diagnostic. From 50 s
on the two roasts are within 1.5 degC of *each other* despite a 37 degC
difference in the beans (+17.5/+16.2 at 50 s, +14.6/+15.0 at 60, +3.9/+4.6 at 90,
+2.0/+2.1 at 120). So the hump is not the charge. It is **the background's dip
timing**: `profile_003` puts TP at **67.4 degC at 37 s**, and the real turning
point is at **21-22 s** in both roasts. The loop spends 0-20 s fighting a target
that is still falling while the bed has already turned, and — with nothing the
heater does reaching BT before ~13.5 s — its correction lands at 18-28 s, exactly
when it is no longer wanted. By 25 s it is on its floor and can do nothing but
watch.

**`charge_dip.py` predicts the turning point to 0-3 s**: TP 84.0 at 22.0 s
against a measured 80.2 at 22.0 (roast 50), and 64.9 at 24.0 against 63.8 at 21.0
(roast 51), rms 4.2-4.5 degC over 0-60 s. The model is right and the background is
15-16 s wrong. Nothing about the tuning needs to change to fix this.

#### And the tuning after the dip is the best on record

Time-to-BT against `profile_003`: **−0.4 / +1.7 / −2.0 s** (roast 50) and
**−0.4 / +2.2 / −2.0 s** (roast 51) at BT 150 / 180 / 196.5, against roast 49's
−0.9 / +2.2 / +2.0. The two roasts agree with **each other to 0.5 s at every
level**, and the error is +1.4 degC at 120-180 s falling to +0.4 by 180 s. A
37 degC difference in charge temperature leaves no trace after DRY END.
`pidKp` 3.0 / `pidKi` 0.07 / the lookahead switch all stand.

### Roast 52 (2026-09-07, 12:40) — the first generated background, and the pre-CHARGE frozen target

380 g in / 334.7 out, `greens_temp` **−12.0**, moisture 10.9%, background
**`profile_380g_m12C.alog`** — the first background whose dip was computed rather
than authored. Preheat fan 58 (Temp_Drive 11.9 at −10 s, BT 130.1, inlet 142.1),
fan 64 at CHARGE, 60 at 3:20 (hand-pressed and late — the operator's own note,
and the reason the step is now an alarm). DRYe 186, FCs 409, DROP 434.

#### The generated dip worked

| | worst error over 0-18 s |
|---|---|
| roast 51 on `profile_003` | **18.2** |
| roast 52 on the generated background | **10.2** at 4 s, and −1.3 .. +2.1 over 10-25 s |

TP **65.6 degC at 22 s** against the background's 63.4 at 29 s. So the dip model
is doing its job and the remaining error in that window is a **model detail, not
a strategy failure**: the generated curve falls ~10 degC too fast over 2-6 s
(background 105.8 at 4 s against a measured 116.0) and has closed by 10 s.
`charge_dip.dip()` starts its mixing exponential at `t = 0` with no pour ramp —
`charge_thermal.py` has one (`w_c`) and `charge_dip.py` does not. **Two seconds
of pour ramp is the fix**, and it is the only outstanding defect in the dip model.

#### And the loop still overacted, for a reason that is in Artisan's source

The operator's question — *why does the control effort skyrocket while BT is
tracking at or above the background?* — has a definite answer, and it is not
tuning. Detail and the fix are in state-plan.md § The charge gate; the roast's own
numbers:

```
+3.0s  T_inlet 140      +3.5s  T_inlet 224      +16.5s  T_inlet 275
```

SV max **275**, heat **100% for 22.5 s**, then **37.5 s on the 140 floor**, and BT
peaked at **+20.1 degC at 58 s**. `pid_control.py:1687` returns the background's
*CHARGE temperature* — one constant — until `timeindex[0]` is set, and autoCHARGE
needs ~5 samples of BT-break evidence, so for ~3.5 s the target was pinned at
130.2 while BT was already through 116. That **inverts the sign of the error**:
live tracking wanted `105.8 − 116.0 = −10.2` and would have cut the heat.

**The PID port settles that it is the target and not the loop.** Driven by roast
52's measured BT and its background it reproduces the commanded SV to **rms 1.84
over 120-240 s**, and over 0-30 s it says SV should have been **145-181, never
above 181**. The entire discrepancy lives in the unmarked-CHARGE window.

#### What that leaves

Everything after the first minute was unremarkable: error +4.0 at 120 s, +1.7 at
180 s, SV 188-194, heat 58-60%. The roast is a **clean separation of concerns** —
the background fixed the target, and what remained was one identifiable Artisan
mechanism rather than a tuning question. Both are now closed in the config;
roast 53 is the test.

### Roast 53 (2026-09-07, 13:15) — the gate never existed, and the kick is the lookahead

400 g of the −12.0 degC lot on `airRoaster_cascadePID_chargetemp.aset` against
`profile_400g_m12C.alog`, the first run of the charge gate and the first with the
fan step on an alarm. **Three of the four checks still fail**, all four improved,
and the reason is two separate defects in the config — neither of them the
tuning, and neither of them the operator.

| check | roast 51 | roast 52 | **roast 53** | pass |
|---|---|---|---|---|
| peak SV, first minute | 300 | 275 | **238** | under ~200 |
| seconds of heat at 100% | 25.4 | 23.4 | **13.9** | 0 |
| seconds on the 140 floor | 26.4 | 38.6 | **46.9** | under ~10 |
| worst BT error vs background, 30-90 s | +19.2 at 56 s | +21.3 at 58 s | **+14.1 at 56 s** | single digits |

(Recomputed here on one 0.5 s grid for all three, so the 52 column differs from
the figures carried in the handoff by up to 1.5 s.)

Time-to-BT was the best of the three — **150/180/196.5 at +0.4 / +3.2 / −2.0 s**
against the background — and everything from 90 s on was excellent: |error| ≤ 0.3
degC from 140 s to DRY END, DRYe −1.0 s, FCs −1.5 s. **The alarm-fired fan step
landed at exactly 120.0 s and cost nothing measurable**: the error runs
monotonically +1.8 → 0.0 straight through it. That half of the previous commit
worked as specified.

#### The gate was cancelled by Artisan, one second after CHARGE

`markCharge` calls `pidcontrol.pidOn()` whenever `pidOnCHARGE` is set and the PID
is not already active (**canvas.py:14656**). `pidOnCHARGE=true` was in the file.
So the `CHARGE` button's `PID OFF` was undone *by the CHARGE mark itself*: the
gate held from the press at −6.5 s to the mark at +1.0 s, which is entirely
before the beans reach the sensor, and was worth nothing. The `CHARGE+15 s → PID
ON` alarm then fired into an already-running loop.

`pidOnCHARGE` had never mattered before, because the preheat runs with the PID
already active — the guard `not pidActive` had always been false. Adding a
deliberate `PID OFF` is what exposed it.

**The log proves the button was pressed**, so this is not procedural. `pidOn()`
sets `slider_force_move`, and `addEvent_internal` records the event when `force`
is set *even if the value has not changed* (main.py:17976-17984). Roast 53 carries
a `T_inlet -> 142` event at +1.0 s repeating the 142 that had stood since −26.5 s.
That duplicate is `pidOn()`'s signature, and it can only fire if the PID was off.

#### And the kick itself is the *lookahead*, not the frozen target

Roast 52's reading — the pre-CHARGE frozen target — is **not the dominant term**,
and roast 53 is the run that separates them, because its frozen window was only
~1 s. Replaying the PID port against roast 53's measured BT and its background:

```
charge_detect_delay 1 s, LA 3 -> 0 at ~2.5 s
   rms(replay - measured SV)   0-30 s  2.1     0-60 s  1.6     120-240 s  0.57 degC
   peak SV  replay 238   measured 238
```

That is the whole first minute reproduced to the resolution of the data, and the
mechanism it contains is this:

1. `calcSV` **ignores `svLookahead` before CHARGE** — pid_control.py:1690 returns
   the background's CHARGE BT, one constant. So the file's `svLookahead = 3`
   first takes effect *on the sample CHARGE is marked*.
2. At that sample the bed is falling ~6 degC/s, so a target 3 s ahead sits
   **15-20 degC below** BT. Error goes hard negative, output floors.
3. `_back_calculate_integral` (pid.py:314-333) converts the clamped excess into
   stored integral: **`Iterm` goes 1.2 → 25.3 → 37.8 in two samples.**
4. `Ki = 0.07` cannot unwind that. It is the **integral**, not the P term, that
   then holds `T_inlet` at 200-238 for the next 30 s. The replay's `Iterm` sits
   at 38-44 across the whole window while `Pterm` swings −7 .. +20.
5. The `LA 0` alarm closes the window at ~2.5 s, which is about 2.5 s too late.

Counterfactuals on the same replay:

| | peak SV, 0-60 s | max `Iterm` through the dip |
|---|---|---|
| as it happened | **238** | 44.1 |
| PID genuinely gated off 0-15 s | **174** | 1.2 |
| no gate, `svLookahead = 0` by default | **179** | 1.4 |
| both | **174** | 1.2 |

So **either** fix alone removes it, and both are now in the file. 174-179 is the
correctly-targeted loop answering the dip model's own error, and it lands 13.5 s
later — past the turning point, where it belongs. It is also the band the roast-52
replay predicted (145-181); that replay was right about the answer and wrong
about the reason, because it put the lookahead switch at CHARGE+1 s and so never
opened the window.

Roast 52 replayed with the corrected timing gives the right *shape* — a broad
230-236 plateau over 6-18 s, `Iterm` pumped to 53 — against a measured 275, so
rms 33 over 0-60 s. The mechanism is there; the magnitude is not fully recovered,
and roast 53 is the run that carries the evidence.

#### What is left

The dip model is untouched by any of this and its two known errors both stand.
The pour ramp: the generated curve is still ~6 degC too cold over 1-4 s (BT 117.2
against a background 110.7 at 3 s), the same defect roast 52 showed at ~10 degC.
And the turning point: measured **62.4 degC at 20 s** against the background's
**62.06 at 29 s** — the depth is right to 0.35 degC and the phase is not, which
`make_charge_background.py --check` has been reporting all along (roast 50 22 s
vs 27 s, roast 51 21 s vs 29 s). That late turning point is what generates the
standing +4.8 degC error over 10-16 s, and it is what the 174-179 of the fixed
loop is answering.

**But about half of that 9 s is the loop, not the model, and none of the series
has ever measured the free dip.** `charge_dip.py` builds the dip with the inlet
**held at its pre-charge value**, and every roast so far railed `T_inlet` to
240-300 through it. `tools/analysis/dekick_tp.py` backs the excess out to first
order with the roast-46 plant card — `BT_excess(t) = a * int(inlet(s-theta) -
140.4) ds`:

| roast | peak inlet 0-40 s | measured TP | de-kicked TP |
|---|---|---|---|
| 50 (warm) | 221 | 80.2 degC at 21.8 s | 77.5 at **32.0 s** |
| 51 | 252 | 63.8 degC at 21.0 s | 62.5 at **24.0 s** |
| 53 | 240 | 62.4 degC at 20.0 s | 61.1 at **23.5 s** |
| the model | — | — | 62.1 at **29.0 s** |

The residual is **~5 s, not 9**, and the depth is right to ~1 degC. It is an
estimate and not a measurement — `theta` carries a band of 13 +5/−1 s and the
neglected feedback term is second-order — but it is enough to settle what to do:
**refitting the dip model now would fit it to the overshoot the loop itself
caused.** That is precisely the circularity `--check` guards against by scoring
only 0-18 s. Roast 54 with a working gate is the first roast that will hold the
inlet near 140 through the dip, i.e. the first that satisfies the model's own
assumption, and it is the measurement.

The two defects also push opposite ways: ~2 s of pour ramp delays the mixing
exponential's start and moves the turning point ~1 s *later*, widening the phase
gap. Fix them together, after roast 54, and run roast 54 on the background
unchanged — which also makes it a clean A/B against roast 53.

### Roast 54 (2026-09-07, 14:09) — the gate held, and the free dip is finally measured

400 g of the same Kenya lot at `greens_temp = -12.0`, same config
(`airRoaster_cascadePID_chargetemp.aset` with `pidOnCHARGE=false` and
`svLookahead=0`), same background (`profile_400g_m12C.alog`, unchanged) — one
variable moved against roast 53. **The gate held, three of the four checks pass,
and the fourth is no longer a loop problem.**

| check | roast 51 | roast 52 | roast 53 | **roast 54** | pass |
|---|---|---|---|---|---|
| peak SV, first minute | 300 | 275 | 238 | **193** | under ~200 — **pass** |
| seconds of heat at 100% | 25.5 | 23.5 | 14.0 | **3.0** | 0 — **near** |
| seconds on the 140 floor | 29.0 | 42.0 | 46.9 | **36.0** | under ~10 — **fail** |
| worst BT error vs background, 30-90 s | +19.2 at 56 s | +21.3 at 58 s | +14.1 at 56 s | **+5.5 at 63 s** | single digits — **pass** |

(The floor row counts `SV <= 141.5`, which is the definition the earlier rows
were computed with. On a strict `SV <= 140.5` the same four roasts read
25.0 / 38.5 / 41.0 / **28.0** s.)

Time-to-BT 150/180/196.5 came in at **−1.5 / +0.2 / −2.5 s**, the tightest of the
series; DRYe −3.0 s, FCs −3.5 s, DROP 424.5 s against the background's 425.0 at
BT 200.1. **From 90 s to DROP the worst absolute error is 1.8 degC** (roast 53:
7.3). The fan step fired at exactly 120.0 s and again cost nothing — error runs
−1.7, −1.7, −1.8, −1.6 across it.

#### The gate

`T_inlet` carries **exactly one event between CHARGE and 15.5 s**, and it is not
a command (see below). The next event is `188` at **15.5 s**, the
`CHARGE+15 s -> PID ON` alarm. Inlet sat at 143-145 from CHARGE to 16 s against
roast 53's climb to 230 by 14 s. Every alarm fired as configured: `LA 0` at +1 s,
`LA 6` at +90 s (which is the SV step 147 -> 171 at 91 s, present in roast 53
too), `PID ON` at +15 s, `Fan 60` at +120 s.

The PID port reproduces the whole roast: driven by roast 54's measured BT with
the loop held off to 15.5 s, `svLookahead` 0 then 6 at 90 s,

```
   rms(replay - measured SV)   0-30 s  7.4    0-60 s  5.4    120-240 s  0.74 degC
   peak SV  replay 189   measured 193      max Iterm 0-60 s  17.3  (roast 53: 44.1)
```

**There is no windup left.** The two remaining defects are both the target, not
the loop.

#### The `T_inlet` duplicate at CHARGE+1 s is `markCharge`, not `pidOn()` — the roast-53 record was wrong about this

Roast 54 carries a `T_inlet -> 143` event at +1.0 s repeating the 143 that had
stood since −9.5 s — the same signature the roast-53 section above attributes to
`pidOn()` and calls proof that the PID was off. **That reading is wrong**, and
roast 54 disproves it directly: `pidOnCHARGE` is `false` here and the PID is
demonstrably off through 15.5 s, yet the duplicate appears anyway.

The real source is `markCharge` itself. After setting `timeindex[0]` it walks all
four sliders and re-records every visible non-zero one
(**canvas.py:14694-14709**, "mark active slider values that are not zero").
`EventRecordAction`'s duplicate guard (**canvas.py:15854-15856**) compares only
against `specialeventstype[-1]` / `specialeventsvalue[-1]` — *the single most
recent event of any type* — so the `Air -> 64` the CHARGE button fires a few
seconds earlier reliably breaks the guard for `T_inlet`. All four roasts show the
pattern:

| roast | last event before CHARGE | at +1.0 s |
|---|---|---|
| 51 | Air 64 at −7.0 s | T_inlet 146 |
| 52 | T_inlet 141 at −3.5 s | Air 64 **and** T_inlet 147 |
| 53 | Air 64 at −6.5 s | T_inlet 142 |
| 54 | Air 64 at −4.5 s | T_inlet 143 |

The `pidOnCHARGE` diagnosis stands on its own — the flag was `true` in the file
and canvas.py:14656 calls `pidOn()` — but the log signature cited for it was
misread, and the handoff's "first thing to check: the events over 0-15 s should
be empty" is not achievable. **The check that actually works is that there is
nothing between +1 s and the PID ON alarm.**

#### The free dip, measured for the first time

Roast 54 is the first roast in the series that satisfies `charge_dip.py`'s own
assumption — inlet held at its pre-charge value through the dip. `dekick_tp.py`
now has almost nothing to remove:

| roast | peak inlet 0-40 s | measured TP | de-kicked TP | kick added by TP |
|---|---|---|---|---|
| 51 | 252 | 63.8 at 21.0 s | 62.5 at 24.0 s | 0.7 degC |
| 53 | 240 | 62.4 at 20.0 s | 61.1 at 23.5 s | 0.5 degC |
| **54** | **204** | **55.6 at 23.0 s** | **55.2 at 24.5 s** | **0.3 degC** |
| the model | — | — | 62.1 at 29.0 s | — |

The free window runs 0 to ~29 s: the PID ON at 15.5 s cannot reach BT before
15.5 + theta = 29 s, so the turning point at 23.0 s is genuinely free.

**Against that window the model is wrong two ways, and the de-kicked estimates
above understated both.** Measured TP 55.6 at 23.0 s against 62.3 at 29 s: the
dip is **6.7 degC deeper and 6 s earlier** than generated. The depth alone is
absorbable by charge state — refitting `T_bean` over 6-30 s gives −25.8 degC and
matches the depth to 0.8 degC — but that leaves the turning point at 30 s and
makes the phase *worse*. `charge_state.py` independently reads roast 54 at
**T_bean = −24.1 degC** (roast 53: −19.3, roast 51: −15.7, all three entered as
−12.0), so depth and charge state are not separable from one roast.

**The two known defects turn out to push the same way, not opposite ways.** The
roast-53 section predicted that adding the pour ramp would move the turning point
~1 s later and widen the phase gap. That is true only at fixed `dT_mix` and
`tau_mix`; in a joint fit the ramp *lets `tau_mix` shorten*, and the turning point
moves earlier. Fitting `(dT_mix, tau_mix)` to roast 54's free window 0-29 s at a
range of fixed pour widths `w_c`:

| `w_c` | `dT_mix` | `tau_mix` | rms 0-29 s | model TP |
|---|---|---|---|---|
| 0 s (today) | 107.6 | 13.70 | 2.83 | 53.1 at 29.0 s |
| 2 s | 100.8 | 10.54 | 1.12 | 54.9 at 28.0 s |
| **3 s** | **98.1** | **9.39** | **1.04** | **55.5 at 26.5 s** |
| 4 s | 95.8 | 8.35 | 1.56 | 56.0 at 25.0 s |
| 5 s | 93.8 | 7.40 | 2.24 | 56.3 at 23.5 s |

Measured: 55.6 at 23.0 s. Without the ramp the fit hits `tau_mix = 13.7` and
still cannot produce a turning point before 29 s — the single exponential is
structurally unable to be both that deep and that early. With `w_c = 3 s` the rms
over the whole free window falls from 2.83 to **1.04 degC** and the phase gap
closes from 6 s to 3.5 s; `w_c = 5 s` closes the phase entirely at the cost of
rms. So the fix is **one joint refit of `(w_c, dT_mix, tau_mix)`**, not two
independent corrections, and the calibration roasts 43/44/46 have to be refit
with it (their `phi` and `tau_mix` absorb the missing ramp today).

#### What the remaining failure actually is

The 36 s on the floor and the +5.5 degC error at 63 s are the *same* event and
they are the model's, not the loop's. The sequence:

```
   0-16 s   gate held, inlet 143-145; BT falls to 8.5 degC BELOW the background
  15.5 s   PID ON into a −8.5 degC error; SV 188-193, heat 100% for 2.5 s
  23.0 s   free turning point, 55.6 degC (the background turns at 29 s, 62.1)
  29-40 s   the 15.5 s command arrives; BT crosses the background at 38 s
  48-76 s   SV on the floor unwinding a +5 degC overshoot
```

The loop was handed a target that is too shallow and too late, drove hard at the
resulting −8.5 degC error, and then spent 28 s on the floor paying for it. Both
the 100%-heat seconds (16.0-18.0 s, plus one sample at 91.5 s when `LA 6` steps
the target) are responses to a *commanded step*, not railing: peak `Iterm` is
17.3 against roast 53's 44.1.

**Fix the dip model and this check goes with it.** There is nothing left to tune.

#### Housekeeping

`moisture_greens` is still `0.0` — not entered, for the second roast running.
Weight loss 10.85% (53: 11.08, 52: 11.92, 51: 12.25).

### The dip model's joint refit (2026-09-07) — a pour ramp and a scale error

The job the roast-54 handoff set: port `charge_thermal.py`'s pour ramp `w_c` into
`charge_dip.dip()` and refit `(w_c, phi400, tau_mix)` jointly, rather than fixing
the ramp and the turning point as two changes. Done, and it found a second defect
the handoff had not separated out.

#### The ramp, and what leaving it out was costing

`dip()`'s mixing rate was a bare exponential starting at `t = 0`. The charge is a
ramp — 400 g takes a second or two to tip in — so each parcel poured at `s` mixes
on its own `tau_mix` and the rate is the convolution of a uniform pour with the
exponential. That has a closed form, and it is now `charge_dip.mix_kernel`:

```
g(t) = exp(-t/tau_mix) * (exp(min(t, w_c)/tau_mix) - 1) / w_c
```

It integrates to exactly 1, so the ramp changes **when** the deficit is drawn and
never how much — the heat stays conserved, which is the property that made the
decaying-rate formulation right in the first place. At `w_c -> 0` it collapses to
the old `exp(-t/tau_mix)/tau_mix`.

**The missing ramp was not costing the first two seconds, it was costing the
phase.** Without it the fit has to buy the dip's depth by stretching `tau_mix`,
and a long `tau_mix` turns late. Profiling `w_c` with `phi` and `tau_mix`
re-optimised at each value (`charge_dip.py --ramp`):

| `w_c` | `phi400` | `tau_mix` | cal rms | roast 54 TP |
|---|---|---|---|---|
| **0 s (the old model)** | 0.7837 | 14.86 | 2.73 | 52.2 at 30.0 s |
| 1 s | 0.7446 | 12.55 | 1.73 | 53.9 at 30.0 s |
| **2.1 s (shipped)** | **0.7118** | **10.84** | **1.31** | **55.3 at 28.5 s** |
| 3 s | 0.6888 | 9.64 | 1.58 | 56.3 at 27.0 s |
| 5 s | 0.6474 | 7.34 | 3.00 | 57.9 at 23.5 s |
| 7 s | 0.6154 | 5.42 | 4.40 | 59.0 at 21.0 s |

measured 55.6 at 23.0 s. The minimum is real and one-basined, the calibration rms
halves, and `w_c` and `tau_mix` correlate at **−0.77** — they trade, so **read the
band 1.5-3 s and not a fourth decimal**. The residuals are autocorrelated as
everywhere else in this directory, so the naive standard errors (`w_c` ±0.10) are
optimistic and are not quoted as a result.

**`w_c` is identified without roast 54 at all.** The old 43/44/46 group profiled
on its own puts the minimum at 2.8 s and drops its rms 3.08 → 1.76. The ramp is
not something roast 54 alone asked for; it is something the whole series wanted
and the previous fit was absorbing into `tau_mix`.

`charge_thermal.py`'s card says `w_c = 0.54 s`, and that is not a contradiction
worth resolving: that fit is no-flow and `w_c` there only scales a wall-to-bed
coupling. Under flow the roasts want 2.1 s and say so with a clear minimum.

#### The second defect: phi was on the wrong temperature scale

The handoff warned that depth and charge state are not separable from one roast.
They are worse than inseparable — they were being **mixed across two scales**,
and that, not the ramp, is most of roast 54's 6.7 degC.

`phi` was fitted on roasts 43/44/46, whose charge temperature is *assumed* at
−18 degC because nothing was entered. `make_charge_background.py` then evaluated
that `phi` at the operator's *entered* −12.0. Twelve degC of charge temperature
is worth 0.07 of `phi`, so the two scales do not commute, and the generated dip
came out shallow by exactly that product. Both branches fit the data
(`charge_dip.py --scale`):

| branch | group | `phi400` | `tau_mix` | `w_c` | rms | `dT_mix` at BT 129.8 |
|---|---|---|---|---|---|---|
| A | 43/44/46 at assumed −18, 54 at `charge_state.py`'s −24.1 | 0.6475 | 9.99 | 2.51 | 1.64 | 99.6 at −24.1 |
| **B (shipped)** | **50/51/53/54 at the entered greens temperatures** | **0.7116** | **10.84** | **2.10** | **1.31** | **100.9 at −12.0** |

**They ask for the same dip.** That is the whole point: the operator's
thermometer offset cancels out of the answer as long as the number fitted on and
the number evaluated at are read the same way. Branch B is shipped because its
scale is the one `--greens-temp` is handed. Branch A is kept as a held-out check
and reports a visibly different `phi` on purpose.

Two independent corroborations that the entered −12.0 is not the bean's core:
`charge_state.py` reads roast 54 at −24.1 degC, and letting `T_bean(54)` float
in the branch-A joint fit lands it at **−23.9** — two estimators with nothing in
common agreeing to 0.2 degC. Neither settles it, because both are anchored on the
same −18 assumption. **`phi` is depth per degC on the operator's scale and is not
physics**; settling it needs a charge whose *core* temperature is measured.

#### The calibration group changed, and so did the fit window

`CAL_RIDS` is now `50/51/53/54` — every roast carrying an entered greens
temperature — replacing 43/44/46. Each roast is scored over its own **loop-free
window** (`charge_dip.free_window`): `theta` seconds after that roast's inlet
first leaves the preheat, past which the residual is the plant card replaying the
loop's own kick. That is 15.0/16.0/18.5 s for roasts 50/51/53 and **30.0 s** for
roast 54. Only roast 54's window reaches past its own turning point, so the
descent is fitted by four roasts and the *turn* by one. Leave-one-out is stable:
`phi400` 0.689-0.712, `tau_mix` 10.5-10.8, `w_c` 2.05-2.28.

#### The fusion enthalpy: zero again, and now for a better reason

`--fusion` used to argue from held-out warm roasts whose temperatures came from
the same proxy. The recorded group makes the argument directly: **roast 50 is a
+25 degC charge, the only *measured* charge temperature in the entire set, and
unfrozen**, so `h_fus` cannot touch its depth — every J/g raises its residual as
the frozen roasts pull `phi` down. Across 0-35 J/g roast 50's rms goes
1.18 → 4.52 while the frozen roasts improve by a tenth. `h_fus = 0` stands, still
against `charge_thermal.py`'s still-air preference for 7-35, and the disagreement
is still unresolved.

#### What the refit fixed, and the one defect it did not

Against roast 54 over its full 30 s free window, the generated background's worst
error falls from **22.6 degC** (`profile_003`) to **2.6 degC**.

**The turning point is still ~6 s late, and that is now residual error rather
than an expected offset.** `make_charge_background.py` used to claim the opposite
— that 27-29 s against the roasts' 21-22 s was correct because those roasts
turned early only *because* the loop kicked. Roast 54 disproved it: the gate
held, `dekick_tp.py` puts the loop's whole contribution to its turning point at
**0.3 degC**, and it turned at 55.6 at 23.0 s. The generated curve turns at 55.0
at 29 s. No value of `w_c` fixes it — a single exponential mix cannot be both
this deep and turn this early against this plant card — and the docstring has
been corrected to say so.

It costs little because the minimum is flat, and the residual is a clean phase
signature against roast 54:

| t (s) | 5 | 10 | 15 | 20 | 23 | 25 | 30 |
|---|---|---|---|---|---|---|---|
| background − BT | −1.0 | +0.9 | +2.0 | +1.5 | +0.7 | −0.2 | −2.6 |

The background runs ~2 degC **above** the bed through the descent and ~2.5 degC
**below** it by 30 s. So at the `PID ON` alarm the loop sees about 2 degC of
error where roast 54's background handed it 8.5, and by 24 s the sign has flipped
to the direction that makes the loop back off rather than kick. The remaining gap
is the one defect the model still has; it is not licence to fit the turning point.

#### Also changed

- `make_charge_background.py --check` now scores each reference roast over its
  own free window instead of a fixed 0-18 s, and **roast 54 is a reference** —
  the only free dip on record.
- `--no-write` added. `--check` generates the background and *then* reports on
  it, so running it after a roast destroys the profile that roast was scored
  against. `--no-write` scores without touching the disk.

### Designing roast 55 (2026-09-07) — the TP trigger, and the blend that had to shorten

Three findings, two of which changed the plan.

#### Artisan *can* key the loop off the measured dip; it is not worth doing

The roast-54 record assumed this was impossible. It is not. Artisan alarms carry
a **TP** time base — `alarmtime == 8`, the combo-box entry sitting between CHARGE
and DRY END (alarms.py:847-854) — and `alarm_time` is measured from
`sample_timex[self.TPalarmtimeindex]` (canvas.py:5278-5279). `TPalarmtimeindex`
is set **live** by `sample()`: `checkTPalarmtime()` (canvas.py:4642-4650) waits
for >20 s since CHARGE and four rising samples, then `findTP()`
(util.py:927-954) returns the index of the *true* BT minimum, retrospectively.
There is a 2-minute backstop that forces the index if no TP is found
(canvas.py:5129-5133). So "N seconds after the measured turning point" is a
first-class trigger, available today with no firmware change.

**It buys nothing, because the turning-point time barely depends on the charge.**
The refitted model, inlet held at the preheat:

| `T_bean` | −6 | −12 | −18 | −24 |
|---|---|---|---|---|
| TP | 58.6 at 28.5 s | 55.1 at 29.0 s | 51.5 at 29.0 s | 47.9 at 29.0 s |

18 degC of charge moves the depth by 10.7 degC and the *timing* by 0.5 s. The
roasts say the same: 37 degC of measured charge difference moved the measured TP
by about a second (roast 50 at 22 s, roast 51 at 21 s, roast 54 at 23 s). The
charge state lives in the dip's **depth**, and depth is exactly the quantity that
cannot be separated from `phi`. A TP-keyed trigger adapts to a variable that does
not vary. Recorded here so it is not re-proposed.

#### Switching on later is strictly worse

Worst error handed to the PID at switch-on, over a ±6 degC charge range:

| trigger | CHARGE+15.5 s | +20 s | +25 s | +30 s | TP+3 s | TP+5 s | TP+12 s | BT≥65 | BT≥75 |
|---|---|---|---|---|---|---|---|---|---|
| worst | **6.0** | 6.6 | 7.0 | 7.2 | 7.2 | 7.3 | 7.4 | 8.8 | 12.3 |

At 15.5 s only about two-thirds of the mixing deficit has been drawn, so an early
switch-on catches the charge-state error before it has finished developing; every
later rule waits for the full deficit. The BT-threshold rules are worst of all
because they conflate depth with time. **The existing CHARGE+15 s alarm is
already the best of the rules tested**, and the answer to charge-temperature
uncertainty is not a cleverer trigger: ±6 degC of charge costs ±3 degC at
switch-on, which `Kp` 3.0 turns into ±9 degC of SV.

#### The blend window had to shorten, and this nearly shipped a regression

Regenerating roast 55's background from `profile_003` at the stock
`--t1 30 --t2 150` fixed the dip and **broke the recovery**. The blend is only
16% source at 60 s, so 84% of the curve there is the dip model — which means
"the inlet stayed at the preheat and no heat was added". The refitted dip is
deeper and later, so the whole recovery dropped with it:

| background, BT at | 40 s | 60 s | 75 s | 90 s |
|---|---|---|---|---|
| roast 54 measured | 65.7 | 80.7 | 89.6 | 97.3 |
| roast 54's background | −1.1 | −5.3 | −4.3 | −1.3 |
| refit, `t2 = 150` | **−7.4** | **−9.9** | **−7.6** | −3.6 |
| refit onto roast 54's bkg, `t2 = 50` | −4.3 | −5.3 | −4.3 | −1.3 |

Roast 54 already spent **36 s saturated on the 140 floor** unable to hold the bed
*down* to a target 5 degC below it. A target 10 degC below would have made the
one failing check worse while the headline number improved — a regression hiding
behind a better dip. The dip model is credible to ~40 s (97.5% of the mixing is
delivered by then) and says nothing useful past it, so the blend now ends at
50 s and the source is **roast 54's own background** rather than `profile_003`.
Past 60 s the file is byte-identical (max diff 0.000 degC), which makes roast 55
a genuine one-variable experiment. All the candidates reach BT 150 at the same
193 s, so the blend choice does not touch the roast's schedule.

#### The closed-loop simulator is not validated through the dip

`sim.simulate` was used to try to settle the above and **could not**: against
roast 54, same background and same config, it runs rms 4.9 degC over 16-60 s and
4.7 over 60-120 s, and it never puts SV on the floor at all where the real roast
sat at 140 for 45 s. Its bed runs 5-6 degC cold through the recovery, so its loop
keeps pushing where the real one backed off. The validated claim was always about
the **PID port** (`replay_pid`) over **120-240 s**, which is a different thing.
**Do not use `simulate` to design a background**; the open-loop comparison above
needs no simulator and is what the decision rests on.

### The SV floor, and why it should have come down four roasts ago (2026-09-07)

Operator, on being handed a fifth plan that left it alone: *"why not lower the
floor? You've resisted that so many times I really don't understand... it's
really irritating to see the control hit its floor and build up error because it
keeps the bean temp above the background."*

The objection is correct and the deferrals were not justified. The measurement
that settles it, from roast 54's own log while `SV` sat pinned at 140:

| t (s) | 45 | 50 | 55 | 60 | 65 | 70 | 75 | 80 |
|---|---|---|---|---|---|---|---|---|
| `SV` | 143 | 140 | 140 | 140 | 140 | 140 | 140 | 141 |
| `HT` % | 44.3 | 46.0 | 44.9 | 46.8 | 46.0 | 45.2 | 45.1 | 49.8 |
| BT | 69.9 | 73.8 | 77.2 | 80.7 | 83.7 | 87.0 | 89.6 | 92.4 |

**The heater was at 46% for the whole 36 s the loop spent "out of authority".**
It was not out of authority; it was forbidden from using roughly half the
machine's range. The bed stayed above the background and the error persisted
because the controller could not act, which is exactly what the operator has been
watching happen for four roasts.

**The floor has no roast-phase justification.** It is a *preheat* number —
holding BT 130 at fan 60 needs inlet 140.4 and 140 was set just under it. The
firmware clamps `INLET` at `INLET_SV_MIN_C = 0.0` (airRoaster.ino:191), so
nothing downstream needs it. It is harmful in the preheat too: § The preheat runs
at fan 60 records the inlet pinning to the floor and BT stalling at **137** at
fan 64, which is this clamp.

**Why it is not a one-line change, and what actually made it look forbidding.**
Artisan maps the PID's 0-100% output onto `[positiveTargetMin, positiveTargetMax]`
(pid_control.py:1302-1304), so `dSV/derror = Kp*(max-min)/100`. Two consequences
that have to be handled together, and neither was worked out before:

1. **Widening the span raises the gain.** 140→100 takes the span 160→200, a 25%
   gain increase, unless `Kp` and `Ki` are scaled by 0.8. At `Kp` 2.4 / `Ki`
   0.056 the physical gain is *identical* — 4.80 degC of SV per degC of BT error
   and 0.1120 degC/s per degC-second — so the loop behaves the same everywhere it
   was already working and differs only where it was clamped.
2. **The integrator carries the whole operating point.** At zero error the loop
   commands `SV = min`, so holding the preheat's 140.4 needs `Iterm = 20.2` where
   it needed 0.3. The preheat builds this under the PID, and `update()` freezes
   it through the charge gate (it forces `target = i` while inactive,
   pid.py:406-408, so `err = 0` and the integral holds). **The new failure mode
   is a short or late preheat**, which now starts the roast with the integrator
   low and the bed cold. The check is the one the protocol already has: PID on,
   BT flat at 130, inlet settled at ~140.4, `Temp_Drive` 10-12.

The authority bought, from `ff_roast47` at fan 64 — extrapolated below its `sv`
box of [145, 185], but it predicted roast 54's floor heat to 0.3 points:

| `SV` | 140 | 120 | 100 | 80 |
|---|---|---|---|---|
| heat % | 46.0 | 41.5 | **37.1** | 32.7 |

**Shipped as `artisan/airRoaster_cascadePID_floor100.aset`**: roast 54's
`_chargetemp` set with `positiveTargetMin` 140→100, `pidKp` 3.0→2.4, `pidKi`
0.07→0.056, and nothing else touched (diff is those three lines).

**On changing it in the same roast as the background.** The two act in disjoint
regions — the background changes the target over 0-50 s, the floor changes only
what happens when the loop wants `SV < 140`, which on roast 54 was 45-90 s — and
the log separates them: the dip fix is read at 0-30 s and in the peak SV, the
floor in whether `SV` ever goes below 140 and in the 45-90 s error. The
one-variable rule is a means to attribution, not an end, and here attribution
survives both changes. Note also state-plan.md § What was ruled out, whose
"pure reparameterisation" row was being read as a standing objection to this; it
answers a different question (can the range be used to shrink the integrator's
swing?) and says nothing about saturation. Corrected there.
