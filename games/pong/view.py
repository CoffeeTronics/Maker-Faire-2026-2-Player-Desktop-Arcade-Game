# pong_view.py - VIEW (MVC pattern)
# For 128x64 RGB Matrix (4 panels, rotated 90°)

import displayio
import sys
sys.path.insert(0, "/API")
from matrix_display import FlippedBitmap

from games.pong.model import (
    DISPLAY_WIDTH, DISPLAY_HEIGHT,
    PADDLE_WIDTH, PADDLE_HEIGHT, BALL_SIZE
)
from games.view_utils import (
    draw_tiny_text, draw_big_text, clear_bitmap, text_width_tiny
)

# Palette indices
_BG      = 0
_WHITE   = 1
_GREEN   = 2
_RED     = 3
_YELLOW  = 4
_CYAN    = 5

# Sound effect paths
_SOUND_PATHS = {
    "hit":      "/AudioFiles/210.wav",
    "score":    "/AudioFiles/smb_coin.wav",
    "gameover": "/AudioFiles/gameover_man.wav",
}


class PongView:
    """All visual and audio output for Pong on 128x64 matrix."""

    def __init__(self, display, audio):
        self._display = display
        self._audio = audio
        self._game_initialized = False

        # Direct WaveFile loading (like Snake game)
        self._sfx_hit = None
        self._sfx_score = None
        self._sfx_gameover = None
        try:
            from audiocore import WaveFile
            self._wav_hit_f = open("/AudioFiles/210.wav", "rb")
            self._sfx_hit = WaveFile(self._wav_hit_f)
            self._wav_score_f = open("/AudioFiles/smb_coin.wav", "rb")
            self._sfx_score = WaveFile(self._wav_score_f)
            self._wav_gameover_f = open("/AudioFiles/gameover_man.wav", "rb")
            self._sfx_gameover = WaveFile(self._wav_gameover_f)
        except Exception as e:
            print(f"Audio init failed: {e}")

        # Create bitmap with FlippedBitmap wrapper for panel compensation
        self._raw_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 6)
        self._bitmap = FlippedBitmap(self._raw_bitmap)
        self._palette = displayio.Palette(6)
        self._palette[_BG]     = 0x000000
        self._palette[_WHITE]  = 0xFFFFFF
        self._palette[_GREEN]  = 0x00FF00
        self._palette[_RED]    = 0xFF0000
        self._palette[_YELLOW] = 0xFFFF00
        self._palette[_CYAN]   = 0x00FFFF

        tg = displayio.TileGrid(self._raw_bitmap, pixel_shader=self._palette)
        self._root = displayio.Group()
        self._root.append(tg)
        display.root_group = self._root

        # Previous positions for dirty-rect updates
        self._prev_player_y = None
        self._prev_ai_y = None
        self._prev_ball_x = None
        self._prev_ball_y = None
        self._prev_player_score = None
        self._prev_ai_score = None

        # Score regions for ball overlap detection
        # Player score at x=10, AI score ends around x=54
        self._player_score_region = (10, 1, 20, 6)  # x, y, w, h
        self._ai_score_region = (44, 1, 20, 6)

        # Splash screen state
        self._in_splash = True
        self._blink_counter = 0
        self._player_mode = 2  # 1 or 2 player
        self._show_splash()

    def _show_splash(self):
        """Show the initial splash screen."""
        clear_bitmap(self._bitmap, _BG)
        # Draw "PONG" centered
        text1 = "PONG"
        text_w1 = text_width_tiny(text1)
        x1 = (DISPLAY_WIDTH - text_w1) // 2
        draw_tiny_text(self._bitmap, text1, x1, 15, _GREEN)
        # Draw player mode
        mode_text = f"{self._player_mode} PLAYER"
        mode_w = text_width_tiny(mode_text)
        draw_tiny_text(self._bitmap, mode_text, (DISPLAY_WIDTH - mode_w) // 2, 30, _WHITE)
        # Draw "PRESS START"
        text2 = "PRESS START"
        text_w2 = text_width_tiny(text2)
        x2 = (DISPLAY_WIDTH - text_w2) // 2
        draw_tiny_text(self._bitmap, text2, x2, 45, _YELLOW)

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
                    py = 45 + dy
                    if 0 <= px < DISPLAY_WIDTH and 0 <= py < DISPLAY_HEIGHT:
                        self._bitmap[px, py] = _BG
        else:
            draw_tiny_text(self._bitmap, text, x, 45, _YELLOW)

    def set_player_mode(self, mode):
        """Set player mode (1 or 2) on splash screen."""
        if not self._in_splash:
            return
        if mode == self._player_mode:
            return
        self._player_mode = mode
        # Clear the player mode text area
        mode_y = 30
        for dy in range(5):
            for dx in range(50):
                px = 39 + dx
                if 0 <= px < DISPLAY_WIDTH:
                    self._bitmap[px, mode_y + dy] = _BG
        # Draw new text
        mode_text = f"{self._player_mode} PLAYER"
        mode_w = text_width_tiny(mode_text)
        draw_tiny_text(self._bitmap, mode_text, (DISPLAY_WIDTH - mode_w) // 2, mode_y, _WHITE)

    def get_player_mode(self):
        """Return current player mode (1 or 2)."""
        return self._player_mode

    def hide_start_menu(self):
        """Dismiss splash and initialize game graphics."""
        self._in_splash = False
        self._game_initialized = True
        self._prev_player_y = None
        self._prev_ai_y = None
        self._prev_ball_x = None
        self._prev_ball_y = None
        self._prev_player_score = None
        self._prev_ai_score = None
        self._preload_sounds()

    def _preload_sounds(self):
        """Sound preloading not needed - using direct WaveFile."""
        pass

    def _draw_rect(self, x, y, w, h, color_idx):
        """Draw a filled rectangle."""
        for dy in range(h):
            for dx in range(w):
                px = int(x) + dx
                py = int(y) + dy
                if 0 <= px < DISPLAY_WIDTH and 0 <= py < DISPLAY_HEIGHT:
                    self._bitmap[px, py] = color_idx

    def _draw_center_line(self):
        """Draw the dashed center line."""
        center_x = DISPLAY_WIDTH // 2
        for y in range(0, DISPLAY_HEIGHT, 4):
            if y + 2 <= DISPLAY_HEIGHT:
                self._bitmap[center_x, y] = _WHITE
                self._bitmap[center_x, y + 1] = _WHITE

    def _ball_overlaps_region(self, ball_x, ball_y, region):
        """Check if ball overlaps a rectangular region."""
        rx, ry, rw, rh = region
        return (ball_x < rx + rw and ball_x + BALL_SIZE > rx and
                ball_y < ry + rh and ball_y + BALL_SIZE > ry)

    def _draw_initial_frame(self, model):
        """Draw the complete initial frame."""
        clear_bitmap(self._bitmap, _BG)
        self._draw_center_line()

        # Draw paddles
        player_y = int(model.player.y)
        ai_y = int(model.ai.y)
        self._draw_rect(int(model.player.x), player_y, PADDLE_WIDTH, PADDLE_HEIGHT, _WHITE)
        self._draw_rect(int(model.ai.x), ai_y, PADDLE_WIDTH, PADDLE_HEIGHT, _WHITE)

        # Draw ball
        ball_x = int(model.ball.x)
        ball_y = int(model.ball.y)
        self._draw_rect(ball_x, ball_y, BALL_SIZE, BALL_SIZE, _WHITE)

        # Draw scores
        self._draw_scores(model)

        # Store positions
        self._prev_player_y = player_y
        self._prev_ai_y = ai_y
        self._prev_ball_x = ball_x
        self._prev_ball_y = ball_y
        self._prev_player_score = model.player.score
        self._prev_ai_score = model.ai.score

    def _draw_scores(self, model):
        """Draw scores at top of screen - only clear minimal area."""
        player_score = str(model.player.score)
        ai_score = str(model.ai.score)
        
        # Only clear if score changed - minimal rectangle
        player_w = text_width_tiny(player_score) + 2
        ai_w = text_width_tiny(ai_score) + 2
        ai_x = DISPLAY_WIDTH - 10 - text_width_tiny(ai_score)
        
        # Clear just the digit areas (5 rows high for tiny font)
        for y in range(1, 6):
            for x in range(10, 10 + player_w):
                self._bitmap[x, y] = _BG
            for x in range(ai_x, ai_x + ai_w):
                self._bitmap[x, y] = _BG
        
        draw_tiny_text(self._bitmap, player_score, 10, 1, _GREEN)
        draw_tiny_text(self._bitmap, ai_score, ai_x, 1, _RED)

    def draw(self, model):
        """Update display from model state - only changed pixels."""
        if self._in_splash:
            return

        # First frame - draw everything
        if self._prev_ball_x is None:
            self._draw_initial_frame(model)
            return

        player_y = int(model.player.y)
        ai_y = int(model.ai.y)
        ball_x = int(model.ball.x)
        ball_y = int(model.ball.y)

        # Check if ball was in score region (before erasing)
        prev_in_player_score = self._ball_overlaps_region(
            self._prev_ball_x, self._prev_ball_y, self._player_score_region)
        prev_in_ai_score = self._ball_overlaps_region(
            self._prev_ball_x, self._prev_ball_y, self._ai_score_region)

        # Erase old ball position
        if self._prev_ball_x != ball_x or self._prev_ball_y != ball_y:
            self._draw_rect(self._prev_ball_x, self._prev_ball_y, BALL_SIZE, BALL_SIZE, _BG)
            # Redraw center line if ball was over it
            if self._prev_ball_x <= DISPLAY_WIDTH // 2 < self._prev_ball_x + BALL_SIZE:
                self._draw_center_line()

        # Erase old player paddle position (only the changed rows)
        if self._prev_player_y != player_y:
            if player_y > self._prev_player_y:
                # Moved down - erase top rows
                rows_to_clear = player_y - self._prev_player_y
                self._draw_rect(int(model.player.x), self._prev_player_y, PADDLE_WIDTH, rows_to_clear, _BG)
            else:
                # Moved up - erase bottom rows
                rows_to_clear = self._prev_player_y - player_y
                self._draw_rect(int(model.player.x), player_y + PADDLE_HEIGHT, PADDLE_WIDTH, rows_to_clear, _BG)

        # Erase old AI paddle position (only the changed rows)
        if self._prev_ai_y != ai_y:
            if ai_y > self._prev_ai_y:
                rows_to_clear = ai_y - self._prev_ai_y
                self._draw_rect(int(model.ai.x), self._prev_ai_y, PADDLE_WIDTH, rows_to_clear, _BG)
            else:
                rows_to_clear = self._prev_ai_y - ai_y
                self._draw_rect(int(model.ai.x), ai_y + PADDLE_HEIGHT, PADDLE_WIDTH, rows_to_clear, _BG)

        # Draw new ball position
        self._draw_rect(ball_x, ball_y, BALL_SIZE, BALL_SIZE, _WHITE)

        # Draw paddles at new positions
        self._draw_rect(int(model.player.x), player_y, PADDLE_WIDTH, PADDLE_HEIGHT, _WHITE)
        self._draw_rect(int(model.ai.x), ai_y, PADDLE_WIDTH, PADDLE_HEIGHT, _WHITE)

        # Check if ball is currently in score region
        curr_in_player_score = self._ball_overlaps_region(
            ball_x, ball_y, self._player_score_region)
        curr_in_ai_score = self._ball_overlaps_region(
            ball_x, ball_y, self._ai_score_region)

        # Redraw scores if ball just left the score region or score changed
        need_redraw_player = (prev_in_player_score and not curr_in_player_score)
        need_redraw_ai = (prev_in_ai_score and not curr_in_ai_score)
        score_changed = (model.player.score != self._prev_player_score or
                        model.ai.score != self._prev_ai_score)

        if need_redraw_player or need_redraw_ai or score_changed:
            self._draw_scores(model)
            self._prev_player_score = model.player.score
            self._prev_ai_score = model.ai.score

        # Store current positions for next frame
        self._prev_player_y = player_y
        self._prev_ai_y = ai_y
        self._prev_ball_x = ball_x
        self._prev_ball_y = ball_y

    def show_game_over(self, winner):
        """Show game over screen."""
        clear_bitmap(self._bitmap, _BG)

        if winner == "player":
            draw_big_text(self._bitmap, "YOU", (DISPLAY_WIDTH - 18) // 2, 18, _GREEN)
            draw_big_text(self._bitmap, "WIN", (DISPLAY_WIDTH - 18) // 2, 36, _GREEN)
        else:
            draw_big_text(self._bitmap, "GAME", (DISPLAY_WIDTH - 24) // 2, 18, _RED)
            draw_big_text(self._bitmap, "OVER", (DISPLAY_WIDTH - 24) // 2, 36, _RED)

    def play_sfx(self, name):
        """Play a named sound effect using direct WaveFile."""
        wav = None
        if name == "hit":
            wav = self._sfx_hit
        elif name == "score":
            wav = self._sfx_score
        elif name == "gameover":
            wav = self._sfx_gameover
        
        if wav is None or self._audio is None:
            return
        try:
            if self._audio.is_playing:
                self._audio.stop()
            # Play directly through the internal audio object
            self._audio._audio.play(wav)
        except Exception as e:
            print(f"Play error {name}: {e}")

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
        # Close WAV file handles
        for attr in ['_wav_hit_f', '_wav_score_f', '_wav_gameover_f']:
            try:
                fh = getattr(self, attr, None)
                if fh:
                    fh.close()
            except:
                pass
