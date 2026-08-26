# Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

"""
Calibration script for the Helmholtz coil.

- SMU outputs current in steps through the Helmholtz coil
- The Alphalab MR3 measures the resulting magnetic flux density in mG
- The sweep is performed in several steps.
- Script calculates linear regression using scipy.linregress and calculates slope, 
intercept and coefficient of determination (R^2).
- Plots the results and stores the raw data, plot and the regression result to the results/coil directory.

Equipment used:
  SMU: Keysight B2910BL
  Magnetic field sensor: Alphalab MR3

Authors:        Julius Berg (kjuliusberg)
                Daniel Rising (danielrising)
Affiliation:    ScalinQ AB
Date: 26/8 - 2026
"""

import numpy as np
import sys
import time
import matplotlib.pyplot as plt
from scipy.stats import linregress
from pathlib import Path

# Import custom drivers for the SMU and Alphalab MR3
from instrument_drivers.smu_driver import SMUInterface
from instrument_drivers.alphalab import AlphaLabMeter

# Address handling. Change SMU IP address to match your instrument
# SMU can also be connected through USB. Alphalab MR3 only has USB support
IP_ADDRESS_SMU = "PLACEHOLDER"                               
smu_address = f"TCPIP0::{IP_ADDRESS_SMU}::inst0::INSTR"

# Hardware initilization with failure checks
print(f"Attempting to connect to SMU at {smu_address}...")
try:
    smu = SMUInterface(smu_address)
    smu.initialize(voltage_compliance=20)
    print("Connected to SMU: ", smu.get_identity())
except Exception as e:
    print(f"Failed to connect to SMU. Error: {e}")
    sys.exit(1)

print(f"Attempting to connect to Alphalab MR3...")
try:
    alphalab = AlphaLabMeter()
    props = alphalab.get_properties()
    print(f"Connected to Alphalab MR3: {props.get('METER_NAME', 'Unknown AlphaLab Device')}")
except Exception as e:
    print(f"Failed to connect to Alphalab MR3. Error: {e}")
    sys.exit(1)

# Initlilize result files
filename_raw_data = "results/coil/coil_calibration_raw_data.csv"
filename_calibration = "results/coil/coil_calibration_result.csv"
filename_plot = "results/coil/coil_calibration_plot.pdf"

Path(filename_raw_data).parent.mkdir(parents=True, exist_ok=True)

# Measurement parameters
#   currents: Currents to sweep through in the calibration. In Ampere
#   number_of_runs: Number of current sweeps
#   measurement_delay: Time between measurements in seconds
currents = np.geomspace(1e-4, 100e-3, 20)
number_of_runs = 10
measurement_delay = 1.5

next_reading_time = time.perf_counter()
sample = 0

# Lists to store all currents and magnetic field values
all_currents = []
all_b_fields = []

try:
    with open(filename_raw_data, "w") as file:
        file.write("Current [mA], Magnetic field [mG]\n")
        
        print("\nStarting coil calibration:")
        print("-" * 55)
        print(f"{'Sample':<10} | {'Current [mA]':<15} | {'Magnetic Field [mG]':<20}")
        print("-" * 55)

        # Main measurement loop. Will run the set number of times
        for run in range(number_of_runs):
            smu.set_current(currents[0])
            smu.enable_output()
            time.sleep(1.5)

            # The Alphalab has a problem with an unflushed buffer and sometimes returns "old data"
            # We fix this by taking 5 measurements and discard them
            for _ in range(5):
                alphalab.get_b_field(mode="magnitude")
                time.sleep(0.3)

            next_reading_time = time.perf_counter()

            # The main current sweep
            for I in currents:
                sample += 1
                smu.set_current(I)

                next_reading_time += measurement_delay
                sleep_duration = next_reading_time - time.perf_counter()

                if sleep_duration > 0:
                    time.sleep(sleep_duration)
                else:
                    next_reading_time = time.perf_counter()

                # Measures the magnetic flux denisty in the x direction. 
                # Make sure to line up the MR3 measurement probe accordingly
                b_field = alphalab.get_b_field(mode="x")
                current_mA = I * 1000 
                
                all_currents.append(current_mA)
                all_b_fields.append(b_field)
                
                print(f"{sample:<10} | {current_mA:<15.3f} | {b_field:<20.2f}")
                file.write(f"{current_mA:.3f}, {b_field:.2f}\n")

            # After a completed current run, turn of the output and wait to let the physical system settle properly
            smu.enable_output(False)
            time.sleep(1.5)
            
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
        alphalab.close()
    except Exception as e:
        print(f"Failed to close AlphaLab meter: {e}")

# Perform a linear regression of the datapoints and save the regression parameters.
# These will be read later in the manual- and automatic sensor calibration scripts
if len(all_currents) > 1:
    print("\nPerforming linear regression...")
    
    x_data = np.array(all_currents)
    y_data = np.array(all_b_fields)

    res = linregress(x_data, y_data)
    slope = res.slope
    intercept = res.intercept
    r_squared = res.rvalue ** 2

    print("-" * 40)
    print("CALIBRATION RESULTS")
    print("-" * 40)
    print(f"Coil Constant (Slope) : {slope:.4f} mG/mA")
    print(f"Background (Intercept): {intercept:.4f} mG")
    print(f"R-squared             : {r_squared:.6f}")
    print("-" * 40)

    # Save calibration result to the calibration results file
    try:
        with open(filename_calibration, "w") as cal_file:
            cal_file.write("Parameter,Value,Unit\n")
            cal_file.write(f"Slope,{slope:.6f},mG/mA\n")
            cal_file.write(f"Intercept,{intercept:.6f},mG\n")
            cal_file.write(f"R_squared,{r_squared:.6f},\n")
        print(f"Regression parameters saved to: {filename_calibration}")
    except Exception as e:
        print(f"Failed to save regression results: {e}")

    # Plot the data to see the result of the coil calibration
    print("Generating plot...")
    plt.figure(figsize=(8, 6))
    
    plt.scatter(x_data, y_data, label="Measured Data", color="blue", alpha=0.5, s=15)
    
    x_fit = np.array([x_data.min(), x_data.max()])
    y_fit = slope * x_fit + intercept
    plt.plot(x_fit, y_fit, color="red", linewidth=2, label=f"Fit: B = {slope:.3f}*I + {intercept:.3f}")

    plt.title("Helmholtz Coil Calibration")
    plt.xlabel("Current [mA]")
    plt.ylabel("Magnetic Field [mG]")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(filename_plot, format="pdf")
    print(f"Plot saved to: {filename_plot}")
    plt.show()

else:
    print("\nNot enough data points collected to perform linear regression.")