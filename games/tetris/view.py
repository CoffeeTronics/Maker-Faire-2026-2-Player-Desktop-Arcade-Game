# tetris_view.py - VIEW (MVC pattern)
# For 128x64 RGB Matrix (4 panels, rotated 90°) - Horizontal Tetris

import displayio
import sys
sys.path.insert(0, "/API")
from matrix_display import FlippedBitmap

from games.tetris.model import (
    DISPLAY_WIDTH, DISPLAY_HEIGHT,
    BOARD_WIDTH, BOARD_HEIGHT, BOARD_X, BOARD_Y, CELL_SIZE
)
from games.view_utils import (
    draw_tiny_text, draw_big_text, clear_bitmap, text_width_tiny
)

# Palette indices
_BG      = 0
_CYAN    = 1   # I
_YELLOW  = 2   # O
_PURPLE  = 3   # T
_GREEN   = 4   # S
_RED     = 5   # Z
_BLUE    = 6   # J
_ORANGE  = 7   # L
_WHITE   = 8
_GRAY    = 9   # Ghost piece / grid

# Sound effect paths
_SOUND_PATHS = {
    "rotate":   "/AudioFiles/210.wav",
    "land":     "/AudioFiles/Tetris (GB) (27)-piece_landed.wav",
    "clear":    "/AudioFiles/Tetris (GB) (21)-line_clear.wav",
    "drop":     "/AudioFiles/210.wav",
    "gameover": "/AudioFiles/gameover_man.wav",
}


class TetrisView:
    """All visual and audio output for Tetris on 128x64 matrix."""

    def __init__(self, display, audio):
        self._display = display
        self._audio = audio
        self._game_initialized = False

        # Create bitmap with FlippedBitmap wrapper for panel compensation
        self._raw_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 10)
        self._bitmap = FlippedBitmap(self._raw_bitmap)
        self._palette = displayio.Palette(10)
        self._palette[_BG]     = 0x000000
        self._palette[_CYAN]   = 0x00FFFF
        self._palette[_YELLOW] = 0xFFFF00
        self._palette[_PURPLE] = 0xAA00FF
        self._palette[_GREEN]  = 0x00FF00
        self._palette[_RED]    = 0xFF0000
        self._palette[_BLUE]   = 0x0000FF
        self._palette[_ORANGE] = 0xFF8800
        self._palette[_WHITE]  = 0xFFFFFF
        self._palette[_GRAY]   = 0x333333

        tg = displayio.TileGrid(self._raw_bitmap, pixel_shader=self._palette)
        self._root = displayio.Group()
        self._root.append(tg)
        display.root_group = self._root

        # Previous state for dirty updates
        self._prev_board = None
        self._prev_piece_blocks = None
        self._prev_ghost_blocks = None
        self._prev_score = None
        self._prev_level = None

        # Splash screen state
        self._in_splash = True
        self._blink_counter = 0
        self._show_splash()

    def _show_splash(self):
        """Show the initial splash screen."""
        clear_bitmap(self._bitmap, _BG)
        # Draw "TETRIS" centered (vertically centered for 128x64)
        text1 = "TETRIS"
        text_w1 = text_width_tiny(text1)
        x1 = (DISPLAY_WIDTH - text_w1) // 2
        draw_tiny_text(self._bitmap, text1, x1, 20, _CYAN)
        # Draw "PRESS START"
        text2 = "PRESS START"
        text_w2 = text_width_tiny(text2)
        x2 = (DISPLAY_WIDTH - text_w2) // 2
        draw_tiny_text(self._bitmap, text2, x2, 38, _YELLOW)

    def blink_start_prompt(self):
        """Blink the start prompt text."""
        if not self._in_splash:
            return
        self._blink_counter += 1
        if self._blink_counter >= 30:
            self._blink_counter = 0

        text = "PRESS START"
        text_w = text_width_tiny(text)
        x = (DISPLAY_WIDTH - text_w) // 2

        if self._blink_counter >= 15:
            for dy in range(5):
                for dx in range(text_w + 1):
                    px = x + dx
                    py = 38 + dy
                    if 0 <= px < DISPLAY_WIDTH and 0 <= py < DISPLAY_HEIGHT:
                        self._bitmap[px, py] = _BG
        else:
            draw_tiny_text(self._bitmap, text, x, 38, _YELLOW)

    def hide_start_menu(self):
        """Dismiss splash and initialize game graphics."""
        self._in_splash = False
        self._game_initialized = True
        self._prev_board = None
        self._prev_piece_blocks = None
        self._prev_ghost_blocks = None
        self._prev_score = None
        self._prev_level = None
        self._preload_sounds()

    def _preload_sounds(self):
        """Preload all sound effects."""
        if self._audio is None:
            return
        for name, path in _SOUND_PATHS.items():
            try:
                self._audio.preload_wav(name, path)
            except Exception as e:
                print(f"Failed to preload {name}: {e}")

    def _draw_cell(self, board_x, board_y, color_idx):
        """Draw a single cell on the board."""
        px = BOARD_X + board_x * CELL_SIZE
        py = BOARD_Y + board_y * CELL_SIZE
        for dy in range(CELL_SIZE):
            for dx in range(CELL_SIZE):
                sx = px + dx
                sy = py + dy
                if 0 <= sx < DISPLAY_WIDTH and 0 <= sy < DISPLAY_HEIGHT:
                    self._bitmap[sx, sy] = color_idx

    def _draw_initial_frame(self, model):
        """Draw the complete initial frame."""
        clear_bitmap(self._bitmap, _BG)

        # Draw board border
        self._draw_border()

        # Draw board cells (locked pieces)
        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                if model.board[y][x] != 0:
                    self._draw_cell(x, y, model.board[y][x])

        # Draw current piece
        if model.current_piece:
            # Ghost first (so piece draws over it)
            ghost = model.get_ghost_blocks()
            for gx, gy in ghost:
                if 0 <= gx < BOARD_WIDTH and 0 <= gy < BOARD_HEIGHT:
                    self._draw_cell(gx, gy, _GRAY)

            for bx, by in model.current_piece.get_blocks():
                if 0 <= bx < BOARD_WIDTH and 0 <= by < BOARD_HEIGHT:
                    self._draw_cell(bx, by, model.current_piece.color)

        # Store state
        self._prev_board = [row[:] for row in model.board]
        self._prev_piece_blocks = list(model.current_piece.get_blocks()) if model.current_piece else []
        self._prev_ghost_blocks = model.get_ghost_blocks() if model.current_piece else []
        self._prev_score = model.score
        self._prev_level = model.level

    def _draw_border(self):
        """Draw the board border."""
        # Top edge
        for x in range(BOARD_X - 1, BOARD_X + BOARD_WIDTH * CELL_SIZE + 1):
            if 0 <= x < DISPLAY_WIDTH and BOARD_Y - 1 >= 0:
                self._bitmap[x, BOARD_Y - 1] = _GRAY
        # Bottom edge
        by = BOARD_Y + BOARD_HEIGHT * CELL_SIZE
        for x in range(BOARD_X - 1, BOARD_X + BOARD_WIDTH * CELL_SIZE + 1):
            if 0 <= x < DISPLAY_WIDTH and by < DISPLAY_HEIGHT:
                self._bitmap[x, by] = _GRAY
        # Left edge (spawn side)
        for y in range(BOARD_Y - 1, BOARD_Y + BOARD_HEIGHT * CELL_SIZE + 1):
            if 0 <= y < DISPLAY_HEIGHT and BOARD_X - 1 >= 0:
                self._bitmap[BOARD_X - 1, y] = _GRAY
        # Right edge (where pieces land)
        rx = BOARD_X + BOARD_WIDTH * CELL_SIZE
        for y in range(BOARD_Y - 1, BOARD_Y + BOARD_HEIGHT * CELL_SIZE + 1):
            if 0 <= y < DISPLAY_HEIGHT and rx < DISPLAY_WIDTH:
                self._bitmap[rx, y] = _GRAY

    def draw(self, model):
        """Update display from model state."""
        if self._in_splash:
            return

        # First frame - draw everything
        if self._prev_board is None:
            self._draw_initial_frame(model)
            return

        # Get current positions
        curr_piece_blocks = list(model.current_piece.get_blocks()) if model.current_piece else []
        curr_ghost_blocks = list(model.get_ghost_blocks()) if model.current_piece else []

        # Check if piece/ghost moved
        piece_moved = curr_piece_blocks != self._prev_piece_blocks
        ghost_moved = curr_ghost_blocks != self._prev_ghost_blocks

        # Only erase old positions if they changed
        if ghost_moved and self._prev_ghost_blocks:
            for gx, gy in self._prev_ghost_blocks:
                if 0 <= gx < BOARD_WIDTH and 0 <= gy < BOARD_HEIGHT:
                    if self._prev_board[gy][gx] == 0:
                        self._draw_cell(gx, gy, _BG)

        if piece_moved and self._prev_piece_blocks:
            for bx, by in self._prev_piece_blocks:
                if 0 <= bx < BOARD_WIDTH and 0 <= by < BOARD_HEIGHT:
                    if self._prev_board[by][bx] == 0:
                        self._draw_cell(bx, by, _BG)

        # Update changed board cells
        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                if model.board[y][x] != self._prev_board[y][x]:
                    if model.board[y][x] == 0:
                        self._draw_cell(x, y, _BG)
                    else:
                        self._draw_cell(x, y, model.board[y][x])

        # Only draw new positions if they changed
        if ghost_moved and curr_ghost_blocks:
            for gx, gy in curr_ghost_blocks:
                if 0 <= gx < BOARD_WIDTH and 0 <= gy < BOARD_HEIGHT:
                    if model.board[gy][gx] == 0:
                        self._draw_cell(gx, gy, _GRAY)

        if piece_moved and curr_piece_blocks:
            for bx, by in curr_piece_blocks:
                if 0 <= bx < BOARD_WIDTH and 0 <= by < BOARD_HEIGHT:
                    self._draw_cell(bx, by, model.current_piece.color)

        # Store current state
        self._prev_piece_blocks = curr_piece_blocks
        self._prev_ghost_blocks = curr_ghost_blocks

        # Store board state
        self._prev_board = [row[:] for row in model.board]

    def show_game_over(self):
        """Show game over screen."""
        clear_bitmap(self._bitmap, _BG)
        draw_big_text(self._bitmap, "GAME", (DISPLAY_WIDTH - 24) // 2, 18, _RED)
        draw_big_text(self._bitmap, "OVER", (DISPLAY_WIDTH - 24) // 2, 36, _RED)

    def play_sfx(self, name):
        """Play a named sound effect."""
        if self._audio:
            self._audio.play_preloaded(name)

    def stop_audio(self):
        """Stop the current sound."""
        if self._audio:
            self._audio.stop()

    def is_audio_playing(self):
        """True if audio is currently playing."""
        if self._audio:
            return self._audio.is_playing
        return False

    def cleanup(self):
        """Release view resources."""
        pass
