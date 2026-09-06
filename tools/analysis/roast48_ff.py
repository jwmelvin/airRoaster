#!/usr/bin/env python3
"""Refit `feedforward()` **loaded**, from roast 48, and test whether the empty map transfers.

Roast 48 is `tools/gen_char_single.py`'s one 400 g sacrificial batch: the same
replayed-schedule mechanism as roast 47 (Test A), with the inlet parked at three
flat setpoints -- 245, 215, 190 degC -- and a fan step taken inside each, plus
two SV 150 valleys.  It is the first characterisation run **with beans in the
chamber** and the first roast on firmware v0.20.0, where `feedforward()` carries
roast 47's measured map and is live rather than clamped at 100.

It answers two questions the empty run could not.

1. **Does a bean bed change the heat a fan level costs?**  `ff_roast47.json`'s
   note says it should not -- the inlet thermocouple sits upstream of the bed --
   but a bed changes the pressure drop and so the *flow* a fan level delivers,
   which is why `FF SLOPE` exists.  Nothing had tested it.
2. **Is `slope(sv) = c_fan + c_fansv*sv/100` really a line?**  Three setpoints
   is the smallest design that can see curvature at all; the two-batch plan this
   replaced took its slope at SV 200 only and could not have.

Unlike the plant-fit half of this directory the module is **standard library
only** -- same reasoning as `roast47_ff.py`, and the same estimator, so the two
runs are compared on identical arithmetic.

Usage
-----
``python3 tools/analysis/roast48_ff.py`` runs every section.
``--emit-card`` writes ``tools/analysis/ff_roast48_loaded.json``.
"""

import argparse
import ast
import json
import os
import sys
import datetime as _dt

HOME = os.path.expanduser('~')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, 'Documents/artisan/airRoaster_48.alog')
ALOG47 = os.path.join(HOME, 'Documents/artisan/airRoaster_47.alog')
EMPTY_CARD = os.path.join(REPO, 'tools/analysis/ff_roast47.json')
CARD = os.path.join(REPO, 'tools/analysis/ff_roast48_loaded.json')

# A block is 30 s at the two high setpoints and 60 s at SV 190/150.  Roast 47
# measured heat reaching 95 % of its final value within 2 s of a fan step, and
# roast 48 confirms it settles in 3-6 s, so 12 s of lead is ample and lets the
# 30 s blocks -- which are where the SV 245 and SV 215 slopes live -- be used.
LEAD = 12.0       # discard this much after a slider change
WINDOW = 30.0     # average over at most this many seconds before the next change
MINSEG = 25.0     # a segment shorter than this is not a measurement
BLOCKS = 165.0    # the replayed charge ramp ends and the flat blocks begin
GUARD = 25.0      # quiet-window guard after a fan change
IN_GUARD = 60.0   # ... and after an inlet change.  A 95 degC step down is not a
                  # control excursion: heat goes to 0 and the inlet falls at the
                  # rate the hardware cools, so the first minute is the plant,
                  # not the loop.

# Roast 47's worst inlet excursion in the 40 s after each fan step, from
# `roast47_ff.py`.  v0.19.0's feedforward() was clamped at 100 % for every roast
# sample, so d(FF)/d(fan) was 0 and the inner loop absorbed these unaided.
# Artisan REWRITES the two samples before every step in a constant-valued channel.
# This is not smoothing.  `inputFilter` (canvas.py:4535) ends with an "improve a
# previously corrected reading" repair that assumes an equal run of readings was
# caused by drop-out replacement, and un-sticks it by linear interpolation toward
# the new value -- destructively, in the array that gets saved:
#
#     if (minmaxLimits or dropSpikes or dropDuplicates):
#         if tempx[-1] == tempx[-2] == tempx[-3] != temp:
#             delta = (tempx[-3] - temp) / 3.0
#             tempx[-1] = tempx[-3] - 2*delta;  tempx[-2] = tempx[-3] - delta
#
# The gate is any of the three filters, and `dropSpikes` alone is enough -- it is
# `true` in every cascade .aset, while `dropDuplicates` and `minmaxLimits` are
# false.  So a genuinely constant channel trips a repair meant for a stuck sensor.
# SV 245 -> 150 is stored as 245, 213.33, 181.67, 150; the integer heat channel
# carries thirds (59.7, 75.3); `amb` reads 28.36666667.
#
# Window *means* survive it -- the ramp it substitutes is nearly mean-preserving,
# and dropping every non-integer heat sample moves the 14 window means here by at
# most 0.10 % -- but the two samples before any transition are fabricated, so
# every guard around a step must open BEFORE the step.
FILTER = 3.0      # seconds of a step's backward smear to stand clear of


def ext(v):
    """events_internal_to_external_value (artisanlib/util.py:982-999)."""
    if -1.0 <= v <= 1.0:
        return 0
    return -(int(round(abs(v) * 10)) - 10) if v < -1.0 else int(round(v * 10)) - 10


def load(path):
    with open(path, encoding='utf-8') as fh:
        d = ast.literal_eval(fh.read())
    ci = d['timeindex'][0]
    t0 = d['timex'][ci]
    r = {
        't': [x - t0 for x in d['timex']],
        'BT': d['temp2'],
        'IN': d['extratemp1'][0],       # extra device 1 ch1
        'SV': d['extratemp1'][2],       # extra device 3 ch1 -- v0.19.0 getData SV
        'HT': d['extratemp2'][2],       # extra device 3 ch2 -- v0.19.0 getData HT
        'amb': d['extratemp2'][0],
    }
    names = (d['extraname1'][2], d['extraname2'][2])
    if names != ('SV', 'HT'):
        sys.exit(f'{path}: extra device 3 is {names}, not (SV, HT); this profile '
                 'predates the v0.19.0 channels and carries no heat curve')
    ev = sorted((r['t'][i], ty, ext(v)) for i, ty, v in
                zip(d['specialevents'], d['specialeventstype'], d['specialeventsvalue']))
    r['fan_events'] = [(x, v) for x, ty, v in ev if ty == 0]
    r['inlet_events'] = [(x, v) for x, ty, v in ev if ty == 2]
    r['changes'] = sorted({x for x, ty, _ in ev if ty in (0, 2)})
    # inlet changes that actually move the setpoint, for the guards below
    r['sv_steps'] = sorted({x for i, (x, v) in enumerate(r['inlet_events'])
                            if i and v != r['inlet_events'][i - 1][1]})
    r['drop'] = r['t'][d['timeindex'][6]] if d['timeindex'][6] else r['t'][-1]
    r['weight'] = d['weight']
    return r


def hold(events, x):
    """Zero-order hold -- what event playback does to a slider."""
    v = events[0][1]
    for at, val in events:
        if at <= x:
            v = val
        else:
            break
    return v


def segments(r):
    """Steady windows: SV and fan both constant, averaged before the next change."""
    out = []
    marks = [m for m in r['changes'] if m >= 0]
    for a, b in zip(marks, marks[1:] + [r['drop']]):
        if b - a < MINSEG or a >= r['drop']:
            continue
        lo, hi = max(a + LEAD, b - WINDOW), b - 2.0
        idx = [k for k, x in enumerate(r['t']) if lo <= x <= hi and r['SV'][k] > 0]
        if len(idx) < 10:
            continue
        mean = lambda key: sum(r[key][k] for k in idx) / len(idx)
        ht = mean('HT')
        sd = (sum((r['HT'][k] - ht) ** 2 for k in idx) / len(idx)) ** 0.5
        out.append({'t': (lo, hi), 'fan': float(hold(r['fan_events'], a)),
                    'sv': round(mean('SV')), 'heat': ht, 'sd': sd,
                    'bt': mean('BT'), 'amb': mean('amb'),
                    'in_err': mean('IN') - mean('SV')})
    return out


def ols(rows, cols, y='heat'):
    """Normal equations with Gaussian elimination.  A dozen points; this is fine."""
    n, p = len(rows), len(cols)
    X = [[c(r) for c in cols] for r in rows]
    Y = [r[y] for r in rows]
    A = [[sum(X[k][i] * X[k][j] for k in range(n)) for j in range(p)] +
         [sum(X[k][i] * Y[k] for k in range(n))] for i in range(p)]
    for i in range(p):
        pv = max(range(i, p), key=lambda k: abs(A[k][i]))
        A[i], A[pv] = A[pv], A[i]
        if abs(A[i][i]) < 1e-12:
            sys.exit('singular design matrix: the inputs did not move independently')
        for k in range(p):
            if k != i:
                f = A[k][i] / A[i][i]
                for cc in range(i, p + 1):
                    A[k][cc] -= f * A[i][cc]
    b = [A[i][p] / A[i][i] for i in range(p)]
    res = [Y[k] - sum(b[i] * X[k][i] for i in range(p)) for k in range(n)]
    return b, (sum(e * e for e in res) / n) ** 0.5, res


ONE = lambda r: 1.0
FAN = lambda r: r['fan']
SV = lambda r: r['sv']
FANSV = lambda r: r['fan'] * r['sv'] / 100.0


def predict(c, fan, sv):
    return c['c0'] + c['c_fan'] * fan + c['c_sv'] * sv + c['c_fansv'] * fan * sv / 100.0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--alog', default=ALOG)
    ap.add_argument('--emit-card', action='store_true',
                    help=f'write {os.path.relpath(CARD, REPO)}')
    args = ap.parse_args()

    r = load(args.alog)
    segs = segments(r)
    amb = sum(s['amb'] for s in segs) / len(segs)
    with open(EMPTY_CARD, encoding='utf-8') as fh:
        empty = json.load(fh)

    print('=== steady windows (SV and fan both constant) ===')
    print(f"{'window':>15} {'fan':>4} {'SV':>4} {'heat %':>7} {'sd':>5} {'BT':>6} "
          f"{'IN-SV':>6}")
    for s in segs:
        print(f"{s['t'][0]:6.0f}-{s['t'][1]:<6.0f} {s['fan']:4.0f} {s['sv']:4.0f} "
              f"{s['heat']:7.2f} {s['sd']:5.2f} {s['bt']:6.1f} {s['in_err']:+6.2f}")
    print(f"loaded {r['weight'][0]:.0f} -> {r['weight'][1]:.0f} {r['weight'][2]}, "
          f'ambient {amb:.1f} degC, {len(segs)} windows, '
          f'fan {min(s["fan"] for s in segs):.0f}-{max(s["fan"] for s in segs):.0f}, '
          f'SV {min(s["sv"] for s in segs):.0f}-{max(s["sv"] for s in segs):.0f}')

    print('\n=== does the empty-chamber map transfer to a loaded chamber? ===')
    print(f"   {empty['model']}")
    print(f"   c0 {empty['c0']:+.4f}  c_fan {empty['c_fan']:+.4f}  "
          f"c_sv {empty['c_sv']:+.4f}  c_fansv {empty['c_fansv']:+.4f}   "
          f"(roast 47, empty, fit box fan {empty['fit_box']['fan'][0]:.0f}-"
          f"{empty['fit_box']['fan'][1]:.0f} / SV {empty['fit_box']['sv'][0]}-"
          f"{empty['fit_box']['sv'][1]})")
    errs = []
    for s in segs:
        p = predict(empty, s['fan'], s['sv'])
        errs.append(p - s['heat'])
        flag = '  (extrapolated in SV)' if s['sv'] > empty['fit_box']['sv'][1] else ''
        print(f"   fan {s['fan']:3.0f} SV {s['sv']:3.0f}: measured {s['heat']:5.1f}  "
              f"empty map {p:5.1f}   {p - s['heat']:+6.2f}{flag}")
    bias = sum(errs) / len(errs)
    rms = (sum(e * e for e in errs) / len(errs)) ** 0.5
    print(f'   bias {bias:+.2f} %, rms {rms:.2f} %, worst {max(errs, key=abs):+.2f} % '
          f"-- against the empty run's own residual of {empty['resid_rms_pct']:.2f} %")

    print('\n=== fan slope, per setpoint ===')
    print('   the quantity FF SLOPE corrects, and the one a bean bed should move')
    print(f"   {'SV':>4} {'fan':>9} {'measured':>9} {'empty map':>10} {'ratio':>7}")
    slopes = []
    for i, s in enumerate(segs):
        for t2 in segs[i + 1:]:
            if t2['sv'] != s['sv'] or t2['fan'] == s['fan'] or t2['t'][0] - s['t'][1] > 90:
                continue
            d = (t2['heat'] - s['heat']) / (t2['fan'] - s['fan'])
            de = empty['c_fan'] + empty['c_fansv'] * s['sv'] / 100.0
            slopes.append((s['sv'], d, de))
            print(f"   {s['sv']:4.0f} {s['fan']:4.0f}->{t2['fan']:<4.0f} "
                  f"{d:9.3f} {de:10.3f} {d / de:7.2f}   %/fan-unit")
    byv = {}
    for sv, d, de in slopes:
        byv.setdefault(sv, []).append(d)
    pts = sorted((sv, sum(v) / len(v)) for sv, v in byv.items())
    print(f'   mean measured/empty ratio '
          f'{sum(d / de for _, d, de in slopes) / len(slopes):.3f}')
    if len(pts) >= 3:
        print('\n   is slope(SV) a line?  three setpoints is the smallest design that can tell')
        rows = [{'sv': sv, 'y': y} for sv, y in pts]
        b, srms, sres = ols(rows, [ONE, lambda q: q['sv'] / 100.0], y='y')
        for (sv, y), e in zip(pts, sres):
            print(f'      SV {sv:3.0f}: {y:6.3f}   line {y - e:6.3f}   {-e:+6.3f}')
        print(f'      slope(SV) = {b[0]:+.4f} {b[1]:+.4f}*SV/100   rms {srms:.4f} '
              f'%/fan-unit over {len(pts)} points')
        print(f'      empty      = {empty["c_fan"]:+.4f} {empty["c_fansv"]:+.4f}*SV/100')

    print('\n=== loaded refit ===')
    fits = {}
    b, arms, _ = ols(segs, [ONE, FAN, SV])
    fits['affine'] = (b, arms)
    print(f'   affine    heat = {b[0]:+.2f} {b[1]:+.4f}*fan {b[2]:+.4f}*SV'
          f'{"":26s} rms {arms:.2f} %')
    bi, irms, _ = ols(segs, [ONE, FAN, SV, FANSV])
    fits['product'] = (bi, irms)
    print(f'   +product  heat = {bi[0]:+.2f} {bi[1]:+.4f}*fan {bi[2]:+.4f}*SV '
          f'{bi[3]:+.4f}*fan*SV/100  rms {irms:.2f} %')
    print(f'   noise floor: sd of heat within a window is '
          f'{min(s["sd"] for s in segs):.2f}-{max(s["sd"] for s in segs):.2f} %')
    print('   NOTE the loaded design varies fan over only 60-70 and confounds fan')
    print('   level with setpoint (66 only at SV 215/245, 70 only at SV 190), so the')
    print('   refit is far less identified than roast 47 and is a check, not a')
    print('   replacement.  What it can settle is the *ratio*, which is FF SLOPE.')

    print('\n=== FF SLOPE recommendation ===')
    for sv, y in pts:
        de = empty['c_fan'] + empty['c_fansv'] * sv / 100.0
        k = y / de
        print(f'   at SV {sv:3.0f}: FF SLOPE {y:.3f}  -> k = {k:.3f}, '
              f'c_fan {empty["c_fan"] * k:+.4f}, c_fansv {empty["c_fansv"] * k:+.4f}')

    print('\n=== pooled fit: roast 47 (empty) + roast 48 (loaded) ===')
    print('   the two runs each cover a box the other does not -- roast 47 spans')
    print('   fan 58-80 at SV 145/185, roast 48 spans SV 140-245 at fan 60-70 --')
    print('   so every disagreement above is one extrapolation against another.')
    print('   Pooled, they cover the box a roast actually uses.')
    try:
        r47 = load(ALOG47)
    except SystemExit:
        r47 = None
    pooled_card = None
    if r47 is None:
        print('   roast 47 unavailable; skipped')
    else:
        # roast 47's autoDROP excursion is not the experiment (roast47_ff.py LOST)
        s47 = [q for q in segments(r47) if q['t'][1] <= 601.0 or q['t'][0] >= 730.0]
        for q in s47:
            q['loaded'] = 0.0
        for q in segs:
            q['loaded'] = 1.0
        pool = s47 + segs
        print(f'   {len(s47)} empty + {len(segs)} loaded = {len(pool)} windows, '
              f'fan {min(q["fan"] for q in pool):.0f}-{max(q["fan"] for q in pool):.0f}, '
              f'SV {min(q["sv"] for q in pool):.0f}-{max(q["sv"] for q in pool):.0f}')
        bp, prms, _ = ols(pool, [ONE, FAN, SV, FANSV])
        print(f'   pooled    heat = {bp[0]:+.2f} {bp[1]:+.4f}*fan {bp[2]:+.4f}*SV '
              f'{bp[3]:+.4f}*fan*SV/100  rms {prms:.2f} %')
        bl, lrms, _ = ols(pool, [ONE, FAN, SV, FANSV, lambda q: q['loaded']])
        print(f'   + a load *offset*:      {bl[4]:+.2f} %          rms {lrms:.2f} %')
        bs, srms, _ = ols(pool, [ONE, FAN, SV, FANSV,
                                 lambda q: q['loaded'] * q['fan'] * q['sv'] / 100.0])
        print(f'   + a load x fan x SV:    {bs[4]:+.4f}       rms {srms:.2f} %')
        print('   Read these carefully.  A load *offset* is absorbed by the inner')
        print("   loop's integral trim within seconds and costs nothing; only a change")
        print('   in the fan *sensitivity* survives, and that is what FF SLOPE corrects.')
        print('   The two are also weakly separable here: the loaded run is the only')
        print('   source of SV > 185 and the empty run the only source of fan < 60 or')
        print('   > 70, so the indicator carries some of that, not load alone.')
        print(f"   pooled vs the flashed v0.20.0 map, over the box the cascade uses:")
        pooled = {'c0': bp[0], 'c_fan': bp[1], 'c_sv': bp[2], 'c_fansv': bp[3]}
        print(f"      {'fan':>4} {'SV':>4} {'v0.20.0':>8} {'pooled':>8} {'delta':>7}")
        for fan in (58, 64, 70):
            for sv in (150, 200, 250):
                a_, b_ = predict(empty, fan, sv), predict(pooled, fan, sv)
                print(f'      {fan:4d} {sv:4d} {a_:8.1f} {b_:8.1f} {b_ - a_:+7.1f}')
        fits['pooled'] = (bp, prms)
        pooled_card = {
            'sources': ['airRoaster_47.alog (empty)', 'airRoaster_48.alog (400 g)'],
            'n_windows': len(pool),
            'c0': bp[0], 'c_fan': bp[1], 'c_sv': bp[2], 'c_fansv': bp[3],
            'resid_rms_pct': prms,
            'fit_box': {'fan': [min(q['fan'] for q in pool), max(q['fan'] for q in pool)],
                        'sv': [min(q['sv'] for q in pool), max(q['sv'] for q in pool)]},
            'load_offset_pct': bl[4], 'load_offset_resid_rms_pct': lrms,
            'load_fansv_term': bs[4], 'load_fansv_resid_rms_pct': srms,
            'max_abs_delta_vs_flashed_pct': max(
                abs(predict(pooled, f, v) - predict(empty, f, v))
                for f in (58, 64, 70) for v in (150, 200, 250)),
            'note': 'The union of both characterisation runs, on one estimator, '
                    'over the box the cascade actually uses. This is the fit to '
                    'flash if feedforward() is ever recalibrated; as of roast 48 '
                    'it differs from the flashed v0.20.0 map by under 2 % '
                    'everywhere in that box, so there is nothing to do.',
        }

    print('\n=== the inner loop, with feedforward() live for the first time ===')
    def quiet(x, in_guard):
        # the guard opens FILTER seconds *before* each step: the moving average
        # smears a transition backwards, so the sample before it is not quiet
        return (all(not (-FILTER <= x - m < GUARD) for m, _ in r['fan_events'])
                and all(not (-FILTER <= x - m < in_guard) for m in r['sv_steps']))

    for lab, lo, g in (
            ("whole run, 25 s guard (roast 47's figure)", 0.0, GUARD),
            ('ramp only, 0-165 s (SV moves every 5 s)', 0.0, GUARD),
            ('flat blocks only, 165 s-DROP', BLOCKS, IN_GUARD)):
        hi = BLOCKS if 'ramp only' in lab else r['drop'] - 2
        q = [k for k, x in enumerate(r['t'])
             if lo < x < hi and r['SV'][k] > 0 and quiet(x, g)]
        err = [r['IN'][k] - r['SV'][k] for k in q]
        print(f'   {lab}: {len(err)} samples, mean '
              f'{sum(err) / len(err):+.2f}, rms '
              f'{(sum(e * e for e in err) / len(err)) ** 0.5:.2f}, worst '
              f'{max(err, key=abs):+.2f} degC')
    print('   the steady figure is the IN-SV column in the window table above: '
          'every one of the 14 windows is inside +-0.30 degC.')

    print('\n   settling after each commanded inlet step (the plant, not the map):')
    for m in r['sv_steps']:
        if m < BLOCKS or m >= r['drop']:
            continue
        k0 = min(range(len(r['t'])), key=lambda k: abs(r['t'][k] - m))
        tgt = next(r['SV'][k] for k in range(k0, len(r['t'])) if r['t'][k] > m + FILTER)
        was = r['IN'][k0 - 3]
        for k in range(k0, len(r['t'])):
            if abs(r['IN'][k] - tgt) < 2.0:
                print(f'      {m:5.0f}s  SV {was:5.1f} -> {tgt:5.0f} '
                      f'({tgt - was:+6.1f} degC): |IN-SV| < 2 at '
                      f'+{r["t"][k] - m:.0f} s')
                break
    print('   worst inlet excursion in the 40 s after each fan step '
          '-- what feedforward() exists to remove:')
    for x, v in r['fan_events'][1:]:
        prev = [pv for px, pv in r['fan_events'] if px < x][-1]
        if v == prev or x < GUARD or x > r['drop']:
            continue
        # the window must close at the next inlet step, or it reports that
        # step's 95 degC ramp as if the fan had caused it
        nxt = min([m for m in r['sv_steps'] if m > x] + [r['drop']])
        end = min(x + 40.0, nxt - FILTER)
        w = [k for k, xx in enumerate(r['t']) if x <= xx <= end and r['SV'][k] > 0]
        if not w:
            continue
        k = max(w, key=lambda k: abs(r['IN'][k] - r['SV'][k]))
        h = [r['HT'][j] for j in w[:6]]
        flat = all(abs(r['SV'][j] - r['SV'][w[0]]) < 0.5 for j in w)
        print(f'      {x:5.0f}s  fan {prev:3d} -> {v:3d}   '
              f'{r["IN"][k] - r["SV"][k]:+6.2f} degC at +{r["t"][k] - x:.0f} s '
              f'(over {end - x:.0f} s)   heat {h[0]:.0f} -> {max(h):.0f} '
              f'within {len(h) - 1} s'
              f'{"" if flat else "   [setpoint still ramping -- not attributable]"}')

    if args.emit_card:
        b, rms_ = fits['product']
        card = {
            '_comment': 'Loaded feedforward() check. Generated by '
                        'tools/analysis/roast48_ff.py --emit-card.',
            'generated': _dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'source': os.path.basename(args.alog),
            'load_g': r['weight'][0],
            'model': 'heat% = c0 + c_fan*fan + c_sv*SV + c_fansv*fan*SV/100',
            'c0': b[0], 'c_fan': b[1], 'c_sv': b[2], 'c_fansv': b[3],
            'resid_rms_pct': rms_,
            'fit_box': {'fan': [min(s['fan'] for s in segs), max(s['fan'] for s in segs)],
                        'sv': [min(s['sv'] for s in segs), max(s['sv'] for s in segs)]},
            'ambient_degC': amb,
            'n_windows': len(segs),
            'empty_map_transfer': {
                'card': os.path.basename(EMPTY_CARD),
                'bias_pct': bias, 'rms_pct': rms,
                'worst_pct': max(errs, key=abs),
                'fan_slope_ratio_loaded_over_empty':
                    sum(d / de for _, d, de in slopes) / len(slopes),
                'per_sv_slope': {str(int(sv)): y for sv, y in pts},
            },
            'pooled': pooled_card if r47 is not None else None,
            'note': 'NOT a replacement for ff_roast47.json. Fan moved only over '
                    '60-70 and is confounded with setpoint, so this refit is weakly '
                    'identified; its value is the transfer check and the fan-slope '
                    'ratio that FF SLOPE would apply.',
        }
        with open(CARD, 'w', encoding='utf-8') as fh:
            json.dump(card, fh, indent=2)
            fh.write('\n')
        print(f'\nwritten {CARD}')


if __name__ == '__main__':
    main()
