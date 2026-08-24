# Power — 5 V rail budget

The low-voltage system's supply architecture and its current budget, including
planned hardware. Referenced from [pins.md](pins.md) and the BME688 plan in
[../state-plan.md](../state-plan.md) § PLANNED.

---

## Architecture

- **12 V** enters on the mains side of the enclosure divider.
- A **RECOM R-78W-0.5** (12 V → 5 V switcher, **500 mA rated**) sits below the
  divider; only the filtered 5 V crosses to the low-voltage section
  (see [emi.md](emi.md) § Supply side for the relocation rationale and the
  decoupling-cap status).
- The **ESP32-S3 Feather's onboard 3.3 V LDO** hangs off the 5 V rail and feeds
  the OLED, both MAX31865s, the MAX31855, and (planned) the BME688. Being
  linear, it passes current through ~1:1, so 3.3 V loads count directly against
  the 5 V budget.

## Budget — as configured (2026-07-12)

| Load | Typical | Worst case | Basis |
|------|---------|------------|-------|
| 2× dimmer heatsink fans (5 V, 0.2 A each) | 400 mA | ~2× at spin-up | operator-confirmed; direct-wired to 5 V, always on (bypasses the modules' fan-management headers) |
| ESP32-S3 Feather, WiFi active | 100–130 mA | ~350–450 mA TX bursts (ms-scale) | Espressif S3 datasheet |
| 2× DimmerLink controllers + dimmer-board logic | 30–60 mA | gate pulses each half-cycle | estimate; RBDimmer publishes no electrical specs |
| SH1107 OLED (via 3.3 V) | 5–10 mA | ~15 mA all-pixels | typical 1.1" OLED |
| 2× MAX31865 + PT1000 VBIAS (via 3.3 V) | ~5 mA | ~8 mA | datasheet |
| MAX31855 (via 3.3 V) | ~1 mA | — | datasheet |
| **Total** | **~545–610 mA** | **~0.9–1.0 A coincident** | |

**The as-configured system already exceeds the R-78W-0.5's 500 mA rating**
(~110–120 % continuous) — and because the fans are direct-wired and always on,
it does so **whenever the system is powered**, not just under load. Any added
draw (a WiFi TX burst) pushes further past rating; if the converter
current-limits, the rail droops and the ESP32 brownout-resets. The boot-time
dimmer sync makes that failure *safe* (heat forced to 0, fan restored from the
RTC shadow) but it disrupts the roast and presents as an unexplained reboot.

## Budget — with planned hardware

| Planned load | Typical | Notes |
|--------------|---------|-------|
| BME688 (gas heater off) | <1 mA | via 3.3 V / STEMMA QT; negligible |
| **Air pump** — Adafruit 4699 (ZR370-02PM), 4.5 V nominal / 5 V, 2.5 LPM | **~500 mA while running** | brushed DC motor: expect ~2× inrush at start; rated duty ~50 % (10 s on / 5 s off, 30 k cycles) |

The pump accompanies the BME688 (sampled airflow across the sensor — see
[../state-plan.md](../state-plan.md) § PLANNED — BME688). With it running the
rail needs **~1.05–1.11 A continuous, ~1.4 A worst-case coincident** — more
than double the present converter's rating.

## Decided architecture — two rails (2026-07-12)

Re-plan the 5 V system **before the pump lands** as a clean electronics rail
plus a "dirty" motor branch, both fed from the 12 V bus below the divider:

| Rail | Converter | Loads | Continuous | Worst case |
|------|-----------|-------|-----------|------------|
| **Clean** (electronics) | existing R-78W-0.5 (500 mA) | ESP32 Feather (+3.3 V loads: OLED, 2× MAX31865, MAX31855, BME688), DimmerLink logic | ~150–210 mA | ~0.5 A ms-scale WiFi TX bursts |
| **Dirty** (motors) | RECOM **R-78B5.0-2.0** (2 A, 6.5–18 V in, SIP-3) | air pump (~500 mA run, ~1 A brushed inrush), 2× dimmer fans (400 mA) | ~900 mA | ~1.4 A at pump start |

Notes:

- The fans are **direct-wired to 5 V and always on** (operator decision — they
  bypass the dimmer modules' temperature-managed fan headers), so they move to
  the motor branch freely; always-on heatsink cooling on a roaster is a
  reasonable trade. This takes their commutation noise off the sensor rail
  along with the pump's brush noise.
- **DimmerLink logic stays on the clean rail.** It shares the I2C bus with the
  OLED (and future BME688), and the v0.13 register-read misbehavior
  ([emi.md](emi.md)) argues against feeding its logic from a rail carrying
  motor noise.
- Clean-rail margin: WiFi TX bursts (~0.35–0.45 A, ms-scale) on top of the
  ~0.2 A base briefly approach the R-78W-0.5's rating — expected to ride on
  the output/point-of-load caps (emi.md item 8). If unexplained brownout
  resets appear, upgrade the clean rail to **R-78E5.0-1.0** (1 A, 7–28 V in).
  E-family vs. the branch's B-family also keeps the two converters' nominal
  switching frequencies apart (see rationale below).
- Pump start transients (every ~15 s under duty-cycled sampling) are confined
  to the branch. The pump still needs its MOSFET low-side switch + flyback
  diode on a free GPIO ([pins.md](pins.md) § Free GPIOs).

### Branched vs. one larger converter — rationale (2026-07-12)

Considered and decided in favor of the **branched design** for the motor loads
(pump + fans), despite the known downside of dual switchers.

**The downside, honestly stated: beat frequency.** Two converters at
nearly-equal switching frequencies (R-78 family parts all run in the same
few-hundred-kHz region, and fsw drifts with load/temperature) mix on shared
impedance — mainly the common 12 V input bus, plus near-field coupling if
mounted adjacent. The difference product can land anywhere from sub-Hz to tens
of kHz — inside the RTD measurement band — and it wanders. Why this is
second-order here:

- The coupling path is the shared 12 V input, and that is filterable:
  per-converter input filtering (ferrite or small LC + a *separate* local
  input bulk cap for each converter — do not share one) drops the mixing
  amplitude to µV scale. This extends [emi.md](emi.md) item 8.
- The MAX31865 measurement is ratiometric (RTD and Rref see the same bias), so
  supply ripple cancels to first order; the noise floor is set by triac
  phase-cut transients and brush arcing, which dwarf a filtered converter beat.
- The board already hosts two triacs and two managed fan controllers — one
  more small, filtered switcher is marginal against the existing spectrum.

**Why one larger shared regulator is worse than it looks:**

- The pump is duty-cycled by design (~10 s on / 5 s off): on a shared rail
  that is a repetitive ±500 mA load step — droop and recovery at the cadence
  of sampling, conducted straight into the rail the Feather's LDO feeds. A
  periodic load step cannot be filtered the way input ripple can.
- Brush arcing is broadband (kHz–MHz, hundreds of mV) injected on the *output*
  side, where only the LDO's mediocre HF PSRR shields the 3.3 V sensors. On
  the branched design that noise must fight backward through the pump's own
  converter and the input filters to reach the sensor rail.

The branch is therefore a **noise partition**, not just ampacity: pump + fans +
converter become one quarantined motor cell on the mains side, and the
interaction surface shrinks to a filterable 12 V bus. Design notes for the build:
physically separate the two converters; give each its own local input cap; and
optionally pick the pump's converter from a different family so nominal
switching frequencies sit well apart (biases the beat above the sensor band —
imperfect, since fsw drifts, but favorable odds).

Rejected outright: **linear 12→5 V** for the pump (3.5 W of heat at 0.5 A) and
**PWM-ing the motor directly from 12 V** (overdrives peak current, eats
brushes).

Whatever the choice, keep the point-of-load decoupling plan from
[emi.md](emi.md) § Capacitor summary in force on the sensor side.
