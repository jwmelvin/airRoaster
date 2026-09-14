# Row L — the latent-heat term in the background's RoR spec

Work in `/Users/jwmelvin/airRoaster` on a `feature/…` branch off `main` (never
commit to `main`, never push). **Read `state-current.md` first** — the HANDOFF
section is the whole job — then `state-plan.md § TEST PLAN` and
`state-history-residual.md § Roast 62`. Follow `CLAUDE.md`: commit each finished
unit with the state docs updated in the same commit, and run `./verify.sh`.

This is two pieces of work with a roast between them. **Do part 1 completely and
stop**; part 2 runs when the operator brings back the log.

---

## Part 1 — design the term and author the background (desk work, no beans)

### What you are modelling

Every cascade roast falls below its own background between about 110 and 200 s
and recovers by 300. At fan 60 (roast 56) the minimum is **−2.91 degC at 165 s**;
at fan 64 (roast 62) it is **−1.50 at 179 s**. The difference is the 120 s fan
step, measured at **1.4-1.7 degC**. **What is left — about 1.5 degC — is
evaporative load the background's RoR specification does not carry**, and that is
what you are adding.

**Size it on roast 62** (`~/Documents/artisan/airRoaster_62.alog`, background
`artisan/profile_400g_m5C_v4.alog`). It is the only roast that entered the window
flat — entry slope over 85-115 s is **−0.03 degC/min** — so it is the only one
whose residual is not contaminated by a charge-phase transient. Roasts 56, 57 and
60 enter at −1.22, −6.65 and −5.01; **do not size anything on 57 or 60.**

### Two facts that decide how you fit it

1. **Through the descent the error is approximately the load.** The feature has a
   period near 100 s, which is **2.1× the loop's 213 s crossover period**, and at
   2× crossover a 33.7 degC phase margin gives `|S| ≈ 1` — essentially no
   rejection. So the RoR deficit `d(e)/dt` over the descent reads the load
   directly. **The slow tail after ~200 s is loop dynamics and is not load** —
   do not fit to it. (state-history-residual.md § Is the dip the loop ringing?)
2. **The deficit is a function of BT, not of the clock.** Across roasts 56, 57
   and 60 the RoR deficit ends at **BT 135-140** every time — not at DRY END
   (BT 149) and not at a fixed second. Parameterise in BT. Check roast 62 gives
   the same endpoint before you rely on it.

### What the tool does not have

`tools/make_background.py` builds BT as the integral of a RoR specification of
the form `rise(u) × fall(u)`: **four free parameters pinned by exactly four
constraints** — three marks plus `--ror-peak-at` (default 53, a spec in force,
read `state-plan.md § The RoR-peak pin` before touching it). There is no drying
term. `--h-fus` is heat of **fusion** in the charge dip — melting a frozen
charge — a different quantity; do not reuse it.

So you are adding a **fifth shape term**, subtractive, over a BT window. It will
move DRY END, FCs and DROP, so the four-constraint solve has to re-converge with
it in place. Keep the existing family and constraints intact; the term is an
addition, not a reshaping.

**Parameterise it physically where you can.** `moisture_greens` is recorded on
every roast since 56 (11.0 %) and mass is known, so the term's *magnitude* should
scale with water mass rather than being a free constant fitted to one roast.
Its *shape* in BT is what roast 62 measures. Say plainly in the docs which parts
are measured and which are assumed — one roast cannot identify both.

### Deliverables for part 1

- the term implemented in `make_background.py`, with `--help` and the module
  docstring updated in the file's existing voice;
- a new background authored for **400 g, `--greens-temp -5`, `C1043`** — keep the
  standing nominal even though the dip it authors is ~5 degC too shallow
  (background TP 59.2 against roast 62's measured 53.8). That offset is known and
  tolerated: roast 62 shows it does not break the entry slope, and a nominal that
  moves per roast makes backgrounds incomparable, which is the whole reason the
  nominal exists. **Do not "fix" it inside this task**;
  (`tools/analysis/beans.py --coffee C1043` for `--fcs` / `--ror-at-fcs`),
  written to `artisan/` with a version-bumped name;
- **the desk check, printed and pasted into the commit**: all four constraints at
  0.00, RoR monotone both sides of the peak, and the new curve against
  `profile_400g_m5C_v4.alog` over 120-300 s — state how much it differs and
  where, since that difference *is* the intervention;
- a prediction, written down before the roast: **what `BT − background` should
  do over 100-320 s if the term is right.** Getting this on the record first is
  the point of the exercise.

---

## Part 2 — score the test roast

The roast is `airRoaster_<n>.alog` in `~/Documents/artisan/`. Configuration:
**fan 64 held for the whole roast** (`artisan/airRoaster_cascadePID_phaseB.aset`,
alarm rows 7 and 8 off, row 9 on), 400 g `C1043`, `greens_temp −5.0`,
`moisture_greens 11.0`, **the new background** — so against roast 62 the single
change is the background.

### Gate it before reading anything

1. **Entry slope over 85-115 s must be inside ±2 degC/min.** Outside that, the
   roast is **unscored** — say so and stop; do not read 120-230 s. This gate
   exists because Phase B published a fan number it had not measured
   (state-history-residual.md § Correction).
2. **Charge proxy**: `python3 tools/analysis/charge_state.py 62 <n>`. Roasts 60
   and 62 agree to 0.07 per 100 g and that is what makes them comparable; roast
   56 sits 1.77 off and cannot be paired with either. If the new roast is more
   than ~0.2 from roast 62, say so and treat the pairing as weakened.
   **Pair on the proxy, never on the entered `greens_temp`** — it is a nominal
   from an emissivity-sensitive IR reading of the bean *surface*, and two
   independent instruments put roasts 60/62 12-17 degC colder than roast 56 while
   the entered number was identical for all three
   (state-current.md § 1b).
3. **B6 and B3** from `state-plan.md § Phase B` — mass, greens, alarm rows, no
   `Air` event at 120 s, nothing in the gate between +1 s and the PID handover,
   `LA 6` at ~46 s, no SV step at 105 s, and the auto-DROP chain firing within a
   second or two of the mark.

### The read

`BT − background` on the 0.5 s grid at 10 s marks over 100-320 s, plus the
minimum and its time over 120-230 s, the rms over 120-230, and **the swing from
100 s and from 120 s as well as the absolute minimum**. Report all three. If
they disagree, the entry was not clean and the gate missed it.

Baseline: **roast 62, −1.50 @ 179 s, rms 1.06, swings −1.66 and −1.12.**

| outcome | reading |
|---|---|
| \|e\| under ~0.7 across 120-230, no coherent dip | the term is right; the residual is closed |
| dip shrinks to roughly −0.7 to −1.0 | partly right — refit the magnitude, keep the shape |
| dip unchanged near −1.5 | the term is in the wrong place or the load is not evaporative |
| a **new** feature appears, or the dip moves | record it; do not force it into the model |

**Over-correction is a real outcome and must be reported as one**: if `e` goes
*positive* over 130-200 the term is too large, and that is as informative as the
dip surviving. Also score the four checks, the 120 s → DROP tracking rms (roast
62's **0.67** is the record), and `HT` in the 130-200 / 200-300 / 300-370 windows
against roast 62's 63.18 / 67.95 / 70.89.

### Then

Update `state-current.md`, `state-plan.md` and `state-history-residual.md` in the
same commit as the result, moving the narrative into the history file and leaving
only what is true in the other two. If the term worked, the next open item is
row Q (the settled-fan preheat) and then bringing the fan down off 64 as a
whole-roast change.
