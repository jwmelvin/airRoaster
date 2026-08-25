# vision/

Tooling for the camera-based circulation metric. The plan, architecture, and
phase gates live in [../vision.md](../vision.md); this directory holds the code.

## Camera decision — settled 2026-08-25

The **Logitech HD Pro Webcam C920 passed** the § UVC probe procedure. Phase 1
proceeds on hardware already on hand; the Basler dart is not required. Full
results are recorded in [../vision.md](../vision.md) under "Record here".

| | |
|---|---|
| Vendor / product | `0x046d` / `0x082d` |
| OpenCV index | **0** (`cv2.CAP_AVFOUNDATION`) — *not* the ffmpeg index |
| Frame rate | 30.0 fps @ 1280x720, 1 ms exposure, no drops |
| Exposure range | `3`–`2047` (0.3–204.7 ms), gain `0`–`255` |
| Lock behavior | holds, **once applied after the capture opens** |

Still open: step 8's exposure floor under real roaster lighting. At 1 ms in a
normally lit room the C920 returns a mean of 0.47 — no usable image — so the
lighting needs roughly **16x** that illumination (or ~8x at gain 255, with
noise). That is a lighting spec, not a camera problem.

## uvcc_probe.py

    ./uvcc_probe.py export              # control surface (steps 3-4)
    ./uvcc_probe.py identify            # which OpenCV index is this camera
    ./uvcc_probe.py step7               # does the lock survive capture open
    ./uvcc_probe.py step6               # decisive behavioral test
    ./uvcc_probe.py sweep               # exposure ramp + PNGs (step 8)

Defaults target the C920 at index 0; `--vendor/--product/--index` retarget it
for a different camera. Requires `brew install node libusb`,
`npm install --global uvcc`, and `opencv-python`.

The subcommands that open a capture need macOS camera permission for the
calling terminal. Approve the prompt on first run; a process without it fails
with `not authorized to capture video` rather than a useful error.

`sweep` writes PNGs to `./captures/`, which is gitignored.

## What the vision module must inherit from this

Three behaviors are baked into the probe because each one silently produces a
confident wrong answer. They are not C920 quirks to work around later — they
are requirements on however the camera gets opened in Phase 1.

1. **Apply UVC controls _after_ `cv2.VideoCapture` opens, then verify.**
   Opening the stream runs an auto-exposure pass that overwrites the lock —
   observed jumping `exposure 10 → 415, gain 128 → 255` against a dark scene.
   Code that configures the camera at init and trusts it is silently running
   at gain 255. `Uvcc.apply_lock()` is the single place this ordering lives.

2. **Never trust the device index.** OpenCV's enumeration order need not match
   `ffmpeg -list_devices`; here the C920 is OpenCV 0 but ffmpeg 1. Identify the
   camera positively by toggling a register and watching which index responds.

3. **Expect ±1-2 quantization on writes.** Setting exposure 10 / gain 128 can
   read back as 9 / 127. A stable offset is harmless — calibrate against what
   the camera actually delivers. What would wreck the metric is movement
   *during* streaming, which is what `step7` distinguishes.

A fourth, for anyone extending the probe: a monotonic exposure→brightness ramp
is the strongest single check that auto-exposure is genuinely off, because a
compensating camera cannot produce one. It is more reliable than the
lamp-switching test in the procedure, which depends on the operator holding a
lighting change steady.
