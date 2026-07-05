// ===========================================================================
// airRoaster — ESP32-S3 hot-air coffee roaster controller
//
// Firmware version: see FW_VERSION below.
// Change history:   bottom of this file.
// (Intentionally no "last edited" date in this header — it only goes stale.
//  The top entry of the version history is the real last-changed date.)
// ===========================================================================
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <WiFi.h>
#include <ArduinoOTA.h>    // OTA firmware updates (espota protocol; verify.sh "ota" mode)
#include <WebSocketsServer.h>
#include <Adafruit_MAX31855.h>
#include "max31865_direct.h"   // register-level MAX31865 driver, continuous mode
#include <Preferences.h>   // NVS-backed persistence of the tuning set
#include <esp_task_wdt.h>  // task watchdog (a hung loop with heat on is the worst case)

// ---------------------------------------------------------------------------
// Firmware identity
// ---------------------------------------------------------------------------
#define FW_VERSION  "0.16.0"

// ---------------------------------------------------------------------------
// WiFi credentials (defined in secrets.h — do not commit that file)
// ---------------------------------------------------------------------------
#include "secrets.h"

// OTA is never unauthenticated: define OTA_PASS in secrets.h for a dedicated
// credential, otherwise the WiFi password is reused.
#ifndef OTA_PASS
#define OTA_PASS WIFI_PASS
#endif

// ---------------------------------------------------------------------------
// Sensor SPI chip-select pins  (assign free GPIOs to suit your wiring)
// ---------------------------------------------------------------------------
#define CS_RTD_BT   10   // MAX31865 (product 3648) — bean temp RTD (connected probe)
#define CS_RTD_ET   9    // MAX31865 (product 3648) — exhaust/ET RTD (no probe yet — disabled below)
#define CS_TC_IN    8    // MAX31855 (product 269)  — inlet thermocouple

// Set to 1 when the ET RTD probe is installed and filtered
#define RTD_ET_ENABLED  0

// MAX31865 wiring: true for 3-wire RTDs, false for 2- or 4-wire (we run 4-wire)
#define RTD_WIRE3   false

// PT1000 reference resistor on the 3648 board is 4300 Ω; nominal at 0 °C is 1000 Ω
#define RTD_REF     4300.0f
#define RTD_NOMINAL 1000.0f

// Sensor poll interval (ms) — much shorter than Artisan's sample rate
#define SENSOR_INTERVAL_MS  250

// Robust-read parameters (dimmer EMI tolerance — see hardware/emi.md)
#define RTD_VALID_MIN_C       -20.0f  // plausibility window for accepting a reading
#define RTD_VALID_MAX_C        600.0f
#define RTD_READ_DISAGREE_C    2.0f   // two same-cycle reads differing by more => SPI glitch, hold
#define SENSOR_FAULT_DEBOUNCE  4      // consecutive bad reads before a channel is declared faulted
#define SENSOR_REFAULT_LOG_MS  5000   // min interval between repeated fault-log entries (anti-flood)
#define RTD_MEDIAN_WINDOW      5      // samples in the median filter (set 1 to disable)
#define RTD_REASSERT_MS        5000   // re-assert VBIAS/auto-convert this often (silent-stall guard)

// ---------------------------------------------------------------------------
// DimmerLink I2C addresses and registers
// ---------------------------------------------------------------------------
#define HEAT_ADDR   0x51
#define FAN_ADDR    0x52

#define REG_STATUS   0x00
#define REG_COMMAND  0x01   // write ops: RESET / RECALIBRATE / SWITCH_UART
#define REG_ERROR    0x02
#define REG_VERSION  0x03
#define REG_LEVEL    0x10
#define REG_CURVE    0x11
#define REG_FREQ     0x20

#define DL_CMD_RESET 0x01   // COMMAND register value: module soft-reset

// Curve modes (register 0x11): how level maps to output
#define DL_CURVE_LINEAR  0  // linear in firing angle (Vrms S-shaped, steepest mid-scale)
#define DL_CURVE_RMS     1  // linear in output Vrms (the power-on default here)
#define DL_CURVE_LOG     2  // perceptual (LED) curve

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
#define DUTY_STEP               1    // UP/DOWN step (%): the fan responds over a
                                     // narrow band, so nudges must be fine-grained
#define WS_PORT                 81
#define DL_INIT_RETRY_DELAY_MS  500   // ms between initDL ready-check retries
#define OTA_HOSTNAME  "airroaster"    // mDNS name for espota (airroaster.local)

// Interlock config — power-on defaults only. The live values are runtime
// globals (ilFanMin / ilFanFull / ilHeatAtMin), settable over the IL command
// and persisted in NVS alongside the tuning set (loadInterlock/saveInterlock).
#define IL_FAN_MIN_DFLT      48   // fan level below which heat is always 0
#define IL_FAN_FULL_DFLT     55   // fan level at or above which heat is unrestricted
#define IL_HEAT_AT_MIN_DFLT  30   // heat cap (%) when fan is exactly at ilFanMin (soft mode)

// Safety guards
#define WDT_TIMEOUT_MS      8000    // task watchdog: panic->reset if loop() hangs this long
#define INLET_PV_STALE_MS   3000    // closed loop / tune abort if the inlet PV is older than this
#define INLET_OVERTEMP_C    350.0f  // closed loop aborts above this inlet temp (SV max is 300; tune abort is separate and tighter)

// Cooldown guard: the fan may stop only once the roaster is provably cool —
// inlet below COOL_FAN_OFF_C, sustained for the dwell on fresh readings, heat
// off. Until then, fan commands below the cooldown fan minimum are deferred
// and airflow is enforced (see serviceCooldown / COOL command). The minimum
// and dwell are power-on defaults only: the live values are coolFanMin /
// coolDwellS, settable via COOL MIN / COOL DWELL and persisted in NVS
// (loadCool/saveCool). Size the dwell to outlast the post-release soak-back:
// too short and the guard cycles the fan as stagnant heat re-warms the inlet
// (observed 2026-07-05: 30 s released early, two re-enforce cycles followed).
#define COOL_FAN_OFF_C     70.0f   // inlet must stay below this for fan shut-down (°C)
#define COOL_DWELL_S_DFLT  30      // default dwell (s) "below" must hold before release
#define COOL_FAN_MIN_DFLT  50      // fan level enforced while cooling down

// WiFi: bounded connect wait at boot; reconnection is watched from loop().
// The roaster must be fully operable over serial with no network present.
#define WIFI_CONNECT_TIMEOUT_MS  15000
#define WIFI_CHECK_MS            10000   // link watch cadence in loop()

// Telemetry push (dashboard feed): temps, setpoint, levels, mode, PID terms.
#define TELEM_PERIOD_MS       1000   // default cadence; runtime-set via TELEM command
#define TELEM_TUNE_PERIOD_MS  500    // faster while a step test is running

// ---------------------------------------------------------------------------
// Inlet-temperature control (closed loop) — see the control section below and
// work.md for the design. Cooperative for now: controlStep() runs on a fixed
// cadence from loop(); the "seam" keeps the law liftable into a FreeRTOS task
// later without changing the math.
// ---------------------------------------------------------------------------
#define CONTROL_PERIOD_MS   250     // control cadence (Hz = 1000/this); matches sensor poll
#define INLET_SV_MIN_C      0.0f    // plausibility window for an inlet setpoint
#define INLET_SV_MAX_C      300.0f
#define PID_D_FILTER_TC     1.0f    // derivative low-pass time constant (s); 0 = off
#define PID_KAW             0.1f    // anti-windup back-calculation gain (1/s)

// Open-loop step-test autotune (TUNE command). Holds the current heat to measure
// a baseline, applies a heat step, records the inlet response, fits a first-order-
// plus-dead-time (FOPDT) model, and suggests PI gains (SIMC/lambda). Run it with
// fan in the normal range and the roaster roughly steady first.
#define TUNE_STEP_DELTA     15      // default heat step (% points) if none given
#define TUNE_STEP_DELTA_MIN 5
#define TUNE_STEP_DELTA_MAX 40
#define TUNE_BASELINE_MS    8000    // hold current heat this long to measure T0
#define TUNE_MAX_MS         180000  // hard cap on the step-observation phase
#define TUNE_MIN_TEST_MS    10000   // suppress settle detection before this
#define TUNE_SAMPLE_MS      500     // response sampling interval
#define TUNE_MAX_SAMPLES    360     // 180 s at TUNE_SAMPLE_MS
#define TUNE_SETTLE_SECS    15      // response flat this long => settled
#define TUNE_SETTLE_BAND_C  1.0f    // "flat" = max-min within this band (°C)
#define TUNE_MIN_RISE_C     3.0f    // require at least this rise to identify (°C)
#define TUNE_TEMP_ABORT_C   280.0f  // abort the test above this inlet temp (°C)

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
uint8_t requestedHeatLevel = 0;  // commanded heat level
uint8_t heatLevel = 0;           // actual heat level sent to device
uint8_t fanLevel = 0;

// Fan-level shadow in RTC no-init RAM: survives every MCU-only reset
// (crash / WDT / panic / OTA reboot) — exactly the cases where the dimmer
// module keeps running and boot must re-adopt its level — and is garbage
// after a true power-on, when the module has lost power too. Validated by
// magic + inverted-copy checksum; never touches flash (no NVS wear, no
// write latency in the command path). Deliberately NOT read back from the
// module: getLevel() lies while the module is firing (emi.md § DimmerLink).
#define FAN_RTC_MAGIC  0x464E4C56UL   // "FNLV"
RTC_NOINIT_ATTR uint32_t rtcFanMagic;
RTC_NOINIT_ATTR uint8_t  rtcFanLevel;
RTC_NOINIT_ATTR uint8_t  rtcFanCheck;  // ~rtcFanLevel
// (rtcSaveFan() / rtcFanValid() defined with the DimmerLink helpers below —
// function bodies this early would move the Arduino auto-prototype insertion
// point above the struct definitions.)
bool    interlockSoft = false;   // false = hard (binary), true = soft (linear ramp)

// Interlock limits (see the IL command; persisted in NVS, defaults above).
// Invariants enforced everywhere they are set: 1 <= fanMin <= fanFull <= 100,
// heatAtMin <= 100 — fanMin == 0 would let the heater run with the fan off.
uint8_t ilFanMin    = IL_FAN_MIN_DFLT;
uint8_t ilFanFull   = IL_FAN_FULL_DFLT;
uint8_t ilHeatAtMin = IL_HEAT_AT_MIN_DFLT;

// Cooldown guard state (see serviceCooldown / the COOL command). Runtime-only:
// coolEnabled deliberately resets to true on every boot — a disarmed safety
// guard must not survive into the next session.
bool     coolEnabled   = true;   // COOL ON|OFF; OFF is the operator escape hatch
bool     coolPending   = false;  // guard holds the fan up; coolTargetFan applies when cool
uint8_t  coolTargetFan = 0;      // deferred fan level, applied once shutdown criteria are met
uint32_t coolBelowMs   = 0;      // when the inlet went below COOL_FAN_OFF_C (0 = it hasn't)
uint8_t  coolFanMin    = COOL_FAN_MIN_DFLT;  // enforced cooldown fan level (COOL MIN, NVS)
uint16_t coolDwellS    = COOL_DWELL_S_DFLT;  // release dwell, seconds (COOL DWELL, NVS)

// Active dimmer curves (CURVE command; runtime-only, never persisted — an
// experiment must not survive a reboot into a roast). Power-on default is RMS,
// asserted by initDL(). The heat power-linearization below applies only while
// heatCurve is RMS, because the sqrt map is derived from that curve's
// level-to-Vrms linearity.
uint8_t heatCurve = DL_CURVE_RMS;
uint8_t fanCurve  = DL_CURVE_RMS;
// (heatDimmerLevel() / curveFor() defined with the DimmerLink helpers below —
// function bodies this early would move the Arduino auto-prototype insertion
// point above the struct definitions.)

float btTemp  = 0.0;  // bean temp  — MAX31865 PT1000 (°C)
float etTemp  = 0.0;  // exhaust/ET — MAX31865 PT1000 (°C)
float inTemp  = 0.0;  // inlet temp — MAX31855 thermocouple (°C)

// Freshness stamp of the last *accepted* inlet reading. The hold-last-good
// policy means inTemp can be a frozen value during a fault; anything closing a
// loop on inTemp must check this age, never the value alone.
uint32_t inLastGoodMs = 0;

String inputBuffer = "";
volatile bool flagDisplayUpdate;

// ---------------------------------------------------------------------------
// Inlet control state
// ---------------------------------------------------------------------------
// Operating mode: MANUAL = heat is whatever OT1 last set; INLET = heat is
// modulated by the closed loop to hold inletSV. Marked volatile because a
// future FreeRTOS control task would read/write these across cores.
enum ctrlMode_t { MODE_MANUAL, MODE_INLET, MODE_TUNE };
volatile ctrlMode_t ctrlMode = MODE_MANUAL;
volatile float       inletSV  = 0.0f;   // inlet setpoint (°C), valid in MODE_INLET

// Autotune progress + last suggestion. Declared here (ahead of processCommand,
// which starts/aborts/applies a tune) rather than beside the tune internals.
enum tunePhase_t { TUNE_IDLE, TUNE_BASELINE, TUNE_STEP };
volatile tunePhase_t tunePhase   = TUNE_IDLE;
bool                 tuneHaveSug = false;   // a suggested-gain set is available
float                tuneSugKp   = 0.0f;    // SIMC "tight" suggestion from last tune
float                tuneSugKi   = 0.0f;

// PID gains — PLACEHOLDERS. The plant has NOT been characterized yet; these are
// deliberately gentle and are not expected to control well. Tune via the step
// test / TUNE routine (work.md phase 3) or live with the PID command before
// relying on closed-loop control. Starts PI-only (Kd = 0) — the inlet TC is
// noisy near the dimmers, so derivative is added only after characterization.
float pidKp = 1.5f;
float pidKi = 0.05f;   // 1/s
float pidKd = 0.0f;

// Telemetry cadence (ms), runtime-adjustable via TELEM <ms>|OFF; 0 disables.
uint16_t telemPeriodMs = TELEM_PERIOD_MS;

// Last control-step terms, captured for telemetry so the dashboard can show
// what the loop is doing (P/I/D contributions and the feedforward share).
// Only meaningful while mode is "inlet"; the mode field says whether to trust.
float ctlP = 0.0f, ctlI = 0.0f, ctlD = 0.0f, ctlFF = 0.0f;

// Feedforward power map (the main robustness-to-airflow mechanism). Physically,
// steady-state heat scales with airflow × temperature rise, so
//   heat_ff = ffK · fan · (SV − ffAmbient)
// One coefficient suffices across the narrow fan band; a fan change moves the
// feedforward immediately and the PID only trims the residual. ffK defaults to 0
// (feedforward off) until calibrated — see the FF command / FF CAL.
float ffK       = 0.0f;    // %·/(fan-level·°C); 0 disables feedforward
float ffAmbient = 25.0f;   // reference/ambient temp the rise is measured from (°C)

// Cooperative-cadence jitter watch (worst control-step late-fire, µs). This is
// the evidence that decides whether a dedicated core is ever warranted — read
// and zeroed via the STAT command. Declared here (ahead of processCommand,
// which reports it) rather than beside the other PID working state below.
volatile uint32_t ctrlMaxJitterUs = 0;

// Worst single loop() pass (µs). The jitter watch above can't see blocking
// that happens *inside* the pass that fires the control step (the timestamps
// are captured at loop top), so this is the honest measure of how long the
// cooperative loop can go dark — WebSocket, serial, and display service all
// stall for the duration. Read and zeroed via STAT alongside the jitter.
volatile uint32_t loopMaxUs = 0;

// ---------------------------------------------------------------------------
// Sensors
// ---------------------------------------------------------------------------
static Max31865Direct rtdBT(CS_RTD_BT, RTD_NOMINAL, RTD_REF);
#if RTD_ET_ENABLED
static Max31865Direct rtdET(CS_RTD_ET, RTD_NOMINAL, RTD_REF);
#endif
static Adafruit_MAX31855 tcIN(CS_TC_IN);

// Per-channel fault tracking (debounce + rate-limited logging) and, for the
// RTDs, a median-filter ring buffer and the stall-guard re-assert timer.
struct SensorFaultState {
    uint8_t  badCount;                // consecutive bad reads
    bool     faulted;                 // currently in the (logged) faulted state
    uint32_t lastLogMs;               // last time a fault was logged for this channel
    uint32_t lastReassertMs;          // last VBIAS/auto-convert re-assert (RTD only)
    float    hist[RTD_MEDIAN_WINDOW]; // recent accepted readings (RTD only)
    uint8_t  histHead;                // next write index into hist[]
    uint8_t  histCount;              // valid entries in hist[]
};
static SensorFaultState rtdBTfault = {0, false, 0, 0, {0}, 0, 0};
#if RTD_ET_ENABLED
static SensorFaultState rtdETfault = {0, false, 0, 0, {0}, 0, 0};
#endif
static SensorFaultState tcINfault  = {0, false, 0, 0, {0}, 0, 0};

// ---------------------------------------------------------------------------
// Display
// ---------------------------------------------------------------------------
Adafruit_SH1107 display = Adafruit_SH1107(64, 128, &Wire);
#define COL1A     0
#define COL2A     64
#define ROWHEIGHT 8

enum rows_t { ROW1, ROW2, ROW3, ROW4, ROW5, ROW6, ROW7, ROW8 };

// ---------------------------------------------------------------------------
// WebSocket server
// ---------------------------------------------------------------------------
WebSocketsServer webSocket(WS_PORT);

// ---------------------------------------------------------------------------
// Error log (RAM only — no flash writes)
// ---------------------------------------------------------------------------
#define ERR_LOG_SIZE    8
#define ERR_MSG_LEN     64

static char  errLog[ERR_LOG_SIZE][ERR_MSG_LEN];
static uint8_t errHead = 0;   // next write index
static uint8_t errCount = 0;  // total entries stored (capped at ERR_LOG_SIZE)

void logError(const char* msg) {
    strncpy(errLog[errHead], msg, ERR_MSG_LEN - 1);
    errLog[errHead][ERR_MSG_LEN - 1] = '\0';
    errHead = (errHead + 1) % ERR_LOG_SIZE;
    if (errCount < ERR_LOG_SIZE) errCount++;

    Serial.print("[ERR] ");
    Serial.println(msg);

    char buf[ERR_MSG_LEN + 28];
    snprintf(buf, sizeof(buf), "{\"pushMessage\":\"error\",\"data\":\"%s\"}", msg);
    webSocket.broadcastTXT(buf);
}

void sendLog(uint8_t clientNum) {
    uint8_t start = (errCount < ERR_LOG_SIZE) ? 0 : errHead;
    for (uint8_t i = 0; i < errCount; i++) {
        uint8_t idx = (start + i) % ERR_LOG_SIZE;
        char buf[ERR_MSG_LEN + 32];
        snprintf(buf, sizeof(buf), "{\"pushMessage\":\"log\",\"data\":\"%s\"}", errLog[idx]);
        webSocket.sendTXT(clientNum, buf);
    }
    if (errCount == 0) {
        webSocket.sendTXT(clientNum, "{\"pushMessage\":\"log\",\"data\":\"no errors\"}");
    }
}

// ---------------------------------------------------------------------------
// JSON field helpers
// ---------------------------------------------------------------------------

// Extract a quoted string field from a flat JSON object.
// Returns "" if not found.
static String jsonString(const String& json, const char* key) {
    String search = String("\"") + key + "\"";
    int pos = json.indexOf(search);
    if (pos < 0) return "";
    int colon = json.indexOf(':', pos + search.length());
    if (colon < 0) return "";
    int q1 = json.indexOf('"', colon + 1);
    if (q1 < 0) return "";
    int q2 = json.indexOf('"', q1 + 1);
    if (q2 < 0) return "";
    return json.substring(q1 + 1, q2);
}

// Extract a numeric field from a flat JSON object.
// Returns NAN if not found.
static float jsonFloat(const String& json, const char* key) {
    String search = String("\"") + key + "\"";
    int pos = json.indexOf(search);
    if (pos < 0) return NAN;
    int colon = json.indexOf(':', pos + search.length());
    if (colon < 0) return NAN;
    int start = colon + 1;
    while (start < (int)json.length() && json[start] == ' ') start++;
    return json.substring(start).toFloat();
}

// ---------------------------------------------------------------------------
// Forward declarations
// ---------------------------------------------------------------------------
void processCommand(String cmd, int8_t clientNum = -1);
void applyInterlock();
bool setFanLevel(uint8_t level);
void serviceCooldown(uint32_t now);
void sendCoolState(int8_t clientNum);
void broadcastStatus();
void broadcastTelemetry();
bool handleArtisanRequest(uint8_t clientNum, const String& msg);
void initSensors();
void updateSensors();
void serviceRtd(Max31865Direct &dev, SensorFaultState &st, float &out, const char *name);
float feedforward(float sv, uint8_t fan);
void  engageInlet(float sv);
void  controlStep(uint32_t dtMs);
void  startTune(float deltaPct);
void  abortTune(const char *why);
void  tuneStep(uint32_t dtMs);

// ===========================================================================
// Sensors — init and periodic update
// ===========================================================================

void initSensors() {
    tcIN.begin();

    // begin() puts the chip straight into continuous conversion (VBIAS|AUTO,
    // 60 Hz notch) and clears power-on faults; then arm the on-chip conversion
    // window so out-of-plausible-range conversions latch fault bits on silicon.
    rtdBT.begin(RTD_WIRE3, false /*60 Hz*/);
    rtdBT.setThresholdsRaw(rtdBT.rawFromTemp(RTD_VALID_MIN_C),
                           rtdBT.rawFromTemp(RTD_VALID_MAX_C));
#if RTD_ET_ENABLED
    rtdET.begin(RTD_WIRE3, false /*60 Hz*/);
    rtdET.setThresholdsRaw(rtdET.rawFromTemp(RTD_VALID_MIN_C),
                           rtdET.rawFromTemp(RTD_VALID_MAX_C));
#else
    // Keep the unpopulated ET board's chip select deasserted so it can never
    // chatter on the shared MISO line.
    pinMode(CS_RTD_ET, OUTPUT);
    digitalWrite(CS_RTD_ET, HIGH);
#endif

    Serial.println("Sensors initialized");
}

// Median of the valid entries in a channel's history ring (order doesn't matter).
static float rtdMedian(const SensorFaultState &st) {
    float tmp[RTD_MEDIAN_WINDOW];
    uint8_t n = st.histCount;
    for (uint8_t i = 0; i < n; i++) tmp[i] = st.hist[i];
    for (uint8_t i = 1; i < n; i++) {          // insertion sort (n is tiny)
        float key = tmp[i];
        int8_t j = i - 1;
        while (j >= 0 && tmp[j] > key) { tmp[j + 1] = tmp[j]; j--; }
        tmp[j + 1] = key;
    }
    return tmp[n / 2];
}

// Robust RTD read. Rejects single-cycle SPI glitches (two disagreeing register
// reads), median-filters accepted samples (rejects single-sample spikes),
// debounces genuine faults, holds the last good value through brief transients,
// periodically re-asserts the config byte to guard against a silently-stalled
// converter, and keeps the converter alive after a fault. The chip runs in
// continuous auto-convert mode (see max31865_direct.h), so each read here is a
// microsecond register access, not a blocking conversion. See hardware/emi.md
// for the noise story.
void serviceRtd(Max31865Direct &dev, SensorFaultState &st, float &out, const char *name) {
    uint32_t now = millis();

    // Stall guard: a transient can silently clear VBIAS/auto-convert in the
    // config register, freezing conversions while the RTD register keeps
    // returning the last latched (stale-but-plausible) value. Re-assert the
    // config periodically so the converter always recovers within
    // RTD_REASSERT_MS even with no fault flag set.
    if (now - st.lastReassertMs >= RTD_REASSERT_MS) {
        st.lastReassertMs = now;
        dev.reassert();
    }

    // Two reads this cycle: the RTD register is latched between conversions,
    // so any disagreement means the SPI frames themselves were corrupted by a
    // dimmer transient — hold the last good value, retry next cycle.
    bool f1 = false, f2 = false;
    float t1 = dev.temperatureFromRaw(dev.readRaw(&f1));
    float t2 = dev.temperatureFromRaw(dev.readRaw(&f2));
    if (fabsf(t1 - t2) > RTD_READ_DISAGREE_C) return;

    float t = 0.5f * (t1 + t2);

    // Good reading — accept even if a transient fault bit was momentarily set
    // (established policy from the EMI work: in-window data beats a flag), but
    // clear a lingering latch so the per-sample bit stays meaningful.
    if (t > RTD_VALID_MIN_C && t < RTD_VALID_MAX_C) {
        if (f1 || f2) dev.clearFault();
        st.hist[st.histHead] = t;                     // push into the median ring
        st.histHead = (st.histHead + 1) % RTD_MEDIAN_WINDOW;
        if (st.histCount < RTD_MEDIAN_WINDOW) st.histCount++;
        out = rtdMedian(st);                          // output the median, not the raw sample
        st.badCount = 0;
        st.faulted  = false;
        return;
    }

    // Out of range and consistent across both reads — candidate genuine fault.
    if (st.badCount < 255) st.badCount++;

    uint8_t fault = dev.readFaultReg();  // latched detail, intact: the read
                                         // path no longer clears it behind us
    dev.clearFault();                    // recover; also re-asserts VBIAS|AUTO
    // 'out' intentionally holds its last good value (do not zero) during the fault.

    if (st.badCount < SENSOR_FAULT_DEBOUNCE) return;  // ignore brief transients

    if (!st.faulted || (now - st.lastLogMs) >= SENSOR_REFAULT_LOG_MS) {
        st.faulted   = true;
        st.lastLogMs = now;
        char msg[48];
        snprintf(msg, sizeof(msg), "MAX31865 %s fault: 0x%02X", name, fault);
        logError(msg);
    }
}

void updateSensors() {
    serviceRtd(rtdBT, rtdBTfault, btTemp, "BT");
#if RTD_ET_ENABLED
    serviceRtd(rtdET, rtdETfault, etTemp, "ET");
#endif

    // --- MAX31855: inlet thermocouple (holds last good value on fault) ---
    double tc = tcIN.readCelsius();
    if (!isnan(tc)) {
        inTemp = (float)tc;
        inLastGoodMs = millis();
        tcINfault.badCount = 0;
        tcINfault.faulted  = false;
    } else {
        if (tcINfault.badCount < 255) tcINfault.badCount++;
        if (tcINfault.badCount >= SENSOR_FAULT_DEBOUNCE) {
            uint32_t now = millis();
            if (!tcINfault.faulted || (now - tcINfault.lastLogMs) >= SENSOR_REFAULT_LOG_MS) {
                tcINfault.faulted   = true;
                tcINfault.lastLogMs = now;
                char msg[48];
                snprintf(msg, sizeof(msg), "MAX31855 IN fault: 0x%02X", tcIN.readError());
                logError(msg);
            }
        }
    }
}

// ===========================================================================
// Tuning persistence (NVS)
// ===========================================================================
// The tuning set — PID gains and feedforward params — survives reboots in the
// ESP32's NVS flash. Defaults above are compile-time placeholders; on a virgin
// device (no stored keys) load() leaves them untouched, so the firmware behaves
// identically until the first PID/FF/TUNE-APPLY commits a value. save() is
// called only from those (infrequent) mutation paths, never the control loop,
// so flash wear is a non-issue. Preferences.putFloat() also skips the write
// when the value is unchanged.
static Preferences prefs;
static const char *NVS_NS = "tuning";

void loadTuning() {
    prefs.begin(NVS_NS, true);               // read-only
    pidKp     = prefs.getFloat("kp",    pidKp);
    pidKi     = prefs.getFloat("ki",    pidKi);
    pidKd     = prefs.getFloat("kd",    pidKd);
    ffK       = prefs.getFloat("ffK",   ffK);
    ffAmbient = prefs.getFloat("ffAmb", ffAmbient);
    prefs.end();
}

void saveTuning() {
    prefs.begin(NVS_NS, false);              // read-write
    prefs.putFloat("kp",    pidKp);
    prefs.putFloat("ki",    pidKi);
    prefs.putFloat("kd",    pidKd);
    prefs.putFloat("ffK",   ffK);
    prefs.putFloat("ffAmb", ffAmbient);
    prefs.end();
}

// Interlock configuration persists the same way (separate namespace). Because
// this is a safety configuration, load() re-validates: anything inconsistent
// (bad write, downgrade, manual NVS edit) falls back to the compile-time
// defaults rather than a weaker-than-intended interlock.
static const char *NVS_IL_NS = "interlock";

void loadInterlock() {
    prefs.begin(NVS_IL_NS, true);            // read-only
    ilFanMin      = prefs.getUChar("fanMin",  ilFanMin);
    ilFanFull     = prefs.getUChar("fanFull", ilFanFull);
    ilHeatAtMin   = prefs.getUChar("heatMin", ilHeatAtMin);
    interlockSoft = prefs.getBool("soft",     interlockSoft);
    prefs.end();
    if (ilFanMin < 1 || ilFanFull < ilFanMin || ilFanFull > 100 || ilHeatAtMin > 100) {
        ilFanMin    = IL_FAN_MIN_DFLT;
        ilFanFull   = IL_FAN_FULL_DFLT;
        ilHeatAtMin = IL_HEAT_AT_MIN_DFLT;
        logError("interlock NVS invalid: defaults restored");
    }
}

void saveInterlock() {
    prefs.begin(NVS_IL_NS, false);           // read-write
    prefs.putUChar("fanMin",  ilFanMin);
    prefs.putUChar("fanFull", ilFanFull);
    prefs.putUChar("heatMin", ilHeatAtMin);
    prefs.putBool("soft",     interlockSoft);
    prefs.end();
}

// The cooldown fan minimum and release dwell persist the same way (own
// namespace). Safety config again: load re-validates — fanMin 0 would let the
// fan stop under a hot roaster, defeating the guard.
static const char *NVS_COOL_NS = "cool";

void loadCool() {
    prefs.begin(NVS_COOL_NS, true);          // read-only
    coolFanMin = prefs.getUChar("fanMin",  coolFanMin);
    coolDwellS = prefs.getUShort("dwellS", coolDwellS);
    prefs.end();
    if (coolFanMin < 1 || coolFanMin > 100 ||
        coolDwellS < 1 || coolDwellS > 3600) {
        coolFanMin = COOL_FAN_MIN_DFLT;
        coolDwellS = COOL_DWELL_S_DFLT;
        logError("cool NVS invalid: defaults restored");
    }
}

void saveCool() {
    prefs.begin(NVS_COOL_NS, false);         // read-write
    prefs.putUChar("fanMin",  coolFanMin);
    prefs.putUShort("dwellS", coolDwellS);
    prefs.end();
}

// ===========================================================================
// OTA firmware updates
// ===========================================================================
// ArduinoOTA (espota protocol; push with `./verify.sh ota [host]`). Serviced
// from loop() only while the roaster is idle — manual mode with heat commanded
// and confirmed at 0 — because the flash write blocks the cooperative loop
// (and with it the interlock, failsafes, and sensor reads) for its whole
// duration. An upload attempted mid-roast simply times out on the host.
// onStart still re-zeros the heater at the wire as defense in depth. The fan
// keeps its level so a hot roaster keeps cooling air moving during the write.
bool otaBegun = false;   // ArduinoOTA.begin() done (deferred until WiFi is up)

void setupOTA() {
    ArduinoOTA.setHostname(OTA_HOSTNAME);
    ArduinoOTA.setPassword(OTA_PASS);

    ArduinoOTA.onStart([]() {
        // Heater off at the wire and every path that could re-drive it closed:
        // loop() goes dark until the update finishes or fails.
        ctrlMode  = MODE_MANUAL;
        tunePhase = TUNE_IDLE;
        requestedHeatLevel = 0;
        if (setLevel(HEAT_ADDR, 0)) heatLevel = 0;
        else logError("OTA: heat zero write failed");
        // The flash write stalls loop() far past WDT_TIMEOUT_MS; stop watching
        // this task for the duration. onError re-arms; success reboots.
        esp_task_wdt_delete(NULL);
        display.clearDisplay();
        display.setCursor(COL1A, ROW1 * ROWHEIGHT);
        display.print("OTA update");
        display.display();
        Serial.println("OTA: start");
    });

    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        static uint8_t lastPct = 255;
        uint8_t pct = (uint8_t)((uint64_t)progress * 100 / total);
        if (pct == lastPct) return;   // the OLED push is ~30 ms — repaint on change only
        lastPct = pct;
        display.setCursor(COL1A, ROW3 * ROWHEIGHT);
        display.printf("%3u%%", pct);
        display.display();
    });

    ArduinoOTA.onEnd([]() {
        // The core reboots into the new image; boot re-zeros heat as always.
        Serial.println("OTA: complete, rebooting");
    });

    ArduinoOTA.onError([](ota_error_t error) {
        esp_task_wdt_add(NULL);   // resume watching the loop task
        char msg[40];
        snprintf(msg, sizeof(msg), "OTA failed: error %u", (unsigned)error);
        logError(msg);
        flagDisplayUpdate = true; // repaint the normal screen over the OTA one
    });

    ArduinoOTA.begin();
    otaBegun = true;
    Serial.printf("OTA: listening as %s.local\n", OTA_HOSTNAME);
}

// ===========================================================================
// Setup
// ===========================================================================
void setup() {
    Serial.begin(115200);
    Wire.begin();
    delay(250);

    Serial.printf("\nairRoaster firmware v%s\n", FW_VERSION);

    // Restore persisted tuning (overrides the compile-time placeholders if a
    // device has been tuned before). Before WiFi/sensors so the loaded gains are
    // in force the moment control can engage. Interlock config likewise —
    // before the boot dimmer sync so the very first applyInterlock() runs with
    // the operator's limits.
    loadTuning();
    loadInterlock();
    loadCool();

    // Task watchdog on the loop task. A hang with the heater energized is the
    // worst failure mode; panic->reset is safe because the boot dimmer sync
    // below re-zeros the heat after any reset. The IDF may have already started
    // the WDT (watching idle tasks only), so reconfigure first, init as fallback.
    {
        esp_task_wdt_config_t wdtCfg;
        wdtCfg.timeout_ms    = WDT_TIMEOUT_MS;
        wdtCfg.idle_core_mask = 0;
        wdtCfg.trigger_panic  = true;
        if (esp_task_wdt_reconfigure(&wdtCfg) != ESP_OK) esp_task_wdt_init(&wdtCfg);
        esp_task_wdt_add(NULL);
    }

    // Display init
    display.begin(0x3C, true);
    display.clearDisplay();
    display.display();
    display.setTextSize(1);
    display.setTextColor(1, 0);
    display.setRotation(1);

    // DimmerLink init (before WiFi to avoid missing the ready window at power-on)
    initDL(HEAT_ADDR);
    initDL(FAN_ADDR);

    // Boot dimmer sync. After an MCU-only reset (crash / WDT / panic / OTA)
    // the dimmer modules keep running at their last levels while firmware
    // state restarts at zero. Kill the heat unconditionally; restore the fan
    // from the RTC no-init copy so a hot roaster keeps its cooling airflow
    // after a mid-roast reset. Reading the module instead is not an option:
    // getLevel() lies while the module is firing (emi.md § DimmerLink) — the
    // v0.13 read-adoption returned 0 and the 5 s re-assert then physically
    // stopped a running fan. The RTC copy survives exactly the resets that
    // matter; after a true power-on it is invalid garbage, and the fan module
    // has lost power too, so falling back to 0 matches reality.
    if (!setLevel(HEAT_ADDR, 0)) logError("boot: heat zero write failed");
    if (rtcFanValid()) {
        fanLevel = rtcFanLevel;
        if (fanLevel > 0) {
            if (setLevel(FAN_ADDR, fanLevel))
                Serial.printf("boot: restored fan level %u (RTC)\n", fanLevel);
            else
                logError("boot: fan restore write failed");
        }
    } else {
        rtcSaveFan(0);   // true power-on: initialize the RTC copy
    }

    // Sensor init
    initSensors();

    // WiFi: bounded wait, then proceed regardless — the roaster must be fully
    // operable over serial (control loop, interlock, display) with no network.
    // setAutoReconnect covers drops; the loop() watch kicks a full reconnect
    // if the link stays down.
    Serial.print("Connecting to WiFi");
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    uint32_t wifiStartMs = millis();
    while (WiFi.status() != WL_CONNECTED &&
           millis() - wifiStartMs < WIFI_CONNECT_TIMEOUT_MS) {
        esp_task_wdt_reset();   // connect can exceed the WDT timeout legitimately
        delay(250);
        Serial.print(".");
    }
    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
        Serial.print("WiFi connected. IP: ");
        Serial.println(WiFi.localIP());
        setupOTA();
    } else {
        Serial.println("WiFi not connected — continuing; retrying in background");
        // OTA init is deferred to the loop() link watch when WiFi comes up.
    }

    // WebSocket server
    webSocket.begin();
    webSocket.onEvent(webSocketEvent);

    flagDisplayUpdate = true;
}

// ===========================================================================
// WebSocket event handler
// ===========================================================================
void webSocketEvent(uint8_t num, WStype_t type, uint8_t *payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            Serial.printf("[WS] Client %u connected\n", num);
            // Send current status to the newly connected client
            broadcastStatus();
            break;

        case WStype_DISCONNECTED:
            Serial.printf("[WS] Client %u disconnected\n", num);
            break;

        case WStype_TEXT: {
            String cmd = String((char*)payload, length);
            cmd.trim();
            Serial.printf("[WS] Command from client %u: %s\n", num, cmd.c_str());
            if (!handleArtisanRequest(num, cmd)) {
                // JSON command envelope: {"command":"OT1","value":60.0,...}
                if (cmd.startsWith("{")) {
                    String kw = jsonString(cmd, "command");
                    float val = jsonFloat(cmd, "value");
                    String plain = kw;
                    if (!isnan(val)) {
                        plain += " ";
                        // Keep the fraction: Artisan's ramped INLET playback
                        // sends sub-degree setpoints every tick, and rounding
                        // here would quantize the ramp to 1 °C steps.
                        plain += String(val, 2);
                    }
                    processCommand(plain, (int8_t)num);
                } else {
                    processCommand(cmd, (int8_t)num);
                }
            }
            break;
        }

        case WStype_BIN:
            Serial.printf("[WS] Binary frame from client %u (%u bytes)\n", num, (unsigned)length);
            break;

        default:
            Serial.printf("[WS] Unhandled event type %u from client %u\n", (unsigned)type, num);
            break;
    }
}

// ===========================================================================
// Broadcast status JSON to all WebSocket clients
// ===========================================================================
static const char* modeName() {
    return ctrlMode == MODE_INLET ? "inlet" : (ctrlMode == MODE_TUNE ? "tune" : "manual");
}

void broadcastStatus() {
    char buf[176];
    snprintf(buf, sizeof(buf),
             "{\"pushMessage\":\"status\",\"data\":{\"heat\":%u,\"heatReq\":%u,\"fan\":%u,\"ilCap\":%u,\"ilSoft\":%s,\"mode\":\"%s\",\"inSV\":%.1f,\"cool\":%s}}",
             heatLevel,
             requestedHeatLevel,
             fanLevel,
             interlockCap(),
             interlockSoft ? "true" : "false",
             modeName(),
             inletSV,
             coolPending ? "true" : "false");
    webSocket.broadcastTXT(buf);
}

// Telemetry: the periodic dashboard feed. Everything a tuning session needs in
// one line — temps, setpoint, applied/requested levels, mode, and the last
// control-step term breakdown. Cadence set by telemPeriodMs (TELEM command).
void broadcastTelemetry() {
    if (webSocket.connectedClients() == 0) return;   // don't build the string for nobody
    char buf[288];
    snprintf(buf, sizeof(buf),
        "{\"pushMessage\":\"telem\",\"data\":{\"t\":%lu,\"IN\":%.1f,\"BT\":%.1f,\"ET\":%.1f,"
        "\"sv\":%.1f,\"heat\":%u,\"heatReq\":%u,\"fan\":%u,\"ilCap\":%u,\"mode\":\"%s\","
        "\"p\":%.1f,\"i\":%.1f,\"d\":%.1f,\"ff\":%.1f,\"fltIN\":%u,\"fltBT\":%u}}",
        (unsigned long)millis(), inTemp, btTemp, etTemp,
        inletSV, heatLevel, requestedHeatLevel, fanLevel, interlockCap(), modeName(),
        ctlP, ctlI, ctlD, ctlFF,
        tcINfault.faulted ? 1u : 0u, rtdBTfault.faulted ? 1u : 0u);
    webSocket.broadcastTXT(buf);
}

// ===========================================================================
// Artisan WebSocket request handler
// Artisan sends: {"command":"getData","id":12345,"machine":0}
// We respond:    {"id":12345,"data":{"BT":0.0,"ET":0.0,"IN":0.0}}
// ===========================================================================
bool handleArtisanRequest(uint8_t clientNum, const String& msg) {
    if (msg.indexOf("getData") < 0) return false;

    // Extract numeric id value
    int idPos = msg.indexOf("\"id\"");
    if (idPos < 0) return false;
    int colon = msg.indexOf(':', idPos);
    if (colon < 0) return false;
    int start = colon + 1;
    while (start < (int)msg.length() && msg[start] == ' ') start++;
    int end = start;
    while (end < (int)msg.length() && isDigit(msg[end])) end++;
    if (end == start) return false;

    char idStr[12];
    msg.substring(start, end).toCharArray(idStr, sizeof(idStr));

    char buf[96];
    snprintf(buf, sizeof(buf),
             "{\"id\":%s,\"data\":{\"BT\":%.1f,\"ET\":%.1f,\"IN\":%.1f}}",
             idStr, btTemp, etTemp, inTemp);
    webSocket.sendTXT(clientNum, buf);
    return true;
}

// ===========================================================================
// Display update
// ===========================================================================
void displayUpdate() {
    display.setCursor(COL1A, ROW1 * ROWHEIGHT);
    display.printf("airRoaster v%s", FW_VERSION);

    display.setCursor(COL1A, ROW2 * ROWHEIGHT);
    display.printf("Heat: %u", heatLevel);
    display.setCursor(COL2A, ROW2 * ROWHEIGHT);
    display.printf("Req: %u", requestedHeatLevel);

    display.setCursor(COL1A, ROW3 * ROWHEIGHT);
    display.printf("Fan: %u", fanLevel);

    display.setCursor(COL1A, ROW4 * ROWHEIGHT);
    {
        uint8_t cap = interlockCap();
        if (cap == 0) {
            display.printf("IL:%s BLOCKED", interlockSoft ? "S" : "H");
        } else if (cap < 100) {
            display.printf("IL:S cap=%u%%", cap);
        } else {
            display.printf("IL:%s ok", interlockSoft ? "S" : "H");
        }
    }

    display.setCursor(COL1A, ROW5 * ROWHEIGHT);
    if (ctrlMode == MODE_INLET) {
        display.printf("Inlet SV:%.0f", inletSV);
    } else if (ctrlMode == MODE_TUNE) {
        display.printf("Tuning...");
    } else {
        display.printf("Inlet: off");
    }

    display.setCursor(COL1A, ROW6 * ROWHEIGHT);
    if (WiFi.status() == WL_CONNECTED) {
        display.printf("%s", WiFi.localIP().toString().c_str());
    } else {
        display.printf("No WiFi");
    }

    display.setCursor(COL1A, ROW7 * ROWHEIGHT);
    if (!coolEnabled) {
        display.printf("Cool guard OFF");
    } else if (coolPending) {
        display.printf("Cool: fan held");
    }

    display.setCursor(COL1A, ROW8 * ROWHEIGHT);
    display.printf("B:%.1f E:%.1f I:%.1f", btTemp, etTemp, inTemp);

    display.display();
}

// ===========================================================================
// DimmerLink helpers
// ===========================================================================
void initDL(uint8_t addr) {
    for (int attempt = 0; attempt < 3; attempt++) {
        if (isReady(addr)) {
            Serial.printf("DimmerLink 0x%02X ready, fw version %d\n", addr, getVersion(addr));
            Serial.print("Mains frequency: ");
            Serial.print(getFrequency(addr));
            Serial.println(" Hz");
            Serial.print("setting curve...");
            Serial.println(setCurve(addr, 1));
            checkDLError(addr);
            return;
        }
        delay(DL_INIT_RETRY_DELAY_MS);
    }
    char msg[40];
    snprintf(msg, sizeof(msg), "DimmerLink 0x%02X not ready after 3 tries", addr);
    logError(msg);
}

bool isReady(uint8_t addr) {
    Wire.beginTransmission(addr);
    Wire.write(REG_STATUS);
    Wire.endTransmission(false);

    Wire.requestFrom(addr, 1);
    if (Wire.available()) {
        return (Wire.read() & 0x01) != 0;
    }
    return false;
}

bool setLevel(uint8_t addr, uint8_t level) {
    if (level > 100) return false;

    Wire.beginTransmission(addr);
    Wire.write(REG_LEVEL);
    Wire.write(level);
    return Wire.endTransmission() == 0;
}

int getLevel(uint8_t addr) {
    Wire.beginTransmission(addr);
    Wire.write(REG_LEVEL);
    Wire.endTransmission(false);

    Wire.requestFrom(addr, 1);
    if (Wire.available()) {
        return Wire.read();
    }
    return -1;
}

bool setCurve(uint8_t addr, uint8_t curve) {
    if (curve > 2) return false;

    Wire.beginTransmission(addr);
    Wire.write(REG_CURVE);
    Wire.write(curve);
    return Wire.endTransmission() == 0;
}

int getCurve(uint8_t addr) {
    Wire.beginTransmission(addr);
    Wire.write(REG_CURVE);
    Wire.endTransmission(false);

    Wire.requestFrom(addr, 1);
    if (Wire.available()) {
        return Wire.read();
    }
    return -1;
}

int getFrequency(uint8_t addr) {
    Wire.beginTransmission(addr);
    Wire.write(REG_FREQ);
    Wire.endTransmission(false);

    Wire.requestFrom(addr, 1);
    if (Wire.available()) {
        return Wire.read();
    }
    return -1;
}

// Module error register; -1 when the module doesn't answer (absent, or busy
// rebooting). Callers must never treat a non-answer as an error *code*.
int getError(uint8_t addr) {
    Wire.beginTransmission(addr);
    Wire.write(REG_ERROR);
    Wire.endTransmission(false);

    Wire.requestFrom(addr, 1);
    if (Wire.available()) {
        return Wire.read();
    }
    return -1;
}

int getVersion(uint8_t addr) {
    Wire.beginTransmission(addr);
    Wire.write(REG_VERSION);
    Wire.endTransmission(false);

    Wire.requestFrom(addr, 1);
    if (Wire.available()) {
        return Wire.read();
    }
    return -1;
}

// Operator-commanded recovery (DLRESET) for a module stuck in an error state.
// NEVER call this autonomously: on this hardware (observed 2026-07-02, see
// hardware/emi.md § DimmerLink) a soft reset drives the module's output FULL
// ON for ~3-4 s regardless of the commanded level, and the module NACKs
// writes while it reboots. So: command the reset, poll until the module
// answers again (bounded — every second at full output counts), then
// re-assert curve and level with the results checked. The 5 s re-assert in
// loop() converges anything this misses.
void resetDL(uint8_t addr, uint8_t level) {
    char msg[48];
    snprintf(msg, sizeof(msg), "DimmerLink 0x%02X: operator reset", addr);
    logError(msg);
    Wire.beginTransmission(addr);
    Wire.write(REG_COMMAND);
    Wire.write(DL_CMD_RESET);
    Wire.endTransmission();
    uint32_t t0 = millis();
    while (millis() - t0 < 3000) {
        esp_task_wdt_reset();   // deliberate blocking wait, not a hung loop
        delay(50);
        if (isReady(addr)) break;
    }
    if (!setCurve(addr, curveFor(addr)) || !setLevel(addr, level)) {
        snprintf(msg, sizeof(msg), "DimmerLink 0x%02X post-reset re-assert failed", addr);
        logError(msg);
    }
}

// Commanded heat % -> dimmer level. On the RMS curve, level maps linearly to
// Vrms, so heater power goes as level² (P = V²/R); commanding through the
// square root makes heat % proportional to *watts*. That keeps the plant gain
// the PID sees constant across the range and makes the feedforward's
// heat ∝ power assumption true, at the cost of heat % no longer being the raw
// dimmer level (all firmware state stays in command/power units; the mapping
// happens only at the hardware write and readback-audit boundary).
uint8_t heatDimmerLevel(uint8_t pct) {
    if (heatCurve != DL_CURVE_RMS) return pct;   // map unknown on other curves
    return (uint8_t)lroundf(10.0f * sqrtf((float)pct));
}

// The curve a channel should be running (for re-asserts after module resets).
uint8_t curveFor(uint8_t addr) {
    return (addr == FAN_ADDR) ? fanCurve : heatCurve;
}

// RTC fan-shadow helpers (variables + rationale up in the state section).
void rtcSaveFan(uint8_t level) {
    rtcFanLevel = level;
    rtcFanCheck = (uint8_t)~level;
    rtcFanMagic = FAN_RTC_MAGIC;
}

bool rtcFanValid() {
    return rtcFanMagic == FAN_RTC_MAGIC &&
           rtcFanCheck == (uint8_t)~rtcFanLevel &&
           rtcFanLevel <= 100;
}

// Commit-on-ack fan write: the interlock caps heat from fanLevel, so the cache
// must track what the fan hardware actually acknowledged. Shadows the level in
// RTC RAM for boot restore. On failure the cache is unchanged (rate-limit
// logged), so callers running on a cadence retry naturally.
bool setFanLevel(uint8_t level) {
    if (!setLevel(FAN_ADDR, level)) {
        logDimmerWriteFail(FAN_ADDR);
        return false;
    }
    fanLevel = level;
    rtcSaveFan(level);
    checkDLError(FAN_ADDR);
    return true;
}

const char* dlErrorName(uint8_t code) {
    switch (code) {
        case 0x00: return nullptr;          // OK — no error
        case 0xF9: return "ERR_SYNTAX";
        case 0xFC: return "ERR_NOT_READY";
        case 0xFD: return "ERR_INDEX";
        case 0xFE: return "ERR_PARAM";
        default:   return "ERR_UNKNOWN";
    }
}

// Read + decode the module error register. Returns true if an error is
// present. Diagnostics only — nothing may act on this: register reads lie
// while the module is firing (see assertDLState). A non-answer is a comms
// fault ("not responding" — absent module, or one busy rebooting), never
// conflated with a module error code. Logging is per-address rate-limited:
// a new state logs immediately, the same state repeating logs once a minute
// — an absent module must not flood the 8-entry log.
bool checkDLError(uint8_t addr) {
    static uint16_t lastCode[2] = {0, 0};   // 0x100 = not-responding sentinel
    static uint32_t lastMs[2]   = {0, 0};
    uint8_t idx = (addr == FAN_ADDR) ? 1 : 0;

    int r = getError(addr);
    uint16_t state = (r < 0) ? 0x100 : (uint16_t)r;
    if (r >= 0 && dlErrorName((uint8_t)r) == nullptr) {
        lastCode[idx] = 0;      // cleared: the next occurrence logs immediately
        return false;
    }
    uint32_t now = millis();
    if (state != lastCode[idx] || now - lastMs[idx] >= 60000) {
        lastCode[idx] = state;
        lastMs[idx]   = now;
        char msg[48];
        if (r < 0) {
            snprintf(msg, sizeof(msg), "DimmerLink 0x%02X not responding", addr);
        } else {
            snprintf(msg, sizeof(msg), "DimmerLink 0x%02X %s (0x%02X)",
                     addr, dlErrorName((uint8_t)r), (uint8_t)r);
        }
        logError(msg);
    }
    return true;
}

// Rate-limited log for failed level writes. The caller leaves its cached level
// unchanged on failure, so the write is retried naturally (applyInterlock runs
// every loop); this only keeps the retry storm out of the 8-entry error log.
void logDimmerWriteFail(uint8_t addr) {
    static uint32_t lastMs = 0;
    uint32_t now = millis();
    if (lastMs != 0 && now - lastMs < 5000) return;
    lastMs = now;
    char msg[48];
    snprintf(msg, sizeof(msg), "DimmerLink 0x%02X level write failed", addr);
    logError(msg);
}

// 5 s dimmer state service — replaces the v0.7 readback audit + reset
// escalation, which on real hardware reset a healthy module every 15 s and
// surged the output to full each time. The hardware facts this design rests
// on (observed 2026-07-02, hardware/emi.md § DimmerLink): register WRITES are
// reliable at any level, but READS lie while the module is firing (level
// 1..99: the level reads back 0, the error register returns garbage), and a
// soft reset drives the output full on for seconds — so no read may ever
// trigger a reset. Convergence therefore comes from the reliable direction:
// unconditionally re-assert the curve and level the channel should have.
// Idempotent on a healthy module; pulls back a self-reset one within 5 s.
// The readback check runs only when the channel is commanded OFF — the one
// region where reads are trustworthy, and the one divergence that matters
// most (output on when it must be off).
void assertDLState(uint8_t addr, uint8_t level) {
    if (level == 0) {
        int actual = getLevel(addr);
        if (actual > 0) {
            static uint32_t lastMs[2] = {0, 0};
            uint8_t idx = (addr == FAN_ADDR) ? 1 : 0;
            uint32_t nowMs = millis();
            if (lastMs[idx] == 0 || nowMs - lastMs[idx] >= 60000) {
                lastMs[idx] = nowMs;
                char msg[56];
                snprintf(msg, sizeof(msg), "DimmerLink 0x%02X reads %d while commanded off", addr, actual);
                logError(msg);
            }
        }
    }
    if (!setCurve(addr, curveFor(addr)) || !setLevel(addr, level))
        logDimmerWriteFail(addr);
}

// ===========================================================================
// Interlock
// ===========================================================================
// Returns the heat cap imposed by the interlock at the current fan level.
uint8_t interlockCap() {
    if (fanLevel < ilFanMin) return 0;
    if (!interlockSoft || fanLevel >= ilFanFull) return 100;
    // Linear ramp: ilHeatAtMin% at ilFanMin, 100% at ilFanFull. Unreachable
    // when ilFanFull == ilFanMin (the >= check above wins), so no div-by-zero.
    return (uint8_t)(ilHeatAtMin +
        (uint32_t)(100 - ilHeatAtMin) * (fanLevel - ilFanMin) / (ilFanFull - ilFanMin));
}

void applyInterlock() {
    uint8_t cap = interlockCap();
    uint8_t effective = (requestedHeatLevel < cap) ? requestedHeatLevel : cap;
    if (effective != heatLevel) {
        // Commit the cached level only when the hardware acknowledged the write;
        // on failure the stale cache makes this branch retry every loop.
        // (heatLevel stays in command/power %; the map applies at the wire.)
        if (setLevel(HEAT_ADDR, heatDimmerLevel(effective))) {
            heatLevel = effective;
            checkDLError(HEAT_ADDR);
            flagDisplayUpdate = true;
        } else {
            logDimmerWriteFail(HEAT_ADDR);
        }
    }
}

// ===========================================================================
// Cooldown guard
// ===========================================================================
// The fan may stop only once the roaster is provably cool: inlet below
// COOL_FAN_OFF_C, sustained for the coolDwellS dwell (COOL DWELL,
// NVS-persisted) on fresh readings, heat off.
// Until then a fan command below coolFanMin (COOL MIN, NVS-persisted) is
// deferred — held at coolFanMin — and the requested level applies itself when
// the criteria are met. Enforcement also runs unprompted: a hot roaster with
// the fan below minimum (hot boot with a lost RTC fan shadow, inlet soak-back
// after a release) gets its airflow forced back on. Decisions use the
// hold-last-good inTemp, so a
// sensor that dies hot keeps the fan running (fail safe); the release
// additionally requires a *fresh* reading. COOL OFF is the operator escape
// hatch, runtime-only so a reboot always re-arms the guard.

void sendCoolState(int8_t clientNum) {
    uint32_t belowS = (coolPending && coolBelowMs != 0)
                          ? (millis() - coolBelowMs) / 1000 : 0;
    char b[192];
    snprintf(b, sizeof(b),
        "{\"pushMessage\":\"cool\",\"data\":{\"enabled\":%s,\"pending\":%s,\"fanMin\":%u,"
        "\"target\":%u,\"offC\":%.0f,\"dwellS\":%u,\"belowS\":%lu,\"inC\":%.1f}}",
        coolEnabled ? "true" : "false", coolPending ? "true" : "false",
        coolFanMin, coolTargetFan, COOL_FAN_OFF_C,
        (unsigned)coolDwellS, (unsigned long)belowS, inTemp);
    if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
    else                webSocket.broadcastTXT(b);
    Serial.println(b);
}

void serviceCooldown(uint32_t now) {
    if (!coolEnabled) return;

    bool hot = (inTemp >= COOL_FAN_OFF_C);

    // Enforcement: hot with the fan below the cooldown minimum — force it up,
    // remembering the level to restore once cool. In manual mode the requested
    // heat is zeroed too: a raised fan must not silently un-block a heat level
    // the interlock had capped while the fan was low. (In closed loop the
    // setpoint is the operator's standing intent — left alone.) A failed fan
    // write leaves fanLevel unchanged, so this retries every pass.
    if (hot && fanLevel < coolFanMin) {
        if (!coolPending) {
            coolPending   = true;
            coolTargetFan = fanLevel;
            char msg[56];
            snprintf(msg, sizeof(msg), "cooldown: fan forced to %u (inlet %.0fC)",
                     coolFanMin, inTemp);
            logError(msg);
        }
        coolBelowMs = 0;
        if (ctrlMode == MODE_MANUAL) requestedHeatLevel = 0;
        if (setFanLevel(coolFanMin)) {
            flagDisplayUpdate = true;
            applyInterlock();
            broadcastStatus();
        }
        return;
    }

    if (!coolPending) { coolBelowMs = 0; return; }

    // Release: the deferred level applies only after the inlet has stayed
    // below the threshold for the full dwell, on fresh (non-held) readings,
    // with the heater off — a live heat command means someone is roasting,
    // and dropping the fan would just trip the interlock under them.
    bool fresh = (now - inLastGoodMs) <= INLET_PV_STALE_MS;
    if (hot || !fresh || requestedHeatLevel > 0 || heatLevel > 0) {
        coolBelowMs = 0;
        return;
    }
    if (coolBelowMs == 0) { coolBelowMs = now; return; }
    if (now - coolBelowMs < (uint32_t)coolDwellS * 1000UL) return;

    if (setFanLevel(coolTargetFan)) {     // on failure: retried next pass
        coolPending = false;
        coolBelowMs = 0;
        Serial.printf("cooldown complete: fan released to %u\n", coolTargetFan);
        sendCoolState(-1);
        flagDisplayUpdate = true;
        applyInterlock();
        broadcastStatus();
    }
}

// ===========================================================================
// Command parser
// ===========================================================================

// Split cmd on comma, space, semicolon, or equals; return token count (max 5)
int tokenize(const String &cmd, String tokens[], int maxTokens) {
    int count = 0;
    int start = 0;
    int len = cmd.length();
    for (int i = 0; i <= len && count < maxTokens; i++) {
        char c = (i < len) ? cmd[i] : '\0';
        if (c == ',' || c == ' ' || c == ';' || c == '=' || c == '\0') {
            if (i > start) {
                tokens[count++] = cmd.substring(start, i);
            }
            start = i + 1;
        }
    }
    return count;
}

// Strict numeric parsing. String::toInt()/toFloat() return 0 for garbage, so
// "OT1 x" once meant heat 0 and "PID a b c" persisted zero gains to NVS —
// invalid arguments must be rejected, never coerced.
static bool parseFloatStrict(const String &s, float &out) {
    if (s.length() == 0) return false;
    const char *c = s.c_str();
    char *end = nullptr;
    float v = strtof(c, &end);
    if (end == c || *end != '\0') return false;
    if (isnan(v) || isinf(v)) return false;
    out = v;
    return true;
}

// Integer via the strict float path (Artisan sliders may send "60.00").
static bool parseIntStrict(const String &s, int &out) {
    float f;
    if (!parseFloatStrict(s, f)) return false;
    out = (int)lroundf(f);
    return true;
}

// Reject an invalid argument back to the sender (client or serial) without
// polluting the 8-entry device error log — a typo is not a device fault.
static void replyBadArg(int8_t clientNum, const char *kw) {
    char kwSafe[16];
    uint8_t i = 0;
    for (const char *p = kw; *p && i < sizeof(kwSafe) - 1; p++)
        if (isalnum((unsigned char)*p) || *p == ' ') kwSafe[i++] = *p;
    kwSafe[i] = '\0';
    char b[80];
    snprintf(b, sizeof(b), "{\"pushMessage\":\"error\",\"data\":\"%s: invalid argument\"}", kwSafe);
    if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
    Serial.println(b);
}

void processCommand(String cmd, int8_t clientNum) {
    cmd.trim();
    if (cmd.length() == 0) return;

    String tokens[5];
    int n = tokenize(cmd, tokens, 5);
    if (n == 0) return;

    String kw = tokens[0];
    kw.toUpperCase();

    if (kw == "LOG") {
        if (clientNum >= 0) {
            sendLog((uint8_t)clientNum);
        } else {
            uint8_t start = (errCount < ERR_LOG_SIZE) ? 0 : errHead;
            if (errCount == 0) {
                Serial.println("[LOG] no errors");
            } else {
                for (uint8_t i = 0; i < errCount; i++) {
                    Serial.print("[LOG] ");
                    Serial.println(errLog[(start + i) % ERR_LOG_SIZE]);
                }
            }
        }
        return;

    } else if (kw == "OT1") {
        if (n < 2) return;
        String param = tokens[1];
        param.toUpperCase();
        // Validate before any side effect: a garbage argument must not abort a
        // running tune or drop out of closed loop, let alone set a level.
        uint8_t newHeat;
        if (param == "UP") {
            newHeat = (requestedHeatLevel + DUTY_STEP > 100) ? 100 : requestedHeatLevel + DUTY_STEP;
        } else if (param == "DOWN") {
            newHeat = (requestedHeatLevel >= DUTY_STEP) ? requestedHeatLevel - DUTY_STEP : 0;
        } else {
            int duty;
            if (!parseIntStrict(tokens[1], duty) || duty < 0 || duty > 100) {
                replyBadArg(clientNum, "OT1");
                return;
            }
            newHeat = (uint8_t)duty;
        }
        if (tunePhase != TUNE_IDLE) abortTune("manual override");
        ctrlMode = MODE_MANUAL;   // manual heat command is an instant override
        requestedHeatLevel = newHeat;
        flagDisplayUpdate = true;
        applyInterlock();
        broadcastStatus();

    } else if (kw == "OT2") {
        if (n < 2) return;
        String param = tokens[1];
        param.toUpperCase();
        uint8_t newFan;
        if (param == "UP") {
            newFan = (fanLevel + DUTY_STEP > 100) ? 100 : fanLevel + DUTY_STEP;
        } else if (param == "DOWN") {
            newFan = (fanLevel >= DUTY_STEP) ? fanLevel - DUTY_STEP : 0;
        } else {
            int duty;
            if (!parseIntStrict(tokens[1], duty) || duty < 0 || duty > 100) {
                replyBadArg(clientNum, "OT2");
                return;
            }
            newFan = (uint8_t)duty;
        }
        // Cooldown guard: while the inlet is hot, a fan level below the
        // cooldown minimum would strand heat in the roaster. The command is
        // deferred, not obeyed — the fan holds at coolFanMin and the requested
        // level applies itself once the inlet has stayed below COOL_FAN_OFF_C
        // for the dwell (serviceCooldown). COOL OFF is the override.
        if (coolEnabled && newFan < coolFanMin && inTemp >= COOL_FAN_OFF_C) {
            coolPending   = true;
            coolTargetFan = newFan;
            coolBelowMs   = 0;
            char b[144];
            snprintf(b, sizeof(b),
                "{\"pushMessage\":\"error\",\"data\":\"OT2 %u deferred: inlet %.0fC, fan held at %u until <%.0fC for %us\"}",
                newFan, inTemp, coolFanMin, COOL_FAN_OFF_C, coolDwellS);
            if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
            Serial.println(b);
            newFan = coolFanMin;
        } else {
            coolPending = false;   // an accepted fan command supersedes a deferred one
            coolBelowMs = 0;
        }
        setFanLevel(newFan);   // commit-on-ack; cache tracks acknowledged writes only
        flagDisplayUpdate = true;
        applyInterlock();
        broadcastStatus();

    } else if (kw == "IL") {
        // IL                                — report interlock mode + limits.
        // IL HARD | IL SOFT                 — set the mode explicitly.
        // IL <fanMin> <fanFull> <heatAtMin> — set the limits.
        // Mode and limits persist in NVS. (The pre-v0.10 bare-IL toggle is
        // gone: a toggle desyncs against a stateful dashboard.)
        if (n >= 2) {
            String up = tokens[1];
            up.toUpperCase();
            if (up == "HARD") {
                interlockSoft = false;
            } else if (up == "SOFT") {
                interlockSoft = true;
            } else if (n >= 4) {
                int fmin, ffull, hmin;
                if (!parseIntStrict(tokens[1], fmin) ||
                    !parseIntStrict(tokens[2], ffull) ||
                    !parseIntStrict(tokens[3], hmin) ||
                    fmin < 1 || ffull < fmin || ffull > 100 ||   // fanMin 0 would
                    hmin < 0 || hmin > 100) {                    // defeat the interlock
                    replyBadArg(clientNum, "IL");
                    return;
                }
                ilFanMin    = (uint8_t)fmin;
                ilFanFull   = (uint8_t)ffull;
                ilHeatAtMin = (uint8_t)hmin;
            } else {
                replyBadArg(clientNum, "IL");
                return;
            }
            saveInterlock();
            flagDisplayUpdate = true;
            applyInterlock();     // new limits take effect immediately
            broadcastStatus();
        }
        char b[144];
        snprintf(b, sizeof(b),
            "{\"pushMessage\":\"il\",\"data\":{\"soft\":%s,\"fanMin\":%u,\"fanFull\":%u,\"heatAtMin\":%u,\"cap\":%u}}",
            interlockSoft ? "true" : "false", ilFanMin, ilFanFull, ilHeatAtMin, interlockCap());
        if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
        Serial.println(b);

    } else if (kw == "INLET") {
        // INLET <degC> — set inlet setpoint and engage closed-loop control.
        // INLET 0        — no setpoint: disengage and drop heat to 0.
        // INLET OFF      — disengage; heat holds at its current level.
        if (n < 2) return;
        String upper = tokens[1];
        upper.toUpperCase();
        if (upper == "OFF") {
            if (tunePhase != TUNE_IDLE) abortTune("inlet override");
            ctrlMode = MODE_MANUAL;   // leave requestedHeatLevel where it is
        } else {
            float sv;
            if (!parseFloatStrict(tokens[1], sv)) {
                replyBadArg(clientNum, "INLET");
                return;   // garbage must not engage the loop (or abort a tune)
            }
            if (tunePhase != TUNE_IDLE) abortTune("inlet override");
            if (sv <= 0.0f) {
                // A heater can't track 0 °C, and Artisan's SV slider parks at
                // 0 — the loop would otherwise rail P negative and pin heat
                // at 0 while still "engaged". Operator intent is cooldown.
                ctrlMode = MODE_MANUAL;
                requestedHeatLevel = 0;
                applyInterlock();
            } else {
                engageInlet(sv);
            }
        }
        flagDisplayUpdate = true;
        broadcastStatus();

    } else if (kw == "PID") {
        // PID            — report current gains/setpoint/mode.
        // PID <kp ki kd> — set gains live (for manual tuning).
        if (n >= 4) {
            float kp, ki, kd;
            if (!parseFloatStrict(tokens[1], kp) ||
                !parseFloatStrict(tokens[2], ki) ||
                !parseFloatStrict(tokens[3], kd)) {
                replyBadArg(clientNum, "PID");
                return;   // a typo must never persist zero gains to NVS
            }
            pidKp = kp;
            pidKi = ki;
            pidKd = kd;
            saveTuning();
        }
        char b[112];
        snprintf(b, sizeof(b),
            "{\"pushMessage\":\"pid\",\"data\":{\"kp\":%.3f,\"ki\":%.3f,\"kd\":%.3f,\"sv\":%.1f,\"mode\":\"%s\"}}",
            pidKp, pidKi, pidKd, inletSV, modeName());
        if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
        Serial.println(b);

    } else if (kw == "STAT") {
        // Report the control-cadence jitter watch (worst late-fire, µs) and the
        // worst single loop() pass, then zero both. Evidence on whether the
        // cooperative loop ever needs a real core.
        char b[112];
        snprintf(b, sizeof(b),
            "{\"pushMessage\":\"stat\",\"data\":{\"ctrlMaxJitterUs\":%lu,\"loopMaxUs\":%lu}}",
            (unsigned long)ctrlMaxJitterUs, (unsigned long)loopMaxUs);
        if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
        Serial.println(b);
        ctrlMaxJitterUs = 0;
        loopMaxUs = 0;

    } else if (kw == "TUNE") {
        // TUNE              — start a step test (default step size).
        // TUNE <pct>        — start with a specific heat step (% points).
        // TUNE ABORT|OFF    — cancel a running test.
        // TUNE APPLY        — apply the last "tight" suggestion as PID gains.
        if (n >= 2) {
            String p = tokens[1];
            String up = p;
            up.toUpperCase();
            if (up == "OFF" || up == "ABORT") {
                if (tunePhase != TUNE_IDLE) abortTune("operator abort");
            } else if (up == "APPLY") {
                if (tuneHaveSug) {
                    pidKp = tuneSugKp;
                    pidKi = tuneSugKi;
                    pidKd = 0.0f;
                    saveTuning();
                    char b[112];
                    snprintf(b, sizeof(b),
                        "{\"pushMessage\":\"tune\",\"data\":{\"applied\":true,\"kp\":%.3f,\"ki\":%.4f}}",
                        pidKp, pidKi);
                    webSocket.broadcastTXT(b);
                    Serial.println(b);
                }
            } else {
                float delta;
                if (!parseFloatStrict(p, delta)) {
                    replyBadArg(clientNum, "TUNE");
                    return;   // garbage once clamped to a 5% step and ran a test
                }
                if (tunePhase == TUNE_IDLE) startTune(delta);
            }
        } else if (tunePhase == TUNE_IDLE) {
            startTune((float)TUNE_STEP_DELTA);
        }

    } else if (kw == "FF") {
        // FF            — report feedforward params + current value.
        // FF <k>        — set ffK directly.
        // FF AMB <degC> — set the ambient reference temp.
        // FF AMB        — seed ambient from the MAX31855 cold junction (board
        //                 ambient; the enclosure runs a little warm — override
        //                 with an explicit value if that matters).
        // FF CAL        — derive ffK from the current (assumed steady) point.
        // FF OFF        — disable feedforward (ffK = 0).
        if (n >= 2) {
            String up = tokens[1];
            up.toUpperCase();
            if (up == "OFF") {
                ffK = 0.0f;
            } else if (up == "AMB") {
                if (n >= 3) {
                    float amb;
                    if (!parseFloatStrict(tokens[2], amb)) {
                        replyBadArg(clientNum, "FF AMB");
                        return;
                    }
                    ffAmbient = amb;
                } else {
                    double cj = tcIN.readInternal();
                    if (isnan(cj)) {
                        replyBadArg(clientNum, "FF AMB");   // cold junction unreadable
                        return;
                    }
                    ffAmbient = (float)cj;
                }
            } else if (up == "CAL") {
                float denom = (float)fanLevel * (inTemp - ffAmbient);
                if (heatLevel > 0 && denom > 1.0f) ffK = (float)heatLevel / denom;
            } else {
                float k;
                if (!parseFloatStrict(tokens[1], k)) {
                    replyBadArg(clientNum, "FF");
                    return;
                }
                ffK = k;
            }
            saveTuning();   // OFF / AMB / CAL / direct-set all mutate the tuning set
        }
        char b[160];
        snprintf(b, sizeof(b),
            "{\"pushMessage\":\"ff\",\"data\":{\"ffK\":%.5f,\"amb\":%.1f,\"ff\":%.1f}}",
            ffK, ffAmbient,
            feedforward(ctrlMode == MODE_INLET ? inletSV : inTemp, fanLevel));
        if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
        Serial.println(b);

    } else if (kw == "TELEM") {
        // TELEM          — report the telemetry period.
        // TELEM <ms>     — set the period (100–10000 ms).
        // TELEM OFF      — disable the periodic push.
        if (n >= 2) {
            String up = tokens[1];
            up.toUpperCase();
            if (up == "OFF") {
                telemPeriodMs = 0;
            } else {
                int ms;
                if (!parseIntStrict(tokens[1], ms) || ms < 100 || ms > 10000) {
                    replyBadArg(clientNum, "TELEM");
                    return;
                }
                telemPeriodMs = (uint16_t)ms;
            }
        }
        char b[72];
        snprintf(b, sizeof(b),
            "{\"pushMessage\":\"telem\",\"data\":{\"periodMs\":%u}}", telemPeriodMs);
        if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
        Serial.println(b);

    } else if (kw == "CURVE") {
        // CURVE                  — report both channels' curve modes.
        // CURVE HEAT|FAN <0|1|2> — set a channel's curve: 0=linear 1=rms 2=log.
        // Runtime-only (never persisted): the power-on default is RMS, so an
        // experiment can't survive a reboot into a roast. Note the heat
        // power-linearization applies only on RMS — on other curves heat %
        // falls back to raw dimmer level.
        if (n >= 3) {
            String ch = tokens[1];
            ch.toUpperCase();
            int cv;
            bool isHeat = (ch == "HEAT");
            if ((!isHeat && ch != "FAN") ||
                !parseIntStrict(tokens[2], cv) || cv < 0 || cv > 2) {
                replyBadArg(clientNum, "CURVE");
                return;
            }
            uint8_t addr = isHeat ? HEAT_ADDR : FAN_ADDR;
            if (setCurve(addr, (uint8_t)cv)) {
                if (isHeat) heatCurve = (uint8_t)cv; else fanCurve = (uint8_t)cv;
                // The same output needs a different level under the new curve —
                // re-send the current level through the (possibly new) mapping.
                if (isHeat) setLevel(HEAT_ADDR, heatDimmerLevel(heatLevel));
                else        setLevel(FAN_ADDR, fanLevel);
                checkDLError(addr);
            } else {
                char msg[48];
                snprintf(msg, sizeof(msg), "DimmerLink 0x%02X curve write failed", addr);
                logError(msg);
            }
        } else if (n >= 2) {
            replyBadArg(clientNum, "CURVE");
            return;
        }
        char b[96];
        snprintf(b, sizeof(b),
            "{\"pushMessage\":\"curve\",\"data\":{\"heat\":%u,\"fan\":%u,\"heatPowerMap\":%s}}",
            heatCurve, fanCurve,
            heatCurve == DL_CURVE_RMS ? "true" : "false");
        if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
        Serial.println(b);

    } else if (kw == "COOL") {
        // COOL           — report the cooldown guard state ("cool" push).
        // COOL ON        — arm the guard (the power-on default).
        // COOL MIN <lvl> — set the enforced cooldown fan level (1–100, NVS).
        // COOL DWELL <s> — set the release dwell (1–3600 s, NVS): how long the
        //                  inlet must stay below the threshold before the fan
        //                  releases. Size it to outlast soak-back.
        // COOL OFF       — disarm the guard and release any deferred fan level
        //                  NOW. Operator escape hatch (e.g. an inlet sensor
        //                  stuck hot); runtime-only, never persisted — a
        //                  reboot always re-arms.
        if (n >= 2) {
            String up = tokens[1];
            up.toUpperCase();
            if (up == "ON") {
                coolEnabled = true;
            } else if (up == "DWELL") {
                int s;
                if (n < 3 || !parseIntStrict(tokens[2], s) || s < 1 || s > 3600) {
                    replyBadArg(clientNum, "COOL DWELL");
                    return;
                }
                coolDwellS = (uint16_t)s;
                saveCool();
                coolBelowMs = 0;   // a pending release re-accumulates the new dwell
            } else if (up == "MIN") {
                int lvl;
                if (n < 3 || !parseIntStrict(tokens[2], lvl) || lvl < 1 || lvl > 100) {
                    replyBadArg(clientNum, "COOL MIN");  // 0 would defeat the guard
                    return;
                }
                coolFanMin = (uint8_t)lvl;
                saveCool();
                // A held fan tracks the new floor immediately (while pending
                // the guard owns the level, so it is exactly the old minimum).
                if (coolEnabled && coolPending) {
                    setFanLevel(coolFanMin);
                    applyInterlock();
                    broadcastStatus();
                }
            } else if (up == "OFF") {
                coolEnabled = false;
                if (coolPending) {
                    logError("cooldown guard disarmed: deferred fan level applied");
                    setFanLevel(coolTargetFan);
                    coolPending = false;
                    coolBelowMs = 0;
                    applyInterlock();
                    broadcastStatus();
                }
            } else {
                replyBadArg(clientNum, "COOL");
                return;
            }
            flagDisplayUpdate = true;
        }
        sendCoolState(clientNum);

    } else if (kw == "DLRESET") {
        // DLRESET HEAT|FAN — operator-commanded DimmerLink soft reset, the
        // only path to resetDL(). Hardware-observed (2026-07-02, emi.md): the
        // module drives its output FULL ON for ~3-4 s after a soft reset —
        // which is why this never happens autonomously, and why resetting the
        // heat module is refused without interlock-level airflow.
        if (n < 2) { replyBadArg(clientNum, "DLRESET"); return; }
        String ch = tokens[1];
        ch.toUpperCase();
        bool isHeat = (ch == "HEAT");
        if (!isHeat && ch != "FAN") { replyBadArg(clientNum, "DLRESET"); return; }
        if (isHeat && fanLevel < ilFanMin) {
            char b[112];
            snprintf(b, sizeof(b),
                "{\"pushMessage\":\"error\",\"data\":\"DLRESET HEAT refused: fan %u < interlock min %u\"}",
                fanLevel, ilFanMin);
            if (clientNum >= 0) webSocket.sendTXT((uint8_t)clientNum, b);
            Serial.println(b);
            return;
        }
        if (isHeat) resetDL(HEAT_ADDR, heatDimmerLevel(heatLevel));
        else        resetDL(FAN_ADDR, fanLevel);
        broadcastStatus();
    }
}

// ===========================================================================
// Inlet temperature control (closed loop)
// ===========================================================================
// The entire control law lives in controlStep(), operating only on shared
// globals (inTemp, fanLevel, requestedHeatLevel, the PID state). That is the
// "seam": cooperative now (called on a fixed cadence from loop()), but liftable
// into a pinned FreeRTOS control task later with no change to the math — see
// work.md. In MODE_MANUAL it does nothing; OT1 drives heat directly.

// PID working state (file-local).
static float    pidITerm  = 0.0f;   // integral accumulator, in heat-% units
static float    pidPvPrev = 0.0f;   // previous process value (inTemp)
static float    pidDFilt  = 0.0f;   // filtered derivative term
static bool     ctrlPrimed = false; // false until the first step seeds pvPrev
// (ctrlMaxJitterUs is declared up in the state section, ahead of processCommand.)

// Static feedforward heat estimate: heat_ff = ffK · fan · (sv − ffAmbient),
// clamped to 0..100. Returns 0 when ffK <= 0 (feedforward disabled). Wired into
// the control law, the engage-seed, and the anti-windup so they all stay
// consistent when it is active.
float feedforward(float sv, uint8_t fan) {
    if (ffK <= 0.0f) return 0.0f;
    float ff = ffK * (float)fan * (sv - ffAmbient);
    if (ff < 0.0f)   ff = 0.0f;
    if (ff > 100.0f) ff = 100.0f;
    return ff;
}

// Engage closed-loop control with a bumpless transfer: seed the integrator so
// the first output equals the current heat level (u = Kp*e + iTerm + FF must
// equal heatLevel  =>  iTerm = heatLevel - Kp*e - FF). No step on engage.
void engageInlet(float sv) {
    if (sv < INLET_SV_MIN_C) sv = INLET_SV_MIN_C;
    if (sv > INLET_SV_MAX_C) sv = INLET_SV_MAX_C;

    // Already closed-loop: just retarget and keep the integrator. The setpoint
    // changes gradually during a roast (Artisan drives INLET repeatedly), so
    // re-seeding here would reset integral action on every update.
    if (ctrlMode == MODE_INLET) { inletSV = sv; return; }

    // Manual -> inlet: bumpless transfer. Seed the integrator so the first
    // output equals the current heat level (u = Kp*e + iTerm + FF == heatLevel).
    inletSV = sv;
    float e = sv - inTemp;
    pidITerm  = (float)heatLevel - pidKp * e - feedforward(sv, fanLevel);
    pidPvPrev = inTemp;
    pidDFilt  = 0.0f;
    ctrlPrimed = true;
    ctrlMode  = MODE_INLET;
}

// Failsafe: drop out of closed loop to heat 0 (fan keeps running — with the
// heater off, airflow only cools). Used when the loop can no longer trust its
// PV: the hold-last-good policy means a faulted sensor presents a frozen,
// plausible-looking inTemp, and the integrator would wind against it forever.
static void inletFailsafe(const char *why) {
    ctrlMode = MODE_MANUAL;
    requestedHeatLevel = 0;
    applyInterlock();
    char msg[48];
    snprintf(msg, sizeof(msg), "inlet failsafe: %s", why);
    logError(msg);
    flagDisplayUpdate = true;
    broadcastStatus();
}

// One control iteration. dtMs is the measured interval since the last call, so
// timing jitter doesn't bias the integral/derivative.
void controlStep(uint32_t dtMs) {
    if (ctrlMode == MODE_TUNE) { tuneStep(dtMs); return; }
    if (ctrlMode != MODE_INLET) { ctrlPrimed = false; return; }

    // Guard the PV before using it: stale (sensor faulted, value frozen by
    // hold-last-good) or over-temp both mean the loop must let go.
    if (millis() - inLastGoodMs > INLET_PV_STALE_MS) { inletFailsafe("inlet PV stale");   return; }
    if (inTemp > INLET_OVERTEMP_C)                   { inletFailsafe("inlet over-temp"); return; }

    float dt = dtMs * 0.001f;
    if (dt <= 0.0f) return;
    if (dt > 1.0f) dt = 1.0f;   // clamp a pathological gap (e.g. post-stall)

    float pv = inTemp;
    if (!ctrlPrimed) { pidPvPrev = pv; ctrlPrimed = true; }  // belt-and-suspenders

    float e  = inletSV - pv;
    float P  = pidKp * e;
    float ff = feedforward(inletSV, fanLevel);

    // Derivative on measurement (no setpoint-change kick), low-pass filtered.
    float dRaw = -pidKd * (pv - pidPvPrev) / dt;
    if (PID_D_FILTER_TC > 0.0f) {
        float a = dt / (PID_D_FILTER_TC + dt);
        pidDFilt += a * (dRaw - pidDFilt);
    } else {
        pidDFilt = dRaw;
    }
    float D = pidDFilt;

    pidITerm += pidKi * e * dt;            // provisional integration
    float u = P + pidITerm + D + ff;

    // What the hardware will actually apply: clamp to 0..100 and the interlock.
    float uClamped = u < 0.0f ? 0.0f : (u > 100.0f ? 100.0f : u);
    float cap      = (float)interlockCap();
    float applied  = uClamped < cap ? uClamped : cap;

    // Back-calculation anti-windup against the *applied* value, so saturation —
    // including the fan interlock capping heat — doesn't wind the integrator up.
    pidITerm += PID_KAW * (applied - u) * dt;
    // Integral bounds: with feedforward active the integral is a *trim* term
    // and must be able to go negative to cancel an over-predicting FF — the
    // old [0, 100] floor held a permanent +10 °C offset on hardware
    // (2026-07-03 log: FF=80 vs ~50 true, I pinned at 0, P carrying −28).
    // Bound the steady command I+FF to the actuator range instead:
    // I ∈ [−ff, 100−ff], which reduces to the original [0, 100] when FF is off.
    if (pidITerm < -ff)          pidITerm = -ff;
    if (pidITerm > 100.0f - ff)  pidITerm = 100.0f - ff;

    pidPvPrev = pv;

    // Term capture for telemetry (dashboard tuning aid). I is the post-anti-
    // windup value — the one that persists into the next step.
    ctlP  = P;
    ctlI  = pidITerm;
    ctlD  = D;
    ctlFF = ff;

    requestedHeatLevel = (uint8_t)lroundf(uClamped);
    applyInterlock();   // writes min(requestedHeatLevel, cap) to the heat dimmer
}

// ===========================================================================
// Open-loop step-test autotune (TUNE)
// ===========================================================================
// State machine, stepped from controlStep() at the control cadence while in
// MODE_TUNE: hold baseline -> step heat -> sample the inlet response -> fit an
// FOPDT model (two-point 28.3%/63.2% method) -> suggest PI gains (SIMC). The
// step goes through applyInterlock(), so inadequate airflow aborts the test.

static uint8_t  tuneU0        = 0;     // baseline applied heat (%)
static uint8_t  tuneCmdDelta  = 0;     // commanded step size (% points)
static uint8_t  tuneStepHeat  = 0;     // commanded heat during the step
static float    tuneStepDelta = 0.0f;  // actual applied heat delta (post-interlock)
static float    tuneT0        = 0.0f;  // measured baseline temp (°C)
static uint32_t tunePhaseMs   = 0;     // elapsed time in the current phase
static uint32_t tuneSampleAcc = 0;     // ms since the last response sample
static float    tuneBaseAcc   = 0.0f;  // baseline-temp accumulator
static uint16_t tuneBaseN     = 0;     // baseline samples
static float    tuneBuf[TUNE_MAX_SAMPLES];  // sampled response (buf[0] at step)
static uint16_t tuneCount     = 0;     // samples recorded

// Send a result line to every client and the serial console, then return to
// manual holding the pre-test baseline heat.
static void tuneReportAndRestore(const char *json) {
    webSocket.broadcastTXT(json);
    Serial.println(json);
    requestedHeatLevel = tuneU0;
    ctrlMode  = MODE_MANUAL;
    tunePhase = TUNE_IDLE;
    applyInterlock();
    flagDisplayUpdate = true;
    broadcastStatus();
}

void abortTune(const char *why) {
    char buf[128];
    snprintf(buf, sizeof(buf),
        "{\"pushMessage\":\"tune\",\"data\":{\"ok\":false,\"reason\":\"%s\"}}", why);
    tuneReportAndRestore(buf);
}

// First time (s, relative to the step) the response reaches `target`, linearly
// interpolated; -1 if it never does. Assumes a rising response (buf[0] ~ T0).
static float tuneCrossTime(float target) {
    for (uint16_t i = 0; i < tuneCount; i++) {
        if (tuneBuf[i] >= target) {
            if (i == 0) return 0.0f;
            float a = tuneBuf[i - 1], b = tuneBuf[i];
            float frac = (b > a) ? (target - a) / (b - a) : 0.0f;
            return ((float)(i - 1) + frac) * (TUNE_SAMPLE_MS * 0.001f);
        }
    }
    return -1.0f;
}

// SIMC (Skogestad) PI tuning for an FOPDT model. lambda is the closed-loop time
// constant (robustness knob: smaller = brisker). Outputs gains in our units —
// kc [%/°C], ki [%/(°C·s)] = kc / Ti.
static void tuneSimcPI(float Kp, float tau, float theta, float lambda,
                       float &kc, float &ki) {
    float denom = lambda + theta;
    if (denom < 1e-3f) denom = 1e-3f;
    kc = (1.0f / Kp) * (tau / denom);
    float Ti = (tau < 4.0f * denom) ? tau : 4.0f * denom;
    ki = (Ti > 1e-3f) ? kc / Ti : 0.0f;
}

// Fit the recorded response and report the model + suggested gains. `settled`
// says whether the response actually flattened or the test just timed out —
// a timeout fit underestimates dT and therefore suggests too-hot gains.
static void tuneFinish(bool settled) {
    uint16_t navg = tuneCount < 8 ? tuneCount : 8;
    float sum = 0.0f;
    for (uint16_t i = tuneCount - navg; i < tuneCount; i++) sum += tuneBuf[i];
    float Tfinal = navg ? sum / navg : tuneT0;
    float dT = Tfinal - tuneT0;

    char buf[256];
    if (dT < TUNE_MIN_RISE_C || tuneStepDelta < 1.0f) {
        snprintf(buf, sizeof(buf),
            "{\"pushMessage\":\"tune\",\"data\":{\"ok\":false,\"reason\":\"insufficient response\",\"dT\":%.1f,\"step\":%.0f}}",
            dT, tuneStepDelta);
        tuneReportAndRestore(buf);
        return;
    }

    float Kp = dT / tuneStepDelta;                       // process gain (°C/%)
    float t28 = tuneCrossTime(tuneT0 + 0.283f * dT);
    float t63 = tuneCrossTime(tuneT0 + 0.632f * dT);
    if (t28 < 0.0f || t63 <= t28) {
        snprintf(buf, sizeof(buf),
            "{\"pushMessage\":\"tune\",\"data\":{\"ok\":false,\"reason\":\"could not fit FOPDT\",\"dT\":%.1f}}",
            dT);
        tuneReportAndRestore(buf);
        return;
    }
    float tau   = 1.5f * (t63 - t28);
    float theta = t63 - tau;
    if (theta < 0.0f) theta = 0.0f;

    // Two robustness levels: "tight" (brisk, per the operator's tracking-first
    // preference) and "cons" (conservative). Bound lambda so a tiny dead time
    // doesn't blow the gains up.
    float lamT = (theta > 0.1f * tau) ? theta : 0.1f * tau;
    float lamC = (3.0f * theta > 0.5f * tau) ? 3.0f * theta : 0.5f * tau;
    float kpT, kiT, kpC, kiC;
    tuneSimcPI(Kp, tau, theta, lamT, kpT, kiT);
    tuneSimcPI(Kp, tau, theta, lamC, kpC, kiC);

    tuneSugKp = kpT;
    tuneSugKi = kiT;
    tuneHaveSug = true;

    snprintf(buf, sizeof(buf),
        "{\"pushMessage\":\"tune\",\"data\":{\"ok\":true,\"settled\":%s,\"fan\":%u,\"step\":%.0f,\"dT\":%.1f,"
        "\"Kp\":%.3f,\"tau\":%.1f,\"theta\":%.1f,"
        "\"tight\":{\"kp\":%.3f,\"ki\":%.4f},\"cons\":{\"kp\":%.3f,\"ki\":%.4f}}}",
        settled ? "true" : "false",
        fanLevel, tuneStepDelta, dT, Kp, tau, theta, kpT, kiT, kpC, kiC);
    tuneReportAndRestore(buf);
}

// Begin a step test from the current operating point.
void startTune(float deltaPct) {
    if (deltaPct < TUNE_STEP_DELTA_MIN) deltaPct = TUNE_STEP_DELTA_MIN;
    if (deltaPct > TUNE_STEP_DELTA_MAX) deltaPct = TUNE_STEP_DELTA_MAX;
    tuneU0       = heatLevel;            // current applied heat is the baseline
    tuneCmdDelta = (uint8_t)deltaPct;
    tuneBaseAcc  = 0.0f;
    tuneBaseN    = 0;
    tunePhaseMs  = 0;
    tuneSampleAcc = 0;
    tuneCount    = 0;
    tunePhase    = TUNE_BASELINE;
    ctrlMode     = MODE_TUNE;
    flagDisplayUpdate = true;
    broadcastStatus();
}

void tuneStep(uint32_t dtMs) {
    const uint16_t settleSamples = (TUNE_SETTLE_SECS * 1000) / TUNE_SAMPLE_MS;

    if (inTemp > TUNE_TEMP_ABORT_C) { abortTune("over-temp"); return; }
    if (millis() - inLastGoodMs > INLET_PV_STALE_MS) { abortTune("inlet PV stale"); return; }

    switch (tunePhase) {

    case TUNE_BASELINE:
        requestedHeatLevel = tuneU0;
        applyInterlock();
        tuneBaseAcc += inTemp;
        tuneBaseN++;
        tunePhaseMs += dtMs;
        if (tunePhaseMs >= TUNE_BASELINE_MS) {
            tuneT0 = tuneBaseN ? tuneBaseAcc / tuneBaseN : inTemp;
            uint16_t cmd = (uint16_t)tuneU0 + tuneCmdDelta;
            if (cmd > 100) cmd = 100;
            tuneStepHeat = (uint8_t)cmd;
            requestedHeatLevel = tuneStepHeat;
            applyInterlock();
            tuneStepDelta = (float)heatLevel - (float)tuneU0;   // actual, post-interlock
            if (tuneStepDelta < 1.0f) { abortTune("interlock capped step (raise fan)"); return; }
            tuneBuf[0] = inTemp;       // sample at t = 0 (≈ T0)
            tuneCount  = 1;
            tuneSampleAcc = 0;
            tunePhaseMs = 0;
            tunePhase = TUNE_STEP;
        }
        break;

    case TUNE_STEP:
        requestedHeatLevel = tuneStepHeat;
        applyInterlock();
        tunePhaseMs   += dtMs;
        tuneSampleAcc += dtMs;

        if (tuneSampleAcc >= TUNE_SAMPLE_MS) {
            tuneSampleAcc -= TUNE_SAMPLE_MS;
            if (tuneCount < TUNE_MAX_SAMPLES) tuneBuf[tuneCount++] = inTemp;

            // Settled? Response flat (max-min within band) over the last window.
            if (tuneCount >= settleSamples && tunePhaseMs >= TUNE_MIN_TEST_MS) {
                float mn = 1e9f, mx = -1e9f;
                for (uint16_t i = tuneCount - settleSamples; i < tuneCount; i++) {
                    float v = tuneBuf[i];
                    if (v < mn) mn = v;
                    if (v > mx) mx = v;
                }
                if (mx - mn < TUNE_SETTLE_BAND_C) { tuneFinish(true); return; }
            }
        }

        if (tunePhaseMs >= TUNE_MAX_MS || tuneCount >= TUNE_MAX_SAMPLES) {
            tuneFinish(false);   // timeout — fit whatever we have, flagged unsettled
            return;
        }
        break;

    default:
        tunePhase = TUNE_IDLE;
        ctrlMode  = MODE_MANUAL;
        break;
    }
}

// ===========================================================================
// Loop
// ===========================================================================
void loop() {
    uint32_t loopStartUs = micros();
    esp_task_wdt_reset();
    webSocket.loop();

    // Serial commands
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n') {
            processCommand(inputBuffer, -1);
            inputBuffer = "";
        } else if (c != '\r') {
            if (inputBuffer.length() < 32) inputBuffer += c;
        }
    }

    // Sensor update (every SENSOR_INTERVAL_MS)
    static uint32_t lastSensorPoll = 0;
    uint32_t now = millis();
    if (now - lastSensorPoll >= SENSOR_INTERVAL_MS) {
        lastSensorPoll = now;
        updateSensors();
    }

    // Display heartbeat: repaint at 1 Hz, decoupled from the sensor poll so the
    // full-framebuffer I2C push (~30 ms, a cooperative-loop blocker) hits the
    // control deadline at most once a second. Event handlers still flag an
    // immediate repaint for instant response to commands.
    static uint32_t lastDisplayMs = 0;
    if (now - lastDisplayMs >= 1000) {
        lastDisplayMs = now;
        flagDisplayUpdate = true;
    }

    // Inlet control step (fixed cadence; the controlStep() seam). Uses the
    // measured interval so cooperative jitter doesn't bias the integral, and
    // records the worst late-fire as evidence on whether a dedicated core is
    // ever needed (read via STAT). controlStep() is a no-op in MODE_MANUAL.
    static uint32_t lastCtrl = 0;
    uint32_t ctrlDt = now - lastCtrl;
    if (ctrlDt >= CONTROL_PERIOD_MS) {
        if (lastCtrl != 0 && ctrlDt > CONTROL_PERIOD_MS) {
            uint32_t jitterUs = (ctrlDt - CONTROL_PERIOD_MS) * 1000UL;
            if (jitterUs > ctrlMaxJitterUs) ctrlMaxJitterUs = jitterUs;
        }
        lastCtrl = now;
        controlStep(ctrlDt);
    }

    // Cooldown guard: enforce airflow while the roaster is hot; apply a
    // deferred fan level once the shutdown criteria are met.
    serviceCooldown(now);

    // Periodic DimmerLink service (every 5 s): error-register poll (diagnostic
    // logging only) + unconditional curve/level re-assert — see assertDLState
    // for the hardware facts behind this shape. No autonomous reset, ever: a
    // soft reset drives the module's output FULL ON for ~3-4 s (emi.md);
    // reset is operator-only via DLRESET. Heat crosses the power-linearization
    // map at the wire, so its re-assert is in dimmer units, not command units.
    static uint32_t lastDLService = 0;
    if (now - lastDLService >= 5000) {
        lastDLService = now;
        checkDLError(HEAT_ADDR);
        checkDLError(FAN_ADDR);
        assertDLState(HEAT_ADDR, heatDimmerLevel(heatLevel));
        assertDLState(FAN_ADDR, fanLevel);
    }

    // WiFi link watch: autoReconnect covers most drops; if the link is down for
    // a full check interval, kick an explicit reconnect. Repaint on any change
    // (the display's IP row).
    static uint32_t lastWifiCheck = 0;
    static bool wifiWasUp = false;
    if (now - lastWifiCheck >= WIFI_CHECK_MS) {
        lastWifiCheck = now;
        bool up = (WiFi.status() == WL_CONNECTED);
        if (up != wifiWasUp) flagDisplayUpdate = true;
        if (!up && !wifiWasUp) WiFi.reconnect();
        if (up && !otaBegun) setupOTA();   // boot happened without WiFi
        wifiWasUp = up;
    }

    // OTA: serviced only while idle — manual mode, heat commanded and
    // confirmed at 0 (see the OTA section header for why). The fan may run.
    if (otaBegun && ctrlMode == MODE_MANUAL &&
        requestedHeatLevel == 0 && heatLevel == 0) {
        ArduinoOTA.handle();
    }

    // Telemetry push (faster cadence during a tune so the step response is
    // well-resolved on the dashboard).
    static uint32_t lastTelem = 0;
    uint16_t telemDue = (ctrlMode == MODE_TUNE) ? TELEM_TUNE_PERIOD_MS : telemPeriodMs;
    if (telemDue > 0 && now - lastTelem >= telemDue) {
        lastTelem = now;
        broadcastTelemetry();
    }

    // Recheck interlock every loop in case fan level changed outside OT2
    applyInterlock();

    // Display
    if (flagDisplayUpdate) {
        display.clearDisplay();
        displayUpdate();
        flagDisplayUpdate = false;
    }

    // Worst-pass watch (see loopMaxUs declaration): how long this pass kept
    // the cooperative loop dark.
    uint32_t loopDurUs = micros() - loopStartUs;
    if (loopDurUs > loopMaxUs) loopMaxUs = loopDurUs;
}

// ===========================================================================
// Version history
// ---------------------------------------------------------------------------
// v0.16.0 2026-07-04  Cooldown guard: minimum fan-shutdown criteria enforced.
//                     The fan may stop only once the inlet has stayed below
//                     COOL_FAN_OFF_C (70 C) for coolDwellS (default 30 s,
//                     live-set via COOL DWELL <1-3600>, NVS — size it to
//                     outlast soak-back; the 2026-07-05 drill saw two
//                     re-enforce cycles at 30 s) on
//                     fresh readings, with heat off. A fan command below the
//                     cooldown fan minimum while hot is deferred, not obeyed:
//                     the fan holds at coolFanMin (default 50, live-set via
//                     COOL MIN <1-100>, persisted in NVS namespace "cool",
//                     re-validated on load) and the requested level
//                     applies itself when the criteria are met (new "cool"
//                     push; status gains "cool"; OLED row 7). The guard also
//                     enforces unprompted — a hot roaster with the fan below
//                     minimum (hot boot with a lost RTC shadow, soak-back
//                     after release) gets airflow forced back on, with
//                     manual-mode requested heat zeroed so the raised fan
//                     cannot un-block a previously interlock-capped level.
//                     A sensor that dies hot keeps the fan running (fail
//                     safe); COOL OFF is the operator escape (runtime-only,
//                     re-armed at every boot). New COOL / COOL ON|OFF /
//                     COOL MIN command; OT2 refactored through commit-on-ack
//                     setFanLevel().
// v0.15.1 2026-07-04  INLET 0 (or any sv <= 0) now means "no setpoint": drop
//                     to manual with heat 0 instead of engaging the loop on an
//                     unreachable target. Previously a follow-background run
//                     ending with Artisan's SV slider at 0 left the loop
//                     "engaged" railing P at about -280 with heat pinned at 0
//                     (2026-07-04 log). INLET OFF is unchanged (disengage,
//                     hold heat) — 0 is the cooldown intent, OFF the handoff.
// v0.15.0 2026-07-05  Fan level survives MCU-only resets via RTC no-init RAM.
//                     Boot fan adoption previously read getLevel(), which lies
//                     while the module is firing — so after any reboot with
//                     the fan running (observed post-OTA), adoption read 0 and
//                     the 5 s re-assert physically stopped the fan, breaking
//                     the mid-roast crash-recovery airflow guarantee. The
//                     commanded fan level is now shadowed in RTC_NOINIT_ATTR
//                     RAM (magic + inverted-copy checksum, zero flash wear):
//                     valid across crash/WDT/panic/OTA reboots -> restored and
//                     asserted at boot; garbage after a true power-on -> falls
//                     back to 0, matching the also-unpowered fan module. Fan
//                     now also keeps spinning seamlessly across OTA updates.
// v0.14.1 2026-07-03  Inlet over-temp failsafe 280 -> 350 °C: the setpoint
//                     clamp already allowed INLET 300, but the failsafe
//                     tripped at 280, killing the loop mid-seek. 350 leaves
//                     overshoot margin over the SV max. Tune abort stays 280.
// v0.14.0 2026-07-03  Integral trim can go negative under feedforward. On
//                     hardware, an over-predicting FF (stale NVS ffK) plus the
//                     integrator's [0,100] floor produced a permanent +10 °C
//                     steady-state offset: I needed to sit at −30 to cancel
//                     the FF excess and couldn't, leaving the P term to carry
//                     it via standing error. New bounds keep the steady
//                     command I+FF within 0..100 (I ∈ [−ff, 100−ff]) —
//                     identical to the old behavior with FF off. Companion
//                     dashboard change (no firmware cost): an automated FF
//                     step calibration that measures ffK as the fan-step
//                     slope Δheat/(Δfan·ΔT) in closed loop — immune to the
//                     standing-loss intercept that makes the through-origin
//                     FF CAL over-predict when calibrated at low temperature.
// v0.13.0 2026-07-02  Remove the DimmerLink auto-reset escalation; rework the
//                     5 s poll around hardware facts found in first on-roaster
//                     validation (fan at 50 for ~1 min): module register READS
//                     lie while the triac is firing (level reads back 0, error
//                     register returns garbage), which fed the error streak
//                     and soft-reset a healthy module every 15 s — and a soft
//                     reset drives the output FULL ON for ~3-4 s (fan surged
//                     to 100% with no UI indication). New shape: reads are
//                     diagnostics only (rate-limited logs; "not responding"
//                     distinguished from error codes); convergence comes from
//                     unconditionally re-asserting curve+level every 5 s
//                     (writes are reliable at any level); readback checked
//                     only when a channel is commanded off. Soft reset is now
//                     operator-only (new DLRESET HEAT|FAN command; HEAT
//                     refused below interlock fan minimum), waits for the
//                     module to answer before re-asserting state. Details:
//                     hardware/emi.md § DimmerLink.
// v0.12.0 2026-07-02  Over-the-air firmware updates (ArduinoOTA, port 3232,
//                     mDNS "airroaster.local", password OTA_PASS from
//                     secrets.h, falling back to WIFI_PASS). Serviced only
//                     while idle (manual mode, heat 0); onStart re-zeros the
//                     heater at the wire and detaches the task WDT for the
//                     flash-write stall; a failed update re-arms the WDT and
//                     logs. Requires the TinyUF2 OTA partition scheme
//                     (2×1408K app slots) — verify.sh now selects it; the
//                     first flash after this change must be over USB.
//                     `./verify.sh ota [host]` pushes updates thereafter.
// v0.11.0 2026-07-02  Heat power linearization + CURVE command. On the RMS
//                     curve the dimmer level maps linearly to Vrms, so heater
//                     power went as level² — commanded heat % now passes
//                     through a sqrt map at the hardware write boundary, making
//                     heat % proportional to WATTS. All firmware state (PID,
//                     FF, interlock, tune, telemetry, display) stays in
//                     command/power units; only setLevel and the readback
//                     audit/reset paths translate. RE-TUNE REQUIRED: gains and
//                     ffK identified before this version are in dimmer-level
//                     units and no longer match the plant. New CURVE command
//                     (report / CURVE HEAT|FAN 0..2, runtime-only, default RMS
//                     re-asserted at boot) for the work.md curve experiments;
//                     module resets/audits re-assert the *active* curve. The
//                     heat power map applies only while the heat curve is RMS.
// v0.10.1 2026-07-02  DUTY_STEP 5 -> 1: OT1/OT2 UP/DOWN now nudge by a single
//                     percent. The fan operates over a narrow, sensitive band,
//                     so 5%-steps overshoot; absolute set commands unchanged.
// v0.10.0 2026-07-02  Runtime-configurable interlock. IL_FAN_MIN/IL_FAN_FULL/
//                     IL_HEAT_AT_MIN become runtime globals (compile-time
//                     values remain as power-on defaults), persisted in NVS
//                     namespace "interlock" alongside the tuning set; load()
//                     re-validates and falls back to defaults on inconsistent
//                     data (safety config must never weaken via a bad write).
//                     IL command reworked — BREAKING: bare IL now *reports*
//                     (pushMessage "il") instead of toggling; the mode is set
//                     explicitly with IL HARD / IL SOFT, limits with
//                     IL <fanMin> <fanFull> <heatAtMin> (validated: fanMin>=1,
//                     fanMin<=fanFull<=100, heatAtMin<=100). New limits apply
//                     immediately through applyInterlock(). Dashboard gains an
//                     Interlock panel (mode buttons + limit fields, prefilled
//                     from the il report on connect).
// v0.9.0  2026-07-02  Protocol hardening + telemetry (F4/F5/F7/F9). Strict
//                     numeric parsing everywhere: garbage arguments are
//                     rejected with an error reply to the sender instead of
//                     being coerced to 0 (OT1/OT2/INLET/PID/TUNE/FF — "PID a b
//                     c" no longer persists zero gains). JSON command envelope
//                     keeps the fractional value (Artisan's ramped INLET
//                     playback is no longer quantized to 1 °C). WiFi connect is
//                     bounded (15 s) and the roaster boots without network;
//                     loop watches the link and kicks reconnects. TUNE results
//                     carry "settled" (timeout fits underestimate dT => too-hot
//                     gains). DimmerLink: fw version logged at init, error-poll
//                     logging rate-limited per address, and a persistent-error
//                     streak escalates to a module soft reset (COMMAND 0x01)
//                     with curve/level re-assert. FF AMB with no value seeds
//                     ambient from the MAX31855 cold junction. New "telem"
//                     push (default 1 Hz, 2 Hz during tune, TELEM <ms>|OFF):
//                     temps, SV, levels, interlock cap, mode, P/I/D/FF terms,
//                     sensor fault flags — the dashboard's data feed.
// v0.8.0  2026-07-02  MAX31865 direct-register driver (max31865_direct.h),
//                     replacing the Adafruit library on the RTD path (F2/F10).
//                     The library's temperature() was a blocking one-shot
//                     (~75 ms of delay() per read, VBIAS toggled off after,
//                     fault register cleared on entry), which stalled the
//                     cooperative loop ~150 ms per 250 ms sensor cycle and
//                     defeated the continuous-mode design serviceRtd() was
//                     written against. The chip now genuinely runs in
//                     auto-convert mode (VBIAS|AUTO, 60 Hz notch, conversions
//                     free-running); reads are microsecond register accesses;
//                     the VBIAS re-assert stall guard is real again; on-chip
//                     fault thresholds are armed to the plausibility window so
//                     out-of-range conversions latch evidence on silicon; the
//                     per-sample RTD fault bit feeds the robust-read layer.
//                     STAT gains loopMaxUs (worst single loop() pass) — the old
//                     jitter metric couldn't see in-pass blocking. MAX31855
//                     path unchanged (verified free-running/non-blocking).
// v0.7.0  2026-07-02  Safety hardening (review findings F1/F3/F6/F8, see
//                     state-archive.md). Boot dimmer sync: heat forced to 0 and
//                     the fan's actual level adopted at startup, so an MCU-only
//                     reset (crash/WDT/brownout) can't leave the heater running
//                     against zeroed firmware state. Inlet failsafe: MODE_INLET
//                     drops to manual at heat 0 on stale PV (>3 s without an
//                     accepted inlet reading — hold-last-good would otherwise
//                     feed the integrator a frozen value) or over-temp (280 C);
//                     TUNE gains the same stale-PV abort. Dimmer level writes
//                     are now commit-on-ack: the cached level only updates when
//                     the I2C write succeeds, so failures retry every loop, with
//                     rate-limited logging; a 5 s readback audit re-asserts
//                     level+curve if the module state drifts (self-reset).
//                     Task watchdog (8 s, panic->reset) on the loop task.
// v0.6.0  2026-06-29  Persist the tuning set (PID gains + feedforward params) in
//                     NVS flash via the Preferences library. loadTuning() at
//                     boot restores stored values over the compile-time
//                     placeholders (virgin device keeps the defaults);
//                     saveTuning() is called from the PID, TUNE APPLY, and FF
//                     mutation paths only — never the control loop — so flash
//                     wear is negligible. Namespace "tuning".
// v0.5.0  2026-06-29  Feedforward power map (robustness to airflow changes):
//                     heat_ff = ffK · fan · (SV − ffAmbient), summed into the
//                     control law so a fan change moves heat immediately and the
//                     PID only trims the residual. FF command: report / set ffK /
//                     FF AMB <degC> / FF CAL (auto-calibrate ffK from the current
//                     steady point) / FF OFF. Defaults off (ffK = 0). Already
//                     consistent with the bumpless engage-seed and anti-windup,
//                     which referenced feedforward() from the start.
// v0.4.0  2026-06-29  Open-loop step-test autotune (TUNE command). Holds the
//                     current heat to measure a baseline, applies a heat step,
//                     samples the inlet response, fits an FOPDT model (two-point
//                     28.3%/63.2% method) and suggests PI gains via SIMC at two
//                     robustness levels (tight/conservative). New MODE_TUNE; the
//                     step runs through applyInterlock() so inadequate airflow
//                     aborts it, with over-temp and operator-override aborts too.
//                     TUNE [pct] / TUNE ABORT / TUNE APPLY. Results broadcast as
//                     a "tune" push message. No external library — identification
//                     and tuning are inline (see work.md phase 3).
// v0.3.0  2026-06-29  Inlet-temperature closed-loop control (cooperative). New
//                     MODE_INLET: controlStep() modulates heat from measured
//                     inlet temp with a PI(D) loop — derivative-on-measurement,
//                     back-calculation anti-windup against the *applied* (post-
//                     interlock) heat, bumpless engage. Commands: INLET <degC> /
//                     INLET OFF, PID (report/set gains live), STAT (control
//                     jitter watch). OT1 is an instant manual override. Mode +
//                     setpoint added to the status broadcast and OLED row 5.
//                     Gains are untuned placeholders. Feedforward + sTune TUNE
//                     routine are the next phases (see work.md). The control law
//                     is isolated in controlStep() so it can later move to a
//                     pinned FreeRTOS task unchanged.
// v0.2.1  2026-06-28  RTD read robustness: periodic VBIAS/auto-convert re-assert
//                     (guards against a silently-stalled converter), and a median
//                     filter over recent samples (rejects single-sample spikes).
//                     Also: BT mapped to the connected board (CS_RTD_BT=10); the
//                     empty board is ET (CS=9), gated off via RTD_ET_ENABLED.
// v0.2.0  2026-06-28  Sensor integration: 2x MAX31865 PT1000 (BT/ET) + MAX31855
//                     K-type (inlet), 3-channel Artisan output (BT/ET/IN),
//                     temps on OLED. Robust RTD reads — same-cycle glitch
//                     rejection, fault debounce, hold-last-good, rate-limited
//                     fault logging. ET RTD behind RTD_ET_ENABLED gate (no probe
//                     yet). BT/ET CS pins swapped to match wiring.
// v0.1.0  (baseline)  Dual DimmerLink heat/fan control, WebSocket + Artisan
//                     protocol, plain-text/serial commands, OLED status, fan
//                     interlock (hard/soft), RAM error log.
// ===========================================================================
