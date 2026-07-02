// ===========================================================================
// Max31865Direct — minimal register-level MAX31865 driver for continuous
// (auto-convert) operation.
//
// Why not the Adafruit library: its temperature()/readRTD() path is one-shot —
// it toggles VBIAS, burns ~75 ms in delay() per read, clears the fault register
// on entry (destroying evidence), and leaves the chip unbiased with the
// auto-convert bit still set. Its readFault() default runs a master-initiated
// fault-detection cycle that drops the chip out of auto mode. None of that is
// compatible with airRoaster's continuous-mode robust-read design (serviceRtd).
//
// This driver keeps the chip in the datasheet's continuous mode — config
// VBIAS|AUTO, conversions at the 50/60 Hz notch rate, VBIAS held on — and reads
// the RTD/fault registers directly, so a read costs microseconds and the
// latched fault state survives until we choose to clear it.
//
// Datasheet traceability (hardware/max31865.pdf):
//   p.13 Table 1/2  register map, config bits; registers read at 0x0N, write
//                   at 0x8N, MSB first, multibyte auto-increment
//   p.13 D6         auto mode converts continuously at the notch rate,
//                   "VBIAS remains on continuously"
//   p.14 D1         fault clear = config D1 written with D5/D3/D2 zero
//   p.14 D0         do not change the notch frequency while auto-converting
//   p.15 Table 4/5  RTD registers: 15-bit ratio in D15..D1, D0 = fault bit
//   p.16 Table 6/7  thresholds share the RTD register format and are compared
//                   on every conversion (latching fault bits D7/D6)
//   p.17            SPI modes 1 and 3, MSB first
// ===========================================================================
#pragma once
#include <Arduino.h>
#include <SPI.h>

class Max31865Direct {
public:
    // Register addresses (read side; write address = addr | 0x80)
    static constexpr uint8_t REG_CONFIG  = 0x00;
    static constexpr uint8_t REG_RTD_MSB = 0x01;
    static constexpr uint8_t REG_HFT_MSB = 0x03;  // high fault threshold
    static constexpr uint8_t REG_LFT_MSB = 0x05;  // low fault threshold
    static constexpr uint8_t REG_FAULT   = 0x07;

    // Configuration register bits (datasheet Table 2)
    static constexpr uint8_t CFG_VBIAS    = 0x80;
    static constexpr uint8_t CFG_AUTO     = 0x40;
    static constexpr uint8_t CFG_3WIRE    = 0x10;
    static constexpr uint8_t CFG_FAULTCLR = 0x02;
    static constexpr uint8_t CFG_50HZ     = 0x01;

    // Fault status register bits (datasheet Table 7) — for log decoding
    static constexpr uint8_t FAULT_HIGHTHRESH = 0x80;
    static constexpr uint8_t FAULT_LOWTHRESH  = 0x40;
    static constexpr uint8_t FAULT_REFINHIGH  = 0x20;
    static constexpr uint8_t FAULT_REFINLOW   = 0x10;
    static constexpr uint8_t FAULT_RTDINLOW   = 0x08;
    static constexpr uint8_t FAULT_OVUV       = 0x04;

    Max31865Direct(uint8_t csPin, float rtdNominal, float refResistor)
        : _cs(csPin), _rNom(rtdNominal), _rRef(refResistor) {}

    // Enter continuous conversion mode. Wire/filter bits are written first in
    // normally-off mode (the notch must not change while auto-converting),
    // then VBIAS|AUTO is asserted and any power-on faults are cleared.
    void begin(bool wire3 = false, bool filt50 = false) {
        pinMode(_cs, OUTPUT);
        digitalWrite(_cs, HIGH);
        SPI.begin();
        _cfg = (wire3 ? CFG_3WIRE : 0) | (filt50 ? CFG_50HZ : 0);
        writeReg8(REG_CONFIG, _cfg);       // notch/wiring set while normally-off
        delay(1);
        _cfg |= CFG_VBIAS | CFG_AUTO;
        clearFault();                       // writes _cfg|FAULTCLR: clears faults
                                            // and enters continuous mode in one op
    }

    // Re-assert the running configuration. This is the stall guard from
    // hardware/emi.md: an EMI transient can flip config bits and silently
    // freeze conversions with no fault latched; rewriting the byte bounds the
    // outage at the caller's re-assert interval.
    void reassert() { writeReg8(REG_CONFIG, _cfg); }

    // Arm the on-chip conversion-window comparators. Arguments are 15-bit raw
    // ratios (use rawFromTemp); out-of-window conversions latch FAULT_HIGH/
    // LOWTHRESH and set the per-sample fault bit — EMI evidence on silicon.
    void setThresholdsRaw(uint16_t low15, uint16_t high15) {
        uint8_t buf[4] = {
            (uint8_t)(high15 >> 7), (uint8_t)(high15 << 1),   // HFT MSB, LSB
            (uint8_t)(low15  >> 7), (uint8_t)(low15  << 1),   // LFT MSB, LSB
        };
        writeRegs(REG_HFT_MSB, buf, 4);    // 0x03..0x06 in one burst
    }

    // One atomic read of the RTD register pair (multibyte read, so MSB and LSB
    // come from the same latched conversion). Returns the 15-bit ratio;
    // *fault receives the per-sample fault bit (RTD LSB D0).
    uint16_t readRaw(bool *fault = nullptr) {
        uint16_t v = readReg16(REG_RTD_MSB);
        if (fault) *fault = (v & 0x0001) != 0;
        return v >> 1;
    }

    // Latched fault detail (plain register read — deliberately NOT the
    // master-initiated fault-detection cycle, which would leave auto mode).
    uint8_t readFaultReg() { return readReg8(REG_FAULT); }

    // Clear latched faults: config D1 with D5/D3/D2 zero (never set in _cfg).
    // Also re-asserts VBIAS|AUTO as a side effect.
    void clearFault() { writeReg8(REG_CONFIG, _cfg | CFG_FAULTCLR); }

    // Read back the live config byte (diagnostic: compare against expected()).
    uint8_t readConfig() { return readReg8(REG_CONFIG); }
    uint8_t expected() const { return _cfg; }

    // Temperature (°C) from a 15-bit raw ratio. Callendar–Van Dusen inversion,
    // same AN709 technique as the Adafruit library: closed form above 0 °C,
    // rational polynomial below.
    float temperatureFromRaw(uint16_t raw15) const {
        float Rt = (float)raw15 / 32768.0f * _rRef;

        float Z2 = CVD_A * CVD_A - 4.0f * CVD_B;
        float Z3 = 4.0f * CVD_B / _rNom;
        float temp = (sqrtf(Z2 + Z3 * Rt) - CVD_A) / (2.0f * CVD_B);
        if (temp >= 0.0f) return temp;

        Rt = Rt / _rNom * 100.0f;          // normalize to PT100 for the poly
        float rpoly = Rt;
        temp = -242.02f + 2.2228f * rpoly;
        rpoly *= Rt; temp += 2.5859e-3f * rpoly;
        rpoly *= Rt; temp -= 4.8260e-6f * rpoly;
        rpoly *= Rt; temp -= 2.8183e-8f * rpoly;
        rpoly *= Rt; temp += 1.5243e-10f * rpoly;
        return temp;
    }

    // 15-bit raw ratio for a Celsius bound, via forward CVD R = R0(1+AT+BT²).
    // The missing C term below 0 °C is negligible at fault-threshold precision.
    uint16_t rawFromTemp(float tC) const {
        float R = _rNom * (1.0f + CVD_A * tC + CVD_B * tC * tC);
        float ratio = R / _rRef;
        if (ratio < 0.0f) ratio = 0.0f;
        if (ratio > 0.999969f) ratio = 0.999969f;   // 32767/32768
        return (uint16_t)(ratio * 32768.0f);
    }

private:
    uint8_t _cs;
    float   _rNom, _rRef;
    uint8_t _cfg = 0;

    static constexpr float CVD_A = 3.9083e-3f;
    static constexpr float CVD_B = -5.775e-7f;

    // 1 MHz, mode 1 — within the datasheet's supported modes and matching what
    // the rest of the (shared) bus already runs.
    SPISettings _spiCfg = SPISettings(1000000, MSBFIRST, SPI_MODE1);

    void writeReg8(uint8_t addr, uint8_t val) { writeRegs(addr, &val, 1); }

    void writeRegs(uint8_t addr, const uint8_t *buf, uint8_t n) {
        SPI.beginTransaction(_spiCfg);
        digitalWrite(_cs, LOW);
        SPI.transfer(addr | 0x80);
        for (uint8_t i = 0; i < n; i++) SPI.transfer(buf[i]);
        digitalWrite(_cs, HIGH);
        SPI.endTransaction();
    }

    uint8_t readReg8(uint8_t addr) {
        SPI.beginTransaction(_spiCfg);
        digitalWrite(_cs, LOW);
        SPI.transfer(addr & 0x7F);
        uint8_t v = SPI.transfer(0x00);
        digitalWrite(_cs, HIGH);
        SPI.endTransaction();
        return v;
    }

    uint16_t readReg16(uint8_t addr) {
        SPI.beginTransaction(_spiCfg);
        digitalWrite(_cs, LOW);
        SPI.transfer(addr & 0x7F);
        uint16_t v = (uint16_t)SPI.transfer(0x00) << 8;
        v |= SPI.transfer(0x00);
        digitalWrite(_cs, HIGH);
        SPI.endTransaction();
        return v;
    }
};
