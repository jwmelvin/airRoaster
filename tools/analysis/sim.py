"""Closed-loop simulator for the cascade: background -> Artisan PID -> inlet SV
-> firmware inner loop -> plant -> BT.

Two modes:

``replay_pid``
    Drive the PID with a *measured* BT trace and check that the commanded SV
    comes back out.  This tests the controller port alone, with no plant model
    in the way.

``simulate``
    Full closed loop against a fitted plant.

The per-tick order follows canvas.py's sample loop exactly: the smoothed PV is
formed first, ``pid.update()`` runs (canvas.py:5016) against the target left
over from the previous tick, and only then does ``calcSV``/``setSV``
(canvas.py:5184) install the target the *next* tick will use.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from artisan_pid import PID, PIDcontrol, Background


@dataclass
class LoopConfig:
    Kp: float = 3.0
    Ki: float = 0.07
    Kd: float = 0.0
    beta: float = 1.0          # pidPsetpointWeight
    gamma: float = 0.0         # pidDsetpointWeight (0 = DoM, 1 = DoE)
    svLookahead: float = 3.0
    sv_filter: int = 0
    duty_filter: int = 1
    derivative_filter: int = 0
    pidDlimit: float = 500.0
    pidIWP: bool = True
    pidIlimitFactor: float = 1.0
    pidIRoC: bool = False
    pidIRoCthreshold: float = 30.0
    dutySteps: int = 1
    dutyMin: int = 0
    dutyMax: int = 100
    positiveTargetMin: int = 140
    positiveTargetMax: int = 300
    slider_min: int = 0
    slider_max: int = 320
    curvefilter: int = 3
    charge_detect_delay: float = 0.0   # autoCHARGE backdating, in ticks/seconds
    # runtime lookahead switching: list of (t_since_charge, new_svLookahead)
    lookahead_schedule: list = field(default_factory=list)
    # runtime gain switching via Artisan's p-i-d(<p>,<i>,<d>) command
    # (main.py:10759 -> pid_control.confPID -> pid.setPID, which assigns the
    # gains and leaves Iterm alone -- bumpless).  List of (t, Kp, Ki, Kd).
    gain_schedule: list = field(default_factory=list)


def make_pid(cfg: LoopConfig, bg: Background, iterm0=0.0, target0=None):
    pid = PID(p=cfg.Kp, i=cfg.Ki, d=cfg.Kd, beta=cfg.beta, gamma=cfg.gamma,
              sampling_rate=1.0)
    pid.setDutySteps = None
    pid.dutySteps, pid.dutyMin, pid.dutyMax = cfg.dutySteps, cfg.dutyMin, cfg.dutyMax
    pid.output_filter_level = cfg.duty_filter
    pid.derivative_filter_level = cfg.derivative_filter
    pid.derivative_limit = cfg.pidDlimit
    pid.integral_windup_prevention = cfg.pidIWP
    pid.integral_limit_factor = cfg.pidIlimitFactor
    pid.integral_reset_on_setpoint_change = cfg.pidIRoC
    pid.setpoint_change_threshold = cfg.pidIRoCthreshold
    pid.integral_just_reset = False
    pid.Iterm = iterm0
    pid.active = True
    ctl = PIDcontrol(bg, pid, svLookahead=cfg.svLookahead, sv_filter=cfg.sv_filter,
                     positiveTargetMin=cfg.positiveTargetMin,
                     positiveTargetMax=cfg.positiveTargetMax,
                     slider_min=cfg.slider_min, slider_max=cfg.slider_max)
    ctl.charged = True
    ctl.charge_detect_delay = cfg.charge_detect_delay
    pid.control = ctl.setEnergy
    if target0 is not None:
        pid.target = target0
        pid.lastTarget = target0
    return pid, ctl


def _apply_schedule(cfg, ctl, t):
    for ts, L in cfg.lookahead_schedule:
        if t >= ts:
            ctl.svLookahead = L
    for ts, kp, ki, kd in cfg.gain_schedule:
        if t >= ts:
            ctl.pid.Kp, ctl.pid.Ki, ctl.pid.Kd = kp, ki, kd


def replay_pid(bg: Background, t, bt_measured, cfg: LoopConfig, iterm0=0.0,
               bg_offset=0.0, sv0=None):
    """Feed measured BT through the controller and return the commanded SV.

    ``bg_offset`` is where the background's CHARGE sits on the roast clock
    after ``timealign``'s whole-second ``movebackground`` (canvas.py:5931-5946).
    """
    pid, ctl = make_pid(cfg, bg, iterm0=iterm0,
                        target0=(bg.smoothed_bt_at(-bg_offset + cfg.svLookahead)
                                 if sv0 is None else sv0))
    ctl.commanded_sv = None
    out = {k: np.full(len(t), np.nan) for k in
           ("sv", "pv", "target", "P", "I", "D", "duty")}
    hist = []
    for k, tk in enumerate(t):
        _apply_schedule(cfg, ctl, tk)
        hist.append(float(bt_measured[k]))
        hist = hist[-cfg.curvefilter:]
        w = np.arange(1, len(hist) + 1)
        pv = float(np.average(hist, weights=w))          # decay_average
        pid.update(pv, tk)
        sv = ctl.calcSV(tk - bg_offset)
        if sv is not None and sv != ctl.sv:
            ctl.setSV(max(0.0, sv), init=False)
        out["pv"][k] = pv
        out["target"][k] = pid.target
        out["P"][k], out["I"][k], out["D"][k] = pid.Pterm, pid.Iterm, pid.Dterm
        out["duty"][k] = (pid.lastOutput if pid.lastOutput is not None else np.nan)
        out["sv"][k] = (ctl.commanded_sv if ctl.commanded_sv is not None else np.nan)
    return out


def simulate(bg: Background, cfg: LoopConfig, plant, t0, t1, bt0,
             iterm0=0.0, bg_offset=0.0, dt_plant=0.25, inlet_tau=0.76,
             inlet_delay=0.25, inlet0=None, bt_noise=0.0, seed=0,
             sv0=None):
    """Full closed loop.

    ``plant`` is a callable ``(t, bt, inlet_delayed) -> dBT/dt``.
    ``inlet_tau``/``inlet_delay`` model the firmware inner loop, measured on
    roast 46 as tau 0.76 s / delay 0.25 s (rms 1.19 degC, mostly ripple).
    """
    rng = np.random.default_rng(seed)
    pid, ctl = make_pid(cfg, bg, iterm0=iterm0,
                        target0=(bg.smoothed_bt_at(-bg_offset + cfg.svLookahead)
                                 if sv0 is None else sv0))
    n = int(round((t1 - t0) / dt_plant)) + 1
    ts = t0 + dt_plant * np.arange(n)
    bt = np.empty(n)
    inlet = np.empty(n)
    sv_trace = np.full(n, np.nan)
    itrace = np.full(n, np.nan)
    ptrace = np.full(n, np.nan)
    ttrace = np.full(n, np.nan)
    bt[0] = bt0
    inlet[0] = bt0 if inlet0 is None else inlet0
    ctl.commanded_sv = inlet[0]

    hist = []
    next_tick = t0
    alpha = np.exp(-dt_plant / inlet_tau)
    ndelay = max(0, int(round(inlet_delay / dt_plant)))
    for k in range(n):
        if ts[k] >= next_tick - 1e-9:
            _apply_schedule(cfg, ctl, ts[k])
            hist.append(bt[k] + (rng.normal(0, bt_noise) if bt_noise else 0.0))
            hist = hist[-cfg.curvefilter:]
            w = np.arange(1, len(hist) + 1)
            pv = float(np.average(hist, weights=w))
            pid.update(pv, ts[k])
            sv = ctl.calcSV(ts[k] - bg_offset)
            if sv is not None and sv != ctl.sv:
                ctl.setSV(max(0.0, sv), init=False)
            next_tick += 1.0
        sv_trace[k] = ctl.commanded_sv
        itrace[k], ptrace[k], ttrace[k] = pid.Iterm, pid.Pterm, pid.target
        if k + 1 < n:
            cmd = sv_trace[max(0, k - ndelay)]
            inlet[k + 1] = alpha * inlet[k] + (1 - alpha) * cmd
            bt[k + 1] = bt[k] + dt_plant * plant(ts[k], bt[k], inlet[k])
    return {"t": ts, "bt": bt, "inlet": inlet, "sv": sv_trace,
            "I": itrace, "P": ptrace, "target": ttrace}


def delayed_inlet_plant(a, theta, slow, hist_dt):
    """Build a plant callable with a ``theta``-second transport delay.

    The delay is served from the simulator's own inlet history, so the plant
    closure keeps a ring buffer of its inputs.
    """
    buf = []
    nd = max(1, int(round(theta / hist_dt)))

    def f(t, bt, inlet_now):
        buf.append(inlet_now)
        if len(buf) > nd + 1:
            buf.pop(0)
        inlet_del = buf[0]
        return a * (inlet_del - bt) + slow(t)

    return f
