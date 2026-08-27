// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "signal_processing.h"

#include "config.h"
#include "AD7175_adc.h"
#include "buffers.h"
#include "current_control.h"

#include <stdio.h>

#include "pico/stdlib.h"


volatile bool integration_timer_flag = false;

static repeating_timer_t integration_timer;

static bool integration_callback(repeating_timer_t *rt) {
    integration_timer_flag = true;
    return true; 
}

void __not_in_flash_func(read_loop)() {
    while (true) {
        // Wait for DRDY (MISO goes low)
        while (gpio_get(ADC0_MISO));

        producer_writing = true;

        // Read raw ADC value (24-bit offset binary)
        int32_t adc_val = ad7175_fast_read();

        // Skip accumulation if modulation state is unstable
        if (!modulation_state_stable || !axis_state_stable) {
            producer_writing = false;
            continue;
        }

        // Center the value around 0 before accumulating
        int32_t centered_val = adc_val - zeroed_offset_binary;

        switch (spinning_current_state) {
        case CURRENT_NORTH:
            buffers[producer_buffer_index].sum_n += centered_val;
            buffers[producer_buffer_index].count_n++;
            break;
        case CURRENT_SOUTH:
            buffers[producer_buffer_index].sum_s += centered_val;
            buffers[producer_buffer_index].count_s++;
            break;
        case CURRENT_EAST:
            buffers[producer_buffer_index].sum_e += centered_val;
            buffers[producer_buffer_index].count_e++;
            break;
        case CURRENT_WEST:
            buffers[producer_buffer_index].sum_w += centered_val;
            buffers[producer_buffer_index].count_w++;
            break;
        default:
            break;
        }

        producer_writing = false;
    }
}

double  calculate_hall_voltage() {
    if (buffers[consumer_buffer_index].count_n == 0 || buffers[consumer_buffer_index].count_s == 0
            || buffers[consumer_buffer_index].count_e == 0 || buffers[consumer_buffer_index].count_w == 0) {
        printf("Warning: No samples collected for some direction during this integration period.\n");
        return 0.0;
    }

    // Average ADC value in 24bit offset binary
    int32_t adc_average_n = buffers[consumer_buffer_index].sum_n / buffers[consumer_buffer_index].count_n;
    int32_t adc_average_s = buffers[consumer_buffer_index].sum_s / buffers[consumer_buffer_index].count_s;
    int32_t adc_average_e = buffers[consumer_buffer_index].sum_e / buffers[consumer_buffer_index].count_e;
    int32_t adc_average_w = buffers[consumer_buffer_index].sum_w / buffers[consumer_buffer_index].count_w;

    // Update flag
    consumed_buffer = true;

    // Convert to voltage
    double voltage_n = ((double)adc_average_n / 0x800000) * ADC_VOLTAGE_REFERENCE;
    double voltage_s = ((double)adc_average_s / 0x800000) * ADC_VOLTAGE_REFERENCE;
    double voltage_e = ((double)adc_average_e / 0x800000) * ADC_VOLTAGE_REFERENCE;
    double voltage_w = ((double)adc_average_w / 0x800000) * ADC_VOLTAGE_REFERENCE;

    // Calculate using spinning current logic
    double voltage = (voltage_n - voltage_s + voltage_e - voltage_w) / 4;

    return voltage;
}

void start_integration_timer() {
    add_repeating_timer_ms(
        -integration_time_ms, 
        integration_callback, 
        NULL, 
        &integration_timer
    );
}

void stop_integration_timer(void) {
    cancel_repeating_timer(&integration_timer);
    integration_timer_flag = false;
}