# state-archive — completed work and standing findings

> Companion to [state-current.md](state-current.md), [state-plan.md](state-plan.md)
> and [state-history.md](state-history.md).
> Newest entries first. This file is the durable record: review findings keep
> their F-numbers here even after the fixes land, so plan/commit references
> stay resolvable.

## 2026-07-04 — v0.15.0 validated on roaster; merged to main

`feature/fan-restore` fast-forwarded into `main` (8e31624) after on-roaster
validation: fan running → OTA update → the fan kept spinning through the
reboot with the UI in sync. `main` now holds v0.15.0 with the entire v0.12 →
v0.15 line (OTA, DimmerLink rework, closed-loop/FF fixes, fan-level shadow)
validated in live operation. Left unchecked: the OTA idle gate drill (moved
to state-plan.md § NEXT).

## 2026-07-02 — Fan level survives MCU-only resets (v0.15.0)

Post-OTA observation: the fan physically stopped ~5 s after any reboot with
the fan running — which also broke the mid-roast crash-recovery airflow
guarantee. Cause: boot fan-level adoption read `getLevel()` while the fan was
firing → the read lied (returned 0, the v0.13 finding) → the v0.13
unconditional re-assert wrote the believed 0 to the hardware. Fix
(`feature/fan-restore`): the commanded fan level is shadowed in
`RTC_NOINIT_ATTR` RAM (magic + inverted-copy checksum; zero flash wear —
chosen over NVS for wear concerns, though the math showed NVS had ~60M-write
headroom). The shadow survives exactly MCU-only resets (crash/WDT/panic/OTA)
and is invalid after a true power-on, when the fan module is also unpowered
and 0 is correct.

## 2026-07-03 — Closed-loop standing offset → integral bound + FF step cal (v0.14.0/.1)

First closed-loop test held a rock-steady +10 °C offset at SV 150: a stale
NVS-persisted ffK made FF=80 where the plant needed ~50, and the integrator's
[0,100] floor could not go negative to cancel it (P carried −28 via standing
error — arithmetic matches exactly). v0.14.0 bounds the integral as
I ∈ [−ff, 100−ff] (steady command I+FF stays in 0..100; identical to before
when FF is off). The dashboard gained a client-side **FF step cal** panel that
measures ffK as the fan-step slope Δheat/(Δfan·ΔT) in closed loop — immune to
the standing-loss intercept that makes the through-origin FF CAL over-predict
when calibrated at warmup temperatures (measured plant: 25% heat @ ΔT 25,
~50% @ ΔT 115). **Validated on hardware 2026-07-03** (v0.14.1): closed loop
settles on SV, and after an FF step calibration the feedforward "almost
perfectly compensates" fan changes (user's assessment). The trouble-free
session also implicitly validated the v0.13 dimmer rework (no error flood, no
fan surges). v0.14.1 raised the inlet over-temp failsafe to 350 °C (SV max
300).

## 2026-07-02 — DimmerLink reset rework: writes trusted, reads demoted (v0.13.0)

The first hardware run of the v0.7 dimmer robustness code (fan 50, heat 0)
exposed two DimmerLink hardware behaviors: **register reads lie while a
module is firing**, and **a soft reset drives the output FULL ON for
~3–4 s** (fan visibly surged to 100%, no UI indication). The v0.7 reset
escalation was therefore resetting a healthy module every 15 s; on the heat
channel it would have been an uncommanded full-power burst, possibly with no
airflow. v0.13.0 removes autonomous resets entirely (operator-only `DLRESET`,
heat refused below interlock fan min), re-asserts curve+level unconditionally
every 5 s (writes are the reliable direction), and demotes all dimmer reads
to rate-limited diagnostics; level readback checked only at commanded-off.
Full write-up: [hardware/emi.md](hardware/emi.md) § DimmerLink addendum.
Validated implicitly by the trouble-free 2026-07-03 session (above).

## 2026-07-02 — OTA firmware updates (v0.12.0)

ArduinoOTA over WiFi, serviced from loop() only while idle (manual mode,
heat 0); onStart re-zeros the heater at the wire and detaches the task WDT
for the flash-write stall. verify.sh pins the TinyUF2 OTA partition scheme
(2×1408K app slots; NVS offset unchanged, tunings survive) and gained
`./verify.sh ota [host]`. **Validated on hardware 2026-07-02**: USB reflash
with the new partition table, then a full OTA push (mDNS resolve, auth,
upload, reboot, WebSocket back up). The idle gate (an OTA push with heat > 0
should time out on the host, then succeed again at heat 0) remains a
validation item in state-plan.md § NEXT.

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
- **Quantization (user-raised, assessed benign):** the √ map's slope drops
  below 1 above 25% power, so adjacent heat commands can collapse to one dimmer
  level (~2:1 near full scale, intermittent pairs mid-range). This exposes the
  hardware's real power resolution — 101 Vrms steps, P ∝ V² ⇒ ~2% of max power
  per step near the top — rather than losing anything (pre-map, adjacent
  commands were uniform in Vrms but spanned 0.2–4% of max power depending on
  operating point). Immaterial in INLET mode: the integrator dithers between
  adjacent levels, so average power resolves finer than one step. Documented in
  README § plain-text commands.

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
**The per-phase specifications are in § Appendix — phase specifications**
at the end of this file.

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

## Appendix — phase specifications (phases 1–5, all DONE 2026-07-02)

The as-planned specs for the five phases summarised in
§ 2026-07-02 — Robustness + dashboard implementation above. Moved here from
state-plan.md on 2026-09-06: the work is done, so the specs are record, not
plan. Kept in full because they carry the *reasoning* per item and the F-number
mapping that the summary entry compresses.

### Phase 1 — firmware safety (FW 0.7.0) — DONE 2026-07-02

*Answers F1 (boot level mismatch), F3 (closed-loop sensor failsafe), F6
(unchecked dimmer writes), F8 (no watchdog).*

1. **Boot dimmer sync.** After `initDL()` for both modules: force heat to 0
   (`setLevel(HEAT_ADDR, 0)`, retried); read the fan's actual level with
   `getLevel(FAN_ADDR)` and adopt it into `fanLevel` — after a crash mid-roast
   the fan keeps cooling the hot roaster while the heat is killed. Log if the
   sync fails.
2. **Inlet-loop failsafe.** Track inlet-PV freshness (`inLastGoodMs` stamped in
   `updateSensors()` on every accepted MAX31855 read). In `MODE_INLET`:
   - PV stale (> `INLET_PV_STALE_MS`, 3000 ms) → drop to `MODE_MANUAL`,
     heat 0, `logError`, broadcast. A frozen hold-last-good PV must never keep
     feeding the integrator.
   - Over-temp (`inTemp > INLET_OVERTEMP_C`, reuse 280 °C) → same action.
   - `MODE_TUNE` gains the same stale-PV abort (it already has over-temp).
3. **Checked dimmer writes.** `applyInterlock()` and the OT2 path only update
   the cached level when `setLevel()` returns true; on failure the cache keeps
   the old value so the next loop retries, with a rate-limited log entry. Add a
   **readback audit** to the existing 5 s DimmerLink error poll: `getLevel()`
   both channels; mismatch against the cached value → log + rewrite.
4. **Task watchdog.** `esp_task_wdt` (IDF 5 API: `esp_task_wdt_reconfigure` /
   `_init` with `esp_task_wdt_config_t`, `trigger_panic = true`, ~8 s), add the
   loop task, `esp_task_wdt_reset()` each loop; feed it inside the WiFi connect
   wait until Phase 3 makes that non-blocking. Safe only because of item 1.

### Phase 2 — MAX31865 direct-register driver (FW 0.8.0) — DONE 2026-07-02

*Answers F2 (blocking one-shot reads / defeated continuous-mode design) and
F10 (blind jitter metric). Datasheet traceability in state-archive.md.*

1. New local header `max31865_direct.h`, small class, no external deps:
   - Own SPI transactions: `SPISettings(1_000_000, MSBFIRST, SPI_MODE1)`,
     manual CS. Registers: read `0x0N`, write `0x8N`, MSB first, auto-increment
     multibyte.
   - `begin()`: config = `VBIAS(0x80) | AUTO(0x40)` (+3-wire/50 Hz bits if ever
     needed; we run 4-wire, 60 Hz ⇒ 0xC0), thresholds armed (below), faults
     cleared. Filter bit set before enabling auto mode (datasheet forbids
     changing the notch while converting).
   - `reassert()`: rewrite the config byte — this makes the existing
     `RTD_REASSERT_MS` stall guard actually meaningful.
   - `readRaw(bool &fault)`: one 2-byte read at 0x01; bit 0 of the pair is the
     per-sample fault flag; value is the 15-bit ratio.
   - `readFault()` / `clearFault()`: plain register read of 07h (no
     master-initiated fault cycle — the Adafruit default knocks the chip out of
     auto mode); clear via config D1 with D5/D3/D2 zero.
   - Temperature from raw via Callendar–Van Dusen (same math as the Adafruit
     `calculateTemperature`, implemented locally).
   - Threshold arming: convert `RTD_VALID_MIN_C`/`RTD_VALID_MAX_C` to raw via
     forward CVD `R = R0(1 + AT + BT²)` (B-term adequacy at −20 °C is fine for
     a fault threshold), write as 15-bit << 1. The chip then latches D7/D6 on
     every out-of-window conversion — on-silicon EMI evidence.
2. Rework `serviceRtd()` to use the driver: the two-read disagree check
   becomes two cheap register reads (a true SPI-glitch detector), fault
   evidence is no longer destroyed by the read path, and per-sample fault bits
   feed the debounce. Median filter, debounce, hold-last-good, rate-limited
   logging all stay as-is.
3. Remove the `Adafruit_MAX31865` dependency (keep MAX31855 — verified
   non-blocking and correct).
4. **Honest load metric**: track worst single `loop()` duration (µs) alongside
   the control-jitter watch; report and reset both via `STAT`
   (`loopMaxUs` field). The old metric couldn't see in-pass blocking.

### Phase 3 — protocol hardening + telemetry (FW 0.9.0) — DONE 2026-07-02

*Answers F4 (garbage parses as zero), F5 (JSON envelope int-rounds the ramped
setpoint), F7 (WiFi), F9 (DimmerLink extras), tune-settled flag, and adds the
telemetry channel the dashboard needs.*

1. **Strict numeric parsing** (`parseFloatStrict`/`parseIntStrict`): `OT1 x`
   or `PID a b c` is rejected with a reply to the sender, never treated as 0,
   and never persisted to NVS.
2. **JSON envelope keeps floats**: `{"command":"INLET","value":183.4}` becomes
   `INLET 183.40` (currently rounded to int — quantizes Artisan's ramped
   playback to 1 °C steps).
3. **WiFi**: bounded connect wait (~15 s, WDT-fed, display progress), then boot
   proceeds regardless; `setAutoReconnect(true)` plus a rate-limited reconnect
   check in loop; display already shows state. Roaster must be fully usable
   over serial with no WiFi.
4. **TUNE result gains `"settled":true|false`** — a timeout fit underestimates
   dT and suggests too-hot gains; the flag says whether to trust it.
5. **DimmerLink extras**: log VERSION (reg 0x03) at init; escalate to COMMAND
   RESET (reg 0x01 ← 0x01) after N consecutive error-poll failures, then
   re-init (re-assert curve, restore level). Level readback audit came in
   Phase 1.
6. **`FF AMB` with no value** seeds `ffAmbient` from the MAX31855 cold-junction
   temperature (`readInternal()`), with the enclosure-warmer-than-room caveat
   documented.
7. **Telemetry push**: every `TELEM_PERIOD_MS` (default 1000 ms; 500 ms during
   TUNE) broadcast
   `{"pushMessage":"telem","data":{"t":<ms>,"IN":..,"BT":..,"ET":..,"sv":..,"heat":..,"heatReq":..,"fan":..,"ilCap":..,"mode":"..","p":..,"i":..,"d":..,"ff":..,"fltIN":0|1,"fltBT":0|1}}`
   — the PID terms come from the last `controlStep()`. `TELEM <ms>|OFF` command
   (clamped 100–10000). Skip building the string when no client is connected.

### Phase 4 — dashboard rebuild — DONE 2026-07-02

Single file, zero dependencies, works from `file://`. Grouped panels:

1. **Connection** — IP (remembered), connect/disconnect, auto-reconnect with
   backoff, status dot.
2. **Status** — mode badge (manual/inlet/tune), heat bar showing applied vs
   requested, fan bar, interlock state/cap, inlet SV.
3. **Temperatures** — large IN/BT/ET readouts, per-channel fault badges from
   telemetry flags.
4. **Inlet tuning** (the centerpiece) —
   - Canvas strip chart: IN (PV) and SV on the temperature axis, heat on a
     0–100 % axis; rolling buffer (≥30 min at 1 Hz), pause, window selector,
     CSV export of the buffer.
   - PID editor prefilled from `pid` pushes; FF editor (`ffK`, ambient, CAL,
     OFF); live P/I/D/FF term readout.
   - TUNE workflow: start (step % field), abort; on result show the model
     (Kp/tau/theta/dT, settled flag) and both gain sets with **Apply tight**
     and **Apply cons** buttons (cons applies via `PID <kp> <ki> 0`).
5. **Console + log** — every message timestamped into a capped capture buffer;
   per-class filter checkboxes (status/telem/error/log/tune-pid-ff-stat/sent/
   other; telem hidden by default), free-text filter, **Save log** (.txt
   download) — the device log is 8 RAM entries, so the browser is the real
   archive; `LOG` requested on connect.
6. **Commissioning** — existing sequence panel, retained and updated.

### Phase 5 — docs sync — DONE 2026-07-02

- README: interlock constants (code says 48/55/30, README says 23/30/30),
  dashboard path (repo root, not `artisan/`), delete the stale "BT/ET stubbed
  at 0.0" paragraph, document new commands (`TELEM`, no-arg `FF AMB`), boot
  dimmer sync, watchdog, WiFi behavior, `settled` flag, direct-driver sensor
  path.
- emi.md addendum: the library one-shot discovery — unbiased auto-convert
  windows between polls were a plausible contributor to spurious `0x60`
  faults; continuous mode changes the experiment. Note what to watch in the
  next roast's fault log.
- Keep state docs current per the update discipline in state-current.md.

