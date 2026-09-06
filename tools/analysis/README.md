# Offline analysis of the Artisan cascade

Python, numpy + scipy. Nothing here runs on the roaster; it reads roast logs and
reproduces the outer loop so tuning can be tested before it is roasted.

| file | what it is |
|---|---|
| `roastdata.py` | loaders for Artisan `.alog` and the dashboard CSV, plus the CHARGE alignment |
| `plantfit.py` | first-order-plus-deadtime identification of `Inlet -> BT` |
| `artisan_pid.py` | a faithful port of Artisan v4.2.0's software PID and its Follow-Background plumbing |
| `sim.py` | the closed-loop simulator: background -> PID -> inlet SV -> inner loop -> plant |
| `margins.py` | frequency-domain phase margin for the same loop |
| `roast46_refit.py` | driver that reproduces the numbers in state-plan.md § Roast 46 refit |
| `dip_strategies.py` | charge-state robustness of the dip strategies; state-plan.md § Dip strategies |
| `roast47_ff.py` | refits `feedforward()` from roast 47's fan x SV grid; **stdlib only**, no venv needed |
| `roast48_ff.py` | the same grid **loaded** (roast 48, 400 g): does the empty map transfer, is `slope(SV)` a line, and the pooled 47+48 fit; **stdlib only** |
| `plant_roast46.json` | the plant card `tools/merge_inlet_base.py` reads: `a`, `theta` and the loss cubic, with provenance |
| `ff_roast47.json` | the `feedforward()` card: the product-form coefficients, the affine fallback and the fitted box |
| `ff_roast48_loaded.json` | the loaded check: transfer error against the flashed map, per-setpoint fan slopes, and the pooled 47+48 refit |

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy
.venv/bin/python tools/analysis/roast46_refit.py
.venv/bin/python tools/analysis/roast46_refit.py --emit-plant   # refresh plant_roast46.json
```

`--emit-plant` is the seam between this directory and the authoring tools: it
writes the three plant numbers and the loss cubic into `plant_roast46.json`, and
`tools/merge_inlet_base.py` (stdlib only) reads that to build the step-9
feed-forward schedule. After the characterisation roasts (runbook steps 3-5),
re-run `--emit-plant` and re-run the merge; nothing else changes.

Roast logs live outside the repository (`~/Documents/artisan/`, `~/Downloads/`);
the paths are at the top of `roast46_refit.py`.

```bash
python3 tools/analysis/roast47_ff.py --emit-card    # no venv: stdlib only
python3 tools/analysis/roast48_ff.py --emit-card    # reads roast 47 too, for the pooled fit
```

Four traps the code encodes so they cannot be repeated:

- The CHARGE origin is `timex[timeindex[0]]`, and `timeindex[0] == 0` is a
  **valid** index, not "unset" (`profile_003` relies on it).
- A plant delay cannot be identified while the disturbance is a free function of
  time. `fit_integral` restricts it to a low-order polynomial; `fit_disturbance`
  relaxes that only *after* the plant parameters are fixed, and exists purely to
  give the simulator something to run against.
- A coefficient is only as good as the range its input moved over.
  `feedforward()`'s `SV` term was fitted from preheat steps that barely moved SV
  and came out **26x** too small; `roast47_ff.py` refuses a design matrix whose
  inputs did not move independently, and cards the fitted box alongside the
  coefficients so an extrapolation is visible as one.
- **Artisan rewrites the two samples before every step in a constant-valued
  channel.** `inputFilter` (canvas.py:4535) ends with an "improve a previously
  corrected reading" repair that un-sticks an equal run by linear interpolation,
  destructively, in the array it saves; the gate is any of `minmaxLimits` /
  `dropSpikes` / `dropDuplicates`, and `dropSpikes` alone is on. `SV` and `HT`
  are constant by construction and trip it constantly. Window means survive
  (0.10 %); transient timing does not. `roast48_ff.py` opens every guard
  `FILTER` seconds *before* a step. Untick **Drop Spikes** and this goes away.
