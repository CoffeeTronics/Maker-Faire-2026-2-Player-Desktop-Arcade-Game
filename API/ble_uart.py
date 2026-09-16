"""
ble_uart.py — BLE UART via RNBD451 Module
=========================================
Board: Dev Board

Manages the Microchip RNBD451 BLE module connected to the dev board via:
  board.BLE_TX, board.BLE_RX  — UART data bus
  board.BLE_CLR               — hardware reset pin

The RNBD451 is configured using its ASCII command interface.  Once in data
mode, any bytes written to the UART are transparently forwarded over BLE to
a connected central device (phone, PC, etc.).

Typical workflow
----------------
  1. Create a BLEUart instance  → resets module into data mode
  2. Call poll() once per main loop to update state and receive user messages
  3. Check connected, just_connected, just_disconnected for BLE status
  4. Call send() to transmit data to the connected central

BLE Connection from phone
-------------------------
  Use the "MBD" (Microchip Bluetooth Data) app or any BLE UART terminal app.
  The device advertises as "RNBD451-xxxx" by default.
"""

import re
import board
import busio
import digitalio
import time


# RNBD451 plain-text status keywords — emitted when the module sends connection
# events without %...% delimiters (firmware-version dependent).
_PROTO_KEYWORDS = ("CONNECT", "DISC", "CONN_PARAM", "AM_OPENCONN",
                   "PHY_UPDATED", "ERROR", "STREAM_OPEN")

# Catch-all pattern for unknown protocol events: ALLCAPS_WORD,4HEX
_PROTO_RE = re.compile(r"[A-Z][A-Z_]{2,},[0-9A-Fa-f]{4}")

# Seconds to suppress incoming data after any connection state change,
# to prevent protocol noise from appearing as user messages.
_SETTLE_SECS = 2.0


class BLEUart:
    """Communicate wirelessly via the RNBD451 BLE UART module.

    Parameters
    ----------
    baudrate : UART baud rate (default 115200, matching RNBD451 default)

    Example - Poll BLE UART and send messages
    -------
import pykit_explorer
from ble_uart import BLEUart
ble = BLEUart()
while True:
    msg = ble.poll()
    if ble.connected:
        ble.send("Hello BLE!\n")
    if msg:
        print("Got:", msg)
    time.sleep(1)
    
    """

    def __init__(self, baudrate: int = 115200):
        # Release pins in case they are still held from a previous run
        for pin in (board.BLE_TX, board.BLE_RX, board.BLE_CLR):
            try:
                tmp = digitalio.DigitalInOut(pin)
                tmp.deinit()
            except ValueError:
                pass

        self._uart = busio.UART(board.BLE_TX, board.BLE_RX,
                                baudrate=baudrate, timeout=0.01)
        self._reset_pin = digitalio.DigitalInOut(board.BLE_CLR)
        self._reset_pin.direction = digitalio.Direction.OUTPUT

        # Stack-level connection state: set by _parse_status via %STREAM_OPEN%
        self._connected    = False
        # Hardware-level connection state: set by plain-text proto keyword detection
        self._hw_connected = False

        self._rx_buf       = ""
        self._pending_reset = False

        # Per-poll() connection transition flags
        self._just_connected           = False
        self._just_disconnected        = False
        self._was_logically_connected  = False
        self._was_stack_connected      = False  # tracks _connected across reads

        # Settle window timestamp
        self._changed_at = 0.0

        self._reset()

    # -- Initialisation -------------------------------------------------------

    def _reset(self):
        """Hardware reset the RNBD451 module (200 ms LOW pulse).

        Waits for the module to boot, then flushes all startup messages so
        the state is clean before the main loop starts calling poll().
        """
        self._reset_pin.value = False
        time.sleep(0.2)
        self._reset_pin.value = True
        time.sleep(2.5)   # RNBD451 needs ~2 s to boot and start advertising

        # Flush UART buffer — discard all boot messages
        for _ in range(10):
            if self._uart.read(64) is None:
                break
        self._rx_buf       = ""
        self._connected    = False
        self._hw_connected = False

    # -- Connection status ----------------------------------------------------

    @property
    def connected(self) -> bool:
        """True if a BLE central is connected (stack or hardware proto events)."""
        return self._connected or self._hw_connected

    @property
    def just_connected(self) -> bool:
        """True during the first poll() call after a connection is established."""
        return self._just_connected

    @property
    def just_disconnected(self) -> bool:
        """True during the first poll() call after disconnection."""
        return self._just_disconnected

    # -- Status message parsing -----------------------------------------------

    def _parse_status(self, text: str) -> str:
        """Strip RNBD451 %STATUS% messages from text and update _connected.

        The module sends %STREAM_OPEN% when the transparent UART stream is
        active (data can flow) and %DISCONNECT% on disconnection.  All %...%
        blocks are stripped; only user data is returned.

        Fixes vs the original implementation:
        - Dangling-% bug: %MSG1%MSG2% left a lone '%' in _rx_buf that caused
          all subsequent data to be buffered indefinitely. Fixed by treating
          an empty rest after a complete extraction as a closing delimiter.
        - Plain-text STREAM_OPEN: firmware sometimes emits STREAM_OPEN without
          % delimiters. Detected in the inter-block 'before' segment.
        """
        self._rx_buf += text
        user_data = ""
        while "%" in self._rx_buf:
            before, _, rest = self._rx_buf.partition("%")
            # Text between %...% blocks may carry plain-text status keywords
            if "STREAM_OPEN" in before:
                self._connected = True
            if "DISCONNECT" in before or "REBOOT" in before:
                self._connected = False
            user_data += before
            if "%" not in rest:
                if len("%" + rest) > 256:
                    # Far too large to be a status message — flush as data
                    user_data += "%" + rest
                    self._rx_buf = ""
                elif rest == "":
                    # Lone '%' is a closing delimiter, not a new opener — discard
                    self._rx_buf = ""
                else:
                    # Incomplete status message — keep for next read
                    self._rx_buf = "%" + rest
                return user_data
            msg, _, rest = rest.partition("%")
            if msg.strip() == "STREAM_OPEN":
                self._connected = True
            elif msg.startswith("DISCONNECT") or msg.startswith("REBOOT"):
                self._connected = False
            self._rx_buf = rest
        user_data += self._rx_buf
        self._rx_buf = ""
        return user_data

    # -- Main poll / send interface -------------------------------------------

    def poll(self) -> str:
        """Read BLE data and update connection state. Call once per main loop.

        Handles proto-string filtering, settle window, and
        just_connected / just_disconnected transition tracking.

        Returns the incoming user message string, or '' if none.
        """
        now = time.monotonic()

        if self._pending_reset:
            self._pending_reset           = False
            self._rx_buf                  = ""
            self._was_logically_connected = False
            self._was_stack_connected     = False
            self._reset()
            return ""

        # Save pre-read stack state so we can detect drops during this read
        stack_was = self._connected

        # Read from UART; _parse_status strips %...% blocks and updates _connected
        data = self._uart.read(64)
        raw  = self._parse_status(
            "" if data is None else "".join(chr(b) for b in data)
        ).strip()

        # Filter plain-text protocol events; update hw_connected and settle window
        if raw and any(kw in raw for kw in _PROTO_KEYWORDS):
            self._hw_connected = "DISC" not in raw
            self._changed_at   = now
            raw = ""
        elif raw and _PROTO_RE.search(raw):
            self._hw_connected = True
            self._changed_at   = now
            raw = ""

        # When the stack-level connection drops, clear hw_connected so the
        # combined connected state also drops and just_disconnected fires.
        if stack_was and not self._connected:
            self._hw_connected = False

        # Compute combined state and transition flags
        logically_connected     = self._connected or self._hw_connected
        self._just_connected    = logically_connected and not self._was_logically_connected
        self._just_disconnected = not logically_connected and self._was_logically_connected

        if self._just_connected or self._just_disconnected:
            self._changed_at = now

        # Suppress data received within the settle window after a state change
        if raw and (now - self._changed_at) <= _SETTLE_SECS:
            raw = ""

        self._was_logically_connected = logically_connected
        return raw

    def send(self, text: str, encoding: str = "ascii"):
        """Send a string over BLE to the connected central device."""
        self._uart.write(bytes(text, encoding))

    def send_bytes(self, data: bytes):
        """Send raw bytes over BLE."""
        self._uart.write(data)

    def receive(self, num_bytes: int = 64, debug: bool = False) -> str:
        """Low-level receive — returns raw user data with %STATUS% stripped.

        Prefer poll() for main-loop use; it also handles proto filtering,
        the settle window, and connection state tracking.
        """
        if self._pending_reset:
            self._pending_reset = False
            self._rx_buf = ""
            self._reset()
            return ""
        data = self._uart.read(num_bytes)
        if data is None:
            return self._parse_status("")
        if debug:
            print(f"[BLE RAW] {data}")
        return self._parse_status("".join(chr(b) for b in data))

    def _read_raw(self, num_bytes: int = 20):
        return self._uart.read(num_bytes)

    def deinit(self):
        self._uart.deinit()
        self._reset_pin.deinit()
