"""
lcd_display.py — ST7789 TFT LCD Display
=========================================
Board: Ruler Baseboard

Initialises the 240×135 pixel ST7789 TFT LCD and exposes helpers for:
  - Drawing filled rectangles and backgrounds
  - Displaying BMP sprite sheets / images
  - Animating positioned displayio Groups (for sprites or text)
  - Backlight control

Hardware pins (defined in the Ruler board variant)
--------------------------------------------------
  board.LCD_SPI()  — SPI bus factory function
  board.LCD_CS     — chip select
  board.D4         — data/command (DC) pin
  board.LCD_BL — backlight LED anode (PA06)

Requires
--------
  adafruit_st7789     (display driver)
  adafruit_imageload  (BMP sprite loading)
  fourwire / displayio

Use this module for:
  - Showing sensor data graphically
  - Sprite-based games
  - Status dashboards
  - IMU-driven animations
"""

import board
import displayio
import digitalio
import terminalio
import adafruit_imageload
import time
from adafruit_display_text import label as _label

try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

from adafruit_st7789 import ST7789

# Display dimensions
WIDTH  = 240
HEIGHT = 135

class Colors:
    BLACK      = 0x000000
    WHITE      = 0xFFFFFF
    RED        = 0xFF0000
    GREEN      = 0x00FF00
    PURPLE     = 0xB400FF
    BLUE       = 0x0000FF
    ORANGE     = 0xFF8000
    YELLOW     = 0xFFFF00
    GRAY       = 0x888888
    DARK_BLUE  = 0x000080
    DARK_GREEN = 0x003000
    CYAN       = 0x00FFFF

class LCDDisplay:
    """Drive the 240×135 ST7789 TFT LCD on the Ruler baseboard.

    Example - create a full-screen group with a blue background and a centered sprite
    -------
import pykit_explorer
from lcd_display import LCDDisplay
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 135
lcd = LCDDisplay()
lcd.backlight_on()
bg_group = lcd.fill_screen(0x001F)            # solid blue background
sprite_group = lcd.load_sprite("/Images/Meatball_32x30_16color.bmp", 32, 30)
sprite_group.x = (DISPLAY_WIDTH - 32) // 2  # center horizontally
sprite_group.y = (DISPLAY_HEIGHT - 30) // 2  # center vertically
bg_group.append(sprite_group)
lcd.display.refresh()
while True:
    pass
    
    """

    def __init__(self):
        # Backlight controlled via board.LCD_BL (PA06)
        self._backlight = digitalio.DigitalInOut(board.LCD_BL)
        self._backlight.direction = digitalio.Direction.OUTPUT
        self._backlight.value = False

        # Release any previously claimed display resources
        displayio.release_displays()

        spi    = board.LCD_SPI()
        tft_cs = board.LCD_CS
        tft_dc = board.D4

        display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
        self._display = ST7789(
            display_bus,
            rotation=90,
            width=WIDTH,
            height=HEIGHT,
            rowstart=40,
            colstart=53,
        )

    # -- Backlight -----------------------------------------------------------

    def backlight_on(self):
        """Turn the LCD backlight on."""
        self._backlight.value = False

    def backlight_off(self):
        """Turn the LCD backlight off."""
        self._backlight.value = True

    @property
    def display(self):
        """The raw ST7789 display object — use for direct displayio access."""
        return self._display

    # -- Single-group display setup ------------------------------------------

    def make_group(self, bg_color: int = Colors.BLACK):
        """Create a full-screen displayio Group with a solid background.

        Sets it as the display root_group immediately.  Returns a tuple of
        (group, palette) so the caller can swap the background colour later
        by writing palette[0] = new_color.

        Parameters
        ----------
        bg_color : 24-bit RGB colour for the background, e.g. 0x000080

        Returns
        -------
        (displayio.Group, displayio.Palette)

        Example - Create a group with a black background, add a label, then swap to dark blue
        -------
import pykit_explorer
from lcd_display import LCDDisplay
lcd = LCDDisplay()
lcd.backlight_on()
# Create a full-screen group with black background
group, palette = lcd.make_group(0x000000)
# Add a label to the group
label = lcd.add_label(group, "Hello!", 120, 60, color=0xFFFFFF, scale=3)
# Swap the background color to dark blue
time.sleep(2)
palette[0] = 0x000080
# Update label text
label.text = "Dark Blue!"
while True:
    pass
    
        """

        bitmap  = displayio.Bitmap(WIDTH, HEIGHT, 1)
        palette = displayio.Palette(1)
        palette[0] = bg_color
        group = displayio.Group()
        group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
        self._display.root_group = group
        return group, palette

    def add_label(self, group: displayio.Group, text: str,
                  x: int, y: int,
                  color: int = 0xFFFFFF,
                  scale: int = 2) -> "_label.Label":
        """Create a horizontally-centred label and append it to *group*.

        Uses terminalio.FONT with anchor_point=(0.5, 0.0) so x=120 centres
        text on the 240 px display.  Returns the Label so the caller can
        update .text or .hidden later.

        Parameters
        ----------
        group : displayio.Group to append to
        text  : initial string
        x, y  : pixel position (x=120 centres on a 240 px display)
        color : 24-bit RGB text colour
        scale : integer font scale (1 = 6×8 px per char)

        Returns
        -------
        adafruit_display_text.label.Label

        Example - Create a label and update its text after a delay
        -------
import pykit_explorer
from lcd_display import LCDDisplay
lcd = LCDDisplay()
lcd.backlight_on()
# Create a group with default black background
group, palette = lcd.make_group()
# Add a temperature label
temp_lbl = lcd.add_label(group, "--.- C", 120, 42,
                         color=0x00FF00, scale=3)
# Create a list of temps to update in main loop
temps = [20.5, 21.3, 22.1, 23.8, 24.5]
index = 0
while True:
    temp_lbl.text = f"{temps[index]:.1f} C"
    index = (index + 1) % len(temps)
    time.sleep(1)

        """

        lbl = _label.Label(
            terminalio.FONT,
            text=text,
            color=color,
            scale=scale,
            anchor_point=(0.5, 0.0),
            anchored_position=(x, y),
        )
        group.append(lbl)
        return lbl

    # -- Text scrolling ------------------------------------------------------

    def scroll_label(self, label, text: str, y: int,
                     scale: int = 2, step: int = 4, delay: float = 0.0,
                     poll=None):
        """Scroll text across the full display width, right to left.

        Wraps the label in a temporary sub-group and moves group.x each frame,
        which is cheaper than updating anchored_position and gives smoother
        animation at small step sizes.

        Parameters
        ----------
        label : a Label returned by add_label()
        text  : the full string to scroll
        y     : vertical pixel position (same y used when the label was created)
        scale : font scale — must match the label's scale (default 2)
        step  : pixels to advance per frame (smaller = smoother, default 2)
        delay : seconds to sleep between frames (default 0.0)
        poll  : optional callable invoked each frame (e.g. ble.receive) to
                prevent UART buffer overflow during the blocking scroll
        """
        char_w = 6 * scale
        text_w = len(text) * char_w

        # Position label at x=0 within the sub-group; group.x does the scrolling
        label.text              = text
        label.anchor_point      = (0.0, 0.0)
        label.anchored_position = (0, y)

        # Remove label from its current parent (root group) before reparenting
        root = self._display.root_group
        label_index = None
        for i in range(len(root)):
            if root[i] is label:
                label_index = i
                break
        if label_index is not None:
            root.remove(label)

        # Wrap in a sub-group so group.x does the scrolling (cheaper than anchored_position)
        sub_group = displayio.Group(x=WIDTH, y=0)
        sub_group.append(label)
        root.append(sub_group)

        self._display.auto_refresh = False
        try:
            x = WIDTH
            while x > -text_w:
                x -= step
                sub_group.x = x
                if poll is not None:
                    poll()
                self._display.refresh()
                if delay:
                    time.sleep(delay)
        finally:
            self._display.auto_refresh = True
            # Restore label to root group
            root.remove(sub_group)
            sub_group.remove(label)
            label.anchor_point      = (0.5, 0.0)
            label.anchored_position = (WIDTH // 2, y)
            label.text = ""
            root.append(label)

    # -- Scrolling label -----------------------------------------------------

    def make_scroll_label(self, group: displayio.Group,
                          x: int, y: int,
                          color: int = Colors.YELLOW,
                          scale: int = 2,
                          scroll_width: int = 20,
                          scroll_interval: float = 0.05,
                          min_duration: float = 5.0) -> "ScrollLabel":
        """Create a ScrollLabel and append it to *group*.

        Parameters
        ----------
        group           : displayio.Group to append to
        x, y            : pixel position (x=120 centres on a 240 px display)
        color           : 24-bit RGB text colour
        scale           : integer font scale
        scroll_width    : visible character window width (default 20)
        scroll_interval : seconds between scroll steps (default 0.05)
        min_duration    : minimum seconds to display any message (default 5.0)

        Returns
        -------
        ScrollLabel

        Example - Create a scrolling label and cycle through messages
        -------
import pykit_explorer
from lcd_display import LCDDisplay
lcd = LCDDisplay()
lcd.backlight_on()
# Create a group with default black background
group, palette = lcd.make_group()
# Create a scrolling label
ble_lbl = lcd.make_scroll_label(group, 120, 55)
# Set initial message
ble_lbl.set("Hello world!")
messages = [
    "Welcome to the display!",
    "This text scrolls across the screen",
    "Each message shows for a few seconds"
]
msg_index = 0
while True:
    now = time.monotonic()
    if not ble_lbl.update(now):
        # Message expired, show the next one
        ble_lbl.set(messages[msg_index % len(messages)])
        msg_index += 1
    time.sleep(0.05)

        """

        return ScrollLabel(group, x, y, color=color, scale=scale,
                           scroll_width=scroll_width,
                           scroll_interval=scroll_interval,
                           min_duration=min_duration)

    # -- Background ----------------------------------------------------------

    def fill_screen(self, color_565: int = 0x0000):
        """Fill the entire screen with a 16-bit RGB565 colour.

        Parameters
        ----------
        color_565 : 16-bit colour, e.g. 0xF800 = red, 0x001F = blue

        Returns the root Group that was applied — you can append more elements.
        """
        bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
        palette = displayio.Palette(1)
        palette[0] = color_565
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
        group = displayio.Group()
        group.append(tile_grid)
        self._display.root_group = group
        return group

    # -- Sprite loading ------------------------------------------------------

    def load_sprite(self, bmp_path: str, sprite_w: int = WIDTH, sprite_h: int = HEIGHT,
                    x: int = 0, y: int = 0) -> displayio.Group:
        """Load a BMP sprite sheet and return a positioned displayio.Group.

        The returned group contains a single TileGrid showing the first tile.
        Assign it to display.root_group or append it to an existing group.

        Parameters
        ----------
        bmp_path  : path to BMP file on the CIRCUITPY filesystem
        sprite_w  : tile width in pixels
        sprite_h  : tile height in pixels
        x, y      : initial pixel position

        Returns
        -------
        displayio.Group  (group.x / group.y can be modified to move the sprite)
        """
        sheet, palette = adafruit_imageload.load(
            bmp_path,
            bitmap=displayio.Bitmap,
            palette=displayio.Palette,
        )
        tile_grid = displayio.TileGrid(
            sheet,
            pixel_shader=palette,
            width=1,
            height=1,
            tile_width=sprite_w,
            tile_height=sprite_h,
        )
        group = displayio.Group(scale=1)
        group.append(tile_grid)
        group.x = x
        group.y = y
        return group

    # -- Sprite animation helpers --------------------------------------------

    def bounce_sprite(self, group: displayio.Group,
                      sprite_w: int, sprite_h: int,
                      dx: int = 2, dy: int = 3,
                      delay: float = 0.05):
        """Move a sprite group with wall-bouncing physics — single frame.

        Maintains velocity state internally on the group object.  Call this
        every loop iteration to animate the sprite.

        Parameters
        ----------
        group            : the displayio.Group to move
        sprite_w, sprite_h : sprite dimensions (for boundary checking)
        dx, dy           : initial pixel velocity (stored on group after first call)
        delay            : optional sleep per call (set 0 for time-managed loops)

    Example - Bounce a sprite around the screen
    -------
import pykit_explorer
from lcd_display import LCDDisplay
lcd = LCDDisplay()
lcd.backlight_on()
group = lcd.load_sprite("/Images/Meatball_32x30_16color.bmp", 32, 30, x=100, y=50)
lcd.display.root_group = group
vx, vy = 2, 3
sprite_w, sprite_h = 32, 30
while True:
    group.x += vx
    group.y += vy
    if group.x >= 240 - sprite_w:
        group.x = 240 - sprite_w
        vx = -abs(vx)
    if group.x <= 0:
        group.x = 0
        vx = abs(vx)
    if group.y >= 135 - sprite_h:
        group.y = 135 - sprite_h
        vy = -abs(vy)
    if group.y <= 0:
        group.y = 0
        vy = abs(vy)
    time.sleep(0.05)

        """

        if not hasattr(group, "_vx"):
            group._vx = dx
            group._vy = dy

        group.x += group._vx
        group.y += group._vy

        if group.x >= WIDTH - sprite_w:
            group.x = WIDTH - sprite_w
            group._vx = -abs(group._vx)
        if group.x <= 0:
            group.x = 0
            group._vx = abs(group._vx)
        if group.y >= HEIGHT - sprite_h:
            group.y = HEIGHT - sprite_h
            group._vy = -abs(group._vy)
        if group.y <= 0:
            group.y = 0
            group._vy = abs(group._vy)

        if delay:
            time.sleep(delay)

    def move_sprite_clamped(self, group: displayio.Group,
                             dx: int, dy: int,
                             sprite_w: int, sprite_h: int):
        """Move sprite by (dx, dy), clamping to display boundaries.

        Useful for IMU-driven movement where acceleration is mapped to delta.

        Parameters
        ----------
        group           : displayio.Group to move
        dx, dy          : pixel delta (can be positive or negative)
        sprite_w/h      : sprite dimensions for boundary clamping
        """
        group.x = max(0, min(WIDTH  - sprite_w, group.x + dx))
        group.y = max(0, min(HEIGHT - sprite_h, group.y + dy))


class ScrollLabel:
    """A label that automatically scrolls long messages character by character.

    Created via LCDDisplay.make_scroll_label().

    The display duration is calculated from the message length so that the
    full message always scrolls into view before expiring. Short messages
    (at or under scroll_width) are shown statically for min_duration seconds.

    Parameters
    ----------
    group           : displayio.Group to append the label to
    x, y            : pixel position
    color           : 24-bit RGB text colour
    scale           : integer font scale
    scroll_width    : visible character window (default 20)
    scroll_interval : seconds per scroll step (default 0.05)
    min_duration    : minimum display time in seconds (default 5.0)

    Example - Create a scrolling label and cycle through messages
    -------
import pykit_explorer
import time
from lcd_display import LCDDisplay
lcd = LCDDisplay()
lcd.backlight_on()
group, palette = lcd.make_group()
temp_lbl = lcd.add_label(group, "25.0° C", 120, 42, color=0x00FF00, scale=3)
ble_lbl = lcd.make_scroll_label(group, 120, 80, min_duration=3.0)
messages = [
    "A short message",
    "A much longer message that needs to scroll across the screen",
    "Welcome to the display!",
    "Cycling through messages"
]
msg_index = 0
temp_show_time = time.monotonic()
show_temp = True

while True:
    now = time.monotonic()
    
    if show_temp:
        # Display only temperature label for 3 seconds
        temp_lbl.hidden = False
        ble_lbl._lbl.hidden = True
        if now - temp_show_time >= 3:
            # Switch to message mode
            show_temp = False
            ble_lbl.set(messages[msg_index])
            msg_index = (msg_index + 1) % len(messages)
    else:
        # Display scrolling message
        temp_lbl.hidden = True
        if not ble_lbl.update(now):
            # Message finished, switch back to temp
            show_temp = True
            temp_show_time = now
    
    time.sleep(0.05)

    """

    def __init__(self, group, x, y, color=Colors.YELLOW, scale=2,
                 scroll_width=20, scroll_interval=0.05, min_duration=5.0):
        self._lbl = _label.Label(
            terminalio.FONT,
            text="",
            color=color,
            scale=scale,
            anchor_point=(0.5, 0.0),
            anchored_position=(x, y),
        )
        self._lbl.hidden = True
        group.append(self._lbl)

        self._scroll_width    = scroll_width
        self._scroll_interval = scroll_interval
        self._min_duration    = min_duration

        self._msg        = ""
        self._pos        = 0
        self._until      = 0.0
        self._next_step  = 0.0

    def set(self, text: str):
        """Display *text*, scrolling if longer than scroll_width.

        Calculates the display duration so the full message always completes
        one scroll pass before expiring.

        Parameters
        ----------
        text : message to display
        """
        self._msg       = text
        self._pos       = 0
        self._next_step = 0.0
        self._lbl.hidden = False

        now = time.monotonic()
        if len(text) > self._scroll_width:
            steps = len(text) - self._scroll_width + 1
            self._until = now + max(self._min_duration,
                                    steps * self._scroll_interval)
        else:
            self._until = now + self._min_duration

    def update(self, now: float) -> bool:
        """Advance the scroll and update the label. Call once per main loop.

        Parameters
        ----------
        now : current time.monotonic() value

        Returns
        -------
        True while a message is being displayed, False when it has expired.
        """
        if not self._msg or now >= self._until:
            self._msg        = ""
            self._lbl.hidden = True
            return False

        if len(self._msg) <= self._scroll_width:
            self._lbl.text = self._msg
        elif now >= self._next_step:
            self._lbl.text = self._msg[self._pos:self._pos + self._scroll_width]
            self._pos      = min(self._pos + 1,
                                 len(self._msg) - self._scroll_width)
            self._next_step = now + self._scroll_interval

        return True

    def clear(self):
        """Immediately hide the label and discard the current message."""
        self._msg        = ""
        self._lbl.hidden = True
        self._until      = 0.0

    @property
    def active(self) -> bool:
        """True if a message is currently being displayed."""
        return bool(self._msg)

