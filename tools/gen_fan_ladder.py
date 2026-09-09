#!/usr/bin/env python3
"""Generate the Phase A bench ladder — a fan ladder at fixed BT, then a BT ladder.

state-plan.md § TEST PLAN § Phase A. Empty chamber, no beans, unattended: the
background carries **both** programs, so the operator preheats to BT 145, presses
CHARGE, and walks away.

    temp2 (the BT curve)   is the outer PID's target      (svMode = 2, pidSource = 1)
    type-0 events (Air)    are replayed onto slider 1     (specialeventplayback[0])

The two do not collide: playback drives the fan slider, the PID drives the inlet
slider. That is the per-type playback flag (canvas.py:1848) the cascade could not
use when *both* wanted slider 3.

The schedule
------------
=========  ==========================================================
0:00       BT 145, fan 60      the anchor rung (phase 0 read HT 48.25 / 48.48 here)
5:00       fan 64              the level the roast steps from
10:00      fan 72              span
15:00      fan 80              span
20:00      fan 60              the return rung — the session's own repeatability check
25:00      BT 160, fan 60      the BT ladder starts; fan is done moving
31:00      BT 175
37:00      BT 190
43:00      DROP
=========  ==========================================================

Fan rungs get 300 s (duty settles in ~3 min); BT rungs get 360 s (phase 0 needed
~2 min to settle a 10-15 degC step, plus a 120 s read window). The BT rungs step
**upward only** — phase 0 showed the chamber metal's hysteresis is signed, so a
monotone ladder keeps its sign constant.

Why the fan span is 60-80 and not 60-64
---------------------------------------
At fixed BT the chamber's losses are fixed, so ``mdot * (T_in - T_out)`` is
constant and **Temp_Drive is proportional to 1/mdot**. Fitting ``TD = C/(fan-f0)``
over 60 -> 80 separates ``mdot ~ fan`` from ``mdot ~ (fan-40)`` by about 2 degC of
Temp_Drive; over 60 -> 64 the same contrast is 0.5 degC and is inside the noise.
The ladder is wider than the step it is sizing on purpose.

Usage
-----
``.venv/bin/python tools/gen_fan_ladder.py`` writes
``artisan/ladder_fan_BT145_v1.alog``. ``--dry-run`` prints the schedule only.
Load it with ``artisan/airRoaster_cascadePID_ladder.aset``.
"""

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ARTISAN = HERE.parent / 'artisan'
SRC = ARTISAN / 'profile_400g_m5C_v4.alog'
ASET = ARTISAN / 'airRoaster_cascadePID_ladder.aset'

sys.path.insert(0, str(HERE))
from merge_inlet_base import _IDENTITY_KEYS, ext_to_internal, load_alog  # noqa: E402
from gen_char_doublet import FAN_TYPE, IL_FAN_FULL, aset_etypes          # noqa: E402

# (seconds since CHARGE, fan level) -- t=0 is the initial condition, not a step
FAN = [(0, 60), (300, 64), (600, 72), (900, 80), (1200, 60)]
# (seconds since CHARGE, BT target degC) -- likewise
BT = [(0, 145.0), (1500, 160.0), (1860, 175.0), (2220, 190.0)]
LENGTH = 2580.0
IL_MARGIN = 3           # keep this far above the interlock's full-authority level
FAN_CIRC_FLOOR = 58     # circulation floor at 400 g; nothing here needs to go below


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', default=str(SRC),
                    help='any cascade background; only its key layout is reused')
    ap.add_argument('--aset', default=str(ASET))
    ap.add_argument('--out', default=str(ARTISAN / 'ladder_fan_BT145_v1.alog'))
    ap.add_argument('--length', type=float, default=LENGTH, metavar='SEC')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    for _, v in FAN:
        if v < IL_FAN_FULL + IL_MARGIN:
            sys.exit(f'fan {v} leaves under {IL_MARGIN} units over the interlock '
                     f'full-authority threshold {IL_FAN_FULL} '
                     '(airRoaster.ino:111); the heat would clip and the ladder '
                     'would be measuring the interlock, not the machine')
        if v < FAN_CIRC_FLOOR:
            sys.exit(f'fan {v} is below the {FAN_CIRC_FLOOR} circulation floor; '
                     'the chamber is empty here so it is safe, but nothing in '
                     'this test needs it and a loaded repeat would not survive it')
    if FAN[-1][0] + 300 > BT[1][0]:
        sys.exit('the last fan rung must settle before the first BT step; the two '
                 'ladders have to stay separable')

    p = dict(load_alog(args.src))
    etypes_aset = aset_etypes(args.aset)
    dt = p['timex'][1] - p['timex'][0]
    n = int(round(args.length / dt)) + 1

    def hold(prog, t):
        """Zero-order hold: the value of the last entry at or before t."""
        v = prog[0][1]
        for tt, vv in prog:
            if t >= tt:
                v = vv
        return v

    timex = [k * dt for k in range(n)]
    p['timex'] = timex
    # ET blank by design: there is no fitted empty plant to draw one from, and a
    # made-up curve on the chart reads as a prediction (gen_char_empty.py).
    p['temp1'] = [-1.0] * n
    p['temp2'] = [hold(BT, t) for t in timex]
    p['extratimex'] = [list(timex[:-1]) for _ in p['extradevices']]
    p['extratemp1'] = [[-1.0] * (n - 1) for _ in p['extradevices']]
    p['extratemp2'] = [[-1.0] * (n - 1) for _ in p['extradevices']]
    # CHARGE at sample 0 and DROP at the last sample: calcSV returns None past
    # drop_t, so the schedule has to end inside the background's own window.
    p['timeindex'] = [0, 0, 0, 0, 0, 0, n - 1, 0]

    fresh = [(int(round(t / dt)), FAN_TYPE, v, '') for t, v in FAN]
    fresh.sort(key=lambda e: (e[0], e[1]))
    p['specialevents'] = [e[0] for e in fresh]
    p['specialeventstype'] = [e[1] for e in fresh]
    p['specialeventsvalue'] = [ext_to_internal(e[2]) for e in fresh]
    p['specialeventsStrings'] = [f'{e[2]}{e[3]}' for e in fresh]

    # Playback compares the numeric type index, never the name (canvas.py:6436-6444),
    # so this is only the chart label -- take the .aset's if it has one, keep the
    # source's otherwise. The cascade .asets leave etypes[0] blank.
    etypes = list(p['etypes'])
    if FAN_TYPE < len(etypes_aset) and etypes_aset[FAN_TYPE].strip():
        etypes[FAN_TYPE] = etypes_aset[FAN_TYPE]
    p['etypes'] = etypes

    p['title'] = 'PHASE A - fan ladder at BT 145, then BT ladder at fan 60 (EMPTY)'
    p['beans'] = 'BENCH LADDER - empty chamber, no beans'
    p['weight'] = [0.0, 0.0, 'g']
    p['roastingnotes'] = (
        'Empty chamber, no beans. Load airRoaster_cascadePID_ladder.aset, bring BT '
        'to 145 under the PID, START, CHARGE - the background then drives the BT '
        'target and replays the fan. Unattended for 43 min. Record settled BT, '
        'Inlet, Temp_Drive, HT and ambient over the LAST 120 s of each rung. '
        'ABORT: HT over ~85% at fan 80 (drop the top rung to 76); any rung that '
        'will not settle (record it and stop there). The fan-60 return rung at '
        '20:00 must reproduce the 0:00 rung HT to +/-0.5% or the session drifted. '
        'state-plan.md TEST PLAN Phase A.')
    p['cuppingnotes'] = ''
    p['roastertype'] = 'airRoaster'
    p.update(_IDENTITY_KEYS)

    fan_rungs = [(t, v) for t, v in FAN]
    print(f'{pathlib.Path(args.out).name}: {n} samples, {len(fresh)} fan events, '
          f'{args.length / 60:.0f} min')
    print('  fan  ' + '  '.join(f'{t // 60:.0f}:{t % 60:02.0f}->{v}' for t, v in fan_rungs))
    print('  BT   ' + '  '.join(f'{t // 60:.0f}:{t % 60:02.0f}->{v:.0f}' for t, v in BT))
    print('  rung read windows (last 120 s of each):')
    edges = sorted({t for t, _ in FAN} | {t for t, _ in BT} | {args.length})
    for a, b in zip(edges, edges[1:]):
        print(f'    {a // 60:2.0f}:{a % 60:02.0f}-{b // 60:2.0f}:{b % 60:02.0f}  '
              f'fan {hold(FAN, a):.0f}  BT {hold(BT, a):.0f}   '
              f'read {(b - 120) // 60:2.0f}:{(b - 120) % 60:02.0f}-{b // 60:2.0f}:{b % 60:02.0f}')
    if not args.dry_run:
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(repr(p))
        print(f'  written {args.out}')


if __name__ == '__main__':
    main()
