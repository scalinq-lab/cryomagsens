// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#pragma once

#include "config.h"

// Enum naming the different spinning current states after general direction of the current
typedef enum {
    
    // Current traveling from node d -> b
    CURRENT_WEST = 0,
    
    // Current traveling from node b -> d
    CURRENT_EAST = 1,

    // Current traveling from node c -> a
    CURRENT_NORTH = 2,

    // Current traveling from node a -> c
    CURRENT_SOUTH = 3

} SpinningCurrentState;

// Enum naming the different current states, this is tied to multiplexer states and hardware resistances
typedef enum {
    CURRENT_AUTO = -1,
    CURRENT_3000_uA = 0,
    CURRENT_300_uA = 1,
    CURRENT_30_uA = 2, 
    CURRENT_8300_uA = 3 
} CurrentLevel;

// Flag indicating that it's time to switch buffers and calculate results
extern volatile bool integration_timer_flag;

// Flag indicating the stability of the modulation state
// Everytime the current switches direction there will be an "unstable" time where
// the values are unreliable due to transients
extern volatile bool modulation_state_stable;

// Flag indicating the stability of the axis state
// Everytime the current switches axis there will be an "unstable" time where
// the values are unreliable due to transients
extern volatile bool axis_state_stable;

// The state of the spinning current setup
extern volatile SpinningCurrentState spinning_current_state;

// The configured time to integrate for before reporting results
extern volatile uint32_t integration_time_ms; 

// The frequency for which the current should be modulated
// - This is done via a square wave generator using a H-bridge
// - Default freuency should be 7000 Hz, which is tied to 0 phase difference in the analog bandpass filter
extern volatile uint32_t current_polarity_frequency;

// The frequency for which axises over the Hall element should switch
// - This produces big transients where the results are marked as unstable, therefore a lower frequency is prefered
// - Default is 70 Hz changing this value slightly should have little to none impact.
extern volatile uint32_t current_axis_frequency; 

// This is the time for which to wait after switching current modulation state, before noticing the results at through
// the ADC
extern volatile uint32_t modulation_propagation_time_us;

// The time it takes for a current modulation transient to settle
extern volatile uint32_t modulation_unstable_time_us; 

// The time it takes for an axis switch transient to settle
extern volatile uint32_t axis_unstable_time_us;

// The configured current level
extern volatile CurrentLevel user_defined_current_level;

// Starts the current modulation/axis switching timer
// - This also triggers the axis switching at the required intervals
// - and updates unstable times and current direction states accordingly
void start_current_timer(void);

// Stops the current modulation/axis switching
void stop_current_timer(void);

// Updates the multiplexers to the specified current level state
void set_current_level(CurrentLevel level);