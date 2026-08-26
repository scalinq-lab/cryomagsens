# Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
# Copyright (c) 2026    ScalinQ AB
#
# This software is released under the MIT License. 
# <https://opensource.org/licenses/MIT>

"""Simplified driver interface for AlphaLab MR3 meters."""

import math
import struct
import time
from typing import Dict, Optional, Union
import serial
import serial.tools.list_ports


class AlphaLabMeter:
    """Simplified interface for AlphaLab 3-Axis Milligauss Meters.
    
    Example use script:
    
    import time
    from MR3 import AlphaLabMeter  

    def main():
        print("Initializing meter...")
        alphalab = AlphaLabMeter()
        
        try:
            print("-" * 40)
            print("Taking 10 magnetic field measurements...")
            print("-" * 40)
            
            for i in range(10):
                # mode="magnitude" returns just the float value of the magnitude
                mag = alphalab.get_b_field(mode="magnitude")
                
                # Print the magnitude cleanly, rounded to 2 decimal places
                print(f"Sample {i+1:2d} | |B| = {mag:.2f} mG")

                time.sleep(0.5)

        finally:
            alphalab.close()
            print("\nConnection closed.")

    if __name__ == "__main__":
        main()
    """

    BAUD = 115200
    CMD_PROP = 0x01
    CMD_STREAM = 0x03
    CMD_RESET = 0x04
    CMD_ACK = 0x08
    CMD_KILL = 0xFF
    DONT_CARE = b"\x00" * 5

    def __init__(self, port: Optional[str] = None, timeout: float = 2.0):
        """Initialize and connect to meter. Auto-detects port if not specified."""
        self.port = port or self.find_port()
        if not self.port:
            raise RuntimeError("AlphaLab meter not found. Check USB connection.")

        self._ser = serial.Serial(
            port=self.port, 
            baudrate=self.BAUD, 
            timeout=timeout
        )
        
        # 1. Aggressively clear any running processes
        self._kill()
        time.sleep(0.3)

        # 2. Query properties to get the EXACT number of fields the meter expects
        props = self.get_properties()
        raw_headers = props.get("TABLE_HEADERS", "")
        self.headers = [h.strip() for h in raw_headers.split(",") if h.strip()]
        
        if not self.headers:
            self.headers = ["X", "Y", "Z"]  # Safe fallback
        self.n_fields = len(self.headers)

        # 3. Reset time/counter (first sample resets the meter)
        self._send_cmd(self.CMD_RESET)
        total_bytes = self.n_fields * 6
        self._read_exact(total_bytes)
        self._ser.read(1)  # Consume trailing ACK byte
        
        # Drain leftover bytes safely after a full read
        time.sleep(0.05)
        self._ser.reset_input_buffer()

    # ── High-Level User Methods ───────────────────────────────────────────────

    def get_readings(self) -> Dict[str, Optional[float]]:
        """Returns a dict mapping each header name to its current value or None if disabled."""
        self._send_cmd(self.CMD_STREAM)
        
        total_bytes = self.n_fields * 6
        payload = self._read_exact(total_bytes)
        self._ser.read(1)  # Consume trailing ACK byte
        
        # Drain any leftover bytes cleanly to prevent framing shifts
        time.sleep(0.05)
        self._ser.reset_input_buffer()

        readings = {}
        for i, name in enumerate(self.headers):
            chunk = payload[i * 6 : (i + 1) * 6]
            val = self._decode_value(chunk)
            # Assign the value directly, even if it is None, so the user sees missing axes
            readings[name] = val
            
        return readings

    def get_b_field(
        self, mode: str = "magnitude"
    ) -> Union[float, Dict[str, Optional[float]]]:
        """Get magnetic field measurement.

        Args:
            mode: 'magnitude' (default) returns sqrt(X²+Y²+Z²) of available axes.
                  'components' returns dict of magnetic axes.
                  'all' returns dict with components and magnitude.
                  'x', 'y', or 'z' returns the specific float value for that axis.
        """
        data = self.get_readings()

        # Strictly extract valid (non-None) X, Y, Z components
        mag_components = {
            k: v for k, v in data.items()
            if v is not None and any(axis in k.upper() for axis in ("X", "Y", "Z", "BX", "BY", "BZ"))
        }

        # Fallback: if headers are weird, just grab the first available numeric values
        # that aren't obviously time or status fields
        if not mag_components:
            mag_components = {
                k: v for k, v in data.items() 
                if v is not None and "TIME" not in k.upper() and "STATUS" not in k.upper()
            }

        mode_upper = mode.upper()

        # 1. Handle single-axis requests ('x', 'y', 'z')
        if mode_upper in ("X", "Y", "Z"):
            for key, val in mag_components.items():
                # Matches keys like 'X Axis (mG)', 'X', 'BX', etc.
                if mode_upper in key.upper():
                    return val
            raise ValueError(f"Axis '{mode_upper}' not found or is currently disabled (Null).")

        # 2. Handle component dictionary request
        if mode == "components":
            return mag_components

        # 3. Handle Magnitude calculation
        mag = math.sqrt(sum(v**2 for v in mag_components.values()))

        if mode == "magnitude":
            return mag
            
        # 4. Handle full dictionary request
        elif mode == "all":
            # Return the full raw dictionary (including Nones) plus our computed Magnitude
            full_data = data.copy()
            full_data["Calculated_Magnitude"] = mag
            return full_data
            
        else:
            raise ValueError("mode must be 'magnitude', 'components', 'all', 'x', 'y', or 'z'")   

    def close(self):
        """Close the serial port connection."""
        if self._ser and self._ser.is_open:
            self._kill()
            self._ser.close()

    # ── Protocol & Internal Helpers ──────────────────────────────────────────

    def _kill(self):
        """Stop any running process and aggressively flush the line."""
        for _ in range(3):
            self._ser.write(bytes([self.CMD_KILL]) + self.DONT_CARE)
            time.sleep(0.1)
        
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            leftover = self._ser.read(self._ser.in_waiting or 1)
            if not leftover:
                break
            time.sleep(0.05)

        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def get_properties(self) -> Dict[str, str]:
        """Fetch ASCII property metadata dict from device."""
        self._send_cmd(self.CMD_PROP)
        
        result = bytearray()
        while True:
            chunk = self._read_exact(20)
            status = self._read_exact(1)
            result += chunk
            
            if status[0] == 0x07:  # TERMINATE
                break
            elif status[0] == 0x08:  # ACK -> request next chunk
                self._send_cmd(self.CMD_ACK)
            else:
                raise ValueError(f"Unexpected status byte: 0x{status[0]:02X}")

        raw = result.rstrip(b"\x00").decode("ascii", errors="ignore")
        props = {}
        for token in raw.split(":"):
            token = token.strip()
            if "=" in token:
                k, _, v = token.partition("=")
                props[k.strip()] = v.strip()
        return props

    def _send_cmd(self, cmd_byte: int):
        """Send a 6-byte command structure to the instrument."""
        self._ser.write(bytes([cmd_byte]) + self.DONT_CARE)

    def _read_exact(self, n: int) -> bytes:
        """Read exactly n bytes, blocking until they all arrive."""
        buf = bytearray()
        deadline = time.monotonic() + self._ser.timeout
        while len(buf) < n:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Expected {n} bytes, received {len(buf)}")
            chunk = self._ser.read(n - len(buf))
            if chunk:
                buf += chunk
        return bytes(buf)

    @staticmethod
    def _decode_value(six_bytes: bytes) -> Optional[float]:
        """Unpack 6-byte binary reading to float value."""
        if len(six_bytes) < 6:
            return None

        b1, b2 = six_bytes[0], six_bytes[1]
        is_null = bool(b1 & 0x40)
        if is_null:
            return None

        is_negative = bool(b2 & 0x08)
        decimal_shift = b2 & 0x07
        raw_int = struct.unpack(">I", six_bytes[2:6])[0]

        val = raw_int / (10**decimal_shift)
        return -val if is_negative else val

    @staticmethod
    def find_port() -> Optional[str]:
        """Find connected Silicon Labs / FTDI serial port."""
        for p in serial.tools.list_ports.comports():
            info = f"{p.description} {p.manufacturer}".lower()
            if any(k in info for k in ("ftdi", "alphalab", "cp210", "silicon labs")):
                return p.device
        return None