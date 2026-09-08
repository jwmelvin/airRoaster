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
| `TP .. DROP` | the **design** — a rate-of-rise curve, integrated to BT so it is smooth by construction. |

## Four inputs, and where each comes from

| input | source | never |
|---|---|---|
| `--mass` | the scale, for **this** roast | scale a background from another mass — the mass term is 5.4% out and in the wrong direction (state-current.md § The mass term) |
| `--greens-temp` | the operator's thermometer, **read the same way every time** | mix scales — `phi` absorbs any offset and is only right if fed numbers read the same way (`analysis/charge_dip.py --scale`) |
| `--fcs`, `--ror-at-fcs` | `analysis/beans.py --coffee <hr_id>` | pool across coffees — see below |
| `--development` | how the operator roasts: seconds from FCs to DROP | pin a DROP temperature instead unless you mean to |

A fifth input, `--ror-peak-at`, has a default (53 s) and normally stays there.
It is the constraint that pins the **ramp**; see § The ramp used to be a lottery.

The coffee's hr_id is in the last roast's `.alog` as `plus_coffee`.

## The recipe

```bash
.venv/bin/python tools/analysis/beans.py --coffee C1043      # prints --fcs and --ror-at-fcs
.venv/bin/python tools/make_background.py --mass 400 --greens-temp -5 \
    --fcs 399:197.7 --development 28 --ror-at-fcs 9.4 \
    --compare artisan/profile_400g_m5C_v4.alog \
    --out artisan/profile_400g_m5C_fc197_v6.alog
```

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
converges to 1e-14 across −24…+25 degC and 250…500 g in both `--development`
and `--drop` mode, and what is left is the honest coupling:

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
