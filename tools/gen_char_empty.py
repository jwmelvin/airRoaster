#!/usr/bin/env python3
"""Extend Test A (empty roaster) with a fan sweep, so it also refits `feedforward()`.

Test A was specified as an inlet step sequence on an empty roaster, to identify
the plant without beans.  With no beans in it the run has **no circulation floor
and no blow-out ceiling** -- the only limit is the interlock, which stops giving
the heater full authority below fan 55 (``IL_FAN_FULL_DFLT``, airRoaster.ino:111).
That makes it the one run in the set that can sweep the fan over a wide range,
and it costs nothing: no beans, and the extra time is electricity.

Why that is worth doing
-----------------------
Runbook step 8 replaces the saturated `feedforward()` with the affine form
``heat = -30.62 + 0.99*fan + 0.0096*SV`` (state-history-cascade.md § Roast 46).  Those
coefficients come from **five preheat fan steps spanning 0.81-1.11 %heat/unit** --
a short lever arm, fitted on data taken for another purpose.  This schedule gives
the same regression **six fan levels from 58 to 80 crossed against seven inlet
levels**, on a grid deliberately offset so the two inputs never step together and
the fit can separate them.

It does **not** replace Test C.  An empty chamber measures the *machine's* heat
demand against airflow, which is what `feedforward()` compensates; the loaded
loss term that step 9's schedule needs is a bean-bed quantity and only the loaded
doublets (`gen_char_doublet.py`) can measure it.

The schedule
------------
=========  ================================================================
inlet      145 -> 185 @2:00 -> 145 @5:00 -> 185 @7:00 -> 145 @10:00
           -> 185 @12:00 -> 145 @15:00
fan        64 -> 72 @2:30 -> 58 @5:50 -> 80 @9:10 -> 64 @12:30 -> 72 @15:50
end        17:00, DROP by hand
=========  ================================================================

The fan grid is 200 s and the inlet grid is 120-180 s, phase-shifted so no fan
change lands within 30 s of an inlet change.  Fan 58 keeps three units of margin
over the interlock threshold; the run would still be *safe* below it, but the
heat would clip and the regression would be fitting the interlock instead of the
machine.

The background's BT column
--------------------------
Left as recorded through the original 12 minutes and **blank (-1) beyond**.  On
an empty roaster the BT probe reads chamber air, and there is no fitted empty
plant to extrapolate with; a made-up curve would look like a prediction.  Nothing
in the run reads it -- the PID is off and playback is by time.

Usage
-----
``python3 tools/gen_char_empty.py`` -- writes ``artisan/charstep_empty_fan.alog``
and leaves ``charstep_empty.alog`` alone.  ``--dry-run`` to see the schedule.
"""

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ARTISAN = HERE.parent / 'artisan'
SRC = ARTISAN / 'charstep_empty.alog'
ASET = ARTISAN / 'airRoaster_cascadePID.aset'

sys.path.insert(0, str(HERE))
from merge_inlet_base import _IDENTITY_KEYS, ext_to_internal, load_alog  # noqa: E402
from gen_char_doublet import FAN_TYPE, INLET_TYPE, IL_FAN_FULL, aset_etypes  # noqa: E402

# (seconds since CHARGE, degC) -- the original five, then two more
INLET = [(0, 145), (120, 185), (300, 145), (420, 185),
         (600, 145), (720, 185), (900, 145)]
# 200 s grid, offset off the inlet grid so the two never step together
FAN = [(0, 64), (150, 72), (350, 58), (550, 80), (750, 64), (950, 72)]
LENGTH = 1020.0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', default=str(SRC))
    ap.add_argument('--aset', default=str(ASET))
    ap.add_argument('--out', default=str(ARTISAN / 'charstep_empty_fan.alog'))
    ap.add_argument('--length', type=float, default=LENGTH, metavar='SEC')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    p = dict(load_alog(args.src))
    etypes_aset = aset_etypes(args.aset)
    dt = p['timex'][1] - p['timex'][0]
    n_old = len(p['timex'])
    n_new = int(round(args.length / dt)) + 1
    if n_new <= n_old:
        sys.exit(f'--length {args.length} is not longer than the source')

    # t = 0 is the initial condition on both sliders, not a step
    gaps = [abs(ft - it) for ft, _ in FAN if ft for it, _ in INLET if it]
    if min(gaps) < 30:
        sys.exit(f'a fan step lands {min(gaps):.0f} s from an inlet step; the fit '
                 'cannot separate two inputs that move together')
    for _, v in FAN:
        if v < IL_FAN_FULL + 3:
            sys.exit(f'fan {v} leaves under 3 units over the interlock '
                     f'full-authority threshold {IL_FAN_FULL} (airRoaster.ino:111); '
                     'the heat would clip and the fit would be measuring the '
                     'interlock, not the machine')

    timex = [k * dt for k in range(n_new)]
    p['timex'] = timex
    p['temp1'] = [p['temp1'][k] if k < n_old else -1.0 for k in range(n_new)]
    p['temp2'] = [p['temp2'][k] if k < n_old else -1.0 for k in range(n_new)]
    p['extratimex'] = [list(timex) for _ in p['extradevices']]
    p['extratemp1'] = [[-1.0] * n_new for _ in p['extradevices']]
    p['extratemp2'] = [[-1.0] * n_new for _ in p['extradevices']]
    p['timeindex'] = [0, 0, 0, 0, 0, 0, n_new - 1, 0]

    fresh = [(int(round(t / dt)), INLET_TYPE, v, 'C') for t, v in INLET] + \
            [(int(round(t / dt)), FAN_TYPE, v, '') for t, v in FAN]
    fresh.sort(key=lambda e: (e[0], e[1]))
    p['specialevents'] = [e[0] for e in fresh]
    p['specialeventstype'] = [e[1] for e in fresh]
    p['specialeventsvalue'] = [ext_to_internal(e[2]) for e in fresh]
    p['specialeventsStrings'] = [f'{e[2]}{e[3]}' for e in fresh]

    etypes = list(p['etypes'])
    for k in (FAN_TYPE, INLET_TYPE):
        if k < len(etypes_aset):
            etypes[k] = etypes_aset[k]
    p['etypes'] = etypes

    p['title'] = 'CHAR A - empty roaster, inlet steps x fan sweep 58-80 (PID OFF)'
    p['beans'] = 'CHARACTERISATION RUN - empty, no beans'
    p['roastingnotes'] = (
        'Empty roaster. Load airRoaster_cascadePID_char.aset, set fan 64, START, '
        'CHARGE; the schedule replays both sliders. Refits feedforward() as well '
        'as identifying the empty plant. BT is blank past 12:00 by design. '
        'DROP by hand at 17:00.')
    p.update(_IDENTITY_KEYS)

    print(f'{pathlib.Path(args.out).name}: {n_new} samples, '
          f'{len(fresh)} events, closest fan/inlet step {min(gaps):.0f} s apart')
    print('  inlet  ' + '  '.join(f'{t}s->{v}' for t, v in INLET))
    print('  fan    ' + '  '.join(f'{t}s->{v}' for t, v in FAN))
    if not args.dry_run:
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(repr(p))
        print(f'  written {args.out}')


if __name__ == '__main__':
    main()
