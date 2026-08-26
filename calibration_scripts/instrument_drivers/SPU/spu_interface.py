# Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

import serial
from serial.tools import list_ports
import threading
import time
import pandas as pd
from parse import parse


class SPUInterface:
    def __init__(self, port, allowed_number_of_sensors = 3, baudrate=115200, timeout=1):
        # Connect to Pico
        self.ser = serial.Serial(port, baudrate, timeout=timeout)

        self.wait_for_reboot_flag = False

        # Sensor management
        self.allowed_number_of_sensors = allowed_number_of_sensors
        self.sensor_known = [False, False, False]

        # Buffers
        self.data_buffer = [None, None, None]
        self.raw_data_buffer = []
        
        # Start background reader thread
        self.running = True
        self.lock = threading.Lock()
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()

    @staticmethod
    def find_pico_ports():
        """
        Scans all connected serial interfaces and returns a list of ports
        that are likely connected to a Raspberry Pi Pico.

        Returns:
            list[dict]: A list of dicts with port info for each detected Pico.
        """
        # Known USB identifiers for the Raspberry Pi Pico
        PICO_VID = 0x2E8A  # Raspberry Pi vendor ID
        PICO_PIDS = {
            0x0003: "Pico (C SDK - UART bridge)",
            0x000B: "Pico (C SDK - USB CDC)",
            0x0005: "Pico (MicroPython)",
            0x000A: "Pico W (MicroPython)",
            0x0009: "Pico (CircuitPython)",
            0x0024: "Pico 2 (MicroPython)",
        }

        found = []

        for port in list_ports.comports():
            is_pico = False
            firmware = "Unknown"

            # Match by VID/PID
            if port.vid == PICO_VID:
                is_pico = True
                firmware = PICO_PIDS.get(port.pid, f"Pico (PID=0x{port.pid:04X})")

            # Fallback: match by description or manufacturer string
            elif any(
                kw in (port.description or "").lower() or kw in (port.manufacturer or "").lower()
                for kw in ["pico", "raspberry pi"]
            ):
                is_pico = True
                firmware = "Pico (matched by description)"

            if is_pico:
                found.append({
                    "port":         port.device,
                    "description":  port.description,
                    "manufacturer": port.manufacturer,
                    "vid":          f"0x{port.vid:04X}" if port.vid else None,
                    "pid":          f"0x{port.pid:04X}" if port.pid else None,
                    "serial_number": port.serial_number,
                    "firmware":     firmware,
                })

        return found



    """ INPUT FROM SPU """
    def _read_loop(self):
        while self.running:
            try:
                while self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    if not line:
                        continue
                    self.parse_line(line)
            except Exception as e:
                print(f"Read error: {e}")
            time.sleep(0.001)
    
    def parse_line(self, line):

        #print(f"[SPU]: {line}")

        # Voltage reading
        pattern0 = "Sensor {:d}: Hall Voltage = {:f} uV, Temperature Voltage = {:f} V"
        result0 = parse(pattern0, line)
        if result0:
            if (not self.sensor_known[result0[0]]):
                if sum(self.sensor_known) > self.allowed_number_of_sensors:
                    print(f"Warning: More than {self.allowed_number_of_sensors} sensors detected. " 
                        f"Ignoring sensor {result0[0]}.")
                else:
                    self.sensor_known[result0[0]] = True

            self.data_buffer[result0[0]] = (result0[1], result0[2])

        # Get raw data
        pattern1 = "Raw voltage: {:f} V {:d} {:d}"
        result1 = parse(pattern1, line)
        if result1:
            self.raw_data_buffer.append([result1[0], result1[1], result1[2]])

        # Reboot acknowledgement
        elif (line == "Clean shutdown completed!" or line == "Debug mode: No reboot required."):
            self.wait_for_reboot_flag = False


    """ OUTPUT TO SPU """
    def write_to_spu(self, cmd):
        self.ser.write(f"{cmd}\n".encode('utf-8'))
        time.sleep(0.05)

    def wait_for_reboot(self):
        """Waits for the Pico reboot acknowledgement, then flush the serial buffer."""
        while self.wait_for_reboot_flag:
            time.sleep(0.1)
        self.ser.reset_input_buffer()
        self.data_buffer = [None, None, None]
        self.wait_for_reboot_flag = False

    # Show the help message
    def help(self):
        self.write_to_spu("help")

    # Print current system status
    def status(self):
        self.write_to_spu("status")

    # 0 - 3 mA, 1 - 300 uA, 2 - 30 uA, 3 - 8.3 mA, 4 - Auto (Not yet implemented)
    def set_current_level(self, current_index):
        self.wait_for_reboot_flag = True
        self.write_to_spu(f"set current level {current_index}")
        self.wait_for_reboot()

    # Set the integration time in milliseconds
    def set_integration_time(self, ms):
        self.wait_for_reboot_flag = True
        self.write_to_spu(f"set integration time {ms}")
        self.wait_for_reboot()

    # Set the current polarity switching frequency (Hz), i.e. the lock-in amplifier frequency
    def set_polarity_frequency(self, hz):
        self.wait_for_reboot_flag = True
        self.write_to_spu(f"set polarity frequency {hz}")
        self.wait_for_reboot()

    # Set the current axis switching frequency (Hz), i.e. the spinning current frequency
    def set_axis_frequency(self, hz):
        self.wait_for_reboot_flag = True
        self.write_to_spu(f"set axis frequency {hz}")
        self.wait_for_reboot()

    # Set the time from switching to seeing results through ADC
    def set_propagation_time(self, us):
        self.wait_for_reboot_flag = True
        self.write_to_spu(f"set propagation time {us}")
        self.wait_for_reboot()

    # Set the time for which to discard samples after the current has propagated
    def set_unstable_time(self, us):
        self.wait_for_reboot_flag = True
        self.write_to_spu(f"set unstable time {us}")
        self.wait_for_reboot()

    # Reboot measurements to clear all buffers
    def reset(self):
        self.wait_for_reboot_flag = True
        self.write_to_spu("reset")
        self.wait_for_reboot()

    # Toggles debug mode
    def debug(self, enabled):
        self.write_to_spu(f"debug {int(enabled)}")
    
    # Manually sets the active sensor (If connected)
    def set_sensor(self, sensor_index):
        self.wait_for_reboot_flag = True
        self.write_to_spu(f"set sensor {sensor_index}")
        self.wait_for_reboot()

    # Manually sets the current direction to: 0 - NORTH, 1 - SOUTH, 2 - EAST, 3 - WEST
    def set_current_direction(self, direction_index):
        self.write_to_spu(f"set current direction {direction_index}")

    # Manually starts (1)/stops ()0 current flow (If a sensor is connected)
    def toggle_current(self, state):
        self.write_to_spu(f"toggle current {state}")

    # Set modulation of the current (both axis and polarity) off (0) or on (1)
    def set_modulation(self, on_off):
        self.write_to_spu(f"set modulation {on_off}")

    # Get specified number of raw data points from the ADC
    def get_raw_data(self, num_points):
        self.write_to_spu(f"get raw data {num_points}")
        timeout = 0
        last_length = 0;
        while len(self.raw_data_buffer) < num_points:
            if (last_length == len(self.raw_data_buffer)):
                timeout += 1
                if (timeout > 1000):
                    print("Timeout at {} samples".format(last_length))
                    break
            else:
                last_length = len(self.raw_data_buffer)
                timeout = 0
            time.sleep(0.01)
        results = self.raw_data_buffer
        self.raw_data_buffer = []
        return results

   # Returns latest data if available, or waits until available.
    def get_latest_data(self):
        """Returns latest data if available, or waits until available."""
        while self.running:
            with self.lock:
                for i in range(3):
                    if self.data_buffer[i] is not None:
                        data = self.data_buffer[i]
                        self.data_buffer[i] = None
                        return [i, data]
            time.sleep(0.01)
        return None

    def close(self):
        self.running = False
        self.ser.close()