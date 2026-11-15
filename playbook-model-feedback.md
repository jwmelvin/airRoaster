# Playbook — feeding roasts back into the engine

**For an LLM in a fresh context.** Work in `/Users/jwmelvin/airRoaster` on a
`feature/…` branch (never commit to `main`, never push). Follow `CLAUDE.md`.
Read `state-current.md` and `roast-space.md` first; this page is the procedure
for one job: **after a batch of roasts, decide whether the engine that authors
backgrounds should change, change it if so, and leave the next reader able to
check you.**

## 1. What you are improving, and what you are not

**The engine** turns a roast spec into a background.

```
spec:   DRY END (time)   FCs (time, at the lot's T_FC)   slope at FCs   DROP (dt, dT after FCs)
batch:  mass, greens_temp, moisture, lot, fan, preheat
                    |
        tools/make_background.py  ->  artisan/profile_*.alog  ->  the loop follows it  ->  the roast
```

**The engine is right when the roast lands on the spec.** Its error is the gap
between what the background said and what the bed did. That is the only thing
this playbook optimises.

**Whether the spec makes good coffee is a different loop, and it is not yours
to close in code.** Cup notes and roast degree change *the spec the operator
asks for* (roast-space.md § Experiments). Never tune an engine parameter to make
a cup result come out. If a session produces a cup finding, write it in
roast-space.md § Record and stop there.

## 2. The engine's parts, and who owns which error

| part | lives in | its numbers | fitted on | known to be wrong about |
|---|---|---|---|---|
| **dip** (0 → TP) | `analysis/charge_dip.py` | `phi(mass)`, `tau_mix`, `w_c` | roasts 50/51/53/54 | `BT_c` term 4.7 degC too steep; mass (5.4 % out at 380 g; TP 1.7 high and 4 s early at 500 g; **8.5 high at 462 g of `C1055`, roast 64**); knows nothing of fan |
| **plant card** | `analysis/plant_roast46.json` | `a`, `theta`, loss cubic | roast 46 | `theta` is total lag, not delay |
| **ramp** (TP → ~110 s) | `make_background.py` `--ror-peak-at` | peak time 53 s | a convention, not a fit | a heavy bed peaks near 70 s (roast 63) |
| **drying term** | `make_background.py` `drying_K` | `eta`, window BT 100-140, shape | roast 62 | **unscored**; scaling with water mass is assumed |
| **RoR family and solver** | `make_background.py` `fit` | four parameters, four constraints | — | cannot take DROP and slope together; with DRY END at 3:12 it cannot put a 201.8 crack before about 6:17 |
| **bean table** | `analysis/beans.py` | `T_FC` per lot | the logs | n = 1 on a new lot |
| **the loop** | `analysis/artisan_pid.py`, `sim.py` | Kp/Ki, lookahead | roasts 46-49 | the docs say 3.0/0.07; the logs and the `.aset` say 2.4/0.056 |
| **slope through crack** | nowhere yet | — | — | achieved runs 0.70 ± 0.68 degC/min under spec (roasts 49-63) |
| **roast degree** | nowhere yet | — | — | weight loss scatters 0.59 % at fixed development |

**Residual → owner.** Read the scorecard top to bottom and assign each miss
before thinking about fixes:

| the scorecard shows | owner |
|---|---|
| TP temperature or time off | dip (then ask: mass, charge, fan, or preheat?) |
| `e` at 45-90 s, entry slope outside ±2 | ramp, or the dip handing it a wrong start |
| `min e` over 120-230 s, **only if the entry slope passed** | drying term |
| DRY END late or early with `e120` fine | drying term or RoR family |
| rms `e`, DRY END → FCs | the loop (it is the reference tracking error) |
| FCs at the wrong time, `e` near zero there | bean table (`T_FC`), not the machine |
| slope at FCs against the curve's | slope-through-crack (new part) |
| mean `e` FCs → DROP, drive rising or falling | development: exotherm, or the curve's end |
| DROP temperature off with DROP time right | RoR family (`dT_dev` follows; it is not pinned) |

## 3. When to run this

- **Three or more new roasts** since the last revision, or
- **one roast that was a deliberate step** in a single input (it counts for more
  than three that drifted), or
- **the same residual, same sign, on two consecutive roasts.**

One surprising roast is a note in the record, not a revision.

## 4. The procedure

### Step 1 — establish what actually ran

The log is not a reliable witness to its own configuration.

```bash
python3 tools/analysis/scorecard.py <n>                      # per roast
python3 downsample_logs.py ~/Documents/artisan/airRoaster_<n>.alog --rows 40
```

Check, and write down any that fail:

- **the background** named in the card is the one intended;
- **`LA 6` fired**: a step in SV near 46 s (about +20 to +24);
- **fan events** match the plan. A fan change inside 0-120 s is a disturbance,
  and the roast's first two minutes then say nothing about the dip or ramp;
- **`greens_temp` is typed by hand.** Ask the operator if it looks like a
  default (roast 63 said 0.0 for a frozen charge). Even when right it is a
  nominal on the operator's scale, not a core temperature;
- **weight out** present; a missing one reads as 100 % loss;
- **the lot** (`plus_coffee`). Never pool `T_FC` across lots.

### Step 2 — the table

```bash
python3 tools/analysis/scorecard.py <all roasts since the last revision, plus the ones that revision was fitted on>
```

Put the table in the record as it prints. Then mark every roast **scored** or
**unscored** per window, by the gates: entry slope inside ±2 degC/min for the
120-230 s window; no fan change for the window it falls in; curve still running
(the background must extend past DROP, because SV falls away after its end).

### Step 3 — assign, then count

For each miss, name its owner (§ 2). Then for each owner with a miss:

1. **How many scored roasts show it, with what sign?** Report the residual from
   two or three reference points where that applies (swing from 100 s, from
   120 s, the minimum). If they disagree the experiment is unscored.
2. **How big is it against that part's own scatter?** Known scatters: TP 2.7 degC
   across four nominally identical −12 roasts; slope at FCs sd 0.68; weight loss
   0.59 %; `T_FC` about 1 degC within a lot.
3. **Count free parameters against independent residuals.** Consecutive BT
   samples correlate above 0.99: a 400-sample window is 5-9 points, and a roast
   is usually **one** point per part. Two parameters cannot be fitted to one
   roast, however many samples it has.
4. **Is there a cheaper explanation outside the engine?** An entry slip, a fan
   move, a cold machine (roast 59: first roast of the day settles in 23 min, the
   second in 3), a different preheat.

**Change a part only if** the miss is repeated or deliberate, clears the
scatter, and has no cheaper explanation. Otherwise record it under "watching"
with the roast numbers, so the next session can add to the count.

### Step 4 — make one change

- **One part per revision.** Two changes that both move the first two minutes
  cannot be told apart afterwards.
- **Refit on every roast the part applies to**, not on the new ones. State which
  roasts are in, which are out and why.
- **Fit and evaluate on one scale.** A number fitted against assumed charge
  temperatures and then handed measured ones cost roast 54 (6.7 degC of dip).
- **Prefer a structural reason to a constant.** A term written so it scales
  (`K` with water mass) transfers; a constant fitted to one roast does not. Say
  which parts of the form are measured and which are assumed.
- **Then difference the curves.** Regenerate the last background with the new
  engine and print new minus old over the whole roast. The size of the term you
  added is not the size of the change: the constrained solve pays it back
  elsewhere (the drying term's 1.62 degC became +0.85 at 100 s and nothing after
  160 s).
- **Back-test.** Re-author the backgrounds of the roasts the part was fitted on
  and of at least two it was not, and compare against what those beds did.
  A revision that helps the new roasts and hurts the old ones is a refit to
  noise. Print the before and after for every one.
- `make_background.py`'s own check block must still pass: four constraints at
  0.00, RoR monotone, peak well under 72 degC/min.

### Step 5 — write the prediction before the next roast

**A revision without a written prediction cannot be scored.** In
roast-space.md § Record, before any beans are used:

- the scorecard rows the change should move, with numbers and a band;
- the rows it must **not** move;
- what result would mean the change is wrong.

### Step 6 — record and commit

- roast-space.md § Record: the table, the assignments, what changed, what is
  being watched, the prediction.
- § 2 of this file: update "fitted on" and "known to be wrong about". **This
  table is the engine's memory; keep it true.**
- `tools/README.md` if an input or a default changed.
- Bump the background's version suffix (`_v10`, …) and never overwrite a
  background a roast was run on: the logs point at it by path.
- One commit, `tools:` or `plan:` prefix, with the docs in the same commit.

## 5. Things this effort has already paid for

- **A claim repeated in every doc can still be unverified.** "Three parameters,
  three marks" was written everywhere and was false; the fit had a free
  direction and the ramp was noise for four backgrounds.
- **"One variable at a time" is a means to attribution, not a rule.** Do the
  arithmetic: if the confound is worth a tenth of the effect, run the roast.
- **An excursion scored from one start time is not scored.**
- **A proxy constant is not a physical fraction**, and `theta` is not a
  transport delay. Do not move a number between models that define it
  differently.
- **Circulation is per lot.** A fan floor from one coffee is not another's.
- **The operator knows things no log shows**: what the bed looked like, where
  the beans came from, what they meant to type. Ask before modelling around it.

## 6. Backlog — what the engine needs next, in order of what it unblocks

1. **A development segment**, so the spec's DROP point and slope at FCs can both
   be pinned (roast-space.md § 5). Unblocks experiments S2-S4.
2. **A slope-through-crack correction**: the bed arrives 0.7 degC/min under the
   curve. Needs the slope varied on purpose first (S3); do not fit it on ten
   roasts that all asked for 8-9.5.
3. **A forward prediction** (`sim.py` driven from an authored background: dip →
   plant → PID), so step 5's prediction is computed, not estimated.
4. **The dip's mass and fan terms.** Needs a mass pair at one fan, or a fan pair
   at one mass. S1's 462 g on the 400/500 g ramp spec is one more point.
5. **A roast-degree model**: weight loss against `D(Q)`, once roasts exist
   outside the 20-36 s corner.
