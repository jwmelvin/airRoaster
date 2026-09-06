#!/usr/bin/env python3
"""Merge the step-9 inlet feed-forward schedule into a recorded background profile.

The cascade's outer loop today emits an *absolute* inlet setpoint, so its
integrator has to supply the entire operating point.  Runbook step 9 splits that
in two: the firmware gets a **base** inlet schedule replayed from the background
as special events, and Artisan's PID drives a bounded **`INLET TRIM`** on top of
it (state-plan.md § Dip strategies § The structural fix).

    INLET = ff(t since CHARGE) + trim,        trim in [-80, +80] degC
    ff(t) = bg(t + theta) + (dbg/dt(t + theta) - loss(t + theta)) / a

That needs *one* background carrying three things at once: the BT curve the outer
PID follows (`pidSource = 1`), the base schedule as replayable special events,
and the real `timeindex` marks.  ``artisan/make_inlet_background.py`` emits
neither of its two modes in that shape and is frozen by scope
(state-plan.md § The base-curve authoring gap), so the step-9 background is a
**merge** onto profile_003/004, not a generation.  This tool is that merge: it
reads a recorded ``.alog``, computes ``ff``, reduces it to N replayable events,
and writes a copy with the four ``specialevents*`` arrays added.  Everything
else in the profile is passed through untouched.

Usage
-----
    tools/merge_inlet_base.py --into artisan/profile_003.alog
    tools/merge_inlet_base.py --into artisan/profile_003.alog --tol 0.5 --csv /tmp/base.csv

The plant comes from a card written by ``tools/analysis/roast46_refit.py
--emit-plant``.  Re-run that after the characterisation roasts (runbook steps
3-5) and re-run this; nothing else changes.

What was checked in the Artisan source, and why the file looks like this
-----------------------------------------------------------------------
Citations are into ``~/src/artisan`` at **v4.2.0** (state-plan.md § Development
framework -- do not read master).

* **Playback is gated on foreground CHARGE, but only if the background has a
  CHARGE mark.**  ``canvas.py:5381`` calls ``playbackevent()`` when
  ``timeindex[0] > -1 or timeindexB[0] < 0``, and ``main.py:14521`` preserves a
  saved ``timeindex[0] == 0`` as 0 rather than -1.  So a background *with* CHARGE
  replays from CHARGE (what we want) and a background *without* one starts
  replaying at START, driving INLET through the preheat.  This tool refuses to
  write a profile whose CHARGE mark it cannot vouch for.
* **Events after the background's DROP never replay** --
  ``(timeindexB[6]==0 or bge <= timeindexB[6])``, ``canvas.py:6444``.  The last
  usable event is at ``timeindex[6]``; nothing is emitted past it.  The *input*
  side of that is subtler: ``ff(t)`` reads ``bg(t + theta)``, and a recorded roast
  continues past DROP into the **cooling phase**, so reading it there rails the
  base to ``--min`` over exactly the last ``theta`` seconds.  The background is
  therefore used only up to DROP and blended into its own terminal RoR fit over
  ``--tail-window``; blending rather than butt-joining matters because ``dbg/dt``
  is divided by ``a``, so a 0.005 degC/s kink at the seam is a 1 degC step in the
  base and the knot chooser then spends events on it.
* **Between events Artisan sends a float, at every sample tick.**  The ramp
  branch fires ``moveslider`` plus ``fireslideraction_internal(k, ramp_value)``
  with the interpolated float (``canvas.py:6675-6677``), and at an event itself
  the direct branch fires the integer slider value.  So the replay is *exactly* a
  linear interpolation through the whole-degree event values -- which makes
  "choose N from the residual" an exact offline computation, done below on the
  quantised, index-snapped polyline rather than on the ideal curve.
* **The event-type *name* check is inert in v4.2.0.**  ``canvas.py:6530`` (and
  ``:6546``, guarding the ramp branch) reads
  ``str(self.etypesf(t) == str(self.Betypesf(t)))`` -- ``str(bool)``, always a
  non-empty truthy string, so the comparison never fails.  Only the numeric type
  index matters today.  We align the name anyway: a future Artisan that fixes the
  parenthesis would start enforcing it, and a mismatched name would then silently
  stop the whole schedule.
* **Event values are not unit-converted on background load**
  (``main.py:14474-14477``), so they are written in the slider's own unit.  The
  firmware is degC-only, so a profile in F is refused.
* ``moveslider`` clamps the slider to ``[eventslidermin, eventslidermax]``
  (``main.py:11479``) while ``fireslideraction_internal`` sends the unclamped
  float, so a base above the slider maximum would be *sent* but displayed wrong.
  The summary reports the range so the ``.aset``'s ``slidermax`` can be checked.

The charge dip
--------------
The schedule deliberately knows nothing about the dip -- it is the one part of a
roast that is not repeatable, so it is left entirely to the trim.  Inverting the
plant straight through the dip is not an option: the background falls at up to
3.5 degC/s there and ``/a`` multiplies that by ~204, so raw ``ff`` reaches
**-432 degC** at CHARGE on profile_003.  ``--dip`` picks what the base does
instead, over ``[0, --ramp-start]``:

``extrapolate``  (default) linear back-extrapolation of ``ff`` from
                 ``--ramp-start``, fitted over ``--extrap-window``.  On
                 profile_003 that is a nearly flat 198.7 -> 200.9 degC, so the
                 base holds a plausible inlet and the trim absorbs the whole
                 excursion.
``hold``         flat at ``ff(--ramp-start)``.
``follow``       raw ``ff`` clamped to ``[--min, --max]``, i.e. the base dives to
                 the floor and climbs back out.

**Note that `follow` is what state-plan.md § Dip strategies actually simulated**
(``dip_strategies.py:make_ff`` clips to ``[120, 300]``), so the FF-trim rows in
that table describe `follow`, not the default.  The two differ by ~80 degC of
base over the first 40 s and the difference has not been run through the closed
loop.

Traps this tool refuses to walk into
------------------------------------
* an event index past ``timeindex[6]`` (never replays);
* a background with no usable CHARGE or DROP mark;
* a profile in Fahrenheit;
* pre-existing special events of the target type (use ``--replace``);
* silently reusing the source roast's identity -- ``roastUUID``, the ``plus_*``
  keys, ``hash`` and ``signature`` are blanked, because the output is a doctored
  background and must not be mistaken for, or re-synced as, a real roast.

Standard library only, to match the other tools in this directory.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
PLANT_CARD = REPO / 'tools' / 'analysis' / 'plant_roast46.json'

CURVEFILTER = 3          # canvas.py smooth_slice decay window, .aset curvefilter
TRIM_MAX_C = 80.0        # airRoaster.ino INLET_TRIM_MAX_C
SV_CEILING_C = 300.0     # airRoaster.ino INLET_SV_MAX_C

# Keys that carry the source roast's identity.  Blanked on output; see the
# module docstring.
_IDENTITY_KEYS = {
    'roastUUID': '', 'backgroundUUID': '', 'backgroundpath': '',
    'hash': '', 'signature': '', 'plus_sync_record_hash': '',
    'plus_store': '', 'plus_store_label': '',
    'plus_coffee': '', 'plus_coffee_label': '',
}


# --------------------------------------------------------------------------
# small numeric helpers (no numpy -- see the module docstring)
# --------------------------------------------------------------------------
def polyval(coeffs, x):
    """numpy.polyval order: highest power first."""
    y = 0.0
    for c in coeffs:
        y = y * x + c
    return y


def interp(x, xs, ys):
    """Linear interpolation, flat outside the support."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    h = xs[hi] - xs[lo]
    return ys[lo] + (ys[hi] - ys[lo]) * ((x - xs[lo]) / h if h else 0.0)


def linfit(xs, ys):
    """Ordinary least squares slope and intercept."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    m = sxy / sxx if sxx else 0.0
    return m, my - m * mx


def decay_smooth(y, window=CURVEFILTER):
    """canvas.py ``smooth_slice`` decay branch: causal weighted trailing mean.

    Weights 1..window, so at curvefilter 3 they are 1:2:3.  This is what
    Follow-Background mode targets, so it is what the schedule must invert.
    """
    out = []
    for k in range(len(y)):
        seq = y[max(0, k - window + 1): k + 1]
        w = list(range(window - len(seq) + 1, window + 1))
        out.append(sum(a * b for a, b in zip(seq, w)) / sum(w))
    return out


def moving_average(y, window):
    """Centred moving average, shrinking at the edges.  ``window <= 1`` is a
    no-op.  Only used to tame a noisy background's RoR (``--smooth-ror``)."""
    if window <= 1:
        return list(y)
    h = window // 2
    return [sum(y[max(0, k - h): min(len(y), k + h + 1)])
            / len(y[max(0, k - h): min(len(y), k + h + 1)])
            for k in range(len(y))]


# --------------------------------------------------------------------------
# Artisan event-value encoding (artisanlib/util.py:982-999)
# --------------------------------------------------------------------------
def ext_to_internal(v):
    """``events_external_to_internal_value``.  ``v`` is a whole degree."""
    v = int(round(v))
    if v == 0:
        return 0.0
    if v >= 1:
        return v / 10.0 + 1.0
    return v / 10.0 - 1.0


def internal_to_ext(v):
    """``events_internal_to_external_value``; the inverse, used to verify."""
    if -1.0 <= v <= 1.0:
        return 0
    if v < -1.0:
        return -(int(round(abs(v) * 10)) - 10)
    return int(round(v * 10)) - 10


# --------------------------------------------------------------------------
# the profile
# --------------------------------------------------------------------------
def load_alog(path):
    with open(path, encoding='utf-8') as fh:
        return ast.literal_eval(fh.read())


def charge_drop(profile, path):
    """CHARGE and DROP indices, with the trap that has bitten this project.

    ``timeindex[0] == 0`` is a *valid* index meaning "CHARGE is the first
    sample" (profile_003 relies on it), so it is never tested for truthiness.
    ``timeindex[6] == 0`` genuinely does mean "no DROP", and that would disable
    the ``bge <= timeindexB[6]`` window entirely (canvas.py:6444).
    """
    ti = profile['timeindex']
    n = len(profile['timex'])
    ci, di = ti[0], ti[6]
    if not 0 <= ci < n:
        sys.exit(f'{path}: timeindex[0] = {ci} is not a sample index; a background '
                 'without CHARGE replays from START (canvas.py:5381)')
    if di == 0:
        sys.exit(f'{path}: no DROP mark (timeindex[6] = 0).  Every event would '
                 'replay unbounded (canvas.py:6444); mark DROP in Artisan first')
    if not ci < di < n:
        sys.exit(f'{path}: DROP index {di} is not after CHARGE {ci}')
    return ci, di


def check_bt(profile, ci, di, path):
    """The outer PID follows this curve, so it has to be there.

    ``make_inlet_background.py --events`` writes ``temp2 = [-1.0] * len(timex)``
    by construction (state-plan.md § The base-curve authoring gap): an
    inlet-only background with nothing for ``pidSource = 1`` to follow.  Merging
    a base schedule into one of those would produce a file that looks right and
    controls nothing.
    """
    bt = profile['temp2'][ci:di + 1]
    bad = sum(1 for v in bt if v is None or v <= -1.0)
    if bad:
        sys.exit(f'{path}: {bad} of {len(bt)} BT samples between CHARGE and DROP '
                 'are blank (-1).  The outer PID follows BT (pidSource = 1); this '
                 'is an inlet-only background, not a roast profile')


def background_curve(profile, ci):
    """The smoothed BT curve as Follow-Background mode sees it, CHARGE-based.

    ``Background`` re-samples ``timex`` onto a linear grid before smoothing
    (``smooth_slice``), which matters only for a profile with dropped samples.
    """
    timex = profile['timex']
    t0 = timex[ci]
    t = [x - t0 for x in timex]
    n = len(t)
    span = t[-1] - t[0]
    t_lin = [t[0] + span * k / (n - 1) for k in range(n)]
    bt = [interp(x, t, profile['temp2']) for x in t_lin]
    return t_lin, decay_smooth(bt)


# --------------------------------------------------------------------------
# the schedule
# --------------------------------------------------------------------------
def build_schedule(bg_t, bg_y, drop_t, plant, args):
    """``ff`` on the 1 s grid from CHARGE to DROP, with the dip rule applied.

    Returns ``(grid, base, raw_ff, notes)``; ``raw_ff`` is the unclamped
    inversion, kept so the summary can say how far the dip rule moved things.
    """
    a, theta = plant['a'], plant['theta']
    loss = plant['loss_poly']

    # ff(t) reads bg(t + theta), so the last theta seconds of the schedule have
    # no background left to read (state-plan.md § The base-curve authoring gap).
    # The window ends at DROP, not at the last sample: a recorded roast continues
    # into the cooling phase, and reading that steep fall rails the base to --min
    # over exactly the last theta seconds of the roast.  So the background is
    # blended into its own terminal fit over --tail-window and continued along it.
    ext_hi = drop_t + theta + 2.0
    t_end, w0 = drop_t, drop_t - args.tail_window
    bg_drop = interp(drop_t, bg_t, bg_y)
    tail_m, tail_b = 0.0, bg_drop
    if args.tail == 'ror':
        w = [(x, y) for x, y in zip(bg_t, bg_y) if w0 <= x <= drop_t]
        if len(w) >= 2:
            tail_m, tail_b = linfit([q[0] for q in w], [q[1] for q in w])

    def extended(x):
        """The background, blended into its terminal fit over the last window.

        Blending rather than butt-joining matters: ``dbg/dt`` is divided by ``a``,
        so a 0.005 degC/s kink at the seam is a 1 degC step in the base, and the
        knot chooser then spends events on it.
        """
        line = tail_m * x + tail_b
        if x >= t_end:
            return line
        y = interp(x, bg_t, bg_y)
        if x <= w0 or args.tail == 'flat':
            return y
        f = (x - w0) / (t_end - w0)
        return (1.0 - f) * y + f * line

    gx = [float(k) for k in range(0, int(ext_hi) + 1)]
    gy = [extended(x) for x in gx]

    # dbg/dt by central difference, matching dip_strategies.py's np.gradient.
    d = [0.0] * len(gy)
    for k in range(len(gy)):
        if k == 0:
            d[k] = gy[1] - gy[0]
        elif k == len(gy) - 1:
            d[k] = gy[-1] - gy[-2]
        else:
            d[k] = (gy[k + 1] - gy[k - 1]) / 2.0
    d = moving_average(d, args.smooth_ror)

    ff = [gy[k] + (d[k] - polyval(loss, gx[k])) / a for k in range(len(gx))]

    grid = [float(k) for k in range(0, int(round(drop_t)) + 1)]
    raw = [interp(t + theta, gx, ff) for t in grid]

    lo, hi = args.min, args.max
    base = [min(max(v, lo), hi) for v in raw]
    notes = []

    if args.dip != 'follow':
        r0 = args.ramp_start
        if r0 >= drop_t:
            sys.exit(f'--ramp-start {r0} is at or past DROP ({drop_t:.0f} s)')
        if args.dip == 'hold':
            fill = lambda t: raw[int(round(r0))]                    # noqa: E731
            notes.append(f'dip held flat at ff({r0:.0f}) = {raw[int(round(r0))]:.1f}')
        else:
            hi_t = min(r0 + args.extrap_window, drop_t)
            w = [(t, raw[k]) for k, t in enumerate(grid) if r0 <= t <= hi_t]
            m, b = linfit([q[0] for q in w], [q[1] for q in w])
            fill = lambda t: m * t + b                              # noqa: E731
            notes.append(f'dip back-extrapolated from {r0:.0f} s at '
                         f'{m:+.4f} degC/s over {args.extrap_window:.0f} s')
        for k, t in enumerate(grid):
            if t < r0:
                base[k] = min(max(fill(t), lo), hi)
    else:
        notes.append('dip follows the raw inversion, clamped -- '
                     'state-plan.md § Dip strategies simulated this variant')

    return grid, base, raw, notes


# --------------------------------------------------------------------------
# the polyline
# --------------------------------------------------------------------------
def replay(knots, values, grid):
    """What Artisan actually sends: linear interpolation through the whole-degree
    event values (canvas.py:6675-6677)."""
    return [interp(t, knots, [float(v) for v in values]) for t in grid]


def choose_knots(grid, base, tol=None, n=None, limit=64):
    """Greedy insertion at the worst *actual* residual, quantisation included.

    Starts from the two endpoints and repeatedly adds the sample where the
    replayed polyline is furthest from ``base``.  Because the value at each knot
    is rounded to a whole degree before the residual is measured, the tolerance
    is a promise about the delivered schedule, not about an ideal curve.
    """
    idx = [0, len(grid) - 1]
    while True:
        ks = [grid[i] for i in idx]
        vs = [int(round(base[i])) for i in idx]
        r = replay(ks, vs, grid)
        errs = [abs(r[k] - base[k]) for k in range(len(grid))]
        worst = max(range(len(errs)), key=errs.__getitem__)
        if n and len(idx) >= n:
            why = f'--events {n}'
        elif not n and errs[worst] <= tol:
            why = f'--tol {tol}'
        elif worst in idx:
            # The worst point is itself a knot, so its error is the whole-degree
            # quantisation of the event value and no further knot can reduce it.
            why = 'whole-degree event quantisation (floor ~0.5 degC)'
        elif len(idx) >= limit:
            why = f'--max-events {limit}'
        else:
            idx = sorted(idx + [worst])
            continue
        return idx, ks, vs, r, errs, why


# --------------------------------------------------------------------------
# the merge
# --------------------------------------------------------------------------
EVENT_KEYS = ('specialevents', 'specialeventstype', 'specialeventsvalue',
              'specialeventsStrings')


def existing_events(profile):
    if not profile.get('specialevents'):
        return []
    return list(zip(*(profile.get(k, []) for k in EVENT_KEYS)))


def merge_events(profile, etype, indices, values, unit, replace):
    """Add the base events, preserving any events of other types, in index order."""
    keys = EVENT_KEYS
    old = existing_events(profile)
    kept = [e for e in old if e[1] != etype]

    fresh = [(i, etype, ext_to_internal(v), f'{int(round(v))}{unit}')
             for i, v in zip(indices, values)]
    merged = sorted(kept + fresh, key=lambda e: e[0])
    for k, col in zip(keys, zip(*merged)):
        profile[k] = list(col)
    return len(kept)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--into', required=True, metavar='PROFILE.alog',
                    help='the recorded background to merge into (profile_003/004)')
    ap.add_argument('--out', metavar='PATH', help='default: <stem>_base.alog')
    ap.add_argument('--plant', default=str(PLANT_CARD), metavar='CARD.json',
                    help='plant card from roast46_refit.py --emit-plant')
    ap.add_argument('--a', type=float, help='override the plant gain')
    ap.add_argument('--theta', type=float, help='override the plant delay (s)')

    ap.add_argument('--type', type=int, default=2, choices=range(4), metavar='0-3',
                    help='special-event type carrying the base (default 2 = T_inlet)')
    ap.add_argument('--etype-name', default='T_inlet',
                    help="name written into the profile's etypes for --type")

    ap.add_argument('--tol', type=float, default=1.0, metavar='degC',
                    help='max replay error of the polyline against ff (default 1.0)')
    ap.add_argument('--events', type=int, metavar='N',
                    help='fix the event count instead of the tolerance')
    ap.add_argument('--max-events', type=int, default=64, metavar='N')

    ap.add_argument('--dip', choices=('extrapolate', 'hold', 'follow'),
                    default='extrapolate', help='what the base does before --ramp-start')
    ap.add_argument('--ramp-start', type=float, default=90.0, metavar='SEC')
    ap.add_argument('--extrap-window', type=float, default=60.0, metavar='SEC')
    ap.add_argument('--tail', choices=('ror', 'flat'), default='ror',
                    help='how bg(t+theta) is continued past the background')
    ap.add_argument('--tail-window', type=float, default=30.0, metavar='SEC')
    ap.add_argument('--smooth-ror', type=int, default=0, metavar='N',
                    help='centred moving average on dbg/dt for a noisy background')

    ap.add_argument('--min', type=float, default=120.0, metavar='degC')
    ap.add_argument('--max', type=float, default=300.0, metavar='degC')
    ap.add_argument('--replace', action='store_true',
                    help='drop pre-existing events of --type first')
    ap.add_argument('--csv', metavar='PATH', help='write t, ff, base, replay')
    ap.add_argument('--dry-run', action='store_true', help='report, write nothing')
    args = ap.parse_args()

    profile = load_alog(args.into)
    if profile.get('mode') != 'C':
        sys.exit(f"{args.into}: mode is {profile.get('mode')!r}; event values are "
                 'not unit-converted on load (main.py:14474) and the firmware is '
                 'degC-only')
    ci, di = charge_drop(profile, args.into)
    check_bt(profile, ci, di, args.into)
    clash = [e for e in existing_events(profile) if e[1] == args.type]
    if clash and not args.replace:
        sys.exit(f'{args.into}: already carries {len(clash)} special events of '
                 f'type {args.type}; pass --replace to drop them')

    with open(args.plant, encoding='utf-8') as fh:
        plant = json.load(fh)
    if args.a is not None:
        plant['a'] = args.a
    if args.theta is not None:
        plant['theta'] = args.theta

    bg_t, bg_y = background_curve(profile, ci)
    drop_t = bg_t[di]
    grid, base, raw, notes = build_schedule(bg_t, bg_y, drop_t, plant, args)

    idx, knots, values, rep, errs, why = choose_knots(
        grid, base, tol=args.tol, n=args.events, limit=args.max_events)
    # specialevents holds sample *indices*, not times, and the sample interval is
    # not guaranteed to be 1 s -- map each knot back through the profile's own grid.
    def index_at(t):
        return min(range(len(bg_t)), key=lambda i: abs(bg_t[i] - t))
    ev_idx = [index_at(t) for t in knots]

    # --- report ----------------------------------------------------------
    a = plant['a']
    print(f'background {os.path.basename(args.into)}: CHARGE index {ci}, '
          f'DROP index {di} ({drop_t:.0f} s), {len(profile["timex"])} samples')
    print(f'plant      a {a:.5f}  theta {plant["theta"]:.1f} s  tau {1/a:.0f} s  '
          f'({plant.get("source", "?")})')
    for n in notes:
        print(f'           {n}')
    dip = max(abs(base[k] - min(max(raw[k], args.min), args.max))
              for k in range(len(grid)) if grid[k] < args.ramp_start) \
        if args.dip != 'follow' else 0.0
    print(f'schedule   {min(base):.1f} .. {max(base):.1f} degC; '
          f'base(0) {base[0]:.1f}, base(DROP) {base[-1]:.1f}; '
          f'raw ff(0) {raw[0]:.0f}')
    if dip:
        print(f'           dip rule moves the base by up to {dip:.0f} degC '
              f'before {args.ramp_start:.0f} s')
    print(f'events     {len(knots)} of type {args.type}, indices '
          f'{ev_idx[0]}..{ev_idx[-1]}, values {min(values)}..{max(values)} degC')
    print(f'replay     max |error| {max(errs):.2f} degC of base '
          f'(= {max(errs) * a:.4f} degC/s of BT rate), rms '
          f'{(sum(e * e for e in errs) / len(errs)) ** 0.5:.2f}; stopped on {why}')
    if not args.events and max(errs) > args.tol:
        if why.startswith('--max-events'):
            print(f'  WARNING  the knot chooser ran out of events at '
                  f'{args.max_events} and is still {max(errs):.1f} degC out: '
                  'dbg/dt is divided by a, so a rough background costs events.  '
                  'Try --smooth-ror 15, or a smoother background.')
        else:
            print(f'  NOTE     --tol {args.tol} was not reached: event values are '
                  'whole degrees, so the residual cannot go below ~0.5 degC of base '
                  f'(~{0.5 * a:.4f} degC/s of BT rate)')

    clipped = sum(1 for k in range(len(grid))
                  if grid[k] >= args.ramp_start and not args.min <= raw[k] <= args.max)
    if clipped:
        print(f'  WARNING  ff is clamped for {clipped} s after --ramp-start; the '
              'schedule is asking for more than [--min, --max] allows')
    head = SV_CEILING_C - max(values)
    if head < TRIM_MAX_C:
        print(f'  NOTE     base peaks at {max(values)} degC, so the firmware ceiling '
              f'({SV_CEILING_C:.0f}) leaves only +{head:.0f} of the +{TRIM_MAX_C:.0f} '
              'trim range at the top of the roast')
    if min(values) - TRIM_MAX_C <= 0:
        print(f'  NOTE     base bottoms at {min(values)} degC; with trim '
              f'-{TRIM_MAX_C:.0f} the effective setpoint reaches '
              f'{min(values) - TRIM_MAX_C:.0f} -- INLET <= 0 disengages the loop')
    if any(i > di for i in ev_idx):
        sys.exit('internal error: an event landed past DROP (canvas.py:6444)')
    if profile.get('ramp_lookahead'):
        print(f"  NOTE     ramp_lookahead is {profile['ramp_lookahead']} in this "
              'profile; the schedule already carries theta of lead')

    if args.csv:
        with open(args.csv, 'w', encoding='utf-8') as fh:
            fh.write('t,ff_raw,base,replay,error\n')
            for k, t in enumerate(grid):
                fh.write(f'{t:.0f},{raw[k]:.3f},{base[k]:.3f},{rep[k]:.3f},'
                         f'{rep[k] - base[k]:.3f}\n')
        print(f'csv        {args.csv}')

    if args.dry_run:
        print('dry run    nothing written')
        return

    # --- write -----------------------------------------------------------
    etypes = list(profile.get('etypes', ['', '', '', '', '']))
    while len(etypes) < 5:
        etypes.append('')
    if etypes[args.type] != args.etype_name:
        print(f'etypes[{args.type}] {etypes[args.type]!r} -> {args.etype_name!r} '
              '(inert in v4.2.0, canvas.py:6530, but aligned deliberately)')
        etypes[args.type] = args.etype_name
    profile['etypes'] = etypes

    kept = merge_events(profile, args.type, ev_idx, values,
                        profile.get('mode', 'C'), args.replace)
    if kept:
        print(f'preserved  {kept} existing special events of other types')

    profile.update(_IDENTITY_KEYS)
    profile['computed'] = {}
    title = profile.get('title', '')
    if '+base' not in title:
        profile['title'] = f'{title} +base'.strip()

    out = args.out or str(pathlib.Path(args.into).with_name(
        pathlib.Path(args.into).stem + '_base.alog'))
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(repr(profile))
    print(f'wrote      {out}')

    # round-trip the encoding rather than trusting it
    back = load_alog(out)
    got = [internal_to_ext(v) for v, t in zip(back['specialeventsvalue'],
                                              back['specialeventstype'])
           if t == args.type]
    if got != values:
        sys.exit(f'encoding round-trip failed: {got[:5]} != {values[:5]}')
    print(f'verified   {len(got)} event values survive the '
          'external->internal->external round trip')


if __name__ == '__main__':
    main()
