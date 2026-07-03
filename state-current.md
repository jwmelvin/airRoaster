# state-current — what is being worked on right now

> One of three state documents. **This file**: the active effort and where it
> stands. [state-plan.md](state-plan.md): planned phases and their full specs.
> [state-archive.md](state-archive.md): completed work, review findings, and
> decided-and-done rationale. Update discipline: when a phase completes, move
> its detail from *plan* to *archive* and re-point this file at the next phase.

## Development framework (read this first if you are new here)

**What this is.** ESP32-S3 firmware (`airRoaster.ino`, single sketch file) for a
hot-air coffee roaster: two I2C AC dimmers (heat 0x51, fan 0x52), three SPI
temperature sensors (2× MAX31865 RTD, 1× MAX31855 thermocouple), SH1107 OLED,
WebSocket server speaking Artisan's protocol plus plain-text commands, and an
on-device PI(D) closed loop holding inlet temperature. `dashboard.html` (repo
root) is a zero-dependency browser console for commissioning and tuning.

**How to build.** `./verify.sh` compile-verifies (arduino-cli, FQBN
`esp32:esp32:adafruit_feather_esp32s3`, ESP32 core 3.3.10 / IDF 5.x);
`./verify.sh upload` flashes. There is no test suite — the verify script plus
on-roaster commissioning ([README](README.md) § Commissioning) is the loop.
Compile after every meaningful edit; the script surfaces sketch-local warnings.

**Ground truth documents.**
- [README.md](README.md) — user-facing behavior, command set, Artisan setup.
- [hardware/pins.md](hardware/pins.md) — pin/bus/address map. Do not invent pins.
- [hardware/emi.md](hardware/emi.md) — the RTD noise/fault history and why the
  sensor code is shaped the way it is. Read before touching `serviceRtd()`.
- [hardware/max31865.pdf](hardware/max31865.pdf), [hardware/max31855.pdf](hardware/max31855.pdf)
  — sensor datasheets; register-level claims must trace to these.
- DimmerLink I2C protocol: https://www.rbdimmer.com/docs/dimmerlink-I2CCommunication
  (registers: 0x00 status, 0x01 command [RESET=0x01], 0x02 error, 0x03 version,
  0x10 level, 0x11 curve, 0x20 freq, 0x30 address).

**Conventions.**
- Single `.ino` plus small local headers when a component earns isolation
  (e.g. the direct MAX31865 driver). No external libraries beyond those in
  README § Dependencies without good reason.
- Version history lives at the bottom of `airRoaster.ino`; bump `FW_VERSION`
  and add an entry per firmware-visible change set.
- All unsolicited WebSocket traffic uses Artisan's push envelope
  `{"pushMessage":"<type>","data":...}`; replies to a specific client go only
  to that client. JSON is built with `snprintf` into sized buffers — check the
  buffer size when adding fields.
- Safety posture: the heater must never run without airflow (interlock), never
  survive a crash-reboot (boot-time level sync), and never be driven by a stale
  or faulted sensor (control-loop failsafe). New features must not weaken these.
- The control law stays isolated in `controlStep()` (the "seam") so it can move
  to a FreeRTOS task later without changing the math.
- Roaster is not always on the bench: code must behave sanely with no dimmers,
  no sensors, and no WiFi present (log, hold safe defaults, keep serving serial).

**Git.** Development happens on feature branches; `main` holds roast-tested
firmware. Current branch: `feature/ota-updates` (branched from
`feature/robustness-dashboard`). Commit per phase with
a message naming the phase. The user's Artisan config churn (`artisan/*.aset`,
`*.alog`) may be present in the working tree — never sweep it into a firmware
commit; stage files explicitly.

## Active effort (2026-07-02)

**OTA firmware updates** (`feature/ota-updates`, v0.12.0): ArduinoOTA over
WiFi, serviced from loop() only while idle (manual mode, heat 0); onStart
re-zeros the heater at the wire and detaches the task WDT for the flash-write
stall. verify.sh now pins the TinyUF2 OTA partition scheme (2×1408K app slots;
NVS offset unchanged, tunings survive) and gained `./verify.sh ota [host]`.
**Validated on hardware 2026-07-02**: USB reflash with the new partition
table, then a full OTA push (mDNS resolve, auth, upload, reboot, WebSocket
back up) — the device now runs OTA-delivered firmware. Still to check: the
idle gate (an OTA push with heat > 0 should time out on the host, then
succeed again at heat 0).

**Validation finding → v0.13.0 (same branch).** The first hardware run of the
v0.7 dimmer robustness code (fan 50, heat 0) exposed two DimmerLink hardware
behaviors — register reads lie while a module is firing, and a soft reset
drives the output FULL ON for ~3-4 s (fan visibly surged to 100%, no UI
indication). The v0.7 reset escalation was therefore resetting a healthy
module every 15 s; on the heat channel it would have been an uncommanded
full-power burst, possibly with no airflow. v0.13.0 removes autonomous resets
entirely (operator-only `DLRESET`, heat refused below interlock fan min),
re-asserts curve+level unconditionally every 5 s (writes are the reliable
direction), and demotes all dimmer reads to rate-limited diagnostics; level
readback checked only at commanded-off. Full write-up:
[hardware/emi.md](hardware/emi.md) § DimmerLink addendum. Needs on-roaster
re-validation: fan at 50 must now run error-free and surge-free.

**Closed-loop finding → v0.14.0.** First closed-loop test (2026-07-03 log)
held a rock-steady +10 °C offset at SV 150: a stale NVS-persisted ffK made
FF=80 where the plant needed ~50, and the integrator's [0,100] floor could
not go negative to cancel it (P carried −28 via standing error — arithmetic
matches exactly). v0.14.0 bounds the integral as I ∈ [−ff, 100−ff] (steady
command I+FF stays in 0..100; identical to before when FF is off). The
dashboard gained a client-side **FF step cal** panel that measures ffK as the
fan-step slope Δheat/(Δfan·ΔT) in closed loop — immune to the standing-loss
intercept that makes the through-origin FF CAL over-predict when calibrated
at warmup temperatures (measured plant: 25% heat @ ΔT 25, ~50% @ ΔT 115).
**Validated on hardware 2026-07-03** (v0.14.1): closed loop settles on SV,
and after an FF step calibration the feedforward "almost perfectly
compensates" fan changes (user's assessment). The trouble-free session also
implicitly validates the v0.13 dimmer rework (no error flood, no fan surges
with the fan running). Over-temp failsafe raised to 350 °C (SV max 300).

**Known open issue (fan stop after reboot).** Boot fan-level adoption reads
`getLevel()` while the fan is firing → the read lies (returns 0) → adoption
fails → the v0.13 unconditional re-assert then writes the believed 0 and
physically stops the fan ~5 s after any reboot with the fan running (observed
after an OTA update; also breaks the mid-roast crash-recovery airflow
guarantee). Proposed fix (not yet implemented): persist commanded fan level
to NVS on change and restore+assert it at boot instead of trusting a read.

**Robustness + dashboard development** (from the July 2026 code review) is
**implemented through all five phases** on `feature/robustness-dashboard` —
firmware v0.9.0, one commit per phase. Full findings and what landed:
[state-archive.md](state-archive.md). Remaining planned work (chiefly
**on-roaster validation** — nothing has run on hardware yet, only
compile-verify): [state-plan.md](state-plan.md).

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Review, datasheet verification, state docs | done |
| 1 | Firmware safety: boot dimmer sync, inlet failsafe, checked dimmer writes, watchdog (v0.7.0) | done |
| 2 | MAX31865 direct-register continuous-mode driver (v0.8.0) | done |
| 3 | Protocol hardening + telemetry push (v0.9.0) | done |
| 4 | Dashboard rebuild: grouped panels, tuning chart, log capture/filter/export | done |
| 5 | Docs sync: README, emi.md addendum | done |

**Key verified facts the work rests on** (traceable to datasheets, see archive):
- Adafruit_MAX31865 v1.6.2 `temperature()` is a blocking one-shot (~75 ms) that
  toggles VBIAS off after each read and clears the fault register — it defeats
  the firmware's continuous-mode design. Direct register access is confirmed
  viable: auto-convert mode (config `VBIAS|AUTO` = 0xC0) converts continuously
  at the notch rate with VBIAS held on; RTD MSB+LSB read atomically (multibyte
  read from 0x01, SPI mode 1, 1 MHz); LSB bit D0 is a per-sample fault flag;
  fault thresholds (03h–06h, RTD-register format = 15-bit ratio << 1) are
  compared on every conversion; latched faults at 07h clear via config D1 with
  D5/D3/D2 = 0.
- MAX31855 free-runs conversions (70–100 ms) and updates while CS is high — the
  existing library path is already non-blocking; keep it. `readInternal()`
  (cold junction, 0.0625 °C) is available as an ambient estimate.
- After an MCU-only reset the DimmerLink modules are assumed to hold their last
  levels (power-on default is undocumented) — boot must force heat to 0 and
  adopt the fan's actual level via `getLevel()`.
