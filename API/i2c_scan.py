"""
i2c_scan.py — I2C Bus Scanner
==============================
Board: PyKit Explorer

Scans the I2C bus for connected devices and attempts to confirm each one by
reading its WHO_AM_I or chip ID register. Results include the device address,
a candidate name based on the known address map, and a confirmed device name
where a WHO_AM_I register is defined.

On-board devices covered:
  0x39  APDS9960 (gesture / colour / proximity)
  0x68  ICM-20948 (IMU, when IMU_ADDR is pulled low)
  0x69  ICM-20948 (IMU, default address)
  0x76  BME680 (environmental sensor, SDO low)
  0x77  BME680 (environmental sensor, SDO high)

Use this module for:
  - Verifying which I2C devices are present and responding on the bus
  - Confirming the exact device type via WHO_AM_I when multiple devices
    share the same address
  - Debugging QWIIC breakout connections

Example
-------
import pykit_explorer
from i2c_scan import I2CScanner
scanner = I2CScanner()
scanner.scan()
scanner.report()

"""

import board
import busio


# Candidate device names keyed by 7-bit I2C address
_KNOWN_DEVICES = {
    0x10: "VEML7700 (light sensor)",
    0x18: "LIS3DH (accelerometer)",
    0x1C: "MMA8451 (accelerometer)",
    0x1D: "LSM303 (accelerometer)",
    0x1E: "LSM303 (magnetometer) / HMC5883L",
    0x1F: "NXP FXOS8700 (IMU)",
    0x28: "BNO055 (IMU, ADDR low)",
    0x29: "BNO055 (IMU, ADDR high) / VL53L0X (distance)",
    0x38: "VEML6070 (UV sensor)",
    0x39: "APDS9960 (gesture/color/proximity)",
    0x3C: "SSD1306 (OLED 128x64, ADDR low)",
    0x3D: "SSD1306 (OLED 128x64, ADDR high)",
    0x40: "INA219 (power monitor) / HTU21D / Si7021 (temp/humidity)",
    0x44: "SHT31 (temp/humidity, ADDR low)",
    0x45: "SHT31 (temp/humidity, ADDR high)",
    0x48: "ADS1x15 (ADC, ADDR GND) / TMP102 (temp)",
    0x49: "ADS1x15 (ADC, ADDR VDD)",
    0x4A: "ADS1x15 (ADC, ADDR SDA)",
    0x4B: "ADS1x15 (ADC, ADDR SCL)",
    0x57: "MAX17048 (fuel gauge) / 24AA02 (EEPROM)",
    0x60: "Si5351 (clock gen) / MPL3115A2 (pressure)",
    0x62: "SCD40 (CO2 sensor)",
    0x68: "ICM-20948 (IMU, IMU_ADDR pulled low) / PCF8523 (RTC) / DS1307 (RTC)",
    0x69: "ICM-20948 (IMU)",
    0x6A: "LSM6DS (IMU, ADDR low) / ICM-20X",
    0x6B: "LSM6DS (IMU, ADDR high)",
    0x70: "HT16K33 (LED matrix driver)",
    0x76: "BME280 / BME680 / BMP280 (env sensor, ADDR low)",
    0x77: "BME280 / BME680 / BMP280 (env sensor, ADDR high)",
}

# WHO_AM_I definitions: address -> (register, {value: confirmed_name})
_WHO_AM_I = {
    0x18: (0x0F, {0x33: "LIS3DH"}),
    0x19: (0x0F, {0x33: "LIS3DH"}),
    0x1C: (0x0D, {0x1A: "MMA8451Q"}),
    0x1D: (0x0D, {0x1A: "MMA8451Q"}),
    0x1E: (0x0F, {0x3D: "LIS3MDL"}),
    0x28: (0x00, {0xA0: "BNO055"}),
    0x29: (0x00, {0xA0: "BNO055"}),
    0x39: (0x92, {0xAB: "APDS9960"}),
    0x68: (0x00, {0xEA: "ICM-20948"}),
    0x69: (0x00, {0xEA: "ICM-20948"}),
    0x6A: (0x0F, {0x6C: "LSM6DS33", 0x69: "LSM6DSO", 0x6B: "LSM6DSL"}),
    0x6B: (0x0F, {0x6C: "LSM6DS33", 0x69: "LSM6DSO", 0x6B: "LSM6DSL"}),
    0x76: (0xD0, {0x61: "BME680", 0x60: "BME280", 0x58: "BMP280", 0x57: "BMP280", 0x56: "BMP280"}),
    0x77: (0xD0, {0x61: "BME680", 0x60: "BME280", 0x58: "BMP280"}),
}


class I2CScanner:
    """Scan the I2C bus and identify devices via address lookup and WHO_AM_I.

    Parameters
    ----------
    scl : SCL pin (default board.SCL)
    sda : SDA pin (default board.SDA)

    Attributes
    ----------
    results : list of dicts, one per found device, each containing:
                'address'   (int)  — 7-bit I2C address
                'candidate' (str)  — name from address lookup, or 'Unknown device'
                'who_am_i'  (int or None) — raw WHO_AM_I byte, or None if not read
                'confirmed' (str or None) — confirmed device name, or None

# Access results directly
for device in scanner.results:
    print(hex(device['address']), device['confirmed'])
    """

    def __init__(self, scl=board.SCL, sda=board.SDA):
        self._i2c = busio.I2C(scl, sda)
        self.results = []

    def scan(self):
        """Scan the bus and populate results with address, candidate, and WHO_AM_I data."""
        self.results = []

        while not self._i2c.try_lock():
            pass
        try:
            addresses = self._i2c.scan()
        finally:
            self._i2c.unlock()

        for addr in sorted(addresses):
            candidate = _KNOWN_DEVICES.get(addr, "Unknown device")
            who_am_i_val = None
            confirmed = None

            if addr in _WHO_AM_I:
                reg, known_ids = _WHO_AM_I[addr]
                who_am_i_val = self._read_register(addr, reg)
                if who_am_i_val is not None:
                    confirmed = known_ids.get(who_am_i_val, "unrecognised")

            self.results.append({
                "address":   addr,
                "candidate": candidate,
                "who_am_i":  who_am_i_val,
                "confirmed": confirmed,
            })

    def report(self):
        """Print a formatted summary of the last scan."""
        if not self.results:
            print("No I2C devices found." if self.results is not None else
                  "No scan results — call scan() first.")
            return

        print("I2C scan results")
        print("=" * 40)
        print("Found {} device{}:".format(
            len(self.results), "s" if len(self.results) != 1 else ""))
        print()

        for device in self.results:
            addr = device["address"]
            print("  0x{:02X}  {}".format(addr, device["candidate"]))

            if addr in _WHO_AM_I:
                reg = _WHO_AM_I[addr][0]
                val = device["who_am_i"]
                if val is None:
                    print("        WHO_AM_I @ 0x{:02X}: read failed".format(reg))
                else:
                    print("        WHO_AM_I @ 0x{:02X}: 0x{:02X} → {}".format(
                        reg, val, device["confirmed"]))

        print()
        print("Scan complete.")

    def _read_register(self, address, register):
        """Read one byte from *register* on the device at *address*.

        Returns the byte value as an int, or None if the read fails.
        """
        result = bytearray(1)
        try:
            while not self._i2c.try_lock():
                pass
            try:
                self._i2c.writeto(address, bytes([register]))
                self._i2c.readfrom_into(address, result)
            finally:
                self._i2c.unlock()
        except OSError:
            return None
        return result[0]

    def deinit(self):
        self._i2c.deinit()
