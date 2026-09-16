"""
hid_input.py — USB HID Keyboard & Mouse Emulation
===================================================
Board: Dev Board (USB-capable; requires USB_HID in boot.py)

Turns the dev board into a USB HID device that can type keystrokes, press key
combos, and control the mouse cursor — all without any driver on the host PC.

Requirements
------------
  - adafruit_hid library bundle
  - boot.py must include:
        import usb_hid
        usb_hid.enable()

Use this module for:
  - USB automation / macro keyboards
  - Assistive technology devices
  - Game controllers
  - Interactive demos that type or move the mouse
"""

import time
import board
import digitalio
import usb_hid

from adafruit_hid.keyboard        import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode          import Keycode
from adafruit_hid.mouse            import Mouse


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------

class HIDKeyboard:
    """Type strings and press key combinations over USB HID.

    Example - Type strings and press combos over USB HID
    -------
import pykit_explorer
from hid_input import HIDKeyboard
from adafruit_hid.keycode import Keycode
from digital_io import DigitalInput
from cap_touch import CapTouch
kbd = HIDKeyboard()
btn = DigitalInput(board.D3)
touch = CapTouch(board.A5)
while True:
    touch.update()
    if btn.is_pressed():
        kbd.type("Hello, world!\\n")
    elif touch.just_touched:
        kbd.press_combo(Keycode.CONTROL, Keycode.ALT, Keycode.DELETE)

    """

    def __init__(self):
        time.sleep(1)   # brief delay to allow USB enumeration
        self._kbd = Keyboard(usb_hid.devices)
        self._layout = KeyboardLayoutUS(self._kbd)

    def type(self, text: str):
        """Type a string (supports printable ASCII + \\n \\t)."""
        self._layout.write(text)

    def press_combo(self, *keycodes):
        """Press and immediately release a key combination.

        Parameters
        ----------
        *keycodes : one or more Keycode constants

        Example - Use press_combo to send key combinations (e.g., Shift+A)
        -------
kbd.press_combo(Keycode.SHIFT, Keycode.A)   # types 'A'
kbd.press_combo(Keycode.ALT, Keycode.F4)    # Alt-F4
        """
        self._kbd.press(*keycodes)
        self._kbd.release_all()

    def press(self, *keycodes):
        """Hold keys down (must call release_all when done)."""
        self._kbd.press(*keycodes)

    def release_all(self):
        """Release all currently held keys."""
        self._kbd.release_all()


# ---------------------------------------------------------------------------
# Mouse
# ---------------------------------------------------------------------------

class HIDMouse:
    """Move the mouse cursor and click buttons over USB HID.

    The move() values are relative — positive X moves right, positive Y
    moves down (matching standard screen coordinates).

    Example - Move and click the mouse based on inputs
    -------
import pykit_explorer 
from hid_input import HIDMouse
from digital_io import DigitalInput
from cap_touch import CapTouch
btn = DigitalInput(board.D3)
mouse = HIDMouse()
touch = CapTouch(board.A5)
while True:
    touch.update()
    if btn.is_pressed():
        mouse.move(x=10, y=-5)        # right 10, up 5
    elif touch.just_touched:    
        mouse.click_left()

    """

    def __init__(self):
        time.sleep(1)
        self._mouse = Mouse(usb_hid.devices)

    def move(self, x: int = 0, y: int = 0, wheel: int = 0):
        """Move the cursor and/or scroll wheel by relative amounts.

        Parameters
        ----------
        x     : pixels to move horizontally (negative = left)
        y     : pixels to move vertically (negative = up)
        wheel : scroll wheel clicks (negative = scroll down)
        """
        self._mouse.move(x=x, y=y, wheel=wheel)

    def click_left(self):
        """Click the left mouse button."""
        self._mouse.click(Mouse.LEFT_BUTTON)

    def click_right(self):
        """Click the right mouse button."""
        self._mouse.click(Mouse.RIGHT_BUTTON)

    def click_middle(self):
        """Click the middle mouse button."""
        self._mouse.click(Mouse.MIDDLE_BUTTON)

    def press(self, button=Mouse.LEFT_BUTTON):
        """Hold a mouse button down."""
        self._mouse.press(button)

    def release(self, button=Mouse.LEFT_BUTTON):
        """Release a held mouse button."""
        self._mouse.release(button)


# ---------------------------------------------------------------------------
# Analog joystick → mouse helper
# ---------------------------------------------------------------------------

class JoystickMouse:
    """Map two analog axes (potentiometers / joystick) to mouse movement.

    Parameters
    ----------
    x_pin   : analog pin for horizontal axis (default board.A0)
    y_pin   : analog pin for vertical axis   (default board.A1)
    btn_pin : digital pin for left click     (default board.A2, pull-up)
    deadzone: fraction of full range to treat as centre (default 0.1)

    Example - Map two analog axes to mouse movement and click
    -------
import pykit_explorer
from hid_input import JoystickMouse
joy = JoystickMouse()
while True:
    joy.update()
    time.sleep(0.01)
    
    """

    _VREF = 3.3
    _STEPS = 20

    def __init__(self, x_pin=board.A0, y_pin=board.A1,
                 btn_pin=board.A2, deadzone: float = 0.1):
        import analogio
        self._x   = analogio.AnalogIn(x_pin)
        self._y   = analogio.AnalogIn(y_pin)
        self._btn = digitalio.DigitalInOut(btn_pin)
        self._btn.direction = digitalio.Direction.INPUT
        self._btn.pull = digitalio.Pull.UP
        self._mouse = Mouse(usb_hid.devices)
        self._deadzone = deadzone
        self._step = self._VREF / self._STEPS

    def _voltage(self, pin) -> float:
        return (pin.value * self._VREF) / 65536

    def _axis_to_delta(self, voltage: float) -> int:
        steps = round(voltage / self._step)
        centre = self._STEPS // 2
        delta = steps - centre
        if abs(delta) <= int(self._deadzone * self._STEPS):
            return 0
        speed = 8 if abs(delta) >= (self._STEPS - 2) else 1
        return speed if delta > 0 else -speed

    def update(self):
        """Sample axes and button and send relative mouse movement.

        Call this every loop iteration.
        """
        dx = self._axis_to_delta(self._voltage(self._x))
        dy = self._axis_to_delta(self._voltage(self._y))

        if dx or dy:
            self._mouse.move(x=dx, y=dy)

        if not self._btn.value:
            self._mouse.click(Mouse.LEFT_BUTTON)
            time.sleep(0.2)   # debounce
