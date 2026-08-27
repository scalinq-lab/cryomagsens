// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include "config.h" 

#include <stdbool.h>
#include <stdint.h>

extern volatile bool sensor_presence_changed_flag;
extern volatile bool all_sensors_read_flag;
extern volatile uint8_t current_sensor_index;
extern volatile uint8_t active_sensors_count;
extern volatile bool sensor_active[NUMBER_OF_SENSORS];

void init_sensors(void);

void configure_sensors(void);

void switch_to_next_sensor(void);

bool is_sensor_present(uint8_t index);

void set_sensor_mux_state(uint8_t active_sensor);