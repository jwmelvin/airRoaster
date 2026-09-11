#!/usr/bin/env python3
"""Refit the plant from roast 48 -- the first run with deliberate excitation.

Roast 46 is the only earlier roast that identifies a plant at all, and it does so
by accident: a 400 g batch against a 345 g dip drove the commanded inlet rail to
rail in the first two minutes.  Roast 48 does it **on purpose**.  Its schedule
parks the inlet at three flat setpoints and steps between them by -95, +65, -65
and +40 degC at 270/330/435/495 s, with the PID off, so the input is a designed
sequence rather than a control loop chasing its own tail.

It also carries nine fan steps, four of them +-10 units at a dead-flat inlet.
That is what makes this the first data able to say anything about the **plant's**
fan sensitivity -- distinct from `feedforward()`'s, which is about the heat needed
to hold an inlet temperature, and which `roast48_ff.py` settles.  state-current.md
§ Tests A/B/C calls the fan "still a single weakly-identified coefficient"; this
is the run that was supposed to fix that.

What came out of it, so the sections below are read the right way
------------------------------------------------------------------
The fan term is the clean result and the plant card is not.  ``kf`` lands at
**0.000**, tightly: forcing it to the 0.049 that state-history-cascade.md § Correction
once measured (and later retracted for circularity) costs **1.67x** the residual.
So the plant's gain does not depend on the fan over 60-70.

``a`` and ``theta``, on the other hand, are **not stationary over this run**.
Refit on sub-windows they range a 0.0062-0.0085 and theta 7.8-15.5, which is as
wide as their disagreement with roast 46 -- so roast 48 does *not* hand over a
replacement for `plant_roast46.json`, and section 5 says so rather than picking a
winner.  What it does show is **structural**: the two-lag estimator fits the same
data far better with `theta ~ 0` and a 10-25 s first lag, so roast 46's 13.5 s
"deadtime" is at least partly a lag and not a transport delay.

What this module deliberately does NOT do
-----------------------------------------
No PID replay and no closed-loop section: roast 48 ran **open loop**
(`pidOnCHARGE = false`), so there is no outer loop to reproduce.  Compare
`roast46_refit.py` sections 2 and 3, which need one.

And the emitted card's **loss cubic is not a substitute for roast 46's**.  `a`,
`theta` and `kf` are properties of the machine and the bed; `loss(t)` is the
trajectory of one particular roast, and roast 48's is a sacrificial batch held
below first crack by a schedule designed for measurement.  `merge_inlet_base.py`
reads both from one card, so `plant_roast46.json` stays the authoring source
until a real roast is refit.  This card is written beside it, never over it.

Needs numpy and scipy (tools/analysis/README.md).  Usage:

    .venv/bin/python tools/analysis/roast48_plant.py
    .venv/bin/python tools/analysis/roast48_plant.py --emit-plant
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plantfit as pf                                        # noqa: E402
import margins as mg                                         # noqa: E402
from roastdata import load_profile                           # noqa: E402

HOME = os.path.expanduser('~')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, 'Documents/artisan/airRoaster_48.alog')
CARD = os.path.join(REPO, 'tools/analysis/plant_roast48.json')
CARD46 = os.path.join(REPO, 'tools/analysis/plant_roast46.json')

# The inlet series must extend max(thetas) before the window start, and the fit
# must not include the charge mixing transient, which is not the plant
# (state-current.md § Charge temperature: nothing the heater does reaches BT
# before ~14 s).  Roast 48's inlet channel starts at CHARGE-59 s, so 45 s is as
# early as roast 46's convention and still leaves 104 s of lead.
FIT_WINDOW = 45.0
FIT_ORDER = 5        # slow(t) over 705 s; roast 46 used 4 over 385 s
THETAS = np.arange(0.0, 36.01, 0.25)


def ext(v):
    """events_internal_to_external_value (artisanlib/util.py:982-999)."""
    if -1.0 <= v <= 1.0:
        return 0
    return -(int(round(abs(v) * 10)) - 10) if v < -1.0 else int(round(v * 10)) - 10


def fan_series(prof, t):
    """Zero-order hold of the replayed Air events, on the grid `t`."""
    raw = prof.raw
    t0 = raw['timex'][raw['timeindex'][0]]
    ev = sorted((raw['timex'][i] - t0, ext(v))
                for i, ty, v in zip(raw['specialevents'], raw['specialeventstype'],
                                    raw['specialeventsvalue']) if ty == 0)
    xs = np.array([e[0] for e in ev])
    ys = np.array([e[1] for e in ev], dtype=float)
    idx = np.searchsorted(xs, t, side='right') - 1
    return ys[np.clip(idx, 0, len(ys) - 1)]


def section_fit(p, te, ye, hi):
    print('== 1. plant fit, no fan term ==')
    t = np.arange(FIT_WINDOW, hi + 1e-9, 1.0)
    bt = p.bt_at(t)
    f = pf.fit_integral(t, bt, te, ye, order=FIT_ORDER, thetas=THETAS)
    scan = dict((round(x, 2), y) for x, y in f.scan)
    print(f'   primary   {f}')
    print(f'   ridge depth: resid(theta=0)/resid(min) = {scan[0.0] / f.resid_rms:.1f}')
    _, samp = pf.block_bootstrap(t, bt, te, ye, order=FIT_ORDER,
                                 thetas=np.arange(0.0, 36.01, 0.5),
                                 n_boot=200, block=60, seed=7)
    q = lambda x: np.percentile(x, [2.5, 50, 97.5])   # noqa: E731
    print(f'   bootstrap theta 95% {q(samp[:, 0])[0]:.1f}..{q(samp[:, 0])[2]:.1f} s, '
          f'a 95% {q(samp[:, 1])[0]:.5f}..{q(samp[:, 1])[2]:.5f}')
    print('   window x order (theta / a / resid):')
    for lo in (25, 45, 90, 165):
        cells = []
        for order in (4, 5, 6, 7):
            tt = np.arange(lo, hi + 1e-9, 1.0)
            g = pf.fit_integral(tt, p.bt_at(tt), te, ye, order=order, thetas=THETAS)
            cells.append(f'th{g.theta:5.2f} a{g.a:.5f} r{g.resid_rms:.3f}')
        print(f'    ({lo:3d},{hi:.0f}) ' + ' | '.join(cells))
    print('   (lo=165 drops the replayed charge ramp and keeps only the designed steps)')
    return f


def section_fan(p, te, ye, hi, f0):
    print('\n== 2. the fan term in the plant ==')
    print('   a_eff(fan) = a * (1 + kf*(fan-60)); nine replayed fan steps, four of')
    print('   them +-10 units at a dead-flat inlet')
    t = np.arange(FIT_WINDOW, hi + 1e-9, 1.0)
    bt, fan = p.bt_at(t), fan_series(p, t)
    kfs = np.arange(-0.06, 0.0601, 0.002)
    f = pf.fit_integral_fan(t, bt, te, ye, fan, order=FIT_ORDER,
                            thetas=THETAS, kfs=kfs)
    print(f'   best      {f}')
    print(f'   kf = {f.kf:+.4f} per fan unit  ->  {f.kf * 10 * 100:+.1f} % of plant '
          f'gain per 10 fan units')
    print(f'   residual {f.resid_rms:.4f} against {f0.resid_rms:.4f} without the term '
          f'({(1 - f.resid_rms / f0.resid_rms) * 100:+.1f} %)')
    sc = f.scan
    at_best_th = sc[np.abs(sc[:, 0] - f.theta) < 1e-9]
    order = np.argsort(at_best_th[:, 1])
    prof = at_best_th[order]
    within = prof[prof[:, 2] <= f.resid_rms * 1.01]
    print(f'   kf within 1 % of the residual minimum: '
          f'{within[:, 1].min():+.3f} .. {within[:, 1].max():+.3f}')
    print('\n   what a forced kf costs -- state-history-cascade.md § Correction measured')
    print('   ~49 % of plant gain per 10 fan units from roast 45, on a fit later')
    print('   retracted for circularity; this is the bound that replaces it:')
    print(f"      {'kf':>8} {'%gain/10':>9} {'theta':>6} {'a':>9} {'resid':>7} {'x best':>7}")
    for k in (0.0, 0.005, 0.010, 0.020, 0.030, 0.049, -0.010):
        g = pf.fit_integral_fan(t, bt, te, ye, fan, order=FIT_ORDER,
                                thetas=THETAS, kfs=(k,))
        print(f'      {k:+8.4f} {k * 1000:9.1f} {g.theta:6.2f} {g.a:9.5f} '
              f'{g.resid_rms:7.4f} {g.resid_rms / f.resid_rms:7.3f}')
    return f


def section_replay(p, te, ye, hi, f, ffan):
    print('\n== 3. open-loop replay ==')
    t = np.arange(FIT_WINDOW, hi + 1e-9, 1.0)
    for name, g, use_fan in (('no fan term', f, False), ('with fan term', ffan, True)):
        slow, ol = pf.fit_disturbance(t, p.bt_at(t), te, ye, g.a, g.theta,
                                      knot_spacing=8.0)
        sl = lambda x: float(np.interp(x, t, slow))       # noqa: E731
        inlet = lambda x: float(np.interp(x, te, ye))     # noqa: E731
        fanfn = None
        if use_fan:
            fan = fan_series(p, t)
            fanfn = lambda x: float(np.interp(x, t, fan))  # noqa: E731
        ts, sim = pf.replay(t, inlet, float(p.bt_at(t[0])), g.a, g.theta, sl,
                            fan_fn=fanfn, kf=getattr(g, 'kf', 0.0), dt=0.25)
        e = sim - p.bt_at(ts)
        print(f'   {name:14s} spline-disturbance fit {ol:.3f}, forward replay '
              f'mean {e.mean():+.3f} rms {np.sqrt((e ** 2).mean()):.3f} '
              f'max {np.abs(e).max():.2f} degC')


def section_stability(p, te, ye, hi):
    print('\n== 4. is one first-order-plus-deadtime model enough?  no ==')
    print('   the same estimator on sub-windows; if the model were right these')
    print('   would agree, and roast 46 (a .0049 / theta 13.5) would sit among them')
    print(f"   {'window':>13} {'n':>5} {'theta':>6} {'a':>9} {'tau':>6} {'resid':>7}")
    wins = [(45, 300), (45, 430), (165, 450), (300, hi), (450, hi), (45, hi)]
    for lo, whi in wins:
        t = np.arange(lo, whi + 1e-9, 1.0)
        g = pf.fit_integral(t, p.bt_at(t), te, ye, order=4, thetas=THETAS)
        print(f'   {lo:5.0f}-{whi:<6.0f} {len(t):5d} {g.theta:6.2f} {g.a:9.5f} '
              f'{g.tau:6.0f} {g.resid_rms:7.4f}')
    print('   45-300 is under-excited -- one inlet step, at its very end -- and is')
    print('   the outlier; the rest still spread a 0.0062-0.0085, theta 7.8-15.5.')

    print('\n   two lags instead of a deadtime: Inlet -> 1/(1+tau2 s) -> a/(s+a) -> BT')
    print(f"   {'window':>13} {'theta':>6} {'tau2':>6} {'a':>9} {'tau1':>6} {'resid':>7}")
    for lo, whi in wins:
        t = np.arange(lo, whi + 1e-9, 1.0)
        g = pf.fit_integral_2lag(t, p.bt_at(t), te, ye, order=4,
                                 thetas=np.arange(0.0, 31.01, 0.5),
                                 tau2s=np.arange(0.0, 121.0, 5.0))
        print(f'   {lo:5.0f}-{whi:<6.0f} {g.theta:6.1f} '
              f'{getattr(g, "tau2", float("nan")):6.1f} {g.a:9.5f} {g.tau:6.0f} '
              f'{g.resid_rms:7.4f}')
    print('   theta collapses to ~0 with a 10-25 s lag in its place, and the residual')
    print('   drops by a third on every well-excited window.  The 13.5 s "deadtime"')
    print('   carried since roast 46 is at least partly a lag.')


def section_margins(f):
    print('\n== 5. phase margin against BOTH plants (Kp 3.0) ==')
    print('   read this as a caution, not a retune. Roast 45 measured a 177 s ring at')
    print("   Ki 0.10; roast 46's plant predicts 190 s there and roast 48's 135 s, so")
    print('   the one closed-loop behaviour on record favours the roast 46 card.')
    try:
        with open(CARD46, encoding='utf-8') as fh:
            c = json.load(fh)
        a46, th46 = c['a'], c['theta']
    except OSError:
        a46 = th46 = None
    print(f"   {'Ki':>5} {'PM r48':>8} {'T r48':>7}"
          + (f" {'PM r46':>8} {'T r46':>7}" if a46 else ''))
    for Ki in (0.05, 0.07, 0.10, 0.15):
        _, pm, T = mg.margins(f.a, f.theta, 3.0, Ki)
        row = f'   {Ki:5.2f} {pm:8.1f} {T:7.0f}'
        if a46:
            _, pm46, T46 = mg.margins(a46, th46, 3.0, Ki)
            row += f' {pm46:8.1f} {T46:7.0f}'
        print(row)


def compare46(f, ffan):
    print('\n== 6. against roast 46 ==')
    try:
        with open(CARD46, encoding='utf-8') as fh:
            c = json.load(fh)
    except OSError:
        print('   plant_roast46.json unavailable')
        return None
    print(f"   roast 46 (accidental doublet, 400 g): a {c['a']:.5f}  theta "
          f"{c['theta']:.1f}  tau {c['tau']:.0f}  resid {c['resid_rms']:.4f}")
    print(f'   roast 48 (designed steps,  400 g): a {f.a:.5f}  theta {f.theta:.2f}  '
          f'tau {f.tau:.0f}  resid {f.resid_rms:.4f}')
    print(f"   ratio a {f.a / c['a']:.2f}x, theta {f.theta - c['theta']:+.1f} s")
    print('   That gap is real but it is NOT a supersede: section 4 shows roast 48\'s')
    print('   own sub-windows spread nearly as far. Roast 46 is a real roast to BT')
    print('   200+, closed-loop, frozen charge; roast 48 is a warm sacrificial batch')
    print('   held under 185 by a schedule that parks the inlet far above BT for')
    print('   minutes at a time. Neither is wrong about the roaster it measured.')
    print('   plant_roast46.json stays the authoring source. What roast 48 settles')
    print('   is kf, and what it questions is the deadtime.')
    return c


def emit(p, f, ffan, hi, path, loss_order=3):
    t = np.arange(FIT_WINDOW, hi + 1e-9, 1.0)
    slow, _ = pf.fit_disturbance(t, p.bt_at(t), te_ye[0], te_ye[1], f.a, f.theta,
                                 knot_spacing=8.0)
    poly = np.polyfit(t, slow, loss_order)
    resid = float(np.sqrt(np.mean((np.polyval(poly, t) - slow) ** 2)))
    card = {
        '_comment': 'Plant card from roast 48. Generated by '
                    'tools/analysis/roast48_plant.py --emit-plant.',
        'generated': _dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'source': os.path.basename(ALOG),
        'load_g': 400.0,
        'model': 'dBT/dt = a * (1 + kf*(fan-60)) * (Inlet(t - theta) - BT) + loss(t)',
        'a': f.a, 'theta': f.theta, 'tau': f.tau,
        'kf': ffan.kf, 'a_with_fan_term': ffan.a, 'theta_with_fan_term': ffan.theta,
        'loss_poly': list(poly),
        'loss_poly_note': 'numpy.polyval order, highest power first; t in seconds '
                          'since CHARGE',
        'loss_window': [FIT_WINDOW, hi],
        'fit_window': [FIT_WINDOW, hi],
        'fit_order': FIT_ORDER,
        'resid_rms': f.resid_rms,
        'resid_rms_with_fan_term': ffan.resid_rms,
        'loss_poly_resid_rms': resid,
        'supersedes_plant_roast46': False,
        'note': 'DO NOT point merge_inlet_base.py at this card. Only kf is settled '
                'here (0.000; forcing the retracted 0.049 costs 1.67x the '
                'residual), and it says the plant gain does not depend on the fan '
                'over 60-70. a and theta are NOT stationary over this run -- '
                'sub-window refits spread a 0.0062-0.0085 and theta 7.8-15.5, as '
                'wide as the gap to roast 46 -- and the two-lag estimator fits the '
                'same data better with theta ~ 0 and a 10-25 s lag, so the 13.5 s '
                'deadtime is at least partly a lag. loss_poly is a sacrificial '
                "batch's trajectory, not a roast's. plant_roast46.json remains the "
                'authoring source.',
    }
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(card, fh, indent=2)
        fh.write('\n')
    print(f'\nwritten {path}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--alog', default=ALOG)
    ap.add_argument('--emit-plant', action='store_true')
    args = ap.parse_args()

    prof = load_profile(args.alog)
    te_ye = prof.extras['Inlet']
    drop = prof.marks['DROP']
    print(f'roast 48: CHARGE_BT {prof.bt_at(0.0):.1f}, DROP {drop:.0f} s at BT '
          f'{prof.bt_at(drop):.1f}, fit window {FIT_WINDOW:.0f}-{drop:.0f} s\n')
    fit = section_fit(prof, te_ye[0], te_ye[1], drop)
    fitfan = section_fan(prof, te_ye[0], te_ye[1], drop, fit)
    section_replay(prof, te_ye[0], te_ye[1], drop, fit, fitfan)
    section_stability(prof, te_ye[0], te_ye[1], drop)
    section_margins(fit)
    compare46(fit, fitfan)
    if args.emit_plant:
        emit(prof, fit, fitfan, drop, CARD)
