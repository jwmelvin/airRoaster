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
firmware. `main` is at **v0.17.0** (2026-07-07): `feature/ambient` (ambient
reporting — the `AT` channel + cold-junction surfacing) was fast-forwarded into
`main` and pushed; its on-roaster validation is still pending (state-plan.md
§ NEXT item 12). Start the next effort on a fresh branch off `main`. Commit per
phase with
a message naming the phase. The user's Artisan config churn (`artisan/*.aset`,
`*.alog`) may be present in the working tree — never sweep it into a firmware
commit; stage files explicitly.

## Active effort (2026-07-10)

**Command authentication → v0.18.0** (on `feature/auth-proxy`). Connect-time
challenge–response sessions on the WebSocket: the device pushes a random
nonce to each new client ("auth" push); a client proves the shared `AUTH_KEY`
(secrets.h; absent/empty = feature entirely off) by returning
`AUTH HMAC-SHA256(key, nonce-hex)` and its connection is trusted until it
drops (5 fails burn the connection; each failure re-nonces). Tiered
enforcement `AUTH MODE OFF|CONFIG|FULL` (NVS "auth"; a keyed build's first
boot defaults to CONFIG — operator decision 2026-07-11): CONFIG gates
safety/config mutations while OT1/OT2/INLET stay open for direct Artisan;
FULL gates all mutations — Artisan then connects through
`tools/roaster_proxy.py` (localhost signing proxy: answers the challenge,
relays everything else; transparent pipe against a keyless device). The
always-open safe subset (operator requirement): reads plus `OT1 0`,
`INLET OFF`/`INLET 0`, `COOL ON`, `TUNE ABORT` — any device can stop the
roaster, never start it. `AUTH MODE` itself always requires auth; serial is
always trusted (physical access). Single gate at the top of
`processCommand()` via `cmdTier()`. Dashboard: key field (localStorage),
automatic challenge answering (Web Crypto), Auth panel. Compile-verified;
proxy validated end-to-end against a firmware-faithful fake device (correct
key / wrong key / keyless all behave); dashboard HMAC cross-checked against
a Python reference. On-roaster + live-Artisan drill: state-plan.md § NEXT
item 13. Design decisions (operator-confirmed 2026-07-10): session auth over
per-message HMAC; runtime tier; secrets.h key; python proxy. Key management
(`tools/auth_key.py`, stdlib-only; operator-confirmed 2026-07-11): secrets.h
is the single source of truth — `generate` writes a 64-hex CSPRNG key there
(refuses to replace without `--rotate`), the proxy parses it automatically,
`show` feeds the dashboard paste, `hmac <nonce>` supports manual testing;
rotation = generate --rotate + reflash (USB preferred — an OTA image carries
the key across the LAN in cleartext) + dashboard re-paste. The helper's `ota`
subcommand likewise generates a dedicated random OTA_PASS (2026-07-11): the
firmware's WIFI_PASS fallback means a device without one accepts firmware
pushes from anyone on the WLAN; verify.sh reads the value automatically, and
the first flash after a change must be USB. Deliberately deferred (see the
auth item in state-plan § Later for the record): signed images / Secure Boot
/ OTA arming.

**Prior: Ambient reporting → v0.17.0** (merged to `main`). The Artisan `getData`
response gains an `AT` node (°C): Artisan maps it to an extra WebSocket
channel and selects that channel in **Config › Device › Ambient** (tab), then
samples it at CHARGE into Roast Properties (README § Ambient temperature has
the click-path). Three sources via the new `AMB` command (`amb` push, NVS
namespace "amb", re-validated on load): **cold-start memory** (default) — a
once-per-boot capture that saves the BT RTD as ambient only when it agrees
with the MAX31855 cold junction within 8 °C, so a power cycle on a hot roaster
keeps the capture from the last genuinely cold boot; **cold junction** — live
`readInternal()`, now read every sensor poll (hold-last-good `cjTemp`) and
surfaced in telemetry (`cj`, plus `amb` = the reported value); **manual** —
`AMB <degC>` (also switches the source to manual). Dashboard: cold-junction
readout in Temperatures, new Ambient panel (source selector; manual entry
defaults to °F, converts to °C before sending — firmware and Artisan stay
°C-only). Deliberately separate from `FF AMB` (control-law parameter).
Compile-verified; dashboard checked in browser preview with simulated pushes;
on-roaster drill is state-plan.md § NEXT item 12.

**Prior: Cooldown guard → v0.16.0** (on `main`). Minimum fan-shutdown
criteria, per operator request: the fan may stop only once the inlet has
stayed below `COOL_FAN_OFF_C` (70 °C) for the release dwell (`coolDwellS`,
default 30 s, live-set via `COOL DWELL <1-3600>`, NVS) on fresh
readings with heat off. **First on-roaster run 2026-07-05**: deferral, hold,
and auto-release all worked, but the 30 s dwell released into soak-back and
the guard re-enforced twice (fan pulsed twice at ~17:36–17:38 on the log) —
which is why the dwell became adjustable; raise it until one release sticks. An `OT2` below `coolFanMin` (default 50, live-set via
`COOL MIN`, NVS namespace "cool") while hot is *deferred* (fan
held at `coolFanMin`, requested level auto-applies when the criteria are met);
a hot roaster with the fan below minimum gets airflow forced back on
autonomously (manual-mode requested heat zeroed so the raised fan can't
un-block interlock-capped heat). Stale-hot sensor keeps the fan running;
`COOL OFF` is the runtime-only operator escape (re-armed every boot). New
`COOL` command, `cool` push, status `cool` field, OLED row 7; OT2 refactored
through commit-on-ack `setFanLevel()`. Dashboard gains a Cooldown panel
(arm/disarm, fan-min read/set, hold-state line; prefilled from `COOL` on
connect) and a cooldown line in the Status panel. Compile-verified; dashboard
checked in browser preview with simulated pushes; on-roaster drill is
state-plan.md § NEXT item 11. README + state docs updated.

**Prior: INLET 0 semantics → v0.15.1** (on `main`). A follow-background test (2026-07-04 dashboard CSV)
ended with Artisan's SV slider at 0; the firmware clamped it to
`INLET_SV_MIN_C` (0 °C) and kept the loop "engaged" on an unreachable target —
P railed at about −280 with heat pinned at 0 for the whole cooldown.
`INLET <sv ≤ 0>` now means "no setpoint": drop to manual, heat 0 (cooldown
intent). `INLET OFF` unchanged (disengage, hold heat). New tool
`downsample_logs.py` (repo root) condenses .alog / dashboard-CSV / dashboard
txt logs into a compact summary for review, and mirrors the semantics (SV ≤ 0
blanked from series and tracking stats). Compile-verified; on-roaster check is
trivial: SV slider to 0 → mode `manual`, heat 0.

Otherwise **between efforts.** `feature/fan-restore` (v0.15.0, RTC no-init fan
shadow) was **validated on the roaster 2026-07-04** — fan running → OTA
update → fan kept spinning through the reboot with the UI in sync — and
fast-forwarded into `main`, which now holds v0.15.0. The full v0.12 → v0.15
development record (OTA updates, the v0.13 DimmerLink rework, the v0.14
closed-loop/feedforward fixes, the v0.15 fan-level shadow) is in
[state-archive.md](state-archive.md). Start the next effort on a fresh branch
off `main`.

Remaining known work: the unchecked on-roaster validation items in
[state-plan.md](state-plan.md) § NEXT (failsafe drills, WDT margin, RTD
fault-rate comparison, interlock persistence, OTA idle gate, WiFi
kill/restore) and the unscheduled ideas in § Later / not scheduled.

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
  restore the fan level. DimmerLink register reads (incl. `getLevel()`) lie
  while a module is firing (v0.13 finding), so the fan level is recovered from
  the RTC no-init shadow (v0.15), never from readback.
