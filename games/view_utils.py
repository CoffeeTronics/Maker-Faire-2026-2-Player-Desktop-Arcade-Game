"""
view_utils.py - Shared View Utilities for 128x64 RGB Matrix Games
=================================================================

Provides bitmap font definitions and drawing utilities shared across
all games on the 128x64 RGB Matrix display (4 panels, rotated 90°).

Fonts included:
  - TINY_FONT: 3x5 pixel characters for HUD text
  - BIG_FONT: 5x7 pixel characters for large text like "GAME OVER"

Icons included:
  - HEART_ICON: 5x5 pixel heart for lives display
"""

# 3x5 pixel font for tiny text (HUD, scores)
# Each character is a list of 5 rows, each row is a 3-bit pattern
TINY_FONT = {
    "0": [0b111, 0b101, 0b101, 0b101, 0b111],
    "1": [0b010, 0b110, 0b010, 0b010, 0b111],
    "2": [0b111, 0b001, 0b111, 0b100, 0b111],
    "3": [0b111, 0b001, 0b111, 0b001, 0b111],
    "4": [0b101, 0b101, 0b111, 0b001, 0b001],
    "5": [0b111, 0b100, 0b111, 0b001, 0b111],
    "6": [0b111, 0b100, 0b111, 0b101, 0b111],
    "7": [0b111, 0b001, 0b001, 0b001, 0b001],
    "8": [0b111, 0b101, 0b111, 0b101, 0b111],
    "9": [0b111, 0b101, 0b111, 0b001, 0b111],
    "A": [0b111, 0b101, 0b111, 0b101, 0b101],
    "B": [0b110, 0b101, 0b110, 0b101, 0b110],
    "C": [0b111, 0b100, 0b100, 0b100, 0b111],
    "D": [0b110, 0b101, 0b101, 0b101, 0b110],
    "E": [0b111, 0b100, 0b111, 0b100, 0b111],
    "F": [0b111, 0b100, 0b111, 0b100, 0b100],
    "G": [0b111, 0b100, 0b101, 0b101, 0b111],
    "H": [0b101, 0b101, 0b111, 0b101, 0b101],
    "I": [0b111, 0b010, 0b010, 0b010, 0b111],
    "J": [0b001, 0b001, 0b001, 0b101, 0b111],
    "K": [0b101, 0b101, 0b110, 0b101, 0b101],
    "L": [0b100, 0b100, 0b100, 0b100, 0b111],
    "M": [0b101, 0b111, 0b101, 0b101, 0b101],
    "N": [0b101, 0b111, 0b111, 0b111, 0b101],
    "O": [0b111, 0b101, 0b101, 0b101, 0b111],
    "P": [0b111, 0b101, 0b111, 0b100, 0b100],
    "Q": [0b111, 0b101, 0b101, 0b111, 0b001],
    "R": [0b111, 0b101, 0b111, 0b110, 0b101],
    "S": [0b111, 0b100, 0b111, 0b001, 0b111],
    "T": [0b111, 0b010, 0b010, 0b010, 0b010],
    "U": [0b101, 0b101, 0b101, 0b101, 0b111],
    "V": [0b101, 0b101, 0b101, 0b101, 0b010],
    "W": [0b101, 0b101, 0b101, 0b111, 0b101],
    "X": [0b101, 0b101, 0b010, 0b101, 0b101],
    "Y": [0b101, 0b101, 0b010, 0b010, 0b010],
    "Z": [0b111, 0b001, 0b010, 0b100, 0b111],
    " ": [0b000, 0b000, 0b000, 0b000, 0b000],
    ":": [0b000, 0b010, 0b000, 0b010, 0b000],
    "-": [0b000, 0b000, 0b111, 0b000, 0b000],
    ".": [0b000, 0b000, 0b000, 0b000, 0b010],
    "!": [0b010, 0b010, 0b010, 0b000, 0b010],
}

# 5x7 pixel font for large text (GAME OVER, titles)
# Each character is a list of 7 rows, each row is a 5-bit pattern
BIG_FONT = {
    "G": [0b01110, 0b10001, 0b10000, 0b10011, 0b10001, 0b10001, 0b01110],
    "A": [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "M": [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    "E": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "V": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "R": [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    "S": [0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
    "N": [0b10001, 0b11001, 0b10101, 0b10101, 0b10101, 0b10011, 0b10001],
    "K": [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    "P": [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    "C": [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    "I": [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    "W": [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    "Y": [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    "!": [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
    " ": [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
}

# 5x5 heart icon for lives display
HEART_ICON = [
    0b01010,
    0b11111,
    0b11111,
    0b01110,
    0b00100,
]


def draw_tiny_char(bitmap, char, x, y, color_idx, bg_idx=None):
    """Draw a single 3x5 character to a bitmap.

    Parameters
    ----------
    bitmap : displayio.Bitmap
        Target bitmap to draw on
    char : str
        Single character to draw
    x, y : int
        Top-left pixel position
    color_idx : int
        Palette index for foreground color
    bg_idx : int, optional
        Palette index for background (None = transparent)
    """
    if char.upper() not in TINY_FONT:
        return
    rows = TINY_FONT[char.upper()]
    for row_idx, row in enumerate(rows):
        for col in range(3):
            px = x + col
            py = y + row_idx
            if 0 <= px < bitmap.width and 0 <= py < bitmap.height:
                if row & (0b100 >> col):
                    bitmap[px, py] = color_idx
                elif bg_idx is not None:
                    bitmap[px, py] = bg_idx


def draw_tiny_text(bitmap, text, x, y, color_idx, bg_idx=None):
    """Draw text using 3x5 font.

    Parameters
    ----------
    bitmap : displayio.Bitmap
        Target bitmap to draw on
    text : str
        Text string to draw
    x, y : int
        Top-left pixel position of first character
    color_idx : int
        Palette index for foreground color
    bg_idx : int, optional
        Palette index for background (None = transparent)

    Returns
    -------
    int
        Width of drawn text in pixels
    """
    cursor_x = x
    for char in text:
        draw_tiny_char(bitmap, char, cursor_x, y, color_idx, bg_idx)
        cursor_x += 4  # 3px char + 1px spacing
    return cursor_x - x - 1  # total width minus trailing space


def draw_big_char(bitmap, char, x, y, color_idx, bg_idx=None):
    """Draw a single 5x7 character to a bitmap.

    Parameters
    ----------
    bitmap : displayio.Bitmap
        Target bitmap to draw on
    char : str
        Single character to draw
    x, y : int
        Top-left pixel position
    color_idx : int
        Palette index for foreground color
    bg_idx : int, optional
        Palette index for background (None = transparent)
    """
    if char.upper() not in BIG_FONT:
        return
    rows = BIG_FONT[char.upper()]
    for row_idx, row in enumerate(rows):
        for col in range(5):
            px = x + col
            py = y + row_idx
            if 0 <= px < bitmap.width and 0 <= py < bitmap.height:
                if row & (0b10000 >> col):
                    bitmap[px, py] = color_idx
                elif bg_idx is not None:
                    bitmap[px, py] = bg_idx


def draw_big_text(bitmap, text, x, y, color_idx, bg_idx=None):
    """Draw text using 5x7 font.

    Parameters
    ----------
    bitmap : displayio.Bitmap
        Target bitmap to draw on
    text : str
        Text string to draw
    x, y : int
        Top-left pixel position of first character
    color_idx : int
        Palette index for foreground color
    bg_idx : int, optional
        Palette index for background (None = transparent)

    Returns
    -------
    int
        Width of drawn text in pixels
    """
    cursor_x = x
    for char in text:
        draw_big_char(bitmap, char, cursor_x, y, color_idx, bg_idx)
        cursor_x += 6  # 5px char + 1px spacing
    return cursor_x - x - 1


def draw_heart(bitmap, x, y, color_idx, bg_idx=None):
    """Draw a 5x5 heart icon.

    Parameters
    ----------
    bitmap : displayio.Bitmap
        Target bitmap to draw on
    x, y : int
        Top-left pixel position
    color_idx : int
        Palette index for heart color
    bg_idx : int, optional
        Palette index for background (None = transparent)
    """
    for row_idx, row in enumerate(HEART_ICON):
        for col in range(5):
            px = x + col
            py = y + row_idx
            if 0 <= px < bitmap.width and 0 <= py < bitmap.height:
                if row & (0b10000 >> col):
                    bitmap[px, py] = color_idx
                elif bg_idx is not None:
                    bitmap[px, py] = bg_idx


def draw_lives(bitmap, lives, max_lives, x, y, color_idx, bg_idx=None):
    """Draw lives as a row of hearts.

    Parameters
    ----------
    bitmap : displayio.Bitmap
        Target bitmap to draw on
    lives : int
        Current number of lives
    max_lives : int
        Maximum lives (determines number of heart slots)
    x, y : int
        Top-left position of first heart
    color_idx : int
        Palette index for filled heart
    bg_idx : int, optional
        Palette index for empty heart slot (None = transparent)
    """
    spacing = 6  # 5px heart + 1px gap
    for i in range(max_lives):
        hx = x + i * spacing
        if i < lives:
            draw_heart(bitmap, hx, y, color_idx, bg_idx)
        elif bg_idx is not None:
            # Clear the heart area
            for dy in range(5):
                for dx in range(5):
                    px = hx + dx
                    py = y + dy
                    if 0 <= px < bitmap.width and 0 <= py < bitmap.height:
                        bitmap[px, py] = bg_idx


def draw_lives_centered(bitmap, lives, max_lives, y, color_idx, bg_idx=None):
    """Draw lives as centered hearts.

    Parameters
    ----------
    bitmap : displayio.Bitmap
        Target bitmap to draw on
    lives : int
        Current number of lives
    max_lives : int
        Maximum lives (determines number of heart slots)
    y : int
        Top position of hearts
    color_idx : int
        Palette index for filled heart
    bg_idx : int, optional
        Palette index for empty heart slot (None = transparent)
    """
    spacing = 6
    total_width = max_lives * 5 + (max_lives - 1) * 1
    start_x = (bitmap.width - total_width) // 2
    draw_lives(bitmap, lives, max_lives, start_x, y, color_idx, bg_idx)


def clear_bitmap(bitmap, color_idx=0):
    """Fill entire bitmap with a single color index.

    Parameters
    ----------
    bitmap : displayio.Bitmap
        Target bitmap to clear
    color_idx : int
        Palette index to fill with (default: 0)
    """
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            bitmap[x, y] = color_idx


def text_width_tiny(text):
    """Calculate pixel width of text in TINY_FONT."""
    return len(text) * 4 - 1 if text else 0


def text_width_big(text):
    """Calculate pixel width of text in BIG_FONT."""
    return len(text) * 6 - 1 if text else 0
