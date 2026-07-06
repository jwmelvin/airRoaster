#!/usr/bin/env bash
# Compile-verify the firmware for the ESP32-S3 Feather (2MB PSRAM).
# Filters the ESP32 core's internal warnings and shows only sketch-relevant
# output plus the final pass/fail + size summary.
#
# Usage:  ./verify.sh            # compile only (verify)
#         ./verify.sh upload     # compile + upload over USB (auto-detects port)
#         ./verify.sh ota [host] # compile + push over WiFi (default airroaster.local)
#
# The FQBN pins the TinyUF2 OTA partition scheme (2×1408K app slots). The
# first flash after switching schemes must be over USB (`upload`) because the
# partition table itself can't be rewritten over the air; every flash after
# that can be `ota`.
set -euo pipefail

# Resolve to the real-case, symlink-free path. macOS is case-insensitive, so
# `cd ~/airroaster` works but hands arduino-cli a lowercase folder name, which
# it can't match against airRoaster.ino. realpath canonicalizes the case from
# the filesystem (unlike `pwd -P`, which trusts the stale $PWD env hint).
cd "$(realpath "$(dirname "$0")")"

FQBN="esp32:esp32:adafruit_feather_esp32s3:PartitionScheme=tinyuf2"
SKETCH="airRoaster.ino"

# OTA pushes need the .bin exported into ./build (gitignored). The odd
# expansion below is the bash-3.2 (macOS default) safe way to pass a
# possibly-empty array under `set -u`.
extra=()
[[ "${1:-}" == "ota" ]] && extra+=(--export-binaries)

# Pull FW_VERSION straight out of the sketch so we can confirm which build
# we're about to compile (and, for ota/upload, flash).
version="$(sed -n 's/^#define FW_VERSION[[:space:]]*"\(.*\)".*/\1/p' "$SKETCH")"
echo "==> airRoaster firmware v${version:-unknown}"

echo "==> Compiling $SKETCH for $FQBN"
# --warnings all surfaces sketch issues; we grep our own file out of the noise.
out="$(arduino-cli compile --fqbn "$FQBN" --warnings all ${extra[@]+"${extra[@]}"} "$SKETCH" 2>&1)" || {
  echo "$out" | grep -iE "error:|airRoaster" || true
  echo "==> BUILD FAILED"
  exit 1
}

# Surface any warning/error that references our sketch (should be none).
sketch_msgs="$(echo "$out" | grep -iE "airRoaster.*(warning|error)" || true)"
if [[ -n "$sketch_msgs" ]]; then
  echo "==> Sketch warnings/errors:"
  echo "$sketch_msgs"
else
  echo "==> No warnings or errors in the sketch."
fi

echo "$out" | grep -E "Sketch uses|Global variables" || true
echo "==> BUILD OK"

if [[ "${1:-}" == "ota" ]]; then
  host="${2:-airroaster.local}"
  # espota.py ships with the installed ESP32 core; pick the newest if several.
  espota="$(ls "$HOME"/Library/Arduino15/packages/esp32/hardware/esp32/*/tools/espota.py 2>/dev/null | sort -V | tail -1)"
  if [[ -z "$espota" ]]; then echo "==> espota.py not found in the ESP32 core"; exit 1; fi
  # --export-binaries writes here (arduino-cli strips the FQBN menu options).
  bin="build/esp32.esp32.adafruit_feather_esp32s3/${SKETCH}.bin"
  if [[ ! -f "$bin" ]]; then echo "==> $bin not found (export failed?)"; exit 1; fi
  # OTA password: OTA_PASS from secrets.h, else the firmware's WIFI_PASS fallback.
  pass="$(sed -n 's/^#define OTA_PASS[[:space:]]*"\(.*\)".*/\1/p' secrets.h)"
  if [[ -z "$pass" ]]; then
    pass="$(sed -n 's/^#define WIFI_PASS[[:space:]]*"\(.*\)".*/\1/p' secrets.h)"
  fi
  echo "==> Pushing $bin to $host (device must be idle: manual mode, heat 0)"
  python3 "$espota" -i "$host" -p 3232 --auth="$pass" -f "$bin"
  echo "==> OTA OK — device is rebooting into the new firmware"
fi

if [[ "${1:-}" == "upload" ]]; then
  # Prefer the port arduino-cli identifies as our FQBN; otherwise fall back to
  # the first USB serial port. Never match the Bluetooth ports (cu.BLTH,
  # cu.Bluetooth-*), which also report protocol "serial" but aren't the board.
  list="$(arduino-cli board list 2>/dev/null)"
  port="$(awk -v fqbn="$FQBN" '$1 ~ /^\/dev\// && index($0, fqbn) {print $1; exit}' <<<"$list")"
  if [[ -z "$port" ]]; then
    port="$(awk '$1 ~ /^\/dev\/cu\.(usbmodem|usbserial|wchusbserial|SLAB)/ {print $1; exit}' <<<"$list")"
  fi
  if [[ -z "$port" ]]; then echo "==> No ESP32 serial port detected"; echo "$list"; exit 1; fi
  echo "==> Uploading to $port"
  arduino-cli upload --fqbn "$FQBN" -p "$port" "$SKETCH"
fi
