"""
i2c_bus.py — I2C Bus Interface
================================
Board: Dev Board  (also works with the Ruler baseboard via the QWIIC connector)

Wraps board.I2C() (SCL / SDA) for scanning, reading, and writing to I2C
peripheral devices.

Hardware
--------
  Default bus: board.I2C()  → board.SCL + board.SDA
  QWIIC connector shares the same I2C bus.

Use this module for:
  - Discovering I2C devices on the bus (address scan)
  - Raw register reads and writes to any I2C peripheral
  - As a base for sensor-specific libraries
"""

import board
import busio
import time


class I2CBus:
    """Manage an I2C bus and perform device discovery and raw transfers.

    Example
    -------
import pykit_explorer 
from i2c_bus import I2CBus
bus = I2CBus()
addresses = bus.scan()  # Get all found addresses
for addr in addresses:
    try:
        data = bus.read_register(addr, 0x00, 2)
        print(f"Address 0x{addr:02X}: {data}")
    except Exception as e:
        print(f"Address 0x{addr:02X}: Error - {e}")
        

    """

    def __init__(self, scl=board.SCL, sda=board.SDA):
        self._i2c = busio.I2C(scl, sda)

    def scan(self, print_results: bool = True) -> list:
        """Scan the bus and return a list of found device addresses.

        Parameters
        ----------
        print_results : if True, print discovered addresses to the console

        Returns
        -------
        List of integer addresses (e.g. [0x48, 0x68])
        """
        while not self._i2c.try_lock():
            pass
        addresses = []
        try:
            addresses = self._i2c.scan()
            if print_results:
                if addresses:
                    print("I2C devices found:", [hex(a) for a in addresses])
                else:
                    print("No I2C devices found.")
        finally:
            self._i2c.unlock()
        return addresses

    def scan_loop(self, interval: float = 2.0):
        """Continuously scan the bus and print results every *interval* seconds.

        Blocks until interrupted with Ctrl-C.
        """
        while not self._i2c.try_lock():
            pass
        try:
            while True:
                print("I2C addresses found:",
                      [hex(a) for a in self._i2c.scan()])
                time.sleep(interval)
        finally:
            self._i2c.unlock()

    # -- Raw transfers (lock managed internally) -----------------------------

    def write_register(self, address: int, register: int, data: bytes):
        """Write *data* bytes to *register* on the device at *address*.

        Parameters
        ----------
        address  : 7-bit I2C device address
        register : register / command byte
        data     : bytes to write after the register byte
        """
        buf = bytes([register]) + bytes(data)
        while not self._i2c.try_lock():
            pass
        try:
            self._i2c.writeto(address, buf)
        finally:
            self._i2c.unlock()

    def read_register(self, address: int, register: int,
                      num_bytes: int) -> bytearray:
        """Read *num_bytes* from *register* on the device at *address*.

        Returns
        -------
        bytearray of length *num_bytes*
        """
        result = bytearray(num_bytes)
        while not self._i2c.try_lock():
            pass
        try:
            self._i2c.writeto(address, bytes([register]))
            self._i2c.readfrom_into(address, result)
        finally:
            self._i2c.unlock()
        return result

    @property
    def bus(self):
        """The raw busio.I2C object — pass this to Adafruit driver libraries."""
        return self._i2c

    def deinit(self):
        self._i2c.deinit()
