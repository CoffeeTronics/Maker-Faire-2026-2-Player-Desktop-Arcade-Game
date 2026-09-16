"""
buttons.py - 4-Button Arcade Button Set
=======================================
Board: Curiosity PyKit with RGB Matrix

Provides a simple abstraction for reading 4 arcade-style buttons
with edge detection (press/release events).

Hardware Configuration:
  - Button A: board.D4 (active HIGH, Pull.DOWN)
  - Button B: board.D5 (active HIGH, Pull.DOWN)
  - Button C: board.D6 (active HIGH, Pull.DOWN)
  - Button D: board.D7 (active HIGH, Pull.DOWN) - typically game switch
"""

import board
import digitalio
from digital_io import DigitalInput, EdgeDetector


class ButtonSet:
    """4-button arcade button set with edge detection.

    Provides both current state and edge detection for each button.
    Call update() once per frame to refresh edge detection state.

    Example
    -------
    from buttons import ButtonSet

    buttons = ButtonSet()
    while True:
        buttons.update()
        if buttons.a_pressed:
            print("A is held")
        if buttons.b_fell:
            print("B just pressed")
        if buttons.d_fell:
            print("Switch game!")
        time.sleep(0.016)
    """

    def __init__(self, a_pin=None, b_pin=None, c_pin=None, d_pin=None):
        """Initialize button set with GPIO pins.

        Parameters
        ----------
        a_pin : board pin, optional
            Pin for button A (default: board.D4)
        b_pin : board pin, optional
            Pin for button B (default: board.D5)
        c_pin : board pin, optional
            Pin for button C (default: board.D6)
        d_pin : board pin, optional
            Pin for button D (default: board.D7)
        """
        self.a = EdgeDetector(
            a_pin if a_pin else board.D4,
            pull=digitalio.Pull.DOWN
        )
        self.b = EdgeDetector(
            b_pin if b_pin else board.D5,
            pull=digitalio.Pull.DOWN
        )
        self.c = EdgeDetector(
            c_pin if c_pin else board.D6,
            pull=digitalio.Pull.DOWN
        )
        self.d = EdgeDetector(
            d_pin if d_pin else board.D7,
            pull=digitalio.Pull.DOWN
        )

    def update(self):
        """Update edge detection state for all buttons.

        Call this once per frame before checking button states.
        """
        self.a.update()
        self.b.update()
        self.c.update()
        self.d.update()

    # Current state properties (True while held)
    @property
    def a_pressed(self):
        """True while button A is held down."""
        return self.a.value

    @property
    def b_pressed(self):
        """True while button B is held down."""
        return self.b.value

    @property
    def c_pressed(self):
        """True while button C is held down."""
        return self.c.value

    @property
    def d_pressed(self):
        """True while button D is held down."""
        return self.d.value

    # Edge detection properties (True for one frame on press)
    @property
    def a_fell(self):
        """True for one frame when button A is first pressed."""
        return self.a.fell

    @property
    def b_fell(self):
        """True for one frame when button B is first pressed."""
        return self.b.fell

    @property
    def c_fell(self):
        """True for one frame when button C is first pressed."""
        return self.c.fell

    @property
    def d_fell(self):
        """True for one frame when button D is first pressed."""
        return self.d.fell

    # Edge detection properties (True for one frame on release)
    @property
    def a_rose(self):
        """True for one frame when button A is released."""
        return self.a.rose

    @property
    def b_rose(self):
        """True for one frame when button B is released."""
        return self.b.rose

    @property
    def c_rose(self):
        """True for one frame when button C is released."""
        return self.c.rose

    @property
    def d_rose(self):
        """True for one frame when button D is released."""
        return self.d.rose

    def deinit(self):
        """Release GPIO resources."""
        self.a.deinit()
        self.b.deinit()
        self.c.deinit()
        self.d.deinit()
