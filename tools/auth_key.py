#!/usr/bin/env python3
"""AUTH_KEY management for airRoaster (see README § Command authentication).

The command-auth shared secret lives in ONE place — `#define AUTH_KEY "..."`
in the repo's gitignored secrets.h — and is copied from there to the clients:
the firmware gets it at compile time (flash to apply), the Artisan proxy
reads secrets.h automatically, and the dashboard takes a one-time paste into
its connection-bar key field.

Subcommands (stdlib only, no dependencies):

    generate [--rotate]   Create a 32-byte (64 hex chars) key from the OS
                          CSPRNG and write it into secrets.h (creating the
                          file with placeholder WiFi credentials if absent).
                          Refuses to replace an existing key unless --rotate
                          is given: a key change locks out every client until
                          they are updated, so it must not happen by accident.
    show                  Print the current key (for pasting into the
                          dashboard on another machine).
    hmac <nonce>          Print HMAC-SHA256(key, nonce) — the exact challenge
                          response the firmware expects — for manual testing
                          from a raw WebSocket client.
    ota [--rotate]        Create/rotate a dedicated random OTA_PASS the same
                          way. Without one, the firmware falls back to
                          WIFI_PASS — which everyone on the WLAN knows by
                          definition, i.e. anyone on the network could push
                          firmware. verify.sh reads the new value
                          automatically; the first flash after a change must
                          go over USB (the device still expects the old one).

Rotation checklist (printed by `generate --rotate` too):
  1. Reflash the device:  ./verify.sh upload   (USB keeps the key off the air;
     an OTA push sends the image — key included — in cleartext on the LAN)
  2. Dashboard: paste the new key into the connection-bar field, reconnect.
  3. Proxy: nothing — it reads secrets.h on the next connection.
"""

import argparse
import hashlib
import hmac as hmac_mod
import re
import secrets as pysecrets
import subprocess
import sys
from pathlib import Path

DEFAULT_SECRETS = Path(__file__).resolve().parent.parent / "secrets.h"


def _define_re(name: str):
    # Active defines only (a commented-out template line starts with //, which
    # ^\s* does not match). New defines are written at column 0 — verify.sh's
    # sed extraction of OTA_PASS requires that.
    return re.compile(r'^(\s*#define\s+' + name + r'\s+)"([^"]*)"', re.M)

SECRETS_TEMPLATE = """\
#pragma once
// airRoaster secrets — gitignored, never commit this file.
#define WIFI_SSID   "your_ssid"
#define WIFI_PASS   "your_password"
// Optional: dedicated password for over-the-air updates (falls back to WIFI_PASS).
//#define OTA_PASS    "your_ota_password"
// Shared secret for WebSocket command authentication (README § Command
// authentication). Empty disables auth entirely. Managed by tools/auth_key.py.
#define AUTH_KEY    ""
"""


def read_define(name: str, path: Path):
    """Return a #define's string value from secrets.h, or None if absent/empty."""
    try:
        m = _define_re(name).search(path.read_text())
    except OSError:
        return None
    return m.group(2) or None if m else None


def read_auth_key(path: Path = DEFAULT_SECRETS):
    """Return the AUTH_KEY string from secrets.h, or None (imported by roaster_proxy)."""
    return read_define("AUTH_KEY", path)


def write_define(name: str, path: Path, value: str):
    rx = _define_re(name)
    if path.exists():
        text = path.read_text()
        if rx.search(text):
            text = rx.sub(lambda m: m.group(1) + '"' + value + '"', text, count=1)
        else:
            text = (text.rstrip("\n") +
                    f'\n\n// Managed by tools/auth_key.py:\n#define {name}    "{value}"\n')
    else:
        text = SECRETS_TEMPLATE.replace(f'#define {name}    ""',
                                        f'#define {name}    "{value}"')
        if f'#define {name}' not in text:   # template had no slot for it
            text += f'\n// Managed by tools/auth_key.py:\n#define {name}    "{value}"\n'
        print(f"note: created {path} with PLACEHOLDER WiFi credentials — edit them",
              file=sys.stderr)
    path.write_text(text)


def clipboard(text: str) -> bool:
    """Best-effort copy (macOS pbcopy); False if unavailable."""
    try:
        subprocess.run(["pbcopy"], input=text.encode(), check=True, timeout=5)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def cmd_generate(args):
    existing = read_auth_key(args.secrets)
    if existing and not args.rotate:
        sys.exit(f"{args.secrets} already holds a key — pass --rotate to replace it\n"
                 "(a key change locks out every client until they get the new key)")
    key = pysecrets.token_hex(32)          # 32 bytes -> 64 hex chars, 256-bit
    write_define("AUTH_KEY", args.secrets, key)
    copied = clipboard(key)
    print(f"AUTH_KEY {'rotated' if existing else 'generated'} in {args.secrets}:\n\n"
          f"    {key}\n" + ("    (copied to clipboard)\n" if copied else ""))
    print("Next steps:\n"
          "  1. flash the device:   ./verify.sh upload    # USB keeps the key off the air\n"
          "     (OTA works too, but the image — key included — crosses the LAN in cleartext)\n"
          "  2. dashboard:          paste the key into the connection-bar field, reconnect\n"
          "  3. Artisan proxy:      nothing — it reads secrets.h automatically\n"
          "  4. enforcement:        a keyed build boots in CONFIG mode (guardrails locked,\n"
          "     Artisan direct); raise to FULL with AUTH MODE FULL from an authed client")


def cmd_ota(args):
    existing = read_define("OTA_PASS", args.secrets)
    if existing and not args.rotate:
        sys.exit(f"{args.secrets} already holds an OTA_PASS — pass --rotate to replace it")
    password = pysecrets.token_hex(32)
    write_define("OTA_PASS", args.secrets, password)
    print(f"OTA_PASS {'rotated' if existing else 'generated'} in {args.secrets}\n")
    print("Next steps:\n"
          "  1. flash over USB once:  ./verify.sh upload\n"
          "     (the device still authenticates OTA with its OLD password, so this\n"
          "      first flash cannot go over the air)\n"
          "  2. thereafter:           ./verify.sh ota — it reads OTA_PASS from\n"
          "     secrets.h automatically; nothing else holds this credential")


def cmd_show(args):
    key = read_auth_key(args.secrets)
    if not key:
        sys.exit(f"no AUTH_KEY in {args.secrets} — run: tools/auth_key.py generate")
    print(key)


def cmd_hmac(args):
    key = read_auth_key(args.secrets)
    if not key:
        sys.exit(f"no AUTH_KEY in {args.secrets}")
    print(hmac_mod.new(key.encode(), args.nonce.encode(), hashlib.sha256).hexdigest())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--secrets", type=Path, default=DEFAULT_SECRETS,
                    help=f"path to secrets.h (default: {DEFAULT_SECRETS})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="create (or --rotate) the shared key")
    g.add_argument("--rotate", action="store_true",
                   help="replace an existing key (invalidates all clients)")
    g.set_defaults(func=cmd_generate)
    s = sub.add_parser("show", help="print the current key")
    s.set_defaults(func=cmd_show)
    o = sub.add_parser("ota", help="create (or --rotate) a dedicated random OTA_PASS")
    o.add_argument("--rotate", action="store_true",
                   help="replace an existing OTA_PASS (first reflash must be USB)")
    o.set_defaults(func=cmd_ota)
    h = sub.add_parser("hmac", help="compute a challenge response for a nonce")
    h.add_argument("nonce", help="the nonce hex string from the device's auth push")
    h.set_defaults(func=cmd_hmac)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
