#!/usr/bin/env python3
"""Regenerate airRoaster_cascadePID_lookahead.aset from the canonical config.

The lookahead variant = canonical config + two hidden Artisan-Command buttons
(pidLookahead(0)/pidLookahead(6)) appended after the existing event buttons,
plus two time-only-from-CHARGE alarms that press them.  Button numbers in
`alarmstrings` are 1-based positions in `extraeventslabels`, so they must be
re-derived from the canonical file every time -- never hand-edited.
Spec: state-plan.md "The lookahead-switching config".
"""
import re, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent / 'artisan'
SRC  = HERE / 'airRoaster_cascadePID.aset'
DST  = HERE / 'airRoaster_cascadePID_lookahead.aset'

lines = SRC.read_text(encoding='utf-8').split('\n')

def value_of(key):
    for l in lines:
        if l.startswith(key + '='):
            return l[len(key) + 1:]
    sys.exit(f'missing key: {key}')

# --- derive the new button numbers from the canonical file -------------------
nbuttons = len(value_of('extraeventslabels').split(', '))
la0, la6 = nbuttons + 1, nbuttons + 2          # 1-based, as alarmstrings wants
nalarms  = len(value_of('alarmaction').split(', '))
print(f'canonical: {nbuttons} event buttons, {nalarms} alarms')
print(f'lookahead buttons will be {la0} (LA 0) and {la6} (LA 6)')

# --- the two appended buttons, and the two alarms that press them -----------
BUTTON = {
    'extraeventbuttoncolor':     ', #808080, #808080',
    'extraeventbuttontextcolor': ', white, white',
    'extraeventsactions':        ', 20, 20',                 # 20 = Artisan Command
    'extraeventsactionstrings':  ', pidLookahead(0), pidLookahead(6)',
    'extraeventsdescriptions':   ', , ',
    'extraeventslabels':         ', LA 0, LA 6',
    'extraeventstypes':          ', 4, 4',                   # 4 = no event recorded
    'extraeventsvalues':         ', 0, 0',
    'extraeventsvisibility':     ', 0, 0',                   # hidden
}
ALARM = {
    'alarmaction':      ', 2, 2',                # 2 = Event Button
    'alarmbeep':        ', 0, 0',
    'alarmcond':        ', 1, 1',
    'alarmflag':        ', 1, 1',                # enabled
    'alarmguard':       ', -1, -1',
    'alarmnegguard':    ', -1, -1',
    'alarmoffset':      ', 1, 90',               # seconds after CHARGE
    'alarmsource':      ', -3, -3',              # -3 = time only
    'alarmstrings':     f', {la0}, {la6}',
    'alarmtemperature': ', 0, 0',
    'alarmtime':        ', 0, 0',                # from CHARGE
}

APPEND = {**BUTTON, **ALARM}
seen = set()
out = []
for l in lines:
    m = re.match(r'([A-Za-z_]+)=', l)
    if m and m.group(1) in APPEND:
        k = m.group(1)
        l += APPEND[k]
        seen.add(k)
    out.append(l)

missing = set(APPEND) - seen
if missing:
    sys.exit(f'keys not found in canonical file: {sorted(missing)}')

DST.write_text('\n'.join(out), encoding='utf-8')
print(f'wrote {DST}')
