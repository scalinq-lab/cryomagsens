// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "pico/stdlib.h"

/* PARAMETERS */
// Hardware parameters
#define ADC_VOLTAGE_REFERENCE 2.5
#define NUMBER_OF_SENSORS 3

// Default operational parameters
#define DEFAULT_INTEGRATION_TIME_MS 1000
#define DEFAULT_CURRENT_POLARITY_FREQUENCY 7000
#define DEFAULT_CURRENT_AXIS_FREQUENCY 70
#define DEFAULT_MODULATION_PROPAGATION_TIME_US 12
#define DEFAULT_MODULATION_UNSTABLE_TIME_US 16
#define DEFAULT_AXIS_UNSTABLE_TIME_US 145 + 224 * 3


/* GPIO/SPI PINOUT */
// Main power enable for the positive and negative supply rails
#define PIN_POWER_ENABLE_POS 0
#define PIN_POWER_ENABLE_NEG 1

// Current multiplexer pins 00: 3mA, 01: 0.3mA, 10: 30uA, 11: 8.3mA
#define PIN_CURRENT_LEVEL_0 2
#define PIN_CURRENT_LEVEL_1 3

// Direction of the current through the sensor (0 = c->a or d->b, 1 = a->c or b->d)
#define PIN_CURRENT_DIRECTION 4

// Axis of the current through the sensor (0 = b&d, 1 = a&c)
#define PIN_CURRENT_AXIS 5

// Sensor multiplexer pins 00: Sensor 0, 01: Sensor 1, 10: Sensor 2, 11: (NOT AN ALLOWED STATE)
#define PIN_SENSOR_MUX_0 6 
#define PIN_SENSOR_MUX_1 7

// Sensor presence detection pins (active low when sensor is present, using pull-up resistors)
#define PIN_SENSOR_PRS_0 8
#define PIN_SENSOR_PRS_1 9
#define PIN_SENSOR_PRS_2 10

// 2.5V power enable, turn off when no sensor is connected to avoid illegal state on current source
// Unfortunately, this also powers the hall voltage ADC - meaning we need to reconfigure it after each power cycle
#define PIN_POWER_ENABLE_2V5 11

// ADS8866 SPI pins (Temperature ADC)
#define SPI_ADC1 spi1
#define ADC1_MISO 12
#define ADC1_CONVST 13
#define ADC1_SCLK 14
#define ADC1_MOSI 15

// AD7175-2 SPI pins (Hall voltage ADC)
#define SPI_ADC0 spi0
#define ADC0_MISO 16
#define ADC0_SYNC_ERR 17
#define ADC0_SCLK 18
#define ADC0_MOSI 19

// Pico ADC0 (Hall current saturation check)
#define PICO_ADC0 26


/* MACROS */
// Frequency to timer conversion, i.e. how many microseconds to wait in between toggling modulation states for a given frequency
#define FREQUENCY_TO_TIMER_US(f) (500000 / (f))