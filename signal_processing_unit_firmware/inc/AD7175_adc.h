// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include <stdint.h>

// AD7175-2 Register Map
#define REG_ADCMODE   0x01
#define REG_IFMODE    0x02
#define REG_CH0       0x10
#define REG_SETUPCON0 0x20
#define REG_FILTCON0  0x28

// Used for software recalibration of adc zeroing and corresponds to the value of which you should subtract from the
// offset binary from the adc to get a zeroed signed binary
extern int32_t volatile zeroed_offset_binary;

// Writes a 16-bit value to a specified register address
void ad7175_write_reg16(uint8_t reg, uint16_t value);

// Initializes the SPI lane for communication with the AD7175
void init_ad7175();

// Configures settings for the AD7175
// - Configures channel setup and specifies analog inputs
// - Sets bipolar coding (measures +/- 2.5 V)
// - Sets output rate (default is 250 ksps)
// - Sets continous conversion and read mode
void configure_ad7175();

// Reads without sending a register address first (Continuous Read mode)
// - Importantly this needs to be accurately timed to the ADCs signal, to avoid misaligned packages and corrupted data
uint32_t ad7175_fast_read();

// Takes an average of 56000 samples (10 full periods of 70 Hz) and stores the calculated zero in zeroed_offset_binary
// - For accurate calibrations the modulation should be active before running this and due to the nature of the
//   bandpass filter it is expected that this value is zero.
void ad7175_set_zero();