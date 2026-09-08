#!/usr/bin/env python3
"""Author a whole background: measured dip, then a smooth declining RoR.

`make_charge_background.py` **merges** a computed dip into an existing Designer
curve and smoothsteps back onto it.  That was the right move while the ramp was
the operator's and only the dip was wrong, and it has one defect that no choice
of blend window removes: **the blend leaves a bulge and then a cliff in RoR.**
`profile_400g_m12C_v2.alog` runs `38 -> 43 -> 41 -> 25 degC/min` across
60-150 s, because the merged curve sits below the source and has to climb back
onto it.  The bed is asked to accelerate and then abruptly stop accelerating,
in the window where the loop is still recovering from the charge.

This authors the curve outright instead, and the division of labour is the same
one `make_charge_background.py` states -- it is just drawn in the right place:

    0 .. TP        the dip.  Physics: mass, charge temperature and the machine
                   decide it (`charge_dip.dip`, inlet held at the preheat).
    TP .. DROP     the design.  A rate-of-rise curve that starts at zero at the
                   turning point, rises to a peak, and then declines smoothly
                   and monotonically to DROP.

**BT is the integral of the RoR spec, so the RoR is smooth by construction**
rather than being whatever differentiating a hand-drawn curve happens to give.
The Designer is not needed for any of this; nothing here reads it except the
`--template` used for the file's Artisan metadata.

**The declining segment wants to be exponential, and this is a real finding, not
a preference.**  Fitting each family to the three marks below:

    family      DRY END / FCs / DROP error      RoR at DROP
    linear      -0.0 / +1.9 / -1.9 degC          0.0  <- flat at DROP
    quadratic   +3.7 / +1.7 / -2.2 degC          0.0  <- flat at 360 s
    exponential -0.0 / +0.0 / -0.0 degC          8.7

A roast's RoR decline is convex -- fast early, long slow tail -- so a straight
line through it either runs hot in the middle or runs out of rate before DROP.
Asked to hit 3:12 / 6:39 / 7:05, a linear decline reaches **zero RoR exactly at
DROP** and still misses FCs by 2 degC.  `--decline linear` is kept because it is
worth being able to see that, but `exp` is the default.

    RoR(u) = (1 - exp(-u/tau_r)) * (R_inf + (R0 - R_inf) * exp(-u/tau_d))
    u = t - t_TP,  BT(t) = BT_TP + integral of RoR/60

``tau_r`` is the rise off the turning point; the bracket is the decline.  Three
free parameters against three marks, so the marks are hit rather than
approached.  The ``(1 - exp(-u/tau_r))`` factor is what makes the join smooth:
the dip arrives at the TP with RoR 0 by definition and the spec leaves it at
RoR 0, so BT is C1 there with no blend and no window to choose.

    .venv/bin/python tools/make_background.py --mass 400 --greens-temp -12
    .venv/bin/python tools/make_background.py --mass 400 --greens-temp -12 \\
        --decline linear --compare artisan/profile_400g_m12C_v2.alog
"""

from __future__ import annotations

import argparse
import ast
import os
import sys

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analysis'))

import charge_dip as cd                                    # noqa: E402
from roastdata import load_profile                         # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, 'artisan/profile_003.alog')

# Pre-charge inlet at the fan-58/60 preheat equilibrium (dashboard 2026-09-07:
# BT 130.2 / inlet 140.4 / Temp_Drive 10.25).
INLET_PRECHARGE = 140.4
# profile_003's marks, which roasts 50-54 were designed and scored against.
# NOTE the FCs temperature: 197.5 is at the BOTTOM of what this coffee actually
# cracks at (roasts 50-55: mean 198.8, median 198.4, range 197.3-201.2).  A
# background whose FC mark is 1.3 degC low arrives there ~9 s early at the
# ~8.3 degC/min the roasts run through FC, and the whole roast stretches past
# it -- roast 55's FCs landed at 408 s against the background's 399.  Prefer
# --development mode below, and set --fcs to the coffee's own FC temperature.
DEFAULT_MARKS = {'dry_end': (192.0, 149.6), 'fcs': (399.0, 197.5),
                 'drop': (425.0, 201.4)}
# Measured over roasts 50-55 (slope fitted over FCs +-15 s, and DROP - FCs).
FC_ROR_DEFAULT = 8.3          # degC/min through first crack
DEVELOPMENT_DEFAULT = 28.0    # s from FCs to DROP


def _mark(s):
    """``<seconds>:<BT>`` or ``m:ss:<BT>``."""
    parts = s.split(':')
    bt = float(parts[-1])
    t = (float(parts[0]) if len(parts) == 2
         else float(parts[0]) * 60.0 + float(parts[1]))
    return t, bt


def ror_spec(u, params, decline='exp'):
    """RoR in degC/min at ``u`` seconds past the turning point.

    Zero at ``u = 0`` in every family, which is what makes the join to the dip
    C1 without a blend: the dip reaches its minimum with RoR 0 by definition.
    """
    tau_r = params[0]
    rise = 1.0 - np.exp(-np.clip(u, 0.0, None) / tau_r)
    if decline == 'exp':
        R0, R_inf, tau_d = params[1], params[2], params[3]
        fall = R_inf + (R0 - R_inf) * np.exp(-np.clip(u, 0.0, None) / tau_d)
    elif decline == 'linear':
        fall = params[1] - params[2] * np.clip(u, 0.0, None)
    elif decline == 'quad':
        uu = np.clip(u, 0.0, None)
        fall = params[1] - params[2] * uu + params[3] * uu * uu
    else:
        raise ValueError(decline)
    return np.maximum(rise * fall, 0.0)


def build(t, dip_bt, i_tp, params, decline='exp'):
    """BT over ``t``: the dip up to its turning point, the spec after it."""
    u = t - t[i_tp]
    R = ror_spec(u, params, decline)
    R[:i_tp + 1] = 0.0
    y = np.array(dip_bt, dtype=float)
    dt = float(t[1] - t[0])
    y[i_tp:] = dip_bt[i_tp] + np.cumsum(np.r_[0.0, R[i_tp:-1]]) * dt / 60.0
    return y, R


def fit(t, dip_bt, i_tp, marks, decline='exp', ror_mark=None):
    """Fit the spec so the curve passes through the marks.

    ``marks`` are ``(t, BT)`` pairs.  ``ror_mark``, if given, is a
    ``(t, degC/min)`` pair used **instead of** a third BT mark -- this is
    `--development` mode, where DROP is placed a fixed time after FCs and its
    temperature is whatever the curve gives, rather than being pinned.  That is
    how the operator actually roasts: FCs is a *temperature* the coffee decides
    and DROP is a *time past it*.
    """
    # Multi-start: a single start converges to a local minimum on some charge
    # temperatures (found at -5 degC, which stopped 0.35 degC/min short on the
    # RoR mark while -12 hit machine zero).  Four starts and tight tolerances
    # take every charge temperature from -24 to +25 to a residual under 1e-13.
    starts, lo, hi = {
        'exp':    ([[25., 55., 8., 120.], [15., 70., 4., 150.],
                    [40., 45., 10., 90.], [10., 90., 2., 200.]],
                   [3., 10., 0., 20.], [120., 150., 40., 600.]),
        'linear': ([[25., 55., 0.11], [15., 70., 0.15], [40., 45., 0.08]],
                   [3., 10., 0.0], [120., 150., 1.0]),
        'quad':   ([[25., 55., 0.11, 1e-4], [15., 70., 0.15, 1e-4],
                    [40., 45., 0.08, -1e-4]],
                   [3., 10., 0.0, -1e-2], [120., 150., 1.0, 1e-2]),
    }[decline]

    def resid(p):
        y, R = build(t, dip_bt, i_tp, p, decline)
        out = [float(np.interp(tm, t, y)) - bm for tm, bm in marks]
        if ror_mark is not None:
            out.append(float(np.interp(ror_mark[0], t, R)) - ror_mark[1])
        return out

    best = None
    for x0 in starts:
        r = least_squares(resid, x0, bounds=(lo, hi),
                          xtol=1e-14, ftol=1e-14, gtol=1e-14)
        if best is None or np.max(np.abs(r.fun)) < np.max(np.abs(best.fun)):
            best = r
    return best.x, np.asarray(best.fun)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mass', type=float, default=400.0, help='charge mass, g')
    ap.add_argument('--greens-temp', type=float, required=True,
                    help='degC, READ THE SAME WAY the calibration roasts were '
                         '(charge_dip.py --scale)')
    ap.add_argument('--charge-bt', type=float, default=130.2)
    ap.add_argument('--inlet-precharge', type=float, default=INLET_PRECHARGE)
    ap.add_argument('--decline', choices=('exp', 'linear', 'quad'), default='exp')
    ap.add_argument('--dry-end', type=_mark, default=DEFAULT_MARKS['dry_end'])
    ap.add_argument('--fcs', type=_mark, default=DEFAULT_MARKS['fcs'])
    ap.add_argument('--drop', type=_mark, default=None,
                    help='<s>:<BT>. Pins DROP temperature. Mutually exclusive '
                         'with --development')
    ap.add_argument('--development', type=float, default=None,
                    help='seconds from FCs to DROP (roasts 50-55: 23-36, mean '
                         f'{DEVELOPMENT_DEFAULT:.0f}). DROP temperature then '
                         'follows from the curve instead of being pinned, which '
                         'is how the operator roasts. Implies --ror-at-fcs as '
                         'the third constraint')
    ap.add_argument('--ror-at-fcs', type=float, default=FC_ROR_DEFAULT,
                    help='degC/min through first crack, the third constraint in '
                         f'--development mode (roasts 50-55: 6.2-9.8, mean '
                         f'{FC_ROR_DEFAULT})')
    ap.add_argument('--template', default=TEMPLATE,
                    help="only for the file's Artisan metadata; no curve is read")
    ap.add_argument('--compare', default=None, help='an existing background to print beside')
    ap.add_argument('--h-fus', type=float, default=0.0)
    ap.add_argument('--out', default=None)
    ap.add_argument('--no-write', action='store_true')
    args = ap.parse_args()

    plant = cd.load_plant()
    c_b = 1.7
    phi400, tau_mix, w_c, cal_rms = cd.calibrate(plant, c_b, args.h_fus)
    C_ch = cd.C_chamber_from_phi(phi400, c_b)

    if args.drop and args.development:
        ap.error('--drop and --development are mutually exclusive')
    dev_mode = args.drop is None
    if dev_mode:
        if args.development is None:
            args.development = DEVELOPMENT_DEFAULT
        t_drop = args.fcs[0] + args.development
        marks = [args.dry_end, args.fcs]
        ror_mark = (args.fcs[0], args.ror_at_fcs)
    else:
        t_drop = args.drop[0]
        marks = [args.dry_end, args.fcs, args.drop]
        ror_mark = None
    t = np.arange(0.0, t_drop + 2.0, 1.0)
    dip_bt = cd.dip(t, args.charge_bt, args.greens_temp, args.mass,
                    lambda _t: args.inlet_precharge, plant,
                    phi=cd.phi_of_mass(args.mass, c_b, C_ch), phi_ref=phi400,
                    c_b=c_b, tau_mix=tau_mix, h_fus=args.h_fus, w_c=w_c)
    i_tp = int(np.argmin(dip_bt))

    print(f"== {args.mass:.0f} g at {args.greens_temp:+.1f} degC, "
          f"decline '{args.decline}' ==")
    print(f"   dip: phi(400 g) {phi400:.4f}, tau_mix {tau_mix:.2f} s, w_c {w_c:.2f} s "
          f"(rms {cal_rms:.2f} degC),\n        inlet held at "
          f"{args.inlet_precharge:.1f} -> TP {dip_bt[i_tp]:.1f} degC at "
          f"{t[i_tp]:.0f} s")
    print("   --greens-temp is on the OPERATOR'S scale, not a bean's core: a "
          f"thermometer offset of\n        d degC moves the dip by {phi400:.2f}*d "
          "(charge_dip.py --scale).")

    params, err = fit(t, dip_bt, i_tp, marks, args.decline, ror_mark)
    bt, R = build(t, dip_bt, i_tp, params, args.decline)

    names = ['DRY END', 'FCs', 'DROP']
    print("\n   mark      target            authored          error")
    for (tm, bm), n, e in zip(marks, names, err):
        print(f"   {n:<8s}  {tm:5.0f} s ({tm//60:.0f}:{tm%60:02.0f})  {bm:6.1f}   "
              f"{float(np.interp(tm, t, bt)):6.1f}   {e:+6.2f} degC")
    if dev_mode:
        print(f"   RoR@FCs   {args.fcs[0]:5.0f} s          "
              f"{args.ror_at_fcs:6.1f}   {float(np.interp(args.fcs[0], t, R)):6.1f}   "
              f"{err[-1]:+6.2f} degC/min")
        print(f"   DROP      {t_drop:5.0f} s "
              f"({t_drop//60:.0f}:{t_drop%60:02.0f})     ---   "
              f"{float(np.interp(t_drop, t, bt)):6.1f}      --   "
              f"<- {args.development:.0f} s past FCs, temperature NOT pinned")
    i_pk = int(np.argmax(R))
    rising = bool(np.all(np.diff(R[i_tp:i_pk + 1]) >= -1e-9))
    falling = bool(np.all(np.diff(R[i_pk:int(t_drop) + 1]) <= 1e-9))
    print(f"\n   RoR peaks at {R[i_pk]:.1f} degC/min at {t[i_pk]:.0f} s "
          f"(roast 54's machine delivered 72)")
    print(f"   monotone rising TP->peak: {rising};  monotone falling peak->DROP: "
          f"{falling};  RoR at DROP {float(np.interp(t_drop, t, R)):.1f}")
    if not falling:
        print("   *** RoR is NOT monotone after the peak -- the marks are not "
              "reachable by this\n       family; try --decline exp, or move a mark.")

    cols = [30, 60, 90, 120, 180, 240, 300, 360, 420]
    cols = [c for c in cols if c <= t_drop]
    print('\n   t     ' + ' '.join(f'{c:6d}' for c in cols))
    print('   BT    ' + ' '.join(f'{float(np.interp(c, t, bt)):6.1f}' for c in cols))
    print('   RoR   ' + ' '.join(f'{float(np.interp(c, t, R)):6.1f}' for c in cols))
    if args.compare:
        cp = load_profile(args.compare)
        y = np.interp(t, cp.t, cp.bt)
        r = np.gradient(y, t) * 60.0
        base = os.path.basename(args.compare)[:14]
        print(f'   -- {base}')
        print('   BT    ' + ' '.join(f'{float(np.interp(c, t, y)):6.1f}' for c in cols))
        print('   RoR   ' + ' '.join(f'{float(np.interp(c, t, r)):6.1f}' for c in cols))

    if args.no_write:
        print('\n--no-write: nothing written')
        return

    with open(args.template) as fh:
        raw = ast.literal_eval(fh.read())
    n = int(t_drop) + 1
    src_t = np.asarray(raw['timex'], dtype=float)
    src_t = src_t - src_t[raw['timeindex'][0]]
    raw['timex'] = [float(x) for x in t[:n]]
    raw['temp2'] = [float(x) for x in bt[:n]]
    # ET is cosmetic here -- pidSource is BT -- but a background with a ragged
    # ET is confusing to look at, so resample the template's onto the new grid.
    raw['temp1'] = [float(x) for x in
                    np.interp(t[:n], src_t, np.asarray(raw['temp1'], dtype=float))]
    raw['timeindex'] = [0, int(round(args.dry_end[0])), int(round(args.fcs[0])),
                        0, 0, 0, int(round(t_drop)), 0]
    raw['roastingnotes'] = (
        f"Authored by tools/make_background.py: {args.mass:.0f} g at "
        f"greens_temp {args.greens_temp:+.1f} degC (operator scale), charge BT "
        f"{args.charge_bt:.1f}, inlet held {args.inlet_precharge:.1f}. Dip from "
        f"charge_dip (phi {phi400:.4f}, tau_mix {tau_mix:.2f}, w_c {w_c:.2f}) to "
        f"TP {dip_bt[i_tp]:.1f} at {t[i_tp]:.0f} s; RoR '{args.decline}' spec "
        f"{np.array2string(params, precision=4)} thereafter, fitted to "
        + (f"DRY END, FCs and RoR {args.ror_at_fcs:.1f} degC/min at FCs; DROP "
           f"{args.development:.0f} s past FCs at "
           f"{float(np.interp(t_drop, t, bt)):.1f} degC."
           if dev_mode else "DRY END/FCs/DROP."))
    out = args.out or os.path.join(
        REPO, 'artisan',
        f"profile_{args.mass:.0f}g_{args.greens_temp:+.0f}C_authored.alog"
        .replace('+', 'p').replace('-', 'm'))
    with open(out, 'w') as fh:
        fh.write(repr(raw))
    print(f"\nwrote {os.path.relpath(out, REPO)}  "
          f"({n} samples at 1 s, timeindex {raw['timeindex']})")


if __name__ == '__main__':
    main()
