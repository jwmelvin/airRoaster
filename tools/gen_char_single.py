#!/usr/bin/env python3
"""One 400 g sacrificial batch that does the whole loaded characterisation.

The two-batch plan (`gen_char_doublet.py`) needs 800 g of sacrificial beans.
With 617 g the choice is one 400 g batch or two 308 g ones, and **two 308 g
batches are the wrong answer**: charge mass sets both quantities these runs
exist to measure -- the bed's pressure drop, and therefore the flow a fan level
delivers (what `FF SLOPE` corrects), and the thermal mass in the plant fit. A
308 g pair would characterise a roaster the operator does not run, and a single
mass gives nothing to extrapolate from.

What one batch can do that two could not
----------------------------------------
Roast 47 measured the thing that sets the design: **heat reaches 95 % of its
final value within 2 s of a fan step** (the slow tail is only the integrator
trimming the last fraction of a percent). A slope measurement therefore costs
~45 s, not a plateau, so it can be taken at *several* setpoints instead of one.

That matters because the model's fan sensitivity is a line in the setpoint:

    slope(sv) = cfan + cfansv * sv / 100

Measuring at one setpoint only supports `FF SLOPE`, which rescales both fan
terms together because their split is not identifiable from a single point.
**Three setpoints identify `cfan` and `cfansv` separately, loaded** -- strictly
more than the two-batch plan could deliver, which took its slope at SV 200 only.

The second thing one batch buys is that there is no batch-to-batch variance to
confound anything: the between-batch fan-level contrast is lost, but it was
always the weaker half, and it was a roast-quality question rather than a
characterisation one.

Why the schedule is shaped this way
-----------------------------------
**Every fan step happens at a dead-flat inlet.** Heat depends on fan and on the
commanded setpoint, and essentially *not* on BT -- the inlet thermocouple is
upstream of the bed -- so BT climbing through a measurement block does not
contaminate the heat slope at all. What BT does constrain is how long a block
can last before first crack, and that is the only reason the blocks are short.

**The cooling valleys are not filler.** A steady inlet drags BT to within
~15 degC of itself (`loss/a`), so a high setpoint cannot simply be held: at
SV 245 the plateau would be BT ~230, deep into second crack. Dropping the inlet
to 150 between blocks pulls BT back down at ~0.2 degC/s -- and those up-and-down
inlet steps *are* the plant-identification excitation, which is why this file
does not also need the separate 3:00-5:00 doublet the two-batch files carry.

**Block C uses +-10 rather than +6.** The small pulses are sized for the heat
signal, which resolves to 0.4-1.5 %; the outer plant's fan gain is read from BT,
which needs a much larger push. So block C doubles as the slope point at SV 190
and as the BT excitation.

The batch comes out heavily baked and under-developed -- it stays below first
crack throughout by construction. That is the point of a sacrificial batch.

Usage
-----
``python3 tools/gen_char_single.py`` writes ``artisan/charsingle_400g.alog``.
``--dry-run`` prints the schedule and the simulated BT without writing.
"""

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ARTISAN = HERE.parent / 'artisan'
SRC = ARTISAN / 'chardoublet_loaded.alog'
ASET = ARTISAN / 'airRoaster_cascadePID.aset'
PLANT_CARD = HERE / 'analysis' / 'plant_roast46.json'

sys.path.insert(0, str(HERE))
from merge_inlet_base import _IDENTITY_KEYS, ext_to_internal, load_alog  # noqa: E402
from gen_char_doublet import (FAN_TYPE, INLET_TYPE, IL_FAN_FULL,          # noqa: E402
                              aset_etypes, load_plant, simulate_bt, step_lookup)

RAMP_END = 165.0     # roast 45's own commanded SV is replayed up to here
FC_C = 196.0         # first crack; the schedule must stay under it

# (seconds since CHARGE, degC). Everything from RAMP_END on is authored.
INLET = [
    (165, 245),      # block A -- flat, the highest setpoint, taken while BT is lowest
    (270, 150),      # valley
    (330, 215),      # block B
    (435, 150),      # valley
    (495, 190),      # block C -- held to DROP
]
# (seconds, level). 64 through the charge is not optional: a 400 g charge does
# not circulate at 60 (see gen_char_doublet.py).
FAN = [
    (0, 64), (90, 60),
    (195, 66), (240, 60),      # slope @ SV 245
    (360, 66), (405, 60),      # slope @ SV 215
    (525, 70), (585, 60),      # slope @ SV 190, and the outer fan gain
    (645, 70), (705, 60),
]
LENGTH = 735.0       # DROP by hand at 12:15
MIN_GAP = 20.0       # no fan step within this of an inlet step


def ms(t):
    return f'{int(t) // 60}:{int(t) % 60:02d}'


def blocks(inlet, fan):
    """Each fan step, the setpoint it sits at, and whether that setpoint is flat.

    Only a step taken at a *flat* inlet is a slope measurement. The 1:30
    circulation bump happens while the replayed ramp is still moving, so the
    setpoint is changing underneath it and the heat change is not attributable
    to the fan alone; it is reported, because it is the same free fan step every
    real roast carries, but it is not counted toward identifiability.
    """
    inl = step_lookup(inlet)
    out = []
    for i, (t, v) in enumerate(fan):
        if i == 0:
            continue
        prev = fan[i - 1][1]
        if v == prev:
            continue
        out.append((t, prev, v, inl(t), t > RAMP_END))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', default=str(SRC))
    ap.add_argument('--aset', default=str(ASET))
    ap.add_argument('--plant', default=str(PLANT_CARD))
    ap.add_argument('--out', default=str(ARTISAN / 'charsingle_400g.alog'))
    ap.add_argument('--length', type=float, default=LENGTH, metavar='SEC')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    p = dict(load_alog(args.src))
    etypes_aset = aset_etypes(args.aset)
    a, theta, poly, window = load_plant(args.plant)
    dt = p['timex'][1] - p['timex'][0]
    n_new = int(round(args.length / dt)) + 1

    # the replayed charge ramp, then the authored schedule
    def ext(v):
        if -1.0 <= v <= 1.0:
            return 0
        return -(int(round(abs(v) * 10)) - 10) if v < -1.0 else int(round(v * 10)) - 10
    ramp = [(p['timex'][i], ext(v))
            for i, ty, v in zip(p['specialevents'], p['specialeventstype'],
                                p['specialeventsvalue'])
            # strictly less: RAMP_END is the *authored* block A event, and two
            # type-2 events on one sample is a duplicate index, not a schedule
            if ty == INLET_TYPE and p['timex'][i] < RAMP_END]
    inlet = ramp + [(float(t), float(v)) for t, v in INLET]
    fan = [(float(t), float(v)) for t, v in FAN]

    # --- guards: each is a way the run could be wasted rather than merely noisy
    for t, v in fan:
        if v < IL_FAN_FULL + 2:
            sys.exit(f'fan {v:.0f} leaves under 2 units over the interlock '
                     f'full-authority threshold {IL_FAN_FULL} (airRoaster.ino:111)')
    gaps = [(abs(ft - it), ft, it) for ft, _ in fan if ft
            for it, _ in inlet if it > RAMP_END]
    worst = min(gaps)
    if worst[0] < MIN_GAP:
        sys.exit(f'a fan step at {ms(worst[1])} lands {worst[0]:.0f} s from an inlet '
                 f'step at {ms(worst[2])}; the fit cannot separate inputs that move '
                 'together')
    svs = sorted({sv for _, _, _, sv, flat in blocks(inlet, fan) if flat})
    if len(svs) < 3:
        sys.exit(f'fan steps sit at only {len(svs)} flat setpoint(s) {svs}; three '
                 'are needed to identify cfan and cfansv separately rather than '
                 'only rescaling them together')

    # --- simulate BT forward from the end of the replayed ramp
    inlet_of = step_lookup(inlet)
    i_sim = int(round(RAMP_END / dt))
    bt = simulate_bt(p['temp2'][i_sim], RAMP_END, args.length, inlet_of,
                     a, theta, poly, window, dt)
    timex = [k * dt for k in range(n_new)]
    temp2 = [p['temp2'][k] if k < i_sim else bt[timex[k]] for k in range(n_new)]
    if max(temp2) >= FC_C:
        sys.exit(f'simulated BT reaches {max(temp2):.0f} degC at '
                 f'{ms(timex[temp2.index(max(temp2))])} — first crack is {FC_C:.0f}; '
                 'shorten a block or deepen a valley')

    p['timex'] = timex
    p['temp1'] = [-1.0] * n_new
    p['temp2'] = temp2
    p['extratimex'] = [list(timex) for _ in p['extradevices']]
    p['extratemp1'] = [[inlet_of(t) for t in timex]] + \
                      [[-1.0] * n_new for _ in p['extradevices'][1:]]
    p['extratemp2'] = [[-1.0] * n_new for _ in p['extradevices']]

    lo, hi = p['phases'][1], p['phases'][2]
    first = lambda thr: next((k for k, v in enumerate(temp2) if v >= thr), 0)
    p['timeindex'] = [0, first(lo), first(hi), 0, 0, 0, n_new - 1, 0]

    fresh = [(int(round(t / dt)), INLET_TYPE, v, 'C') for t, v in inlet] + \
            [(int(round(t / dt)), FAN_TYPE, v, '') for t, v in fan]
    fresh.sort(key=lambda e: (e[0], e[1]))
    p['specialevents'] = [e[0] for e in fresh]
    p['specialeventstype'] = [e[1] for e in fresh]
    p['specialeventsvalue'] = [ext_to_internal(e[2]) for e in fresh]
    p['specialeventsStrings'] = [f'{int(round(e[2]))}{e[3]}' for e in fresh]

    etypes = list(p['etypes'])
    for k in (FAN_TYPE, INLET_TYPE):
        if k < len(etypes_aset):
            etypes[k] = etypes_aset[k]
    p['etypes'] = etypes

    p['title'] = ('CHAR single 400g - fan slope at SV 245/215/190 + inlet '
                  'staircase (PID OFF)')
    p['beans'] = 'CHARACTERISATION RUN - 400 g sacrificial'
    p['roastingnotes'] = (
        'Open-loop, 400 g. Load airRoaster_cascadePID_char.aset, set fan 64 before '
        'CHARGE; the schedule replays both sliders. Fan steps sit at a flat inlet by '
        'design. DROP by hand at ' + ms(args.length) + '. Weigh in and out, fill in '
        'greens_temp. BT column is a forward simulation of the plant card from '
        + ms(RAMP_END) + ', not a recorded roast.')
    p.update(_IDENTITY_KEYS)

    print(f'{pathlib.Path(args.out).name}: {n_new} samples, {len(fresh)} events, '
          f'DROP {ms(args.length)}')
    print('  inlet  ' + '  '.join(f'{ms(t)}→{v:.0f}' for t, v in inlet[-len(INLET):]))
    print('  fan    ' + '  '.join(f'{ms(t)}→{v:.0f}' for t, v in fan))
    print(f'  closest fan/inlet step {worst[0]:.0f} s apart')
    print('\n  fan steps and the setpoint each is measured at:')
    for t, prev, v, sv, flat in blocks(inlet, fan):
        note = f'at SV {sv:.0f}' if flat else f'during the ramp (SV ~{sv:.0f}, moving)'
        print(f'    {ms(t):>6}  fan {prev:.0f} → {v:.0f}   {note}')
    print(f'\n  slope measured at {len(svs)} flat setpoints '
          f'{[int(x) for x in svs]} → cfan and cfansv separable, loaded')
    print('\n  simulated BT:  ' +
          '  '.join(f'{ms(t)} {temp2[int(t / dt)]:.0f}'
                    for t in range(0, int(args.length) + 1, 90)))
    print(f'  BT max {max(temp2):.1f} degC (first crack {FC_C:.0f})')

    if not args.dry_run:
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(repr(p))
        print(f'\n  written {args.out}')


if __name__ == '__main__':
    main()
