#!/usr/bin/env python3
"""How much flow does a fan unit buy, and can the 64 -> 60 step at 120 s
account for the -2.9 degC residual at 170 s?

**MEASURED 2026-09-10 by roasts 58 (empty) and 59 (345 g of roasted beans),
and the answer is yes -- with room to spare.**  state-plan.md § TEST PLAN
§ Phase A asked for `f`, the fractional flow lost on `Air 64 -> 60`, with a
decision rule of `f >= 0.12` => "the fan can account for essentially all of
2.9 degC".

    f(64 -> 60)   empty 0.162     loaded 0.181-0.189      threshold 0.12

The ceiling arithmetic the plan wrote -- `deficit = RoR * f * T_eff / 60` at
`RoR = 29.0` and `T_eff = 45 s` -- then gives **3.9 degC against the 2.93
observed**, so the fan term is not merely sufficient, it over-covers by about a
third and the compensation (less flow means a larger `T_in - T_out`) has to eat
the difference.

## The model that fits, and the one that does not

Route 1 of the plan -- `Temp_Drive ∝ 1/mdot` at fixed BT -- **cannot be run on
this machine.**  Empty at BT 145 / fan 60, `Temp_Drive` read 12.84, 8.47, 6.51
and 7.49 on four visits in one session while heater duty over the same four
repeated to +-0.09 %, and at fan 72 and 80 the settled `Inlet` sits *below* BT,
which `1/mdot` cannot produce at all.  This is state-history-residual.md § Phase 0's
"duty is a state variable at this precision; `Inlet - BT` is not", now with a
mechanism attached (§ The soak, below).

Route 2 -- the duty model -- fits at the duty channel's own 1 % quantisation:

    HT = A * (fan - f0) * (Inlet - amb) + c

    empty  (roast 58, 10 rungs, 3 params, 7 dof)   f0 = 39.3   rms 0.182 %
    loaded (roast 59, 11 rungs, 3 params, 8 dof)   f0 = 42.8   rms 0.202 %
    joint, shared A and c, separate f0 (21, 4, 17) 40.0 / 41.8  rms 0.231 %

`c = 22.7 %` is the flow-independent duty, measured rather than extrapolated;
the plan had carried `c = 24.9 %` from a 5x extrapolation of phase 0's BT
ladder, and it was close.  Pooling the two sessions onto **one** `f0` costs a
factor of 5.5 in residual (1.281 %), so the empty/loaded difference is real:
**345 g of beans costs 9.2 % of the flow at fan 60.**

## The blower saturates above fan 64

With `f0` pinned by the fan 53-64 rungs, the two high rungs fall short of the
linear-flow model by a growing margin:

    fan 72   predicted HT 57.55   measured 55.87   -> the flow of a nominal 70.4
    fan 80   predicted HT 65.43   measured 60.18   -> the flow of a nominal 75.0

So `mdot ∝ (fan - 40)` holds across the range the roast uses and bends over
above it.  The ladder's top rungs are therefore *not* the ones that size `f`,
which is the opposite of what the plan expected when it chose 60-80 for span.

## The direct step response, loaded -- the part no model is needed for

Roast 59 held BT 145 under the same cascade with 345 g in the chamber and
stepped the fan.  Against a 90 s pre-step baseline:

    60 -> 64  (f = -0.222)   BT +0.49 degC, peak at  46 s
    64 -> 56  (f = +0.364)   BT -0.67 degC, bottom at 54 s, recovered by ~130 s
    56 -> 58, 58 -> 60       under +-0.35 degC -- in the noise

**The timing is the finding.**  The roast residual bottoms 45-50 s after the
120 s fan step and has recovered by 230 s, 110 s after it.  The bench step
bottoms at 54 s and recovers by 130 s.  Same loop, same shape.

The *magnitude* does not transfer directly and the bench cannot make it: at a
settled BT 145 the delivered power is the chamber loss alone (`Inlet - BT` ~ 2
degC loaded), while at 145 s of a roast `Inlet - BT` is 49-60 degC, so the same
`f` removes 25-30x more power.  Scaled linearly that predicts 8-10 degC and the
roast shows 2.9, which is the compensation term again, larger than the ceiling
arithmetic allows for.  **Do not read a magnitude out of the bench step; read
the sign, the shape and the timing.**

## The soak, and what it cost phase 0

Roast 58 started from a cold machine (BT 29.0 = ambient).  At fan 60 / BT 145
its duty decayed 50.5 -> 47.6 % over the first seven minutes and only reached
46.5 % by 23 minutes; three later fan-60 / BT-145 visits spanning 23 to 62
minutes then agreed to **0.18 %**.  Roast 59, run an hour later on the soaked
machine, settled in three minutes and its first rung matched its last to 0.3 %.

Phase A's stated abort criterion ("rung 5 must reproduce rung 1's HT to
+-0.5 %") therefore **failed** -- rung 1 read 1.22 % high -- and the failure is
the session's cold start, not drift in the measurement.  Note that the duty
model above absorbs it anyway: the soak raises `Inlet` and `HT` together, so
rung 1's residual against the fit is +0.03 %.  It is the *BT*-referenced line
`HT(BT)` that the soak breaks, because a soaking chamber is not standing still.

That is the best available explanation for why phase 0's line disagrees with
this session's (§ The standing-duty lines, below), alongside the other
possibility the plan itself flagged: phase 0's log records no `Air` event at
all, and one fan unit is worth ~0.96 % of duty.

## The standing-duty lines -- A2's answer

Four rungs each at fan 60, BT 145 / 160 / 175 / 190, read over the last 120 s:

    empty    HT = 15.16 + 0.2165 * BT      residuals -0.00 -0.05 +0.11 -0.06
    loaded   HT = 17.75 + 0.1788 * BT      residuals +0.06 -0.09 +0.00 +0.03

**The line is linear out to BT 190** -- second differences under 0.03 %/degC,
residuals at the duty quantisation -- which is A2's primary question answered
cleanly.  Nothing is superlinear and no rung failed to settle, so the empty
chamber has no ceiling below 190 and the "superlinear loss" candidate for the
excess-duty model's intercept disagreement (0.81 vs 6.46 between roasts 56 and
57) is **dead**.

But phase 0's `HT = 20.25 + 0.1922*BT` is not this line.  It over-predicts the
empty chamber by 1.57 % at BT 145, falling to 0.53 % at 190; about 0.47 % of
that is the 2.4 degC warmer ambient in this session and the rest is unexplained
(soak, or an unrecorded fan level, above).  Its slope is within its own
uncertainty of the new one -- it was fitted over 22 degC where this is fitted
over 45.

**The loaded line does not transfer to a roast, and that is worth knowing.**
Phase 0's line sits **4.45 % above the loaded line at BT 145, widening to
5.05 % at 190**.  Re-basing state-history-residual.md § Phase 0's excess-duty model onto
it moves roast 56's intercept from `RoR = 0.81 + 2.66*excess` to about
`-11.7 + 2.66*excess`, i.e. a loaded chamber standing still would be cooling at
12 degC/min, which it is not.  345 g of *roasted* beans sitting still at fan 60
is not 400 g of circulating greens: it loses no water, it may not be
circulating at 56-60 at all, and the BT probe is buried in a static pile.

What survives is the *size* of the question.  The intercept disagreement the
excess-duty model has between roasts 56 and 57 -- 0.81 against 6.46 degC/min --
is 5.65 degC/min, or **2.1 % of duty at the model's own 2.66 slope**.  The
baseline candidates measured here span 4.5 %.  So that disagreement is a
baseline-level question and the baseline level is not pinned down to better
than the disagreement itself; the empty line's apparent success is to that
extent luck, and no re-basing on this data will settle it.

Usage:
    python3 tools/analysis/fan_ladder.py                 # both sessions
    python3 tools/analysis/fan_ladder.py --logs DIR      # non-default log dir

Stdlib only.
"""

import argparse
import ast
import math
import os
import statistics as st

LOGS = os.path.expanduser('~/Documents/artisan')

# (fan, from, to) windows are the last 120 s before the next scheduled change;
# see the module docstring for why rung 1 of roast 58 is kept despite the soak.
EMPTY_FAN = [  # roast 58, BT 145, fan stepped
    (60, '5:14', '7:14', 'rung 1, inside the cold-start soak'),
    (64, '8:00', '10:00', 'short rung -- 166 s, stepped early at 7:14'),
    (72, '13:00', '15:00', 'blower short of the linear-flow model'),
    (80, '18:00', '20:00', 'blower short of the linear-flow model'),
    (60, '22:50', '24:50', 'return rung'),
    (60, '48:42', '50:42', 'after the BT ladder'),
    (56, '53:26', '55:26', ''),
    (53, '57:26', '59:26', ''),
    (60, '60:24', '62:20', 'final return'),
]
EMPTY_BT = [  # roast 58, fan 60, BT stepped
    (145, '22:50', '24:50'), (160, '28:55', '30:55'),
    (175, '34:54', '36:54'), (190, '40:55', '42:55'),
]
LOADED_FAN = [  # roast 59, BT 145, 345 g of roasted beans
    (60, '3:00', '5:00', ''),
    (64, '7:10', '9:10', ''),
    (56, '11:10', '13:10', ''),
    (58, '14:15', '16:15', 'short rung -- 185 s, reads low'),
    (60, '16:44', '18:44', ''),
    (60, '32:20', '34:20', 'after the BT ladder'),
    (56, '34:50', '35:45', 'short rung -- 55 s'),
]
LOADED_BT = [
    (145, '16:44', '18:44'), (160, '21:10', '23:10'),
    (175, '25:25', '27:25'), (190, '28:40', '30:30'),
]
LOADED_EXTRA = [(56, 160, '38:39', '40:35')]  # BT 160 at fan 56

# (t, fan_from, fan_to) -- steps clean enough to read a BT transient from
LOADED_STEPS = [(300, 60, 64), (550, 64, 56), (790, 56, 58), (975, 58, 60)]
EMPTY_STEPS = [(1200, 80, 60), (3042, 60, 56), (3326.5, 56, 53), (3566, 53, 60)]


def clock(s):
    return sum(float(x) * 60 ** i for i, x in enumerate(reversed(s.split(':'))))


def mmss(x):
    m, s = divmod(int(round(x)), 60)
    return '%d:%02d' % (m, s)


def load(path):
    """CHARGE-relative time plus the named channels of an Artisan .alog."""
    d = ast.literal_eval(open(path, encoding='utf-8', errors='replace').read())
    tx, ti = d['timex'], d['timeindex']
    c = tx[ti[0]] if ti[0] > 0 else 0.0
    ch = {'ET': d['temp1'], 'BT': d['temp2']}
    for which in ('1', '2'):
        for i, n in enumerate(d.get('extraname' + which, [])):
            ch[n] = d['extratemp' + which][i]
    return d, [x - c for x in tx], ch


def trimmed(xs):
    """Duty is logged as integers with occasional excursions from a step the
    window straddles; drop anything more than 8 from the median."""
    m = st.median(xs)
    k = [x for x in xs if abs(x - m) < 8]
    return sum(k) / len(k)


def read(t, ch, a, b):
    a, b = clock(a), clock(b)
    idx = [i for i in range(len(t)) if a <= t[i] <= b]
    return {k: trimmed([ch[k][i] for i in idx]) for k in
            ('BT', 'Inlet', 'Temp_Drive', 'HT', 'amb')}, len(idx)


def ols(pts):
    n = len(pts)
    sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxx = sum(p[0] ** 2 for p in pts); sxy = sum(p[0] * p[1] for p in pts)
    m = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b = (sy - m * sx) / n
    return m, b, [y - (m * x + b) for x, y in pts]


def duty_fit(pts, f0=None):
    """HT = A*(fan-f0)*(Inlet-amb) + c.  Scans f0 unless one is given."""
    best = None
    grid = [f0] if f0 is not None else [x / 100.0 for x in range(-2000, 5500, 5)]
    for g in grid:
        X = [(fan - g) * (inl - amb) for fan, inl, amb, _ in pts]
        Y = [p[3] for p in pts]
        n = len(X); sx = sum(X); sy = sum(Y)
        sxx = sum(x * x for x in X); sxy = sum(x * y for x, y in zip(X, Y))
        den = n * sxx - sx * sx
        if abs(den) < 1e-12:
            continue
        A = (n * sxy - sx * sy) / den
        c = (sy - A * sx) / n
        ss = sum((y - (A * x + c)) ** 2 for x, y in zip(X, Y))
        if best is None or ss < best[0]:
            best = (ss, g, A, c)
    ss, g, A, c = best
    resid = [H - (A * (fan - g) * (inl - amb) + c) for fan, inl, amb, H in pts]
    return g, A, c, math.sqrt(ss / max(1, len(pts) - 3)), resid


def joint(a_pts, b_pts):
    """Shared A and c, separate f0 -- the only split the physics allows, since
    A = K*alpha and c belong to the heater and the blower, not the chamber."""
    best = None
    for fa in [x / 20.0 for x in range(400, 1040)]:
        for fb in [x / 20.0 for x in range(400, 1040)]:
            X = ([(f - fa) * (i - m) for f, i, m, _ in a_pts] +
                 [(f - fb) * (i - m) for f, i, m, _ in b_pts])
            Y = [p[3] for p in a_pts] + [p[3] for p in b_pts]
            n = len(X); sx = sum(X); sy = sum(Y)
            sxx = sum(x * x for x in X); sxy = sum(x * y for x, y in zip(X, Y))
            A = (n * sxy - sx * sy) / (n * sxx - sx * sx)
            c = (sy - A * sx) / n
            ss = sum((y - (A * x + c)) ** 2 for x, y in zip(X, Y))
            if best is None or ss < best[0]:
                best = (ss, fa, fb, A, c)
    ss, fa, fb, A, c = best
    return fa, fb, A, c, math.sqrt(ss / (len(a_pts) + len(b_pts) - 4))


def rung_table(path, spec, title, bt_ladder=False):
    d, t, ch = load(path)
    print('\n%s' % title)
    print('  %-5s %-14s %5s %7s %7s %7s %7s %6s  %s' %
          ('fan', 'window', 'n', 'BT', 'Inlet', 'TD', 'HT', 'amb', 'note'))
    out = []
    for row in spec:
        if bt_ladder:
            fan, a, b, note = 60, row[1], row[2], ''
        else:
            fan, a, b, note = row
        r, n = read(t, ch, a, b)
        print('  %-5d %-14s %5d %7.2f %7.2f %7.2f %7.3f %6.2f  %s' %
              (fan, a + '-' + b, n, r['BT'], r['Inlet'], r['Temp_Drive'],
               r['HT'], r['amb'], note))
        out.append((fan, r['Inlet'], r['amb'], r['HT'], r['BT']))
    return out


def steps(path, spec, f0, title):
    d, t, ch = load(path)
    near = lambda tt: min(range(len(t)), key=lambda i: abs(t[i] - tt))
    print('\n%s' % title)
    print('  %-8s %-9s %8s %8s %9s' % ('at', 'step', 'f', 'peak dBT', 't_peak'))
    for ts, a, b in spec:
        i0, j0 = near(ts), near(ts - 90)
        base = sum(ch['BT'][i] for i in range(j0, i0)) / (i0 - j0)
        worst = (0.0, 0.0)
        for k in range(i0, near(ts + 150)):
            e = ch['BT'][k] - base
            if abs(e) > abs(worst[1]):
                worst = (t[k] - ts, e)
        print('  %-8s %-9s %8.3f %+8.2f %8.0f s' %
              (mmss(ts), '%d->%d' % (a, b), (a - b) / (a - f0), worst[1], worst[0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--logs', default=LOGS)
    args = ap.parse_args()
    e58 = os.path.join(args.logs, 'airRoaster_58.alog')
    e59 = os.path.join(args.logs, 'airRoaster_59.alog')

    print('=' * 78)
    print('PHASE A -- fan and BT ladders, roasts 58 (empty) and 59 (345 g roasted)')
    print('=' * 78)

    ef = rung_table(e58, EMPTY_FAN, 'roast 58, empty, fan ladder at BT 145')
    eb = rung_table(e58, [(b, a, c) for b, a, c in EMPTY_BT],
                    'roast 58, empty, BT ladder at fan 60', bt_ladder=True)
    lf = rung_table(e59, LOADED_FAN, 'roast 59, 345 g, fan ladder at BT 145')
    lb = rung_table(e59, [(b, a, c) for b, a, c in LOADED_BT],
                    'roast 59, 345 g, BT ladder at fan 60', bt_ladder=True)
    lx = rung_table(e59, [(f, a, b, 'BT %d at fan %d' % (bt, f))
                          for f, bt, a, b in LOADED_EXTRA],
                    'roast 59, 345 g, the extra fan-56 rung')

    print('\n--- the standing-duty lines (fan 60) ---')
    for lbl, rows in (('empty ', eb), ('loaded', lb)):
        m, b, r = ols([(p[4], p[3]) for p in rows])
        print('  %s  HT = %7.3f + %.5f*BT     residuals %s' %
              (lbl, b, m, ' '.join('%+.2f' % v for v in r)))
    me, be, _ = ols([(p[4], p[3]) for p in eb])
    ml, bl, _ = ols([(p[4], p[3]) for p in lb])
    print('  phase 0 carried HT = 20.25 + 0.1922*BT (empty, BT 130-152):')
    for bt in (145, 160, 175, 190):
        print('     BT %3d  phase0 %6.2f   this empty %6.2f (%+5.2f)'
              '   this loaded %6.2f (%+5.2f)' %
              (bt, 20.25 + .1922 * bt, be + me * bt,
               be + me * bt - (20.25 + .1922 * bt), bl + ml * bt,
               bl + ml * bt - (20.25 + .1922 * bt)))

    print('\n--- the duty model  HT = A*(fan-f0)*(Inlet-amb) + c ---')
    lin = [p[:4] for p in ef if p[0] <= 64] + [p[:4] for p in eb[1:]]
    f0e, Ae, ce, rmse, re_ = duty_fit(lin)
    print('  empty, fan 53-64 (n=%d, 3 params, %d dof): f0=%.1f A=%.5g c=%.2f'
          '  rms %.3f %%' % (len(lin), len(lin) - 3, f0e, Ae, ce, rmse))
    print('    residuals: %s' % ' '.join('%+.2f' % v for v in re_))
    for fan, inl, amb, HT in [p[:4] for p in ef if p[0] > 64]:
        pred = Ae * (fan - f0e) * (inl - amb) + ce
        eff = f0e + (HT - ce) / (Ae * (inl - amb))
        print('    fan %2d: predicted %5.2f, measured %5.2f (%+5.2f)'
              '  -> the flow of a nominal %.1f' % (fan, pred, HT, HT - pred, eff))

    lall = [p[:4] for p in lf] + [p[:4] for p in lb[1:]] + [p[:4] for p in lx]
    f0l, Al, cl, rmsl, rl = duty_fit(lall)
    print('  loaded (n=%d, 3 params, %d dof): f0=%.1f A=%.5g c=%.2f  rms %.3f %%'
          % (len(lall), len(lall) - 3, f0l, Al, cl, rmsl))
    print('    residuals: %s' % ' '.join('%+.2f' % v for v in rl))

    print('\n  does the bed restrict the flow?  A and c are heater properties and'
          '\n  must be shared; only f0 may differ:')
    _, _, _, rms_pool, _ = duty_fit(lin + lall)
    fe, fl_, Aj, cj, rmsj = joint(lin, lall)
    print('    one f0 for both:      rms %.3f %%  (%d points, 3 params)'
          % (rms_pool, len(lin) + len(lall)))
    print('    shared A and c, separate f0:  f0 = %.1f empty / %.1f loaded,'
          ' A=%.5g, c=%.2f,  rms %.3f %% (4 params, %d dof)'
          % (fe, fl_, Aj, cj, rmsj, len(lin) + len(lall) - 4))
    print('    => the bed costs %.1f %% of the flow at fan 60, and pooling onto one'
          '\n       f0 costs a factor of %.1f in residual' %
          (100 * (1 - (60 - fl_) / (60 - fe)), rms_pool / rmsj))

    print('\n--- f, the fraction of flow lost on the roast\'s 64 -> 60 step ---')
    for lbl, f0 in (('empty ', f0e), ('loaded', f0l), ('joint ', fl_)):
        f = 4.0 / (64 - f0)
        print('  %s  f0 = %.1f   f = %.3f   ceiling deficit = RoR*f*T_eff/60 ='
              ' %.2f degC   (observed residual 2.93)' %
              (lbl, f0, f, 29.0 * f * 45.0 / 60.0))
    print('  decision rule (state-plan.md § TEST PLAN): f >= 0.12 => the fan can'
          ' account for\n  essentially all of it; run Phase B expecting the dip to'
          ' disappear.')

    steps(e59, LOADED_STEPS, f0l,
          'roast 59, 345 g -- BT transient after a fan step, setpoint held at 145')
    steps(e58, EMPTY_STEPS, f0e,
          'roast 58, empty -- the same, for contrast (probe-fast, not bed-slow)')
    print('\n  the roast residual bottoms 45-50 s after the 120 s step and has'
          '\n  recovered by 230 s; the loaded 64->56 step bottoms at 54 s and'
          '\n  recovers by ~130 s.  Same shape, same loop.\n')


if __name__ == '__main__':
    main()
