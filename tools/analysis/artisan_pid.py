"""A faithful reimplementation of Artisan v4.2.0's software PID and its
Follow-Background plumbing, for offline replay of this roaster's outer loop.

Ported function-by-function from ``~/src/artisan`` at tag ``v4.2.0``:

* ``PID.update``                     pid.py:394-492
* ``PID._should_integrate``          pid.py:286-297
* ``PID._back_calculate_integral``   pid.py:314-333
* ``PID.applyIntegralLimits``        pid.py:359-364
* ``PID._calculate_derivative``      pid.py:249-278
* ``PID.getParameter`` (scheduling)  pid.py:370-387
* ``_calculate_integral_limits``     pid.py:44-63
* ``PIDcontrol.calcSV``              pid_control.py:1658-1717
* ``PIDcontrol.smooth_sv``           pid_control.py:1643-1655
* ``PIDcontrol.setEnergy``           pid_control.py:1292-1324
* ``ApplicationWindow.addEvent_internal`` main.py (the integer gate that
  decides whether a slider command is actually sent)
* ``ArtisanCanvas.decay_average``    canvas.py:4613-4640 (the smoothed PV)
* the ordering that gives the loop one sample of its own: ``pid.update()`` runs
  at canvas.py:5016, ``calcSV``/``setSV`` at canvas.py:5184, so the target the
  PID uses is always the one computed on the previous tick.

The bumpless snap at pid.py:406-408 (``target = i`` on every inactive sample)
is in ``update`` and is the reason ``Iterm`` is merely *frozen*, not wound,
while the PID is switched off.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import iirfilter


class _LiveSos:
    """Streaming second-order-section filter, transposed direct form II.

    Equivalent to Artisan's ``LiveSosFilter`` (filters.py) and to
    ``scipy.signal.sosfilt`` applied sample by sample; written out here rather
    than imported so no AGPL source is vendored into this MIT repository.
    """

    def __init__(self, sos):
        self.sos = np.asarray(sos, dtype=float)
        self.state = np.zeros((self.sos.shape[0], 2))

    def __call__(self, x):
        if np.isnan(x):
            return x
        y = x
        for s in range(self.sos.shape[0]):
            b0, b1, b2, _a0, a1, a2 = self.sos[s]
            y = b0 * x + self.state[s, 0]
            self.state[s, 0] = b1 * x - a1 * y + self.state[s, 1]
            self.state[s, 1] = b2 * x - a2 * y
            x = y
        return float(y)


def _calculate_integral_limits(outMin, outMax, integral_limit_factor):
    """pid.py:44-63."""
    integral_range = (outMax - outMin) * integral_limit_factor
    if outMin >= 0:
        return 0.0, integral_range
    if outMax <= 0:
        return -integral_range, 0.0
    return -integral_range / 2, integral_range / 2


def _irr_filter(sampling_rate, wn):
    return _LiveSos(iirfilter(1, Wn=max(0.0, min(wn, sampling_rate / 2 - 0.001)),
                                   fs=sampling_rate, btype="low", ftype="butter",
                                   output="sos"))


class PID:
    """pid.py's ``PID``, minus the Qt semaphore and the logging."""

    def __init__(self, control=lambda _: None, p=2.0, i=0.03, d=0.0,
                 beta=1.0, gamma=1.0, sampling_rate=1.0):
        self.outMin, self.outMax = 0, 100
        self.dutySteps = 1
        self.dutyMin, self.dutyMax = 0, 100
        self.control = control
        self.Kp, self.Ki, self.Kd = p, i, d
        self.beta, self.gamma = beta, gamma
        self.sampling_rate = sampling_rate

        self.gain_scheduling = False
        self.gain_scheduling_on_SV = True
        self.gain_scheduling_quadratic = False
        self.Kp1, self.Ki1, self.Kd1 = p, i, d
        self.Kp2, self.Ki2, self.Kd2 = p, i, d
        self.Schedule0 = self.Schedule1 = self.Schedule2 = 0

        self.Pterm = self.Iterm = self.Dterm = 0.0
        self.errSum = 0.0
        self.lastError = None
        self.lastInput = None
        self.lastOutput = None
        self.lastTime = None
        self.target = 0.0
        self.active = False

        self.output_filter_level = 0
        self.output_filter = _irr_filter(sampling_rate, 0.35)
        self.derivative_filter_level = 0
        self.derivative_filter = _irr_filter(sampling_rate, 0.1)

        self.force_duty = 3
        self.iterations_since_duty = 0

        self.lastTarget = 0.0
        self.derivative_limit = 100.0
        self.measurement_history = []
        self.max_len_measurement_history = 5
        self.setpoint_changed_significantly = False
        self.significant_setup_change_limit = 15.0

        self.integral_windup_prevention = True
        self.integral_limit_factor = 1.0
        self.setpoint_change_threshold = 25.0
        self.integral_reset_on_setpoint_change = False
        self.back_calculation_factor = 0.5
        self.integral_just_reset = True

    # -- gain scheduling ----------------------------------------------------
    def getParameter(self, PV, y1, y2, y3):
        if self.gain_scheduling:
            x = self.target if self.gain_scheduling_on_SV else PV
            if self.gain_scheduling_quadratic:
                c = np.polyfit([self.Schedule0, self.Schedule1, self.Schedule2],
                               [y1, y2, y3], 2)
                lo, hi = min(y1, y2, y3), max(y1, y2, y3)
            else:
                c = np.polyfit([self.Schedule0, self.Schedule1], [y1, y2], 1)
                lo, hi = min(y1, y2), max(y1, y2)
            return max(lo, min(hi, float(np.poly1d(c)(x))))
        return y1

    def getKp(self, PV): return self.getParameter(PV, self.Kp, self.Kp1, self.Kp2)
    def getKi(self, PV): return self.getParameter(PV, self.Ki, self.Ki1, self.Ki2)
    def getKd(self, PV): return self.getParameter(PV, self.Kd, self.Kd1, self.Kd2)

    # -- internals ----------------------------------------------------------
    def _smooth_output(self, output):
        if self.output_filter_level > 0:
            return self.output_filter(output)
        return output

    def _detect_measurement_discontinuity(self, current_input):
        if len(self.measurement_history) < 2:
            return False
        recent = [abs(self.measurement_history[-i] - self.measurement_history[-i - 1])
                  for i in range(1, min(len(self.measurement_history),
                                        self.max_len_measurement_history - 1))]
        if not recent:
            return False
        avg = sum(recent) / len(recent)
        cur = abs(current_input - self.measurement_history[-1])
        return cur > 2.5 * avg and cur > 1.0

    def _calculate_derivative(self, current_input, dt):
        if self.lastInput is None:
            return 0.0
        error = self.gamma * self.target - current_input
        last_error = self.gamma * self.lastTarget - self.lastInput
        derror = (error - last_error) / dt
        if self.derivative_filter_level > 0:
            derror = self.derivative_filter(derror)
        if abs(derror) > self.derivative_limit:
            derror = self.derivative_limit if derror > 0 else -self.derivative_limit
        if self.setpoint_changed_significantly:
            derror *= 1 - max(0.0, min(1.0, self.gamma)) / 2
        if self._detect_measurement_discontinuity(current_input):
            derror *= 0.3
        return self.getKd(current_input) * derror

    def _update_measurement_history(self, current_input):
        self.measurement_history.append(current_input)
        if len(self.measurement_history) > self.max_len_measurement_history:
            self.measurement_history.pop(0)

    def _should_integrate(self, error, output_before_clamp):
        if not self.integral_windup_prevention:
            return True
        if self.integral_just_reset:
            return False
        return (not (output_before_clamp > self.outMax and error > 0)
                and not (output_before_clamp < self.outMin and error < 0))

    def _handle_setpoint_change_integral(self, setpoint_change):
        if not self.integral_reset_on_setpoint_change:
            return
        if abs(setpoint_change) > self.setpoint_change_threshold:
            self.Iterm = 0.0
            self.integral_just_reset = True
        elif abs(setpoint_change) > self.setpoint_change_threshold * 0.5:
            self.Iterm *= 0.5

    def _back_calculate_integral(self, PV, before, after):
        if not self.integral_windup_prevention:
            return
        if abs(before - after) > 0.001 and self.getKi(PV) != 0:
            self.Iterm -= (before - after) * self.back_calculation_factor
            self.Iterm = self.applyIntegralLimits(PV, self.Iterm)

    def applyIntegralLimits(self, PV, iterm):
        lo, hi = _calculate_integral_limits(self.outMin, self.outMax,
                                            self.integral_limit_factor)
        hi += self.getKp(PV) * (1 - self.beta) * self.target
        return max(lo, min(hi, iterm))

    # -- the loop -----------------------------------------------------------
    def update(self, i, now):
        """pid.py:394-492.  ``now`` replaces ``time.time()``."""
        control_func = None
        output_value = None
        if i is not None and not self.active:
            self.target = i                      # bumpless transfer, pid.py:406-408
        if i is None or i == -1:
            return
        err = self.target - i
        if self.lastError is None or self.lastTime is None:
            self.lastTime, self.lastError, self.lastInput = now, err, i
            return
        dt = now - self.lastTime
        if dt < 0.05:
            return

        setpoint_change = self.target - self.lastTarget
        if abs(setpoint_change) > 0.001:
            self.setpoint_changed_significantly = (
                abs(setpoint_change) > self.significant_setup_change_limit > 0)
            self._handle_setpoint_change_integral(setpoint_change)
        else:
            self.setpoint_changed_significantly = False

        self.Pterm = self.getKp(i) * (self.beta * self.target - i)
        output_before_integration = self.Pterm + self.Iterm
        if self._should_integrate(err, output_before_integration):
            self.Iterm += self.getKi(i) * err * dt
            self.Iterm = self.applyIntegralLimits(i, self.Iterm)
        self.integral_just_reset = False

        self.Dterm = self._calculate_derivative(i, dt)
        self._update_measurement_history(i)

        self.lastTime, self.lastError, self.lastInput = now, err, i
        self.lastTarget = self.target

        output = self.Pterm + self.Iterm + self.Dterm
        output = self._smooth_output(output)
        output_before_clamp = output
        output = max(float(self.outMin), min(float(self.outMax), output))
        self._back_calculate_integral(i, output_before_clamp, output)

        final_output = min(float(self.dutyMax), max(float(self.dutyMin), output))
        if (self.lastOutput is None
                or self.iterations_since_duty >= self.force_duty
                or final_output >= self.lastOutput + self.dutySteps
                or final_output <= self.lastOutput - self.dutySteps):
            if self.active:
                control_func, output_value = self.control, final_output
            self.lastOutput = output          # note: the clamped output, not final
        self.iterations_since_duty += 1

        if control_func is not None and output_value is not None:
            control_func(output_value)
            self.iterations_since_duty = 0

    def init(self):
        """pid.py:497-533."""
        self.derivative_filter = _irr_filter(self.sampling_rate, 0.1)
        self.output_filter = _irr_filter(self.sampling_rate, 0.35)
        self.errSum = 0.0
        self.lastError = 0.0
        self.lastInput = None
        self.lastTime = None
        self.Pterm = self.Iterm = 0.0
        self.lastOutput = None
        self.lastTarget = self.target
        self.measurement_history = []
        self.setpoint_changed_significantly = False
        self.integral_just_reset = False

    def setTarget(self, target, init=True):
        self.target = target
        if init:
            self.init()


# ---------------------------------------------------------------------------
# Follow-Background plumbing
# ---------------------------------------------------------------------------

def decay_smooth(y, window_len=3):
    """canvas.py ``smooth_slice`` decay branch: causal weighted trailing mean.

    Weights are ``1..window_len``, so at ``curvefilter=3`` the weights are
    1:2:3 and the group delay is 2/3 of a sample.
    """
    y = np.asarray(y, dtype=float)
    w_full = np.arange(1, window_len + 1)
    out = np.empty_like(y)
    for k in range(len(y)):
        seq = y[max(0, k - window_len + 1): k + 1]
        w = w_full[window_len - len(seq):]
        out[k] = np.average(seq, weights=w)
    return out


class Background:
    """A background profile as Follow-Background mode sees it.

    ``timeB`` is CHARGE-relative here; Artisan keeps absolute times and shifts
    ``timeB`` by whole seconds in ``timealign`` (canvas.py:5931-5946), which
    comes to the same thing once both are CHARGE-based.
    """

    def __init__(self, t, bt, drop_t, curvefilter=3):
        t_lin = np.linspace(t[0], t[-1], len(t))       # smooth_slice re-samples
        self.t = t_lin
        self.bt_raw = np.interp(t_lin, t, bt)
        self.sbt = decay_smooth(self.bt_raw, curvefilter)
        self.drop_t = drop_t

    def smoothed_bt_at(self, seconds):
        """``backgroundSmoothedBTat`` -> ``timetemparray2temp``; -1 if out of range."""
        if seconds > self.t[-1] or seconds < self.t[0]:
            return -1.0
        return float(np.interp(seconds, self.t, self.sbt))


class PIDcontrol:
    """The subset of ``pid_control.PIDcontrol`` the cascade uses."""

    def __init__(self, background, pid, svLookahead=3, sv_filter=0,
                 positiveTargetMin=140, positiveTargetMax=300,
                 slider_min=0, slider_max=320, svValue=201.0,
                 svSliderMin=0.0, svSliderMax=250.0):
        self.bg = background
        self.pid = pid
        self.svLookahead = svLookahead
        self.sv_smoothing_factor = 5 if sv_filter else 0    # sv_smoothing_factor_default
        self.sv_decay_weights = None
        self.previous_svs = []
        self.heat_min = max(positiveTargetMin, slider_min)
        self.heat_max = min(positiveTargetMax, slider_max)
        self.svValue = svValue
        self.svSliderMin, self.svSliderMax = svSliderMin, svSliderMax
        self.sv = None
        self.last_event_int = None      # addEvent_internal's integer gate
        self.commanded_sv = None        # the float actually sent over the wire
        self.charged = False
        self.dropped = False
        # autoCHARGE backdates timeindex[0] by 3 (tight) or 5 (loose) samples
        # (canvas.py:5121-5126, main.py BTbreak), so Follow-Background mode only
        # starts this many ticks after the CHARGE the profile records.
        self.charge_detect_delay = 0.0

    def smooth_sv(self, sv):
        """pid_control.py:1643-1655."""
        if self.sv_smoothing_factor:
            if (self.sv_decay_weights is None
                    or len(self.sv_decay_weights) != self.sv_smoothing_factor):
                self.sv_decay_weights = list(np.arange(1, self.sv_smoothing_factor + 1))
            self.previous_svs.append(sv)
            self.previous_svs = self.previous_svs[-self.sv_smoothing_factor:]
            if len(self.previous_svs) >= self.sv_smoothing_factor:
                return float(np.average(self.previous_svs, weights=self.sv_decay_weights))
        return sv

    def calcSV(self, tx):
        """pid_control.py:1658-1717, Follow-Background branch (svMode 2, BT)."""
        if self.dropped:
            return max(self.svSliderMin, min(self.svSliderMax, self.svValue))
        if not self.charged or tx < self.charge_detect_delay:
            res = self.bg.smoothed_bt_at(0.0)      # background CHARGE BT
            return None if res == -1 else self.smooth_sv(res)
        if tx + self.svLookahead > self.bg.drop_t:
            return None                            # control window closed
        res = self.bg.smoothed_bt_at(tx + self.svLookahead)
        if res == -1:
            return None
        return self.smooth_sv(res)

    def setEnergy(self, v):
        """pid_control.py:1292-1324 plus main.py's ``addEvent_internal`` gate.

        ``raw_heat`` (a float) is what the WebSocket command carries; the
        integer is only what gates the send and what gets recorded as an event.
        """
        raw_heat = float(np.interp(v, [0, 100], [self.heat_min, self.heat_max]))
        heat = int(round(raw_heat))
        if self.last_event_int is None or heat != self.last_event_int:
            self.last_event_int = heat
            self.commanded_sv = raw_heat

    def setSV(self, sv, init=False):
        self.pid.setTarget(sv, init=init)
        self.sv = sv
        self.svValue = sv
