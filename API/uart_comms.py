"""
uart_comms.py — UART Serial Communication
==========================================
Board: Dev Board

Wraps busio.UART for both the debug UART and any general-purpose UART.
Provides send/receive helpers with optional string encoding.

The dev board exposes two UART buses:
  - DEBUG  (board.DEBUG_TX / board.DEBUG_RX)  — routed to the USB-serial bridge
  - BLE    (board.BLE_TX  / board.BLE_RX)     — connects to the RNBD451 BLE module
    (see ble_uart.py for BLE-specific commands)

Use this module for:
  - Sending debug strings over the hardware UART (separate from the REPL)
  - Talking to GPS modules, displays, or other serial devices
  - Loopback testing
"""

import board
import busio
import time


class UARTComms:
    """Send and receive data over a hardware UART port.

    Parameters
    ----------
    tx          : TX board pin  (default board.DEBUG_TX)
    rx          : RX board pin  (default board.DEBUG_RX)
    baudrate    : baud rate     (default 115200)
    timeout     : read timeout in seconds (default 0 = non-blocking)

    Example - Send and receive strings over UART. Place a loopback jumper between 
    DEBUG_TX and DEBUG_RX to see the sent message received.
    -------
import pykit_explorer
from uart_comms import UARTComms
uart = UARTComms()     # use debug UART
uart.send("Hello\\n")
reply = uart.receive(32)
print(reply)

    """

    def __init__(self, tx=board.DEBUG_TX, rx=board.DEBUG_RX,
                 baudrate: int = 115200, timeout: float = 0):
        self._uart = busio.UART(tx, rx, baudrate=baudrate, timeout=timeout)
        self._baudrate = baudrate

    # -- Transmit ------------------------------------------------------------

    def send(self, text: str, encoding: str = "ascii"):
        """Send a string.

        Parameters
        ----------
        text     : string to transmit
        encoding : character encoding (default 'ascii')
        """
        self._uart.write(bytes(text, encoding))

    def send_bytes(self, data: bytes):
        """Send raw bytes."""
        self._uart.write(data)

    def send_line(self, text: str, encoding: str = "ascii"):
        """Send a string followed by CRLF."""
        self.send(text + "\r\n", encoding)

    # -- Receive -------------------------------------------------------------

    def receive(self, num_bytes: int = 32) -> str:
        """Read up to *num_bytes* bytes and return as a decoded string.

        Returns an empty string if nothing is available.
        """
        data = self._uart.read(num_bytes)
        if data is None:
            return ""
        return "".join([chr(b) for b in data])

    def receive_bytes(self, num_bytes: int = 32):
        """Read up to *num_bytes* bytes and return as raw bytes (or None)."""
        return self._uart.read(num_bytes)

    # -- Periodic send helper ------------------------------------------------

    def send_periodic(self, text: str, interval: float, counter_ref: list,
                      last_time_ref: list):
        """Non-blocking periodic transmit helper.

        Designed to be called every loop iteration.  Transmits *text* when
        *interval* seconds have elapsed since the last send.

        Parameters
        ----------
        text            : string to send periodically
        interval        : minimum seconds between sends
        counter_ref     : single-element list holding a message counter [int]
        last_time_ref   : single-element list holding last send time [float]

        Example
        -------
counter   = [0]
last_time = [0.0]
while True:
    uart.send_periodic(f"count={counter[0]}\\n", 0.5, counter, last_time)
    reply = uart.receive()
    counter[0] += 1
        """
        now = time.monotonic()
        if now - last_time_ref[0] >= interval:
            self.send(text)
            last_time_ref[0] = now

    def deinit(self):
        self._uart.deinit()
