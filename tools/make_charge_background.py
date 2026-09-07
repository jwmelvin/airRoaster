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
            -- and `--greens-temp` MUST be read the way the calibration roasts'
            greens temperatures were, because `phi` is depth per degC on that
            scale and nothing has measured a bean's core (charge_dip.py --scale)
    blend:  smoothstep from the computed dip onto the source curve
    ramp:   the source background, untouched

**Why the inlet is held rather than predicted.**  Using a measured roast's inlet
would be circular: that trace is the loop reacting to the very background being
replaced, so baking it in would preserve the overshoot rather than remove it.
Holding the pre-charge inlet answers the self-consistent question -- *what does
BT do if the loop leaves the setpoint where the preheat put it?* -- which is
exactly the behaviour a correct background should elicit.

**The acceptance test is each roast's own loop-free window, and only that.**
`--check` scores the generated curve against the roasts in `REFERENCES` over
`0..free_window`, which `charge_dip.free_window` ends `theta` seconds after that
roast's inlet first left the preheat -- 15-16 s for roasts 50 and 51, but **30 s
for roast 54**, whose charge gate held.  Past it the measurement is the loop
railing against the very background being replaced, so matching it would mean
reproducing the overshoot.  `--check` also reports the RoR the new curve asks
for against what the machine actually delivered, which is the other thing that
matters -- a background that demands more than the machine has will saturate it
just as surely as one that is 17 degC low.

**The turning point still lands ~6 s late, and that IS residual error.**  This
file used to claim the opposite -- that 27-29 s against the roasts' 21-22 s was
correct, because those roasts turned early only *because* the loop kicked.
**Roast 54 disproved it.**  Its gate held, `dekick_tp.py` puts the loop's whole
contribution to its turning point at **0.3 degC**, and it turned at **55.6 degC
at 23.0 s** -- a free dip, measured.  The generated curve turns at 55.0 at 29 s.
The depth is right to under a degree; the phase is not, and no value of `w_c`
fixes it (`charge_dip.py --ramp`): a single exponential mix cannot be both this
deep and turn this early against this plant card.

**What the phase error costs is small and its sign is benign.**  Because the
minimum is flat, the worst gap to roast 54 anywhere in its 30 s free window is
**2.6 degC** -- against `profile_003`'s 22.6 -- and the residual is a phase
signature: the background runs ~2 degC *above* the bed through the descent
(13-18 s) and ~2.5 degC *below* it by 30 s.  At the PID-ON alarm the loop
therefore sees ~2 degC of error where roast 54's background handed it 8.5, and
by 24 s the sign has flipped to the direction that makes the loop back off
rather than kick.  Do not read the remaining gap as licence to fit the turning
point -- read it as the one defect the model still has.

    python3 tools/make_charge_background.py --mass 400 --greens-temp 5
    python3 tools/make_charge_background.py --mass 400 --greens-temp -12 --check

**`--check` writes the background file** -- it reports on the curve it has just
generated, it does not inspect an existing one.  Pass `--no-write` to score
without touching the disk, or run it before the roast rather than after.
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

# The roasts whose charge temperature the operator entered rather than the
# analysis inferred.  `--check` scores against these.  Roast 54 is the one that
# matters: the charge gate held, `dekick_tp.py` puts the loop's contribution to
# its turning point at 0.3 degC, and it is therefore the only **free dip** on
# record -- the only roast whose turn is a measurement rather than an artefact.
# 50 and 51 are in the calibration, so they check the arithmetic, not the model.
REFERENCES = {'50': 25.0, '51': -12.0, '54': -12.0}

# Pre-charge inlet at the fan-58 preheat equilibrium (dashboard log 2026-09-07:
# BT 130.2 / inlet 140.4 / Temp_Drive 10.25).  Overridable, because it is the one
# machine number in the construction.
INLET_PRECHARGE = 140.4


def smoothstep(x):
    """C1 at both ends, so the blend adds no kink for the loop to chase."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def build(source_bt, source_t, mass, greens_temp, plant, phi400, tau_mix,
          t1, t2, inlet_pre=INLET_PRECHARGE, c_b=1.7, h_fus=0.0, charge_bt=None,
          w_c=cd.W_C):
    """Return the rewritten BT curve on ``source_t`` (seconds from CHARGE)."""
    C_ch = cd.C_chamber_from_phi(phi400, c_b)
    bt_charge = (float(np.interp(0.0, source_t, source_bt))
                 if charge_bt is None else float(charge_bt))

    grid = np.arange(0.0, max(t2 + 1.0, 1.0), 0.5)
    model = cd.dip(grid, bt_charge, greens_temp, mass,
                   lambda _t: inlet_pre, plant,
                   phi=cd.phi_of_mass(mass, c_b, C_ch), phi_ref=phi400,
                   c_b=c_b, tau_mix=tau_mix, h_fus=h_fus, w_c=w_c)

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
                    help='score against the roasts in REFERENCES')
    ap.add_argument('--no-write', action='store_true',
                    help='report only. --check ALONE STILL WRITES the background '
                         'file -- it is a report on the file it just generated, '
                         'not a read-only inspection of an existing one. Pass '
                         'this to score without touching anything on disk.')
    args = ap.parse_args()

    plant = cd.load_plant()
    phi400, tau_mix, w_c, cal_rms = cd.calibrate(plant, 1.7, args.h_fus)

    src = load_profile(args.source)
    new_bt, grid, model = build(src.bt, src.t, args.mass, args.greens_temp,
                                plant, phi400, tau_mix, args.t1, args.t2,
                                args.inlet_precharge, h_fus=args.h_fus,
                                charge_bt=args.charge_bt, w_c=w_c)

    print(f"== {os.path.basename(args.source)} -> {args.mass:.0f} g at "
          f"{args.greens_temp:+.1f} degC ==")
    print(f"   phi(400 g) {phi400:.4f}, tau_mix {tau_mix:.2f} s, w_c {w_c:.2f} s "
          f"(fitted jointly to roasts\n   {'/'.join(cd.CAL_RIDS)} over their "
          f"loop-free windows at the ENTERED greens temperatures, rms "
          f"{cal_rms:.2f} degC); inlet held at {args.inlet_precharge:.1f}")
    print(f"   --greens-temp must be read the SAME WAY those were: phi is depth "
          f"per degC on\n   that scale, so a thermometer offset of d degC moves "
          f"the dip by {phi400:.2f}*d. See\n   charge_dip.py --scale.")
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
        print("\n   == acceptance: each roast's own loop-independent window ==")
        print("   The window ends theta seconds after that roast's inlet first left")
        print("   the preheat, which is `charge_dip.free_window` and not a fixed")
        print("   18 s: 15-16 s for roasts 50 and 51, but 30 s for roast 54, whose")
        print("   gate held. Scoring past it would reward reproducing the loop's")
        print("   own overshoot -- the circularity this tool exists to remove.")
        for rid, tb in REFERENCES.items():
            p = load_profile(ALOG % rid)
            gen, _, _ = build(src.bt, src.t, 400.0, tb, plant, phi400, tau_mix,
                              args.t1, args.t2, args.inlet_precharge,
                              h_fus=args.h_fus, w_c=w_c,
                              charge_bt=float(np.interp(0.0, p.t, p.bt)))
            ti, inl = p.extras['Inlet']
            pre = float(np.mean(inl[(ti >= -30) & (ti < 0)]))
            t_end = cd.free_window(p, pre, plant['theta'])
            tt = np.arange(0.0, 150.1, 0.5)
            meas = np.interp(tt, p.t, p.bt)
            g = np.interp(tt, src.t, gen)
            o = np.interp(tt, src.t, src.bt)
            w = tt <= t_end
            gi = int(np.argmin(g[tt <= 120])); mi = int(np.argmin(meas[tt <= 120]))
            print(f"   roast {rid} ({tb:+.1f} degC): worst 0-{t_end:.0f} s  source "
                  f"{np.max(np.abs(o - meas)[w]):5.1f}  ->  new "
                  f"{np.max(np.abs(g - meas)[w]):5.1f} degC")
            print(f"      TP  measured {meas[mi]:5.1f} at {tt[mi]:4.0f} s | "
                  f"source 67.4 at 37 s | new {g[gi]:5.1f} at {tt[gi]:4.0f} s")
            print(f"      peak RoR asked {np.diff(g).max() / 0.5 * 60:5.0f} degC/min, "
                  f"machine delivered {np.diff(meas).max() / 0.5 * 60:5.0f}")

    if args.no_write:
        print("\n--no-write: nothing written")
        return

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
