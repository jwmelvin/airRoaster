#!/usr/bin/env python3
"""
downsample_logs.py

Condense airRoaster roast logs into a compact, chat-pasteable summary so a
whole run can be reviewed without shipping the raw arrays.

Input formats (auto-detected by extension, content-sniffed as fallback):
  .alog   Artisan profile/background (Python literal dict): timex/temp1/temp2
          plus extra-device channels, timeindex marks, special events.
  .csv    dashboard.html "Export CSV": time,IN,BT,SV,heat,fan,mode,P,I,D,FF.
  .txt    dashboard.html "Save log": "<ISO> [class] <raw>" lines. telem JSON
          samples become the data series; every non-telemetry line (sent
          commands, device log, errors, reports) is kept verbatim.

What comes out (stdout, plain text):
  - metadata: title/date/unit, sample count, duration, per-channel ranges
  - sparse exact sections: timeindex marks, special events, mode/fan/SV/fault
    transitions, non-telemetry log lines
  - the dense series reduced to --rows time buckets (bucket means; blank cell
    = no samples in that bucket) with a rate-of-rise column for the main temp
  - closed-loop tracking stats (IN vs SV): mean/RMS/max error, heat
    saturation, and a per-plateau breakdown where the SV holds steady

Examples:
    python3 downsample_logs.py roast.alog
    python3 downsample_logs.py airRoaster_data_2026-07-03.csv --rows 60
    python3 downsample_logs.py airRoaster_log_2026-07-03.txt --from 4:00 --to 9:30

Times accepted by --from/--to are seconds or m:ss, on the same clock the
output uses (CHARGE-relative for .alog, first-sample-relative otherwise).

No third-party dependencies (standard library only).
"""

import argparse
import ast
import csv
import json
import math
import re
import sys
from datetime import datetime


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------
def parse_clock(s):
    """'330', '5:30' or '1:05:30' -> seconds."""
    t = 0.0
    for part in s.split(':'):
        t = t * 60 + float(part)
    return t


def mmss(t):
    sign = '-' if t < 0 else ''
    m, s = divmod(int(round(abs(t))), 60)
    return '{}{}:{:02d}'.format(sign, m, s)


def fnum(v, prec=1):
    """Compact number: 1 decimal, trailing zeros stripped; None -> ''."""
    if v is None:
        return ''
    s = '{:.{}f}'.format(v, prec)
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return '0' if s == '-0' else s


def parse_iso(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


# --------------------------------------------------------------------------
# Downsampling: fixed time buckets, mean of the samples that land in each.
# Channels are (name, times, values) with values numeric or None.
# --------------------------------------------------------------------------
def bucket_means(times, vals, t0, t1, n):
    sums = [0.0] * n
    cnts = [0] * n
    w = (t1 - t0) / n
    for t, v in zip(times, vals):
        if v is None or t < t0 or t > t1:
            continue
        k = min(n - 1, int((t - t0) / w)) if w > 0 else 0
        sums[k] += v
        cnts[k] += 1
    return [sums[k] / cnts[k] if cnts[k] else None for k in range(n)]


def render_table(chans, t0, t1, rows, ror_name=None):
    """CSV-style table of bucket means; optional d<chan>/min RoR column
    from centered differences of the bucket means."""
    w = (t1 - t0) / rows
    cols = [(name, bucket_means(tt, vv, t0, t1, rows)) for name, tt, vv in chans]

    ror = None
    if ror_name:
        for name, m in cols:
            if name == ror_name:
                ror = [None] * rows
                for k in range(rows):
                    lo = k - 1 if k > 0 else k
                    hi = k + 1 if k < rows - 1 else k
                    if hi > lo and m[lo] is not None and m[hi] is not None:
                        ror[k] = (m[hi] - m[lo]) / ((hi - lo) * w) * 60.0
                break

    header = 't,' + ','.join(name for name, _ in cols)
    if ror is not None:
        header += ',d{}/min'.format(ror_name)
    lines = [header]
    for k in range(rows):
        cells = [mmss(t0 + k * w)] + [fnum(m[k]) for _, m in cols]
        if ror is not None:
            cells.append(fnum(ror[k]))
        lines.append(','.join(cells))
    return lines


def value_edges(times, vals, thresh):
    """(t, old, new) whenever a numeric channel steps by more than thresh."""
    out, prev = [], None
    for t, v in zip(times, vals):
        if v is None:
            continue
        if prev is None or abs(v - prev) > thresh:
            out.append((t, prev, v))
            prev = v
    return out


def str_edges(times, vals):
    out, prev = [], None
    for t, v in zip(times, vals):
        if not v:
            continue
        if v != prev:
            out.append((t, prev, v))
            prev = v
    return out


def edge_lines(label, edges, limit=24):
    """Render an edge list, or summarize it when it is dense (SV ramps)."""
    if not edges:
        return []
    if len(edges) > limit:
        return ['{}: {} changes {}..{} (ramping; see series)'.format(
            label, len(edges), mmss(edges[0][0]), mmss(edges[-1][0]))]
    parts = []
    for t, old, new in edges:
        new_s = fnum(new) if isinstance(new, float) else str(new)
        parts.append('{} {}'.format(mmss(t), new_s))
    return ['{}: {}'.format(label, ' | '.join(parts))]


# --------------------------------------------------------------------------
# Closed-loop tracking stats (the actual feedback signal for tuning).
# --------------------------------------------------------------------------
def tracking_stats(times, pv, sv, heat):
    pts = [(t, p - s) for t, p, s in zip(times, pv, sv)
           if p is not None and s is not None]
    if len(pts) < 5:
        return []
    es = [e for _, e in pts]
    mean = sum(es) / len(es)
    rms = math.sqrt(sum(e * e for e in es) / len(es))
    tmax, emax = max(pts, key=lambda p: abs(p[1]))
    lines = ['closed-loop IN vs SV: n={} ({}..{}), err mean {:+.1f}, '
             'rms {:.1f}, max {:+.1f} at {}'.format(
                 len(pts), mmss(pts[0][0]), mmss(pts[-1][0]),
                 mean, rms, emax, mmss(tmax))]

    if heat is not None:
        hs = [h for h, s in zip(heat, sv) if h is not None and s is not None]
        if hs:
            hi = sum(1 for h in hs if h >= 99.5) / len(hs) * 100
            lo = sum(1 for h in hs if h <= 0.5) / len(hs) * 100
            if hi >= 0.5 or lo >= 0.5:
                lines.append('heat saturation: {:.0f}% of loop time at 100, '
                             '{:.0f}% at 0'.format(hi, lo))

    lines += sv_segment_stats(times, pv, sv)
    return lines


def sv_segment_stats(times, pv, sv, min_dur=30.0):
    """Per-plateau error stats where the SV holds within +-0.5 for >=30 s.
    A continuously ramping SV yields no plateaus and no output."""
    lines, i, n = [], 0, len(times)
    while i < n:
        if sv[i] is None:
            i += 1
            continue
        j = i
        while (j + 1 < n and sv[j + 1] is not None
               and abs(sv[j + 1] - sv[i]) <= 0.5):
            j += 1
        if times[j] - times[i] >= min_dur:
            es = [(t, p - s) for t, p, s in
                  zip(times[i:j + 1], pv[i:j + 1], sv[i:j + 1])
                  if p is not None]
            if len(es) >= 3:
                vals = [e for _, e in es]
                mean = sum(vals) / len(vals)
                rms = math.sqrt(sum(e * e for e in vals) / len(vals))
                _, emax = max(es, key=lambda p: abs(p[1]))
                lines.append('  SV {} plateau {}..{}: err mean {:+.1f}, '
                             'rms {:.1f}, max {:+.1f}'.format(
                                 fnum(sv[i]), mmss(times[i]), mmss(times[j]),
                                 mean, rms, emax))
        i = j + 1
    return lines


# --------------------------------------------------------------------------
# Artisan .alog
# --------------------------------------------------------------------------
TIMEINDEX_NAMES = ['CHARGE', 'DRYe', 'FCs', 'FCe', 'SCs', 'SCe', 'DROP', 'COOL']


def event_internal_to_external(v):
    """Inverse of Artisan's events_external_to_internal_value."""
    if v == 0:
        return 0.0
    return (v - 1.0) * 10.0 if v > 0 else (v + 1.0) * 10.0


def load_alog(path):
    with open(path) as f:
        d = ast.literal_eval(f.read())

    timex = [float(t) for t in d.get('timex', [])]
    ti = list(d.get('timeindex', []))
    charge = 0.0
    if ti and isinstance(ti[0], int) and 0 <= ti[0] < len(timex):
        charge = timex[ti[0]]
    tt = [t - charge for t in timex]

    def clean(a):
        return [None if v is None or v == -1 else float(v) for v in a]

    chans = []
    for name, key in (('ET', 'temp1'), ('BT', 'temp2')):
        vals = clean(d.get(key, []))
        if any(v is not None for v in vals):
            chans.append((name, tt, vals))

    xt = d.get('extratimex', [])
    for i in range(len(d.get('extradevices', []))):
        times_i = ([t - charge for t in xt[i]]
                   if i < len(xt) and xt[i] else tt)
        for names_key, data_key in (('extraname1', 'extratemp1'),
                                    ('extraname2', 'extratemp2')):
            data = d.get(data_key, [])
            if i >= len(data):
                continue
            vals = clean(data[i])
            if not any(v is not None for v in vals):
                continue
            names = d.get(names_key, [])
            name = names[i] if i < len(names) and names[i] else \
                '{}[{}]'.format(data_key, i)
            chans.append((name, times_i, vals))

    meta = ['artisan .alog  title: {!r}'.format(d.get('title', '')),
            'date: {} {}  unit: {}  {} samples @ {:g}s, span {}..{} '
            '(t=0 at CHARGE)'.format(
                d.get('roastisodate', '?'), d.get('roasttime', '?'),
                d.get('mode', '?'), len(timex),
                float(d.get('samplinginterval', 0) or 0),
                mmss(tt[0]) if tt else '?', mmss(tt[-1]) if tt else '?')]

    sparse = []
    marks = []
    for k, idx in enumerate(ti[:8]):
        is_set = (idx > -1) if k == 0 else (idx > 0)
        if is_set and 0 <= idx < len(tt):
            marks.append('{} {}'.format(TIMEINDEX_NAMES[k], mmss(tt[idx])))
    if marks:
        sparse.append('marks: ' + ' | '.join(marks))

    ev = d.get('specialevents', [])
    if ev:
        etypes = d.get('etypes', [])
        tps = d.get('specialeventstype', [])
        vals = d.get('specialeventsvalue', [])
        strs = d.get('specialeventsStrings', [])
        sparse.append('events ({}):'.format(len(ev)))
        for k, idx in enumerate(ev[:60]):
            t = tt[idx] if 0 <= idx < len(tt) else 0.0
            tp = (etypes[tps[k]] if k < len(tps) and tps[k] < len(etypes)
                  else '?') or 'ev{}'.format(tps[k] if k < len(tps) else '?')
            label = strs[k] if k < len(strs) and strs[k] else \
                fnum(event_internal_to_external(vals[k])) if k < len(vals) else ''
            sparse.append('  {} {} {}'.format(mmss(t), tp, label))
        if len(ev) > 60:
            sparse.append('  ... {} more'.format(len(ev) - 60))

    chans = blank_no_setpoint(chans)
    ctl = control_channels(chans, ('Inlet', 'IN'), 'SV', ('Duty %', 'heat'))
    return meta, sparse, chans, ctl


def blank_no_setpoint(chans):
    """SV <= 0 means 'no setpoint' (firmware v0.15.1 semantics; Artisan's SV
    slider parks at 0 after playback) — blank it so tables, edges and
    tracking stats don't treat 0 degC as a target."""
    return [(name,
             tt,
             [None if v is not None and v <= 0 else v for v in vv]
             if name == 'SV' else vv)
            for name, tt, vv in chans]


def control_channels(chans, pv_names, sv_name, heat_names):
    """Pick PV/SV/heat channels by name for tracking stats; the PV and SV
    must share a time base (same sample count) to be compared."""
    by_name = {name: (tt, vv) for name, tt, vv in chans}
    pv = next((by_name[n] for n in pv_names if n in by_name), None)
    sv = by_name.get(sv_name)
    if not pv or not sv or len(pv[0]) != len(sv[0]):
        return None
    heat = next((by_name[n][1] for n in heat_names if n in by_name), None)
    return pv[0], pv[1], sv[1], heat


# --------------------------------------------------------------------------
# dashboard.html CSV export: time,IN,BT,SV,heat,fan,mode,P,I,D,FF
# --------------------------------------------------------------------------
def load_dash_csv(path):
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit('{}: empty CSV'.format(path))

    t0 = parse_iso(rows[0]['time'])
    tt = [(parse_iso(r['time']) - t0).total_seconds() for r in rows]

    def col(name):
        out = []
        for r in rows:
            s = (r.get(name) or '').strip()
            try:
                out.append(float(s))
            except ValueError:
                out.append(None)
        return out

    numeric = {name: col(name)
               for name in ('IN', 'BT', 'SV', 'heat', 'fan',
                            'P', 'I', 'D', 'FF')}
    # SV <= 0 is "no setpoint" (see blank_no_setpoint).
    numeric['SV'] = [None if v is not None and v <= 0 else v
                     for v in numeric['SV']]
    modes = [(r.get('mode') or '').strip() for r in rows]

    meta = ['dashboard CSV  start: {}  {} samples, span {}..{}'.format(
        rows[0]['time'], len(rows), mmss(tt[0]), mmss(tt[-1]))]

    sparse = []
    sparse += edge_lines('mode', str_edges(tt, modes))
    sparse += edge_lines('fan', value_edges(tt, numeric['fan'], 0.5))
    sparse += edge_lines('SV steps', value_edges(tt, numeric['SV'], 2.0))

    # fan and mode are fully described by the edge lines; keep them out of
    # the table to save columns.
    chans = [(n, tt, numeric[n])
             for n in ('IN', 'BT', 'SV', 'heat', 'P', 'I', 'D', 'FF')
             if any(v is not None for v in numeric[n])]
    ctl = (tt, numeric['IN'], numeric['SV'], numeric['heat'])
    return meta, sparse, chans, ctl


# --------------------------------------------------------------------------
# dashboard.html saved log: "<ISO> [class] <raw>"; telem lines carry samples.
# --------------------------------------------------------------------------
LOG_LINE = re.compile(r'^(\S+)\s+\[(\w+)\]\s?(.*)$')

TELEM_FIELDS = (('IN', 'IN'), ('BT', 'BT'), ('ET', 'ET'), ('SV', 'sv'),
                ('heat', 'heat'), ('heatReq', 'heatReq'), ('fan', 'fan'),
                ('P', 'p'), ('I', 'i'), ('D', 'd'), ('FF', 'ff'))


def load_dash_txt(path):
    telem, other = [], []
    with open(path) as f:
        for raw in f:
            raw = raw.rstrip('\n')
            if not raw:
                continue
            m = LOG_LINE.match(raw)
            if not m:
                other.append((None, raw))
                continue
            ts, cls, text = m.groups()
            try:
                t = parse_iso(ts)
            except ValueError:
                other.append((None, raw))
                continue
            data = None
            if cls == 'telem':
                try:
                    data = json.loads(text).get('data')
                except (ValueError, AttributeError):
                    data = None
            if data is not None and 'periodMs' not in data:
                telem.append((t, data))
            else:
                other.append((t, '[{}] {}'.format(cls, text)))

    if not telem and not other:
        raise SystemExit('{}: no parseable lines'.format(path))

    base = telem[0][0] if telem else next(t for t, _ in other if t)
    tt = [(t - base).total_seconds() for t, _ in telem]

    def num(d, key):
        v = d.get(key)
        return float(v) if isinstance(v, (int, float)) else None

    series = {name: [num(d, key) for _, d in telem]
              for name, key in TELEM_FIELDS}
    modes = [str(d.get('mode', '')) for _, d in telem]
    # SV is only meaningful in closed loop, and SV <= 0 is "no setpoint"
    # (see blank_no_setpoint); blank both.
    series['SV'] = [sv if md == 'inlet' and sv is not None and sv > 0
                    else None
                    for sv, md in zip(series['SV'], modes)]
    # heatReq only earns a column when the interlock cap makes it differ.
    if not any(a is not None and b is not None and abs(a - b) > 0.5
               for a, b in zip(series['heat'], series['heatReq'])):
        del series['heatReq']

    meta = ['dashboard log  start: {}  {} telem samples, span {}..{}, '
            '{} other lines'.format(
                telem[0][0].isoformat() if telem else '?', len(telem),
                mmss(tt[0]) if tt else '?', mmss(tt[-1]) if tt else '?',
                len(other))]

    sparse = []
    sparse += edge_lines('mode', str_edges(tt, modes))
    sparse += edge_lines('fan', value_edges(tt, series['fan'], 0.5))
    sparse += edge_lines('SV steps', value_edges(tt, series['SV'], 2.0))
    for flt in ('fltIN', 'fltBT'):
        vals = [num(d, flt) for _, d in telem]
        if any(v for v in vals):
            sparse += edge_lines(flt, value_edges(tt, vals, 0.5))

    if other:
        sparse.append('non-telemetry lines ({}):'.format(len(other)))
        shown = other if len(other) <= 120 else other[:80] + other[-40:]
        for k, (t, text) in enumerate(shown):
            if len(other) > 120 and k == 80:
                sparse.append('  ... {} lines omitted ...'
                              .format(len(other) - 120))
            stamp = mmss((t - base).total_seconds()) if t else '?'
            sparse.append('  {} {}'.format(stamp, text))

    order = ('IN', 'BT', 'ET', 'SV', 'heat', 'heatReq', 'P', 'I', 'D', 'FF')
    chans = [(n, tt, series[n]) for n in order
             if n in series and any(v is not None for v in series[n])]
    ctl = (tt, series['IN'], series['SV'], series['heat'])
    return meta, sparse, chans, ctl


# --------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------
def report(path, meta, sparse, chans, ctl, args):
    out = ['== {} =='.format(path)]
    out += meta

    if not chans:
        out += sparse
        out.append('(no plottable channels)')
        return out

    lo = min(tt[0] for _, tt, _ in chans if tt)
    hi = max(tt[-1] for _, tt, _ in chans if tt)
    t0 = args.t_from if args.t_from is not None else lo
    t1 = args.t_to if args.t_to is not None else hi
    if t1 <= t0:
        raise SystemExit('{}: empty window {}..{}'.format(
            path, mmss(t0), mmss(t1)))

    ranges = []
    for name, tt, vv in chans:
        vals = [v for t, v in zip(tt, vv) if v is not None and t0 <= t <= t1]
        if vals:
            ranges.append('{} {}..{}'.format(
                name, fnum(min(vals)), fnum(max(vals))))
    out.append('ranges: ' + ', '.join(ranges))
    out += sparse

    ror_name = next((n for n in ('BT', 'IN', 'Inlet', 'ET')
                     if any(c[0] == n for c in chans)), None)
    w = (t1 - t0) / args.rows
    out.append('series ({} rows, bucket mean over {:.1f}s):'.format(
        args.rows, w))
    out += render_table(chans, t0, t1, args.rows, ror_name)

    if ctl:
        tt, pv, sv, heat = ctl
        keep = [k for k, t in enumerate(tt) if t0 <= t <= t1]
        stats = tracking_stats([tt[k] for k in keep], [pv[k] for k in keep],
                               [sv[k] for k in keep],
                               [heat[k] for k in keep] if heat else None)
        out += stats
    return out


def sniff_loader(path):
    if path.endswith('.alog'):
        return load_alog
    if path.endswith('.csv'):
        return load_dash_csv
    if path.endswith(('.txt', '.log')):
        return load_dash_txt
    with open(path) as f:
        head = f.read(200).lstrip()
    if head.startswith('{'):
        return load_alog
    if head.lower().startswith('time,'):
        return load_dash_csv
    return load_dash_txt


def main():
    p = argparse.ArgumentParser(
        description='Downsample airRoaster roast logs (.alog / dashboard '
                    'CSV / dashboard txt log) into a compact summary for '
                    'review.')
    p.add_argument('files', nargs='+', help='log file(s) to condense')
    p.add_argument('--rows', type=int, default=40,
                   help='time buckets in the series table (default 40)')
    p.add_argument('--from', dest='t_from', type=parse_clock, default=None,
                   metavar='M:SS', help='window start (seconds or m:ss)')
    p.add_argument('--to', dest='t_to', type=parse_clock, default=None,
                   metavar='M:SS', help='window end (seconds or m:ss)')
    args = p.parse_args()

    for i, path in enumerate(args.files):
        if i:
            print()
        loader = sniff_loader(path)
        meta, sparse, chans, ctl = loader(path)
        print('\n'.join(report(path, meta, sparse, chans, ctl, args)))


if __name__ == '__main__':
    main()
