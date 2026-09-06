"""Frequency-domain margins for the Artisan outer loop.

Loop, breaking at the PID output (duty)::

    L(s) = (Kp + Ki/s + Kd*s/(1 + s/wd)) * Kact * a/(s + a)
           * 1/(1 + tau2*s) * exp(-tot*s)

``Kact`` is the actuator gain of the target subrange -- ``(max-min)/100`` degC of
inlet setpoint per duty unit, 1.6 for the 140/300 range in use.  ``tot`` is the
plant transport delay plus the loop's own small lags (inner loop, BT smoothing,
the one-sample ordering between ``pid.update()`` and ``setSV``).

``tau2`` is the plant's **second lag** and defaults to 0, which reproduces every
number these functions returned before it existed.  It is not cosmetic: roast 48
identifies the ``Inlet -> BT`` path as ``theta ~ 0`` plus a 10-13 s lag rather
than 8-13 s of pure deadtime (state-history.md § Deadtime versus lag), and a lag
and a delay of the same size cost different phase -- ``-arctan(w*tau2)``, which
saturates at 90 deg, against ``-w*theta``, which does not.  Below the crossover
the two are nearly the same, which is exactly why the open-loop residual on a
smooth roast cannot separate them; the arithmetic here is where the difference
would show up if it were large.
"""

from __future__ import annotations

import numpy as np


def _pade(T, n):
    """Pade [n/n] approximation of ``exp(-T s)`` as (numerator, denominator).

    ``scipy.signal.pade`` was removed in SciPy 1.15, so the coefficients are
    built directly:  c_k = (2n-k)! n! / ((2n)! k! (n-k)!) * (-T)^k  (numerator)
    and the same with +T (denominator), highest power first.
    """
    from math import factorial as fact

    num = [fact(2 * n - k) * fact(n) / (fact(2 * n) * fact(k) * fact(n - k))
           * (-T) ** k for k in range(n + 1)]
    den = [fact(2 * n - k) * fact(n) / (fact(2 * n) * fact(k) * fact(n - k))
           * (T) ** k for k in range(n + 1)]
    return np.array(num[::-1]), np.array(den[::-1])

# small fixed lags outside the identified plant delay, in seconds
INNER_LOOP_LAG = 1.0      # Inlet vs commanded SV, measured
BT_SMOOTHING = 0.67       # curvefilter=3, weights 1:2:3 (canvas.py:4958-4976)
SAMPLE_ORDERING = 1.0     # pid.update() at canvas.py:5016 runs before setSV at 5184
EXTRA_LAG = INNER_LOOP_LAG + BT_SMOOTHING + SAMPLE_ORDERING


def loop_tf(w, a, theta, Kp, Ki, Kd=0.0, Kact=1.6, extra=EXTRA_LAG,
            deriv_filter_hz=0.1, tau2=0.0):
    s = 1j * np.asarray(w, dtype=complex)
    C = Kp + Ki / s
    if Kd:
        wd = 2 * np.pi * deriv_filter_hz
        C = C + Kd * s / (1.0 + s / wd)
    L = C * Kact * (a / (s + a)) * np.exp(-(theta + extra) * s)
    if tau2 > 0:
        L = L / (1.0 + tau2 * s)
    return L


def margins(a, theta, Kp, Ki, Kd=0.0, **kw):
    """Return (gain-crossover rad/s, phase margin deg, period s at crossover).

    ``tau2`` passes through to :func:`loop_tf`.
    """
    w = np.logspace(-4, 0, 40001)
    L = loop_tf(w, a, theta, Kp, Ki, Kd, **kw)
    mag = np.abs(L)
    idx = np.nonzero((mag[:-1] >= 1.0) & (mag[1:] < 1.0))[0]
    if len(idx) == 0:
        return np.nan, np.nan, np.nan
    i = idx[-1]
    f = (np.log(mag[i]) - 0.0) / (np.log(mag[i]) - np.log(mag[i + 1]))
    wc = float(np.exp(np.log(w[i]) + f * (np.log(w[i + 1]) - np.log(w[i]))))
    Lc = loop_tf(np.array([wc]), a, theta, Kp, Ki, Kd, **kw)[0]
    pm = float(180.0 + np.degrees(np.angle(Lc)))
    return wc, pm, 2 * np.pi / wc


def closed_loop_modes(a, theta, Kp, Ki, Kd=0.0, Kact=1.6, extra=EXTRA_LAG,
                      npade=6, tau2=0.0):
    """Dominant closed-loop poles via a Pade approximation of the delay.

    Returns the least-damped oscillatory mode as (period_s, zeta).  This is the
    period a ring would actually be observed at; :func:`margins` returns the
    *crossover* period, which is a different quantity and runs longer.  Roast 45's
    measured 177 s ring is a closed-loop period, so compare it against this.
    """
    tot = theta + extra
    num_d, den_d = _pade(tot, npade)
    # plant a/(s+a) * delay, and the second lag if there is one
    num_p = np.polymul([a], num_d)
    den_p = np.polymul([1.0, a], den_d)
    if tau2 > 0:
        den_p = np.polymul(den_p, [tau2, 1.0])
    # controller (Kp*s + Ki)/s   (Kd omitted: it needs its own filter pole)
    num_c, den_c = np.array([Kp, Ki]), np.array([1.0, 0.0])
    if Kd:
        wd = 2 * np.pi * 0.1
        num_c = np.polyadd(np.polymul([Kp, Ki], [1.0 / wd, 1.0]), [Kd, 0.0, 0.0])
        den_c = np.polymul([1.0, 0.0], [1.0 / wd, 1.0])
    num = np.polymul(np.polymul(num_c, num_p), [Kact])
    den = np.polymul(den_c, den_p)
    cl_den = np.polyadd(den, num)
    poles = np.roots(cl_den)
    osc = [p for p in poles if p.imag > 1e-9]
    if not osc:
        return np.nan, np.nan
    p = max(osc, key=lambda z: z.real)           # least damped
    wn = abs(p)
    return float(2 * np.pi / p.imag), float(-p.real / wn)
