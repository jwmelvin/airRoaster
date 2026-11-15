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
| **S1** | does roast level show up in weight loss and in the cup? | `C1055`, two 462 g batches at one total time: A light (roast 64), B with crack 30 s sooner and +9.6 after it | **A done, B next — § 7** |
| S2 | is `D(Q)` the right index: do a short-hot and a long-cool development with equal `D` roast the same? | ready to author | needs tooling |
| S3 | **the slope at FCs as the variable** | same three points, `S_FC` about 6 against about 10 | ready to author |
| S4 | Maillard length at fixed development | move `t_FC` with `t_DE` and the development segment held | ready to author |
| S5 | does lower airflow change the cup? | pairs differing only in fan, off the loft floor | not scheduled; the loop is fan-sensitive |

## 7. S1 — the two `C1055` batches

**A is done (roast 64, § Record). B was redrawn at the operator's call**
(2026-11-15): a higher finish at **the same total time as A**, so first crack
comes sooner and the bed goes through it faster. B is no longer "A with a later
drop". It differs from A in crack time, slope at crack and finish, and the cup
comparison is between two roasts, not along one variable.

| | **A — roast 64, as run** | **B — to run** |
|---|---|---|
| background | `profile_462g_m5C_space_v9.alog` | **`profile_463g_m18C_fast_v10.alog`** |
| DRY END | 3:15 | 3:12 |
| FCs | 201.8 @ 6:50 | **201.8 @ 6:20** on the curve |
| slope at FCs | 6.6 (curve 7.9) | **curve 10.0** |
| DROP | 205.3 @ **7:27** | **at 7:27 by the clock**, curve 211.4 |
| `dT_dev` | +3.5 in 37 s | +9.6 in 67 s |
| `D(2)` / `D(3)` | 42 / 46 | 97 / 122 |
| weight loss | 12.34 % | |

```
make_background.py --mass 463 --greens-temp -18 --fcs 380:201.8 --ror-at-fcs 10.0 \
    --development 100 --moisture-greens 11.0
```

All four constraints at 0.00, RoR monotone, peak 51.5 degC/min at 53 s. The
curve runs on to 8:00 so SV does not fall away before the drop.

**Three things in that command are not what was first planned:**

- **`--greens-temp −18`.** A turned at 47.5 against a predicted 56.0. −18 is the
  input that makes the dip model turn at 47.8 for this mass, so B's reference
  starts where A's bed actually was. It is a fitted nominal, not a reading.
- **FCs at 6:20, not sooner.** With DRY END held at 3:12 this curve family
  cannot put 201.8 earlier than about 6:17: asked for 6:07 it misses all three
  marks by about 1 degC. 6:20 is the earliest it hits exactly.
- **Slope 10.0.** That is what the crack point needs at 6:20, and it is the
  first spec outside 8.1-9.5. The achieved slope has run 0.7-1.3 under the
  curve, so expect about 9.

**Prediction for B, written before it is run:**

| | expect | would mean something is wrong |
|---|---|---|
| TP | 47-49 | above 52: this charge was warmer than A's, and the first two minutes will lead |
| FCs | 201.8 ± 1 between 6:08 and 6:22 | outside ± 1.5: `T_FC` for this lot is not 201.8 |
| `e` from 300 s to FCs | drifts up by 1-2 degC, as on A | flat: A's late gain was not the bean |
| DROP at 7:27 | 211-212.5 | under 210: the loop did not deliver the faster Maillard |
| weight loss | above 13.0 % | within 0.6 % of A: weight loss does not resolve roast level here |

**Same as A:** config, preheat (inlet SV 142, BT 130), frozen charge handled the
way A's was, and **A's fan schedule**: 65 at charge, 63 at 0:12, 62 at 0:17, 61
at 0:24, then untouched. Enter `greens_temp` and the moisture reading if there
is one. Record weight out.

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

