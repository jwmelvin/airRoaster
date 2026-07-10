# Configuration — airRoaster

The one-time and per-deployment configuration steps for the whole system:
credentials, the DimmerLink AC-dimmer provisioning (a factory UART→I2C switch
that must be redone for any replacement module), and the Artisan roasting-software
setup. Firmware *runtime* configuration (interlock, cooldown, tuning, ambient,
curves) is documented in the [README](README.md) command reference and persists
in NVS on the device; this file covers the setup that happens **outside** the
normal command surface.

> An alternate, Phidget-based Artisan configuration (BT/ET read from networked
> Phidget modules rather than the ESP32) is documented separately in
> [artisan/artisan_config_context.md](artisan/artisan_config_context.md). This
> file describes the all-in-firmware setup, where the ESP32 is the temperature
> source.

---

## 1. Secrets (`secrets.h`)

WiFi and OTA credentials live in `secrets.h` at the repo root. The file is
**gitignored** — it is never committed. Create it before the first build:

```cpp
#define WIFI_SSID  "your-network"
#define WIFI_PASS  "your-password"
#define OTA_PASS   "your-ota-password"   // falls back to WIFI_PASS if omitted
```

`OTA_HOSTNAME` (mDNS name for over-the-air updates, default `airroaster` →
`airroaster.local`) is a compile-time constant in `airRoaster.ino`, not a secret.

---

## 2. Firmware compile-time constants

Pins, bus assignments, and the tuning/safety defaults are `#define`s at the top
of `airRoaster.ino`. The full table is in the README
([Compile-time constants](README.md#compile-time-constants)); the pin/bus/address
map is authoritative in [hardware/pins.md](hardware/pins.md). Most operating
parameters (interlock limits, cooldown criteria, PID/feedforward, ambient source)
are runtime-settable and NVS-persisted — the constants are only first-boot
defaults. Two feature gates that *are* compile-time only:

- `RTD_ET_ENABLED` (`0`) — set to `1` once a second RTD probe is wired for ET.
- `RTD_WIRE3` (`false`) — RTD wiring; the project runs 4-wire PT1000s.

---

## 3. DimmerLink AC dimmer modules (UART → I2C provisioning)

The two RBDimmer DimmerLink modules (heat and fan) **ship from the factory with
the UART serial interface enabled** and a default I2C address of `0x50`. This
project drives them over **I2C** (heat `0x51`, fan `0x52`), so each module must
be provisioned once — over UART first, then re-addressed on I2C. This was done
manually with a separate one-off provisioning sketch (not part of the main
`airRoaster.ino`); redo it for any **replacement** module.

### Register / command reference

Source: [DimmerLink I2C protocol](https://www.rbdimmer.com/docs/dimmerlink-I2CCommunication).

| Register | Name | R/W | Notes |
|----------|------|-----|-------|
| `0x00` | STATUS | R | Device status |
| `0x01` | COMMAND | W | `0x01` RESET · `0x02` RECALIBRATE · `0x03` SWITCH_UART (revert to UART) |
| `0x02` | ERROR | R | Error codes |
| `0x03` | VERSION | R | Firmware version |
| `0x10` | DIM0_LEVEL | R/W | Output level 0–100 % |
| `0x11` | DIM0_CURVE | R/W | Dimming curve: 0 linear, 1 RMS, 2 log |
| `0x20` | AC_FREQ | R | Mains frequency |
| `0x21`–`0x22` | AC_PERIOD_L/H | R | Mains period (µs) |
| `0x23` | CALIBRATION | R | Calibration status |
| `0x30` | I2C_ADDRESS | R/W | 7-bit address, range `0x08`–`0x77`. **Writing it takes effect immediately and is saved to EEPROM** — the old address stops responding at once. |

- **UART → I2C**: send the UART command `SWITCH_I2C` (`0x5B`) over serial. I2C
  stays enabled on every subsequent power-up.
- **I2C → UART** (to undo): write `0x03` (SWITCH_UART) to the COMMAND register
  `0x01`.

### Provisioning procedure (per module, one at a time)

Do the modules **individually** — while a fresh module is still at the default
`0x50` it would collide with any other unconfigured module on the bus.

1. Connect the module over **UART serial** and send `SWITCH_I2C` (`0x5B`). It now
   speaks I2C at the default address `0x50` and will stay in I2C mode across
   power cycles.
2. On the I2C bus (default `0x50`), write the target address to register `0x30`:
   `0x51` for the **heat** module, `0x52` for the **fan** module. The change is
   instant and persisted to EEPROM.
3. Verify: the module answers at its new address (read VERSION `0x03`) and no
   longer at `0x50`. Repeat for the second module.

```cpp
// Set a module currently at 0x50 to the heat address 0x51:
Wire.beginTransmission(0x50);
Wire.write(0x30);          // I2C_ADDRESS register
Wire.write(0x51);          // new address (0x52 for fan)
Wire.endTransmission();    // effective immediately, saved to EEPROM
```

After both modules are addressed, the main firmware talks to them directly —
`initDL()` asserts the RMS curve (`0x11` ← `1`) at boot, and level writes go to
`0x10`. See [hardware/pins.md](hardware/pins.md) for the I2C bus wiring and
[hardware/emi.md](hardware/emi.md) / [hardware/triac-protection.md](hardware/triac-protection.md)
for the electrical history behind these modules.

> **Under evaluation:** moving the link back to **UART serial** — see the note in
> [state-plan.md](state-plan.md) § Later. On the project's questionable wiring the
> serial link has looked at least as noise-tolerant as I2C.

---

## 4. Artisan roasting software

Artisan reads temperatures from and sends slider commands to the ESP32 over a
single WebSocket connection (`ws://<device-ip>:81`). The device IP is shown on
the OLED at startup. A ready-to-import settings file is at
[artisan/airRoaster.aset](artisan/airRoaster.aset) — open it in a text editor and
replace `<device-ip>` with your ESP32's IP before **File › Load Settings**.

### 4.1 The key step — Config › Port › WebSocket

The WebSocket tab is where the firmware's JSON is mapped to Artisan channels.
Nothing about the channel numbering lives in the firmware: it emits one flat
`data` object with **named nodes** (`BT`, `ET`, `IN`, `AT`), and this row decides
which node feeds which Input.

**Machine**

| Field | Value |
|-------|-------|
| Host | `<device-ip>` (from the OLED) |
| Port | `81` |
| Path | *(empty)* |
| ID | `0` |
| Timeout — Connect / Reconnect / Request | `4.0` / `2.0` / `0.5` s |

**Nodes / Commands** (JSON envelope field names — match the firmware exactly)

| Field | Value |
|-------|-------|
| Message ID | `id` |
| Machine ID | `roasterID` |
| Command | `command` |
| Data | `data` |
| Message | `pushMessage` |
| Data Request | `getData` |

**Inputs** (the Nodes row — type the node name, set Mode to `C`)

| Input | Node | Mode | Source |
|-------|------|------|--------|
| 1 | `BT` | C | Bean RTD (MAX31865, the connected probe) |
| 2 | `ET` | C | Exhaust RTD (no probe yet; reads ~0 until `RTD_ET_ENABLED 1`) |
| 3 | `IN` | C | Inlet thermocouple (MAX31855) |
| 4 | `AT` | C | Ambient temperature (`AMB` source; see [README § Ambient](README.md#ambient-temperature-at)) |

For Inputs 3–4 to exist as channels, define the matching extra WebSocket
device(s) under **Config › Device › Extra Devices** (same host/port); untick the
LCD/Curve boxes for any channel you only want logged, not plotted.

`compression` may stay checked. The CHARGE/DROP message and event-node fields
(`startRoasting`, `endRoasting`, `addEvent`, `colorChangeEvent`, …) are Artisan
defaults; the current firmware does not act on them — it responds to `getData`
and to the slider commands below.

### 4.2 Sliders (heat / fan / inlet setpoint)

| Slider | Purpose | Sends |
|--------|---------|-------|
| Fan | Fan level 0–100 % | `OT2;<value>` |
| Heat | Heat level 0–100 % | `OT1;<value>` |
| `T_inlet` (temperature-scaled) | Closed-loop inlet setpoint | `INLET;<value>` |

The `T_inlet` slider can be driven automatically from a background profile — see
[README § Driving the setpoint from a roast profile](README.md#driving-the-setpoint-from-a-roast-profile-artisan-event-playback).

### 4.3 Ambient temperature into Roast Properties

To have Artisan auto-fill the ambient temperature at CHARGE, open
**Config › Device › Ambient** and select the `AT` channel (Input 4) as the
**Temperature** source. Artisan samples it at CHARGE and stores it with the
roast's ambient conditions; it converts to the display unit itself (the wire
value stays °C). The firmware's ambient source (cold-start memory / cold junction
/ manual) is chosen with the `AMB` command or the dashboard's Ambient panel —
see [README § Ambient temperature](README.md#ambient-temperature-at).

### 4.4 Troubleshooting

If a channel reads 0 °C / 32 °F while live data appears on a *different* curve,
the cause is almost always the **firmware** reading the wrong board for that
channel (confirm `CS_RTD_BT` points at the MAX31865 the bean probe is wired to,
[hardware/pins.md](hardware/pins.md)) — not an Artisan channel-order issue.
