# Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

"""
Calibration script for the sensor unit. 

- Code reads calibration values from the coil calibration results file 
and converts the resulting B field to an output current for the SMU.
- Asks you to input the sensor ID, drive current and temperature. 
- Performs a number of magnetic field sweeps by outputting a different currents through the Helmholtz coil.
- Performs a linear regression of the data, calculates slope, intercept and coefficient of determination (R^2).
- Plots the results and stores the raw data and the regression result to the results/sensorID directory.

Equipment used:
  SMU: Keysight B2910BL

Authors:        Julius Berg (kjuliusberg)
                Daniel Rising (danielrising)
Affiliation:    ScalinQ AB
Date: 26/8 - 2026
"""

import pandas as pd
import numpy as np
import time
import sys
import matplotlib.pyplot as plt
from scipy.stats import linregress
from pathlib import Path

# Import custom drivers for the SMU and SPU
from instrument_drivers.smu_driver import SMUInterface
from instrument_drivers.SPU import SPUInterface

# Address handling. Change SMU IP address to match your instrument
# SMU can also be connected through USB. SPU currently only has USB support
IP_ADDRESS_SMU = "PLACEHOLDER"                                
smu_address = f"TCPIP0::{IP_ADDRESS_SMU}::inst0::INSTR"
SPU_port = SPUInterface.find_pico_ports()[0]["port"]

# Hardware initilization with failure checks
print(f"Attempting to connect to SMU at {smu_address}...")
try:
    smu = SMUInterface(smu_address)
    smu.initialize(voltage_compliance=20)
    print("Connected to SMU: ", smu.get_identity())
except Exception as e:
    print(f"Failed to connect to SMU. Error: {e}")
    sys.exit(1)

print(f"Attempting to connect to SPU at {SPU_port}...")
try:
    SPU = SPUInterface(SPU_port, allowed_number_of_sensors=1)
    print("Connected to SPU: ", SPU.find_pico_ports()[0]["description"])
except Exception as e:
    print(f"Failed to connect to SPU. Error: {e}")
    sys.exit(1)

# Read coil calibration data from calibration file. Calibration data must exist for this to work
df = pd.read_csv('results/coil/coil_calibration_result.csv', sep=',')
slope, intercept, _ = df["Value"].tolist()

def b_field_to_current(B, slope=slope, intercept=intercept):

    """ 
    Function that converts a desired magnetic flux denisty to a given current,
    based on calibration data for the Helmholtz coil.

    args:
        B: Desired magnetic flux density
        slope: Linear slope coefficient, given from linear regression of coil calibration data
        intercept: Linear regression intercept

    returns:
        I: Equivalent output current in Amps

    B = kI + m --> I = (B - m) / k"""

    I = ((B - intercept) / slope) / 1000
    return I

# Initilize results files. The files will have attributes:
#   sensorID: Integer ID number for that sensor
#   drive_current: The current pushed through the Hall element
#   temp: Temperature for which the current was carried out   
print("Insert sensor ID number:")
sensorID = "sensor" + input().strip()

print("Input drive current:\n" \
"0: 3 mA\n" \
"1: 300 uA\n" \
"2: 30 uA\n" \
"3: 8.3 mA")
drive_current = int(input().strip())

if drive_current == 0:
    drive_current_string = "3mA"
elif drive_current == 1:
    drive_current_string = "300uA"
elif drive_current == 2:
    drive_current_string = "30uA"
elif drive_current == 3:
    drive_current_string = "8.3mA"
else:
    print("Invalid drive current!")
    sys.exit(1)

print("Input temperature:")
temp = input.strip()

filename_raw_data = f"results/sensor{sensorID}/sensor_calibration_raw_data_{drive_current_string}_{temp}.csv"
filename_calibration = f"results/sensor{sensorID}/sensor_calibration_result_{drive_current_string}_{temp}.csv"
filename_plot = f"results/sensor{sensorID}/sensor_calibration_plot_{drive_current_string}_{temp}.pdf"

Path(filename_raw_data).parent.mkdir(parents=True, exist_ok=True)

# Measurement parameters. 
#   b_fields: Magnetic flux density in mG
#   measurement_delay: Delay between measurements in seconds
#   integration_time: Integration time in milliseconds
b_fields = np.geomspace(1, 2000, 20)
spu_current = drive_current
number_of_runs = 10
measurement_delay = 0.5
integration_time = 5000
next_reading_time = time.perf_counter()
sample = 0

all_b_fields = []
all_voltages = []

# Send relevant measurement parameters to the SPU
SPU.set_integration_time(integration_time)
SPU.set_current_level(spu_current)

# Main measurement loop
try:
    with open(filename_raw_data, "w") as file:
            file.write("Magnetic field [mG], Voltage [µV]\n")
            
            print("\nStarting sensor calibration:")
            print("-" * 55)
            print(f"{'Sample':<10} | {'Magnetic Field [mG]':<20} | {'Voltage [µV]':<15}")
            print("-" * 55)

            # Turn on SMU output
            smu.enable_output()
            
            for run in range(number_of_runs):
                
                for B in b_fields:
                    sample += 1
                    I = b_field_to_current(B, slope, intercept)
                    smu.set_current(I)

                    time.sleep(measurement_delay)
                    SPU.reset()
                    voltage = SPU.get_latest_data()[1][0]
                    current_mA = I * 1000 
                    
                    all_b_fields.append(B)
                    all_voltages.append(voltage)
                    
                    print(f"{sample:<10} | {B:<20.3f} | {voltage:<15.8f}")
                    file.write(f"{B:.3f}, {voltage:.2f}\n")

                # Set current output to zero and wait for the magnetic field to settle
                smu.set_current(0.0)
                time.sleep(2)

except KeyboardInterrupt:
    print("\nMeasurement interrupted by user (Ctrl+C).")
except Exception as e:
    print(f"\nAn error occurred during calibration: {e}")

# Perform a clean shutdown of all the equipment
finally:
    print("\nShutting down equipment...")
    try:
        smu.enable_output(False)
        smu.close()
    except Exception as e:
        print(f"Failed to close SMU: {e}")
        
    try:
        SPU.close()
    except Exception as e:
        print(f"Failed to close Pico: {e}")

# Perform a linear regression of all the data using scipy.linregress
if len(all_b_fields) > 1:
    print("\nPerforming linear regression...")
    
    x_data = np.array(all_b_fields)
    y_data = np.array(all_voltages)

    res = linregress(x_data, y_data)
    slope = res.slope
    intercept = res.intercept
    r_squared = res.rvalue ** 2

    print("-" * 40)
    print("CALIBRATION RESULTS")
    print("-" * 40)
    print(f"Sensor Sensitivity (Slope): {slope:.4f} µV/mG")
    print(f"Offset Voltage (Intercept): {intercept:.4f} µV")
    print(f"R-squared                 : {r_squared:.6f}")
    print("-" * 40)

    # Save calibration result to the calibration results file
    try:
        with open(filename_calibration, "w", encoding="utf-8") as cal_file:
            cal_file.write("Parameter,Value,Unit\n")
            cal_file.write(f"Slope,{slope:.6f},µV/mG\n")
            cal_file.write(f"Intercept,{intercept:.6f},µV\n")
            cal_file.write(f"R_squared,{r_squared:.6f},\n")
        print(f"Regression parameters saved to: {filename_calibration}")
    except Exception as e:
        print(f"Failed to save regression results: {e}")

    print("Generating plot...")

    # Plot the result and save the plot to the results file
    plt.figure(figsize=(8, 6)) 
    plt.scatter(x_data, y_data, label="Measured Data", color="blue", alpha=0.5, s=15)
    
    x_fit = np.array([x_data.min(), x_data.max()])
    y_fit = slope * x_fit + intercept
    plt.plot(x_fit, y_fit, color="red", linewidth=2, label=f"Fit: V = {slope:.3f}*B + {intercept:.3f}")

    plt.title("Sensor Calibration")
    plt.xlabel("Magnetic Field [mG]")
    plt.ylabel("Voltage [µV]")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(filename_plot, format="pdf")
    print(f"Plot saved to: {filename_plot}")
    plt.show()

else:
    print("\nNot enough data points collected to perform linear regression.")