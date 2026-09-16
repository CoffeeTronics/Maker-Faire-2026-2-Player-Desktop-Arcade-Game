"""
bme680.py — BME680 Environmental Sensor
=========================================
Breakout: Adafruit BME680 (I2C, QWIIC connector)

Reads temperature, humidity, barometric pressure, and gas resistance (VOC)
from the BME680 sensor via I2C.

Pressure is automatically adjusted for elevation above sea level using the
International Standard Atmosphere equation, so readings match what your
local weather service reports.

Hardware
--------
  Connect the BME680 breakout to the QWIIC connector on the Ruler baseboard.
  Uses the shared I2C bus (board.SCL / board.SDA).

Requires
--------
  adafruit_bme680 library

Usage
-----
  Pass the .bus property from an i2c_bus.I2CBus instance:

import pykit_explorer
from i2c_bus import I2CBus
from bme680 import BME680Sensor
my_i2c = I2CBus()
sensor = BME680Sensor(my_i2c.bus)
print(sensor.temperature)
print(sensor.humidity)
print(sensor.pressure)
print(sensor.gas)
sensor.print_all()

Use this module for:
  - Indoor air quality monitoring
  - Weather stations
  - Comfort level dashboards
  - Environmental data logging to SD card
"""

import math
import time
import adafruit_bme680


class BME680Sensor:
    """Read temperature, humidity, pressure, and gas from the BME680.

    Parameters
    ----------
    i2c          : raw busio.I2C object — pass i2c_bus_instance.bus
    elevation_m  : your elevation in metres above sea level (default 0)
                   Used to adjust pressure to sea-level equivalent.
                   Find your elevation at: https://www.whatismyelevation.com

    Example - Read temperature, humidity, pressure, and gas
    -------
import pykit_explorer
from i2c_bus import I2CBus
from bme680 import BME680Sensor
my_i2c = I2CBus()
sensor = BME680Sensor(my_i2c.bus, elevation_m=362)
print(sensor.temperature)
print(sensor.pressure)     # sea-level adjusted
print(sensor.humidity)
print(sensor.gas)

    """

    def __init__(self, i2c, elevation_m: float = 0):
        self._sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x77)
        self._elevation = elevation_m

    # -- Raw sensor readings -------------------------------------------------

    @property
    def temperature(self) -> float:
        """Temperature in degrees Celsius."""
        return self._sensor.temperature

    @property
    def humidity(self) -> float:
        """Relative humidity as a percentage (0–100%)."""
        return self._sensor.humidity

    @property
    def pressure(self) -> float:
        """Barometric pressure adjusted to sea level in hPa / mBar.

        Uses the International Standard Atmosphere equation:
          P0 = P1 * (1 - (0.0065h / (T + 0.0065h + 273.15))) ^ -5.257

        where P1 = measured pressure, h = elevation (m), T = temperature (°C).
        Set elevation_m on init for accurate readings.
        """
        t = self._sensor.temperature
        h = self._elevation
        mantissa = 1.0 - (0.0065 * h / (t + (0.0065 * h) + 273.15))
        adjustment = math.pow(mantissa, -5.257)
        return adjustment * self._sensor.pressure

    @property
    def pressure_raw(self) -> float:
        """Absolute (unadjusted) barometric pressure in hPa / mBar."""
        return self._sensor.pressure

    @property
    def gas(self) -> int:
        """Gas resistance in Ohms. Higher = better air quality."""
        return self._sensor.gas

    # -- Threshold helpers ---------------------------------------------------

    def temperature_level(self,
                           low: float = 25.0,
                           med: float = 30.0,
                           high: float = 35.0) -> str:
        """Return 'LOW', 'MED', 'HIGH', or 'VERY_HIGH' based on temperature.

        Parameters
        ----------
        low, med, high : threshold values in °C
        """
        t = self.temperature
        if t <= low:
            return "LOW"
        if t <= med:
            return "MED"
        if t <= high:
            return "HIGH"
        return "VERY_HIGH"

    def humidity_level(self,
                        low: float = 10.0,
                        med: float = 20.0,
                        high: float = 30.0) -> str:
        """Return 'LOW', 'MED', 'HIGH', or 'VERY_HIGH' based on humidity."""
        h = self.humidity
        if h <= low:
            return "LOW"
        if h <= med:
            return "MED"
        if h <= high:
            return "HIGH"
        return "VERY_HIGH"

    def pressure_level(self,
                        low: float = 1000.0,
                        med: float = 1013.25,
                        high: float = 1020.0) -> str:
        """Return 'LOW', 'MED', 'HIGH', or 'VERY_HIGH' based on adjusted pressure."""
        p = self.pressure
        if p <= low:
            return "LOW"
        if p <= med:
            return "MED"
        if p <= high:
            return "HIGH"
        return "VERY_HIGH"

    def gas_level(self,
                   low: int = 30000,
                   med: int = 50000,
                   high: int = 70000) -> str:
        """Return 'POOR', 'FAIR', 'GOOD', or 'EXCELLENT' based on gas resistance.

        Higher resistance = better air quality.
        """
        g = self.gas
        if g <= low:
            return "POOR"
        if g <= med:
            return "FAIR"
        if g <= high:
            return "GOOD"
        return "EXCELLENT"

    # -- Formatted strings for display / logging ----------------------------

    def formatted_strings(self) -> tuple:
        """Return (str1, str2, str3, str4) formatted strings for all four readings.

        Suitable for writing directly to LCD text labels or a serial log.

        Returns
        -------
        Tuple of four strings: temperature, humidity, pressure, gas
        """
        return (
            f"Temp: {self.temperature:.1f} C",
            f"Humidity: {self.humidity:.1f} %",
            f"Pressure: {self.pressure:.1f} mB",
            f"Gas: {self.gas} Ohms",
        )

    def print_all(self):
        """Print all four sensor readings to the console."""
        for s in self.formatted_strings():
            print(s)
        print()

    def log_loop(self, interval: float = 1.0):
        """Continuously print all readings every *interval* seconds (blocking)."""
        while True:
            self.print_all()
            time.sleep(interval)
