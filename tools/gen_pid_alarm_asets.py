#!/usr/bin/env python3
"""Regenerate the timed-alarm .aset variants from the canonical cascade config.

Each variant is `airRoaster_cascadePID.aset` plus a set of **hidden
Artisan-Command buttons** and **time-only-from-CHARGE alarms** that press them.
Nothing else differs: the gains, the target subrange, the sliders and the
existing two alarms are copied through untouched.

Variants
--------
``lookahead``           `svLookahead` 3 -> 0 at CHARGE+1 s -> 6 at CHARGE+90 s
                        (state-plan.md § The lookahead-switching config, § Roast 46)
``kigate``              `pidKi` 0.07 -> 0 at CHARGE+1 s -> 0.07 at CHARGE+90 s
                        (state-plan.md § The dip is a different control problem)
``lookahead_kigate``    both
``char``                no buttons, no alarms: **key overrides only**.  The
                        open-loop characterisation config for runbook steps 3-5
                        -- PID never arms at CHARGE, both alarms disabled, and
                        background event playback enabled for event types
                        0 (`Air`, slider 1) and 2 (`T_inlet`, slider 3), so the
                        test's inlet *and* fan schedules replay by themselves
                        instead of being hand-driven.
                        (state-plan.md § Files for the characterisation runs)

Why the two alarms per lever, and why 90 s
------------------------------------------
`Ki = 0` closes *both* integral windup paths at once: the `Ki*err*dt` term
contributes nothing, and `_back_calculate_integral` returns early because it is
gated on `getKi(PV) != 0` (pid.py:314-333).  So `Iterm` is frozen through the
charge dip and handed to the ramp at a known value instead of one set by
anti-windup saturation.  Restoring at 90 s rather than earlier is what makes it
work: simulated over a 62 degC swing in charge temperature the handover spread is
34.9 at a 30 s restore, 15.7 at 60 s and **0.6 at 90 s**.

Why the ``char`` variant replays instead of hand-driving
--------------------------------------------------------
`specialeventplayback` is a **per-event-type** 4-element list (canvas.py:1848)
and the master switch `backgroundPlaybackEvents` is separate, so enabling types 0
and 2 drives sliders 1 and 3 from the background and touches nothing else.  The
fan is replayed because `gen_char_doublet.py` puts a fan square wave *inside*
each doublet batch -- hand-timing it would put the run's one measured variable
back under a stopwatch.  Playback
fights the PID for slider 3 (§ Background event playback must be off) -- which is
harmless here precisely because these runs are open-loop, and it makes the
excitation identical between runs instead of hand-timed.  Two consequences worth
knowing: `playbackevent()` only runs once the **foreground CHARGE** is marked
(canvas.py:5381), so Test A must press CHARGE -- which is why `pidOnCHARGE` is
forced off rather than relying on not pressing it -- and events after the
background's DROP are never replayed (canvas.py:6444), which both test files
already respect.  The DROP alarm is disabled because `autoDRY` can mark DRY END
on an empty roaster (BT crosses the 149 threshold in `charstep_empty.alog`),
which would arm a DeltaBT DROP in the middle of a step test.

`p-i-d()` and `pidLookahead()` are both bumpless -- `setPID` (pid.py:552-564)
assigns only the gains and leaves `Iterm` alone.

Traps
-----
* **`p-i-d()` is sticky.**  It writes `pidcontrol.pidKp/Ki/Kd`, so *Save Settings
  while the gate is in force writes `pidKi = 0` into the `.aset`*.  Do not save
  settings during a roast, and re-load the file if a roast is abandoned before
  1:30.
* **If the 90 s alarm does not fire the loop is P-only for the rest of the
  roast** -- a large standing BT deficit, roast 40's failure mode.  Visible at
  once as a flat, low SV while BT falls behind; the CONTROL button is the escape.
* Button numbers in `alarmstrings` are **1-based positions in
  `extraeventslabels`**, so they must be re-derived from the canonical file every
  time.  Never hand-edit them.
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent / 'artisan'
SRC = HERE / 'airRoaster_cascadePID.aset'

# label, Artisan Command, seconds after CHARGE
LOOKAHEAD = [('LA 0', 'pidLookahead(0)', 1),
             ('LA 6', 'pidLookahead(6)', 90)]
KIGATE = [('Ki 0', 'p-i-d(3,0,0)', 1),
          ('Ki on', 'p-i-d(3,0.07,0)', 90)]

VARIANTS = {
    'lookahead': LOOKAHEAD,
    'kigate': KIGATE,
    'lookahead_kigate': LOOKAHEAD + KIGATE,
    'char': [],
}

# whole-line key replacements applied after the buttons/alarms are appended
OVERRIDES = {
    'char': {
        'pidOnCHARGE': 'false',                            # PID must never arm
        'backgroundPlaybackEvents': 'true',                # master playback switch
        'replayType': '0',                                 # replay by time
        'specialeventplayback': 'true, false, true, false',    # Air + T_inlet
        'specialeventplaybackramp': 'false, false, false, false',  # steps, not ramps
        'alarmflag': '0, 0',                               # no auto-DROP in a step test
    },
}

BUTTON_FIELDS = {
    'extraeventbuttoncolor': lambda b, n: '#808080',
    'extraeventbuttontextcolor': lambda b, n: 'white',
    'extraeventsactions': lambda b, n: '20',        # 20 = Artisan Command
    'extraeventsactionstrings': lambda b, n: b[1],
    'extraeventsdescriptions': lambda b, n: '',
    'extraeventslabels': lambda b, n: b[0],
    'extraeventstypes': lambda b, n: '4',           # 4 = no event recorded
    'extraeventsvalues': lambda b, n: '0',
    'extraeventsvisibility': lambda b, n: '0',      # hidden
}
ALARM_FIELDS = {
    'alarmaction': lambda b, n: '2',                # 2 = Event Button
    'alarmbeep': lambda b, n: '0',
    'alarmcond': lambda b, n: '1',
    'alarmflag': lambda b, n: '1',                  # enabled
    'alarmguard': lambda b, n: '-1',
    'alarmnegguard': lambda b, n: '-1',
    'alarmoffset': lambda b, n: str(b[2]),
    'alarmsource': lambda b, n: '-3',               # -3 = time only
    'alarmstrings': lambda b, n: str(n),            # 1-based button number
    'alarmtemperature': lambda b, n: '0',
    'alarmtime': lambda b, n: '0',                  # measured from CHARGE
}


def value_of(lines, key):
    for line in lines:
        if line.startswith(key + '='):
            return line[len(key) + 1:]
    sys.exit(f'missing key in {SRC}: {key}')


def build(name, buttons, lines):
    nbuttons = len(value_of(lines, 'extraeventslabels').split(', '))
    numbers = [nbuttons + 1 + i for i in range(len(buttons))]

    append = {}
    for key, fn in BUTTON_FIELDS.items():
        append[key] = ''.join(', ' + fn(b, n) for b, n in zip(buttons, numbers))
    for key, fn in ALARM_FIELDS.items():
        append[key] = ''.join(', ' + fn(b, n) for b, n in zip(buttons, numbers))

    overrides = OVERRIDES.get(name, {})

    seen, overridden, out = set(), set(), []
    for line in lines:
        m = re.match(r'([A-Za-z_]+)=', line)
        if m and m.group(1) in append:
            seen.add(m.group(1))
            line += append[m.group(1)]
        if m and m.group(1) in overrides:
            overridden.add(m.group(1))
            line = f'{m.group(1)}={overrides[m.group(1)]}'
        out.append(line)
    missing = (set(append) - seen) | (set(overrides) - overridden)
    if missing:
        sys.exit(f'keys not found in canonical file: {sorted(missing)}')

    dst = HERE / f'airRoaster_cascadePID_{name}.aset'
    dst.write_text('\n'.join(out), encoding='utf-8')
    pairs = ', '.join(f'{b[1]} at CHARGE+{b[2]}s [button {n}]'
                      for b, n in zip(buttons, numbers))
    if overrides:
        pairs += ('; ' if pairs else '') + ', '.join(f'{k}={v}' for k, v in overrides.items())
    print(f'{dst.name}: {pairs}')
    return dst


def main():
    lines = SRC.read_text(encoding='utf-8').split('\n')
    print(f'canonical: {len(value_of(lines, "extraeventslabels").split(", "))} event '
          f'buttons, {len(value_of(lines, "alarmaction").split(", "))} alarms')
    wanted = sys.argv[1:] or list(VARIANTS)
    for name in wanted:
        if name not in VARIANTS:
            sys.exit(f'unknown variant {name!r}; choose from {list(VARIANTS)}')
        build(name, VARIANTS[name], lines)


if __name__ == '__main__':
    main()
