"""
digital_io.py — Digital Input / Output
=======================================
Board: Dev Board (any digital-capable pin)

Provides simple wrappers for reading digital inputs and driving digital outputs.
Use this module any time your project needs to:
  - Read a button, switch, or logic-level signal
  - Drive an LED, relay, transistor, or other digital load
  - Detect edges (press / release events)

Typical pins: D0–D7, D13 (LED), A0–A5 (also usable as digital I/O)
"""

import board
import digitalio
import time


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

class DigitalOutput:
    """Drive a single digital output pin HIGH or LOW.

    Example - Drive an LED output, blink and toggle
    -------
import pykit_explorer
from digital_io import DigitalOutput
led = DigitalOutput(board.LED)
led.on()
time.sleep(0.5)
led.off()
time.sleep(0.5)
led.toggle()
time.sleep(0.5)
led.blink(on_time=0.2, off_time=0.2, count=5)

    """

    def __init__(self, pin):
        self._pin = digitalio.DigitalInOut(pin)
        self._pin.direction = digitalio.Direction.OUTPUT
        self._state = False

    @property
    def value(self):
        return self._pin.value

    @value.setter
    def value(self, state: bool):
        self._pin.value = state
        self._state = state

    def on(self):
        """Drive the pin HIGH."""
        self.value = True

    def off(self):
        """Drive the pin LOW."""
        self.value = False

    def toggle(self):
        """Flip the current output state."""
        self.value = not self._state

    def blink(self, on_time: float = 0.5, off_time: float = 0.5, count: int = 1):
        """Blink the output *count* times (blocking).

        Parameters
        ----------
        on_time  : seconds the pin is HIGH per blink
        off_time : seconds the pin is LOW between blinks
        count    : number of blink cycles
        """
        for _ in range(count):
            self.on()
            time.sleep(on_time)
            self.off()
            time.sleep(off_time)

    def deinit(self):
        self._pin.deinit()


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

class DigitalInput:
    """Read a digital input pin, with optional internal pull resistor.

    Parameters
    ----------
    pin       : board pin (e.g. board.D3, board.A0)
    pull      : digitalio.Pull.UP, digitalio.Pull.DOWN, or None

    Example - Read a button state and both the value and if it is pressed
    -------
import pykit_explorer
from digital_io import DigitalInput
import digitalio
btn = DigitalInput(board.D3, pull=digitalio.Pull.UP)
while True:
    print(btn.value)         # True = not pressed (active-low)
    print(btn.is_pressed())  # True when button pulled LOW
    time.sleep(0.1)  # debounce delay

"""

    def __init__(self, pin, pull=digitalio.Pull.UP):
        self._pin = digitalio.DigitalInOut(pin)
        self._pin.direction = digitalio.Direction.INPUT
        if pull is not None:
            self._pin.pull = pull
        self._active_low = (pull == digitalio.Pull.UP)

    @property
    def value(self):
        """Raw pin state (True = HIGH)."""
        return self._pin.value

    def is_pressed(self):
        """Return True when the button/switch is in its active state.

        For pull-up wiring (common): returns True when pin is LOW.
        For pull-down wiring: returns True when pin is HIGH.
        """
        return not self._pin.value if self._active_low else self._pin.value

    def deinit(self):
        self._pin.deinit()


# ---------------------------------------------------------------------------
# Edge detector
# ---------------------------------------------------------------------------

class EdgeDetector:
    """Detect rising and falling edges on a digital input.

    Wraps a DigitalInput and compares the current state to the previous
    state every time ``update()`` is called.  Call ``update()`` inside
    your main loop.

    Example - Detect rising/falling edges and report events
    -------
import pykit_explorer
from digital_io import EdgeDetector
btn = EdgeDetector(board.D3)
while True:
    btn.update()
    if btn.fell:   # button just pressed (active-low)
        print("Pressed!")
    if btn.rose:   # button just released
        print("Released!")
    time.sleep(0.1)  # debounce delay
    
    """

    def __init__(self, pin, pull=digitalio.Pull.UP):
        self._input = DigitalInput(pin, pull)
        self._last = self._input.value
        self.rose = False   # True for one update cycle on LOW→HIGH transition
        self.fell = False   # True for one update cycle on HIGH→LOW transition

    def update(self):
        """Read the pin and update rose/fell flags.  Call this every loop iteration."""
        current = self._input.value
        self.rose = (not self._last) and current
        self.fell = self._last and (not current)
        self._last = current

    @property
    def value(self):
        return self._input.value

    def deinit(self):
        self._input.deinit()
