"""
cpu_temp.py — CPU Temperature Sensor
======================================
Board: Dev Board (any CircuitPython board with microcontroller.cpu.temperature)

Reads the on-chip temperature sensor built into the microcontroller.
Accuracy is typically ±5 °C — useful for thermal monitoring, not precision
measurement.

Use this module for:
  - Monitoring board temperature over time
  - Triggering alerts if the board gets too warm
  - Logging temperature to serial or SD card
"""

import microcontroller
import time


class CPUTemperature:
    """Read the on-chip CPU temperature.

    Example - Read and print CPU temperature
    -------
import pykit_explorer
from cpu_temp import CPUTemperature
temp = CPUTemperature()
print(f"Temp: {temp.celsius}°C")
print(f"Temp: {temp.fahrenheit}°F")

    """

    @property
    def celsius(self) -> float:
        """CPU temperature in degrees Celsius."""
        return microcontroller.cpu.temperature

    @property
    def fahrenheit(self) -> float:
        """CPU temperature in degrees Fahrenheit."""
        return microcontroller.cpu.temperature * (9 / 5) + 32

    def log_once(self):
        """Print a single temperature reading to the console."""
        c = self.celsius
        f = self.fahrenheit
        print(f"CPU Temp: {c:.1f} °C  ({f:.1f} °F)")

    def log_loop(self, interval: float = 1.0):
        """Continuously print temperature every *interval* seconds (blocking)."""
        while True:
            self.log_once()
            time.sleep(interval)

    def is_above(self, threshold_c: float) -> bool:
        """Return True if the CPU temperature exceeds *threshold_c* °C."""
        return self.celsius > threshold_c

    def formatted_string(self) -> str:
        """Return a formatted string suitable for UART or SD card logging."""
        return f"{self.celsius:.1f} C, {self.fahrenheit:.1f} F"
