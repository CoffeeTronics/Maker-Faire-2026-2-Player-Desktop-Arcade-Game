"""
neopixels.py — NeoPixel RGB LED Strip
========================================
Board: Ruler Baseboard

Controls the 5 NeoPixel RGB LEDs on the baseboard via board.NEOPIX.
"""

import board
import neopixel
import time

try:
    from rainbowio import colorwheel
except ImportError:
    def colorwheel(pos: int) -> tuple:
        pos = pos & 0xFF
        if pos < 85:
            return (255 - pos * 3, pos * 3, 0)
        if pos < 170:
            pos -= 85
            return (0, 255 - pos * 3, pos * 3)
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)

OFF = 0x000000

class Colors:
    WHITE      = 0xFFFFFF
    RED        = 0xFF0000
    GREEN      = 0x00FF00
    BLUE       = 0x0000FF
    ORANGE     = 0xFF8000
    YELLOW     = 0xFFFF00
    CYAN       = 0x00FFFF
    PURPLE     = 0xB400FF


class NeoPixels:
    """Drive the NeoPixel LEDs."""

    def __init__(self, pin=board.NEOPIXEL, num_pixels: int = 5,
                 brightness: float = 0.1):
        self._pixels = neopixel.NeoPixel(pin, num_pixels,
                                          brightness=brightness,
                                          auto_write=False)
        self._n = num_pixels

    # -- Item access (for compatibility with direct neopixel usage) ----------

    def __getitem__(self, index):
        return self._pixels[index]

    def __setitem__(self, index, color):
        self._pixels[index] = color

    def __len__(self):
        return self._n

    def show(self):
        """Push pixel data to the strip."""
        self._pixels.show()

    # -- Basic controls ------------------------------------------------------

    def fill(self, color):
        """Set all pixels to *color* and update the strip."""
        self._pixels.fill(color)
        self._pixels.show()

    def off(self):
        """Turn all pixels off."""
        self.fill(OFF)

    def set(self, index: int, color, show: bool = True):
        """Set a single pixel."""
        self._pixels[index] = color
        if show:
            self._pixels.show()

    def set_all(self, colors: list):
        """Set each pixel from a list of colors, then update."""
        for i, c in enumerate(colors[:self._n]):
            self._pixels[i] = c
        self._pixels.show()

    @property
    def brightness(self) -> float:
        return self._pixels.brightness

    @brightness.setter
    def brightness(self, value: float):
        self._pixels.brightness = max(0.0, min(1.0, value))
        self._pixels.show()

    # -- Animations ----------------------------------------------------------

    def color_chase(self, color, wait: float = 0.1):
        for i in range(self._n):
            self._pixels[i] = color
            time.sleep(wait)
            self._pixels.show()
        time.sleep(0.5)

    def rainbow_cycle(self, wait: float = 0.0, cycles: int = 1):
        for _ in range(cycles):
            for j in range(255):
                for i in range(self._n):
                    rc_index = (i * 256 // self._n) + j
                    self._pixels[i] = colorwheel(rc_index & 255)
                self._pixels.show()
                time.sleep(wait)

    def pulse(self, color, steps: int = 20, delay: float = 0.05):
        old_brightness = self._pixels.brightness
        self._pixels.fill(color)
        for i in range(steps + 1):
            self._pixels.brightness = (i / steps) * old_brightness
            self._pixels.show()
            time.sleep(delay)
        for i in range(steps, -1, -1):
            self._pixels.brightness = (i / steps) * old_brightness
            self._pixels.show()
            time.sleep(delay)
        self._pixels.brightness = old_brightness

    def map_value(self, value: float, min_val: float = 0.0,
                  max_val: float = 100.0):
        fraction = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
        lit = round(fraction * self._n)
        hue = int((1.0 - fraction) * 85)
        color = colorwheel(hue)
        for i in range(self._n):
            self._pixels[i] = color if i < lit else OFF
        self._pixels.show()

    def deinit(self):
        self.off()
