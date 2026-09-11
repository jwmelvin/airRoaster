#!/usr/bin/env python3
"""Refit `feedforward()` from roast 47 (Test A), and check what the run cost.

Roast 47 is the first characterisation run: an empty roaster, PID off, with the
inlet step sequence and the fan sweep both replayed from
``artisan/charstep_empty_fan.alog``.  It is the first data set on this project in
which **fan and inlet setpoint are varied independently over a real range** --
six fan levels 58-80 crossed against 145 and 185 degC -- which is what runbook
step 8 needs and what the five preheat fan steps behind the current proposal
could not give.

Unlike the rest of this directory this module is **standard library only**.  The
regression is nine points and three parameters; numpy would be gratuitous, and
staying stdlib means the tool runs without the venv the README describes.

Usage
-----
``python3 tools/analysis/roast47_ff.py`` runs every section.
``--emit-card`` writes ``tools/analysis/ff_roast47.json`` for the record.
"""

import argparse
import ast
import json
import os
import sys
import datetime as _dt

HOME = os.path.expanduser('~')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, 'Documents/artisan/airRoaster_47.alog')
CARD = os.path.join(REPO, 'tools/analysis/ff_roast47.json')

# The autoDROP excursion: Artisan's built-in detector (canvas.py:5151) fired on
# the 601 s inlet step-down, ran the DROP button chain (INLET 0, heat 0) and the
# operator's cooldown took the fan to 100.  Everything between is not the
# experiment.
LOST = (601.0, 730.0)

SETTLE = 45.0     # a segment must be this long to be usable
WINDOW = 30.0     # average over the last WINDOW seconds before the next change
GUARD = 25.0      # quiet-window guard after any slider change

# roast 46's own preheat operating point, for the extrapolation check
CHECK_FAN, CHECK_SV, CHECK_HEAT = 60.0, 240.0, 55.0
OLD = (-30.62, 0.99, 0.0096)   # the model runbook step 8 proposed


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
    r['changes'] = sorted({x for x, ty, _ in ev if ty in (0, 2)})
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


def usable(x):
    return x <= LOST[0] or x >= LOST[1]


def segments(r):
    """Steady windows: SV and fan both constant, averaged before the next change."""
    out = []
    marks = r['changes']
    for a, b in zip(marks, marks[1:] + [r['t'][-1]]):
        if b - a < SETTLE or not (usable(a) and usable(b)):
            continue
        lo, hi = b - WINDOW, b - 2.0
        idx = [k for k, x in enumerate(r['t']) if lo <= x <= hi]
        if len(idx) < 10:
            continue
        mean = lambda key: sum(r[key][k] for k in idx) / len(idx)
        ht = mean('HT')
        sd = (sum((r['HT'][k] - ht) ** 2 for k in idx) / len(idx)) ** 0.5
        out.append({'t': (lo, hi), 'fan': float(hold(r['fan_events'], a)),
                    'sv': round(mean('SV')), 'heat': ht, 'sd': sd,
                    'bt': mean('BT'), 'amb': mean('amb')})
    return out


def ols(rows, cols, y='heat'):
    """Normal equations with Gaussian elimination.  Nine points; this is fine."""
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

    print('=== steady windows (SV and fan both constant) ===')
    print(f"{'window':>15} {'fan':>4} {'SV':>4} {'heat %':>7} {'sd':>5} {'BT':>6}")
    for s in segs:
        print(f"{s['t'][0]:6.0f}-{s['t'][1]:<6.0f} {s['fan']:4.0f} {s['sv']:4.0f} "
              f"{s['heat']:7.2f} {s['sd']:5.2f} {s['bt']:6.1f}")
    print(f'ambient {amb:.1f} degC, {len(segs)} windows, '
          f'fan {min(s["fan"] for s in segs):.0f}-{max(s["fan"] for s in segs):.0f}, '
          f'SV {min(s["sv"] for s in segs):.0f}-{max(s["sv"] for s in segs):.0f}')

    print('\n=== models ===')
    fits = {}
    b, rms, _ = ols(segs, [ONE, FAN, SV])
    fits['affine'] = (b, rms)
    print(f'affine      heat = {b[0]:+.2f} {b[1]:+.4f}*fan {b[2]:+.4f}*SV'
          f'{"":14s} rms {rms:.2f} %')
    bm, rmsm, _ = ols(segs, [ONE, lambda s: s['fan'] * (s['sv'] - amb) / 100.0])
    print(f'mass-flow   heat = {bm[0]:+.2f} {bm[1]:+.4f}*fan*(SV-{amb:.0f})/100'
          f'{"":11s} rms {rmsm:.2f} %')
    bi, rmsi, resi = ols(segs, [ONE, FAN, SV, FANSV])
    fits['product'] = (bi, rmsi)
    print(f'+product    heat = {bi[0]:+.2f} {bi[1]:+.4f}*fan {bi[2]:+.4f}*SV '
          f'{bi[3]:+.4f}*fan*SV/100   rms {rmsi:.2f} %')
    fan0 = -bi[2] / bi[3] * 100.0    # fan level the product term pivots about
    sv0 = -bi[1] / bi[3] * 100.0     # SV the product term pivots about
    print(f'            = {bi[3] / 100:.6f}*(fan-{fan0:.1f})*(SV-{sv0:.1f}) '
          f'{bi[0] - bi[1] * bi[2] / bi[3] * 100:+.1f}')
    print(f'measurement noise floor: sd of heat within a window is '
          f'{min(s["sd"] for s in segs):.2f}-{max(s["sd"] for s in segs):.2f} %')

    print('\n=== against the model runbook step 8 proposed ===')
    print(f'   heat = {OLD[0]} {OLD[1]:+}*fan {OLD[2]:+}*SV   '
          '(five preheat fan steps, state-history-cascade.md § Roast 46)')
    worst = 0.0
    for s in segs:
        pred = OLD[0] + OLD[1] * s['fan'] + OLD[2] * s['sv']
        worst = max(worst, abs(pred - s['heat']))
        print(f"   fan {s['fan']:3.0f} SV {s['sv']:3.0f}: measured {s['heat']:5.1f}  "
              f'proposed {pred:5.1f}   {pred - s["heat"]:+6.1f}')
    print(f'   worst error {worst:.1f} %; the SV coefficient is '
          f'{fits["affine"][0][2] / OLD[2]:.0f}x too small')

    print('\n=== extrapolation to the roast operating point ===')
    print(f'   roast 46 preheat measured {CHECK_HEAT:.0f} % at fan {CHECK_FAN:.0f} / '
          f'SV {CHECK_SV:.0f} (outside the fitted box)')
    for name, (b, _) in fits.items():
        p = b[0] + b[1] * CHECK_FAN + b[2] * CHECK_SV + \
            (b[3] * CHECK_FAN * CHECK_SV / 100.0 if len(b) > 3 else 0.0)
        print(f'   {name:8s} predicts {p:5.1f} %   {p - CHECK_HEAT:+5.1f}')

    print('\n=== the inner loop ===')
    q = [k for k, x in enumerate(r['t'])
         if usable(x) and 0 < x < r['t'][-1] - 2 and r['SV'][k] > 0
         and all(not (0 <= x - m < GUARD) for m in r['changes'])]
    err = [r['IN'][k] - r['SV'][k] for k in q]
    rms_in = (sum(e * e for e in err) / len(err)) ** 0.5
    print(f'   tracking over {len(err)} quiet samples: mean {sum(err) / len(err):+.2f}, '
          f'rms {rms_in:.2f} degC')
    print('   worst inlet excursion in the 40 s after each fan step '
          '-- this is what feedforward() exists to remove:')
    for x, v in r['fan_events'][1:]:
        prev = [pv for px, pv in r['fan_events'] if px < x][-1]
        # skip the duplicate event at CHARGE and anything before the loop settles
        if not usable(x) or v == prev or x < GUARD:
            continue
        w = [k for k, xx in enumerate(r['t']) if x <= xx <= x + 40 and r['SV'][k] > 0]
        if not w:
            continue
        k = max(w, key=lambda k: abs(r['IN'][k] - r['SV'][k]))
        print(f'      {x:5.0f}s  fan {prev:3d} -> {v:3d}   '
              f'{r["IN"][k] - r["SV"][k]:+6.2f} degC at +{r["t"][k] - x:.0f} s')

    print('\n=== what the autoDROP cost ===')
    lost = [k for k, x in enumerate(r['t']) if LOST[0] <= x <= LOST[1]]
    span = r['t'][-1]
    kept = (LOST[0] + (span - LOST[1])) / span * 100.0
    print(f'   fired at 605 s on the 601 s inlet step-down; inlet '
          f'{max(r["IN"][k] for k in lost):.0f} -> {min(r["IN"][k] for k in lost):.0f}, '
          f'BT {max(r["BT"][k] for k in lost):.0f} -> {min(r["BT"][k] for k in lost):.0f} degC')
    print(f'   one steady window lost (fan 80 / SV 145); {kept:.0f} % of the run usable')

    if args.emit_card:
        b, rms = fits['product']
        card = {
            '_comment': 'feedforward() refit. Generated by tools/analysis/roast47_ff.py --emit-card.',
            'generated': _dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'source': os.path.basename(args.alog),
            'model': 'heat% = c0 + c_fan*fan + c_sv*SV + c_fansv*fan*SV/100',
            'c0': b[0], 'c_fan': b[1], 'c_sv': b[2], 'c_fansv': b[3],
            'resid_rms_pct': rms,
            'affine': dict(zip(('c0', 'c_fan', 'c_sv'), fits['affine'][0]),
                           resid_rms_pct=fits['affine'][1]),
            'fit_box': {'fan': [min(s['fan'] for s in segs), max(s['fan'] for s in segs)],
                        'sv': [min(s['sv'] for s in segs), max(s['sv'] for s in segs)]},
            'ambient_degC': amb,
            'n_windows': len(segs),
            'note': 'Empty roaster. The inlet TC is upstream of the bed, so the heat '
                    'needed to reach a given inlet temperature should not depend on a '
                    'load -- but that has not been tested and the loaded doublets are '
                    'the check.',
        }
        with open(CARD, 'w', encoding='utf-8') as fh:
            json.dump(card, fh, indent=2)
            fh.write('\n')
        print(f'\nwritten {CARD}')


if __name__ == '__main__':
    main()
