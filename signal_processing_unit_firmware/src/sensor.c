// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "config.h"
#include "sensor.h"

volatile bool sensor_presence_changed_flag = false;
volatile bool all_sensors_read_flag = false;
volatile uint8_t current_sensor_index = 0;
volatile uint8_t active_sensors_count = 0;
volatile bool sensor_active[NUMBER_OF_SENSORS] = {false, false, false};

static uint8_t presence_pins[NUMBER_OF_SENSORS] = {PIN_SENSOR_PRS_0, PIN_SENSOR_PRS_1, PIN_SENSOR_PRS_2};
static uint8_t cycle_start_sensor_index = 0;

static uint64_t time_last_presence_change = 0;

static void gpio_presence_irq_handler(uint gpio, uint32_t events) {
    if (time_us_64() - time_last_presence_change < 100000) {
        return;
    }

    gpio_put(PIN_POWER_ENABLE_2V5, 0);
    sensor_presence_changed_flag = true;

    time_last_presence_change = time_us_64();
}

void set_sensor_mux_state(uint8_t active_sensor) {
    
    switch (active_sensor)
    {
    case 0:
        gpio_put(PIN_SENSOR_MUX_0, 0);
        gpio_put(PIN_SENSOR_MUX_1, 0);
        break;
    
    case 1:
        gpio_put(PIN_SENSOR_MUX_0, 1);
        gpio_put(PIN_SENSOR_MUX_1, 0);
        break;
    
    case 2:
        gpio_put(PIN_SENSOR_MUX_0, 0);
        gpio_put(PIN_SENSOR_MUX_1, 1);
        break;
    
    default:
        break;
    }
}

void configure_sensors(void) {
    active_sensors_count = 0;
    all_sensors_read_flag = false;

    for (uint8_t i = 0; i < NUMBER_OF_SENSORS; i++)
    {
        if(!gpio_get(presence_pins[i])) {

            if (sensor_active[i] == false) {
                printf("New sensor connected at channel %u\n", i);
            }

            sensor_active[i] = true;
            active_sensors_count++;
        } else {

            if (sensor_active[i] == true) {
                printf("Sensor disconnected at channel %u\n", i);
            }

            sensor_active[i] = false;
        }
    }

    if (active_sensors_count == 0)
    {
        return;
    }
    
    for (uint8_t i = 0; i < NUMBER_OF_SENSORS; i++)
    {
        if (sensor_active[i] == true)
        {
            current_sensor_index = i;
            cycle_start_sensor_index = i;
            set_sensor_mux_state(current_sensor_index);
            break;
        }
    }
    
    return;
}

void init_sensors(void) {

    // TODO: Disable interrupts for short while to avoid contact bouncing
    for (uint8_t i = 0; i < NUMBER_OF_SENSORS; i++) {
        gpio_set_irq_enabled_with_callback(
            presence_pins[i], 
            GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, 
            true, 
            &gpio_presence_irq_handler
        );
    }

    configure_sensors();
}

void switch_to_next_sensor(void) {

    if (active_sensors_count == 0) {
        return;
    }

    uint8_t search_index = current_sensor_index;

    while (true) {
        search_index = (search_index + 1) % NUMBER_OF_SENSORS;

        if (active_sensors_count == 1) {
            all_sensors_read_flag = true;
            return;
        }

        if (sensor_active[search_index]) {
            current_sensor_index = search_index;
            set_sensor_mux_state(current_sensor_index);

            if (current_sensor_index == cycle_start_sensor_index) {
                all_sensors_read_flag = true;
            }
            return;
        }
    }
}

bool is_sensor_present(uint8_t index) {
    if (index >= NUMBER_OF_SENSORS) {
        return false;
    }
    
    return !gpio_get(presence_pins[index]);
}

