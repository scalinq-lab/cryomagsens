// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include <stdint.h>

// =====================================================================================================================
// AD7175-2 Register Map
// =====================================================================================================================

#define AD7175_REG_ADCMODE   0x01
#define AD7175_REG_IFMODE    0x02
#define AD7175_REG_CH0       0x10
#define AD7175_REG_SETUPCON0 0x20
#define AD7175_REG_FILTCON0  0x28

// =====================================================================================================================
// Global Variables
// =====================================================================================================================

// Used for software recalibration of adc zeroing and corresponds to the value of which you should subtract from the
// offset binary from the adc to get a zeroed signed binary
extern int32_t volatile zeroed_offset_binary;

// =====================================================================================================================
// Functions
// =====================================================================================================================

// Initializes the SPI lane for communication with the AD7175
void init_ad7175(void);

// Configures settings for the AD7175
// - Configures channel setup and specifies analog inputs
// - Sets bipolar coding (measures +/- 2.5 V)
// - Sets output rate (default is 250 ksps)
// - Sets continous conversion and read mode
void configure_ad7175(void);

// Takes an average of 56000 samples (10 full periods of 70 Hz) and stores the calculated zero in zeroed_offset_binary
// - For accurate calibrations the modulation should be active before running this and due to the nature of the
//   bandpass filter it is expected that this value is zero.
void ad7175_set_zero(void);

// Reads without sending a register address first (Continuous Read mode)
// - Importantly this needs to be accurately timed to the ADCs signal, to avoid misaligned packages and corrupted data
uint32_t ad7175_fast_read(void);