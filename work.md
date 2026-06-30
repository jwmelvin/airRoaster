# Development plan

## inlet-temp control

### framing

The airRoaster now measures inlet temperature, which is a primary process variable. The current system relies on external commands to regulate the heater to maintain a desired inlet temperature. That suffers from the slower reporting cycle by which Artisan receives temperature updates and sends heater commands (1 Hz). Improvement (tighter control) can come from internalizing the control loop. It will also allow flexible control strategies that Artisan may not.

### objectives

Develop a switchable operating mode that accepts "inlet" commands to set the desired inlet temperature, and implements feedback control from the measured inlet temp to modulate the heater with the tightest possible control. The control strategy and tuning should prioritize robustness against flow variation (e.g., from external fan-speed changes). Generally, the inlet setpoint will change gradually during a roast, with large transitions happening only at the start of a roast. The internal controller design should consider how it will be tuned, whether by an autotune procedure or with prescribed routines that an operator can run. 

### design considerations

- as an initial gate, consider whether this change (or other project attributes) would favor moving from the Arduino environment to ESP-IDF (https://docs.espressif.com/projects/esp-idf/en/v6.0.1/esp32s3/index.html)

- one reason for that potential migration is that the microcontroller for this project, ESP32-S3, has dual cores and the temperature-measurement-and-control aspects might benefit from separating them from the interface (WiFi, websocket, and OLED) aspects. I do not know if Arduino supports dual-core implementations but ESP-IDF does.


### constraints

- Operate the control loop with deterministic timing.
- Branch the project so that work can progress on this new capability without disturbing the current code.
- Initially plan only, no coding. 
- Consider existing work, and conduct web research to determine if the references in this prompt are the best options for this effort.

### references

- PID library for Arduino environment: https://github.com/br3ttb/Arduino-PID-Library
-- author's explanations: http://brettbeauregard.com/blog/2011/04/improving-the-beginners-pid-introduction/
-- explanation of the library's POM mode:  http://brettbeauregard.com/blog/2017/06/introducing-proportional-on-measurement/
-- and: http://brettbeauregard.com/blog/2017/06/proportional-on-measurement-the-code/ 

# utilities

## Artisan profile generator so a background can drive SV through Inlet control parameter

python3 make_inlet_background.py --out bkgnd_001-base_330-550_5.30.alog --mode ror_endpoint --no-mirror --template bkgnd_001-base.alog \
--t_drop 330 \
--T_start 350 --T_drop 500 \
--ror_start 50

