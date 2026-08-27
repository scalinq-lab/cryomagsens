// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include "config.h" 

#include <stdbool.h>
#include <stdint.h>

// =====================================================================================================================
// Global variables
// =====================================================================================================================

// Flag to indicate need for reconfiguration of sensors
extern volatile bool sensor_presence_changed_flag;

// Flag to inticate when a full cycle of sensor switching has occured, meaning it's time to report results
extern volatile bool all_sensors_read_flag;

// Read-only
extern volatile uint8_t current_sensor_index;

// Read-only
extern volatile uint8_t active_sensors_count;

// Read-only
extern volatile bool sensor_active[NUMBER_OF_SENSORS];

// =====================================================================================================================
// Functions
// =====================================================================================================================

// Initializes interrupts for PRS (presence) pins and calls an initial configure_sensors() pass
void init_sensors(void);

// Updates flags and activity states, reports sensor connected/disconnected,
void configure_sensors(void);

// Switch to next sensor in the cycle, updates all_sensors_read_flag if necessary
void switch_to_next_sensor(void);

// Manually set a sensor state, used internally and for debug mode
void set_sensor_mux_state(uint8_t active_sensor);