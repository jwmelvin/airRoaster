#!/usr/bin/env python3
"""Roast 49 against the step-6 predictions, and the simulator at 0.5 s sampling.

Step 6 is the runtime `svLookahead` switch: `pidLookahead(0)` at CHARGE+1 s and
`pidLookahead(6)` at CHARGE+90 s, from two hidden Artisan-Command buttons driven
by time-from-CHARGE alarms (`artisan/airRoaster_cascadePID_lookahead.aset`).
Roast 46 is the one-variable baseline; state-plan.md § Step 6 carries the
predictions this reproduces.

Roast 49 is also the first log at Artisan's new 0.5 s sampling with "Drop
Spikes" off, so section 4 doubles as a check that the validated PID replay
carries over unchanged -- the outer loop's gains are rate-independent
(`Ki*err*dt` in real seconds, `svLookahead` in seconds), only the two IIR
filters and the `curvefilter` window move.

Needs numpy and scipy.

    .venv/bin/python tools/analysis/roast49_step6.py
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from roastdata import load_profile                      # noqa: E402
from artisan_pid import Background                      # noqa: E402
from sim import LoopConfig, replay_pid                  # noqa: E402

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, "Documents/artisan/airRoaster_%d.alog")
PROFILE_003 = os.path.join(REPO, "artisan/profile_003.alog")

CHARGE_DETECT = 3.0        # autoCHARGE backdating, canvas.py:5121-5126
SWITCH_T = 90.0            # the pidLookahead(6) alarm
FLOOR_C = 140.0            # positiveTargetRangeLimit min


def bg_offset(roast, background):
    """Sub-second residual left by ``timealign``'s whole-second movebackground."""
    d = (roast.raw["timex"][roast.raw["timeindex"][0]]
         - background.raw["timex"][background.raw["timeindex"][0]])
    return -(d - round(d))


def channel(p, name):
    """One extra-device curve as (t_since_charge, y), either Y column."""
    r = p.raw
    t0 = r["timex"][r["timeindex"][0]]
    for key, tkey in (("extraname1", "extratemp1"), ("extraname2", "extratemp2")):
        if name in r.get(key, []):
            i = r[key].index(name)
            return (np.asarray(r["extratimex"][i], float) - t0,
                    np.asarray(r[tkey][i], float))
    raise KeyError(f"{name} not in {p.path}")


def section_marks(roasts, bg):
    print("== 1. time to BT, against the background ==")
    print(f"   {'':>6} " + "".join(f"{lvl:>18}" for lvl in (150, 180, 196.5)))
    for name, p in roasts:
        cells = ""
        for lvl in (150, 180, 196.5):
            cells += f"{p.time_to_bt(lvl) - bg.time_to_bt(lvl):>+11.1f} s     "
        print(f"   {name:>6} {cells}")
    print("   (step 6 predicted -1.9 / +3.2 / +0.9 s; roast 46 ran +3.4 / +4.9 / +4.8)")


def section_tracking(roasts, bg, lo=180.0):
    print("\n== 2. steady tracking error, 3:00 to DROP-10 ==")
    for name, p in roasts:
        off = bg_offset(p, bg)
        hi = p.marks["DROP"] - 10.0
        t = np.arange(lo, hi, 0.5)
        err = bg.bt_at(t + off) - p.bt_at(t)          # target - PV
        slope = np.gradient(bg.bt_at(t + off), t)
        lag = err / slope
        print(f"   {name:>6}  mean {np.nanmean(err):+.2f} degC   rms {np.sqrt(np.nanmean(err**2)):.2f}"
              f"   lag {np.nanmean(lag):+.2f} s   range {np.nanmin(err):+.2f} .. {np.nanmax(err):+.2f}")
    print("   (step 6 predicted +0.05 degC / 0.44 s)")


def section_sv(p, bg):
    print("\n== 3. the commanded setpoint ==")
    ts, sv = channel(p, "SV")
    th, ht = channel(p, "HT")
    ti, inl = p.extras["Inlet"]
    dt = float(np.median(np.diff(ts)))
    drop = p.marks["DROP"]
    m = (ts >= 0) & (ts <= drop)
    floor = float(np.sum(sv[m] <= FLOOR_C + 0.5) * dt)
    last = float(ts[m][sv[m] <= FLOOR_C + 0.5][-1]) if floor else float("nan")
    print(f"   sampling {dt:.3f} s   SV {np.nanmin(sv[m]):.1f} .. {np.nanmax(sv[m]):.1f} degC")
    print(f"   on the {FLOOR_C:.0f} degC floor for {floor:.1f} s, last at {last:.0f} s"
          "   (predicted 16 s; roast 46 measured 11)")

    m2 = (ts >= 60) & (ts <= drop)
    peak, worst, wt = sv[m2][0], 0.0, 0.0
    for a, b in zip(ts[m2], sv[m2]):
        peak = max(peak, b)
        if b - peak < worst:
            worst, wt = b - peak, a
    print(f"   worst downward reversal after 1:00: {worst:.2f} degC at {wt:.0f} s"
          "   (predicted 3.2; roast 46 measured 0.3)")

    # the switch: the SV jump the pidLookahead(6) alarm produces
    pre = float(np.interp(SWITCH_T - 0.5, ts, sv))
    jump = float(np.interp(SWITCH_T + 2.0, ts, sv))
    post = float(np.max(sv[(ts >= SWITCH_T) & (ts <= SWITCH_T + 30)]))
    off = bg_offset(p, bg)
    step = float(bg.bt_at(SWITCH_T + off + 6.0) - bg.bt_at(SWITCH_T + off))
    settle = ts[(ts >= SWITCH_T) & (ts <= SWITCH_T + 60)]
    svs = sv[(ts >= SWITCH_T) & (ts <= SWITCH_T + 60)]
    t95 = next((a for a, b in zip(settle, svs) if b >= pre + 0.95 * (post - pre)),
               float("nan"))
    print(f"   the 1:30 switch: target step {step:+.2f} degC -> SV {pre:.1f}"
          f" -> {jump:.1f} within 2 s ({jump - pre:+.1f} degC), peak {post:.1f}"
          f" ({post - pre:+.1f}), 95% of it in {t95 - SWITCH_T:.0f} s")
    print("   (predicted +4.0 degC -> +24.7 degC, settled in ~15 s)")

    inl_i = np.interp(ts, ti, inl)
    mq = (ts >= 120) & (ts <= drop - 10)
    e = inl_i[mq] - sv[mq]
    hti = np.interp(ts, th, ht)
    print(f"\n   inner loop 2:00-DROP: mean {np.nanmean(e):+.2f} rms {np.sqrt(np.nanmean(e**2)):.2f}"
          f" max |e| {np.nanmax(np.abs(e)):.2f} degC")
    print(f"   heat {np.nanmin(hti[m]):.0f}-{np.nanmax(hti[m]):.0f} %,"
          f" {np.sum(hti[m] >= 99.5) * dt:.1f} s at 100, {np.sum(hti[m] <= 0.5) * dt:.1f} s at 0")

    # Artisan's destructive equal-run repair (canvas.py:4535) leaves a linear
    # ramp into every step of a constant-valued channel; with Drop Spikes off
    # the step should be one sample wide.
    k = int(np.nanargmax(np.abs(np.diff(sv))))
    print(f"   drop-spikes check, samples around the largest SV step: "
          + " ".join(f"{v:.1f}" for v in sv[max(0, k - 3):k + 3]))


def section_replay(p, bg, rate):
    print("\n== 4. PID replay: measured BT -> commanded SV ==")
    off = bg_offset(p, bg)
    back = Background(bg.t, bg.bt, bg.marks["DROP"], curvefilter=3)
    ts, svm = channel(p, "SV")
    dt = 1.0 / rate
    t = np.arange(0.0, p.marks["DROP"], dt)
    cfg = LoopConfig(Kp=3.0, Ki=0.07, svLookahead=6.0, sampling_rate=rate,
                     charge_detect_delay=CHARGE_DETECT,
                     lookahead_schedule=[(1.0, 0.0), (SWITCH_T, 6.0)])
    out = replay_pid(back, t, p.bt_at(t), cfg, iterm0=0.0, bg_offset=off)
    meas = np.interp(t, ts, svm)
    for lo, hi in ((0, 30), (30, 120), (120, 240), (240, t[-1]), (30, t[-1])):
        m = (t >= lo) & (t <= hi) & np.isfinite(out["sv"])
        e = out["sv"][m] - meas[m]
        print(f"   {lo:4.0f}-{hi:4.0f}s  mean {np.nanmean(e):+6.2f}  rms {np.sqrt(np.nanmean(e**2)):5.2f}"
              f"  max|e| {np.nanmax(np.abs(e)):6.2f}")
    m = (t >= 200) & (t <= 400)
    slope = np.polyfit(t[m], out["I"][m], 1)[0]
    print(f"   Iterm 200-400 s climbs at {slope:.4f} duty/s  ->  e_ss = (dI/dt)/Ki"
          f" = {slope / cfg.Ki:.2f} degC")
    print(f"   Iterm: {out['I'][int(SWITCH_T / dt)]:.1f} at 1:30, {out['I'][-1]:.1f} at DROP")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=2.0,
                    help="Artisan sampling rate in Hz (roast 49 ran at 2)")
    args = ap.parse_args()

    p49 = load_profile(ALOG % 49)
    p46 = load_profile(ALOG % 46)
    bg = load_profile(PROFILE_003)
    roasts = [("49", p49), ("46", p46)]

    section_marks(roasts, bg)
    section_tracking(roasts, bg)
    section_sv(p49, bg)
    section_replay(p49, bg, args.rate)


if __name__ == "__main__":
    main()
