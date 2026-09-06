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
| `roast48_plant.py` | the plant from roast 48's **designed** inlet steps: the fan term (`kf = 0`), the sub-window instability, and the two-lag alternative to the deadtime |
| `dip_strategies.py` | charge-state robustness of the dip strategies; state-plan.md § Dip strategies |
| `roast47_ff.py` | refits `feedforward()` from roast 47's fan x SV grid; **stdlib only**, no venv needed |
| `roast48_ff.py` | the same grid **loaded** (roast 48, 400 g): does the empty map transfer, is `slope(SV)` a line, and the pooled 47+48 fit; **stdlib only** |
| `roast49_step6.py` | roast 49 against state-plan.md § Step 6's predictions, and the PID replay at 0.5 s sampling |
| `charge_state.py` | how cold the beans were: the control-independent mixing proxy, air-corrected; **stdlib only** |
| `plant_roast46.json` | the plant card `tools/merge_inlet_base.py` reads: `a`, `theta` and the loss cubic, with provenance |
| `plant_roast48.json` | roast 48's plant, **not** an authoring source (`supersedes_plant_roast46: false`); its settled content is `kf` |
| `ff_roast47.json` | the `feedforward()` card: the product-form coefficients, the affine fallback and the fitted box |
| `ff_roast48_loaded.json` | the loaded check: transfer error against the flashed map, per-setpoint fan slopes, and the pooled 47+48 refit |

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy   # .venv/ is gitignored
.venv/bin/python tools/analysis/roast46_refit.py
.venv/bin/python tools/analysis/roast46_refit.py --emit-plant   # refresh plant_roast46.json
.venv/bin/python tools/analysis/roast48_plant.py                # the designed-excitation refit
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
python3 tools/analysis/charge_state.py              # run this after every roast
```

`charge_state.py` is the one to run habitually: it is the only read the project
has on the charge state, and it stops being an inference the moment `greens_temp`
is filled in.

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
- **A plant card is not automatically the best one available.** Roast 48's
  excitation is designed and roast 46's is accidental, yet `plant_roast46.json`
  is still what `merge_inlet_base.py` reads: roast 48's `a` and `theta` are not
  stationary across its own sub-windows, and the one closed-loop behaviour on
  record (roast 45's 177 s ring at Ki 0.10) is predicted by roast 46's card and
  not by roast 48's. Check a fit against a *measured closed-loop* response before
  letting it move any tuning.
