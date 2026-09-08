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

1. **All three marks at `0.00`.** They are fitted against three free
   parameters, so anything else means the fit failed — not that the curve is
   slightly off.
2. **RoR monotone** rising TP→peak and falling peak→DROP. A non-monotone RoR is
   the merge-tool defect this authoring tool exists to avoid.
3. **The RoR peak, against `--compare`'s.** The ceiling is what the machine has
   actually delivered — **72 degC/min**, roast 54 — and the authored curves sit
   at 43-48, so a peak near the ceiling is a specification the loop will
   saturate against. Its *timing* is not a spec but is diagnostic: it moves
   20 s for a 1 degC change to a mark 340 s away, so a peak that has jumped
   means a constraint moved, not that the curve improved.
4. **The `30-120 s` row against `--compare`.** This is the one people skip.

## The trap that costs the most

**Moving a back-half mark moves the first minute.** The RoR spec is one
three-parameter exponential fitted to `BT(DRY END)`, `BT(FCs)` and `RoR(FCs)`,
so every constraint reshapes the whole curve — and the early ramp is not even
monotone in the mark. At 400 g / −5 degC:

| `--fcs` | 198.8 | 197.7 | 197.4 | 195.5 |
|---|---|---|---|---|
| BT at 60 s | 78.1 | 73.3 | 74.1 | 74.5 |
| RoR peak at | 52 s | 73 s | 70 s | 69 s |

A 1.1 degC change to a mark **340 s away** moves BT at 60 s by 4.8 degC and the
peak by 21 s — right through the window the roast checks are scored in. So:

- **Never run a regenerated background and a control change in the same roast.**
  The whole method here is one or two changes in *disjoint* regions; a new
  background is not disjoint from anything.
- **The FCs mark is a label.** Nothing in the cascade reads it — `calcSV` uses
  only `BT(t + svLookahead)` and `drop_t`. A curve marked 198.8 that passes
  195.4 at 375 s still cracks a 195.4 bean at a repeatable 375 s. Regenerate
  when you want the crack at a different **time**, not to make the label true.

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
