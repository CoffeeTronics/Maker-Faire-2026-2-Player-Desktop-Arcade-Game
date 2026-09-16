"""
joystick.py - 4-Direction Digital Joystick
==========================================
Board: Curiosity PyKit with RGB Matrix

Provides a simple abstraction for reading a 4-direction digital joystick
connected to GPIO pins.

Hardware Configuration:
  - Up:    board.LCD_SCK   (active HIGH, Pull.DOWN)
  - Down:  board.LCD_CS    (active HIGH, Pull.DOWN)
  - Left:  board.LCD_BL    (active HIGH, Pull.DOWN)
  - Right: board.LCD_MOSI  (active HIGH, Pull.DOWN)
"""

import board
import digitalio
from digital_io import DigitalInput

# Direction constants (dx, dy)
UP    = (0, -1)
DOWN  = (0, 1)
LEFT  = (-1, 0)
RIGHT = (1, 0)


class Joystick:
    """4-direction digital joystick abstraction.

    Reads 4 GPIO pins to determine joystick direction.
    All pins are configured as active HIGH with internal pull-down.

    Example
    -------
    from joystick import Joystick, UP, DOWN, LEFT, RIGHT

    joy = Joystick()
    while True:
        if joy.up:
            print("Up pressed")
        direction = joy.get_direction()
        if direction == LEFT:
            print("Going left")
        time.sleep(0.05)
    """

    def __init__(self, up_pin=None, down_pin=None, left_pin=None, right_pin=None):
        """Initialize joystick with GPIO pins.

        Parameters
        ----------
        up_pin : board pin, optional
            Pin for up direction (default: board.LCD_SCK)
        down_pin : board pin, optional
            Pin for down direction (default: board.LCD_CS)
        left_pin : board pin, optional
            Pin for left direction (default: board.LCD_BL)
        right_pin : board pin, optional
            Pin for right direction (default: board.LCD_MOSI)
        """
        self._up = DigitalInput(
            up_pin if up_pin else board.LCD_SCK,
            pull=digitalio.Pull.DOWN
        )
        self._down = DigitalInput(
            down_pin if down_pin else board.LCD_CS,
            pull=digitalio.Pull.DOWN
        )
        self._left = DigitalInput(
            left_pin if left_pin else board.LCD_BL,
            pull=digitalio.Pull.DOWN
        )
        self._right = DigitalInput(
            right_pin if right_pin else board.LCD_MOSI,
            pull=digitalio.Pull.DOWN
        )

    @property
    def up(self):
        """True if joystick is pushed up."""
        return self._up.value

    @property
    def down(self):
        """True if joystick is pushed down."""
        return self._down.value

    @property
    def left(self):
        """True if joystick is pushed left."""
        return self._left.value

    @property
    def right(self):
        """True if joystick is pushed right."""
        return self._right.value

    def get_direction(self):
        """Get current joystick direction.

        Returns
        -------
        tuple or None
            Direction constant (UP, DOWN, LEFT, RIGHT) or None if centered.
            Priority order: Up, Down, Left, Right (first detected wins).
        """
        if self._up.value:
            return UP
        if self._down.value:
            return DOWN
        if self._left.value:
            return LEFT
        if self._right.value:
            return RIGHT
        return None

    def get_xy(self):
        """Get joystick position as normalized (-1, 0, +1) coordinates.

        Returns
        -------
        tuple
            (x, y) where x is -1 (left), 0 (center), +1 (right)
            and y is -1 (up), 0 (center), +1 (down)
        """
        x = 0
        y = 0
        if self._left.value:
            x = -1
        elif self._right.value:
            x = 1
        if self._up.value:
            y = -1
        elif self._down.value:
            y = 1
        return (x, y)

    def deinit(self):
        """Release GPIO resources."""
        self._up.deinit()
        self._down.deinit()
        self._left.deinit()
        self._right.deinit()
