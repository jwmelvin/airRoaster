# state-plan — planned work and phase specifications

> Companion to [state-current.md](state-current.md) (what is active now) and
> [state-archive.md](state-archive.md) (what is done, and the review findings
> these phases answer). Findings are referenced as F-numbers from the archive.

## NEXT — remaining on-roaster validation

The live sessions of 2026-07-02/03/04 (see the archive's v0.12–v0.15 entries)
validated much of the original checklist; items are marked accordingly.
Remaining drills, roughly in commissioning order:

1. ~~**Boot sync sanity**~~ — **done/superseded.** Heat-zero at boot stands;
   fan-level adoption via `getLevel()` was replaced by the RTC no-init shadow
   (v0.15.0, reads lie while firing). Fan-through-reboot validated 2026-07-04
   via a live OTA update with the fan running.
2. **Sensor path**: BT read sane in live sessions, but the specific checks are
   unrecorded — `STAT` after a few minutes (`loopMaxUs` should be dominated by
   the ~30 ms display push, not sensor reads); compare RTD fault frequency in
   the log against pre-v0.8.0 roasts (emi.md addendum says what to expect).
3. **Failsafe drills** (roaster cold, heat low): engage `INLET`, unplug the
   inlet TC → expect `inlet failsafe: inlet PV stale` within ~3 s, heat 0,
   mode manual. Confirm a TUNE aborts the same way.
4. **Telemetry + dashboard** — **mostly done**: the commissioning sequence
   (TUNE → APPLY → FF cal → INLET) ran end-to-end in the 2026-07-03 session.
   Still unchecked: kill/restore WiFi to see auto-reconnect on both sides.
5. **WDT confidence**: none of the normal paths (tune, big display repaints,
   WS bursts) should approach 8 s — `loopMaxUs` gives the margin number.
6. ~~**DimmerLink reset escalation**~~ — **superseded.** v0.13.0 removed
   autonomous resets entirely (soft reset drives the output full-on for
   ~3–4 s); resets are operator-only via `DLRESET`. The fw-version line at
   boot is still worth a glance.
7. **Interlock config (v0.10.0)**: from the dashboard panel set soft mode and
   custom limits, confirm the heat cap follows the fan slider accordingly, then
   power-cycle and confirm the values and mode survive (NVS). Try an invalid
   set (`IL 0 55 30`) and confirm it is rejected.
8. ~~**Power linearization (v0.11.0)**~~ — **done.** TUNE and FF calibration
   were re-run post-map; closed loop settles on SV and FF compensates fan
   steps (validated 2026-07-03, v0.14.1).
9. **OTA idle gate (v0.12.0)**: an OTA push with heat > 0 should time out on
   the host, then succeed again at heat 0. The happy path (idle OTA push,
   reboot, fan preserved) is validated.
10. **Curve experiments** (`CURVE FAN 0|2`, optional): compare fan response per
    level step on the dashboard chart; expectation is RMS (1) remains best.
    Reboot restores RMS automatically.
11. **Cooldown guard (v0.16.0)** — *mostly validated 2026-07-05*: deferral,
    hold, auto-release, and soak-back re-enforcement all observed working on
    the roaster. The 30 s dwell released early into soak-back (two re-enforce
    cycles), so the dwell is now adjustable (`COOL DWELL <s>`, NVS): find the
    dwell that makes one release stick (start ~90–120 s) and set it. Still
    unchecked: `COOL MIN`/`COOL DWELL` surviving a power cycle (NVS), and
    `COOL OFF` releasing a held fan immediately.
12. **Ambient reporting (v0.17.0)** — on a cold roaster, power up and check the
    serial log for `ambient: cold-start capture` with a sane room temp (BT vs
    CJ within 8 °C); dashboard Ambient panel should show it. Then run the
    roaster hot, power-cycle, and confirm the log says `warm boot … keeping`
    and the stored capture is unchanged. Check `AMB SRC`/`AMB <degC>` survive
    a power cycle (NVS). In Artisan: map the `AT` node to an extra WebSocket
    channel, select it on Config › Device › Ambient, and confirm Roast
    Properties picks up the ambient temperature at CHARGE (README § Ambient
    temperature has the click-path).

## Completed phases (specs kept for reference; details in the archive)

## Phase 1 — firmware safety (FW 0.7.0) — DONE 2026-07-02

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

## Phase 2 — MAX31865 direct-register driver (FW 0.8.0) — DONE 2026-07-02

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

## Phase 3 — protocol hardening + telemetry (FW 0.9.0) — DONE 2026-07-02

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

## Phase 4 — dashboard rebuild — DONE 2026-07-02

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

## Phase 5 — docs sync — DONE 2026-07-02

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

## Later / not scheduled

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
