# state-archive — completed work and standing findings

> Companion to [state-current.md](state-current.md) and [state-plan.md](state-plan.md).
> Newest entries first. This file is the durable record: review findings keep
> their F-numbers here even after the fixes land, so plan/commit references
> stay resolvable.

## 2026-07-02 — Heat power linearization + CURVE command (v0.11.0)

Follow-on from the fan-sensitivity discussion. Two findings first: the firmware
has always run curve mode 1 = **RMS** (not linear, as assumed), and of the three
DimmerLink curves (0=linear-in-firing-angle, 1=linear-in-Vrms, 2=LED-log) RMS is
already the best for the fan's mid-scale operating band — LINEAR is steepest
mid-scale (worse resolution there) and LOG spends resolution below the motor's
stall threshold. The narrow fan band is motor+blower physics, not a curve
artifact; the level register is integer 0–100, so 1 count is the hardware
quantum regardless of curve. Also v0.10.1: DUTY_STEP 5 → 1 (single-percent
UP/DOWN nudges).

What landed in v0.11.0:
- **Heat % now means % of max power.** On the RMS curve P ∝ level², so the
  commanded heat passes through `heatDimmerLevel()` (√ map) at the hardware
  write boundary. All firmware state — PID, FF, interlock, tune buffers,
  telemetry, display — stays in command/power units; only `setLevel` writes and
  the readback-audit/reset paths translate. Constant plant gain across the
  range; the feedforward's heat ∝ power assumption now actually holds.
  **Re-TUNE + FF CAL required** — pre-v0.11.0 gains/ffK are in dimmer units.
- **CURVE command** (report / `CURVE HEAT|FAN 0..2`), runtime-only by design:
  power-on default returns to RMS so a curve experiment can never survive a
  reboot into a roast. Module resets/audits re-assert the *active* curve
  (`curveFor()`), not a hardcoded one. The heat power map disables itself on
  non-RMS curves (mapping unknown there). Dashboard gained a Curves group
  (selectors + heatPowerMap indicator). Serves the work.md "test dimmerlink
  curves" item.
- Gotcha recorded: Arduino's preprocessor inserts auto-prototypes before the
  *first function definition* in the sketch — defining helper functions up in
  the state section broke the build (prototypes landed above struct
  definitions). Keep function bodies below the type definitions.

## 2026-07-02 — Runtime-configurable interlock (v0.10.0)

User-requested follow-on: interlock mode and limits configurable from the
dashboard, persisted like the tunings. `IL_FAN_MIN`/`IL_FAN_FULL`/
`IL_HEAT_AT_MIN` became runtime globals (`ilFanMin`/`ilFanFull`/`ilHeatAtMin`;
compile-time `*_DFLT` constants are first-boot defaults) stored in NVS
namespace `"interlock"` together with the hard/soft mode.

- **Breaking:** bare `IL` now *reports* (new `il` push:
  `{soft,fanMin,fanFull,heatAtMin,cap}`) instead of toggling; mode is set with
  `IL HARD`/`IL SOFT`, limits with `IL <fanMin> <fanFull> <heatAtMin>`.
- Validation on set **and** on NVS load (`1 ≤ fanMin ≤ fanFull ≤ 100`,
  `heatAtMin ≤ 100`); inconsistent stored data falls back to defaults with a
  logged error — a safety config must not weaken via a bad write. `fanMin ≥ 1`
  because 0 would let the heater run with the fan off. `fanFull == fanMin` is
  legal and degenerates to hard-style behavior (no div-by-zero: the `>=
  fanFull` check precedes the ramp).
- `loadInterlock()` runs before the boot dimmer sync so the first
  `applyInterlock()` uses the operator's limits; new limits apply immediately
  through `applyInterlock()`.
- Dashboard: Interlock panel (Hard/Soft buttons with active highlight, three
  limit fields, Set/Read), prefilled via `IL` on connect.

## 2026-07-02 — Robustness + dashboard implementation (phases 1–5)

All five phases from the review below landed on `feature/robustness-dashboard`,
one commit per phase; firmware v0.6.0 → v0.9.0 (per-version detail in the
`airRoaster.ino` history block). Compile-verified only — **on-roaster
validation is the open next step** (checklist in state-plan.md § NEXT).

- **v0.7.0** safety: boot dimmer sync (heat zeroed, fan level adopted), inlet
  stale-PV/over-temp failsafe (drop to manual at heat 0), commit-on-ack dimmer
  writes + 5 s readback audit, task watchdog (8 s). → F1 F3 F6 F8
- **v0.8.0** sensor path: `max31865_direct.h` register-level driver, true
  continuous mode (~150 ms/cycle of blocking removed), on-chip thresholds
  armed, per-sample fault bit, meaningful stall-guard re-assert, `loopMaxUs`
  in STAT. → F2 F10
- **v0.9.0** protocol: strict numeric parsing with error replies, float-
  preserving JSON envelope, bounded WiFi boot + loop-side reconnect, tune
  `settled` flag, DimmerLink version log / rate-limited error poll / soft-reset
  escalation, no-arg `FF AMB` from cold junction, `telem` push + `TELEM`
  command. → F4 F5 F7 F9
- **Dashboard** rebuilt single-file: status/temperature panels, canvas tuning
  chart with CSV export, PID/FF/TUNE workflow (tight + cons apply, settled
  warning), timestamped filterable console with save-to-file (the durable log),
  auto-reconnect. Element-ID/function cross-check passed; JS syntax verified.
- **Docs**: README brought current (interlock constants, startup sequence,
  new commands, telem schema, failsafe, dependencies note), emi.md addendum on
  the library one-shot discovery and what to watch in the next roast's fault
  log.

Design decisions worth remembering:
- Failsafe action is **heat 0**, not hold: with an untrusted PV, holding heat
  unattended can overheat; fan keeps running because airflow only cools.
- Boot sync **adopts** the fan level rather than zeroing it, so a mid-roast
  MCU reset keeps cooling airflow on a hot roaster.
- In-window RTD samples are accepted even with the fault bit set (per the
  standing EMI policy), but the latch is then cleared so the bit stays fresh.
- The DimmerLink COMMAND reset values came from the vendor doc (RESET=0x01);
  power-on level default is undocumented, which is why boot sync exists.

## 2026-07-02 — Code review (firmware + dashboard) and datasheet verification

Review of firmware v0.6.0 and dashboard against the installed libraries
(Adafruit_MAX31865 1.6.2, Adafruit_MAX31855 1.4.2, WebSockets 2.7.2), the
MAX31865/MAX31855 datasheets (hardware/), and the DimmerLink I2C protocol doc.
Branch `feature/robustness-dashboard` created for the resulting work.

### Findings

- **F1 (safety, critical): dimmer levels not synced at boot.** After an
  MCU-only reset the DimmerLink modules hold their last levels (power-on
  default undocumented) while firmware state boots at heat=0/fan=0;
  `applyInterlock()` writes only on change, so a heater left at 70 % stays on
  with the OLED showing `Heat: 0`. → Phase 1.
- **F2 (efficiency + design, critical): Adafruit_MAX31865 `temperature()` is a
  blocking one-shot.** `readRTD()` = `clearFault()` + bias on + `delay(10)` +
  1-shot + `delay(65)` + read + **bias off**. Two reads per `serviceRtd()` =
  ~150 ms blocked per 250 ms cycle (~300 ms once ET is enabled). Side effects:
  the firmware's `autoConvert(true)` + VBIAS re-assert design never actually
  operates; between polls the chip free-runs conversions *unbiased* (a
  plausible contributor to spurious `0x60` faults); `clearFault()` inside the
  read destroys fault evidence; `readFault()`'s default argument runs a
  master-initiated fault-detection cycle that drops the chip out of auto mode.
  → Phase 2 (direct-register driver).
- **F3 (safety): no sensor-fault/over-temp guard in `MODE_INLET`.**
  Hold-last-good + closed loop = integrator winds against a frozen PV. TUNE
  has a 280 °C abort; INLET has nothing. → Phase 1.
- **F4: garbage command args parse as 0** (`OT1 x` → heat 0; `INLET abc` →
  closed loop at SV 0; `PID a b c` → zero gains persisted to NVS). → Phase 3.
- **F5: JSON envelope int-rounds `value`**, quantizing Artisan's ramped INLET
  playback to 1 °C steps. → Phase 3.
- **F6: `setLevel()` returns are ignored**; an I2C NACK on "heat 0" leaves
  firmware believing a level the hardware never received. → Phase 1.
- **F7: WiFi blocks boot forever; no reconnect management.** → Phase 3.
- **F8: no task watchdog** (heater controller, cooperative loop). → Phase 1.
- **F9: unused peripheral capabilities**: DimmerLink COMMAND reg 0x01
  (RESET=0x01, RECALIBRATE=0x02), VERSION reg 0x03, `getLevel()` readback;
  MAX31865 on-chip fault thresholds (disarmed at POR values) and per-sample
  RTD-LSB fault bit; MAX31855 `readInternal()` cold-junction temp as an
  FF-ambient estimate. → Phases 1–3.
- **F10: `STAT` jitter metric is blind to in-pass blocking** (`now` captured at
  loop top; sensor block and control step share the pass), so it reported
  single-digit ms while the loop stalled 150 ms/cycle. → Phase 2 (loopMaxUs).
- **F11: README drift**: interlock constants (README 23/30 vs code 48/55),
  dashboard path (`artisan/` vs repo root), stale "BT/ET stubbed" paragraph.
  → Phase 5.
- **F12 (noted, unscheduled): String-heavy parsing in hot paths** — heap churn
  acceptable on the S3 with PSRAM; revisit only on evidence.
- **Tune fit trust**: a 180 s-timeout fit on an unsettled response
  underestimates dT → overestimates gains; result should carry a `settled`
  flag. → Phase 3.

### Datasheet verification (for the direct-driver approach)

- MAX31865 (hardware/max31865.pdf pp. 13–18): registers read at `0x0N` / write
  at `0x8N`, MSB first, multibyte auto-increment (RTD MSB+LSB atomically);
  auto-convert mode (config D6) converts continuously at the 50/60 Hz notch
  rate with **VBIAS held on**; RTD LSB bit D0 is a per-sample fault flag; high/
  low fault thresholds (03h–06h, same 15-bit<<1 format as the RTD registers)
  are compared on **every** conversion, latching D7/D6; latched faults clear
  via config D1 written with D5/D3/D2 = 0; notch must not change during auto
  mode; SPI modes 1/3. One-shot conversions take ~52 ms (60 Hz) — the library's
  blocking behavior is inherent to one-shot mode, not a bug in the library.
- MAX31855 (hardware/max31855.pdf): conversions free-run (t_CONV 70–100 ms),
  data updates while CS is high, so brief 250 ms-interval reads are correct and
  non-blocking as-is; cold junction readable at 0.0625 °C resolution.
- DimmerLink protocol: COMMAND 0x01 (RESET=0x01, RECALIBRATE=0x02,
  SWITCH_UART=0x03), VERSION 0x03, AC period 0x21/0x22, calibration status
  0x23, I2C address 0x30. Power-on level default is undocumented — hence the
  boot sync requirement (F1).

## Pre-review history (firmware, from the in-file version log)

- v0.6.0 2026-06-29 — tuning set (PID + FF) persisted in NVS.
- v0.5.0 2026-06-29 — feedforward power map (`heat_ff = ffK·fan·(SV−amb)`).
- v0.4.0 2026-06-29 — open-loop step-test autotune (TUNE), FOPDT fit + SIMC.
- v0.3.0 2026-06-29 — inlet closed loop (PI(D), anti-windup, bumpless engage).
- v0.2.x 2026-06-28 — sensor integration + RTD robust-read layer (see
  hardware/emi.md for the EMI history that drove it).
- v0.1.0 — dual DimmerLink control, WebSocket/Artisan protocol, interlock,
  OLED, RAM error log.
