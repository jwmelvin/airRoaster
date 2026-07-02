# utilities

## Inlet-SV background generator (`artisan/make_inlet_background.py`)

Builds an Artisan background `.alog` whose inlet setpoint curve drives the
firmware's `INLET` closed-loop control. Two output modes share the same curve
parameters (`ror_endpoint` / `anchor` / `ror`); pick shape once, choose how it's
written.

### Discrete events + ramped playback (preferred)

`--events N` writes the SV as `N` discrete **T_inlet** (event type 3) special
events sampled off the shaped curve (default 8, concentrated toward the drop).
Artisan's background-event playback (replay *by time*) linearly interpolates the
slider between them and fires `send({"command":"INLET","value":{}})` each tick, so
the points reproduce as a smooth setpoint ramp. Requires the Artisan playback
config in `artisan/airRoaster.aset` (Playback Events on, by time, T_inlet
playback+ramp).

```
python3 artisan/make_inlet_background.py --mode ror_endpoint \
  --T_start 175 --T_drop 245 --t_drop 330 --ror_start 22 \
  --unit C --events 8 --out inlet_events.alog
```

Point clustering: `--tail-width` (final fraction of the roast over which points
concentrate, finest at the drop; default 0.4) and `--tail-bias` (strength; 0 =
even spacing). Events are charge-aligned (schedule starts at CHARGE). See
`--help` for the anchor/RoR modes.

### Continuous channel (legacy, PID Follow-Background)

Without `--events`, the curve is written to extra-device channel B3 for Artisan's
software-PID "Follow Background" mode instead of the on-firmware loop.

```
python3 artisan/make_inlet_background.py --mode ror_endpoint \
  --T_start 350 --T_drop 500 --t_drop 330 --ror_start 50 --no-mirror \
  --out bkgnd_001-base_330-550_5.30.alog
```
