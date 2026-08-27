// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include <stdbool.h>

#define INPUT_BUFFER_SIZE 64

extern volatile bool debug_mode;
extern volatile bool reboot_measurement_flag;

// EXTERN FROM MAIN FIXME:
extern volatile bool measurement_active;

bool read_usb_input();

void process_command();