# Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

"""
Script that gets the raw ADC data for system debugging.

- Reads a specific number of ADC values from the SPU and notes the current modulation state
- Performs a spinning current demodulation of the signal
- Plots the captured data and annotates the signal state

Authors:        Julius Berg (kjuliusberg)
                Daniel Rising (danielrising)
Affiliation:    ScalinQ AB
Date: 26/8 - 2026            
"""
import matplotlib.pyplot as plt
import time

# Import custom driver for the SPU
from instrument_drivers.SPU import SPUInterface

# Hardware initilization with failure checks
ports = SPUInterface.find_pico_ports()
if not ports:
    print("Error: No Raspberry Pi Pico found. Check USB connection.")
    exit()

port_name = ports[0]["port"]
print(f"Connecting to Pico on {port_name} ({ports[0]['firmware']})...")

spu = SPUInterface(port=port_name)

# Set SPU into debug mode in order to disable automatic data aquisiton and enable changing of modulation settings
print("Configuring...")
spu.debug(True)
spu.toggle_current(1)
spu.set_modulation(1)
time.sleep(1)

print("Requesting raw data points from the ADC...")

raw_data = spu.get_raw_data(56000)

# Separate stable data points (mod_state == 1) by spinning current state
state_voltages = {0: [], 1: [], 2: [], 3: []}       

for item in raw_data:
    v = item[0]
    spin_state = item[1]
    mod_state = item[2]
    
    # Only collect data when the modulation is stable
    if mod_state == 1 and spin_state in state_voltages:
        state_voltages[spin_state].append(v)

hall_voltage = 9999

# Check if we captured enough data for all 4 phases
if all(len(state_voltages[s]) > 0 for s in range(4)):
    # Calculate the average voltage for each individual phase
    v_avg = {}
    for s in range(4):
        v_avg[s] = sum(state_voltages[s]) / len(state_voltages[s])
        print(f"State {s} Average: {v_avg[s]:.6f} V (from {len(state_voltages[s])} points)")

    # 4-Phase Demodulation (Lock-in average)
    # Subtracting opposing polarities cancels offset. 
    # Adding orthogonal axes averages the Hall effect across the sensor body.
    hall_voltage = (v_avg[0] - v_avg[1] - v_avg[2] + v_avg[3]) / 4.0
    
    print(f"\n---> Demodulated Hall Voltage: {hall_voltage:.8f} V <---")
else:
    print("\n---> Error: Missing stable data for one or more spinning current states. <---")
    print("     Try requesting more data points (e.g., > 2500) or check modulation frequency.")

# Generate the base time axis and extract just the voltages for a continuous background line
time_us = [i * 4 for i in range(len(raw_data))]
voltages = [item[0] for item in raw_data]

# Set up the figure
plt.figure(figsize=(10, 5))

# Plot a faint gray line connecting all points to show the continuous sequence over time
plt.plot(time_us, voltages, linestyle='-', color='gray', alpha=0.4, zorder=1)

# Prepare groups for colored markers
plot_groups = {
    "Unstable (Red)": {"time": [], "volt": [], "color": "red", "marker": "x"},
    "Stable - State 0 (WEST)": {"time": [], "volt": [], "color": "blue", "marker": "o"},
    "Stable - State 1 (EAST)": {"time": [], "volt": [], "color": "green", "marker": "o"},
    "Stable - State 2 (NORTH)": {"time": [], "volt": [], "color": "purple", "marker": "o"},
    "Stable - State 3 (SOUTH)": {"time": [], "volt": [], "color": "orange", "marker": "o"}
}

# Sort the raw data into the correct groups for plotting
for i, item in enumerate(raw_data):
    v = item[0]
    spin_state = item[1]
    mod_state = item[2]
    t = i * 4
    
    if mod_state == 0:  
        plot_groups["Unstable (Red)"]["time"].append(t)
        plot_groups["Unstable (Red)"]["volt"].append(v)
    else:               
        if spin_state == 0:
            plot_groups["Stable - State 0 (WEST)"]["time"].append(t)
            plot_groups["Stable - State 0 (WEST)"]["volt"].append(v)
        elif spin_state == 1:
            plot_groups["Stable - State 1 (EAST)"]["time"].append(t)
            plot_groups["Stable - State 1 (EAST)"]["volt"].append(v)
        elif spin_state == 2:
            plot_groups["Stable - State 2 (NORTH)"]["time"].append(t)
            plot_groups["Stable - State 2 (NORTH)"]["volt"].append(v)
        elif spin_state == 3:
            plot_groups["Stable - State 3 (SOUTH)"]["time"].append(t)
            plot_groups["Stable - State 3 (SOUTH)"]["volt"].append(v)

# Plot the grouped data
for label, data in plot_groups.items():
    if data["time"]:  
        plt.scatter(data["time"], data["volt"], 
                    color=data["color"], marker=data["marker"], 
                    s=20, label=label, zorder=2)

# Format the graph
plt.title(f"SPU Raw Voltage Over Time (Demodulated V_hall = {hall_voltage*1000:.3f} mV)")
plt.xlabel("Time (µs)")
plt.ylabel("Voltage (V)")
plt.ylim(-2.6, 2.6) 
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(loc="upper right") 
plt.tight_layout()

# Display the plot
plt.show()

# Shut down equipment
spu.set_modulation(0)
spu.debug(False)
spu.close()