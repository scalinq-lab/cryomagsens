// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include <stdint.h>
#include <stdbool.h>

// =====================================================================================================================
// ADC Sample accumulator struct
// =====================================================================================================================

typedef struct {
    int64_t sum_n;
    uint32_t count_n;
    int64_t sum_s;
    uint32_t count_s;
    int64_t sum_e;
    uint32_t count_e;
    int64_t sum_w;
    uint32_t count_w;
} accum_t;

// =====================================================================================================================
// Global variables
// =====================================================================================================================

// Two accum_t buffers, one for the consumer (core0) and one for the producer (core1)
extern volatile accum_t buffers[2];

// Flag to indicate which buffer is currently being consumed
extern volatile uint8_t consumer_buffer_index;

// Flag to indicate which buffer is currently being produced
extern volatile uint8_t producer_buffer_index;

// Flag to make sure buffers don't switch mid-write
extern volatile bool producer_writing;

// Flag to indicate if we lost buffered data during switching
extern volatile bool consumed_buffer;

// Flag for flow control in main and deadlock protection in state synced buffer switching
extern volatile bool measurement_active;

// =====================================================================================================================
// Functions
// =====================================================================================================================

// Performs a clean, timed switch between producer and consumer buffers
// - Clears old consumer buffer
// - Waits precisely until a full cycle of spinning current has completed or measurement stops
// - Switches when producer is inactive
void switch_producer_buffer();

// Performs a clean, timed flush by marking as consumed and switching buffers
void flush_buffers();