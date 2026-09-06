#!/usr/bin/env python3
"""Charge-state robustness of the outer loop's dip handling, strategy by strategy.

The question this answers: the `Ki`-gate hands the ramp an integrator at ~8 duty
when the ramp needs ~30, so the loop spends the DRY phase catching up.  What, if
anything, fixes that *without* measuring the incoming bean temperature?

Everything is run against the roast-46 plant and the validated `PID.update()`
port (state-plan.md § Roast 46 refit), from CHARGE+2 s to DROP.

The charge sweep
----------------
Roast 46 was a **frozen** charge (state-plan.md § Charge temperature), so the
physically reachable variation is one-sided: warmer, by up to ~42 degC.  A
warmer charge is injected as an extra mixing term in the plant disturbance,

    d(t) = (0.386 * dT / tau_mix) * exp(-(t - t0) / tau_mix)

whose integral is the ``0.386 degC of BT dip per degC of charge temperature``
implied by the measured 0-13 s fall (59.6 degC on 400 g frozen; a room
temperature batch should fall ~28% less).  ``tau_mix = 5 s`` puts mixing
essentially complete by 13 s, which is where the 13.5 s plant delay says the
heater first gets a vote.

NOTE this is *not* the sweep behind the tables in state-plan.md § The dip is a
different control problem; that code was ad hoc and is not in the repository.
This one gives materially smaller baseline sensitivity -- see § Dip strategies.

Strategies
----------
``base``        roast 46 as run: `Ki` 0.07, `svLookahead` 3
``LA``          step 6: `pidLookahead` 0 at CHARGE+1 s, 6 at CHARGE+90 s
``LA+KI``       `airRoaster_cascadePID_lookahead_kigate.aset`
``LA+GS``       the same gate built from Artisan's *native gain scheduling* on
                BT instead of two timed alarms
``FF``          inlet feed-forward schedule + the PID as a bounded trim
                (needs an `INLET TRIM` firmware command; see § Dip strategies)
``FF+KI``       both
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plantfit as pf                                       # noqa: E402
from roastdata import load_profile                          # noqa: E402
from artisan_pid import Background, PIDcontrol              # noqa: E402
from sim import LoopConfig, make_pid                        # noqa: E402

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALOG = os.path.join(HOME, "Documents/artisan/airRoaster_%d.alog")
PROFILE_003 = os.path.join(REPO, "artisan/profile_003.alog")

CHARGE_DETECT = 3.0          # autoCHARGE backdating, canvas.py:5121-5126
FIT_WINDOW_LO = 45.0
FIT_ORDER = 4
DIP_PER_DEGC = 0.386
TAU_MIX = 5.0
T0 = 2.0


class TrimPIDcontrol(PIDcontrol):
    """The firmware holds the inlet schedule; the PID output is a bounded trim.

    ``INLET = ff(t_since_CHARGE) + trim``.  Artisan drives this with event
    playback on one slider (the base) and the PID's positive target on another
    (the trim) -- `specialeventplayback` is per event type (canvas.py:1848), so
    the two do not collide the way playback and the PID did on slider 3.
    """

    def __init__(self, *a, ff=None, trim_min=-80.0, trim_max=80.0, **kw):
        super().__init__(*a, **kw)
        self.ff = ff
        self.trim_min, self.trim_max = trim_min, trim_max
        self.t_now = 0.0

    def setEnergy(self, v):
        trim = float(np.interp(v, [0, 100], [self.trim_min, self.trim_max]))
        raw = self.ff(self.t_now) + trim
        heat = int(round(raw))
        if self.last_event_int is None or heat != self.last_event_int:
            self.last_event_int = heat
            self.commanded_sv = raw


def gain_schedule_on(pid, s0, s1, ki0, ki1, on_sv=False):
    """Artisan's native gain scheduling: a linear map in PV (or SV), clamped to
    ``[min(ki0, ki1), max(ki0, ki1)]`` (pid.py:370-386)."""
    pid.gain_scheduling = True
    pid.gain_scheduling_on_SV = on_sv
    pid.gain_scheduling_quadratic = False
    pid.Schedule0, pid.Schedule1 = s0, s1
    pid.Ki, pid.Ki1 = ki0, ki1
    pid.Kp1, pid.Kd1 = pid.Kp, pid.Kd


def run(bg, cfg, plant, t1, bt0, iterm0, bg_offset, inlet0, sv0,
        ff=None, pid_patch=None, dt=0.25, inlet_tau=0.76, inlet_delay=0.25):
    pid, ctl = make_pid(cfg, bg, iterm0=iterm0, target0=sv0)
    if ff is not None:
        ctl = TrimPIDcontrol(bg, pid, ff=ff, svLookahead=cfg.svLookahead,
                             sv_filter=cfg.sv_filter,
                             positiveTargetMin=cfg.positiveTargetMin,
                             positiveTargetMax=cfg.positiveTargetMax,
                             slider_min=cfg.slider_min, slider_max=cfg.slider_max)
        ctl.charged = True
        ctl.charge_detect_delay = cfg.charge_detect_delay
        pid.control = ctl.setEnergy
    if pid_patch is not None:
        pid_patch(pid)

    n = int(round((t1 - T0) / dt)) + 1
    ts = T0 + dt * np.arange(n)
    bt = np.empty(n)
    inlet = np.empty(n)
    sv = np.full(n, np.nan)
    it = np.full(n, np.nan)
    bt[0], inlet[0] = bt0, inlet0
    ctl.commanded_sv = inlet0
    hist, nxt = [], T0
    alpha = np.exp(-dt / inlet_tau)
    nd = max(0, int(round(inlet_delay / dt)))
    for k in range(n):
        if ts[k] >= nxt - 1e-9:
            for tsw, L in cfg.lookahead_schedule:
                if ts[k] >= tsw:
                    ctl.svLookahead = L
            for tsw, kp, ki, kd in cfg.gain_schedule:
                if ts[k] >= tsw:
                    pid.Kp, pid.Ki, pid.Kd = kp, ki, kd
            if ff is not None:
                ctl.t_now = ts[k]
            hist.append(bt[k])
            hist = hist[-cfg.curvefilter:]
            pv = float(np.average(hist, weights=np.arange(1, len(hist) + 1)))
            pid.update(pv, ts[k])
            s = ctl.calcSV(ts[k] - bg_offset)
            if s is not None and s != ctl.sv:
                ctl.setSV(max(0.0, s), init=False)
            nxt += 1.0
        sv[k], it[k] = ctl.commanded_sv, pid.Iterm
        if k + 1 < n:
            inlet[k + 1] = alpha * inlet[k] + (1 - alpha) * sv[max(0, k - nd)]
            bt[k + 1] = bt[k] + dt * plant(ts[k], bt[k], inlet[k])
    return {"t": ts, "bt": bt, "inlet": inlet, "sv": sv, "I": it}


def _cross(t, y, level):
    for k in range(1, len(y)):
        if y[k - 1] < level <= y[k]:
            return t[k - 1] + (level - y[k - 1]) / (y[k] - y[k - 1]) * (t[k] - t[k - 1])
    return float("nan")


def metrics(r, bg, bg_offset):
    t, bt = r["t"], r["bt"]
    err = np.array([bg.smoothed_bt_at(x - bg_offset) for x in t]) - bt
    w = (t >= 90) & (t <= 200)
    s = (t >= 300) & (t <= 420)
    return dict(
        TP=float(bt.min()),
        I90=float(r["I"][np.argmin(np.abs(t - 90.0))]),
        Iend=float(r["I"][-1]),
        worst=float(err[w][np.argmax(np.abs(err[w]))]),
        mean=float(err[s].mean()),
        rms=float(np.sqrt((err[s] ** 2).mean())),
        didt=float(np.polyfit(t[s], r["I"][s], 1)[0]),
        dt150=_cross(t, bt, 150.0) - (_cross(bg.t, bg.sbt, 150.0) + bg_offset),
        dt196=_cross(t, bt, 196.5) - (_cross(bg.t, bg.sbt, 196.5) + bg_offset),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep", type=float, nargs="*", default=[0.0, 21.0, 42.0],
                    help="charge temperatures, degC WARMER than roast 46's frozen charge")
    args = ap.parse_args()

    p46, p03 = load_profile(ALOG % 46), load_profile(PROFILE_003)
    bg = Background(p03.t, p03.bt, p03.marks["DROP"])
    diff = (p46.raw["timex"][p46.raw["timeindex"][0]]
            - p03.raw["timex"][p03.raw["timeindex"][0]])
    off = -(diff - round(diff))
    drop = p46.marks["DROP"]

    te, ye = p46.extras["Inlet"]
    tf = np.arange(FIT_WINDOW_LO, drop + 1e-9, 1.0)
    f = pf.fit_integral(tf, p46.bt_at(tf), te, ye, order=FIT_ORDER,
                        thetas=np.arange(0, 36.01, 0.25))
    tg = np.arange(T0, drop + 1e-9, 1.0)
    slow, ol = pf.fit_disturbance(tg, p46.bt_at(tg), te, ye, f.a, f.theta,
                                  knot_spacing=8.0)
    print(f"plant a={f.a:.5f} theta={f.theta:.1f}s tau={1/f.a:.0f}s; "
          f"open-loop replay {ol:.3f} degC")

    bt0 = float(p46.bt_at(T0))
    inlet0 = float(p46.extra_at("Inlet", T0))
    sv0 = bg.smoothed_bt_at(T0 - 1 - off + 3)
    base = lambda x: float(np.interp(x, tg, slow))          # noqa: E731

    def plant_for(dT):
        amp = DIP_PER_DEGC * dT / TAU_MIX
        buf, nd = [], max(1, int(round(f.theta / 0.25)))

        def g(t, bt, inlet_now):
            buf.append(inlet_now)
            if len(buf) > nd + 1:
                buf.pop(0)
            extra = amp * np.exp(-(t - T0) / TAU_MIX) if t >= T0 else 0.0
            return f.a * (buf[0] - bt) + base(t) + extra
        return g

    # The feed-forward schedule.  Inverting the plant on the *background*:
    #   Inlet(t) = bg(t+theta) + (dbg/dt(t+theta) - loss(t+theta)) / a
    # The loss term is a cubic fitted over 45 s..DROP and extrapolated back, so
    # the schedule knows nothing about the charge dip -- which is the honest
    # case, since the dip is exactly the part that is not repeatable.
    grid = np.arange(0.0, drop + 60.0, 1.0)
    bgv = np.array([bg.smoothed_bt_at(x) for x in grid])
    cpoly = np.polyfit(np.arange(45.0, drop + 1e-9, 1.0),
                       [base(x) for x in np.arange(45.0, drop + 1e-9, 1.0)], 3)

    def make_ff(a_err=1.0):
        ffv = np.clip(bgv + (np.gradient(bgv, grid) - np.polyval(cpoly, grid))
                      / (f.a * a_err), 120.0, 300.0)
        return lambda t: float(np.interp(t + f.theta, grid, ffv))   # noqa: E731

    LA = [(1.0, 0.0), (90.0, 6.0)]
    KI = [(1.0, 3.0, 0.0, 0.0), (90.0, 3.0, 0.07, 0.0)]

    def mk(**kw):
        d = dict(Ki=0.07, svLookahead=3, charge_detect_delay=CHARGE_DETECT)
        d.update(kw)
        return LoopConfig(**d)

    trim = dict(svLookahead=0, positiveTargetMin=0, positiveTargetMax=160)
    V = [
        ("base (roast 46)", mk(), {}),
        ("LA (step 6)", mk(lookahead_schedule=list(LA)), {}),
        ("LA+KI (the file)", mk(lookahead_schedule=list(LA),
                                gain_schedule=list(KI)), {}),
        ("LA+GS(BT 70-95)", mk(lookahead_schedule=list(LA)),
         dict(pid_patch=lambda p: gain_schedule_on(p, 70, 95, 0.0, 0.07))),
        ("FF trim", mk(**trim), dict(ff=make_ff(), iterm0=50.0)),
        ("FF trim + KI", mk(gain_schedule=list(KI), **trim),
         dict(ff=make_ff(), iterm0=50.0)),
        ("FF trim + KI, a -20%", mk(gain_schedule=list(KI), **trim),
         dict(ff=make_ff(0.8), iterm0=50.0)),
        ("FF trim + KI, a +20%", mk(gain_schedule=list(KI), **trim),
         dict(ff=make_ff(1.2), iterm0=50.0)),
    ]

    hdr = (f"{'strategy':22s} {'dT':>4s} {'TP':>6s} {'I@90':>6s} {'I@DROP':>7s} "
           f"{'worst':>7s} {'mean':>6s} {'rms':>5s} {'dt150':>6s} {'dt196':>6s} "
           f"{'dI/dt':>6s}")
    print(hdr)
    print("-" * len(hdr))
    for name, cfg, extra in V:
        rows = []
        for dT in args.sweep:
            r = run(bg, cfg, plant_for(dT), drop, bt0,
                    extra.get("iterm0", 8.0), off, inlet0, sv0,
                    ff=extra.get("ff"), pid_patch=extra.get("pid_patch"))
            m = metrics(r, bg, off)
            rows.append(m)
            print(f"{name:22s} {dT:+4.0f} {m['TP']:6.1f} {m['I90']:6.1f} "
                  f"{m['Iend']:7.1f} {m['worst']:+7.2f} {m['mean']:+6.2f} "
                  f"{m['rms']:5.2f} {m['dt150']:+6.1f} {m['dt196']:+6.1f} "
                  f"{m['didt']:+6.3f}")
        sp = lambda k: max(x[k] for x in rows) - min(x[k] for x in rows)  # noqa: E731
        print(f"{'  spread over sweep':22s} {'':4s} {'':6s} {sp('I90'):6.1f} "
              f"{'':7s} {'':7s} {'':6s} {'':5s} {sp('dt150'):6.1f}\n")


if __name__ == "__main__":
    main()
