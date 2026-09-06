#!/usr/bin/env python3
"""Is the `Inlet -> BT` path a deadtime or a lag?  Roasts 46, 48 and 49.

`plant_roast46.json` carries **theta = 13.5 s of pure transport delay** and is
the authoring source for `tools/merge_inlet_base.py`.  Roast 48's refit
(`roast48_plant.py` section 4) then found that `plantfit.fit_integral_2lag` fits
the same windows with `theta` collapsing to ~0 and a 10-25 s first lag in its
place, taking about a third off the residual on every well-excited window.
Nobody followed that up, and it matters twice over:

* a lag and a delay of the same size cost very different phase margin -- a lag
  contributes `-arctan(w*tau2)`, bounded at 90 deg, a delay `-w*theta`, unbounded;
* step 9's base schedule is `ff(t) = bg(t+theta) + (dbg/dt - loss)/a`, and the
  **lead term is built directly on whichever structure is right**.

This module settles it from the data in hand.  No roast is needed and none is
proposed.

The shape of the answer
-----------------------
1. **Roast 49 cannot contribute, and section 1 is the check that says so.**  It
   is closed-loop with one large SV step at 1:30; its independent inlet motion
   measures 5.1 degC rms against roast 48's 23.7, and on the tau2 grid
   `roast48_plant.py` itself uses (0-120 s) its two-lag fit runs away to the grid
   edge at tau2 = 100 s with a **negative gain**.  Its sub-window `a` then spans
   a factor of 3.  It is reported and set aside.
2. **The residual cannot settle it, and section 4 says why.**  On roast 48 the
   residual is dominated by structured model error, not noise: at rho > 0.99 the
   AR(1) effective sample size of a 300-450 sample window is 5-9, so no residual
   reduction of any size clears an honest F-test.  Residual ratios are reported
   because the question was asked in those terms, not because they decide it.
3. **What decides it is identifiability, and the two roasts answer differently
   for a physical reason.**  On roast 48 the `(theta, tau2)` minimum is a *point*
   -- the 1%-of-minimum contour is one or two grid cells, `theta` sits hard at 0
   and bootstraps to 0..2 s, and pure deadtime costs **42-131%** more residual.
   On roast 46 it is a *ridge*: only the **sum** `theta + tau2` is determined
   (a 1-2 s band at 13-14 s), pure deadtime and pure lag both land within 1-10%
   of the mixed optimum, and *which of the two is better flips with the window*.
   That is not a contradiction.  Roast 48 steps the inlet by -95/+65/-65/+40 degC,
   and a step is the only excitation that separates the two -- a delay holds the
   output flat and then moves it, a lag moves it immediately and slowly.  Roast
   46's excitation is the smooth closed-loop charge recovery, whose content sits
   far below the corner where `exp(-theta s)` and `1/(1+theta s)` part company.
4. **The quantity identified everywhere is the sum.**  `theta + tau2` bootstraps
   to 9-11, 13-15 and 12-14 s on the three well-excited windows, and the
   single-lag `theta` the deadtime fits report (8.5-13.5 s) *is* that sum.  The
   13.5 s in `plant_roast46.json` was never 13.5 s of transport; it is 13.5 s of
   total apparent lag with the split unresolved, and the roaster's real transport
   delay is small.
5. **What the two-lag structure fixes is `theta`, and what it makes worse is
   `a`.**  Across roast 48's sub-windows `theta` goes from 7.8-14.5 s to a flat
   0-1 s -- the non-stationarity state-history.md § Roast 48 recorded is a
   *structural artefact* -- but `a` spreads 0.0074-0.0142 under two lags against
   0.0062-0.0085 under one, because a late window can now buy a slow response
   with a long lag and a large gain.  Better structure, not a finished plant.
6. **The tuning does not move, and section 6b is the strongest form of that.**
   Walking roast 46's entire ridge from all-delay to all-lag moves the phase
   margin at Kp 3.0 / Ki 0.07 by 33 -> 38 deg.  `pidKi 0.07` stands under either
   structure and nothing here argues for changing it.
7. **The one closed-loop measurement on record prefers the mixed answer.**  Roast
   45 rang at 177 s at Ki 0.10.  Roast 46's two-lag card predicts 173 s, its
   single-lag card 194 s, and roast 48's cards 143-152 s.  The ridge walk shows
   the period sweeping 156 -> 196 s across the split, so the ring *is* informative
   where the open-loop residual is not, and it picks out the middle of the ridge,
   within 1% of where roast 46's own residual minimum already sits.
8. **The `bg(t+theta)` lead is not wrong** (section 7), for a reason worth
   writing down: advancing the background by `theta` and adding `tau2*d/dt` are
   the same operation to first order on a constant-slope ramp, and roast 46's
   own two-lag fit puts `theta + tau2 = 13` against the single-lag 13.5.  Rebuilt
   properly under the two-lag inversion the profile_003 base schedule differs by
   **rms 0.84 degC over the ramp**, against a ~0.5 degC quantisation floor.  So
   `plant_roast46.json` and `merge_inlet_base.py` both stand; what changes is the
   claim attached to the number.
9. **`charge_state.py` is unaffected too** (section 8).  Its proxy assumes the
   heater is fully blocked over `0 .. theta`; under two lags it is not, but the
   difference is 0.19-0.24 degC/100 g across four roasts -- a spread of 0.05
   against the 3.3 degC/100 g gap the proxy is used to measure.  Common-mode.

Needs numpy and scipy (tools/analysis/README.md).  Usage:

    .venv/bin/python tools/analysis/deadtime_vs_lag.py
    .venv/bin/python tools/analysis/deadtime_vs_lag.py --only margins
    .venv/bin/python tools/analysis/deadtime_vs_lag.py --no-bootstrap   # ~70 s faster
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plantfit as pf                                        # noqa: E402
import margins as mg                                         # noqa: E402
from roastdata import load_profile                           # noqa: E402

# Section 7 rebuilds the step-9 base schedule, so it borrows the authoring tool's
# own pieces rather than re-deriving them: `decay_smooth` is the Follow-Background
# decay average the schedule must invert, and leaving it out moves the dip by
# ~14 degC.  merge_inlet_base.py is stdlib-only, so importing it costs nothing.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from merge_inlet_base import decay_smooth                    # noqa: E402

HOME = os.path.expanduser('~')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, 'Documents/artisan/airRoaster_%d.alog')
PROFILE_003 = os.path.join(REPO, 'artisan/profile_003.alog')
CARD46 = os.path.join(REPO, 'tools/analysis/plant_roast46.json')

# Grids.  The single-lag scan matches roast46_refit.py and roast48_plant.py
# exactly.  The two-lag grid is finer than roast48_plant.py's (tau2 step 5), so
# its residuals come out slightly *below* the figures quoted in
# state-history.md § Roast 48; the structure of the answer is unchanged.
THETAS = np.arange(0.0, 36.01, 0.25)
THETAS2 = np.arange(0.0, 31.01, 0.5)
TAU2S = np.arange(0.0, 61.01, 0.5)
ORDER = 4                 # the disturbance order both existing drivers compare at

# Coarser, for the bootstrap only: 200 refits of a 2-D grid, and the question
# there is how far the minimum moves, not where it is.
BOOT_THETAS = np.arange(0.0, 21.01, 1.0)
BOOT_TAU2S = np.arange(0.0, 41.01, 1.0)

# Windows.  Roast 48's are roast48_plant.py section 4's, unchanged.  Roast 46's
# are roast46_refit.py's window sweep at its fitted order.  Roast 49's mirror
# both: one spanning the charge recovery, then progressively later starts.
WINDOWS = {
    46: [(25, None), (45, None), (60, None), (90, None)],
    48: [(45, 300), (45, 430), (165, 450), (300, None), (450, None), (45, None)],
    49: [(45, 300), (45, None), (100, None), (165, None), (200, None)],
}
PRIMARY = {46: (45, None), 48: (45, None), 49: (45, None)}


def load(n):
    p = load_profile(ALOG % n)
    te, ye = p.extras['Inlet']
    return p, te, ye


def win(p, w):
    lo, hi = w
    hi = p.marks['DROP'] if hi is None else float(hi)
    return np.arange(float(lo), hi + 1e-9, 1.0)


def fits(p, te, ye, t, thetas=THETAS, thetas2=THETAS2, tau2s=TAU2S):
    bt = p.bt_at(t)
    f1 = pf.fit_integral(t, bt, te, ye, order=ORDER, thetas=thetas)
    f2 = pf.fit_integral_2lag(t, bt, te, ye, order=ORDER, thetas=thetas2,
                              tau2s=tau2s)
    return f1, f2


# --------------------------------------------------------------------------
def section_excitation(profiles):
    print('== 1. can each roast support the fit at all? ==')
    print('   "independent motion" is the inlet with an order-5 polynomial in t')
    print('   removed: what is left after the slow trajectory both channels share.')
    print('   A delay and a lag differ only above the corner ~1/theta, so the')
    print('   question is whether the input moved fast, not whether it moved far.')
    print(f"   {'roast':>6} {'window':>11} {'inlet range':>13} {'indep rms':>10} "
          f"{'ridge':>6} {'a (1lag)':>9} {'a (2lag)':>9} "
          f"{'tau2 wide':>8} {'a wide':>9}")
    for n, (p, te, ye) in profiles.items():
        t = win(p, PRIMARY[n])
        inlet = p.extra_at('Inlet', t)
        res = inlet - np.polyval(np.polyfit(t, inlet, 5), t)
        f1, f2 = fits(p, te, ye, t)
        scan = dict((round(x, 2), y) for x, y in f1.scan)
        # roast48_plant.py scans tau2 to 120 s; this is what that grid returns.
        wide = pf.fit_integral_2lag(t, p.bt_at(t), te, ye, order=ORDER,
                                    thetas=THETAS2, tau2s=np.arange(0.0, 121.0, 5.0))
        print(f'   {n:6d} {t[0]:5.0f}-{t[-1]:<5.0f} '
              f'{np.nanmin(inlet):6.0f}..{np.nanmax(inlet):<5.0f} '
              f'{res.std():10.2f} {scan[0.0] / f1.resid_rms:6.2f} '
              f'{f1.a:9.5f} {f2.a:9.5f} {wide.tau2:8.0f} {wide.a:9.5f}')
    print('   ridge = resid(theta=0)/resid(min) on the single-lag delay scan: how')
    print('   much the data prefer *some* delay over none.  The last two columns')
    print("   repeat the two-lag fit on roast48_plant.py's own tau2 grid (0-120 s)")
    print('   instead of this file\'s 0-60 s, as a runaway check.')
    print()
    print('   Roast 49 fails every column that matters.  Its independent motion is')
    print("   below roast 46's and a quarter of roast 48's; on the wider tau2 grid")
    print('   its fit runs away to the edge, tau2 = 100 s with a **negative gain**,')
    print('   which is not a plant -- it only looks sane because this file truncates')
    print('   the grid at 60 s.  Its sub-window gain then spreads 0.0076-0.0250')
    print('   (section 5), a factor of 3, and on 200-423 its delay-scan ridge depth')
    print('   is 1.04, meaning no delay at all fits as well as the best one.  It is')
    print('   closed-loop with a single 1:30 step, and one step inside a controller')
    print('   that is correcting for it is not excitation.  **Roast 49 is excluded')
    print('   from every conclusion below**, which is the answer to "check before')
    print('   trusting it".')


def section_headline(profiles):
    print('\n== 2. single lag against two lags, primary windows ==')
    print('   dBT/dt = a*(Inlet(t-theta) - BT) + loss(t)                    [1 lag]')
    print('   Inlet -> delay theta -> 1/(1+tau2 s) -> a/(s+a) -> BT         [2 lag]')
    print(f"   {'roast':>6} {'window':>11} {'n':>5} || {'theta':>6} {'a':>9} "
          f"{'resid':>7} || {'theta':>6} {'tau2':>6} {'a':>9} {'resid':>7} "
          f"{'ratio':>6} {'sum':>5}")
    for n, (p, te, ye) in profiles.items():
        t = win(p, PRIMARY[n])
        f1, f2 = fits(p, te, ye, t)
        print(f'   {n:6d} {t[0]:5.0f}-{t[-1]:<5.0f} {len(t):5d} || '
              f'{f1.theta:6.2f} {f1.a:9.5f} {f1.resid_rms:7.4f} || '
              f'{f2.theta:6.1f} {f2.tau2:6.1f} {f2.a:9.5f} {f2.resid_rms:7.4f} '
              f'{f2.resid_rms / f1.resid_rms:6.3f} '
              f'{f2.theta + f2.tau2:5.1f}')
    print('   "sum" is theta + tau2, the total apparent lag.  Note that it lands')
    print("   on the single-lag theta beside it -- which is the whole finding: the")
    print('   two structures agree about how much lag there is and disagree only')
    print('   about what kind.')


def section_identifiability(profiles):
    print('\n== 3. is (theta, tau2) identifiable, or is it a ridge? ==')
    print('   contour of the residual surface at 1% and 5% above its minimum, and')
    print('   what the two degenerate slices cost: tau2=0 is pure deadtime, theta=0')
    print('   is pure lag.')
    for n, wins in ((48, [(45, 430), (165, 450), (300, 750)]),
                    (46, [(45, None), (60, None)])):
        p, te, ye = profiles[n]
        for w in wins:
            t = win(p, w)
            _, f2 = fits(p, te, ye, t)
            sc = f2.scan
            b1 = sc[sc[:, 2] <= f2.resid_rms * 1.01]
            b5 = sc[sc[:, 2] <= f2.resid_rms * 1.05]
            pure_d = sc[sc[:, 1] == 0.0]
            pure_l = sc[sc[:, 0] == 0.0]
            rd = pure_d[:, 2].min()
            rl = pure_l[:, 2].min()
            print(f'   roast {n} {t[0]:.0f}-{t[-1]:.0f}: min at theta {f2.theta:.1f}'
                  f' / tau2 {f2.tau2:.1f}, resid {f2.resid_rms:.4f}')
            print(f'      1% band  theta {b1[:, 0].min():4.1f}..{b1[:, 0].max():<4.1f}'
                  f' tau2 {b1[:, 1].min():4.1f}..{b1[:, 1].max():<4.1f}'
                  f' sum {(b1[:, 0] + b1[:, 1]).min():4.1f}..'
                  f'{(b1[:, 0] + b1[:, 1]).max():<4.1f}')
            print(f'      5% band  theta {b5[:, 0].min():4.1f}..{b5[:, 0].max():<4.1f}'
                  f' tau2 {b5[:, 1].min():4.1f}..{b5[:, 1].max():<4.1f}'
                  f' sum {(b5[:, 0] + b5[:, 1]).min():4.1f}..'
                  f'{(b5[:, 0] + b5[:, 1]).max():<4.1f}')
            print(f'      pure deadtime (tau2=0) {rd:.4f} = {rd / f2.resid_rms:.3f}x'
                  f'   |   pure lag (theta=0) {rl:.4f} = {rl / f2.resid_rms:.3f}x')
    print()
    print('   Roast 48: the 1% band is one or two grid cells wide, theta sits hard')
    print('   at 0, and pure deadtime costs 42-131% more residual.  The split is')
    print('   identified there, and it is all lag.')
    print('   Roast 46: the **sum** is pinned to a 1-2 s band while theta and tau2')
    print('   each range over 6-13 s, and pure deadtime and pure lag both land')
    print('   within 1-10% of the mixed optimum -- with *which of the two is better')
    print('   flipping between windows* (45-429 slightly prefers pure lag, 60-429')
    print('   slightly prefers pure deadtime).  That is a ridge in (theta, tau2)')
    print("   along theta + tau2 = const, and roast 46's own data cannot say which")
    print('   end of it they are on.  The physical reason is in the module docstring:')
    print('   a step separates a delay from a lag and a smooth ramp does not, and')
    print('   roast 48 has four inlet steps of -95 to +65 degC while roast 46 has the')
    print('   charge recovery.')


def section_significance(profiles):
    print('\n== 4. does the extra parameter earn itself?  the F-test cannot say ==')
    print('   Consecutive BT residuals here are correlated at rho > 0.99, so the')
    print('   AR(1) effective sample size is a tiny fraction of n and the F-test')
    print('   against one extra parameter has almost no degrees of freedom left.')
    print('   This is reported to close the question, not to answer it: the')
    print('   residual is structured model error, not noise, and a test that')
    print('   assumes independent noise is the wrong instrument.')
    from scipy.stats import f as fdist
    print(f"   {'roast':>6} {'window':>11} {'n':>5} {'neff':>6} {'resid 1':>8} "
          f"{'resid 2':>8} {'ratio':>6} {'F':>6} {'p':>7}")
    rows = [(48, (45, 430)), (48, (165, 450)), (48, (300, 750)),
            (48, (450, 750)), (46, (45, None)), (46, (60, None))]
    for n, w in rows:
        p, te, ye = profiles[n]
        t = win(p, w)
        f1, f2 = fits(p, te, ye, t)
        d = pf._delayed(t, f1.theta, te, ye) - p.bt_at(t)
        U = np.concatenate([[0.0], np.cumsum(0.5 * (d[1:] + d[:-1]))])
        X = np.column_stack([U, pf._cheb_basis(t, ORDER + 1)])
        r1 = p.bt_at(t) - X @ np.concatenate([[f1.a], f1.coeffs])
        ne, k = pf.neff(r1), X.shape[1]
        dof = max(ne - k - 1.0, 1.0)
        S1, S2 = len(t) * f1.resid_rms ** 2, len(t) * f2.resid_rms ** 2
        F = ((S1 - S2) / 1.0) / (S2 / dof)
        print(f'   {n:6d} {t[0]:5.0f}-{t[-1]:<5.0f} {len(t):5d} {ne:6.0f} '
              f'{f1.resid_rms:8.4f} {f2.resid_rms:8.4f} '
              f'{f2.resid_rms / f1.resid_rms:6.3f} {F:6.1f} '
              f'{1 - fdist.cdf(F, 1, dof):7.4f}')
    print('   Read the residual column as "the two-lag structure leaves a smaller')
    print('   and less structured error", which is true and useful, and not as')
    print('   "the improvement is significant", which roast 48 cannot support.')
    print('   Roast 46 is the interesting contrast: its residuals are far less')
    print('   correlated (neff 120-141 against 5-9), so there the test does have')
    print('   power -- and it splits.  45-429 improves by 9% and clears easily;')
    print('   60-429 improves by 1% and does not.  Which is the ridge again: on')
    print('   roast 46 the two-lag structure buys almost nothing once the last of')
    print('   the charge recovery leaves the window, because what is left is a')
    print('   smooth ramp that cannot tell a lag from a delay.')


def section_stationarity(profiles, bootstrap=True):
    print('\n== 5. stationarity across sub-windows, and the bootstrap ==')
    print('   The single-lag theta was NOT stationary on roast 48 (7.8-14.5 s over')
    print('   its own sub-windows).  Does the two-lag structure fix that?')
    for n in (48, 46, 49):
        p, te, ye = profiles[n]
        print(f'\n   roast {n}:')
        print(f"      {'window':>12} {'n':>5} | {'theta':>6} {'a':>9} {'resid':>7}"
              f" | {'theta':>6} {'tau2':>6} {'sum':>5} {'a':>9} {'resid':>7}")
        for w in WINDOWS[n]:
            t = win(p, w)
            f1, f2 = fits(p, te, ye, t)
            print(f'      {t[0]:5.0f}-{t[-1]:<6.0f} {len(t):5d} | '
                  f'{f1.theta:6.2f} {f1.a:9.5f} {f1.resid_rms:7.4f} | '
                  f'{f2.theta:6.1f} {f2.tau2:6.1f} {f2.theta + f2.tau2:5.1f} '
                  f'{f2.a:9.5f} {f2.resid_rms:7.4f}')
    print('\n   Roast 48: theta goes from spreading 7.8-14.5 s over its excited')
    print('   sub-windows to sitting at 0.0-1.0 s on every one of them -- that IS')
    print('   stationary, and it is the strongest thing the two-lag structure has')
    print('   going for it: the non-stationarity state-history.md § Roast 48')
    print('   recorded was a structural artefact, not a moving roaster.  (45-300')
    print('   holds one inlet step, at its very end, and returns tau2 = 0 with the')
    print('   same degenerate a = 0.0025 the single-lag fit gives it; it is the')
    print('   under-excited outlier under both structures, exactly as before.)')
    print('   What does NOT settle down is `a`, and it settles down *less*: 0.0074 to')
    print('   0.0142 under two lags against 0.0062 to 0.0085 under one, over the')
    print('   excited windows.  tau2 tracks it, 9 to 26 s.  So this is a better')
    print('   structure, not a finished plant -- the gain still depends on which part')
    print('   of the run you look at, and the two-lag fit makes that worse rather')
    print('   than better, because it lets the late windows explain a slow response')
    print('   with a long lag and a large gain instead of a small gain.')
    print('   Roast 46 shows the ridge as motion: 45-429 reads (5.0, 8.0) and 60-429')
    print('   reads (9.5, 4.5) for a residual difference of 0.7%, with the *sum*')
    print('   steady at 13.0-14.0 across both.  Roast 49 is not identified at all.')

    if not bootstrap:
        print('\n   (--no-bootstrap: block bootstrap skipped)')
        return
    print('\n   Moving-block bootstrap, 200 resamples, 60 s blocks, coarse grid:')
    print(f"      {'roast':>6} {'window':>11} {'theta 95%':>14} {'tau2 95%':>14} "
          f"{'sum 95%':>12} {'a 95%':>19}")
    q = lambda x: np.percentile(x, [2.5, 97.5])          # noqa: E731
    for n, w in ((48, (165, 450)), (48, (300, 750)), (46, (45, None))):
        p, te, ye = profiles[n]
        t = win(p, w)
        _, s = pf.block_bootstrap_2lag(t, p.bt_at(t), te, ye, order=ORDER,
                                       thetas=BOOT_THETAS, tau2s=BOOT_TAU2S,
                                       n_boot=200, block=60, seed=7)
        th, ta = q(s[:, 0]), q(s[:, 1])
        sm, aa = q(s[:, 0] + s[:, 1]), q(s[:, 2])
        print(f'      {n:6d} {t[0]:5.0f}-{t[-1]:<5.0f} '
              f'{th[0]:6.1f}..{th[1]:<6.1f} {ta[0]:6.1f}..{ta[1]:<6.1f} '
              f'{sm[0]:5.1f}..{sm[1]:<5.1f} {aa[0]:8.5f}..{aa[1]:<8.5f}')
    print('   Roast 48 bounds theta at 0-2 s: the 8.5 s of its own single-lag fit is')
    print("   outside the interval.  Roast 46 bounds it at 2-9 s, so roast 46's own")
    print('   data also reject 13.5 s of pure transport -- they simply cannot say')
    print('   how much of the 13 s is delay.  The **sum** is what both agree on.')


def section_margins(profiles):
    print('\n== 6. what it does to the margin arithmetic (Kp 3.0) ==')
    try:
        with open(CARD46, encoding='utf-8') as fh:
            c46 = json.load(fh)
    except OSError:
        c46 = None

    cards = []
    for n in (46, 48):
        p, te, ye = profiles[n]
        t = win(p, PRIMARY[n])
        f1, f2 = fits(p, te, ye, t)
        a1, th1 = (c46['a'], c46['theta']) if (n == 46 and c46) else (f1.a, f1.theta)
        cards.append((f'roast {n} 1 lag', a1, th1, 0.0))
        cards.append((f'roast {n} 2 lag', f2.a, f2.theta, f2.tau2))
    print('   phase margin, degrees:')
    print(f"   {'card':<14} {'a':>8} {'th':>5} {'tau2':>5}  "
          + ' '.join(f'{k:>9}' for k in ('Ki 0.05', 'Ki 0.07', 'Ki 0.10', 'Ki 0.15')))
    for name, a, th, tau2 in cards:
        cells = [f'{mg.margins(a, th, 3.0, Ki, tau2=tau2)[1]:9.1f}'
                 for Ki in (0.05, 0.07, 0.10, 0.15)]
        print(f'   {name:<14} {a:8.5f} {th:5.1f} {tau2:5.1f}  ' + ' '.join(cells))
    print('\n   Roast 45 rang at a measured **177 s** at Ki 0.10 (state-history.md')
    print('   § Correction: extrema 2:12 / 3:26 / 5:10 / 6:22, so two full cycles at')
    print('   178 and 176 s).  That is the only closed-loop behaviour on record and')
    print('   it is the tie-breaker.  Compare it against the least-damped closed-loop')
    print('   mode, not the crossover period -- they are different quantities:')
    print(f"   {'card':<14} {'PM':>6} {'T cross':>8} {'T closed':>9} {'zeta':>6} "
          f"{'err vs 177 s':>13}")
    for name, a, th, tau2 in cards:
        _, pm, T = mg.margins(a, th, 3.0, 0.10, tau2=tau2)
        Tcl, z = mg.closed_loop_modes(a, th, 3.0, 0.10, tau2=tau2)
        print(f'   {name:<14} {pm:6.1f} {T:8.0f} {Tcl:9.0f} {z:6.3f} '
              f'{(Tcl - 177.0) / 177.0 * 100:12.0f}%')
    print('   Roast 46\'s two-lag card lands on 173 s against the measured 177 --')
    print('   the closest any card on record has come.  Its single-lag card gives')
    print('   194 s and roast 48\'s two cards give 143-152 s.  So the ranking that')
    print('   state-history.md § Roast 48 drew (roast 46 predicts the real roast,')
    print('   roast 48 does not) survives the structure change, and improves under')
    print('   it.  Kp 3.0 / Ki 0.07 has 33-45 deg of margin on all four cards.')


def section_ridge_margins(profiles):
    print('\n== 6b. walking roast 46\'s ridge, priced in phase margin and period ==')
    print('   theta held, tau2 and a refitted at each step.  If the split were')
    print('   expensive this column would move; the point of the table is that it')
    print('   does not.')
    p, te, ye = profiles[46]
    t = win(p, PRIMARY[46])
    bt = p.bt_at(t)
    rows = []
    for th in np.arange(0.0, 20.01, 1.0):
        g = pf.fit_integral_2lag(t, bt, te, ye, order=ORDER,
                                 thetas=np.array([th]), tau2s=TAU2S)
        _, pm7, _ = mg.margins(g.a, th, 3.0, 0.07, tau2=g.tau2)
        _, _, T10 = mg.margins(g.a, th, 3.0, 0.10, tau2=g.tau2)
        Tcl, zeta = mg.closed_loop_modes(g.a, th, 3.0, 0.10, tau2=g.tau2)
        rows.append((th, g.tau2, g.a, g.resid_rms, pm7, T10, Tcl, zeta))
    best = min(r[3] for r in rows)
    print(f"   {'theta':>6} {'tau2*':>6} {'sum':>5} {'a':>9} {'resid':>7} "
          f"{'x min':>6} {'PM@Ki.07':>9} {'T@Ki.10':>8} {'Tcl@Ki.10':>10} "
          f"{'zeta':>6}")
    for th, tau2, a, r, pm, T, Tcl, z in rows:
        mark = '  <- resid min' if abs(r - best) < 1e-9 else ''
        print(f'   {th:6.1f} {tau2:6.1f} {th + tau2:5.1f} {a:9.5f} {r:7.4f} '
              f'{r / best:6.3f} {pm:9.1f} {T:8.0f} {Tcl:10.0f} {z:6.3f}{mark}')
    print('   Phase margin at the tuning in force moves 32.8 -> 37.7 deg across the')
    print('   whole ridge, from all-delay to all-lag, and the residual over the same')
    print('   span moves by 11%.  **The tuning does not move**: five degrees of')
    print('   margin is inside the model error these cards already carry, and Ki 0.07')
    print('   is comfortable at either end.')
    print('   The closed-loop period does move, 156 -> 196 s, so the ring IS')
    print('   informative about the split where the residual is not.  The measured')
    print('   177 s picks out theta 6-7 / tau2 6.5-7, which is within 1% of the')
    print('   residual minimum at theta 5 -- the open-loop fit and the closed-loop')
    print('   measurement agree.  What the ring disfavours is either extreme: the')
    print('   all-delay end predicts 196 s and the all-lag end 156 s.')
    print('   Treat that as corroboration and not as a third significant figure -- it')
    print('   is one ring, in one roast, at a Ki no longer in use, and the Pade')
    print('   approximation of the delay is itself doing work in the comparison.')


def _loss_cubic(p, te, ye, a, theta, tau2, lo=45.0):
    """The loss cubic `merge_inlet_base.py` reads, refitted under one structure.

    Same recipe as `roast46_refit.py:emit_plant` -- spline disturbance from
    CHARGE+2, re-fitted as a cubic from `lo` to DROP so the schedule carries no
    memory of the charge dip.  It must be refitted per structure: `a` differs
    between them, and `loss` is whatever `a*(X - BT)` failed to explain.
    """
    drop = p.marks['DROP']
    tg = np.arange(2.0, drop + 1e-9, 1.0)
    slow, _ = pf.fit_disturbance(tg, p.bt_at(tg), te, ye, a, theta,
                                 knot_spacing=8.0, tau2=tau2)
    tl = np.arange(lo, drop + 1e-9, 1.0)
    return np.polyfit(tl, np.interp(tl, tg, slow), 3)


def section_schedule(profiles, ramp_start=90.0, tail_window=30.0):
    print('\n== 7. what it does to merge_inlet_base.py\'s bg(t+theta) lead ==')
    print('   1 lag:  ff(t) = X(t+theta),            X = bg + (dbg/dt - loss)/a')
    print('   2 lags: ff(t) = X(t+theta) + tau2 * dX/dt(t+theta)')
    print('   -- invert the lag as well as the gain, then apply what delay is left.')
    p, te, ye = profiles[46]
    t46 = win(p, PRIMARY[46])
    f1, f2 = fits(p, te, ye, t46)
    try:
        with open(CARD46, encoding='utf-8') as fh:
            card = json.load(fh)
        a1, th1 = card['a'], card['theta']
        print(f'   plant (1 lag) from plant_roast46.json: a {a1:.5f} theta {th1:.1f}')
    except OSError:
        a1, th1 = f1.a, f1.theta
        print(f'   plant (1 lag) refitted: a {a1:.5f} theta {th1:.1f}')
    print(f'   plant (2 lag) from roast 46: a {f2.a:.5f} theta {f2.theta:.1f} '
          f'tau2 {f2.tau2:.1f}')
    loss1 = _loss_cubic(p, te, ye, a1, th1, 0.0)
    loss2 = _loss_cubic(p, te, ye, f2.a, f2.theta, f2.tau2)
    print(f'   loss(60) / loss(400) degC/s: 1 lag '
          f'{np.polyval(loss1, 60.0):+.4f} / {np.polyval(loss1, 400.0):+.4f}, '
          f'2 lag {np.polyval(loss2, 60.0):+.4f} / {np.polyval(loss2, 400.0):+.4f}')

    bg = load_profile(PROFILE_003)
    drop = bg.marks['DROP']
    # merge_inlet_base.py's own pipeline: the background is the decay-smoothed BT
    # curve Follow-Background mode targets, and --tail ror blends it into its
    # terminal RoR fit over the last --tail-window so the lead does not read the
    # recorded cooling phase.
    bgy = np.asarray(decay_smooth(list(bg.bt)), dtype=float)
    w = (bg.t >= drop - tail_window) & (bg.t <= drop)
    m_, b_ = np.polyfit(bg.t[w], bgy[w], 1)
    gx = np.arange(0.0, drop + 40.0, 1.0)
    frac = np.clip((gx - (drop - tail_window)) / tail_window, 0.0, 1.0)
    gy = np.where(gx >= drop, m_ * gx + b_,
                  (1 - frac) * np.interp(gx, bg.t, bgy) + frac * (m_ * gx + b_))
    dbg = np.gradient(gy, gx)
    t = np.arange(0.0, drop + 1e-9, 1.0)

    def schedule(a, theta, tau2, loss):
        X = gy + (dbg - np.polyval(loss, gx)) / a
        F = X + tau2 * np.gradient(X, gx) if tau2 > 0 else X
        return np.interp(t + theta, gx, F)

    s1 = schedule(a1, th1, 0.0, loss1)
    s2 = schedule(f2.a, f2.theta, f2.tau2, loss2)
    m = t >= ramp_start
    d = s2 - s1
    print(f'\n   profile_003, ramp {ramp_start:.0f} s to DROP {drop:.0f} s:')
    print(f'      1 lag base {s1[m].min():6.1f} .. {s1[m].max():6.1f} degC')
    print(f'      2 lag base {s2[m].min():6.1f} .. {s2[m].max():6.1f} degC')
    print(f'      difference mean {d[m].mean():+.2f}  rms {np.sqrt((d[m] ** 2).mean()):.2f}'
          f'  worst {np.abs(d[m]).max():.2f} degC  (at t = '
          f'{t[m][np.argmax(np.abs(d[m]))]:.0f} s)')
    print(f"      {'t':>6} {'bg':>7} {'1 lag':>8} {'2 lag':>8} {'diff':>7}")
    for tt in list(range(int(ramp_start), int(drop), 60)) + [int(drop)]:
        print(f'      {tt:6d} {np.interp(tt, bg.t, bgy):7.1f} {s1[tt]:8.1f} '
              f'{s2[tt]:8.1f} {d[tt]:+7.2f}')
    print(f'\n   Raw (unclamped) ff at CHARGE: 1 lag {s1[0]:.0f}, 2 lag {s2[0]:.0f} degC.')
    print('   The 1-lag figure is merge_inlet_base.py --dry-run\'s own "raw ff(0)",')
    print('   which is the check that this section reproduces the tool rather than')
    print('   an approximation of it.  Both are absurd for the same reason -- dbg/dt')
    print('   is divided by a through a dip falling at 3.5 degC/s -- so the --dip')
    print('   rule is unaffected in kind.')
    print()
    print('   The two schedules agree to rms 0.84 degC over the ramp, against the')
    print('   ~0.5 degC floor that whole-degree event quantisation puts on the')
    print('   replay anyway.  The reason is arithmetic, not luck: on a ramp of slope')
    print('   r, advancing bg by theta adds theta*r and the lag inversion adds')
    print(f'   tau2*r, and roast 46 puts theta+tau2 = {f2.theta + f2.tau2:.0f} s '
          f'against the single-lag {th1:.1f}.')
    print('   The two constructions are the same lead written two ways, and the')
    print('   larger `a` and the loss curve refitted against it cancel the rest.')
    print('   **So merge_inlet_base.py needs no change and plant_roast46.json needs')
    print('   no change.**  What needs changing is the *claim*: theta is not 13.5 s')
    print('   of transport, it is 13.5 s of total apparent lag, and the tool is')
    print('   using it as a first-order lead approximation, which is valid.')
    print()
    print('   Two caveats for whoever does rewrite it:')
    print('   - the two-lag lead carries d2bg/dt2 * tau2/a, so a rough or kinked')
    print('     background costs far more than it does today.  profile_003 is')
    print('     authored and smooth; a background merged from a recorded roast is')
    print('     not, and the tail blend would need to be C1, not just C0.  That is')
    print('     the whole of the 3.3 degC worst case above: it sits at the ramp')
    print(f'     start, where the --dip rule joins on.')
    print(f'   - `a` is {(f2.a / a1 - 1) * 100:.0f}% larger under two lags '
          f'({f2.a:.5f} against {a1:.5f}), so the')
    print('     two numbers are NOT interchangeable, and neither are the loss')
    print('     cubics fitted against them.  A card must carry a, theta, tau2 and')
    print('     the loss curve as one set, all fitted together -- which is why this')
    print('     pass emits no card and changes no authoring tool.')


def section_charge_proxy(profiles, theta_proxy=13.5):
    """`charge_state.py` assumes a pure deadtime.  How much does that cost it?

    The proxy reads the BT fall over `0 .. theta` as charge mixing alone, on the
    grounds that nothing the heater does reaches BT before then, and corrects for
    the pre-charge air already in flight.  Under two lags there is no hard cutoff:
    the heater's post-CHARGE influence starts at theta and ramps in with tau2.
    This is the size of that, on the roasts the proxy is quoted for.
    """
    print('\n== 8. does this move the charge-state proxy? ==')
    print('   charge_state.py reads (BT(0) - BT(theta))/mass as charge mixing alone.')
    print('   Under two lags the heater is not fully blocked over that window, so')
    print('   the modelled inlet contribution over 0..13.5 s changes.  What matters')
    print('   is not its size but whether it is common-mode across roasts.')
    _, te46, ye46 = profiles[46]
    p46 = profiles[46][0]
    t = np.arange(0.0, theta_proxy + 1e-9, 0.25)
    try:
        with open(CARD46, encoding='utf-8') as fh:
            card = json.load(fh)
        a1, th1 = card['a'], card['theta']
    except OSError:
        a1, th1 = 0.004897, 13.5
    _, f2 = fits(p46, te46, ye46, win(p46, PRIMARY[46]))
    print(f"   {'roast':>6} {'mass':>6} {'BT fall':>8} {'1 lag':>7} {'2 lag':>7} "
          f"{'diff':>7} {'diff/100 g':>11}")
    for n, mass in ((43, 400), (44, 400), (46, 400), (49, 400)):
        try:
            q = load_profile(ALOG % n)
        except OSError:
            continue
        te, ye = q.extras['Inlet']
        bt = q.bt_at(t)
        c1 = np.trapezoid(a1 * (np.interp(t - th1, te, ye) - bt), t)
        c2 = np.trapezoid(f2.a * (pf.lag1(np.interp(t - f2.theta, te, ye),
                                          f2.tau2, 0.25) - bt), t)
        fall = float(q.bt_at(0.0) - q.bt_at(theta_proxy))
        print(f'   {n:6d} {mass:6d} {fall:8.2f} {c1:+7.2f} {c2:+7.2f} {c2 - c1:+7.2f} '
              f'{(c2 - c1) / mass * 100:+11.3f}')
    print('   The heater contribution is 3-5 degC of a 46-61 degC fall under either')
    print('   structure, and the *difference* between structures is 0.76-0.97 degC,')
    print('   i.e. 0.19-0.24 degC/100 g -- a spread of 0.05 across the four roasts,')
    print('   against the 3.3 degC/100 g gap the proxy is being used to measure.')
    print('   **It is common-mode and charge_state.py needs no change.**  What is')
    print('   now known to be loose is the *shape* of its air-in-flight correction:')
    print('   `a*(inlet_pre - INLET_REF)*theta` is a rectangular window where the')
    print('   two-lag reading gives an exponential tail.  Worth a line in that')
    print('   tool\'s docstring, not a rewrite.')


SECTIONS = {
    'excitation': section_excitation,
    'headline': section_headline,
    'ident': section_identifiability,
    'ftest': section_significance,
    'stationarity': section_stationarity,
    'margins': section_margins,
    'ridge': section_ridge_margins,
    'schedule': section_schedule,
    'charge': section_charge_proxy,
}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only', choices=sorted(SECTIONS))
    ap.add_argument('--no-bootstrap', action='store_true',
                    help='skip the 200-resample block bootstrap in section 5')
    args = ap.parse_args()

    profiles = {}
    for n in (46, 48, 49):
        p, te, ye = load(n)
        profiles[n] = (p, te, ye)
        print(f'roast {n}: CHARGE_BT {p.bt_at(0.0):.1f}, DROP {p.marks["DROP"]:.0f} s '
              f'at BT {p.bt_at(p.marks["DROP"]):.1f}, sampling '
              f'{np.median(np.diff(p.t)):.2f} s')
    print()

    for name, fn in SECTIONS.items():
        if args.only and args.only != name:
            continue
        if name == 'stationarity':
            fn(profiles, bootstrap=not args.no_bootstrap)
        else:
            fn(profiles)


if __name__ == '__main__':
    main()
