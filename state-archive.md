# state-archive — completed work and standing findings

> Companion to [state-current.md](state-current.md) and [state-plan.md](state-plan.md).
> Newest entries first. This file is the durable record: review findings keep
> their F-numbers here even after the fixes land, so plan/commit references
> stay resolvable.

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
