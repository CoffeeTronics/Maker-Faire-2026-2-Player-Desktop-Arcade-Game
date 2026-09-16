"""
apds9960.py — APDS9960 Proximity, Gesture & Color Sensor
==========================================================
Breakout: Adafruit APDS9960 (I2C, QWIIC connector)

The APDS9960 has three independent sensing functions that are enabled and
disabled individually:

  1. Proximity  — measures distance (0–255) to nearby objects
  2. Gesture    — detects hand swipes (UP, DOWN, LEFT, RIGHT)
  3. Color      — measures RGBC (red, green, blue, clear) light intensity

Only one mode should be active at a time.  Call the appropriate enable_*()
method before reading from that mode.

Hardware
--------
  Connect the APDS9960 breakout to the QWIIC connector on the Ruler baseboard.
  Uses the shared I2C bus (board.SCL / board.SDA).

Requires
--------
  adafruit_apds9960 library

Usage
-----
  Pass the .bus property from an i2c_bus.I2CBus instance:

import pykit_explorer
from i2c_bus import I2CBus
from apds9960 import APDS9960Sensor
my_i2c = I2CBus()
sensor = APDS9960Sensor(my_i2c.bus)
sensor.enable_proximity()
print(sensor.proximity)

Use this module for:
  - Touchless gesture controls (swipe to change state)
  - Proximity-triggered events or audio theremin effects
  - Color matching and color-driven NeoPixel reproduction
  - Presence detection
"""

import time
from adafruit_apds9960.apds9960 import APDS9960

class Gestures:
    # Gesture constants — match the values returned by apds.gesture()
    GESTURE_NONE  = 0x0
    GESTURE_UP    = 0x1
    GESTURE_DOWN  = 0x2
    GESTURE_LEFT  = 0x3
    GESTURE_RIGHT = 0x4

class Gesture_Names:
    # Human-readable gesture labels
    GESTURE_NAMES = {
        Gestures.GESTURE_NONE:  "NONE",
        Gestures.GESTURE_UP:    "UP",
        Gestures.GESTURE_DOWN:  "DOWN",
        Gestures.GESTURE_LEFT:  "LEFT",
        Gestures.GESTURE_RIGHT: "RIGHT",
    }

class APDS9960Sensor:
    """Interface to the APDS9960 proximity, gesture, and color sensor.

    Parameters
    ----------
    i2c : raw busio.I2C object — pass i2c_bus_instance.bus

Example - proximity - Print proximity readings continuously
-------------------
import pykit_explorer
from i2c_bus import I2CBus
from apds9960 import APDS9960Sensor
my_i2c = I2CBus()
sensor = APDS9960Sensor(my_i2c.bus)
sensor.enable_proximity()
while True:
    print(sensor.proximity)
    time.sleep(0.1)

    
Example - gesture - Detect and print swipe gestures
-----------------
import pykit_explorer
from i2c_bus import I2CBus
from apds9960 import APDS9960Sensor
my_i2c = I2CBus()
sensor = APDS9960Sensor(my_i2c.bus)
sensor.enable_gesture()
while True:
    g = sensor.gesture()
    if g:
        print(sensor.gesture_name(g))

Example - color - Read RGBC values and mirror color to NeoPixels
---------------
import pykit_explorer
from neopixels import NeoPixels
from i2c_bus import I2CBus
from apds9960 import APDS9960Sensor
my_i2c = I2CBus()
sensor = APDS9960Sensor(my_i2c.bus)
sensor.enable_color()
px = NeoPixels()
while True:
    r, g, b, c = sensor.color
    print(f"R={r} G={g} B={b} C={c}")
    neopixel_color = sensor.color_as_neopixel()
    px.fill(neopixel_color)
    time.sleep(0.5)
    
    """

    def __init__(self, i2c):
        self._apds = APDS9960(i2c)
        self._mode = None

    # -- Mode selection ------------------------------------------------------

    def enable_proximity(self):
        """Switch to proximity mode.

        Disables gesture and color, enables proximity.
        Read sensor data with the ``proximity`` property.
        """
        self._apds.enable_proximity = True
        self._apds.enable_gesture = False
        self._apds.enable_color = False
        self._mode = "proximity"

    def enable_gesture(self):
        """Switch to gesture detection mode.

        Both proximity AND gesture must be enabled for gesture detection to work.
        Read sensor data with the ``gesture()`` method.
        """
        self._apds.enable_proximity = True
        self._apds.enable_gesture = True
        self._apds.enable_color = False
        self._mode = "gesture"

    def enable_color(self):
        """Switch to color sensing mode.

        Disables proximity and gesture, enables color.
        Read sensor data with the ``color`` property.
        """
        self._apds.enable_proximity = False
        self._apds.enable_gesture = False
        self._apds.enable_color = True
        self._mode = "color"

    @property
    def mode(self) -> str:
        """Current active mode: 'proximity', 'gesture', 'color', or None."""
        return self._mode

    # -- Proximity -----------------------------------------------------------

    @property
    def proximity(self) -> int:
        """Proximity reading as an 8-bit value (0–255).

        0 = nothing detected, 255 = very close.
        Call enable_proximity() first.
        """
        return self._apds.proximity

    def proximity_to_dac(self) -> int:
        """Map the 8-bit proximity value to a 16-bit DAC value (0–65535).

        Useful for driving an analog tone pitch proportional to distance.
        Clamps to prevent overflow.
        """
        return min(self._apds.proximity << 8, 65535)

    # -- Gesture -------------------------------------------------------------

    def gesture(self) -> int:
        """Read one gesture from the sensor.

        Returns one of: GESTURE_NONE, GESTURE_UP, GESTURE_DOWN,
        GESTURE_LEFT, GESTURE_RIGHT.

        Call enable_gesture() first.
        """
        return self._apds.gesture()

    def gesture_name(self, gesture_value: int = None) -> str:
        """Return a human-readable string for a gesture value.

        Parameters
        ----------
        gesture_value : integer gesture constant (default: reads live from sensor)

        Returns
        -------
        One of: 'NONE', 'UP', 'DOWN', 'LEFT', 'RIGHT'
        """
        if gesture_value is None:
            gesture_value = self.gesture()
        return Gesture_Names.GESTURE_NAMES.get(gesture_value, "UNKNOWN")


    def wait_for_gesture(self, timeout: float = 5.0) -> int:
        """Block until a non-zero gesture is detected or *timeout* expires.

        Parameters
        ----------
        timeout : maximum seconds to wait (default 5.0)

        Returns
        -------
        Gesture integer constant, or GESTURE_NONE on timeout.
        """
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            g = self._apds.gesture()
            if g != Gestures.GESTURE_NONE:
                return g
        return Gestures.GESTURE_NONE

    # -- Color ---------------------------------------------------------------

    @property
    def color(self) -> tuple:
        """Raw 16-bit RGBC color data as (red, green, blue, clear).

        Values range 0–65535.
        Call enable_color() first.
        """
        return self._apds.color_data

    def color_as_neopixel(self) -> tuple:
        """Convert the RGBC reading to an 8-bit (R, G, B) NeoPixel tuple.

        Normalises each channel against the clear channel so the result
        spans the full 0–255 range regardless of ambient light level.

        Returns
        -------
        (r, g, b) tuple with values 0–255
        """
        r, g, b, c = self._apds.color_data
        if c == 0:
            return (0, 0, 0)
        return (
            min(255, r * 255 // c),
            min(255, g * 255 // c),
            min(255, b * 255 // c),
        )

    def color_as_hex(self) -> int:
        """Convert the 16-bit RGBC reading to a single 24-bit hex colour integer.

        Returns
        -------
        Integer in the form 0xRRGGBB, usable directly with NeoPixel fill()
        or display text label colour properties.
        """
        r, g, b = self.color_as_neopixel()
        return (r << 16) | (g << 8) | b

    # -- Logging -------------------------------------------------------------

    def print_proximity(self):
        """Print the current proximity reading to the console."""
        print(f"Proximity: {self.proximity}")

    def print_color(self):
        """Print the current RGBC color reading to the console."""
        r, g, b, c = self.color
        print(f"R:{r}  G:{g}  B:{b}  Clear:{c}")
        print(f"NeoPixel 8-bit -> R:{r>>8}  G:{g>>8}  B:{b>>8}")
