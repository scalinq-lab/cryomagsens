// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "interface.h"

#include "config.h"
#include "AD7175_adc.h"
#include "buffers.h"
#include "current_control.h"
#include "sensor.h"

#include <stdio.h>
#include <string.h>

#include "pico/stdlib.h"
#include "pico/multicore.h"

// =====================================================================================================================
// Static (Private)
// =====================================================================================================================

// Character buffer
static char usb_buffer[INPUT_BUFFER_SIZE];
static uint8_t usb_buffer_index = 0;

// Counter for retrieval of raw data points
static volatile uint32_t number_of_raw_data_points = 0;

// Alternate retrieval function for retrieval of raw data points
static void get_raw_data() {
    // Buffer
    uint32_t raw_data_buffer[number_of_raw_data_points];

    // Get raw data from the ADC
    for (uint32_t i = 0; i < number_of_raw_data_points; i++) {
        while (gpio_get(ADC0_MISO)); // Wait for DRDY (MISO goes low)
        raw_data_buffer[i] = ad7175_fast_read() | (spinning_current_state << 24) | ((axis_state_stable && modulation_state_stable) << 26); // Store the raw ADC value along with the current state and modulation stability
    }

    // Print the raw data
    for (uint32_t i = 0; i < number_of_raw_data_points; i++) {
        // Calculate voltage

        uint32_t adc_value = raw_data_buffer[i] & 0xFFFFFF; // Mask to get the 24-bit ADC value
        uint8_t spinning_current_state = (raw_data_buffer[i] >> 24) & 0x03; // Extract the current state (2 bits)
        uint8_t modulation_state_stable = (raw_data_buffer[i] >> 26) & 0x01; // Extract the modulation stability state (1 bit)

        double voltage = (((double)adc_value - (double)zeroed_offset_binary) / (double)0x800000) * ADC_VOLTAGE_REFERENCE; // Assuming bipolar mode and 24-bit ADC
        printf("Raw voltage: %f V %u %u\n", voltage, spinning_current_state, modulation_state_stable);
    }
    printf("done!\n\n");
    number_of_raw_data_points = 0; // Reset the number of raw data points after printing

    return;
}

// Reboot measurements following settings change
// - Mainly needed to flush buffers, but also to update timer intervals
// - Reboot not needed in debug mode, which is handled here
static void reboot_measurement() {
    if (debug_mode) {
        printf("Debug mode: No reboot required.\n");
    }
    else {
        reboot_measurement_flag = true;
    }
}

// =====================================================================================================================
// API (Public)
// =====================================================================================================================

volatile bool debug_mode = false;
volatile bool reboot_measurement_flag = false;

bool read_usb_input() {
    while(true) {
        // Read a character from UART with a timeout (non-blocking)
        int c = getchar_timeout_us(0);

        // No more input, exit the loop
        if (c == PICO_ERROR_TIMEOUT) return false;

        // If we receive a newline, terminate the string and exit
        if (c == '\n' || c == '\r') {
            usb_buffer[usb_buffer_index] = '\0';
            return true;
        }

        // Store the character in the buffer if there's space
        if (usb_buffer_index < INPUT_BUFFER_SIZE - 1) {
            // Store the character in the buffer if there's space
            usb_buffer[usb_buffer_index++] = (char)c;
        }

        // Buffer overflow, reset the buffer and index
        else {
            usb_buffer_index = 0;
            usb_buffer[0] = '\0';
            printf("Warning: UART buffer overflow! Command discarded.\n");
            return false;
        }
    }
}

void process_command() {
    int32_t parameter_0;
    int32_t parameter_1;

    if (strcmp(usb_buffer, "help") == 0) {
        printf("Available commands:\n\n");

        printf("  help\n");
        printf("    - Show this help message\n\n");
        
        printf("  status\n");
        printf("    - Print current system status\n\n");

        printf("  set current level <>\n");
        printf("    - 0 - 3 mA, 1 - 300 uA, 2 - 30 uA, 3 - 8.3 mA, 4 - Auto (Not yet implemented)\n\n");

        printf("  set integration time <ms>\n");
        printf("    - Set the integration time in milliseconds\n\n");
        
        printf("  set polarity frequency <Hz>\n");
        printf("    - Set the current polarity switching frequency (Hz), i.e. the lock-in amplifier frequency\n\n");

        printf("  set axis frequency <Hz>\n");
        printf("    - Set the current axis switching frequency (Hz), i.e. the spinning current frequency\n\n");
        
        printf("  set propagation time <us>\n");
        printf("    - Set the time from switching to seeing results through ADC\n\n");
        
        printf("  set unstable time <us>\n");
        printf("    - Set the time for which to discard samples after the current has propagated\n\n");
        
        printf("  reset\n");
        printf("    - Restarts measurements and clears buffers\n\n");

        printf("  debug\n");
        printf("    - Toggles debug mode\n\n");

        if (debug_mode) {
            printf("  set sensor <>\n");
            printf("    - Manually sets the active sensor (If connected)\n\n");

            printf("  set current direction <>\n");
            printf("    - Manually sets the current direction to: 0 - NORTH, 1 - SOUTH, 2 - EAST, 3 - WEST)\n\n");

            printf("  toggle current <>\n");
            printf("    - Manually starts (1)/stops (0) current flow (If a sensor is connected)\n\n");

            printf("  set modulation <>\n");
            printf("    - Set modulation of the current (both axis and polarity) off (0) or on (1)\n\n");

            printf("  get raw data <samples>\n");
            printf("    - Get specified number of raw data points from the ADC\n\n");
        }
    }

    else if (strcmp(usb_buffer, "status") == 0) {
        if (debug_mode) {
            printf("The system is currently in debug mode.\n");
            switch (spinning_current_state) {
            case CURRENT_WEST:
                printf("- Current direction is west\n");
                break;
            case CURRENT_NORTH:
                printf("- Current direction is north\n");
                break;
            case CURRENT_EAST:
                printf("- Current direction is east\n");
                break;
            case CURRENT_SOUTH:
                printf("- Current direction is south\n");
                break;
            default:
                break;
            }
            if (gpio_get(PIN_POWER_ENABLE_2V5)) {
                printf("- Current is flowing\n");
            }
            else {
                printf("- Current is not flowing\n");
            }
            printf("- Current sensor: %u\n", current_sensor_index);
        }

        else if (measurement_active) {
            printf("The system is currently active and measuring.\n");
        }

        else {
            printf("The system is currently inactive and waiting for sensors to connect.\n");
        }
        
        printf("- Sensor connection status [%d, %d, %d]\n", sensor_active[0], sensor_active[1], sensor_active[2]);
        printf("- Integration interval: %u ms\n", integration_time_ms);
        printf("- Current level: %u uA\n", user_defined_current_level);
        printf("- Current Polarity Frequency: %u Hz\n", current_polarity_frequency);
        printf("- Current Axis Frequency: %u Hz\n", current_axis_frequency);
        printf("- Current Propagation Time: %u us\n", modulation_propagation_time_us);
        printf("- Current Unstable Time: %u us\n\n", modulation_unstable_time_us);
    }

    else if (sscanf(usb_buffer, "set current level %u", &parameter_0) == 1) {        
        switch (parameter_0) {
        case CURRENT_3000_uA:
            set_current_level(CURRENT_3000_uA);
            reboot_measurement();
            printf("Set current level to 3000 uA, awaiting change to take effect...\n\n");
            break;
        case CURRENT_300_uA:
            set_current_level(CURRENT_300_uA);
            reboot_measurement();
            printf("Set current level to 300 uA, awaiting change to take effect...\n\n");
            break;
        case CURRENT_30_uA:
            set_current_level(CURRENT_30_uA);
            reboot_measurement();
            printf("Set current level to 30 uA, awaiting change to take effect...\n\n");
            break;
        case CURRENT_8300_uA:
            set_current_level(CURRENT_8300_uA);
            reboot_measurement();
            printf("Set current level to 8300 uA, awaiting change to take effect...\n\n");
            break;
        case 4:
            set_current_level(CURRENT_AUTO);
            reboot_measurement();
            printf("Set current level to auto, awaiting change to take effect...\n\n");
            break;
        default:
            printf("Current %u not defined\n\n", parameter_0);
            break;
        }
    }

    else if (sscanf(usb_buffer, "set integration time %u", &parameter_0) == 1) {        
        integration_time_ms = parameter_0;
        reboot_measurement();
        printf("Integration time set to: %u ms, awaiting change to take effect...\n\n", parameter_0);
    }
                                 
    else if (sscanf(usb_buffer, "set polarity frequency %u", &parameter_0) == 1) {
        current_polarity_frequency = (uint32_t)parameter_0;
        reboot_measurement();
        printf("Current polarity frequency set to: %u Hz, awaiting change to take effect...\n\n", parameter_0);
    }

    else if (sscanf(usb_buffer, "set axis frequency %u", &parameter_0) == 1) {
        current_axis_frequency = (uint32_t)parameter_0;
        reboot_measurement();
        printf("Current axis frequency set to: %u Hz, awaiting change to take effect...\n\n", parameter_0);
    }

    else if (sscanf(usb_buffer, "set propagation time %u", &parameter_0) == 1) {
        modulation_propagation_time_us = (uint32_t)parameter_0;
        reboot_measurement();
        printf("Modulation propagation time set to: %u us, awaiting change to take effect...\n\n", parameter_0);
    }

    else if (sscanf(usb_buffer, "set unstable time %u", &parameter_0) == 1) {
        modulation_unstable_time_us = (uint32_t)parameter_0;
        reboot_measurement();
        printf("Modulation unstable time set to: %u us, awaiting change to take effect...\n\n", parameter_0);
    }

    else if (strcmp(usb_buffer, "reset") == 0) {
        reboot_measurement();
        printf("System resetting, awaiting change to take effect...\n\n");
    }

    else if (sscanf(usb_buffer, "debug %u", &parameter_0) == 1) {
        debug_mode = parameter_0;

        if (debug_mode) {
            printf("Debug mode enabled\n\n");
        }
        else {
            printf("Debug mode disabled\n\n");
        }
    }

    else if (debug_mode && sscanf(usb_buffer, "set sensor %u", &parameter_0) == 1) {        

        if (sensor_active[parameter_0]) {
            set_sensor_mux_state((uint8_t)parameter_0);
            current_sensor_index = parameter_0;
            printf("Sensor set to sensor %u\n\n", parameter_0);
        }

        else {
            printf("No sensor connected at channel %u\n\n", parameter_0);
        }
        
    }
    
    else if (debug_mode && sscanf(usb_buffer, "set current direction %u", &parameter_0) == 1) {        
        switch (parameter_0)
        {
        case 0:
            gpio_put(PIN_CURRENT_DIRECTION, 0);
            gpio_put(PIN_CURRENT_AXIS, 1);
            spinning_current_state = CURRENT_NORTH;
            printf("Current direction set to NORTH\n\n");
            break;

        case 1:
            gpio_put(PIN_CURRENT_DIRECTION, 1);
            gpio_put(PIN_CURRENT_AXIS, 1);
            spinning_current_state = CURRENT_SOUTH;
            printf("Current direction set to SOUTH\n\n");
            break;
        case 2:
            gpio_put(PIN_CURRENT_DIRECTION, 1);
            gpio_put(PIN_CURRENT_AXIS, 0);
            spinning_current_state = CURRENT_EAST;
            printf("Current direction set to EAST\n\n");
            break;
        case 3:
            gpio_put(PIN_CURRENT_DIRECTION, 0);
            gpio_put(PIN_CURRENT_AXIS, 0);
            spinning_current_state = CURRENT_WEST;
            printf("Current direction set to WEST\n\n");
            break;
        default:
            break;
        }
    }
    
    else if (debug_mode && sscanf(usb_buffer, "toggle current %u", &parameter_0) == 1) {

        if (!parameter_0) {
            gpio_put(PIN_POWER_ENABLE_2V5, 0);
            printf("Current turned off\n\n");
        
        }
        else if (sensor_active[current_sensor_index]) {
            gpio_put(PIN_POWER_ENABLE_2V5, 1);
            printf("Current turned on\n\n");
        }
        else {
            printf("No active sensor connected at channel %d, unable to start current\n", current_sensor_index);
            printf("Connect sensor or change sensor channel\n\n");
        }
    }

    else if (debug_mode && sscanf(usb_buffer, "set modulation %u", &parameter_0) == 1) {
        if (parameter_0 == 0) {
            stop_current_timer();
            printf("Current modulation turned off\n\n");
        }
        else if (parameter_0 == 1) {
            start_current_timer();
            printf("Current modulation turned on\n\n");
        }
        else {
            printf("Error: Invalid parameter for 'set current modulation'. Use 0 or 1.\n\n");
        }
    }

    else if (debug_mode && sscanf(usb_buffer, "get raw data %u", &parameter_0) == 1) {
        printf("Getting %u raw data points from the ADC...\n", parameter_0);

        configure_ad7175();
        
        sleep_ms(1000);
        
        ad7175_set_zero();
        
        number_of_raw_data_points = parameter_0;
        multicore_launch_core1(get_raw_data);

        while (number_of_raw_data_points > 0) {
            tight_loop_contents(); // Wait for core 1 to finish
        }

        multicore_reset_core1(); // Reset core 1 after finishing
        printf("done!\n\n");
    }

    else {
        printf("Error: Unrecognized command. Type 'help' for a list of available commands.\n");
        printf("Received command: '%s'\n\n", usb_buffer);
    }

    usb_buffer_index = 0; // Reset buffer index for the next command
    usb_buffer[0] = '\0'; // Clear the buffer

    return;
}