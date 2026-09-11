#!/usr/bin/env python3
"""What temperature each *coffee* cracks at, read out of the roast logs.

The FC temperature is a **property of the lot**, and it is the one number
`tools/make_background.py --fcs <s>:<BT>` cannot derive for itself.  It does not
need to be recorded by hand: every `.alog` carries the coffee's artisan.plus
identifier and the crack mark, so this derives the table instead of duplicating
it.

**Artisan itself cannot store this.**  The `Coffee` record artisan.plus syncs
down (`~/src/artisan/src/plus/stock.py:82-94` at v4.2.0) carries `label`,
`origin`, `varietals`, `grade`, `stock`, `default_unit`, `moisture`, `density`,
`screen_size`, `processing` and `crop_date` -- and no temperature field of any
kind.  So there is nowhere in the roast properties to put it and nothing that
would apply it to a future roast.  The logs are the store; this is the reader.

Four traps, all of which have produced a wrong number in this project:

* **Group by `plus_coffee`, not by the label.**  The same hr_id is written with
  two different `plus_coffee_label` strings (`C1043` is
  ``Ethiopia, Crown Jewel Sidama Daye Bensa Washed`` on roast 56 and
  ``Crown Jewel Sidama Daye Bensa Washed`` on roast 20), so grouping on the
  label splits one coffee in two.
* **`mode` can be `F`.**  Roasts 1-15 are Fahrenheit and their raw `temp2` is in
  degF.  Pooling them unconverted is what puts a 403.7 "degC" first crack in a
  table.
* **Do not pool across coffees.**  This is the error the roast-56 background was
  built on: a "measured mean over roasts 50-55" of 198.8 degC is a mean over
  *three* coffees -- C1074 at 199.8, C1062 at 197.7 -- and describes none of
  them.  Within a lot the spread is 1.6-3.1 degC; between lots it is larger and
  it is not noise.
* **Mass, machine and era are all part of the measurement.**  A crack heard at
  250 g on a hand-driven roast is not the same reading as a 400 g cascade roast
  tracking a background, and a crack heard on a *different roaster* is not
  comparable at all: the same C1043 reads **204.5 degC** across eighteen 250 g
  roasts on the operator's Behmor and **197.7** on this machine.  The log
  directory holds both, so this filters on `roastertype` and only then on
  `--min-mass` / `--since`; the default reports both the full group and the
  cascade-era subset.

    tools/analysis/beans.py                    # every coffee, most-roasted first
    tools/analysis/beans.py --coffee C1043     # one coffee, roast by roast
    tools/analysis/beans.py --since 40 --min-mass 380   # cascade-era only
"""

from __future__ import annotations

import argparse
import ast
import glob
import os
import re

import numpy as np

LOGS = os.path.expanduser("~/Documents/artisan")
# The log directory is shared with the operator's other roasters (a Behmor and a
# Phidget rig, ~530 files).  `roastertype` is the only reliable separator: the
# filename prefix is not (`jwm_...` carries one airRoaster roast).
ROASTER = "airRoaster"

# Cracks outside this band are a mis-set mark or a probe fault, not a coffee.
FC_BAND = (170.0, 215.0)
# The cascade era: roast 40 is the first outer-loop roast (state-history-cascade.md
# § Roast 40) and 380 g the smallest batch run in it.
CASCADE_SINCE, CASCADE_MIN_MASS = 40, 380.0


def _f_to_c(x):
    return (x - 32.0) * 5.0 / 9.0


def read_roasts(logdir=LOGS, roaster=ROASTER):
    """Every `.alog` with a CHARGE and an FCs mark, temperatures in degC."""
    out = []
    for path in sorted(glob.glob(os.path.join(logdir, "*.alog"))):
        try:
            r = ast.literal_eval(open(path).read())
        except Exception:                                   # noqa: BLE001
            continue
        if roaster and not str(r.get("roastertype", "")).startswith(roaster):
            continue
        ti = r.get("timeindex")
        if not ti or ti[0] < 0 or ti[2] <= 0:               # no CHARGE or no FCs
            continue
        timex = np.asarray(r["timex"], dtype=float)
        bt = np.asarray(r["temp2"], dtype=float)
        if r.get("mode") == "F":
            bt = _f_to_c(bt)
        t = timex - timex[ti[0]]
        fcs_t = float(t[ti[2]])
        fcs_bt = float(np.interp(fcs_t, t, bt))
        if not (FC_BAND[0] <= fcs_bt <= FC_BAND[1]):
            continue
        m = re.search(r"(\d+)(?=\.alog$)", os.path.basename(path))
        out.append(dict(
            rid=int(m.group(1)) if m else -1,
            path=path,
            coffee=r.get("plus_coffee") or "(unlinked)",
            label=r.get("plus_coffee_label") or r.get("title") or "",
            mass=float(r["weight"][0]),
            moisture=float(r.get("moisture_greens", 0.0) or 0.0),
            fcs_t=fcs_t,
            fcs_bt=fcs_bt,
            # slope over +-15 s, the same window state-history-cascade.md quotes
            ror=(float(np.interp(fcs_t + 15, t, bt))
                 - float(np.interp(fcs_t - 15, t, bt))) / 30.0 * 60.0,
            dev=(float(t[ti[6]]) - fcs_t) if ti[6] > 0 else float("nan"),
        ))
    return out


def _stats(xs):
    b = np.array([x["fcs_bt"] for x in xs])
    return dict(n=len(b), mean=b.mean(), median=float(np.median(b)),
                lo=b.min(), hi=b.max(),
                ror=float(np.mean([x["ror"] for x in xs])),
                dev=float(np.nanmean([x["dev"] for x in xs])))


def _row(x):
    return (f"      r{x['rid']:<3d} {x['mass']:4.0f} g  FCs {x['fcs_t']:6.1f} s  "
            f"BT {x['fcs_bt']:6.1f}  RoR {x['ror']:5.1f}  dev {x['dev']:5.1f} s"
            f"{'' if x['moisture'] else '   (no moisture entered)'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", default=LOGS)
    ap.add_argument("--roaster", default=ROASTER,
                    help="`roastertype` prefix to keep; '' for every machine")
    ap.add_argument("--coffee", help="one artisan.plus hr_id, e.g. C1043")
    ap.add_argument("--since", type=int, default=0, help="lowest roast number to include")
    ap.add_argument("--min-mass", type=float, default=0.0)
    args = ap.parse_args()

    rows = [x for x in read_roasts(args.logs, args.roaster)
            if x["rid"] >= args.since and x["mass"] >= args.min_mass]
    if not rows:
        print("no roasts matched")
        return

    groups = {}
    for x in rows:
        groups.setdefault(x["coffee"], []).append(x)
    if args.coffee:
        groups = {k: v for k, v in groups.items() if k == args.coffee}
        if not groups:
            print(f"no roasts of {args.coffee}")
            return

    for hr_id, xs in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        xs.sort(key=lambda x: x["rid"])
        s = _stats(xs)
        label = max((x["label"] for x in xs), key=len)
        print(f"\n{hr_id}  {label}")
        print(f"   n={s['n']}  FCs BT mean {s['mean']:.2f}  median {s['median']:.2f}  "
              f"range {s['lo']:.1f}-{s['hi']:.1f} (spread {s['hi'] - s['lo']:.1f})  "
              f"RoR {s['ror']:.1f}  dev {s['dev']:.1f} s")
        casc = [x for x in xs
                if x["rid"] >= CASCADE_SINCE and x["mass"] >= CASCADE_MIN_MASS]
        if casc and len(casc) != len(xs):
            c = _stats(casc)
            print(f"   cascade-era only (r>={CASCADE_SINCE}, >={CASCADE_MIN_MASS:.0f} g): "
                  f"n={c['n']}  mean {c['mean']:.2f}  median {c['median']:.2f}  "
                  f"range {c['lo']:.1f}-{c['hi']:.1f}  RoR {c['ror']:.1f}")
        if args.coffee or len(xs) > 1:
            for x in xs:
                mark = "  <- cascade" if x in casc and len(casc) != len(xs) else ""
                print(_row(x) + mark)
        best = casc or xs
        b = _stats(best)
        print(f"   -> make_background.py --fcs <s>:{b['median']:.1f} "
              f"--ror-at-fcs {b['ror']:.1f}"
              + ("" if casc else "   (no cascade-era roast; treat as provisional)"))


if __name__ == "__main__":
    main()
