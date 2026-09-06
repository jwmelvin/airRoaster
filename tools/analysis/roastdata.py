"""Loaders for Artisan .alog profiles and the airRoaster dashboard CSV.

Conventions that have bitten this project before, encoded here once:

* The CHARGE origin is ``timex[timeindex[0]]``.  ``timeindex[0] == 0`` is a
  *valid* index meaning "CHARGE is the first sample", not "unset" -- so the
  index is never tested for truthiness.  ``profile_003`` relies on this.
* Special-event values decode as ``(v - 1) * 10``.
* The ``.alog`` stamps the PID settings at *save* time, not roast time, so
  ``pidKi`` and friends here are advisory only.
"""

from __future__ import annotations

import ast
import csv
import datetime as _dt
from dataclasses import dataclass, field

import numpy as np

TIMEINDEX_NAMES = ("CHARGE", "DRYe", "FCs", "FCe", "SCs", "SCe", "DROP", "COOL")


def _lin(t_src, y_src, t_dst):
    """Interpolate onto ``t_dst``; NaN outside the source support."""
    y = np.interp(t_dst, t_src, y_src, left=np.nan, right=np.nan)
    return y


@dataclass
class Profile:
    """One Artisan ``.alog``, re-based on CHARGE."""

    path: str
    raw: dict
    t: np.ndarray            # seconds since CHARGE
    bt: np.ndarray
    et: np.ndarray
    extras: dict = field(default_factory=dict)   # name -> (t, y), also CHARGE-based
    marks: dict = field(default_factory=dict)    # e.g. {"DRYe": 194.6}

    @property
    def charge_epoch(self) -> float:
        """Unix seconds at CHARGE."""
        return self.raw["roastepoch"] + self.raw["timex"][self.raw["timeindex"][0]]

    def bt_at(self, t):
        return _lin(self.t, self.bt, np.asarray(t, dtype=float))

    def extra_at(self, name, t):
        te, ye = self.extras[name]
        return _lin(te, ye, np.asarray(t, dtype=float))

    def time_to_bt(self, level, t_min=30.0):
        """First time after ``t_min`` at which BT crosses ``level`` upward."""
        m = self.t >= t_min
        t, bt = self.t[m], self.bt[m]
        idx = np.nonzero((bt[:-1] < level) & (bt[1:] >= level))[0]
        if len(idx) == 0:
            return np.nan
        i = idx[0]
        f = (level - bt[i]) / (bt[i + 1] - bt[i])
        return t[i] + f * (t[i + 1] - t[i])

    def sv_events(self):
        """Slider-3 (T_inlet) special events as (t_since_charge, degC).

        Values decode as ``(v - 1) * 10``.  Type 2 is the third event type,
        which is ``etypes[2] == 'T_inlet'`` in this configuration.
        """
        r = self.raw
        t0 = r["timex"][r["timeindex"][0]]
        out = []
        for idx, typ, val in zip(r["specialevents"], r["specialeventstype"],
                                 r["specialeventsvalue"]):
            if typ != 2:
                continue
            out.append((r["timex"][idx] - t0, (val - 1.0) * 10.0))
        return np.array(out) if out else np.zeros((0, 2))


def load_profile(path: str) -> Profile:
    with open(path) as fh:
        raw = ast.literal_eval(fh.read())

    timex = np.asarray(raw["timex"], dtype=float)
    ti = raw["timeindex"]
    t0 = timex[ti[0]]                       # index 0 is valid -- see module docstring
    t = timex - t0

    prof = Profile(
        path=path,
        raw=raw,
        t=t,
        bt=np.asarray(raw["temp2"], dtype=float),
        et=np.asarray(raw["temp1"], dtype=float),
    )

    for name, xs, ys in zip(raw.get("extraname1", []),
                            raw.get("extratimex", []),
                            raw.get("extratemp1", [])):
        prof.extras[name] = (np.asarray(xs, dtype=float) - t0,
                             np.asarray(ys, dtype=float))

    for k, name in enumerate(TIMEINDEX_NAMES):
        if k == 0 or ti[k] == 0:
            continue
        prof.marks[name] = float(timex[ti[k]] - t0)
    prof.marks["CHARGE"] = 0.0
    return prof


@dataclass
class DashLog:
    """One dashboard CSV.  ``t`` is seconds since CHARGE once aligned."""

    path: str
    epoch: np.ndarray        # unix seconds
    cols: dict               # name -> float array (NaN for blanks)
    mode: np.ndarray
    charge_epoch: float | None = None

    @property
    def t(self):
        if self.charge_epoch is None:
            raise RuntimeError("not aligned yet")
        return self.epoch - self.charge_epoch

    def at(self, name, t):
        return _lin(self.t, self.cols[name], np.asarray(t, dtype=float))


def load_dashlog(path: str) -> DashLog:
    epoch, mode = [], []
    cols: dict[str, list] = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            ts = row["time"].replace("Z", "+00:00")
            epoch.append(_dt.datetime.fromisoformat(ts).timestamp())
            mode.append(row["mode"])
            for k, v in row.items():
                if k in ("time", "mode"):
                    continue
                cols.setdefault(k, []).append(float(v) if v not in ("", None) else np.nan)
    return DashLog(path=path,
                   epoch=np.asarray(epoch),
                   cols={k: np.asarray(v) for k, v in cols.items()},
                   mode=np.asarray(mode))


def align_dashlog(dash: DashLog, prof: Profile, col="BT", ref="bt",
                  window=(-400.0, 400.0), step=0.05, t_range=(0.0, None)):
    """Find the CHARGE epoch that best lines the CSV up with the profile.

    Cross-correlates ``dash.cols[col]`` against the profile's ``ref`` series
    over a grid of candidate CHARGE epochs and returns
    ``(charge_epoch, residual_rms)``, having set ``dash.charge_epoch``.
    """
    if ref == "bt":
        pt, py = prof.t, prof.bt
    else:
        pt, py = prof.extras[ref]

    lo = t_range[0]
    hi = prof.marks.get("DROP", pt[-1]) if t_range[1] is None else t_range[1]
    m = (pt >= lo) & (pt <= hi)
    pt, py = pt[m], py[m]

    guess = prof.charge_epoch
    best = (np.inf, guess)
    for off in np.arange(window[0], window[1] + 1e-9, step):
        cand = guess + off
        y = _lin(dash.epoch - cand, dash.cols[col], pt)
        good = ~np.isnan(y)
        if good.sum() < 0.8 * len(pt):
            continue
        r = float(np.sqrt(np.mean((y[good] - py[good]) ** 2)))
        if r < best[0]:
            best = (r, cand)
    dash.charge_epoch = best[1]
    return best[1], best[0]
