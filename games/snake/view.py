# view.py - Snake Game View (MVC pattern)
# For 128x64 RGB Matrix with 64x32 grid (2x2 pixels per cell)

import time
import displayio
import sys
sys.path.insert(0, "/API")
from matrix_display import FlippedBitmap

from games.snake.model import GRID_W, GRID_H
from games.view_utils import (
    TINY_FONT, BIG_FONT, HEART_ICON,
    draw_tiny_text, draw_big_text, draw_heart,
    draw_lives_centered, clear_bitmap, text_width_tiny
)

# Display dimensions
DISPLAY_W = 128
DISPLAY_H = 64

# Palette indices
_BG     = 0
_SNAKE  = 1
_FOOD   = 2
_HEAD   = 3
_WHITE  = 4
_YELLOW = 5

# Cell size in pixels (2x2)
CELL_SIZE = 2


class SnakeView:
    """All visual and audio output for the Snake game on 64x32 matrix."""

    def __init__(self, display, audio):
        self._display = display
        self._audio = audio

        # Audio file handles
        self._sfx_food = None
        self._sfx_gameover = None
        try:
            from audiocore import WaveFile
            self._wav_food_f = open("AudioFiles/210.wav", "rb")
            self._sfx_food = WaveFile(self._wav_food_f)
            self._wav_gameover_f = open("AudioFiles/140.wav", "rb")
            self._sfx_gameover = WaveFile(self._wav_gameover_f)
        except Exception as e:
            print("Audio init failed:", e)

        # Create bitmap with FlippedBitmap wrapper for panel compensation
        self._raw_bitmap = displayio.Bitmap(DISPLAY_W, DISPLAY_H, 6)
        self._bitmap = FlippedBitmap(self._raw_bitmap)
        self._palette = displayio.Palette(6)
        self._palette[_BG]     = 0x000000
        self._palette[_SNAKE]  = 0x00FF00
        self._palette[_FOOD]   = 0xFF0000
        self._palette[_HEAD]   = 0x00FFFF
        self._palette[_WHITE]  = 0xFFFFFF
        self._palette[_YELLOW] = 0xFFFF00

        tg = displayio.TileGrid(self._raw_bitmap, pixel_shader=self._palette)

        self._root = displayio.Group()
        self._root.append(tg)
        display.root_group = self._root

        # State tracking for dirty rendering
        self._score = 0
        self._high_score = 0
        self._lives = 3
        self._prev_score_text = ""
        self._prev_high_text = ""
        self._prev_lives = -1
        self._prev_snake = []
        self._prev_food = None

        # Splash screen state
        self._in_splash = True
        self._blink_counter = 0
        self._show_splash()

    def _show_splash(self):
        """Show the initial splash screen."""
        clear_bitmap(self._bitmap, _BG)
        # Draw "SNAKE" centered (vertically centered for 128x64)
        text = "SNAKE"
        text_w = text_width_tiny(text)
        x = (DISPLAY_W - text_w) // 2
        draw_tiny_text(self._bitmap, text, x, 20, _SNAKE)
        # Draw "PUSH START"
        text2 = "PUSH START"
        text_w2 = text_width_tiny(text2)
        x2 = (DISPLAY_W - text_w2) // 2
        draw_tiny_text(self._bitmap, text2, x2, 38, _YELLOW)

    def blink_start_prompt(self):
        """Blink the start prompt text."""
        if not self._in_splash:
            return
        self._blink_counter += 1
        if self._blink_counter >= 30:
            self._blink_counter = 0

        text = "PUSH START"
        text_w = text_width_tiny(text)
        x = (DISPLAY_W - text_w) // 2

        if self._blink_counter >= 15:
            # Clear the text area
            for dy in range(5):
                for dx in range(text_w + 1):
                    px = x + dx
                    py = 38 + dy
                    if 0 <= px < DISPLAY_W and 0 <= py < DISPLAY_H:
                        self._bitmap[px, py] = _BG
        else:
            draw_tiny_text(self._bitmap, text, x, 38, _YELLOW)

    def hide_start_menu(self):
        """Dismiss splash and show game screen."""
        self._in_splash = False
        clear_bitmap(self._bitmap, _BG)
        # Reset dirty tracking
        self._prev_snake = []
        self._prev_food = None
        self._prev_score_text = ""
        self._prev_high_text = ""
        self._prev_lives = -1

    def _draw_cell(self, cx, cy, color_idx):
        """Draw a 2x2 cell at grid position (cx, cy)."""
        for dy in range(CELL_SIZE):
            for dx in range(CELL_SIZE):
                px = cx * CELL_SIZE + dx
                py = cy * CELL_SIZE + dy
                if 0 <= px < DISPLAY_W and 0 <= py < DISPLAY_H:
                    self._bitmap[px, py] = color_idx

    def render(self, model):
        """Redraw the game grid from Model state."""
        if self._in_splash:
            return

        bmp = self._bitmap
        snake_set = set(model.snake)
        prev_snake_set = set(self._prev_snake)

        # Clear cells that snake left
        for pos in prev_snake_set - snake_set:
            if pos != model.food:
                self._draw_cell(pos[0], pos[1], _BG)

        # Clear old food position if it moved
        if self._prev_food and self._prev_food != model.food and self._prev_food not in snake_set:
            self._draw_cell(self._prev_food[0], self._prev_food[1], _BG)

        # Draw food
        self._draw_cell(model.food[0], model.food[1], _FOOD)

        # Draw snake
        for i, (sx, sy) in enumerate(model.snake):
            color = _HEAD if i == 0 else _SNAKE
            self._draw_cell(sx, sy, color)

        # Draw score (top left) - "P:123"
        score_text = "P:" + str(self._score)
        if score_text != self._prev_score_text:
            # Clear old score area
            for dy in range(5):
                for dx in range(20):
                    if 0 <= dx < DISPLAY_W and 0 <= dy < DISPLAY_H:
                        self._bitmap[dx, dy] = _BG
            draw_tiny_text(self._bitmap, score_text, 0, 0, _WHITE)
            self._prev_score_text = score_text

        # Draw high score (top right) - "H:123"
        high_text = "H:" + str(self._high_score)
        if high_text != self._prev_high_text:
            text_w = text_width_tiny(high_text)
            # Clear old high score area
            for dy in range(5):
                for dx in range(20):
                    px = DISPLAY_W - 1 - dx
                    if 0 <= px < DISPLAY_W and 0 <= dy < DISPLAY_H:
                        self._bitmap[px, dy] = _BG
            draw_tiny_text(self._bitmap, high_text, DISPLAY_W - text_w, 0, _YELLOW)
            self._prev_high_text = high_text

        # Draw lives as hearts (top center)
        if self._lives != self._prev_lives:
            draw_lives_centered(self._bitmap, self._lives, 3, 0, _FOOD, _BG)
            self._prev_lives = self._lives

        # Update tracking
        self._prev_snake = list(model.snake)
        self._prev_food = model.food

    def update_score(self, score):
        self._score = score

    def update_high_score(self, high_score):
        self._high_score = high_score

    def update_lives(self, lives):
        self._lives = lives

    def flash_red(self, duration=0.15):
        """Flash screen red briefly."""
        old_bg = self._palette[_BG]
        self._palette[_BG] = 0xFF0000
        clear_bitmap(self._bitmap, _BG)
        time.sleep(duration)
        self._palette[_BG] = old_bg

    def show_game_over(self, score, high_score, duration=3.0):
        """Display game over screen."""
        clear_bitmap(self._bitmap, _BG)

        # Draw "GAME" centered (vertically centered for 128x64)
        draw_big_text(self._bitmap, "GAME", (DISPLAY_W - 24) // 2, 18, _FOOD)
        # Draw "OVER" centered below
        draw_big_text(self._bitmap, "OVER", (DISPLAY_W - 24) // 2, 36, _FOOD)

        time.sleep(duration)

        # Clear for next game
        clear_bitmap(self._bitmap, _BG)
        print("Game Over! Score:", score, "High:", high_score)

        # Reset dirty tracking
        self._prev_snake = []
        self._prev_food = None
        self._prev_score_text = ""
        self._prev_high_text = ""
        self._prev_lives = -1

    def play_food_sfx(self):
        self._play(self._sfx_food)

    def play_gameover_sfx(self):
        self._play(self._sfx_gameover)

    def play_life_lost_sfx(self):
        self._play(self._sfx_gameover)

    def _play(self, wav):
        if wav is None or self._audio is None:
            return
        try:
            if self._audio.is_playing:
                self._audio.stop()
            self._audio._audio.play(wav)
        except Exception as e:
            print("Audio play error:", e)

    def cleanup(self):
        """Release view resources."""
        pass
