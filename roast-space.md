# roast-space — choosing the curve, not just following it

> **This file: the effort to map what a roast *is*, in coordinates that matter
> to the cup.** Started 2026-11-15. The cascade work (state-history-*.md) made
> the machine follow a background to about 1 degC from 110 s to DROP. That
> answers "can it follow a curve". This asks "which curve".
>
> Results go in § Record at the bottom, newest last. What is planned and not yet
> run is § Experiments.

## 1. The coordinates

A roast is three phases, split at two events:

| phase | from → to | what sets the boundary |
|---|---|---|
| **dry** | CHARGE → DRY END | a convention: BT 149.6 on this probe |
| **Maillard** | DRY END → FCs | the **bean**: first crack happens at its own BT |
| **development** | FCs → DROP | the operator |

**First crack is the anchor.** Its temperature is a property of the lot,
measured and not chosen (`tools/analysis/beans.py`). Its *time* is chosen. DROP
is then written relative to it. A roast is the vector

```
( t_DE,  t_FC,  T_FC [measured],  dt_dev,  dT_dev )   + a shape per phase
```

with `dt_dev = t_DROP − t_FC` and `dT_dev = BT_DROP − T_FC`.

**The phases order the effects.** Reactions after first crack run fast and
faster with temperature, so ten seconds there are not ten seconds of Maillard,
and the quantity of interest is a nonlinear integral (§ 3). That is also why the
development phase gets its own two coordinates instead of being "the tail of
the curve".

## 2. What the machine leaves free

- **0 → TP is physics.** Mass, charge temperature and the machine decide the
  dip. Nothing there is a choice.
- **TP → about 110 s is only loosely ours.** The loop is still recovering from
  the charge; a heavy bed ran 8.5 degC behind at 60 s (roast 63). Shape claims
  about the dry phase have to be made on what the bed did, not on what was asked.
- **110 s → DROP is followed to about 1 degC**, with a known drying dip of about
  1.2 degC near 180-200 s. This is the region the roast space is actually
  explored in: late dry, all of Maillard, all of development.
- **The RoR ceiling** is 72 degC/min delivered (roast 54).

## 3. Development is nonlinear — a working index

A hypothesis, not a result:

```
D(Q) = integral from FCs to DROP of  Q ^ ((BT − T_FC) / 10)  dt        [seconds]
```

`Q` is a Q10: how much faster development runs per 10 degC. At `Q = 1` it is
plain development time. Roast chemistry suggests somewhere in 2-3. **Nothing
here has measured it.** Its job is to turn `(dt_dev, dT_dev)` into one number
that predicts roast degree, so that a short hot development and a long cool one
can be called equal or not.

**The measured side of roast degree is weight loss**, and colour if a meter
turns up. Weight loss is machine-independent, which is what lets the Behmor
history speak to this roaster at all.

## 4. What the logs already say (2026-11-15)

**Eighteen airRoaster roasts carry both an FCs mark and a weight out, and
seventeen of them sit in one corner.**

| | `dt_dev` | `dT_dev` | weight loss |
|---|---|---|---|
| roasts 41-62 (17 roasts, 4 lots) | 19.5-36 s | +2.3 to +4.3 | 10.6-12.8 % |
| roast 63 (`C1066`, 500 g) | 57.5 s | +6.4 | 12.4 % |

Across them weight loss does **not** track development: `r = +0.28` on
`dt_dev`, +0.27 on `dT_dev`, +0.29 on `D(2)`, residual rms **0.59 %**. That is
not evidence against the index. The span of development is too narrow to see
anything through the noise, and the noise is itself the finding: **`C1043`
alone reads 10.6-12.5 % at essentially one development** (roasts 43-62). Lot
moisture, chaff and the scale are all in that number.

**So a roast-level pair has to be far enough apart to clear 0.6 %.** That sets
the spread of the first experiment.

**`C1055` on the Behmor**, eleven roasts 2025-03 to 2026-05: weight loss
**13.1-15.3 %, median 14.3**, with `dt_dev` 50-122 s. The operator's judgement
of those is "easy to overroast, it takes off at the end". The one earlier
airRoaster roast of it (roast 8, 575 g, pre-cascade) lost 13.6 %. So this lot's
unexplored region is **below 13 %**.

## 5. The curve family

**What exists.** `make_background.py` draws TP → DROP as one RoR function, a
rise times an exponential fall, less the drying term. It has four parameters
and four constraints (DRY END, FCs, RoR at FCs, RoR peak time). Development is
just that same curve continued, so `dT_dev` is not free: it is whatever
`dt_dev` gives at the RoR the approach leaves.

**What this effort needs.** A per-phase description that keeps RoR continuous
at the two boundaries. With each phase an exponential in RoR:

```
RoR(s) = R_in * exp(−k * s),   s = 0..1 through the phase
dT     = R_in * dt * (1 − exp(−k)) / k
```

one number `k = ln(R_in / R_out)` shapes each phase, `k = 0` is a straight
line, and continuity hands each phase's `R_out` to the next as `R_in`. For
development that means `(dt_dev, dT_dev)` become independent choices, inside the
bound `dT_dev <= R_FC * dt_dev` if RoR is never allowed to rise after crack.
**That bound is the "takes off at the end" guard written as a spec.**

**This is the operator's "gamma curve", with the ends repaired** (settled
2026-11-15). The idea is display gamma: between two fixed points, one number
says how far the curve departs above or below the straight line. Written
literally, `y = x^g`, it has a defect here: the slope at one end is zero or
infinite, so RoR would stall or spike at every phase boundary. The exponential
form does the same job with finite slopes at both ends:

```
y(s) = (1 − exp(−k*s)) / (1 − exp(−k))        y = fraction of the phase's dT
bow  = y(0.5) − 0.5 = tanh(k/4) / 2
```

**`bow` is the number to think in**: how far above the straight line the curve
sits at mid-phase, as a fraction of the phase's temperature span. `bow = 0` is
linear (constant RoR), positive is front-loaded (declining RoR), negative is
back-loaded. `bow = +0.10` is `k = 0.81`, an entry RoR 2.25× the exit. For scale,
v9's Maillard phase (149.6 → 198.8 over 207 s, RoR 23 → 8.3) is about
`bow = +0.13`.

## 6. Experiments

| # | question | design | status |
|---|---|---|---|
| **S1** | does roast level show up, in weight loss and in the cup, when only `dt_dev` changes? | `C1055`, two 462 g batches on one background, DROP at FCs + 35 s and FCs + 80 s | **next — § 7** |
| S2 | is `D(Q)` the right index: do a short-hot and a long-cool development with equal `D` roast the same? | needs the per-phase development segment (§ 5) | needs tooling |
| S3 | Maillard length at fixed development | move `t_FC` with `t_DE` and the development segment held | needs tooling |
| S4 | does lower airflow change the cup? | pairs differing only in fan, off the loft floor | not scheduled; the loop is fan-sensitive |

## 7. S1 — the two `C1055` batches

**One file, two drop rules.** Both batches run
`artisan/profile_462g_m5C_space_v9.alog`, so everything up to first crack is a
replicate and the only designed difference is when the beans leave.

```
make_background.py --mass 462 --greens-temp -5 --fcs 399:198.8 --ror-at-fcs 8.3 \
    --development 120 --moisture-greens 11.0
```

TP 56.0 @ 29 s, peak 48.3 degC/min @ 53 s, DRY END 149.6 @ 3:12, the FCs
*label* at 198.8 @ 6:39, RoR 8.3 there. All four constraints at 0.00, RoR
monotone. **The curve runs to 8:39 on purpose**: the background's DROP mark is
not the drop, it is room for a late crack.

| | **A — light, first** | **B — darker, second** |
|---|---|---|
| mass | 462 g | 463 g (what is left) |
| DROP | **FCs + 35 s** | **FCs + 80 s** |
| expected `dT_dev` | +4.5 (4.2-4.8) | +9.4 (8.8-10.0) |
| expected DROP BT, if FCs is 198.8 | 203.3 | 208.2 |
| `D(2)` / `D(3)` | 41 / 46 s | 115 / 144 s |
| RoR at DROP | 7.2 | 6.0 |

(The ranges are for a crack anywhere from 6:25 to 6:55.)

**Why these.** A is the corner the 400 g series lives in, so it ties this lot
to seventeen existing roasts. B is 2.8× the index and still shorter and cooler
than most of the Behmor history that read as overroasted. The gap should be
worth well over the 0.6 % weight-loss noise.

**Why equal masses, and not a 400/525 mass pair.** The mass term is an open item
(state-current.md § The mass term) and this was a chance at it. But a mass pair
would put a different first two minutes under each roast level, and the cup
comparison is the point. 462 g also gives a third mass on the same ramp spec
between 400 and 500.

**Held the same for both, deliberately not experiments today:**

- **Charge: frozen, enter `greens_temp −5.0`.** The dip model is anchored there.
- **No pre-hydration.** It changes the drying load, which the background carries
  a term for.
- **Preheat as roast 62**: inlet SV 142.0, trim BT to 130 with the fan.
- **Fan: A finds it, B copies it.** On A, charge at 64 and come down to the
  lowest level that keeps the bed circulating, finished by 30 s, then **do not
  touch it again**. B repeats A's fan events at A's times.
- **Config** `airRoaster_cascadePID_phaseB.aset`, alarm rows 7 and 8 off.
- `moisture_greens` is authored at 11.0 because no log of this lot records it.
  If a meter reading exists, enter it; the drying term will be off by the ratio.

**To record, both batches:** FCs marked at the first sustained cracks, **weight
out**, and anything about the spout or chaff. Cup them side by side, blind, at
the same rest.

**What each batch is read for:**

1. `T_FC` for `C1055` on this probe (unknown: the Behmor and roast 8 are other
   scales). A and B give two readings.
2. `e` at 45/60/90 s against roast 63's −6.8/−8.5/−2.8 at 500 g.
3. A against B from 110 s to FCs: the repeatability of the reference itself.
4. **Whether the loop holds the curve through development.** `e` and
   `Temp_Drive` (inlet − BT) from FCs to DROP. If this bean "takes off", the
   inlet has to back away to hold 8 → 6 degC/min, and the size of that retreat
   is the exotherm on this machine. Roast 63's drive *rose* 31.5 → 34.5 over the
   same stretch.
5. Weight loss A against B, against the 0.59 % noise.

## Record

*(nothing yet)*
