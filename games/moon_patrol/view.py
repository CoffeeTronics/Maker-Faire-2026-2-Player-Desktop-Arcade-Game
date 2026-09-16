# moon_patrol/view.py - VIEW (MVC pattern)
# 2-Player Moon Patrol for 128x64 RGB Matrix
# Optimized for minimal per-frame pixel writes

import displayio
import sys
sys.path.insert(0, "/API")
from matrix_display import FlippedBitmap

from games.moon_patrol.model import (
    DISPLAY_WIDTH, DISPLAY_HEIGHT, HUD_HEIGHT,
    UFO_ZONE_TOP, UFO_ZONE_BOTTOM, GROUND_Y, TERRAIN_Y,
    BUGGY_WIDTH, BUGGY_HEIGHT, UFO_WIDTH, UFO_HEIGHT,
    BULLET_WIDTH, BULLET_HEIGHT, BOMB_WIDTH, BOMB_HEIGHT,
    BUGGY_INITIAL_LIVES, UFO_INITIAL_HP
)
from games.view_utils import draw_tiny_text, text_width_tiny, clear_bitmap

# Palette indices
_BG = 0
_WHITE = 1
_CYAN = 2
_RED = 3
_YELLOW = 4
_ORANGE = 5
_BROWN = 6
_GREEN = 7
_GRAY = 8

PALETTE_SIZE = 9

# Buggy sprite (12x8 pixels)
BUGGY_SPRITE = [
    0b000111111000,
    0b001111111100,
    0b011111111110,
    0b111111111111,
    0b111111111111,
    0b110011001111,
    0b011111111110,
    0b001100110010,
]

BUGGY_JUMPING = [
    0b000111111000,
    0b001111111100,
    0b011111111110,
    0b111111111111,
    0b111111111111,
    0b110011001111,
    0b011111111110,
    0b000110011000,
]

# UFO sprite (10x6 pixels)
UFO_SPRITE = [
    0b0001111000,
    0b0111111110,
    0b1111111111,
    0b1111111111,
    0b0111111110,
    0b0001111000,
]

UFO_SPRITE_ALT = [
    0b0001111000,
    0b0111001110,
    0b1111111111,
    0b1111111111,
    0b0111001110,
    0b0001111000,
]

# Bullet sprite (2x3 pixels)
BULLET_SPRITE = [
    0b11,
    0b11,
    0b11,
]

# Bomb sprite (4x4 pixels)
BOMB_SPRITE = [
    0b0110,
    0b1111,
    0b1111,
    0b0110,
]

# Sound effect paths
_SOUND_PATHS = {
    "jump": "/AudioFiles/210.wav",
    "shoot": "/AudioFiles/210.wav",
    "bomb": "/AudioFiles/210.wav",
    "explosion": "/AudioFiles/210.wav",
    "hit": "/AudioFiles/210.wav",
}


class MoonPatrolView:
    """Rendering for 128x64 Moon Patrol - optimized dirty-rect rendering."""

    def __init__(self, display, audio):
        self._display = display
        self._audio = audio
        self._game_initialized = False

        # Create bitmap with FlippedBitmap wrapper
        self._raw_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, PALETTE_SIZE)
        self._bitmap = FlippedBitmap(self._raw_bitmap)
        self._palette = displayio.Palette(PALETTE_SIZE)
        self._init_palette()

        tg = displayio.TileGrid(self._raw_bitmap, pixel_shader=self._palette)
        self._root = displayio.Group()
        self._root.append(tg)
        display.root_group = self._root

        # Previous state for dirty updates (reuse tuples, don't allocate)
        self._prev_buggy_x = -100
        self._prev_buggy_y = -100
        self._prev_buggy_visible = True
        self._prev_buggy_jumping = False
        self._prev_ufo_x = -100
        self._prev_ufo_y = -100
        self._prev_ufo_anim = False
        self._prev_lives = -1
        self._prev_hp = -1
        self._prev_score = -1

        # Cached bullet/bomb positions (fixed size arrays)
        self._prev_bullet_pos = [(-100, -100, False) for _ in range(4)]
        self._prev_bomb_pos = [(-100, -100, False) for _ in range(3)]
        self._prev_exp_state = [(0, 0, -1) for _ in range(6)]  # x, y, frame

        # Terrain cache
        self._terrain_drawn = False
        self._prev_terrain_offset = -1
        # Cache previous crater screen positions (x, width) - max 10
        self._prev_craters = [(-200, 0)] * 10
        self._prev_crater_count = 0

        # Splash screen
        self._in_splash = True
        self._blink_counter = 0
        self._player_mode = 2  # 1 or 2 player
        self._show_splash()

    def _init_palette(self):
        self._palette[_BG] = 0x000000
        self._palette[_WHITE] = 0xFFFFFF
        self._palette[_CYAN] = 0x00FFFF
        self._palette[_RED] = 0xFF0044
        self._palette[_YELLOW] = 0xFFFF00
        self._palette[_ORANGE] = 0xFF6600
        self._palette[_BROWN] = 0x442200
        self._palette[_GREEN] = 0x00FF00
        self._palette[_GRAY] = 0x666666

    def _show_splash(self):
        clear_bitmap(self._bitmap, _BG)
        title = "MOON PATROL"
        tw = text_width_tiny(title)
        draw_tiny_text(self._bitmap, title, (DISPLAY_WIDTH - tw) // 2, 20, _CYAN)
        sub = "2 PLAYER"
        sw = text_width_tiny(sub)
        draw_tiny_text(self._bitmap, sub, (DISPLAY_WIDTH - sw) // 2, 30, _WHITE)
        prompt = "PRESS START"
        pw = text_width_tiny(prompt)
        draw_tiny_text(self._bitmap, prompt, (DISPLAY_WIDTH - pw) // 2, 45, _YELLOW)

    def blink_start_prompt(self):
        if not self._in_splash:
            return
        self._blink_counter += 1
        if self._blink_counter >= 30:
            self._blink_counter = 0

        prompt = "PRESS START"
        pw = text_width_tiny(prompt)
        x = (DISPLAY_WIDTH - pw) // 2
        y = 45

        if self._blink_counter >= 15:
            for dy in range(5):
                for dx in range(pw + 1):
                    px, py = x + dx, y + dy
                    if 0 <= px < DISPLAY_WIDTH and 0 <= py < DISPLAY_HEIGHT:
                        self._bitmap[px, py] = _BG
        else:
            draw_tiny_text(self._bitmap, prompt, x, y, _YELLOW)

    def set_player_mode(self, mode):
        """Set player mode (1 or 2) on splash screen."""
        if not self._in_splash:
            return
        if mode == self._player_mode:
            return  # No change needed
        self._player_mode = mode
        # Clear the player mode text area
        sub_y = 30
        for dy in range(5):
            for dx in range(50):
                px = 39 + dx  # roughly centered area
                if 0 <= px < DISPLAY_WIDTH:
                    self._bitmap[px, sub_y + dy] = _BG
        # Draw new text
        sub = f"{self._player_mode} PLAYER"
        sw = text_width_tiny(sub)
        draw_tiny_text(self._bitmap, sub, (DISPLAY_WIDTH - sw) // 2, sub_y, _WHITE)

    def get_player_mode(self):
        """Return current player mode (1 or 2)."""
        return self._player_mode

    def hide_start_menu(self):
        self._in_splash = False
        self._game_initialized = True
        self._terrain_drawn = False
        self._prev_terrain_offset = -1
        self._prev_lives = -1
        self._prev_hp = -1
        self._prev_score = -1
        self._preload_sounds()

    def _preload_sounds(self):
        if self._audio is None:
            return
        for name, path in _SOUND_PATHS.items():
            try:
                self._audio.preload_wav(name, path)
            except Exception as e:
                print(f"Failed to preload {name}: {e}")

    def _draw_sprite(self, data, x, y, color_idx, width):
        """Draw sprite from bit pattern."""
        ix, iy = int(x), int(y)
        for row_idx, row in enumerate(data):
            for col in range(width):
                px = ix + col
                py = iy + row_idx
                if 0 <= px < DISPLAY_WIDTH and 0 <= py < DISPLAY_HEIGHT:
                    if row & (1 << (width - 1 - col)):
                        self._bitmap[px, py] = color_idx

    def _erase_rect(self, x, y, w, h):
        """Erase rectangle to background."""
        ix, iy = int(x), int(y)
        for dy in range(h):
            for dx in range(w):
                px, py = ix + dx, iy + dy
                if 0 <= px < DISPLAY_WIDTH and 0 <= py < DISPLAY_HEIGHT:
                    self._bitmap[px, py] = _BG

    def _draw_initial_frame(self, model):
        """Draw complete initial frame - only called once."""
        clear_bitmap(self._bitmap, _BG)

        # Draw terrain with craters
        craters = model.terrain.get_visible_craters()

        # First draw all ground
        for x in range(DISPLAY_WIDTH):
            for ty in range(TERRAIN_Y, TERRAIN_Y + 2):
                self._bitmap[x, ty] = _GRAY
            for y in range(TERRAIN_Y + 2, DISPLAY_HEIGHT):
                self._bitmap[x, y] = _BROWN

        # Then cut semi-circular crater holes
        crater_count = 0
        for cx, cw in craters:
            for x in range(int(cx), int(cx + cw) + 1):
                if 0 <= x < DISPLAY_WIDTH:
                    depth = self._calc_crater_depth(x, cx, cw)
                    if depth > 0:
                        self._draw_terrain_column(x, depth)
            if crater_count < len(self._prev_craters):
                self._prev_craters[crater_count] = (cx, cw)
                crater_count += 1
        self._prev_crater_count = crater_count

        # Draw static HUD labels
        draw_tiny_text(self._bitmap, "P1:", 2, 1, _GREEN)
        draw_tiny_text(self._bitmap, "P2:", 90, 1, _GREEN)

        self._terrain_drawn = True
        self._prev_terrain_offset = int(model.terrain.offset)

    def _calc_crater_depth(self, x, crater_x, crater_w):
        """Calculate semi-circle depth at column x within crater."""
        radius = crater_w / 2.0
        center = crater_x + radius
        d = abs(x - center)
        if d >= radius:
            return 0
        max_depth = min(6, int(radius))
        depth_ratio = (1.0 - (d * d) / (radius * radius)) ** 0.5
        return max(1, int(depth_ratio * max_depth))

    def _draw_terrain_column(self, x, crater_depth=0):
        """Draw terrain column with semi-circular crater depth."""
        if not (0 <= x < DISPLAY_WIDTH):
            return
        if crater_depth > 0:
            # Crater: no surface, just the bowl
            self._bitmap[x, TERRAIN_Y] = _BG
            self._bitmap[x, TERRAIN_Y + 1] = _BG
            for y in range(TERRAIN_Y + 2, TERRAIN_Y + 2 + crater_depth):
                if y < DISPLAY_HEIGHT:
                    self._bitmap[x, y] = _BG
            for y in range(TERRAIN_Y + 2 + crater_depth, DISPLAY_HEIGHT):
                self._bitmap[x, y] = _BROWN
        else:
            self._bitmap[x, TERRAIN_Y] = _GRAY
            self._bitmap[x, TERRAIN_Y + 1] = _GRAY
            for y in range(TERRAIN_Y + 2, DISPLAY_HEIGHT):
                self._bitmap[x, y] = _BROWN

    def _update_terrain_scroll(self, model):
        """Update terrain for scrolling - only update columns that changed."""
        curr_offset = int(model.terrain.offset)
        if curr_offset == self._prev_terrain_offset:
            return

        self._prev_terrain_offset = curr_offset
        craters = model.terrain.get_visible_craters()

        # Build dict of crater columns with depth (previous)
        prev_cols = {}
        for i in range(self._prev_crater_count):
            px, pw = self._prev_craters[i]
            for x in range(int(px), int(px + pw) + 1):
                if 0 <= x < DISPLAY_WIDTH:
                    prev_cols[x] = self._calc_crater_depth(x, px, pw)

        # Build dict of crater columns with depth (current)
        curr_cols = {}
        crater_count = 0
        for cx, cw in craters:
            for x in range(int(cx), int(cx + cw) + 1):
                if 0 <= x < DISPLAY_WIDTH:
                    curr_cols[x] = self._calc_crater_depth(x, cx, cw)
            if crater_count < len(self._prev_craters):
                self._prev_craters[crater_count] = (cx, cw)
                crater_count += 1
        self._prev_crater_count = crater_count

        # Only update columns that changed
        all_cols = set(prev_cols.keys()) | set(curr_cols.keys())
        for x in all_cols:
            prev_depth = prev_cols.get(x, 0)
            curr_depth = curr_cols.get(x, 0)
            if prev_depth != curr_depth:
                self._draw_terrain_column(x, curr_depth)

    def _update_hud(self, model):
        """Update only changed HUD elements."""
        # P1 lives - only redraw if changed
        if model.buggy.lives != self._prev_lives:
            # Clear lives area
            for i in range(BUGGY_INITIAL_LIVES):
                for dx in range(3):
                    for dy in range(3):
                        self._bitmap[16 + i * 5 + dx, 2 + dy] = _BG
            # Draw current lives
            for i in range(model.buggy.lives):
                for dx in range(3):
                    for dy in range(3):
                        self._bitmap[16 + i * 5 + dx, 2 + dy] = _CYAN
            self._prev_lives = model.buggy.lives

        # Score - only redraw if changed
        display_score = model.score // 10
        if display_score != self._prev_score:
            # Clear score area
            for dx in range(24):
                for dy in range(5):
                    self._bitmap[55 + dx, 1 + dy] = _BG
            score_str = str(display_score)
            draw_tiny_text(self._bitmap, score_str, 55, 1, _WHITE)
            self._prev_score = display_score

        # P2 HP - only redraw if changed
        if model.ufo.hp != self._prev_hp:
            # Clear HP area
            for i in range(UFO_INITIAL_HP):
                for dx in range(3):
                    for dy in range(3):
                        self._bitmap[104 + i * 5 + dx, 2 + dy] = _BG
            # Draw current HP
            for i in range(model.ufo.hp):
                for dx in range(3):
                    for dy in range(3):
                        self._bitmap[104 + i * 5 + dx, 2 + dy] = _RED
            self._prev_hp = model.ufo.hp

    def draw(self, model):
        """Update display - dirty rectangle rendering."""
        if self._in_splash:
            return

        # First frame - draw everything
        if not self._terrain_drawn:
            self._draw_initial_frame(model)

        # Update scrolling terrain
        self._update_terrain_scroll(model)

        # --- Get current positions ---
        curr_buggy_x = int(model.buggy.x)
        curr_buggy_y = int(model.buggy.y)
        curr_buggy_visible = model.buggy.invincible == 0 or model.buggy.invincible % 6 < 3
        curr_buggy_jumping = not model.buggy.on_ground

        curr_ufo_x = int(model.ufo.x)
        curr_ufo_y = int(model.ufo.y)
        curr_ufo_anim = model.ufo.anim_frame >= 15

        # Check what changed
        buggy_moved = (curr_buggy_x != self._prev_buggy_x or
                       curr_buggy_y != self._prev_buggy_y or
                       curr_buggy_visible != self._prev_buggy_visible or
                       curr_buggy_jumping != self._prev_buggy_jumping)

        ufo_moved = (curr_ufo_x != self._prev_ufo_x or
                     curr_ufo_y != self._prev_ufo_y or
                     curr_ufo_anim != self._prev_ufo_anim)

        # --- Erase only if moved ---

        if buggy_moved and self._prev_buggy_x >= 0:
            self._erase_rect(self._prev_buggy_x, self._prev_buggy_y, BUGGY_WIDTH, BUGGY_HEIGHT)

        if ufo_moved and self._prev_ufo_x >= 0:
            self._erase_rect(self._prev_ufo_x, self._prev_ufo_y, UFO_WIDTH, UFO_HEIGHT)

        # Erase previous bullets (always check - they move every frame)
        for i, (px, py, was_active) in enumerate(self._prev_bullet_pos):
            if was_active:
                self._erase_rect(px, py, BULLET_WIDTH, BULLET_HEIGHT)

        # Erase previous bombs (always check - they move every frame)
        for i, (px, py, was_active) in enumerate(self._prev_bomb_pos):
            if was_active:
                self._erase_rect(px, py, BOMB_WIDTH, BOMB_HEIGHT)

        # Erase previous explosions
        for i, (ex, ey, prev_frame) in enumerate(self._prev_exp_state):
            if prev_frame >= 0:
                r = min(prev_frame + 3, 6)  # Cap erase radius
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        if dx * dx + dy * dy <= r * r:
                            px, py = int(ex) + dx, int(ey) + dy
                            if 0 <= px < DISPLAY_WIDTH and HUD_HEIGHT <= py < DISPLAY_HEIGHT:
                                self._bitmap[px, py] = _BG

        # --- Draw only if moved ---

        if buggy_moved and curr_buggy_visible:
            sprite = BUGGY_JUMPING if curr_buggy_jumping else BUGGY_SPRITE
            self._draw_sprite(sprite, model.buggy.x, model.buggy.y, _CYAN, BUGGY_WIDTH)

        # Store buggy state
        self._prev_buggy_x = curr_buggy_x if curr_buggy_visible else -100
        self._prev_buggy_y = curr_buggy_y if curr_buggy_visible else -100
        self._prev_buggy_visible = curr_buggy_visible
        self._prev_buggy_jumping = curr_buggy_jumping

        if ufo_moved:
            sprite = UFO_SPRITE_ALT if curr_ufo_anim else UFO_SPRITE
            self._draw_sprite(sprite, model.ufo.x, model.ufo.y, _RED, UFO_WIDTH)

        # Store UFO state
        self._prev_ufo_x = curr_ufo_x
        self._prev_ufo_y = curr_ufo_y
        self._prev_ufo_anim = curr_ufo_anim

        # Draw bullets and store positions
        for i, bullet in enumerate(model.bullets):
            if bullet.active:
                self._draw_sprite(BULLET_SPRITE, bullet.x, bullet.y, _YELLOW, BULLET_WIDTH)
                self._prev_bullet_pos[i] = (int(bullet.x), int(bullet.y), True)
            else:
                self._prev_bullet_pos[i] = (-100, -100, False)

        # Draw bombs and store positions
        for i, bomb in enumerate(model.bombs):
            if bomb.active:
                self._draw_sprite(BOMB_SPRITE, bomb.x, bomb.y, _ORANGE, BOMB_WIDTH)
                self._prev_bomb_pos[i] = (int(bomb.x), int(bomb.y), True)
            else:
                self._prev_bomb_pos[i] = (-100, -100, False)

        # Draw explosions
        for i, exp in enumerate(model.explosions):
            if exp.active:
                r = min(exp.frame + 2, 6)  # Cap radius at 6 (12px diameter)
                cx, cy = int(exp.x), int(exp.y)
                color = _YELLOW if (exp.frame % 2 == 0) else _ORANGE
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        if dx * dx + dy * dy <= r * r:
                            px, py = cx + dx, cy + dy
                            if 0 <= px < DISPLAY_WIDTH and HUD_HEIGHT <= py < DISPLAY_HEIGHT:
                                self._bitmap[px, py] = color
                self._prev_exp_state[i] = (exp.x, exp.y, exp.frame)
            else:
                self._prev_exp_state[i] = (0, 0, -1)

        # Update HUD (only changed parts)
        self._update_hud(model)

    def show_game_over(self, winner):
        """Show game over screen."""
        clear_bitmap(self._bitmap, _BG)
        if winner == "buggy":
            line1 = "BUGGY"
            line2 = "WINS!"
            color = _CYAN
        else:
            line1 = "UFO"
            line2 = "WINS!"
            color = _RED

        w1 = text_width_tiny(line1)
        w2 = text_width_tiny(line2)
        draw_tiny_text(self._bitmap, line1, (DISPLAY_WIDTH - w1) // 2, 24, color)
        draw_tiny_text(self._bitmap, line2, (DISPLAY_WIDTH - w2) // 2, 34, color)

    def play_sfx(self, name):
        if self._audio:
            try:
                self._audio.play_preloaded(name)
            except:
                pass

    def stop_audio(self):
        if self._audio:
            self._audio.stop()

    def is_audio_playing(self):
        if self._audio:
            return self._audio.is_playing
        return False

    def cleanup(self):
        pass
