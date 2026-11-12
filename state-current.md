# state-current — what is being worked on right now

> **This file: the active effort and where it stands.** Nothing that is merely
> a record of what happened belongs here.
>
> - [state-plan.md](state-plan.md) — planned work and the specifications in force.
> - [state-history.md](state-history.md) — index of the three investigation
>   records: [cascade](state-history-cascade.md) (roasts 40-49),
>   [charge](state-history-charge.md) (50-56),
>   [residual](state-history-residual.md) (57-59).
> - [state-archive.md](state-archive.md) — completed firmware work and the
>   F-numbered review findings.
>
> **Update discipline.** When a phase completes, move its detail out of *plan*
> and re-point this file at the next phase. When a section here turns into a
> record of what happened rather than a statement of what is true now, move it
> to the history file for that effort. A "superseded" note is a signal the
> content belongs elsewhere, not a way to keep it here.

## HANDOFF — after roast 62 (2026-09-13): the fan step is **1.4-1.7 degC** and drying keeps ~1.5

**If you are a fresh context, this section is the whole job.** Everything below
it is background. Full records: state-history-residual.md § Roast 62, § Phase B,
§ Roast 61, § Phase A.

### 1. What roast 62 measured, and what is next

**Roast 62 is the first roast since 56 to enter the measurement window flat**,
and the first whose answer does not move with the reference point. Entry slope
over 85-115 s: **−0.03 degC/min** against roast 56's −1.22 and roast 60's −5.01.

| | roast 56 (fan 60) | **roast 62 (fan 64)** | **the fan's share** |
|---|---|---|---|
| minimum | −2.91 @ 165 s | **−1.50 @ 179 s** | **1.41** |
| swing from 100 s | −3.37 | **−1.66** | **1.71** |
| swing from 120 s | −2.83 | **−1.12** | **1.71** |
| rms 120-230 s | 1.97 | **1.06** | |

**The 120 s fan step is worth 1.4-1.7 degC of the 2.9 and about 1.5 degC
survives at fan 64.** Phase A's ceiling arithmetic said 2.68-3.93, so the fan
delivers about half of it; the Phase B figure of 0.72-1.22 is superseded, and it
was too low because roast 60 never entered the window flat.

**Row L is authored and the next thing needed is one roast to score it.** The
term is in `make_background.py` and the background is
**`artisan/profile_400g_m5C_dry_v7.alog`**; the sizing, the desk check and the
written-down prediction are state-history-residual.md § The drying term. In
short:

```
RoR(u) = rise(u) * fall(u) / (1 + K*g(BT))     K = 1.62 degC at 400 g / 11.0 %
```

`g(BT)` is the free water released per degC of BT over **BT 100 → 140**, and the
window's far end is the measured part: the RoR deficit crosses zero at **BT
138-141 on roasts 56, 57, 60 and 62 alike** — not at DRY END (BT 149), not at a
fixed second. `K` is written as `eta·m_w·h_vap/(m·c_b + C_chamber)` so it scales
with water mass; `eta = 0.0156` is one lumped number fitted to roast 62, and
what it lumps is in the record. `--h-fus` remains heat of *fusion* in the charge
dip, a different quantity.

**Two things to carry into scoring it.** The four-constraint solve pays the
removed rate back before the window, so `v7` differs from `v4` by **+0.85 degC at
100 s, +0.46 at 120, and under 0.07 from 180 s to DROP** — the intervention is to
bring the bed along before the water boils, not to lower the curve through the
dip. And it therefore relieves only **0.89 degC of roast 62's 1.66 degC swing**
on the curve alone; the rest depends on the loop delivering the extra front-end
rate. **`e` at 100 s says which happened** — about +0.1 if it did, about −0.85 if
it did not.

**Then row Q** — the settled-fan preheat — and after that the fan can come down
off 64 as a whole-roast change with no step in the window.

### 1a. The preheat is solved, and the operator's method is better than the spec

**Hold the inlet SV fixed through the preheat and trim BT with the fan.** Roast
62 held `T_inlet` at 142.0 from −573 s, walked the fan 58 → 60 → 62 → 58 to bring
BT to 130, then stepped to 64 at −5.5 s. At −2 s: **Inlet 142.0 / BT 130.6**
against roast 56's 141.8 / 130.4. Both variables pinned, which the spec as
written (fix inlet, let BT float) does not do.

**Why it matters is § 1c: the precharge inlet sets the PID handover**, not the
dip.

### 1b. The 0.94 precharge-inlet gain is withdrawn — the inlet does not set the turning point

**Roast 62 carries roast 56's precharge inlet and returns roast 60's turning
point.** That is the whole argument and it needs no model:

| roast | inlet_pre | greens | **TP** | charge proxy /100 g |
|---|---|---|---|---|
| 56 | **142.0** | −5.0 | **61.1** | 14.10 |
| 57 | 155.3 | −5.0 | 62.6 | 16.92 |
| 60 | **133.0** | −5.0 | **52.8** | 15.80 |
| 62 | **141.9** | −5.0 | **53.8** | 15.87 |

- **the precharge-inlet gain is 0.11** — roasts 60 and 62, inlets 8.9 degC apart,
  turning points 1.0 degC apart — and that matches roast 57's 0.11 exactly.
  **The 0.94 read off roasts 56 and 60 is withdrawn**; those two differ in
  something else as well, and roast 62 is the control that separates them. The
  dip model's near-inert `--inlet-precharge` (gain 0.13) was right;
- **so the preheat is a weak lever in both its variables** — 0.100 per degC of
  preheat BT, 0.11 per degC of precharge inlet — which is § 6 as originally
  written, and the correction in § 1b's earlier form is retracted.

**What separates roast 56 from 60 and 62 is the charge, and `greens_temp` did
not see it.** The operator: *"they well could have been colder beans. i try to
measure, but there's a ton of noise in the IR sensor (emissivity sensitive)."*
**Two independent instruments agree with that and with each other:**

| | roast 56 | roasts 60 / 62 | difference |
|---|---|---|---|
| entered `greens_temp` | −5.0 | −5.0 / −5.0 | **0** |
| charge proxy → `T_bean` | −7.8 | −24.8 / −24.9 | **16.9 degC** |
| dip model → `--greens-temp` reproducing the measured TP | ≈ −2.5 | ≈ −14.5 | **12 degC** |

`charge_state.py`'s proxy is a **control-independent** BT-drop measurement;
`charge_dip.dip` is a **fitted mixing model** inverted against the observed
turning point. They share no data and no parameters, and both say roasts 60 and
62 charged **12-17 degC colder than roast 56** while the entered number was
identical. Their absolute values differ because each carries its own calibration
assumption; only the difference is being read here.

**So the entered `greens_temp` is a nominal, not a measurement** — which is
§ Robustness over precision as originally written, now with a number on the
error. An IR gun reads the bean *surface*, and beans out of a freezer warm at the
surface within minutes while the core stays cold, so the reading is warm-biased
by an amount that depends on how long they have been out. That is the shape of
this disagreement.

**And it is a bias, not scatter: roasts 60 and 62 agree to 0.07 on the proxy.**
Whatever was done on 2026-09-13 is repeatable to better than 1 degC of bean
temperature. **So standardise the handling rather than the measurement** — a
fixed time out of the freezer before CHARGE, the same every roast — and use the
proxy to verify it. Do not chase the IR reading, and do not re-nominal
`--greens-temp` per roast; a moving nominal makes backgrounds incomparable, which
is the whole reason the nominal exists.

**One consequence to carry into authoring.** The background's dip is authored at
the nominal, so it is systematically **too shallow** — the background's TP is
59.2 where roast 62 delivered 53.8. Roast 62 shows a 5.4 degC dip mismatch does
*not* break the entry slope, so this is a known tolerated offset rather than a
fault; but it is why the loop has work to do in the first 50 s, and it is worth
revisiting once the handling is fixed and the proxy is stable across several
roasts.

**Pair roasts on the proxy, never on the entered temperature.** Roasts 60 and 62
agreeing to 0.07 is what makes their 0.11 inlet gain trustworthy; roast 56's
1.77 gap is why it cannot be paired with either on the charge.

### 1c. What the precharge inlet *does* do — it sets the PID handover

At +15 s the loop inherits whatever SV the preheat left:

| | precharge inlet | peak SV, first minute | entry slope |
|---|---|---|---|
| 56 | 142.0 | 167.3 @ 65 s | −1.22 |
| **60** | **133.0** | **180.6 @ 21.6 s** | **−5.01** |
| 62 | 141.9 | 167.6 @ 58 s | −0.03 |

Roast 60 handed the PID an SV 9 degC below what it needed, it slammed to 180.6
within 7 s of switching on, and spent 100 s unwinding — which is the whole reason
Phase B could not be scored. **Hand the loop the right operating point and it
does not have to catch up through the measurement window.** That is why fixing
the inlet is right, and the reason is the handover, not the dip.

### 1e. The fan ladder (roast 61) — the gap law behind the preheat

Roast 60 held the specified preheat **BT 130.1** but its precharge inlet settled
at **132.8 against the specified 141.8**, because the machine had soaked 23.8 min
rather than roast 56's 9.7 and a warm-walled chamber holds BT 130 on 9 degC less
inlet. **A preheat specified in BT is not a state of the machine** — this is
§ 4's soak finding restated on the roasting side.

It cost an **8.3 degC deeper turning point** (52.8 against 61.1), absorbed by
50 s and worth only +0.5 degC at 120 s — which is the whole reason the Phase B
read survives it, and the reason the bracket has two ends.

**Spec: fan 64 from the start of the preheat, `T_inlet` SV fixed at 141.8,
CHARGE when BT has been flat for 2 minutes. Record BT — it is a readout, not a
setting; expect 139-141.** The operator's proposal, and roast 61's ladder makes
the case quantitative (state-history-residual.md § Roast 61, § The preheat spec).

**Why the inlet and not BT.** `Inlet − BT` is a clean function of fan with a
session-drift term — empty chamber, BT 130, fans 54-70, both legs:

```
gap = (A0 + A1*(t-525))/(fan - f0) + B
A0 = 492.0   A1 = -2.47 /min   f0 = 42.83   B = -20.46      rms 0.345 over 15 rungs

fan    54     56     58     60     62     64     66     68     70
gap +23.71 +16.42 +11.78  +7.44  +3.64  +0.80  -0.53  -2.11  -3.52
```

The drift has to land on *some* variable: hold BT and the inlet drifts at
**0.117 degC/min at fan 64**; hold the inlet and BT drifts instead. The precharge
inlet carries most of the leverage on the turning point and preheat BT is nearly
inert (§ 6), so the drift costs about a ninth as much on BT. **And the inlet is
what the operator commands** — BT is a PID's controlled variable, pinned at its
target regardless of the machine's state, which is exactly why roasts 56 and 60
looked identical while being 8.8 degC apart.

**Never step the fan near CHARGE.** Roasts 56 and 57 both stepped to 64 within
8 s of it and the inlet had not moved at all — they charged with fan-58/60 air at
fan-64 flow. Roast 60 charged settled. That reconciles the inlet gain reading
0.11 from roasts 56/57 and 0.94 from 56/60: as a **fan-step burst** it is one
story, since 56 and 57 land within 1.5 degC of each other despite 14 degC of
preheat difference. A hypothesis, not a measurement — but the instruction is the
same either way.

**Two things withdrawn.** The 60 → 64 "collapse" and the probe-washing
explanation for it: the ladder is smooth and monotone, and the collapse was an
artefact of mixing unsettled readings from two roasts (roast 60's fan-60 segment
read 11.13 where the settled value is 7.44). **And `f0 = 42.83` here against
Phase A's 41.9 loaded**, from a completely different measurement.

**What is real is the sign change** — the gap crosses zero near **fan 65** and
the inlet settles *below* BT above it, which brackets what Phase A saw at fans 72
and 80. `1/mdot` cannot produce it; the `B = −20.5 degC` term is what does.

**§ 1b withdraws the 0.94 inlet gain this section used to report** — roast 62
shows it was an unmeasured bean-temperature difference. § 6's conclusion stands
as originally written: **the preheat is a weak lever on the turning point in
both its variables**, 0.100 per degC of BT and 0.11 per degC of inlet.

**And the dip model has those two in the wrong order** — `make_background.py`
gives 0.28 per degC of charge BT against 0.13 per degC of precharge inlet, i.e.
BT dominant, where the roasts say inlet dominant by 9×. Both roast readings are
single roasts confounded with soak and ambient, so neither calibrates anything —
but the disagreement in *ordering* is why **row P reproduces a measured preheat
point instead of authoring a dip for a new one.**

### 1f. The duty model composes between roasts, and must not be used inside one

Phase A's `HT = A(fan−f0)(Inlet−amb)+c` — fitted on a bench ladder, empty and
with 345 g of *roasted* beans — predicts roast 60's live duty from roast 56's to
**−0.07 / +0.64 / +1.12 %** across the three windows, through a fan change,
5.7 degC of ambient and 5 degC of inlet. **The +4.6 % duty step is the fan,
measured.** That is the strongest transfer result the bench programme has
produced.

**But as a standing-duty baseline inside a roast it is backwards**, giving a
negative RoR-vs-excess slope on all three roasts: it is fitted in `Inlet` over
the bench range, and inside a roast `Inlet` runs to 230, so the modelled loss
grows faster than the real one and eats the entire excess. **The excess-duty
model does not transfer across fan on either baseline** — the fan-60 empty
`HT(BT)` line leaves roast 60 at `−33.3 + 4.23·excess`, and re-basing it by the
modelled +5.2 % fixes the level and not the slope. § 3's warning stands:
do not quietly pick the baseline that flatters the fit.

### 2. What Phase A measured (roasts 58 and 59, 2026-09-10)

Roast 58 ran the planned ladder empty; **roast 59 is the operator's addition —
the same ladder with 345 g of already-roasted beans in the chamber** — and it is
the more useful of the two, because it is the configuration the roast runs in.

```
HT = A*(fan - f0)*(Inlet - amb) + c          <- a HEATER relation, not a chamber one

empty  fan 53-64    f0 = 39.2   rms 0.182 %   (10 rungs, 3 params, 7 dof)
loaded fan 56-64    f0 = 42.9   rms 0.202 %   (11 rungs, 3 params, 8 dof)
joint, shared A,c   f0 = 40.0 / 41.9    c = 22.7 %     rms 0.231 % (21, 4, 17)

f(64 -> 60) = 0.162 empty, 0.189 loaded, 0.181 joint       threshold was 0.12
ceiling deficit = RoR*f*T_eff/60 = 3.5 - 4.1 degC          observed 2.93
```

**The fan over-covers the residual by about a third**, which is the room the
ceiling arithmetic asked for: less flow also raises `T_in − T_out`. `c = 22.7 %`
is the flow-independent duty **measured** rather than extrapolated 5× — the plan
had assumed 24.9 % and was close.

**The direct step response is the part that needs no model.** Roast 59, BT held
at 145 with the bed in, `64 → 56`: BT moved **−0.67 degC, bottomed at 54 s,
recovered by ~130 s**. The roast residual bottoms 45-50 s after the 120 s step
and recovers by 230 s. Same loop, same shape — the first direct evidence that a
fan step on this machine makes a transient of the residual's shape at all.
**Do not read a magnitude out of it**: `Inlet − BT` is ~2 degC at the settled
bench against 49-60 in the roast, so the same `f` removes 25-30× more power
there, and linear scaling would predict 8-10 degC. Timing from the step, size
from the duty model.

Three more, all in state-history-residual.md § Phase A:

- **the blower saturates above fan 64** — fan 72 delivers the flow of a nominal
  70.4 and fan 80 of a nominal 75.0. `mdot ∝ (fan − 40)` holds across the range
  the roast uses and bends over above it, so the 60-80 span the plan chose for
  contrast is not what sized `f`; **the descending 60 / 56 / 53 rungs the
  operator added did**;
- **345 g of beans is a 9.3 % flow restriction** (shared `A` and `c`, separate
  `f0`; pooling onto one `f0` costs 5.5× in residual);
- **route 1 is unavailable, not disagreeing.** `Temp_Drive` at BT 145 / fan 60
  read 12.84 / 8.47 / 6.51 / 7.49 in one session while duty repeated to ±0.09 %,
  and at fan 72 and 80 the settled `Inlet` sits *below* BT, which `1/mdot`
  cannot produce at all. This is § 5 below, reproduced at 8× the sample count.

### 3. The duty line is linear to BT 190 — and its level is not pinned down

Four rungs each at fan 60, last 120 s, residuals at the duty quantisation over a
45 degC span:

```
empty    HT = 15.16 + 0.2165*BT      residuals  -0.00 -0.05 +0.11 -0.06
loaded   HT = 17.75 + 0.1788*BT      residuals  +0.06 -0.09 +0.00 +0.03
```

**Nothing is superlinear, no rung failed to settle, and the empty chamber has no
ceiling below 190** (`HT` only 60.2 % at fan 80). A2 is answered and the
superlinear-loss candidate for the excess-duty model's intercept disagreement is
dead.

**But phase 0's `HT = 20.25 + 0.1922·BT` is not this line** — it sits 1.57 %
high at BT 145 falling to 0.47 % at 190, of which ~0.47 % is this session's
2.4 degC warmer ambient. The slopes are consistent (22 degC of span against 45),
so the disagreement is a **level**, and there are two candidates this data cannot
separate: the soak (§ 4), or phase 0's unrecorded fan being a unit or two above
60 at ~0.96 % of duty per unit.

**Re-basing the excess-duty model on the loaded line does not work** — it drives
roast 56's `RoR = 0.81 + 2.66·excess` to about `−11.7 + 2.66·excess`, i.e. a
loaded chamber standing still cooling at 12 degC/min. 345 g of *roasted* beans
sitting at fan 60 is not 400 g of circulating greens.

**What survives is the size of the question.** The intercept disagreement between
roasts 56 and 57 is 5.65 degC/min, which at the model's own slope is **2.1 % of
duty**; the baseline candidates measured here span **4.5 %**. The empty line's
apparent success is to that extent luck, and **no re-basing on this data settles
it.** Do not quietly pick the baseline that flatters the fit.

### 4. Soak the machine before the first rung — 20 minutes, or run second

Roast 58 started cold (BT 29.0 = ambient). Its fan-60 / BT-145 duty decayed
**50.5 → 47.6 %** over seven minutes and only reached 46.5 % by 23. Three later
visits spanning 23 to 62 minutes then agreed to **0.18 %**. So Phase A's own
criterion — *rung 5 must reproduce rung 1 to ±0.5 %* — **failed**, rung 1 reading
1.22 % high, and the cause is the cold start rather than drift in the
measurement. Roast 59, an hour later on the soaked machine, settled in three
minutes.

**The duty model absorbs the soak and that is informative**: rung 1's residual
against the fit is +0.03 %, because the soak raises `Inlet` and `HT` together and
the model is written in `Inlet`. It is the BT-referenced line `HT(BT)` a soaking
chamber breaks, because a soaking chamber is not standing still.

### 5. Temp_Drive: stage A passes, but read the number correctly

**`d(TD)/d(BT) = +0.025`** across a settled empty ladder at BT 130 / 140 / 145 /
152 — an order of magnitude below the 0.10-0.383 bracket every document here
carried, and **20× below the ~0.5 that would have killed the design**. The
drive→BT loop has a DC gain near 40 and is very nearly an integrator. Even the
most adverse pairing in the data gives 0.17. **Stage A's gate is open; go to
stage B (desk).**

**But do not quote 0.025 as a measurement.** Temp_Drive moved 0.6 degC across the
whole 22 degC ladder while two same-BT repeats *inside one session* disagreed by
−1.51 and +1.02. Phase A reproduced this at 8× the sample count and worse: four
visits to BT 145 / fan 60 spread **6.3 degC** while duty repeated to ±0.09 %, and
`Inlet` goes *below* BT at fan 72 and 80. **Duty is a state variable at this
precision; `Inlet − BT` is not, and at high fan it does not even carry the right
sign.** Carry that into stage B item 4: the 29-94 degC drive range is real but
every figure in it has ±1.5 degC of probe history, so size the range with margin
and never tune on a Temp_Drive difference under ~2 degC.

### 6. The preheat lever is withdrawn — do not build the compensated roast

> **Read § 1b first.** Roast 60 shows this section levered the wrong variable:
> the gain below is the gain on preheat **BT**, and the precharge **inlet** —
> which roast 57 moved at the same time — has a gain nine times larger. The
> conclusion *"do not build the compensated roast"* stands; the reason is now
> that BT is the inert half of the pair, not that the preheat as a whole is.

**ΔTP = +1.50 degC for +15.04 degC of preheat** (roast 57). The gain is **0.100**
against a predicted 0.415, inside the old stop condition. `0.60 / 0.100` = **6.0
degC of preheat per degC of greens temperature**: a 10 degC bean-temperature
swing would need 60 degC of preheat, and 145 was already 15 degC hotter than the
beans had ever been tipped into.

`preheat = 124.4 − 1.17 × greens_temp` is **withdrawn**, and so is
`tools/analysis/preheat_lever.py`'s use as a shipping calculator — keep the tool,
it now reads 6.0 and says so.

**Why it failed is worth more than the lever was.** The preheat had left the
reading by **20 s**, *inside the PID-off window* (the cascade engages at
CHARGE+15.5 s), so no control action removed it; then it came back **doubled** at
70 s as the loop chased the missed turning point. `dT_mix = phi·(BT_c − T_bean)`
treats the preheat reading as the chamber's available energy. It is not: it is
largely the probe and the metal it sits against, on the **non-flow side of the
asymmetric expansion chamber**, and 400 g of −5 degC beans overwrite the probe's
local environment in under twenty seconds. **The preheat is a slow lever aimed at
the wrong window.** Do not spend another load on a preheat rung.

### 7. What the bench line already bought

`HT = 20.25 + 0.1922·BT` (phase 0; see § 3 for its level problem) is the duty the
empty chamber needs to stand still. Subtract it from a roast's live duty and the
remainder is nearly proportional to the rate of rise: post-DRY-END,
`RoR = 0.81 + 2.66·excess` (roast 56, resid 0.74 degC/min) and
`6.46 + 2.29·excess` (roast 57, resid 1.11), over RoR 2-25 degC/min. **One
parameter, measured empty in forty minutes, tracking the loaded roast to about
1 degC/min.**

That is the answer to whether `plant_roast46.json`'s `loss(t)` cubic is really a
BT-dependent loss aliased into a time function: **mostly yes**, and it can be
replaced by a bench line. The slopes agree to 15 %, the intercepts do not, and
§ 3 now says why that gap is not going to close from bench data.

The same line reads the ceiling: post-DRY-END RoR is linear in BT in both roasts
(`79.79 − 0.3657·BT`, `73.57 − 0.3357·BT`), crossing zero at **BT 218.2 and
219.2**. At the duty the loop settles on and fan 60, **the machine asymptotes to
~218 degC** and the whole back-half RoR decay is first-order approach to it.

**This is the strongest argument yet for step 9's shape** — a feedforward whose
loss term is measured on the bench rather than fitted to one roast — and it is
the first thing here that is not circular.

**And roast 20 (2026-07-03) is the other half of the argument.** It ran an inlet
schedule off background playback with no outer loop at all — three special events
in the whole log — and produced the smoothest BT in the archive: post-dip RoR
fits its own cubic to **0.375 degC/min** against the cascade's 1.6-2.8, with the
inner loop holding the commanded polyline at **rms 0.60 degC**.

**Two cautions come with it, and the second is general.** Roast 20 has no BT
target to score against and the archive has no open-loop repeat pair, so
"smoother" is not "better" — that is what the trim is for. And **roast 20 cannot
identify the plant**: profiling the fit residual over `a` = 0.000…0.016 moves it
7 %, monotone, so its best fit is `a = 0`, where roast 46's swings 5× around a
sharp minimum at 0.0049. **A smooth input carries no information about the
transfer function.** Never read a plant number off a well-behaved roast — see
state-history-residual.md § Roast 20 revisited.

**`LA 12` stays deferred and its premise is now dead.** It was sized against the
lag reading of the same residual Phase A has just shown to be a disturbance, and
105 s would have pushed SV up fifteen seconds *before* the fan step, masking the
cause without ever naming it.

### 8. The bean budget — 1-2 loads of `C1043` left, and none of them are spoken for

**The one question that needed `C1043` is answered.** Roast 57 cracked at
**197.40 at 397 s** and roast 60 at **196.90 at 384 s**; `beans.py --coffee
C1043` reads a cascade-era median of **197.55**, and recommends
`--fcs <s>:197.6 --ror-at-fcs 9.4`. Roast 56's
195.3 stands 1.2 degC below the rest of its lot and is a mark made early by ear.
**`artisan/profile_400g_m5C_fc195_v5.alog` is retired** — it was parked on that
single reading.

Everything remaining on the list is a *machine* measurement scored over 0-200 s,
so **run it on whatever else is in the cupboard** and keep `C1043` for cupping.
On another lot the only cost is a less well-targeted back half: no cascade-era
history means no derived `--fcs` / `--ror-at-fcs`, so use `beans.py`'s pooled
default, accept that first crack lands early or late, and say so in the log
rather than pretending the back half was on target.

## Every roast — the procedure and the checks

### Regenerating the background

**`tools/README.md` is the orientation brief for this task** — the four inputs,
the recipe, the check block to read, and the traps. In short:

```
.venv/bin/python tools/make_background.py --mass 400 --greens-temp <measured> \
    --fcs 399:<bean FCs BT> --ror-at-fcs <lot> --development 28 \
    --moisture-greens 11.0 --out artisan/profile_400g_<T>_<tag>.alog
```

**The current 400 g / −5 degC background is
`artisan/profile_400g_m5C_dry_v7.alog`** — v4 plus the drying term, marks
unchanged (§ 1).

**A 500 g background exists for a darker roast, outside the measurement
programme: `artisan/profile_500g_m5C_dev52_v8.alog`** (2026-11-11). It uses v7's
marks and drying term at 500 g / −5 degC with `--development 52`, so DROP is
**205.3 at 7:31**, +2.9 degC and +24 s on v7, and the curve is identical to v7
from 180 s to FCs. The dip is deeper (TP 54.3 vs 59.2) and the peak is 49.5 vs
46.0 degC/min. Pinning `--drop 427:205.4` instead misses its marks by 0.1 and
peaks at 66 degC/min, so that one is rejected. **It is unvalidated twice over**:
the mass term is untested at 500 g (§ The mass term), and 500 g needs more fan
than 400 g's 64 to circulate, which has not been sized. Do not score it against
the 400 g series.

`--development` places DROP at `FCs + <seconds>` with whatever temperature
follows; `--fcs <s>:<BT>` sets the crack mark, and the per-lot value comes from
state-plan.md § Bean reference. `--moisture-greens` sizes the drying term. Generate at the mass and charge temperature
actually being roasted — **never scale** (see § The mass term below).

**The first-minute coupling was a solver defect, and it is fixed (2026-09-08).**
The exponential RoR spec has **four** free parameters (`tau_r, R0, R_inf,
tau_d`), not the three every document here claimed; DRY END, FCs and RoR@FCs
supply three. The fit was underdetermined by exactly one, and every point along
the leftover direction hit all three marks to 1e-14 while giving a different
roast — BT at 60 s anywhere over 71-81 degC, the RoR peak anywhere over 44-83 s
— with the winner picked by whichever multi-start converged lower on
floating-point noise. That, not physics, is what made a 1.1 degC change to a
mark 340 s away move BT at 60 s by 4.8 degC, non-monotonically.

`make_background.py` now takes **`--ror-peak-at` (default 53 s since CHARGE)** as
a fourth constraint. The system is square with it and converges to 1e-14 across
−24…+25 degC and 250…500 g in both `--development` and `--drop` mode. What is
left is the honest coupling: over `--fcs` 195.5-198.8, BT at 60 s moves **0.8
degC, monotone** (was 7.2 degC, non-monotone). See tools/README.md § The ramp
used to be a lottery.

The default 53 s is where `profile_400g_m5C_v4.alog` — roast 56's background,
the only curve to pass all four checks — happens to peak, so the fix reshapes
nothing silently. It is a lottery draw promoted to a spec, **not a measurement**;
vary it deliberately, one roast at a time. The reachable band at 400 g / −5 degC
is about 45-80 s.

**Still do not run a regenerated background and a control change in the same
roast** — the 0.8 degC has been seen in the fit, not yet on the machine.

### The alarm table can silently disagree with the .aset — CHECK IT EVERY ROAST

Found 2026-09-07: after loading `floor100.aset`, Artisan's Alarms dialog showed
the `LA 6` alarm at **00:30** while the file said **90**. Every other row matched.
Roast 56 was clean — the file said 45 and the log shows the switch at 46.3 s —
but the mechanism has not gone away.

**It is not RESET.** `reset()` clears only `alarmstate` and `TPalarmtimeindex` —
the triggered flags and the TP index — and never touches `alarmoffset`.

**It is `savealarms()`** (alarms.py:730-776), which writes *every* row back into
`qmc.alarm*` from the dialog's widgets when the dialog closes. Load an `.aset`
with the Alarms dialog open and the load updates Artisan's state, then closing
the dialog overwrites it with the stale widgets. Artisan then saves settings on
quit, so the wrong value persists in the operator's own settings regardless of
what the repo file says. `selectAlarmSet` (canvas.py:6067+) would replace the
whole table too, but the `alarmsets` slots in these files are empty.

**Before every roast, open Alarms and check every row against this table.** The
time column is `mm:ss`, so 120 s reads `02:00`, not `:20`.

**Roast 57 was clean by this test** — the file said row 8 off and the log shows
no SV step at 105 s. **For the next roast the eighth row must still read `off`**
(load `preheat.aset`, not `floor100.aset`) **and row 7 must read `off` too** —
that is the whole change, and the fan stays at 64 for the roast. See § 2 and
state-plan.md § TEST PLAN § B1.

| # | On | From | Time | Source | Cond | Value | Action | Button |
|---|---|---|---|---|---|---|---|---|
| 1 | off | CHARGE | 00:01 | | > | 0 | Playback ON | |
| 2 | ON | DRY END | 00:00 | ΔBT | < | −25 | DROP | |
| 3 | ON | CHARGE | 00:01 | | > | 0 | Event Button | 20 = `LA 0` |
| 4 | ON | CHARGE | 00:45 | | > | 0 | Event Button | 21 = `LA 6` |
| 5 | ON | ON | 16:00 | BT | < | 131 | Event Button | 23 = `ARM bak` |
| 6 | ON | CHARGE | 00:15 | | > | 0 | Event Button | 25 = `PID on` |
| **7** | ON — **off for the next roast** | CHARGE | 02:00 | | > | 0 | Event Button | 26 = `Fan 60` |
| **8** | **off** (ON in `floor100.aset`) | CHARGE | **01:45** | | > | 0 | Event Button | **27 = `LA 12`** |

(Button numbers in `alarmstrings` are 1-based into `extraeventslabels`, which is
0-based: `alarmstrings` `21` is `extraeventslabels[20]` = `LA 6`.)

**And verify from the log afterwards, because the `.alog` cannot tell you.** It
records `svLookahead` at *save* time (roast 56 says 6, which is only the value
that happened to be live at the end). The switch instant is visible as a **step
in SV**, because `L` seconds of lookahead adds `bkg(t + L) − bkg(t)` of target
and `dSV/derror = 4.8`:

| | roast 54 | roast 55 | roast 56 | **roast 57** |
|---|---|---|---|---|
| SV step at 91.0 s | 20.2 | 20.3 | **0.00** | **0.00** |
| SV step at 46.3-46.5 s | — | — | **+24.25** (predicted +21.4) | **+19.30** |
| SV step at 105 s (`LA 12`) | — | — | — | **0.00 — row 8 was off** |
| SV step at 30 s | −0.2 | 0.0 | −3.02 | 0.00 |

**That arithmetic is the only reliable check of what actually ran**, and the PID
port confirms it independently: replaying roast 56 with the switch assumed at
46.3 s gives rms 1.97 degC of SV over 30-180 s, against 8.94 / 9.68 / 23.20 /
42.83 for 30 s / 60 s / 91 s / never.

**Caveat, stated plainly:** `replay_pid` is fed *measured* BT, so it says what the
controller would have commanded, not what BT would have resulted. It is a good
detector of what already happened and a bad predictor of a sustained change.

### Checking the gate in the log

**The roast-53 handoff's check was wrong** and roast 54 disproved it. `markCharge`
re-records every visible non-zero slider at CHARGE (canvas.py:14694-14709), and
`EventRecordAction`'s duplicate guard (canvas.py:15854-15856) compares only against
the single most recent event *of any type* — so the `Air -> 64` the CHARGE button
fires a few seconds earlier reliably breaks the guard and a duplicate `T_inlet`
event lands at +1.0 s on **every** roast, gated or not. That duplicate is not
`pidOn()`'s signature and proves nothing.

**The check that works**: `T_inlet` must carry *nothing* between +1 s and the
`PID ON` alarm at +15.5 s. Roasts 54, 55, 56 and 57 are all clean by that test —
roast 56 carries the two preheat entries at −16 and −14 s, the duplicate at
+1.0 s, and then nothing until 15.5 s.

## Settled, and what is still wrong

### Settled and not worth re-opening

`k = 0.1056`, measured from roasts 50/51 across a 37 degC span to 0.34 %;
`h_fus` under ~1 J/g; the 13.5 s is total apparent lag rather than transport;
the preheat equilibrium is fan 58 / BT 130.2 / Temp_Drive 10.25. The charge
gate, the alarm-fired fan step and the 100 floor are all proven.
**`d(TP)/d(preheat) = 0.100`** and the preheat lever is dead (§ 6).
**`d(TD)/d(BT) = +0.025`** and Temp_Drive stage A passes (§ 5).
**`C1043` cracks at 197.6** (§ 8).

**"The plant has no fan term" now needs qualifying.** The fan does not enter the
*inner* loop's identified plant, and the inner loop absorbs a 4-unit step in
seconds — that part stands. But the fan sets the mass flow, so it enters the
*outer* loop as delivered power: 64 → 60 is a **6.6-7.4 % flow reduction**
(0.9-1.0 % heat per unit, loaded, matching the empty 0.992), and the 120 s step
is the leading suspect for the −2.9 degC residual at 170 s. § 2 is the test.

**`moisture_greens` is entered again** — roasts 56 and 57 both carry `11.0`,
matching roasts 50-52's `10.9` for the same lot, after four roasts at `0.0`. Keep
entering it.

**The dip model has two −5 degC points now, and it straddles them.** Roast 56
turned at **61.10 at 25.5 s** against the m5C background's 59.24; roast 57 at
**62.60 at 26.0 s** against pre145_v6's 65.48 — **+1.86 and −2.88**. The sign
flip across a 15 degC preheat step *is* the failed lever: over that span the
model's charge term is **4.7 degC too steep in `BT_c`**, predicting a 6.24 degC
turning-point shift where the machine gave 1.50.

Scored against the shipped calibration (fitted to roasts 50/51/53/54 at +25 and
−12, nothing between), roast 56 reads rms 1.92 / worst 3.61, the poorest of the
six recorded-temperature roasts. **That was still inside the model's own
scatter** — the four −12 roasts measure drops of 60.30, 61.40, 63.00 and 62.20
against one prediction — which is why it was not refitted on `n = 1`. **Roast 57
is a different matter**: it is a *deliberate step* in the one variable the model
is wrong about, not another draw from the scatter. **Refit the `BT_c` term on
`d(TP)/d(preheat) = 0.100` before generating any background at a preheat away
from 130.2**, and note that the two −5 roasts together now give the model its
third calibration temperature.

### The mass term still disagrees with `phi(mass)`

Roasts 51 and 52 are the same lot at the same measured −12.0 degC, differing only
in mass, and they disagree with the model:

| roast | mass | `k` |
|---|---|---|
| 51 | 400 g | 0.10483 |
| 52 | 380 g | **0.10253** |

`phi = mc/(C_chamber + mc)` saturates, so `phi/m` is **larger** at 380 g — the
model predicts roast 52 should read **+3.4%**, i.e. `k = 0.1084`. It reads
**−2.2%**, so the model is **5.4% out** over a 5% change in mass, and in the
**wrong direction**. Two caveats: `n = 1`, and both roasts carry
`greens_temp = −12.0` exactly, which may be one measurement entered twice.
**Treat any background generated away from 400 g as unvalidated** and generate at
the mass actually being roasted rather than scaling. Resolving it needs a
deliberate mass pair at one charge temperature.

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

**Git — the version and branch truth.** Development happens on feature
branches; `main` holds roast-tested firmware.

| | version | state |
|---|---|---|
| `main` | **v0.18.0** (2026-08-23) | command authentication (`feature/auth-proxy`, fast-forwarded in); on-roaster validation still pending — state-plan.md § NEXT items 9 and 10 |
| **`feature/artisan-pid`** — current | **v0.19.0**, then **v0.20.0** | both **flashed**. v0.19.0 validated on roast 47 (`SV`/`HT` `getData` nodes live; `INLET TRIM` flashed but **un-drilled**, § NEXT item 11). Every roast from 48 on has run v0.20.0's measured `feedforward()` map |
| `feature/vision-uvc-probe` | — | two commits that exist on no other branch and have **never been pushed** |

What v0.19.0 and v0.20.0 contain is state-archive.md § Firmware v0.19.0 and
v0.20.0. Start each new effort on a fresh branch off `main`; commit per phase
with a message naming the phase. The operator's Artisan config churn
(`artisan/*.aset`, `*.alog`) may be present in the working tree — **never sweep
it into a firmware commit**; stage files explicitly.

## Active effort — the Artisan cascade PID

**Branch `feature/artisan-pid`, off `main` at v0.18.0.** Artisan's software PID
is the **outer** loop of a cascade: PV = BT against a generated background curve,
and its output is the **inlet setpoint** the firmware's `MODE_INLET` loop holds.

```
background BT curve -> Artisan PID (2 Hz) -> INLET <degC> -> controlStep() (250 ms) -> heat
```

It replaces the flat arrangement where `pidSource=3` had Artisan PID-ing the
*Inlet* channel straight to OT1 heat, duplicating the firmware's own inner loop
across a WebSocket link. The cascade keeps the fast inner loop on-device and
gives Artisan the slow outer job it is good at. The specification in force — the
settings delta, the source citations, the alarm rows, the floor — is
state-plan.md § Artisan cascade PID.

### Where it stands, in one table

| | value | status |
|---|---|---|
| `pidKp` / `pidKi` / `pidKd` | **3.0 / 0.07 / 0** | settled, not a compromise — best on the nominal plant, under +14 s of delay and +50 % of gain |
| `svLookahead` | **0 → 6** at 45 s, by alarm | validated roast 49; the type-1 ramp error is cancelled |
| output floor / ceiling | **100** / 300 degC | floor came down over roasts 42-55; 100 validated roast 55 |
| inner loop | Kp 1.5 / Ki 0.05 / Kd 0 | **not retuned**, roast-validated, rms 0.40-0.52 degC |
| sampling / `dropSpikes` | 0.5 s / **off** | both applied to all `.aset` files from roast 49 |
| firmware | **v0.20.0** flashed | measured `feedforward()` map; `INLET TRIM` present but un-drilled |

**The controller is no longer the limiting error.** Roast 49 tracks `profile_003`
to **+0.40 degC / 1.84 s** with the error inside −1.94…+0.93 degC for the whole
ramp; roasts 50 and 51 agree with each other to 0.5 s at every level across a
37 degC charge difference. What is left is in the *reference* — the background
curve — and § 1 has now put a number on it: of the 140-200 s residual, **the fan
step is 1.4-1.7 degC and the background's missing latent-heat term owned the
remaining ~1.5, which is now authored into it.**

### The four things that had to be got right, and what each cost

1. **The integrator must supply the whole operating point**, because the outer
   loop's output is an *absolute* setpoint, not a duty. That is the root of
   roast 40's +17 degC standing deficit at `Ki = 0.003`, of the type-1 ramp
   error, of why `svLookahead` is needed at all, and of step 9's entire case.
2. **Only the ON button zeroes `Iterm`** — not `pidOn`, not DROP, not RESET, not
   loading settings, and there is no `pidReset()` command. Hence the standing
   procedure: press ON, turn the PID on, **preheat under PID control**, then
   CHARGE, one PID cycle per monitor cycle.
3. **`_back_calculate_integral` re-seeds the integrator at the floor** to
   `Kp*|worst dip error|` within seconds, so whatever the preheat left is
   forgotten in the charge dip — which is why raising `Ki` costs nothing on the
   charge transient, and why each second of `svLookahead` through the dip adds
   ~4 degC to the preload.
4. **Background event playback fights the PID for slider 3**, so it is off in
   every cascade `.aset`, along with the Playback-ON-at-CHARGE alarm. Playback is
   per-event-type (canvas.py:1848), which is what makes the characterisation runs
   and step 9 possible without reintroducing the collision.

### The plant

```
dBT/dt = a * (Inlet(t - theta) - BT) + loss(t)
roast 46:  a 0.0049   theta 13.5 s   tau 204 s    residual 0.116 degC
roast 48:  a 0.0080   theta  8.5 s   tau 125 s    kf = 0.0000 (no fan term)
```

`plant_roast46.json` is the **authoring source** — roast 48's card carries a
`supersedes_plant_roast46: false` field saying so, because roast 48's own
sub-windows spread `a` and `theta` as widely as the two cards differ.

**The 13.5 s was never 13.5 s of transport.** What is identified everywhere is
`theta + tau2`; the real transport delay is 0-2 s where roast 48's steps can see
it. The tuning does not move along that ridge — walking roast 46's entire ridge
from all-delay to all-lag moves the phase margin by 32.8 to 37.7 deg, inside the
model error these cards already carry.

**And a smooth roast cannot identify a plant at all.** Profiling roast 20's
residual over `a` = 0.000…0.016 moves it 7 %, monotone — best fit `a = 0` —
where roast 46's swings 5× around a sharp minimum. Never read a plant number off
a well-behaved roast, and never soften a characterisation schedule to make it
roast nicely.

### The dip model

`dT_mix = phi*(BT_c − T_bean)`, delivered as a **decaying rate** in front of the
unchanged plant card (`tools/analysis/charge_dip.py`). Fitted jointly to roasts
50/51/53/54: `phi`(400 g) **0.7116**, `tau_mix` **10.84 s**, `w_c` **2.10 s**,
rms **1.31 degC**. Two standing cautions: `charge_state.py`'s `k` is **not**
`phi` (reading it as the asymptotic fraction under-predicts every charge drop by
7-10 degC), and `phi` is depth per degC on the **operator's entered** temperature
scale — mixing scales has already cost one roast.

Its `BT_c` term is **4.7 degC too steep**, measured by roast 57's deliberate
15 degC preheat step (§ 6). Refit it before generating any background at a
preheat away from 130.2.

### What is still open, in order

1. **Score the latent-heat term** — authored 2026-09-13 into
   `make_background.py` and `artisan/profile_400g_m5C_dry_v7.alog`, sized on
   roast 62, desk-checked and predicted. § 1 and state-plan.md § Row L. One
   roast, the background the only change. The fan compensation is behind it and
   must be re-sized off the measured 1.4-1.7 degC.
2. **Refit the dip model's `BT_c` term** — and on the **precharge inlet**, not
   the preheat BT. § 1b: the gains are 0.94 and 0.100 respectively, and the
   inlet one is free to test.
3. **The mass term** (§ The mass term below) — needs a deliberate mass pair at
   one charge temperature.
4. **Step 9, `INLET TRIM`** — the outer loop's output becomes a bounded trim on a
   replayed base schedule, so the integrator stops supplying the operating point.
   The firmware half is flashed and inert; the design and what is left to close
   are state-plan.md § Step 9. § 7 above is the argument that recovered it.
5. **Whether charge state reaches the cup** — needs a *warm* charge on the same
   configuration dropped at the same BT to the tenth.

## Reference — facts and drills the work rests on

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
