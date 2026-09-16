"""
matrix_display.py - 128x64 RGB Matrix Display (4 panels)
=========================================================
Board: Curiosity PyKit with RGB Matrix

Provides a display abstraction for four chained 64x32 RGB LED Matrix panels
using the adafruit_matrixportal library in a vertical arrangement,
rotated 90 degrees clockwise for landscape orientation.

Panel Configuration:
  - 4 panels stacked vertically, rotated 90° CW for landscape
  - Cables reversed (Controller → Panel 4 → 3 → 2 → 1)
  - Physical order left-to-right: Panel 4, 3, 2, 1
  - Panels 2 & 4 need 180° flip compensation (via FlippedBitmap)
  - Total display: 128 pixels wide x 64 pixels tall

Usage:
  Use FlippedBitmap wrapper for all bitmap drawing to ensure correct
  panel orientation. Pass the raw bitmap to TileGrid.

  from matrix_display import MatrixDisplay, FlippedBitmap, WIDTH, HEIGHT

  matrix = MatrixDisplay()
  raw_bitmap = displayio.Bitmap(WIDTH, HEIGHT, num_colors)
  bitmap = FlippedBitmap(raw_bitmap)
  bitmap[x, y] = color  # Use wrapper for drawing
  tg = displayio.TileGrid(raw_bitmap, pixel_shader=palette)  # Use raw for TileGrid
"""

from adafruit_matrixportal.matrix import Matrix
import displayio

# Display dimensions (after 90° rotation: 64x128 becomes 128x64)
WIDTH = 128
HEIGHT = 64

# Panel chaining configuration
PANEL_WIDTH = 64
PANEL_HEIGHT = 32
TILE_ROWS = 4
SERPENTINE = False  # Using software flip instead
BIT_DEPTH = 2
ROTATION = 90  # Clockwise rotation


class FlippedBitmap:
    """Bitmap wrapper that flips panels 1 & 3 to compensate for physical orientation.

    After 90° CW rotation, the 4 panels map to these x-regions (32 pixels each):
      - Panel 1: x = 0-31   (needs 180° flip)
      - Panel 2: x = 32-63  (correct orientation)
      - Panel 3: x = 64-95  (needs 180° flip)
      - Panel 4: x = 96-127 (correct orientation)

    Usage:
        real_bitmap = displayio.Bitmap(128, 64, num_colors)
        bitmap = FlippedBitmap(real_bitmap)
        bitmap[x, y] = color  # Coordinates are auto-transformed
        tg = displayio.TileGrid(bitmap.raw, pixel_shader=palette)
    """

    def __init__(self, bitmap):
        self._bitmap = bitmap
        self.width = bitmap.width
        self.height = bitmap.height

    @property
    def raw(self):
        """Return underlying bitmap for TileGrid."""
        return self._bitmap

    def _transform(self, x, y):
        """Transform coordinates for reversed cable order.

        With reversed cables, physical panel order left-to-right is: 4, 3, 2, 1
        x=0-31 → Panel 4 (needs 180° flip)
        x=32-63 → Panel 3 (no flip)
        x=64-95 → Panel 2 (needs 180° flip)
        x=96-127 → Panel 1 (no flip)
        """
        if 0 <= x < 32:  # Panel 4: 180° flip within region
            x = 31 - x
            y = 63 - y
        elif 64 <= x < 96:  # Panel 2: 180° flip within region
            x = 159 - x
            y = 63 - y
        return x, y

    def __setitem__(self, key, value):
        x, y = key
        x, y = self._transform(x, y)
        if 0 <= x < self.width and 0 <= y < self.height:
            self._bitmap[x, y] = value

    def __getitem__(self, key):
        x, y = key
        x, y = self._transform(x, y)
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._bitmap[x, y]
        return 0

    def fill(self, value):
        """Fill entire bitmap with a value."""
        self._bitmap.fill(value)


def create_flipped_bitmap(width, height, num_colors):
    """Create a FlippedBitmap with proper panel compensation.

    Returns:
        tuple: (FlippedBitmap wrapper, raw displayio.Bitmap for TileGrid)
    """
    raw = displayio.Bitmap(width, height, num_colors)
    return FlippedBitmap(raw), raw


class MatrixDisplay:
    """128x64 RGB Matrix display abstraction (4 chained panels).

    Wraps the adafruit_matrixportal Matrix class to provide a consistent
    interface. Configured for 4 panels in a 2x2 grid with serpentine wiring.

    Example
    -------
    from matrix_display import MatrixDisplay, WIDTH, HEIGHT
    import displayio

    matrix = MatrixDisplay()

    # Create a simple display group
    group = displayio.Group()
    bitmap = displayio.Bitmap(WIDTH, HEIGHT, 2)
    palette = displayio.Palette(2)
    palette[0] = 0x000000  # black
    palette[1] = 0xFF0000  # red

    # Draw a red pixel at center
    bitmap[64, 32] = 1

    group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
    matrix.display.root_group = group
    """

    def __init__(self, width=WIDTH, height=HEIGHT, bit_depth=BIT_DEPTH):
        """Initialize the RGB Matrix display.

        Parameters
        ----------
        width : int, optional
            Display width in pixels (default: 128)
        height : int, optional
            Display height in pixels (default: 64)
        bit_depth : int, optional
            Color bit depth (default: 6, range 1-6)
            Higher values give more colors but use more memory.
        """
        # Note: Pass physical dimensions (64x128) to Matrix,
        # rotation swaps them to logical dimensions (128x64)
        self._matrix = Matrix(
            width=PANEL_WIDTH,
            height=PANEL_HEIGHT * TILE_ROWS,
            bit_depth=bit_depth,
            tile_rows=TILE_ROWS,
            serpentine=SERPENTINE,
            rotation=ROTATION,
        )
        self._display = self._matrix.display
        self.width = width
        self.height = height

    @property
    def display(self):
        """The raw displayio Display object for direct access."""
        return self._display

    def fill_screen(self, color):
        """Fill the entire screen with a solid color.

        Parameters
        ----------
        color : int
            24-bit RGB color value (e.g., 0xFF0000 for red)

        Returns
        -------
        displayio.Group
            The root group that was created and applied.
        """
        import displayio
        bitmap = displayio.Bitmap(self.width, self.height, 1)
        palette = displayio.Palette(1)
        palette[0] = color
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
        group = displayio.Group()
        group.append(tile_grid)
        self._display.root_group = group
        return group

    def clear(self):
        """Clear the display to black."""
        self.fill_screen(0x000000)
