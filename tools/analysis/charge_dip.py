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

**What this module adds is one equation with two constants.**

    mixing:  dBT/dt = -dT_mix * g(t; tau_mix, w_c)
    plant:   dBT/dt =  a*(Inlet(t - theta) - BT) + loss(t)

    dT_mix = phi*(BT_c - T_bean) + m*h_fus/(C_chamber + m*c_b)
    g(t)   = exp(-t/tau_mix) * (exp(min(t,w_c)/tau_mix) - 1) / w_c

``phi`` is the mixing fraction, ``m*c_b / (C_chamber + m*c_b)`` -- the fraction
of the gap between the charge temperature and the pre-charge BT that the mix
closes.  ``w_c`` is the **pour ramp**: 400 g does not arrive in an instant, and
``g`` is a uniform pour convolved with the bare exponential, normalised so it
still integrates to exactly ``dT_mix`` (``mix_kernel``).  Everything else is the
plant card the project already has.

**The ramp was added on 2026-09-07 and it is not a detail.**  Without it the fit
has to buy the dip's depth by stretching ``tau_mix`` to 12-15 s, which then turns
the dip 6-7 s late -- the defect that put roast 54's background 6.7 degC above
the bed at the turn.  With it, ``tau_mix`` falls to ~10.8 s, the calibration rms
halves (2.73 -> 1.31 degC) and the turn comes back within 3-5 s.  Run
``--ramp`` for the profile.  ``w_c`` and ``tau_mix`` trade at -0.77, so read the
band 1.5-3 s and not a fourth decimal.

**Mixing is a finite quantity of heat, not a setpoint**, and getting that wrong
is worth 40 degC.  Written the obvious way -- ``dBT/dt = -(BT - BT_mix)/tau`` --
the mix becomes a permanent attractor at ``BT_mix`` that goes on fighting the
heater for the whole roast: the model flatlines near 62 degC while roasts 43
and 46 turn at 58 degC at 23 s and are back through 100 degC by 60 s.  As a
decaying *rate* it integrates to exactly ``dT_mix`` and then stops, which is
what mixing does, and the plant takes the roast back.

**Where the numbers come from, and this is the part that matters.**

* ``phi``, ``tau_mix`` and ``w_c`` are **fitted to the roasts**, not to the
  charge-thermal test, jointly, over each roast's **loop-free window** --
  ``theta`` seconds after the inlet first leaves the preheat, past which the
  residual is the plant card replaying the loop's own kick.  They are *not*
  read off ``charge_state.py``'s ``k``: that constant is the drop measured at
  ``+theta``, which already folds in how far the mix has got by 13.5 s **and**
  the heat the plant put back over the same window, so ``phi = 4k``
  under-predicts the asymptote and the drops come out 7-10 degC short.  ``k``
  is a proxy; ``phi`` is a parameter, and they are not the same number.  The
  fit is under **forced convection at the charge fan**, which is the condition
  a roast is in and the charge-thermal test is not.
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

**``phi`` IS NOT PHYSICS -- IT IS DEPTH PER degC ON THE OPERATOR'S SCALE.**  It
is fitted against charge temperatures nobody has measured at the bean's core,
and 12 degC of charge temperature is worth 0.07 of ``phi``: roasts 43/44/46 at
an assumed -18 with roast 54 at ``charge_state.py``'s inferred -24.1 give
``phi = 0.648``, and the same roasts' successors at the temperatures the
operator actually entered give ``phi = 0.712``.  **Both fit, and both ask for
the same dip** -- because the offset cancels as long as the number you fit on
and the number you evaluate at are read the same way.  Mixing the two scales is
not a rounding error: it is exactly what left roast 54's generated background
6.7 degC too shallow, and why the group here is the roasts with an *entered*
greens temperature rather than the older assumed-temperature group.  Run
``--scale``.  Settling it needs a charge whose **core** temperature is measured.

    .venv/bin/python tools/analysis/charge_dip.py
    .venv/bin/python tools/analysis/charge_dip.py --ramp
    .venv/bin/python tools/analysis/charge_dip.py --scale
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
# calibrates on; 48 and 49 are what it then reads off.  **Not one of these is a
# measurement** -- see RECORDED below and the module docstring's scale warning.
T_BEAN_ASSUMED = {"43": -18.0, "44": -18.0, "46": -18.0, "48": 12.8, "49": 15.5}

# The roasts that carry a charge temperature the operator actually entered in
# Roast Properties.  Roast 50 is the only *measured* one in the whole set (a
# room-temperature charge, thermometer read); 51/53/54 are the operator's
# freezer reading, and may be one measurement entered three times.  This is the
# calibration group, because it is the only one on the same scale as the number
# `make_charge_background.py --greens-temp` is handed.
T_BEAN_RECORDED = {"50": 25.0, "51": -12.0, "53": -12.0, "54": -12.0}
CAL_RIDS = ("50", "51", "53", "54")

# The pour ramp, seconds, fitted with the rest.  charge_thermal.py's card says
# 0.54 s, but that fit is no-flow and w_c there only scales a wall-to-bed
# coupling; under flow the roasts want 2.1 s and say so with a clear minimum.
W_C = 2.10


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


def mix_kernel(t, tau_mix, w_c):
    """The mixing rate's shape, normalised so ``integral_0^inf = 1``.

    **The charge is a ramp, not a step** -- the same correction
    ``charge_thermal.py`` needed and for the same reason: tipping 400 g in takes
    a second or two, so the cold mass arrives over ``w_c`` rather than all at
    ``t = 0``.  Each parcel poured at ``s`` then mixes on its own ``tau_mix``,
    so the rate is the convolution of a uniform pour with the bare exponential:

        g(t) = integral_0^min(t,w_c) (1/w_c) (1/tau) exp(-(t-s)/tau) ds
             = exp(-t/tau) * (exp(min(t,w_c)/tau) - 1) / w_c

    which is closed-form, integrates to exactly 1 (the deficit is conserved --
    a ramp changes *when* the heat is drawn, never how much), and collapses to
    the old ``exp(-t/tau)/tau`` as ``w_c -> 0``.

    **Leaving it out does not just soften the first two seconds.**  The bare
    exponential has to be both as deep as the measurement and as early, and it
    cannot be: the fit buys the depth by stretching ``tau_mix`` to 12-14 s,
    which then turns the dip 4-6 s late.  With the ramp in, ``tau_mix`` falls to
    ~10 s and the turning point comes back -- see the ``--ramp`` table.
    """
    t = np.asarray(t, dtype=float)
    if w_c <= 1e-6:
        return np.exp(-t / tau_mix) / tau_mix
    u = np.minimum(t, w_c)
    return np.where(t <= 0.0, 0.0,
                    np.exp(-t / tau_mix) * (np.expm1(u / tau_mix)) / w_c)


def dip(t, bt_charge, t_bean, mass, inlet_fn, plant, phi=None, c_b=1.7,
        tau_mix=6.0, h_fus=0.0, dt=0.25, phi_ref=None, w_c=W_C):
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
    g = mix_kernel(ts, tau_mix, w_c)
    bt = np.empty(n)
    x = bt_charge
    for k in range(n):
        bt[k] = x
        tk = ts[k]
        d_mix = -dT_mix * g[k]
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


def free_window(prof, pre, theta, tol=5.0, cap=40.0):
    """Seconds after CHARGE over which BT is still innocent of the loop.

    The loop's correction cannot reach BT before ``theta``, so the honest fit
    window ends ``theta`` after the inlet first leaves where the preheat put it.
    Every roast before 54 had the outer loop railing ``T_inlet`` within a few
    seconds of CHARGE, which is why their windows are 15-18 s and only roast 54
    -- the first with the charge gate armed -- reaches past its own turning
    point.  Fitting past the window would be fitting the loop's overshoot, the
    circularity ``dekick_tp.py`` and ``make_charge_background.py --check`` both
    exist to avoid.
    """
    g = np.arange(0.0, cap + 0.5, 0.5)
    v = np.interp(g, *prof.extras["Inlet"])
    off = np.abs(v - pre) > tol
    return float(g[int(np.argmax(off))]) + theta if off.any() else cap


def _roast_case(rid, t_bean, theta=None):
    prof = load_profile(ALOG % rid)
    ti, inlet = prof.extras["Inlet"]
    pre = float(np.mean(inlet[(ti >= -30) & (ti < 0)]))
    c = dict(rid=rid, prof=prof, mass=float(prof.raw["weight"][0]),
             bt_c=float(np.interp(0.0, prof.t, prof.bt)), t_bean=t_bean,
             fn=roast_inlet_fn(prof, pre), pre=pre)
    if theta is not None:
        c["t_end"] = free_window(prof, pre, theta)
    return c


def calibrate(plant, c_b, h_fus, rids=CAL_RIDS, t_bean=None, free_w_c=True,
              w_c=W_C):
    """Fit ``(phi at 400 g, tau_mix, w_c)`` to measured BT over each roast's
    loop-free window.

    **The group changed on 2026-09-07 and the reason is a scale, not a fit.**
    It used to be roasts 43/44/46 at an *assumed* -18 degC, and the resulting
    ``phi`` was then handed a *measured* greens temperature by
    ``make_charge_background.py``.  Those are two different scales, and mixing
    them is what made roast 54's background 6.7 degC too shallow: fitted at
    -18/-24, evaluated at the operator's -12.  The group here is instead every
    roast that carries a greens temperature the operator entered, so the
    calibration and the tool's input are on one scale and whatever offset the
    operator's thermometer has cancels out of the answer.

    ``phi`` is therefore **not physics** -- it is depth per degC on the
    operator's scale.  If the entered temperatures are 12 degC warm, ``phi``
    absorbs exactly that, and it is only correct as long as it keeps being fed
    numbers read the same way.  The 43/44/46 group is kept as a held-out check
    and reports a visibly different ``phi`` for exactly this reason.
    """
    from scipy.optimize import least_squares
    theta = plant["theta"]
    tb = dict(T_BEAN_ASSUMED, **T_BEAN_RECORDED)
    if t_bean:
        tb.update(t_bean)
    cases = [_roast_case(r, tb[r], theta) for r in rids]

    def resid(x):
        phi400, tau_mix = x[0], x[1]
        w = x[2] if free_w_c else w_c
        C_ch = C_chamber_from_phi(phi400, c_b)
        out = []
        for c in cases:
            t = np.arange(0.0, c["t_end"] + 0.01, 0.5)
            y = dip(t, c["bt_c"], c["t_bean"], c["mass"], c["fn"], plant,
                    phi=phi_of_mass(c["mass"], c_b, C_ch), phi_ref=phi400,
                    c_b=c_b, tau_mix=tau_mix, h_fus=h_fus, w_c=w)
            out.append(y - np.interp(t, c["prof"].t, c["prof"].bt))
        return np.concatenate(out)

    x0, lo, hi = [0.65, 10.0, 2.5], [0.05, 1.0, 0.0], [0.95, 40.0, 15.0]
    if not free_w_c:
        x0, lo, hi = x0[:2], lo[:2], hi[:2]
    r = least_squares(resid, x0, bounds=(lo, hi))
    w = float(r.x[2]) if free_w_c else w_c
    return float(r.x[0]), float(r.x[1]), w, float(np.sqrt(np.mean(r.fun ** 2)))


def check_against_roasts(plant, c_b, h_fus, phi400, tau_mix, w_c=W_C,
                         rids=None, t_bean=None):
    """Predicted vs measured over each roast's loop-free window.

    Scored on the free window, not a fixed 0-40 s: past it the residual is the
    plant card replaying the loop's own kick and says nothing about the mix.
    """
    C_ch = C_chamber_from_phi(phi400, c_b)
    theta = plant["theta"]
    tb = dict(T_BEAN_ASSUMED, **T_BEAN_RECORDED)
    if t_bean:
        tb.update(t_bean)
    rows = []
    for rid in (rids if rids is not None else sorted(tb, key=int)):
        c = _roast_case(rid, tb[rid], theta)
        t = np.arange(0.0, c["t_end"] + 0.01, 0.5)
        y = dip(t, c["bt_c"], c["t_bean"], c["mass"], c["fn"], plant,
                phi=phi_of_mass(c["mass"], c_b, C_ch), phi_ref=phi400,
                c_b=c_b, tau_mix=tau_mix, h_fus=h_fus, w_c=w_c)
        meas = np.interp(t, c["prof"].t, c["prof"].bt)
        i_y, i_m = int(np.argmin(y)), int(np.argmin(meas))
        rows.append(dict(roast=rid, mass=c["mass"], bt_c=c["bt_c"],
                         t_bean=c["t_bean"], pre=c["pre"], t_end=c["t_end"],
                         meas_drop=c["bt_c"] - float(np.interp(theta, t, meas)),
                         pred_drop=c["bt_c"] - float(np.interp(theta, t, y)),
                         rms=float(np.sqrt(np.mean((y - meas) ** 2))),
                         worst=float(np.max(np.abs(y - meas))),
                         tp_pred=(float(y[i_y]), float(t[i_y])),
                         tp_meas=(float(meas[i_m]), float(t[i_m]))))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep", action="store_true",
                    help="dip depth and turning point against charge temperature")
    ap.add_argument("--fusion", action="store_true",
                    help="what the roasts say about the fusion enthalpy")
    ap.add_argument("--ramp", action="store_true",
                    help="profile the pour ramp w_c, and what dropping it costs")
    ap.add_argument("--scale", action="store_true",
                    help="the phi / charge-temperature degeneracy, both branches")
    ap.add_argument("--h-fus", type=float, default=None,
                    help="J/g; default 0 -- see --fusion")
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
    # Default 0, against the charge-thermal test's own preference, and --fusion
    # says why: on the recorded-temperature group the only *measured* charge in
    # the set (roast 50, +25 degC, unfrozen) drives h_fus hard to zero, and the
    # frozen roasts cannot outvote it because phi absorbs any value they prefer.
    h_fus = args.h_fus if args.h_fus is not None else 0.0

    phi400, tau_mix, w_c, cal_rms = calibrate(plant, c_b, h_fus)
    C_ch = C_chamber_from_phi(phi400, c_b)
    print("== the mixing constant, and where each half of it comes from ==")
    print(f"   phi(400 g) = {phi400:.4f}, tau_mix = {tau_mix:.2f} s, "
          f"w_c = {w_c:.2f} s")
    print(f"   fitted jointly to roasts {'/'.join(CAL_RIDS)} over each roast's "
          f"loop-free window,\n   at the greens temperatures the operator "
          f"entered, rms {cal_rms:.2f} degC.")
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
    print("   phi is depth per degC ON THE OPERATOR'S TEMPERATURE SCALE and is "
          "not physics.\n   Feed it numbers read the same way or it is wrong by "
          "phi times the offset --\n   see --scale.")

    print("\n== phi is not linear in mass, which is why roast 45 read low ==")
    for m in (300.0, 345.0, 400.0, 450.0, 500.0):
        p_ = phi_of_mass(m, c_b, C_ch)
        per_g = (p_ / m) / (phi400 / MASS_REF)
        print(f"   {m:5.0f} g   phi {p_:.4f}   per gram {100 * (per_g - 1):+5.1f}% "
              "against 400 g")
    print("   UNVALIDATED away from 400 g: roasts 51 and 52 differ only in mass "
          "and\n   disagree with this column by 5.4%, in the wrong direction "
          "(state-current.md).")

    print("\n== against the roasts, over each one's loop-free window ==")
    rows = check_against_roasts(plant, c_b, h_fus, phi400, tau_mix, w_c)
    print("   roast  mass  BT@0  T_bean  window   drop meas/pred     rms  worst"
          "   TP meas / pred")
    for r in rows:
        held = "" if r["roast"] in CAL_RIDS else "  <- held out, ASSUMED T_bean"
        print(f"   {r['roast']:>5s} {r['mass']:5.0f} {r['bt_c']:6.1f} "
              f"{r['t_bean']:+7.1f} {r['t_end']:6.1f}s  "
              f"{r['meas_drop']:6.2f} /{r['pred_drop']:6.2f}  "
              f"{r['rms']:6.2f} {r['worst']:6.2f}   "
              f"{r['tp_meas'][0]:5.1f}@{r['tp_meas'][1]:4.1f} / "
              f"{r['tp_pred'][0]:5.1f}@{r['tp_pred'][1]:4.1f}{held}")
    print("   43/44/46/48/49 carry no entered greens temperature at all: theirs "
          "is the\n   -18 degC assumption charge_state.py calibrates on, so "
          "they are a check on\n   the *shape* and read a different phi by "
          "construction.  Windows shorter than\n   the turning point score the "
          "descent only -- the turn is roast 54's alone.")

    if args.ramp:
        print("\n== the pour ramp: profile of w_c, tau and phi re-optimised ==")
        print("   w_c    phi400   tau_mix    rms    roast 54 TP")
        c54 = _roast_case("54", T_BEAN_RECORDED["54"], plant["theta"])
        t54 = np.arange(0.0, c54["t_end"] + 0.01, 0.5)
        m54 = np.interp(t54, c54["prof"].t, c54["prof"].bt)
        for w in (0.0, 1.0, 2.0, 2.1, 3.0, 4.0, 5.0, 7.0):
            ph, tm, _, rm = calibrate(plant, c_b, h_fus, free_w_c=False, w_c=w)
            C = C_chamber_from_phi(ph, c_b)
            y = dip(t54, c54["bt_c"], c54["t_bean"], c54["mass"], c54["fn"],
                    plant, phi=phi_of_mass(c54["mass"], c_b, C), phi_ref=ph,
                    c_b=c_b, tau_mix=tm, h_fus=h_fus, w_c=w)
            i_ = int(np.argmin(y))
            print(f"   {w:4.1f}   {ph:.4f}   {tm:6.2f}   {rm:5.3f}    "
                  f"{y[i_]:5.1f} at {t54[i_]:4.1f} s")
        print(f"   measured                                  "
              f"{m54.min():5.1f} at {t54[int(np.argmin(m54))]:4.1f} s")
        print("   w_c = 0 is the old model.  The minimum is real and shallow-"
              "sided, and\n   w_c trades against tau_mix at -0.77 -- they are "
              "not independent, but the\n   profile has one basin and the "
              "residuals are autocorrelated, so read the\n   band 1.5-3 s and "
              "not a fourth decimal (tools/analysis/README.md).")
        print("   The turning point stays 3-5 s late at every w_c: a single "
              "exponential mix\n   cannot be both this deep and turn this "
              "early against this plant card.  It\n   costs under 1.5 degC "
              "because the minimum is flat -- the model and roast 54\n   agree "
              "to 2.3 degC everywhere in the free window -- so it is a phase "
              "defect\n   worth recording and not worth another parameter.")

    if args.scale:
        print("\n== the degeneracy: phi and the charge temperature trade ==")
        alt = {"43": -18.0, "44": -18.0, "46": -18.0, "54": -24.1}
        pa, ta, wa, ra = calibrate(plant, c_b, h_fus,
                                   rids=("43", "44", "46", "54"), t_bean=alt)
        print(f"   A  43/44/46 at an assumed -18, 54 at charge_state.py's "
              f"-24.1:\n      phi400 {pa:.4f}  tau {ta:.2f}  w_c {wa:.2f}  "
              f"rms {ra:.3f}")
        print(f"   B  50/51/53/54 at the entered greens temperatures "
              f"(shipped):\n      phi400 {phi400:.4f}  tau {tau_mix:.2f}  "
              f"w_c {w_c:.2f}  rms {cal_rms:.3f}")
        Ca, Cb = C_chamber_from_phi(pa, c_b), C_ch
        for tb_a, tb_b in ((-24.1, -12.0),):
            da = phi_of_mass(400.0, c_b, Ca) * (129.8 - tb_a)
            db = phi_of_mass(400.0, c_b, Cb) * (129.8 - tb_b)
            print(f"   Both fit.  At roast 54's BT 129.8 they ask for the same "
                  f"dip:\n      A: phi {pa:.3f} x (129.8 - ({tb_a:+.1f})) = "
                  f"{da:.1f} degC     B: phi {phi400:.3f} x "
                  f"(129.8 - ({tb_b:+.1f})) = {db:.1f} degC")
        print("   That is the point: 12 degC of charge temperature and 0.07 of "
              "phi are the\n   same number, and one roast cannot tell them "
              "apart.  B is shipped because\n   its scale is the one "
              "`--greens-temp` is handed.  Fitting A and evaluating\n   at an "
              "entered -12 is what made roast 54's background 6.7 degC shallow.")
        print("   Settling it needs a charge whose core temperature is measured, "
              "not the\n   surface of a bag out of a freezer.")

    if args.fusion:
        print("\n== the fusion enthalpy, and the one disagreement in the set ==")
        print("   h_fus   phi400   tau_mix   w_c    cal rms   per-roast rms "
              + " ".join(f"{r:>5s}" for r in CAL_RIDS))
        for h in (0.0, 7.0, 14.0, 21.0, 28.0, 35.0):
            ph, tm, w, rm = calibrate(plant, c_b, h)
            d = {r["roast"]: r["rms"] for r in
                 check_against_roasts(plant, c_b, h, ph, tm, w, rids=CAL_RIDS)}
            print(f"   {h:5.1f}   {ph:.4f}   {tm:6.2f}  {w:5.2f}   {rm:6.3f}    "
                  + " ".join(f"{d[r]:5.2f}" for r in CAL_RIDS))
        print("   Roast 50 is the whole argument: a +25 degC charge, the only")
        print("   *measured* one in the set, and unfrozen, so h_fus cannot touch")
        print("   its depth -- every J/g raises it as the frozen roasts pull phi")
        print("   down.  Its rms nearly quadruples across the band while the")
        print("   frozen roasts improve by a tenth.  h_fus = 0, which is what the")
        print("   old assumed-temperature group also concluded and the opposite of")
        print("   what the charge-thermal test's still-air fit wants.  The")
        print("   disagreement is real and unresolved; the default follows the roasts.")

    if args.sweep:
        print("\n== the dip against charge temperature, 400 g, inlet held at "
              "the preheat ==")
        print("   Held, not roast 46's measured trace: that trace is the loop")
        print("   railing against the background being replaced, and baking it in")
        print("   is the circularity make_charge_background.py exists to avoid.")
        t = np.arange(0.0, 120.01, 0.5)
        print("   T_bean   BT@theta   dip min   at (s)   BT@60   BT@90")
        for tb_ in (-20.0, -10.0, 0.0, 10.0, 20.0, 30.0):
            y = dip(t, 130.2, tb_, 400.0, lambda _t: 140.4, plant,
                    phi=phi_of_mass(400.0, c_b, C_ch), phi_ref=phi400,
                    c_b=c_b, tau_mix=tau_mix, h_fus=h_fus, w_c=w_c)
            i_ = int(np.argmin(y))
            print(f"   {tb_:+6.1f}   {float(np.interp(plant['theta'], t, y)):8.1f}   "
                  f"{y[i_]:7.1f}   {t[i_]:6.1f}   "
                  f"{float(np.interp(60.0, t, y)):6.1f}   "
                  f"{float(np.interp(90.0, t, y)):6.1f}")
        print("   The spread at +theta is phi*(range of T_bean) by construction.")
        print("   What is *not* by construction is how much of it survives to")
        print("   +60 and +90 s, which is the plant pulling the roast back.")


if __name__ == "__main__":
    main()
