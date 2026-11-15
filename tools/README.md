# Authoring a background for the next roast

**Orientation brief.** If you are a fresh context whose job is "make the
background for roast *N*", this page is the whole task. The tools' own
docstrings are *rationale* — why the curve is shaped this way, what was
measured, what was got wrong — and are worth reading once, not before every
roast. `analysis/README.md` catalogues the investigation tooling.

## What the background is

The outer loop follows it. `BT(t)` from this file **is** the setpoint:
Artisan's PID reads `BT(t + svLookahead)` off it and commands the inlet. So the
curve is the roast specification, and everything else in the config is how well
the loop follows it.

Two halves, drawn separately:

| `0 .. TP` | the **dip** — physics. Mass, charge temperature and the machine decide it; nothing here is a choice. |
| `TP .. DROP` | the **design** — a rate-of-rise curve, integrated to BT so it is smooth by construction, **less the drying load** between BT 100 and BT 140. |

## Five inputs, and where each comes from

| input | source | never |
|---|---|---|
| `--mass` | the scale, for **this** roast | scale a background from another mass — the mass term is 5.4% out and in the wrong direction (state-current.md § The mass term) |
| `--greens-temp` | the operator's thermometer, **read the same way every time** | mix scales — `phi` absorbs any offset and is only right if fed numbers read the same way (`analysis/charge_dip.py --scale`) |
| `--fcs`, `--ror-at-fcs` | `analysis/beans.py --coffee <hr_id>` | pool across coffees — see below |
| `--development` | how the operator roasts: seconds from FCs to DROP | pin a DROP temperature instead unless you mean to |
| `--moisture-greens` | the roast's own `moisture_greens` field (11.0 on this lot) | leave it at the default for a lot that reads differently — it sets the drying term's size |

**To pin DROP as well, use `--drop-after <s>:<dT>` in place of
`--development`**: DROP that many seconds after FCs and that many degC above it,
with `--ror-at-fcs` still setting the slope through crack. Development then gets
its own decaying segment after FCs (roast-space.md § 5). The tool refuses a DROP
that would need RoR to rise after crack. It also defaults `--hold 30`, which
puts the file's DROP mark 30 s after the intended drop so SV keeps updating:
**drop by the clock, not by the mark.** `--hold <s>` works in the other modes too.

A sixth input, `--ror-peak-at`, has a default (53 s) and normally stays there.
It is the constraint that pins the **ramp**; see § The ramp used to be a lottery.
The drying term (§ below) has three more, `--drying-eta`, `--drying-window` and
`--drying-shape`, which are the *calibration* and stay put; `--no-drying`
authors the pre-2026-09-13 curve for comparison.

The coffee's hr_id is in the last roast's `.alog` as `plus_coffee`.

**Changing a mark is not free, so change one thing at a time.** `profile_400g_m5C_v4.alog`
carries `--fcs 399:198.8 --ror-at-fcs 8.3`, and 198.8 is the retired
pooled-across-three-coffees figure; `beans.py` now reads **197.4 / 9.1** for
`C1043`. Regenerating onto the lot's own numbers moves the curve **+1.1 degC at
90-120 s and −1.8 degC at 300-320 s** — larger than most of the effects being
measured, and squarely inside the window the residual is scored in. It is a
wanted correction and it wants its own roast.

## The recipe

```bash
.venv/bin/python tools/analysis/beans.py --coffee C1043      # prints --fcs and --ror-at-fcs
.venv/bin/python tools/make_background.py --mass 400 --greens-temp -5 \
    --fcs 399:198.8 --ror-at-fcs 8.3 --development 28 --moisture-greens 11.0 \
    --compare artisan/profile_400g_m5C_v4.alog \
    --out artisan/profile_400g_m5C_dry_v7.alog
```

(That is the command that authored `profile_400g_m5C_dry_v7.alog`, the current
400 g / −5 degC background. The marks are **v4's**, deliberately — see the note
above — so that the drying term is the only thing that changed.)

Then read the check block it prints, and do not load the file until all four
hold:

1. **All four constraints at `0.00`** — DRY END, FCs, RoR@FCs *and* the RoR
   peak row. Four free parameters against four constraints, so anything else
   means the fit failed, not that the curve is slightly off. If the peak row
   misses, the tool says so in as many words: the ramp is then back to being
   whatever the solver picked.
2. **RoR monotone** rising TP→peak and falling peak→DROP. A non-monotone RoR is
   the merge-tool defect this authoring tool exists to avoid.
3. **The RoR peak height, against `--compare`'s.** The ceiling is what the
   machine has actually delivered — **72 degC/min**, roast 54 — and the authored
   curves sit at 43-48, so a peak near the ceiling is a specification the loop
   will saturate against. Its *timing* is no longer diagnostic, because it is
   now an input: it is whatever `--ror-peak-at` says.
4. **The `30-120 s` row against `--compare`.** This is the one people skip.

**And read the residuals, do not assume they are zero.** The four-constraint
solve reaches 1e-14 at 400 g over `--greens-temp` −24…0, which is the corner
every roast has been run in — but **not everywhere**. At 250 g / +25 degC the
RoR@FCs constraint is missed by 1.6 degC/min with or without the drying term
(the term makes it slightly *better*, never worse): the marks are simply not
reachable by this family from that turning point. The tool prints the number; a
non-zero error row means the curve is approaching the marks, not hitting them.

## The ramp used to be a lottery — fixed 2026-09-08

**This was the trap that cost the most, and it was a defect, not a property of
the curve.** The exponential RoR spec has **four** free parameters
(`tau_r, R0, R_inf, tau_d`); DRY END, FCs and RoR-at-FCs supply **three**. The
fit was underdetermined by exactly one, and every point along the leftover
direction hit all three marks to 1e-14 while being a visibly different roast:

| `tau_r` | 4 | 15 | 30 | 50 |
|---|---|---|---|---|
| BT at 60 s | 80.8 | 75.8 | 72.7 | 71.3 |
| RoR peak at | 44 s | 64 s | 77 s | 83 s |
| max residual | 3e-14 | 0 | 3e-14 | 0 |

Which one you got was decided by which of the four multi-starts converged
marginally lower on floating-point noise. That is why a 1.1 degC change to the
FCs mark — **340 s away** — appeared to move BT at 60 s by 4.8 degC and the peak
by 21 s, non-monotonically in the mark. **The coupling was never physical.** The
back-half marks hardly constrain the ramp at all; the solver was sliding along
the manifold, and the shape of the window all four roast checks live in was
noise. The four backgrounds this tool has authored show it directly — their RoR
peaks land at **65, 68, 53 and 69 s** (`m12C_v3`, `m12C_v4`, `m5C_v4`,
`m5C_fc195_v5`) with nobody having chosen any of them.

`--ror-peak-at` is the fourth constraint. With it the system is square, it
converges to 1e-14 at 400 g across `--greens-temp` −24…0 in both `--development`
and `--drop` mode (**not** everywhere — see the residual note above), and what is
left is the honest coupling:

| `--fcs` | 198.8 | 197.7 | 197.4 | 195.5 | spread |
|---|---|---|---|---|---|
| BT at 60 s, **before** | 80.6 | 74.8 | 78.1 | 73.4 | 7.2 degC, non-monotone |
| BT at 60 s, **now** | 78.4 | 78.7 | 78.8 | 79.3 | **0.8 degC, monotone** |

0.25 degC of first minute per degC of FCs, in the direction that makes sense: a
cooler FCs target needs a weaker decline, so a little more rate early to still
make DRY END. **A back-half edit is now a back-half edit.**

Three things follow.

- **The peak's *time* is pinned, not its height.** Height barely varies along
  the old null manifold — 48.2 to 43.5 degC/min across the whole of it — so it
  identifies the missing parameter eight times worse than the time does
  (`d(peak)/d(tau_r)` = −0.10 degC/min/s against +0.85 s/s). This README used to
  say the peak's timing "is not a spec but is diagnostic". It is a spec now,
  because something in the ramp has to be.
- **The default, 53 s, is not a measurement.** It is where
  `profile_400g_m5C_v4.alog` happens to peak — the background roast 56 was
  scored against, and the only curve that has passed all four checks — so the
  fix does not silently reshape anything. It was a lottery draw, promoted to a
  spec so it stops moving. The reachable band at 400 g / −5 degC is about
  45–80 s. Vary it deliberately, one roast at a time, like any other number.
- **A regenerated background is still a change to the first minute** — just a
  small, monotone, attributable one now. Keep it as its own roast until the
  0.8 degC has been seen on the machine rather than only in the fit.

`--free-ramp` reproduces the old, undetermined behaviour, for regenerating a
pre-2026-09-08 file to compare against. It prints a warning saying so.

**The FCs mark is a label.** Nothing in the cascade reads it — `calcSV` uses
only `BT(t + svLookahead)` and `drop_t`. A curve marked 198.8 that passes 195.4
at 375 s still cracks a 195.4 bean at a repeatable 375 s. Regenerate when you
want the crack at a different **time**, not to make the label true.

## The drying term — added 2026-09-13, runbook row L

**The RoR specification above carries no evaporative load, and a wet bed cannot
make it.** Every cascade roast falls below its own background between about 110
and 200 s and recovers by 300. Roast 62 — the only roast to enter that window
flat — bottoms at **−1.50 degC at 179 s**, of which the 120 s fan step accounts
for none (roast 62 held fan 64 all the way). That is what the term is.

```
RoR(u) = rise(u) * fall(u) / (1 + K*g(BT))          K = 1.62 degC at 400 g / 11.0 %
```

`g(BT)` is the free water released per degC of BT, a single bump over
**BT 100 → 140**, normalised so the term costs exactly `K` degC of BT however
fast the curve crosses the window.

| | | |
|---|---|---|
| **measured** | the window's far end | the RoR deficit crosses zero at **BT 138-141** on roasts 56, 57, 60 and 62 alike — not at DRY END (BT 149), not at a fixed second. That is why the term is written in BT |
| **measured** | the total, `K` | **1.62 degC** at 400 g / 11.0 %, fitted over roast 62's descent (100-175 s) to rms 0.076 degC |
| **assumed** | the onset, BT 100 | water boils. The term leaves BT 100 at zero and grows linearly, so it first clears the residual's own 0.1 degC quantisation near BT 105 — which is where roast 62's deficit becomes visible |
| **assumed** | that `K` scales with water mass | `eta * m_w * h_vap / (m*c_b + C_chamber)`. **Nothing measures this**; it is what lets the term transfer to another mass or another lot's moisture instead of being a constant fitted to one roast. `eta = 0.0156` is a lumped number, not an evaporation efficiency |
| **weakly measured** | the shape exponents | `q = 1.0` costs 0.016 degC of rms against the fitted 1.4. The roast says the release is a single bump; it does not pin its exponents |

**What the term does to the curve, which is the part to look at before loading
it.** The four-constraint solve re-converges with the term in place, so DRY END,
FCs, RoR@FCs and the peak are all still hit — which means the rate the term
removes inside the window is paid back *before* it. At 400 g / 11.0 %, `v7`
against `v4`:

```
   t      40     60     80    100    120    140    160    180    200 .. 427
 dBT   -0.01  +0.28  +0.66  +0.85  +0.46  +0.05  -0.10  -0.04  +0.02 .. +0.01
 dRoR  +0.27  +1.17  +1.04  -0.54  -1.43  -0.91  -0.00  +0.21  +0.13 .. +0.02
```

**About +1.2 degC/min more rate over 50-90 s and 1.4 degC/min less over
105-140 s, and nothing at all after 160 s.** The intervention is to get the bed
about 0.85 degC ahead by the time the water boils and then let the drying load
spend that lead. It is not a lowering of the curve through the dip: over
120-300 s the two curves differ by at most **0.46 degC, at 120 s**.

**So the term can only relieve about half the swing on its own.** Over 100-180 s
`v7` asks for 0.89 degC less BT gain than `v4` against a measured 1.66 degC of
swing; the other 0.77 has to come from the loop actually delivering the extra
front-end rate. That is what the scoring roast tests, and `e` at 100 s is the
sample that says which happened.

## The other four, briefly

- **Never pool FC temperatures across coffees.** A "mean over roasts 50-55" of
  198.8 is a mean over three lots and describes none of them. `beans.py` groups
  by `plus_coffee` for exactly this reason, and filters on `roastertype` because
  the log directory holds ~530 files from two other roasters.
- **`greens_temp` is on the operator's scale, not a bean core temperature.** It
  is a number to be read consistently, not to be got right.
- **The dip model is calibrated at +25 and −12 degC only.** −5 is interpolated;
  roast 56 is its one point there and its worst fit (1.5 degC over-predicted,
  still inside the −12 group's own 2.7 degC scatter).
- **Artisan cannot store any of this.** The `Coffee` record artisan.plus syncs
  (`~/src/artisan/src/plus/stock.py:82-94`, v4.2.0) has no temperature field.
  The logs are the store; `beans.py` is the reader.

## After the roast

```bash
.venv/bin/python tools/analysis/beans.py --coffee <hr_id>   # did the lot move?
python3 tools/analysis/charge_state.py                      # how cold the charge was
```

Then score the roast against the four checks in state-current.md § HANDOFF, and
write the record. Read **state-current.md first** — it carries the active
effort, the alarm table to verify before every roast, and which background is
actually loaded.
