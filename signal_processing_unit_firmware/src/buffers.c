// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "buffers.h"

#include "config.h"
#include "current_control.h"

#include <stdio.h>

volatile accum_t buffers[2] = {0, 0};
volatile uint8_t consumer_buffer_index = 0;
volatile uint8_t producer_buffer_index = 1;
volatile bool producer_writing = false;
volatile bool consumed_buffer = true;
volatile bool measurement_active = false;

void switch_producer_buffer() {

    // Check if old consumer buffer was correctly consumed
    if (!consumed_buffer) {
        printf("Warning: Consumer never consumed buffer before switch.\n");
    }

    // Mark the new consumer buffer as not yet consumed
    consumed_buffer = false;

    // Clear old consumer buffer before switching
    buffers[consumer_buffer_index].sum_n = 0;
    buffers[consumer_buffer_index].count_n = 0;
    buffers[consumer_buffer_index].sum_s = 0;
    buffers[consumer_buffer_index].count_s = 0;
    buffers[consumer_buffer_index].sum_e = 0;
    buffers[consumer_buffer_index].count_e = 0;
    buffers[consumer_buffer_index].sum_w = 0;
    buffers[consumer_buffer_index].count_w = 0;

    // Wait for read loop to finish reading first axis
    while (spinning_current_state == CURRENT_NORTH || spinning_current_state == CURRENT_SOUTH) {
        if (!measurement_active) return;
    }

    // Wait for read loop to finish reading second axis
    while (spinning_current_state == CURRENT_EAST || spinning_current_state == CURRENT_WEST)  {
        if (!measurement_active) return;
    }

    // Wait for producer to finish its last write
    while (producer_writing) {
        if (!measurement_active) return;
    }

    producer_buffer_index ^= 1;
    consumer_buffer_index ^= 1;

    // Wait for any stray writes to finish
    while (producer_writing) {
        if (!measurement_active) return;
    }
}

void flush_buffers() {
    // Since we don't care wether we actually consumed the old buffer, we mark it as consumed
    consumed_buffer = true;

    // Then perform a regular switch, which is effectively a clean flush
    switch_producer_buffer();

    // Mark the new consumer buffer as consumed, since we don't care about its contents
    consumed_buffer = true;
}