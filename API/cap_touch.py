"""
cap_touch.py — Capacitive Touch Input
======================================
Board: Dev Board

Wraps the touchio library to detect touch and release events on a
capacitive touch pad.

Hardware
--------
  Default pin: board.A5  (labelled CAP1 / A5 on the dev board)

Use this module for:
  - Touchpad buttons (no mechanical switch needed)
  - Proximity detection
  - Interactive installations and games
"""

import board
import touchio


class CapTouch:
    """Detect touch and release events on a capacitive pad.

    Parameters
    ----------
    pin : capacitive-touch capable pin (default board.A5 / CAP1)

    Example - Detect touch/release events and print transitions
    -------
import pykit_explorer
from cap_touch import CapTouch
pad = CapTouch(board.A5)
while True:
    pad.update()
    if pad.just_touched:
        print("Touched!")
    if pad.just_released:
        print("Released!")
    time.sleep(0.05)  # debounce delay

    """

    def __init__(self, pin=board.A5):
        self._touch = touchio.TouchIn(pin)
        self._last_state = False
        self.just_touched = False    # True for one update cycle on touch start
        self.just_released = False   # True for one update cycle on touch end

    @property
    def is_touched(self) -> bool:
        """True while the pad is currently being touched."""
        return self._touch.value

    @property
    def raw_value(self) -> int:
        """Raw capacitance reading — useful for threshold tuning."""
        return self._touch.raw_value

    @property
    def threshold(self) -> int:
        """Touch detection threshold.  Increase to reduce sensitivity."""
        return self._touch.threshold

    @threshold.setter
    def threshold(self, value: int):
        self._touch.threshold = value

    def update(self):
        """Sample the pad and update just_touched / just_released flags.

        Must be called every iteration of your main loop.
        """
        current = self._touch.value
        self.just_touched = current and not self._last_state
        self.just_released = not current and self._last_state
        self._last_state = current

    def deinit(self):
        self._touch.deinit()
