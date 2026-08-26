// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

// Initilizes SPI port 1 for communication with the ADC
// - Sets clock frequency to 20 MHz
// - Configures SCLK and MISO pins as SPI pins
// - Configures CONVST (conversion stage) pin as a GPIO pin
// - Configures MOSI as a GPIO pin to act as a CS-pin(in this configuration) 
void init_ads8866(void);

// Tells the ADC to start converting a voltage value to a 16 bit value
// - Pulls CONVST pin high to start a voltage reading
// - Starts a timer to make sure sufficient conversion time has passed before reading the data 
void ads8866_start_conversion(void);

// Reads the voltage value from the ADC
// - Checks to see if sufficint time has passed for the conversion stage (max time 8.8µs)
// - Pull CONVST pin low to activate data transmission
// - Read ADC data and converts to a voltage value
float ads8866_get_voltage(void);