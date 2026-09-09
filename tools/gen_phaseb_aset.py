#!/usr/bin/env python3
"""Build the Phase B roast config from `airRoaster_cascadePID_preheat.aset`.

Phase B (state-plan.md § TEST PLAN § Phase B) is roast 56's configuration with
**one** change to the roast — the `Fan 60` step at 02:00 removed, so fan 64 is
held from before CHARGE to DROP — plus **one** change to instrumentation that
cannot affect the measurement: a ninth alarm that marks DROP from the inlet
spike.

Two edits, both line-level, both against the preheat file so the LA 12 row stays
off exactly as roast 57 ran it:

1. `alarmflag` row 7 (`Fan 60`, CHARGE+120 s) 1 -> 0.  Row 8 (`LA 12`) is
   already 0 in the source file.
2. a new alarm row 9 appended to all eleven alarm lists:

       From DRY END, offset 0, source = HT, below 20 %, action 13 = DROP

`alarmsource = 7` is the HT channel: canvas.py:5323-5331 reads extra channels as
`source - 2`, even into `extratemp1` and odd into `extratemp2`, so 7 is
`extratemp2[(7-2)//2]` = `extratemp2[2]`, which `extraname2` names `HT`.

`alarmoffset` **must** be 0.  canvas.py:5272 only evaluates the time branch
`if alarmoffset[i] > 0`, and the time and temperature branches each set
`alarm_ready` independently, so a non-zero offset would fire the alarm on the
clock alone (state-plan.md § Auto-DROP detection).

`alarmstrings` is unused by action 13 (canvas.py:6260-6263 reads only
`timeindex[6]`); `DROP` is written there so the row is legible in the Alarms
dialog, and because a trailing empty element in a QSettings string list is a
parse risk this file does not need to take.

Why HT and not `Inlet - SV`, which is the more direct statement of the spike:
they fire within 0.5 s of each other on every roast measured (53-57), and HT is
already a channel.  `Inlet - SV` needs a fourth extra device, and adding one to
this file would put a config change with its own failure modes inside the
measurement roast.  See state-plan.md § The inlet spike beats the RoR collapse.

    python3 tools/gen_phaseb_aset.py
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent / 'artisan'
SRC = HERE / 'airRoaster_cascadePID_preheat.aset'
DST = HERE / 'airRoaster_cascadePID_phaseB.aset'

FAN_STEP_ROW = 6          # 0-based: alarm row 7, `Fan 60` at CHARGE+120 s

# the appended DROP-on-inlet-spike row, one value per alarm list
NEW_ALARM = {
    'alarmaction': '13',        # DROP
    'alarmbeep': '0',
    'alarmcond': '0',           # below
    'alarmflag': '1',           # enabled
    'alarmguard': '-1',
    'alarmnegguard': '-1',
    'alarmoffset': '0',         # must be 0 — see the module docstring
    'alarmsource': '7',         # extratemp2[2] = HT
    'alarmstrings': 'DROP',     # unused by action 13
    'alarmtemperature': '20',   # % heater duty
    'alarmtime': '1',           # from DRY END
}


def split_line(line: str) -> tuple[str, list[str]]:
    key, _, rest = line.partition('=')
    return key, rest.split(', ')


def main() -> int:
    if not SRC.exists():
        sys.exit(f'missing {SRC}')
    out = []
    seen = set()
    for line in SRC.read_text().splitlines():
        key, items = split_line(line)
        if key == 'alarmflag':
            if items[FAN_STEP_ROW] != '1':
                sys.exit(f'alarmflag row {FAN_STEP_ROW + 1} is {items[FAN_STEP_ROW]!r},'
                         ' not 1 — the source file is not the one this expects')
            items[FAN_STEP_ROW] = '0'
        if key in NEW_ALARM:
            items = items + [NEW_ALARM[key]]
            seen.add(key)
            line = f'{key}=' + ', '.join(items)
        out.append(line)
    missing = set(NEW_ALARM) - seen
    if missing:
        sys.exit(f'source file has no {sorted(missing)} line(s)')
    DST.write_text('\n'.join(out) + '\n')
    n = len(split_line([l for l in out if l.startswith('alarmaction=')][0])[1])
    print(f'{DST.name}: {n} alarms, fan step off, DROP on HT < 20 % from DRY END')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
