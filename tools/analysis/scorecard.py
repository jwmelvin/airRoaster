#!/usr/bin/env python3
"""One roast against the background it ran: the fixed residual vector that
playbook-model-feedback.md works from.

The engine (``make_background.py`` and what it reads) turns a roast spec into a
background.  Whether the engine is right is the difference between what that
background said and what the bed did, **read the same way on every roast** --
that is all this prints.  It fits nothing and decides nothing.

    python3 tools/analysis/scorecard.py 63            # one roast, full card
    python3 tools/analysis/scorecard.py 56 60 62 63   # the table across roasts
    python3 tools/analysis/scorecard.py 64 --bkg artisan/profile_462g_m5C_space_v9.alog

The background is the one the log names in ``backgroundpath`` unless ``--bkg``
overrides it.  ``e = BT - background``, on the CHARGE clock of each.

Three things it deliberately reports rather than hides:

* **the entry slope over 85-115 s.**  Outside +/-2 degC/min the 120-230 s
  window is carrying a charge transient and must not be scored (roasts 57, 60).
* **the spec errors at the marks**, which is what the roast-space effort is
  specified in: when DRY END and FCs happened against where the curve put those
  temperatures, and the measured slope at FCs against the curve's.
* **what the log cannot vouch for**: ``greens_temp`` is typed by hand (roast 63
  says 0.0 for a frozen charge), and a missing weight-out reads as 100 % loss.

Stdlib only -- no venv needed.
"""

from __future__ import annotations

import argparse
import ast
import bisect
import os

LOGDIR = os.path.expanduser('~/Documents/artisan')
DRY_BT = 149.6


def load(path):
    with open(path) as f:
        return ast.literal_eval(f.read())


def clock(d):
    ci = d['timeindex'][0]
    if ci < 0:
        raise SystemExit('no CHARGE mark')
    t0 = d['timex'][ci]
    return [x - t0 for x in d['timex']]


def at(ts, ys, x):
    i = bisect.bisect_left(ts, x)
    if i <= 0 or i >= len(ts):
        return None
    a = (x - ts[i - 1]) / (ts[i] - ts[i - 1])
    return ys[i - 1] + a * (ys[i] - ys[i - 1])


def slope(ts, ys, x0, x1):
    a, b = at(ts, ys, x0), at(ts, ys, x1)
    return None if a is None or b is None else (b - a) / (x1 - x0) * 60.0


def crossing(ts, ys, level, after=30.0):
    for i in range(1, len(ts)):
        if ts[i] > after and ys[i - 1] < level <= ys[i]:
            a = (level - ys[i - 1]) / (ys[i] - ys[i - 1])
            return ts[i - 1] + a * (ts[i] - ts[i - 1])
    return None


def channel(d, name):
    n1, n2 = d.get('extraname1', []), d.get('extraname2', [])
    if name in n1:
        return d['extratemp1'][n1.index(name)]
    if name in n2:
        return d['extratemp2'][n2.index(name)]
    return None


def fan_events(d, t):
    et = d.get('etypes', [])
    out = []
    for k, i in enumerate(d.get('specialevents', [])):
        tp = d['specialeventstype'][k]
        if tp < len(et) and et[tp].lower().startswith('air'):
            out.append((t[i], round((d['specialeventsvalue'][k] - 1) * 10)))
    return out


def integral(ts, ys, t0, t1, fn, step=0.5):
    s, x = 0.0, t0
    while x < t1 - 1e-9:
        h = min(step, t1 - x)
        a, b = at(ts, ys, x), at(ts, ys, x + h)
        if a is None or b is None:
            return None
        s += 0.5 * (fn(a) + fn(b)) * h
        x += h
    return s


def score(rid, bkg_path=None):
    path = rid if os.path.exists(str(rid)) else os.path.join(LOGDIR, f'airRoaster_{rid}.alog')
    d = load(path)
    t, bt = clock(d), d['temp2']
    ti = d['timeindex']
    mark = lambda k: (t[ti[k]], bt[ti[k]]) if ti[k] > 0 else (None, None)
    bp = bkg_path or d.get('backgroundpath') or ''
    r = {'roast': rid, 'coffee': d.get('plus_coffee'), 'bkg': os.path.basename(bp),
         'mass': d['weight'][0], 'greens': d.get('greens_temp'),
         'moisture': d.get('moisture_greens')}
    w = d['weight']
    r['loss'] = (w[0] - w[1]) / w[0] * 100 if w[0] and w[1] else None
    inlet = channel(d, 'Inlet')
    r['charge_bt'] = bt[ti[0]]
    r['inlet_pre'] = at(t, inlet, -2.0) if inlet else None
    fans = fan_events(d, t)
    r['fan'] = ' '.join(f'{v}@{x:.0f}' for x, v in fans if -30 <= x) or '--'
    i0 = ti[0]
    j = min(range(i0, min(i0 + 240, len(bt))), key=lambda k: bt[k])
    r['tp_t'], r['tp_bt'] = t[j], bt[j]

    b = None
    if bp and os.path.exists(bp):
        b = load(bp)
        tb, bb = clock(b), b['temp2']
        jb = min(range(len(bb)), key=lambda k: bb[k] if tb[k] < 120 else 1e9)
        r['tp_t_bkg'], r['tp_bt_bkg'] = tb[jb], bb[jb]
        e = lambda x: (None if at(t, bt, x) is None or at(tb, bb, x) is None
                       else at(t, bt, x) - at(tb, bb, x))
        for x in (45, 60, 90, 120, 180, 240, 300, 360):
            r[f'e{x}'] = e(x)
        a, c = e(85), e(115)
        r['entry'] = None if a is None or c is None else (c - a) * 2.0
        win = [(e(x), x) for x in range(120, 231)]
        win = [p for p in win if p[0] is not None]
        if win:
            r['min_e'], r['min_t'] = min(win)
        de_t, _ = mark(1)
        fc_t, fc_bt = mark(2)
        if de_t is not None:
            c = crossing(tb, bb, DRY_BT)
            r['de_dt'] = None if c is None else de_t - c
        if fc_t is not None:
            c = crossing(tb, bb, fc_bt)
            r['fc_dt'] = None if c is None else fc_t - c
            r['ror_fc_bkg'] = slope(tb, bb, fc_t - 15, fc_t + 15)
            xs = [x for x in range(int(de_t or 200), int(fc_t)) if e(x) is not None]
            if xs:
                r['rms_mid'] = (sum(e(x) ** 2 for x in xs) / len(xs)) ** 0.5

    de_t, de_bt = mark(1)
    fc_t, fc_bt = mark(2)
    dr_t, dr_bt = mark(6)
    r['de_t'], r['fc_t'], r['fc_bt'], r['drop_t'], r['drop_bt'] = de_t, fc_t, fc_bt, dr_t, dr_bt
    if fc_t is not None:
        r['ror_fc'] = slope(t, bt, fc_t - 15, fc_t + 15)
        if dr_t is not None:
            r['dev_dt'], r['dev_dT'] = dr_t - fc_t, dr_bt - fc_bt
            for q in (2, 3):
                r[f'D{q}'] = integral(t, bt, fc_t, dr_t, lambda y: q ** ((y - fc_bt) / 10))
            if inlet:
                drv = [u - v for u, v in zip(inlet, bt)]
                r['drive_fc'] = at(t, drv, fc_t)
                # past the background's end the SV falls away (roast 63), so the
                # drive there is not the bed's doing: read it inside the curve
                end = dr_t - 3 if b is None else min(dr_t - 3, tb[-1] - 8)
                r['drive_end_t'] = end
                r['drive_drop'] = at(t, drv, end)
            if b is not None:
                xs = [x for x in range(int(fc_t), int(dr_t) - 2)
                      if at(tb, bb, x) is not None]
                if xs:
                    r['e_dev'] = sum(at(t, bt, x) - at(tb, bb, x) for x in xs) / len(xs)
    return r


def f(v, spec='.1f', plus=False):
    if v is None:
        return '--'
    if isinstance(v, str):
        return v
    return format(v, ('+' if plus else '') + spec)


CARD = [
    ('batch', lambda r: f"{f(r['mass'], '.0f')} g {r['coffee']}  greens {f(r['greens'])} (typed)  moisture {f(r['moisture'])}"),
    ('background', lambda r: r['bkg'] or '-- none found: pass --bkg'),
    ('charge', lambda r: f"BT {f(r['charge_bt'])}  inlet at -2 s {f(r['inlet_pre'])}  fan {r['fan']}"),
    ('TP', lambda r: f"{f(r['tp_bt'])} @ {f(r['tp_t'], '.0f')} s   (bkg {f(r.get('tp_bt_bkg'))} @ {f(r.get('tp_t_bkg'), '.0f')} s)"),
    ('e 45/60/90/120', lambda r: ' / '.join(f(r.get(k), '.2f', True) for k in ('e45', 'e60', 'e90', 'e120'))),
    ('entry slope 85-115', lambda r: f"{f(r.get('entry'), '.2f', True)} degC/min" + ('' if r.get('entry') is None or abs(r['entry']) <= 2 else '   <- OUTSIDE +/-2: do not score 120-230 s')),
    ('min e 120-230', lambda r: f"{f(r.get('min_e'), '.2f', True)} @ {f(r.get('min_t'), '.0f')} s"),
    ('e 180/240/300/360', lambda r: ' / '.join(f(r.get(k), '.2f', True) for k in ('e180', 'e240', 'e300', 'e360'))),
    ('rms e, DRY END-FCs', lambda r: f(r.get('rms_mid'), '.2f')),
    ('DRY END', lambda r: f"{f(r['de_t'], '.0f')} s   ({f(r.get('de_dt'), '.1f', True)} s against the curve)"),
    ('FCs', lambda r: f"{f(r['fc_bt'])} @ {f(r['fc_t'], '.0f')} s   ({f(r.get('fc_dt'), '.1f', True)} s against where the curve reaches that BT)"),
    ('slope at FCs', lambda r: f"{f(r.get('ror_fc'))} degC/min   (curve {f(r.get('ror_fc_bkg'))})"),
    ('development', lambda r: f"{f(r.get('dev_dt'), '.1f')} s  dT {f(r.get('dev_dT'), '.1f', True)}  D2 {f(r.get('D2'), '.0f')}  D3 {f(r.get('D3'), '.0f')}  mean e {f(r.get('e_dev'), '.2f', True)}"),
    ('drive FCs -> end', lambda r: f"{f(r.get('drive_fc'))} -> {f(r.get('drive_drop'))} degC of inlet over BT, read at {f(r.get('drive_end_t'), '.0f')} s"),
    ('DROP', lambda r: f"{f(r['drop_bt'])} @ {f(r['drop_t'], '.0f')} s"),
    ('weight loss', lambda r: f"{f(r['loss'], '.2f')} %" if r['loss'] is not None else '-- no weight out'),
]

COLS = [('roast', 'roast', '', 5), ('g', 'mass', '.0f', 4), ('TP', 'tp_bt', '.1f', 5),
        ('e60', 'e60', '+.1f', 5), ('e90', 'e90', '+.1f', 5), ('entry', 'entry', '+.1f', 6),
        ('min_e', 'min_e', '+.2f', 6), ('rms', 'rms_mid', '.2f', 5), ('DE_dt', 'de_dt', '+.0f', 5),
        ('FC_bt', 'fc_bt', '.1f', 6), ('FC_dt', 'fc_dt', '+.0f', 5), ('RoR_FC', 'ror_fc', '.1f', 6),
        ('dev_s', 'dev_dt', '.0f', 5), ('dev_dT', 'dev_dT', '+.1f', 6), ('D2', 'D2', '.0f', 4),
        ('loss%', 'loss', '.2f', 6)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('roasts', nargs='+', help='roast numbers or .alog paths')
    ap.add_argument('--bkg', help='background to score against (default: the log\'s backgroundpath)')
    a = ap.parse_args()
    rs = [score(int(x) if x.isdigit() else x, a.bkg) for x in a.roasts]
    if len(rs) == 1:
        r = rs[0]
        print(f"== roast {r['roast']} ==")
        for label, fn in CARD:
            print(f'   {label:<20} {fn(r)}')
        return
    print(' '.join(f'{h:>{w}}' for h, _, _, w in COLS))
    for r in rs:
        cells = []
        for _, k, spec, w in COLS:
            v = r.get(k)
            cells.append(f"{(format(v, spec) if spec and v is not None else ('--' if v is None else str(v))):>{w}}")
        print(' '.join(cells))


if __name__ == '__main__':
    main()
