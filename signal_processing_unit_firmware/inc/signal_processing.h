// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include <stdbool.h>

// Flag indicating that the processor has finished collecting data
extern volatile bool integration_timer_flag;

// Main second core loop to continuously read from the Hall Voltage ADC
void read_loop();

// Averages from the buffer and converts from offset 24bit binary, to scaled voltage as a double with regards to voltage reference
double calculate_hall_voltage();

// Starts the integration timer
void start_integration_timer(void);

// Stops the integration timer
void stop_integration_timer(void);