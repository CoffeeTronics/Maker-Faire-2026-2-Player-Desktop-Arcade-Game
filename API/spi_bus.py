"""
spi_bus.py — SPI Bus Communication
====================================
Board: Dev Board

Wraps the default board.SPI() bus for general-purpose SPI transactions.
Manages bus locking and chip select automatically.

Hardware
--------
  board.SCK   (PB03) — SPI clock
  board.MOSI  (PB02) — Master Out Slave In
  board.MISO  (PB00) — Master In Slave Out
  board.CS    (PB01) — default chip select

The board also provides board.LCD_SPI() and board.SD_SPI() as dedicated
buses for the LCD and SD card — this module uses the default board.SPI().

Use this module for:
  - Communicating with external SPI peripherals (sensors, ADCs, EEPROMs, etc.)
  - Prototyping SPI device drivers
  - Any general-purpose SPI data exchange
"""

import board
import digitalio


class SPIBus:
    """General-purpose SPI bus wrapper with automatic CS and bus locking.

    Parameters
    ----------
    cs_pin    : chip select pin (default board.CS)
    baudrate  : SPI clock speed in Hz (default 1 MHz)
    polarity  : clock idle state (default 0)
    phase     : clock sampling edge (default 0)

    Example - Send a command and read a response in one transaction
    -------
import pykit_explorer
from spi_bus import SPIBus
spi = SPIBus()
data = spi.transfer(bytes([0x9F, 0x00, 0x00, 0x00]))
print("Response:", [hex(b) for b in data])

    """

    def __init__(self, cs_pin=board.CS, baudrate: int = 1_000_000,
                 polarity: int = 0, phase: int = 0):
        self._spi = board.SPI()
        self._cs = digitalio.DigitalInOut(cs_pin)
        self._cs.direction = digitalio.Direction.OUTPUT
        self._cs.value = True
        self._baudrate = baudrate
        self._polarity = polarity
        self._phase = phase

    def _lock(self):
        """Acquire the SPI bus lock and configure it."""
        while not self._spi.try_lock():
            pass
        self._spi.configure(baudrate=self._baudrate,
                            polarity=self._polarity,
                            phase=self._phase)

    def _unlock(self):
        """Release the SPI bus lock."""
        self._spi.unlock()

    # -- Transactions ----------------------------------------------------------

    def write(self, data: bytes):
        """Write bytes to the SPI device.

        Parameters
        ----------
        data : bytes or bytearray to send
        """
        self._lock()
        self._cs.value = False
        try:
            self._spi.write(data if isinstance(data, bytearray)
                            else bytearray(data))
        finally:
            self._cs.value = True
            self._unlock()

    def read(self, num_bytes: int, write_value: int = 0x00) -> bytearray:
        """Read bytes from the SPI device.

        Parameters
        ----------
        num_bytes   : number of bytes to read
        write_value : byte clocked out during read (default 0x00)
        """
        buf = bytearray(num_bytes)
        self._lock()
        self._cs.value = False
        try:
            self._spi.readinto(buf, write_value=write_value)
        finally:
            self._cs.value = True
            self._unlock()
        return buf

    def transfer(self, data: bytes) -> bytearray:
        """Write data and simultaneously read the same number of bytes back.

        Parameters
        ----------
        data : bytes to send; response is the same length
        """
        out = data if isinstance(data, bytearray) else bytearray(data)
        result = bytearray(len(out))
        self._lock()
        self._cs.value = False
        try:
            self._spi.write_readinto(out, result)
        finally:
            self._cs.value = True
            self._unlock()
        return result

    def write_then_read(self, out_data: bytes, in_count: int,
                        write_value: int = 0x00) -> bytearray:
        """Write a command then read a response in a single CS-low transaction.

        Parameters
        ----------
        out_data    : command bytes to send first
        in_count    : number of response bytes to read
        write_value : byte clocked out during the read phase (default 0x00)
        """
        result = bytearray(in_count)
        self._lock()
        self._cs.value = False
        try:
            self._spi.write(out_data if isinstance(out_data, bytearray)
                            else bytearray(out_data))
            self._spi.readinto(result, write_value=write_value)
        finally:
            self._cs.value = True
            self._unlock()
        return result

    def deinit(self):
        self._spi.deinit()
        self._cs.deinit()
