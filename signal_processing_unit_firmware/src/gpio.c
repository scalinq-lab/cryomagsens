// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "gpio.h"

#include "config.h"

#include "pico/stdlib.h"

// =====================================================================================================================
// API (Public)
// =====================================================================================================================

void init_gpio() {
    gpio_init(PIN_POWER_ENABLE_POS);
    gpio_set_dir(PIN_POWER_ENABLE_POS, GPIO_OUT);
    gpio_put(PIN_POWER_ENABLE_POS, 0);

    gpio_init(PIN_POWER_ENABLE_NEG);
    gpio_set_dir(PIN_POWER_ENABLE_NEG, GPIO_OUT);
    gpio_put(PIN_POWER_ENABLE_NEG, 0);

    gpio_init(PIN_CURRENT_LEVEL_0);
    gpio_set_dir(PIN_CURRENT_LEVEL_0, GPIO_OUT);
    gpio_put(PIN_CURRENT_LEVEL_0, 0);

    gpio_init(PIN_CURRENT_LEVEL_1);
    gpio_set_dir(PIN_CURRENT_LEVEL_1, GPIO_OUT);
    gpio_put(PIN_CURRENT_LEVEL_1, 0);

    gpio_init(PIN_CURRENT_DIRECTION);
    gpio_set_dir(PIN_CURRENT_DIRECTION, GPIO_OUT);
    gpio_put(PIN_CURRENT_DIRECTION, 0);

    gpio_init(PIN_CURRENT_AXIS);
    gpio_set_dir(PIN_CURRENT_AXIS, GPIO_OUT);
    gpio_put(PIN_CURRENT_AXIS, 0);

    gpio_init(PIN_SENSOR_MUX_0);
    gpio_set_dir(PIN_SENSOR_MUX_0, GPIO_OUT);
    gpio_put(PIN_SENSOR_MUX_0, 0);

    gpio_init(PIN_SENSOR_MUX_1);
    gpio_set_dir(PIN_SENSOR_MUX_1, GPIO_OUT);
    gpio_put(PIN_SENSOR_MUX_1, 0);

    gpio_init(PIN_SENSOR_PRS_0);
    gpio_set_dir(PIN_SENSOR_PRS_0, GPIO_IN);
    gpio_pull_up(PIN_SENSOR_PRS_0);

    gpio_init(PIN_SENSOR_PRS_1);
    gpio_set_dir(PIN_SENSOR_PRS_1, GPIO_IN);
    gpio_pull_up(PIN_SENSOR_PRS_1);

    gpio_init(PIN_SENSOR_PRS_2);
    gpio_set_dir(PIN_SENSOR_PRS_2, GPIO_IN);
    gpio_pull_up(PIN_SENSOR_PRS_2);

    gpio_init(PIN_POWER_ENABLE_2V5);
    gpio_set_dir(PIN_POWER_ENABLE_2V5, GPIO_OUT);
    gpio_put(PIN_POWER_ENABLE_2V5, 0);
}