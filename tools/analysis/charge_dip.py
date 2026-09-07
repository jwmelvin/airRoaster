#!/usr/bin/env python3
"""Predicting the charge dip from (mass, greens temperature).

The early roast is two processes that overlap and have never been separated:
**mixing**, in which a cold charge and a hot chamber find a common temperature,
and the **plant**, in which the heater drives BT through `Inlet -> BT`.  The
simulator behind state-plan.md is honest that the dip is its weak part -- floor
times good to about +-10 s, dip absolute numbers not trustworthy -- because it
has no mixing term at all: the whole dip lives inside `loss(t)`, a low-order
polynomial fitted per roast.  That is fine for reproducing *one* roast and
useless for predicting a *different charge state*.

**What this module adds is one equation with one new constant.**

    mixing:  dBT/dt = -(dT_mix / tau_mix) * exp(-t / tau_mix)
    plant:   dBT/dt =  a*(Inlet(t - theta) - BT) + loss(t)

    dT_mix = phi*(BT_c - T_bean) + m*h_fus/(C_chamber + m*c_b)

``phi`` is the mixing fraction, ``m*c_b / (C_chamber + m*c_b)`` -- the fraction
of the gap between the charge temperature and the pre-charge BT that the mix
closes.  Everything else is the plant card the project already has.

**Mixing is a finite quantity of heat, not a setpoint**, and getting that wrong
is worth 40 degC.  Written the obvious way -- ``dBT/dt = -(BT - BT_mix)/tau`` --
the mix becomes a permanent attractor at ``BT_mix`` that goes on fighting the
heater for the whole roast: the model flatlines near 62 degC while roasts 43
and 46 turn at 58 degC at 23 s and are back through 100 degC by 60 s.  As a
decaying *rate* it integrates to exactly ``dT_mix`` and then stops, which is
what mixing does, and the plant takes the roast back.

**Where the numbers come from, and this is the part that matters.**

* ``phi`` and ``tau_mix`` are **fitted to the roasts**, not to the charge-thermal test, over
  ``0..40 s`` of measured BT on roasts 43/44/46 at an assumed -18 degC.  They
  are *not* read off ``charge_state.py``'s ``k``: that constant is the drop
  measured at ``+theta``, which already folds in how far the mix has got by
  13.5 s **and** the heat the plant put back over the same window, so
  ``phi = 4k`` under-predicts the asymptote and the drops come out 7-10 degC
  short.  ``k`` is a proxy; ``phi`` is a parameter, and they are not the same
  number.  The fit is under **forced convection at the charge fan**, which is
  the condition a roast is in and the charge-thermal test is not.
* ``c_b`` and the **fusion enthalpy bound** come from the charge-thermal test
  (``charge_thermal.py``).  Fusion matters here: it is the difference between a
  frozen charge costing ``m*c_b*dT`` and costing ``m*(c_b*dT + h_fus)``.
* ``a``, ``theta`` and ``loss`` come from ``plant_roast46.json``, untouched.

**What the charge-thermal test does *not* supply, and why.**  It was run to calibrate
``C_chamber`` directly, and it cannot: with no fan the BT probe sits in a narrow
expansion zone reading the chamber walls rather than the bed, and the charge
temperature trades against that so completely that the best-fitting solution
puts a room-temperature charge at -2 degC (``charge_thermal.py``).  So
``C_chamber`` here is **derived from ``phi``**, not from the charge-thermal test, and the charge-thermal test
is used for the two things it does pin down.

    .venv/bin/python tools/analysis/charge_dip.py
    .venv/bin/python tools/analysis/charge_dip.py --sweep
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
from scipy.special import erf

from roastdata import load_profile

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, "Documents/artisan/airRoaster_%s.alog")
PLANT = os.path.join(REPO, "tools/analysis/plant_roast46.json")
THERMAL = os.path.join(REPO, "tools/analysis/charge_thermal.json")

# charge_state.py's calibration, and its stated uncertainty.  degC per 100 g of
# charge, per degC of (BT_charge - T_bean).
K_PROXY, K_SD = 0.10217, 0.00227
MASS_REF = 400.0

# The assumed charge temperatures behind that calibration, and the two the charge-thermal test
# measured them against.  43/44/46 are the frozen group charge_state.py
# calibrates on; 48 and 49 are what it then reads off.
T_BEAN_ASSUMED = {"43": -18.0, "44": -18.0, "46": -18.0, "48": 12.8, "49": 15.5}


def load_plant():
    with open(PLANT) as fh:
        return json.load(fh)


def load_thermal():
    if not os.path.exists(THERMAL):
        return None
    with open(THERMAL) as fh:
        return json.load(fh)


def phi_of_mass(mass, c_b=1.7, C_chamber=None):
    """Mixing fraction at ``mass``.

    ``phi`` is measured at 400 g and extrapolated by the physics, not by a
    per-gram rule: ``phi = m c / (C_chamber + m c)`` saturates, which is exactly
    why charge_state.py warns that its proxy is not linear in mass and why
    roast 45 at 345 g reads low.
    """
    if C_chamber is None:
        C_chamber = C_chamber_from_phi(MASS_REF * K_PROXY * MASS_REF / 100.0, c_b)
    mc = mass * c_b
    return mc / (C_chamber + mc)


def C_chamber_from_phi(phi, c_b=1.7, mass=MASS_REF):
    """Invert ``phi = m c / (C_chamber + m c)``."""
    mc = mass * c_b
    return mc * (1.0 - phi) / phi


# The melt band, matching charge_thermal.py: not a step at 0 degC.
T_MELT, W_MELT = -2.0, 4.0


def dip(t, bt_charge, t_bean, mass, inlet_fn, plant, phi=None, c_b=1.7,
        tau_mix=6.0, h_fus=0.0, dt=0.25, phi_ref=None):
    """BT over ``t`` seconds from CHARGE.

    ``inlet_fn(t)`` is the commanded/measured inlet in degC; the plant's own
    delay is applied inside, so pass the *un*-delayed trace.  ``loss`` is the
    plant card's cubic, evaluated on the same clock it was fitted on.
    """
    a, theta = plant["a"], plant["theta"]
    coef = plant.get("loss_poly")
    t_lo = plant.get("loss_window", [45.0, 430.0])[0]

    if phi_ref is None:
        phi_ref = phi if phi is not None else 4.0 * K_PROXY
    if phi is None:
        phi = phi_of_mass(mass, c_b, C_chamber_from_phi(phi_ref, c_b))

    # The fusion enthalpy is spent as the bed crosses the melt band, and the
    # only place it can show up in a BT equation is as extra thermal mass --
    # i.e. as a *deeper* mix.  m*h_fus / (C_chamber + m*c_b) is that in degC,
    # and it applies only to a charge that starts below the band at all.
    # Smeared over the melt band rather than switched at 0 degC: green coffee's
    # water is partly bound and its freezing point is depressed, and a hard
    # switch puts a 7 degC step into the middle of the charge-temperature sweep
    # at exactly the value nothing physical happens at.
    frac = 0.5 * (1.0 + erf((T_MELT - t_bean) / (W_MELT * np.sqrt(2.0))))
    extra = frac * mass * h_fus / (C_chamber_from_phi(phi_ref, c_b) + mass * c_b)

    dT_mix = phi * (bt_charge - t_bean) + extra

    n = int(np.ceil(t[-1] / dt)) + 1
    ts = np.arange(n) * dt
    bt = np.empty(n)
    x = bt_charge
    for k in range(n):
        bt[k] = x
        tk = ts[k]
        d_mix = -(dT_mix / tau_mix) * np.exp(-tk / tau_mix)
        d_plant = a * (inlet_fn(tk - theta) - x)
        if coef is not None:
            # The loss cubic was fitted over 45-430 s and is an extrapolation
            # before that -- straight into the window this module exists for.
            # Held flat at its first fitted value rather than extrapolated: a
            # cubic run backwards 45 s is not a loss curve, it is an artefact.
            d_plant += float(np.polyval(coef, max(tk, t_lo)))
        x += dt * (d_mix + d_plant)
    return np.interp(t, ts, bt)


def roast_inlet_fn(prof, pre_charge):
    """Measured inlet as a function of time from CHARGE.

    Before CHARGE the trace exists, so it is used; the plant's delay reaches
    back into it, which is the whole reason ``charge_state.py`` needed an air
    correction in the first place.
    """
    ti, inlet = prof.extras["Inlet"]

    def f(t):
        if t < ti[0]:
            return pre_charge
        return float(np.interp(t, ti, inlet))
    return f


def _roast_case(rid, t_bean):
    prof = load_profile(ALOG % rid)
    ti, inlet = prof.extras["Inlet"]
    pre = float(np.mean(inlet[(ti >= -30) & (ti < 0)]))
    return dict(rid=rid, prof=prof, mass=float(prof.raw["weight"][0]),
                bt_c=float(np.interp(0.0, prof.t, prof.bt)), t_bean=t_bean,
                fn=roast_inlet_fn(prof, pre), pre=pre)


def calibrate(plant, c_b, h_fus, rids=("43", "44", "46"), t_end=40.0):
    """Fit ``(phi at 400 g, tau_mix)`` to measured BT over ``0..t_end``.

    Calibrated on the frozen group alone, so roasts 48 and 49 are held out --
    with the caveat that their assumed charge temperatures come from the same
    proxy and the same -18 degC assumption, so they are a check on the *shape*,
    not an independent test of the physics.
    """
    from scipy.optimize import least_squares
    cases = [_roast_case(r, T_BEAN_ASSUMED[r]) for r in rids]
    t = np.arange(0.0, t_end + 0.01, 0.5)

    def resid(x):
        phi400, tau_mix = x
        C_ch = C_chamber_from_phi(phi400, c_b)  # noqa: F841 -- used below
        out = []
        for c in cases:
            y = dip(t, c["bt_c"], c["t_bean"], c["mass"], c["fn"], plant,
                    phi=phi_of_mass(c["mass"], c_b, C_ch), phi_ref=phi400,
                    c_b=c_b, tau_mix=tau_mix, h_fus=h_fus)
            out.append(y - np.interp(t, c["prof"].t, c["prof"].bt))
        return np.concatenate(out)

    r = least_squares(resid, [0.45, 6.0], bounds=([0.05, 1.0], [0.95, 40.0]))
    return float(r.x[0]), float(r.x[1]), float(np.sqrt(np.mean(r.fun ** 2)))


def check_against_roasts(plant, c_b, h_fus, phi400, tau_mix, t_end=40.0):
    """Predicted vs measured, both the +theta drop and the whole 0..t_end arc."""
    C_ch = C_chamber_from_phi(phi400, c_b)
    theta = plant["theta"]
    t = np.arange(0.0, t_end + 0.01, 0.5)
    rows = []
    for rid, t_bean in T_BEAN_ASSUMED.items():
        c = _roast_case(rid, t_bean)
        y = dip(t, c["bt_c"], t_bean, c["mass"], c["fn"], plant,
                phi=phi_of_mass(c["mass"], c_b, C_ch), phi_ref=phi400,
                c_b=c_b, tau_mix=tau_mix, h_fus=h_fus)
        meas = np.interp(t, c["prof"].t, c["prof"].bt)
        rows.append(dict(roast=rid, mass=c["mass"], bt_c=c["bt_c"],
                         t_bean=t_bean, pre=c["pre"],
                         meas_drop=c["bt_c"] - float(np.interp(theta, t, meas)),
                         pred_drop=c["bt_c"] - float(np.interp(theta, t, y)),
                         rms=float(np.sqrt(np.mean((y - meas) ** 2))),
                         worst=float(np.max(np.abs(y - meas)))))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep", action="store_true",
                    help="dip depth and turning point against charge temperature")
    ap.add_argument("--fusion", action="store_true",
                    help="what the roasts say about the fusion enthalpy")
    ap.add_argument("--h-fus", type=float, default=None,
                    help="J/g; default is the charge-thermal test's fitted value if carded")
    args = ap.parse_args()

    plant = load_plant()
    th = load_thermal()
    # c_b is at a bound in the charge-thermal test's fit and is not identified there either;
    # 1.7 J/g/K is green coffee at 10-12% moisture from the literature, and it
    # only ever appears here multiplied into C_chamber, which IS fitted.
    c_b = 1.7
    # The card's point estimate is not usable: the charge-thermal test cannot resolve the
    # magnitude, and the fitted value comes out above 35 J/g -- more fusion
    # enthalpy than a 10.5% moisture charge physically contains.  Take the
    # middle of the carded band and sweep it with --h-fus.
    # Default 0, against the charge-thermal test's own preference, and the --fusion table says
    # why: the frozen calibration group absorbs any value of h_fus exactly into
    # phi (rms 3.08 at every one of 0-35 J/g), so it carries no information, and
    # the only roasts that do carry some -- the warm held-out pair -- get
    # monotonically worse as h_fus rises.
    h_fus = args.h_fus if args.h_fus is not None else 0.0

    phi400, tau_mix, cal_rms = calibrate(plant, c_b, h_fus)
    C_ch = C_chamber_from_phi(phi400, c_b)
    print("== the mixing constant, and where each half of it comes from ==")
    print(f"   phi(400 g) = {phi400:.4f}, tau_mix = {tau_mix:.2f} s   "
          f"(fitted to roasts 43/44/46 over 0-40 s, rms {cal_rms:.2f} degC)")
    print(f"   charge_state.py's 4k = {4 * K_PROXY:.4f} is the drop at +theta, "
          "not this: it is\n   smaller because the mix is incomplete at 13.5 s "
          "and the plant is already pushing back.")
    print(f"   c_b = {c_b:.3f} J/g/K, h_fus = {h_fus:.1f} J/g "
          f"(band {th['h_fus_band_J_per_g'] if th else 'n/a'})   "
          "(charge_thermal.py, the charge-thermal test)")
    print(f"   -> C_bed(400 g) = {MASS_REF * c_b:.0f} J/K, "
          f"C_chamber = {C_ch:.0f} J/K, ratio {C_ch / (MASS_REF * c_b):.2f}")
    print(f"   a = {plant['a']:.5f} /s, theta = {plant['theta']:.1f} s "
          "(plant_roast46.json, unchanged)")

    print("\n== phi is not linear in mass, which is why roast 45 read low ==")
    for m in (300.0, 345.0, 400.0, 450.0, 500.0):
        p = phi_of_mass(m, c_b, C_ch)
        per_g = (p / m) / (phi400 / MASS_REF)
        print(f"   {m:5.0f} g   phi {p:.4f}   per gram {100 * (per_g - 1):+5.1f}% "
              "against 400 g")

    print("\n== against the roasts, over the whole 0-40 s arc ==")
    rows = check_against_roasts(plant, c_b, h_fus, phi400, tau_mix)
    print("   roast  mass  BT@0  T_bean   drop meas/pred      rms   worst")
    for r in rows:
        held = "" if r["roast"] in ("43", "44", "46") else "  <- held out"
        print(f"   {r['roast']:>5s} {r['mass']:5.0f} {r['bt_c']:6.1f} "
              f"{r['t_bean']:+7.1f}   {r['meas_drop']:6.2f} / {r['pred_drop']:6.2f}   "
              f"{r['rms']:6.2f}  {r['worst']:6.2f}{held}")
    print("   43/44/46 are the calibration.  48 and 49 are held out of the fit,")
    print("   but their charge temperatures came from the same proxy and the same")
    print("   -18 degC assumption, so they test the shape and not the physics.")
    print("   Nothing in this project has yet measured a charge temperature")
    print("   under flow -- see charge_thermal.py for why the charge-thermal test does not.")

    if args.fusion:
        print("\n== the fusion enthalpy, and the one disagreement in the set ==")
        print("   h_fus   phi400   cal rms   held-out rms 48 / 49   C_chamber")
        for h in (0.0, 7.0, 14.0, 21.0, 28.0, 35.0):
            ph, tm, rm = calibrate(plant, c_b, h)
            d = {r["roast"]: r["rms"] for r in
                 check_against_roasts(plant, c_b, h, ph, tm)}
            print(f"   {h:5.1f}   {ph:.4f}    {rm:5.2f}      "
                  f"{d['48']:5.2f} / {d['49']:5.2f}        "
                  f"{C_chamber_from_phi(ph, c_b):5.0f} J/K")
        print("   The calibration rms does not move at all: on a frozen-only")
        print("   group, phi and h_fus are the same parameter and phi absorbs it.")
        print("   The held-out warm roasts are the only lever, and they want")
        print("   h_fus = 0 -- which is the opposite of what the charge-thermal test's still-air")
        print("   fit wants (zero costs it 20% of residual). The disagreement is")
        print("   real and unresolved; the default here follows the roasts.")

    if args.sweep:
        print("\n== the dip against charge temperature, 400 g, roast 46's inlet ==")
        prof = load_profile(ALOG % "46")
        ti, inlet = prof.extras["Inlet"]
        pre = float(np.mean(inlet[(ti >= -30) & (ti < 0)]))
        fn = roast_inlet_fn(prof, pre)
        bt_c = float(np.interp(0.0, prof.t, prof.bt))
        t = np.arange(0.0, 120.01, 0.5)
        print("   T_bean   BT@theta   dip min   at (s)   BT@60   BT@90")
        for tb in (-20.0, -10.0, 0.0, 10.0, 20.0, 30.0):
            y = dip(t, bt_c, tb, 400.0, fn, plant,
                    phi=phi_of_mass(400.0, c_b, C_ch), phi_ref=phi400,
                    c_b=c_b, tau_mix=tau_mix, h_fus=h_fus)
            i = int(np.argmin(y))
            print(f"   {tb:+6.1f}   {float(np.interp(plant['theta'], t, y)):8.1f}   "
                  f"{y[i]:7.1f}   {t[i]:6.1f}   "
                  f"{float(np.interp(60.0, t, y)):6.1f}   "
                  f"{float(np.interp(90.0, t, y)):6.1f}")
        print("   The spread at +theta is phi*(range of T_bean) by construction.")
        print("   What is *not* by construction is how much of it survives to")
        print("   +60 and +90 s, which is the plant pulling the roast back.")


if __name__ == "__main__":
    main()
