# Offline analysis of the Artisan cascade

> Authoring a background for the next roast? **`../README.md` is the
> orientation brief** — four inputs, the recipe, and the traps. This page is
> the catalogue of the investigation tooling.

Python, numpy + scipy. Nothing here runs on the roaster; it reads roast logs and
reproduces the outer loop so tuning can be tested before it is roasted.

| file | what it is |
|---|---|
| `roastdata.py` | loaders for Artisan `.alog` and the dashboard CSV, plus the CHARGE alignment |
| `plantfit.py` | identification of `Inlet -> BT`: first-order-plus-deadtime, the two-lag variant, the fan-scaled gain, block bootstraps for both structures |
| `artisan_pid.py` | a faithful port of Artisan v4.2.0's software PID and its Follow-Background plumbing |
| `sim.py` | the closed-loop simulator: background -> PID -> inlet SV -> inner loop -> plant |
| `margins.py` | frequency-domain phase margin for the same loop |
| `roast46_refit.py` | driver that reproduces the numbers in state-plan.md § Roast 46 refit |
| `roast48_plant.py` | the plant from roast 48's **designed** inlet steps: the fan term (`kf = 0`), the sub-window instability, and the two-lag alternative to the deadtime (followed up in `deadtime_vs_lag.py`) |
| `dip_strategies.py` | charge-state robustness of the dip strategies; state-plan.md § Dip strategies |
| `roast47_ff.py` | refits `feedforward()` from roast 47's fan x SV grid; **stdlib only**, no venv needed |
| `roast48_ff.py` | the same grid **loaded** (roast 48, 400 g): does the empty map transfer, is `slope(SV)` a line, and the pooled 47+48 fit; **stdlib only** |
| `roast49_step6.py` | roast 49 against state-plan.md § Step 6's predictions, and the PID replay at 0.5 s sampling |
| `deadtime_vs_lag.py` | is `Inlet -> BT` a deadtime or a lag?  Excitation screen, the `(theta, tau2)` identifiability surface, the two-lag bootstrap, the margin arithmetic under both structures, and what it does to the step-9 lead |
| `charge_state.py` | how cold the beans were: the control-independent mixing proxy, air-corrected; **stdlib only** |
| `charge_thermal.py` | the charge-thermal test's two no-flow charge decays. Primarily an **identifiability report**: what the still-air decay measures (the probe's weighting onto the chamber, the fan-burst bias) and what it cannot (the chamber capacity, the charge temperature). ~14 min |
| `dekick_tp.py` | how much of a measured turning point is the loop's own kick: backs the inlet excess out of the dip with the plant card, so the dip model is not refitted against the overshoot it caused |
| `charge_dip.py` | the charge dip from `(mass, greens temp)`: a mixing term (pour ramp + exponential) in front of the plant card, fitted jointly to roasts 50/51/53/54 over their loop-free windows. `--ramp` profiles `w_c`; **`--scale` is the one to read before trusting `phi`** |
| `preheat_lever.py` | **can the preheat absorb a varying charge temperature?** Sizes the compensation (~1.17 degC of preheat per degC of greens at 400 g), what it buys (the demanded peak RoR spread falls 21.9 → 6.2 degC/min) and — the part that matters — which half of the answer is measured. `--experiment` sizes the roast that would settle it |
| `fan_ladder.py` | **how much flow does a fan unit buy, and can the 64 → 60 step account for the −2.9 degC residual at 170 s?** Phase A, roasts 58 (empty) and 59 (345 g loaded): the duty model `HT = A(fan−f0)(Inlet−amb)+c` fitted to the rung tables, **`f(64→60) = 0.18`**, the blower saturating above fan 64, the bed's 9.3 % flow restriction, the empty/loaded standing-duty lines out to BT 190, and the loaded fan-step transients. **stdlib only**; reads `~/Documents/artisan` |
| `beans.py` | **what temperature each coffee cracks at**, derived from the logs' `plus_coffee` ids rather than recorded by hand. Prints the `--fcs` / `--ror-at-fcs` arguments for `make_background.py`. Groups by hr_id (not the label), converts Fahrenheit logs, and filters on `roastertype` — the log directory holds ~530 files from two other roasters |
| `../make_background.py` | **authors a whole background**: the dip, then a RoR specification integrated to BT — smooth by construction, marks fitted exactly, no Designer curve and no blend, **less a drying term over BT 100-140** sized on the charge's water mass and calibrated on roast 62. `--decline linear` shows why the decline has to be exponential; `--no-drying` authors the pre-2026-09-13 curve |
| `../make_charge_background.py` | the older **merge**: splices that dip into an existing Designer curve and smoothsteps back onto it. Superseded by `make_background.py` — the blend leaves a bulge and then a cliff in RoR that no window removes |
| `plant_roast46.json` | the plant card `tools/merge_inlet_base.py` reads: `a`, `theta` and the loss cubic, with provenance |
| `plant_roast48.json` | roast 48's plant, **not** an authoring source (`supersedes_plant_roast46: false`); its settled content is `kf` |
| `ff_roast47.json` | the `feedforward()` card: the product-form coefficients, the affine fallback and the fitted box |
| `ff_roast48_loaded.json` | the loaded check: transfer error against the flashed map, per-setpoint fan slopes, and the pooled 47+48 refit |
| `charge_thermal.json` | the charge-thermal test's card, and it is mostly a list of what is *not* pinned down. Read `not_identified` before using any number in it |

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy   # .venv/ is gitignored
.venv/bin/python tools/analysis/roast46_refit.py
.venv/bin/python tools/analysis/roast46_refit.py --emit-plant   # refresh plant_roast46.json
.venv/bin/python tools/analysis/roast48_plant.py                # the designed-excitation refit
.venv/bin/python tools/analysis/deadtime_vs_lag.py              # ~2 min; --no-bootstrap is faster
```

`--emit-plant` is the seam between this directory and the authoring tools: it
writes the three plant numbers and the loss cubic into `plant_roast46.json`, and
`tools/merge_inlet_base.py` (stdlib only) reads that to build the step-9
feed-forward schedule. After the characterisation roasts (runbook steps 3-5),
re-run `--emit-plant` and re-run the merge; nothing else changes.

Roast logs live outside the repository (`~/Documents/artisan/`, `~/Downloads/`);
the paths are at the top of `roast46_refit.py`.

```bash
.venv/bin/python tools/analysis/charge_thermal.py --no-bootstrap --no-profile
.venv/bin/python tools/make_background.py --mass 400 --greens-temp -12
.venv/bin/python tools/analysis/charge_dip.py --ramp --scale
.venv/bin/python tools/analysis/charge_dip.py --fusion --sweep
python3 tools/analysis/roast47_ff.py --emit-card    # no venv: stdlib only
python3 tools/analysis/roast48_ff.py --emit-card    # reads roast 47 too, for the pooled fit
python3 tools/analysis/charge_state.py              # run this after every roast
```

`charge_state.py` is the one to run habitually: it is the only read the project
has on the charge state, and it stops being an inference the moment `greens_temp`
is filled in.

Twelve traps the code encodes so they cannot be repeated:

- **`timeindex[0] == -1` means CHARGE is unset, and `-1` is a legal Python
  index.** `timex[-1]` is the *last* sample, so a recording with no CHARGE mark
  (the charge-thermal test) silently re-bases onto a negative clock and every window lands
  somewhere else. `load_profile` tests `>= 0` and sets `has_charge`.
- **A proxy constant is not a physical fraction.** `charge_state.py`'s
  `4k = 0.409` is the drop measured at `+theta`; the *asymptotic* mixing
  fraction is 0.71, because at 13.5 s the mix is incomplete and the plant is
  already pushing back. Reading one as the other under-predicts every charge
  drop by 7-10 degC. `charge_dip.py` fits `phi` rather than reading `k`.
- **A parameter fitted against an assumed input is on that assumption's scale,
  and handing it a measured input is a bug.** `charge_dip.py`'s `phi` was
  fitted on roasts whose charge temperature was *assumed* at -18 degC, then
  evaluated by `make_charge_background.py` at the operator's *entered* -12 --
  and 12 degC of charge temperature is worth 0.07 of `phi`, so the generated
  dip came out 6.7 degC shallow and roast 54 fell through its own background.
  Both scales fit the data equally well (`--scale`); only one matches the
  number the tool is handed. Fit and evaluate on one scale, and say in the
  card which scale that is.
- **A missing ramp does not cost you the first two seconds, it costs you the
  phase.** `charge_dip.py`'s mix had no pour ramp, so the fit bought the dip's
  depth by stretching `tau_mix` to 12-15 s and then turned 6-7 s late. Adding
  `w_c` (a uniform pour convolved with the exponential, normalised so the heat
  is conserved) drops `tau_mix` to 10.8 and halves the residual. The two trade
  at -0.77: read the band, not the fourth decimal.
- **Mixing is a finite quantity of heat, not a setpoint.** Written the obvious
  way -- `dBT/dt = -(BT - BT_mix)/tau` -- the charge becomes a permanent
  attractor that fights the heater for the whole roast, and the model flatlines
  40 degC below a roast that has already recovered. As a decaying *rate* it
  integrates to the right total and then stops.

Seven more:

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
- **`theta` in a first-order-plus-deadtime fit is *total apparent lag*, not
  transport delay.**  The two are only separable by a **step**: below the corner
  where they part company `exp(-theta s)` and `1/(1+theta s)` are the same
  function, so a fit to a smooth ramp or a closed-loop recovery will happily call
  a lag a delay.  `plant_roast46.json`'s 13.5 s is a sum; roast 48's steps put the
  real transport delay at 0-2 s (`deadtime_vs_lag.py`).  The sum is what the loop
  and the base schedule actually depend on, which is why nothing had to change --
  but do not quote `theta` as a transport time, and do not mix an `a` fitted under
  one structure with a `theta`, `tau2` or loss curve fitted under the other.
- **An F-test on these residuals is meaningless and `plantfit.neff` says why.**
  Consecutive BT residuals correlate at rho > 0.99, so a 400-sample window carries
  5-9 independent samples.  Model comparison here has to rest on identifiability,
  stationarity and a bootstrap, not on a residual ratio.
- **A plant card is not automatically the best one available.** Roast 48's
  excitation is designed and roast 46's is accidental, yet `plant_roast46.json`
  is still what `merge_inlet_base.py` reads: roast 48's `a` is not stationary
  across its own sub-windows (its `theta` spread turned out to be the structural
  artefact above), and the one closed-loop behaviour on record — roast 45's 177 s
  ring at Ki 0.10 — is predicted by roast 46's card (173-194 s) and not by roast
  48's (143-152 s). Check a fit against a *measured closed-loop* response before
  letting it move any tuning, and compare against the least-damped closed-loop
  mode rather than the crossover period; they are different quantities.
