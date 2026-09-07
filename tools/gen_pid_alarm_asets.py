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
``chargetemp``          `lookahead` **plus** a disarmed autoCHARGE: `autoCharge`
                        starts `false`, a *visible* `ARM CHG` button turns it on
                        with `autoCHARGE(1)`, and a backstop alarm presses a
                        hidden twin if the operator forgets.  For the
                        charge-temperature pair, whose preheat protocol settles
                        BT down to 130 degC from an elevated pre-preheat -- a
                        descent Artisan would otherwise mark as CHARGE.
                        (state-plan.md § The charge-temperature experiment)
``char``                no buttons, no alarms: **key overrides only**.  The
                        open-loop characterisation config for runbook steps 3-5
                        -- PID never arms at CHARGE, both alarms disabled, and
                        background event playback enabled for event types
                        0 (`Air`, slider 1) and 2 (`T_inlet`, slider 3), so the
                        test's inlet *and* fan schedules replay by themselves
                        instead of being hand-driven.
                        (state-plan.md § Files for the characterisation runs)

Why ``chargetemp`` exists
-------------------------
The pre-preheat settles BT from ~185 degC (empty chamber at `INLET 200`) down to
the 130 degC preheat.  Artisan's autoCHARGE fires on a BT break of `d = -0.34`
degC per sample over two consecutive legs at `Delay=500` (canvas.py:5121,
main.py:24306, params canvas.py:548) -- **0.68 degC/s**, above 77 degC.  The
empty-chamber time constant is 40-50 s (roast 50's reheat), so a 55 degC descent
runs at **1.1-1.3 degC/s** and trips it within seconds.  A gentler overshoot does
not help: 30 degC gives 0.67 degC/s, exactly on the boundary.  So it is disarmed
by config and re-armed deliberately.

`autoCHARGE(<bool>)` is an **Artisan Command** (action 20, main.py:10286), and
alarms cannot issue one -- their action list is 26 fixed entries and "Artisan
Command" is not among them (alarms.py:898).  The route is alarm -> **Event
Button** -> command, the same pattern the timed levers above already use.

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
* **`autoChargeFlag` is persisted** as `autoCharge=` in the `.aset`.  A *Save
  Settings while disarmed* writes `autoCharge=false` into the file and the next
  roast then silently never marks CHARGE -- the same sticky-config class as
  `p-i-d()` above.  Re-load the file rather than saving over it.
* A **missed** arm is worse than a spurious CHARGE: a spurious one can be undone,
  a missing one costs the backdated 3-sample accuracy `charge_state.py` reads the
  charge state from.  Hence the backstop alarm as well as the button.
"""

import collections
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent / 'artisan'
SRC = HERE / 'airRoaster_cascadePID.aset'

Btn = collections.namedtuple(
    'Btn', 'label cmd offset time source cond temp visible action etype evalue')

# Verbatim from the canonical file's own fan buttons: action 22 with this send
# string plus event type 0 is what makes a button both move the fan and record
# the event, so a replayed fan change looks identical to a hand-pressed one.
FAN_SEND = r'"send({{\"command\":\"OT2\",\"value\":{}}})\n"'
ACT_COMMAND, ACT_MULTIPLE, ACT_SEND = 20, 3, 22
ETYPE_AIR, ETYPE_NONE = 0, 4


def btn(label, cmd, offset=None, time=0, source=-3, cond=1, temp=0, visible=False,
        action=ACT_COMMAND, etype=ETYPE_NONE, evalue=0):
    """One Artisan-Command button, and optionally the alarm that presses it.

    ``offset=None`` makes it a button with **no alarm** -- an operator control.
    ``time`` is Artisan's alarm reference (alarms.py:847): 9 = ON, 0 = CHARGE,
    1 = DRY END.  ``source`` is its index minus 3 (alarms.py:804): -3 = time
    only, -1 = DeltaBT, 1 = BT.  ``cond`` is 0 = ``<``, 1 = ``>``.
    """
    return Btn(label, cmd, offset, time, source, cond, temp, visible,
               action, etype, evalue)


LOOKAHEAD = [btn('LA 0', 'pidLookahead(0)', 1),
             btn('LA 6', 'pidLookahead(6)', 90)]
KIGATE = [btn('Ki 0', 'p-i-d(3,0,0)', 1),
          btn('Ki on', 'p-i-d(3,0.07,0)', 90)]
# The operator's arm button, and a backstop that presses a hidden twin if it is
# forgotten.  The backstop is BOTH time- and temperature-gated, and the
# temperature gate is the one doing the work: BT crosses 131 about 3 time
# constants into the settle (tau ~45 s empty), by which point it is drifting at
# ~0.02 degC/s against autoCHARGE's 0.68 degC/s threshold, so arming there
# cannot trip it.  The 16:00 from ON only guards against the elevated phase
# being skipped altogether, and is early enough to cover a protocol that runs
# short.  A backstop that fires after CHARGE is harmless: `autoChargeIdx` and
# `timeindex[0]` both block re-detection (canvas.py:5121).
CHARGE_ARM = [btn('ARM CHG', 'autoCHARGE(1)', visible=True),
              btn('ARM bak', 'autoCHARGE(1)', offset=960, time=9,
                  source=1, cond=0, temp=131)]

# The charge gate.  `pid_control.py:1687`: until `timeindex[0]` is set, Follow
# Background returns *the background's CHARGE temperature* -- one constant -- not
# the curve.  autoCHARGE needs ~5 samples of BT-break evidence, so for ~3.5 s
# after the beans go in the target is pinned at 130 while BT is already through
# 116.  That inverts the error's sign (live tracking wants -10, the frozen target
# says +14) and roast 52 answered it by stepping T_inlet 140 -> 224 in a single
# 0.5 s sample with heat at 100%.  The energy lands 13.5 s later, on the turning
# point, and the loop then spent 37.5 s on the floor undoing it.
#
# The loop has *no authority* over 0..theta -- nothing the heater does reaches BT
# before ~13.5 s -- so gating it off there costs nothing and removes the kick.
# It also makes the plant satisfy the assumption `make_charge_background.py`
# builds the dip on: the inlet held at its pre-charge value.  Same assumption on
# both sides, which is why this closes rather than trading one error for another.
#
# `PID OFF` cannot be an alarm: alarms fire *from CHARGE*, which is the mark that
# arrives too late.  It is pressed by hand, folded into one CHARGE button with
# the fan step so it cannot be forgotten or mistimed.
CHARGE_GATE = [
    btn('CHARGE', '"4,19"', visible=True, action=ACT_MULTIPLE),   # Fan FULL + PID OFF
    btn('PID on', 'PIDon', offset=15),                            # first action lands ~28 s
]
# The fan step, timed rather than hand-pressed.  At 2:00 the dip is long over, the
# 1:30 lookahead switch has settled (95% in 12 s on roast 49) and DRY END is still
# ~60 s away, so it lands in the quietest window in the roast.  The plant has no
# fan term (`kf = 0`, roast 48), so this moves the operating point and not the
# dynamics: holding BT needs ~3.5 degC more inlet at fan 60 than at 64.
FAN_CUT = [btn('Fan 60', FAN_SEND, offset=120, action=ACT_SEND,
               etype=ETYPE_AIR, evalue=7.0)]

VARIANTS = {
    'lookahead': LOOKAHEAD,
    'kigate': KIGATE,
    'lookahead_kigate': LOOKAHEAD + KIGATE,
    'chargetemp': LOOKAHEAD + CHARGE_ARM + CHARGE_GATE + FAN_CUT,
    'char': [],
}

# whole-line key replacements applied after the buttons/alarms are appended
OVERRIDES = {
    'chargetemp': {
        'autoCharge': 'false',   # re-armed by the ARM CHG button, or the backstop
    },
    'char': {
        'pidOnCHARGE': 'false',                            # PID must never arm
        'backgroundPlaybackEvents': 'true',                # master playback switch
        'replayType': '0',                                 # replay by time
        'specialeventplayback': 'true, false, true, false',    # Air + T_inlet
        'specialeventplaybackramp': 'false, false, false, false',  # steps, not ramps
        'alarmflag': '0, 0',                               # the DeltaBT auto-DROP alarm
        'autoDrop': 'false',                               # *and* Artisan's built-in one
    },
}

BUTTON_FIELDS = {
    'extraeventbuttoncolor': lambda b, n: '#808080',
    'extraeventbuttontextcolor': lambda b, n: 'white',
    'extraeventsactions': lambda b, n: str(b.action),
    'extraeventsactionstrings': lambda b, n: b.cmd,
    'extraeventsdescriptions': lambda b, n: '',
    'extraeventslabels': lambda b, n: b.label,
    'extraeventstypes': lambda b, n: str(b.etype),
    'extraeventsvalues': lambda b, n: str(b.evalue),
    'extraeventsvisibility': lambda b, n: '1' if b.visible else '0',
}
ALARM_FIELDS = {
    'alarmaction': lambda b, n: '2',                # 2 = Event Button
    'alarmbeep': lambda b, n: '0',
    'alarmcond': lambda b, n: str(b.cond),
    'alarmflag': lambda b, n: '1',                  # enabled
    'alarmguard': lambda b, n: '-1',
    'alarmnegguard': lambda b, n: '-1',
    'alarmoffset': lambda b, n: str(b.offset),
    'alarmsource': lambda b, n: str(b.source),
    'alarmstrings': lambda b, n: str(n),            # 1-based button number
    'alarmtemperature': lambda b, n: str(b.temp),
    'alarmtime': lambda b, n: str(b.time),
}


def value_of(lines, key):
    for line in lines:
        if line.startswith(key + '='):
            return line[len(key) + 1:]
    sys.exit(f'missing key in {SRC}: {key}')


def build(name, buttons, lines):
    nbuttons = len(value_of(lines, 'extraeventslabels').split(', '))
    numbers = [nbuttons + 1 + i for i in range(len(buttons))]

    # Every entry becomes a button; only those carrying an offset get an alarm.
    alarmed = [(b, n) for b, n in zip(buttons, numbers) if b.offset is not None]

    append = {}
    for key, fn in BUTTON_FIELDS.items():
        append[key] = ''.join(', ' + fn(b, n) for b, n in zip(buttons, numbers))
    for key, fn in ALARM_FIELDS.items():
        append[key] = ''.join(', ' + fn(b, n) for b, n in alarmed)

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
    refs = {9: 'ON', 0: 'CHARGE', 1: 'DRY END'}
    def describe(b, n):
        if b.offset is None:
            return f'{b.cmd} on the {b.label!r} button [button {n}, visible]'
        where = f'{refs.get(b.time, b.time)}+{b.offset}s'
        if b.source != -3:
            where += f' and BT {"<" if b.cond == 0 else ">"} {b.temp:g}'
        return f'{b.cmd} at {where} [button {n}]'
    pairs = ', '.join(describe(b, n) for b, n in zip(buttons, numbers))
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
