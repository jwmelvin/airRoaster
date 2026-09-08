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

## HANDOFF — roast 57 (2026-09-08): the preheat step

**If you are a fresh context, this section is the whole job.** Everything below it
is background.

### Roast 56 passed all four checks — full record in state-history.md § Roast 56

| check | roast 54 | roast 55 | **roast 56** | pass |
|---|---|---|---|---|
| peak SV, first minute | 193 | 154 | **165** | under ~200 — **pass** |
| seconds of heat at 100% | 2.0 | 1.0 | **1.0** | 0 — **near** |
| seconds **saturated** at own floor | 40.0 | 0.0 | **0.0** | under ~10 — **pass** |
| worst BT error vs background, 30-90 s | +5.5 | −4.9 | **+2.2** | single digits — **pass** |
| worst \|bkg − BT\| over 0-30 s | 8.6 | 3.9 | **3.7** | — |

Tracking rms, each roast against its own background:

| roast | 0-30 | 30-90 | 60-95 | 95-120 | 120-DROP | 0-DROP | min SV |
|---|---|---|---|---|---|---|---|
| 55 | 1.52 | 2.70 | 3.29 | 4.10 | **0.79** | 1.71 | 122 |
| **56** | 2.00 | **0.94** | **0.58** | **0.41** | 1.28 | **1.26** | 128 |

Three things to carry forward:

- **The lookahead switch at 45 s works and it fired.** SV steps **+24.25 degC at
  46.3 s** (predicted +21.4) and **0.00 at 91 s**; the port picks the instant out
  at rms 1.97 vs 8.94 / 9.68 / 23.20 for 30 / 60 / 91 s. The 60-95 s undershoot
  went from −5.33 to −1.13 and **no 40-60 s overshoot replaced it** (worst
  −1.24), so the 60 s intermediate is not needed. The single 100% heat sample is
  the inner loop servicing the +22.7 degC SV step at 46.5 s, not exhausted
  authority.
- **The seeding rule holds**: `replay_pid` fits roast 56 at `iterm0 = 18.63`
  (roast 55: 21.3), rms **1.97 degC of SV over 30-180 s**, and is out by 26.15 at
  zero.
- **`moisture_greens` is entered at last — 11.0**, matching roasts 50-52's 10.9
  for the same lot. Four roasts of 0.0 are over.

Roast 56 also carried an **unplanned third change**: the charge was
`greens_temp = -5.0`, so the background that ran was
`profile_400g_m5C_v4.alog`. It is confined to the dip (the two v4 backgrounds
differ by at most 6.96 degC at 57 s and by under 0.4 degC after 130 s), but it
means 0-120 s carried two changes at once.

### The job: roast 57 — step the PREHEAT, and read three things off one roast

**This replaces the `LA 12` lookahead plan** (operator, 2026-09-08). LA 12 is not
cancelled, it is deferred — and it may turn out to be unnecessary, because the
Temp_Drive loop attacks the same 140-200 s lag structurally (state-plan.md
§ Temp_Drive as the effort variable). The old plan is preserved in
state-history.md § The LA 12 plan, deferred.

**Bean budget: 2-3 loads of `C1043` remain.** That is the binding constraint on
everything below. See § The bean budget.

#### 0. BENCH FIRST — the Temp_Drive ladder, and it costs no beans

**Do this before the roast, in one preheat session, and do not charge if it
fails.** At fan **60**, under the PID, settle and record `Temp_Drive`
(`Inlet − BT`, the Y3−Y2 channel) at each rung:

| BT | settle until Temp_Drive is flat, then record | predicted |
|---|---|---|
| 130.2 | the historical point — this is the anchor | 10.25 (roasts 53-56 read 11.6-13.5) |
| 140 | | 11.2 (slope 0.10) … 14.0 (slope 0.383) |
| **145** | **the rung roast 57 runs at** | 11.8 … 16.0 |
| 152 | the coldest-charge rung the schedule would ever ask for | 12.4 … 18.6 |

**This one ladder is the most valuable measurement on the list.** `d(TD)/d(BT)`
is bracketed 0.10-0.383 and has never been measured, and it sets **three**
separate things: the preheat lever (state-plan.md § Normalize the charge with
the PREHEAT), how integrator-like a Temp_Drive loop is (§ Temp_Drive as the
effort variable), and how much of `plant_roast46.json`'s `loss(t)` is really a
BT-dependent loss aliased into a time function. Measuring it inside **one
session** removes the machine-history scatter that makes the across-roast
readings (11.62 / 11.92 / 13.19 / 13.45) useless for a slope.

**Abort criteria, and they are the point of doing this first:**

- **If a rung will not settle** — BT flat, inlet off its floor, Temp_Drive
  steady — that rung is unreachable at fan 60 and the schedule stops below it.
  Drop roast 57 to the highest rung that did settle and regenerate.
- **If 145 will not settle**, run the roast at **140** instead (predicted TP
  shift +4.15 rather than +6.24 — still clears the noise) and say so in the log.
- The empty-chamber evidence behind the 0.383 slope is explicitly warned as
  trend-only (25 s windows against a ~45 s time constant), so **a reading
  outside 0.10-0.383 is a result, not an error.**

#### 1. The roast: preheat 130.2 → 145.2, everything else held

**One change.** Same coffee (`C1043`), same mass (400 g), **same greens
temperature (−5.0)**, same fan schedule, same gate, same gains. Only the preheat
moves.

| | roast 56 | **roast 57** |
|---|---|---|
| preheat BT | 130.2 | **145.2** |
| precharge inlet | 141.8 | **~157** (whatever § 0 measured) |
| background | `profile_400g_m5C_v4.alog` | **`profile_400g_m5C_pre145_v6.alog`** |
| FCs mark | 198.8 | 197.7 (see § 3 — it rides along, and cannot confound) |
| `.aset` | `…_floor100.aset` | **`…_preheat.aset`** — see the box below |

> **`floor100.aset` would fire `LA 12` at 105 s and give you two variables.**
> Roast 57's plan was written before the lookahead row existed; the row is real,
> enabled, and checked in — `alarmflag=0, 1, 1, 1, 1, 1, 1, **1**`, row 8,
> `CHARGE + 105 s`, button 27. **Load
> `artisan/airRoaster_cascadePID_preheat.aset` instead.** It is `floor100.aset`
> with exactly one field changed, `alarmflag` row 8 → `0`, and nothing else: same
> gains, same floor 100, same seven other alarms, same buttons. Verify with
> `diff` before trusting it, and then still check row 8 reads **off** in the
> Alarms dialog — see § The alarm table can silently disagree with the .aset.

**The background is already generated and checked in.** All four constraints at
0.00, RoR monotone, peak 42.4 degC/min at 53 s. If § 0 reads a settled inlet more
than ~3 degC off 157, regenerate — but the whole 11.8-vs-16.0 Temp_Drive spread
is worth only **0.56 degC of TP**, so this is a tidiness fix, not a correctness
one:

```
.venv/bin/python tools/make_background.py --mass 400 --greens-temp -5 \
    --charge-bt 145.2 --inlet-precharge <measured> \
    --fcs 399:197.7 --development 28 --ror-at-fcs 9.4 \
    --compare artisan/profile_400g_m5C_v4.alog \
    --out artisan/profile_400g_m5C_pre145_v6.alog
```

**`greens_temp = -5.0` is a hard requirement, not a nicety.** The measurement is
`TP(57) − TP(56)` with everything else cancelled, and greens temperature enters
the TP at **0.60 degC/degC** — so 2 degC of drift is 1.2 degC of TP, 19% of the
signal. Read it the same way, from the same place, at the same time out of the
freezer. If it cannot be matched, record what it actually was and say so: the
roast is still readable against the model, just with the model's own 1.85 degC
bias back in play.

#### 1a. What the roast measures

**`d(TP)/d(preheat)` — the number the whole preheat idea rests on.** Every
calibration roast charged at BT 129.7-131.0, a 1.3 degC spread, so this gain is
currently *structure* (it follows from `dT_mix = phi·(BT_c − T_bean)` putting
both temperatures in one bracket) and not data. The model **assumes the trade it
is being asked about** and cannot falsify it.

| | value |
|---|---|
| roast 56's measured TP | **61.10 degC at 26 s** |
| model for roast 56 | 59.25 (so the model runs **1.85 degC deep** here) |
| model for roast 57 | 65.48 |
| **predicted TP** | **≈ 67.3** (model + the same bias), i.e. **ΔTP ≈ +6.2** |
| repeatability to beat | roasts 54 and 55, gated, same lot/mass/greens: TP **55.60 and 55.60** |

**Read the gain as `ΔTP / 15.0`.** Predicted **0.415**.

- **0.30 … 0.55** → the lever stands. Ship
  `preheat = 124.4 − 1.17 × greens_temp` at 400 g and move on.
- **outside that band** → recompute the lever from the measured gain before any
  compensated roast. `tools/analysis/preheat_lever.py` is the tool; the lever is
  `0.60 / measured_gain`.
- **ΔTP under ~2** → the mechanism is not there and the whole preheat idea is
  dead. That is a real possible outcome and it is worth one roast to find out.

#### 1b. It is still a readable roast for two other things

- **The 140-200 s lag.** The two backgrounds differ by **+0.62 degC at 160 s and
  −0.12 at 200 s** — they have converged by then. So roast 57's drying-ramp
  residual is directly comparable with roast 56's −2.91, and the LA 12 question
  keeps its baseline.
- **`C1043`'s first-crack temperature**, which is why this roast is worth
  spending a scarce load on. See § 3.

#### 2. Decide step 9, `INLET TRIM` — the tracking case is dead

Roast 56 tracks its background at rms **0.94 degC over 30-90 s**, **0.41 over
95-120 s**, **1.26 over the whole roast**, with the inner loop at rms **0.91**
from 50 s to DROP. There is no tracking error left for an inlet trim to remove.
**Either argue step 9 on robustness alone — behaviour when the inner loop is
disturbed or the plant moves — and say what would test that, or drop it.**
state-plan.md § NEXT item 14 should record whichever.

#### 3. The FC mark — the 198.8 was three coffees, and it should go back to ~197.5

**Corrected 2026-09-08 from the logs.** Every `.alog` carries `plus_coffee`, the
artisan.plus hr_id, so the lots are known exactly — and the "measured mean over
roasts 50-55" of **198.8 that roast 56's background was built on is a mean over
two different coffees**. Roasts 50-52 are `C1074` (Colombia, median 200.1);
53-55 are `C1062` (Kenya, median 197.4); **roast 56 is `C1043`, the Ethiopia
that roasts 43-49 ran on** — not a new bean at all.

| `plus_coffee` | roasts (cascade-era) | FCs BT | median |
|---|---|---|---|
| `C1043` Ethiopia Daye Bensa | 43, 44, 46, 49, **56** | 197.4 / 197.7 / 197.8 / 197.9 / **195.3** | **197.7** |
| `C1062` Kenya Ichamama | 53, 54, 55 | 197.4 / 197.3 / 198.7 | 197.4 |
| `C1074` Colombia Peach | 50, 51, 52 | 201.2 / 198.1 / 200.1 | 200.1 |

Two earlier conclusions fall with it. **`profile_003`'s original 197.5 was
right** — 0.1 from the Kenya's median, 0.2 from the Ethiopia's. And **there was
never a systematic FC lag**: § Roast 55 read one roast's 408 s against a 399 s
mark, but roasts 53 and 54 are the same coffee against the same mark and landed
at 397.5 and 395.5 s, *early*. Roast 56's change 1 was chasing noise. It did no
harm — BT was +0.33 degC from the background at the crack — but it was not a
correction.

**Roast 56's 195.3 is the outlier of its own lot.** `beans.py --coffee C1043`
now reads eight roasts: 196.0 / 196.6 / 197.4 / 197.7 / 197.8 / 197.9 / **195.3**
(and one 250 g Behmor-era entry excluded by mass). Seven sit in a 1.9 degC band;
195.3 is 1.2 degC below the lowest of them. Either a new bag under the same hr_id
(artisan.plus identifies the coffee, not the crop or the bag) or a crack marked
early by ear. `artisan/profile_400g_m5C_fc195_v5.alog` is parked at 195.5 and
**rests on that single reading**; 197.7 is the better bet.

**It has been folded into roast 57 and no longer needs a roast of its own.**
That was decided on arithmetic, not on principle — the mark change costs
**+0.00 degC at the TP and +0.26 at 60 s** against the preheat step's +6.24 and
+4.69, so it is **0% of the primary signal and 5% of the secondary one** and
cannot confound it. (Before the RoR peak was pinned it would have been −4.8 degC
at 60 s, which is why it was ever a roast of its own; see § Regenerating the
background.) Roast 57 therefore reads `C1043`'s crack temperature *as an
observation* — the mark is a label the cascade never reads — and settles the
195.3 question in the same load.

**What settles it:** roast 57 cracking at 197-198 makes 195.3 a one-off and the
lot's number is 197.7. Cracking at ~195 twice running makes it a real property of
this bag, and the background moves to 195.5 for the remaining loads. Either way
run `beans.py --coffee C1043` again afterwards; per-lot FC is derived, never
recorded by hand (state-plan.md § Bean reference).

DROP came **19 s** after FCs, not the 28 the background specifies. Left at 28
for now — the DROP mark only closes the control window (`calcSV` returns `None`
past `drop_t`) and every roast has dropped well inside it.

### What to expect

**Primary.** TP **≈ 67.3 degC** (61.10 + 6.2), still at **26-30 s**. The TP
*time* barely moves with preheat (the model says +0 s), so a large shift in the
turn time means something other than the preheat moved — check greens
temperature and the fan step first.

**The first 90 s is the whole experiment.** BT should run **+6.2 degC at 30 s,
+4.7 at 60 s, +3.0 at 90 s** above roast 56, converging to **+0.6 at 160 s** and
**−0.1 at 200 s**. That is the background's own shape, so if the loop tracks,
these are the numbers.

**The four checks should be unchanged**, and this is a real prediction rather
than a hope: the demanded peak RoR *falls* from 44.9 to **42.4 degC/min**,
because a higher turning point needs less ramp to make DRY END. So peak SV, heat
at 100% and floor saturation should all be **as good as roast 56 or better**. If
any of them degrades, the preheat has changed something the dip model does not
contain — which is itself the finding.

**Watch for, and log:**

- **the settled Temp_Drive at 145** — § 0's ladder is the measurement, but record
  the value the roast actually charged from too.
- **scorching or tipping.** 145 degC is 15 degC hotter than the beans have ever
  been tipped into. It is well under the ~200 degC surface temperature that
  scorches, and the bed drops the chamber immediately, so this is expected to be
  a non-event — but it is the one risk the model has nothing to say about, and
  **the operator's judgement overrides the schedule.** Look at the beans.
- **first crack time and temperature.** v6 passes **195.3 at 384 s and 197.7 at
  399 s** — 15 s apart, so the crack *time* distinguishes them on its own. (v4
  was 375 / 391; the mark is now on the curve rather than 8 s past it, because
  197.7 is the mark v6 was fitted to.)
- **the 140-200 s residual**, comparable with roast 56's −2.91 (§ 1b).

**What would make this roast uninterpretable:** a greens temperature that is not
−5, a different mass, or the alarm table having drifted. Check all three before
charging.

### The bean budget — 2-3 loads of `C1043` left

**`C1043` is only irreplaceable for one question: what this lot cracks at.**
Everything else on the list is a *machine* measurement — the dip is over by 29 s,
the loop's window is 30-200 s, and first crack is at ~395 s. A control experiment
scored on 0-200 s does not care which coffee is in the drum.

So the rule is: **spend `C1043` where the lot matters, and run machine work on
whatever else is in the cupboard.**

| load | what | why it must be `C1043` |
|---|---|---|
| **1 — roast 57** | the preheat step | it is not required, but it is free: the crack reading rides along and settles the 195.3 question in a load that was being spent anyway |
| **2 — reserve** | only if roast 57's crack reading is ambiguous (marked uncertainly, or lands between 195.5 and 197.7) | confirming the lot's number |
| **3 — if it exists** | the first compensated roast, or the Temp_Drive first light | not required — prefer another coffee and keep this one |

**On another coffee, the only cost is a less well-targeted back half**: a lot
with no cascade-era history has no derived `--fcs` / `--ror-at-fcs`, so use
`beans.py`'s pooled default and accept that first crack lands early or late.
**That is not a defect for a control experiment** — the four checks and the
loop's window all close 200 s before the crack. Say so in the log rather than
pretending the back half was on target.

**Do not spend a `C1043` load on:** the Temp_Drive bench work (no beans at all),
the empty-chamber shakedown (no beans), or a second preheat rung (any coffee).

### Regenerating the background

**`tools/README.md` is the orientation brief for this task** — the four inputs,
the recipe, the check block to read, and the traps. In short:

```
.venv/bin/python tools/make_background.py --mass 400 --greens-temp <measured> \
    --fcs 399:<bean FCs BT> --development 28 --out artisan/profile_400g_<T>_<tag>.alog
```

`--development` places DROP at `FCs + <seconds>` with whatever temperature
follows; `--fcs <s>:<BT>` sets the crack mark, and the per-lot value comes from
state-plan.md § Bean reference. Generate at the mass and charge temperature
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

**For roast 57 the eighth row must read `off`** — that is the only difference
between `floor100.aset` and `preheat.aset`, and it is the difference between one
variable and two.

| # | On | From | Time | Source | Cond | Value | Action | Button |
|---|---|---|---|---|---|---|---|---|
| 1 | off | CHARGE | 00:01 | | > | 0 | Playback ON | |
| 2 | ON | DRY END | 00:00 | ΔBT | < | −25 | DROP | |
| 3 | ON | CHARGE | 00:01 | | > | 0 | Event Button | 20 = `LA 0` |
| 4 | ON | CHARGE | 00:45 | | > | 0 | Event Button | 21 = `LA 6` |
| 5 | ON | ON | 16:00 | BT | < | 131 | Event Button | 23 = `ARM bak` |
| 6 | ON | CHARGE | 00:15 | | > | 0 | Event Button | 25 = `PID on` |
| 7 | ON | CHARGE | 02:00 | | > | 0 | Event Button | 26 = `Fan 60` |
| **8** | **off for roast 57** (ON in `floor100.aset`) | CHARGE | **01:45** | | > | 0 | Event Button | **27 = `LA 12`** |

(Button numbers in `alarmstrings` are 1-based into `extraeventslabels`, which is
0-based: `alarmstrings` `21` is `extraeventslabels[20]` = `LA 6`.)

**And verify from the log afterwards, because the `.alog` cannot tell you.** It
records `svLookahead` at *save* time (roast 56 says 6, which is only the value
that happened to be live at the end). The switch instant is visible as a **step
in SV**, because `L` seconds of lookahead adds `bkg(t + L) − bkg(t)` of target
and `dSV/derror = 4.8`:

| | roast 54 | roast 55 | **roast 56** |
|---|---|---|---|
| SV step at 91.0 s | 20.2 | 20.3 | **0.00** |
| SV step at 46.3 s | — | — | **+24.25** (predicted +21.4) |
| SV step at 30 s | −0.2 | 0.0 | −3.02 |

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
`PID ON` alarm at +15.5 s. Roasts 54, 55 and 56 are all clean by that test —
roast 56 carries the two preheat entries at −16 and −14 s, the duplicate at
+1.0 s, and then nothing until 15.5 s.

### Where the strategy stands

Settled and not worth re-opening: `k = 0.1056` measured from roasts 50/51 across a
37 degC span to 0.34%; `h_fus` under ~1 J/g; the plant has no fan term; the
13.5 s is total apparent lag rather than transport; the preheat equilibrium is
fan 58 / BT 130.2 / Temp_Drive 10.25. The charge gate, the alarm-fired fan step
and now the 100 floor are all proven.

**`moisture_greens` is entered again** — roast 56 carries `11.0`, matching roasts
50-52's `10.9` for the same lot, after four roasts at `0.0`. Keep entering it.

**The dip model has one −5 degC point and it is its worst fit.** Roast 56 turned
at **61.1 degC at 27.5 s** against the m5C background's 59.2 at 29.0 — 1.9 degC
shallow. Scored against the shipped calibration (fitted to roasts 50/51/53/54 at
+25 and −12, nothing between), roast 56 reads rms 1.92 / worst 3.61, the poorest
of the six recorded-temperature roasts, and the model over-predicts its drop by
1.5 degC. **That is still inside the model's own scatter**: the four −12 roasts
measure drops of 60.30, 61.40, 63.00 and 62.20 against one prediction. Do not
refit on `n = 1`. Roast 56 is the obvious third calibration temperature once a
second −5 roast exists — it has an entered greens temperature, a held gate and
the longest loop-free window in the set (30.5 s).

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

Open, in order: (1) roast 57 — the 140-200 s ramp lag, and deciding step 9;
(2) the mass term; (3) whether charge state reaches the cup, which needs a *warm*
charge on the same configuration dropped at the same BT to the tenth; (4) a
second −5 degC charge, which would give the dip model a third calibration
temperature. **Step 9, `INLET TRIM`, is now a decision rather than an open
question**: roast 56 leaves no tracking error for it to remove (rms 0.94 over
30-90 s, 1.26 over the whole roast, inner loop 0.91 from 50 s), so it is
robustness or nothing — see the handoff.

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
working branch is **`feature/artisan-pid`**, which carries **v0.19.0** (flashed
2026-09-06 and validated on roast 47: the `SV`/`HT` `getData` nodes are live;
`INLET TRIM` is flashed but still un-drilled — state-plan.md § NEXT item 14) and
now **v0.20.0** — the measured `feedforward()` map. **v0.20.0 IS flashed**
(corrected 2026-09-08; this paragraph said "unflashed" and contradicted its own
§ Step 8, which records roast 48 on 2026-09-06 as *"the first roast on v0.20.0"*
and scores fourteen windows *"against the map flashed in v0.20.0"* at bias
+1.07% / rms 1.61%). Every roast from 48 on has run it. Note that
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

**Roast 47 (2026-09-06) is Test A, and the replayed-schedule mechanism works.**
Empty roaster, PID off, `airRoaster_cascadePID_char.aset` with
`charstep_empty_fan.alog`: all 13 scheduled events fired on time, the inner loop
held the commanded setpoint to **rms 1.12 degC over 619 quiet samples**, and
**v0.19.0's `SV`/`HT` channels are live** — the first roast whose commanded
setpoint and heat percent are in the profile itself, with no dashboard CSV taken
or needed.

**It found a trap that would have cost both loaded runs.** At 10:05 the DROP
chain ran on its own. Not the alarm — `alarmflag` was off — but Artisan's
**built-in `autoDrop`** (canvas.py:5151), which is not an alarm and which
`alarmflag` does not touch: its gate is BT > 160 degC and **more than 7 minutes
since CHARGE**, after which any `BTbreak` marks DROP. That 7-minute gate is why
it has never appeared here (these roasts drop at 6:20-6:31, which is why the
DeltaBT alarm exists at all) and why **every characterisation run trips it**. It
cost 88 s and one steady window; the char config now carries `autoDrop = false`.
It would have taken the last third of the fan measurement out of both doublets.

**And it overturned step 8's coefficients.** Nine steady windows, fan **58-80**
crossed against SV **145/185**, show the proposed
`heat = -30.62 + 0.99*fan + 0.0096*SV` under-predicts by **10.8 to 25.9 %** with
the `SV` term **26x too small** — the short-lever-arm failure the run was designed
to catch, since the five preheat steps it came from held SV nearly constant. The
fan coefficient survives. Use the **product form**,
`heat = 69.87 - 0.8570*fan - 0.5101*SV + 1.1423*fan*SV/100` (rms 0.68 % against
the affine form's 1.63, and it extrapolates better at roast 46's own preheat
point). Carded in `tools/analysis/ff_roast47.json`; detail in
state-history.md § Roast 47. **Step 8 is now the next thing to do**, and it is
bench work.

**Step 8 is done and `main`'s successor is now v0.20.0 (unflashed).**
`feedforward()` gets roast 47's measured map,
`heat_ff = 69.8685 - 0.8570*fan - 0.5101*sv + 1.1423*fan*sv/100` (rms 0.68 %),
replacing the single-product form that was clamped at 100 for 430 of 430 samples
of roast 46 — inert, with `d(FF)/d(fan) = 0`, and collapsing the anti-windup
bound to `[-100, 0]`. It is **on by default**, which is a behaviour change at
first boot: the old "`ffK = 0` disables" idiom cannot survive coefficients that
are not sign-constrained, so there is an explicit `ffEnabled` behind `FF ON`/`FF
OFF`, and NVS uses new keys so an upgrading device comes up on the measured
defaults rather than a stale coefficient. `FF CAL` and `FF AMB` are removed and
say so. Compile-verified; dashboard checked in browser preview against simulated
pushes (the four-coefficient panel round-trips, a partial map is refused, and the
step-cal panel emits `FF SLOPE`).

**The map is empty-chamber and that is tracked, not forgotten** (operator,
2026-09-06): a bean bed changes the pressure drop and so the flow a fan level
delivers, so the fan terms will move once loaded. Every coefficient is
runtime-settable and NVS-persisted, so **a loaded refit is a command, not a
reflash** — and `FF SLOPE <%/fan-unit>` takes a fan slope measured from a single
fan step and rescales both fan terms by the ratio while holding the current
operating point fixed, which is exactly the bean-load correction. The two
scheduled doublets deliver that number for free from their 60/70 square wave at
SV 200; a dedicated loaded FF grid stays unscheduled unless those disagree,
because it costs a batch and the bed's flow resistance drifts as the beans dry.
state-plan.md § Step 8.

**Roast 48 (2026-09-06) is that batch, and it closes the open question:
`feedforward()`'s empty-chamber map transfers to a loaded chamber.** Steps 4-5,
the first roast on v0.20.0, and — the operator's framing — **Test A's design run
again with beans in it** rather than the doublet. All 45 scheduled events fired
on time, `autoDrop = false` held on exactly the 7:15 `BTbreak` that cost roast 47
88 s, and BT peaked at 184.6 degC against the generator's simulated 185.7.
400 g in, 350 g out.

Fourteen steady windows, fan 60-70 × SV 140-245, against the map flashed in
v0.20.0: **bias +1.07%, rms 1.61%, worst +2.45%**, with most rows extrapolated in
SV beyond roast 47's box. The fan slope — the quantity a bean bed was supposed to
move, and the reason `FF SLOPE` exists — measures 1.03-1.11x the empty map at
SV 190 and 215 and 1.33x at SV 245, but SV 245 is 60 degC outside roast 47's
fitted box, so that row is one extrapolation against another and is not a load
effect. **Pooled** (25 windows over the union of both runs, one estimator,
fan 58-80 × SV 140-245) the refit is `82.71 - 1.0774*fan - 0.6255*SV +
1.3294*fan*SV/100`, rms 1.21%, which differs from the flashed coefficients by at
most **1.65%** anywhere in the box the cascade uses. **Nothing to reflash, and
`FF SLOPE` has nothing to correct.** Carded in
`tools/analysis/ff_roast48_loaded.json`; tool `tools/analysis/roast48_ff.py`.

**And the feedforward does the job it was written for.** Worst inlet excursion
after a fan step at a flat setpoint is **1.5 degC on a 10-unit step**, about
0.13 degC/fan-unit, against roast 47's 0.50 with `d(FF)/d(fan) = 0` (its 22-unit
step cost 13.2 degC). Roast 47 predicted the loaded runs would show ~6 degC per
transition until step 8 landed; step 8 landed and they show 1.5. Inner-loop
tracking rms **0.40 degC** over 226 quiet samples against roast 47's 1.12, all 14
windows inside ±0.30 degC, and commanded inlet steps of ±40 to ±95 degC settle
within 2 degC in **3-6 s**.

**Two Artisan settings came out of it and both should change before the next
run.** First, **untick "Drop Spikes"** (Config › Curves › Filters;
`dropSpikes=true` in every cascade `.aset`). Artisan's `inputFilter`
(canvas.py:4535) ends with a repair that assumes any run of equal readings is a
stuck sensor and **destructively rewrites the two samples before the change** as
a linear ramp, in the array it saves — gated on *any* of `minmaxLimits` /
`dropSpikes` / `dropDuplicates`, of which only `dropSpikes` is on. `SV` and `HT`
are constant by construction, so they trip it constantly: SV 245 → 150 is stored
as 245, 213.33, 181.67, 150. Window means survive it (0.10% worst), transient
timing does not — naively this run reads rms 2.79 degC of tracking error against
a true 0.40. Second, **Artisan can sample at up to 10 Hz** (`min_delay = 100`,
canvas.py:608; Config › Sampling takes 0.10-999.99 s and only warns below 2 s),
and the outer loop's tuning is **rate-independent** — `Ki` is applied as
`Ki*err*dt` in real seconds and `svLookahead` is in seconds, so Kp 3.0 / Ki 0.07
/ lookahead 3 carry over unchanged. **0.5 s doubles the resolution on every
transient this project measures**, and 0.25 s is the floor worth having (the
firmware's `controlStep()` period). What moves with it: WebSocket load, and
`curvefilter`, a count of samples, so the PID's own PV filter goes from 0.67 s of
lag to 0.33 s. RoR does not move — `deltaBTsamples` is derived from the stored
`deltaBTspan` (20 s) and the interval (canvas.py:2796).

**Both are applied** (operator decision 2026-09-06): `dropSpikes` true -> false
and `Delay` 1000 -> 500 in `artisan/airRoaster_cascadePID.aset`, propagated to
all four variants by `tools/gen_pid_alarm_asets.py`. `curvefilter` stays at 3 —
it is the one setting whose time constant moves, and changing it in the same step
would put two variables in one roast. **The files are ahead of the live Artisan
session**: load the `.aset` (or set both in Config › Curves › Filters and
Config › Sampling) before the next run. Detail in state-history.md § Roast 48.

**The plant refit is done too (`tools/analysis/roast48_plant.py`,
`plant_roast48.json`), and it settles one thing, questions another and supersedes
nothing.** Roast 48 is the first run whose excitation was *designed* — inlet steps
of -95/+65/-65/+40 degC with the PID off, so no controller correlates input with
output.

**Settled: the plant has no fan term.** `kf` fits to **0.0000** in
`dBT/dt = a*(1 + kf*(fan-60))*(Inlet(t-theta) - BT) + loss(t)`, band -0.004 to
+0.002, and forcing it to the 0.049 that state-history.md § Correction measured
from roast 45 costs **1.67x the residual**. That figure was already retracted for
circularity; this replaces the retraction with a bound of about 5% of plant gain
per 10 fan units. It closes the last item Tests A/B/C were kept alive for. Note
what it does *not* say: `roast48_ff.py` measures 1.3-2.6% more **heat** per fan
unit to hold the same inlet, which is real. Once the air is at temperature,
17% more of it does not measurably speed the bed up. The bed is not flow-limited.

**Not settled: `a` and `theta`.** The whole-window fit is `theta 8.5 / a 0.00802 /
tau 125` against roast 46's `13.5 / 0.00490 / 204`, but roast 48's own sub-windows
spread `a` 0.0062-0.0085 and `theta` 7.8-14.5 — as wide as the gap — so the
disagreement is not evidence against roast 46. **`plant_roast46.json` remains the
authoring source for `merge_inlet_base.py`**; the new card says so in a
`supersedes_plant_roast46: false` field.

**Questioned: the deadtime.** `fit_integral_2lag`, unused since roast 46, fits the
same windows with `theta` collapsing to **~0** and a 10-25 s first lag in its
place, taking about a third off the residual on every well-excited window. The
13.5 s "deadtime" is at least partly a lag — which matters, because the two cost
very different phase margin. **That question is now settled at the desk — see the
paragraph below the roast 49 entry.**

**The tuning does not move.** Roast 48's plant gives Kp 3.0 / Ki 0.07 a 44.5 deg
margin and would allow more; roast 46's gives 33.7. The tie-breaker is empirical:
roast 45 rang at **177 s** at Ki 0.10, and roast 46's plant predicts 190 s there
against roast 48's 135 s. The card fitted to a real roast predicts the real roast.
**`pidKi` 0.07 stands.** Detail in state-history.md § Roast 48.

`greens_temp` was again left at `0.0`.

**Roast 49 (2026-09-06) is step 6, and it passes.**
`airRoaster_cascadePID_lookahead.aset` unmodified with `profile_003`, 400 g, no
intervention, DROP by the DeltaBT alarm at 7:03. The steady tracking error falls
to **+0.40 degC / 1.84 s** against roast 46's +1.06 / 4.73, and time-to-BT
150/180/196.5 lands at **-0.9 / +2.2 / +2.0 s** against the profile where roast
46 ran +3.4 / +4.9 / +4.8. The 1:30 switch behaves as designed — a +3.96 degC
target step, +21.2 degC of commanded SV inside two samples, 95% of the excursion
in 12 s — and after 1:40 the error stays inside **-1.94 .. +0.93 degC** with no
ring. **The type-1 ramp error is cancelled**; `e_ss = (dI/dt)/Ki = 1.42 degC` and
six seconds of lead against a 0.22 degC/s background takes ~1.3 of it, which is
arithmetic rather than luck.

**Both Artisan settings changes landed** — sampling 0.511 s, and the largest `SV`
step is one sample wide where roast 48's was rewritten into a three-sample ramp.
**And the simulator carries over unchanged**: replayed at `sampling_rate = 2` it
reproduces the commanded SV to **rms 0.83 degC from 0:30, 0.44 after 4:00**, the
same figures as roast 46 at 1 Hz. `LoopConfig` gains a `sampling_rate` field.
**Step 7 also came for free and in a stronger form than specified**: the fan sat
at **64 for the entire recording**, preheat and charge bump included, so there is
no air schedule anywhere in the trace.

**Two predictions missed — floor time 29.2 s against 16, worst SV reversal 7.7
degC against 3.2 — and both are the charge state rather than the loop.** The dip
ran BT 12 degC *above* the background instead of roast 46's 9.8 below, so the
error went to -16 degC and the output floored for 29 s (heat 44-48% throughout;
the floor never killed heat, and `Iterm` was back-calculated to 49 and had
drained to 25 by 1:30). The "reversal" is one monotone settle after the 1:30
kick. **Rows 4-5 of the step-6 table are therefore not a one-variable comparison
against roast 46 and must not be read as one**; rows 1-3, the experiment, are
unaffected, because the tracking window starts long after the integrator
re-converges and `svLookahead` has no charge term in it.

**The charge was 33-35 degC warmer than roasts 43-46, and that is now a tool.**
`tools/analysis/charge_state.py` runs the control-independent proxy from
state-history.md § Charge temperature — the BT fall over `0..theta` is charge
mixing alone, because nothing the heater does reaches BT before 13.5 s — and adds
the correction roast 49 forced: **the air already in flight counts**, since inlet
air from `t in [-theta, 0]` lands inside the mixing window and roast 49's preheat
sat at 168.6 degC against roasts 43-46's 140-150 (worth +0.39 degC/100 g).
Corrected, roast 49 reads **11.81 degC/100 g against the 400 g frozen group's
15.14 / 14.57 / 15.15**, which holds to 2.2% — 22% low, or **T_bean ~ +15 degC**
(band +13..+18) if 43/44/46 were at -18. The *difference* is anchor-free: the
freezer temperature cancels out of it. Roast 48's sacrificial stock reads +12.8
on the same estimator. Two cautions are in the tool: the proxy is **not linear in
mass** (roast 45 at 345 g reads 7% low for that reason alone — compare like
masses), and the **preheat trajectory is part of the measurement**, so an
experiment must hold it fixed rather than merely hit the same CHARGE_BT.

So roast 49 is the accidental **warm arm** of the ambient-vs-freezer pair; one
deliberate frozen batch closes it. `greens_temp` was left at `0.0` for the fourth
roast running, which is the only reason any of this had to be inferred.
Detail in state-history.md § Roast 49.

**The deadtime-versus-lag question is settled, and the answer changes a claim
rather than a number (2026-09-06, desk work — state-plan.md § What roasts 47-49
jointly say, item 4).** Tool `tools/analysis/deadtime_vs_lag.py`; `plantfit.py`
and `margins.py` gained the second lag. **No roast was needed and none is
proposed.**

**Roast 49 was checked first and it cannot contribute.** It is closed-loop with
one 1:30 SV step: independent inlet motion 5.08 degC rms against roast 48's
23.68, and on the tau2 grid `roast48_plant.py` itself uses (0-120 s) its two-lag
fit runs away to the edge and returns a **negative gain**. Its sub-window `a`
spans a factor of three. Excluded.

**The residual cannot settle it either, and that is worth knowing.** Roast 48's
BT residuals are correlated at rho > 0.99, so the AR(1) effective sample size of
a 300-450 sample window is **5 to 9** — no residual reduction of any size clears
an honest F-test there. What settles it is **identifiability**. On roast 48 the
`(theta, tau2)` minimum is a *point*: the 1%-of-minimum contour is one or two
grid cells, `theta` sits hard at 0 and bootstraps to 0-2 s, and forcing pure
deadtime costs **42-131%** more residual. On roast 46 it is a *ridge*: only the
**sum** is determined (a 1-2 s band at 13-14 s) while `theta` and `tau2` each
range over 6-13 s, and which of pure-deadtime and pure-lag is better *flips*
between windows. That is not a contradiction — roast 48 has four inlet steps of
-95 to +65 degC and **a step is the only excitation that separates a lag from a
delay**; roast 46 has the smooth charge recovery, whose content sits below the
corner where the two part company.

**So the 13.5 s was never 13.5 s of transport.** What is identified everywhere is
`theta + tau2`, which bootstraps to 9-11 / 13-15 / 12-14 s on the three
well-excited windows — and the single-lag `theta` the deadtime fits report (8.5 s
roast 48, 13.5 s roast 46) **is that sum**. The real transport delay is 0-2 s
where roast 48 can see it. The structure also **fixes `theta`'s
non-stationarity** — 7.8-14.5 s across roast 48's sub-windows becomes a flat
0.0-1.0 s, so that spread was a structural artefact — but it makes `a` *worse*
(0.0074-0.0142 against 0.0062-0.0085), because a late window can buy a slow
response with a long lag and a large gain. Better structure, not a finished
plant.

**The tuning does not move and this is the strongest form of that statement.**
Walking roast 46's entire ridge from all-delay to all-lag moves the phase margin
at Kp 3.0 / Ki 0.07 by **32.8 to 37.7 deg**, over a span across which the
residual moves 11%. Five degrees is inside the model error these cards already
carry. **`pidKi` 0.07 stands.** What *does* move along the ridge is the
closed-loop period, 156 to 196 s — so roast 45's measured **177 s** ring at
Ki 0.10 is informative where the residual is not, and it picks out `theta` 6-7 /
`tau2` 6.5-7, within 1% of roast 46's own residual minimum. Compared against the
least-damped closed-loop mode (**not** the crossover period — the earlier notes
compared the wrong quantity), roast 46's two-lag card gives **173 s** against the
measured 177, its single-lag card 194 s, and roast 48's cards 143-152 s. The
ranking § Roast 48 drew survives and improves.

**And `plant_roast46.json` and `merge_inlet_base.py` both stand unchanged.** The
two-lag inversion is `ff(t) = X(t+theta) + tau2*dX/dt(t+theta)` with
`X = bg + (dbg/dt - loss)/a`; built from roast 46's own two-lag card against
`profile_003` — through the authoring tool's own pipeline, so the one-lag column
reproduces `merge_inlet_base.py --dry-run` exactly — it differs from today's
schedule by **mean -0.04, rms 0.84, worst 3.25 degC** on a base running
200-256 degC — against the ~0.5 degC whole-degree
event quantisation floor and the 0.87 degC replay error the tool already reports.
The reason is arithmetic: on a ramp of slope `r`, advancing `bg` by `theta` adds
`theta*r` and the lag inversion adds `tau2*r`, and roast 46 puts
`theta + tau2 = 13` against the single-lag 13.5. **The `bg(t+theta)` lead is a
valid first-order stand-in for the lag inversion**, and what needs correcting is
the description of `theta`, not the construction. Two things for whoever does
rewrite it: the two-lag lead carries `tau2/a * d²bg/dt²`, so a rough background
costs far more and the tail blend would have to be C1; and `a`, `theta`, `tau2`
and the loss curve are **one set** (`a` is 22% larger under two lags), so no card
is emitted here and no authoring tool is touched. **`charge_state.py` is
unaffected as well**: its proxy assumes the heater is blocked over `0..theta`,
which under two lags it is not, but the difference is 0.19-0.24 degC/100 g across
roasts 43/44/46/49 — a spread of 0.05 against the 3.3 degC/100 g gap the proxy
measures, so it is common-mode. Detail, tables and the excitation that would
settle what is left (it is `a`, not the delay) in state-history.md § Deadtime
versus lag.

**The charge-thermal test (2026-09-06, 20:27) is not a roast, and its headline is a negative
result.** Two cycles of *preheat the empty chamber to BT 130, cut heat and fan
together with the cooldown guard disabled, tip 400 g in, wait 150 s* — one arm at
room temperature, one from the freezer. The operator supplied what the log does
not: freezer **−18 degC** actual, room **~29 degC**, **400 g** both arms;
`greens_temp` is `0.0` for the fifth run running. The preheat end-states match to
within 0.1 degC of BT and 0.4 degC of inlet, so the pair is clean.

**The still-air decay cannot measure charge temperature.** Left free, the joint
fit puts the room-temperature arm at **−2.2 degC** and the freezer arm at its
**−45 degC bound**, with a **16 kJ/K** chamber to pay for it — and that fit is
*better* than one with the temperatures held at truth (rms 1.64 against 2.21) on
residuals whose `neff` is **0.3-1.1 per arm**. `C_chamber` is not identified
either: `rho` walks to whatever bound it is given, 29.7 against a bound of 30,
even with the charge temperatures fixed. **The cause is structural and the
operator named it** — the preheated chamber holds a lot of heat and the BT
probe's expansion zone is narrow, so in still air BT is an instrument pointed at
the chamber: **`beta` 0.34 onto the walls, `tau_p` 36 s**, the only two
parameters stable across every configuration tried.

**The nine-second fan burst is the measurement that does work**, and it is the
run's real product. BT falls **23.5 → 19.5 degC in 9 s** at fan 64 — **3.9 degC**
of still-air bias removed — and 19.5 is *below* the 29 degC room air being drawn
in, so nothing but the bean bed can be what the probe is reading. The procedure
is therefore **charge, wait, short burst, read the trough**; the wait alone does
not work. Only the frozen arm got one, which is much of why the joint fit is
under-determined, so **the cheap follow-up is to repeat the warm arm with a
burst** — one preheat, no beans consumed.

**Bypassing the cooldown guard is benign from a preheat state.** Inlet falls
140 → 97 degC in 4 s, soaks back to only **109-111 degC** at +12-18 s — 30 degC
*below* the running setpoint — then decays with a 510-557 s time constant. The
interlock held; heat was 0 within 1.5 s in arm 1 and never came on in arm 2. One
0.5 s sample of `HT 50` is procedural, not a fault: inlet-off was sent while
Artisan's PID was still running, so it re-sent `INLET 140.1` a tick later and the
inner loop re-engaged until the fan reached 0 — **kill the outer PID before the
inlet**, as arm 2 did. Limits worth keeping: this was a *preheat* state (140 degC
inlet, 45% duty), the element itself is unmeasured, and the `COOL` guard would
not have released for over four minutes here, so it is correctly sized for
exactly this soak.

**The dip is now modelled rather than absorbed into `loss(t)`
(`tools/analysis/charge_dip.py`).** A mixing term in front of the unchanged plant
card: `dT_mix = phi*(BT_c - T_bean)`, delivered as a **decaying rate** — which
matters more than any constant in it. Written as a relaxation toward `BT_mix` the
charge becomes a permanent attractor that fights the heater all roast and the
model flatlines near 62 degC; as a rate it integrates to the right total and
stops. **Refitted 2026-09-07** (state-history.md § The dip model's joint refit):
the rate now carries a **pour ramp** — a uniform pour of width `w_c` convolved
with the exponential, normalised so the heat is still conserved
(`charge_dip.mix_kernel`) — because without it the fit buys the dip's depth by
stretching `tau_mix` to 15 s and then turns 6-7 s late. Fitted jointly to roasts
**50/51/53/54** over each one's loop-free window: `phi`(400 g) **0.7116**,
`tau_mix` **10.84 s**, `w_c` **2.10 s**, rms **1.31 degC**, hence `C_chamber`
276 J/K. `w_c` and `tau_mix` trade at −0.77 — read the band 1.5-3 s.
**`charge_state.py`'s `k` is not `phi`**: `4k = 0.409` is the drop at `+theta`
and already folds in the incomplete mix and the heat the plant put back, so
reading it as the asymptotic fraction under-predicts every charge drop by
7-10 degC. That is a reading error, not a bug in that tool.

**`phi` is depth per degC on the operator's temperature scale, and mixing scales
is a bug that has already cost one roast.** The old `phi` (0.658) was fitted
against a charge temperature *assumed* at −18 degC and then evaluated by
`make_charge_background.py` at the operator's *entered* −12.0 — and 12 degC of
charge temperature is worth 0.07 of `phi`, which is most of why roast 54's
background came out 6.7 degC shallow. The calibration group is now every roast
with an **entered** greens temperature, so the operator's thermometer offset
cancels. The old group, refitted, gives `phi` 0.6475 at a charge temperature of
−24.1 and **asks for the same dip** (99.6 degC against 100.9); `--scale` prints
both. Two independent estimators put roast 54's charge near −24 (`charge_state.py`
−24.1; floating `T_bean` in the joint fit −23.9) against an entered −12.0, and
neither settles it, because both are anchored on the same −18 assumption.

**One disagreement is left open and neither dataset can close it.** The charge-thermal test says
the frozen arm needs extra cold-side thermal mass (`r_fus = 0` costs 20% of
residual) and cannot say how much (5-25 degC-equivalent all within 3%; the point
estimate exceeds the 35 J/g such a charge physically has). The roasts say none,
and since the refit the argument is direct rather than by held-out proxy: **roast
50 is the only *measured* charge temperature in the set (+25 degC) and is
unfrozen**, so `h_fus` cannot touch its depth — across 0-35 J/g its rms goes
1.18 → 4.52 while the frozen roasts improve by a tenth. `charge_dip.py` defaults
to **0** and follows the roasts; `--fusion` prints the table.

**And the standing exposure is unchanged: nothing has yet measured a charge
temperature under flow, or at a bean's core.** `charge_state.py`'s `k`, roast
48's +12.8, roast 49's +15.5 and `charge_dip.py`'s `phi` all rest on charge
temperatures that are either assumed or read off the outside of a bag. The
charge-thermal test could have broken that dependency and does not, because it
has no flow. Detail in state-history.md § The charge-thermal test.

**Roasts 50 and 51 (2026-09-07) are the charge-temperature pair, and
`greens_temp` is finally a measurement: +25.0 and −12.0 degC**, 400 g in / 349 and
351 g out, moisture 10.9%, same lot and session,
`airRoaster_cascadePID_chargetemp.aset` + `profile_003`, no intervention. **Batch
numbers collided**: `airRoaster_50.alog` is now the warm arm, and the 2026-09-06
bench run that held that name (§ The charge-thermal test) was **overwritten with
no backup** — `charge_thermal.json` is the only surviving record and
`charge_thermal.py` now refuses to run rather than analyse the wrong file.

**The preheat protocol works, and the level is fan 58.** At a constant inlet
140.4 in an empty chamber *at equilibrium* the dashboard log gives BT
136.9 / 133.4 / **130.2** at fan 64 / 60 / **58** — Temp_Drive 3.50 / 7.02 /
**10.25**, i.e. −0.88 degC per fan unit over 60-64 steepening to −1.62 over
58-60. So **fan 58 puts the equilibrium exactly on the background's CHARGE_BT**,
and its Temp_Drive matches the 10.5-11.4 roasts 46 and the charge-thermal test
read — *those were transients at fan 60*, and fan 58 reaches the same state as a
fixed point. Pre-charge Temp_Drive came out 9.85 and 9.02.

**`k` is now measured, and the proxy's linear form survives a 37 degC span to
0.34%**: `k = proxy_corr/(BT_charge − T_bean)` reads **0.10578** (warm) and
**0.10542** (frozen), against `charge_state.py`'s assumed-frozen **0.10217** —
**3.4% low**. The historical set re-reads warmer: roasts 43/44/46 at
**−15.6 / −9.7 / −14.5** rather than −18, roast 48 **+15.2**, roast 49 **+19.3**.
The "frozen" group was never at freezer temperature; a charge arrives at about
−10 to −16, which is where roast 51's measured −12.0 sits.

**The fusion enthalpy is closed, against the charge-thermal test.** Any real
`h_fus` inflates the *frozen* roast's apparent `k` — by 2.2 / 4.3 / 8.6 / 15.1%
at 5 / 10 / 20 / 35 J/g. Measured, it reads **0.34% low**, so `h_fus` is under
~1 J/g. The still-air fit wanted 7-35 and could not size it; `charge_dip.py`'s
default of zero was right.

**The early stage overacts, and it is the background, not the tuning.** Roast 51
railed SV to its **300 ceiling for 9 s** with heat at **100% for 24.5 s**; both
roasts then sat on the **140 floor** (36.5 s and 22.5 s) while BT ran **+17 degC
above the background**. Authority is not the problem — the loop hits both rails.
**The overshoot is charge-state-independent**: from 50 s on the two roasts are
within **1.5 degC of each other** despite 37 degC of charge difference. The cause
is `profile_003`'s dip timing — its TP is **67.4 degC at 37 s** against a real
turning point at **21-22 s** — so the loop spends the first 20 s chasing a target
still falling while the bed has already turned, and with nothing the heater does
reaching BT before ~13.5 s its correction lands at 18-28 s, too late to help and
early enough to overshoot. **`charge_dip.py` predicts the turning point to 0-3 s**
(84.0 at 22.0 s vs 80.2 at 22.0; 64.9 at 24.0 vs 63.8 at 21.0; rms 4.2-4.5 degC
over 0-60 s). The model is right and the background is 15-16 s wrong.
*Superseded in part:* those measured turning points are the loop's, not the
bed's — roast 54's **free** dip turns at 23.0 s and the refitted model still
turns ~6 s late against it (state-history.md § The dip model's joint refit). The
background being 15-16 s wrong stands; the model matching to 0-3 s does not.

**And the tuning after the dip is the best on record.** Time-to-BT 150/180/196.5
lands at **−0.4 / +1.7 / −2.0 s** and **−0.4 / +2.2 / −2.0 s** against
`profile_003`, the two roasts agreeing **with each other to 0.5 s at every
level**, error +1.4 degC at 120-180 s falling to +0.4 by 180. A 37 degC charge
difference leaves no trace after DRY END. `pidKp` 3.0, `pidKi` 0.07 and the
lookahead switch all stand. **The next thing to do is generate the background's
first 90 s from `charge_dip.py`** — state-plan.md § What it unlocks item 2, now
unblocked and validated. Detail in state-history.md § Roasts 50 and 51.

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
