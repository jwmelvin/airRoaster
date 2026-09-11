# state-history-charge — the charge state, the dip model, and authoring the background

> **Effort:** once the controller stopped being the limiting error, the remaining
> error was in the *reference*. This file is the work that measured the charge
> state, modelled the charge dip, and moved the background from Artisan's
> Designer to a generated curve. **The charge-thermal test and roasts 50-56,
> 2026-09-06 to 2026-09-07.** Closed: `k = 0.1056` measured over a 37 degC span,
> `h_fus` under ~1 J/g, the dip model jointly refitted, the SV floor at 100, and
> a background that passes all four checks.
>
> One of three history files. [state-history-cascade.md](state-history-cascade.md)
> is the controller work this follows.
> [state-history-residual.md](state-history-residual.md) takes up where this
> leaves off — the −2.9 degC residual roast 56 exposed. The index is
> [state-history.md](state-history.md); what is *current* is
> [state-current.md](state-current.md) and [state-plan.md](state-plan.md).
>
> **Read it in order, oldest first.** A finding here is current only if nothing
> below it says otherwise.

## Contents

- The charge-thermal test — what a still-air probe cannot see
- Roasts 50 and 51 — the charge-temperature pair, `greens_temp` finally measured
- Roast 52 — the first generated background, and the pre-CHARGE frozen target
- Roast 53 — the gate never existed, and the kick is the lookahead
- Roast 54 — the gate held, and the free dip is finally measured
- The dip model's joint refit — a pour ramp and a scale error
- Designing roast 55 — the TP trigger, and the blend that had to shorten
- The SV floor, and why it should have come down four roasts ago
- Authoring the background outright — RoR as the specification
- Roast 55 — the floor was the constraint, and all four checks pass
- The alarm table drifts from the .aset, and RESET is not the cause
- Roast 56 — the lookahead switch works, and the residual moves to the drying ramp

## The record

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

### Authoring the background outright (2026-09-07) — RoR as the specification

Operator: *"I prefer that background profiles have a smooth shape. This work
accommodating the dip is disrupting that... There's nothing really special about
the Artisan designer."*

Both halves are right. The merge in `make_charge_background.py` has a defect no
choice of blend window removes: the merged curve sits below its source, has to
climb back onto it, and then stops climbing. `profile_400g_m12C_v2.alog` runs
**38 → 43 → 41 → 25 degC/min across 60-150 s** — a bulge and then a cliff, in
exactly the window where the loop is still recovering from the charge. And the
Designer contributes nothing here except the file's metadata.

**`tools/make_background.py` authors the whole curve from a RoR specification**,
with the same division of labour drawn in the right place:

    0 .. TP      the dip.  Physics (charge_dip, inlet held at the preheat).
    TP .. DROP   the design.  RoR(u) integrated to BT.

    RoR(u) = (1 - exp(-u/tau_r)) * (R_inf + (R0 - R_inf) exp(-u/tau_d))
    u = t - t_TP,   BT(t) = BT_TP + integral of RoR/60

Because **BT is the integral of the spec**, the RoR is smooth by construction
rather than being whatever differentiating a hand-drawn curve gives. **The join
needs no blend window at all**: the dip arrives at its minimum with RoR 0 by
definition and the spec leaves it at RoR 0, so BT is C1 at the turning point.
The `(1 - exp(-u/tau_r))` factor is the rise off the TP; the bracket is the
decline. Three free parameters against three marks, so the marks are *hit*.

#### A linear RoR decline cannot hit the marks, and that is a finding

The operator asked for "generally a linear shape to the RoR decline". Fitted to
`profile_003`'s own marks — DRY END 3:12 at 149.6, FCs 6:39 at 197.5, DROP 7:05
at 201.4:

| decline | DRY END / FCs / DROP error | peak RoR | RoR at DROP |
|---|---|---|---|
| linear | −0.0 / **+1.9** / **−1.9** degC | 42.0 at 88 s | **0.0** |
| quadratic | +3.7 / +1.7 / −2.2 degC | 43.4 at 96 s | **0.0** (flat from 360 s) |
| **exponential** | **−0.0 / +0.0 / −0.0** | 48.1 at 65 s | **8.7** |

A roast's RoR decline is convex — fast early, long slow tail — so a straight line
through it either runs hot in the middle or runs out of rate before DROP. Asked
to hit these three marks the linear fit reaches **zero RoR exactly at DROP**,
which is not a roast, and still misses FCs by 2 degC. `--decline linear` is kept
in the tool so this stays visible; `exp` is the default.

#### What v3 is, and what it costs

| | v2 (merged) | **v3 (authored)** |
|---|---|---|
| worst gap over roast 54's 30 s free window | 2.92 | 3.01 degC |
| error at the CHARGE+15 s alarm | +2.1 | +2.1 degC |
| peak RoR asked | 56 | **48.1** degC/min |
| RoR monotone after its peak | **no** | **yes** |
| largest sample-to-sample RoR step past 35 s | 4.44 | **2.73** degC/min |
| marks | inherited | **hit to 0.00 degC** |

The dip is untouched — that is the point of drawing the line at the TP. v3 runs
cooler than v2 through the recovery (72.2 vs 75.4 at 60 s, 115.5 vs 117.3 at
120 s), converging by 180 s and identical at the marks. Its peak RoR of 48.1 is
inside what roast 54 delivered (72) and in line with the 45-48 the bed actually
ran at 40-60 s, but **it is a lower absolute target than roast 54's bed reached**,
which is precisely what the lowered SV floor exists to make survivable.

`make_charge_background.py` is superseded but kept: it is the curve v2 came from
and the record of the merge approach.

### Roast 55 (2026-09-07, 21:37) — the floor was the constraint, and all four checks pass

400 g of the same lot at `greens_temp = -12.0`, `airRoaster_cascadePID_floor100.aset`
(`pidKp` 2.4, `pidKi` 0.056, `positiveTargetMin` 100) against
`profile_400g_m12C_v3.alog`. Two changes from roast 54 — the authored background
and the lowered SV floor — acting in disjoint regions as planned.

| check | roast 52 | roast 53 | roast 54 | **roast 55** | pass |
|---|---|---|---|---|---|
| peak SV, first minute | 275 | 238 | 193 | **154** | under ~200 — **pass** |
| seconds of heat at 100% | 23.5 | 14.0 | 2.0 | **1.0** | 0 — **near** |
| seconds **saturated** at own floor | 42.0 | 46.9 | 40.0 | **0.0** | under ~10 — **pass** |
| worst BT error vs background, 30-90 s | +21.3 | +14.1 | +5.5 | **−4.9** | single digits — **pass** |
| worst \|bkg − BT\| over 0-30 s | — | — | 8.6 | **3.9** | — |

Tracking rms by window, against each roast's own background:

| roast | 30-90 s | 90-DROP | 120-DROP | peak SV | min SV |
|---|---|---|---|---|---|
| 51 | 11.71 | 1.09 | — | 300 | 140 |
| 53 | 11.60 | 1.35 | — | 238 | 140 |
| 54 | 3.88 | 0.68 | — | 193 | 140 |
| **55** | **2.70** | 1.50 | **0.79** | **154** | **122** |

**The floor was the binding constraint, and this settles it.** The loop spent
**41.5 s below the old 140 clamp**, bottoming at **SV 122** from 31.5 to 72.5 s —
using 18 degC of range that did not exist on roasts 51-54 — and **never saturated
at all**. Where roast 54 sat 40 s pinned at 140 with the heater at 46% and a bed
it could not pull down, roast 55 regulated through the whole recovery. The count
at `SV <= 141.5` is still 44.5 s, but that number no longer means saturation: it
is the loop working in the band it now has.

`SV` never approached the new 100 floor, so **100 was deep enough** and the 80
fallback is not needed.

**The gate held.** `T_inlet` carries only the known duplicate at +1.0 s and then
nothing until the PID ON alarm at +15.5 s; the inlet sat at 144.8-146.0 and SV at
145 throughout. Free dip measured **TP 55.6 degC at 27.0 s** against v3's 55.1 at
29.0 s — depth right to 0.5 degC, phase 2 s.

**And the dip model's "6 s phase error" is smaller than the roast-to-roast
scatter.** Roasts 54 and 55 are nominally identical and turned at **23.0 s and
27.0 s** — at *exactly* the same depth, 55.6 degC both times. The depth is
strikingly repeatable; the timing is not. § The dip model's joint refit records
the ~6 s lateness as the model's one remaining defect. It is at most half that,
and it is inside the scatter of the measurement it was scored against.

**The PID port reproduces roast 55 to rms 1.70 degC of SV** over 30-180 s — but
only when the integrator is seeded at `iterm0 = 21.3`. Started at zero it is out
by rms 22.7 and commands the floor. That is a direct confirmation of the floor
change's arithmetic: § The SV floor predicted the preheat would have to build
`Iterm` to **20.2** to hold SV 140.4 under the new mapping, and the roast says
21.3. **Any future replay of a lowered-floor roast must seed the integrator.**

#### The one new artifact: a single overcorrection at 40-95 s

| window | 30-60 s | 60-95 s | 95-120 s | 120-DROP |
|---|---|---|---|---|
| rms | 2.49 | 3.29 | 4.10 | **0.79** |
| worst | +3.3 | −5.3 | −5.3 | −2.3 |

The bed ran **+3.3 above** the background at 40-50 s, the loop pulled SV to 122,
and that correction landed 13.5 s later — right when v3 demands its peak RoR
(47.7 degC/min at 60 s). The bed then fell **−4.9 behind** by 90 s, and the one
sample of 100% heat is at 92.0 s recovering from it. From 120 s to DROP the
tracking is the best in the series at rms 0.79.

So the sign flipped and the magnitude fell (+5.5 → −4.9), but the loop now
oscillates once where it used to saturate once. **This is a deadtime problem, not
a gain problem**: `svLookahead` is 0 until 90 s — chosen when the dip was a mess
and the loop had to be stopped from chasing a falling target — so through the
whole steep recovery the loop is tracking a target 13.5 s stale.

Replaying roast 55's measured BT through the port with the integrator seeded
(the validated configuration above):

| t (s) | 50 | 60 | 75 | 90 | 105 |
|---|---|---|---|---|---|
| measured SV | 122 | 126 | 142 | 160 | 192 |
| LA 6 from 90 s (as run) | 121 | 124 | 141 | 159 | 191 |
| **LA 6 from 45 s** | **143** | **155** | **180** | **202** | 214 |
| LA 6 from 30 s | 148 | 159 | 184 | 207 | 219 |

Six seconds of lookahead is worth 4.8 degC of target at 60 s, against a 4.9 degC
undershoot. Switching at **45 s** leaves the 40 s correction intact (127 either
way) and only starts anticipating after it; switching at 30 s fights the +3.3
overshoot instead. **Caveat: `replay_pid` is fed measured BT, so it says what the
controller would have commanded, not what BT would have resulted.**

#### First crack is hotter than the background assumes, and that is the stretch

Operator: *"The FC for this coffee seems to be a bit higher than our model, which
stretches out the overall roast (I usually go by time past FC)."* Correct, and
the arithmetic closes exactly.

| roast | 50 | 51 | 52 | 53 | 54 | 55 | mean | v3 |
|---|---|---|---|---|---|---|---|---|
| FCs BT | 201.2 | 198.1 | 200.1 | 197.4 | 197.3 | 198.7 | **198.8** | **197.5** |
| RoR at FCs (slope over ±15 s) | 8.3 | 9.8 | 7.6 | 8.8 | 8.9 | 6.2 | **8.3** | 9.3 |
| DROP − FCs | 26.0 | 35.5 | 25.0 | 31.5 | 29.0 | 23.0 | **28.3** | 26 |

`profile_003`'s 197.5 sits at the **bottom** of the range. A mark 1.3 degC low,
at the 8.3 degC/min the roasts actually run through FC, is **9.4 s** — and roast
55's FCs landed at **408 s against the background's 399**. The lag is the mark,
not the loop.

**`make_background.py` gains a `--development` mode**, which is how the operator
roasts: FCs is a *temperature the coffee decides* and DROP is a *time past it*.
It replaces the pinned DROP temperature with `--ror-at-fcs` as the third
constraint, so the three fitted are `BT(DRY END)`, `BT(FCs)` and `RoR(FCs)`, and
DROP is placed at `FCs + --development` with whatever temperature follows.

`artisan/profile_400g_m12C_v4.alog`: FCs 6:39 at **198.8**, RoR at FCs 8.3, DROP
28 s later at 7:07 / 202.5. All three constraints hit to 0.00, RoR monotone from
its 46.3 peak, dip identical to v3 (3.94 degC worst against roast 55 either way).

### The alarm table drifts from the .aset, and RESET is not the cause (2026-09-07)

Preparing roast 56, the operator reported that after loading
`airRoaster_cascadePID_floor100.aset` the `LA 6` alarm showed **00:30** while the
file carried **90**. Every other row matched the file exactly (16:00 = 960,
02:00 = 120, 00:15 = 15), so the `mm:ss` decoding was not the issue — and an
initial reading of it as "01:30 misread as :30" was **wrong**; the screenshot
showed 00:30.

**Not RESET.** `QMC.reset()` touches only `alarmstate` (the triggered flags) and
`TPalarmtimeindex`, so a new TP is recognised each roast. It never rewrites
`alarmoffset`.

**`savealarms()` is the mechanism** (alarms.py:730-776, called from
`closeEvent`). It writes *every* row back into `qmc.alarm*` from the dialog's
widgets. Load an `.aset` while the Alarms dialog is open and the load updates
Artisan's internal state; closing the dialog then overwrites it from the stale
widgets. Artisan saves settings on quit, so a wrong value persists in the
operator's own settings independently of the repo file. (`selectAlarmSet`,
canvas.py:6067+, replaces the whole table wholesale, but the `alarmsets` slots in
these files are empty, and an empty set would give zero rows rather than seven.)

**What actually ran is recoverable from the log, and the `.alog` cannot tell
you** — it records `svLookahead` at *save* time, which is only the post-switch
value (roast 55 says 6). The switch instant shows as a **step in SV**, because
six seconds of lookahead adds `RoR x 6` degC of target, and `dSV/derror = 4.8`:

| | roast 54 | roast 55 |
|---|---|---|
| SV step at 91.0 s | **20.2** | **20.3** degC |
| predicted (`RoR x 6 x 4.8`) | 20.8 | 20.9 |
| SV step at 30 s | −0.2 | 0.0 |
| predicted if it had switched at 30 s | 2.7 | 2.9 |

So both roasts switched at **90 s**, as their `.aset` said, and neither switched
at 30 s. § Roast 55's deadtime analysis stands.

**Consequences, both now in the roast-56 handoff**: the seven-row alarm table is
written out in state-current.md and must be checked in the dialog before every
roast, and the SV-step arithmetic is the only reliable after-the-fact check of
when the lookahead actually switched.

Two related exposures worth knowing about, both currently inert. The generated
backgrounds inherit `profile_003`'s embedded `alarm*` **and** PID keys
(`pidKp` 3.0, `pidKi` 0.07, `svLookahead` 3), and `main.py:14500-14509` will load
alarms, ramp/soak and PID settings *from a background* if the corresponding flags
are set. All three are `false` in these `.aset` files
(`loadAlarmsFromBackground`, `loadRampSoakFromBackground`, `loadpidfrombackground`),
so nothing is applied today — but turning any of them on would silently restore
the pre-floor-change gains from a background file.

### Roast 56 (2026-09-07, 22:27) — the lookahead switch works, and the residual moves to the drying ramp

400 g, `airRoaster_cascadePID_floor100.aset` (`pidKp` 2.4, `pidKi` 0.056,
`positiveTargetMin` 100) against `artisan/profile_400g_m5C_v4.alog`.
**`moisture_greens` is finally entered — 11.0**, ending four roasts of 0.0.

**Not the same lot as roast 55, and not a new coffee either.** The Kenya ran out
and the operator switched to `C1043`, *Ethiopia, Crown Jewel Sidama Daye Bensa
Washed* — the coffee roasts 43-49 ran on. Roasts 50-52 were `C1074` (Colombia)
and 53-55 `C1062` (Kenya). This was read out of the logs on 2026-09-08 and it
invalidates the FC arithmetic below; see § The FC temperature is a property of
the lot.

**Three things changed from roast 55, not two.** The planned pair were the FC
mark (197.5 → 198.8) and the lookahead switch (CHARGE+90 → +45). The third was
not in the plan: the charge was **`greens_temp = -5.0`**, not the freezer's
−12.0, so the background actually loaded was `profile_400g_m5C_v4.alog`
(`backgroundpath` confirms it). That is legitimate — the handoff anticipated
either — and it is confined to the dip: the two v4 backgrounds differ by at most
**6.96 degC at 57 s** and are within **0.4 degC everywhere after 130 s**. It does
mean the 0-120 s region carries two changes at once, and § the dip below is
scored against a charge temperature the dip model has never been calibrated at.

| check | roast 53 | roast 54 | roast 55 | **roast 56** | pass |
|---|---|---|---|---|---|
| peak SV, first minute | 238 | 193 | 154 | **165** | under ~200 — **pass** |
| seconds of heat at 100% | 14.0 | 2.0 | 1.0 | **1.0** | 0 — **near** |
| seconds **saturated** at own floor | 46.9 | 40.0 | 0.0 | **0.0** | under ~10 — **pass** |
| worst BT error vs background, 30-90 s | +14.1 | +5.5 | −4.9 | **+2.2** | single digits — **pass** |
| worst \|bkg − BT\| over 0-30 s | — | 8.6 | 3.9 | **3.7** | — |

Tracking rms by window, each roast against its own background:

| roast | 0-30 | 30-60 | 30-90 | 60-95 | 95-120 | 120-DROP | 0-DROP | peak SV | min SV |
|---|---|---|---|---|---|---|---|---|---|
| 54 | — | — | 3.88 | — | — | — | — | 193 | 140 |
| 55 | 1.52 | 2.49 | **2.70** | 3.29 | 4.10 | **0.79** | 1.71 | 154 | 122 |
| **56** | **2.00** | **1.21** | **0.94** | **0.58** | **0.41** | **1.28** | **1.26** | **165** | **128** |

**All four checks pass, and 30-90 s is now better than roast 55 by a factor of
three.** The old `SV <= 141.5` count — kept only for series comparability, since
the floor is 100 and saturation is `SV <= 101.5` — is **26.1 s**, down from
roast 55's 45.5; the loop bottomed at **SV 128.2 at 37.0 s** and spent 22.9 s
below 140 (23.1 to 46.0 s). Seconds at the actual floor: **0.0**. Inner loop
`Inlet − SV` rms **0.91 degC from 50 s to DROP**.

#### Change 2 fired, and the SV-step check says so unambiguously

The `.aset` carries `alarmoffset` row 4 = 45, and the log confirms it happened:

| | at 30 s | at 46.3 s | at 91 s |
|---|---|---|---|
| measured SV step | −3.02 | **+24.25** | **0.00** |
| predicted if the switch were here (`(bkg(t+6) − bkg(t)) x 4.8`) | +9.3 | **+21.4** | +18.0 |

SV goes **132.0 → 154.7 between 46.03 and 46.55 s** and is flat across 90-94.5 s.
The alarm is at 45 s and the step lands 1.3-1.5 s later, the same tick latency the
`PID ON` alarm shows (15 s → 15.5 s). **The alarm table did not drift this
roast.**

The PID port agrees independently. Replaying measured BT with the integrator
seeded, the best fit is `iterm0 = 18.63`, **rms 1.97 degC of SV over 30-180 s**,
and the switch instant is sharply identified:

| assumed switch | 30 s | **46.3 s** | 60 s | 91 s | never |
|---|---|---|---|---|---|
| rms vs measured SV, 30-180 s | 8.94 | **1.97** | 9.68 | 23.20 | 42.83 |

`iterm0 = 18.63` against roast 55's 21.3 — the same operating point, and the
lowered-floor seeding rule holds again (at `iterm0 = 0` the replay is out by
rms 26.15).

#### The 60-95 s undershoot is gone, and no overshoot replaced it

| window | 30-60 s | 40-60 s | 60-95 s | 95-120 s |
|---|---|---|---|---|
| roast 55 worst | +3.25 | +3.25 | **−5.33** | −5.29 |
| **roast 56 worst** | **+2.17** | **−1.24** | **−1.13** | **+0.91** |

That was the whole point of moving the switch to 45 s: leave the 40 s correction
intact and only anticipate after it. It did exactly that — the worst error in
40-60 s is −1.24, so the feared 40-60 s overshoot **did not appear**, and the
60 s intermediate the handoff held in reserve is not needed.

**The one 100% heat sample is the step, not the authority.** Both 100% samples
are at 46.5 and 47.1 s, i.e. the inner loop servicing the +22.7 degC SV step: it
took `Inlet` from 131.9 to 162.9 in two seconds and then tracked. Heat never
reached 100% again, never reached 0, and `Inlet − SV` rms from 50 s to DROP is
0.91.

#### Change 1 is neither confirmed nor falsified — because the crack moved

> **Superseded 2026-09-08.** The table below pools three different coffees and
> its 198.8 "mean" describes none of them. The finding that survives is the
> first sentence — the loop delivered the curve — not the arithmetic. See § The
> FC temperature is a property of the lot.

The loop delivered the authored curve almost exactly through the back half:
|error| **under 0.5 degC from 250 s to DROP**, and **+0.33 degC at the FCs mark
itself**. So the roast did not stretch: BT is on the background. What moved is
the coffee.

| roast | 50 | 51 | 52 | 53 | 54 | 55 | **56** | mean 50-55 | v4 mark |
|---|---|---|---|---|---|---|---|---|---|
| FCs BT | 201.2 | 198.1 | 200.1 | 197.4 | 197.3 | 198.7 | **195.3** | 198.8 | **198.8** |
| FCs t | 419 | 400 | 409 | 397 | 395 | 408 | **373** | | 399 |
| DROP − FCs | 26.0 | 35.5 | 25.0 | 31.5 | 29.0 | 23.0 | **19.0** | 28.3 | 28 |

FCs was marked at **195.3 degC**, **2.0 degC below the previous minimum of the
six** and 3.5 below the mean the mark was set to, so it landed **26 s early**
against a correction that predicted ~399 s. The background reaches 195.3 at
375.1 s and the roast reached it at 372.5 — 2.6 s early, which is the whole of
the timing difference. **The mark is now doing its job and the residual is bean
variance (or mark subjectivity), not loop lag.** One sample does not justify
moving 198.8 again; including roast 56 the mean is 198.3.

DROP followed 19 s after FCs rather than the 28 the background specifies, so the
roast ended at 392 s / BT 197.9 against the background's 427 s / 202.4. That is
the operator's call at the machine, not a tracking failure.

#### The new residual: a ramp-following lag at 140-200 s

| t (s) | 120 | 140 | 160 | 165 | 180 | 200 | 220 | 250 |
|---|---|---|---|---|---|---|---|---|
| roast 54 err | −1.72 | −1.68 | −0.30 | — | +0.45 | +0.17 | −0.26 | — |
| roast 55 err | −2.30 | −0.99 | −1.14 | — | −1.48 | −1.20 | −0.77 | −0.05 |
| **roast 56 err** | **−0.08** | −1.30 | −2.60 | **−2.91** | −2.60 | −2.18 | −1.12 | −0.41 |

Roast 56 enters 120 s dead on the curve and then **diverges to −2.91 degC by
165 s** before recovering. This is the one place roast 56 is worse than roast 55
(120-DROP rms 1.28 vs 0.79), and it is not the background: v3 and v4 agree to
0.35 degC and their RoRs to 1.5 degC/min across 140-220 s.

It is the **integrator's fill rate against the drying ramp**. Backing the terms
out of the recorded SV — `output = (SV − 100)/2` under the 100/300 mapping,
`Iterm = output − Kp x (bkg(t + LA) − BT)`:

| t (s) | 90 | 105 | 120 | 140 | 160 | 180 | 200 | 240 |
|---|---|---|---|---|---|---|---|---|
| roast 55 `Iterm` | 18.2 | 26.1 | 32.1 | 36.7 | 40.9 | 44.6 | 48.7 | 54.3 |
| **roast 56 `Iterm`** | 25.8 | 27.9 | 29.8 | 32.6 | 37.7 | 43.7 | 48.1 | 54.5 |

Roast 55 arrived at 140 s carrying **4 more duty** (8 degC of SV) than roast 56,
because it had spent 90-120 s digging out of a 5 degC undershoot and the large
error pumped the integrator. Roast 56 never had that error, so its integrator
climbed only at `Ki x err` — and the background's demand through 130-200 s
outruns it. **Fixing the 60-95 s undershoot removed the very error that was
pre-charging the integrator for the drying ramp.**

The size is a phase, not a gain: −2.6 degC where the background runs
25-27 degC/min is **~6 s of lag** — the residual of a 13.5 s apparent plant lag
against 6 s of lookahead. Two candidate fixes, neither yet run:

- **more lookahead in that region only** (`LA 12` from ~120 s), which is 6 s of
  phase exactly where it is missing and worth only 2 degC of target by 300 s
  where RoR has fallen to 10 degC/min. There is **no `LA 12` button** in the
  `.aset` today — `extraeventslabels` has `LA 0` (button 20) and `LA 6`
  (button 21) only, so this needs a new button `pidLookahead(12)` and an eighth
  alarm row.
- **more `Ki`**, which fills the integrator faster everywhere, including the dip.

`replay_pid` **cannot size either of these.** It is fed measured BT, so a
sustained change in lookahead shows up as a permanent P offset that the real
loop would erase as BT caught up: it reports `LA 12` from 120 s commanding
SV 278 at 300 s, which is not a prediction, it is the artifact. The phase
arithmetic above is the honest sizing.

#### The gate, the dip, and the turning point

**The gate held.** `T_inlet` carries the two preheat entries at −16 and −14 s,
the known duplicate at **+1.0 s**, and then **nothing until 15.5 s**, the `PID
ON` alarm. Preheat equilibrium was `Inlet` 141.8 / `SV` 141.9 / `Temp_Drive`
11.6 / heat 45.8%, and CHARGE BT was **130.20**, the background's value to the
hundredth.

The loop-free window is **30.5 s**, the longest in the series. Free turning
point **61.1 degC at 27.5 s** against the background's **59.2 at 29.0 s** —
1.9 degC shallow, 1.5 s early.

**This is the dip model's first −5 degC point, and it is its worst fit.** Scoring
all six recorded-temperature roasts against the shipped calibration
(`phi(400 g) = 0.7116`, `tau_mix = 10.84`, `w_c = 2.10`, fitted to 50/51/53/54):

| roast | T_bean | window | drop meas / pred | rms | worst | TP meas / pred |
|---|---|---|---|---|---|---|
| 50 | +25.0 | 15.0 s | 44.30 / 44.01 | 1.18 | 3.11 | 83.5@15.0 / 83.5@15.0 |
| 51 | −12.0 | 16.0 s | 60.30 / 61.95 | 1.41 | 2.68 | 66.7@16.0 / 64.0@16.0 |
| 53 | −12.0 | 18.5 s | 61.40 / 61.53 | 1.15 | 2.63 | 63.1@18.5 / 60.5@18.5 |
| 54 | −12.0 | 30.0 s | 63.00 / 61.09 | 1.41 | 2.25 | 55.6@23.0 / 55.3@28.5 |
| 55 | −12.0 | 30.0 s | 62.20 / 61.56 | 1.36 | 3.47 | 55.6@27.0 / 55.8@28.5 |
| **56** | **−5.0** | **30.5 s** | **56.60 / 58.13** | **1.92** | **3.61** | **61.1@27.5 / 59.5@28.5** |

The model over-predicts the drop by **1.5 degC** at −5, where the calibration has
points at +25 and −12 and nothing between. **But the four −12 roasts measure
60.30, 61.40, 63.00 and 62.20 against one prediction — a 2.7 degC spread on
nominally identical charges — so a 1.5 degC miss at a new temperature is inside
the model's own scatter.** Do not refit on `n = 1`. Roast 56 is, however, the
obvious third temperature for the calibration group when a second −5 roast
exists: it has an entered greens temperature, a held gate and the longest
loop-free window in the set.

#### What this settles for step 9, `INLET TRIM`

The tracking case is now **dead**, not merely weakened. Roast 56 tracks its
background at rms **0.94 degC over 30-90 s**, **0.41 over 95-120 s** and
**1.26 over the whole roast**, with the inner loop at rms 0.91 from 50 s on.
There is no tracking error left for an inlet trim to remove. What survives is
purely the robustness argument — behaviour when the inner loop is disturbed or
the plant moves — and that has to be argued on its own terms or dropped.

