#!/usr/bin/env python3
"""Can the preheat absorb a varying charge temperature?

**The operator's idea (2026-09-08):** instead of authoring a different roast for
every greens temperature, preheat *hotter* for a cold charge and *cooler* for a
warm one, so that every batch arrives at the same post-dip state and the loop
sees the same job.  This module answers it from `charge_dip`'s model, sizes the
compensation, and says which parts of the answer are measured and which are not.

**The short answer is yes, with a lever of about 1.17 degC of preheat per degC
of greens at 400 g** -- and the reason is *not* mainly the retained energy the
phrase suggests.

    preheat BT = 124.4 - 1.17 * greens_temp        (400 g, operator's scale)

## Why not retained energy

    phi = m*c_b / (C_chamber + m*c_b) = 0.712 at 400 g
    => C_chamber = 276, against m*c_b = 680

**The chamber is worth about 162 g of coffee.**  It is not a flywheel: it is
41% of a 400 g charge.  So raising the preheat by 1 degC does not hand the bed
1 degC -- the mix gives most of it straight back, and what survives is
``(1 - phi) = 0.29``.  That is the ceiling on the stored-energy mechanism, and
it is set by the same ``phi`` that makes a cold charge hurt in the first place.

The lever is bigger than 0.29 because a settled preheat is two things at once:

    d(TP)/d(greens temp)                 +0.60 degC/degC   <- what must be undone
    d(TP)/d(preheat BT), inlet fixed     +0.27             <- the store
    d(TP)/d(precharge inlet), BT fixed   +0.13             <- the flow
    d(TP)/d(preheat), inlet tracking     +0.40 to +0.47

Holding a hotter BT needs a hotter inlet (Temp_Drive), and the inlet keeps
delivering right through the dip while the mixing deficit is spent once.  About
**two thirds of the lever is the store and one third is the flow.**

## What it buys, and what it cannot

Compensating to match the *turning point* is the obvious target and it is the
wrong one: it matches BT at the TP and then over-drives the recovery, because the
mixing deficit is spent once while the hotter inlet goes on working.  Fitting the
preheat to the loop's own window (30-90 s) instead is the better trade.  At
400 g, spread across greens -24…+25 degC:

    target                      TP    BT@60   BT@90   rms(30-90 s)
    preheat fixed at 130.2    29.2     27.5    23.8    1.11-16.71
    preheat = match TP         0.0      5.0    14.4    0.31- 4.36
    preheat = min rms 30-90    5.3      0.9     7.6    0.18- 2.71

Roast 56's own tracking rms in that window was 0.94 degC, so at 0.18-2.71 the
compensated residual is **at the noise floor of what the machine achieves.**  A
tighter target is not worth chasing.

What the loop is *asked* for matters more than the tracking number.  Regenerating
the background at each charge temperature (RoR peak pinned at 53 s):

    demanded peak RoR      today            compensated
    over greens -24…+25    33.5-55.4        42.8-49.0 degC/min
    spread                 21.9              6.2
    machine ceiling        72                72

**Nearly a third of the machine's demonstrated rate range is currently spent on
charge temperature alone.**  That is the real prize.  It is a different roast
every time, and the one-variable-at-a-time method has been paying for it.

## THE PART THAT IS NOT MEASURED -- read this before believing the number

`charge_dip`'s calibration roasts 50/51/53/54 charged at BT **129.7, 131.0,
130.5, 129.8**.  A spread of 1.3 degC.  **Nobody has ever preheated this machine
anywhere but 130**, so:

* ``d(TP)/d(greens)`` = 0.60 is fitted against a real greens range (roast 50 at
  room temperature against 51/53/54 out of the freezer).  It is a measurement.
* ``d(TP)/d(preheat)`` = 0.40 is **structure, not data.**  It follows from
  ``dT_mix = phi*(BT_c - T_bean)`` -- from the model putting the two
  temperatures in one bracket -- and from the plant card's ``a``.

So **this model cannot falsify the idea**: it assumes the trade it is being
asked about.  What it can do is size the experiment, which is what `--experiment`
prints.  Three things could break it on the machine and none are in the model:

1. **``phi`` may not be constant in preheat.**  The BT probe is not the chamber
   wall.  If a hotter preheat stores energy the probe reads differently, ``phi``
   moves and the lever with it.
2. **Losses look super-linear.**  Temp_Drive evidence (state-plan.md § The
   preheat runs at fan 60) implies ~0.38 degC of drive per degC of BT, against
   0.10 for a loss linear in (BT - ambient).  A 152 degC preheat may not settle
   at fan 60 at all, and the walls may give more back during the pour.
3. **Scorching.**  Tipping into 152 degC is not tipping into 130 degC.  That is
   an operator judgement this module has nothing to say about.

    .venv/bin/python tools/analysis/preheat_lever.py
    .venv/bin/python tools/analysis/preheat_lever.py --mass 400
    .venv/bin/python tools/analysis/preheat_lever.py --experiment
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from scipy.optimize import brentq, minimize_scalar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import charge_dip as cd                                    # noqa: E402

# The settled preheat every calibration roast and every cascade roast has used,
# and its Temp_Drive at fan 60 (dashboard 2026-09-07: BT 130.2 / inlet 140.4).
BT_REF, TD_REF = 130.2, 10.25
# How much more inlet a hotter preheat needs, per degC of preheat BT.  0.10 is
# a loss linear in (BT - ambient); roast 47's empty-chamber grid, corrected to
# fan 60, implies 0.38.  The lever moves by only 0.05 across that whole band
# (--gains prints it), which is why the uncertainty does not matter much.
TD_SLOPE = 0.10
REF_GREENS = -5.0
WINDOW = np.arange(30.0, 91.0, 1.0)     # the loop's own window: PID on at 15 s,
                                        # first correction lands ~28.5 s


def model():
    plant = cd.load_plant()
    c_b = 1.7
    phi400, tau_mix, w_c, rms = cd.calibrate(plant, c_b, 0.0)
    return dict(plant=plant, c_b=c_b, phi400=phi400, tau_mix=tau_mix, w_c=w_c,
                rms=rms, C_ch=cd.C_chamber_from_phi(phi400, c_b))


def curve(m, preheat, greens, mass=400.0, td_slope=TD_SLOPE, inlet=None,
          t=np.arange(0.0, 160.0, 1.0)):
    """BT through the dip at a given preheat.  ``inlet`` overrides the settled one."""
    if inlet is None:
        inlet = preheat + TD_REF + td_slope * (preheat - BT_REF)
    y = cd.dip(t, preheat, greens, mass, lambda _t: inlet, m['plant'],
               phi=cd.phi_of_mass(mass, m['c_b'], m['C_ch']), phi_ref=m['phi400'],
               c_b=m['c_b'], tau_mix=m['tau_mix'], h_fus=0.0, w_c=m['w_c'])
    i = int(np.argmin(y))
    return y, float(y[i]), float(t[i]), inlet


def best_preheat(m, greens, ref, mass=400.0, td_slope=TD_SLOPE):
    """The preheat that best reproduces ``ref`` over the loop's window."""
    t = np.arange(0.0, 160.0, 1.0)

    def cost(x):
        y = curve(m, x, greens, mass, td_slope)[0]
        return float(np.sqrt(np.mean((np.interp(WINDOW, t, y) - ref) ** 2)))

    r = minimize_scalar(cost, bounds=(50.0, 300.0), method='bounded',
                        options={'xatol': 1e-6})
    return float(r.x), float(r.fun)


def lever(m, mass, td_slope=TD_SLOPE, lo=-20.0, hi=10.0):
    """degC of preheat per degC of greens, fitted over the loop's window."""
    t = np.arange(0.0, 160.0, 1.0)
    ref = np.interp(WINDOW, t, curve(m, BT_REF, REF_GREENS, mass, td_slope)[0])
    a = best_preheat(m, lo, ref, mass, td_slope)[0]
    b = best_preheat(m, hi, ref, mass, td_slope)[0]
    return (a - b) / (hi - lo)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mass', type=float, default=400.0)
    ap.add_argument('--td-slope', type=float, default=TD_SLOPE)
    ap.add_argument('--inlet-floor', type=float, default=100.0,
                    help='positiveTargetMin from the .aset (floor100: 100)')
    ap.add_argument('--experiment', action='store_true',
                    help='size the roast that would measure the unmeasured half')
    args = ap.parse_args()

    m = model()
    t = np.arange(0.0, 160.0, 1.0)
    mass, s = args.mass, args.td_slope
    print(f"phi({mass:.0f} g) {cd.phi_of_mass(mass, m['c_b'], m['C_ch']):.4f}   "
          f"C_chamber {m['C_ch']:.0f} = {m['C_ch'] / m['c_b']:.0f} g of coffee, "
          f"against a {mass:.0f} g charge   (dip cal rms {m['rms']:.2f} degC)\n")

    _, tp0, tt0, in0 = curve(m, BT_REF, REF_GREENS, mass, s)
    print(f"reference: greens {REF_GREENS:+.0f}, preheat {BT_REF}, inlet {in0:.1f}"
          f"  ->  TP {tp0:.2f} degC at {tt0:.0f} s")

    print("\n== the gains ==")
    for name, kw in (('greens temp', dict(greens=REF_GREENS + 1)),
                     ('preheat BT alone (inlet fixed)',
                      dict(preheat=BT_REF + 1, inlet=in0)),
                     ('precharge inlet alone (BT fixed)', dict(inlet=in0 + 1))):
        k = dict(preheat=BT_REF, greens=REF_GREENS, mass=mass, td_slope=s)
        k.update(kw)
        print(f"   d(TP)/d({name:32s}) {curve(m, **k)[1] - tp0:+.3f} degC/degC")
    for sl in (0.0, 0.10, 0.25, 0.383, 0.5):
        d = curve(m, BT_REF + 1, REF_GREENS, mass, sl)[1] - \
            curve(m, BT_REF, REF_GREENS, mass, sl)[1]
        print(f"   d(TP)/d(preheat, inlet tracking at Temp_Drive slope {sl:5.3f})"
              f" {d:+.3f}")

    print("\n== the lever, by mass (it is NOT scalable -- phi saturates) ==")
    print("   mass    phi     degC preheat per degC greens")
    for mm in (250., 300., 350., 400., 450., 500.):
        print(f"   {mm:4.0f}   {cd.phi_of_mass(mm, m['c_b'], m['C_ch']):.4f}"
              f"        {lever(m, mm, s):.2f}")
    lv = lever(m, mass, s)

    print(f"\n== the schedule at {mass:.0f} g ==")
    ref = np.interp(WINDOW, t, curve(m, BT_REF, REF_GREENS, mass, s)[0])
    print("   greens  preheat   inlet     TP    BT@60   BT@90   rms(30-90)  reachable")
    grid = list(range(-24, 26, 7))
    rows = []
    for g in grid:
        b, r = best_preheat(m, float(g), ref, mass, s)
        y, tp, tt, inl = curve(m, b, float(g), mass, s)
        rows.append((g, b, inl, tp, np.interp(60, t, y), np.interp(90, t, y), r))
        ok = 'yes' if inl >= args.inlet_floor else f'NO (< {args.inlet_floor:.0f})'
        print(f"   {g:+5d}  {b:7.1f}  {inl:6.1f}  {tp:6.2f}  {np.interp(60,t,y):6.2f}"
              f"  {np.interp(90,t,y):6.2f}   {r:7.2f}    {ok}")
    # preheat(g) = BT_REF - lv*(g - REF_GREENS), i.e. intercept BT_REF + lv*REF_GREENS
    a = BT_REF + lv * REF_GREENS
    print(f"\n   rule of thumb:  preheat BT = {a:.1f} - {lv:.2f} * greens_temp"
          f"   ({mass:.0f} g, operator's thermometer scale)")

    fixed = [curve(m, BT_REF, float(g), mass, s) for g in grid]
    sp = lambda v: max(v) - min(v)                                  # noqa: E731
    print(f"\n   spread over greens {grid[0]:+d}…{grid[-1]:+d}:")
    print(f"     preheat fixed at {BT_REF}:  TP {sp([c[1] for c in fixed]):5.1f}   "
          f"BT@60 {sp([float(np.interp(60,t,c[0])) for c in fixed]):5.1f}   "
          f"BT@90 {sp([float(np.interp(90,t,c[0])) for c in fixed]):5.1f} degC")
    print(f"     compensated:             TP {sp([r[3] for r in rows]):5.1f}   "
          f"BT@60 {sp([r[4] for r in rows]):5.1f}   "
          f"BT@90 {sp([r[5] for r in rows]):5.1f} degC")

    lo_g = min(g for g, b, inl, *_ in rows if inl >= args.inlet_floor)
    hi_g = max(g for g, b, inl, *_ in rows if inl >= args.inlet_floor)
    print(f"\n   the inlet floor ({args.inlet_floor:.0f}) is the binding constraint at the"
          f" WARM end;\n   reachable over greens {lo_g:+d}…{hi_g:+d} degC at least, "
          "which covers freezer to room temperature.")

    if args.experiment:
        print("\n== sizing the experiment ==")
        print("Every calibration roast charged at BT 129.7-131.0 -- a 1.3 degC spread.")
        print("d(TP)/d(preheat) is therefore structure, not data. To measure it, hold")
        print("the greens temperature and the mass and step the PREHEAT:\n")
        d = curve(m, BT_REF + 1, REF_GREENS, mass, s)[1] - tp0
        need = 4.0 / d
        print(f"   the dip model's own calibration rms is {m['rms']:.2f} degC and the")
        print(f"   -12 group's roast-to-roast scatter is 2.7 degC, so a TP shift needs")
        print(f"   to clear ~4 degC to be unambiguous.  At {d:+.3f} degC of TP per degC")
        print(f"   of preheat that is a step of **{need:.0f} degC**.\n")
        for step in (10., 15., 20.):
            y, tp, tt, inl = curve(m, BT_REF + step, REF_GREENS, mass, s)
            print(f"   preheat {BT_REF + step:5.1f} (inlet {inl:5.1f}): predicted TP "
                  f"{tp:6.2f} ({tp - tp0:+.2f}), BT@60 "
                  f"{float(np.interp(60,t,y)):6.2f} "
                  f"({float(np.interp(60,t,y)) - float(np.interp(60,t,curve(m,BT_REF,REF_GREENS,mass,s)[0])):+.2f})")
        print("\n   ONE roast does it: the 130.2 baseline is already four roasts deep.")
        print("   Regenerate the background at the new preheat (--charge-bt and")
        print("   --inlet-precharge) so the loop is not asked to fight the step, and")
        print("   read the TP off the log.  A measured gain below ~0.3 or above ~0.55")
        print("   moves the lever enough to matter; inside that band, ship the rule.")
        print("\n   It also tests the two things the model cannot: whether fan 60 still")
        print("   settles at the higher preheat at all, and what Temp_Drive does there")
        print("   (predicted {:.1f} at BT {:.1f} on the 0.10 slope, {:.1f} on 0.383)."
              .format(TD_REF + 0.10 * 15, BT_REF + 15, TD_REF + 0.383 * 15))


if __name__ == '__main__':
    main()
