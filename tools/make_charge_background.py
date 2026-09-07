#!/usr/bin/env python3
"""Rebuild a background's charge dip from (mass, greens temperature).

`profile_003`'s dip puts the turning point at **67.4 degC at 37 s**.  Roasts 50
and 51 turned at **21-22 s**, from charges 37 degC apart, and both then ran
**+17 degC above the background at 50 s** -- within 1.5 degC of *each other*, so
the hump is the background's shape and not the beans.  The loop spends the first
twenty seconds chasing a target still falling while the bed has already turned,
and since nothing the heater does reaches BT before ~13.5 s its correction lands
at 18-28 s: too late to help, big enough to overshoot.  Roast 51 railed SV to its
300 ceiling for 9 s at 100% heat and then sat on the 140 floor for 22 s.

**The division of labour.**  The dip is physics -- mass, charge temperature and
the machine decide it, and no Designer work changes what the bed does.  The ramp
is the roast *design* and stays the operator's.  So this tool **merges**: it
rewrites `temp2` from CHARGE to the join and leaves everything past it alone, so
`timeindex`, DRY END, FCs and DROP are all preserved exactly.

    dip:    charge_dip.dip(mass, greens_temp), inlet held at its pre-charge value
    blend:  smoothstep from the computed dip onto the source curve
    ramp:   the source background, untouched

**Why the inlet is held rather than predicted.**  Using a measured roast's inlet
would be circular: that trace is the loop reacting to the very background being
replaced, so baking it in would preserve the overshoot rather than remove it.
Holding the pre-charge inlet answers the self-consistent question -- *what does
BT do if the loop leaves the setpoint where the preheat put it?* -- which is
exactly the behaviour a correct background should elicit.

**The acceptance test is the first 18 seconds, and only those.**  `--check`
scores the generated curve against roasts 50 and 51 over `0..18 s` -- the window
in which nothing the heater does has arrived yet, so the measurement is
loop-independent and a fair target.  Scoring the *whole* dip against those roasts
is not fair and is actively misleading: roast 51's trace is the loop railing
against the very background being replaced, so matching it would mean
reproducing the overshoot.  Past 18 s `--check` reports the RoR the new curve
asks for against what the machine actually delivered, which is the other thing
that matters -- a background that demands more than the machine has will saturate
it just as surely as one that is 17 degC low.

**Expect the turning point to land 5-8 s later than the measured roasts**, at
27-29 s against 21-22.  That is correct, not residual error: those roasts turned
early *because* the loop kicked.  With a background it does not have to fight,
the inlet stays where the preheat put it and the bed turns later.  The
construction is self-consistent at 27-29 s; it is `profile_003`'s 37 s that is
wrong.

    python3 tools/make_charge_background.py --mass 400 --greens-temp 5
    python3 tools/make_charge_background.py --mass 400 --greens-temp -12 --check
"""

from __future__ import annotations

import argparse
import ast
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analysis'))

import charge_dip as cd                                    # noqa: E402
from roastdata import load_profile                         # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(REPO, 'artisan/profile_003.alog')
HOME = os.path.expanduser('~')
ALOG = os.path.join(HOME, 'Documents/artisan/airRoaster_%s.alog')

# The two roasts whose charge temperature is measured rather than inferred.
# They are what `--check` scores against; nothing here is fitted to them.
REFERENCES = {'50': 25.0, '51': -12.0}

# Pre-charge inlet at the fan-58 preheat equilibrium (dashboard log 2026-09-07:
# BT 130.2 / inlet 140.4 / Temp_Drive 10.25).  Overridable, because it is the one
# machine number in the construction.
INLET_PRECHARGE = 140.4


def smoothstep(x):
    """C1 at both ends, so the blend adds no kink for the loop to chase."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def build(source_bt, source_t, mass, greens_temp, plant, phi400, tau_mix,
          t1, t2, inlet_pre=INLET_PRECHARGE, c_b=1.7, h_fus=0.0, charge_bt=None):
    """Return the rewritten BT curve on ``source_t`` (seconds from CHARGE)."""
    C_ch = cd.C_chamber_from_phi(phi400, c_b)
    bt_charge = (float(np.interp(0.0, source_t, source_bt))
                 if charge_bt is None else float(charge_bt))

    grid = np.arange(0.0, max(t2 + 1.0, 1.0), 0.5)
    model = cd.dip(grid, bt_charge, greens_temp, mass,
                   lambda _t: inlet_pre, plant,
                   phi=cd.phi_of_mass(mass, c_b, C_ch), phi_ref=phi400,
                   c_b=c_b, tau_mix=tau_mix, h_fus=h_fus)

    out = np.array(source_bt, dtype=float)
    m = (source_t >= 0.0) & (source_t <= t2)
    tt = source_t[m]
    mod = np.interp(tt, grid, model)
    w = smoothstep((tt - t1) / (t2 - t1))
    out[m] = (1.0 - w) * mod + w * out[m]
    return out, grid, model


def turning_point(t, bt, t_max=200.0):
    m = t <= t_max
    i = int(np.argmin(bt[m]))
    return float(bt[m][i]), float(t[m][i])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mass', type=float, required=True, help='charge mass, g')
    ap.add_argument('--greens-temp', type=float, required=True, help='degC')
    ap.add_argument('--source', default=SOURCE)
    ap.add_argument('--out', default=None,
                    help='default: artisan/profile_<mass>g_<temp>C.alog')
    ap.add_argument('--t1', type=float, default=30.0,
                    help='pure computed dip up to here (s)')
    ap.add_argument('--t2', type=float, default=150.0,
                    help='fully back on the source curve by here (s)')
    ap.add_argument('--inlet-precharge', type=float, default=INLET_PRECHARGE)
    ap.add_argument('--charge-bt', type=float, default=None,
                    help='BT at CHARGE (default: the source background\'s). The '
                         'fan-58 preheat settles at 130.2; profile_003 says 128.0, '
                         'and roasts 50/51 charged at 129.7 and 131.0.')
    ap.add_argument('--h-fus', type=float, default=0.0)
    ap.add_argument('--check', action='store_true',
                    help='score against roasts 50 and 51')
    args = ap.parse_args()

    plant = cd.load_plant()
    phi400, tau_mix, cal_rms = cd.calibrate(plant, 1.7, args.h_fus)

    src = load_profile(args.source)
    new_bt, grid, model = build(src.bt, src.t, args.mass, args.greens_temp,
                                plant, phi400, tau_mix, args.t1, args.t2,
                                args.inlet_precharge, h_fus=args.h_fus,
                                charge_bt=args.charge_bt)

    print(f"== {os.path.basename(args.source)} -> {args.mass:.0f} g at "
          f"{args.greens_temp:+.1f} degC ==")
    print(f"   phi(400 g) {phi400:.4f}, tau_mix {tau_mix:.2f} s "
          f"(fitted to roasts 43/44/46, rms {cal_rms:.2f} degC); "
          f"inlet held at {args.inlet_precharge:.1f}")
    o_bt, o_t = turning_point(src.t, src.bt)
    n_bt, n_t = turning_point(src.t, new_bt)
    print(f"   turning point {o_bt:.1f} degC at {o_t:.0f} s "
          f"->  {n_bt:.1f} degC at {n_t:.0f} s")
    print(f"   blend {args.t1:.0f}-{args.t2:.0f} s; nothing past {args.t2:.0f} s is "
          f"touched, so DRYe/FCs/DROP are unchanged")
    print("     t     source      new     delta")
    for t in (0, 10, 20, 30, 45, 60, 90, 120, 150, 180):
        a = float(np.interp(t, src.t, src.bt)); b = float(np.interp(t, src.t, new_bt))
        print(f"   {t:4d}   {a:7.1f}  {b:7.1f}   {b - a:+7.1f}")

    if args.check:
        print("\n   == acceptance: the loop-independent window, 0-18 s ==")
        print("   Nothing the heater does reaches BT before ~13.5 s, so only this")
        print("   window is a fair target. Scoring the whole dip against these two")
        print("   would reward reproducing roast 51's own overshoot.")
        for rid, tb in REFERENCES.items():
            p = load_profile(ALOG % rid)
            gen, _, _ = build(src.bt, src.t, 400.0, tb, plant, phi400, tau_mix,
                              args.t1, args.t2, args.inlet_precharge,
                              h_fus=args.h_fus,
                              charge_bt=float(np.interp(0.0, p.t, p.bt)))
            tt = np.arange(0.0, 150.1, 0.5)
            meas = np.interp(tt, p.t, p.bt)
            g = np.interp(tt, src.t, gen)
            o = np.interp(tt, src.t, src.bt)
            w = tt <= 18.0
            gi = int(np.argmin(g[tt <= 120])); mi = int(np.argmin(meas[tt <= 120]))
            print(f"   roast {rid} ({tb:+.1f} degC): worst 0-18 s  source "
                  f"{np.max(np.abs(o - meas)[w]):5.1f}  ->  new "
                  f"{np.max(np.abs(g - meas)[w]):5.1f} degC")
            print(f"      TP  measured {meas[mi]:5.1f} at {tt[mi]:4.0f} s | "
                  f"source 67.4 at 37 s | new {g[gi]:5.1f} at {tt[gi]:4.0f} s")
            print(f"      peak RoR asked {np.diff(g).max() / 0.5 * 60:5.0f} degC/min, "
                  f"machine delivered {np.diff(meas).max() / 0.5 * 60:5.0f}")

    out = args.out or os.path.join(
        REPO, 'artisan',
        f"profile_{args.mass:.0f}g_{args.greens_temp:+.0f}C.alog".replace('+', 'p').replace('-', 'm'))
    with open(args.source) as fh:
        raw = ast.literal_eval(fh.read())
    raw['temp2'] = [float(x) for x in new_bt]
    raw['roastingnotes'] = (
        f"Charge dip rebuilt by tools/make_charge_background.py from "
        f"{os.path.basename(args.source)}: mass {args.mass:.0f} g, greens_temp "
        f"{args.greens_temp:+.1f} degC, blend {args.t1:.0f}-{args.t2:.0f} s, "
        f"inlet held {args.inlet_precharge:.1f}. Ramp and all marks are the "
        f"source's, untouched.")
    with open(out, 'w') as fh:
        fh.write(repr(raw))
    print(f"\nwrote {os.path.relpath(out, REPO)}")


if __name__ == '__main__':
    main()
