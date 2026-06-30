# Triac Dimmer Protection — airRoaster

Notes on protecting the RBDimmer 40 A AC dimmer modules against the failure
observed on the **fan channel** (triac failed closed / shorted, full output).
Covers snubber placement, MOV/TVS transient suppression, and the differences
between the inductive fan channel and the resistive heater channel.

Suggested location: `hardware/triac-protection.md`

---

## Background: the observed failure

- **Failed device:** fan-channel triac, failed **closed** (full output continuously).
- **Failed-closed (shorted)** is one of the most common triac failure modes;
  this was not a steady-state overload.
- **Load:** AMETEK-Lamb 116392-00 — 120 V, single-phase, **universal AC/DC**
  brushed motor, **8.6 A max**, **no motor thermal protection**, Class A
  insulation, **intermittent duty**, ~500 hr average life.
- **Dimmer:** RBDimmer 40 A module (rated "AC 600V-40A"), so ~5x steady-state
  current headroom. Current margin was **not** the problem.

### Likely causes, ranked

1. **Inrush / dI/dt at phase-controlled startup** (most likely). A two-stage
   universal motor draws a large locked-rotor surge (plausibly 6–10x the 8.6 A
   running current). Firing the triac at a non-zero phase angle into a cold,
   stalled rotor stacks high dI/dt onto that inrush.
2. **Brush-arc transients** (chronic degrader). Universal motors arc at the
   brushes continuously; fast spikes erode the triac over operating hours.
   "Fail closed" is how a fatigued triac typically dies.
3. **Inadequate triac cooling.** Hot triacs fail closed sooner. The module has a
   temperature sensor and expects the `rbpowerESP32` library to manage cooling —
   confirm active cooling is actually running.
4. **Snubber placement / tuning** (see below).

---

## 1. Snubber placement

### Fan channel (inductive — universal motor) — CHANGE THIS

Move the snubber to sit **across the triac main terminals (MT1–MT2)**, i.e.
between the dimmer's **input and output** terminals, **not** output-to-neutral.

- Across MT1–MT2 controls **commutating dV/dt** — the voltage step that appears
  across the device the instant it stops conducting and the inductive load
  forces current to keep flowing. This is the placement that protects the triac.
- Value the snubber for **this motor's inductance**, not a resistive load. A
  snubber tuned for a heater will not be right for the motor. Typical starting
  point ~100 Ω / 0.1 µF, but verify against the load.

### Heater channel (resistive) — OPTIONAL, low priority

A resistive element is near pure-resistive: current is ~in phase with voltage
and near zero at commutation, so there is little stored energy and the
commutating-dV/dt problem barely exists. Across-triac placement here is **not
wrong** (still helps with line-side dV/dt and cross-channel noise) but is **not
the targeted fix** it is for the motor.

- Caveat: a long / tightly-wound (coiled-coil) Nichrome element has some
  self-inductance — then an across-triac snubber is mildly beneficial.
- Recommendation: change only if trivial to do at the same time. The heater
  channel was almost certainly not the failure mode.

### Two snubbers (across-triac AND across-load)?

Marginal benefit; usually not worth it. The two positions overlap heavily —
with short internal wiring they are nearly in parallel for the commutation
transient, so a second snubber mostly just adds parallel capacitance. Genuinely
helps only when:

- **Long leads** between dimmer and motor (lead inductance separates the nodes;
  a snubber *at the motor* damps ringing the across-triac one can't reach). Does
  not apply to short roaster wiring.
- You are specifically chasing **load-side EMI** / conducted-radiated emissions.
- **Severe ringing** that one snubber can't be valued to damp. Rare at this scale.

If fan noise later shows up in thermocouple/RTD readings or the ESP32, an
across-load snubber or an X-cap at the motor becomes a reasonable EMC addition —
but that is a different goal than keeping the triac alive.

---

## 2. Transient suppression — MOV (primary) and TVS (optional)

### MOV (metal-oxide varistor) — the workhorse

Bidirectional, voltage-dependent resistor: high impedance below its clamp
threshold (effectively invisible), low impedance above it to shunt the surge.
Place **across the line, on the line side of the dimmer**, to clamp incoming
spikes before they reach the triac.

**Sizing rule:** pick the working voltage above the line *peak* with margin;
don't go higher than necessary or the clamp voltage rises and protection weakens.

| Line | MOV working voltage | V_nom (≈1 mA pt) | Example parts | Disc |
|------|--------------------|--------------------|----------------|------|
| 120 V (170 V pk) | **150 V RMS** | ~240 V | V150LA20A, 20D241K | 20 mm |
| 240 V (340 V pk) | **275 V RMS** | ~430–470 V | V275LA20A, 20D431K | 20 mm |

- **Use a 20 mm disc** (not 14 mm), especially at 240 V — more joules, more surge
  current, lower clamp, longer life.
- **Check the clamping voltage (V_C).** This is the voltage the triac actually
  sees during a surge; it must sit **comfortably below the triac's V_DRM**
  (600–800 V class).
  - **240 V concern:** a 275 V-RMS MOV clamps high (~700–775 V max). Against a
    **600 V** triac this may not clamp below V_DRM. Use a larger disc (lower
    V_C), and/or rely on the snubber as primary commutation defense with the MOV
    as bulk-surge backup. **An 800 V triac gives comfortable margin.**
- **MOVs fail shorted** and degrade with each surge. Use a **thermally-protected
  MOV (TMOV)** or an **upstream fuse** so a failed MOV can't sustain an arc.
  Good practice at 120 V; closer to mandatory at 240 V.

### TVS (transient voltage suppressor) diode — optional, fast residual

Silicon avalanche device: sub-ns response, tighter clamp, but **far lower energy
capacity** than an MOV. For AC mains use a **bidirectional** TVS (or two
back-to-back unidirectional). On its own it cannot absorb a real mains surge —
it will vaporize.

- Role: catch the **fast, low-energy** transients an MOV is too slow/soft for —
  e.g. the **brush-arc spikes** from the universal fan motor.
- A TVS is **not a substitute** for the MOV (speed vs. energy — different jobs).
- Robust hybrid: **MOV across line** (bulk energy) → small series impedance (a
  few Ω, or wiring inductance) → **TVS near the triac** (fast residual).

---

## 3. 240 V split-phase specifics (US, L1 / L2)

The heater is across **L1–L2** (each leg 120 V to neutral, 180° apart, 240 V
line-to-line; neutral not in the load path).

**MOV value across L1–L2 is unchanged: 275 V RMS, 20 mm, thermally protected.**
This catches **differential** (line-to-line) surges and protects the triac from
differential/commutation events.

**Add leg-to-ground MOVs (the "full" three-MOV split-phase config):**

| Position | MOV | Catches |
|----------|-----|---------|
| L1–L2 | 275 V RMS | differential-mode (line-to-line) |
| L1–G  | 150 V RMS | common-mode |
| L2–G  | 150 V RMS | common-mode |

- Because each leg is only 120 V to ground, the leg-to-ground parts can be the
  lower-clamping **150 V** MOVs (~400–500 V clamp vs. 700+ V for the 275 V part).
  On **common-mode** surges (both legs swinging together vs. ground — typical of
  externally-coupled / lightning-induced transients) the triac then sees a much
  lower clamp. This partly rescues the 275 V-vs-600 V-triac clamp-margin concern.
- **Requires a solid chassis/earth ground** at the dimmer. If the ground is
  floating or poor, the leg-to-ground MOVs are useless or worse (can lift the
  chassis during a surge).
- **TMOV / per-leg fusing matters most here:** a degraded leg-to-ground MOV
  shorts a hot leg to chassis ground — a shock/fire hazard. Not optional.
- **Keep the L1–L2 MOV** regardless — it does the heaviest differential lifting.

---

## Action checklist

**Fan channel (do these):**
- [ ] Relocate snubber to **across MT1–MT2**, valued for the motor's inductance.
- [ ] Add **firmware soft-start** — ramp the dimmer up from zero rather than
      snapping to a setpoint mid-waveform (addresses the #1 likely cause).
- [ ] Add a **150 V-RMS, 20 mm, fused/TMOV** across the line (line side).
- [ ] Confirm the module's **active cooling** (`rbpowerESP32`) is running.
- [ ] Log **RMS current** via the module's current sensor at real roast
      conduction angles to confirm margin to thermal limits.
- [ ] (Optional) Bidirectional **TVS across the triac** if brush transients
      remain a problem after the above.

**Heater channel (240 V split-phase):**
- [ ] **275 V-RMS, 20 mm, fused/TMOV** across **L1–L2** (line side). Must-have.
- [ ] **Two 150 V-RMS leg-to-ground MOVs** (L1–G, L2–G) **iff** solid chassis
      ground — improves common-mode clamping and clamp-vs-V_DRM margin.
- [ ] Snubber across MT1–MT2 — optional (resistive load); change only if trivial.

**Still to confirm (closes the clamp-margin question):**
- [ ] Read the **triac part marking** off each module to get its actual
      **V_DRM (600 vs 800 V)** and **ITSM / I²t** surge ratings. If 600 V, the
      leg-to-ground MOVs become more valuable, not less. If you can get the
      part number + the fan's measured inrush, the startup-surge theory can be
      checked directly.
