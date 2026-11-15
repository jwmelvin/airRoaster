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

## 5. The roast spec: three points and the slope at first crack

**A roast is specified by where it has to be and how fast it is going when it
cracks:**

| | what is given | |
|---|---|---|
| DRY END | time, at BT 149.6 | fixed point |
| **FCs** | time, at the lot's `T_FC` | fixed point |
| **slope at FCs** | `S_FC`, degC/min | **the roast parameter** |
| DROP | `dt_dev` after FCs, `dT_dev` above it | fixed point |

**The shape between the points is the engine's business, not a roast
parameter.** The engine is `tools/make_background.py` and the models it reads
(the dip, the plant card, the drying term, the bean table). It takes this spec
plus the batch (mass, charge temperature, moisture, lot) and returns the
background: the dip as physics, then a RoR that is smooth and monotone through
the points. How well its curve turns into the roast that was asked for is what
[playbook-model-feedback.md](playbook-model-feedback.md) measures and corrects.

**The engine takes the whole spec** (since 2026-11-15):

```
make_background.py --dry-end 192:149.6 --fcs <t>:<T_FC> --ror-at-fcs <S_FC> \
    --drop-after <dt_dev>:<dT_dev>
```

The single RoR curve has four parameters and is used up by DRY END, FCs, the
slope and the ramp. So `--drop-after` cuts it at FCs and gives development a
segment of its own: RoR leaves at `S_FC` and decays exponentially at whatever
rate lands `dT_dev` in `dt_dev`, exactly, on the grid the file ships on. RoR is
continuous through crack; its own slope steps there, and the tool prints both
sides.

**The tool refuses a DROP that needs RoR to rise after crack**, i.e. any
`dT_dev` above `S_FC * dt_dev`. That bound is the "takes off at the end" guard
written as a spec.

**`--hold` (default 30 s with `--drop-after`)** carries the curve and the file's
DROP mark past the intended drop. Artisan stops updating SV at the background's
DROP mark less the lookahead, so a mark placed at the real drop freezes the
target if the crack is late (roast 63's last 13 s). **Drop by the clock or the
spec, never by the mark.**

`--development <s>` (slope pinned, DROP temperature follows) and `--drop <t>:<BT>`
(DROP pinned, slope follows) still author the uncut curve.

**What the logs already say about the slope (2026-11-15).** Measured as the BT
slope over FCs ± 15 s, against the background's over the same seconds, on the
ten roasts from 49 to 63 that have both:

```
achieved − specified = −0.70 degC/min, sd 0.68        (range −2.28 to 0.00)
```

**The bed goes through first crack slower than the curve says, by about 0.7.**
And every one of those specs sat between 8.1 and 9.5, so the parameter this
effort is built on has never been varied. Two specs closer than about 1.5
degC/min cannot be told apart in one roast.

## 6. Experiments

| # | question | design | status |
|---|---|---|---|
| **S1** | does roast level show up in weight loss and in the cup? | `C1055`, two 462 g batches at one total time: A light (roast 64), B with crack 44 s sooner and +10.6 after it | **run — § 7. Weight loss: yes. Cup: outstanding** |
| S2 | is `D(Q)` the right index: do a short-hot and a long-cool development with equal `D` roast the same? | ready to author | needs tooling |
| S3 | **the slope at FCs as the variable** | same three points, `S_FC` about 6 against about 10 | ready to author |
| S4 | Maillard length at fixed development | move `t_FC` with `t_DE` and the development segment held | ready to author |
| S5 | does lower airflow change the cup? | pairs differing only in fan, off the loft floor | not scheduled; the loop is fan-sensitive |

## 7. S1 — result: roast level resolves in weight loss, by three times the noise

Two 462 g batches of `C1055` at one total time (2026-11-15). Records: § Roast 64,
§ Roast 65.

| | **A — roast 64** | **B — roast 65** |
|---|---|---|
| background | `profile_462g_m5C_space_v9.alog` | `profile_463g_m18C_fast_v10.alog` |
| FCs | 201.8 @ 6:50 | 201.2 @ 6:06 |
| slope at FCs | 6.6 | 11.0 |
| DROP | 205.3 @ 7:27 | 211.8 @ 7:29 |
| development | 37 s, +3.5 | 83 s, +10.6 |
| `D(2)` / `D(3)` | 42 / 46 | 126 / 163 |
| **weight loss** | **12.34 %** | **14.20 %** |

**+1.86 % of weight loss for 3× the development index**, against 0.59 % of
scatter. B's 14.2 % is the median of this lot's Behmor history (14.3), the
roasts the operator called overroasted; A's 12.3 % is below anything it has had.
**The cup comparison is outstanding**, and it is between two roasts that differ
in crack time, slope through crack and finish, not along one variable. Two
points cannot say what `Q` is.

**`T_FC` for `C1055`: 201.8 and 201.2**, marked by ear on roasts whose crack was
hard to hear. The operator's standing estimate is about 200.

## Record

### Roast 64 (2026-11-15, 17:26) — S1 batch A: 462 g `C1055`, DROP 205.3 at 7:27

`scorecard.py 64`, against `profile_462g_m5C_space_v9.alog`:

```
charge       BT 130.3, inlet 140.2, fan 65@1 63@12 62@17 61@24, held 61
TP           47.5 @ 27 s          (curve 56.0 @ 29 s)
e 45/60/90/120       −8.72 / −7.29 / −0.40 / +1.31
entry slope 85-115   +5.17 degC/min     -> the 120-230 s window is unscored
e 180/240/300/360    −1.40 / −0.87 / −0.53 / +1.30       rms DRY END-FCs 1.09
DRY END      195 s (+2.5 s)
FCs          201.8 @ 410 s        slope 6.6 (curve 7.9)
development  37 s, +3.5, D2 42, D3 46, mean e +1.10
DROP         205.3 @ 447 s        weight loss 12.34 %
```

- **The dip was 8.5 degC deeper than the model's.** Roast 63 (500 g, another
  lot) missed by 1.7 the same way. Charge and preheat matched the spec (BT
  130.3, inlet 140.2), so it is the beans, the lot, or the 12.9 degC room. The
  log's `greens_temp` and `moisture_greens` both read 0.0, i.e. not entered.
  **Watching: dip, one roast.** B is authored at a nominal −18 to match.
- **`T_FC` for `C1055` on this probe: 201.8** (n = 1), the highest of any lot on
  the airRoaster.
- **The bed gained on the curve before crack while the loop was taking heat
  away.** `e` went −0.53 → +1.30 between 300 and 360 s as the inlet came down
  241 → 232, and the drive fell from 62 degC at 4:41 to 26 at FCs. Roasts 62 and
  63 are flat over the same stretch (+0.2, +0.1). That is consistent with the
  operator's "takes off at the end", and it is one roast. **Watching:
  development, one roast.**
- **Slope at FCs 1.3 under the curve**, in line with the −0.70 ± 0.68 on record.
- The tracking error from DRY END to FCs (rms 1.09) is about twice roasts 60-63.
- 37 s and +3.5 at 12.34 % sits inside the 400 g series' corner, as designed.


### Roast 65 (2026-11-15, 17:48) — S1 batch B: DROP 211.8 at 7:29, 14.20 %

`scorecard.py 65`, against `profile_463g_m18C_fast_v10.alog`:

```
charge       BT 134.3, inlet 140.8, fan 64@1 62@8, held 62
TP           45.6 @ 32 s          (curve 47.8 @ 29 s)
e 45/60/90/120       −6.68 / −7.84 / −1.95 / +0.04
entry slope 85-115   +5.32 degC/min     -> the 120-230 s window is unscored
e 180/240/300/360    −1.75 / −1.47 / −0.40 / +1.81       rms DRY END-FCs 1.25
DRY END      195 s (+3.5 s)
FCs          201.2 @ 366 s        slope 11.0 (curve 10.7)
development  83 s, +10.6, D2 126, D3 163, mean e +1.03
DROP         211.8 @ 449 s        weight loss 14.20 %
```

**Against the prediction written before it ran:**

| | predicted | got | |
|---|---|---|---|
| TP | 47-49 | 45.6 | 1.4 under the band, and on the cold side |
| FCs | 201.8 ± 1, 6:08-6:22 | 201.2 @ 6:06 | temperature held; 2 s early |
| `e` from 300 s to FCs | up 1-2 | **+2.2** (−0.40 → +1.81) | held, a little over |
| DROP at 7:27 | 211-212.5 | 211.8 @ 7:29 | held |
| weight loss | above 13.0 % | 14.20 % | held |

**Not as planned:** the fan went 64 → 62 at 8 s instead of repeating A's
65/63/62/61 schedule, charge BT was 134.3 against A's 130.3, and `greens_temp`
and `moisture_greens` again read 0.0.

- **The dip input was the right correction.** Authored at a nominal −18, the
  curve's TP was 2.2 above the bed's; at −5 it was 8.5 above (roast 64).
- **The first minute did not improve with it.** `e60` is −7.8 with the TP
  matched, against −7.3 with it missed by 8.5. So the lag at 45-90 s is not the
  dip handing the ramp a wrong start. **It is the ramp**: the curves peak at
  53-55 s and these beds peak later and higher while catching up.

  | roast | mass | bed's RoR peak | curve's | `e60` | entry slope |
  |---|---|---|---|---|---|
  | 62 | 400 g | 53.6 @ 61 s | 44.6 @ 54 s | −3.7 | +0.1 |
  | 63 | 500 g | 58.4 @ 71 s | 49.2 @ 55 s | −8.5 | +8.0 |
  | 64 | 462 g | 62.0 @ 65 s | 48.0 @ 55 s | −7.3 | +5.2 |
  | 65 | 462 g | 62.4 @ 73 s | 51.1 @ 55 s | −7.8 | +5.3 |

  Three roasts, one sign, far outside any scatter. The cheaper explanation
  still standing is the fan: all three heavy roasts stepped it down inside the
  first 30 s and roast 62 held 64. **Ramp: eligible for a revision** under
  playbook § 3, with mass and the fan step still confounded.
- **The late gain repeated.** `e` over 300 → 360 s: roast 64 **+1.8**, roast 65
  **+2.2**; roasts 62 and 63 +0.3 and +0.1. Both `C1055` roasts ran 1.3-1.8 degC
  ahead from 330 s to FCs with the inlet coming down. Two roasts, one lot, one
  sign: this is the lot, and it is what "takes off at the end" looks like here.
  The loop contains it to under 2 degC; it does not remove it.
- **Slope at FCs 11.0 against the curve's 10.7**: the first roast on record to go
  through crack *faster* than asked (the ten before it average −0.70). It is
  also the first whose spec was above 9.5.
