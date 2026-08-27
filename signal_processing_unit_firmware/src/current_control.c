// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "current_control.h"

#include "config.h"

#include "pico/stdlib.h"

// =====================================================================================================================
// Static (Private)
// =====================================================================================================================

static repeating_timer_t current_timer;

// Counts the current modulation switches
static int switch_counter = 0;

// The threshhold of current modulation switches for which to switch axis
static int switch_threshold = 0;

static int64_t axis_unstable_callback(alarm_id_t id, void *user_data) {
    axis_state_stable = true;
    return 0;
}

static int64_t modulation_unstable_callback(alarm_id_t id, void *user_data) {
    modulation_state_stable = true;
    return 0;
}

static int64_t modulation_propagated_callback(alarm_id_t id, void *user_data) {
    
    // Transient has just now propagated, state is unstable for the specified time
    modulation_state_stable = false;

    // Current change has propagated, apply new state
    SpinningCurrentState new_state = (SpinningCurrentState)(uintptr_t)user_data;
    spinning_current_state = new_state;

    // Alarm to mark the state as stable again
    add_alarm_in_us(
        modulation_unstable_time_us, 
        modulation_unstable_callback, 
        NULL, 
        true
    );
    return 0; 
}

static bool current_timer_callback(repeating_timer_t *rt) {
    // Switch current modulation state
    gpio_put(PIN_CURRENT_DIRECTION, !gpio_get(PIN_CURRENT_DIRECTION));

    // Increment counter to record when it's time to switch axis
    switch_counter++;
    
    if (switch_counter >= switch_threshold) {
        // Switch axis state
        gpio_put(PIN_CURRENT_AXIS, !gpio_get(PIN_CURRENT_AXIS));

        // Reset counter
        switch_counter = 0;

        // Instantly mark state as unstable
        // (Technically this could wait for the propagation time as well, but that's a small optimization)
        axis_state_stable = false;

        // Alarm to mark state as stable again
        add_alarm_in_us(
            axis_unstable_time_us, 
            axis_unstable_callback, 
            NULL, 
            true
        );
    }   
    
    // The state that the system will be in once the change has propagated
    uint8_t pending_state = (gpio_get(PIN_CURRENT_AXIS) << 1) | gpio_get(PIN_CURRENT_DIRECTION);
    
    // Set alarm for when the change has propagated
    add_alarm_in_us(
        modulation_propagation_time_us,
        modulation_propagated_callback, 
        (void *)(uintptr_t)pending_state, 
        true
    );

    return true;
}

// =====================================================================================================================
// API (Public)
// =====================================================================================================================

// Current state
volatile bool modulation_state_stable = true;
volatile bool axis_state_stable = true;
volatile SpinningCurrentState spinning_current_state = CURRENT_SOUTH;

// Parameters
volatile uint32_t integration_time_ms = DEFAULT_INTEGRATION_TIME_MS; 
volatile uint32_t current_polarity_frequency = DEFAULT_CURRENT_POLARITY_FREQUENCY;
volatile uint32_t current_axis_frequency = DEFAULT_CURRENT_AXIS_FREQUENCY; 
volatile uint32_t modulation_propagation_time_us = DEFAULT_MODULATION_PROPAGATION_TIME_US;
volatile uint32_t modulation_unstable_time_us = DEFAULT_MODULATION_UNSTABLE_TIME_US;
volatile uint32_t axis_unstable_time_us = DEFAULT_AXIS_UNSTABLE_TIME_US;
volatile CurrentLevel user_defined_current_level = CURRENT_3000_uA; // TODO: rename and make this static, using getters/setters

void start_current_timer() {
    // Calculate the axis switching threshold, the polarity switch period and reset the counter
    switch_counter = 0;
    switch_threshold = current_polarity_frequency / current_axis_frequency;
    int polarity_period_us = FREQUENCY_TO_TIMER_US(current_polarity_frequency);

    // Start modulation timer
    add_repeating_timer_us(
        -polarity_period_us, 
        current_timer_callback, 
        NULL, 
        &current_timer
    );
}

void stop_current_timer(void) {
    cancel_repeating_timer(&current_timer);
}

void set_current_level(CurrentLevel level) {

    user_defined_current_level = level;

    switch (level)
    {
    case CURRENT_3000_uA:
        user_defined_current_level = CURRENT_3000_uA;
        gpio_put(PIN_CURRENT_LEVEL_0, 0);
        gpio_put(PIN_CURRENT_LEVEL_1, 0);
        break;

    case CURRENT_300_uA:
        user_defined_current_level = CURRENT_300_uA;
        gpio_put(PIN_CURRENT_LEVEL_0, 1);
        gpio_put(PIN_CURRENT_LEVEL_1, 0);
        break;

    case CURRENT_30_uA:
        user_defined_current_level = CURRENT_30_uA;
        gpio_put(PIN_CURRENT_LEVEL_0, 0);
        gpio_put(PIN_CURRENT_LEVEL_1, 1);
        break;

    case CURRENT_8300_uA:
        user_defined_current_level = CURRENT_8300_uA;
        gpio_put(PIN_CURRENT_LEVEL_0, 1);
        gpio_put(PIN_CURRENT_LEVEL_1, 1);
        break;

    case CURRENT_AUTO:

        break;

    default:
        break;
    }
}

