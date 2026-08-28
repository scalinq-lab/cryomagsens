# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

"""
Logging script with the SPU.

- Asks you to insert sensor ID and test type
- Measures the hall voltage and diode voltage once every measurement interval time
- Saves the raw data file to csv and plots the result

Authors:        Julius Berg (kjuliusberg)
                Daniel Rising (danielrising)
Affiliation:    ScalinQ AB
Date: 26/8 - 2026            
"""
import time
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path

# Import custom driver for the SPU
from instrument_drivers.SPU import SPUInterface

SPU_port = SPUInterface.find_pico_ports()[0]["port"]
print(f"Attempting to connect to SPU at {SPU_port}...")
try:
    SPU = SPUInterface(SPU_port, allowed_number_of_sensors=1)
    SPU.set_integration_time(8000)
    print("Connected to SPU: ", SPU.find_pico_ports()[0]["description"])
except Exception as e:
    print(f"Failed to connect to SPU. Error: {e}")
    sys.exit(1)

# Initilize results files. The files will have attributes:
#   sensorID: Integer ID number for that sensor
#   test_type: What kind of test you are running, e.g cooldown or warmup
print("Input sensor ID number:")
sensor_ID = input().strip()

print("Insert test type (e.g cooldown or warmup):")
test_type = input().strip()

filename_log = f"results/sensor{sensor_ID}/sensor{sensor_ID}_{test_type}_log.csv"
filename_plot = f"results/sensor{sensor_ID}/sensor{sensor_ID}_{test_type}_plot.pdf"

Path(filename_log).parent.mkdir(parents=True, exist_ok=True)
# Define measurement interval in seconde
MEASUREMENT_INTERVAL = 10.0  

plot_times = []
plot_diode_v = []
plot_hall_v = []

print("\nStarting indefinite logging... Press Ctrl+C to stop and plot.")
print("-" * 55)
print(f"{'Time':<10} | {'Diode Voltage':<20} | {'Hall Voltage':<20}")
print("-" * 55)

next_reading_time = time.perf_counter()
SPU.set_current_level(2)
# Main measurement loop
try:
    with open(filename_log, "a", encoding="utf-8") as log:

        # Write CSV Header
        #log.write("Time,Diode_Voltage,Hall_Voltage\n")

        while True:
            # Read doide voltage from the SPU
            try:
                hall_voltage, diode_voltage = SPU.get_latest_data()[1]
            except Exception as e:
                print(f"Failed to read SPU: {e}")
                diode_voltage = np.nan
                hall_voltage = np.nan

            now_obj = datetime.now()
            now_str = now_obj.strftime("%H:%M:%S")

            log.write(f"{now_str},{diode_voltage},{hall_voltage}\n")
            log.flush()

            plot_times.append(now_obj)
            plot_diode_v.append(diode_voltage)
            plot_hall_v.append(hall_voltage)

            print(f"{now_str:<10} | {diode_voltage:<20.5f} | {hall_voltage:<20.5f}")

            next_reading_time += MEASUREMENT_INTERVAL
            sleep_duration = next_reading_time - time.perf_counter()
            
            if sleep_duration > 0:
                time.sleep(sleep_duration)
            else:
                next_reading_time = time.perf_counter()

except KeyboardInterrupt:
    print("\nMeasurement stopped by user (Ctrl+C).")

except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")

finally:
    # Perform a safe shutdown of the equipment
    print("Shutting down equipment...")
    try:
        SPU.close()
    except Exception as e:
        print(f"Failed to close Pico cleanly: {e}")

    # Plot the data and save the plot
    if len(plot_times) > 1:
        print("Generating plot...")
        fig, ax = plt.subplots(figsize=(10, 6))

        color = 'tab:blue'
        ax.set_xlabel('Time')
        ax.set_ylabel('Diode Reading (SPU)', color=color)
        ax.plot(plot_times, plot_diode_v, color=color, marker='o', linestyle='-', markersize=4, label='Diode (SPU)')
        ax.plot(plot_times, np.array(plot_hall_v), color=color, marker='o', linestyle='-', markersize=4, label='Diode (SPU)')
        ax.tick_params(axis='y', labelcolor=color)
        ax.grid(True, linestyle='--', alpha=0.6)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig.autofmt_xdate()
        ax.legend(loc='best')

        fig.tight_layout()
        plt.savefig(filename_plot)
        print(f"Plot saved to: {filename_plot}")
        plt.show()
    else:
        print("Not enough data collected to generate a plot.")