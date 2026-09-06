#!/usr/bin/env python3
"""Generate the extended Test B/C backgrounds: an inlet doublet *and* a fan doublet.

Runbook steps 4-5 were specified as three sacrificial batches -- one loaded
doublet, then the same doublet repeated at fan 58 and fan 65 -- and were
collapsed to two (state-plan.md § Files for the characterisation runs).  Two
batches measure the fan only as a **between-batch** contrast, and at n = 2 that
contrast is also a batch contrast: roast 46 is the standing proof that batch
differences are not small (55 g of batch size manufactured a 30 degC error
swing).  This tool removes the confound without adding a run, by putting fan
excitation *inside* each batch.

What it emits
-------------
``chardoublet_fan57.alog`` and ``chardoublet_fan65.alog``, each a 9-minute
extension of ``chardoublet_loaded.alog``:

===============  =========================================================
0:00 - 1:30      **fan 64** -- establish circulation.  Identical in both files
0:00 - 5:00      unchanged -- roast 45's own commanded SV with the +30/-30
                 degC inlet doublet over 3:00-5:00
1:30 - 6:00      fan drops to this batch's **base** (60 or 68)
5:05 - 5:20      inlet stepped down to the **hold** value in two steps
5:20 - 9:00      inlet held, so BT levels off instead of running on
6:00 - 9:00      **fan square wave 60 <-> 70**, 60 s half-cycles,
                 phase-reversed between the two files
9:00             DROP (by hand -- the char config disables both alarms)
===============  =========================================================

The fan floor is a **bean** constraint, not an actuator one
--------------------------------------------------------------
**A 400 g charge does not circulate at fan 60.**  It takes ~64 to get the bed
lofted and drying, after which it sustains at 60 (operator, 2026-09-06).  Roast
46's own events say the same thing and are not the "constant 60" that
state-current.md summarised them as: 60 at CHARGE+2 s, **64 at +7 s**, 63 at
+11 s, back to 60 at +85 s.  So a constant fan from CHARGE is not a schedule this
roaster can run, and both files open with **64 until 1:30** -- identical in both,
so it differences out of the comparison, and a step rather than a level, which is
excitation rather than a confound.

Below **55** the interlock stops giving the heater full authority
(``IL_FAN_FULL_DFLT``, airRoaster.ino:111): the heat clips, the inner loop stops
holding the inlet, and an open-loop identification run is invalid.  The operator
puts the practical floor higher still -- 58-59 is the lowest reachable at all --
so the schedule never goes below **60**.  There is no blow-out ceiling (operator,
2026-09-06); the concerns above the usual band are moisture loss at higher
Reynolds number and bed uniformity (chuffing drives local circulations that
short-cut the funnel), neither of which is a reason to avoid **70** for 60 s at a
time on a sacrificial batch.

So the plateau modulation is a **phase-reversed 60 <-> 70 square wave**, the same
two levels in both files with opposite phase: six transitions across the pair in
both directions, and slow drift common to the two runs cancels in the difference.
The **base** through the ramp differs -- 60 and 68 -- which is the between-batch
level contrast, and which also puts a first number on a question the operator has
open independently: whether minimum airflow costs or saves moisture.  **Weigh in
and out on both**; that comparison is indicative rather than definitive, since
the two runs share the plateau.

Why the inlet is levelled off rather than continued
---------------------------------------------------
Replaying roast 45's SV to 9:00 would take BT past second crack.  Holding the
inlet near ``BT + loss/a`` instead makes BT roughly flat, which is both safe and
the *better* place to measure the fan: the plateau lands near BT 185, below
first crack, so the bean exotherm is not confounding the measurement.  The
batches come out underdeveloped rather than burnt -- they are sacrificial either
way.

The background's BT column
--------------------------
``chardoublet_loaded.alog`` carries roast 45's **closed-loop** BT, which stopped
being a prediction the moment the doublet was spliced into the inlet schedule.
Here it is replaced from 3:00 onward by an open-loop forward simulation of the
plant card (``dBT/dt = a*(Inlet(t-theta) - BT) + loss(t)``), so the background is
an honest prediction of the run and can be compared against live.  ``loss(t)`` is
a cubic fitted over 45 s..DROP of roast 46 and is **clamped at the window edges**
rather than extrapolated -- extrapolated to 540 s it turns over and asks for a
60 degC inlet-to-BT gap, which is fit artefact, not physics.

Usage
-----
``python3 tools/gen_char_doublet.py`` (writes both), ``--dry-run`` to see the
schedules and the predicted BT without writing.
"""

import argparse
import ast
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ARTISAN = HERE.parent / 'artisan'
SRC = ARTISAN / 'chardoublet_loaded.alog'
PLANT_CARD = HERE / 'analysis' / 'plant_roast46.json'
ASET = ARTISAN / 'airRoaster_cascadePID.aset'

sys.path.insert(0, str(HERE))
from merge_inlet_base import (                       # noqa: E402
    _IDENTITY_KEYS, ext_to_internal, internal_to_ext, load_alog, polyval)

FAN_TYPE = 0          # etypes[0] -- slider 1, OT2
INLET_TYPE = 2        # etypes[2] -- slider 3, INLET
IL_FAN_FULL = 55      # airRoaster.ino IL_FAN_FULL_DFLT: heat unrestricted at/above


def aset_etypes(path):
    """The event-type names the config in force uses.

    ``playbackevent`` compares them as ``str(self.etypesf(t) == str(self.Betypesf(t)))``
    -- ``str(bool)``, always truthy, so on v4.2.0 the comparison is inert
    (canvas.py:6530/:6546).  merge_inlet_base.py's policy is to align the names
    deliberately rather than rely on that bug, so the background takes its names
    from the ``.aset`` rather than inventing them: an Artisan that fixes the
    parenthesis would otherwise stop replaying.
    """
    for line in pathlib.Path(path).read_text(encoding='utf-8').split('\n'):
        if line.startswith('etypes='):
            return [x.strip() for x in line[len('etypes='):].split(',')]
    sys.exit(f'{path}: no etypes= line')


def load_plant(path):
    import json
    with open(path, encoding='utf-8') as fh:
        card = json.load(fh)
    return card['a'], card['theta'], card['loss_poly'], card['loss_window']


def loss_at(t, poly, window):
    """The fitted cubic, clamped at the fit window rather than extrapolated."""
    return polyval(poly, min(max(t, window[0]), window[1]))


def simulate_bt(bt0, t0, tend, inlet_of, a, theta, poly, window, dt=1.0):
    """Forward-Euler the plant from ``bt0`` at ``t0``.  Returns {t: BT}."""
    out = {t0: bt0}
    bt = bt0
    t = t0
    while t < tend:
        bt += dt * (a * (inlet_of(t - theta) - bt) + loss_at(t, poly, window))
        t += dt
        out[t] = bt
    return out


def step_lookup(points):
    """Zero-order hold over (t, value) pairs -- what event playback does."""
    pts = sorted(points)

    def f(t):
        v = pts[0][1]
        for pt, pv in pts:
            if pt <= t:
                v = pv
            else:
                break
        return v
    return f


def build(src, base_fan, args, a, theta, poly, window):
    p = dict(src)
    n_old = len(p['timex'])
    dt = p['timex'][1] - p['timex'][0]
    n_new = int(round(args.length / dt)) + 1
    if n_new <= n_old:
        sys.exit(f'--length {args.length} is not longer than the source '
                 f'({p["timex"][-1]:.0f} s)')

    # ---- inlet schedule: keep <= hold_start, then two steps down to the hold
    old = list(zip(p['specialevents'], p['specialeventstype'], p['specialeventsvalue']))
    inlet = [(p['timex'][i], internal_to_ext(v))
             for i, ty, v in old if ty == INLET_TYPE and p['timex'][i] <= args.hold_start]
    inlet_hi = inlet[-1][1]
    mid = round((inlet_hi + args.hold) / 2.0)
    inlet += [(args.hold_start + 5.0, mid), (args.hold_start + 20.0, float(args.hold))]

    # ---- fan: circulation bump, then the ramp base, then the square wave
    fan = [(0.0, float(args.charge_fan)),
           (args.charge_fan_until, float(base_fan))]
    # start the square wave on whichever level is further from this batch's base,
    # so no half-cycle is wasted repeating the level the ramp already sat at
    k = 0 if abs(args.mod[0] - base_fan) > abs(args.mod[1] - base_fan) else 1
    t = args.fan_start
    while t < args.length:
        fan.append((t, float(args.mod[k % 2])))
        k += 1
        t += args.fan_period
    for _, v in fan:
        if v < IL_FAN_FULL + 2:
            sys.exit(f'fan level {v:.0f} leaves under 2 units of margin over the '
                     f'interlock full-authority threshold {IL_FAN_FULL} '
                     '(airRoaster.ino:111); the heat would clip and the inner '
                     'loop would stop holding the inlet')

    # ---- extend the sample arrays, then overwrite BT with the simulation
    inlet_of = step_lookup(inlet)
    t_sim = args.sim_from
    i_sim = int(round(t_sim / dt))
    bt = simulate_bt(p['temp2'][i_sim], t_sim, args.length, inlet_of,
                     a, theta, poly, window, dt)

    timex = [k * dt for k in range(n_new)]
    temp2 = [p['temp2'][k] if k < i_sim else bt[timex[k]] for k in range(n_new)]
    temp1 = [-1.0] * n_new
    p['timex'], p['temp1'], p['temp2'] = timex, temp1, temp2
    p['extratimex'] = [list(timex) for _ in p['extradevices']]
    # extra device 1 channel 1 is the Inlet curve: draw the commanded schedule
    p['extratemp1'] = [[inlet_of(t) for t in timex]] + \
                      [[-1.0] * n_new for _ in p['extradevices'][1:]]
    p['extratemp2'] = [[-1.0] * n_new for _ in p['extradevices']]

    # ---- marks: CHARGE and DROP are load-bearing, the phase marks are not
    lo, hi = p['phases'][1], p['phases'][2]
    def first_at(thr):
        for k, v in enumerate(temp2):
            if v >= thr:
                return k
        return 0
    p['timeindex'] = [0, first_at(lo), first_at(hi), 0, 0, 0, n_new - 1, 0]

    # ---- events, in index order
    fresh = [(int(round(t / dt)), INLET_TYPE, v, 'C') for t, v in inlet] + \
            [(int(round(t / dt)), FAN_TYPE, v, '') for t, v in fan]
    fresh.sort(key=lambda e: (e[0], e[1]))
    p['specialevents'] = [e[0] for e in fresh]
    p['specialeventstype'] = [e[1] for e in fresh]
    p['specialeventsvalue'] = [ext_to_internal(e[2]) for e in fresh]
    p['specialeventsStrings'] = [f'{int(round(e[2]))}{e[3]}' for e in fresh]

    etypes = list(p['etypes'])
    for k in (FAN_TYPE, INLET_TYPE):
        if k < len(args._etypes):
            etypes[k] = args._etypes[k]
    p['etypes'] = etypes

    p['title'] = (f'CHAR BC - inlet doublet 3:00-5:00, ramp fan {base_fan}, '
                  f'fan {args.mod[0]}/{args.mod[1]} square wave 6:00-9:00 '
                  '(PID OFF)')
    p['beans'] = 'CHARACTERISATION RUN - not a roast'
    p['roastingnotes'] = (
        f'Open-loop. Load airRoaster_cascadePID_char.aset. Set fan '
        f'{args.charge_fan} before CHARGE; the schedule replays every change from '
        f'there (ramp base {base_fan}). Weigh in and out. BT column is a forward '
        f'simulation of the plant card from {args.sim_from:.0f} s, not a recorded '
        'roast. DROP by hand at 9:00.')
    p.update(_IDENTITY_KEYS)

    # round-trip the event encoding on what we are about to write
    for want, got in zip([e[2] for e in fresh],
                         [internal_to_ext(v) for v in p['specialeventsvalue']]):
        assert abs(int(round(want)) - got) <= 0, (want, got)

    return p, inlet, fan, temp2


def report(name, inlet, fan, temp2, dt):
    print(f'\n{name}')
    print('  inlet  ' + '  '.join(f'{t:.0f}s->{v:.0f}' for t, v in inlet[-4:]))
    print('  fan    ' + '  '.join(f'{t:.0f}s->{v:.0f}' for t, v in fan))
    marks = [180, 240, 300, 330, 360, 420, 480, 540]
    print('  BT     ' + '  '.join(
        f'{t}s {temp2[int(t / dt)]:.0f}' for t in marks if int(t / dt) < len(temp2)))
    print(f'  BT max {max(temp2):.1f} degC')


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', default=str(SRC))
    ap.add_argument('--plant', default=str(PLANT_CARD))
    ap.add_argument('--aset', default=str(ASET),
                    help='config the run will load; its etypes names are copied')
    ap.add_argument('--bases', type=int, nargs='+', default=[60, 68],
                    help='fan level through the ramp, per output file')
    ap.add_argument('--charge-fan', type=int, default=64, metavar='LEVEL',
                    help='fan until --charge-fan-until, to establish circulation')
    ap.add_argument('--charge-fan-until', type=float, default=90.0, metavar='SEC')
    ap.add_argument('--mod', type=int, nargs=2, default=[60, 70], metavar='LEVEL',
                    help='the two plateau modulation levels (default 60 70)')
    ap.add_argument('--fan-start', type=float, default=360.0, metavar='SEC')
    ap.add_argument('--fan-period', type=float, default=60.0, metavar='SEC')
    ap.add_argument('--hold-start', type=float, default=300.0, metavar='SEC',
                    help='end of the inlet doublet; the level-off starts here')
    ap.add_argument('--hold', type=float, default=200.0, metavar='degC',
                    help='inlet held from --hold-start + 20 s to DROP')
    ap.add_argument('--sim-from', type=float, default=180.0, metavar='SEC',
                    help='where the simulated BT column takes over')
    ap.add_argument('--length', type=float, default=540.0, metavar='SEC')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    src = load_alog(args.src)
    a, theta, poly, window = load_plant(args.plant)
    args._etypes = aset_etypes(args.aset)
    dt = src['timex'][1] - src['timex'][0]
    print(f'source {pathlib.Path(args.src).name}: {len(src["timex"])} samples, '
          f'plant a={a:.6f} theta={theta} loss window {window[0]:.0f}-{window[1]:.0f} s')

    for base in args.bases:
        p, inlet, fan, temp2 = build(src, base, args, a, theta, poly, window)
        name = f'chardoublet_fan{base}.alog'
        report(name, inlet, fan, temp2, dt)
        if not args.dry_run:
            dst = ARTISAN / name
            with open(dst, 'w', encoding='utf-8') as fh:
                fh.write(repr(p))
            print(f'  written {dst}')


if __name__ == '__main__':
    main()
