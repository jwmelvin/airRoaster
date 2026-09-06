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

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy
.venv/bin/python tools/analysis/roast46_refit.py
```

Roast logs live outside the repository (`~/Documents/artisan/`, `~/Downloads/`);
the paths are at the top of `roast46_refit.py`.

Two traps the code encodes so they cannot be repeated:

- The CHARGE origin is `timex[timeindex[0]]`, and `timeindex[0] == 0` is a
  **valid** index, not "unset" (`profile_003` relies on it).
- A plant delay cannot be identified while the disturbance is a free function of
  time. `fit_integral` restricts it to a low-order polynomial; `fit_disturbance`
  relaxes that only *after* the plant parameters are fixed, and exists purely to
  give the simulator something to run against.
