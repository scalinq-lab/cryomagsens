// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include <stdbool.h>

// =====================================================================================================================
// Buffer size
// =====================================================================================================================

#define INPUT_BUFFER_SIZE 64

// =====================================================================================================================
// Global variables
// =====================================================================================================================

// When debug mode is activated, additional commands are available and measurements should no longer automatically start
extern volatile bool debug_mode;

// Flag to tell the main polling loop to restart due to a settings change
extern volatile bool reboot_measurement_flag;

// =====================================================================================================================
// Functions
// =====================================================================================================================

// Reads the usb input, stores to buffer and returns true if a command is ready.
// - This is non-blocking and should be polled frequently
bool read_usb_input();

// Reads the buffer and processes the command accordingly
// - Implements all changes directly in itself
void process_command();