# state-plan — planned work and specifications in force

> **What belongs here: work not yet done, and the specifications currently in
> force.** Every configuration key, file, alarm and firmware command below is
> either something to build or something to load. If a section reads as a record
> of what happened rather than a statement of what to do, it is in the wrong file
> — move it to the history for that effort rather than marking it superseded.
>
> - [state-current.md](state-current.md) — the active effort and where it stands.
> - [state-history.md](state-history.md) — index of the three investigation
>   records: [cascade](state-history-cascade.md) (roasts 40-49),
>   [charge](state-history-charge.md) (50-56),
>   [residual](state-history-residual.md) (57-59). The evidence for *why* each
>   value below is what it is lives there, referenced as
>   `state-history-<effort>.md § …`.
> - [state-archive.md](state-archive.md) — completed firmware work and the
>   F-numbered review findings, referenced as F-numbers.

## Bean reference — the first-crack temperature each lot cracks at

**A specification in force**, because it is the `--fcs <s>:<BT>` argument
`tools/make_background.py` is handed and nothing else supplies it — but it is
**derived, not recorded**. Every `.alog` carries `plus_coffee` (the artisan.plus
hr_id), `plus_coffee_label` and the crack mark, so the table is read out of the
logs:

```
.venv/bin/python tools/analysis/beans.py               # every coffee
.venv/bin/python tools/analysis/beans.py --coffee C1043
```

It prints the `--fcs` and `--ror-at-fcs` arguments to hand `make_background.py`.
**Do not maintain a copy by hand** — the snapshot below is illustrative and the
tool is authoritative.

**Artisan cannot store this.** The `Coffee` record artisan.plus syncs down
(`~/src/artisan/src/plus/stock.py:82-94` at v4.2.0) carries `label`, `origin`,
`varietals`, `grade`, `stock`, `default_unit`, `moisture`, `density`,
`screen_size`, `processing` and `crop_date` — and no temperature field of any
kind. There is nowhere to put it and nothing that would apply it forward.

Snapshot at roast 57, cascade-era only (roast ≥ 40, ≥ 380 g, `roastertype`
`airRoaster`):

| `plus_coffee` | coffee | roasts | FCs BT median | spread |
|---|---|---|---|---|
| `C1043` | Ethiopia, Crown Jewel Sidama Daye Bensa Washed | 43, 44, 46, 49, 56, **57** | **197.6** | 195.3-197.9 |
| `C1062` | Kenya, CJ Ichamama Factory Othaya Town | 53, 54, 55 | **197.4** | 197.3-198.7 |
| `C1074` | Colombia, Crown Jewel Carbonic Honey Peach Co-Ferment | 50, 51, 52 | **200.1** | 198.1-201.2 |

**Never pool across coffees.** This is the error the roast-56 background was
built on: a "mean over roasts 50-55" of 198.8 degC is a mean over `C1074` and
`C1062` and describes neither. Within a lot the spread is 1.6-3.1 degC and most
of that is mark subjectivity; between lots it is real. state-history-residual.md § The FC
temperature is a property of the lot has the full correction, including that
`profile_003`'s original **197.5** was right for both coffees it was ever run
against.

**One roast does not characterise a lot, but four in a 0.5 degC band do — and
roast 57 closed this one.** `C1043` reads 197.4 / 197.7 / 197.8 / 197.9 across
roasts 43, 44, 46 and 49, **195.3** on roast 56, and **197.40 on roast 57**. Five
readings inside 0.5 degC and one 1.2 degC below the rest: **195.3 is a mark made
early by ear, not a new bag**, and the lot's number is **197.6**. The tool now
prints `--fcs <s>:197.6 --ror-at-fcs 9.4`, and
`artisan/profile_400g_m5C_fc195_v5.alog` — which was parked on that single
reading — **is retired.**

The general caution stands for the next lot: artisan.plus identifies the
*coffee*, not the crop or the bag, so a new bag under the same hr_id is
invisible; that is the one thing the tool cannot tell you. **The way to tell them
apart is a second roast**, which is what roast 57 was.

**Regenerating for a new FC temperature used to be a change to the first
minute; since 2026-09-08 it is barely one.** The old behaviour was a defect, not
a property of a global fit — the exponential spec has **four** free parameters
(`tau_r, R0, R_inf, tau_d`) and DRY END / FCs / RoR@FCs supply **three**, so the
ramp was undetermined and the optimizer chose it off floating-point noise. At
400 g / −5 degC, BT at 60 s:

| `--fcs` | 198.8 | 197.7 | 197.4 | 195.5 | spread |
|---|---|---|---|---|---|
| **before** — ramp free | 80.6 | 74.8 | 78.1 | 73.4 | 7.2 degC, non-monotone |
| **now** — `--ror-peak-at 53` | 78.4 | 78.7 | 78.8 | 79.3 | 0.8 degC, monotone |

### The RoR-peak pin is a specification in force

`make_background.py --ror-peak-at <s since CHARGE>`, **default 53**, is the
fourth constraint that makes the fit square. Rules:

- **Leave it at 53 unless you are deliberately testing it.** 53 s is where
  `profile_400g_m5C_v4.alog` (roast 56's background, the only curve to pass all
  four checks) happens to peak, so the fix reshapes nothing silently. It is a
  lottery draw promoted to a spec, **not a measurement of the machine.**
- **It is a design number now, so it can be swept** — one roast at a time, like
  any other. Earlier peak = more rate demanded while the loop is still
  recovering from the charge and `Ki` is gated; later = the reverse. Reachable
  band at 400 g / −5 degC is about **45-80 s**; outside it the tool says the
  constraint is not satisfied and the ramp is unpinned again.
- **The peak's *time* is pinned, not its height.** Height varies only 48.2 to
  43.5 degC/min along the whole old null manifold, so it identifies the missing
  parameter ~8× worse (−0.10 degC/min/s against +0.85 s/s).
- **`--decline linear` takes no pin** — three parameters, always square.
  `--free-ramp` reproduces the pre-fix behaviour for comparing against an old
  file, and warns that it is doing so.
- **Verified** to 1e-14 with RoR monotone across −24…+25 degC and 250…500 g, in
  both `--development` and `--drop` mode.

**Still never run a regenerated background and a control change in the same
roast**, and print the 30-120 s column before loading one — the 0.8 degC has
been demonstrated in the fit, not yet on the machine.

**Cheapest reading of all this**: the FCs mark is a *label*. Nothing in the
cascade reads it — `calcSV` reads only `BT(t + svLookahead)` and `drop_t`
(`pid_control.py:1658-1717`) — so a curve marked 198.8 at 399 s that passes
195.4 at 375.8 s still puts a 195.4-cracking bean at a repeatable 375 s.
Regenerate when you want the crack at a different **time**, not merely to make
the label true.

## TEST PLAN — what causes the −2.9 degC residual at 170 s (2026-09-08, phases A and B done)

> **Where this stands. Both phases are run and the answer is both causes.**
> Phase A sized the fan at `f = 0.181`; Phase B (roast 60, fan 64 held) left
> **−1.69 degC at 168 s** standing, so the top row is out — the fan does not
> account for the residual. **How much of it the fan *is* was not measured**:
> roast 60's off-spec precharge inlet put it into the window falling at
> −5.0 degC/min, and the answer ranges from −0.3 to +1.2 degC with the reference
> point (state-history-residual.md § Correction). **The next roast repeats
> roast 60 with the preheat at the charge fan and settled**; until it enters the
> window flat, neither branch below can be sized.

**The question.** Roasts 56 and 57 both fall **−2.91 at 165 s** and **−2.96 at
170 s** below their own backgrounds, from a standing start of −0.08 and +1.55 at
120 s, recovering half of it by 212 / 215 s. Two roasts, different preheat,
different background, errors of opposite sign going in, **the same number at the
same second coming out**. It is a disturbance the loop is rejecting, not a lag it
is accumulating (state-history-residual.md § Roast 57).

Two candidates:

1. **the fan step at 120 s** — `Air 64 → 60`, the only scheduled event in the
   window;
2. **evaporative load through DRY END** (196.5 / 197.0 s in the two roasts) — the
   background's RoR spec carries no latent-heat term, so a real roast must fall
   behind where drying loads the bed hardest and recover once free moisture is
   gone.

**The plan was bench first, then one roast**, in the same shape as roast 57's
phase 0: the bench work costs no beans and can size — or kill — the fan
hypothesis before a load is spent, and it produces three other numbers that are
wanted anyway. It did all four, and the operator's loaded ladder added a fifth.

### Phase A — DONE 2026-09-10, roasts 58 and 59. `f = 0.18`

**The record is state-history-residual.md § Phase A and the headline numbers are
state-current.md § 2-4**; the tool is `tools/analysis/fan_ladder.py`.

```
HT = A*(fan - f0)*(Inlet - amb) + c

empty  fan 53-64   f0 = 39.2   rms 0.182 %      loaded  fan 56-64   f0 = 42.9   rms 0.202 %
f(64 -> 60) = 0.162 empty, 0.189 loaded, 0.181 joint        threshold was 0.12
ceiling deficit = RoR*f*T_eff/60 = 3.5 - 4.1 degC           observed 2.93
```

**The fan over-covers the residual by about a third**, which is the room the
ceiling arithmetic asked for. Four results carry into Phase B and beyond:

- **the direct step response** — roast 59, BT held at 145 with the bed in,
  `64 → 56` moved BT **−0.67 degC, bottoming at 54 s, recovered by ~130 s**,
  where the roast residual bottoms 45-50 s after the 120 s step and recovers by
  230 s. Same loop, same shape. **Timing transfers, magnitude does not**:
  `Inlet − BT` is ~2 degC at the settled bench against 49-60 in the roast;
- **the blower saturates above fan 64** — fan 72 delivers the flow of a nominal
  70.4 and fan 80 of a nominal 75.0. `mdot ∝ (fan − 40)` holds over the range the
  roast uses and bends above it, so the 60-80 span this plan chose for contrast
  is *not* what sized `f`; the descending rungs the operator added did;
- **345 g of beans is a 9.3 % flow restriction**;
- **the duty line is linear to BT 190** (A2 answered, no superlinearity, no
  ceiling) — but the three candidate baselines span **4.5 %** of duty against a
  disagreement worth 2.1 %, so **no re-basing settles the excess-duty model's
  intercept**. Do not quietly pick the baseline that flatters the fit.

**One process note for every future bench session: soak the machine for 20
minutes before the first rung, or run the session second.** Roast 58's rung 1
failed this plan's ±0.5 % repeatability criterion by reading 1.22 % high, and the
cause is the cold start — its duty was still falling at 0.4 %/min at seven
minutes and did not settle until 23. Roast 59, an hour later on the soaked
machine, settled in three.
### Phase B — DONE 2026-09-13, roast 60. The answer is **both**

**The record is state-history-residual.md § Phase B**; the config is
`artisan/airRoaster_cascadePID_phaseB.aset` (`tools/gen_phaseb_aset.py`).

One roast, one change: fan **64 held from before CHARGE to DROP**, row 7 off,
everything else roast 56's. B6 passes on all four counts and B3 passes on all
four — no `Air` event at 120 s, no SV step at 105 s, `LA 6` present at 46.0 s,
the gate empty from +1 s to `PID ON`.

```
                     e(120)    minimum        rms 120-230   swing from 120 s
roast 56              -0.08    -2.91 @ 165 s     1.97            -2.83
roast 60 (fan 64)     +0.42    -1.69 @ 168 s     1.15            -2.11
```

**The dip is shallower and it is still there, at the same second, with the same
shape** — B4's "both" row, whose predicted band was −1.2 to −2.0. Removing the
step removed **0.72-1.22 degC**: the lower figure charges the +0.5 degC that
roast 60 carried into 120 s against the fan, the upper does not. Take the pair as
the bracket.

**The fan is real and worth a third of its own ceiling.** `f = 0.181` predicted a
3.93 degC ceiling deficit and put the fan's share of the 2.93 at 2.68; the
measurement is 18-31 % of that. **The ceiling was honest about being a ceiling
and is not an estimate of the size.** What is left — 1.69 degC bottoming 26 s
before DRY END and two-thirds gone 36 s after it — is the drying term's to
explain.

Four results carry forward:

- **the duty model composes across roasts.** Phase A's
  `HT = A(fan−f0)(Inlet−amb)+c`, fitted on the bench, predicts roast 60's live
  duty from roast 56's to **−0.07 / +0.64 / +1.12 %** over the three windows,
  through a fan change, 5.7 degC of ambient and 5 degC of inlet. The +4.6 % duty
  step **is** the fan, measured;
- **and it must not be used as an in-roast baseline.** As a standing-duty line
  inside a roast it gives a negative RoR-vs-excess slope on all three roasts,
  because it is fitted in `Inlet` over the bench range. The excess-duty model
  **does not transfer across fan on either baseline** — the fan-60 empty
  `HT(BT)` line leaves roast 60 at `−33.3 + 4.23·excess`, and re-basing it by the
  modelled +5.2 % fixes the level and not the slope;
- **the auto-DROP alarm works and the roast 56 heat-off anomaly is closed.**
  Row 9 fired on the spike sample (`HT` 70 → 17, `Inlet` 228 → 249); the mark
  landed at −0.1 s rather than 56's −0.5, and **`SV` and `HT` both reached 0
  within 1.0 s** against roast 56's 17.5 s. Row 2 never acted — Artisan v4.2.0
  guards `action == 13` on `timeindex[6] == 0` *before* `markDrop()`, so the
  second DROP alarm is a no-op, not an undo;
- **120 s → DROP tracking is the best on record at 0.73 rms** (56: 1.28,
  57: 1.76), which is what removing a scheduled disturbance from the window
  should do.

**One unplanned variable, and it is the most interesting thing in the roast.**
The precharge inlet came out at **132.8 against the specified 141.8** while the
preheat BT was exactly on spec — the machine had soaked 23.8 min rather than 9.7,
and a warm-walled chamber holds BT 130 on 9 degC less inlet. It cost an
**8.3 degC deeper turning point**, absorbed by 50 s and worth only +0.5 degC at
120 s. It also separates two levers roast 57 confounded: **preheat BT is inert
(gain 0.100) and the precharge inlet moves the turning point nearly one for one
(gain 0.94)**. One roast each, so it is a hypothesis with a number on it.

### What follows — both branches, and drying is the bigger one

**Phase B ruled out the top row and did not settle the partition** — the fan is
somewhere in −0.3 to +1.2 degC of the 2.9 and drying keeps most of what is left,
but roast 60's entry transient is the same size as the effect
(state-history-residual.md § Correction). **Neither branch can be sized until a
roast enters the window flat**, which is what preheating at the charge fan buys. The fan compensation below is still sized off the 3.93 degC ceiling and
**that number is now known to be far too large — do not build it.**

**The fan branch.** The compensation was sized: holding `mdot·(Inlet − BT)`
across the step needs `ΔSV = TD·f/(1−f)`, and at the **measured `f = 0.181`**
that is **+10.8 degC at `TD = 49` and +13.3 at the `TD = 60` roast 56 actually
ran at 120 s**. That is a large step to put into an SV that the four checks
watch, so ramp it rather than stepping it — which is what (a) below does anyway.
Then the next roast restores
`Fan 60` at 02:00 *with* the compensation and is scored on whether the dip is
gone. Two ways to deliver it, and they are not equivalent:

- **(a) the cheap test — ramp the fan instead of stepping it.** 64 → 60 over
  60 s as four alarm rows at 15 s spacing, so the disturbance is inside the
  loop's own bandwidth and no feedforward is needed at all. Config only.
  **Cost: three more alarm rows in a table that is already known to drift
  silently** (state-current.md § The alarm table…), so the pre-flight check gets
  longer every roast.
- **(b) the right answer — fold it into step 9's base schedule**, where a
  fan-dependent term belongs. `INLET TRIM` cannot carry it as a one-shot: the
  firmware ramps the trim out after 15 s without a refresh
  (`INLET_TRIM_STALE_MS`, airRoaster.ino:202), so it needs a repeating source,
  which is the base schedule.

Do (a) first; it is one roast and it either removes the dip or falsifies the
whole line of reasoning.

**The drying branch, and it now carries 1.69 of the 2.9.**
`make_background.py`'s exponential RoR spec needs a latent-heat term, and the
larger part of the residual becomes a **background-authoring** fix rather than a
control one. **Author it against the load, not against the residual**: the
−1.69 degC is the closed-loop response to the drying load through a loop with a
213 s crossover period, so the load itself is narrower in time and larger in
amplitude than the error trace (state-history-residual.md § Is the dip the loop
ringing?). That would also explain the property that started this: it never
varied with the loop's state, because the loop was tracking a curve that was
asking for something the bed could not deliver while it was still wet. The
`moisture_greens` field is already entered on every roast since 56, so there is
an input for it.

**Either way, `LA 12` stays dead.** Neither cause is a type-1 ramp error, and a
lookahead patch fired at 105 s would have hidden whichever it is behind an SV
step fifteen seconds before the event.

## NEXT — remaining on-roaster validation

**Only what is still unchecked.** The live sessions of 2026-07-02/03/04
validated the rest of the original checklist — boot sync, power linearization,
the DimmerLink reset rework and the commissioning sequence are all done and are
recorded in the archive's v0.12–v0.15 entries. Roughly in commissioning order:

1. **Sensor path**: BT read sane in live sessions, but the specific checks are
   unrecorded — `STAT` after a few minutes (`loopMaxUs` should be dominated by
   the ~30 ms display push, not sensor reads); compare RTD fault frequency in
   the log against pre-v0.8.0 roasts (emi.md addendum says what to expect).
2. **Failsafe drills** (roaster cold, heat low): engage `INLET`, unplug the
   inlet TC → expect `inlet failsafe: inlet PV stale` within ~3 s, heat 0,
   mode manual. Confirm a TUNE aborts the same way.
3. **Telemetry + dashboard** — **mostly done**: the commissioning sequence
   (TUNE → APPLY → FF cal → INLET) ran end-to-end in the 2026-07-03 session.
   Still unchecked: kill/restore WiFi to see auto-reconnect on both sides.
4. **WDT confidence**: none of the normal paths (tune, big display repaints,
   WS bursts) should approach 8 s — `loopMaxUs` gives the margin number.
5. **Interlock config (v0.10.0)**: from the dashboard panel set soft mode and
   custom limits, confirm the heat cap follows the fan slider accordingly, then
   power-cycle and confirm the values and mode survive (NVS). Try an invalid
   set (`IL 0 55 30`) and confirm it is rejected.
6. **OTA idle gate (v0.12.0)**: an OTA push with heat > 0 should time out on
   the host, then succeed again at heat 0. The happy path (idle OTA push,
   reboot, fan preserved) is validated.
7. **Curve experiments** (`CURVE FAN 0|2`, optional): compare fan response per
    level step on the dashboard chart; expectation is RMS (1) remains best.
    Reboot restores RMS automatically.
8. **Cooldown guard (v0.16.0)** — *mostly validated 2026-07-05*: deferral,
    hold, auto-release, and soak-back re-enforcement all observed working on
    the roaster. The 30 s dwell released early into soak-back (two re-enforce
    cycles), so the dwell is now adjustable (`COOL DWELL <s>`, NVS): find the
    dwell that makes one release stick (start ~90–120 s) and set it. Still
    unchecked: `COOL MIN`/`COOL DWELL` surviving a power cycle (NVS), and
    `COOL OFF` releasing a held fan immediately.
9. **Ambient reporting (v0.17.0)** — on a cold roaster, power up and check the
    serial log for `ambient: cold-start capture` with a sane room temp (BT vs
    CJ within 8 °C); dashboard Ambient panel should show it. Then run the
    roaster hot, power-cycle, and confirm the log says `warm boot … keeping`
    and the stored capture is unchanged. Check `AMB SRC`/`AMB <degC>` survive
    a power cycle (NVS). In Artisan: map the `AT` node to an extra WebSocket
    channel, select it on Config › Device › Ambient, and confirm Roast
    Properties picks up the ambient temperature at CHARGE (README § Ambient
    temperature has the click-path).
10. **Command auth (v0.18.0)** — with `AUTH_KEY` in secrets.h: dashboard
    authenticates automatically (key field) and `AUTH` reports authed; set
    `AUTH MODE CONFIG` and confirm an *unkeyed* browser gets "AUTH required"
    for `PID`/`IL`/`COOL MIN` but can still run `OT1 60`, `OT1 0`, `INLET
    OFF`, `COOL ON`; set `AUTH MODE FULL` and confirm `OT1 60` is refused
    unkeyed while `OT1 0` still works; run `tools/roaster_proxy.py` with the
    key and confirm live Artisan drives sliders through it in FULL mode;
    wrong-key proxy → refused; mode survives a power cycle (NVS); serial
    stays fully trusted. Also confirm a keyless build (empty AUTH_KEY)
    behaves exactly as v0.17.
11. **`INLET TRIM` (v0.19.0, second item)** — bench drill, heater cold, fan at
    a level that clears the interlock; watch the dashboard Setpoint panel and
    the serial log. (a) `INLET 200`, then `INLET TRIM 20` → readout `base 200.0
    + trim +20.0 = SV 220.0`, OLED `Inlet SV:220`, and the PID `I` term must
    carry on from where it was rather than jump — a trim is a retarget on an
    already-engaged loop, and a retarget must never re-seed the integrator.
    (b) `INLET TRIM -20` → effective 180. (c) bare `INLET TRIM` →
    reports all three. (d) stop sending for 15 s → `inlet trim stale: ramping to
    0` appears **once**, the effective SV walks back to the base at 2 °C/s
    (10 s from ±20), and one status push lands when it arrives; confirm the base
    is untouched and the loop is still engaged. (e) `INLET TRIM 20` again, then
    each of `INLET OFF`, `INLET 0`, `TUNE` (then `TUNE ABORT`), and a forced
    failsafe (unplug the inlet TC, as in item 3) → `INLET TRIM` must read
    `trim 0.0` after every one.
    (f) bounds: `INLET TRIM 500` clamps to +80, `INLET TRIM -500` to −80,
    `INLET TRIM abc` replies `invalid argument` and changes nothing.
    (g) auth: with `AUTH MODE FULL` and an unkeyed browser, **every** form —
    `INLET TRIM 20`, `INLET TRIM 0`, and bare `INLET TRIM` — must be refused,
    while `INLET OFF` and `INLET 0` still work. (h) regression: run a normal
    `INLET <degC>` session start to finish without ever sending `INLET TRIM` and
    confirm nothing differs from v0.18 behaviour.

## Artisan cascade PID — outer BT loop driving the inlet setpoint

*Active effort, branch `feature/artisan-pid` (off `main` at v0.18.0).
Artisan configuration + docs + commissioning; **no firmware change**.*

**Shape.** Artisan's software PID becomes the *outer* loop of a cascade: it
controls BT against a background curve, and its output is the **inlet
setpoint** that the firmware's existing `MODE_INLET` loop holds.

```
background BT curve (authored in Artisan's Designer)
  -> Artisan software PID (PV = BT, pidCycle 1000 ms)
  -> duty 0-100% mapped onto the slider-3 subrange [140, 300] degC
  -> slider 3 action: send({"command":"INLET","value":{}})
  -> firmware controlStep() (250 ms) modulates heat to hold that inlet temp
```

The firmware needs nothing new: `INLET <degC>` is already the entry point,
`engageInlet()` is already bumpless on retarget (keeps the integrator across a
gradually-moving setpoint), and the JSON envelope already preserves the
fraction (airRoaster.ino:1141). Time-constant separation is why this should
work — inlet air responds in seconds, BT in tens of seconds.

**Why not the flat loop.** Today `pidSource=3` points Artisan's software PID at
the *Inlet* channel with output to slider 4 (OT1 heat): Artisan duplicating the
firmware's own inner loop across a 1 Hz WebSocket link. The cascade keeps the
fast inner loop on-device and hands Artisan the slow outer job it is good at —
profile following against a background curve.

**Design decisions (operator-confirmed 2026-09-02).**

- Outer PV = **BT**, which is `pidSource=1` (see § Verified against source).
- Outer SV = **follow background** (`svMode=2`, already set); curves authored in
  Artisan's **Designer**.
- `artisan/make_inlet_background.py` is **out of scope and unchanged.** It
  remains the tool for the *inner*-loop event-playback path (README § Driving
  the setpoint from a roast profile), which stays available as the non-cascade
  alternative. The cascade does not generate inlet curves at all — the inlet
  setpoint is computed live by the outer loop.
- Output target = **slider 3** (`pidPositiveTarget=3`), the existing `INLET`
  slider.
- Setpoint range **140-300 degC via `positiveTargetRangeLimit=true`,
  `positiveTargetMin=140`, `positiveTargetMax=300`** — see § The floor for why
  this, and not `dutyMin`/`dutyMax`.
- `pidOnCHARGE=true`, `pidOffDROP=true`.
- **Heat-off at drop needs an Artisan alarm**, not `PID_OFF_action` — see
  § Heat-off at drop.
- Inner loop **not retuned** — Kp 1.5 / Ki 0.05 / Kd 0 stand (roast-validated).
  Revisit only if commissioning shows the inner loop is the limiting factor.
- The alternate gain sets (`pidKp1/2` etc.) were leftovers of unknown
  provenance; they are overwritten to match the new single set.
  `pidGainScheduling` stays false.

**Deliverable.** **`artisan/airRoaster_cascadePID.aset`** — the single canonical
config. It was briefly split into an `_edit` variant while the operator added the
alarms in Artisan; that content was folded back onto this filename 2026-09-02
and the `_edit` file removed (recoverable from commit 90c9c46). The background is now
**`artisan/profile_002.alog`** (CHARGE BT 127.8, DRYe 3:20, FCs 6:30, DROP 6:51
at BT 201.2 — a gentler middle ramp than `profile_001` to the same endpoint,
reached sooner). Both backgrounds carry zero special events, so neither can
conflict with the PID over slider 3.

**The base it was derived from** is
`artisan/airRoaster_inletPoints.aset`, the operator's live config as saved
2026-09-02 (itself superseding the older `airRoaster.aset`; their `[ArduinoPID]`
and `[Sliders]` sections are byte-identical, so the delta applies to either).
Both originals are left untouched so the inner-loop playback setup stays
loadable.

| Key (`[ArduinoPID]`) | playback config | **cascade, in force** |
|---|---|---|
| `pidSource` | 3 (Inlet) | **1 (BT)** |
| `pidPositiveTarget` | 4 (OT1 heat) | **3 (INLET)** |
| `positiveTargetRangeLimit` | false | **true** |
| `positiveTargetMin` / `positiveTargetMax` | 0 / 4 | **100 / 300** |
| `pidKp` / `pidKi` / `pidKd` | 0.18 / 0.054 / 0.09 | **3.0 / 0.07 / 0** |
| `pidKp1,2` / `pidKi1,2` / `pidKd1,2` | 27 / 0.018 / 36 | match the single set |
| `svLookahead` | 0 | **0, switched to 6 at 45 s by alarm** |
| `pidDsetpointWeight` | 1 | **0** (derivative on measurement) |
| `pidOnCHARGE` / `pidOffDROP` | false / false | **true / true** |
| `dropSpikes` | true | **false** (it rewrites `SV`/`HT` steps) |
| `Delay` | 1000 | **500** (the tuning is rate-independent) |

`dutyMin`/`dutyMax` stay **0 / 100** and `[Sliders]` is **unchanged** — both
deliberate, see below. `pidGainScheduling` stays false.

**The floor reached 100 over roasts 42-55**, from 120 → 170 → 140 → 100; the
argument for each move is § The floor, and roast 55 is where 100 was validated.

### Verified against source

Read from `~/src/artisan/src/artisanlib/{pid,pid_control,main,canvas}.py` at
**v4.2.0**, the installed build (the shipped `.app` is compiled, so the bundle
cannot answer these). Cite line numbers only from that clone — see
state-current.md § Referencing the Artisan source.

1. **`pidSource` numbering is 1=BT, 2=ET, >2=extra curves** with
   `n = pidSource-3`, `c = n//2`, even `n` = channel A / odd = channel B
   (`pid_control.py:1432`). So BT is **1**, not 2. The earlier inference of
   1=ET/2=BT was backwards. The identification of `pidSource=3` as extra1A
   ("Inlet") was right, since extras start at 3 either way.
2. **The PID output is a duty in [0,100] that is linearly mapped onto the
   target slider's range** (`pid_control.py` `setEnergy`):
   `raw = numpy.interp(v, [0,100], [heat_min, heat_max])`, where `heat_min/max`
   come from the slider's own min/max, narrowed to
   `[positiveTargetMin, positiveTargetMax]` when `positiveTargetRangeLimit`.
   So the slider range governs the commanded degC entirely.
3. **The fractional value does reach the command.** `setEnergy` emits both the
   rounded int and `raw_heat`; `addEvent_internal` uses the int only for the
   slider position and change-detection, and passes `raw_value` to the slider
   action ("if raw_value is not None, it is send to the slider action instead
   of the integer value"). No 1 degC quantization on the wire — the earlier
   concern about `dutySteps` re-introducing what airRoaster.ino:1141 removed
   does not apply to the *value*. It does bound the update *cadence*: an update
   is emitted when the duty moves by `dutySteps` (1 duty unit = 1.6 degC over
   the 160 degC span) or the integer slider position changes.
4. **Slider action type**: stored `slideractions=18` maps through
   `eventactionx` (`a+2` for `21 > a > 5`) to action 20 = "Artisan Command",
   which is what accepts the `send({...})` form. Unchanged by this work.

### The floor — and the correction that matters

`INLET <= 0` means *disengage*, not *setpoint 0* (v0.15.1, README § Inlet
temperature control): Artisan's SV slider parks at 0 after a background
playback, and a 0 degC target would leave the loop railed with heat pinned at
0. In a cascade, an outer loop that saturates low would kick the inner loop to
`MODE_MANUAL` at heat 0 and then, next tick, re-engage through `engageInlet()`
— which reseeds the integrator from the now-zero heat level. Not mere mode
chatter: a full inner-loop reset plus a heat kill, once per tick. The output
must therefore be structurally unable to reach 0.

**`dutyMin=120` was the wrong mechanism and would have been dangerous.**
`dutyMin`/`dutyMax` are *duty percentages*, not degC: `pid.py:473` clamps
`final_output = min(dutyMax, max(dutyMin, output))` where `output` is already
bounded by `outMin=0`/`outMax=100`. Setting `dutyMin=120` would pin
`final_output` at 120 every cycle, and `numpy.interp(120, [0,100], ...)` clamps
above the input range and returns `heat_max` — i.e. **the inlet setpoint would
sit at its maximum permanently, with the outer loop having no effect at all.**
A runaway-heat configuration. (`pid_control.py:1502` separately re-clamps
`dutyMin/Max` into 0-100 on the ArduinoTC4 path, confirming the intended
domain.)

The correct mechanism is the one Artisan documents for exactly this:
`positiveTargetRangeLimit=true` with `positiveTargetMin=140`,
`positiveTargetMax=300` — "the duty is mapped to the target slider subrange"
(`pid_control.py:1196`). Duty 0% -> 140 degC, duty 100% -> 300 degC. (120 until
roast 40, briefly 170, then 140 to allow a PID-driven preheat; see below.)

**`[Sliders]` is deliberately left alone.** Artisan's own stated assumption is
`slider_min < positiveTargetMin < positiveTargetMax < slider_max`
(`pid_control.py:1302`). Slider 3's existing 0-320 satisfies
`0 < 140 < 300 < 320`. The earlier plan to tighten `slidermax` to 300 would
violate it — so the 320/300 mismatch against `INLET_SV_MAX_C` stays, and
remains harmless (the firmware clamps, and the cascade never asks above 300).

Note the floor is a *heating* floor: on a BT overshoot the coolest the cascade
can ask for is 140 degC inlet. The operator's path below that is to turn the
PID off, which is also what `pidOffDROP` does at the drop.

### Heat-off at drop — already wired, no alarm needed

**This is already configured in `airRoaster_inletPoints.aset`** and needs no new
work. `buttonactions=0,0,0,0,0,0,20,0` with
`buttonactionstrings[6]="16,15,11"`: index 6 is DROP (canvas.py `markDrop` calls
`eventactionx(self.buttonactions[6], ...)` at canvas.py:15542), and stored 20
maps through `eventactionx` to action 3 = Multiple Event, which presses extra
event buttons 16, 15 and 11:

| Button | Label | Effect |
|---|---|---|
| 16 | `playback_OFF` | `playbackmode(0)` |
| 15 | `inlet_OFF` | `send({"command":"INLET","value":0})` -> firmware manual, heat 0 |
| 11 | `heatSlider_OFF` | event type 3 value 0 -> slider 3 to 0, same INLET 0 (redundant, harmless) |

`INLET 0` is exactly the v0.15.1 cooldown path: `MODE_MANUAL`,
`requestedHeatLevel = 0`, `applyInterlock()`.

**The ordering against `pidOffDROP` is safe.** In `markDrop`,
`pidcontrol.pidOff()` runs at canvas.py:15424, *before* the button action at
canvas.py:15542 — so the PID is already stopped when `INLET 0` is sent and
cannot re-command a setpoint afterwards. (CHARGE mirrors this: `pidOn()` at
canvas.py:14656 precedes `eventactionx(buttonactions[0])`.)

**Two mechanisms that look like they could do this cannot, so do not reach for
them.** `PID_OFF_action` fires only for external MODBUS/S7 PID control
(`pid_control.py:1538-1545`); this is a WebSocket device, so
`externalPIDControl()` returns 0. And an Artisan **alarm** cannot send a
WebSocket command at all — alarm actions have their own numbering topping out at
25 (`canvas.py:6153-6335`: 0=popup, 2=event button, 3-6=sliders, 13=DROP,
22=Playback ON, 23=Playback OFF, 24/25=canvas colour), with no Artisan Command
among them; an alarm can only reach the firmware indirectly by pressing an event
button. None of it is needed — the DROP button action already does it directly.

### Background event playback must be off

The one genuine conflict. In `airRoaster_inletPoints.aset`,
`specialeventplayback=false, false, true, false` and
`specialeventplaybackramp=false, false, true, false` enable replay of the
**T_inlet** event type — which drives **slider 3**. The cascade's outer PID
drives that same slider. Both writing it would fight.

The live config also carries an alarm that turns playback on automatically:
enabled, source -3 (no temperature source, so time-only), `alarmtime=0`
(after CHARGE), `alarmoffset=1` (1 s), `alarmaction=22` = **Playback ON**
(`turn_playback_event_ON()`), empty command string. It must not fire in the
cascade config.

So `airRoaster_cascadePID.aset` additionally sets, outside `[ArduinoPID]`:

| Key | From | To |
|---|---|---|
| `specialeventplayback` | `false, false, true, false` | all `false` |
| `specialeventplaybackramp` | `false, false, true, false` | all `false` |
| `alarmflag` | QVariantList[int] = 1 | 0 (alarm disabled) |
| `buttonactionstrings[0]` (CHARGE, `[DefaultButtons]`) | `"17,18,19"` | *(empty)* |
| `Controlbuttonflag` (`[Device]`) | false | **true** |

The CHARGE row is the third playback trigger in the live config: buttons 17-19
are `playback_time` / `playback_ON` / `playback_ramp`. It was already inert
there — `buttonactions[0]=0` (None) means `eventactionx` never runs the string —
but leaving the string in place is a trap: setting the action type would
silently start playback fighting the PID for slider 3. Cleared in the cascade
config.

### Config > Device > Control must be ticked

`Controlbuttonflag` (Config > Device > "Control") gates the software PID
itself, not just the visibility of the CONTROL button. `pidOn()`'s software-PID
branch is `elif self.aw.qmc.Controlbuttonflag:` (pid_control.py:1519), so with
the flag false `pidOn()` falls through and never activates the PID — meaning
`pidOnCHARGE` would silently do nothing. Monitor start likewise skips
`confSoftwarePID(reset=True)` unless `externalPIDControl() == 0 and
Controlbuttonflag` (canvas.py:13438), so the PID would never even be configured
with the current gains and sampling rate.

The live config has it **false**, so this is a required change, not a
convenience. It also surfaces the CONTROL button, which is the operator's
manual PID on/off — the escape hatch for dropping below the floor
mid-roast. (`PIDbuttonflag` is a different flag, for TC4/Fuji hardware PID
control; left as-is.)

**CHARGE still arms the outer loop**, without a button action:
`pidOnCHARGE=true` makes `markCharge` call `pidcontrol.pidOn()` directly
(canvas.py:14656), before any button action runs — mirroring `pidOffDROP` at
canvas.py:15424. This is also the moment the charge-aligned background SV curve
becomes meaningful. The remaining `[DefaultButtons]` rows (DRY, FCs, FCe, SCs,
SCe, COOL) are all action 0 with empty strings and need nothing.

These are exactly what to re-enable when switching back to the inner-loop
playback workflow — which is why the two configs stay separate files rather
than one file with a mode switch.

### Auto-DROP detection (operator requirement 2026-09-02)

DROP is the trigger for the whole heat-off chain — `pidOffDROP` stops the outer
loop and `buttonactions[6]` sends `INLET 0` — so a missed DROP leaves the heater
running. The operator wants it detected from the lever pull, which is plainly
visible in the traces (BT falls, RoR plummets).

**Artisan's built-in auto-DROP cannot do it.** `canvas.py:5151-5153` gates the
BT-break detector on `(sample_timex[-1] - sample_timex[timeindex[0]]) > 7*60` —
**auto-DROP cannot fire until 7:00 after CHARGE**, and these roasts drop at
6:20-6:31. `7*60` is a literal, so the Standard/Sensitive `autoDropMode` switch
is never consulted. (For the record, at 1 s sampling Sensitive only changes
`d_drop` from -0.34 to 0.00; `offset_drop` is identical at 0.2.)

**The background path is a scheduled drop, not detection.** `playbackdrop()`
(canvas.py:6345-6356) has a 4-minute gate (`playbackdrop_min_roasttime = 4*60`)
and its own flag `backgroundPlaybackDROP`, independent of event playback
(canvas.py:5384) — so it could be enabled without reintroducing the slider
conflict, via the Artisan Command `playbackdropmode(<n>)` (0 off, 1 by time,
2 by BT, 3 by ET). But it fires on the profile's schedule: by BT it needs the
background's DROP BT to sit *below* where the operator actually pulls (roast 42
peaked at 201.0 against a 202.0 background DROP, so it would never have fired),
and by time it fires at the profile's DROP regardless of the lever. Left off.

**The solution: an alarm on the RoR collapse.** Alarm action 13 = DROP
(canvas.py:6260-6263) with no time gate. Threshold sized from the traces
(10 s RoR span, degC/min):

| | roast 41 | roast 42 |
|---|---|---|
| min during DRYe..DROP (armed window) | -4.9 | **+5.4** |
| after the dump | -24.6 | **-43.6** |
| **charge dip** (for contrast) | **-266.7** | **-267.0** |

`-25` never occurs while roasting (tightest margin ~20 degC/min) and is crossed
within ~3 s of the BT peak at the dump. The charge dip at -267 is why the alarm
**must not be armed from CHARGE** — it would fire at turning point every roast.
DRYe (~2:36-3:20) is safely past TP (~0:30).

As entered and verified in `airRoaster_cascadePID.aset`:

```
alarm 1: off  From=CHARGE   offset=1s  Source=(none/time)  above    0  -> Playback ON
alarm 2: ON   From=DRY END  offset=0s  Source=DeltaBT      below  -25  -> DROP
```

**`Time` must be 00:00.** The alarm's time and temperature conditions are OR'd,
not AND'd — `if alarm_time >= alarmoffset: alarm_ready = True` (canvas.py:5286)
and the temperature block each set the flag independently. A non-zero offset
makes the alarm fire on the clock alone, ignoring the RoR entirely.

Safe alongside a manual press: the DROP action is guarded by
`timeindex[6] == 0`, so whichever comes first wins and there is no double-mark.
Artisan's own `autoDrop` can stay on; its 7-minute gate makes it inert at these
roast lengths.

**Still wanted eventually** (operator): instrument the dump lever so the pull
sends a real signal. The clean path needs no new Artisan capability — expose the
lever as an extra channel in `handleArtisanRequest()` (README § adding a
channel), then an alarm with Source = that channel, condition above 0.5, action
DROP. Same alarm mechanism, a measured event instead of an inferred one.

#### The inlet spike beats the RoR collapse, and it is measured (operator proposal, 2026-09-08)

The operator asked for the **inlet spike at the dump** as the trigger. Roasts
53-57 say it is the better signal on every axis that matters, and the margins
are not close.

**The mechanism, from the operator (2026-09-09).** The inlet probe is a bare
thin-wire thermocouple protruding into the airflow **just downstream of the
heater and upstream of the grate** that holds the bed — nearly no mass, and
extended away from the entry port so it reads the air rather than the wall.
Pulling the dump lever *slides the grate*: it opens the dump chute and blocks the
grate at the same time, so the fan keeps pushing into a highly restricted path.
Flow past the probe collapses while the heater is still delivering, and the probe
— having almost no thermal mass — spikes immediately. The inner loop then cuts
heat to zero, which is the correction, not the event. All of it inside two
seconds.

**That is why this signal is fast and why it is not a temperature threshold.**
The spike is a *flow* event read by a near-massless sensor, so its size is set by
the restriction and the duty at that moment, not by how hot the roast was.

| roast | `Inlet − SV` at the dump | max `Inlet − SV`, DRYe→DROP−5 s | `HT` at the spike | min `HT`, same window |
|---|---|---|---|---|
| 53 | **+23.4** | 2.3 | 0 | 51 |
| 54 | **+19.6** | 1.8 | 1 | 51 |
| 55 | **+20.0** | 1.4 | 0 | 56 |
| 56 | **+21.9** | 1.2 | 0 | 56 |
| 57 | **+20.2** | 1.9 | 0 | 53 |

degC and %. A threshold of `Inlet − SV > 10` sits **4-8× above** anything the
armed window produces and **2× below** every event. The inner loop tracks at
rms 0.91 degC, so the spike is a 20-sigma excursion.

**And it leads the DROP mark instead of lagging it.** First crossing, seconds
relative to the DROP mark in each file:

| | 53 | 54 | 55 | 56 | 57 |
|---|---|---|---|---|---|
| `Inlet − SV > 10` | **−3.5** | **−2.5** | **−2.0** | **−0.5** | **−3.5** |
| `HT < 20 %` | −3.5 | −2.0 | −2.0 | −0.5 | −3.0 |
| `DeltaBT` (10 s span) below −25 | +6.0 | +7.0 | +6.5 | **never** | +6.0 |

The RoR collapse is a *consequence* of the beans leaving and cannot precede it;
the spike is the vent itself. **The swing is 7-10 s of heater on-time**, and on
a 10 s span roast 56 misses the collapse threshold outright.

**Arming is the same constraint as the DeltaBT alarm, for the same reason.**
Measured from CHARGE+30 instead of DRY END, the same window gives max
`Inlet − SV` of **9.2-11.5** and 2 s inlet rises of **30-35 degC** — the dip
recovery — which would trip a +10 threshold every roast. **Arm from DRY END.**

**Implementation.** `Inlet` is extra channel 1 and `SV` extra channel 3, so the
discriminator is a virtual channel of the shape `Temp_Drive` (`Y3-Y2`) already
uses; or alarm on `HT` below 20 %, which fires at the same instant with a 2.5×
margin and needs no new channel. Alarm action 13 = DROP, `alarmtime` = DRY END,
`alarmoffset` **0** (§ above: time and temperature conditions are OR'd, so a
non-zero offset fires on the clock alone). It replaces neither the DeltaBT alarm
nor the instrumented lever — the lever is still the measured event, this is the
best inference available without new hardware — and it can run alongside the
DeltaBT alarm, since the DROP action is guarded by `timeindex[6] == 0`.

**The roast 56 anomaly is closed — roast 60's chain fired in 1.0 s**
(state-history-residual.md § Phase B). What was wrong is recorded below for the
next time it happens; nothing in the roast 60 log says which of the candidates it
was, so this is a symptom description, not a diagnosis. In
roast 56 the DROP mark sat at 392 s, on the spike — but the heat-off chain did
not run there. `SV` climbed 230.9 → **255.2** and `HT` went 38 → 90 → **100 %**
over the next 16 s, BT recovering 194.4 → **201.7** in an emptied chamber; heat
reached 0 only at **+17.5 s**. `pidOffDROP = true` and `buttonactions[6] =
"19,14,11,12"` are both present in `airRoaster_cascadePID_floor100.aset`, so on
the file the chain should have fired at the mark — and on
`airRoaster_cascadePID_phaseB.aset` it did. **If a future roast shows the mark
landing without the heat going off, that is this bug back**: score check (b) of
§ Phase B's B3 on every roast that auto-DROPs, because a trigger 3 s earlier into
a chain that takes 17 s to act buys nothing.

### The characterisation-run config — `airRoaster_cascadePID_char.aset`

*The runs themselves are done (roasts 47 and 48, state-history-cascade.md). The
config is kept because it is the open-loop replay harness, and step 9 depends on
the same machinery.*

**It replays, it is not hand-driven.** `specialeventplayback` is a
**per-event-type** 4-element list (canvas.py:1848) and the master switch
`backgroundPlaybackEvents` is separate, so enabling types 0 (`Air`, slider 1) and
2 (`T_inlet`, slider 3) replays a test's fan *and* inlet schedules and touches
nothing else. The collision that forces playback off for the cascade
(§ Background event playback must be off) is specifically that playback and the
PID both want slider 3, which cannot arise on a run that is open-loop by
construction. Replaying makes the excitation identical between runs and rehearses
exactly the machinery step 9 needs.

Generated by `tools/gen_pid_alarm_asets.py` as a key-override variant of the
canonical config — no buttons, no alarms, five keys:

```
pidOnCHARGE = false                                # the PID must never arm
backgroundPlaybackEvents = true                    # master playback switch
replayType = 0                                     # replay by time
specialeventplayback = true, false, true, false    # Air + T_inlet
alarmflag = 0, 0                                   # the DeltaBT auto-DROP alarm
autoDrop = false                                   # *and* Artisan's built-in detector
```

**`autoDrop` is not an alarm, and it cost roast 47 eighty-eight seconds.**
Artisan's built-in DROP detector (canvas.py:5151) is gated on `autoDropFlag`,
BT > 160 degC and **more than 7 minutes since CHARGE**, and `alarmflag` does not
touch it. That 7-minute gate is why it never appears on a real roast here — these
drop at 6:20-6:31, which is the whole reason the DeltaBT alarm exists — but
**every characterisation run is longer than 7 minutes and above 160 degC.**

**The DeltaBT alarm is disabled too**, because `autoDRY` can mark DRY END on an
*empty* roaster (the empty-run background takes BT past the 149 degC Phases
threshold), which would arm the auto-DROP mid-test and end the run through the
`INLET 0` chain. **Press DROP by hand on these runs.**

**Procedure: press ON, load the file as background, press START, then press
CHARGE.** CHARGE is required rather than forbidden — `playbackevent()` runs only
once the foreground CHARGE is marked (canvas.py:5381) — and it is safe because
`pidOnCHARGE` is forced off *in the file* rather than avoided by not pressing the
button. Everything after that is automatic; the operator's job is the fan level
and DROP.

**The schedule files**, all generated, all ordinary background profiles carrying
the test schedule as `T_inlet` and `Air` events:

| file | generator | what it is |
|---|---|---|
| `artisan/charstep_empty_fan.alog` | `tools/gen_char_empty.py` | empty, 17 min — inlet steps 145/185 crossed with a fan sweep **58-80** on an offset grid (no fan step within 30 s of an inlet step). Run as roast 47 |
| `artisan/charsingle_400g.alog` | `tools/gen_char_single.py` | loaded, 12:15 — three flat setpoints (190/215/245) each carrying a fan step, valleys between to pull BT back. Run as roast 48 |
| `artisan/chardoublet_fan60.alog`, `..._fan68.alog` | `tools/gen_char_doublet.py` | the two-batch alternative, never run — kept for the 800 g case |
| `artisan/charstep_empty.alog`, `artisan/chardoublet_loaded.alog` | — | superseded originals; do not use |

**Three constraints any future schedule must respect.** A charge does not
circulate at fan 60 — it takes ~64 to loft the bed, so every file opens at 64
until 1:30. The fan floor is **55** (`IL_FAN_FULL_DFLT`, airRoaster.ino:111,
below which the interlock clips the heat and the inner loop stops holding the
inlet) and 58-59 in practice, so the tools refuse under 57. And the plateau stays
**below first crack** — ~185 degC — so the bean exotherm does not sit on top of
the signal being measured.
### The lookahead-switching config (2026-09-02)

`artisan/airRoaster_cascadePID_lookahead.aset` — the canonical config plus the
runtime lookahead switch from state-history-cascade.md § Scheduling. **A separate file
deliberately**: it is an experiment and should not ride along with the `pidKi`
and profile_003 changes on the next roast.

Two new event buttons appended after the existing ones — action 20 = Artisan
Command, hidden, recording no event — the first running `pidLookahead(0)` and
the second `pidLookahead(6)`. As of 2026-09-03 the canonical config has 19 event
buttons, so they are user-facing **20** and **21**.

> **The button numbers are positional and will drift.** They were 22/23, then
> 23/24 when a "Fan Mid" button was added, then 20/21 when the canonical config
> was reworked from 22 buttons down to 19. `alarmstrings` holds the **1-based
> index**, so adding or removing an event button silently re-points these
> alarms. **Never hand-edit this variant.** Regenerate it with
> [tools/gen_pid_alarm_asets.py](tools/gen_pid_alarm_asets.py), which derives the
> button numbers from `len(extraeventslabels)` in the canonical file and appends
> the buttons and alarms to a fresh copy of it.

```bash
python3 tools/gen_pid_alarm_asets.py
```

and two new alarms, both **time-only from CHARGE** (`alarmsource = -3`, so the
temperature branch never evaluates and the OR'd conditions cannot misfire),
action **2** = press an event button, whose `alarmstrings` entry is the
**1-based** button number (canvas.py:6194-6211):

```
alarm 3: From CHARGE, offset  1 s, source -3 -> button 20 -> pidLookahead(0)
alarm 4: From CHARGE, offset 90 s, source -3 -> button 21 -> pidLookahead(6)
```

So the dip runs at lookahead 0 — no manufactured error, no SV floor at turning
point (state-history-cascade.md § profile_003) — and the ramp gets 6 s of feedforward,
which costs no phase margin. 90 s is past turning point and where the background
RoR has fallen enough that the switch is a ~+3.5 degC target step rather than
+4.6.

### Step 9 — the inlet feedforward schedule with the PID as a trim (design)

*The design that runbook step 9 executes. It came out of the strategy search of
2026-09-06 (state-history-cascade.md § Dip strategies), which is where the sweep numbers
and the discarded alternatives are.*

> **A cheaper relative was proposed 2026-09-08** — commanding `Temp_Drive =
> Inlet − BT` instead, which is this design with the base supplied by
> measurement rather than by a schedule. It is weaker on tracking and stronger
> on nearly everything else; see § Temp_Drive as the effort variable below, and
> settle the preheat measurement before deciding between them.

> **Status after roast 56 (2026-09-07): the tracking case for this is dead.**
> The premise below — that `e_ss = (dI/dt)/Ki` is a limiting error and that
> `svLookahead` exists to hide it — was written when the loop tracked to several
> degC. Roast 56 tracks its background at rms **0.94 degC over 30-90 s**, **0.41
> over 95-120 s** and **1.26 over the whole roast**, with the inner loop at rms
> **0.91 from 50 s to DROP** (state-history-charge.md § Roast 56). The simulated
> "steady rms 0.11-0.14 degC" is no longer an improvement worth the two open
> config problems below. **What survives is the robustness argument** — that a
> feedforward base degrades more gracefully than an integrator carrying the
> whole operating point when the plant moves or the inner loop is disturbed —
> **and that has to be argued on its own terms, with a stated test, or step 9
> should be dropped.** The residual roast 56 does leave (−2.9 degC at 140-200 s,
> the integrator's fill rate against the drying ramp) is a *phase* deficit and
> is being attacked with lookahead first; see state-current.md § HANDOFF.

#### The structural fix: an inlet feedforward schedule with the PID as a trim

**The root defect has been on the table since roast 40 and has never been
addressed: the outer loop's output is an absolute setpoint, so its integrator has
to supply the entire operating point** — a job the inner loop gives to
`feedforward()`. That is why `I` climbs 8 → 63 across a roast at 0.09 duty/s, why
`e_ss = (dI/dt)/Ki` exists at all, why `svLookahead` is needed, and why the value
handed over at 1:30 matters in the first place. Every option above rearranges
that burden. This one removes it.

Give the firmware a **base inlet schedule** and make Artisan's PID output a
**bounded trim** on it:

```
INLET = ff(t since CHARGE) + trim,        trim in [-80, +80] degC
ff(t) = bg(t+theta) + (dbg/dt(t+theta) - loss(t+theta)) / a
```

— the plant inverted on the background, `a = 0.0049`, `theta = 13.5 s`, with the
loss term a cubic fitted over 45 s..DROP. **The schedule deliberately knows
nothing about the charge dip**, which is the honest case: the dip is the one part
that is not repeatable, so it is left entirely to the trim.

What that buys, from the table above:

- **`dI/dt` collapses from 0.09 to 0.01 duty/s** and `I@DROP` from 63 to 50 — the
  trim sits mid-range instead of ramping, so the type-1 error is **structurally**
  gone rather than cancelled. Steady rms **0.11-0.14 degC** against 0.26-0.38.
- **`svLookahead` becomes unnecessary** — every FF row runs `L = 0`. The whole
  lookahead-versus-dip tension (state-history-cascade.md § Roast 44 outer-loop analysis:
  `L > 4` winds the integrator through the dip) disappears with it.
- **the handover value stops mattering**: with the gate, `I@1:30` is 49.9 at every
  charge state and `dt150` is +1.6 s at every charge state — spreads of **0.0 and
  0.1**, against 1.2 and 4.2 for `lookahead_kigate`. The dip becomes a bounded
  trim excursion instead of an integrator re-seeding event.
- and the gate now **helps** rather than trading: worst error over 1:30-3:20 goes
  +2.25 → **-0.87**, because there is no longer an operating point for the frozen
  integrator to be behind on.
- **±20% of error in the assumed plant gain** costs `dt150` +6.4 s or -1.1 s and
  leaves steady rms at 0.15-0.16 — still better than anything else in the table.
  A 30% error in the loss term costs about the same.

**The base mechanism is not speculative — roast 20 ran it (2026-07-03).** Three
special events in the whole log and an inlet that ramped 150 → 265 degC anyway:
`playbackevent` replayed the background's eight `T_inlet` events, the inner loop
tracked the commanded polyline at **rms 0.60 degC, worst −1.88, over 20-330 s**,
and the resulting BT is the smoothest in the archive — post-dip RoR fits its own
cubic to **0.375 degC/min** against the cascade's 1.6-2.8. **The cost of the
integrator supplying the operating point is measurable in the input**: the
cascade's inlet command deviates from a smooth curve by 12-18× what the playback
schedule did, and jumps up to 36.7 degC in ten seconds. See state-history-residual.md
§ Roast 20 revisited — including the two things it does *not* show (it has no BT
target to score against, and the archive has no open-loop repeat pair).

**It needs one small firmware command and no new Artisan machinery.**
`specialeventplayback` is **per event type** (canvas.py:1848) and
`pidPositiveTarget` selects **any of sliders 1-4** (pid_control.py:1252), so
background event playback can drive the base on one slider while the PID drives
the trim on another — the collision that forced playback off for the cascade
(§ Background event playback must be off) was specifically that both wanted
slider 3. So:

- **Artisan**: re-enable playback for the inlet-base event type only; point
  `pidPositiveTarget` at the trim slider; map that slider's target subrange onto
  the trim range. The base curve goes into the background `.alog` as replayable
  events — **but `artisan/make_inlet_background.py` does not currently emit a
  file of that shape**; see § The base-curve authoring gap below.
- **Firmware**: one new command, `INLET TRIM <degC>`, bounded, defaulting to 0,
  cleared on disengage and on `INLET 0`. The inner loop's setpoint becomes
  base + trim. Everything else, including the `INLET 0` DROP chain and the
  cooldown guard, is untouched.

**What it needs characterised before it is worth roasting**, and this is the
honest weakness of the simulation: `ff` here is built from roast 46's own fitted
plant and disturbance, so the exact-FF rows are partly circular. The ±20% gain
and -30% loss rows are the answer to that and they hold up, but the real
confirmation is Test A/B/C — **which have just recovered their priority**, since
the FF schedule is exactly `1/a` and the loss curve, and the loss curve is where
the fan enters. A schedule that is wrong in the *loss* term is wrong in the same
direction for the whole roast, which the trim absorbs; a schedule wrong in `a` is
wrong in proportion to the ramp rate, which it also absorbs, at 6 s of timing.

**Risks to close before this is run.** The base schedule runs open-loop, so a
stalled Artisan leaves the firmware holding base + last trim rather than a single
frozen setpoint — the same exposure as today but with two stale numbers instead
of one, and it argues for a trim staleness timeout in the firmware. The trim
range must be bounded on the device, not only in the Artisan mapping. And an
authoring error in the base curve is a whole-roast error rather than a transient,
so the base must be regenerated from the background whenever the background
changes.

#### Temp_Drive as the effort variable — a cheaper relative of step 9 (operator, 2026-09-08)

**The idea.** Let the outer loop command `Temp_Drive = Inlet − BT` instead of an
absolute inlet setpoint. The firmware owns `btTemp`, so the inner loop's target
becomes `btTemp + drive`. Structurally this is step 9 **with the base supplied by
measurement instead of by a schedule**:

```
step 9:      INLET = bg(t+theta) + (dbg/dt(t+theta) - loss(t+theta))/a  +  trim
Temp_Drive:  INLET = BT(t)       +  drive                    <- the PID's output
```

Step 9's feedforward carries two terms — the **operating point** `bg` and the
**rate** `(dbg/dt − loss)/a`. Temp_Drive cancels the first and leaves the second
to the PID. That is the whole comparison, and it decides everything below.

##### What the logs already say — and it is less than the algebra promises

The drift in the loop's own output is what sets the type-1 ramp error
(`e_ss = (dU/dt)/Ki`). Measured on the cascade roasts, smoothed 11 s:

| | inlet SV, drift | Temp_Drive, drift | ratio |
|---|---|---|---|
| **40 s → DROP** 53 / 54 / 55 / 56 | +0.267 / +0.243 / +0.282 / +0.290 | −0.051 / −0.103 / −0.074 / −0.087 | 5.3 / 2.4 / 3.8 / 3.3× |
| **120 s → DROP** 53 / 54 / 55 / 56 | +0.181 / +0.141 / +0.138 / +0.201 | −0.080 / −0.133 / −0.140 / −0.094 | **2.3 / 1.1 / 1.0 / 2.1×** |

degC/s. **Over the whole roast Temp_Drive drifts 2.4-5.3× less; over the drying
ramp — the window the −2.9 degC residual actually lives in — it is 1.0-2.3×, and
on roasts 54 and 55 it is no better at all.**

The reason is visible in the sign. BT rising pushes the inlet **up**; the
background's RoR declining (46 → 9 degC/min) pushes the required drive **down**.
Over the whole roast the BT rise dominates. Over the drying ramp the two are the
same size, so cancelling only the first leaves a drift of comparable magnitude
pointing the other way. **Step 9 cancels both terms and Temp_Drive cancels one —
and in the window that matters, it is the smaller one.**

**So: do not adopt this for tracking.** On that metric it is a weaker step 9, and
step 9's own tracking case is already dead (roast 56, rms 0.94 over 30-90 s).

##### Where it is genuinely better than step 9, and it is not a small list

All of these are robustness arguments, which is the only ground step 9 still has:

- **No base curve to author.** § The base-curve authoring gap is step 9's open
  blocker — `make_inlet_background.py` does not emit a file of the right shape.
  Temp_Drive needs no file.
- **No open-loop whole-roast failure mode.** Step 9 warns that "an authoring
  error in the base curve is a whole-roast error rather than a transient". The
  Temp_Drive base is BT. It cannot be authored wrong.
- **No plant card, so no circularity.** Step 9's `ff` is built from `1/a` and
  roast 46's loss cubic, which the section itself calls "partly circular" and
  gates on the characterisation runs. `INLET = BT + drive` needs neither `a` nor
  `loss`, because the operating-point term is exact by construction. **It is not
  blocked on Tests A/B/C.**
- **Background-independent.** Step 9's base must be regenerated whenever the
  background changes. Temp_Drive composes with any background — including a
  regenerated one, which is the whole point of the peak pin.
- **The floor stops being scale-dependent, and this may be the best argument.**
  `positiveTargetMin = 100` means `TD ≥ +41` at the turning point (BT 59) and
  `TD ≥ −100` at DROP (BT 200): the *same config number* is "still heating hard"
  early and "cool as hard as you can" late. That is why the floor has been
  retuned four times (120 → 170 → 140 → 100) and why roast 54 sat **40 s
  saturated at its own floor** — an absolute floor is the wrong shape of
  constraint. A drive floor means one thing all roast.

##### Three risks, one of them a genuine safety regression

1. **A stale command runs away.** A frozen absolute SV is self-limiting — BT
   converges to it. A frozen *drive* keeps ramping: at the observed TD ≈ 70 that
   is ~20 degC/min, indefinitely. **This is worse than today and must be
   designed for**, not noticed later. v0.19.0's `INLET_TRIM_STALE_MS` pattern is
   the right shape; here it is load-bearing rather than hygiene, and the safe
   fallback is to latch the last *absolute* setpoint, not to zero the drive.
2. **BT enters its own setpoint with gain 1.** Probe noise, drop spikes and RTD
   faults go straight into the inner loop. Use the filtered `btTemp`, rate-limit
   the base, and hold the last good value across an RTD fault.
3. **It must not be engaged through the dip.** `INLET = BT + drive` would chase
   BT down from 130 to 59 and cut the inlet exactly when the bed needs it. It has
   to engage with the PID at CHARGE+15 s and hold an absolute setpoint before
   that — which is what § The charge gate already does, so this costs nothing.

##### What it would take

Small, and mostly config. The slider already sends
`send({"command":"INLET","value":{}})`; a drive mode is one firmware command
alongside the existing `inletBase`/`inletTrim` pair, plus
`positiveTargetMin`/`Max` remapped onto a drive range. Note Artisan asserts
`slider_min < positiveTargetMin` (pid_control.py:1302), so a drive range
starting at 0 needs slider 3's minimum moved below it.

##### The development plan — five stages, and only one of them costs beans

Gated on the preheat characterisation (state-current.md § HANDOFF § 0 and § 1),
because stage A's design constants come out of it.

**A. Bench, no beans — the Temp_Drive ladder. DONE 2026-09-08, and it passes.**
`artisan/airRoaster_empty_BT-target-steps.alog`, six settled rungs at BT 130 /
140 / 145 / 152 / 130 / 145. **`d(TD)/d(BT) = +0.025`** — DC gain near 40, so the
drive→BT loop is very nearly an integrator, and the kill criterion below is
cleared by **20×**. Even the most adverse pairing in the data gives 0.17.
The kill criterion was `d(TD)/d(BT)` **above ~0.5**, which would have left the
drive→BT loop a high-gain type-0 with the structural benefit mostly gone. It came
back 20× clear. **Go to stage B.**

Two cautions carry forward (state-history-residual.md § Phase 0, reproduced at 8×
the sample count by Phase A): the slope is *bounded*, not measured — Temp_Drive
moved 0.6 degC across the whole ladder while same-BT repeats disagreed by −1.51
and +1.02 — and **heater duty repeats 6× better than `Inlet − BT`**, because the
BT probe carries a slow local-metal component. **Never tune on a Temp_Drive
difference under ~2 degC.**

**B. Desk — settle the four design questions.** None need hardware.

1. **The staleness fallback.** A frozen drive keeps ramping; a frozen absolute SV
   does not. The fallback must **latch the last effective absolute SV**, not zero
   the drive and not hold the drive. `INLET_TRIM_STALE_MS`'s 15 s and its
   "logged once per stale run" pattern are the shape; the *action* is different
   and this is the one place the existing code must not simply be copied.
2. **The BT path into the setpoint.** BT enters its own setpoint with gain 1.
   Decide: which filtered `btTemp`, what slew limit on the base, and what happens
   across an RTD fault (hold last good, and for how long before the failsafe).
3. **The mode transition at CHARGE+15.** The gate holds an absolute SV through
   the dip and drive engages with the PID. That handover must be bumpless in
   *both* directions — the firmware seeds `drive = inletSV − btTemp` on entry,
   and Artisan's PID integrator must map to that same drive. This is the same
   integrator-handover problem the cascade already has at CHARGE+15, at a
   different scale; § Roast 44 outer-loop analysis and § Roast 53 are the prior
   art.
4. **The drive range and the slider assumption.** Map
   `positiveTargetMin`/`Max` onto a drive range — roasts 53-57 ran
   Temp_Drive **29-94 degC**, so something like 0-160 covers it with margin.
   **Every one of those figures carries ±1.5 degC of probe history** (§ Phase 0),
   which is an argument for the margin, not against the range. **Never tune on a
   Temp_Drive difference under ~2 degC.**
   Artisan asserts `slider_min < positiveTargetMin < positiveTargetMax <
   slider_max` (`pid_control.py:1302`), so slider 3's minimum has to move below
   the drive floor. **Do not leave the 0-320 slider range and a 0 floor: that
   violates the assertion Artisan states.**

**C. Firmware — `INLET DRIVE <degC>`, and a bench drill.** One command beside the
existing `inletBase`/`inletTrim` pair (`inletEffectiveSV()`, airRoaster.ino:2543
is the single place that assigns `inletSV`, so this is a small change in a place
already designed for it). Drill it exactly like § NEXT 11: bounds, `INLET DRIVE
0`, bare `INLET DRIVE` reporting, the staleness ramp, clearing on `INLET OFF` /
`INLET 0` / `TUNE` / failsafe, auth under `AUTH MODE FULL`, and a regression run
that never sends the command. **Add one drill § NEXT 11 has no analogue for: with
the drive engaged, spoof an RTD fault and confirm the setpoint holds rather than
following BT to zero.**

**D. Empty chamber, no beans — first light.** Run the whole cascade against a
background with no charge in the drum, exactly as roast 47's grid did. The plant
is wrong (no bed) so tracking numbers mean nothing, but **every failure mode
worth finding is structural**: the CHARGE+15 handover, the staleness fallback,
the drive range mapping, whether BT noise reaches the heat, and whether the loop
is stable at all with BT inside its own setpoint. **This stage is free and it is
where the design should break if it is going to.**

**E. One roast — and not on `C1043`.** By the time this runs it is a
single-variable change against a known-good baseline. Score it on the four checks
plus the 120 s→DROP tracking rms and, specifically, **the drift in the loop's own
output** — the quantity the whole design is about. Predicted: the same tracking
as roast 56 with 2-3× less effort drift over the drying ramp, and **no floor
saturation at any BT**, which is the claim that is most worth checking because it
is the one the measured drift table does not already answer.

**Where LA 12 sits.** Deferred (state-history-residual.md § The LA 12 plan, deferred).
If stage E lands, a lookahead patch on a type-1 ramp error is treating a symptom
the loop no longer has — so **decide LA 12 after E, not before.** If A's kill
criterion fires, LA 12 comes straight back as the cheap fix it was.

##### It also disambiguates the plant card's `loss(t)`

The plant card's `loss(t)` is a function of *time* only because BT(t) is monotone
on a roast, so a **BT-dependent** loss is aliased into it and
`plant_roast46.json` cannot separate the two. A settled Temp_Drive at two
preheats is a steady-state measurement with no time axis to alias against — so
the same ladder that gates this design also tells step 9 whether its loss term is
what it claims to be.

#### The base-curve authoring gap — `make_inlet_background.py` does not emit this file (2026-09-06)

The structural fix above needs **one** background carrying three things at once:
profile_003/004's **BT curve** (the outer PID's target — `pidSource = 1`), the
**base schedule as replayable special events** on the base slider, and the real
**`timeindex` marks**. Neither of the script's two output modes is that file,
and it is not a matter of flags:

- **default mode** writes the continuous curve into `extradevices = [58, 22]`
  (channel B3) for *Follow-Background* mode. That is a different mechanism —
  no special events at all, so nothing for `playbackevent` to replay.
- **`--events N` mode** (`build_events_alog`) does emit the events, and on the
  right type — but it **hard-codes `temp2 = [-1.0] * len(timex)`**, blanks
  `extradevices`, puts the mirrored playback polyline in the *ET* slot
  (`temp1`), and sets `timeindex = [0, 0, 0, 0, 0, 0, len-1, 0]`: CHARGE at
  sample 0, DROP at the last sample, **no DRY END and no FCs**. It is an
  inlet-only background by construction, which is exactly right for the
  inner-loop event-playback path it was written for and gives the outer PID
  nothing to follow.

Measured on the files in the repo: `bkgd_inlet_150+25-255@420.alog` has
`temp2 = -1.0` for all 421 samples and 8 type-2 events; `profile_003.alog` has
BT 67.4-201.6 degC over 427 samples and **zero** special events.

**So the step-9 background is a merge, not a generation.** Take profile_003 (or
004) and add the four `specialevents` / `specialeventstype` /
`specialeventsvalue` / `specialeventsStrings` arrays to it. That is additive to a
recorded profile and disturbs nothing: profile_003 already carries
`etypes[2] = 'T_inlet'`, its own `extradevices = [112, 25]`, and
`timeindex = [0, 192, 399, 0, 0, 0, 425, 0]`. The two pieces the script already
has and the merge should reuse are `events_ext_to_internal` (the
`specialeventsvalue` encoding, whole-degree quantised, and it already handles
negatives) and `place_event_times`.

**Two assumptions corrected against v4.2.0 while checking this.**

1. **Playback does not match event-type *names*.** The script's inline comment
   says *"playback only fires when the background's event-type name matches the
   foreground's (canvas.py:playbackevent)"*. It does not: `playbackevent`
   reads `event_type = self.backgroundEtypes[i]` (canvas.py:6436), admits it on
   `0 <= event_type < 4` (:6438), and gates it on `end_reached[event_type]`
   (:6443), which is seeded as `[not flag for flag in self.specialeventplayback]`
   (:6420) — a 4-element per-type bool list (canvas.py:1848). **No name is
   compared anywhere in the function.** So the merged background does not need its
   `etypes` list aligned with the `.aset`'s — only the numeric type index has to
   agree. Names still drive labels and annotations. This *simplifies* the merge;
   it also means a mismatched name will not save you from a wrong index.
2. **Events after the background's DROP are never replayed** —
   `(self.timeindexB[6]==0 or bge <= self.timeindexB[6])`, canvas.py:6444.
   With profile_003 that caps the base schedule at index **425 (~416 s)**, the
   same window constraint § Auto-DROP detection found for `svLookahead`. It bites
   harder here: `ff(t) = bg(t+theta)` reads the background **ahead** by
   `theta = 13.5 s`, so the last ~14 s of the schedule has no background left to
   read and needs an explicit tail rule rather than the script's flat-outside-
   range `_interp`.

**One thing to choose rather than inherit: the event count.** Playback
interpolates linearly between successive events, so `N` events is an
`(N-1)`-segment polyline. The script's default of 8, tail-biased, was tuned for
the smooth inner-loop ramp; `ff(t) = bg(t+theta) + (dbg/dt - loss)/a` carries a
curvature term the ramp did not have. Pick `N` from the residual of the polyline
against `ff` — a free offline check once `ff` exists — not from the default.
The whole-degree quantisation is not the constraint: 1 degC of base against
`a = 0.0049` is ~0.005 degC/s of BT rate.

**And the mechanism was never the gap.** Roast 20 replayed eight `T_inlet`
events off `bkgd_inlet_150+30-265@330.alog` with no hand on the slider and no
outer loop, so `playbackevent` driving the inner loop is demonstrated on this
machine. What was missing is precisely what this section says: a *file* carrying
both the BT curve and the events. (Roast 20's background is the `--events` mode
output — `temp2 = −1.0`, no DRY END, no FCs — which is why it had no outer loop
to be followed.)

**The gap is closed (2026-09-06).**
`tools/merge_inlet_base.py` is the merge; `make_inlet_background.py` is untouched,
as its 2026-09-02 scope boundary requires. It is standard-library only, like the
other tools in `tools/`, and it reads the plant from a **card** —
`tools/analysis/plant_roast46.json`, written by
`tools/analysis/roast46_refit.py --emit-plant`. That is the seam the steps-3-5
gate needs: when the characterisation runs land, re-run `--emit-plant` and re-run
the merge, and nothing else in the chain changes.

```bash
python3 tools/merge_inlet_base.py --into artisan/profile_003.alog --dry-run
```

On `profile_003` and the roast-46 card (`a` 0.004897, `theta` 13.5 s, loss cubic
over 45 s..DROP) it emits **7 type-2 events**, base **199 → 256 degC**, max replay
error **0.87 degC of base = 0.0042 degC/s of BT rate**. The output is the input
profile plus the four `specialevents*` arrays: BT, `timex`, `timeindex`,
`extradevices` and everything else pass through byte-identical, and only the
source roast's identity (`roastUUID`, `plus_*`, `hash`, `signature`, `computed`)
is blanked so a doctored background cannot be mistaken for, or re-synced as, a
roast. **The file itself is generated on demand, not committed** — there is no
`ff(t)` worth roasting until steps 3-5 run, and a stale one on disk is a thing to
load by accident.

**Five things the implementation found that this section did not have.**

1. **The name check is not absent, it is broken.** The claim above — "no name is
   compared anywhere in the function" — is wrong as stated. `canvas.py:6530` does
   compare, as `str(self.etypesf(t) == str(self.Betypesf(t)))`: `str(bool)`, always
   a non-empty truthy string. The *conclusion* holds for v4.2.0 and the same
   expression guards the ramp branch at :6546 — but it holds by accident, and an
   Artisan that fixes the parenthesis would start enforcing it. So the tool aligns
   `etypes[type]` deliberately rather than relying on the bug.
2. **The `bg(t+theta)` lead reads into the cooling phase, not just off the end.**
   `profile_003` happens to end one sample after DROP, which hides this; any
   ordinary recorded roast continues down through cooling, and inverting that fall
   rails the base to the floor over *exactly* the last `theta` seconds of the
   roast. The window therefore ends at `timeindex[6]`, and the background is
   **blended** into its own terminal RoR fit over `--tail-window` rather than
   butt-joined to it: `dbg/dt` is divided by `a`, so a 0.005 degC/s kink at the
   seam is a 1 degC step in the base. Blending took the schedule from 10 events to
   7 and removed a 1.5 degC bump 14 s before DROP.
3. **The tolerance has a floor at ~0.5 degC of base and it is quantisation.** The
   knot chooser measures the residual of the *quantised, index-snapped* polyline,
   so at a knot the error is the whole-degree rounding. `--tol 0.3` therefore
   stops early and says so. § above is right that this does not matter
   (0.5 degC → 0.0024 degC/s of BT rate); what is worth having is that the number
   the tool reports is a promise about the delivered schedule.
4. **`--dip` is a real choice and the default is not what was simulated.** Raw
   `ff` at CHARGE on `profile_003` is **-432 degC** — the background falls at
   3.5 degC/s through the dip and `/a` multiplies it by 204. `dip_strategies.py`
   clipped that to `[120, 300]`, so the FF-trim rows in the table above describe a
   base that **dives to the floor and climbs back out**. The operator's choice
   (2026-09-06) is instead to back-extrapolate the ramp to CHARGE, which on
   `profile_003` is a nearly flat **198.7 → 200.9 degC**, leaving the whole dip
   excursion to the trim. `--dip follow` reproduces the simulated variant. **The
   two differ by ~80 degC of base over the first 40 s and that difference has not
   been through the closed loop** — closing it is the first thing to do when step 9
   comes up the runbook.
5. **The base peaks at 256 degC, which eats half the positive trim range.** With
   `INLET_SV_MAX_C = 300` the effective setpoint clamps, so the top of the roast
   has only +44 of the +80 trim available. Not a problem at roast-46 duty (the trim
   sits mid-range by construction), but it is the reason the tool reports the base
   range, and it is a thing to watch if a hotter profile is authored.

The tool also refuses, rather than producing a plausible-looking file: a
background whose BT is blank between CHARGE and DROP (which is exactly what
`make_inlet_background.py --events` writes, and what makes it the wrong starting
point); a profile in Fahrenheit (event values are **not** unit-converted on
background load, `main.py:14474-14477`); a missing DROP mark (`timeindex[6] == 0`
disables the replay window entirely); a CHARGE index that is not a sample (such a
background replays from **START**, driving INLET through the preheat); and
pre-existing events of the target type without `--replace`. It round-trips the
`external → internal → external` encoding on the file it just wrote before
reporting success.

**Still not built, and still gated on steps 3-5**: the `.aset` half — the trim
slider (`INLET TRIM` on slider 2 with `slideroffsets` -80 over a 0-160 range,
`pidPositiveTarget = 2`) and `specialeventplayback`/`...ramp` enabled for event
type 2 alone. And the closed-loop check of the emitted file, which is what would
settle item 4 above.

#### Ruled out, so they are not proposed again

| approach | verdict |
|---|---|
| dose the integrator at handover (short high-`Ki` burst) | overshoots 10-30 s on `dt150`; the loop is short of anticipation, not integral |
| temporary large `svLookahead` over 1:30-3:00 | same failure, same direction |
| **relative setpoint** — `INLET = BT + trim`, the PID commanding a lead over BT | **worse, for a principled reason**: it converts the plant from a self-regulating first-order lag into an *integrator* with 13.5 s of delay, so the standing ramp error moves from integrator-rate-limited to gain-limited and the delay caps the gain. Best steady rms 1.17 against 0.24; `worst` +12 to +18. Feedforward on a *known* trajectory (above) gets the same structural benefit with none of it |
| widen/narrow `positiveTargetMin/Max` to shrink the integrator's swing | pure reparameterisation — the map rescales `Kp` and `Ki` together in physical units, so `e_ss = (dI/dt)/Ki` is invariant. No free lunch — **but read the next row before citing this to refuse a floor change** |
| lower `positiveTargetMin` **to add authority** *(not the same thing)* | **not** a reparameterisation, and this entry was misread as forbidding it for four roasts. When the loop is *saturated* the gain argument does not apply: roast 54 sat 36 s at `SV = 140` with the heater still at **46%**, unable to act on a bed above the background. Lowering the floor and scaling `Kp`/`Ki` by `160/(max-min)` holds `dSV/derror` **exactly** and changes behaviour only where the old config was clamped. The cost is that `Iterm` must carry a larger operating point (20.2 rather than 0.3 to hold the preheat's 140.4), which the preheat builds — so **a short preheat now starts the roast cold** |
| `PIDoff` at CHARGE / `PIDon` at 1:30 (freeze at the preheat operating point) | `pidOn` does not reset `Iterm` (pid_control.py:1521-1527), so it is mechanically sound and gives `I@1:30` spread 0.8 — but the SV is frozen for 90 s, and `dt150` swings **14.6 s** across the charge sweep. Open-loop where the disturbance is |
| `pidIRoC` (integral reset on large setpoint change) | inert here: the threshold is compared against the *per-sample* target change, which never exceeds ~5.5 degC even through the dip |
| `pidIlimitFactor` < 1 to bound windup instead of freezing it | fatal on its own — the ramp needs `I` ≈ 63 and the cap is global. Becomes usable only under the FF trim, where `I` stays near 50 |
| lower `Kp` through the dip | already ruled out in state-history-cascade.md § The dip is a different control problem (handover spread 91.5); `beta < 1` via `pidWeights()` is the same move on the target path and no better |
| the fan as a second actuator in the dip | not needed, and the operator now holds it constant deliberately; the ~0.99 %heat/fan-unit sensitivity is a loss-term effect, which the FF schedule and the trim both absorb |

#### The one adaptive idea that is still open, and costs nothing to keep

`(CHARGE_BT - BT at CHARGE+13 s) / mass` is a **free, control-independent proxy
for the charge state** (state-history-cascade.md § Charge temperature) and it is
available at 13 s — well before any handover. Artisan can act on it without a
new process step: an alarm *from CHARGE, offset 13 s, source BT, below/above a
threshold* can fire `loadBackground(<path>)` (main.py:10879),
`moveBackground(<dir>,<step>)` (main.py:10923), `alarmset(<n>)` (main.py:10898)
or `palette(<n>)` (main.py:10863) — so a whole tuning set or background can be
selected on the measured charge state. **Do not build this yet.** It is the
fallback if the FF trim leaves a charge-dependent residual worth chasing; on the
present numbers it would be chasing 1.6 s.

### Open firmware ideas

*Neither is scheduled. The v0.19.0 items that came out of the same discussion
are built and are recorded in state-history-cascade.md § Firmware now in scope.*

#### The one big idea, gated on the characterisation runs

**Publish a *predicted* BT as an extra channel and point the PID at it.** The
loop is deadtime-limited — margin ~30 deg at Ki 0.07 solely because of theta —
and a Smith predictor is the standard answer. It does **not** require moving the
outer loop into firmware: the firmware can run the identified model forward from
the measured inlet and publish `BTP`, and Artisan's `pidSource` can select that
extra channel instead of BT (the PID input list offers exactly the extra device
channels, pid_dialogs.py:1251-1258). The loop then sees a fraction of the
deadtime and Ki could rise several-fold at the same margin.

Two conditions before attempting it:

1. **Trustworthy theta, tau and gain.** The current values come from a flat
   ridge (state-history-cascade.md § Scheduling) and are not good enough to predict
   with. Run Tests A and B first.
2. **A bound on the correction.** Clamp `|BTP - BT|` to something like 10 degC so
   a diverging model degrades to plain BT rather than running the roaster open
   loop on a wrong prediction.

**Not worth doing: moving the outer loop into firmware.** The only reason would
be to enable the predictor, and the channel route achieves that without it. The
1 Hz WebSocket link is not a limitation — 1 s against 17 s of deadtime — and the
background curve authoring belongs in Artisan's Designer.

#### Normalize the charge with the PREHEAT — WITHDRAWN, and moved

Proposed 2026-09-08, withdrawn the same day by roast 57: the lever rests on
`d(TP)/d(preheat) ≈ 0.415` and the measurement is **0.100**, so a 10 degC bean
swing would need 60 degC of preheat. The full design and — more usefully — the
reason it failed are in state-history-residual.md § Normalize the charge with the
PREHEAT. **Do not rebuild it from that section**; see state-current.md § 6.
#### Measure the charge temperature instead of inferring it (operator, 2026-09-06)

**Charge with the fan off, read the incoming bean temperature off the BT probe's
cooling curve, then start the fan to loft the bed and begin profiling.** The
system is already preheated, so the beans are not scorched while they are being
measured, and the probe starts from a known temperature — the preheat BT, ~129
degC — so the *shape* of the fall carries the bean temperature without waiting
for equilibrium. Once enough of the curve has been observed, the fan starts and
the roast begins.

**Why this is worth more than it looks.** `greens_temp` is `0.0` on every roast on
record, and the charge state has had to be inferred (state-history-cascade.md § Charge
temperature) — from the fall over 0-13 s per 100 g, which is only a *proxy*, and
one that has to assume the plant delay to be interpretable. Charge state is the
single largest source of run-to-run variation the strategy search found: it is
what the `Ki` gate was invented for, what makes the handover integrator matter,
and what § Step 9 has to be shown robust against. Measuring it directly turns a
sensitivity study into a known input.

**It also composes with something already required.** The fan has to be at ~64 to
loft a 400 g charge and cannot start at the ramp base anyway (§ Files for the
characterisation runs), so the charge already has a distinct fan phase. This
would make that phase carry information instead of only lofting the bed.

**What has to be settled before it is worth building.**

- **Is the probe reading beans or stagnant air?** With the fan off the bed is not
  circulating, so the heat path to the probe is contact and natural convection.
  If the probe is not buried in the bed the curve reads chamber air and the
  measurement is of the wrong thing. This is checkable on the bench in one
  charge with no roast attached: fan off, watch the BT fall, then loft and see
  whether the settled temperature is consistent with the extrapolation.
- **How long does it take, and what does the delay cost?** Every second with the
  fan off is a second the profile has not started and the chamber is cooling. The
  cascade's whole clock is CHARGE, so a variable-length measure phase moves the
  reference; either the phase is fixed-length or CHARGE is marked at loft rather
  than at the dump.
- **The heater must be off throughout**, which the interlock already enforces
  below fan 48 — so this is safe by construction rather than by new code, and
  that is worth keeping true.
- **The free proxy already exists.** `(CHARGE_BT - BT at CHARGE+13 s) / mass`
  costs no process change at all (§ The one adaptive idea). The new routine is
  better but not free; the honest comparison is *measured `greens_temp` versus
  the proxy on the same charges*, which the runs in the table can supply for
  nothing if `greens_temp` is filled in by hand each time.

**Not scheduled.** It is a firmware routine plus a change to how a roast starts,
and it sits behind step 9. But it is the first idea on this list that would
remove a variable rather than compensate for one.

#### Still wanted, independent of the control problem

**Instrument the dump lever** (already noted in § Auto-DROP detection): expose it
as an extra channel and alarm on it, turning DROP from an RoR-collapse inference
into a measured event. The RoR margin is currently ample but roast-dependent
(-10.4 to +5.4 across the armed windows seen so far), and DROP drives the whole
heat-off chain.

### Runbook — what is left

**One variable per roast.** Steps 1-8 are done; what they closed is in
state-history-cascade.md (roasts 46-49) and state-archive.md § Firmware v0.19.0
and v0.20.0. Two items remain.

| # | what | costs | files |
|---|---|---|---|
| **P** | **re-ask Phase B's question with the charge matched** — preheat fan 58, **CHARGE when `T_inlet` reads 141.8 ± 0.5**, step fan 58 → 64 at −5 s, fan 64 held for the roast. Background and `.aset` unchanged. Reproduces roast 56's charge on both variables; the only change against 56 is the fan step. **Unscored unless the 85-115 s entry slope is inside ±2 degC/min** | 1 real batch | `..._phaseB.aset` + `profile_400g_m5C_v4.alog` |
| **Q** | **the settled-fan preheat, as a deliberate one-variable change** — fan 64 from the start of the preheat, `T_inlet` fixed at 141.8, CHARGE when BT flat 2 min. Measures the settled precharge-inlet gain and retires the fan-step burst | 1 real batch, after P | same |
| **L** | **the latent-heat term** in `make_background.py`'s RoR spec. **Gated on P** — the RoR family is smooth-by-construction with four parameters pinned by four constraints, so this is a fifth shape term, and it must be sized on a roast that entered the window flat. (`--h-fus` is heat of *fusion* in the charge dip, a different quantity.) | authoring + 1 batch to score | `make_background.py` |
| **9** | **step 9** — the FF base schedule with the PID as a trim (§ Step 9). Gated on the `.aset` half and the `--dip` question, not on more roasts | 1 real batch | new |

**B is done** (roast 60, 2026-09-13) and it ruled out the fan as the whole
cause — but its own preheat drifted off spec and cost it the measurement, so
**P comes first and L is gated on it.** P reproduces roast 56's charge rather
than adopting the new preheat spec, because roast 56's is the only configuration
with a *demonstrated* flat entry and the residual question has been blocked for
five roasts; Q adopts the spec once the residual is settled. P changes nothing but the preheat, and
it also reads the precharge-inlet gain for free: roast 60 put it at **0.94 degC
of TP per degC of inlet** against preheat BT's 0.100, while the dip model has
those two at 0.13 and 0.28 — the model has the ordering backwards, which is why
P reproduces a measured preheat point rather than authoring for a new one.

**Steps 1b (profile_004) and 1c (the `Ki` gate) are not scheduled and should not
be run.** Over the *reachable* — warm-side — charge range the gate makes every
metric worse than the lookahead alone (worst error +5.79 against −4.01, steady
rms 0.38 against 0.26, `dt150` spread 4.2 s against 0.4), and both are
rearranging a burden step 9 removes. If the gate is ever wanted, build it from
Artisan's **native gain scheduling** (`Ki` 0 → 0.07 across BT 70 → 95,
pid.py:370-386, persisted in the `.aset`) rather than two timed alarms — same
gate, no missed-alarm P-only failure mode, no sticky-`p-i-d()` trap, worst error
+2.95. Detail: state-history-cascade.md § Dip strategies.

**Do this on every roast, it costs nothing: enter `greens_temp` and
`moisture_greens`, and weigh in and out.** Four roasts ran at `0.0` and their
charge state had to be inferred rather than read.

**Why every characterisation schedule is square waves and not smooth ramps.** A
smooth input cannot identify this plant, because a low-order `slow(t)` reproduces
the output exactly. Roast 20 ran a playback ramp and is the smoothest roast in
the archive; profiling its residual over `a` = 0.000…0.016 moves it **7 %,
monotone increasing**, so its best fit is `a = 0` — no plant at all. The same
profile on roast 46 has a sharp minimum at 0.0049 and swings 5× either side.
**Never read a plant number off a well-behaved roast, and never soften these
schedules to make them roast nicely** (state-history-residual.md § Roast 20
revisited).
### Specifications that came out of roasts 47-49

*The proposal these were written into — § What roasts 47-49 jointly say, 2026-09-06
— has been executed over roasts 50-56 and lives in state-history-cascade.md. What
follows is the part still in force.*
#### The fan step is timed, not hand-pressed

Also in the file: an alarm at **CHARGE+120 s** firing a hidden `Fan 60` button
(event type 0, value 7.0, the same `OT2` send the hand buttons use, so a replayed
step is indistinguishable from a pressed one). 2:00 is the quietest window in the
roast — the dip is long over, the 1:30 lookahead switch has settled (95% in 12 s
on roast 49) and DRY END is still ~60 s away. The plant has **no fan term**
(`kf = 0`, roast 48), so this moves the operating point and not the dynamics:
holding BT needs about **3.5 degC more inlet** at fan 60 than at 64.

#### autoCHARGE must be disarmed through the settle

The settle descends BT from ~185 degC (empty chamber at `INLET 200` sits ~10 degC
under the inlet) to 130. Artisan's autoCHARGE fires on a BT break of `d = -0.34`
degC per sample over two consecutive legs at `Delay=500` — **0.68 degC/s**, above
77 degC (canvas.py:5121, main.py:24306, params canvas.py:548). The empty-chamber
time constant is **40-50 s** (the charge-thermal test's reheat: BT 57 -> 129 at inlet ~235 gives
`a ~ 0.02 /s`), so a 55 degC descent runs at **1.1-1.3 degC/s** and trips it
within seconds. A gentler overshoot does not help: 30 degC gives 0.67 degC/s,
exactly on the boundary. **Disarm it; do not try to stay under the threshold.**

`autoCHARGE(<bool>)` is an **Artisan Command** (action 20, main.py:10286) and
sets `qmc.autoChargeFlag`; `autoDROP(<bool>)` is its sibling at :10298. **Alarms
cannot issue one** — their action list is 26 fixed entries and "Artisan Command"
is not among them (alarms.py:898) — so the route is alarm -> **Event Button** ->
command, the pattern `gen_pid_alarm_asets.py` already uses for the timed levers.
**`artisan/airRoaster_cascadePID_chargetemp.aset`** is that file: `lookahead`
unchanged, plus `autoCharge=false`, a visible `ARM CHG` button carrying
`autoCHARGE(1)`, and a backstop alarm (ON+960 s **and** BT < 131) pressing a
hidden twin. The temperature gate is what makes the backstop safe — BT crosses
131 about three time constants into the settle, drifting at ~0.02 degC/s.

**Trap:** `autoChargeFlag` is persisted as `autoCharge=` in the `.aset`, so a
*Save Settings while disarmed* bakes `autoCharge=false` into the file and the
next roast silently never marks CHARGE. Same sticky-config class as `p-i-d()`.
Re-load the file rather than saving over it.

**Then run the pair.** Two 400 g batches of the same lot, everything else held
identical, one straight from the freezer and one equilibrated at room
temperature for >= 12 h. Roast 49 is already a usable warm arm, so if only one
batch can be spared, **make it the frozen one** and pair it against roast 49 —
but a deliberate pair is worth much more, because roast 49's preheat was 28 degC
hotter than the group's and that had to be corrected for rather than avoided.

What has to be held fixed, and why each one:

- **`greens_temp` recorded on both.** Probe the bean mass, not the air, and enter
  it in Roast Properties. It is `0.0` on all of roasts 43-49, which is the only
  reason any of this is inference. This is the whole point of the run, and it is
  now the *only* thing standing between this project and a measured charge
  temperature under flow: `charge_state.py`'s `k`, roast 48's +12.8, roast 49's
  +15.5 and `charge_dip.py`'s `phi` all rest on roasts 43/44/46 having been at
  −18 degC, and nothing has yet tested that.
- **The preheat trajectory, not just CHARGE_BT.** Inlet air from
  `t in [-theta, 0]` arrives inside the mixing window, so a hotter preheat makes
  the beans look warmer. Hold the inlet flat within +-2 degC for 60 s before
  CHARGE on both.
- **Mass, to the gram.** The proxy is not linear in mass
  (`dBT = m*c*(BT_c - T_b)/(C_chamber + m*c)`), so a mass difference does not
  divide out.
- **Fan constant, as roast 49 already did**, and the same config and background
  (`airRoaster_cascadePID_lookahead.aset` + `profile_003`) so the run is also a
  second step-6 sample.

What it measures: `k` and `C_chamber` in the mixing model, and — the part no
existing run can give — whether the dip *shape* (depth, turning-point time, the
recovery slope out of it) is a function of the same variable, or whether bean
temperature moves more than one thing. `tools/analysis/charge_state.py` runs the
proxy and prints the band; `tools/analysis/charge_dip.py` now predicts the whole
0-90 s arc from `(mass, greens temp)` and is what this run would confirm or
break. It also carries the one open disagreement: the charge-thermal test's still-air fit wants
a fusion enthalpy and the roasts want none, and a pair with `greens_temp`
actually recorded is what separates `phi` from `h_fus`.

**Expect the warm run to roast differently, and let it.** Roast 49 finished with
a 19 s development window against roast 46's 25 s and the background's 26 s, at
the same DROP BT. If that difference survives a controlled pair it is a real
outturn consequence of charge state, not a tracking artefact, and it is the
argument for doing anything about the dip at all.

#### The dump-lever switch

**Yes — ground against a pin with `INPUT_PULLUP` is exactly right.** The ESP32-S3
has ~45 kOhm internal pull-ups, so `pinMode(pin, INPUT_PULLUP)` reads HIGH when
open and LOW when the lever closes it to GND. Specifics for this board:

- **Pin: GPIO 14 (A4).** From [hardware/pins.md](hardware/pins.md) § Free GPIOs.
  It avoids the ESP32-S3 strapping pins (0, 3, 45, 46 — none are on the free
  list anyway), leaves GPIO 38/39 for Serial1 and 42 for SPI SS, and keeps
  GPIO 5/6 (A8/A9) together for the planned BME688 pump driver.
- **Add an external 10 kOhm pull-up to 3V3** rather than relying on the internal
  one. A metre of wire to a mechanical switch beside two AC dimmers is an
  antenna, and this project has an EMI history worth respecting
  ([hardware/emi.md](hardware/emi.md)). A 100 nF capacitor across the switch
  terminals at the *board* end damps the rest. Route the wire away from the
  dimmer AC leads.
- **Debounce in firmware**, 20-50 ms, and act on the **edge** (open -> closed),
  not the level, so a lever left down does not re-trigger.
- **Publish it as `DL`** (0 or 1) in the `getData` reply beside `SV` and `HT`,
  and map it to `channel_nodes` slot 7 with `channel_modes` 0 (not a
  temperature). Then the DROP alarm becomes **Source = that channel, condition
  above 0.5, action DROP** — the same alarm mechanism as today, on a measured
  event instead of an inferred RoR collapse (§ Auto-DROP detection). Keep the
  RoR alarm as a backstop until the switch has proven itself over several roasts.

### Commissioning order

0. **Every roast: press ON (zeroes the integrator), turn the PID on, preheat
   under PID control, then CHARGE — one PID on/off cycle per monitor ON/OFF
   cycle.** ON is the only thing that clears Iterm; **RESET does not**, so cycle
   OFF -> ON between roasts rather than reusing a session (state-history-cascade.md §
   Roast 41). Preheating under the PID hands the roast an integrator already at
   the empty-roaster operating point (state-history-cascade.md § PID-driven preheat).
1. **Bench, heater cold.** Load `airRoaster_cascadePID.aset`. PID on -> confirm
   `INLET` traffic on the dashboard, that the commanded value floors at 140 and
   never reaches 0, that it carries a fraction, and that firmware `mode` reads
   `inlet`. Mark DROP -> confirm the existing button chain sends `INLET 0` and
   the firmware returns to `manual` at heat 0. Confirm no T_inlet playback
   traffic appears on the slider.
2. **First roast, conservative gains.** Watch for outer-loop overshoot and for
   the inner loop saturating (heat pinned at 0 or 100 for long stretches means
   the outer loop is asking for something unreachable).
3. Retune Kp/Ki from the log; only then consider Kd and `svLookahead`
   (currently 0; a few seconds of lead may help against thermal lag).

Optional tuning aid: `createEvents=true` records the commanded inlet SV into
the profile as events, which makes the outer loop's output reviewable
afterwards at the cost of a cluttered profile.

No bundled machine profile in Artisan's own `Machines/` directory does a
cascade: all 35 with a configured software PID target slider 4 (heat), the
Giesens included, even though they too put a temperature slider on 3. There is
no vendor precedent to copy here.

## Plant changes on the table (operator, 2026-09-08)

Four raised together. **None is scheduled and none should precede § TEST PLAN**,
which is measuring a 2.9 degC feature on the present plant. Each is recorded
with the measurement that would size it, because in every case the arithmetic
exists and the number does not.

### Smaller batches — 250 g, and lower

**It is already measured, and batch size is a much smaller perturbation than the
mass ratio suggests.** Roasts **37 and 38** (2026-08-23, Panama Elida, 450 g and
250 g) replayed the **identical inlet schedule** — the same eight `T_inlet`
events at the same times to within 1 s, same values — which makes them a
controlled mass pair. Regressing `dBT/dt` on the driving temperature
`Inlet − BT` over CHARGE+70 s to FCs−10 s gives the plant's gain
`k = h/(m·c + C)`:

| | roast 37 | roast 38 |
|---|---|---|
| charge | 450 g | 250 g |
| `k` (degC/s per degC of drive) | **0.01727** | **0.02095** |
| r² | 0.92 | 0.95 |
| ratio | — | **1.213** |

DRY END lands at 224 s and 186 s, an independent ratio of **1.204** on the same
pair. Solving `(450 + X)/(250 + X) = 1.213` gives **X ≈ 690 g of bean-equivalent
thermal mass that is not the beans** — the chamber, grate and drum riding in the
loop. Roast 38 also ran 3-6 fan units *lower* than roast 37, so it had less `h`,
which biases the ratio down: **690 g is an upper bound.**

**Consequence for 400 → 250 g:** `k` rises by `(400+690)/(250+690) = ` **1.16**,
so the excess-duty → RoR slope goes 2.66 → ~3.1 and the outer loop's gain wants
scaling by ~0.86. Even at half the parasitic mass it is only 1.33. **Batch size
is a 15-35 % gain change, not the 1.6× the mass ratio implies** — which is why
one roast at 250 g is enough to re-point the loop rather than a fresh
characterisation.

**161 g is below the floor, and the archive says so.** Roast 28 (161 g) fits the
same regression at r² **0.73** against 0.92-0.99 everywhere else, with a `k`
*below* the 250 g roasts — which a single-capacity model cannot produce. That is
consistent with the operator's reason for choosing 250 g as the minimum: below
it the bed no longer covers the probe while circulating and BT stops being a bed
temperature. One roast, so corroboration, not a measurement.

**The fan requirement does not fall with batch size — corrected 2026-09-09.**
Artisan stores event values as `level/10 + 1`; decoded correctly, the archive's
250 g roasts ran **fan 60 flat** (roasts 20, 21, 25, 29, 33), the same as the
400 g cascade roasts' sustain level, and the 161 g roast ran 59-60. That is the
expected result: the velocity needed to fluidise is a property of the *bean*, not
of how much of it is in the chamber — a smaller charge changes bed depth and so
pressure drop, not minimum fluidisation velocity. **So 250 g does not by itself
push the working point toward the interlock.**

What does is the declining-fan practice: roast 38 ramped to **54** and roast 37
to **53**, both under `ilFanFull = 55`, at and above which heat is unrestricted;
below it the soft interlock caps heat linearly down to `ilHeatAtMin = 30 %` at
`ilFanMin = 48`, and to zero below that (airRoaster.ino:107-112). **If a target
curve wants a declining fan, that cap is in the path** — move `ilFanFull`
deliberately rather than discovering it as a heat ceiling mid-roast.

**Authoring the curves is already solved; hitting DE and FC is a calibration.**
`make_inlet_background.py` takes `--t_dry --T_dry --t_fc --T_fc --t_drop
--T_drop` in `anchor` mode, so a curve that reaches chosen temperatures at
chosen times is one command. What that does *not* buy is DE and FC landing
there: they are bean events and BT is not bean temperature (§ Bean reference —
`C1043` cracks at **197.40**). Author the *times*, then move the target
*temperature* per lot until the event lands on them. That is the same discipline
§ Bean reference already runs, applied to a second milestone.

### Insulating the metal chamber (not the glass extension)

**View: worth doing, and one empty-chamber ladder is the whole re-characterisation
cost — but after § TEST PLAN, not before.**

What it buys, in this project's own numbers:

- **Headroom the profile work will want.** Post-DRYe RoR is linear in BT and
  crosses zero at **218.2 / 219.2** (roasts 56 / 57): at the duty the loop
  settles on and fan 60 the machine asymptotes to ~218 degC and the whole
  back-half RoR decay is first-order approach to it. That ceiling *is* the loss
  line. Insulation raises it, and any curve that asks for BT 210+ with RoR still
  on it needs that.
- **It shrinks the largest unmeasured roast-to-roast disturbance.** Roasts 56 and
  57 agree on the excess-duty slope (2.66 / 2.29) and disagree on the intercept
  (**0.81 vs 6.46**) across 4.6 degC of ambient. Loss to ambient carries that.
- **It flattens the plant's BT dependence.** `0.1922 %/degC` is the only
  self-regulating term in the plant; reducing it makes the open loop more nearly
  an integrator, so one set of gains works across the whole roast. That is the
  thing four floor retunes (120 → 170 → 140 → 100) and roast 54's 40 s of floor
  saturation have been fighting.
- **It should improve the `Inlet − BT` precision problem.** Phase 0's ±1.5 degC
  is the BT probe blending air with local metal on a many-minute time constant.
  Insulation raises the wall toward the air temperature, moving the contaminating
  term toward the thing being measured — which helps § Temp_Drive directly.

What it costs:

- **Every measured constant moves**: the duty line, the `ff` map coefficients
  (`ffC0/ffF/ffS/ffFS`, airRoaster.ino:360-380), the preheat equilibria, the
  278 s cooldown behaviour. All of it is re-measured by one ~60 min empty-chamber
  session — Phase A has now proven that is cheap, and `FF SET` / `FF SLOPE` mean
  a refit is a command, never a reflash.
- **Longer settling, slower cooldown.** Lower `UA` at unchanged `C` lengthens the
  metal's time constant, so preheat soak and between-batch turnaround both grow.
- **Less loss means a saturated-duty excursion goes further before it
  asymptotes.** The failsafe still drops heat to 0 and `INLET_OVERTEMP_C` is
  unchanged, but the margins deserve a look rather than an assumption.

**Sequencing.** Both candidate causes of the 140-200 s residual live in the loss
term. Insulating mid-investigation would force § TEST PLAN to restart.

### The leak upstream of the chamber

The operator's reading — a bypass that costs efficiency and moves the fan number
— is right about the steady state, and probably optimistic about two things.

**The offset is already in the firmware's map.**
`ff = 0.011423·(fan − 44.7)·(sv − 75.0) + 31.6`, fitted to roast 47's empty grid
at rms 0.68 %. **`fan − 44.7`** is the fan level at which the fit says effective
flow reaches zero, which is the shape a parallel leak produces. At fan 60 only
**15.3 of 60 units** are doing work — which is also why the fan gain is as strong
as it is (0.99 % heat per fan unit, empty and loaded agreeing).

**Fractional flow resolution does not improve by sealing it.** Sensitivity is
`1/(fan − f0)` per unit — 6.5 % per fan unit at fan 60 — and that depends on the
*effective* flow, not on where the offset sits. Sealing the leak moves the
working point down by about as much as it moves `f0`. On that axis the operator
is right: it is just a different number.

> **Measured 2026-09-13 and the premise does not hold.** The operator sealed the
> leaks mid-session on roast 61, inside a fan-58 rung: the settled `Inlet − BT`
> went **+8.58 → +8.29** and duty **43.27 → 43.23 %**, inside the ±0.5 scatter of
> a single rung, and the four post-seal rungs fit the pre-seal curve with no
> offset. Whatever was sealed is worth **under a fifth of a fan unit**. The
> arithmetic below is kept because it is the right arithmetic *if* a leak of that
> size is ever found; nothing here is now a reason to act.

**But the number moves toward the interlock, not away from it.** `ilFanFull = 55`,
`ilFanMin = 48`. A 400 g floor of 58-59 has ~4 units of margin today; sealing a
leak worth even ten fan units puts the 400 g working point under the cap and the
250 g working point well under it. **Sealing the leak and shrinking the batch
push the same direction.**

**And the leak is probably not constant.** A fixed orifice in parallel with the
bed splits by relative resistance, so the split moves whenever the bed's
resistance moves — mass loss, ~15 % expansion, chaff, and the fluidisation
hysteresis already on record (64 to start circulating, 60 to sustain). That turns
a static efficiency loss into a **time-varying flow disturbance**, which is the
shape of the thing § TEST PLAN is chasing at 140-200 s. It does not make the leak
the cause — Phase B's fan-64 roast was the test, and it left 1.69 degC standing
that the fan does not explain — but "it only changes the fan number" is the
optimistic case, not the certain one.

**The measurement.** Phase A's `TD = C/(fan − f0)` fit returns `f0` **empty**.
A loaded `f0` needs one deliberate fan step inside a roast, which `FF SLOPE`
already exists to consume. The difference between the two is the leak's
dependence on bed resistance, and it is the number that decides whether sealing
it is an efficiency job or a control job.

### Auto-DROP from the inlet spike

**Flown on roast 60 and it works** — state-history-residual.md § Phase B. Written
up in § Auto-DROP detection § The inlet spike beats the RoR collapse. Short
version: `Inlet − SV > 10` armed from DRY END fires **0.5-3.5 s
before** the DROP mark against the DeltaBT alarm's **6-7 s after**, with 4-8×
margin over the armed window — but roast 56's heat-off chain took 17.5 s to act
on a mark it already had, and that is the first thing to fix.

## Later / not scheduled

- **Vision module — camera-based fan trim for bean circulation** (idea opened
  2026-08-24). Fan setting isn't repeatable across beans/loads, but circulation
  quality is visually observable; a vision process would quantify it and send
  bounded `FANTRIM` adjustments over the authenticated WebSocket, with
  firmware-side clamp + timeout decay so vision is advisory, never fan
  authority. **Leading architecture: the Mac hosts it** — it already runs
  Artisan and the auth proxy every roast, which deletes the coprocessor, its
  power rail, its EMI cell, and any dev/deploy transfer risk; a Pi 5 stays on
  the shelf as the later path to a self-contained roaster. Firmware exposure is
  one command (`FANTRIM`, default off). Full plan, camera trade study, metric
  candidates, and phased rollout (observation → offline metric → camera
  decision → live display → advisory → closed loop): [vision.md](vision.md).
  Phase 0 (label clips from existing webcam/phone + synced telemetry) costs
  nothing and gates all spending. The gating unknown is manual exposure control
  on macOS (OpenCV's `CAP_PROP_EXPOSURE` no-ops on UVC webcams there); vision.md
  carries a **§ UVC probe procedure** — a runnable `uvcc`/libusb runbook that
  settles it on hardware already on hand before any purchase. Camera screening
  done: **Basler dart daA1440-220um** (IMX273, mono global shutter, 227 fps) is
  the pick — pylon/pypylon covers macOS Intel *and* Apple Silicon *and* Linux
  ARM, so one camera serves the current laptop, a future one, and an Option B
  Pi. Teledyne FLIR ruled out (macOS builds stuck at Mojave).
- **Evaluate moving the DimmerLink link from I2C back to UART serial.** The
  modules ship UART-by-default and were switched to I2C during provisioning
  (see [config.md](config.md) § 3); on this project's questionable wiring the
  serial link has looked *at least as noise-tolerant* as I2C. Worth a
  controlled comparison — if serial holds up, it may be the more robust
  transport here. Would touch the DimmerLink transport layer in
  `airRoaster.ino` (register reads/writes, `initDL`/`assertDLState`,
  boot sync) but not the control law; keep the commit-on-ack + re-assert
  robustness shape (v0.13). Cross-reference the EMI history in
  [hardware/emi.md](hardware/emi.md).
- **Auto-provision a fresh DimmerLink module in place (UART→I2C on the I2C
  pins).** A factory module ships on UART at the default I2C address `0x50`
  ([config.md](config.md) § 3); today that switch is a separate bench sketch.
  Idea: do it in-firmware without rewiring by temporarily driving the I2C pins
  (SDA `GPIO3` / SCL `GPIO4`) as a UART through the ESP32-S3 GPIO matrix. Flow:
  on boot (or a `DLPROVISION HEAT|FAN` command), if the expected address does
  not ACK, tear down `Wire`, bring a UART peripheral up on those pins, send
  `SWITCH_I2C` (`0x5B`), wait for the mode to persist, tear the UART down,
  `Wire.begin()`, write the target address to reg `0x30`, verify `VERSION`.
  Open questions to resolve first: (a) confirm the module's UART TX/RX land on
  the *same* two physical pins as its I2C SDA/SCL (the "two-bus" connector) —
  this is the crux; (b) confirm the DimmerLink UART baud/framing from the UART
  protocol docs; (c) collision — two fresh modules both answer `0x50`, so this
  only works with a single unaddressed module on the bus (provision one at a
  time, or before the second is wired); (d) safety — only with heat off and the
  boot heat-zero intact. Payoff: plug in a replacement dimmer and it
  self-provisions.
- **Data-driven device registry (add a device via a `.json` change) — all
  buses.** Make adding an *auxiliary* peripheral a config edit, not a code
  edit: a small JSON manifest of `{bus, addressing, type, role, options}` the
  firmware reads at boot to instantiate/parse the device. The idea is not
  I2C-specific — it applies the same way across **all three buses**, with the
  bus deciding the addressing field: I2C → device address, SPI → chip-select
  pin (+ SPI mode/clock), serial/UART → port + baud/framing. Candidate
  storage: a compiled-in JSON string, an NVS blob, or a LittleFS/SPIFFS file
  flashed with the firmware (or pushed from the dashboard). Scope guard: keep
  the **safety-critical core** devices (both dimmers, inlet TC, the RTDs)
  hardcoded and interlocked — the registry is for optional sensors first (the
  BME688 ambient below, an extra RTD, environmental sensors) whose presence and
  wiring vary. A full driver-plugin system is a large refactor; a lighter first
  cut is a table of *known* optional device types keyed by bus+address. Ties
  into the dimmer auto-provision above (address assignment) and the BME688 item
  below.
- **Cryptographic authentication of the command interface (safety/security).**
  **→ PROMOTED 2026-07-10: in development as v0.18.0 on `feature/auth-proxy`**
  (see state-current.md). The notes below are the original design record.
  Today the WebSocket server on `:81` accepts plaintext commands from anyone on
  the network — `OT1`/`OT2`/`INLET`, and the safety config (`IL`, `COOL`,
  `DLRESET`, `PID`, `FF`, `CURVE`, `AMB`). On a private WLAN the risk is low,
  but this drives a **heating element**, so an unauthenticated write path is the
  standing exposure. Goal: only authorized clients can issue state-changing
  commands. **The hard constraint is Artisan**: its WebSocket client speaks
  plain `ws://` with no auth header, token, or `wss` client-cert support, so
  mandatory auth would break the primary use. Design has to be layered:
  - Keep the *read* path (`getData`, telemetry, `LOG`, `STAT`) and the Artisan
    *slider* commands usable, and authenticate the privileged/mutating commands
    — or gate privileged commands to the dashboard only while Artisan keeps a
    reduced, network-trust-scoped surface.
  - Candidate mechanisms, lightest first: **HMAC-signed command envelope**
    (shared key + monotonic nonce/timestamp for replay protection) — cheap, no
    TLS handshake, fits the existing JSON envelope; **challenge–response
    session auth** on connect (device issues a nonce, client proves the shared
    key, session trusted thereafter); or full **`wss`/TLS** via mbedTLS (heavier
    on RAM/latency, and still doesn't solve Artisan). OTA already carries a
    shared password (`OTA_PASS`) — precedent for a secret in `secrets.h` + NVS.
  - Dashboard gotcha to verify early: the browser HMAC needs Web Crypto
    (`crypto.subtle`), which requires a **secure context** — `file://` and
    `localhost` qualify, but a dashboard served over `http://<lan-ip>` may not,
    which would block signing. Confirm before committing to a browser-HMAC
    design.
  - **Parked (2026-07-10, operator decision):** mandatory auth stays off the
    table for now because Artisan must keep sending commands or the setup
    doesn't work. The workable shape, if/when revisited, is a **localhost
    signing proxy**: Artisan connects to `ws://127.0.0.1:<port>` on the
    operator's machine (unauthenticated but localhost-bound), and the proxy
    holds the shared key and signs traffic to the roaster, which rejects
    unsigned writes. Artisan needs no changes beyond the Host field. The
    "laptop becomes the sole operator" concern is softer than it sounds:
    *keyed devices* are operators (any machine with the key can run the proxy;
    the dashboard could HMAC directly), and the Artisan machine is already the
    operator console — the proxy co-locates with it. What's lost is ad-hoc
    access from unkeyed devices; the fix is an unauthenticated **safe subset**
    in firmware — reads plus safety-increasing commands only (`OT1 0`,
    `INLET OFF`, `COOL ON`) — so anything on the network can still stop the
    roaster, never start it. **Operator-approved (2026-07-10): the safe subset
    is a requirement of any future auth design**, not an optional mitigation.
    A proxy crash mid-roast is no worse than
    Artisan crashing: the firmware failsafes are client-independent.
  - Open questions: which exact commands are "privileged" vs open; replay/nonce
    persistence across reboot; key provisioning + rotation; and whether to pair
    this with network-level isolation (roaster VLAN) as the pragmatic near-term
    mitigation while the crypto path is built.
- **OTA hardening beyond the dedicated password** (first-order fix shipped
  2026-07-11: `auth_key.py ota` generates a random `OTA_PASS`, closing the
  WIFI_PASS fallback where anyone on the WLAN could push firmware). Two
  further layers, deliberately deferred: (a) **OTA arming** — only call
  `ArduinoOTA.handle()` for ~5 min after an authenticated `OTA ARM` command
  (TIER_CONF or serial), so a push needs both secrets and accidental pushes
  are impossible; cheap (a flag + timeout + one command) and consistent with
  the existing idle gate — do this one first if OTA exposure ever worries us
  again. (b) **Signed images / ESP32 Secure Boot** — defends adversaries who
  already hold the passwords; Secure Boot burns irreversible eFuses and the
  ESP32 Arduino core lacks built-in update signing (unlike ESP8266), so this
  is real toolchain work for a threat beyond the stated LAN model. espota
  transport remains cleartext either way — key-bearing flashes stay on USB.
- ET RTD probe installation → set `RTD_ET_ENABLED 1` (sensor code is ready).
- BME688 ambient sensor on STEMMA QT (`0x76/0x77`) — would give a true room
  ambient for feedforward instead of the cold-junction estimate.
- DimmerLink curve-mode experiments: curve is set to RMS (mode 1) at
  startup; LINEAR/LOG untested.
- Move `controlStep()` to a pinned FreeRTOS task if `STAT` evidence (post
  Phase 2, when the metric is honest) ever shows the cooperative loop failing
  its cadence.
- String→char parsing in hot paths if heap fragmentation ever shows (low
  priority on the S3 with PSRAM).
