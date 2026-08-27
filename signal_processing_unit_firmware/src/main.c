// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "AD7175_adc.h"
#include "ADS8866_adc.h"
#include "buffers.h"
#include "config.h"
#include "gpio.h"
#include "interface.h"
#include "current_control.h"
#include "sensor.h"
#include "signal_processing.h"

#include <stdio.h>

#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/adc.h"

// =====================================================================================================================
// Static (Private)
// =====================================================================================================================

static bool do_clean_shutdown = false;
static uint64_t time_last_idle_print = 0;
static float temperature_voltages[NUMBER_OF_SENSORS] = {-1.0f, -1.0f, -1.0f};
static double hall_voltages[NUMBER_OF_SENSORS] = {-1.0, -1.0, -1.0};

static void init() {
    printf("Cryomagsens starting up...\n\n");

    // Initialize stdio for USB output
    stdio_init_all();
    printf("USB initialized.\n");

    // Initialize gpio pins
    init_gpio();
    printf("GPIO initialized.\n");

    // Initialize sensors with PRS interrupts
    init_sensors();
    printf("Sensors initialized.\n");

    // Initialize Pico ADC0
    adc_init();
    adc_gpio_init(PICO_ADC0);
    adc_select_input(0);
    printf("Pico ADC0 (Current saturation check) initialized.\n");

    // Initialize ADS8866 (temperature ADC)
    init_ads8866();
    printf("SPI for ADS8866 (Temperature ADC) initialized.\n");

    // Initialize AD7175 (Hall voltage ADC)
    init_ad7175();
    printf("SPI for AD7175 (Hall voltage ADC) initialized.\n");

    // Enable main power
    gpio_put(PIN_POWER_ENABLE_POS, 1);
    gpio_put(PIN_POWER_ENABLE_NEG, 1);
    printf("Main power enabled.\n");
}

static void print_results() {
    for (int i = 0; i < NUMBER_OF_SENSORS; i++) {
        if (sensor_active[i]) {
            double h = hall_voltages[i];
            float t = temperature_voltages[i];
            printf("Sensor %d: Hall Voltage = %.6f uV, Temperature Voltage = %.6f V\n", i, h, t);
        }
    }
    printf("\n");
}

// =====================================================================================================================
// Main
// =====================================================================================================================

int main()
{
    init();

    /* POLLING LOOP */
    while (true) {


        // --- READ USER COMMANDS ---
        if (read_usb_input()) {
            // Process the command if one was received
            process_command();
        }


        // --- STOP MEASUREMENT ---
        // Clean shutdown ensured all timers are turned off
        if (do_clean_shutdown || (measurement_active && debug_mode) || reboot_measurement_flag) {
            do_clean_shutdown = false;
            measurement_active = false;
            reboot_measurement_flag = false;

            // 1. Stop timers
            stop_current_timer();
            stop_integration_timer();

            // 2. Turn off read-loop
            multicore_reset_core1();

            // 3. Disable power to the current source
            gpio_put(PIN_POWER_ENABLE_2V5, 0);

            // 4. Clear integration timer flag
            integration_timer_flag = false;

            // 5. Just went idle, wait before printing
            time_last_idle_print = time_us_64();

            // 6. Report that a clean shutdown has now occured
            printf("Clean shutdown completed!\n\n");
        }


        // --- START MEASUREMENT ---
        // If we are currently inactive and we have sensors connected we want to start measurement if we ensure:
        // - Sensor connections have not recently changed and not yet been updated
        // - We are not currently waiting for a clean shutdown
        // - We are not manually turned off through the interface
        if (!measurement_active && active_sensors_count && !sensor_presence_changed_flag && !do_clean_shutdown && !debug_mode) {
            printf("Starting measurements...\n");
            measurement_active = true;

            // 1. Enable power to the current source
            // -- Since we run configure_sensors() following sensor_presence_changed, the MUX is currently set to an active sensor.
            gpio_put(PIN_POWER_ENABLE_2V5, 1);

            // 2. Find highest, non-saturated current OR set to a user-defined current level
            // -- If the user defined a specific current it will already be correct and this will do nothing
            // -- If the user defined AUTO, this line will rerun AUTO and make sure it is up to date.
            set_current_level(user_defined_current_level);

            // 3. Reconfigure AD7175 following power cycle
            sleep_ms(100); // Wait for ADC to power up
            configure_ad7175();

            // 4. Start spinning current timer
            start_current_timer();

            // 5. Calibrate real zero
            ad7175_set_zero();

            // 6. Start integration timer
            start_integration_timer();
            sleep_ms(100);

            // 7. Launch the second core to read hall voltage
            multicore_launch_core1(read_loop);

            // 8. Flush buffers
            // - This is timed to the beginning of a spinning current cycle
            consumed_buffer = true; // Mark the new consumer buffer as consumed, since we don't care about its contents
            switch_producer_buffer();
            printf("Measurements started!\n\n");
        }
        
        
        // --- DATA PROCESSING & SENSOR SWITCH ---
        if (integration_timer_flag) {
            integration_timer_flag = false;

            // 1. Start temperature voltage conversion
            float sum = 0;
            for (int i = 0; i < 10000; i++) {
                ads8866_start_conversion();
                sum += ads8866_get_voltage();
            }
            

            // 2. Switch buffers
            // - This is timed to the beginning of a spinning current cycle
            switch_producer_buffer();
            
            // 3. Get Hall voltage
            double pre_amp_hall_voltage = calculate_hall_voltage();
            double hall_voltage = pre_amp_hall_voltage / 100; // FIXME:
            double hall_voltage_uV = hall_voltage * 1000000;
            hall_voltages[current_sensor_index] = hall_voltage_uV;

            // 4. Get temperature voltage
            temperature_voltages[current_sensor_index] = sum / 10000;

            // 5. Switch to the next sensor in the MUX
            switch_to_next_sensor();

            // 6. If full rotation is completed
            if (all_sensors_read_flag) {
                all_sensors_read_flag = false;
                print_results();
            }
            
            // 7. Flush buffers
            // - This is timed to the beginning of a spinning current cycle
            flush_buffers();
        }


        // --- UPDATE SENSORS ---
        if (sensor_presence_changed_flag) {
            sensor_presence_changed_flag = false;

            printf("Sensor configuration changed...\n\n");

            sleep_ms(100);

            // Reconfigure sensors and update activity flags
            configure_sensors();

            // At least something changed, we cannot trust the latest data
            // thus we need to reconfigure measurement settings
            
            if (measurement_active) {
                do_clean_shutdown = true;
            }
        }


        // --- IDLE MESSAGE ---
        if (!measurement_active && time_us_64() - time_last_idle_print > 5000000) {

            if (debug_mode) {
                //printf("System is manually turned off. Waiting for user commands...\n\n");
            }
            else {
                printf("System is idle. Waiting for sensor connection...\n");
            }
            time_last_idle_print = time_us_64();
        }
    }
}