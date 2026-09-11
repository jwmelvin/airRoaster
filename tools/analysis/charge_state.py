#!/usr/bin/env python3
"""The charge-state proxy: how cold were the beans that went in?

``greens_temp`` is ``0.0`` on every roast on record, so the charge state of the
existing set has to be inferred.  The plant's transport delay makes that
possible without any control-independent instrument: **nothing the heater does
reaches BT before ~theta seconds after CHARGE**, so the BT fall over
``0 .. theta`` is charge mixing alone (state-history-cascade.md § Charge temperature).

    proxy = (BT(CHARGE) - BT(CHARGE + theta)) / mass * 100      degC / 100 g

Two corrections the raw proxy needs, both found on roast 49:

* **The air already in flight counts.**  Inlet air from ``t in [-theta, 0]``
  arrives during the mixing window, so a hotter pre-charge inlet makes the dip
  look shallower — i.e. the beans look warmer than they were.  Roast 49's
  preheat sat 28 degC above roast 46's, worth ~0.45 degC/100 g of the proxy.
  The correction is ``a * (inlet_pre - INLET_REF) * theta``, with ``a`` and
  ``theta`` read from the plant card.
* **The proxy is not linear in mass.**  Physically the mixing settles at
  ``dBT = m*c*(BT_charge - T_bean) / (C_chamber + m*c)``, so dividing by mass
  only removes the leading term; roast 45 at 345 g reads ~7% low against the
  400 g runs for that reason.  **Compare like masses**, which is why the
  charge-temperature experiment holds mass fixed.

With those in hand, ``proxy_corrected = k * (BT_charge - T_bean)`` calibrates
``k`` on roasts of known (or assumed) charge state and reads the rest off.

Stdlib only -- no venv needed.

    python3 tools/analysis/charge_state.py 43 44 45 46 48 49
    python3 tools/analysis/charge_state.py --frozen 43,44,46 --frozen-temp -18
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import statistics

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, "Documents/artisan/airRoaster_%s.alog")
PLANT = os.path.join(REPO, "tools/analysis/plant_roast46.json")

# The pre-charge inlet the air correction normalises to: roasts 43-46 all sat
# in a 140-152 degC band, so referencing to their middle leaves them untouched.
INLET_REF = 145.0


def _interp(xs, ys, x):
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
    f = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + f * (ys[hi] - ys[lo])


def _mean(xs, ys, lo, hi, step=0.5):
    n = max(2, int((hi - lo) / step) + 1)
    vals = [_interp(xs, ys, lo + k * (hi - lo) / (n - 1)) for k in range(n)]
    return sum(vals) / len(vals)


def load(path):
    with open(path) as fh:
        raw = ast.literal_eval(fh.read())
    t0 = raw["timex"][raw["timeindex"][0]]     # index 0 is a valid CHARGE
    t = [x - t0 for x in raw["timex"]]
    out = {"raw": raw, "t": t, "bt": [float(v) for v in raw["temp2"]]}
    try:
        i = raw["extraname1"].index("Inlet")
        out["inlet"] = ([x - t0 for x in raw["extratimex"][i]],
                        [float(v) for v in raw["extratemp1"][i]])
    except (ValueError, KeyError):
        out["inlet"] = None
    return out


def measure(path, a, theta):
    p = load(path)
    r = p["raw"]
    w = r.get("weight") or [0.0, 0.0, "g"]
    mass = float(w[0])
    bt0 = _interp(p["t"], p["bt"], 0.0)
    bt1 = _interp(p["t"], p["bt"], theta)
    drop = bt0 - bt1
    row = {
        "roast": r.get("roastbatchnr"),
        "mass": mass,
        "bt_charge": bt0,
        "bt_theta": bt1,
        "drop": drop,
        "proxy": (drop / mass * 100.0) if mass else float("nan"),
        "inlet_pre": float("nan"),
        "air_corr": 0.0,
        "greens_temp": r.get("greens_temp"),
        "ambient": r.get("ambientTemp"),
    }
    if p["inlet"] is not None and mass:
        pre = _mean(p["inlet"][0], p["inlet"][1], -theta, 0.0)
        row["inlet_pre"] = pre
        # a hotter pre-charge inlet adds a*(pre-ref)*theta degC of BT over the
        # mixing window, which the raw proxy would read as warmer beans
        row["air_corr"] = a * (pre - INLET_REF) * theta / mass * 100.0
    row["proxy_corr"] = row["proxy"] + row["air_corr"]
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roasts", nargs="*", default=["43", "44", "45", "46", "48", "49"],
                    help="roast numbers, or paths to .alog files")
    ap.add_argument("--frozen", default="43,44,46",
                    help="roasts to calibrate k on (comma separated)")
    ap.add_argument("--frozen-temp", type=float, default=-18.0,
                    help="assumed bean temperature of those roasts, degC")
    ap.add_argument("--plant", default=PLANT)
    args = ap.parse_args()

    with open(args.plant) as fh:
        card = json.load(fh)
    a, theta = float(card["a"]), float(card["theta"])
    print(f"plant card {os.path.basename(args.plant)}: a = {a:.5f}, theta = {theta:.1f} s")
    print(f"air correction referenced to a pre-charge inlet of {INLET_REF:.0f} degC\n")

    rows = []
    for spec in args.roasts:
        path = spec if os.path.sep in spec else ALOG % spec
        if not os.path.exists(path):
            print(f"  (skipped {spec}: no such file)")
            continue
        rows.append(measure(path, a, theta))

    hdr = (f"{'roast':>5} {'mass':>6} {'BT@0':>7} {f'BT@{theta:.0f}':>7} {'drop':>7} "
           f"{'/100g':>7} {'air':>6} {'corr':>7} {'inlet_pre':>9} {'greens':>7}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['roast']:>5} {r['mass']:>6.0f} {r['bt_charge']:>7.1f} {r['bt_theta']:>7.1f} "
              f"{r['drop']:>7.2f} {r['proxy']:>7.2f} {r['air_corr']:>+6.2f} {r['proxy_corr']:>7.2f} "
              f"{r['inlet_pre']:>9.1f} {str(r['greens_temp']):>7}")

    ref = [int(x) for x in args.frozen.split(",") if x.strip()]
    cal = [r for r in rows if r["roast"] in ref]
    if len(cal) < 2:
        return
    masses = {round(r["mass"]) for r in cal}
    if len(masses) > 1:
        print("\n  ! calibration roasts do not share a mass; the proxy is not "
              "linear in mass, so k will absorb the difference")
    ks = [r["proxy_corr"] / (r["bt_charge"] - args.frozen_temp) for r in cal]
    k = statistics.fmean(ks)
    sd = statistics.stdev(ks) if len(ks) > 1 else 0.0
    print(f"\ncalibration on roasts {ref} at T_bean = {args.frozen_temp:+.0f} degC:")
    print(f"  k = {k:.5f} +- {sd:.5f}  ({(sd / k * 100 if k else 0):.1f}%)"
          f"   [proxy_corr = k * (BT_charge - T_bean)]")
    print(f"\n{'roast':>5} {'T_bean':>8}   band over k +- 1 sd")
    for r in rows:
        if not r["mass"]:
            continue
        t_hi = r["bt_charge"] - r["proxy_corr"] / (k + sd) if k + sd else float("nan")
        t_lo = r["bt_charge"] - r["proxy_corr"] / (k - sd) if k - sd else float("nan")
        t = r["bt_charge"] - r["proxy_corr"] / k
        flag = "  <- calibration" if r["roast"] in ref else ""
        if round(r["mass"]) not in masses:
            flag += "  (different mass: not comparable)"
        print(f"{r['roast']:>5} {t:>+8.1f}   {min(t_lo, t_hi):+.1f} .. {max(t_lo, t_hi):+.1f}{flag}")
    print("\nRecord greens_temp in Artisan Roast Properties and this stops being "
          "an inference.")


if __name__ == "__main__":
    main()
