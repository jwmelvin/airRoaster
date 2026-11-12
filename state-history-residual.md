# state-history-residual — the −2.9 degC residual, and measuring the machine on the bench

> **Effort:** roasts 56 and 57 both fall 2.9 degC below their own backgrounds at
> 165-170 s, from opposite signs going in. This file is the hunt for what causes
> it — and the bench programme that grew out of it, because the cheap
> measurements cost no beans. **2026-09-08 to 2026-09-10: phase 0, roast 57,
> two archive re-readings, and Phase A (roasts 58 and 59).** Closed: the FC
> temperature is a property of the lot, the background ramp was never fitted at
> all, the preheat lever is dead, the fan step is sized at `f = 0.18`, and
> **Phase B (roast 60) answered "both"** — the fan is 0.72-1.22 degC of the
> 2.9 and drying keeps the rest. **Open: the partition's second half**, and the
> precharge-inlet lever roast 60 stumbled into — state-plan.md § TEST PLAN.
>
> One of three history files. [state-history-cascade.md](state-history-cascade.md)
> is the controller work and [state-history-charge.md](state-history-charge.md)
> the reference-curve work that precede this. The index is
> [state-history.md](state-history.md); what is *current* is
> [state-current.md](state-current.md) and [state-plan.md](state-plan.md).
>
> **Read it in order, oldest first.** A finding here is current only if nothing
> below it says otherwise.

## Contents

- The FC temperature is a property of the lot, and the 198.8 mean was three coffees
- The ramp was never fitted at all — the solver defect in `make_background.py`
- The LA 12 plan, deferred
- Phase 0 — the Temp_Drive ladder, and heater duty is the honest effort variable
- Roast 57 — the preheat lever is dead, and the 140-200 s residual is a disturbance, not a lag
- Normalize the charge with the PREHEAT — the design roast 57 withdrew
- Roast 20 revisited — the inlet-schedule era, and what its smoothness is and is not
- Roasts 37 and 38 revisited — the archive already contains a controlled mass experiment
- Phase A — roasts 58 and 59: the fan step is sized, and it is big enough
- Phase B — roast 60: the fan is about a third of it, and the answer is "both"
- Is the dip the loop ringing? — no, but the loop owns its width
- Correction — Phase B did not cleanly size the fan, and the preheat is why
- The precharge inlet is set by the fan schedule, not by the soak
- Roast 61 — the fan ladder at held BT, and the leak seal is a null
- The preheat spec: fix the inlet, not BT
- Roast 62 — row P lands: the fan step is worth 1.4-1.7 degC
- The precharge inlet does not move the turning point — it sets the PID handover
- The drying term — row L authored on roast 62, and what the four-constraint solve does to it

## The record

### The FC temperature is a property of the lot, and the 198.8 mean was three coffees (2026-09-08)

The operator, asked about storing first-crack temperatures per bean: *"The saved
alog has the bean info, doesn't it? And the data itself indicates FC temp."*
Both true, and reading them settles a question that had been answered wrongly
twice.

**Every `.alog` carries the artisan.plus coffee id.** `plus_coffee` (the hr_id),
`plus_coffee_label`, `plus_store`, and a `plus_sync_record_hash`. So the lot is
identified exactly, and `BT(timeindex[2])` is the crack temperature. Nothing
needs recording by hand — `tools/analysis/beans.py` derives it.

**The lots, which nobody had checked:**

| roasts | `plus_coffee` | coffee |
|---|---|---|
| 50, 51, 52 | `C1074` | Colombia, Crown Jewel Carbonic Honey Peach Co-Ferment |
| 53, 54, 55 | `C1062` | Kenya, CJ Ichamama Factory Othaya Town |
| **43, 44, 45, 46, 49, 56** | **`C1043`** | **Ethiopia, Crown Jewel Sidama Daye Bensa Washed** |

**So "the mean over roasts 50-55 is 198.8" — the number the roast-56 background
was built on — is a mean over two different coffees, and describes neither.**
Per lot, on this machine, cascade-era (roast ≥ 40, ≥ 380 g):

| `plus_coffee` | roasts | FCs BT | median | spread |
|---|---|---|---|---|
| `C1074` | 50, 51, 52 | 201.2 / 198.1 / 200.1 | **200.1** | 3.1 |
| `C1062` | 53, 54, 55 | 197.4 / 197.3 / 198.7 | **197.4** | 1.6 |
| `C1043` | 43, 44, 46, 49, 56 | 197.4 / 197.7 / 197.8 / 197.9 / **195.3** | **197.7** | 2.6 |

**Three things follow, and two of them overturn earlier conclusions.**

**1. `profile_003`'s 197.5 was right, and moving it to 198.8 was the error.**
It is 0.1 degC from the Kenya's median and 0.2 from the Ethiopia's. The
"correction" of § Roast 55 raised the mark by 1.3 degC on the strength of a
pooled mean that included a Colombian sitting 2.7 degC above both.

**2. There was never a systematic FC lag.** § Roast 55 concluded *"the lag is
the mark, not the loop"* from **one** roast — 55's FCs at 408 s against 399.
Roasts 53 and 54 are the same coffee against the same mark and landed at
**397.5 and 395.5 s**, i.e. 1.5 and 3.5 s *early*. Roast 55's 198.7 is the
high outlier of its own three. The premise of roast 56's change 1 was noise.

It did no harm — roast 56 tracked v4 to +0.33 degC at the crack and under
0.5 degC from 250 s to DROP — but it was not a correction, and the change count
for roast 56 was really *one* control change plus a background edit that moved
nothing that mattered.

**3. Roast 56's 195.3 is the outlier of its own lot, not the lot's value.** The
other four 400 g cascade roasts of `C1043` sit in a 0.5 degC band at
**197.4-197.9**. 195.3 is 2.4 degC below all of them. Either a new bag under
the same hr_id — artisan.plus identifies the *coffee*, not the crop or the bag,
so it cannot distinguish one — or a crack marked early by ear. **`n = 1` against
`n = 4` in a 0.5 degC band: the lot's number is ~197.7, and 195.5 rests on the
single lowest reading in the set.**

#### What this does to the tooling

`tools/analysis/beans.py` derives the table rather than duplicating it, and
encodes four traps that each produced a wrong number here:

- **Group by `plus_coffee`, not the label.** `C1043` appears as both
  `Ethiopia, Crown Jewel Sidama Daye Bensa Washed` and
  `Crown Jewel Sidama Daye Bensa Washed`; grouping on the label splits one
  coffee in two.
- **`mode` can be `F`.** Roasts 1-15 are Fahrenheit and their `temp2` is degF.
  Unconverted, they put a 403.7 "degC" first crack in the table.
- **Filter on `roastertype`.** `~/Documents/artisan` holds ~530 logs from the
  operator's other roasters. The same `C1043` reads **204.5 degC** across
  eighteen 250 g roasts on the Behmor and **197.7** here. The filename prefix is
  not a reliable separator; `roastertype` is.
- **Do not pool across coffees, masses or eras.** The failure above.

#### And it sharpens the background-authoring warning

> **Superseded 2026-09-08, later the same day.** The numbers below are real
> outputs of the tool, but the cause diagnosed here is wrong: the spec is not a
> three-parameter fit and the first minute is not a side effect of the back-half
> marks. It was an **underdetermined solver**. See § The ramp was never fitted
> at all, below.

Roast 56's regeneration exercise had already shown that moving the FCs mark
reshapes the first minute, because the RoR spec is one three-parameter
exponential fitted to `BT(DRY END)`, `BT(FCs)` and `RoR(FCs)`. Sweeping the
constraint shows the early ramp is not even **monotone** in it — BT at 60 s,
400 g at −5 degC:

| `--fcs` | 198.8 | 197.7 | 197.4 | 195.5 |
|---|---|---|---|---|
| `--ror-at-fcs` | 8.3 | 8.3 | 8.1 | 8.3 |
| BT at 60 s | 78.1 | **73.3** | 74.1 | 74.5 |
| RoR peak at | 52 s | 73 s | 70 s | 69 s |

**A 1.1 degC change to a mark 340 s away moves BT at 60 s by 4.8 degC and the
RoR peak by 21 s**, and 195.5 lands *closer* to the v4 ramp than 197.7 does. The
first minute is a side effect of the back-half marks. Until the spec pins
something in the ramp as well, **never run a regenerated background and a
control change in the same roast**, and always print the 30-120 s column before
loading one.

### The ramp was never fitted at all (2026-09-08)

The section above closed with "until the spec pins something in the ramp as
well". Doing that turned up the reason the ramp needed pinning, and it is not
the one that section gives.

**`make_background.py`'s exponential RoR spec has four free parameters, and the
marks supply three.**

    RoR(u) = (1 - exp(-u/tau_r)) * (R_inf + (R0 - R_inf) * exp(-u/tau_d))

`tau_r, R0, R_inf, tau_d` — four. `--development` mode constrains `BT(DRY END)`,
`BT(FCs)` and `RoR(FCs)` — three. `--drop` mode constrains three BT marks —
also three. Every document in this repo, including the tool's own docstring,
said "three free parameters against three marks, so the marks are hit rather
than approached". The second clause was true. The first was not, and nobody had
counted.

So `least_squares` was solving a system with a **one-dimensional null manifold**,
and the four multi-starts were four draws from it. Fixing `tau_r` and refitting
the rest, at 400 g / −5 degC / `--fcs 399:197.7`:

| `tau_r` | 4 | 8 | 15 | 22 | 30 | 40 | 50 |
|---|---|---|---|---|---|---|---|
| `R0` | 54.3 | 57.9 | 65.1 | 73.5 | 84.5 | 100.0 | 116.9 |
| `R_inf` | 5.82 | 6.17 | 6.68 | 7.09 | 7.45 | 7.76 | 7.96 |
| `tau_d` | 142 | 133 | 121 | 110 | 101 | 92 | 86 |
| max\|resid\| | 3e-14 | 3e-14 | 0 | 3e-14 | 3e-14 | 3e-14 | 0 |
| **BT at 60 s** | 80.8 | 78.7 | 75.8 | 73.9 | 72.7 | 71.8 | 71.3 |
| **RoR peak at** | 44 s | 53 s | 64 s | 71 s | 77 s | 81 s | 83 s |

Every column hits all three marks to machine zero. They differ by **9.5 degC of
BT at 60 s and 39 s of peak timing** — the whole width of the window the four
roast checks are scored in. Which column came out was decided by which start
converged marginally lower on floating-point noise.

**That is the real explanation of the 4.8 degC.** The back-half marks hardly
constrain the ramp at all, and the "1.1 degC at 340 s away moves the first
minute by 4.8 degC, non-monotonically" was the solver sliding along the manifold
between one draw and the next. The non-monotonicity was the tell and it was read
as a property of the curve. It never was one. The four authored backgrounds show
the same thing directly: their RoR peaks sit at 65, 68, 53 and 69 s
(`m12C_v3`, `m12C_v4`, `m5C_v4`, `m5C_fc195_v5`) and nobody chose any of them.

#### The fix: pin the peak's time

`--ror-peak-at <s since CHARGE>`, default **53**, added as a fourth residual —
`ror_spec_deriv(u_peak) == 0`, the analytic stationarity condition, because an
`argmax` over the 1 s grid is a staircase a least-squares step cannot descend.
The system is square with it. What is left is the honest coupling:

| `--fcs` | 198.8 | 197.7 | 197.4 | 195.5 | spread |
|---|---|---|---|---|---|
| BT at 60 s, ramp free | 80.6 | 74.8 | 78.1 | 73.4 | 7.2 degC, non-monotone |
| BT at 60 s, peak at 53 s | 78.4 | 78.7 | 78.8 | 79.3 | **0.8 degC, monotone** |

0.25 degC of first minute per degC of a mark 340 s away, in the direction that
makes sense: a cooler FCs target needs a weaker decline, so slightly more rate
early to still make DRY END at 192 s. DRY END itself, 132 s away, moves BT at
60 s by 1.0 degC per 2 degC — larger, nearer, monotone. **A back-half edit is a
back-half edit again**, and one-variable-at-a-time attribution works.

Verified to 1e-14 with RoR monotone both sides of the peak across **−24…+25 degC
and 250…500 g**, in both `--development` and `--drop` mode. The reachable peak
band at 400 g / −5 degC is about **45-80 s**; outside it the residual does not go
to zero and the check block says so in as many words, because an unsatisfied pin
is an unpinned ramp.

#### Two choices worth recording

**The peak's *time*, not its height.** Height is nearly invariant along the old
manifold — 48.2 degC/min at `tau_r` 4 down to 43.5 at 50 — so
`d(peak height)/d(tau_r) = −0.10 degC/min/s` against
`d(peak time)/d(tau_r) = +0.85 s/s`. Pinning height to ±0.1 degC/min would buy
what pinning time to ±0.85 s buys; it is an eight-times-worse identifier of the
missing parameter. tools/README.md's line that the peak's timing "is not a spec
but is diagnostic" is now inverted: it is a spec, because something in the ramp
has to be, and it is the best-conditioned thing available.

**The default 53 s is not a measurement.** It is where `profile_400g_m5C_v4.alog`
happens to peak — roast 56's background, the only curve to have passed all four
checks — chosen so the fix reshapes nothing silently. It is one of the lottery
draws above, promoted to a spec so that it stops moving on its own. The
delivered peaks in the logs cannot supply a better number: roasts 51-54 peak at
36-39 s because the loop was slamming heat after the charge, and 55 and 56 peak
at 106 and 64 s because that is what their own backgrounds asked for. It is a
design parameter now, and the first roast that varies it deliberately is the one
that measures it.

`--decline linear` has three parameters and was always square; it takes no pin
and never had this defect. `--free-ramp` reproduces the old behaviour for
regenerating a pre-2026-09-08 file to compare against, with a warning saying the
ramp is undetermined.

**No background file was regenerated.** Roast 57 runs `profile_400g_m5C_v4.alog`
unchanged, as § HANDOFF specifies; this is desk work on the generator only.

### The LA 12 plan, deferred (2026-09-08)

Roast 57 was scoped as a lookahead switch — a 27th event button `LA 12`
(`pidLookahead(12)`) and an eighth alarm row at `CHARGE + 105`, aimed at roast
56's residual: dead on the curve at 120 s (−0.08) and **−2.91 degC by 200 s**,
the integrator's fill rate against the drying ramp. The sizing was phase
arithmetic — at 105-120 s the background runs 25-27 degC/min, so 12 s of
lookahead is worth ~5 degC of SV, and the SV step at 105 s should be
`(bkg(117) − bkg(111)) × 4.8 ≈ 17 degC`. 105 s was chosen because it precedes
the divergence and the loop is calm there (roast-56 error +0.46 to −0.08 over
105-120 s).

**The operator redirected roast 57 to the preheat step instead (2026-09-08), and
this is deferred rather than cancelled.** Three things to carry:

- **The config is already built and checked in** — `LA 12` and its alarm row are
  in `artisan/airRoaster_cascadePID_floor100.aset`. Nothing needs authoring.
  `pidLookahead(<n>)` takes an arbitrary integer (`main.py:10935-10945`).
- **Roast 57 keeps the baseline.** Its background converges to roast 56's by
  160-200 s (+0.62 / −0.12), so the 140-200 s residual stays comparable and the
  case for LA 12 is not weakened by the detour.
- **It may become unnecessary.** § Temp_Drive as the effort variable attacks the
  same lag *structurally* — it is the operating-point term of step 9's
  feedforward, supplied by measurement — and if that lands, a lookahead patch on
  a type-1 ramp error is treating a symptom the loop no longer has. **Decide LA
  12 after the Temp_Drive question, not before.**

**Do not try to size it with `replay_pid`.** It is fed measured BT, so a
sustained lookahead change reads as a permanent P offset the real loop would
erase as BT caught up — it reports `LA 12` commanding SV 278 at 300 s, which is
the artifact, not a prediction. The phase arithmetic above is the honest sizing.


### Phase 0 (2026-09-08, 19:17) — the Temp_Drive ladder, and heater duty is the honest effort variable

`artisan/airRoaster_empty_BT-target-steps.alog`, 41 minutes, empty chamber, PID
closed on BT, six settled rungs. Each figure is the mean over the last 90-120 s
of the rung, `Inlet` and `SV` agreeing to 0.01 degC throughout (the inner loop is
on setpoint everywhere).

| rung | BT | Temp_Drive | HT % | amb |
|---|---|---|---|---|
| 130, first | 130.02 | **7.80** | **45.37** | 27.59 |
| 140 | 140.05 | 7.88 | 46.88 | 27.70 |
| 145, first | 145.03 | 7.81 | 48.25 | 27.80 |
| 152 | 152.04 | 8.42 | 49.53 | 27.80 |
| 130, return | 129.99 | **6.28** | **45.14** | 27.74 |
| 145, return | 145.06 | 8.84 | 48.48 | 27.62 |

Every rung settled. **No abort criterion fired** and the schedule does not stop
below 152.

#### `d(TD)/d(BT)` clears stage A's kill criterion by a factor of twenty

OLS on the four first-pass rungs:

```
Temp_Drive = 4.48  + 0.0247*BT     resid rms 0.167
HT %       = 20.25 + 0.1922*BT     resid rms 0.175
```

**`d(TD)/d(BT) = +0.025`** — an order of magnitude below the 0.10-0.383 bracket
every document here has carried, and **20× below the ~0.5 that would have killed
§ Temp_Drive as the effort variable**. The drive→BT loop has a DC gain near 40
and is very nearly an integrator, which is the outcome the design wanted.

That conclusion survives the worst reading of the data. The largest slope any
pairing supports is 6.28 at 130 against 8.84 at 145 — **0.17** — still a third of
the kill threshold. **Stage A passes under every interpretation.**

#### But the slope is bounded, not measured — and that is the real finding

Temp_Drive moves **0.6 degC across the whole 22 degC ladder** while the two
same-BT repeats inside one session disagree by **−1.51 and +1.02**. The fit
residual (0.167) is ten times smaller than the repeatability, which is the
signature of a fit to drift. Heater duty over the same six rungs repeats to
**±0.23 %**, and its residual (0.175 on a 4.2 % span) is the same size as its
repeat error. **Duty is a state variable at this precision; Temp_Drive is not.**

The sign of the repeat error says what the drift is:

- the **130 return** came down from 152 — metal hotter than equilibrium — and
  read **1.5 degC low**;
- the **145 return** came up from 130 — metal colder — and read **1.0 degC high**.

Thermal hysteresis, correct sign both times. HT carries the same hysteresis with
the same signs (−0.23 and +0.22) at **six times less amplitude**.

**The independent cross-check is roast 57's own preheat**, 20 minutes later, same
fan, same BT: held at **BT 145.24 for five minutes with HT 48.70 and Temp_Drive
10.21**. Duty lands between the ladder's two 145 rungs (48.25 / 48.48). Drive is
out by **1.4 to 2.4 degC**. Same machine, same setting, same hour.

This is the operator's probe observation, quantified. `Inlet − BT` is a
difference of two large numbers, one of them read on the **non-flow side of the
asymmetric expansion chamber**, where the probe blends air with local metal on a
many-minute time constant. Duty is set by the air-side balance and re-equilibrates
in about three minutes; the roast-57 preheat shows HT flat from −3:00 while
Temp_Drive was still falling at −0:25.

**Consequences.** Stage A's number is delivered and its gate is open, but every
Temp_Drive figure in this project — the 11.62 / 11.92 / 13.19 / 13.45 across
roasts 53-56, the 10.25 prediction, the 29-94 degC drive range in stage B item 4
— carries ±1.5 degC of probe history that the readings themselves cannot show.
Size the drive range with margin and do not tune anything to a Temp_Drive
difference under ~2 degC.

**One gap in the record:** the ladder log contains **no `Air` event at all**, so
fan 60 rests on the operator's word rather than on the file. The HT agreement
with roast 57's preheat — which *does* record `Air 60` — is independent evidence
it was 60. Set the fan explicitly at the start of the next bench session so the
log carries it.

#### The empty loss line predicts the loaded roast, and `loss(t)` really is `loss(BT)`

`HT = 20.25 + 0.1922*BT` is the duty the empty chamber needs to stand still.
Subtract it from the live duty of a roast and the remainder — the power actually
going into the bed — is nearly proportional to the rate of rise. Post-DRY-END,
30 s centred RoR against 21 s smoothed excess duty:

| | roast 56 | roast 57 |
|---|---|---|
| fit | RoR = 0.81 + **2.66**·excess | RoR = 6.46 + **2.29**·excess |
| resid rms | 0.74 degC/min | 1.11 degC/min |
| over | RoR 5-25 degC/min, excess 3-10 % | RoR 2-23 degC/min, excess −5-7 % |

One parameter, measured on an empty chamber with no beans, tracking a 20 degC/min
sweep to about 1 degC/min. **That is the answer to the question § HANDOFF § 0
posed**: most of `plant_roast46.json`'s `loss(t)` cubic is a BT-dependent loss
aliased into a time function, and it can be replaced by a line measured on the
bench in forty minutes for no beans. The slopes agree to 15 %; the intercepts do
not (0.81 vs 6.46), so this is a *shape* result, not yet a calibration — roast 57
ran 4.6 degC warmer ambient and lost 357.7 g out of 400 g.

**The same line reads the machine's ceiling.** Post-DRY-END RoR is linear in BT
in both roasts — `RoR = 79.79 − 0.3657·BT` (roast 56, resid 1.46) and
`73.57 − 0.3357·BT` (roast 57, resid 2.52) — crossing zero at **BT 218.2 and
219.2**. At the duty the loop settles on and fan 60, the roaster asymptotes to
about **218 degC**, and the entire back-half RoR decay is first-order approach to
it rather than anything the controller is choosing.

### Roast 57 (2026-09-08, 20:04) — the preheat lever is dead, and the 140-200 s residual is a disturbance, not a lag

`profile_400g_m5C_pre145_v6.alog`, `airRoaster_cascadePID_preheat.aset`, 400 g
`C1043`, `greens_temp = −5.0`, `moisture_greens = 11.0`, out-weight 357.7 g.
**The roast is clean and single-variable.** Mass, greens temperature, lot, fan
schedule, gate and gains all match roast 56; only the preheat moved, 130.2 →
**145.24**. The alarm table behaved: `Air 64` at −7.5 s, `Air 60` at +120.0 s, the
`LA 6` switch as a **+19.30 degC SV step at 46.5 s**, and — the thing that had to
be right — **no SV step at 105 s**, so row 8 was genuinely off and this is one
variable, not two.

#### The primary measurement: `d(TP)/d(preheat) = 0.100`, and the decision rule says stop

| | roast 56 | roast 57 |
|---|---|---|
| preheat BT | 130.2 | **145.24** |
| precharge inlet / Temp_Drive / HT | 141.8 | **155.45 / 10.21 / 48.70** |
| **turning point** | **61.10 at 25.5 s** | **62.60 at 26.0 s** |
| model's TP | 59.25 | 65.48 |

**ΔTP = +1.50 degC for +15.04 degC of preheat.** The gain is **0.100** against a
predicted **0.415**, outside the 0.30-0.55 band that would have let the lever
stand, and inside § HANDOFF § 1a's explicit stop condition: *"ΔTP under ~2 → the
mechanism is not there and the whole preheat idea is dead."*

Read as a lever, `0.60 / 0.100` = **6.0 degC of preheat per degC of greens
temperature**. Normalising a 10 degC swing in bean temperature would need 60 degC
of preheat. The machine does not have it, and 145 was already 15 degC hotter than
the beans had ever been tipped into. **`preheat = 124.4 − 1.17 × greens_temp` is
withdrawn**, and so is the compensated-roast plan behind it.

The TP *time* did not move (25.5 → 26.0 s), exactly as the model said it would
not. That part of the dip model is fine. What is wrong is the energy bookkeeping.

#### Where the 15 degC went, and it is not where the model puts it

BT difference between the two roasts, against the difference the two backgrounds
predict:

| t | actual `57 − 56` | model `v6 − v4` |
|---|---|---|
| 0 | +15.30 | +15.00 |
| 10 | +8.50 | +9.28 |
| **20** | **+2.10** | **+6.86** |
| 30 | +1.80 | +6.24 |
| 40 | +4.20 | +5.86 |
| 60 | +8.80 | +4.98 |
| **70** | **+9.10** | **+4.58** |
| 90 | +7.70 | +3.78 |
| 120 | +4.20 | +2.57 |
| 160 | +1.20 | +1.04 |
| 200 | −0.10 | −0.23 |

Two things, and they point the same way.

**The preheat is gone by 20 s, and no control action removed it.** The cascade
engages at CHARGE+15.5 s, so the collapse from +8.5 at 10 s to +2.1 at 20 s
happens with the inlet still sitting where the preheat left it — *hotter* in
roast 57 by 13 degC. The extra 15 degC left the reading faster than the loop
could have taken it. `dT_mix = phi·(BT_c − T_bean)` treats the preheat reading as
the chamber's available energy; the ladder above says it is largely the probe and
the metal it sits against, on the non-flow side, and 400 g of −5 degC beans
overwrite the probe's local environment in under twenty seconds.

**It comes back late and doubled.** By 70 s the roasts are 9.1 degC apart where
the model says 4.6. That is not stored energy arriving — it is the loop. Roast 57
reached its turning point **2.9 degC below the curve it was tracking**, the
cascade saw the error, and drove the inlet to **175.9 at 30 s against roast 56's
135.8**. The +9.1 at 70 s is the price of a background that assumed the trade it
was asked to test.

**So the preheat is not inert — it is a slow lever pointed at the wrong window.**
It moves 30-120 s by more than the model predicts and the turning point by almost
nothing. Nothing in the current plan wants that shape.

#### Tracking degraded, and all four checks still pass

| check | roast 56 | **roast 57** | pass |
|---|---|---|---|
| peak SV, first minute | 165 | **180.8 at 49.0 s** | under ~200 — **pass** |
| seconds of heat at 100% | 1.0 | **0.5** | 0 — **near** |
| seconds saturated at own floor | 0.0 | **0.0** (min SV 156.1, floor 100) | **pass** |
| worst BT error vs background, 30-90 s | +2.2 | **+5.25 at 80.5 s** | single digits — **pass** |
| worst \|bkg − BT\| over 0-30 s | 3.7 | 7.64 at 3.5 s | — |

| roast | 0-30 | 30-90 | 60-95 | 95-120 | 120-DROP | 0-DROP | inner 50 s-DROP |
|---|---|---|---|---|---|---|---|
| 56 | 2.00 | **0.94** | **0.58** | **0.41** | 1.28 | **1.26** | 0.91 |
| **57** | 3.59 | 3.29 | 4.45 | 2.89 | **1.20** | 2.06 | 1.40 |

**The degradation is entirely the background's TP error propagating**, and it is
the expected consequence of the finding rather than a control regression: the
curve demanded a turning point 2.9 degC above what the machine delivered, the
loop chased it, and the overshoot decayed through 120 s. From 120 s on — where
both backgrounds have converged — roast 57 tracks *better* than roast 56 (1.20 vs
1.28). The controller is not the thing that changed.

#### First crack: 195.3 was the outlier, and `C1043` is 197.6

**FCs 197.40 degC at 397.0 s**, against v6's mark of 197.7 at 399 s — 0.3 degC and
2 s. `beans.py --coffee C1043` now reads nine roasts, cascade-era median
**197.55**, and recommends `--fcs <s>:197.6 --ror-at-fcs 9.4`. Roast 56's 195.3
stands alone 1.2 degC below the rest of its lot and is a mark made early by ear,
not a property of the bag. **`artisan/profile_400g_m5C_fc195_v5.alog` is retired**
— it was parked on that single reading.

This was the one question that needed `C1043`, and it is answered. **The
remaining loads are free for machine work on any coffee.**

#### The 140-200 s residual is a disturbance at a known time, and LA 12 was aimed at the wrong thing

BT minus its own background, the two roasts that ran the 45 s lookahead switch:

| t | roast 56 | roast 57 |
|---|---|---|
| 110 | +0.34 | +2.37 |
| **120 — `Air 60` fires** | **−0.08** | **+1.55** |
| 140 | −1.30 | −0.98 |
| 160 | −2.60 | −2.45 |
| **170** | **−2.76** | **−2.96** |
| 200 | −2.18 | −2.05 |
| 230 | −1.04 | −0.88 |

Different preheat, different background, **1.63 degC apart at 120 s and with the
error in opposite signs** — and both fall by about 2.9 degC over the next fifty
seconds, bottom within 5 s of each other, and recover by 230 s.

**A type-1 ramp error scales with how far behind the loop already is. This does
not.** Roast 57 entered the window 1.55 degC *ahead* and landed on the same
number at the same second. Whatever this is, it is a **disturbance the loop is
rejecting**, not a tracking lag the loop is accumulating — and § The LA 12 plan,
deferred was sized against the lag reading. Worse, 105 s would have pushed SV up
fifteen seconds before the disturbance and *masked* it without ever naming it.

Two candidates, and they are separable for free:

1. **The fan step at 120 s.** It is the only scheduled event in the window, and
   the delay to the residual's knee (~20-40 s) matches the plant's `theta` plus
   its lag.
2. **Evaporative load through DRY END** (196.5 / 197.0 s in the two roasts). The
   background's RoR spec carries no latent-heat term, so a real roast must fall
   behind wherever drying loads the bed hardest and recover once free moisture is
   gone — which is roughly this window and roughly this recovery.

**Move the fan step and the two separate.** `Fan 60` is one field in the alarm
table (row 7, `CHARGE + 02:00`). Fire it at 01:00 or 03:00 on the next roast: if
the dip travels with it, it is the fan; if it stays at 170 s, it is the drying
model. No beans, no firmware, no background regeneration — and either answer is
worth more than LA 12 was.

#### The fan gain, loaded, for the first time — and it costs no beans

§ Step 4/5 predicted that the circulation bump is *"a free fan step on every real
roast"*. It is, but only in roasts where the lookahead switch is at 45 s: the
inner loop holds the inlet on setpoint, so at a **flat** SV the duty change is the
flow change, and roasts 53-55 had SV ramping at 1.0-1.6 degC/s through the window
with no flat baseline to difference against.

Duty over 100-118 s vs 126-146 s, detrended on the 60-118 s slope:

| roast | HT before | HT after | detrended step | `dSV/dt`, 60-110 s |
|---|---|---|---|---|
| 53 | 58.58 | 52.92 | −14.47 | +1.022 degC/s |
| 54 | 61.08 | 54.80 | −16.20 | +1.232 |
| 55 | 62.33 | 53.33 | −18.95 | +1.629 |
| **56** | 56.44 | 52.77 | **−4.17** | +0.079 |
| **57** | 53.56 | 50.88 | **−3.54** | **−0.207** |

Roasts 53-55 are unreadable — the detrend is extrapolating a steep SV-driven ramp
across the step and the numbers are nonsense, which is itself the caution. Roasts
56 and 57 give **0.9-1.0 % of heat per fan unit over 64 → 60**, matching the
empty-chamber preheat regression's **0.992** exactly. **The loaded fan gain equals
the empty one**, and Test C's fan question is answered for the 64/60 step without
spending a batch.

**Sizing a compensation, if the fan turns out to be the cause.** The inner loop
holds the inlet on SV, so at fixed inlet the duty is proportional to mass flow and
the step reads a **6.6-7.4 % flow reduction**. Holding `mdot·(Inlet − BT)` constant
across it needs `ΔSV = TD·f/(1−f)` ≈ **+3.7 degC** at the observed `TD ≈ 49`. But
the ladder's duty line extrapolates to zero air `ΔT` at about **25 % duty**, and if
a quarter of the duty is a flow-independent loss then the flow-proportional part
falls 12 % and the number is **+6.9 degC**. **Bracket +3.7 … +6.9 degC**, and one
free bench measurement closes it — a *fan* ladder at fixed BT on the empty
chamber, which the phase-0 session was already set up to run.

### Normalize the charge with the PREHEAT — the design roast 57 withdrew (2026-09-08)

*Written as a plan section on 2026-09-08 and withdrawn the same day by roast 57.
Kept here in full because the reason it failed is worth more than the lever was
— see the Roast 57 section above, and state-current.md § 6.*

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
> state-history-residual.md § Roast 57; the mechanism is in state-history-residual.md § Phase 0 —
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

---

### Roast 20 revisited (2026-09-08) — the inlet-schedule era, and what its smoothness is and is not

**The operator's observation:** the early inlet-profile roasts got a very smooth
response. They did, measurably — and the reason cuts two ways.

`airRoaster_20.alog` (2026-07-03, 250 g, `bkgd_inlet_150+30-265@330.alog`) is the
cleanest of them. **Three special events in the whole log** — `T_inlet 100` at
−34 s and `Air 60` twice — and an inlet that ran 150 → 265 degC anyway. There was
no outer loop and no hand on the slider: Artisan's `playbackevent` replayed the
background's eight `T_inlet` events and the firmware kept the fractional value
because *"Artisan's ramped INLET playback"* would otherwise quantise to 1 degC
steps (airRoaster.ino:1203-1205).

#### It is smooth, and by a factor of five

Post-dip (60 s onward), fitting each roast's own 30 s centred RoR to a cubic in
`t` and reading the residual:

| roast | config | RoR span | inlet vs its own cubic | worst 10 s inlet move | **RoR vs its own cubic** |
|---|---|---|---|---|---|
| **20** | playback schedule, no outer loop | 47.6 → 13.8 | **0.42 degC** | **5.7 degC** | **0.375 degC/min** |
| 46 | cascade | 40.6 → 9.1 | 8.17 | 36.7 | 1.809 |
| 56 | cascade | 43.6 → 9.4 | 5.24 | 33.6 | 1.612 |
| 57 | cascade | 50.4 → 9.0 | 7.75 | 18.7 | 2.769 |

**The roughness is in the input, not the plant.** The cascade's inlet command
deviates from a smooth curve by 12-18× what the playback schedule does and jumps
up to 36.7 degC in ten seconds — the lookahead switch alone is a +19 to +24 degC
step at 46 s. The plant low-passes it, so BT comes out 4-7× rougher rather than
15× rougher, but the causal direction is not in doubt. High-frequency roughness
is identical across all four (`|d²RoR|` rms 0.50 / 0.52 / 0.55) — that is probe
noise, and it is not what separates them.

**And the inner loop was excellent.** Against the commanded polyline, roast 20
tracks at **rms 0.60 degC, worst −1.88, over 20-330 s**. The schedule itself is
not a straight line: eight events giving a **decelerating ramp, 28.0 → 12.0
degC/min** in seven segments. That is a hand-authored `ff(t)`, and it is the
shape § The structural fix wants to compute.

#### The smoothness *is* the absence of excitation, and that is a hard limit

**Roast 20 cannot identify the plant.** Fix `theta = 13.5 s` and profile the
residual of `dBT/dt = a·(Inlet(t−θ) − BT) + slow(t)` over a grid of `a`, with
`slow` a quartic, 60-340 s:

| `a` | 0.000 | 0.002 | 0.004 | 0.006 | 0.008 | 0.010 | 0.012 | 0.016 |
|---|---|---|---|---|---|---|---|---|
| **roast 20** resid, degC | 0.0876 | 0.0878 | 0.0882 | 0.0887 | 0.0894 | 0.0902 | 0.0912 | 0.0935 |
| **roast 46** resid, degC | 0.611 | 0.375 | 0.163 | 0.175 | 0.391 | — | 0.868 | — |

Roast 20's residual moves **7 % across the entire physical range of `a`** and is
*monotone increasing*, so its best fit is **`a = 0`** — no plant at all, BT is a
polynomial in time. `fit_integral` left free returns `a = −0.0007` at
`theta = 0`. Roast 46, over the same kind of window, has a sharp minimum at
**0.0049** and swings 5× either side.

A smooth input carries no information about the transfer function, because a
low-order `slow(t)` reproduces the output exactly. **This is the whole reason
Tests A/B/C author doublets and steps**, and it is a caution against reading
plant numbers off any well-behaved roast — the better the roast looks, the less
it can tell you.

#### What roast 20 does prove, and it is the thing step 9 needed

**The playback path works end to end on this machine and always did.** Eight
events on type 2, replayed into the inner loop, tracked at rms 0.60 degC, with no
manual intervention for the whole roast. § The base-curve authoring gap was never
about the *mechanism* — it was about the **file**: `make_inlet_background.py`'s
`--events` mode emits an inlet-only background with `temp2 = −1.0` and no DRY END
or FCs, so the outer PID has nothing to follow. `tools/merge_inlet_base.py`
(2026-09-06) closes exactly that, and roast 20 is the evidence that what comes
out the other side will be replayed the way the plan assumes.

#### Three things it does not settle

- **Smooth is not on target.** Roast 20 has no BT curve to score against at all.
  It landed DRY END 169 s / FCs 297 s / DROP 343 s at 250 g, and nothing in the
  record says whether that was the roast that was wanted. The cascade exists to
  put those marks where they are asked for; the smoothness comparison above does
  not touch that.
- **Open-loop repeatability is unmeasured.** Roast 26 is the only other titled
  inlet-schedule roast and it ran a *different* schedule by hand (a staircase —
  its inlet deviates from a cubic by 17.2 degC), so the archive has no repeat pair.
  One smooth roast says nothing about the next one on a colder morning.
- **Different everything.** 250 g against 400 g, a different lot, pre-v0.19.0
  firmware with no `HT` channel, and a much faster roast (FCs 297 s against
  373-397 s).

**One suggestive detail, offered as suggestive only.** Roast 20 set `Air 60` at
−26 s and at CHARGE and **never stepped the fan again** — and its RoR shows no
mid-roast feature at all (worst cubic residual −1.13 degC/min at 61 s, nothing
across 120-200 s), where roasts 56 and 57 both carry −2.8 to −2.9 degC of BT
deficit bottoming at 170 s. That is consistent with § Roast 57's fan-step
hypothesis and is not evidence for it: three other things differ. **The alarm-time
test remains the one that settles it.**

#### The reading this supports

Step 9's case was never "the cascade tracks badly" — roast 56 tracks its
background at rms 0.94 degC over 30-90 s. It is that **the outer loop's integrator
has to supply the entire operating point, and the ramp it produces to do that is
the roughness in the table above.** Roast 20 is what the inlet looks like when
something else supplies the operating point. **Keep the smooth schedule and add a
bounded trim** — which is what § The structural fix says, now with the base
mechanism demonstrated and the input-roughness cost of not doing it measured.

### Roasts 37 and 38 revisited (2026-09-09) — the archive already contains a controlled mass experiment

The operator pointed at the early 250 g work (roasts 18-30, 33, 38, 39, plus a
161 g roast 28 and 450-575 g roasts 5, 6, 8, 37) as evidence for how the machine
behaves at other charges. **Roasts 37 and 38 are better than evidence — they are
a paired experiment**, and nothing in this project had read them that way.

Same bean (Panama Elida Estate Natural), same session (2026-08-23), 450 g and
250 g, and the **same commanded inlet schedule**: eight `T_inlet` events at
t = 2, 96/97, 192/193, 281/282, 330/331, 365/366, 395/396, 420/421 s carrying
identical values (160, 197, 226, 248, 257, 263, 267, 270 degC). Within 1 s and
0 degC on every step. These were open-loop inlet-curve roasts, so the input is
*authored* rather than closed-loop — which is exactly what makes the pair
readable.

#### The measurement

Regress `dBT/dt` (centred, ±5 s) on the driving temperature `Inlet − BT`, over
CHARGE+70 s to FCs−10 s — past the dip, short of the crack:

| | roast 37 | roast 38 |
|---|---|---|
| charge | 450 g | 250 g |
| `k = dBT/dt` per degC of drive | **0.01727** | **0.02095** |
| r² | 0.92 | 0.95 |
| n | 364 | 311 |
| fan | 64 → 53 | 60 → 54 |
| DRY END | 224 s | 186 s |
| FCs | 445 s | 392 s |

`k` is `h/(m·c + C)`, so the ratio **1.213** is the capacity ratio. DRY END gives
**1.204** independently on the same pair; FCs gives 1.135, which is lower because
the crack is an exotherm and the two roasts do not reach it in the same state —
DRY END is the cleaner of the two marks.

Solving `(450 + X)/(250 + X) = 1.213`:

> **X ≈ 690 g of bean-equivalent thermal mass that is not the beans.**

Roast 38 ran 3-6 fan units below roast 37, so it had the smaller `h` of the two;
that biases its `k` down and the ratio down, and therefore **690 g is an upper
bound** on the parasitic capacity.

#### Why it matters

The plant's gain is dominated by the machine, not the charge. Going 400 → 250 g
raises `k` by `(400+690)/(250+690) = ` **1.16** — the excess-duty → RoR slope
moves 2.66 → ~3.1 and the outer loop wants ~0.86× its gain. Even at half the
parasitic mass it is 1.33. **A batch-size change is a 15-35 % perturbation, not
the 1.6× the mass ratio implies**, so one roast at 250 g re-points the loop
rather than re-characterising it.

It also says something about § Step 9 and § Temp_Drive: a plant whose capacity is
mostly fixed hardware is one whose `a` moves *little* between batch sizes, which
strengthens any design carrying a plant card and weakens the argument that the
card has to be re-fitted per charge.

#### Two cautions, and one correction to the record

**161 g is below the useful floor and the data shows it.** Roast 28 fits the same
regression at r² **0.73** against 0.92-0.99 for every other roast tried, with a
`k` *below* the 250 g roasts — which a single-capacity model cannot produce. The
operator's stated reason for choosing 250 g (below it the beans no longer cover
the probe while circulating) predicts exactly this. One roast, so corroboration
rather than measurement.

**The other 250 g roasts are not a ladder.** Across roasts 18-33 `k` ranges
0.0138-0.0210 at the same nominal charge — bean, moisture, fan and era all move.
Pairs drawn across sessions give `X` of 3600-5100 g, which is not a measurement
of anything. **Only 37/38 hold the input fixed, and only 37/38 should be quoted.**

**Fan levels in this project were being read 10 units high.** Artisan stores
special-event values as `level/10 + 1`, so the `Fan FULL` button's 7.4 is fan
**64**, not 74. Decoded correctly the archive's 250 g roasts ran **fan 60 flat**
(20, 21, 25, 29, 33) — the same as the 400 g cascade roasts' sustain level — and
roast 28 at 161 g ran 59-60. **Smaller charges did not run less fan**, which is
the expected result: minimum fluidisation velocity is a bean property, and a
smaller charge changes bed depth and pressure drop rather than the velocity
needed to lift a bean. The declining ramps in 37 and 38 did reach **53 and 54**,
under `ilFanFull = 55` — so the soft interlock's heat cap has been inside the
operating envelope before, and it is the *declining-fan practice* rather than the
batch size that puts it there.

### Phase A (2026-09-10, 18:25 and 19:31) — roasts 58 and 59: the fan step is sized, and it is big enough

`airRoaster_58.alog` (63 min, empty, `TEST_FAN_LADDER`) and `airRoaster_59.alog`
(44 min, 345 g of already-roasted beans, `TEST_LADDER_WITH_BEANS`). The second is
the operator's addition to the plan and it is the more valuable of the two: it
puts a bed in the chamber, which is the configuration the roast actually runs in.
Everything below is reproduced by `tools/analysis/fan_ladder.py`.

**Both logs record `Air` explicitly** — A0 is done, and the gap phase 0 left is
closed.

#### The answer: `f = 0.18`, against a decision threshold of 0.12

`HT = A·(fan − f0)·(Inlet − amb) + c` fits at the duty channel's own 1 %
quantisation:

| fit | f0 | A | c % | rms | n / params / dof |
|---|---|---|---|---|---|
| empty, fan 53-64 | **39.2** | 0.009405 | 22.65 | **0.182 %** | 10 / 3 / 7 |
| loaded 345 g, fan 56-64 | **42.9** | 0.010228 | 22.96 | **0.202 %** | 11 / 3 / 8 |
| joint, shared `A` and `c` | **40.0 / 41.9** | 0.009737 | 22.73 | **0.231 %** | 21 / 4 / 17 |

```
f(64 -> 60)   empty 0.162    loaded 0.189    joint 0.181     threshold 0.12
deficit = RoR * f * T_eff / 60   at RoR 29.0, T_eff 45 s:   3.5 - 4.1 degC
                                            observed residual:   2.93 degC
```

**The fan is not merely sufficient, it over-covers by about a third** — which is
the room the plan's own caveat asked for, since less flow also raises
`T_in − T_out` and the arithmetic is a ceiling. **Decision rule: the top row.
Run Phase B expecting the dip to disappear.**

`c = 22.7-23.0 %` is the flow-independent duty, now **measured** rather than
extrapolated 5× back to zero air ΔT from a 22 degC ladder. The plan carried
`c = 24.9 %` and was close.

#### The bed costs 9.3 % of the flow, and the blower saturates above fan 64

`A = K·α` and `c` belong to the heater and the blower, so they must be shared
between the two sessions and only `f0` may differ. Pooling onto **one** `f0`
costs a factor of **5.5** in residual (1.281 % against 0.231 %), so the split is
real: at fan 60, `(60 − 41.9)/(60 − 40.0) = 0.907`. **345 g of beans is a 9.3 %
flow restriction.**

With `f0` pinned by the fan 53-64 rungs, the two top rungs fall progressively
short of the linear-flow model:

| rung | predicted HT | measured | deficit | delivers the flow of |
|---|---|---|---|---|
| fan 72 | 57.56 | 55.87 | **−1.69** | a nominal **70.4** |
| fan 80 | 65.43 | 60.18 | **−5.25** | a nominal **75.0** |

`mdot ∝ (fan − 40)` holds across the range the roast uses and bends over above
it. **The ladder's top rungs are therefore not the ones that size `f`**, which
is the opposite of the plan's reason for spanning 60-80; the sizing came from
53 / 56 / 60 / 64, and the plan's own worry — that 60 → 64 alone is too small a
contrast — was answered by the *descending* rungs the operator added, not by the
ascending span.

#### Route 1 cannot be run on this machine

`Temp_Drive ∝ 1/mdot` at fixed BT needs `Inlet − BT` to be a measurement. It is
not. Empty at BT 145 / fan 60, four visits in one session read **12.84, 8.47,
6.51 and 7.49** while heater duty over the same four repeated to **±0.09 %** —
and at fan 72 and 80 the settled `Inlet` sits **below** BT (−2.07 and −3.57),
which `1/mdot` cannot produce at all. This is § Phase 0's "duty is a state
variable at this precision; `Inlet − BT` is not", reproduced at 8× the sample
count, and the plan's "the two routes must agree or report it" resolves as
**route 1 is unavailable, not disagreeing**. The empty/loaded agreement on `f0`
and the direct step response below stand in for it.

#### The direct step response, loaded — the part that needs no model

Roast 59 held BT 145 under the same cascade with 345 g in the chamber and stepped
the fan. Against a 90 s pre-step baseline:

| step | `f` | peak ΔBT | at |
|---|---|---|---|
| 60 → 64 | −0.23 | **+0.49** | 46 s |
| **64 → 56** | **+0.38** | **−0.67** | **54 s**, recovered by ~130 s |
| 56 → 58 | −0.15 | −0.34 | 38 s — in the noise |
| 58 → 60 | −0.13 | −0.27 | 3 s — in the noise |

**The timing is the finding.** The roast residual bottoms 45-50 s after the 120 s
fan step and has recovered by 230 s, 110 s after it. The bench step bottoms at
54 s and recovers by ~130 s. Same loop, same shape, and it is the first direct
evidence that a fan step on this machine produces a BT transient of the residual's
shape at all.

The empty chamber's steps peak at **14-18 s** instead, because with no bed the BT
probe is reading a convection/radiation balance that moves in seconds. That is
why A3 was rated low value and it was right — it is the *loaded* step that
transfers.

**Do not read a magnitude out of the bench step.** At a settled BT 145 the
delivered power is the chamber loss alone — `Inlet − BT` is about 2 degC loaded —
while at 145 s of roast 56 it is **60 degC** (roast 57: 49). The same `f` removes
25-30× more power in the roast, and scaling the bench dip linearly predicts 8-10
degC where the roast shows 2.9. Read the sign, the shape and the timing; the
magnitude comes from the duty model above.

#### A2: the duty line is linear to BT 190, and no rung failed to settle

Four rungs each at fan 60, read over the last 120 s:

```
empty    HT = 15.16 + 0.2165*BT      residuals  -0.00 -0.05 +0.11 -0.06
loaded   HT = 17.75 + 0.1788*BT      residuals  +0.06 -0.09 +0.00 +0.03
```

Residuals at the duty quantisation across a 45 degC span. **Nothing is
superlinear**, `HT` at fan 80 reached only 60.2 % against the 85 % abort, and the
empty chamber has **no ceiling below BT 190**. The plan's first candidate
explanation for the excess-duty model's intercept disagreement — a superlinear
loss — is **dead**.

#### But phase 0's line is not this line, and the loaded line does not transfer

| BT | phase 0 `20.25 + 0.1922·BT` | this empty | this loaded |
|---|---|---|---|
| 145 | 48.12 | 46.55 (**−1.57**) | 43.67 (**−4.45**) |
| 160 | 51.00 | 49.80 (−1.20) | 46.35 (−4.65) |
| 175 | 53.89 | 53.05 (−0.84) | 49.04 (−4.85) |
| 190 | 56.77 | 56.29 (−0.47) | 51.72 (−5.05) |

About 0.47 % of the empty gap is this session's 2.4 degC warmer ambient
(`d(HT)/d(amb) = −A(60 − f0) = −0.196 %/degC`). The slopes are consistent —
0.1922 was fitted over 22 degC where 0.2165 is fitted over 45 — so the
disagreement is a **level**, and there are two candidates and no way to separate
them from this data: the soak (below), or phase 0's unrecorded fan being a unit
or two above 60, one unit being worth ~0.96 % of duty.

**Re-basing the excess-duty model onto the loaded line does not work.** It moves
roast 56's fit from `RoR = 0.81 + 2.66·excess` to about `−11.7 + 2.66·excess`,
i.e. a loaded chamber standing still would be cooling at 12 degC/min. It is not.
345 g of *roasted* beans sitting at fan 60 is not 400 g of circulating greens: no
water leaves it, it may not be circulating at 56-60 at all, and the BT probe is
buried in a static pile.

**What survives is the size of the question.** The excess-duty model's intercept
disagreement between roasts 56 and 57 is 5.65 degC/min, which at its own 2.66
slope is **2.1 % of duty**. The baseline candidates measured here span **4.5 %**.
So the disagreement is a baseline-level question, the baseline level is not
pinned to better than the disagreement itself, and the empty line's apparent
success is to that extent luck. **No re-basing on this data settles it** — say so
rather than picking the line that flatters the fit.

#### The soak: the abort criterion fired, and the cause is the cold start

Roast 58 began on a cold machine (BT 29.0 against ambient 29.5). At fan 60 /
BT 145 its duty decayed **50.5 → 47.6 %** over the first seven minutes and only
reached 46.5 % by 23 minutes. Three later fan-60 / BT-145 visits, spanning 23 to
62 minutes, then agreed to **0.18 %** — 46.55 / 46.49 / 46.67.

So Phase A's stated criterion — *"rung 5 must reproduce rung 1's HT to ±0.5 %.
If it does not, the session drifted and the fit is not trustworthy"* — **failed**:
rung 1 read **1.22 % high**. The criterion did its job and the diagnosis is the
cold start, not drift in the measurement. Roast 59, run an hour later on the
soaked machine, settled in three minutes and its first rung matched its last to
0.3 %.

**The duty model absorbs the soak anyway, and that is informative.** Rung 1's
residual against the fit is **+0.03 %**, because the soak raises `Inlet` and `HT`
*together* and the model is written in `Inlet`, not BT. `HT = A·mdot·(Inlet − amb)
+ c` is a statement about the **heater** — the power to raise air from ambient to
the inlet setpoint — and is indifferent to what the chamber is doing. It is the
BT-referenced line `HT(BT)` that a soaking chamber breaks, because a soaking
chamber is not standing still. That is why rung 1 is kept in the fit and excluded
from the `HT(BT)` line.

**For the next bench session: soak for 20 minutes before the first rung, or run
it second.** It costs one rung and it is the difference between phase 0's numbers
and these.

### Phase B (2026-09-13, 13:52) — roast 60: the fan is about a third of it, and the answer is "both"

The test state-plan.md § Phase B specified: one roast, one change — alarm row 7
off, fan **64 held from before CHARGE to DROP**, everything else roast 56's.
`C1043` at 400 g, `greens_temp −5.0`, `moisture_greens 11.0`, background
`profile_400g_m5C_v4.alog`, config `airRoaster_cascadePID_phaseB.aset`.

#### B3 — the change ran, and the gate held

| check | required | roast 60 |
|---|---|---|
| `Air` events after CHARGE | **none at 120 s** | none; `Air 64` at −5.5 s, next is `Air 0` at 473 s |
| SV step at 105 s (row 8) | absent | absent — `T_inlet` climbs 165 → 167 through 102-108 s |
| `LA 6` step at ~46 s | present | present, **151 → 172** at 46.0 s |
| `T_inlet` between +1 s and `PID ON` | empty | empty — events at 1.0 s then 15.5 s |

**B6 passes on all four**: 400 g, greens −5.0, no drifted alarm row, no `Air`
event at 120 s.

#### The auto-DROP alarm works, and the heat-off chain that failed on roast 56 fired

Row 9 (`HT` below 20 % from DRY END, offset 00:00) fired on the extra-channel
sample at **414.61 s**, where `HT` fell 70 → 17 and `Inlet` rose 228.0 → 249.0 in
one sample. The DROP mark landed at **414.50 s** — on the spike, not after it.

```
         t       Inlet     SV      HT         roast 56, for comparison
    414.07      228.0   227.7    70          mark at 392.0
    414.61      249.0   227.7    17   <- alarm   SV climbed 230.9 -> 255.2
    415.03      252.0   227.7     4          HT went 38 -> 90 -> 100 %
    415.60      245.5     0.0     0   <- heat off   heat reached 0 at +17.5 s
```

**`SV` and `HT` both reach 0 within 1.0 s of the mark.** That closes the roast 56
anomaly recorded in state-plan.md § The inlet spike beats the RoR collapse — the
detector is worth having *and* the chain behind it fires. Both alarms were armed
(row 2, `DeltaBT < −25`, and row 9); row 9 fired first and row 2 never acted,
which is the guard in Artisan v4.2.0 `canvas.py:6260` doing its job —
`elif action == 13 and self.timeindex[6] == 0` sits in `processAlarm`, *before*
`markDrop()`, so a second DROP alarm is a no-op rather than an undo.

#### B4 — the primary read: the dip shrinks by a third to a half, and does not go away

`BT − background` on the 0.5 s grid:

| | roast 56 | roast 57 | **roast 60** |
|---|---|---|---|
| e at 120 s | −0.08 | +4.12 | **+0.42** |
| minimum | **−2.91** @ 165 s | −2.60 @ 182 s | **−1.69 @ 168 s** |
| rms 120-230 s | 1.97 | 2.08 | **1.15** |
| swing from 120 s to the minimum | −2.83 | −6.72 | **−2.11** |

```
  t     100    110    120    130    140    150    160    170    180    190    200    210    220    230
 56   +0.46  +0.34  -0.08  -0.62  -1.30  -1.92  -2.60  -2.76  -2.60  -2.64  -2.18  -1.64  -1.12  -1.04
 60   +1.96  +0.84  +0.42  -0.42  -0.90  -1.62  -1.50  -1.56  -1.60  -1.24  -1.08  -0.94  -0.82  -0.54
```

**This is the "both" row of B4's decision table**, and the table's predicted band
for it was −1.2 to −2.0. The dip is still there, at the same second, with the
same shape — it is **shallower by 1.22 degC read as an absolute minimum, or by
0.72 degC read as the swing from 120 s.** Take the pair as the bracket; § below
says why the lower figure is not dismissible.

**The fan is real and it is far smaller than its own ceiling.** Phase A's
`f = 0.181` predicted a ceiling deficit of **3.93 degC** (joint) and the fan's
share of the 2.93 was put at 2.68. Removing the step removed **0.72-1.22**, i.e.
**18-31 % of the ceiling**. The ceiling was honest about being a ceiling; it was
not a useful estimate of the size.

**What is left — 1.69 degC at 168 s, recovering to −0.54 by 230 s and to zero by
300 s — is the drying term, or whatever else lives in that window.** DRY END is
at 194.0 s, and the residual bottoms 26 s before it and is two-thirds gone 36 s
after it. That is the shape the latent-heat hypothesis wants.

#### The duty model composes — this is the strongest result in the roast

Phase A's `HT = A(fan − f0)(Inlet − amb) + c`, with the joint loaded coefficients
`A = 0.0097371`, `f0 = 41.9`, `c = 22.73`, fitted on a bench ladder with an empty
chamber and 345 g of *roasted* beans, predicting the duty difference between two
*live roasts* at different fan, different ambient and different inlet:

| window | 56 `HT` | 60 `HT` | observed Δ | model Δ | **residual** |
|---|---|---|---|---|---|
| 130-200 s | 56.36 | 60.92 | +4.56 | +4.63 | **−0.07** |
| 200-300 s | 59.05 | 64.53 | +5.48 | +4.85 | **+0.64** |
| 300-370 s | 60.54 | 66.87 | +6.33 | +5.21 | **+1.12** |

Inlet ran *lower* in roast 60 (201.4 → 196.3 in the first window) and ambient
5.7 degC warmer, both of which cut duty; the model carries all of it. B5 asked
for +3 to +5 % raw and got +4.6 to +6.3, which looks like a miss until the two
corrections are applied — after which the first window is exact.

**So the +4.6 % of duty is the fan, measured, not an inference.** The dip
shrinking by only a third while the duty rose by exactly what the fan predicts is
therefore not a failure of the fan step to happen. It happened; it is worth less
than the ceiling arithmetic said.

#### B5 — the excess-duty model does **not** transfer across fan, on either baseline

Method reproduced from § Phase 0: 30 s centred RoR against 21 s smoothed excess
duty, post-DRY-END. The method check reproduces the published fits (roast 56
`1.27 + 2.57·excess`, resid 0.57, against the recorded `0.81 + 2.66`, resid 0.74;
roast 57 `5.90 + 2.43` against `6.46 + 2.29`).

| baseline | roast 56 | roast 57 | **roast 60** |
|---|---|---|---|
| phase 0's empty `HT(BT)` line | `1.27 + 2.57·e` (0.57) | `5.90 + 2.43·e` (0.78) | **`−33.33 + 4.23·e` (1.32)** |
| the duty model at that roast's fan | `27.27 − 8.94·e` (4.07) | `13.62 − 6.61·e` (3.53) | `28.29 − 5.89·e` (1.84) |

**Both baselines fail, for different reasons.**

- The **fan-60 empty `HT(BT)` line** is simply the wrong baseline for a fan-64
  roast: it leaves ~5 % of duty unaccounted in every sample, so the excess range
  collapses from 6.6 % of span to 3.7 % and the fit runs away — intercept −33.3
  against 0.81 and 6.46. Shifting the line by the modelled +5.2 % moves the
  intercept to ~−11 and leaves the slope wrong, so this is **not** a level
  problem that re-basing fixes.
- The **duty model as a standing-duty baseline** gives a *negative* slope on all
  three roasts, which is physically backwards. It is fitted in `Inlet` over the
  bench range and inside a roast `Inlet` runs to 230; the modelled standing loss
  then grows faster than the real one and eats the whole excess (roast 56's
  excess range collapses to 0.9-1.8 %). **The duty model predicts levels between
  roasts and must not be used as an in-roast baseline.**

**One observation, offered as a question rather than a finding.** The excess-duty
slope moved 2.57 → 4.23 (+65 %) from fan 60 to fan 64. The flow ratio
`(64 − 41.9)/(60 − 41.9)` is **1.22**, so the direction is right and the size is
not. Nothing here separates a real fan dependence of the slope from the artefact
of fitting over a collapsed excess range. **Do not carry 4.23 anywhere.**

#### The four checks, and a charge phase that is worse

| check | roast 56 | **roast 60** | pass |
|---|---|---|---|
| peak SV, first minute | 165.1 @ 57.1 s | **180.6 @ 21.6 s** | under ~200 — **pass** |
| seconds of heat at 100 % | 1.0 | **2.6** | **worse** |
| seconds saturated at own floor | 0.0 (min SV 159.3) | **0.0** (min SV 159.4) | **pass** |
| worst `BT − bkg`, 30-90 s | +2.17 @ 32.5 s | **−4.74 @ 30.0 s** | single digits — **pass**, sign flipped |
| worst \|e\| over 0-30 s | 3.65 | **7.84** | **worse** |

Tracking rms against the same background:

| roast | 0-30 | 30-90 | 60-95 | 95-120 | **120-DROP** | 0-DROP |
|---|---|---|---|---|---|---|
| 56 | 2.00 | **0.94** | **0.58** | **0.41** | 1.28 | **1.26** |
| **60** | 5.47 | 2.28 | 2.54 | 1.47 | **0.73** | 1.88 |

**From 120 s to DROP roast 60 tracks better than any roast on record (0.73
against 56's 1.28 and 57's 1.76)** — which is what removing a scheduled
disturbance from that window should do. Everything worse is before 100 s, and
§ below is why.

#### The precharge inlet was 8.8 degC low, and it is a second variable

B1 specified the preheat as roast 56's **130.2 BT / 141.8 inlet**. Roast 60 held
**BT 130.1** and the inlet settled at **132.8**.

| | roast 56 | roast 60 |
|---|---|---|
| preheat BT at −10 s | 130.2 | 130.1 |
| `SV` / `Inlet` at −10 s | 142.1 / 141.8 | **132.8 / 132.7** |
| `HT` at −10 s | 45.9 | 49.0 |
| preheat recorded before CHARGE | 9.7 min | **23.8 min** |
| ambient | 22.7 | 28.4 |

**Nobody set this; the soak did.** Holding BT 130 on a chamber whose walls have
had 24 minutes to come up needs 9 degC less inlet than one 10 minutes in. This is
§ The soak: the abort criterion fired, restated on the roasting side — **a
preheat specified in BT is not a state of the machine**, and "preheat 130.2 /
141.8" is a pair of numbers only one of which the operator controls directly.

**What it cost: the turning point is 8.3 degC deeper.**

```
  t      0      5     10     15     20     25     30     40     50     60     90    120
 bkg  130.2  103.8   81.6   69.0   62.4   59.7   59.2   63.5   70.7   78.1   98.8  116.6
  56  130.2  106.2   83.6   71.0   63.9   61.3   61.2   64.6   69.9   77.0   99.5  116.5
  60  129.8  103.9   77.7   62.4   54.7   52.8   54.5   61.7   70.3   79.2  101.6  117.0
```

TP **52.8 @ 24.5 s** against 56's **61.1 @ 25.5 s**. The loop absorbs it: back on
background by 50 s, 1-2.4 degC *above* it from 60 to 95 s, and only **+0.5 degC**
different from roast 56 at 120 s.

**So the measurement window is contaminated, but lightly.** The honest statement
is the bracket already given: the fan removed **0.72 degC** if the entry offset
at 120 s is charged against it and **1.22 degC** if it is not. Both sit in B4's
"both" band; neither approaches the 2.68 the ceiling arithmetic predicted.

**And it is an accidental preheat experiment that separates two levers roast 57
could not.** Roast 57 raised preheat BT by 15.0 *and* inlet by 13.7 and moved the
TP by **+1.50** — gain 0.100 per degC of BT. Roast 60 held BT constant and
dropped the inlet 8.8, moving the TP by **−8.3** — gain **0.94 per degC of
inlet**, nine times larger. § Roast 57's conclusion that "the preheat is a slow
lever aimed at the wrong window" was drawn on the wrong variable: **it is the
preheat BT that is inert, and the precharge inlet that moves the turning point
nearly one for one.** One roast each, confounded with soak time and 5.7 degC of
ambient, so this is a hypothesis with a number on it, not a lever. **It is also
the cheapest open question in the project** — it needs no beans to hold the inlet
where the spec says, only a longer or shorter soak.

#### The lot, and the rest

`C1043`, FCs at 384 s / **BT 196.9**, against roast 57's 197.4 and the pooled
197.6 — confirming § First crack: 195.3 was the outlier. DROP at 414.5 s /
BT 200.6, DTR 7.4 %, weight 400.0 → 354.5 g (**11.38 %** against roast 57's
10.58 %). Post-DRY-END `RoR(BT) = 71.15 − 0.3173·BT`, zero at **BT 224.2**,
against 222.6 and 226.7 for roasts 56 and 57 — the asymptote is not moved
by the fan in any way this can see.

### Is the dip the loop ringing? (operator, 2026-09-13) — no, but the loop owns its width

The operator, looking at roasts 56-60 in Artisan: *"it looks like the 130-200
(really about 130-240 s) dip is part of the control ringing as it converges on
the BT target."*

**The observation is well-founded and the timescales really do coincide.** At the
shipped `Ki = 0.07` the loop has a phase margin of **33.7 degC** and a crossover
period of **213 s** (`roast46_refit.py` § 4) — genuinely underdamped, and a
213 s period puts a quarter-cycle at 53 s against an excursion that takes ~45 s
to bottom. Anything that shape, in a loop that lightly damped, *should* be
suspected of being the loop. Four tests say it is not, and none of them needs a
plant model.

#### 1. The entry overshoot varies 8× and the trough does not care

Each roast against **its own** background:

| roast | e at 100 s | e at 120 s | trough |
|---|---|---|---|
| 56 | +0.46 | −0.08 | **−2.91** @ 165.0 s |
| 57 | **+3.68** | +1.55 | **−2.98** @ 175.5 s |
| 60 | +1.96 | +0.42 | **−1.69** @ 167.5 s |

**Under ringing the undershoot is a fixed fraction of the overshoot that precedes
it.** The overshoot spans 8× across these three and the trough moves by 4 %
between the two extremes. The only thing that *did* move the trough is the fan
(roast 60), which is not a term in the loop's dynamics at all.

#### 2. The integrator winds monotonically and never reverses

`SV` is the PID's output in Follow-Background — `(SV − 100)/2 = Kp·err + Iterm`
on the `[100, 300]` map — so the split can be backed out of measured data with no
model:

```
roast 56    t    100    120    140    160    180    200    220    240    260    280
          err  +3.13  +3.32  +4.22  +5.24  +4.99  +4.34  +3.07  +2.47  +1.88  +1.58
        Iterm  24.72  27.80  30.09  34.57  40.74  45.54  50.74  53.05  55.85  57.80
           HT   55.4   56.5   52.5   55.0   57.5   57.2   57.5   59.1   60.5   60.0

roast 60  err  +1.63  +2.82  +3.82  +4.14  +3.99  +3.24  +2.77  +2.27  +1.88  +1.58
        Iterm  26.92  27.80  31.14  35.47  39.39  43.69  47.04  50.15  52.10  54.10
           HT   51.5   54.2   57.2   60.0   61.9   61.8   63.0   64.0   63.2   66.0
```

**The integrator climbs monotonically across the whole window — 24.7 → 57.8 and
26.9 → 54.1 — and never unwinds.** So does `HT`. A ringing loop's integrator
oscillates; this one is winding up against something and holding what it wins.
The lookahead error never changes sign either: `err` is positive at every sample
from 100 to 280 s in both roasts.

#### 3. The loop rings in simulation and the roasts do not

`sim.py`'s closed loop, driven from the same background with the same gains and a
**smooth** loss (a cubic in `t`, which cannot manufacture a 40 s feature),
started exactly on the background at 100 s with `Iterm` matched to the measured
`SV`:

```
   t        110    130    150    170    190    210    230    250    270    290
sim (56)  -1.27  -2.50  -1.65  -0.48  +0.39  +0.86  +0.97  +0.80  +0.55  +0.41
sim (60)  -1.50  -3.05  -2.23  -0.86  +0.24  +0.88  +1.06  +0.97  +0.71  +0.42
real 56   +0.34  -0.62  -1.92  -2.76  -2.64  -1.64  -1.04  -0.41  -0.22  -0.22
real 60   +0.84  -0.42  -1.62  -1.56  -1.24  -0.94  -0.54  -0.31  -0.22  -0.12
```

**The simulated loop does exactly what a 33.7 degC phase margin predicts: it dips,
then overshoots to +0.9 to +1.2, then settles.** The real roasts never cross back
— the largest error anywhere from the trough to DROP is **+0.43** (roast 56, at
360 s) and **+0.37** (roast 60, at 372 s), over 200 s of run, more than a full
crossover period. **A loop that just rang 2.9 degC down does not come back inside
±0.4 and stay there.** The real traces decay to zero without a second crossing,
which is a disturbance being rejected.

*(The simulation's own dip at 128-130 s is a start-up transient of the initial
conditions and the roast-46 plant card; it is not evidence of anything and is
quoted here only for the sign of what follows it.)*

#### 4. The reference has no feature to track

A type-1 loop's error follows the reference's rate, so a kink in the background's
RoR would show up as an excursion without any disturbance at all. The background
has none:

```
   t        100    120    140    160    180    200    220    240    260    280    300
bg RoR    36.47  32.91  29.71  26.83  24.24  21.91  19.82  17.93  16.24  14.71  13.34
dRoR/dt  -11.22 -10.12  -9.10  -8.19  -7.37  -6.63  -5.96  -5.36  -4.82  -4.34  -3.90
```

Smooth and monotone in both, through the whole window. `corr(e, bg RoR)` over
100-300 s is **−0.10** (roast 56) and **+0.15** (roast 60) — nothing.
`make_background.py` builds the curve from an integrated RoR specification, so
this is what it is *for*; it is worth having checked rather than assumed.

#### What the operator's reading does own: the width

**The loop's dynamics set the shape and duration of the excursion, and the
disturbance sets only its cause and rough size.** A 213 s crossover period is why
a disturbance lasting a few tens of seconds takes ~45 s to reach its worst and
~110 s to come back; the 130-240 s envelope really is the loop's signature, drawn
around something exogenous.

**This has a consequence for the latent-heat term** (§ Phase B, runbook row L):
the observed −1.69 degC error is the *closed-loop response* to the drying load,
not the load. The underlying disturbance is **narrower in time and larger in
amplitude** than the error trace shows, and the RoR term authored into
`make_background.py` has to match the load, not the error. **Do not fit a
latent-heat term to the shape of the residual.**

### Correction (2026-09-13) — Phase B did not cleanly size the fan, and the preheat is why

**§ Phase B reported the fan as worth 0.72-1.22 degC. That bracket is too
narrow and the lower end of the real range is zero.** The correction came out of
authoring work for the drying term and it is recorded here because the committed
number is wrong, not merely uncertain.

**The two roasts entered the measurement window on different slopes.** Fitting
`e = BT − background` over 85-115 s:

| roast | e at 100 s | e at 120 s | **slope at 85-115 s** | trough | swing from 100 s | from 120 s |
|---|---|---|---|---|---|---|
| 56 | +0.46 | −0.08 | **−1.22 degC/min** | −2.91 | **−3.37** | −2.83 |
| 57 | +3.68 | +1.55 | −6.65 | −2.98 | −6.66 | −4.53 |
| 60 | +1.96 | +0.42 | **−5.01 degC/min** | −1.69 | **−3.65** | −2.11 |

**Roast 56 entered the window nearly flat and roast 60 entered it falling at four
times the rate**, still decaying from the charge-phase overshoot its off-spec
precharge inlet caused. Measured from 100 s the excursion is **−3.37 (fan 60)
against −3.65 (fan 64)** — the fan removed nothing and may have cost 0.3.
Measured from 120 s it removed 0.72; measured as an absolute minimum, 1.22.

**The answer depends entirely on a reference point the experiment does not fix,
so the honest range is about −0.3 to +1.2 degC and Phase B's decision table
cannot be scored.** Linear extrapolation of the entry trend does not rescue it
either — the entry is a decaying transient, not a line, and extrapolating roasts
57 and 60 to their troughs returns −4.8 and −3.7, i.e. nonsense.

**What survives Phase B unchanged:** everything that did not depend on the
120-230 s error — the duty model composing to −0.07/+0.64/+1.12 %, the auto-DROP
alarm and its heat-off chain, the 0.73 rms tracking from 120 s to DROP, and the
qualitative result that **the dip is not gone at fan 64**, which still rules out
the top row of B4's table. The fan's *size* is what is not measured.

**The lesson is the one the project keeps re-learning**: a 1 degC effect at 165 s
cannot be measured through a 2 degC entry transient that is still decaying at
120 s. **The preheat is not a side variable in this programme; it is the noise
floor of every measurement in it.**

### The precharge inlet is set by the fan schedule, not by the soak (operator, 2026-09-13)

**The section this replaces blamed roast 60's low precharge inlet on its 23.8
minute soak. That was wrong, and the operator said so:** *"the preheat this time
was at fan 64 by the end (stepped up fan over the 20+ min preheat) — and that
strongly affects the inlet-BT required for a particular BT."* It does, and it is
the whole effect.

**The gap is flat within a fan segment and steps at every fan change.** Roast
60's preheat ran three fans; skipping the first two minutes after each step:

| | fan 55 | fan 58 | fan 60 | **fan 64** |
|---|---|---|---|---|
| settled `Inlet − BT` at BT 130 | 23.66 ± 4.39 | 12.36 ± 0.90 | 11.13 ± 0.70 | **2.83 ± 0.61** |
| settled `Inlet` | 154.2 | 142.7 | 141.4 | **133.1** |

(fan 58 is roast 56, the other three roast 60.) **Decay *within* a segment is
−0.16 degC/min at fan 60 and −0.22 at fan 64** — over the seven minutes roast 60
spent at fan 60, about 1 degC. The soak is a rounding error against an 8.3 degC
step.

**And the two roasts charged on opposite sides of a fan step.**

```
roast 56   Air 58 at -577 s ......... Air 64 at -5.5 s ... CHARGE
           inlet settled at 142.7, reads 141.8 at -10 s, 141.9 at -1 s
           -- the fan stepped 5.5 s before CHARGE and the inlet had not moved at all

roast 60   Air 55 at -1420 ... Air 60 at -789 ... Air 64 at -361 s ... CHARGE
           inlet settles 139.9 -> 135.4 (+30 s) -> 133.0 (+60 s) and stays
```

**The inlet settles to a new fan's equilibrium in about 60 s.** Roast 56 charged
5.5 s after its step, so it charged with *fan-58 air at fan-64 flow*. Roast 60
charged with fan-64 air at fan-64 flow, six minutes settled. Same BT, same fan at
CHARGE, **8.8 degC of inlet apart, and the soak has nothing to do with it.**

**The advice that produced this was mine and it was right for what it was for.**
§ The soak: the abort criterion fired says to soak 20 minutes before a bench
ladder, because a cold chamber's *duty* was still drifting at seven minutes. That
finding stands and the operator applied it correctly. **What was wrong was
reaching for it to explain a roast**, without first checking the fan schedule in
the log — which is the one thing that had visibly changed.

#### The gap collapses between fan 60 and 64, and `1/mdot` does not explain it

`mdot ∝ (fan − 40)` gives 18 / 20 / 24 for fans 58 / 60 / 64, so a gap that goes
as `1/mdot` should run 12.4 → 11.2 → **9.3**. Measured: 12.4 → 11.1 → **2.8**.
Fans 58 and 60 are on the line and **fan 64 is nowhere near it** — an 8.3 degC
collapse across four fan units against 1.3 across the previous two.

This is an *empty* chamber, so bed fluidisation is not it, and Phase A put blower
saturation above 64 rather than at it. **The leading candidate is the probe:**
the operator describes an asymmetric expansion chamber with the bean probe on the
non-flow side, so if the main jet starts washing it somewhere around fan 62 the
probe stops reading a mixed temperature and starts reading the air. That would
mean **"preheat BT 130" is not the same physical state at fan 58 and at fan 64**,
which matters well beyond the preheat.

**It is a bench measurement and costs no beans:** hold the inlet SV fixed on an
empty chamber and step the fan 56 → 70 in twos, letting each rung settle 90 s,
and watch the gap. If it has a knee near 62 the probe explanation is live; if it
follows `1/mdot`, something else is going on at 64.

### The preheat spec: preheat at the charge fan, settled

**Preheat at the fan you will charge at, and leave at least 2 minutes after the
last fan change.** Then `Inlet − BT` is a fixed property of that fan to ±0.6 and
the precharge inlet is simply `BT_target + gap`. One knob, one readout, no
timing to get right.

**At fan 64 the gap is 2.8, so a preheat BT target of 139 lands the inlet at
~141.8 — roast 56's charge inlet, exactly.** That is runbook row P: fan 64 held,
`profile_400g_m5C_v4.alog` unchanged, `..._phaseB.aset` unchanged, and the single
change from roast 60 is the preheat BT target, 130 → 139.

**Why 139 rather than reproducing roast 60's 130/133.1.** The authored background
expects a turning point near 59.4 and roast 60 delivered 52.8; entering the
measurement window flat is what Phase B lost and what row P has to buy back.
Matching roast 56's precharge inlet is the only way to do that which does not
rely on the dip model, whose inlet sensitivity is 7× too small (§ below).

**It also runs the complement of roast 60's accidental experiment.** Against
roast 56, row P moves the preheat BT +8.8 and the inlet +0.0; roast 60 moved the
inlet −8.8 and the BT +0.0. Two roasts, two clean single-variable reads, and
together they settle which of the two actually moves the turning point.

#### The dip model has the two preheat gains in the wrong order

`make_background.py --charge-bt / --inlet-precharge`, `--mass 400
--greens-temp -5`:

| | modelled TP | gain |
|---|---|---|
| charge BT 130.2 → 139.5, inlet ~142 | 59.4 → 62.0 | **0.28** per degC of BT |
| inlet 141.8 → 132.8, charge BT 130.2 | 59.4 → 58.2 | **0.13** per degC of inlet |

Against the roasts: **0.100** per degC of preheat BT (roast 57) and **0.94** per
degC of precharge inlet (roast 60). **The model says BT matters twice as much as
the inlet; the machine says the inlet matters nine times as much as BT.** Both
roast readings are single roasts confounded with soak and ambient, so neither is
a calibration — but the *ordering* disagrees, and that is enough to stop the
model being used to author a dip at a preheat point no roast has visited.

**So reproduce a measured preheat point rather than authoring for a new one**,
until a deliberate pair settles the two gains. Roast 60 already supplies half of
that pair (inlet moved, BT held); the complement is BT moved with the inlet held,
which a fully-soaked roast at preheat BT ~139.5 would deliver.

### Roast 61 (2026-09-13, 19:56) — the fan ladder at held BT, and the leak seal is a null

An empty chamber with BT held at 130 by the cascade, the fan stepped 54 → 70 in
twos and then partly back down, ~110 s a rung. **The operator sealed air leaks
at t = 1711.8 s**, inside the descending fan-58 rung, and flagged it. Three
questions, three answers.

#### 1. There is no knee — the gap is `1/mdot` and my probe hypothesis is dead

Settled `Inlet − BT` over the last 60 s of each rung, BT 130, ambient 28:

| fan | 54 | 56 | 58 | 60 | 62 | 64 | 66 | 68 | 70 |
|---|---|---|---|---|---|---|---|---|---|
| gap | +23.71 | +16.42 | +11.78 | +7.44 | +3.64 | **+0.80** | −0.53 | −2.11 | −3.52 |
| inlet | 154.1 | 146.8 | 142.0 | 137.7 | 133.8 | 130.9 | 129.5 | 128.0 | 126.6 |

**Smooth and monotone through the whole range.** Fitting every rung from both
legs and both sides of the seal, with a session-drift term:

```
gap = (A0 + A1*(t - 525))/(fan - f0) + B
A0 = 492.0   A1 = -0.0412 /s (-2.47/min)   f0 = 42.83   B = -20.46
rms 0.345 degC over 15 rungs, 4 parameters, 11 dof, fans 54-70
```

`f0 = 42.83` against Phase A's **41.9 loaded** from an entirely different
measurement (duty, not gap). **The 60 → 64 "collapse" reported in
§ The precharge inlet is set by the fan schedule was an artefact of mixing
unsettled readings from two different roasts** — roast 60's fan-60 segment gave
11.13 where the settled ladder gives 7.44, because it was seven minutes into a
session that drifts. There is no discontinuity, so **the probe-washing
hypothesis is withdrawn** and no further test of it is needed.

**What is real is the sign change.** The gap crosses zero near fan 65 and the
inlet settles *below* BT above it. That is the same thing Phase A saw at fans 72
and 80 (§ Route 1 cannot be run on this machine) and it is now bracketed: it
begins at 65, not somewhere past 70. `1/mdot` alone cannot produce it — the `B`
term, **−20.5 degC**, is what does, and it is the part of the chamber's balance
that does not come through the air.

#### 2. The leak seal is a null, and the rung that straddles it says so

| fan 58 | window | BT | Inlet | gap | HT |
|---|---|---|---|---|---|
| **pre-seal** | 1652-1712 | 130.00 | 138.58 | **+8.58 ± 0.51** | 43.27 |
| **post-seal** | 1821-1881 | 130.02 | 138.31 | **+8.29 ± 0.35** | 43.23 |

**−0.29 degC of gap and −0.03 % of duty**, inside the ±0.5 scatter of a single
rung. The four post-seal rungs also fit the pre-seal curve with no offset —
residuals +0.08, −0.43, −0.25, +0.23 against a 0.345 rms.

So state-plan.md § The leak's premise — that a parallel path is stealing a
worth-sealing fraction of the flow — **is not supported**: whatever was sealed
was worth less than 0.3 degC of gap at fan 58, i.e. under a fifth of a fan unit.
The operator raised the seal as a possible confound on this session; it is not
one, and the rest of the session can be read as a single machine.

#### 3. The apparent hysteresis is session drift, and it is on the numerator

Every repeated rung reads lower the second time — fan 54 **23.71 → 17.01**, fan
58 11.78 → 8.58, fan 60 7.44 → 6.18 → 5.22, fan 62 3.64 → 2.17 — and the size
scales as `1/(fan − f0)`, which is why one `A1` absorbs all of it. **The chamber
warms through the session and the numerator falls at 2.47 per minute**, so the
gap drifts at **−0.117 degC/min at fan 64** and **−0.221 at fan 54**. It is not
hysteresis in the fan and it is not the seal.

**This is the number that decides the preheat spec**, § below.

### The preheat spec: fix the inlet, not BT (operator, 2026-09-13)

The operator: *"I propose we preheat at a fixed inlet temp, then we know the
machine's starting point. BT is relevant to beans, not preheat air."*

**Adopt it.** The ladder makes the argument quantitative. The session drift has
to land on *some* variable: hold BT and the inlet drifts at 0.117 degC/min at
fan 64; hold the inlet and BT drifts instead. **The precharge inlet carries most
of the leverage on the turning point and the preheat BT is nearly inert** (§ 6;
roast 57's BT gain is 0.100), so putting the drift on BT costs roughly a ninth of
what putting it on the inlet costs. Over a ±10 minute uncertainty in when CHARGE
happens that is ~0.1 degC of turning point instead of ~1.1.

It is also the variable the operator *commands* — the inlet SV is set directly,
where BT is a PID's controlled variable and the inlet is that PID's output. **A
preheat specified in BT is specified in the one quantity the controller pins
regardless of the machine's state**, which is what made roasts 56 and 60 look
identical when they were 8.8 degC apart.

**Spec: fan 64 from the start of the preheat, `T_inlet` SV fixed at 141.8,
CHARGE when BT has been flat for 2 minutes. Record BT — it is a readout, not a
setting.** Expect BT ≈ 139-141: at fan 64 the fitted gap runs +2.8 early in a
session to +0.5 after twenty more minutes.

#### Why the fan must not be stepped near CHARGE — and what it may have been doing

**Roasts 56 and 57 both stepped the fan to 64 within 8 s of CHARGE**
(58 → 64 at −5.5 s; 60 → 64 at −8 s) and the inlet had not moved at all by
CHARGE — roast 56 read 141.9 at −1 s against a settled fan-58 value of 142.7.
**They charged with fan-58/60 air at fan-64 flow.** Roast 60 stepped at −361 s
and charged settled.

That reconciles a contradiction § 1b could not. Read as an inlet lever, roasts 56
and 57 say the gain is **0.11** and roasts 56 and 60 say **0.94**, which cannot
both be true. Read as a fan-step burst, it is one story: 56 and 57 both got the
burst and land within 1.5 degC of each other **despite 14 degC of preheat
difference**, and 60 had no burst and lands 8.3 degC deeper.

**This is a hypothesis, not a measurement** — no roast has isolated it — but it
is the more economical explanation, and either way the instruction is the same:
**preheat at the fan you will charge at.** A fan step in the last minute puts a
slug of hotter air through the bed at the new flow, inside the PID-off window
where nothing corrects it.

**Row P now measures the settled inlet gain directly.** Against roast 60 — same
settled fan 64, same background, same `.aset` — it moves the commanded inlet
133.0 → 141.8 and nothing else. If the turning point comes back to ~61 the gain
is near 0.94 and the inlet is the lever; if it stays near 53 the gain is near 0.1
and the burst was doing the work in roasts 56 and 57.

### Roast 62 (2026-09-13, 20:54) — row P lands: the fan step is worth 1.4-1.7 degC

The first roast since 56 to enter the measurement window flat, and the first
whose answer does not move with the reference point.

#### The charge was reproduced, and the operator improved on the method

Row P asked for roast 56's charge state. The operator got it by **holding the
inlet SV fixed at 142.0 through the whole preheat and trimming BT with the fan**
(58 → 60 → 62 → 58 over −573 to −97 s), then stepping to 64 at −5.5 s — roast
56's step timing exactly.

| at −2 s | roast 56 | **roast 62** |
|---|---|---|
| Inlet | 141.8 | **142.0** |
| BT | 130.4 | **130.6** |
| fan | 64 (stepped −5.5 s) | **64 (stepped −5.5 s)** |

**That is the fixed-inlet preheat § The preheat spec argued for, run a better way
than the spec described** — the spec assumed BT would be left to float, and using
the fan as the BT trim at fixed inlet pins both. Worth adopting as the method.

#### The gate, and it is the whole reason this roast is readable

| | roast 56 | roast 60 | **roast 62** |
|---|---|---|---|
| entry slope, 85-115 s | −1.22 | −5.01 | **−0.03 degC/min** |
| | pass | **fail** | **pass** |

#### B4 — and for the first time every reference point agrees

| | roast 56 (fan 60) | **roast 62 (fan 64)** | the fan's share |
|---|---|---|---|
| minimum | −2.91 @ 165 s | **−1.50 @ 179 s** | **1.41** |
| swing from 100 s | −3.37 | **−1.66** | **1.71** |
| swing from 120 s | −2.83 | **−1.12** | **1.71** |
| rms 120-230 s | 1.97 | **1.06** | |

```
  t     100    110    120    130    140    150    160    170    180    190    200    210    220    230
 56   +0.46  +0.34  -0.08  -0.62  -1.30  -1.92  -2.60  -2.76  -2.60  -2.64  -2.18  -1.64  -1.12  -1.04
 62   +0.16  -0.16  -0.38  -0.82  -1.00  -1.22  -1.20  -1.36  -1.40  -1.14  -0.98  -0.94  -0.72  -0.64
```

**The 120 s fan step is worth 1.4-1.7 degC of the 2.9, and about 1.5 degC
survives at fan 64.** The range is now the spread between three ways of reading
the same curve rather than a disagreement about which reading to trust — which is
exactly what the entry gate was added to buy.

Against Phase A: the ceiling arithmetic predicted 2.68-3.93 and the fan delivers
**about half** of it. The withdrawn Phase B figure of 0.72-1.22 was too low.
**What is left — 1.5 degC bottoming at 179 s, 14 s before DRY END — is the
drying term's**, and runbook row L can now be sized on this roast.

#### B3, B5, and the DROP alarm

All of B3 passes. No `Air` event after CHARGE at all; `T_inlet` carries nothing
between `markCharge`'s +1.0 s re-record and the handover; `LA 6` present at
46.0 s (136 → 158); no step at 105 s (167 / 168 / 169 through 103-107 s).

**The auto-DROP alarm fired on the spike again and the chain held** — `HT`
69 → 20 at −0.37 s, `Inlet` 226 → 246, `SV` to 0 at **+0.70 s**. Two for two
since roast 60.

| | 56 | 60 | **62** |
|---|---|---|---|
| peak SV, first minute | 165.1 @ 57.1 s | 180.6 @ 21.6 s | **167.6 @ 58.1 s** |
| seconds of heat at 100 % | 1.0 | 2.6 | **0.5** |
| min SV after 50 s (floor 100) | 159.3 | 159.4 | **162.9** |
| **rms 120 s → DROP** | 1.28 | 0.73 | **0.67** |
| `HT` 130-200 / 200-300 / 300-370 | 56.36/59.05/60.54 | 60.92/64.53/66.87 | 63.18/67.95/70.89 |

**Best tracking on record and the best four-check row on record.** FCs BT
**197.3** for `C1043` against the pooled 197.6; DROP 419.5 s at BT 201.3; weight
loss 11.40 %.

#### The PID was off at CHARGE and came on at +14.0 s — the operator's manual push changed nothing

The operator: *"i wasn't sure if PID was turned on when the roast started so i
pushed it manually as the dip looked to be going low."* The log answers it
exactly:

```
  t     0.0   2.0   4.0   6.0   8.0  10.0  12.0  14.0 | 15.0  16.0  17.0
 SV   142.0 142.0 142.0 142.0 142.0 142.0 142.0 142.0 | 137.0 137.0 138.9
 BT   130.4 122.8 110.3  97.8  87.1  78.2  71.1  65.3 |  63.3  61.3  59.8
```

**`SV` sits at 142.00 exactly while BT falls 65 degC.** No running PID does that.
The first move is at **+14.00 s**, and row 6's `PID on` alarm is `CHARGE + 00:15`
— on the 0.5 s grid that is the same event. Whether the button or the alarm got
there first cannot be distinguished and does not matter: the handover happened
where it was meant to, and the gate held.

**The dip going low was correct behaviour, not a fault.** BT bottoms at 53.8 at
27 s in every roast of this configuration; the loop is deliberately held off
until +15 s so that the charge transient is not chased.

### The precharge inlet does not move the turning point — it sets the PID handover

**Roast 62 kills the 0.94 gain reported in § 1b.** It carries roast 56's
precharge inlet and roast 60's charge state, and it returns **roast 60's turning
point**.

`charge_state.py`'s air-corrected mixing proxy, which is control-independent:

| roast | proxy /100 g | inlet_pre | logged greens | TP |
|---|---|---|---|---|
| 56 | **14.10** | 142.0 | −5.0 | **61.1** |
| 57 | 16.92 | 155.3 | −5.0 | 62.6 |
| 60 | **15.80** | 133.0 | −5.0 | **52.8** |
| 62 | **15.87** | 141.9 | −5.0 | **53.8** |

**Roasts 60 and 62 are indistinguishable in charge state (15.80 against 15.87)
and roast 56 sits 1.77 lower.** All four logged `greens_temp −5.0`, and the
operator's account of why that does not settle it is decisive: *"they well could
have been colder beans. i try to measure, but there's a ton of noise in the IR
sensor (emissivity sensitive)."*

**Two independent instruments say the beans were 12-17 degC colder.** The proxy
above inverts to `T_bean` −7.8 (roast 56) against −24.8 / −24.9 (roasts 60 / 62);
independently, `make_background.py`'s dip model needs `--greens-temp ≈ −2.5` to
reproduce roast 56's turning point of 61.1 and `≈ −14.5` to reproduce roast 62's
53.8. A control-independent BT-drop proxy and a fitted mixing model inverted
against the dip share no data and no parameters, and they agree on direction and
on size to about 30 %. **The entered number is a nominal and the IR gun reads the
bean surface**, which warms within minutes of leaving a freezer while the core
does not — a warm bias that grows with time out, which is exactly the shape of
the disagreement.

**It is a bias and not scatter — roasts 60 and 62 agree to 0.07** — so the fix is
to standardise the *handling*, a fixed time out of the freezer, and verify it with
the proxy. **None of it affects what follows** — the inlet gain below is read
from roasts 60 and 62, which agree on the charge.

- **the precharge-inlet gain is 0.11**, from roasts 60 and 62 at the same charge
  state and inlets 8.9 degC apart — and that matches roast 57's 0.11 exactly.
  **The 0.94 read off roasts 56 and 60 is withdrawn** — those two differ in
  something besides the inlet, and roast 62 is the control that separates them;
- **what does set the turning point is not identified.** It tracks the charge
  proxy across these four roasts and not the inlet, but the proxy is an
  inference and `greens_temp` was −5.0 in all of them;
- **and the precharge inlet's real job is the handover.** At +15 s the PID
  inherits whatever SV the preheat left. Roast 60 handed it **132.8** against a
  demand near 142, so it slammed to **180.6 by 21.6 s** and spent 100 s unwinding
  the overshoot — the −5.01 entry slope. Roasts 56 and 62 handed over **142** and
  peaked at **167.3** and **167.6**, both around 60 s, both entering flat.

**That is why the fixed-inlet preheat is right, and the reason is not the dip.**
`--inlet-precharge` in the dip model is nearly inert and correctly so; what the
precharge inlet buys is a loop that starts from the right operating point instead
of catching up through the measurement window.

**One consequence for every future roast: log the charge proxy and check it
before pairing two roasts.** Roasts 60 and 62 agreeing to **0.07** is what makes
their 0.11 inlet gain trustworthy; roast 56's 1.77 gap is why it cannot be paired
with either on the charge. Record `greens_temp` *and* how long the beans were out
of the freezer — the entered temperature was identical across all four and did
not predict the proxy.

### The drying term (2026-09-13) — row L authored on roast 62, and what the four-constraint solve does to it

Desk work, no beans. Roast 62 is the only roast that entered the measurement
window flat, so it is the only one whose residual is not contaminated by a
charge-phase transient, and it is what the term is sized on. The other three
readable roasts enter at −1.22 (56), −6.65 (57) and −5.01 (60); **nothing here
is fitted to 57 or 60.**

#### 1. What the residual says, read as a load rather than as an error

The feature's period is near 100 s, **2.1× the loop's 213 s crossover period**,
and at 2× crossover a 33.7 degC phase margin gives `|S| ≈ 1` — essentially no
rejection. So through the descent the RoR deficit `−d(e)/dt` reads the load
directly (§ Is the dip the loop ringing?). Fitting `e = BT − background` over a
centred 30 s window and differentiating:

```
roast 62   t     100    110    120    130    140    150    160    170    175    180
           BT  105.2  110.8  116.2  121.1  126.0  130.6  135.2  139.4  141.5  143.5
            e  +0.16  -0.16  -0.38  -0.82  -1.00  -1.22  -1.20  -1.36  -1.36  -1.40
   deficit, degC/min
                0.03   1.86   2.15   1.55   1.01   0.77   0.72   0.34  -0.19  -0.60
```

**The deficit turns on between BT 105 and BT 110, peaks at about 2.2 degC/min
near BT 114, and crosses zero at BT 141.** It is the window's far end that
transfers, and it transfers cleanly:

| | roast 56 | roast 57 | roast 60 | **roast 62** |
|---|---|---|---|---|
| deficit crosses zero at | 174 s | 174 s | 167 s | **174 s** |
| **BT there** | **139.7** | **140.2** | **138.0** | **140.8** |

Four roasts, three backgrounds, two fan schedules, DRY END anywhere from 193.4
to 197.0 s — and the deficit ends at **BT 138-141** every time, 9-11 degC below
DRY END. **The load is indexed on bean temperature, not on the clock**, which is
what makes it a term in BT and not a term in `t`.

**And the fan step falls out of the same arithmetic as a cross-check nobody
asked for.** Roast 56's deficit minus roast 62's — same background, same marks,
the only difference the `Air 64 → 60` at 120 s — is `+1.85 / +3.34 / +3.20 /
+1.43 / +0.14` at 130 / 140 / 150 / 160 / 170 s: a single hump that starts at the
step, peaks 25 s later and is spent by 175 s, integrating to about 1.6 degC.
That is Phase A's bench step response (bottoms 54 s after the step, recovered by
130 s) and it is the 1.41-1.71 degC the fan was independently measured at. The
two roasts' drying components cancel and what is left is the fan. Nothing in the
term is fitted to it; it is a consistency check that passed.

#### 2. The term

```
RoR(u) = rise(u) * fall(u) / (1 + K*g(BT))
```

`g(BT)` is the fraction of the charge's free water released per degC of BT — a
single bump `x^p (1-x)^q` on `x = (BT − 100)/(140 − 100)`, normalised so
`∫g dBT = 1`. Written that way the load is `m_w·g(BT)·dBT/dt`, proportional to
the rate the roast is actually making, and the attenuation is the closed-form
solution of `RoR = S − K·g·RoR` rather than an implicit one. **The BT it removes
across the window is then exactly `K`, however fast or slow the curve crosses
it** — which is the property that makes a term written in BT well-posed.

`K` comes from the water mass:

```
K = eta * m_w * h_vap / (m*c_b + C_chamber)      m_w = mass * moisture_greens/100
  = 0.0156 * 44.0 g * 2260 J/g / 955.5 J/K  =  1.62 degC        (400 g, 11.0 %)
```

Fitted over roast 62's descent (100-175 s) with `p = 1`, the fit is **K = 1.63,
q = 1.4, rms 0.076 degC, worst 0.21** across 150 samples of the 0.5 s grid.

**What is measured and what is assumed, because one roast cannot identify both:**

- **measured** — the window's far end (BT 138-141, four roasts) and the total
  (1.63 degC at 400 g / 11.0 %);
- **assumed** — the onset at BT 100, because water boils. With `p = 1` the term
  leaves BT 100 at zero and grows linearly, so it first clears the residual's own
  0.1 degC quantisation near BT 105, which is where roast 62's deficit becomes
  visible. The boiling point is the physics; BT 104-105 is what the measurement
  can say;
- **assumed** — that `K` scales with water mass and inversely with the charge's
  heat capacity. **Nothing here measures that**, and it is the whole reason the
  magnitude is written physically rather than as a constant: it is what lets the
  term transfer to 300 g, or to a lot that reads 9 % instead of 11 %;
- **`eta = 0.0156` is not an evaporation efficiency.** 44 g of water at 2260 J/g
  over 955.5 J/K is 104 degC of BT; 1.6 degC of it lands in the window. `eta`
  absorbs the fraction of the charge's water that actually leaves below BT 140
  (roast 62 lost 11.40 % of its mass over the *whole* roast, dry matter
  included) and the fact that a roaster is a flow system rather than a
  calorimeter, so only part of a latent load ever appears as a BT deficit at all.
  It is one lumped number carrying two unknowns, and the roast measures their
  product;
- **weakly measured** — the exponents. `q = 1.0` costs 0.016 degC of rms against
  the fitted 1.4, and freeing `p` lands at 0.64/0.99 for nothing at all. The
  roast says the release is a single bump across the window; it does not pin its
  shape.

#### 3. `profile_400g_m5C_dry_v7.alog`, and the marks were deliberately not touched

```
.venv/bin/python tools/make_background.py --mass 400 --greens-temp -5 \
    --fcs 399:198.8 --ror-at-fcs 8.3 --development 28 --moisture-greens 11.0 \
    --compare artisan/profile_400g_m5C_v4.alog \
    --out artisan/profile_400g_m5C_dry_v7.alog
```

`--fcs 399:198.8 --ror-at-fcs 8.3` are **v4's own marks, not the lot's.**
`beans.py` now reads 197.4 / 9.1 for `C1043` and v4's 198.8 is the retired
pooled-across-three-coffees figure, so correcting it is wanted — but not in this
roast. Regenerating onto 197.4 / 9.1 moves the curve **+1.1 degC at 90-120 s and
−0.5 to −1.8 degC across 220-320 s**, which is larger than the effect being
measured and lands inside the window it is scored in. Held at v4's marks, the
tool's own no-drying regeneration reproduces the v4 **file** to 0.17 degC, so the
drying term is the only thing that changed. The mark correction is runbook row M.

Desk check, all of it:

```
   mark      target            authored          error
   DRY END     192 s (3:12)   149.6    149.6    -0.00 degC
   FCs         399 s (6:39)   198.8    198.8    +0.00 degC
   RoR@FCs     399 s             8.3      8.3    +0.00 degC/min
   DROP        427 s (7:07)     ---    202.4      --   <- 28 s past FCs, not pinned
   RoR peak     53 s (0:53)      --     53.0    +0.00 s

   RoR peaks at 46.0 degC/min at 53 s (v4: 44.9; roast 54's machine delivered 72)
   monotone rising TP->peak: True;  monotone falling peak->DROP: True
   drying: 11.0 % of 400 g = 44.0 g of water; eta 0.0156
        -> K = 1.62 degC removed across BT 100-140, shape x^1.0 (1-x)^1.4
```

**The difference from v4 is the intervention, and it is not where one might
expect it:**

```
   t      40     60     80    100    120    140    160    180    200 .. 427
 dBT   -0.01  +0.28  +0.66  +0.85  +0.46  +0.05  -0.10  -0.04  +0.02 .. +0.01
 dRoR  +0.27  +1.17  +1.04  -0.54  -1.43  -0.91  -0.00  +0.21  +0.13 .. +0.02
```

**About +1.2 degC/min more rate over 50-90 s and 1.4 degC/min less over
105-140 s, and nothing after 160 s** (`|dBT| ≤ 0.07` from 180 s to DROP). Over
the 120-300 s window the two curves differ by at most **0.46 degC, and that is at
120 s**, the window's own left edge.

**That is the four-constraint solve doing its job, and it caps what the term can
buy.** The term removes 1.62 degC of BT inside BT 100-140, all of it before the
DRY END pin at 192 s / 149.6, so the solve pays it back as extra rate earlier.
The net effect is that over 100-180 s `v7` asks for **0.89 degC less BT gain than
v4** against roast 62's measured **1.66 degC** of swing. **The term relieves
about half the swing on the curve alone; the other half has to come from the loop
actually delivering the extra front-end rate.** The intervention is to bring the
bed along *before* the water boils and then spend that lead, not to lower the
curve through the dip.

#### 4. The prediction, on the record before the roast

Scored as `BT − background` on the 0.5 s grid, roast 62's baseline being
**−1.50 @ 179 s, rms 1.06 over 120-230, swings −1.66 (from 100 s) and −1.12
(from 120 s)**.

**The two limits are both computable and they differ in a useful way.**

*If the loop does not take the front-end offer at all* — the machine repeats
roast 62's BT(t) exactly — then scoring roast 62's own BT against `v7` gives:

```
   t      100    120    140    160    180    200    220    240    260    280    300    320
 e(v4)  +0.16  -0.38  -1.00  -1.20  -1.40  -0.98  -0.72  -0.40  -0.29  -0.13  -0.10  +0.07
 e(v7)  -0.69  -0.84  -1.05  -1.10  -1.36  -1.00  -0.77  -0.47  -0.35  -0.19  -0.15  +0.03
```

minimum **−1.46 @ 179 s**, rms **1.08**, swings **−0.76 and −0.61**, entry slope
**+0.34 degC/min**.

*If the loop does take it*, `e` sits inside ±0.7 across the whole of 100-320 with
no coherent dip.

So the prediction is:

| what comes back | what it means |
|---|---|
| \|e\| under ~0.7 across 120-230, minimum shallower than −0.7 **and at no particular second**, rms under 0.5 | the term is right and the loop delivered the lead. The residual is closed |
| minimum still ≈ **−1.4 at ≈ 179 s** and rms ≈ **1.05**, but the swings fall to about **−0.76 and −0.61** | the term is the right size and **the loop did not take the front-end rate**. This is the pessimistic limit above, arriving almost exactly. It is not a reason to refit the magnitude — it is an argument for feedforward, i.e. step 9 |
| minimum −0.7 to −1.0 **with the swings also roughly halved and agreeing** | partly right: refit the magnitude, keep the shape |
| minimum unchanged near −1.5 **and** swings unchanged near −1.66 / −1.12 | the term is in the wrong place, or the load is not evaporative |
| `e` positive over 130-200 | over-correction — the term is too large, and that is as informative as the dip surviving |

**`e` at 100 s is the single most diagnostic sample.** `v7` asks for 0.85 degC
more BT there than `v4` did. Roast 62 returned **+0.16**; if the new roast
returns about **+0.1** again the loop delivered the lead, and if it returns about
**−0.85** it did not. **Report the minimum, the swing from 100 s and the swing
from 120 s all three** — on roast 62 they agreed, and here they are *designed* to
disagree if the loop did not follow, which is a different failure from a dirty
entry and must not be read as one.

Secondary: the entry slope over 85-115 s should go slightly **positive** (the
pessimistic limit gives +0.34), so the ±2 degC/min gate passes either way and
does not discriminate.

#### 5. Two things found in passing and not fixed

- **the four-constraint solve does not reach 1e-14 everywhere**, and never did.
  At 250 g / +25 degC the RoR@FCs constraint is missed by **1.6 degC/min**, with
  the drying term and without it (the term makes it slightly *better*, never
  worse) — the marks are not reachable by this family from that turning point.
  400 g over −24…0 degC, which is every roast run so far, is exact.
  tools/README.md § the residual note now says so; the tool has always printed
  the number;
- **the 1 s left-Riemann integration is worth 0.75 degC** against the same curve
  integrated at 0.05 s, all of it at the RoR peak. The drying term neither causes
  it nor makes it worse (its own contribution is 0.05 degC), and the fit runs on
  the same grid the file ships on, so the marks are exact for the curve Artisan
  actually plays. Changing it would reshape every background authored to date.

### Roast 63 (2026-11-11, 20:20) — 500 g of a new lot on v8: the +3 degC was delivered, and the first minute was not

**Outside the measurement programme, and unscored against it.** It changed
everything at once: mass 500 g, lot `C1066` (Ethiopia Crown Jewel Natural
Lalesa, `moisture_greens` 12.0), `greens_temp` entered 0.0, precharge inlet
**153** (roast 62: 142), and fan **65 → 62 over the first 26 s**, held at 62 to
DROP. The background was `profile_500g_m5C_dev52_v8.alog`, which was authored
for −5 degC and 11.0 %. Gains as logged on every roast since 56 (`pidKp 2.4 /
pidKi 0.056`, `svLookahead 6`), and `LA 6` fired at 46 s (SV +24).

| | v8 | roast 63 |
|---|---|---|
| TP | 54.3 @ 29 s | **52.6 @ 33 s** |
| DRY END | 149.6 @ 3:12 | 149.1 @ 3:14 |
| FCs | (label) 198.8 @ 6:39 | **199.6 @ 6:46.5** |
| DROP | 205.3 @ 7:31 | **206.0 @ 7:44** (57.5 s development) |

`e = BT − bkg`: **−6.8 at 45 s, −8.5 at 60, −2.8 at 90**, then +0.2 to +0.6 over
110-140, **−1.1 to −1.25 over 180-200** (the drying window again), and then
**0.0 to +0.1 from 300 to 400 s**. Inlet tracked SV at rms 3.1 overall (0.4 on
the preheat plateau), and the heater never saturated (64-75 % through the ramp),
so the first-minute lag is in the reference, not the loop. The dip model's TP
was 1.7 degC high and 4 s early at 500 g. That is the mass term (state-current.md
§ The mass term) or the 0.0 greens entry, and this roast cannot say which.

**The 85-115 s entry slope is about +6.6 degC/min, so the residual window fails
the ±2 gate** and nothing in it can be compared with roasts 56-62.

**What it does establish:** 500 g circulates and sustains at **fan 62**, and
C1066 cracked at **199.6**, its first point for `beans.py`. DROP was +3.6 degC
on v7's 202.4, as asked, with the extra 13 s past the curve's end coming from the
operator's drop.
