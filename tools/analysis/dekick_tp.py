"""How much of a measured turning point is the loop's own kick?

`charge_dip.py` builds the dip with **the inlet held at its pre-charge value**,
and until the charge gate works no roast has satisfied that: the outer loop
railed `T_inlet` to 240-300 through every dip in the series.  So the measured
turning point is not a measurement of the free dip, and refitting the model
against it would reward reproducing the loop's own overshoot -- the circularity
`make_charge_background.py --check` already guards against by scoring only the
0-18 s window.

This backs the kick out to first order.  With the roast-46 plant card,

    dBT/dt = a * (inlet(t - theta) - BT) + <the dip's own mixing term>

so the *excess* the loop added over holding the inlet at `INLET0` is

    BT_excess(t) = a * integral_0^t (inlet(s - theta) - INLET0) ds

with `BT` inside the bracket dropped: over the dip the loop's excess is 80-160
degC of inlet against a 1-3 degC change in the bed it causes, so the neglected
feedback is a second-order correction on a first-order estimate.

**It is an estimate, not a measurement.**  `theta` carries a band of 13 +5/-1 s
(state-history-cascade.md § Deadtime versus lag) and the separation of disturbance from
plant is only as good as the card.  The point of it is to say whether the model's
turning point is wrong or merely unmeasured -- not to supply a new fit.  The
measurement is a roast with the gate actually armed.

    .venv/bin/python tools/analysis/dekick_tp.py 50 51 53
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from roastdata import load_profile                              # noqa: E402

ROASTS = pathlib.Path.home() / "Documents" / "artisan"
HERE = pathlib.Path(__file__).resolve().parent
INLET0 = 140.4      # what make_charge_background.py holds the inlet at
WINDOW = 70.0       # s after CHARGE; the dip is long over by here


def turning_point(t, bt):
    i = int(np.argmin(bt))
    return float(bt[i]), float(t[i])


def dekick(profile, a, theta, inlet0=INLET0, window=WINDOW, dt=0.25):
    """Return (t, measured BT, BT with the inlet excess removed)."""
    t = np.arange(0.0, window + dt, dt)
    bt = profile.bt_at(t)
    inlet = profile.extra_at("Inlet", t - theta)
    inlet = np.where(np.isnan(inlet), inlet0, inlet)   # before the log starts
    excess = np.cumsum(a * (inlet - inlet0)) * dt
    return t, bt, bt - excess


def main():
    card = json.loads((HERE / "plant_roast46.json").read_text())
    a, theta = card["a"], card["theta"]
    numbers = [int(x) for x in sys.argv[1:]] or [50, 51, 53]
    print(f"plant card: a = {a:.5f} /s, theta = {theta} s;  inlet held at {INLET0}\n")
    for n in numbers:
        p = load_profile(str(ROASTS / f"airRoaster_{n}.alog"))
        t, bt, bt_free = dekick(p, a, theta)
        v0, t0 = turning_point(t, bt)
        v1, t1 = turning_point(t, bt_free)
        peak = float(np.nanmax(p.extra_at("Inlet", np.arange(0, 40, 0.5))))
        added = float(bt[np.argmin(np.abs(t - t0))] - bt_free[np.argmin(np.abs(t - t0))])
        print(f"roast {n}:  peak inlet over 0-40 s {peak:5.0f}")
        print(f"   measured TP    {v0:5.1f} degC at {t0:4.1f} s")
        print(f"   de-kicked TP   {v1:5.1f} degC at {t1:4.1f} s "
              f"(the kick had added {added:.1f} degC by the measured TP)")


if __name__ == "__main__":
    main()
