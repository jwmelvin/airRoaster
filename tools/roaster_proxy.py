#!/usr/bin/env python3
"""Artisan-facing authentication proxy for airRoaster.

Artisan's WebSocket client speaks plain ws:// with no authentication, so it
cannot answer the firmware's connect-time challenge (AUTH, firmware v0.18.0).
This proxy runs on the operator's machine, listens on localhost, and bridges
each Artisan connection to the roaster — answering the device's HMAC
challenge itself and relaying everything else untouched:

    Artisan ──ws://127.0.0.1:8181──▶ roaster_proxy ──ws://<roaster>:81──▶ device
                (unauthenticated,          (holds AUTH_KEY, answers
                 localhost-only)            the challenge, then relays)

Usage:
    pip install websockets
    python3 tools/roaster_proxy.py --roaster 192.168.1.109
    # then point Artisan's WebSocket Host at 127.0.0.1, port 8181
    #
    # The key is read from the repo's secrets.h automatically (the same
    # AUTH_KEY the firmware was compiled with — see tools/auth_key.py);
    # --key / --key-file / AIRROASTER_KEY env override it, in that order.

Design notes:
  - One upstream device connection per Artisan connection (Artisan's own
    reconnect logic then drives the proxy's reconnects for free).
  - The bridge is a transparent pipe with a single interception rule:
    device→client messages forward untouched EXCEPT pushMessage=="auth" —
    a challenge ({"nonce": ...}) is answered by the proxy and a state report
    ({"authed": ...}) is logged; neither is forwarded. This makes the proxy
    stateless across re-challenges, and against a device with auth disabled
    (no AUTH_KEY) it degrades to a fully transparent pipe.
  - The response is HMAC-SHA256(key, nonce-hex-string), hex-encoded — the MAC
    is over the nonce's ASCII hex exactly as received, key = the raw secret
    string bytes. Must match the firmware's authVerifyResponse().
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import os
import sys

try:
    import websockets
except ImportError:
    sys.exit("missing dependency: pip install websockets")

# Key parsing lives in auth_key.py (same directory) — secrets.h is the single
# source of truth for the shared secret on the operator machine.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth_key import read_auth_key, DEFAULT_SECRETS

log = logging.getLogger("roaster_proxy")


def auth_response(key: str, nonce_hex: str) -> str:
    return hmac.new(key.encode(), nonce_hex.encode(), hashlib.sha256).hexdigest()


def parse_auth_push(raw):
    """Return the 'data' dict of an auth push, else None."""
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(obj, dict) and obj.get("pushMessage") == "auth":
        data = obj.get("data")
        return data if isinstance(data, dict) else {}
    return None


async def pump_device_to_client(device, client, key):
    """Forward device→Artisan, intercepting only the auth pushes."""
    async for raw in device:
        data = parse_auth_push(raw)
        if data is None:
            await client.send(raw)
            continue
        if "nonce" in data:
            if key:
                log.info("challenge received (mode %s) — answering",
                         data.get("mode", "?"))
                await device.send("AUTH " + auth_response(key, data["nonce"]))
            else:
                log.warning("device sent an auth challenge but no key is "
                            "configured — privileged commands will be refused")
        elif "authed" in data:
            if data["authed"]:
                log.info("upstream connection authenticated (mode %s)",
                         data.get("mode", "?"))
            else:
                log.error("authentication FAILED — check the key; only the "
                          "open command subset will work")


async def pump_client_to_device(client, device):
    """Forward Artisan→device untouched."""
    async for raw in client:
        await device.send(raw)


async def bridge(client, roaster_uri, key):
    peer = getattr(client, "remote_address", None)
    log.info("client connected %s — dialing %s", peer, roaster_uri)
    try:
        async with websockets.connect(roaster_uri, open_timeout=5) as device:
            done, pending = await asyncio.wait(
                [
                    asyncio.ensure_future(pump_device_to_client(device, client, key)),
                    asyncio.ensure_future(pump_client_to_device(client, device)),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
    except (OSError, websockets.WebSocketException) as e:
        log.error("bridge ended: %s", e)
    finally:
        log.info("client disconnected %s", peer)


def normalize_uri(roaster: str) -> str:
    if roaster.startswith(("ws://", "wss://")):
        return roaster
    if ":" not in roaster:
        roaster += ":81"
    return "ws://" + roaster


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--roaster", required=True,
                    help="device address: host, host:port, or ws:// URI (default port 81)")
    ap.add_argument("--listen-host", default="127.0.0.1",
                    help="listen address (default 127.0.0.1 — keep it local!)")
    ap.add_argument("--listen-port", type=int, default=8181,
                    help="port Artisan connects to (default 8181)")
    ap.add_argument("--key", default=None,
                    help="shared secret (prefer AIRROASTER_KEY env or --key-file: "
                         "argv is visible in the process list)")
    ap.add_argument("--key-file", default=None,
                    help="file whose first line is the shared secret")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")

    # Key resolution, most explicit first: --key, --key-file, AIRROASTER_KEY
    # env, then the repo's secrets.h (the normal case — zero configuration).
    if args.key:
        key, src = args.key, "--key"
    elif args.key_file:
        with open(args.key_file) as f:
            key, src = f.readline().strip(), args.key_file
    elif os.environ.get("AIRROASTER_KEY"):
        key, src = os.environ["AIRROASTER_KEY"], "AIRROASTER_KEY env"
    else:
        key, src = read_auth_key(), str(DEFAULT_SECRETS)
    if key:
        log.info("key loaded from %s", src)
    else:
        log.warning("no key found (--key / --key-file / AIRROASTER_KEY / %s) — "
                    "proxy will relay but cannot authenticate", DEFAULT_SECRETS)

    uri = normalize_uri(args.roaster)

    async def run():
        async with websockets.serve(lambda ws: bridge(ws, uri, key),
                                    args.listen_host, args.listen_port):
            log.info("listening on ws://%s:%d → %s",
                     args.listen_host, args.listen_port, uri)
            await asyncio.Future()   # run forever

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("stopped")


if __name__ == "__main__":
    main()
