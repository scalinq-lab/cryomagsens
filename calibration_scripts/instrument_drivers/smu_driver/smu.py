# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

import time
import pyvisa

class SMUInterface:
    """Simple driver class for the Keysight B2910BL Precision Source Measure Unit (SMU)."""

    def __init__(self, resource_name: str):
        """
        Initialize connection to the SMU.

        :param resource_name: VISA address string.
        """
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_name)
        self.inst.timeout = 5000  # 5-second timeout

    def initialize(self, voltage_compliance: float = 20.0) -> None:
        """
        Reset the instrument and configure it for Current Sourcing & Voltage Measurement.

        :param voltage_compliance: Maximum voltage limit in Volts to protect the device under test.
        """
        # Reset instrument to default state
        self.inst.write("*RST")
        self.inst.write("*CLS")

        # Configure Source Mode to Current
        self.inst.write(":SOUR1:FUNC:MODE CURR")

        # Set Voltage Compliance (Limit) to prevent over-voltage damage
        self.inst.write(f":SENS1:VOLT:PROT {voltage_compliance}")

        # Set default current source to 0 A
        self.inst.write(f":SOUR:CURR 0.0")


    def enable_output(self, enable: bool = True):
        """Turn output state ON or OFF."""
        state = "ON" if enable else "OFF"
        self.inst.write(f":OUTP {state}")

    def set_current(self, current_amps: float):
        """
        Set the forced current level in Amps.

        :param current_amps: Current value in Amps (e.g., 0.001 for 1mA, 1e-6 for 1µA)
        """
        self.inst.write(f":SOUR:CURR {current_amps}")

    def measure_voltage(self) -> float:
        """
        Measure and return the present voltage across the terminals in Volts.

        :return: Voltage value in Volts
        """
        voltage_str = self.inst.query(":MEAS:VOLT?")
        return float(voltage_str)

    def get_identity(self) -> str:
        """Return instrument ID string."""
        return self.inst.query("*IDN?").strip()

    def close(self):
        """Safely turn off output and close instrument connection."""
        try:
            self.enable_output(False)
            self.inst.close()
        except Exception:
            pass


# =====================================================================
# Example Usage
# =====================================================================
if __name__ == "__main__":
    # Replace with your actual VISA resource string
    VISA_ADDRESS = ""

    # Initialize SMU object
    smu = SMUInterface(VISA_ADDRESS)

    print(f"Connected to: {smu.get_identity()}")

    # Setup instrument with a 3.3V safety voltage compliance limit
    smu.initialize(voltage_compliance=3.3)

    # Enable channel output
    smu.enable_output(True)

    try:
        # Step through current values from 1mA to 5mA and measure voltage
        currents_to_test = [1e-3, 2e-3, 3e-3, 4e-3, 5e-3]

        for current in currents_to_test:
            smu.set_current(current)
            time.sleep(0.05)  # Brief settling delay

            voltage = smu.measure_voltage()
            print(f"Set Current: {current * 1e3:5.2f} mA | Measured Voltage: {voltage:6.4f} V")

    finally:
        # Always turn off output and close VISA resource safely
        smu.enable_output(False)
        smu.close()
        print("Output disabled and connection closed.")