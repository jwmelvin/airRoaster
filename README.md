# airRoaster

ESP32-based controller for a hot-air coffee roaster. Controls a heating element and fan independently via two [RBDimmer DimmerLink](https://www.rbdimmer.com/docs/dimmerlink-I2CCommunication) I2C AC dimmers, with a WebSocket interface for remote control and an OLED display for local status.

---

## Hardware

| Component | Details |
|-----------|---------|
| MCU | ESP32-S3 Feather with 4MB Flash 2MB PSRAM, https://www.adafruit.com/product/5477 (any ESP32 variant with I2C and WiFi) |
| Display | FeatherWing OLED - 128x64 OLED, https://www.adafruit.com/product/4650 (SH1107 64×128 OLED), I2C address `0x3C` |
| Dimmer interface | RBDimmer DimmerLink ([overview](https://www.rbdimmer.com/docs/dimmerlink-overview), [I2C protocol](https://www.rbdimmer.com/docs/dimmerlink-I2CCommunication)), I2C address heat: `0x51`; fan: `0x52`. Curve is set to RMS (mode `1`) at startup; switchable at runtime with the `CURVE` command. |
| Dimmers |Dimmers purchased from RobotDyn Official Store on AliExpress. "Dimmer AC module High Power for 40A 600V High Load, 1 Channel, 3.3V/5V logic"; "Dimmer AC module for 16A/24A 600V High Load, 1 Channel, 3.3V/5V logic with current load control" |
| RTD amplifiers (BT/ET) | 2× MAX31865, https://www.adafruit.com/product/3648 (PT1000 version, 4.3 kΩ reference), on the shared SPI bus. BT (bean) probe on CS `GPIO 10`, 4-wire PT1000; ET board on CS `GPIO 9` has no probe yet (`RTD_ET_ENABLED 0`, channel reads 0.0). Driven register-direct in continuous auto-convert mode via `max31865_direct.h`, not the Adafruit library — see [Dependencies](#dependencies) for why, and `hardware/emi.md` for the RTD noise/fault history. |
| Thermocouple amplifier (IN) | MAX31855, https://www.adafruit.com/product/269, K-type inlet probe, on the shared SPI bus (CS `GPIO 8`). Read via the Adafruit library (non-blocking, free-running conversions). Its cold-junction temperature doubles as the board-ambient estimate for `FF AMB` and is a selectable ambient source for Artisan's `AT` channel (`AMB SRC CJ`). |
| Heater | from sdm2020_tools on eBay and listed as "1 set 230V 3600W 132.387 Heating Element & mica casing for hot air blower guns". Its power in my use is a little higher because I use 240V.|
| Blower | Ametek 116392-00 |

---

## Configuration

### WiFi credentials

Copy the credentials template and fill in your network details. This file is gitignored and should never be committed.

```
cp secrets.h.example secrets.h   # edit WIFI_SSID and WIFI_PASS
```

If `secrets.h.example` does not exist yet, create `secrets.h` manually:

```cpp
#pragma once
#define WIFI_SSID   "your_ssid"
#define WIFI_PASS   "your_password"
// Optional: dedicated password for over-the-air updates.
// If omitted, OTA authentication falls back to WIFI_PASS (never unauthenticated).
#define OTA_PASS    "your_ota_password"
```

### Compile-time constants

| Constant | Default | Description |
|----------|---------|-------------|
| `DUTY_STEP` | `1` | Increment/decrement step for UP/DOWN commands (%) — single percent; the fan responds over a narrow band |
| `WS_PORT` | `81` | WebSocket server port |
| `DL_INIT_RETRY_DELAY_MS` | `500` | Delay between DimmerLink ready-check retries at startup (ms) |
| `IL_FAN_MIN_DFLT` | `48` | Default fan level below which heat is always 0 (runtime-set via `IL`, NVS-persisted) |
| `IL_FAN_FULL_DFLT` | `55` | Default fan level at or above which heat is fully unrestricted (soft mode) |
| `IL_HEAT_AT_MIN_DFLT` | `30` | Default heat cap (%) when fan is exactly at the fan minimum (soft mode) |
| `WDT_TIMEOUT_MS` | `8000` | Task watchdog: panic→reset if the loop hangs this long |
| `INLET_PV_STALE_MS` | `3000` | Closed loop / tune failsafe if the inlet reading is older than this |
| `INLET_OVERTEMP_C` | `350` | Closed loop failsafe above this inlet temperature (°C) — overshoot margin above the 300 °C setpoint max |
| `COOL_FAN_OFF_C` | `70` | Cooldown guard: the fan may stop only after the inlet stays below this (°C) — see [Cooldown guard](#cooldown-guard) |
| `COOL_DWELL_S_DFLT` | `30` | Default dwell (s) the inlet must stay below `COOL_FAN_OFF_C` before a deferred fan level is applied (runtime-set via `COOL DWELL`, NVS-persisted) |
| `COOL_FAN_MIN_DFLT` | `50` | Default fan level enforced while cooling down (runtime-set via `COOL MIN`, NVS-persisted) |
| `WIFI_CONNECT_TIMEOUT_MS` | `15000` | Boot-time WiFi wait; the roaster starts without network after this |
| `TELEM_PERIOD_MS` | `1000` | Telemetry push cadence (runtime-adjustable via `TELEM`) |
| `OTA_HOSTNAME` | `airroaster` | mDNS name the OTA updater answers to (`airroaster.local`) |

---

## Over-the-air firmware updates

After the first USB flash, updates can be pushed over WiFi:

```
./verify.sh ota              # push to airroaster.local
./verify.sh ota 192.168.1.42 # or by IP (shown on the OLED)
```

Uses [ArduinoOTA](https://docs.espressif.com/projects/arduino-esp32/en/latest/ota_web_update.html)
(part of the ESP32 core — no new dependencies), authenticated with `OTA_PASS`
(falling back to `WIFI_PASS`). The build uses the TinyUF2 **OTA** partition
scheme: two 1408 KB app slots — the update writes to the inactive slot and the
device reboots into it. NVS (persisted tunings and interlock config) is
untouched by updates.

**The updater is only serviced while the roaster is idle** — manual mode with
heat at 0 (the fan may run). A push attempted mid-roast times out on the host
and the roast is unaffected. This is deliberate: the flash write blocks the
main loop, and with it the interlock and sensor failsafes, for its ~15 s
duration, which must never happen with the heater energized. When an update
starts, the heater is additionally forced to 0 at the dimmer and the task
watchdog is detached for the write (re-armed if the update fails). Progress is
shown on the OLED.

Caveats:

- **The first flash after adopting this partition scheme must be over USB**
  (`./verify.sh upload`) — the partition table itself cannot be rewritten over
  the air.
- A bad-but-bootable image sticks (the core has no automatic rollback); USB
  reflash is the recovery path. This is an inconvenience, not a hazard — boot
  always forces heat to 0 before anything else runs.

---

## Startup sequence

1. Task watchdog armed (8 s, panic→reset — safe because of step 4)
2. Display and I2C bus initialize
3. Both DimmerLink devices initialize — retried up to 3 times each (`DL_INIT_RETRY_DELAY_MS` apart); failures are logged. Dimmer init happens before WiFi to avoid missing the ready window at power-on.
4. **Boot dimmer sync**: heat is forced to `0`, and the fan level is restored from an RTC no-init RAM shadow (magic + checksum validated) — after an MCU-only reset (crash / watchdog / OTA reboot) the dimmers keep running at their last levels, so a hot roaster keeps its cooling airflow while the heater is killed. After a true power-on the shadow is invalid and the fan defaults to 0, matching the also-unpowered fan module. (The fan is deliberately *not* read back from the module: DimmerLink register reads are unreliable while a module is firing — see [hardware/emi.md](hardware/emi.md).)
5. Sensors initialize (MAX31865s enter continuous conversion with on-chip fault thresholds armed)
6. ESP32 connects to WiFi — bounded wait (15 s), then boot proceeds regardless; the link is watched and reconnected from the main loop. The roaster is fully operable over serial with no network.
7. OTA updater starts (deferred until the link is up if WiFi was down at boot)
8. WebSocket server starts on port `81`
9. IP address is shown on the display

---

## Interfaces

### Dashboard ([dashboard.html](dashboard.html))

A single self-contained HTML file at the repo root — no build step, no
dependencies, works opened straight from `file://`. It is the commissioning
and tuning console: it connects to the device's WebSocket (below) and every
button simply sends one of the plain-text commands documented in the next
section, so anything the dashboard does can also be typed by hand.

- **Connection bar** — device IP (remembered in the browser), connect/
  disconnect with optional auto-reconnect, link indicator, and always-visible
  safety actions: `HEAT 0`, `INLET OFF`, `TUNE ABORT`.
- **Status** — mode badge (manual / inlet / tune), heat bar showing the
  applied level against the requested level (so an interlock cap is visible at
  a glance), fan bar, interlock state, and cooldown-guard state (whether the
  fan is being held with a release pending).
- **Temperatures** — large IN / BT / ET readouts with per-channel fault
  badges, current setpoint, the MAX31855 cold-junction temperature, and the
  age of the last telemetry frame.
- **Inlet control chart** — rolling strip chart of IN, SV, and BT against
  heat/fan % , fed by the telemetry push; selectable window (1–60 min), pause,
  BT toggle, CSV export of the buffer.
- **Setpoint / Manual** — engage or release the closed loop; direct heat and
  fan entry with fan presets and ±1 % nudges.
- **Tuning panels** — PID editor (prefilled from device reports); feedforward
  (set/read `ffK`, seed ambient, through-origin CAL, off); step test (start
  `TUNE`, then apply the tight or conservative gain suggestion); and **FF step
  cal**, a client-side calibration that measures `ffK` from a fan step while
  the loop holds (the preferred method — see
  [Feedforward](#feedforward-airflow-compensation)).
- **Interlock** — hard/soft mode and the three limits, read/set live
  (NVS-persisted on the device).
- **Cooldown** — arm/disarm the [cooldown guard](#cooldown-guard) and read/set
  the enforced cooldown fan minimum and release dwell (NVS-persisted on the
  device); shows the hold state and release criteria, prefilled from the
  `cool` report on connect.
- **Curves** — runtime dimmer-curve selection per channel, with an indicator
  for whether the heat power map is active.
- **Ambient** — select the ambient source reported to Artisan (cold-start
  memory / cold junction / manual) and enter a manual value in °F (default) or
  °C — converted to °C before sending; see
  [Ambient temperature](#ambient-temperature-at).
- **Console + log** — free-form command line, every message timestamped into
  a capped capture buffer with per-class show/hide (telemetry hidden by
  default) and free-text filtering, **Save log** to a file. The device keeps
  only 8 error-log entries in RAM, so this buffer is the durable record; the
  dashboard requests `LOG` on connect.
- **Commissioning sequence** — a collapsible guided checklist from first
  flash through step-test, gain apply, feedforward calibration, and
  closed-loop verification (see [Commissioning](#commissioning)).

### WebSocket (`ws://<device-ip>:81`)

The controller speaks two protocols on the same connection:

#### Artisan protocol (request/response)

Artisan polls the device on its sample interval. The controller responds with the current temperature readings.

**Request** (sent by Artisan):
```json
{"command": "getData", "id": 12345, "machine": 0}
```

**Response** (sent by controller):
```json
{"id": 12345, "data": {"BT": 195.3, "ET": 210.0, "IN": 182.4, "AT": 21.9}}
```

`BT` is the bean RTD (MAX31865, read register-direct in continuous mode — see
`max31865_direct.h`), `IN` is the inlet thermocouple (MAX31855). `ET` reads
`0.0` until a second RTD probe is wired and `RTD_ET_ENABLED` is set to `1`.
During a sensor fault a channel holds its last good value rather than dropping
to 0 (see [hardware/emi.md](hardware/emi.md)); anything closing a loop on a
reading also checks its freshness. `AT` is the ambient temperature (°C) from
the source selected with the `AMB` command — see
[Ambient temperature](#ambient-temperature-at) for how Artisan consumes it.

#### Plain-text commands

Artisan sliders and any other client send plain-text commands. Token delimiters are space, comma, semicolon, or equals sign. Commands are case-insensitive.

| Command | Example | Description |
|---------|---------|-------------|
| `OT1 <value>` | `OT1 60` | Set heat level, 0–100% **of max power** (power-linearized — see below) |
| `OT1 UP` | `OT1 UP` | Increase heat by `DUTY_STEP` |
| `OT1 DOWN` | `OT1 DOWN` | Decrease heat by `DUTY_STEP` |
| `OT2 <value>` | `OT2 50` | Set fan level (0–100%). A level below the cooldown fan minimum while the inlet is ≥ 70 °C is **deferred**, not obeyed — see [Cooldown guard](#cooldown-guard) |
| `OT2 UP` | `OT2 UP` | Increase fan by `DUTY_STEP` |
| `OT2 DOWN` | `OT2 DOWN` | Decrease fan by `DUTY_STEP` |
| `INLET <degC>` | `INLET 165` | Set inlet setpoint and engage closed-loop control (see [Inlet temperature control](#inlet-temperature-control)) |
| `INLET 0` | `INLET 0` | No setpoint: disengage closed-loop control and set heat to 0 (cooldown) |
| `INLET OFF` | `INLET OFF` | Disengage closed-loop control; heat holds at its current level |
| `PID` | `PID` | Report current PID gains, setpoint, and mode |
| `PID <kp ki kd>` | `PID 1.5 0.05 0` | Set PID gains live (for manual tuning) |
| `TUNE` | `TUNE` | Run an open-loop step test and suggest PI gains (see [Tuning](#tuning)) |
| `TUNE <pct>` | `TUNE 20` | Step test with a specific heat step (% points) |
| `TUNE ABORT` | `TUNE ABORT` | Cancel a running step test |
| `TUNE APPLY` | `TUNE APPLY` | Apply the last test's "tight" suggested gains |
| `FF` | `FF` | Report feedforward params and current value (see [Feedforward](#feedforward-airflow-compensation)) |
| `FF <k>` | `FF 0.0045` | Set the feedforward coefficient `ffK` directly |
| `FF AMB <degC>` | `FF AMB 24` | Set the ambient reference temperature |
| `FF AMB` | `FF AMB` | Seed ambient from the MAX31855 cold-junction temperature (board ambient; the enclosure runs a little warm) |
| `FF CAL` | `FF CAL` | Auto-calibrate `ffK` from the current (steady) operating point |
| `FF OFF` | `FF OFF` | Disable feedforward (`ffK = 0`) |
| `STAT` | `STAT` | Report and reset the load counters: worst control-step late-fire and worst single loop pass (µs) |
| `TELEM <ms>` | `TELEM 500` | Set the telemetry push period (100–10000 ms); `TELEM OFF` disables; `TELEM` reports |
| `IL` | `IL` | Report interlock mode, limits, and current heat cap (`il` push message) |
| `IL HARD` / `IL SOFT` | `IL SOFT` | Set the interlock mode explicitly (see [Fan interlock](#fan-interlock)) |
| `IL <fanMin> <fanFull> <heatAtMin>` | `IL 48 55 30` | Set the interlock limits; validated (`1 ≤ fanMin ≤ fanFull ≤ 100`, `heatAtMin ≤ 100`), applied immediately, NVS-persisted |
| `COOL` | `COOL` | Report the cooldown guard state (`cool` push message) |
| `COOL MIN <level>` | `COOL MIN 50` | Set the fan level enforced while cooling down (1–100; 0 is rejected — it would defeat the guard). Applied immediately to a held fan, NVS-persisted |
| `COOL DWELL <s>` | `COOL DWELL 90` | Set the release dwell (1–3600 s, NVS-persisted): how long the inlet must stay below 70 °C before the fan releases. Size it to outlast soak-back or the guard will cycle the fan |
| `COOL ON` / `COOL OFF` | `COOL OFF` | Arm / disarm the cooldown guard. `OFF` releases any deferred fan level immediately (operator escape hatch, e.g. an inlet sensor stuck hot). Runtime-only — every reboot re-arms |
| `AMB` | `AMB` | Report the ambient state (`amb` push message): source, the value reported to Artisan, cold-start capture, cold junction, manual value |
| `AMB SRC COLD\|CJ\|MANUAL` | `AMB SRC CJ` | Select the ambient source reported to Artisan as `AT` (NVS-persisted): the cold-start capture (default), the live MAX31855 cold junction, or the manual value — see [Ambient temperature](#ambient-temperature-at) |
| `AMB <degC>` | `AMB 22.5` | Set the manual ambient value (−40…60 °C) and switch the source to manual, NVS-persisted. Always °C — the dashboard's °F entry converts before sending |
| `CURVE` | `CURVE` | Report both dimmer curve modes (`curve` push message) |
| `CURVE HEAT\|FAN <0-2>` | `CURVE FAN 0` | Set a channel's dimmer curve: 0=linear, 1=rms, 2=log. Runtime-only — reboot restores RMS |
| `DLRESET HEAT\|FAN` | `DLRESET FAN` | Soft-reset a stuck dimmer module. **The module output goes to full for ~3–4 s during the reset** — `DLRESET HEAT` is refused unless the fan is at or above the interlock minimum |
| `LOG` | `LOG` | Retrieve the error log (sent only to requesting client) |

> **Changed in v0.10.0:** bare `IL` used to *toggle* the mode; it now reports.
> A toggle desyncs against a stateful dashboard — use `IL HARD` / `IL SOFT`.

Numeric arguments are validated strictly: an invalid value (e.g. `OT1 x`) is
rejected with an `error` push back to the sender — never coerced to `0`.

**Heat is power-linearized** (v0.11.0): on the RMS curve the dimmer level maps
linearly to V<sub>rms</sub>, so heater power would go as level². Commanded heat
passes through a √ map at the hardware write, making **heat % proportional to
watts** — constant plant gain for the PID across the range, and the
feedforward's heat ∝ power assumption holds. The map is active only while the
heat curve is RMS (`CURVE` reports `heatPowerMap`). Gains/`ffK` identified
before v0.11.0 are in raw dimmer units — **re-run `TUNE` and `FF CAL`**.

> **Quantization note.** The map's slope falls below 1 above ~25% power, so
> some adjacent heat commands collapse to the same dimmer level (~2:1 near full
> scale: `OT1 96` and `OT1 97` both drive level 98). This is the hardware's
> true power resolution made visible, not a loss from the map — the DimmerLink
> has 101 discrete V<sub>rms</sub> steps, and P ∝ V² means one step near full
> scale spans ~2% of max power however it is commanded. In closed loop
> (`INLET`, the normal mode) it is immaterial: the integrator dithers between
> adjacent levels, so *average* power resolves finer than one step.

Sending `OT1 <value>` (manual heat) at any time is an **instant override**: it
drops the controller out of closed-loop mode and applies the manual level.

All unsolicited messages use Artisan's push message envelope so any client can use a consistent format:

**Status broadcast** (sent to all clients on any state change, and to new clients on connect):

```json
{"pushMessage": "status", "data": {"heat": 60, "heatReq": 60, "fan": 50, "ilCap": 100, "ilSoft": false, "mode": "manual", "inSV": 0.0, "cool": false}}
```

| `data` field | Description |
|-------|-------------|
| `heat` | Actual heat level applied to the dimmer (%) |
| `heatReq` | Requested heat level before interlock (%) |
| `fan` | Fan level (%) |
| `ilCap` | Current heat ceiling imposed by the interlock (0–100%); `0` means heat is fully blocked, `100` means unrestricted |
| `ilSoft` | `true` if soft (linear) interlock mode is active; `false` for hard (binary) mode |
| `mode` | `"manual"` (heat set directly by `OT1`), `"inlet"` (heat modulated by the closed loop), or `"tune"` (a step test is running) |
| `inSV` | Inlet setpoint (°C) in use when `mode` is `"inlet"` |
| `cool` | `true` while the cooldown guard is holding the fan up with a deferred level pending (see [Cooldown guard](#cooldown-guard)) |

**Telemetry broadcast** (periodic, default 1 Hz, 2 Hz during a tune — the
dashboard's data feed; `TELEM <ms>|OFF` adjusts):

```json
{"pushMessage": "telem", "data": {"t": 123456, "IN": 182.4, "BT": 165.1, "ET": 0.0,
  "cj": 27.3, "amb": 21.9,
  "sv": 185.0, "heat": 42, "heatReq": 42, "fan": 57, "ilCap": 100, "mode": "inlet",
  "p": 3.9, "i": 35.2, "d": 0.0, "ff": 0.0, "fltIN": 0, "fltBT": 0}}
```

`t` is device millis; `cj` is the MAX31855 cold-junction (board/enclosure)
temperature and `amb` the ambient value currently reported to Artisan (see the
`AMB` command); `p`/`i`/`d`/`ff` are the last control-step term values
(meaningful in `inlet` mode); `fltIN`/`fltBT` flag a channel currently in the
debounced-fault state (its value is held, not live).

**Error broadcast** (sent to all clients when an error is logged):

```json
{"pushMessage": "error", "data": "DimmerLink 0x51 ERR_PARAM (0xFE)"}
```

**Log response** (sent only to the client that sent `LOG`):

```json
{"pushMessage": "log", "data": "DimmerLink 0x52 not ready after 3 tries"}
{"pushMessage": "log", "data": "no errors"}
```

### Serial (115200 baud)

Accepts the same command set as WebSocket, terminated by newline. Maximum command length is 32 bytes. `LOG` prints the error log to Serial, one entry per line prefixed with `[LOG]`.

---

## Fan interlock

The interlock prevents the heating element from running without adequate airflow. It is always active and has two modes, set with `IL HARD` / `IL SOFT` (default: hard).

The mode **and** the three limits are runtime-configurable — from the dashboard's Interlock panel or directly with `IL <fanMin> <fanFull> <heatAtMin>` — and persist in NVS like the controller tunings (the compile-time `*_DFLT` constants are only the first-boot defaults). Values are validated on set *and* on load; inconsistent NVS data falls back to the defaults rather than a weaker interlock.

### Hard mode (default)

Binary cutoff: heat is forced to `0` when `fan < fanMin`, and fully unrestricted otherwise.

### Soft mode

Linear ramp between two breakpoints (shown with the default limits):

| Fan level | Heat cap |
|-----------|----------|
| `< fanMin` (48) | 0% (blocked) |
| `fanMin` (48) | `heatAtMin` (30%) |
| `fanFull` (55) | 100% (unrestricted) |
| `> fanFull` | 100% |

Between `fanMin` and `fanFull` the cap is interpolated linearly, so heat scales with airflow rather than snapping on at a threshold.

In both modes:
- `heatReq` tracks what the user commanded
- `heat` reflects what is actually applied after capping
- Heat adjusts automatically whenever the fan level changes
- The interlock is re-evaluated every loop iteration

---

## Cooldown guard

The interlock stops heat without airflow; the cooldown guard is its mirror —
it stops the **airflow from quitting while the roaster is still hot**. It is
armed by default and enforces minimum fan-shutdown criteria: the fan may stop
only once the inlet has stayed below `COOL_FAN_OFF_C` (70 °C) for the release
dwell (`COOL DWELL`, default 30 s, NVS-persisted) on fresh sensor readings,
with the heater off. Size the dwell to outlast the roaster's soak-back — after
the fan stops, heat stored in the element and body re-warms the stagnant inlet
air, and a too-short dwell releases early and cycles the fan (observed on
hardware at 30 s: two re-enforce cycles after the first release).

**Deferred fan-off.** An `OT2` command below the cooldown fan minimum
(`COOL MIN`, default 50, NVS-persisted) while the inlet is at or above 70 °C
is deferred, not obeyed: the fan holds at the minimum, the sender gets an
`error` push explaining the hold, and the requested level applies itself
automatically once the criteria are met (a `cool` push and status update
announce the release). So the normal end-of-roast sequence is simply
`INLET 0` (heat off) then `OT2 0` — the firmware runs the cooldown and stops
the fan when it is actually safe to.

**Autonomous enforcement.** If the roaster is hot with the fan below the
minimum — a hot boot where the RTC fan shadow was lost, or inlet soak-back
after the fan was released — the guard forces the fan up to the cooldown
minimum on its own (logged), and in manual mode zeroes the requested heat so
the raised fan cannot silently un-block a previously interlock-capped heat
level. If the
temperature rebounds past 70 °C after a release, enforcement kicks the fan
back on: "below 70 °C" must genuinely *hold*.

**Fail safety and the escape hatch.** Decisions use the hold-last-good inlet
value, so a sensor that dies while hot keeps the fan running; the release
additionally requires readings fresher than `INLET_PV_STALE_MS`. If that ever
strands the fan on (e.g. an inlet sensor stuck at a hot reading), `COOL OFF`
disarms the guard and applies the deferred level immediately. The disarm is
runtime-only — every reboot re-arms the guard. `COOL` reports the guard state
at any time; the OLED shows `Cool: fan held` while a release is pending and
`Cool guard OFF` while disarmed.

---

## Inlet temperature control

The controller can hold a target **inlet** temperature itself, closing the loop
on-device instead of relying on Artisan's 1 Hz command cycle. This is a
switchable mode layered on top of manual heat control.

### Modes

| Mode | How heat is set |
|------|-----------------|
| `manual` (default) | Heat is whatever `OT1` last commanded |
| `inlet` | Heat is modulated by a PI(D) loop to hold the inlet setpoint |

- `INLET <degC>` engages `inlet` mode (bumpless — no heat step on engage) and
  sets the setpoint. Sending `INLET` again just retargets the setpoint and keeps
  the integrator, so a gradually-changing setpoint during a roast (e.g. driven
  from an Artisan background profile) does not reset the loop.
- `INLET 0` (or any setpoint ≤ 0) means "no setpoint": returns to `manual`
  with heat 0. A heater cannot track 0 °C, and Artisan's SV slider parks at 0
  at the end of a background playback — treating that as a target would leave
  the loop railed with heat pinned at 0.
- `INLET OFF` returns to `manual`, holding heat at its current level.
- `OT1 <value>` is an instant manual override (drops back to `manual`).

**Failsafe.** The loop lets go — drops to `manual` at **heat 0** and logs/
broadcasts an error — if the inlet reading goes stale (no accepted sample for
`INLET_PV_STALE_MS`, 3 s) or exceeds `INLET_OVERTEMP_C` (350 °C). Stale matters
because a faulted sensor *holds* its last good value: without the freshness
check the integrator would wind against a frozen reading indefinitely. The fan
keeps running (airflow only cools once the heater is off).

### Driving the setpoint from a roast profile (Artisan event playback)

Rather than nudging `INLET` by hand, the setpoint can follow a planned curve by
letting Artisan **replay a background profile's events**. Artisan's background
event playback (replay *by time*) linearly interpolates a custom event slider
between successive events and fires the slider's action on every sample tick — so
a handful of points become a smooth setpoint ramp streamed to the firmware:

```
background .alog  →  Artisan replays T_inlet events (ramped, by time)
                  →  slider action: send({"command":"INLET","value":{}})
                  →  firmware INLET <degC>  →  closed-loop inlet control
```

Because `INLET` retargeting is bumpless (the loop keeps its integrator), the
interpolated stream drives the setpoint without resetting the loop between points.

**Artisan setup** (a configured example lives in `artisan/`):

1. **Custom event slider** on event type 3, named `T_inlet`, action **WebSocket**
   `send({{"command":"INLET","value":{}}})`, **Temp** ticked, unit `C`.
2. **Config › Background › Playback**: tick **Playback Events**, set replay to
   **by time**, and tick **Playback** + **Ramp** on the `T_inlet` row. An optional
   **Ramp lookahead** of a few seconds leads the setpoint against system lag.
3. Load the generated profile as the background — its events are charge-aligned,
   so the schedule begins when you mark **CHARGE**.

> The background profile's event-type name for slot 3 **must** be `T_inlet` (it has
> to match the foreground event type), or Artisan silently skips the replay.

**Generating a profile.** `artisan/make_inlet_background.py --events N` samples a
shaped curve into `N` discrete `T_inlet` events (default 8), progressively
concentrated over the final portion of the roast so the setpoint has the finest
resolution through the development phase and the drop:

```
python3 artisan/make_inlet_background.py --mode ror_endpoint \
    --T_start 175 --T_drop 245 --t_drop 330 --ror_start 22 \
    --unit C --events 8 --out inlet_events.alog
```

Curve shape comes from the same parameters in either output mode (`ror_endpoint` /
`anchor` / `ror`); `--events` only changes *how* it is written — discrete playback
events here, versus a continuous channel for Artisan's software-PID "Follow
Background" mode without it. See the script's `--help` for `--tail-width` /
`--tail-bias` (point clustering toward the drop) and the anchor/RoR modes.

### Control law

`controlStep()` runs on a fixed cadence (`CONTROL_PERIOD_MS`, default 250 ms)
from the main loop. The law is intentionally isolated in that one function
operating on shared globals — the *seam* that lets it move to a dedicated
FreeRTOS task later without changing the math (see `work.md`). It is currently
**cooperative** (single-core): adequate for a thermal plant with tens-of-seconds
time constants, and free of the cross-core I²C/SPI bus contention a dedicated
control task would introduce. The `STAT` command reports the worst observed
control-step timing jitter as evidence on whether a dedicated core is ever
warranted.

Key properties:
- **Derivative on measurement** (no setpoint-change kick), low-pass filtered.
- **Back-calculation anti-windup** against the *actually applied* heat — i.e.
  post-interlock — so the fan interlock capping heat does not wind up the
  integrator.
- Starts **PI-only** (`Kd = 0`); the inlet thermocouple is noisy near the
  dimmers (see [hardware/emi.md](hardware/emi.md)), so derivative is added only
  after the plant is characterized.

### Tuning

> ⚠️ The default gains (`pidKp`/`pidKi`/`pidKd` in the firmware) are **untuned
> placeholders** and are not expected to control well. Characterize the plant
> with `TUNE` (below) and apply gains before relying on closed-loop control.

- `PID` reports the current gains, setpoint, and mode.
- `PID <kp> <ki> <kd>` sets the gains live over WebSocket/serial, so you can tune
  without recompiling.

#### Autotune (`TUNE`)

`TUNE` runs an **open-loop step test**: it holds the current heat to measure a
baseline inlet temperature, applies a heat step, records the response, fits a
first-order-plus-dead-time (FOPDT) model (two-point 28.3%/63.2% method), and
suggests PI gains via the SIMC rule at two robustness levels.

**Procedure**

1. Set the fan to a representative level (your normal roasting range) and a
   moderate heat, and let the inlet temperature settle.
2. Send `TUNE` (default step) or `TUNE <pct>` (e.g. `TUNE 20`). The display shows
   `Tuning...` and `mode` becomes `tune`.
3. The test holds baseline (~8 s), steps heat up, and watches until the response
   flattens (or a 180 s cap). Heat returns to baseline and mode returns to
   `manual` automatically.
4. The result is broadcast as a `tune` push message:
   ```json
   {"pushMessage":"tune","data":{"ok":true,"settled":true,"fan":57,"step":15,"dT":42.3,
     "Kp":2.82,"tau":18.5,"theta":3.2,
     "tight":{"kp":1.97,"ki":0.13},"cons":{"kp":0.79,"ki":0.05}}}
   ```
   - `settled:false` means the test hit the 180 s cap before the response
     flattened — the fit underestimates `dT` and the suggested gains run hot.
     Re-run longer/steadier before trusting them.
   - `Kp` (°C/%), `tau`, `theta` (s) are the identified plant model.
   - `tight` is the brisker suggestion (tracking-first); `cons` is more
     conservative. Start with `tight`, fall back to `cons` if it overshoots or
     oscillates.
5. Apply gains with `TUNE APPLY` (uses the `tight` set) or `PID <kp> <ki> <kd>`
   to enter a chosen pair manually. Then `INLET <degC>` to run closed-loop.

**Safety / aborts.** The step goes through the fan interlock, so inadequate
airflow aborts the test (`interlock capped step`). It also aborts on over-temp
(`> 280 °C` inlet) and on any `OT1`/`INLET`/`TUNE ABORT`. A failed fit reports
`{"ok":false,"reason":...}`.

Because plant gain and time constant vary with airflow, run `TUNE` at the center
of your fan range (~57). The feedforward below — not the PID gains — is the main
mechanism for robustness against airflow changes.

### Feedforward (airflow compensation)

Steady-state heater power scales with airflow × temperature rise, so the
controller adds a feedforward term:

```
heat_ff = ffK · fan · (SV − ambient)
```

summed into the control output. The PID then only has to trim the residual. The
payoff is **airflow rejection**: when the fan changes mid-roast, `heat_ff` moves
*immediately* in proportion, instead of waiting for the inlet temperature to
drift and the integrator to catch up. One coefficient covers the narrow fan band.

Feedforward is **off by default** (`ffK = 0`), and `ffK` persists in NVS with
the tuning set — check `FF` before trusting an old value.

**Preferred calibration — fan-step slope (dashboard "FF step cal" panel).**
FF's job is fan rejection, so calibrate the fan *sensitivity* directly: with
the inlet loop holding a roast-representative setpoint, the routine measures
steady heat, steps the fan (default +7), waits for re-settle, restores the
fan, and computes

```
ffK = Δheat / (Δfan · (SV − ambient))
```

then offers the result for one-click apply (`FF <k>`). Run it from the
dashboard's **FF step cal** panel — the logic is entirely client-side (the
firmware only sees ordinary `OT2`/`FF` commands). Requires `amb` to be set
(`FF AMB`) and a setpoint comfortably above ambient.

**Why not `FF CAL` at low temperature:** `FF CAL` fits a line *through the
origin* from a single operating point (`ffK = heat / (fan·(inlet−ambient))`).
This plant has a significant standing-loss intercept (measured: 25% heat at
ΔT≈25 °C but only ~50% at ΔT≈115 °C), so a through-origin fit calibrated
during warmup over-predicts badly at roast temperature — observed as `FF=80`
when the plant needed 50. The slope method is immune to the intercept. If you
do use `FF CAL`, run it at a steady roast-representative temperature.

The integral term absorbs whatever the feedforward gets wrong — including
negative trim against an over-prediction (its bounds are `I ∈ [−ff, 100−ff]`,
keeping the steady command `I+FF` within 0..100). `FF` reports as an `ff`
push message: `{"ffK":0.00451,"amb":24.0,"ff":38.7}`; `FF <k>` sets the
coefficient by hand; `FF OFF` disables.

---

## Commissioning

Bring the controller up in this order. Every step after the flash is a command
sent over WebSocket — the dashboard at [dashboard.html](dashboard.html)
has a **Commissioning sequence** panel that walks these steps with the value
fields prefilled, plus a live chart, PID/FF editors, and a filtering console
that captures the log (the device keeps only 8 entries in RAM — save from the
dashboard).

1. **Flash.** With the board connected, run `./verify.sh upload` on the host.
2. **Sanity.** Stay in `manual`; confirm sensors, OLED, and Artisan still behave.
   After a few minutes send `STAT` to read control-cadence jitter — this is the
   evidence on whether the cooperative single-core design holds (expect
   single-digit ms).
3. **Characterize.** Set the fan to the center of your range (`OT2 57`) and a
   moderate heat (`OT1 40`), let the inlet temperature settle, then run `TUNE`.
   Eyeball the reported `dT`/`Kp`/`tau`/`theta` for sanity.
4. **Apply gains.** `TUNE APPLY` uses the `tight` suggestion; if it looks twitchy,
   enter the `cons` set by hand with `PID <kp> <ki> <kd>`.
5. **Calibrate feedforward.** Still steady, send `FF AMB <ambient>` then `FF CAL`.
6. **Close the loop.** `INLET <degC>` near the current inlet temp (bumpless), then
   nudge the setpoint and watch tracking.
7. **The real test.** With the loop holding, deliberately change fan speed and
   confirm the inlet temperature barely moves — that is the feedforward earning
   its keep. Tune gains from there.

## OLED display layout

```
+--------------------------------+
|  airRoaster vX.Y.Z             |  ROW1 (firmware version)
|  Heat: 60        Req: 60       |  ROW2
|  Fan: 50                       |  ROW3
|  IL:H ok                       |  ROW4 (interlock status — see below)
|  Inlet SV:165                  |  ROW5 ("Inlet: off" in manual mode)
|  192.168.1.42                  |  ROW6 (IP address or "No WiFi")
|  Cool: fan held                |  ROW7 (cooldown guard; blank when idle, "Cool guard OFF" when disarmed)
|  B:198.4 E:212.0 I:264.1       |  ROW8 (BT / ET / inlet temps, °C)
+--------------------------------+
```

ROW4 interlock status values:

| Display | Meaning |
|---------|---------|
| `IL:H ok` | Hard mode, fan above threshold, heat unrestricted |
| `IL:S ok` | Soft mode, fan above `fanFull`, heat unrestricted |
| `IL:S cap=N%` | Soft mode, fan in ramp zone, heat capped at N% |
| `IL:H BLOCKED` | Hard mode, fan below `fanMin`, heat forced to 0 |
| `IL:S BLOCKED` | Soft mode, fan below `fanMin`, heat forced to 0 |

---

## Error logging

Errors are stored in a RAM-only circular buffer (8 entries × 64 chars). No flash writes are performed. The log is lost on reboot — the dashboard's console buffer is the durable record (it requests `LOG` on connect and can save the session to a file).

Errors are generated for:
- DimmerLink not ready at startup (after 3 retries)
- DimmerLink error register non-zero after a write (`ERR_SYNTAX`, `ERR_NOT_READY`, `ERR_INDEX`, `ERR_PARAM`, or unknown code)
- DimmerLink error register polled every 5 seconds during operation — **diagnostic logging only**, rate-limited per module (a repeating identical state logs once a minute), with "not responding" distinguished from module error codes. Register reads are unreliable while a module is firing (see [hardware/emi.md](hardware/emi.md)), so nothing acts on them; instead each module's curve + level are unconditionally re-asserted every 5 s (writes are reliable), and the level readback is checked only when a channel is commanded off. A module is **never soft-reset automatically** — a DimmerLink soft reset drives its output to full for ~3–4 s; use `DLRESET` deliberately if a module is truly stuck
- DimmerLink level write failures (rate-limited), and a channel reading back non-zero while commanded off
- Sensor faults (MAX31865 fault codes, MAX31855 fault bits), debounced and rate-limited; the channel holds its last good value during a fault
- Inlet-control failsafe events (stale PV / over-temp)

Retrieve the log at any time by sending `LOG` over WebSocket.

---

## Artisan integration

A ready-to-import Artisan settings file is provided at `artisan/airRoaster.aset` in this repo.

**Before importing**, open the file in a text editor and replace `<device-ip>` with your ESP32's IP address (shown on the OLED at startup). Then import via **File › Load Settings** in Artisan.

| Artisan setting | Value |
|-----------------|-------|
| Device | WebSocket (id 111) |
| Host | your ESP32's IP |
| Port | 81 |
| Input 1 → BT | `BT` node — bean RTD (the connected probe) |
| Input 2 → ET | `ET` node — second RTD (no probe yet; reads ~0) |
| Input 3 → IN | `IN` node — inlet thermocouple |
| Slider 0 | Fan — sends `OT2;<value>` |
| Slider 1 | Heat — sends `OT1;<value>` |

A third, temperature-scaled `T_inlet` slider sends `INLET` for closed-loop
control and can be driven automatically from a background profile — see
[Driving the setpoint from a roast profile](#driving-the-setpoint-from-a-roast-profile-artisan-event-playback).

**Configuring the WebSocket inputs.** In Artisan, under **Config › Port ›
WebSocket**, set the input node names to match the firmware's JSON fields:
**Input 1: `BT`, Input 2: `ET`, Input 3: `IN`** (i.e. `channel_nodes=BT, ET, IN`
in the `.aset`). The node names just select which JSON field feeds each curve.

If a channel reads 0 °C / 32 °F while live data appears on a *different* curve,
the cause is almost always the **firmware** reading the wrong board for that
channel — confirm `CS_RTD_BT` points at the MAX31865 the bean probe is actually
wired to (see [hardware/pins.md](hardware/pins.md)). It is *not* an Artisan
channel-order issue.

The `ET` channel returns `0.0` until a second RTD probe is wired and
`RTD_ET_ENABLED` is set to `1` in the firmware.

### Ambient temperature (AT)

Every `getData` response carries an `AT` node: the ambient temperature in °C,
from the source selected with `AMB SRC` (dashboard: Ambient panel; NVS-persisted):

- **cold-start memory** (default) — once per boot, when the BT RTD (sitting in
  the air path) agrees with the MAX31855 cold junction within 8 °C, the roaster
  provably started cold and the RTD reading is saved as the ambient
  measurement. A power cycle on a *hot* roaster fails that match, so the
  capture from the last genuinely cold boot is kept, not overwritten.
- **cold junction** — the live MAX31855 die temperature. Tracks the enclosure,
  which runs a little warm while powered; useful as a continuous estimate.
- **manual** — a value entered on the dashboard (°F or °C entry; sent to the
  firmware in °C). `AMB <degC>` sets it and switches the source to manual.

**Getting it into Artisan.** Artisan fills the ambient temperature in **Roast
Properties** automatically at CHARGE from a configured source curve
(**Config › Device › Ambient** tab). To feed it from the firmware:

1. Add a WebSocket extra device (**Config › Device › Extra Devices**, device
   "WebSocket 34") — same host/port as the main device; label a channel e.g.
   `AT` (uncheck its Curve/LCD boxes if you don't want it plotted).
2. Under **Config › Port › WebSocket**, set that channel's data node to `AT`.
3. On the **Config › Device › Ambient** tab, select that channel as the
   **Temperature** source.

Artisan samples the channel at CHARGE and stores it with the roast's ambient
conditions (it converts to the display unit itself — the wire value stays °C).

This is deliberately separate from `FF AMB` (the feedforward's reference
temperature): `AT` is roast metadata, `ffAmbient` is a control-law parameter.

### Adding more sensors

Artisan supports up to 10 channels via WebSocket: 2 on the main device plus 2 per extra device (max 4 extra devices), all pointing at the same `ws://<device-ip>:81`. The 10-channel ceiling is a total across the main device and all extra devices combined.

**To add channels** (firmware):
1. Add a global float for the new sensor
2. Extend the `data` object in `handleArtisanRequest()`:
   ```cpp
   snprintf(buf, sizeof(buf),
            "{\"id\":%s,\"data\":{\"BT\":%.1f,\"ET\":%.1f,\"inlet\":%.1f}}",
            idStr, btTemp, etTemp, inletTemp);
   ```

**To expose new channels in Artisan** (up to 10 total):
- For the first 2 channels beyond BT/ET, add node names to `channel_nodes` in the main device's `.aset` entry
- For additional pairs, add WebSocket extra devices in Artisan pointing at the same `ws://<device-ip>:81`, each with its own `channel_nodes` pair — they connect as additional clients and `handleArtisanRequest()` serves them all from the same `data` object with no firmware changes needed

**Beyond 10 channels:** a second WebSocket server on a different port would be required, as Artisan's framework caps at 10 channels per connection group.

---

## Dependencies

Install via Arduino Library Manager:

- [Adafruit GFX Library](https://github.com/adafruit/Adafruit-GFX-Library)
- [Adafruit SH110X](https://github.com/adafruit/Adafruit_SH110x)
- [Adafruit MAX31855](https://github.com/adafruit/Adafruit-MAX31855-library) (inlet thermocouple)
- [WebSockets by Markus Sattler](https://github.com/Links2004/arduinoWebSockets)

The MAX31865 RTD boards are **not** driven through the Adafruit library: its
read path is a blocking one-shot that defeats continuous-mode operation (see
`max31865_direct.h` for the register-level driver and the rationale, and
[hardware/emi.md](hardware/emi.md) for the fault history that motivated it).

---

## Further documentation

Deeper design notes, hardware debugging history, and development state live in
companion documents alongside this README:

| Document | What's in it |
|----------|--------------|
| [hardware/pins.md](hardware/pins.md) | Authoritative pin / bus / I2C-address map for the ESP32-S3 Feather — the ground truth for wiring. Do not invent pins; check here first. |
| [hardware/emi.md](hardware/emi.md) | How the AC dimmers couple noise into the temperature sensors, the RTD fault/noise history, and the mitigations. Read before touching `serviceRtd()` or the robust-read constants. |
| [hardware/triac-protection.md](hardware/triac-protection.md) | Protecting the RBDimmer triac modules against the observed fan-channel failure (failed-closed / full output): snubber placement, MOV/TVS transient suppression, inductive-fan vs. resistive-heater differences. |
| [max31865_direct.h](max31865_direct.h) | The register-direct MAX31865 RTD driver (continuous auto-convert mode) and the rationale for not using the Adafruit library. |
| [artisan/artisan_config_context.md](artisan/artisan_config_context.md) | End-to-end Artisan setup context: reading BT/ET from Phidget modules and driving the roaster over WebSocket. |
| [artisan/artisan_help_sliders.md](artisan/artisan_help_sliders.md) | Reference dump of Artisan's custom-button / event-slider configuration fields (upstream help text). |
| [state-current.md](state-current.md) | Development state: the active effort, plus a "read this first" framework overview for anyone (human or LLM) picking the project up. |
| [state-plan.md](state-plan.md) | Planned work, phase specifications, and the remaining on-roaster validation checklist. |
| [state-archive.md](state-archive.md) | Completed work, code-review findings (F-numbers), and decided-and-done rationale — the durable historical record. |
| [work.md](work.md) | Future-work scratchpad and utility notes (e.g. the `make_inlet_background.py` inlet-SV background profile generator). |

---

## License

MIT — see [LICENSE](LICENSE).
