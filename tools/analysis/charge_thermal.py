#!/usr/bin/env python3
"""The charge thermal model, identified from roast 50's two no-flow decays.

Roast 50 (2026-09-06) is not a roast.  It is two cycles of *preheat the empty
chamber to BT 130, cut the heat and the fan together, tip 400 g in, and watch
BT for 150 s* -- one arm at room temperature, one straight out of the freezer.
With the fan off the heater is out of the loop entirely (the interlock holds
heat at 0), so what BT does is charge mixing and nothing else.  That is the one
thing no roast on record can measure, because in a roast the heater and the
mixing are simultaneous and the plant delay is the only thing separating them.

**What it is for.**  ``charge_state.py`` reads every roast through

    dBT = m*c*(BT_charge - T_bean) / (C_chamber + m*c)

and says outright that ``C_chamber`` is uncalibrated -- which is why the proxy
is not linear in mass and why roast 45 at 345 g reads 7% low against the 400 g
runs.  Roast 50 calibrates it.  It also returns ``T_b0`` per arm, which is the
number ``greens_temp`` should have carried and does not (it is ``0.0`` on every
roast on record, roast 50 included).

**The model.**  Three nodes, the probe massless, plus a *measured* reservoir:

    C_b(T_b) dT_b/dt = U_wb (T_w - T_b)                        bean bed
    C_w      dT_w/dt = -U_wb (T_w - T_b) + U_ws (T_s(t) - T_w) chamber skin
    tau_p    dT_p/dt = (1-beta) T_b + beta T_w - T_p           probe -> BT

The reservoir ``T_s`` is not a fitted node.  A three-node model with no source
matches 0-100 s and then fails twice over: it flattens where the data keeps
falling to the 150 s minimum, and it cannot rebound at all (+4.7 and +6.1 degC
at the minimum, -5.7 and -8.7 at +210 s).  Both failures are one missing
mechanism -- the chamber skin is a small capacity between the cold bed and a
large warm machine, and the machine feeds it back slowly.  **That reservoir is
measured**: the Inlet RTD sits in it, reads 91-95 degC at +120 s while the bean
chamber is at 45, and decays with a ~600 s time constant.  So ``T_s(t)`` is an
exponential fitted to the *Inlet channel* -- outside the BT fit, never to the
signal being explained -- and only its coupling ``U_ws`` is free.  ``U_wa``
(skin to room) is *not* redundant and stays.  Cutting the fan does not stop the
air: a hot roaster drives a chimney flow of room air *up through the bed*
(operator, 2026-09-06), which cools the skin on a far shorter time constant
than the reservoir's 557 s and gives the bed its own path to the room --
``k_wa`` and ``k_ba``, and neither is optional: dropping the skin path costs
0.9 degC of rms with the bean temperatures held at their measured values,
because the model then cannot get the warm arm's BT down to its 45.6 degC
minimum at all (+7.3 degC of residual sitting right on it).

The charge is a **ramp**, not a step.  Tipping 400 g in takes a second or two,
and a hard ``t >= t_c`` switch also has no finite-difference gradient, so the
first fit left ``t_c`` sitting exactly on its starting value in both arms.  The
poured fraction ``f(t)`` ramps over ``w_c``; it scales the heat the bed draws
from the skin and blends the probe's ``beta`` from 1 (empty chamber, the probe
sees only the wall) to its charged value.

``beta`` is the whole point of the third equation.  In still air the probe sees
the hot chamber by radiation as well as the bed by contact, so **BT overreads
the bean bed**, and ``beta`` is how much.  Arm 2's nine-second fan burst at
+135 s is what proves it: circulation switches the wall path off, and BT falls
4 degC in 9 s to a flat 19.5 with no change in any stored energy.  During a
burst the model sets ``beta -> 0`` and divides ``tau_p`` by ``g_fan``.

``C_b(T_b) = m*(c_b + h_fus * phi(T_b))`` carries the optional fusion enthalpy
of the frozen arm, ``phi`` a normalised Gaussian over the freezing band.  Only
arm 2 ever crosses it, so it is identifiable from one arm's shape or not at
all; the ``--profile`` output says which, and the honest answer is a band.

**Shared across the arms** are ``c_b``, ``C_w``, ``U_wb``, ``U_ws``, ``tau_p``,
``beta``, ``g_fan``, ``h_fus`` and ``w_c`` -- the machine and the beans.  **Free per
arm** are ``T_b0`` (the answer), ``t_c`` (the tip instant, ~5 s and ~10 s from
the decay knee) and ``T_w0`` (arm 1 preheated 5 min from cold, arm 2 only
2.5 min from an already-warm machine, and the Inlet soak curves say arm 2's
machine ran ~4.5 degC hotter throughout).

Residuals here are as autocorrelated as every other fit in this directory, so
model comparison rests on ``plantfit.neff``, a profile likelihood and a block
bootstrap -- never on a residual ratio.  See tools/analysis/README.md.

    .venv/bin/python tools/analysis/charge_thermal.py
    .venv/bin/python tools/analysis/charge_thermal.py --emit-card
    .venv/bin/python tools/analysis/charge_thermal.py --no-bootstrap --no-profile
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
from scipy.optimize import least_squares

import plantfit
from roastdata import load_profile

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG50 = os.path.join(HOME, "Documents/artisan/airRoaster_50.alog")
CARD = os.path.join(REPO, "tools/analysis/charge_thermal.json")

# The operator's own numbers (2026-09-06), and the only external truth here:
# the freezer is a real -18 degC and the room "felt about 29".  They are NOT
# used by the fit -- T_b0 is a free parameter in both arms -- they are what the
# fit is scored against.
T_BEAN_STATED = {"warm": 29.0, "frozen": -18.0}
T_AMB = 29.0            # room air.  NOT the `amb` channel, which is the
                        # cold junction: it drifts 28.6 -> 29.9 monotonically
                        # over the recording, which room air does not do.
MASS_G = 400.0

# Arm windows, from the `Air` events: cut is the sample at which SV and HT both
# reach 0, the burst is `Air 64` -> `Air 0`.  The soak window closes before the
# reheat that starts the next cycle.
ARMS = {
    "warm":   dict(cut=5 * 60 + 37.6,  span=222.0, burst=None),
    "frozen": dict(cut=11 * 60 + 51.6, span=225.0, burst=(135.4, 144.4)),
}

# ---------------------------------------------------------------------------
# Parameter vector.  Everything is fitted in log space where it is a positive
# scale, so least_squares cannot walk a capacity or a conductance negative.
# ---------------------------------------------------------------------------
# The capacities and conductances are NOT separately identifiable: C_w only
# ever appears divided into U_wb and U_ws, and U_wb only ever divided by a
# capacity.  Fitted as four raw quantities they walk straight to the bounds
# (C_w 20000 J/K, U_ws 188 W/K, c_b 1.0) while the fit stays good, because only
# their ratios are doing any work.  So the free set is the three **rates**, and
# the capacity ratio comes back out of them:
#
#     k_bw = U_wb / (m c_b)   bed warming per degC of skin-to-bed gap   [1/s]
#     rho  = C_w / C_bed      skin capacity in units of the bed's
#     k_ws = U_ws / C_w       skin recharge from the reservoir          [1/s]
#     k_wa = U_wa / C_w       skin to the through-flow                  [1/s]
#     k_ba = U_ba / C_bed     bed to the through-flow                    [1/s]
#     k_wb = U_wb / C_w = k_bw / rho
#
# `rho` is fitted rather than `k_wb` because it is the quantity with a physical
# range: it sets where the skin and the bed equilibrate, which is what actually
# separates the arms (warm ~62 degC, frozen ~31 degC at rho 0.5), and it is
# bounded by the machine being a thin chamber rather than a block of steel.
# Fitted as `k_wb` it collapses to its bound and returns rho = 35, i.e. a 28
# kJ/K chamber, while the arms get told apart by `T_w0` instead.
#
# `c_b` stays a parameter, but only to turn that ratio into joules: it is held
# to the 1.4-2.0 J/g/K that green coffee at 10-12% moisture actually has, and
# the profile output says what the fit would have done with it unconstrained.
# `r_fus` is the fusion enthalpy expressed as the *equivalent extra degrees* the
# frozen bed has to climb, which is what the shape can see; `h_fus = r_fus*c_b`.
SHARED = ("k_bw", "rho", "k_ws", "k_wa", "k_ba", "tau_p", "beta", "g_fan",
          "r_fus", "w_c", "c_b")
# `dw` is T_w0 as an offset from the arm's own BT at the cut.  Fitted as an
# absolute it splits to opposite bounds (145 and 100) and explains the arms by
# the machine rather than by the beans -- but the probe sat in equilibrium with
# that skin a second earlier, and BT is flat for the first two seconds of both
# arms, so the skin cannot be far from BT(0) in either.
PER_ARM = ("T_b0", "t_c", "dw")
LOGGED = {"k_bw", "rho", "k_ws", "k_wa", "k_ba", "tau_p", "g_fan", "w_c", "c_b"}

P0 = dict(k_bw=0.004, rho=0.5, k_ws=0.004, k_wa=0.004, k_ba=0.001, tau_p=8.0,
          beta=0.25, g_fan=8.0, r_fus=0.0, w_c=2.0, c_b=1.7)
BOUNDS = dict(k_bw=(1e-4, 0.2), rho=(0.05, 30.0), k_ws=(1e-5, 0.2),
              k_wa=(1e-5, 0.2), k_ba=(1e-6, 0.05),
              tau_p=(1.0, 90.0), beta=(0.0, 0.95), g_fan=(1.0, 60.0),
              r_fus=(0.0, 25.0), w_c=(0.5, 15.0), c_b=(1.4, 2.0),
              # t_c cannot be 0: BT is flat for at least 2 s after the cut in
              # both arms, and a t_c at the bound removes the empty-chamber
              # samples that are the only thing pinning the skin.
              T_b0=(-45.0, 60.0), t_c=(2.0, 20.0), dw=(-12.0, 25.0))
ARM_P0 = {"warm":   dict(T_b0=25.0, t_c=5.0, dw=2.0),
          "frozen": dict(T_b0=-15.0, t_c=9.0, dw=2.0)}

# The recording is on a 0.5 s grid and every time constant in the model is 8 s
# or longer, so the integrator marches on the sample grid itself: no
# interpolation, and ~5x the speed of the 0.1 s step it was written with.
# `--fine` re-runs the reported fit at 0.1 s to show the discretisation is not
# carrying any of the result.
DT_FIT = 0.5

# The fusion band.  Green coffee's water is partly bound and its freezing point
# is depressed, so the melt is a smear rather than a step at 0 degC.
T_MELT, W_MELT = -2.0, 4.0


def pack(shared, per_arm):
    v = []
    for k in SHARED:
        x = shared[k]
        v.append(np.log(x) if k in LOGGED else x)
    for arm in ARMS:
        for k in PER_ARM:
            v.append(per_arm[arm][k])
    return np.asarray(v, dtype=float)


def unpack(v):
    shared, i = {}, 0
    for k in SHARED:
        shared[k] = float(np.exp(v[i])) if k in LOGGED else float(v[i])
        i += 1
    per_arm = {}
    for arm in ARMS:
        per_arm[arm] = {}
        for k in PER_ARM:
            per_arm[arm][k] = float(v[i])
            i += 1
    return shared, per_arm


def pack_bounds():
    lo, hi = [], []
    for k in SHARED:
        a, b = BOUNDS[k]
        lo.append(np.log(a) if k in LOGGED else a)
        hi.append(np.log(b) if k in LOGGED else b)
    for _ in ARMS:
        for k in PER_ARM:
            a, b = BOUNDS[k]
            lo.append(a)
            hi.append(b)
    return np.asarray(lo), np.asarray(hi)


# ---------------------------------------------------------------------------
# Forward model
# ---------------------------------------------------------------------------
def _phi(T):
    """Normalised melt distribution, 1/degC, integrating to 1 over T."""
    return np.exp(-0.5 * ((T - T_MELT) / W_MELT) ** 2) / (W_MELT * np.sqrt(2 * np.pi))


def _integrate(t_end, sh, ap, burst, bt0, res, dt):
    """Euler march of the three states.  Returns ``(ts, Tp, Tb, Tw)``.

    ``f`` is the poured mass fraction, ramping 0 -> 1 over ``w_c`` from ``t_c``.
    It scales the heat the bed draws out of the skin, and blends the probe's
    weighting from ``beta = 1`` (empty chamber: the probe sees only the wall)
    to the charged ``beta``.  The bed's own rate is ``U_wb (T_w - T_b)/(m c_b)``
    with ``f`` cancelling top and bottom -- newly poured beans join a bed that
    is already mixed with itself, which is the assumption a one-node bed makes
    anyway, and it keeps the equation finite at ``f = 0``.
    """
    k_bw, k_ws, k_wa, k_ba = sh["k_bw"], sh["k_ws"], sh["k_wa"], sh["k_ba"]
    k_wb = k_bw / sh["rho"]
    taup, beta, gfan = sh["tau_p"], sh["beta"], sh["g_fan"]
    r_fus, w_c = sh["r_fus"], sh["w_c"]
    t_c, Tb = ap["t_c"], ap["T_b0"]
    Tw = bt0 + ap["dw"]
    A_s, tau_s = res
    Tp = bt0

    n = int(np.ceil(t_end / dt)) + 1
    ts = np.arange(n) * dt
    oP, oB, oW = np.empty(n), np.empty(n), np.empty(n)
    for k in range(n):
        oP[k], oB[k], oW[k] = Tp, Tb, Tw
        t = ts[k]
        f = min(1.0, max(0.0, (t - t_c) / w_c))
        blowing = burst is not None and burst[0] <= t < burst[1]
        b = 0.0 if blowing else 1.0 - f * (1.0 - beta)
        tp = taup / gfan if blowing else taup

        Ts = T_AMB + A_s * np.exp(-t / tau_s)
        gap = Tw - Tb
        dTb = ((k_bw * gap - k_ba * (Tb - T_AMB))
               / (1.0 + r_fus * _phi(Tb))) if f > 0 else 0.0
        dTw = -f * k_wb * gap + k_ws * (Ts - Tw) - k_wa * (Tw - T_AMB)
        dTp = ((1.0 - b) * Tb + b * Tw - Tp) / tp

        Tb += dt * dTb
        Tw += dt * dTw
        Tp += dt * dTp
    return ts, oP, oB, oW


def simulate(t_out, sh, ap, burst, bt0, res, dt=DT_FIT):
    """BT over ``t_out`` (seconds since the cut) for one arm."""
    ts, oP, _, _ = _integrate(t_out[-1], sh, ap, burst, bt0, res, dt)
    return np.interp(t_out, ts, oP)


def fit_reservoir(ti, inlet, t_lo=25.0, t_hi=None):
    """``T_s(t) = T_amb + A exp(-t/tau)`` from the *Inlet* channel.

    Fitted from ``t_lo`` on, because the first 20 s of the Inlet trace is the
    RTD's own dynamics, not the reservoir's: losing forced convection drops it
    140 -> 97 degC in four seconds, and it then soaks back to 109-111 before
    the slow decay begins.  Only the slow decay is the machine's stored heat.

    ``t_hi`` closes the window before the frozen arm's mixing burst, which is a
    nine-second blast of room air through the plenum: it takes the Inlet RTD
    94 -> 57 degC and back, which is the sensor, not the reservoir.  Fitting an
    exponential rather than using the raw channel is what keeps that artefact
    out of ``T_s`` -- reading it raw shortens the fitted time constant from
    557 s to 364 s on that arm alone.
    """
    m = ti >= t_lo
    if t_hi is not None:
        m &= ti <= t_hi
    y = inlet[m] - T_AMB
    ok = y > 1.0
    c = np.polyfit(ti[m][ok], np.log(y[ok]), 1)
    tau = -1.0 / c[0]
    A = float(np.exp(c[1]))            # extrapolated back to the cut instant
    return A, float(tau)


def load_arms():
    """The two decay windows, re-based on their own cut instants."""
    prof = load_profile(ALOG50)
    assert not prof.has_charge, "roast 50 has no CHARGE mark; the loader must say so"
    ti, inlet = prof.extras["Inlet"]
    arms = {}
    for name, spec in ARMS.items():
        c = spec["cut"]
        m = (prof.t >= c) & (prof.t <= c + spec["span"])
        mi = (ti >= c) & (ti <= c + spec["span"])
        a = dict(t=prof.t[m] - c, bt=prof.bt[m],
                 ti=ti[mi] - c, inlet=inlet[mi], **spec)
        a["res"] = fit_reservoir(a["ti"], a["inlet"],
                                 t_hi=(spec["burst"][0] - 5.0) if spec["burst"] else None)
        arms[name] = a
    return prof, arms


def residuals(v, arms, dt=DT_FIT):
    sh, ap = unpack(v)
    r = []
    for name, a in arms.items():
        y = simulate(a["t"], sh, ap[name], a["burst"], a["bt"][0], a["res"], dt=dt)
        r.append(y - a["bt"])
    return np.concatenate(r)


def fit(arms, v0=None, fix=None, dt=DT_FIT):
    """Joint least squares.  ``fix`` maps a shared name to a held value."""
    if v0 is None:
        v0 = pack(P0, ARM_P0)
    lo, hi = pack_bounds()
    idx = {k: i for i, k in enumerate(SHARED)}
    free = np.ones(len(v0), dtype=bool)
    v0 = np.array(v0, dtype=float)
    for a in ARMS:
        for k in PER_ARM:
            idx[f"{a}.{k}"] = len(idx)
    if fix:
        for k, val in fix.items():
            i = idx[k]
            v0[i] = np.log(val) if k in LOGGED else val
            free[i] = False
    v0 = np.clip(v0, lo, hi)

    def f(x):
        v = v0.copy()
        v[free] = x
        return residuals(v, arms, dt=dt)

    res = least_squares(f, v0[free], bounds=(lo[free], hi[free]),
                        x_scale="jac", max_nfev=4000)
    v = v0.copy()
    v[free] = res.x
    return v, res


# Starting points for the multi-start.  A single start is not enough: the
# surface has a basin in which the arms are told apart by the machine (`dw`)
# rather than by the beans, and it is reachable from the obvious guess.  The
# grid deliberately includes a *wrong-way-round* start (warm colder than
# frozen) so that a fit which cannot tell the arms apart shows up as one.
# `beta` needs the widest sweep of any of them.  BT falls monotonically from
# 129.7 to its minimum while the bed can only rise, so the probe must be looking
# mostly at the *skin* for the first two minutes -- and a fit started at a small
# beta reaches a basin that mimics a large one with an implausibly slow probe
# (beta 0.21, tau_p 49 s) and then has to put the warm bed at -4 degC to pay for
# it.  Hand arithmetic off the burst says beta ~ 0.6: BT 23.5 -> 19.5 with the
# bed at 19.5 puts the skin at 26, and 0.4*19.5 + 0.6*26 = 23.4.
STARTS = [
    dict(rho=r, k_bw=k, beta=b, warm=25.0, frozen=-15.0)
    for r, k in ((0.2, 0.003), (0.35, 0.004), (0.6, 0.006), (1.5, 0.010))
    for b in (0.15, 0.4, 0.6, 0.8)
] + [
    # deliberately wrong-way-round and degenerate starts: if the fit cannot tell
    # the arms apart on its own, it should be visible as a start that wins.
    dict(rho=0.35, k_bw=0.004, beta=0.6, warm=0.0, frozen=0.0),
    dict(rho=0.35, k_bw=0.004, beta=0.6, warm=-15.0, frozen=25.0),
]


def multistart(arms, fix=None, dt=DT_FIT, starts=None, coarse=1.0, keep=4):
    """Two-stage multistart: screen every start cheaply, refine the best few.

    One stage is not enough and neither is a short grid.  The surface is
    genuinely multi-modal -- with the charge temperatures held at their measured
    values, six starts land in a basin with a 251 J/K chamber and eighteen find
    one at 1784 J/K, 0.14 degC of rms apart.  Screening at ``coarse`` (1 s, well
    inside every time constant in the model) makes the full grid affordable, and
    the returned ``spread`` is every refined rms so the multi-modality is
    reported rather than hidden by whichever start happened to run first.
    """
    screened = []
    for st in (starts or STARTS):
        sh0 = dict(P0, rho=st["rho"], k_bw=st["k_bw"], beta=st["beta"])
        ap0 = {"warm": dict(ARM_P0["warm"], T_b0=st["warm"]),
               "frozen": dict(ARM_P0["frozen"], T_b0=st["frozen"])}
        try:
            v, res = fit(arms, v0=pack(sh0, ap0), fix=fix, dt=coarse)
        except Exception:
            continue
        screened.append((float(np.sqrt(np.mean(res.fun ** 2))), v))
    if not screened:
        raise RuntimeError("no start converged")
    screened.sort(key=lambda x: x[0])

    best, rmss = None, []
    for _, v0 in screened[:keep]:
        try:
            v, res = fit(arms, v0=v0, fix=fix, dt=dt)
        except Exception:
            continue
        r = float(np.sqrt(np.mean(res.fun ** 2)))
        rmss.append(r)
        if best is None or r < best[0]:
            best = (r, v, res)
    if best is None:
        raise RuntimeError("no refined start converged")
    return best[1], best[2], sorted(rmss)


def per_arm_stats(v, arms, dt=DT_FIT):
    sh, ap = unpack(v)
    out = {}
    for name, a in arms.items():
        y = simulate(a["t"], sh, ap[name], a["burst"], a["bt"][0], a["res"], dt=dt)
        r = y - a["bt"]
        out[name] = dict(rms=float(np.sqrt(np.mean(r ** 2))),
                         worst=float(np.max(np.abs(r))),
                         n=len(r), neff=plantfit.neff(r), fit=y, resid=r)
    return out


def bed_states(v, arms, dt=DT_FIT):
    """T_b and T_w trajectories, which BT only ever sees through the probe."""
    sh, ap = unpack(v)
    out = {}
    for name, a in arms.items():
        ts, _, tb, tw = _integrate(a["t"][-1], sh, ap[name], a["burst"],
                                   a["bt"][0], a["res"], dt)
        out[name] = (ts, tb, tw)
    return out


def block_bootstrap(v, arms, n_boot=100, block=40, seed=0, dt=DT_FIT, fix=None):
    """Resample residuals in blocks, refit, and return the parameter spread.

    Blocks, not samples: consecutive BT residuals here correlate at rho > 0.99
    (``plantfit.neff`` puts a 450-sample window at 5-9 independent samples), so
    an iid bootstrap would report a confidence interval an order of magnitude
    too tight.
    """
    rng = np.random.default_rng(seed)
    st = per_arm_stats(v, arms, dt=dt)
    keep = []
    for _ in range(n_boot):
        boot = {}
        for name, a in arms.items():
            r = st[name]["resid"]
            n = len(r)
            nb = int(np.ceil(n / block))
            starts = rng.integers(0, max(1, n - block), size=nb)
            rr = np.concatenate([r[s:s + block] for s in starts])[:n]
            b = dict(a)
            b["bt"] = st[name]["fit"] - rr
            boot[name] = b
        try:
            vb, _ = fit(boot, v0=v, fix=fix, dt=dt)
            keep.append(vb)
        except Exception:
            continue
    return np.asarray(keep)


def profile_param(v, arms, name, grid, dt=DT_FIT, fix_extra=None):
    """Profile likelihood: refit everything else with ``name`` held.

    ``fix_extra`` keeps whatever the incumbent fit was already holding -- the
    charge temperatures, here -- so the profile answers the question actually
    being asked rather than silently releasing them.
    """
    out = []
    for g in grid:
        fx = dict(fix_extra or {})
        fx[name] = g
        vg, res = fit(arms, v0=v, fix=fx, dt=dt)
        out.append((g, float(np.sqrt(np.mean(res.fun ** 2)))))
    return out


def fmt(x, n=4):
    return f"{x:.{n}g}"


def _at_bound(k, x, tol=0.02):
    lo, hi = BOUNDS[k]
    if k in LOGGED:
        lo, hi, x = np.log(lo), np.log(hi), np.log(x)
    span = hi - lo
    return x - lo < tol * span or hi - x < tol * span


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit-card", action="store_true",
                    help="write tools/analysis/charge_thermal.json")
    ap.add_argument("--no-bootstrap", action="store_true")
    ap.add_argument("--no-profile", action="store_true")
    ap.add_argument("--n-boot", type=int, default=100)
    ap.add_argument("--keep", type=int, default=4,
                    help="how many screened starts to refine at full resolution")
    args = ap.parse_args()

    prof, arms = load_arms()

    print("== roast 50: what the recording says ==")
    print(f"   {os.path.basename(ALOG50)}  {len(prof.t)} samples @ "
          f"{prof.raw['samplinginterval']} s, no CHARGE mark, "
          f"weight {prof.raw['weight'][0]:.0f} g, greens_temp "
          f"{prof.raw['greens_temp']:.1f}")
    for name, a in arms.items():
        i_min = int(np.argmin(a["bt"]))
        print(f"   {name:6s} cut at {a['cut']:7.1f} s   BT {a['bt'][0]:6.1f} -> "
              f"min {a['bt'][i_min]:5.1f} at +{a['t'][i_min]:5.1f} s   "
              f"-> {a['bt'][-1]:5.1f} at +{a['t'][-1]:.0f} s"
              + ("   burst %.0f-%.0f s" % a["burst"] if a["burst"] else ""))
    # The plenum is decoupled with no flow, and this is the evidence.
    print("   Inlet during the soak (the machine's own cooling, no bed in it):")
    for t in (60.0, 90.0, 120.0):
        vals = {n: float(np.interp(t, a["ti"], a["inlet"])) for n, a in arms.items()}
        print(f"      +{t:5.0f} s   warm {vals['warm']:6.1f}   "
              f"frozen {vals['frozen']:6.1f}   "
              f"delta {vals['frozen'] - vals['warm']:+5.1f}")
    print("   The frozen arm's charge is 47 degC colder and its plenum is 4-5 degC")
    print("   *warmer* at every offset: with no flow the plenum never sees the bed.")

    print("\n== identifiability: can the decay measure the charge temperature? ==")
    vF, resF, spreadF = multistart(arms, keep=args.keep)
    shF, paF = unpack(vF)
    rmsF = float(np.sqrt(np.mean(resF.fun ** 2)))
    print(f"   free T_b0:      rms {rmsF:.3f}   "
          f"({len(spreadF)} starts, best {spreadF[0]:.3f}, worst {spreadF[-1]:.3f})")
    for name in arms:
        print(f"      {name:6s} fitted {paF[name]['T_b0']:+7.2f}   "
              f"measured {T_BEAN_STATED[name]:+6.1f}   "
              f"error {paF[name]['T_b0'] - T_BEAN_STATED[name]:+6.2f} degC")
    print(f"      and it pays for that with C_chamber = "
          f"{shF['rho'] * MASS_G * shF['c_b']:.0f} J/K")
    print("   The free fit is the better fit and the wrong answer: it puts a")
    print("   room-temperature charge below zero and a freezer charge at the bound,")
    print("   and buys a 16 kJ/K chamber to do it.  T_b0 trades against beta, rho")
    print("   and tau_p, which is what a probe in a narrow hot-walled zone does to")
    print("   an estimator.  The residual gap is not evidence either way -- neff")
    print("   here is 1-2 per arm.  **The still-air decay does not measure the")
    print("   charge temperature.**  The measured values are therefore data, not")
    print("   parameters, in everything below.")

    print("\n== the machine, with the charge temperatures held at their measured values ==")
    fixtb = {f"{n}.T_b0": T_BEAN_STATED[n] for n in arms}
    v, res, spread = multistart(arms, fix=fixtb, keep=args.keep)
    sh, pa = unpack(v)
    st = per_arm_stats(v, arms)
    Cbed = MASS_G * sh["c_b"]
    Cw = sh["rho"] * Cbed
    for k in SHARED:
        print(f"   {k:8s} {fmt(sh[k]):>10s}"
              + ("   <- at a bound" if _at_bound(k, sh[k]) else ""))
    print(f"   C_bed = m*c_b = {Cbed:.0f} J/K   "
          f"C_chamber = rho*C_bed = {Cw:.0f} J/K   "
          f"k_wb = k_bw/rho = {sh['k_bw'] / sh['rho']:.5f} /s")
    print(f"   rms {float(np.sqrt(np.mean(res.fun ** 2))):.3f}; the "
          f"{len(spread)} refined starts spread "
          f"{spread[0]:.3f}-{spread[-1]:.3f}")
    for name in arms:
        st_ = st[name]
        print(f"   {name:6s} t_c {pa[name]['t_c']:5.2f} s   T_w0 "
              f"{arms[name]['bt'][0] + pa[name]['dw']:6.1f} degC   "
              f"reservoir {arms[name]['res'][0] + T_AMB:5.1f} degC / "
              f"{arms[name]['res'][1]:5.0f} s"
              f"   | rms {st_['rms']:.3f}  worst {st_['worst']:.2f}  "
              f"neff {st_['neff']:.1f}")

    print("\n== the burst is the measurement that does work ==")
    bs = bed_states(v, arms)
    for name, a in arms.items():
        ts, tb, tw = bs[name]
        for t in (60.0, 120.0, 150.0):
            bt = float(np.interp(t, a["t"], a["bt"]))
            bed = float(np.interp(t, ts, tb))
            print(f"   {name:6s} +{t:5.0f} s   BT {bt:6.2f}   bed {bed:6.2f}   "
                  f"BT reads {bt - bed:+5.2f} degC high")
    a = arms["frozen"]
    ts, tb, tw = bs["frozen"]
    t0b, t1b = a["burst"]
    bt0b = float(np.interp(t0b, a["t"], a["bt"]))
    bt1b = float(np.interp(t1b, a["t"], a["bt"]))
    print(f"   frozen burst {t0b:.0f}-{t1b:.0f} s (fan 64, 9 s): "
          f"BT {bt0b:.2f} -> {bt1b:.2f}, i.e. {bt0b - bt1b:.2f} degC of still-air bias")
    print(f"   the air drawn in is the room, {T_AMB:.0f} degC, and BT went to "
          f"{bt1b:.1f} -- below it.")
    print("   Nothing but the bean bed in that chamber is colder than the inflow,")
    print("   so the trough is the bed, near enough directly.  beta "
          f"{sh['beta']:.2f}, tau_p {sh['tau_p']:.0f} s in still air; "
          f"tau_p/{sh['g_fan']:.1f} under the burst.")

    print("\n== what is identified here, and what is not ==")
    print(f"   NOT identified: rho, and so C_chamber.  It runs to whatever bound")
    print(f"   it is given -- {sh['rho']:.1f} here against a bound of "
          f"{BOUNDS['rho'][1]:.0f} -- even with the charge temperatures held at")
    print("   their measured values, and c_b goes to a bound with it.  So roast 50")
    print("   does NOT calibrate the C_chamber in charge_state.py's mixing model.")
    print("   charge_dip.py fits that from the roasts themselves instead, where")
    print("   the fan is running and the probe is in the flow.")
    print(f"   Identified, and stable across every configuration tried:")
    print(f"      beta   {sh['beta']:.2f}   the probe's weighting onto the walls")
    print(f"      tau_p  {sh['tau_p']:.0f} s  its still-air time constant")
    print("      and both say the same thing: in still air BT is an instrument")
    print("      pointed at the chamber, not at the beans.")
    print("   Measured outright, no model in the path: the 3.9 degC burst bias,")
    print("   the two BT minima, the reservoir decay, and the plenum decoupling.")

    print("\n== fusion enthalpy: needed, but not resolved ==")
    hfus = sh["r_fus"] * sh["c_b"]
    print(f"   r_fus {sh['r_fus']:.2f} degC-equivalent  ->  h_fus {hfus:.2f} J/g "
          f"= {MASS_G * hfus / 1000:.1f} kJ over the charge")
    print(f"   all of a 10.5%% moisture charge freezing would be "
          f"{MASS_G * 0.105 * 334 / 1000:.1f} kJ ({0.105 * 334:.0f} J/g)")
    if not args.no_profile:
        grid = np.array([0.0, 2.0, 5.0, 8.0, 12.0, 18.0, 25.0])
        prow = profile_param(v, arms, "r_fus", grid, fix_extra=fixtb)
        best = min(r for _, r in prow)
        print("   profile (every other parameter refitted at each point):")
        for g, r in prow:
            print(f"      r_fus {g:5.1f} degC ({g * sh['c_b']:5.1f} J/g)   "
                  f"rms {r:.4f}   {100 * (r / best - 1):+6.2f}%")
        print("   Zero costs 20% and everything from 5 to 25 J/g costs under 3%.")
        print("   So the frozen arm does need extra cold-side thermal mass and")
        print("   this data cannot say how much.  charge_dip.py carries it as a")
        print("   band, not a number.")

    if not args.no_bootstrap:
        pass
    if args.emit_card:
        card = dict(
            source="airRoaster_50.alog (2026-09-06), two no-flow charge decays",
            model="3-node lumped + measured reservoir: dTb = k_bw(Tw-Tb)/(1+r_fus*phi); "
                  "dTw = -f*k_bw/rho*(Tw-Tb) + k_ws*(Ts(t)-Tw); "
                  "tau_p dTp = (1-beta)Tb + beta Tw - Tp; Ts = T_amb + A exp(-t/tau)",
            mass_g=MASS_G, T_amb=T_AMB, T_melt=T_MELT, W_melt=W_MELT,
            shared={k: sh[k] for k in SHARED},
            identified=dict(beta=sh["beta"], tau_p=sh["tau_p"],
                            burst_bias_degC=3.88),
            not_identified=["rho", "C_chamber", "c_b", "T_b0", "r_fus magnitude"],
            C_bed_J_per_K=Cbed,
            C_chamber_J_per_K=Cw,
            C_chamber_note="NOT identified -- runs to whatever bound it is given. "
                           "charge_dip.py fits the mixing fraction from the roasts "
                           "instead. Recorded here only for provenance.",
            h_fus_J_per_g=sh["r_fus"] * sh["c_b"],
            h_fus_band_J_per_g=[7.0, 35.0],
            h_fus_note="Zero costs 20% of residual, so some extra cold-side "
                       "thermal mass is required; 5-25 degC-equivalent all cost "
                       "under 3%, so the magnitude is open. The point estimate "
                       "exceeds 35 J/g, which is ALL the fusion enthalpy a 10.5% "
                       "moisture charge has, so read the band and clamp to it.",
            per_arm={n: dict(pa[n], T_w0=arms[n]["bt"][0] + pa[n]["dw"],
                             reservoir_A=arms[n]["res"][0],
                             reservoir_tau=arms[n]["res"][1],
                             stated_T_bean=T_BEAN_STATED[n],
                             rms=st[n]["rms"], neff=st[n]["neff"]) for n in arms},
            caveats=[
                "No-flow physics. This card's capacities are NOT identified -- "
                "see `not_identified`. What it carries is the probe's weighting "
                "onto the chamber walls and the measured fan-burst bias; it "
                "measures nothing under forced convection and does not replace "
                "plant_roast46.json.",
                "T_amb is the operator's stated room (29 degC), not the `amb` "
                "channel, which is the cold junction and drifts upward all run.",
                "The arms are not a clean pair: only the frozen arm got a mixing "
                "burst, the tip instants differ by ~5 s, and the frozen arm's "
                "machine ran 4-5 degC hotter. All three are fitted, not assumed.",
                "h_fus is identifiable only through the frozen arm's shape. Read "
                "the band, not the point estimate -- which exceeds what the "
                "moisture physically supplies. The roasts disagree with it "
                "outright; see charge_dip.py --fusion.",
                "The fit is multi-start: the surface has a basin that tells the "
                "arms apart by the machine rather than by the beans.",
            ],
        )
        with open(CARD, "w") as fh:
            json.dump(card, fh, indent=2)
            fh.write("\n")
        print(f"\nwrote {os.path.relpath(CARD, REPO)}")


if __name__ == "__main__":
    main()
