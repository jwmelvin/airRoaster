# state-current — what is being worked on right now

> One of four state documents. **This file**: the active effort and where it
> stands. [state-plan.md](state-plan.md): planned work and the specifications
> in force. [state-history.md](state-history.md): the roast-by-roast cascade PID
> reasoning behind them, chronological and superseding as it goes.
> [state-archive.md](state-archive.md): completed work, review findings, and
> decided-and-done rationale. Update discipline: when a phase completes, move
> its detail from *plan* to *archive* and re-point this file at the next phase;
> when a plan section turns into a record of what happened rather than a
> statement of what to do, move it to *history*.

## Development framework (read this first if you are new here)

**What this is.** ESP32-S3 firmware (`airRoaster.ino`, single sketch file) for a
hot-air coffee roaster: two I2C AC dimmers (heat 0x51, fan 0x52), three SPI
temperature sensors (2× MAX31865 RTD, 1× MAX31855 thermocouple), SH1107 OLED,
WebSocket server speaking Artisan's protocol plus plain-text commands, and an
on-device PI(D) closed loop holding inlet temperature. `dashboard.html` (repo
root) is a zero-dependency browser console for commissioning and tuning.

**How to build.** `./verify.sh` compile-verifies (arduino-cli, FQBN
`esp32:esp32:adafruit_feather_esp32s3`, ESP32 core 3.3.10 / IDF 5.x);
`./verify.sh upload` flashes. There is no test suite — the verify script plus
on-roaster commissioning ([README](README.md) § Commissioning) is the loop.
Compile after every meaningful edit; the script surfaces sketch-local warnings.

**Ground truth documents.**
- [README.md](README.md) — user-facing behavior, command set, Artisan setup.
- [hardware/pins.md](hardware/pins.md) — pin/bus/address map. Do not invent pins.
- [hardware/emi.md](hardware/emi.md) — the RTD noise/fault history and why the
  sensor code is shaped the way it is. Read before touching `serviceRtd()`.
- [hardware/max31865.pdf](hardware/max31865.pdf), [hardware/max31855.pdf](hardware/max31855.pdf)
  — sensor datasheets; register-level claims must trace to these.
- DimmerLink I2C protocol: https://www.rbdimmer.com/docs/dimmerlink-I2CCommunication
  (registers: 0x00 status, 0x01 command [RESET=0x01], 0x02 error, 0x03 version,
  0x10 level, 0x11 curve, 0x20 freq, 0x30 address).
- **Artisan source: `~/src/artisan`, checked out at tag `v4.2.0`.** The shipped
  `.app` is compiled, so every claim about Artisan's behaviour in these documents
  is cited as `<file>:<line>` into
  `~/src/artisan/src/artisanlib/{pid,pid_control,main,canvas,pid_dialogs}.py`.
  **Do not re-download it and do not read `master`** — see the box below.

**Referencing the Artisan source.** A local clone lives at **`~/src/artisan`**,
checked out at **`v4.2.0`** — the version installed at `/Applications/Artisan.app`
(`CFBundleShortVersionString` 4.2.0). Read it directly; there is no need to fetch
anything.

```
~/src/artisan/src/artisanlib/{pid,pid_control,main,canvas,pid_dialogs}.py
```

**The version matters and has already bitten this project once.** The analysis
through 2026-09-02 was written against GitHub `master`, which by then was ahead
of 4.2.0 and heading for 4.2.1 — **every `file:line` citation was wrong for the
installed build**, by hundreds of lines in `main.py` and `canvas.py`. All 85
citations in `state-plan.md` and `state-current.md` were remapped to v4.2.0 on
2026-09-02 and spot-checked. So:

- **Cite line numbers only from `~/src/artisan` at `v4.2.0`.** If the operator
  upgrades Artisan, `git checkout` the new tag *and* re-verify the citations
  before trusting them.
- When quoting behaviour, prefer naming the function as well as the line, so a
  version drift is recoverable (`_back_calculate_integral`, pid.py:314-333).
- Grep by **function name**, not by a name prefix. Two findings in this project
  were missed by over-narrow greps: `p-i-d(<p>,<i>,<d>)` was missed by searching
  only for commands starting with `pid`, and the `.alog` PID fields were trusted
  when they record settings at *save* time.

**The mechanisms the control analysis rests on were checked function-by-function
against v4.2.0 and are byte-identical to what was read on master**:
`_back_calculate_integral`, `_should_integrate`, `applyIntegralLimits`,
`update`, `setPID`, `calcSV`, `setEnergy`, `smooth_sv`. Two differ and neither
matters here: `_calculate_derivative` only lazy-inits its filter on master, and
`getParameter` on master adds a guard rejecting an all-zero gain schedule that
4.2.0 lacks — so on 4.2.0, enabling `pidGainScheduling` with `pidSchedule0` and
`pidSchedule1` both at 0 attempts a degenerate fit. Scheduling is off.

**Licensing.** Artisan is AGPL-3.0 and this repository is MIT and public
(`github.com/jwmelvin/airRoaster`). The clone is deliberately **outside** the
repo — do not vendor Artisan source into it.

**Conventions.**
- Single `.ino` plus small local headers when a component earns isolation
  (e.g. the direct MAX31865 driver). No external libraries beyond those in
  README § Dependencies without good reason.
- Version history lives at the bottom of `airRoaster.ino`; bump `FW_VERSION`
  and add an entry per firmware-visible change set.
- All unsolicited WebSocket traffic uses Artisan's push envelope
  `{"pushMessage":"<type>","data":...}`; replies to a specific client go only
  to that client. JSON is built with `snprintf` into sized buffers — check the
  buffer size when adding fields.
- Safety posture: the heater must never run without airflow (interlock), never
  survive a crash-reboot (boot-time level sync), and never be driven by a stale
  or faulted sensor (control-loop failsafe). New features must not weaken these.
- The control law stays isolated in `controlStep()` (the "seam") so it can move
  to a FreeRTOS task later without changing the math.
- Roaster is not always on the bench: code must behave sanely with no dimmers,
  no sensors, and no WiFi present (log, hold safe defaults, keep serving serial).

**Git.** Development happens on feature branches; `main` holds roast-tested
firmware. `main` is at **v0.18.0** (2026-08-23): `feature/auth-proxy` (command
authentication — challenge–response sessions + Artisan signing proxy) was
fast-forwarded into `main`; its on-roaster validation is still pending
(state-plan.md § NEXT item 13, as is the ambient drill, item 12). Current
working branch is **`feature/artisan-pid`**, which now also carries **v0.19.0**
(unflashed): the `SV`/`HT` `getData` nodes and `INLET TRIM`, on top of the
Artisan configuration and documentation work it started as. Note that
`feature/vision-uvc-probe` holds two commits that exist on no other branch and
have never been pushed. Start each new effort on a fresh branch off `main`.
Commit per phase with a message naming the phase. The user's Artisan config
churn (`artisan/*.aset`, `*.alog`) may be present in the working tree — never
sweep it into a firmware commit; stage files explicitly.

## Active effort (2026-09-06)

**Artisan cascade PID** (`feature/artisan-pid`, off `main` at v0.18.0).
Artisan's software PID becomes the **outer** loop of a cascade: PV = BT against
a background curve authored in Artisan's Designer, and its output is the
**inlet setpoint** that the firmware's existing `MODE_INLET` loop holds —
`background BT curve → Artisan PID (1 Hz) → INLET <degC> → controlStep()
(250 ms) → heat`. This replaces the current flat arrangement, where
`pidSource=3` has Artisan PID-ing on the *Inlet* channel straight to OT1 heat,
duplicating the firmware's own inner loop across a 1 Hz WebSocket link. The
cascade keeps the fast inner loop on-device and gives Artisan the slow outer
job it is good at.

**No firmware change is needed** — `INLET` already accepts fractional setpoints
and already retargets bumplessly, and the hazards close in Artisan config.
The `INLET <= 0` = *disengage* semantics (v0.15.1) would let a low-saturating
outer loop reset the inner loop and kill heat once per tick; the fix is
Artisan's target subrange (`positiveTargetRangeLimit` with min 120 / max 300),
which maps the PID's 0-100% duty onto 120-300 degC so the output cannot reach 0.

**Three earlier assumptions were wrong and are corrected in the plan**, all
caught by reading Artisan's source (the shipped .app is compiled; source at
github.com/artisan-roaster-scope/artisan). First, `dutyMin`/`dutyMax` are duty
*percentages*, not degC — the originally-planned `dutyMin=120` would have pinned
the inlet setpoint at maximum permanently with the outer loop having no effect,
a runaway-heat configuration. Second, `pidSource` is 1=BT / 2=ET / >2=extra
curves, so BT is 1. Third, heat-off at drop needed no new mechanism at all:
`PID_OFF_action` fires only for external MODBUS/S7 PID control, and Artisan
alarms have no WebSocket action either — but the operator's config **already**
does it, via the DROP button action (`buttonactions[6]` -> Multiple Event ->
the `inlet_OFF` button -> `INLET 0`), and `pidOffDROP` is invoked before that
button action, so there is no race.

The one real conflict is background event **playback**: it replays T_inlet onto
slider 3, the same slider the outer PID drives. The cascade config therefore
disables `specialeventplayback`/`...ramp` and the Playback-ON-at-CHARGE alarm.

Design decisions, the settings delta, the source citations, starting gains, and
the commissioning order are in state-plan.md § Artisan cascade PID. Two scope
boundaries fixed by the operator (2026-09-02):
`artisan/make_inlet_background.py` is **unchanged** — it stays the tool for the
*inner*-loop event-playback path, which remains the non-cascade alternative —
and the inner loop is **not retuned** (Kp 1.5 / Ki 0.05 / Kd 0 stand,
roast-validated).

**First cascade roast: airRoaster_40, 2026-09-02.** The cascade ran correctly —
the failure was tuning. Replaying the recorded BT error through the PID with the
as-shipped gains reproduces the measured inlet to within ~5 degC, so the config
did what it was told. `Ki=0.003` was 10-20x too small: after six minutes the
integrator had supplied 14 duty of ~60, leaving a P-only loop that needed a
standing **+17 degC BT deficit** to hold its output, all roast. The reason the
estimate was wrong is structural — the outer loop's output is an absolute
setpoint, so the integrator must supply the entire operating point, a job the
firmware's inner loop gives to `feedforward()` and which Artisan's software PID
has no term for. New gains: Kp 3.0, Ki 0.04, floor 140 degC, `svLookahead` 20 s.
Detail and the caveats are in state-history.md § Roast 40.

**Roast 41 (later the same evening, dashboard telemetry only) validated the
inner loop**: on the SV 150 plateau it tracks to rms 0.3 degC, heat reached 100%
for 16 s across 9.5 min and never 0, one clean engage/disengage. Every
limitation seen so far is the outer loop. Its fault is **integral windup**:
solving the loop equation against the real error shows the integral term pinned
at 83-95 against a one-sided [0, 100] clamp for the whole roast, so BT ran
*above* target throughout (every milestone early) and only a large negative P
term could trim it — which is what made Kp=8.5 look like it was helping, and
what produced the +/-50-60 degC ringing. This is the mirror of roast 40, where
I ~ 14 and the loop could not push up; one root cause, an integrator far too
slow at Ki=0.003 to serve as the operating-point supplier.

**Why the integrator was already wound up at CHARGE** (corrected 2026-09-03 —
this previously read *"the PID keeps integrating while switched off"*, which is
wrong): the integrator **cannot** wind while the PID is off in this config.
`update()` snaps the target to the PV on every inactive sample (bumpless
transfer, pid.py:406-408), so `err = 0` and the Ki path adds nothing; at
`beta = 1` and `Kd = 0` the P and D terms are zero too, the output never clamps,
and `Iterm` is simply **frozen**. What put it near 90 is back-calculation at the
output **floor**: `_back_calculate_integral` converges on `Iterm = Kp*|err|`
(8.5 x 10.5 = 89.3, the derived value) in seconds, with no Ki in the path — then
drains only at `Ki*err`, 0.009/s at Ki=0.003. Fast fill, glacial drain.

The guarantee is config-specific: with `beta < 1` or `Kd > 0` the output rails
while off and back-calculation *does* wind it. **The only thing that zeroes
Iterm is the ON button** (`OnMonitor` -> `confSoftwarePID(reset=True)`,
canvas.py:13439) — not `pidOn`, not DROP, not **RESET**, not the PID dialog, not
loading settings, and there is no `pidReset()` command. Required procedure:
press ON (clears Iterm), turn the PID on, **preheat under PID control**, then
CHARGE — the preheat target is supplied automatically as the background's CHARGE
BT — and keep it to **one PID on/off cycle per monitor ON/OFF cycle**, since
RESET between roasts silently carries the previous integrator over.

**That procedure** forced the floor back down to 140 (the loop needs inlet ~148
to hold 129.4 degC, which a 170 floor forbids) and Ki up to 0.04 (a
correctly-started integrator sits at the empty-roaster operating point ~5 duty
and must climb to ~55 during the roast). SV also sat at its 120 degC floor for
19 s during the charge dip — with the range limit unchecked that would have been
`INLET 0` and a heat kill mid-roast, so the floor is doing real work. Detail in
state-history.md § Roast 41.

**Roast 42 (2026-09-02, retuned config + PID-driven preheat): the cascade
works.** Outer integrator settles at 53-65 and stays, carrying the operating
point while P trims within +/-5 duty; tracking error +1.6 ... -0.9 degC from
3:00 on; inner loop rms 2.9 degC; heat never saturated (max 91%); SV touched the
140 floor for 8 s in the charge dip and never approached the ceiling. The
PID-driven preheat landed at CHARGE_BT 129.7 against a 129.4 target. The one
remaining offset is `svLookahead=20`, which makes the roast run 20 s ahead by
construction (DRYe 2:36 vs 3:00) — a spec error, not tuning; it should come down
to ~0 now that the cascade is known to be tight. Detail in state-history.md
§ Roast 42.

**Roast 44 (2026-09-02) is the clean validation run and the cascade is
functionally complete.** Config loaded from file, PID-driven preheat, no
intervention: CHARGE_BT 128.3 against a 127.8 target, DRYe 3:23 vs the
profile's 3:20, DROP 7:03 vs 6:51 at BT 200.7 vs 201.2, tracking error
converging +4.0 -> +1.7 degC. The auto-DROP alarm fired (operator-confirmed in
roast 43; roast 44 shows the same signature). Control settings verified
field-by-field against the PID dialog. Detail in state-history.md § Roast 44.

**The residual droop is now diagnosed, and there is a proposal on the table
(2026-09-02).** Reconstructing the outer loop from roast 44 (`.alog` + the
firmware CSV, charge-aligned by cross-correlating Inlet against IN) shows the
integrator **never settles** — it climbs monotonically 21 -> 70 duty at
~0.135 duty/s for the whole roast. That is a type-1 loop tracking a ramp:
`e_ss = (du_req/dt) / Ki`, in which **Kp does not appear at all**. The handoff's
"~12 s of velocity lag" is not a lag; it decomposes as `(du_req/dBT)/Ki =
0.505/0.04 = 12.6 s`, one over the integrator rate. Genuine loop delay is under
3 s in total (inner loop 1 s / rms 0.7 degC, BT smoothing 0.67 s, the
canvas.py:5016-before-4946 ordering 1 s, plant transport delay ~0).

A faithful reimplementation of `PID.update()` against a plant fitted to roast 44
(`dBT/dt = 0.0145*(Inlet-BT) - 0.68 + w(t)`, tau 69 s) reproduces the roast to
**rms 0.33 degC**, so tuning options are now testable rather than arguable.
**Step 1 was `pidKi` 0.04 -> 0.10 and `svLookahead` 0 -> 3, and roast 45
(2026-09-02, 21:53) confirms it.** On the valid yardstick — time to reach the
same BT, *not* mark times — roast 45 sits **0-7 s behind `profile_002` all the
way through**, against roast 44's uniform 11 s, and the steady droop in the
quiet windows is **+0.19 degC** against +3.4. The DRYe/FCs marks read 9-11 s
early only because `autoDRY`/`autoFCs` fire on the fixed Phases thresholds
(BT 149 / 196) while the profile's own marks sit at BT 152.0 / 197.9; mark-time
comparisons are not meaningful here.

**What is left is the operator's own air schedule, not the loop.** Refitting the
plant with a fan term halves the residual and gives a fan sensitivity of ~49% of
plant gain per 10 fan units, so the `65 -> 60` cut at 1:31 removes a quarter of
the plant gain in three seconds. The error tracks each cut and is flat between
them (-0.24 -> **+2.59 at 2:10** -> ~0 by 3:20 for the 5-unit cut; +0.83 ->
+1.50 -> -0.40 for the 2-unit cut at 4:26), with amplitude linear in step size.
That is load-disturbance rejection, not a limit cycle — no SV reversal over
10 degC after 1:00, SV ripple rms 1.19 degC, inner loop rms 0.91, heat 46-59%
off both rails.

**That air-change reading was wrong, and the operator caught it.** The error
minimum sits at 3:26 and the error was already climbing for a full minute before
the 4:26 cut — faster before it (+0.0130 degC/s) than after (+0.0176 then
reversing). It is one lightly-damped oscillation, not two disturbance responses:
extrema at 2:12 / 3:26 / 5:10 / 6:22, **period 177 s**, peak-to-peak decaying
2.82 -> 1.86 degC, log decrement 0.42, **zeta ~ 0.07**.

**The root error was a circular plant fit.** The disturbance had been modelled as
`w(t)`, a free per-sample time-domain residual, which absorbs exactly the
mismatch a transport delay creates — so the "plant deadtime ~0 s" result could
not have found a delay. Refitting with the disturbance restricted to a low-order
polynomial in t and the delay floating gives **theta = 17 s on roasts 44 and 45
independently**. Physically that is the bean mass between inlet air and the BT
probe; the earlier "under 3 s of lag" counted only instrumentation.

Against that plant the margins are **Ki 0.04 -> 44-47 deg, Ki 0.10 -> 18-20 deg
(predicted period 132-230 s, measured 177 s), Ki 0.15 -> 4-8 deg, Ki 0.20 ->
negative.** So **roast 45's Ki 0.10 was already the stability edge and the
step-2 recommendation of 0.15 is withdrawn.** The alog on disk records 0.15
because Artisan stamps PID settings at *save* time, not roast time — roast 45
actually ran at Ki 0.10, recovered empirically from `dI/dt = Ki*err`
(0.101, r 0.97).

**Revised: `pidKi` 0.07, `svLookahead` stays 3, `pidKp` stays 3.0** (lowering Kp
makes a delay-limited loop *worse*: PM 10 deg at Kp 2, 5 deg at Kp 1.5).
`svLookahead` is now the only free tracking lever, being feedforward. If roast
45's tracking is wanted back the route is `pidKd = 40` with DoE
(`pidDsetpointWeight = 1`) and `derivative_filter = 1`, predicted PM 29-46 deg —
an experiment for its own roast, not a settled recommendation. The fan
sensitivity measurement survives (~49% of plant gain per 10 fan units); what is
retracted is that it shapes roast 45's error trace. Detail in state-history.md
§ Correction: roast 45's error is the loop, not the air.

**A source mechanism the earlier notes missed underpins all of it**:
`_back_calculate_integral` (pid.py:314-333) runs on every clamped cycle whenever
`pidIWP` is on, and at the *low* clamp it drives `Iterm` **up**, converging
geometrically (half per second) on `Kp*|err|`. So the charge dip re-seeds the
integrator to `Kp * |worst dip error|` (roast 44: 3 x 8.4 = 25 against a
measured 24.6), whatever the preheat left is forgotten within seconds of the
floor, and **raising Ki costs nothing on the charge transient** — the dip runs
on a path with no Ki in it. The same mechanism is why `svLookahead` cannot go to
the "natural" 12 s: the background falls at 5.5 degC/s through the dip, so each
second of lead adds ~4 degC to the dip error and hence to the preload, and past
`L=4` the roast starts wound up and overshoots by 5-20 degC in the first two
minutes. The DROP-window truncation the handoff worried about is the *lesser*
constraint. Full analysis, the option-by-option review of Artisan's other
control modes (gain scheduling, beta/gamma, Dlimit, IRoC, ILF, Ramp/Soak,
sv/duty filters, BT-RoR control) and the single-roast validation checklist are
in state-history.md § Roast 44 outer-loop analysis.

**Roast 46 (2026-09-05, 400 g) is runbook step 1, and it passes.** Config
unmodified (Kp 3.0, **Ki 0.07**, Kd 0, `svLookahead` 3, floor 140), background
profile_003, PID-driven preheat, no intervention, **fan held at 60 for the roast
body** so nothing in the trace is air-schedule disturbance — *with the charge
bump*, which this summary previously flattened away and which turns out to
matter: the events read 60 at CHARGE+2 s, **64 at +7 s**, 63 at +11 s, back to 60
at +85 s. state-history.md § Roast 46 recorded it correctly all along as "the
operator's usual 63-64 blip over 0:09-1:26"; what is new (operator, 2026-09-06)
is that it is not a blip but a **requirement** — a 400 g charge does not
circulate at 60, it takes ~64 to loft the bed, after which 60 sustains. So no
run in this project can hold a constant fan from CHARGE, the characterisation
runs included, and the bump sits inside the window the plant fit draws its
excitation from. Five of
six checks pass: time-to-BT **+3.4 to +5.9 s** against the profile (roast 44, the
other 400 g batch, was +8.9 to +13.9); quiet-window error -1.02 and -0.80 degC;
inner loop rms 1.25 degC with heat 4 s at 100% and 1 s at 0% of 430; SV monotone
after 1:00. **The 177 s ring is gone** — the PID error peaks +6.12 at 2:10 and
decays monotonically to +1.06 at 6:40, with only +/-0.05 degC of quantisation
wiggle where roast 45 had 2.82 degC peak-to-peak.

**Two things came out of it, and they set the order of work.** First, the
residual above DRY END is **pure type-1 ramp error** — `Iterm` climbs 41.9 -> 61.8
at 0.095 duty/s, so `e_ss = (dI/dt)/Ki = 1.36 degC`, of which `svLookahead=3`
already cancels 0.68, leaving the measured ~1.0 degC / 4-5 s. Kp is not in that
expression. Solving `L = e_ss/slope` per sample over 3:00-7:00 gives **6.3 s** —
which is the value `artisan/airRoaster_cascadePID_lookahead.aset` already
carries. **Step 6 is therefore promoted to the next roast**; expect a +4.1 degC
target step (~+20 degC of SV) at 1:30 when the switch fires.

Second, **check 5 failed and the cause is batch size, not the loop**:
profile_003's TP is matched to roast 45 at 345 g, roast 46 was 400 g and
bottomed 9.8 degC deeper and 16 s earlier, exactly as state-history.md §
profile_003 predicted. That manufactured a 30.5 degC error swing in the first
twenty seconds, drove SV rail-to-rail (261 -> the 140 floor), put 11 s on the
floor, and re-seeded `Iterm` to ~30 by back-calculation — after which BT
overshot the background by 9.3 degC at 1:00 and sat 4.0 degC behind at 2:00. The
fix is **profile_004**, a 400 g dip spliced onto profile_003's unchanged ramp
(new runbook step 1b).

**A separate firmware finding: the feedforward term is saturated and inert.**
`FF = 100.0` for 430 of 430 roast samples; fitting the model to the three
unclamped preheat samples recovers `ffK` ~ 0.0151 / `ffAmbient` ~ 24.1, which
predicts 196% heat at fan 60 / SV 240 against an actual 55%. So `pidITerm` sits
at -45..-64 purely to cancel it, the anti-windup bound collapses to `[-100, 0]`,
and **the fan compensation the term exists for is dead** (`d(FF)/d(fan) = 0`
while clamped). The operator's five preheat fan steps measure the real number:
**0.99 % heat per fan unit** (five steps spanning 0.81-1.11; OLS over 300 s gives
`heat = -30.62 + 0.99*fan + 0.0096*SV`, resid rms 1.85 %) — so the model form is
~9x too steep in SV and ~1.8x too steep in fan and cannot be fixed by
recalibrating `ffK` alone. New runbook step 8, bench-only, and it must come
before Test C. The inner loop absorbed every one of those steps unaided (worst
7.2 degC on an 11-unit step, 1.3-3.6 degC on the rest).

Detail in state-history.md § Roast 46.

**The plant is refitted against roast 46, and there is now a simulator that
reproduces the roast to 0.16 degC (2026-09-05).** Tooling in
[tools/analysis/](tools/analysis/README.md); `roast46_refit.py` reproduces the
headline numbers.

```
dBT/dt = 0.0049 * (Inlet(t - 13.5 s) - BT) + slow(t)      tau 204 s
   theta 13 (+5, -1) s,  tau 205 (+85, -15) s,  residual 0.116 degC of BT
```

**Roast 46 is the only roast in the set that identifies a plant at all, and the
reason is the check it failed.** The 400 g batch against a 345 g dip drove the
commanded inlet rail to rail in the first two minutes — an involuntary doublet,
and exactly the excitation state-history.md § Scheduling proposed Tests A and B
to obtain. Run through the same code, roasts 44 and 45 return a negative gain or
pin the delay at a grid edge. The residual minimum in theta is **3.9x deep**
here against a flat ridge before, so `theta = 13-18 s` brackets the earlier 17 s
and the retracted `tau 69 / theta 0` model is 4x worse on residual. Estimator
changes that made the difference: integrate the model rather than differentiate
BT, and keep the charge recovery in the window while the disturbance stays a
low-order polynomial (a free `w(t)` is what produced the retracted "deadtime ~0
s").

**Artisan's `PID.update()` is reimplemented against v4.2.0 and validated.**
Driven with roast 46's measured BT and `profile_003` it reproduces the commanded
SV to **rms 0.73 degC over 0:30-7:10, 0.45 after 4:00** — the resolution of the
1 degC slider gate. Closed the loop against the fitted plant it reproduces BT to
**rms 0.159 degC over the whole roast** (0.07 after 4:00), and the *same plant*
at Ki 0.10 reproduces roast 45's 177 s ring extremum for extremum. One plant
explains both roasts.

Two source mechanisms had to be added and are new to these notes. **The
commanded SV is gated on an integer**: `setEnergy` rounds `raw_heat`, and
`addEvent_internal` fires the slider action only when that integer changes —
then sends the float. And **autoCHARGE backdates CHARGE by three samples**
(`autoChargeIdx = length - BTbreak`, `'tight' = 3`, canvas.py:5121-5126), so
Follow-Background mode does not start tracking until CHARGE+3 s; without that
the SV replay is a constant **+21 degC** out for the entire roast, because the
frozen target floors the output and back-calculation pumps `Iterm` to `Kp*|err|`.

**What the simulator says to do, ranked** (detail and the tables in
state-history.md § Roast 46 refit):

1. **Step 6 is the next roast, file unmodified.** The 1.0 degC / 4-5 s steady
   lag goes to **+0.05 degC / 0.44 s**; time-to-BT 150/180/196.5 lands at
   -1.9/+3.2/+0.9 s against the profile. The 1:30 switch is a +4.0 degC target
   step and **+24.7 degC** of commanded SV (a quarter larger than
   state-history.md § Roast 46 estimated), settled in ~15 s. The two-stage
   alternative is **not** meaningfully better — under 0.1 degC of rms for two
   more buttons and an alarm.
2. **Then profile_004, and only with that config.** Together they are the best
   configuration found: **0 s at the output floor**, dip error -2.6 degC against
   -8.8, handover `Iterm` 30 against 42, steady error +0.18 degC. At the present
   constant `svLookahead = 3`, profile_004 on its own is *worse* than profile_003.
   The `pidLookahead(0)` leg of the step-6 file is mildly counterproductive
   against profile_003 (16 s on the floor, not 4) and exactly right against
   profile_004 — which is why the file gets run unchanged rather than edited.
3. **`pidKi` 0.07 and `pidKp` 3.0 are settled, not compromises.** There is no
   room above Ki 0.07 and no need: with the lookahead carrying the tracking the
   standing error is already zero, so more integral gain only overshoots and
   rings, and 0.07 is the best value on the nominal plant, under +14 s of delay
   and under +50% of gain. Kp 3.0 stands; state-history.md § Correction's "do
   not lower Kp" holds for Kp <= 2.0 and is overstated for 2.5, which is within
   model error of 3.0.
4. **`pidKd = 40` with DoE is dropped.** The frequency-domain margin it promised
   (29-46 deg) is an artefact: in the time domain it worsens tracking, adds half
   again to the dip preload, puts 11 s back on the floor and multiplies SV ripple
   fivefold. `pidKd = 20` under DoE with `derivative_filter = 1` is the row worth
   keeping — best steady rms in the study — but it queues behind 1 and 2.
5. **Tests A/B/C drop in priority but keep their point**, which has changed: not
   to find theta (roast 46 did that) but to measure the **fan**, still a single
   weakly-identified coefficient, and to check the plant under a deliberate rather
   than an accidental doublet.

The charge dip is the weak part of the simulation — floor times are good to about
+-10 s and the 0-30 s SV replay is uncheckable at this resolution — so dip
*rankings* above are trustworthy and dip absolute numbers are not.

**Then two operator corrections landed and they change the order of work
(2026-09-05).**

**First: roast 46 was a frozen charge**, and green beans arrive anywhere between
-20 degC and room temperature. `greens_temp` is `0.0` in every roast on record, so
the dataset could not say — but the refit supplied a control-independent
measurement. **The plant delay is 13.5 s, so nothing the heater does reaches BT
before ~14 s after CHARGE**, and the BT fall over 0-13 s is charge mixing alone.
Per 100 g it is **14.46 +- 0.48 (3.3%)** across roasts 43-46, where a
room-temperature batch should read ~28% lower than a freezer one — so **all four
were frozen**, and roast 45 vs 46 really is a pure batch-size comparison. The
batch-size diagnosis of roast 46 and the plant fit both stand; what changes is
that **profile_004 would encode a *frozen* dip**, so its fragility points at warm
charges (BT above target -> negative error -> floor -> windup), the dangerous
direction. Keep `(CHARGE_BT - BT at CHARGE+13 s) / mass` as a free charge-state
proxy, and **start filling in `greens_temp`**.

**Second, and much the more valuable: the dip is a different control problem, so
gate `Ki` off through it.** The operator asked whether coarse parameters could
ride through the initial stage and be swapped after equalisation. They can, and
the earlier "no" in state-history.md § Scheduling was to a different question
(gain scheduling for the *ramp*, where the plant moves by only +-6%). The
mechanism is that `_back_calculate_integral` is gated on `getKi(PV) != 0`
(pid.py:314-333), so **`Ki = 0` closes both windup paths at once** and `Iterm`
is simply frozen — `p-i-d(3,0,0)` at CHARGE+1 s, `p-i-d(3,0.07,0)` at CHARGE+90
s, both bumpless, both the same alarm-plus-hidden-button pattern
`gen_pid_alarm_asets.py` already generates. Simulated over a 62 degC swing in
charge temperature, the integrator handed to the ramp goes from a spread of
**36.5 to 0.3**, worst error in 1:30-3:00 from -14.5 to +0.3 degC, and
time-to-BT-150 from 9.2 s of range to 1.8 s, with `Iterm` at DROP unchanged at
71.2 in every run. It removes the *sensitivity* to the dip rather than
cancelling one instance of it, which is why it is worth more than profile_004.
Costs: the SV sits on the 140 floor longer and cannot lift off it before 1:30;
`p-i-d()` is sticky so a Save Settings before 1:30 writes `pidKi = 0` into the
`.aset`; and a missed 1:30 alarm leaves the loop P-only for the roast. Lowering
`Kp` in the dip is *worse*, not better (handover spread 91.5) — `Kp = 3.0`
everywhere.

**A documentation error was also fixed**: state-history.md § Scheduling listed
`pidILF`, `pidIWP`, `pidIRoC`, `pidDerivativeLimit` and `pidDerivativeFilter` as
runtime-settable. **None of those commands exist.** The complete PID command
surface is `p-i-d(p,i,d)`, `pidWeights(beta,gamma)`, `pidLookahead(n)`,
`pidSource(n)`, the SV/RS commands and `pidmode(...)`. The three gains, the two
weights and the lookahead are the only runtime levers — and they are enough.

**Revised order (operator, 2026-09-05): step 1c first.** Files are generated —
`tools/gen_pid_alarm_asets.py` (replacing `gen_lookahead_aset.py`) emits
**`artisan/airRoaster_cascadePID_kigate.aset`** for step 1c alone and
`..._lookahead_kigate.aset` to run it with step 6. The lookahead switch fires at
1:30 rather than at DRY END, so the two are not strictly disjoint, but their
effects separate: read the dip and `I@1:30` for the gate and **5:00-7:00** for
the lookahead, and ignore DRY-END-to-5:00 in a combined roast (the integrator is
still climbing out of the gate there). **At the usual charge state step 1c is
close to a null experiment on roast quality** — check the mechanism (`I@1:30`
near 8 instead of 16, SV parked on the 140 floor until 1:30, `pidKi` back at
0.07 afterwards), not the outturn. Then step 1b (profile_004, now a refinement
rather than a fix). Runbook and detail in state-history.md § The dip is a
different control problem and § Charge temperature.

**A wider strategy search then changed the order again (2026-09-06), on the
operator's observation that the `Ki` gate hands the ramp an integrator that is
behind and has to build.** Three findings, all from a now-reproducible sweep
(`tools/analysis/dip_strategies.py`; the sweep behind state-history.md § The dip
is a different control problem was ad hoc and is gone).

**First, the correction: over the *reachable* charge range the gate does not pay
for itself.** Roast 46 was frozen, so only the warm half of the earlier +-62 degC
sweep is a charge state this roaster will see. Read that way, the baseline's
`I@1:30` spread is **3.6, not 20.8**; `lookahead` alone is the most
charge-insensitive Artisan-only option (`I@1:30` spread **0.9**, `dt150` spread
**0.4 s**, because lead is feedforward and feedforward does not care about the
integrator); and adding the gate makes every metric worse — worst error +5.79
against -4.01, steady rms 0.38 against 0.26, `dt150` spread 4.2 s against 0.4.
The mechanism stands, the magnitude does not, and the disagreement cannot be
closed. **Step 6 runs alone; steps 1b and 1c are demoted.**

**Second, the obvious repair is wrong.** Dosing the integrator back up at
handover with a short high-`Ki` burst overshoots by 10-30 s on time-to-BT-150,
and a temporary large `svLookahead` fails the same way. The loop is short of
*anticipation* over 1:30-3:20, and integral is the wrong term for it. If the gate
is wanted at all it should be built from Artisan's **native gain scheduling**
(`Ki` 0 -> 0.07 across BT 70 -> 95; pid.py:370-386, persisted in the `.aset`)
rather than two timed alarms — same gate, no missed-alarm P-only failure mode, no
sticky-`p-i-d()` trap, and worst error +2.95 instead of +5.79.

**Third, and this is the answer: give the outer loop a feedforward and make its
output a trim.** The root defect has been on the table since roast 40 — the
outer output is an *absolute* setpoint, so its integrator must supply the whole
operating point, which is why it ramps at 0.09 duty/s, why `e_ss` exists, why
`svLookahead` is needed, and why the handover value matters at all. Put the base
inlet trajectory (`ff(t) = bg(t+theta) + (dbg/dt - loss)/a`) on background event
playback on its own slider and make the PID drive a bounded `INLET TRIM` on
another — `specialeventplayback` is per event type (canvas.py:1848) and
`pidPositiveTarget` takes any of sliders 1-4 (pid_control.py:1252), so the
collision that forced playback off does not arise. Simulated: **`dI/dt` 0.09 ->
0.01**, `I@DROP` 63 -> 50, steady rms **0.11-0.14 degC** against 0.26-0.38,
`svLookahead` **0**, and with the gate the handover integrator (49.9) and
`dt150` (+1.6 s) are *identical at every charge state* — spreads 0.0 and 0.1.
Survives +-20% of error in the assumed plant gain. It needs one small firmware
command — **`INLET TRIM`, now folded into v0.19.0** so the outer-loop
instrumentation and the outer-loop restructuring land in one flash (spec in
state-history.md § Firmware now in scope; it is inert until Artisan is
reconfigured) — and **steps 3-5 first**, because the schedule is exactly `1/a`
and the loss curve. **The firmware half is written (2026-09-06) and v0.19.0 is
now complete and unflashed** — see the paragraph below. The Artisan half had a
gap that was not costed — `artisan/make_inlet_background.py` does **not** emit
the file step 9 needs, since its events mode blanks BT by construction — and
**that gap is now closed (2026-09-06)**: `tools/merge_inlet_base.py` merges the
base schedule into profile_003/004 rather than generating it, reading the plant
from `tools/analysis/plant_roast46.json` (written by `roast46_refit.py
--emit-plant`, so steps 3-5 land as a card refresh and nothing else changes). On
profile_003 it emits **7 events, base 199 → 256 degC, replay error 0.87 degC**,
passing BT/`timex`/`timeindex` through untouched. Implementation corrected four
things in the analysis: the playback name check is not *absent* but *broken*
(`str(bool)` is always truthy, canvas.py:6530/:6546) and so should not be relied
on; the `bg(t+theta)` lead reads into a recorded roast's **cooling phase**, not
merely off the end, so the window closes at DROP and the background is blended
into its terminal RoR fit; the residual has a ~0.5 degC floor from whole-degree
event quantisation; and **the default dip rule is not the one state-history.md §
Dip strategies simulated** — raw `ff` is -432 degC at CHARGE, the simulation
clipped it to the 120 floor, and the operator's choice is instead to
back-extrapolate the ramp to a near-flat 199 degC and leave the whole dip to the
trim (`--dip follow` reproduces the simulated variant). Closing that comparison,
and the `.aset` half (trim slider, `pidPositiveTarget`, per-event-type
playback), are what is left. state-plan.md § The base-curve authoring gap. Still
not on the critical path — there is no real `ff(t)` to author until steps 3-5
run, so the merged background is generated on demand rather than committed. That
is new **runbook step 9**, and it is why the characterisation runs have
recovered their priority. The relative-setpoint variant (`INLET = BT + trim`)
was tried and is **worse** for a principled reason: it turns the plant into an
integrator with 13.5 s of delay. Detail, the full table and the ruled-out list
are in state-plan.md § Ruled out; the sweep that produced them is in
state-history.md § Dip strategies.

**v0.19.0 is written, compile-verified and unflashed (2026-09-06).** Both items
are in: the `SV`/`HT` `getData` nodes (first item, done earlier) and now
**`INLET TRIM`** (second item). `INLET <degC>` becomes the *base* setpoint —
unchanged command, unchanged semantics — `INLET TRIM <degC>` sets a bounded
trim (+-80 degC), and the effective setpoint is
`clamp(base + trim, INLET_SV_MIN_C, INLET_SV_MAX_C)`. `inletSV` still means the
*effective* setpoint, so `controlStep()`, `feedforward()`, the OLED, the status
push and the `getData` `SV` node are untouched; `inletBase`/`inletTrim` sit
upstream of it and `inletEffectiveSV()` is the only place they are combined.
The trim is zeroed on `INLET OFF`, `INLET <= 0`, an inlet failsafe, entry to
`MODE_TUNE` and at boot, and in `MODE_INLET` a trim unrefreshed for 15 s ramps
to 0 at 2 degC/s (logged once) so a dead outer loop degrades to open-loop
feedforward rather than to no heat. Every form of `INLET TRIM` is `TIER_DRIVE`,
`INLET TRIM 0` included — removing a *negative* trim raises the setpoint.
Dashboard, README and the version history are updated. **It is inert until
Artisan is reconfigured**: nothing on the present cascade path changes when it
is flashed, and the Artisan side must not be built until steps 3-5 have measured
`1/a` and the loss curve. The acceptance list is a bench drill with the heater
cold — **state-plan.md § NEXT item 14, not yet run**; the branch is
compile-verified only.

**The run schedule is set and the Artisan side of v0.19.0 is now in the files
(2026-09-06).** The operator is about to start testing runs, so the remaining
runbook was collapsed onto the fewest sessions that keep every comparison to one
variable: **bench (flash + `INLET TRIM` drill) → roast 1 = step 6 → bench (step 8)
→ one session carrying steps 3-5 → desk work → roast 5 = step 9.** Five
recordings, two of them real coffee, two sacrificial, one with no beans. Two
orderings carry weight: step 6 must precede step 8 (its value is the one-variable
comparison against roast 46, which step 8 would break), and step 8 must precede
the characterisation runs (the fan is their subject). Flashing v0.19.0 first
confounds nothing — both items are inert on the present cascade path. Table and
rationale in state-plan.md § Runbook.

**Two config changes came out of that, and both are in the repo.** First, the
open question in state-history.md § Firmware now in scope — *"the device id is
not guessed here because a wrong one silently mis-maps a curve"* — is closed:
it is **113 = `WS_56`** (comm.py:491). It is appended as a **third** extra device,
so the virtual `Temp_Drive` (`Y3-Y2`) survives; the ws channel index comes from
the device *function*, not its position, and `WSread(0)` already fills every
channel from the one `getData` reply, so there is no extra traffic. All five
`.aset` files carry `extradevices = 112, 25, 113` with `SV`/`HT` named. Second,
the characterisation runs are **replayed rather than hand-driven**: new
`artisan/airRoaster_cascadePID_char.aset` (a key-override variant that
`tools/gen_pid_alarm_asets.py` now also generates) forces `pidOnCHARGE` off,
enables background event playback for event types 0 and 2 alone and disables both
alarms, so the test's inlet *and* fan schedules drive sliders 3 and 1 by
themselves. That removes hand-timing as a variable and rehearses the
per-event-type playback that step 9 depends on.

**Test B is merged into Test C, and the fan excitation moved inside the batch**
(operator decision 2026-09-06). Two loaded runs instead of three, but a
between-batch fan contrast at n=2 is also a *batch* contrast, and roast 46 is the
standing proof that batch differences are not small. `tools/gen_char_doublet.py`
extends the doublet to nine minutes — inlet doublet unchanged over 3:00-5:00, an
inlet hold from 5:20 that levels BT off near 185 degC, then a **fan square wave
over 6:00-9:00**, phase-reversed between the two files (`chardoublet_fan60.alog`
runs the ramp at 60, `..._fan68.alog` at 68, and both modulate 60/70 with
opposite phase). Every file opens at **fan 64 until 1:30** for circulation —
identical in both, so it differences out, and a step rather than a level, which
is excitation rather than a confound.

**The fan envelope is set by the beans at the bottom and by nothing at the top**
(operator, 2026-09-06). Below fan **55** the interlock clips the heat and the
inner loop stops holding the inlet (`IL_FAN_FULL_DFLT`, airRoaster.ino:111);
below **58-59** is unreachable in practice, and a *charge* will not circulate
below ~64. There is **no blow-out ceiling** — the concerns above the usual band
are moisture loss at higher Reynolds number and bed uniformity (chuffing drives
local circulations that short-cut the asymmetric expansion funnel), and the
operator's standing preference is the *minimum* airflow that sustains
circulation, for efficiency, untested against any alternative. So 70 for 60 s at
a time is acceptable, and the 60-vs-68 ramp bases put a first number on that open
question — **weigh in and out on both**. The plateau sits at **185 degC, below
first crack**, so the bean exotherm is not on top of the signal. The files' BT
column is a forward simulation of the plant card and is **identical for both**,
because the card has no fan term — which is exactly what the pair is for.

**Test A gains a fan sweep and now also serves step 8.** With no beans it has no
circulation floor and no ceiling, so `tools/gen_char_empty.py` crosses the
original inlet steps with **six fan levels from 58 to 80** on an offset grid (no
fan step within 30 s of an inlet step) and runs 17 minutes:
`artisan/charstep_empty_fan.alog`. Step 8's affine `feedforward()` currently
rests on five preheat fan steps spanning 0.81-1.11 %heat/unit; this is the same
regression with a real lever arm. It does not replace Test C — an empty chamber
measures the machine's heat demand against airflow, not the bean-bed loss term.
state-plan.md § Files for the characterisation runs.

**Canonical config is `artisan/airRoaster_cascadePID.aset`** (one file; the
brief `_edit` variant used while adding the alarms was folded back in and
removed), with background
**`artisan/profile_002.alog`**. It adds the auto-DROP alarm — `From DRY END,
offset 0, Source DeltaBT, below -25 -> DROP` — because Artisan's built-in
auto-DROP is gated on 7 minutes after CHARGE (canvas.py:5151) and these roasts
drop at 6:20-6:31, so no sensitivity setting can reach it. DROP matters beyond
bookkeeping: it drives `pidOffDROP` and the `INLET 0` button chain, so a missed
DROP leaves the heater running. `svLookahead` is now **0**, which also matters
more with `profile_002`: the background's DROP bounds the control window, and at
lookahead 20 the SV would have stopped updating at 6:31 against a 6:51 DROP.
See state-plan.md § Auto-DROP detection.

*Superseded:* `artisan/airRoaster_cascadePID.aset`, derived from
`artisan/airRoaster_inletPoints.aset` (the operator's live config saved
2026-09-02, which supersedes the repo's older `airRoaster.aset`; their
`[ArduinoPID]` and `[Sliders]` sections are byte-identical). 17 `[ArduinoPID]`
keys plus three playback keys changed, nothing else; both originals untouched.
Still to do: bench verification with the heater cold, then a first roast.

**Prior: Command authentication → v0.18.0** (merged to `main`). Connect-time
challenge–response sessions on the WebSocket: the device pushes a random
nonce to each new client ("auth" push); a client proves the shared `AUTH_KEY`
(secrets.h; absent/empty = feature entirely off) by returning
`AUTH HMAC-SHA256(key, nonce-hex)` and its connection is trusted until it
drops (5 fails burn the connection; each failure re-nonces). Tiered
enforcement `AUTH MODE OFF|CONFIG|FULL` (NVS "auth"; a keyed build's first
boot defaults to CONFIG — operator decision 2026-07-11): CONFIG gates
safety/config mutations while OT1/OT2/INLET stay open for direct Artisan;
FULL gates all mutations — Artisan then connects through
`tools/roaster_proxy.py` (localhost signing proxy: answers the challenge,
relays everything else; transparent pipe against a keyless device). The
always-open safe subset (operator requirement): reads plus `OT1 0`,
`INLET OFF`/`INLET 0`, `COOL ON`, `TUNE ABORT` — any device can stop the
roaster, never start it. `AUTH MODE` itself always requires auth; serial is
always trusted (physical access). Single gate at the top of
`processCommand()` via `cmdTier()`. Dashboard: key field (localStorage),
automatic challenge answering (Web Crypto), Auth panel. Compile-verified;
proxy validated end-to-end against a firmware-faithful fake device (correct
key / wrong key / keyless all behave); dashboard HMAC cross-checked against
a Python reference. On-roaster + live-Artisan drill: state-plan.md § NEXT
item 13. Design decisions (operator-confirmed 2026-07-10): session auth over
per-message HMAC; runtime tier; secrets.h key; python proxy. Key management
(`tools/auth_key.py`, stdlib-only; operator-confirmed 2026-07-11): secrets.h
is the single source of truth — `generate` writes a 64-hex CSPRNG key there
(refuses to replace without `--rotate`), the proxy parses it automatically,
`show` feeds the dashboard paste, `hmac <nonce>` supports manual testing;
rotation = generate --rotate + reflash (USB preferred — an OTA image carries
the key across the LAN in cleartext) + dashboard re-paste. The helper's `ota`
subcommand likewise generates a dedicated random OTA_PASS (2026-07-11): the
firmware's WIFI_PASS fallback means a device without one accepts firmware
pushes from anyone on the WLAN; verify.sh reads the value automatically, and
the first flash after a change must be USB. Deliberately deferred (see the
auth item in state-plan § Later for the record): signed images / Secure Boot
/ OTA arming.

**Prior: Ambient reporting → v0.17.0** (merged to `main`). The Artisan `getData`
response gains an `AT` node (°C): Artisan maps it to an extra WebSocket
channel and selects that channel in **Config › Device › Ambient** (tab), then
samples it at CHARGE into Roast Properties (README § Ambient temperature has
the click-path). Three sources via the new `AMB` command (`amb` push, NVS
namespace "amb", re-validated on load): **cold-start memory** (default) — a
once-per-boot capture that saves the BT RTD as ambient only when it agrees
with the MAX31855 cold junction within 8 °C, so a power cycle on a hot roaster
keeps the capture from the last genuinely cold boot; **cold junction** — live
`readInternal()`, now read every sensor poll (hold-last-good `cjTemp`) and
surfaced in telemetry (`cj`, plus `amb` = the reported value); **manual** —
`AMB <degC>` (also switches the source to manual). Dashboard: cold-junction
readout in Temperatures, new Ambient panel (source selector; manual entry
defaults to °F, converts to °C before sending — firmware and Artisan stay
°C-only). Deliberately separate from `FF AMB` (control-law parameter).
Compile-verified; dashboard checked in browser preview with simulated pushes;
on-roaster drill is state-plan.md § NEXT item 12.

**Prior: Cooldown guard → v0.16.0** (on `main`). Minimum fan-shutdown criteria,
per operator request: the fan may stop only once the inlet has stayed below
`COOL_FAN_OFF_C` (70 °C) for the release dwell (`coolDwellS`, default 30 s,
live-set via `COOL DWELL <1-3600>`, NVS) on fresh readings with heat off.
**First on-roaster run 2026-07-05**: deferral, hold, and auto-release all
worked, but the 30 s dwell released into soak-back and the guard re-enforced
twice (fan pulsed twice at ~17:36–17:38 on the log) — which is why the dwell
became adjustable; raise it until one release sticks. An `OT2` below
`coolFanMin` (default 50, live-set via `COOL MIN`, NVS namespace "cool") while
hot is *deferred* (fan held at `coolFanMin`, requested level auto-applies when
the criteria are met); a hot roaster with the fan below minimum gets airflow
forced back on autonomously (manual-mode requested heat zeroed so the raised fan
can't un-block interlock-capped heat). Stale-hot sensor keeps the fan running;
`COOL OFF` is the runtime-only operator escape (re-armed every boot). New `COOL`
command, `cool` push, status `cool` field, OLED row 7; OT2 refactored through
commit-on-ack `setFanLevel()`. Dashboard gains a Cooldown panel (arm/disarm,
fan-min read/set, hold-state line; prefilled from `COOL` on connect) and a
cooldown line in the Status panel. Compile-verified; dashboard checked in
browser preview with simulated pushes; on-roaster drill is state-plan.md § NEXT
item 11. README + state docs updated.

**Prior: INLET 0 semantics → v0.15.1** (on `main`). A follow-background test (2026-07-04 dashboard CSV)
ended with Artisan's SV slider at 0; the firmware clamped it to
`INLET_SV_MIN_C` (0 °C) and kept the loop "engaged" on an unreachable target —
P railed at about −280 with heat pinned at 0 for the whole cooldown.
`INLET <sv ≤ 0>` now means "no setpoint": drop to manual, heat 0 (cooldown
intent). `INLET OFF` unchanged (disengage, hold heat). New tool
`downsample_logs.py` (repo root) condenses .alog / dashboard-CSV / dashboard
txt logs into a compact summary for review, and mirrors the semantics (SV ≤ 0
blanked from series and tracking stats). Compile-verified; on-roaster check is
trivial: SV slider to 0 → mode `manual`, heat 0.

Otherwise **between efforts.** `feature/fan-restore` (v0.15.0, RTC no-init fan
shadow) was **validated on the roaster 2026-07-04** — fan running → OTA
update → fan kept spinning through the reboot with the UI in sync — and
fast-forwarded into `main`, which now holds v0.15.0. The full v0.12 → v0.15
development record (OTA updates, the v0.13 DimmerLink rework, the v0.14
closed-loop/feedforward fixes, the v0.15 fan-level shadow) is in
[state-archive.md](state-archive.md). Start the next effort on a fresh branch
off `main`.

Remaining known work: the unchecked on-roaster validation items in
[state-plan.md](state-plan.md) § NEXT (failsafe drills, WDT margin, RTD
fault-rate comparison, interlock persistence, OTA idle gate, WiFi
kill/restore) and the unscheduled ideas in its § Later / not scheduled.

**Key verified facts the work rests on** (traceable to datasheets, see archive):
- Adafruit_MAX31865 v1.6.2 `temperature()` is a blocking one-shot (~75 ms) that
  toggles VBIAS off after each read and clears the fault register — it defeats
  the firmware's continuous-mode design. Direct register access is confirmed
  viable: auto-convert mode (config `VBIAS|AUTO` = 0xC0) converts continuously
  at the notch rate with VBIAS held on; RTD MSB+LSB read atomically (multibyte
  read from 0x01, SPI mode 1, 1 MHz); LSB bit D0 is a per-sample fault flag;
  fault thresholds (03h–06h, RTD-register format = 15-bit ratio << 1) are
  compared on every conversion; latched faults at 07h clear via config D1 with
  D5/D3/D2 = 0.
- MAX31855 free-runs conversions (70–100 ms) and updates while CS is high — the
  existing library path is already non-blocking; keep it. `readInternal()`
  (cold junction, 0.0625 °C) is available as an ambient estimate.
- After an MCU-only reset the DimmerLink modules are assumed to hold their last
  levels (power-on default is undocumented) — boot must force heat to 0 and
  restore the fan level. DimmerLink register reads (incl. `getLevel()`) lie
  while a module is firing (v0.13 finding), so the fan level is recovered from
  the RTC no-init shadow (v0.15), never from readback.
