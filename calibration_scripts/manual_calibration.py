# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

"""
Manual calibration script for the sensor unit using DMM and SMU. 

- Code reads calibration values from the coil calibration results file 
and converts the resulting B field to an output current for the SMU.
- Asks you to input the sensor ID.
- Prompts the user to manually change node configurations (NORTH, SOUTH, EAST, WEST).
- Performs magnetic field sweeps for each node by outputting different currents through the Helmholtz coil.
- Performs a linear regression of the data, calculates slope, intercept and R^2.
- Plots the results per node, saves the plots, and calculates the final combined spinning result.
- Generates a final plot of the combined spinning regression to verify offset cancellation.
- Stores the raw data and the regression result to the results/sensorID directory.

Equipment used:
  SMU: Keysight B2910BL 
  DMM: Generic DMM (We used a RS PRO IDM-8351)
  External current source to feed constant current through the Hall element 
  (We used a generic PSU and custom voltage-to-current converter circuit)

Authors:        Julius Berg (kjuliusberg)
                Daniel Rising (danielrising)
Affiliation:    ScalinQ AB
Date: 26/8 - 2026
"""

import pandas as pd
import numpy as np
import time
import sys
import pyvisa
import matplotlib.pyplot as plt
from scipy.stats import linregress
from pathlib import Path

# Import custom drivers for the SMU
from instrument_drivers.smu_driver import SMUInterface

# Address handling. Change SMU IP address and DMM COM-port to match your instruments
# SMU can also be connected through USB. Our DMM only has USB support
dmm_address = "COM4"
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

print(f"Attempting to connect to DMM at {dmm_address}...")
rm = pyvisa.ResourceManager()
try:
    dmm = rm.open_resource(dmm_address, baud_rate=115200)
    dmm.timeout = 5000
    dmm.read_termination = '\n'
    dmm.write_termination = '\n'
    print("Connected to DMM: ", dmm.query('*IDN?').strip())
    
    dmm.write('*RST')
    dmm.write('*CLS')
    dmm.write("CONF:VOLT:DC 0.1") # DC Voltage, 100 mV range
    time.sleep(1)
except Exception as e:
    print(f"Failed to connect to DMM. Error: {e}")
    smu.close()
    rm.close()
    sys.exit(1)

# --- LOAD COIL CALIBRATION ---
try:
    df = pd.read_csv('results/coil/coil_calibration_result.csv', sep=',')
    # Extracting safely in case the order changes
    slope = df.loc[df['Parameter'].str.contains('Slope', case=False), 'Value'].values[0]
    intercept = df.loc[df['Parameter'].str.contains('Intercept', case=False), 'Value'].values[0]
    print(f"Loaded coil calibration: Slope = {slope} mG/mA, Intercept = {intercept} mG")
except Exception as e:
    print(f"Error loading coil calibration: {e}. Please run coil calibration first.")
    sys.exit(1)

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

print("Input drive current (With unit, e.g 500uA):")
drive_current = input().strip()

print("Input temperature (With unit, e.g 5.3K):")
temp = input().strip()

filename_raw = f"results/{sensorID}/sensor_manual_calibration_raw_data_{drive_current}_{temp}.csv"
filename_data = f"results/{sensorID}/sensor_manual_calibration_result_{drive_current}_{temp}.csv"
Path(filename_raw).parent.mkdir(parents=True, exist_ok=True)

# Measurement parameters:
#   b_fields_steps_mG: Magnetic flux density in mG
#   runs_per_node: Number of sweeps per node
#   measurement_delay: time delay between measurements in seconds
#   cooldown_time: time delay between runs (necessary if the coil causes self heating)
b_field_steps_mG = np.geomspace(100, 3000, 10) 
runs_per_node = 5
measurement_delay = 3
cooldown_time = 30

nodes = ["SOUTH", "NORTH", "EAST", "WEST"]
messages = [
    "Connect positive current to A and negative current to C. Measure voltage over B - D",
    "Connect positive current to C and negative current to A. Measure voltage over B - D",
    "Connect positive current to B and negative current to D. Measure voltage over A - C",
    "Connect positive current to D and negative current to B. Measure voltage over A - C"
]

# Dictionary to hold our collected voltage data and regression results
data_store = {node: [[] for _ in range(runs_per_node)] for node in nodes}
regressions = {}

# Main measurement loop
try:
    smu.set_current(0.0)
    time.sleep(0.5)

    for i, node in enumerate(nodes):
        print("\n" + "="*70)
        print(f"--- SETUP FOR {node.upper()} ---")
        input(f"{messages[i]}\nPress Enter to begin the {runs_per_node} B-field sweeps...")
        print(f"\nStarting sweeps for {node}...")

        for run in range(runs_per_node):
            print(f"\n--- Run {run + 1} / {runs_per_node} ---")
            print(f"{'B-Field [mG]':<15} | {'Current [mA]':<15} | {'DMM Voltage [µV]':<15}")
            print("-" * 52)
            
            smu.enable_output()

            for B in b_field_steps_mG:
                I_amps = b_field_to_current(B, slope, intercept)
                I_mA = I_amps * 1000
                
                smu.set_current(I_amps)
                time.sleep(measurement_delay) 
                
                # Query DMM 50 times and average the result
                measurements_V = []
                for _ in range(50):
                    voltage_str = dmm.query('READ?')
                    measurements_V.append(float(voltage_str.split(',')[0]))
                
                avg_voltage_V = sum(measurements_V) / len(measurements_V)
                voltage_uV = avg_voltage_V * 1_000_000.0
                
                data_store[node][run].append(voltage_uV)
                print(f"{B:<15.1f} | {I_mA:<15.5f} | {voltage_uV:<15.3f}")
                
            smu.enable_output(False)
            time.sleep(cooldown_time) # Cooldown/settling time between runs

        smu.set_current(0.0)
        print(f"\nAll sweeps for {node} complete. SMU current returned to 0A.")
        
        # --- DATA PROCESSING & PLOTTING PER NODE ---
        flat_b = np.tile(b_field_steps_mG, runs_per_node)
        flat_v = np.array(data_store[node]).flatten()
        
        res = linregress(flat_b, flat_v)
        k = res.slope
        m = res.intercept
        r_squared = res.rvalue ** 2

        regressions[node] = {'k': k, 'm': m, 'r2': r_squared}
        
        print("\n" + "-"*40)
        print(f"Regression Data for {node}:")
        print(f"Equation: V [µV] = {k:.6e} * B [mG] + {m:.6e}")
        print(f"R-squared: {r_squared:.6f}")
        print("-" * 40)
        
        print(f"\n>>> NOTE: Close the plot window to proceed to the next node setup! <<<")
        plt.figure(figsize=(9, 6))
        plt.scatter(flat_b, flat_v, color='blue', s=15, alpha=0.4, label=f'Raw Data ({runs_per_node} Runs)')
        
        y_fit = k * b_field_steps_mG + m
        plt.plot(b_field_steps_mG, y_fit, color='red', linewidth=2, 
                 label=f'Fit: V = {k:.4e}*B + {m:.4e}')
        
        plt.xlabel('Magnetic Field [mG]', fontsize=12)
        plt.ylabel('Voltage [µV]', fontsize=12)
        plt.title(f'{node} Node - Magnetic Field vs Measured Voltage', fontsize=14)
        plt.legend(loc='best')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Save the plot for this specific node
        filename_plot = f"results/{sensorID}/{sensorID}_manual_calibration_plot_{node}.pdf"
        plt.savefig(filename_plot, format="pdf")
        print(f"Plot saved to: {filename_plot}")
        
        plt.show() 
        time.sleep(1)

    # --- SAVE RAW DATA ---
    print(f"\nMeasurements complete. Saving raw data to {filename_raw}...")
    with open(filename_raw, "w") as f:
        header_cols = ["B_Field_mG", "Current_mA"]
        for node in nodes:
            for run in range(runs_per_node):
                header_cols.append(f"{node}_uV_Run{run+1}")
        f.write(",".join(header_cols) + "\n")
        
        for step, B in enumerate(b_field_steps_mG):
            I_mA = b_field_to_current(B, slope, intercept) * 1000
            row_data = [f"{B:.3f}", f"{I_mA:.5f}"]
            for node in nodes:
                for run in range(runs_per_node):
                    row_data.append(str(data_store[node][run][step]))
            f.write(",".join(row_data) + "\n")

    # --- FINAL SPINNING CALCULATION ---
    print("\n" + "="*70)
    print("--- FINAL LINEAR REGRESSION SUMMARY (V = kB + m) ---")
    
    for node in nodes:
        print(f"{node:<5} : V = {regressions[node]['k']:.6e} * B + {regressions[node]['m']:.6e}")
        
    alpha = (- regressions["NORTH"]['k'] - regressions["EAST"]['k'] + regressions["SOUTH"]['k'] + regressions["WEST"]['k']) / 4
    beta = (- regressions["NORTH"]['m'] - regressions["EAST"]['m'] + regressions["SOUTH"]['m'] + regressions["WEST"]['m']) / 4
    
    print("\n--- COMBINED SPINNING RESULT ---")
    print("Calculation: (SOUTH + WEST - NORTH - EAST) / 4")
    print(f"V [µV] = {alpha:.6e} * B [mG] + {beta:.6e}")
    print("======================================================================\n")

    # --- SAVE RESULTS ---
    print(f"Saving processed results to {filename_data}...")
    with open(filename_data, "w", encoding="utf-8") as f:
        f.write("Parameter,Value,Unit\n")
        for node in nodes:
            f.write(f"{node}_Slope,{regressions[node]['k']:.6e},µV/mG\n")
            f.write(f"{node}_Intercept,{regressions[node]['m']:.6e},µV\n")
            f.write(f"{node}_R_squared,{regressions[node]['r2']:.6f},\n")
        
        f.write(f"Spinning_Slope_Alpha,{alpha:.6e},µV/mG\n")
        f.write(f"Spinning_Intercept_Beta,{beta:.6e},µV\n")

    # --- COMBINED SPINNING PLOT ---
    print("\nGenerating final spinning current plot...")
    plt.figure(figsize=(9, 6))
    
    # Re-calculate raw spinning data points by flattening stored arrays
    flat_b = np.tile(b_field_steps_mG, runs_per_node)
    v_n = np.array(data_store["NORTH"]).flatten()
    v_e = np.array(data_store["EAST"]).flatten()
    v_s = np.array(data_store["SOUTH"]).flatten()
    v_w = np.array(data_store["WEST"]).flatten()
    
    # Apply spinning formula to raw data: (SOUTH + WEST - NORTH - EAST) / 4
    v_spin_raw = (v_s + v_w - v_n - v_e) / 4
    
    # Scatter plot the raw spinning points
    plt.scatter(flat_b, v_spin_raw, color='purple', s=20, alpha=0.5, label=f'Raw Spinning Data ({runs_per_node} Runs)')
    
    # Plot the final calculated spinning regression line
    y_spin_fit = alpha * b_field_steps_mG + beta
    plt.plot(b_field_steps_mG, y_spin_fit, color='black', linewidth=2, 
             label=f'Spinning Fit: V = {alpha:.4e}*B + {beta:.4e}')

    # Add a horizontal line at V=0 to easily visualize the DC offset
    plt.axhline(0, color='gray', linewidth=1, linestyle='--', label='Zero Voltage Reference')

    plt.xlabel('Magnetic Field [mG]', fontsize=12)
    plt.ylabel('Spinning Voltage [µV]', fontsize=12)
    plt.title('Sensor Calibration - Final Spinning Current Output', fontsize=14)
    plt.legend(loc='best')
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.tight_layout()
    
    filename_spinning_plot = f"results/{sensorID}/{sensorID}_manual_calibration_plot_SPINNING.pdf"
    plt.savefig(filename_spinning_plot, format="pdf")
    print(f"Spinning plot saved to: {filename_spinning_plot}")
    plt.show()

except KeyboardInterrupt:
    print("\nMeasurement interrupted by user (Ctrl+C).")
except Exception as e:
    print(f"\nAn error occurred during calibration: {e}")

# Perform a clean shutdown of all the equipment
finally:
    print("\nShutting down equipment...")
    try:
        smu.set_current(0.0)
        smu.enable_output(False)
        smu.close()
    except Exception as e:
        print(f"Failed to close SMU cleanly: {e}")
        
    try:
        dmm.close()
        rm.close()
    except Exception as e:
        print(f"Failed to close DMM/VISA connections cleanly: {e}")