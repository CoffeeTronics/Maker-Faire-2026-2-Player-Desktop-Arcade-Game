"""
shift_register_controls.py - Arcade Controls via CD74HC165E Shift Registers
============================================================================
Board: Curiosity PyKit Explorer

Reads 2 player joysticks, 8 player buttons, and 4 admin buttons from
3 daisy-chained CD74HC165E shift registers using hardware SPI.

Hardware Configuration:
  Latch (SH/LD): board.SD_CS  (PA19) - directly controlled GPIO
  Clock (CLK):   board.SD_SCK (PA17) - SPI clock to all 3 shift registers
  Data (QH):     board.SD_MISO (PA18) - serial data from U1

Shift Register Chain:
  U1 (Player 1) -> U2 (Player 2) -> U3 (Admin)
  - U1 QH connects to MISO
  - U2 QH connects to U1 SER
  - U3 QH connects to U2 SER
  - U3 SER tied to GND
  - CLK INH tied to GND on all

Pin Mapping - U1/U2 (Player Controls):
  A (pin 11) = UP        E (pin 3) = btn1 (Top Left)
  B (pin 12) = DOWN      F (pin 4) = btn2 (Top Right)
  C (pin 13) = LEFT      G (pin 5) = btn3 (Bottom Left)
  D (pin 14) = RIGHT     H (pin 6) = btn4 (Bottom Right)

Pin Mapping - U3 (Admin Controls):
  A-D (pins 11-14) = unused (10k pulldown only)
  E (pin 3) = 1-Player
  F (pin 4) = 2-Player
  G (pin 5) = Start
  H (pin 6) = Select

All inputs are active HIGH with 10k pulldown resistors.
"""

import board
import busio
import digitalio
import time

# Direction constants (matching joystick.py)
UP    = (0, -1)
DOWN  = (0, 1)
LEFT  = (-1, 0)
RIGHT = (1, 0)

# Bit masks for player controls (directly from CD74HC165E shift order)
_MASK_UP    = 0x01  # Bit 0 - Input A
_MASK_DOWN  = 0x02  # Bit 1 - Input B
_MASK_LEFT  = 0x04  # Bit 2 - Input C
_MASK_RIGHT = 0x08  # Bit 3 - Input D
_MASK_BTN1  = 0x10  # Bit 4 - Input E (Top Left)
_MASK_BTN2  = 0x20  # Bit 5 - Input F (Top Right)
_MASK_BTN3  = 0x40  # Bit 6 - Input G (Bottom Left)
_MASK_BTN4  = 0x80  # Bit 7 - Input H (Bottom Right)

# Bit masks for admin controls
_MASK_ONE_PLAYER  = 0x10  # Bit 4 - Input E
_MASK_TWO_PLAYER  = 0x20  # Bit 5 - Input F
_MASK_START       = 0x40  # Bit 6 - Input G
_MASK_SELECT      = 0x80  # Bit 7 - Input H


class PlayerState:
    """State and edge detection for one player's controls.

    Holds joystick directions and 4 buttons with fell/rose edge detection.
    Do not instantiate directly - access via ShiftRegisterControls.p1 or .p2
    """

    def __init__(self):
        self._current = 0
        self._last = 0

    def _update(self, byte_val):
        """Update state from shift register byte. Called by parent."""
        self._last = self._current
        self._current = byte_val

    # --- Joystick current state ---

    @property
    def up(self):
        """True while joystick is pushed up."""
        return bool(self._current & _MASK_UP)

    @property
    def down(self):
        """True while joystick is pushed down."""
        return bool(self._current & _MASK_DOWN)

    @property
    def left(self):
        """True while joystick is pushed left."""
        return bool(self._current & _MASK_LEFT)

    @property
    def right(self):
        """True while joystick is pushed right."""
        return bool(self._current & _MASK_RIGHT)

    # --- Button current state ---

    @property
    def btn1(self):
        """True while button 1 (Top Left) is held."""
        return bool(self._current & _MASK_BTN1)

    @property
    def btn2(self):
        """True while button 2 (Top Right) is held."""
        return bool(self._current & _MASK_BTN2)

    @property
    def btn3(self):
        """True while button 3 (Bottom Left) is held."""
        return bool(self._current & _MASK_BTN3)

    @property
    def btn4(self):
        """True while button 4 (Bottom Right) is held."""
        return bool(self._current & _MASK_BTN4)

    # --- Joystick edge detection - fell (just activated) ---

    @property
    def up_fell(self):
        """True for one frame when joystick pushed up."""
        return (self._current & _MASK_UP) and not (self._last & _MASK_UP)

    @property
    def down_fell(self):
        """True for one frame when joystick pushed down."""
        return (self._current & _MASK_DOWN) and not (self._last & _MASK_DOWN)

    @property
    def left_fell(self):
        """True for one frame when joystick pushed left."""
        return (self._current & _MASK_LEFT) and not (self._last & _MASK_LEFT)

    @property
    def right_fell(self):
        """True for one frame when joystick pushed right."""
        return (self._current & _MASK_RIGHT) and not (self._last & _MASK_RIGHT)

    # --- Button edge detection - fell (just pressed) ---

    @property
    def btn1_fell(self):
        """True for one frame when button 1 first pressed."""
        return (self._current & _MASK_BTN1) and not (self._last & _MASK_BTN1)

    @property
    def btn2_fell(self):
        """True for one frame when button 2 first pressed."""
        return (self._current & _MASK_BTN2) and not (self._last & _MASK_BTN2)

    @property
    def btn3_fell(self):
        """True for one frame when button 3 first pressed."""
        return (self._current & _MASK_BTN3) and not (self._last & _MASK_BTN3)

    @property
    def btn4_fell(self):
        """True for one frame when button 4 first pressed."""
        return (self._current & _MASK_BTN4) and not (self._last & _MASK_BTN4)

    # --- Joystick edge detection - rose (just released) ---

    @property
    def up_rose(self):
        """True for one frame when joystick released from up."""
        return (self._last & _MASK_UP) and not (self._current & _MASK_UP)

    @property
    def down_rose(self):
        """True for one frame when joystick released from down."""
        return (self._last & _MASK_DOWN) and not (self._current & _MASK_DOWN)

    @property
    def left_rose(self):
        """True for one frame when joystick released from left."""
        return (self._last & _MASK_LEFT) and not (self._current & _MASK_LEFT)

    @property
    def right_rose(self):
        """True for one frame when joystick released from right."""
        return (self._last & _MASK_RIGHT) and not (self._current & _MASK_RIGHT)

    # --- Button edge detection - rose (just released) ---

    @property
    def btn1_rose(self):
        """True for one frame when button 1 released."""
        return (self._last & _MASK_BTN1) and not (self._current & _MASK_BTN1)

    @property
    def btn2_rose(self):
        """True for one frame when button 2 released."""
        return (self._last & _MASK_BTN2) and not (self._current & _MASK_BTN2)

    @property
    def btn3_rose(self):
        """True for one frame when button 3 released."""
        return (self._last & _MASK_BTN3) and not (self._current & _MASK_BTN3)

    @property
    def btn4_rose(self):
        """True for one frame when button 4 released."""
        return (self._last & _MASK_BTN4) and not (self._current & _MASK_BTN4)

    # --- Helper methods ---

    def get_direction(self):
        """Get current joystick direction.

        Returns
        -------
        tuple or None
            Direction constant (UP, DOWN, LEFT, RIGHT) or None if centered.
            Priority order: Up, Down, Left, Right (first detected wins).
        """
        if self._current & _MASK_UP:
            return UP
        if self._current & _MASK_DOWN:
            return DOWN
        if self._current & _MASK_LEFT:
            return LEFT
        if self._current & _MASK_RIGHT:
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
        if self._current & _MASK_LEFT:
            x = -1
        elif self._current & _MASK_RIGHT:
            x = 1
        if self._current & _MASK_UP:
            y = -1
        elif self._current & _MASK_DOWN:
            y = 1
        return (x, y)


class AdminState:
    """State and edge detection for admin buttons (1P, 2P, Start, Select).

    Do not instantiate directly - access via ShiftRegisterControls.admin
    """

    def __init__(self):
        self._current = 0
        self._last = 0

    def _update(self, byte_val):
        """Update state from shift register byte. Called by parent."""
        self._last = self._current
        self._current = byte_val

    # --- Current state ---

    @property
    def one_player(self):
        """True while 1-Player button is held."""
        return bool(self._current & _MASK_ONE_PLAYER)

    @property
    def two_player(self):
        """True while 2-Player button is held."""
        return bool(self._current & _MASK_TWO_PLAYER)

    @property
    def start(self):
        """True while Start button is held."""
        return bool(self._current & _MASK_START)

    @property
    def select(self):
        """True while Select button is held."""
        return bool(self._current & _MASK_SELECT)

    # --- Edge detection - fell (just pressed) ---

    @property
    def one_player_fell(self):
        """True for one frame when 1-Player first pressed."""
        return (self._current & _MASK_ONE_PLAYER) and not (self._last & _MASK_ONE_PLAYER)

    @property
    def two_player_fell(self):
        """True for one frame when 2-Player first pressed."""
        return (self._current & _MASK_TWO_PLAYER) and not (self._last & _MASK_TWO_PLAYER)

    @property
    def start_fell(self):
        """True for one frame when Start first pressed."""
        return (self._current & _MASK_START) and not (self._last & _MASK_START)

    @property
    def select_fell(self):
        """True for one frame when Select first pressed."""
        return (self._current & _MASK_SELECT) and not (self._last & _MASK_SELECT)

    # --- Edge detection - rose (just released) ---

    @property
    def one_player_rose(self):
        """True for one frame when 1-Player released."""
        return (self._last & _MASK_ONE_PLAYER) and not (self._current & _MASK_ONE_PLAYER)

    @property
    def two_player_rose(self):
        """True for one frame when 2-Player released."""
        return (self._last & _MASK_TWO_PLAYER) and not (self._current & _MASK_TWO_PLAYER)

    @property
    def start_rose(self):
        """True for one frame when Start released."""
        return (self._last & _MASK_START) and not (self._current & _MASK_START)

    @property
    def select_rose(self):
        """True for one frame when Select released."""
        return (self._last & _MASK_SELECT) and not (self._current & _MASK_SELECT)


class ShiftRegisterControls:
    """Arcade controls via 3 daisy-chained CD74HC165E shift registers.

    Provides access to 2 player joysticks, 8 player buttons, and 4 admin
    buttons with edge detection. Call update() once per frame.

    Example - Read controls and detect button presses
    -------
    from shift_register_controls import ShiftRegisterControls, UP, LEFT

    controls = ShiftRegisterControls()

    while True:
        controls.update()

        # Player 1 joystick - current state
        if controls.p1.up:
            print("P1 pushing up")
        if controls.p1.get_direction() == LEFT:
            print("P1 going left")

        # Player 1 joystick - edge detection
        if controls.p1.right_fell:
            print("P1 just pushed right")

        # Player 2 buttons - edge detection
        if controls.p2.btn1_fell:
            print("P2 pressed button 1")
        if controls.p2.btn1_rose:
            print("P2 released button 1")

        # Admin buttons
        if controls.admin.start_fell:
            print("Game starting!")
        if controls.admin.select:
            print("Select held")

        time.sleep(0.016)  # ~60 Hz

    Example - Debug raw values
    -------
    from shift_register_controls import ShiftRegisterControls

    controls = ShiftRegisterControls()

    while True:
        p1, p2, admin = controls.read_raw()
        print(f"P1: {p1:08b}  P2: {p2:08b}  Admin: {admin:08b}")
        time.sleep(0.1)

    """

    def __init__(self, baudrate=8_000_000):
        """Initialize shift register controls.

        Parameters
        ----------
        baudrate : int, optional
            SPI clock speed in Hz (default 1 MHz)
        """
        self._spi = busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO)
        self._baudrate = baudrate

        self._latch = digitalio.DigitalInOut(board.SD_CS)
        self._latch.direction = digitalio.Direction.OUTPUT
        self._latch.value = True

        self._buf = bytearray(3)

        self.p1 = PlayerState()
        self.p2 = PlayerState()
        self.admin = AdminState()

    def _read_shift_registers(self):
        """Read 3 bytes from the shift register chain."""
        self._latch.value = False
        self._latch.value = True

        while not self._spi.try_lock():
            pass
        try:
            self._spi.configure(baudrate=self._baudrate, polarity=0, phase=0)
            self._spi.readinto(self._buf)
        finally:
            self._spi.unlock()

    def update(self):
        """Read all controls and update edge detection state.

        Call this once per frame before checking any button states.
        """
        self._read_shift_registers()
        self.p1._update(self._buf[0])
        self.p2._update(self._buf[1])
        self.admin._update(self._buf[2])

    def read_raw(self):
        """Read raw bytes from shift registers (for debugging).

        Returns
        -------
        tuple
            (p1_byte, p2_byte, admin_byte) - raw shift register values

        Note: This does NOT update edge detection state. Use update() for normal operation.
        """
        self._read_shift_registers()
        return (self._buf[0], self._buf[1], self._buf[2])

    def deinit(self):
        """Release hardware resources."""
        self._spi.deinit()
        self._latch.deinit()
