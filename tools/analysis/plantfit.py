"""First-order-plus-deadtime plant identification for the bean-temperature loop.

Model
-----
::

    dBT/dt = a * (Inlet(t - theta) - BT(t)) + slow(t)

``slow(t)`` stands in for drying, exotherm and anything else that moves the heat
balance on a roast timescale.  It is **restricted to a low-order polynomial in
t**.  That restriction is the whole point: a free per-sample residual ``w(t)``
absorbs exactly the mismatch a transport delay creates, which is what produced
the retracted "deadtime ~ 0 s" result (state-plan.md § Correction).

Two estimators, same model:

``fit_derivative``
    Regresses a numerically differentiated BT on ``(Inlet(t-theta) - BT)`` and
    the polynomial basis.  Residual is in degC/s.

``fit_integral`` (preferred)
    Integrates the model instead, so nothing is differentiated::

        BT(t) = BT(t0) + a * U(t; theta) + Q(t),  U = int (Inlet(s-theta) - BT(s)) ds

    ``Q`` is a polynomial one degree higher than ``slow``.  The residual is in
    degC of BT and the noise entering it is the raw 0.07 degC BT noise rather
    than its derivative.

Both are linear in the parameters for a fixed ``theta``, so ``theta`` is found
by a one-dimensional scan and the rest by least squares.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _cheb_basis(t, order):
    """Chebyshev design matrix (columns 0..order) on ``t`` mapped to [-1, 1]."""
    x = 2.0 * (t - t[0]) / (t[-1] - t[0]) - 1.0
    cols = [np.ones_like(x), x]
    for k in range(2, order + 1):
        cols.append(2 * x * cols[-1] - cols[-2])
    return np.column_stack(cols[: order + 1])


def savgol_deriv(y, dt, window, polyorder=2):
    """Savitzky-Golay first derivative, edges trimmed by the caller."""
    from scipy.signal import savgol_filter

    return savgol_filter(y, window, polyorder, deriv=1, delta=dt, mode="interp")


@dataclass
class PlantFit:
    theta: float
    a: float
    tau: float
    coeffs: np.ndarray       # polynomial (Chebyshev) coefficients of the disturbance
    resid_rms: float
    n: int
    order: int
    window: tuple
    estimator: str
    scan: np.ndarray         # (theta, resid_rms) over the scan grid
    cov_a: float = np.nan    # OLS variance of a, inflated for residual autocorrelation

    def __repr__(self):
        return (f"PlantFit({self.estimator}, theta={self.theta:.1f}s, "
                f"a={self.a:.5f}, tau={self.tau:.0f}s, "
                f"resid={self.resid_rms:.4g}, n={self.n}, order={self.order})")


def _delayed(t, theta, t_in, inlet):
    return np.interp(t - theta, t_in, inlet, left=np.nan, right=np.nan)


def lag1(u, tau2, dt):
    """Exact first-order discretisation of ``1/(1 + tau2 s)`` driven by ``u``.

    ``x[0] = u[0]`` -- the lag starts settled, which is what a fit window opened
    well after CHARGE wants.  ``tau2 <= 0`` is the pass-through.
    """
    if tau2 <= 0:
        return np.asarray(u, dtype=float)
    from scipy.signal import lfilter

    alpha = np.exp(-dt / tau2)
    return lfilter([1.0 - alpha], [1.0, -alpha], u, zi=[alpha * u[0]])[0]


def _solve(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    return beta, r


def _neff_scale(r):
    """Inflation factor on OLS variance for AR(1)-correlated residuals."""
    if len(r) < 10:
        return 1.0
    rho = float(np.corrcoef(r[:-1], r[1:])[0, 1])
    rho = min(max(rho, 0.0), 0.999)
    return (1.0 + rho) / (1.0 - rho)


def fit_derivative(t, bt, t_in, inlet, order=3, thetas=np.arange(0, 41, 1.0),
                   sg_window=21):
    dt = float(np.median(np.diff(t)))
    dbt = savgol_deriv(bt, dt, sg_window)
    P = _cheb_basis(t, order)
    scan = []
    best = None
    for th in thetas:
        u = _delayed(t, th, t_in, inlet) - bt
        good = ~np.isnan(u)
        X = np.column_stack([u[good], P[good]])
        beta, r = _solve(X, dbt[good])
        rms = float(np.sqrt(np.mean(r ** 2)))
        scan.append((th, rms))
        if best is None or rms < best[0]:
            var_a = (np.var(r, ddof=X.shape[1]) *
                     np.linalg.pinv(X.T @ X)[0, 0] * _neff_scale(r))
            best = (rms, th, beta, int(good.sum()), var_a)
    rms, th, beta, n, var_a = best
    a = float(beta[0])
    return PlantFit(theta=float(th), a=a, tau=1.0 / a if a > 0 else np.inf,
                    coeffs=beta[1:], resid_rms=rms, n=n, order=order,
                    window=(float(t[0]), float(t[-1])), estimator="derivative",
                    scan=np.array(scan), cov_a=float(var_a))


def fit_integral(t, bt, t_in, inlet, order=3, thetas=np.arange(0, 41, 1.0)):
    """``order`` is the order of ``slow(t)``; the fitted polynomial is order+1."""
    dt = float(np.median(np.diff(t)))
    P = _cheb_basis(t, order + 1)
    scan = []
    best = None
    for th in thetas:
        d = _delayed(t, th, t_in, inlet) - bt
        if np.isnan(d).any():
            raise ValueError(
                "the input series must extend at least `max(thetas)` before the "
                "fit window; padding it here would bias the delay estimate")
        U = np.concatenate([[0.0], np.cumsum(0.5 * (d[1:] + d[:-1])) * dt])
        X = np.column_stack([U, P])
        beta, r = _solve(X, bt)
        rms = float(np.sqrt(np.mean(r ** 2)))
        scan.append((th, rms))
        if best is None or rms < best[0]:
            var_a = (np.var(r, ddof=X.shape[1]) *
                     np.linalg.pinv(X.T @ X)[0, 0] * _neff_scale(r))
            best = (rms, th, beta, len(t), var_a)
    rms, th, beta, n, var_a = best
    a = float(beta[0])
    return PlantFit(theta=float(th), a=a, tau=1.0 / a if a > 0 else np.inf,
                    coeffs=beta[1:], resid_rms=rms, n=n, order=order,
                    window=(float(t[0]), float(t[-1])), estimator="integral",
                    scan=np.array(scan), cov_a=float(var_a))


def block_bootstrap(t, bt, t_in, inlet, order, thetas, n_boot=200,
                    block=60, estimator="integral", seed=0):
    """Moving-block bootstrap over the residuals; returns (theta, a) samples.

    The block length must exceed the residual correlation time or the spread
    comes out far too tight -- these residuals are smooth, so 60 s is the
    minimum defensible choice.
    """
    fit = (fit_integral if estimator == "integral" else fit_derivative)
    base = fit(t, bt, t_in, inlet, order=order, thetas=thetas)

    dt = float(np.median(np.diff(t)))
    d = _delayed(t, base.theta, t_in, inlet) - bt
    U = np.concatenate([[0.0], np.cumsum(0.5 * (d[1:] + d[:-1])) * dt])
    P = _cheb_basis(t, order + 1)
    X = np.column_stack([U, P])
    yhat = X @ np.concatenate([[base.a], base.coeffs])
    resid = bt - yhat

    rng = np.random.default_rng(seed)
    nb = int(np.ceil(len(t) / block))
    out = []
    for _ in range(n_boot):
        starts = rng.integers(0, max(1, len(resid) - block), size=nb)
        rs = np.concatenate([resid[s:s + block] for s in starts])[: len(t)]
        f = fit(t, yhat + rs, t_in, inlet, order=order, thetas=thetas)
        out.append((f.theta, f.a))
    return base, np.array(out)


def fit_integral_fan(t, bt, t_in, inlet, fan, order=4,
                     thetas=np.arange(0, 41, 1.0), kfs=(0.0,)):
    """``fit_integral`` with a fan-scaled plant gain.

    ``a_eff(fan) = a * (1 + kf * (fan - 60))``.  ``kf`` is gridded because the
    model is not linear in it; ``a`` and the disturbance polynomial still come
    out of one least-squares solve per grid point.
    """
    dt = float(np.median(np.diff(t)))
    P = _cheb_basis(t, order + 1)
    best = None
    scan = []
    for kf in kfs:
        s = 1.0 + kf * (fan - 60.0)
        for th in thetas:
            d = _delayed(t, th, t_in, inlet) - bt
            if np.isnan(d).any():
                raise ValueError("input series does not cover t - max(theta)")
            g = s * d
            U = np.concatenate([[0.0], np.cumsum(0.5 * (g[1:] + g[:-1])) * dt])
            X = np.column_stack([U, P])
            beta, r = _solve(X, bt)
            rms = float(np.sqrt(np.mean(r ** 2)))
            scan.append((th, kf, rms))
            if best is None or rms < best[0]:
                var_a = (np.var(r, ddof=X.shape[1]) *
                         np.linalg.pinv(X.T @ X)[0, 0] * _neff_scale(r))
                best = (rms, th, kf, beta, var_a)
    rms, th, kf, beta, var_a = best
    a = float(beta[0])
    f = PlantFit(theta=float(th), a=a, tau=1.0 / a if a > 0 else np.inf,
                 coeffs=beta[1:], resid_rms=rms, n=len(t), order=order,
                 window=(float(t[0]), float(t[-1])), estimator="integral+fan",
                 scan=np.array(scan), cov_a=float(var_a))
    f.kf = float(kf)
    return f


def replay(t, inlet_fn, bt0, a, theta, slow_fn, fan_fn=None, kf=0.0, dt=0.25,
           tau2=0.0):
    """Forward-simulate the plant.  ``inlet_fn``/``slow_fn`` take seconds.

    ``tau2 > 0`` puts the second lag in front of the gain, matching
    :func:`fit_integral_2lag`: ``Inlet -> delay -> 1/(1+tau2 s) -> a/(s+a)``.
    The lag starts settled at the initial inlet, as the fit does.
    """
    n = int(round((t[-1] - t[0]) / dt)) + 1
    ts = t[0] + dt * np.arange(n)
    bt = np.empty(n)
    bt[0] = bt0
    x = inlet_fn(ts[0] - theta)
    for k in range(n - 1):
        s = 1.0 if fan_fn is None else 1.0 + kf * (fan_fn(ts[k]) - 60.0)
        u = inlet_fn(ts[k] - theta)
        if tau2 > 0:
            d = a * s * (x - bt[k]) + slow_fn(ts[k])
            x += dt * (u - x) / tau2
        else:
            d = a * s * (u - bt[k]) + slow_fn(ts[k])
        bt[k + 1] = bt[k] + dt * d
    return ts, bt


def fit_integral_2lag(t, bt, t_in, inlet, order=4,
                      thetas=np.arange(0, 31, 1.0),
                      tau2s=np.arange(0, 121, 5.0)):
    """Two-lag variant: ``Inlet -> [1/(1+tau2 s)] -> X -> [a/(s+a)] -> BT``.

    A single first-order-plus-deadtime fit to the charge recovery matches the
    fast part of the response but can understate the phase lag at the loop's
    250 s crossover; a second lag is the cheapest structure that separates the
    two.  ``a`` and the disturbance polynomial are still linear for a fixed
    ``(theta, tau2)``.
    """
    dt = float(np.median(np.diff(t)))
    P = _cheb_basis(t, order + 1)
    best = None
    scan = []
    for th in thetas:
        u = _delayed(t, th, t_in, inlet)
        if np.isnan(u).any():
            raise ValueError("input series does not cover t - max(theta)")
        for tau2 in tau2s:
            d = lag1(u, tau2, dt) - bt
            U = np.concatenate([[0.0], np.cumsum(0.5 * (d[1:] + d[:-1])) * dt])
            X = np.column_stack([U, P])
            beta, r = _solve(X, bt)
            rms = float(np.sqrt(np.mean(r ** 2)))
            scan.append((th, tau2, rms))
            if best is None or rms < best[0]:
                best = (rms, th, tau2, beta)
    rms, th, tau2, beta = best
    a = float(beta[0])
    f = PlantFit(theta=float(th), a=a, tau=1.0 / a if a > 0 else np.inf,
                 coeffs=beta[1:], resid_rms=rms, n=len(t), order=order,
                 window=(float(t[0]), float(t[-1])), estimator="integral+2lag",
                 scan=np.array(scan))
    f.tau2 = float(tau2)
    return f


def fit_disturbance(t, bt, t_in, inlet, a, theta, knot_spacing=20.0, lam=0.0,
                    tau2=0.0):
    """With ``a`` and ``theta`` held fixed, recover ``slow(t)`` on a B-spline basis.

    Used only to give the simulator a full-roast disturbance to run against --
    including the charge recovery, which no low-order polynomial can represent.
    The plant parameters must come from :func:`fit_integral` on a window where
    the disturbance *is* low-order; fitting both here would be circular.

    ``tau2 > 0`` recovers ``slow`` under the two-lag structure instead, so a
    loss curve stays matched to the ``(a, theta, tau2)`` it was fitted with --
    the two are not interchangeable, since ``a`` differs between structures.
    """
    from scipy.interpolate import BSpline

    dt = float(np.median(np.diff(t)))
    d = lag1(_delayed(t, theta, t_in, inlet), tau2, dt) - bt
    U = np.concatenate([[0.0], np.cumsum(0.5 * (d[1:] + d[:-1])) * dt])

    interior = np.arange(t[0] + knot_spacing, t[-1], knot_spacing)
    knots = np.concatenate([[t[0]] * 4, interior, [t[-1]] * 4])
    nb = len(knots) - 4
    B = np.zeros((len(t), nb))
    for j in range(nb):
        c = np.zeros(nb)
        c[j] = 1.0
        B[:, j] = BSpline(knots, c, 3, extrapolate=True)(t)
    # integrate the basis so the model stays  BT = BT0 + a*U + int slow
    IB = np.zeros_like(B)
    IB[1:] = np.cumsum(0.5 * (B[1:] + B[:-1]) * dt, axis=0)
    X = np.column_stack([np.ones(len(t)), IB])
    y = bt - a * U
    if lam:
        D = np.diff(np.eye(X.shape[1]), 2, axis=0)
        beta = np.linalg.solve(X.T @ X + lam * D.T @ D, X.T @ y)
    else:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    slow = B @ beta[1:]
    resid = y - X @ beta
    return slow, float(np.sqrt(np.mean(resid ** 2)))


def block_bootstrap_2lag(t, bt, t_in, inlet, order, thetas, tau2s, n_boot=200,
                         block=60, seed=0):
    """:func:`block_bootstrap` for :func:`fit_integral_2lag`.

    Returns ``(base_fit, samples)`` with samples as ``(theta, tau2, a)`` rows.
    The same block-length caution applies: these residuals are smooth, so a
    block shorter than the residual correlation time reports a spread that is
    far too tight.  Because the grid is two-dimensional, keep it coarse here --
    the bootstrap answers "how far does the minimum move", not "where is it".
    """
    base = fit_integral_2lag(t, bt, t_in, inlet, order=order, thetas=thetas,
                             tau2s=tau2s)
    dt = float(np.median(np.diff(t)))
    d = lag1(_delayed(t, base.theta, t_in, inlet), base.tau2, dt) - bt
    U = np.concatenate([[0.0], np.cumsum(0.5 * (d[1:] + d[:-1])) * dt])
    P = _cheb_basis(t, order + 1)
    X = np.column_stack([U, P])
    yhat = X @ np.concatenate([[base.a], base.coeffs])
    resid = bt - yhat

    rng = np.random.default_rng(seed)
    nb = int(np.ceil(len(t) / block))
    out = []
    for _ in range(n_boot):
        starts = rng.integers(0, max(1, len(resid) - block), size=nb)
        rs = np.concatenate([resid[s:s + block] for s in starts])[: len(t)]
        f = fit_integral_2lag(t, yhat + rs, t_in, inlet, order=order,
                              thetas=thetas, tau2s=tau2s)
        out.append((f.theta, f.tau2, f.a))
    return base, np.array(out)


def neff(r):
    """Effective sample size of an AR(1)-correlated residual series.

    An F-test between the one-lag and two-lag structures on the raw sample count
    is meaningless here: consecutive BT residuals are correlated at rho > 0.9, so
    ``n`` overstates the information by an order of magnitude.  This is the
    standard ``n * (1-rho)/(1+rho)`` correction, and it is what makes the extra
    parameter's F statistic honest.
    """
    r = np.asarray(r, dtype=float)
    if len(r) < 10:
        return float(len(r))
    rho = float(np.corrcoef(r[:-1], r[1:])[0, 1])
    rho = min(max(rho, 0.0), 0.999)
    return float(len(r) * (1.0 - rho) / (1.0 + rho))
