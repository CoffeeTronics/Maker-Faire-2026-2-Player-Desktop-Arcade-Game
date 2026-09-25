# Pacman View - Rendering for 128x64 RGB Matrix
# Uses FlippedBitmap wrapper for panel compensation

import displayio
from matrix_display import FlippedBitmap, WIDTH, HEIGHT
from games.view_utils import draw_tiny_text, draw_big_text, draw_lives, text_width_big
from games.pacman.model import (
    CELL_SIZE, HUD_HEIGHT, GRID_W, GRID_H, WALL, GHOST_HOUSE,
    GHOST_FRIGHTENED, GHOST_EATEN, UP, DOWN, LEFT, RIGHT
)

# Sound effect paths
SFX_DOT = "/AudioFiles/pacman_dot.wav"
SFX_DEATH = "/AudioFiles/pacman_death.wav"
SFX_GHOST = "/AudioFiles/pacman_ghost.wav"
SFX_POWER = "/AudioFiles/pacman_power.wav"

# Palette indices
_BG = 0
_WALL = 1
_P1 = 2       # Yellow
_P2 = 3       # Cyan
_DOT = 4      # White
_GHOST_RED = 5
_GHOST_PINK = 6
_GHOST_CYAN = 7
_GHOST_ORANGE = 8
_GHOST_SCARED = 9
_TEXT = 10
_GHOST_EYES = 11

# Pacman sprites (4x4, facing right - rotate for other directions)
PACMAN_CLOSED = [
    0b0110,
    0b1111,
    0b1111,
    0b0110,
]

PACMAN_OPEN = [
    0b0110,
    0b1110,
    0b1110,
    0b0110,
]

PACMAN_WIDE = [
    0b0100,
    0b1100,
    0b1100,
    0b0100,
]

PACMAN_FRAMES = [PACMAN_CLOSED, PACMAN_OPEN, PACMAN_WIDE]

# Ghost sprite (4x4)
GHOST_SPRITE = [
    0b0110,
    0b1111,
    0b1111,
    0b1010,
]

GHOST_EYES = [
    0b0000,
    0b1010,
    0b1010,
    0b0000,
]


class PacmanView:
    """Rendering for 128x64 2-Player Pacman."""

    NUM_COLORS = 12

    def __init__(self, display, audio):
        self._display = display
        self._audio = audio

        # Create bitmap with FlippedBitmap wrapper
        self._raw_bitmap = displayio.Bitmap(WIDTH, HEIGHT, self.NUM_COLORS)
        self._bitmap = FlippedBitmap(self._raw_bitmap)
        self._palette = self._init_palette()

        # Set up display
        tg = displayio.TileGrid(self._raw_bitmap, pixel_shader=self._palette)
        self._group = displayio.Group()
        self._group.append(tg)
        display.root_group = self._group

        # Dirty tracking
        self._prev_p1_pos = (-1, -1)
        self._prev_p2_pos = (-1, -1)
        self._prev_ghost_pos = [(-1, -1)] * 4
        self._prev_p1_score = -1
        self._prev_p2_score = -1
        self._prev_lives = -1
        self._maze_drawn = False

        # Player mode (1 or 2)
        self._player_mode = 2  # Default to 2-player

        # Preload sound effects (keep file handles open for fast replay)
        self._sfx_dot = None
        self._sfx_death = None
        self._sfx_ghost = None
        self._sfx_power = None
        self._wav_dot_f = None
        self._wav_death_f = None
        self._wav_ghost_f = None
        self._wav_power_f = None
        try:
            from audiocore import WaveFile
            self._wav_dot_f = open(SFX_DOT, "rb")
            self._sfx_dot = WaveFile(self._wav_dot_f)
            self._wav_death_f = open(SFX_DEATH, "rb")
            self._sfx_death = WaveFile(self._wav_death_f)
            self._wav_ghost_f = open(SFX_GHOST, "rb")
            self._sfx_ghost = WaveFile(self._wav_ghost_f)
            self._wav_power_f = open(SFX_POWER, "rb")
            self._sfx_power = WaveFile(self._wav_power_f)
        except Exception as e:
            print(f"[PACMAN] Audio preload failed: {e}")

    def _init_palette(self):
        palette = displayio.Palette(self.NUM_COLORS)
        palette[_BG] = 0x000000          # Black
        palette[_WALL] = 0x0000AA        # Blue walls
        palette[_P1] = 0xFFFF00          # Yellow (P1)
        palette[_P2] = 0x00FFFF          # Cyan (P2)
        palette[_DOT] = 0xFFFFFF         # White dots
        palette[_GHOST_RED] = 0xFF0000   # Red ghost
        palette[_GHOST_PINK] = 0xFFAAFF  # Pink ghost
        palette[_GHOST_CYAN] = 0x00FFFF  # Cyan ghost
        palette[_GHOST_ORANGE] = 0xFFAA00  # Orange ghost
        palette[_GHOST_SCARED] = 0x2222FF  # Scared ghost (dark blue)
        palette[_TEXT] = 0x00FF00        # Green text
        palette[_GHOST_EYES] = 0xFFFFFF  # White eyes
        return palette

    def draw_splash(self, high_score):
        """Draw splash/menu screen."""
        self._bitmap.fill(_BG)
        self._maze_drawn = False

        # Title
        title = "PACMAN"
        tx = (WIDTH - text_width_big(title)) // 2
        draw_big_text(self._bitmap, title, tx, 10, _P1)

        # High score
        hs_text = f"HI:{high_score}"
        hs_x = (WIDTH - len(hs_text) * 4) // 2
        draw_tiny_text(self._bitmap, hs_text, hs_x, 24, _TEXT)

        # Player mode selection
        self._draw_player_mode_selection()

        self._blink_visible = True
        self._blink_time = 0

    def _draw_player_mode_selection(self):
        """Draw 1P/2P selection indicators."""
        # Clear mode area
        for y in range(32, 44):
            for x in range(WIDTH):
                self._bitmap[x, y] = _BG

        # 1 PLAYER option (left side)
        p1_color = _P1 if self._player_mode == 1 else _DOT
        draw_tiny_text(self._bitmap, "1 PLAYER", 10, 34, p1_color)

        # 2 PLAYER option (right side)
        p2_color = _P2 if self._player_mode == 2 else _DOT
        draw_tiny_text(self._bitmap, "2 PLAYER", 74, 34, p2_color)

        # Selection indicator (arrow or bracket)
        if self._player_mode == 1:
            draw_tiny_text(self._bitmap, ">", 2, 34, _P1)
        else:
            draw_tiny_text(self._bitmap, ">", 66, 34, _P2)

    def set_player_mode(self, mode):
        """Set player mode (1 or 2) and update display."""
        self._player_mode = mode
        self._draw_player_mode_selection()

    def get_player_mode(self):
        """Return current player mode."""
        return self._player_mode

    def blink_start_prompt(self):
        """Toggle visibility of start prompt."""
        import time
        now = time.monotonic()
        if now - self._blink_time > 0.5:
            self._blink_time = now
            self._blink_visible = not self._blink_visible
            prompt = "PRESS START"
            px = (WIDTH - len(prompt) * 4) // 2
            color = _DOT if self._blink_visible else _BG
            draw_tiny_text(self._bitmap, prompt, px, 54, color, _BG)

    def draw_initial(self, model):
        """Draw initial game state (maze, dots, HUD)."""
        self._bitmap.fill(_BG)
        self._draw_maze(model)
        self._draw_all_dots(model)
        self._draw_hud(model)
        self._maze_drawn = True

        # Reset dirty tracking
        self._prev_p1_pos = (-1, -1)
        self._prev_p2_pos = (-1, -1)
        self._prev_ghost_pos = [(-1, -1)] * 4
        self._prev_p1_score = model.pacman1.score
        self._prev_p2_score = model.pacman2.score
        self._prev_lives = model.lives

    def _draw_maze(self, model):
        """Draw maze walls (called once)."""
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                if model.maze[gy][gx] == WALL:
                    self._draw_cell(gx, gy, _WALL)
                elif model.maze[gy][gx] == GHOST_HOUSE:
                    # Draw ghost house with different color (darker)
                    px = gx * CELL_SIZE
                    py = gy * CELL_SIZE + HUD_HEIGHT
                    for dy in range(CELL_SIZE):
                        for dx in range(CELL_SIZE):
                            self._bitmap[px + dx, py + dy] = _BG

    def _draw_all_dots(self, model):
        """Draw all dots and pellets."""
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                if model.dots[gy][gx]:
                    self._draw_dot(gx, gy)
        for px, py in model.pellets:
            self._draw_pellet(px, py)

    def _draw_cell(self, gx, gy, color_idx):
        """Draw a 4x4 cell at grid position."""
        px = gx * CELL_SIZE
        py = gy * CELL_SIZE + HUD_HEIGHT
        for dy in range(CELL_SIZE):
            for dx in range(CELL_SIZE):
                self._bitmap[px + dx, py + dy] = color_idx

    def _draw_dot(self, gx, gy):
        """Draw a single dot (1x1 pixel at cell center)."""
        px = gx * CELL_SIZE + CELL_SIZE // 2
        py = gy * CELL_SIZE + HUD_HEIGHT + CELL_SIZE // 2
        self._bitmap[px, py] = _DOT

    def _draw_pellet(self, gx, gy):
        """Draw a power pellet (3x3 pixels)."""
        px = gx * CELL_SIZE + (CELL_SIZE - 3) // 2
        py = gy * CELL_SIZE + HUD_HEIGHT + (CELL_SIZE - 3) // 2
        for dy in range(3):
            for dx in range(3):
                # Skip corners for rounder look
                if (dx == 0 or dx == 2) and (dy == 0 or dy == 2):
                    continue
                self._bitmap[px + dx, py + dy] = _DOT

    def _erase_cell(self, gx, gy):
        """Erase a cell (restore to background)."""
        self._draw_cell(gx, gy, _BG)

    def _draw_sprite(self, px, py, sprite, color_idx, direction=RIGHT):
        """Draw a 4x4 sprite with rotation based on direction."""
        for row_idx, row in enumerate(sprite):
            for col in range(4):
                if row & (0b1000 >> col):
                    # Apply rotation based on direction
                    if direction == RIGHT:
                        dx, dy = col, row_idx
                    elif direction == LEFT:
                        dx, dy = 3 - col, row_idx
                    elif direction == UP:
                        dx, dy = row_idx, 3 - col
                    elif direction == DOWN:
                        dx, dy = row_idx, col
                    else:
                        dx, dy = col, row_idx

                    x = px + dx
                    y = py + dy
                    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                        self._bitmap[x, y] = color_idx

    def _draw_pacman(self, pacman, color_idx):
        """Draw a Pacman sprite."""
        px = int(pacman.x * CELL_SIZE)
        py = int(pacman.y * CELL_SIZE) + HUD_HEIGHT
        frame = PACMAN_FRAMES[pacman.anim_frame % 3]
        self._draw_sprite(px, py, frame, color_idx, pacman.direction)

    def _draw_ghost(self, ghost):
        """Draw a ghost sprite."""
        px = int(ghost.x * CELL_SIZE)
        py = int(ghost.y * CELL_SIZE) + HUD_HEIGHT

        if ghost.state == GHOST_EATEN:
            # Just draw eyes
            self._draw_sprite(px, py, GHOST_EYES, _GHOST_EYES)
        elif ghost.state == GHOST_FRIGHTENED:
            # Scared ghost (blue)
            self._draw_sprite(px, py, GHOST_SPRITE, _GHOST_SCARED)
        else:
            # Normal ghost with its color
            self._draw_sprite(px, py, GHOST_SPRITE, ghost.color_idx)

    def _draw_hud_p1_score(self, score):
        """Redraw P1 score only."""
        # Clear P1 score area (first 28 pixels, rows 1-6)
        for y in range(6):
            for x in range(28):
                self._bitmap[x, y + 1] = _BG
        draw_tiny_text(self._bitmap, f"{score}", 1, 1, _P1)

    def _draw_hud_p2_score(self, score):
        """Redraw P2 score only."""
        # Clear P2 score area (last 28 pixels, rows 1-6)
        for y in range(6):
            for x in range(WIDTH - 28, WIDTH):
                self._bitmap[x, y + 1] = _BG
        p2_text = f"{score}"
        p2_x = WIDTH - len(p2_text) * 4
        draw_tiny_text(self._bitmap, p2_text, p2_x, 1, _P2)

    def _draw_hud_lives(self, model):
        """Redraw lives only."""
        lives_x = (WIDTH - model.MAX_LIVES * 6) // 2
        draw_lives(self._bitmap, model.lives, model.MAX_LIVES,
                   lives_x, 1, _P1, _BG)

    def _draw_hud(self, model):
        """Draw full HUD (scores, lives) - called once at game start."""
        # Clear entire HUD area
        for y in range(HUD_HEIGHT):
            for x in range(WIDTH):
                self._bitmap[x, y] = _BG
        self._draw_hud_p1_score(model.pacman1.score)
        if self._player_mode == 2:
            self._draw_hud_p2_score(model.pacman2.score)
        self._draw_hud_lives(model)

    def render(self, model):
        """Update display with dirty-rectangle rendering."""
        if not self._maze_drawn:
            self.draw_initial(model)
            return

        # Erase previous Pacman positions
        if self._prev_p1_pos[0] >= 0:
            self._restore_cell_area(self._prev_p1_pos[0], self._prev_p1_pos[1], model)
        if self._player_mode == 2 and self._prev_p2_pos[0] >= 0:
            self._restore_cell_area(self._prev_p2_pos[0], self._prev_p2_pos[1], model)

        # Erase previous ghost positions
        for i, pos in enumerate(self._prev_ghost_pos):
            if pos[0] >= 0:
                self._restore_cell_area(pos[0], pos[1], model)

        # Draw Pacmen at new positions
        self._draw_pacman(model.pacman1, _P1)
        if self._player_mode == 2:
            self._draw_pacman(model.pacman2, _P2)

        # Draw ghosts at new positions
        for ghost in model.ghosts:
            self._draw_ghost(ghost)

        # Update HUD - only redraw changed portions
        if model.pacman1.score != self._prev_p1_score:
            self._draw_hud_p1_score(model.pacman1.score)
            self._prev_p1_score = model.pacman1.score

        if self._player_mode == 2 and model.pacman2.score != self._prev_p2_score:
            self._draw_hud_p2_score(model.pacman2.score)
            self._prev_p2_score = model.pacman2.score

        if model.lives != self._prev_lives:
            self._draw_hud_lives(model)
            self._prev_lives = model.lives

        # Save current positions for next frame
        self._prev_p1_pos = (int(model.pacman1.x), int(model.pacman1.y))
        if self._player_mode == 2:
            self._prev_p2_pos = (int(model.pacman2.x), int(model.pacman2.y))
        for i, ghost in enumerate(model.ghosts):
            self._prev_ghost_pos[i] = (int(ghost.x), int(ghost.y))

    def _restore_cell_area(self, gx, gy, model):
        """Restore a cell area to its proper state (background, dot, or pellet)."""
        # Erase the 4x4 area
        self._erase_cell(gx, gy)

        # Restore dot if present
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            if model.dots[gy][gx]:
                self._draw_dot(gx, gy)
            if (gx, gy) in model.pellets:
                self._draw_pellet(gx, gy)

    def draw_game_over(self, model):
        """Draw game over screen."""
        # Dim background
        for y in range(HUD_HEIGHT, HEIGHT):
            for x in range(WIDTH):
                if x % 2 == y % 2:
                    self._bitmap[x, y] = _BG

        # Game over text
        text = "GAME OVER"
        tx = (WIDTH - text_width_big(text)) // 2
        draw_big_text(self._bitmap, text, tx, 25, _GHOST_RED)

        # Final scores
        draw_tiny_text(self._bitmap, f"P1:{model.pacman1.score}", 20, 42, _P1)
        draw_tiny_text(self._bitmap, f"P2:{model.pacman2.score}", 75, 42, _P2)

    def draw_level_complete(self, level):
        """Flash screen for level complete."""
        # Flash walls white briefly
        pass  # TODO: Implement if needed

    def _play_preloaded(self, wav_file, sfx, interrupt=True):
        """Play a preloaded sound by recreating WaveFile after seek."""
        if sfx is None or self._audio is None:
            return
        try:
            # Skip if already playing and we don't want to interrupt
            if not interrupt and self._audio.is_playing:
                return
            if self._audio.is_playing:
                self._audio.stop()
            wav_file.seek(0)
            from audiocore import WaveFile
            new_sfx = WaveFile(wav_file)
            self._audio._audio.play(new_sfx)
        except Exception as e:
            print(f"[PACMAN] Play error: {e}")

    def play_dot_sfx(self):
        """Play dot eaten sound - skip if already playing to avoid glitches."""
        self._play_preloaded(self._wav_dot_f, self._sfx_dot, interrupt=False)

    def play_pellet_sfx(self):
        """Play power pellet sound (non-blocking, preloaded)."""
        self._play_preloaded(self._wav_power_f, self._sfx_power)

    def play_death_sfx(self):
        """Play death sound (non-blocking, preloaded)."""
        self._play_preloaded(self._wav_death_f, self._sfx_death)

    def play_ghost_sfx(self):
        """Play ghost eaten sound (non-blocking, preloaded)."""
        self._play_preloaded(self._wav_ghost_f, self._sfx_ghost)

    def cleanup(self):
        """Clean up resources - close WAV file handles."""
        for attr in ['_wav_dot_f', '_wav_death_f', '_wav_ghost_f', '_wav_power_f']:
            try:
                fh = getattr(self, attr, None)
                if fh:
                    fh.close()
            except:
                pass
