"""
reg_peek_poke.py — Register-Level Peek / Poke
===============================================
Board: PyKit Explorer

A REPL-friendly utility for reading (peek) and writing (poke) individual
hardware registers on any I2C or SPI device by address. Useful for exploring
device register maps, verifying configuration writes, and debugging sensor
communication — similar to what you would do with Microchip's MPLAB Data
Visualizer but entirely in Python on the board itself.

Both I2CDevice and SPIDevice share the same three-method interface:

  peek(register)          — read one register and print the value
  peek(register, length)  — burst-read and print multiple consecutive registers
  poke(register, value)   — write one byte to a register, confirm with readback
  dump(start, end)        — read and print every register in a range

Values are always shown as hex, decimal, and binary for easy cross-referencing
against a datasheet register map.

Use this module for:
  - Exploring an unknown device's register map
  - Verifying that a configuration write took effect
  - Reading raw sensor output registers without a full driver
  - Teaching students how register-level I2C / SPI communication works

Example — I2C (ICM-20948 IMU at 0x69)
---------------------------------------
import pykit_explorer
from reg_peek_poke import I2CDevice
imu = I2CDevice(0x69)
imu.peek(0x00)           # WHO_AM_I — should return 0xEA
imu.dump(0x00, 0x06)     # Dump first 7 registers
imu.poke(0x06, 0x01)     # Write 0x01 to PWR_MGMT_1
imu.deinit()

Example — SPI
--------------
import pykit_explorer
from reg_peek_poke import SPIDevice
import board
dev = SPIDevice(board.CS)
dev.peek(0x0F)            # Read register 0x0F
dev.dump(0x00, 0x1F)      # Dump first 32 registers
dev.deinit()
"""

import board
import busio
import digitalio


# ---------------------------------------------------------------------------
# Shared display helpers
# ---------------------------------------------------------------------------

def _print_header():
    print("  Addr   Hex    Dec  Bin")
    print("  " + "-" * 33)


def _print_row(register, value):
    bits = "{:08b}".format(value)
    print("  0x{:02X}   0x{:02X}  {:3d}  {} {}".format(
        register, value, value, bits[:4], bits[4:]))


# ---------------------------------------------------------------------------
# I2C
# ---------------------------------------------------------------------------

class I2CDevice:
    """Read and write registers on an I2C device.

    Parameters
    ----------
    address  : 7-bit I2C address of the target device (e.g. 0x69)
    scl      : SCL pin (default board.SCL)
    sda      : SDA pin (default board.SDA)

    Example - Read and write registers on an I2C device (e.g. ICM-20948 IMU at 0x69)
    -------
import pykit_explorer
from reg_peek_poke import I2CDevice
imu = I2CDevice(0x69)
imu.peek(0x00)           # Read WHO_AM_I → 0xEA on ICM-20948
imu.poke(0x06, 0x80)     # Write to PWR_MGMT_1
imu.dump(0x00, 0x0F)     # Dump first 16 registers
imu.deinit()
    """

    def __init__(self, address: int, scl=board.SCL, sda=board.SDA):
        self._address = address
        self._i2c = busio.I2C(scl, sda)

    # -- Internal helpers ----------------------------------------------------

    def _read(self, register: int, length: int) -> bytearray:
        result = bytearray(length)
        while not self._i2c.try_lock():
            pass
        try:
            self._i2c.writeto(self._address, bytes([register]))
            self._i2c.readfrom_into(self._address, result)
        finally:
            self._i2c.unlock()
        return result

    def _write(self, register: int, value: int):
        while not self._i2c.try_lock():
            pass
        try:
            self._i2c.writeto(self._address, bytes([register, value]))
        finally:
            self._i2c.unlock()

    # -- Public interface ----------------------------------------------------

    def peek(self, register: int, length: int = 1):
        """Read *length* register(s) starting at *register* and print the result.

        Parameters
        ----------
        register : starting register address (0x00–0xFF)
        length   : number of consecutive registers to read (default 1)

        Returns
        -------
        Single int if length == 1, otherwise bytearray.
        """
        try:
            result = self._read(register, length)
        except OSError as e:
            print("  peek failed at 0x{:02X}: {}".format(register, e))
            return None

        _print_header()
        for i, val in enumerate(result):
            _print_row(register + i, val)

        return result[0] if length == 1 else result

    def poke(self, register: int, value: int):
        """Write *value* (0–255) to *register* and confirm with a readback.

        Parameters
        ----------
        register : target register address (0x00–0xFF)
        value    : byte value to write (0–255)
        """
        value = max(0, min(255, int(value)))

        try:
            self._write(register, value)
        except OSError as e:
            print("  poke failed at 0x{:02X}: {}".format(register, e))
            return

        print("  Wrote 0x{:02X} → register 0x{:02X}".format(value, register))

        try:
            readback = self._read(register, 1)[0]
            bits = "{:08b}".format(readback)
            print("  Readback:  0x{:02X}  {:3d}  {} {}".format(
                readback, readback, bits[:4], bits[4:]))
            if readback != value:
                print("  Warning: readback 0x{:02X} != written 0x{:02X} "
                      "(register may be read-only or partially masked)".format(
                          readback, value))
        except OSError:
            print("  Readback failed.")

    def dump(self, start: int = 0x00, end: int = 0x7F):
        """Read and display every register from *start* to *end* inclusive.

        Parameters
        ----------
        start : first register address (default 0x00)
        end   : last register address inclusive (default 0x7F)

        Returns
        -------
        Dict mapping register address (int) to value (int), or None on failure.
        """
        print("  Register dump  0x{:02X} → 0x{:02X}".format(start, end))
        _print_header()
        results = {}
        for reg in range(start, end + 1):
            try:
                val = self._read(reg, 1)[0]
                _print_row(reg, val)
                results[reg] = val
            except OSError:
                print("  0x{:02X}   read failed".format(reg))
                results[reg] = None
        return results

    def deinit(self):
        self._i2c.deinit()


# ---------------------------------------------------------------------------
# SPI
# ---------------------------------------------------------------------------

class SPIDevice:
    """Read and write registers on an SPI device.

    Uses the common MEMS sensor convention: bit 7 of the command byte is set
    to 1 for a read and 0 for a write. This matches the ICM-20948, LSM6DS,
    BMI160, and most other SPI-capable sensors. For devices that use a
    different protocol, adjust *read_bit* and *write_mask* accordingly.

    Parameters
    ----------
    cs_pin     : chip select pin (e.g. board.CS)
    baudrate   : SPI clock speed in Hz (default 1 MHz)
    polarity   : clock idle state (default 0)
    phase      : clock sampling edge (default 0)
    read_bit   : OR-mask applied to the command byte for reads (default 0x80)
    write_mask : AND-mask applied to the command byte for writes (default 0x7F)

    Example
    -------
import pykit_explorer
from reg_peek_poke import SPIDevice
import board
dev = SPIDevice(board.CS)
dev.peek(0x0F)            # Read register 0x0F
dev.poke(0x10, 0x00)      # Write 0x00 to register 0x10
dev.dump(0x00, 0x1F)      # Dump first 32 registers
dev.deinit()
    """

    def __init__(self, cs_pin, baudrate: int = 1_000_000,
                 polarity: int = 0, phase: int = 0,
                 read_bit: int = 0x80, write_mask: int = 0x7F):
        self._spi = board.SPI()
        self._cs = digitalio.DigitalInOut(cs_pin)
        self._cs.direction = digitalio.Direction.OUTPUT
        self._cs.value = True
        self._baudrate = baudrate
        self._polarity = polarity
        self._phase = phase
        self._read_bit = read_bit
        self._write_mask = write_mask

    # -- Internal helpers ----------------------------------------------------

    def _lock(self):
        while not self._spi.try_lock():
            pass
        self._spi.configure(baudrate=self._baudrate,
                            polarity=self._polarity,
                            phase=self._phase)

    def _read(self, register: int, length: int) -> bytearray:
        result = bytearray(length)
        self._lock()
        self._cs.value = False
        try:
            self._spi.write(bytearray([register | self._read_bit]))
            self._spi.readinto(result)
        finally:
            self._cs.value = True
            self._spi.unlock()
        return result

    def _write(self, register: int, value: int):
        self._lock()
        self._cs.value = False
        try:
            self._spi.write(bytearray([register & self._write_mask, value]))
        finally:
            self._cs.value = True
            self._spi.unlock()

    # -- Public interface ----------------------------------------------------

    def peek(self, register: int, length: int = 1):
        """Read *length* register(s) starting at *register* and print the result.

        Parameters
        ----------
        register : starting register address (0x00–0x7F)
        length   : number of consecutive registers to read (default 1)

        Returns
        -------
        Single int if length == 1, otherwise bytearray.
        """
        result = self._read(register, length)

        _print_header()
        for i, val in enumerate(result):
            _print_row(register + i, val)

        return result[0] if length == 1 else result

    def poke(self, register: int, value: int):
        """Write *value* (0–255) to *register* and confirm with a readback.

        Parameters
        ----------
        register : target register address (0x00–0x7F)
        value    : byte value to write (0–255)
        """
        value = max(0, min(255, int(value)))
        self._write(register, value)

        print("  Wrote 0x{:02X} → register 0x{:02X}".format(value, register))

        readback = self._read(register, 1)[0]
        bits = "{:08b}".format(readback)
        print("  Readback:  0x{:02X}  {:3d}  {} {}".format(
            readback, readback, bits[:4], bits[4:]))
        if readback != value:
            print("  Warning: readback 0x{:02X} != written 0x{:02X} "
                  "(register may be read-only or partially masked)".format(
                      readback, value))

    def dump(self, start: int = 0x00, end: int = 0x7F):
        """Read and display every register from *start* to *end* inclusive.

        Parameters
        ----------
        start : first register address (default 0x00)
        end   : last register address inclusive (default 0x7F)

        Returns
        -------
        Dict mapping register address (int) to value (int).
        """
        print("  Register dump  0x{:02X} → 0x{:02X}".format(start, end))
        _print_header()
        results = {}
        for reg in range(start, end + 1):
            val = self._read(reg, 1)[0]
            _print_row(reg, val)
            results[reg] = val
        return results

    def deinit(self):
        self._spi.deinit()
        self._cs.deinit()
