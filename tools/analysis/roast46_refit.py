#!/usr/bin/env python3
"""Reproduce the roast-46 plant refit, the PID validation and the tuning sweeps.

Needs numpy and scipy.  The roast logs live outside the repository:

    ~/Documents/artisan/airRoaster_46.alog
    ~/Downloads/airRoaster_data_2026-09-05-23-57-34.csv   (dashboard CSV)
    artisan/profile_003.alog                              (background)

Run with ``--help`` to see the sections; with no arguments it runs them all.
Numbers quoted in state-plan.md § Roast 46 refit come from here.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plantfit as pf                                        # noqa: E402
import margins as mg                                         # noqa: E402
from roastdata import load_profile, load_dashlog, align_dashlog   # noqa: E402
from artisan_pid import Background                           # noqa: E402
from sim import LoopConfig, replay_pid, simulate, delayed_inlet_plant  # noqa: E402

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, "Documents/artisan/airRoaster_%d.alog")
CSV = os.path.join(HOME, "Downloads/airRoaster_data_2026-09-05-23-57-34.csv")
PROFILE_003 = os.path.join(REPO, "artisan/profile_003.alog")

# autoCHARGE backdates timeindex[0] by BTbreak's 'tight' = 3 samples
# (canvas.py:5121-5126, main.py BTbreak), so Follow-Background mode starts 3 s
# after the CHARGE the profile records.  Without this the SV replay is +21 degC
# out for the whole roast; with it, 0.73 degC rms.
CHARGE_DETECT = 3.0
FIT_WINDOW = (45.0, None)      # None = DROP
FIT_ORDER = 4


def _bg_offset(roast, background):
    """Where the background's CHARGE lands on the roast clock.

    ``timealign`` shifts the background by a whole number of seconds
    (canvas.py:5931-5946), so a sub-second residual is left over.
    """
    diff = (roast.raw["timex"][roast.raw["timeindex"][0]]
            - background.raw["timex"][background.raw["timeindex"][0]])
    return -(diff - round(diff))


def load():
    p46 = load_profile(ALOG % 46)
    p03 = load_profile(PROFILE_003)
    dash = load_dashlog(CSV)
    charge, rms = align_dashlog(dash, p46)
    return p46, p03, dash, charge, rms


def section_fit(p46):
    print("== 1. plant fit ==")
    te, ye = p46.extras["Inlet"]
    thetas = np.arange(0, 36.01, 0.25)
    lo, hi = FIT_WINDOW[0], p46.marks["DROP"]
    t = np.arange(lo, hi + 1e-9, 1.0)
    bt = p46.bt_at(t)
    f = pf.fit_integral(t, bt, te, ye, order=FIT_ORDER, thetas=thetas)
    scan = dict((round(x, 2), y) for x, y in f.scan)
    print(f"  primary   {f}")
    print(f"  ridge depth: resid(theta=0)/resid(min) = {scan[0.0] / f.resid_rms:.1f}")
    _, samp = pf.block_bootstrap(t, bt, te, ye, order=FIT_ORDER,
                                 thetas=np.arange(0, 36.01, 0.5),
                                 n_boot=200, block=60, seed=7)
    q = lambda x: np.percentile(x, [2.5, 50, 97.5])   # noqa: E731
    print(f"  bootstrap theta 95% {q(samp[:, 0])[0]:.1f}..{q(samp[:, 0])[2]:.1f} s, "
          f"a 95% {q(samp[:, 1])[0]:.5f}..{q(samp[:, 1])[2]:.5f}")
    print("  window x order:")
    for wlo, whi in [(25, hi), (35, hi), (45, hi), (60, hi), (90, hi)]:
        cells = []
        for order in (3, 4, 5, 6):
            tt = np.arange(wlo, whi + 1e-9, 1.0)
            g = pf.fit_integral(tt, p46.bt_at(tt), te, ye, order=order, thetas=thetas)
            cells.append(f"th{g.theta:5.1f} a{g.a:.5f} r{g.resid_rms:.3f}")
        print(f"    ({wlo:3d},{whi:.0f}) " + " | ".join(cells))
    return f


def section_pid(p46, p03, dash):
    print("\n== 2. PID replay: measured BT -> commanded SV ==")
    bg = Background(p03.t, p03.bt, p03.marks["DROP"])
    off = _bg_offset(p46, p03)
    t = dash.t[(dash.t >= 0) & (dash.t <= p46.marks["DROP"])]
    sv, bt = dash.at("SV", t), dash.at("BT", t)
    cfg = LoopConfig(svLookahead=3, charge_detect_delay=CHARGE_DETECT)
    r = replay_pid(bg, t, bt, cfg, iterm0=8.0, bg_offset=off,
                   sv0=bg.smoothed_bt_at(0.0))
    for lo, hi in [(0, 30), (30, 120), (120, 240), (240, 430), (30, 430)]:
        m = (t >= lo) & (t <= hi) & ~np.isnan(r["sv"])
        e = r["sv"][m] - sv[m]
        print(f"   {lo:3d}-{hi:3d}s  mean {e.mean():+6.2f}  rms {np.sqrt((e ** 2).mean()):5.2f}"
              f"  max|e| {np.abs(e).max():6.2f}")
    m = (t >= 210) & (t <= 420)
    slope = float(np.polyfit(t[m], r["I"][m], 1)[0])
    print(f"   Iterm 210-420 s climbs at {slope:.4f} duty/s  ->  e_ss = (dI/dt)/Ki "
          f"= {slope / 0.07:.2f} degC")
    return bg, off


def section_closed_loop(p46, p03, bg, off, f):
    print("\n== 3. closed loop: plant + PID from CHARGE+2 ==")
    te, ye = p46.extras["Inlet"]
    t0 = 2.0
    tg = np.arange(t0, p46.marks["DROP"] + 1e-9, 1.0)
    slow, ol = pf.fit_disturbance(tg, p46.bt_at(tg), te, ye, f.a, f.theta,
                                  knot_spacing=8.0)
    print(f"   open-loop replay with the spline disturbance: {ol:.3f} degC")
    sl = lambda x: float(np.interp(x, tg, slow))   # noqa: E731
    cfg = LoopConfig(Ki=0.07, svLookahead=3, charge_detect_delay=CHARGE_DETECT)
    plant = delayed_inlet_plant(f.a, f.theta, sl, 0.25)
    r = simulate(bg, cfg, plant, t0, p46.marks["DROP"], float(p46.bt_at(t0)),
                 iterm0=8.0, bg_offset=off, inlet0=float(p46.extra_at("Inlet", t0)),
                 sv0=bg.smoothed_bt_at(t0 - 1 - off + 3))
    e = r["bt"] - p46.bt_at(r["t"])
    print(f"   BT closed-loop replay: mean {e.mean():+.3f}  rms "
          f"{np.sqrt((e ** 2).mean()):.3f}  max {np.abs(e).max():.2f} degC")
    for lo, hi in [(2, 30), (30, 60), (60, 120), (120, 240), (240, 430)]:
        m = (r["t"] >= lo) & (r["t"] <= hi)
        print(f"     {lo:3d}-{hi:3d}s  mean {e[m].mean():+6.2f}  rms "
              f"{np.sqrt((e[m] ** 2).mean()):5.2f}")


def section_margins(f):
    print("\n== 4. phase margin against the refitted plant (Kp 3.0) ==")
    print("   Ki    PM(deg)  crossover period (s)")
    for Ki in (0.05, 0.07, 0.09, 0.10, 0.12, 0.15):
        _, pm, T = mg.margins(f.a, f.theta, 3.0, Ki)
        print(f"   {Ki:.2f}  {pm:7.1f}  {T:8.0f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["fit", "pid", "loop", "margins"])
    args = ap.parse_args()

    p46, p03, dash, charge, rms = load()
    print(f"CSV aligned: CHARGE epoch {charge:.2f}, BT residual {rms:.3f} degC")
    f = section_fit(p46)
    if args.only == "fit":
        return
    bg, off = section_pid(p46, p03, dash)
    if args.only == "pid":
        return
    if args.only in (None, "loop"):
        section_closed_loop(p46, p03, bg, off, f)
    if args.only in (None, "margins"):
        section_margins(f)


if __name__ == "__main__":
    main()
