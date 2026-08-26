# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

"""
Diode voltage logging script with the SMU.

- Asks you to insert sensor ID and test type
- Outputs a constant 10 µA current and measures the diode voltage once every measurement interval
- Saves the raw data file and plots the result

Equipment used:
  SMU: Keysight B2910BL 

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

# Import custom driver for the SMU
from instrument_drivers.smu_driver import SMUInterface

# Address handling. SMU can also be run using USB
IP_ADDRESS_SMU = "PLACEHOLDER"                                 
smu_address = f"TCPIP0::{IP_ADDRESS_SMU}::inst0::INSTR"


# Hardware initilization with failure checks
print(f"Attempting to connect to SMU at {smu_address}...")
try:
    smu = SMUInterface(smu_address)
    smu.initialize(voltage_compliance=10)
    
    # Try to set 4-wire mode (Remote Sense). 
    try:
        smu.set_remote_sense(True)
    except AttributeError:
        if hasattr(smu, 'write'):
            smu.write(':SENS1:REM ON')
            
    print("Connected to SMU: ", smu.get_identity())
except Exception as e:
    print(f"Failed to connect to SMU. Error: {e}")
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
# Define measurement interval in seconds
MEASUREMENT_INTERVAL = 10.0  

plot_times = []
plot_diode_v = []

print("\nStarting indefinite logging... Press Ctrl+C to stop and plot.")
print("-" * 55)
print(f"{'Time':<10} | {'Diode Voltage [V]':<20} | {'Current [µA]':<15}")
print("-" * 55)

next_reading_time = time.perf_counter()

# Main measurement loop
try:
    with open(filename_log, "w", encoding="utf-8") as log:

        # Write CSV Header
        log.write("Time,Diode_Voltage,Current_A\n")

        while True:
            # Output current
            smu.enable_output(True)
            time.sleep(1)
            smu.set_current(10e-6)
            time.sleep(0.5)

            # Read diode voltage and current from the SMU
            try:
                output_current = smu.get_current()
                diode_voltage = smu.get_voltage()
            except AttributeError:
                # Fallback to standard SCPI if custom methods aren't available
                output_current = float(smu.query("MEAS:CURR?"))
                diode_voltage = float(smu.query(":MEAS:VOLT?"))
            except Exception as e:
                print(f"Failed to read SMU: {e}")
                diode_voltage = np.nan
                output_current = np.nan

            time.sleep(2)
            smu.enable_output(False)

            now_obj = datetime.now()
            now_str = now_obj.strftime("%H:%M:%S")

            log.write(f"{now_str},{diode_voltage},{output_current}\n")
            log.flush()

            plot_times.append(now_obj)
            plot_diode_v.append(diode_voltage)

            print(f"{now_str:<10} | {diode_voltage:<20.5f} | {output_current*1_000_000:<15.6f}")

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
        smu.enable_output(False)
        smu.close()
    except Exception as e:
        print(f"Failed to close SMU cleanly: {e}")

    # Plot the data and save the plot
    if len(plot_times) > 1:
        print("Generating plot...")
        fig, ax = plt.subplots(figsize=(10, 6))

        color = 'tab:blue'
        ax.set_xlabel('Time')
        ax.set_ylabel('Diode Reading (SMU) [V]', color=color)
        ax.plot(plot_times, plot_diode_v, color=color, marker='o', linestyle='-', markersize=4, label='10 µA Drive')
        ax.tick_params(axis='y', labelcolor=color)
        ax.grid(True, linestyle='--', alpha=0.6)

        plt.title(f"{test_type.capitalize()} Log (Sensor ID: {sensor_ID})")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig.autofmt_xdate()
        ax.legend(loc='best')

        fig.tight_layout()
        plt.savefig(filename_plot)
        print(f"Plot saved to: {filename_plot}")
        plt.show()
    else:
        print("Not enough data collected to generate a plot.")