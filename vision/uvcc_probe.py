#!/usr/bin/env python3
"""UVC camera probe for airRoaster's vision module (see ../vision.md).

Answers one question the vision plan is gated on: can a USB webcam hold a
*fixed* exposure and gain on macOS? A drifting exposure is fatal to a
motion-based circulation metric — the auto-exposure loop's own corrections
show up as apparent bean movement.

Implements § UVC probe procedure from ../vision.md. Results for the Logitech
C920 (PASS, 2026-08-25) are recorded there under "Record here".

Three findings from the first run are baked into this tool, because each one
silently produces a confident wrong answer:

  1. OpenCV's device index need not match `ffmpeg -list_devices`. On the
     development Mac the C920 is OpenCV index 0 but ffmpeg index 1. Reading
     the built-in FaceTime camera while writing UVC registers to the USB one
     looks exactly like "registers hold but the image auto-corrects". The
     `identify` subcommand pins this down positively.
  2. Opening the capture runs an auto-exposure pass that OVERWRITES the lock
     (observed: exposure 10 -> 415, gain 128 -> 255). Controls must be applied
     AFTER cv2.VideoCapture opens, then verified. `apply_lock()` is the one
     place that ordering lives; the vision module should reuse it.
  3. A dark scene invalidates the behavioral test — comparing a black frame
     against a covered lens proves nothing. `step6` refuses to run until the
     baseline is actually lit.

Requires: `brew install node libusb`, `npm install --global uvcc`, opencv-python.

Subcommands:

    identify            Which OpenCV index is this camera? Toggles the exposure
                        register and reports which index's brightness responds.
    export              Dump the camera's full UVC control surface (step 3).
    lock                Apply the manual lock the correct way and verify it.
    step6 [--cue S]     Behavioral test: does the lock survive a real luminance
                        change? Auto-selects a working exposure first.
    step7               Does the lock survive capture open, and does the
                        documented post-open re-apply make it stick?
    sweep [--out DIR]   Exposure -> brightness ramp with a PNG per step. This is
                        the step 8 run: point it into the drum under the real
                        roasting lighting.

Note for zsh users: uvcc flags must not be stashed in a plain string variable
(`V="--vendor 0x046d ..."` does not word-split and uvcc prints its usage
banner). This module passes them as a list, which sidesteps the shell entirely.
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time

try:
    import cv2
except ImportError:
    sys.exit("opencv-python is required:  pip install opencv-python")

# Logitech HD Pro Webcam C920 — the camera the probe passed on.
DEFAULT_VENDOR = "0x046d"
DEFAULT_PRODUCT = "0x082d"

# Working capture size. The C920 defaults to 1920x1080; 720p is what the
# frame-rate figure in vision.md was measured at, and the metric downsamples
# far below this anyway.
DEFAULT_W, DEFAULT_H = 1280, 720

# The manual lock. Exposure is in 100 us units, so 10 == 1 ms.
LOCK = {
    "auto_exposure_mode": 1,        # 1 = manual (2 auto, 4 shutter, 8 aperture)
    "auto_white_balance_temperature": 0,
    "auto_focus": 0,
    "absolute_exposure_time": 10,
    "gain": 128,
}
# Order matters: the auto-* switches must go off before the manual values land,
# or the auto loop overwrites them on the way past.
LOCK_ORDER = ("auto_exposure_mode", "auto_white_balance_temperature",
              "auto_focus", "absolute_exposure_time", "gain")

VERIFY_KEYS = ("auto_exposure_mode", "absolute_exposure_time", "gain", "auto_focus")


# --------------------------------------------------------------------------
# uvcc wrappers
# --------------------------------------------------------------------------

class Uvcc:
    def __init__(self, vendor=DEFAULT_VENDOR, product=DEFAULT_PRODUCT):
        self.base = ["uvcc", "--vendor", vendor, "--product", product]

    def _run(self, *args, timeout=15):
        return subprocess.run(self.base + list(args), capture_output=True,
                              text=True, timeout=timeout)

    def export(self):
        """Full control surface as a dict. {} if uvcc could not read it."""
        try:
            return json.loads(self._run("export").stdout)
        except (json.JSONDecodeError, subprocess.SubprocessError, OSError):
            return {}

    def state(self, keys=VERIFY_KEYS):
        s = self.export()
        return {k: s.get(k) for k in keys}

    def set(self, control, value):
        self._run("set", control, str(value))

    def apply_lock(self, values=None):
        """Apply the manual lock. MUST be called with the capture already open —
        see finding 2 in the module docstring."""
        values = values or LOCK
        for control in LOCK_ORDER:
            if control in values:
                self.set(control, values[control])


def open_capture(index, width=DEFAULT_W, height=DEFAULT_H, warmup=10):
    cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    for _ in range(warmup):
        cap.read()
    return cap


def grab_gray(cap, settle=1.2):
    """Read frames for `settle` seconds, return the last as grayscale. The
    settle time lets a just-written exposure change work through the pipeline."""
    end, frame = time.time() + settle, None
    while time.time() < end:
        ok, f = cap.read()
        if ok:
            frame = f
    if frame is None:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


# --------------------------------------------------------------------------
# subcommands
# --------------------------------------------------------------------------

def cmd_identify(args, uvcc):
    """Positively identify the camera's OpenCV index (finding 1)."""
    uvcc.set("auto_exposure_mode", 1)
    print("idx  resolution    mean@0.3ms  mean@40ms    delta   verdict")
    found = []
    for idx in range(args.max_index):
        cap = open_capture(idx, args.width, args.height, warmup=5)
        if cap is None:
            continue
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        uvcc.set("auto_exposure_mode", 1)      # re-apply: the open reset it
        uvcc.set("absolute_exposure_time", 3)
        lo = grab_gray(cap).mean()
        uvcc.set("absolute_exposure_time", 400)
        hi = grab_gray(cap).mean()
        delta = hi - lo
        match = delta > args.threshold
        found += [idx] if match else []
        print(f"{idx:3d}  {w:4d}x{h:<5d}  {lo:10.2f}  {hi:9.2f}  {delta:+7.2f}   "
              f"{'<-- THIS CAMERA' if match else 'not this camera'}")
        sys.stdout.flush()
        cap.release()
        time.sleep(0.4)
    uvcc.set("absolute_exposure_time", LOCK["absolute_exposure_time"])
    if not found:
        print("\nNo index responded. The camera's stream is not honouring its UVC\n"
              "registers — that fails the gate. Check it is connected and not in\n"
              "use by another application.")
        return 1
    print(f"\nUse index {found[0]}.")
    return 0


def cmd_export(args, uvcc):
    """Step 3: dump the control surface."""
    state = uvcc.export()
    if not state:
        print("uvcc returned nothing. Is the camera connected, and are the\n"
              "vendor/product IDs right? Find them with:\n"
              "  system_profiler SPUSBDataType | grep -B2 -A12 -iE 'camera|webcam'")
        return 1
    print(json.dumps(state, indent=2, sort_keys=True))
    missing = [c for c in ("auto_exposure_mode", "absolute_exposure_time", "gain")
               if c not in state]
    if missing:
        print(f"\nMISSING REQUIRED CONTROLS: {missing} — camera fails, stop here.")
        return 1
    print("\nAll required controls present (step 4 pass).")
    return 0


def cmd_lock(args, uvcc):
    """Apply the lock correctly and report what actually stuck."""
    cap = open_capture(args.index, args.width, args.height)
    if cap is None:
        return _no_capture(args.index)
    print("on open      :", uvcc.state())
    uvcc.apply_lock()
    for _ in range(10):
        cap.read()
    got = uvcc.state()
    print("after re-apply:", got)
    want = {k: LOCK[k] for k in VERIFY_KEYS}
    drift = {k: (want[k], got[k]) for k in want if abs((got[k] or 0) - want[k]) > 2}
    print("\n" + ("lock holds" if not drift else f"NOT HELD: {drift}"))
    cap.release()
    return 0 if not drift else 1


def cmd_step7(args, uvcc):
    """Does the lock survive capture open, and does re-applying make it stick?"""
    want = {k: LOCK[k] for k in VERIFY_KEYS}
    uvcc.apply_lock()
    print("before open  :", uvcc.state())
    cap = open_capture(args.index, args.width, args.height)
    if cap is None:
        return _no_capture(args.index)
    print("after open   :", uvcc.state())

    print("\n--- documented remedy: re-apply WHILE streaming ---")
    uvcc.apply_lock()
    for _ in range(10):
        cap.read()
    settled = uvcc.state()
    print("re-applied   :", settled)

    print(f"\nholding {args.hold:.0f}s while streaming:")
    start, stable = time.time(), True
    while time.time() - start < args.hold:
        for _ in range(60):
            cap.read()
        now = uvcc.state()
        stable &= (now == settled)
        print(f"  {time.time()-start:5.1f}s  {now}")
        sys.stdout.flush()
    cap.release()

    # An off-by-one or two is write quantization and is harmless; what would
    # wreck the metric is movement DURING streaming.
    exact = all(abs((settled[k] or 0) - want[k]) <= 2 for k in want)
    print()
    if exact and stable:
        print("STEP7: PASS — post-open lock holds, stable while streaming")
        return 0
    if stable:
        print(f"STEP7: PARTIAL — settled at {settled}, not {want}, but STABLE.\n"
              "       A fixed offset is harmless; calibrate against what it delivers.")
        return 0
    print("STEP7: FAIL — values drift during streaming; this camera cannot hold a lock")
    return 1


def _autoexpose(cap, uvcc, lo=70, hi=170):
    """Find an exposure that actually lights the scene (finding 3). Returns the
    chosen exposure, or None if even a long exposure leaves the frame dark."""
    print("finding an exposure that lights the scene:")
    for e in (10, 20, 40, 80, 156, 312, 625, 1000):
        uvcc.set("absolute_exposure_time", e)
        mean = grab_gray(cap).mean()
        print(f"  exp={e:5d} ({e/10:5.1f} ms)  mean={mean:6.2f}")
        if mean >= lo:
            return e
    return None


def cmd_step6(args, uvcc):
    """The decisive behavioral test."""
    cap = open_capture(args.index, args.width, args.height)
    if cap is None:
        return _no_capture(args.index)
    uvcc.apply_lock()                       # post-open, per finding 2
    for _ in range(10):
        cap.read()
    print("lock applied post-open:", uvcc.state(), "\n")

    exposure = _autoexpose(cap, uvcc)
    if exposure is None:
        print("\nScene too dark even at 100 ms. Uncover the lens or add light —\n"
              "testing against a black frame proves nothing.")
        cap.release()
        return 1
    uvcc.set("absolute_exposure_time", exposure)
    print(f"\nusing exp={exposure} ({exposure/10:.1f} ms); registers {uvcc.state()}")
    print("\n  Leave the scene alone until the cue.\n")

    registers, stop = {}, threading.Event()
    t0 = time.time()

    def poll():
        while not stop.is_set():
            registers[round(time.time() - t0, 1)] = tuple(uvcc.state().values())
            stop.wait(2.0)
    threading.Thread(target=poll, daemon=True).start()

    samples, frames, last, cued = [], 0, time.time(), False
    print("t_sec   mean     sd    fps")
    while True:
        t = time.time() - t0
        if t >= args.duration:
            break
        ok, frame = cap.read()
        if not ok:
            continue
        frames += 1
        if not cued and t >= args.cue:
            cued = True
            print("\n  >>> CHANGE THE LIGHT NOW — AND LEAVE IT CHANGED <<<\n", flush=True)
        if time.time() - last >= 0.5:
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            samples.append((t, g.mean(), g.std()))
            print(f"{t:5.1f}  {g.mean():7.2f} {g.std():6.2f}  {frames/t:5.1f}", flush=True)
            last = time.time()
    stop.set()
    cap.release()

    def window(a, b):
        vals = [m for t, m, _ in samples if a <= t <= b]
        return sum(vals) / len(vals) if vals else 0.0

    # Skip the first 4 s after the cue: that is the operator's hand, not the
    # lighting change.
    pre = window(2.0, args.cue - 1.0)
    post = window(args.cue + 4.0, args.duration - 1.0)
    delta = post - pre
    print(f"\nTOTAL frames={frames} avg_fps={frames/(time.time()-t0):.1f}")
    print(f"pre  mean={pre:7.2f}   post mean={post:7.2f}")
    print(f"delta = {delta:+.2f}  ({abs(delta)/max(pre, 1e-9)*100:.1f}% of baseline)")
    unique = set(registers.values())
    print(f"registers during run: {unique}  -> {'STABLE' if len(unique) == 1 else 'MOVED'}")

    held = abs(delta) > 0.10 * pre
    print("\nSTEP6: " + ("PASS — luminance change held" if held else
                         "FAIL — brightness returned to baseline (auto-exposure alive)"))
    if not held:
        print("       If the light did NOT stay changed, this is inconclusive, not a\n"
              "       fail — rerun and hold the change for the whole window.")
    return 0 if held else 1


def cmd_sweep(args, uvcc):
    """Step 8: exposure ramp under the lighting actually available."""
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    cap = open_capture(args.index, args.width, args.height)
    if cap is None:
        return _no_capture(args.index)
    print("on open      :", uvcc.state())
    uvcc.apply_lock()
    for _ in range(10):
        cap.read()
    print("after re-apply:", uvcc.state(), "\n")

    print("exp_req  exp_act   exp_ms    mean     sd   %clip  file")
    for e in (3, 6, 10, 20, 40, 80, 156, 312, 625):
        uvcc.set("absolute_exposure_time", e)
        g = grab_gray(cap, settle=1.5)
        actual = uvcc.export().get("absolute_exposure_time")
        path = os.path.join(out, f"exp_{e:04d}.png")
        cv2.imwrite(path, cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
        clipped = (g >= 250).mean() * 100
        print(f"{e:7d}  {actual:7}  {(actual or 0)/10:7.1f}  {g.mean():6.2f} "
              f"{g.std():6.2f}  {clipped:5.1f}%  {path}")
        sys.stdout.flush()
    uvcc.set("absolute_exposure_time", LOCK["absolute_exposure_time"])
    cap.release()
    print(f"\nFrames written to {out}/")
    print("A usable exposure is the SHORTEST one with a workable mean and little\n"
          "clipping — beans in motion need a short exposure to avoid blur.")
    return 0


def _no_capture(index):
    print(f"Could not open capture index {index}.\n"
          f"  - Run `uvcc_probe.py identify` to find the right index.\n"
          f"  - On macOS the calling terminal needs camera permission; if this is\n"
          f"    the first run, approve the prompt and try again.")
    return 1


def main():
    p = argparse.ArgumentParser(
        description="UVC camera probe for airRoaster's vision module (see ../vision.md).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Typical first run:\n"
               "  ./uvcc_probe.py export\n"
               "  ./uvcc_probe.py identify\n"
               "  ./uvcc_probe.py step7 --index N\n"
               "  ./uvcc_probe.py step6 --index N\n"
               "  ./uvcc_probe.py sweep --index N     # at the roaster\n")
    p.add_argument("--vendor", default=DEFAULT_VENDOR, help=f"USB vendor id (default {DEFAULT_VENDOR})")
    p.add_argument("--product", default=DEFAULT_PRODUCT, help=f"USB product id (default {DEFAULT_PRODUCT})")
    p.add_argument("--index", type=int, default=0, help="OpenCV capture index (default 0)")
    p.add_argument("--width", type=int, default=DEFAULT_W)
    p.add_argument("--height", type=int, default=DEFAULT_H)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("export", help="dump the UVC control surface (step 3/4)")
    sub.add_parser("lock", help="apply the manual lock correctly and verify")

    s_id = sub.add_parser("identify", help="find which OpenCV index is this camera")
    s_id.add_argument("--max-index", type=int, default=5)
    s_id.add_argument("--threshold", type=float, default=8.0,
                      help="brightness delta counting as a response (default 8)")

    s7 = sub.add_parser("step7", help="does the lock survive capture open?")
    s7.add_argument("--hold", type=float, default=30.0)

    s6 = sub.add_parser("step6", help="decisive behavioral test")
    s6.add_argument("--cue", type=float, default=12.0, help="when to change the light")
    s6.add_argument("--duration", type=float, default=45.0)

    sw = sub.add_parser("sweep", help="exposure ramp + PNGs (step 8)")
    sw.add_argument("--out", default="captures", help="output dir (default ./captures)")

    args = p.parse_args()
    uvcc = Uvcc(args.vendor, args.product)
    if not uvcc.export():
        print(f"uvcc could not read {args.vendor}:{args.product}. Is the camera\n"
              "connected? Is uvcc installed (`npm install --global uvcc`)?")
        return 1
    return {
        "identify": cmd_identify, "export": cmd_export, "lock": cmd_lock,
        "step6": cmd_step6, "step7": cmd_step7, "sweep": cmd_sweep,
    }[args.cmd](args, uvcc)


if __name__ == "__main__":
    sys.exit(main())
