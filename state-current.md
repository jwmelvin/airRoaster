# state-current — what is being worked on right now

> One of three state documents. **This file**: the active effort and where it
> stands. [state-plan.md](state-plan.md): planned phases and their full specs.
> [state-archive.md](state-archive.md): completed work, review findings, and
> decided-and-done rationale. Update discipline: when a phase completes, move
> its detail from *plan* to *archive* and re-point this file at the next phase.

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
working branch is **`feature/artisan-pid`** (Artisan configuration + docs only
— no firmware change). Note that `feature/vision-uvc-probe` holds two commits
that exist on no other branch and have never been pushed. Start each new effort
on a fresh branch off `main`. Commit per phase with
a message naming the phase. The user's Artisan config churn (`artisan/*.aset`,
`*.alog`) may be present in the working tree — never sweep it into a firmware
commit; stage files explicitly.

## Active effort (2026-09-05)

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
has no term for. New gains: Kp 3.0, Ki 0.04, floor 140 degC, `svLookahead` 20 s. Detail and the caveats are in
state-plan.md § Roast 40.

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

**That procedure** forced the floor back down to
140 (the loop needs inlet ~148 to hold 129.4 degC, which a 170 floor forbids)
and Ki up to 0.04 (a correctly-started integrator sits at the empty-roaster
operating point ~5 duty and must climb to ~55 during the roast). SV also sat at its 120 degC floor for 19 s
during the charge dip — with the range limit unchecked that would have been
`INLET 0` and a heat kill mid-roast, so the floor is doing real work. Detail in
state-plan.md § Roast 41.

**Roast 42 (2026-09-02, retuned config + PID-driven preheat): the cascade
works.** Outer integrator settles at 53-65 and stays, carrying the operating
point while P trims within +/-5 duty; tracking error +1.6 ... -0.9 degC from
3:00 on; inner loop rms 2.9 degC; heat never saturated (max 91%); SV touched the
140 floor for 8 s in the charge dip and never approached the ceiling. The
PID-driven preheat landed at CHARGE_BT 129.7 against a 129.4 target. The one
remaining offset is `svLookahead=20`, which makes the roast run 20 s ahead by
construction (DRYe 2:36 vs 3:00) — a spec error, not tuning; it should come down
to ~0 now that the cascade is known to be tight. Detail in state-plan.md
§ Roast 42.

**Roast 44 (2026-09-02) is the clean validation run and the cascade is
functionally complete.** Config loaded from file, PID-driven preheat, no
intervention: CHARGE_BT 128.3 against a 127.8 target, DRYe 3:23 vs the
profile's 3:20, DROP 7:03 vs 6:51 at BT 200.7 vs 201.2, tracking error
converging +4.0 -> +1.7 degC. The auto-DROP alarm fired (operator-confirmed in
roast 43; roast 44 shows the same signature). Control settings verified
field-by-field against the PID dialog. Detail in state-plan.md § Roast 44.

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
retracted is that it shapes roast 45's error trace. Detail in state-plan.md
§ Correction: roast 45's error is the loop, not the air.

**A source mechanism the earlier notes missed underpins all of it**:
`_back_calculate_integral` (pid.py:314-333) runs on every clamped cycle whenever
`pidIWP` is on, and at the *low* clamp it drives `Iterm` **up**, converging
geometrically (half per second) on `Kp*|err|`. So the charge dip re-seeds the
integrator to `Kp * |worst dip error|` (roast 44: 3 x 8.4 = 25 against a measured
24.6), whatever the preheat left is forgotten within seconds of the floor, and
**raising Ki costs nothing on the charge transient** — the dip runs on a path
with no Ki in it. The same mechanism is why `svLookahead` cannot go to the
"natural" 12 s: the background falls at 5.5 degC/s through the dip, so each
second of lead adds ~4 degC to the dip error and hence to the preload, and past
`L=4` the roast starts wound up and overshoots by 5-20 degC in the first two
minutes. The DROP-window truncation the handoff worried about is the *lesser*
constraint. Full analysis, the option-by-option review of Artisan's other
control modes (gain scheduling, beta/gamma, Dlimit, IRoC, ILF, Ramp/Soak,
sv/duty filters, BT-RoR control) and the single-roast validation checklist are
in state-plan.md § Roast 44 outer-loop analysis.

**Roast 46 (2026-09-05, 400 g) is runbook step 1, and it passes.** Config
unmodified (Kp 3.0, **Ki 0.07**, Kd 0, `svLookahead` 3, floor 140), background
profile_003, PID-driven preheat, no intervention, **fan held constant at 60 for
the whole roast** so nothing in the trace is air-schedule disturbance. Five of
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

Second, **check 5 failed and the cause is batch size, not the loop**: profile_003's
TP is matched to roast 45 at 345 g, roast 46 was 400 g and bottomed 9.8 degC
deeper and 16 s earlier, exactly as § profile_003 predicted. That manufactured a
30.5 degC error swing in the first twenty seconds, drove SV rail-to-rail
(261 -> the 140 floor), put 11 s on the floor, and re-seeded `Iterm` to ~30 by
back-calculation — after which BT overshot the background by 9.3 degC at 1:00 and
sat 4.0 degC behind at 2:00. The fix is **profile_004**, a 400 g dip spliced onto
profile_003's unchanged ramp (new runbook step 1b).

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

Detail in state-plan.md § Roast 46.

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

**Prior: Cooldown guard → v0.16.0** (on `main`). Minimum fan-shutdown
criteria, per operator request: the fan may stop only once the inlet has
stayed below `COOL_FAN_OFF_C` (70 °C) for the release dwell (`coolDwellS`,
default 30 s, live-set via `COOL DWELL <1-3600>`, NVS) on fresh
readings with heat off. **First on-roaster run 2026-07-05**: deferral, hold,
and auto-release all worked, but the 30 s dwell released into soak-back and
the guard re-enforced twice (fan pulsed twice at ~17:36–17:38 on the log) —
which is why the dwell became adjustable; raise it until one release sticks. An `OT2` below `coolFanMin` (default 50, live-set via
`COOL MIN`, NVS namespace "cool") while hot is *deferred* (fan
held at `coolFanMin`, requested level auto-applies when the criteria are met);
a hot roaster with the fan below minimum gets airflow forced back on
autonomously (manual-mode requested heat zeroed so the raised fan can't
un-block interlock-capped heat). Stale-hot sensor keeps the fan running;
`COOL OFF` is the runtime-only operator escape (re-armed every boot). New
`COOL` command, `cool` push, status `cool` field, OLED row 7; OT2 refactored
through commit-on-ack `setFanLevel()`. Dashboard gains a Cooldown panel
(arm/disarm, fan-min read/set, hold-state line; prefilled from `COOL` on
connect) and a cooldown line in the Status panel. Compile-verified; dashboard
checked in browser preview with simulated pushes; on-roaster drill is
state-plan.md § NEXT item 11. README + state docs updated.

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
kill/restore) and the unscheduled ideas in § Later / not scheduled.

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
