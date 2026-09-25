# Pacman Game - Controller/Launcher
# 2-player cooperative Pacman for 128x64 RGB Matrix

import time
import gc

from base_game import BaseGame
from joystick import UP, DOWN, LEFT, RIGHT
from games.pacman.model import PacmanModel, UP as M_UP, DOWN as M_DOWN, LEFT as M_LEFT, RIGHT as M_RIGHT
from games.pacman.view import PacmanView

# Debug flag
DEBUG = True

# Game states
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAMEOVER = 2
STATE_LEVEL_COMPLETE = 3
STATE_NAMES = ["MENU", "PLAYING", "GAMEOVER", "LEVEL_COMPLETE"]

# Direction mapping from joystick to model
DIR_MAP = {
    UP: M_UP,
    DOWN: M_DOWN,
    LEFT: M_LEFT,
    RIGHT: M_RIGHT,
}


class PacmanGame(BaseGame):
    """2-Player Pacman game controller."""

    NAME = "Pacman"
    HIGH_SCORE_SLOT = 4  # Unique slot for Pacman

    def setup(self):
        if DEBUG:
            print(f"[PACMAN] Setup start, RAM: {gc.mem_free()}")

        high_score = self.get_high_score()
        if DEBUG:
            print(f"[PACMAN] Creating model...")
        self.model = PacmanModel(high_score=high_score)

        if DEBUG:
            print(f"[PACMAN] Creating view, RAM: {gc.mem_free()}")
        self.view = PacmanView(self.display.display, self.audio)

        self._state = STATE_MENU
        self._last_time = time.monotonic()
        self._death_pause = 0.0

        # Frame timing debug
        self._frame_count = 0
        self._fps_time = time.monotonic()

        # Get P2 and admin controls
        self._p2 = getattr(self.buttons._controls, 'p2', None)
        self._admin = getattr(self.buttons._controls, 'admin', None)

        if DEBUG:
            print(f"[PACMAN] Drawing splash, RAM: {gc.mem_free()}")
        # Show splash screen
        self.view.draw_splash(self.model.high_score)

        if DEBUG:
            print(f"[PACMAN] Setup complete, RAM: {gc.mem_free()}")

    def run(self):
        if DEBUG:
            print(f"[PACMAN] Entering run loop, state={STATE_NAMES[self._state]}")

        while True:
            loop_start = time.monotonic()
            self.buttons.update()
            now = time.monotonic()
            dt = now - self._last_time
            self._last_time = now

            # Check for game switch (Button C = Select)
            if self.buttons.c_fell:
                self._save_score()
                return "switch"

            if self._state == STATE_MENU:
                self._handle_menu()

            elif self._state == STATE_PLAYING:
                self._handle_playing(dt)

            elif self._state == STATE_GAMEOVER:
                self._handle_gameover()

            elif self._state == STATE_LEVEL_COMPLETE:
                self._handle_level_complete()

            # FPS tracking
            self._frame_count += 1
            if DEBUG and self._frame_count % 60 == 0:
                fps_elapsed = now - self._fps_time
                fps = 60.0 / fps_elapsed if fps_elapsed > 0 else 0
                loop_time = (time.monotonic() - loop_start) * 1000
                print(f"[PACMAN] State={STATE_NAMES[self._state]} FPS={fps:.1f} loop={loop_time:.1f}ms RAM={gc.mem_free()}")
                self._fps_time = now

            time.sleep(0.016)  # ~60 FPS input polling

    def _handle_menu(self):
        """Handle menu state - blink prompt, wait for start."""
        self.view.blink_start_prompt()

        # Select 1-Player mode
        if self._admin and self._admin.one_player_fell:
            if DEBUG:
                print("[PACMAN] 1-Player button pressed")
            self.view.set_player_mode(1)
            time.sleep(0.1)
            return

        # Select 2-Player mode
        if self._admin and self._admin.two_player_fell:
            if DEBUG:
                print("[PACMAN] 2-Player button pressed")
            self.view.set_player_mode(2)
            time.sleep(0.1)
            return

        # Start button starts the game
        if self._admin and self._admin.start_fell:
            player_mode = self.view.get_player_mode()
            if DEBUG:
                print(f"[PACMAN] Starting game - {player_mode} player")
            self._state = STATE_PLAYING
            self.model.reset()
            self.model.set_player_mode(player_mode)
            if DEBUG:
                print(f"[PACMAN] Drawing initial frame...")
            self.view.draw_initial(self.model)
            if DEBUG:
                print(f"[PACMAN] Initial draw complete, entering PLAYING state")
            self._last_time = time.monotonic()

    def _handle_playing(self, dt):
        """Handle playing state - game loop."""
        # Handle death pause
        if self._death_pause > 0:
            self._death_pause -= dt
            if self._death_pause <= 0:
                self.view.draw_initial(self.model)
            return

        # Read P1 input
        p1_dir = None
        p1_joy = self.joystick.get_direction()
        if p1_joy in DIR_MAP:
            p1_dir = DIR_MAP[p1_joy]

        # Read P2 input
        p2_dir = None
        if self._p2:
            p2_joy = self._p2.get_direction()
            if p2_joy in DIR_MAP:
                p2_dir = DIR_MAP[p2_joy]

        # Update game model
        events = self.model.update(dt, p1_dir, p2_dir)

        # Handle events
        for event in events:
            event_type = event[0]

            if event_type == 'dot':
                self.view.play_dot_sfx()

            elif event_type == 'pellet':
                self.view.play_pellet_sfx()

            elif event_type == 'ate_ghost':
                self.view.play_ghost_sfx()

            elif event_type == 'life_lost':
                self.view.play_death_sfx()
                self._death_pause = 1.5  # Pause for 1.5 seconds

            elif event_type == 'death':
                self.view.play_death_sfx()
                self._death_pause = 1.5

            elif event_type == 'game_over':
                self._state = STATE_GAMEOVER
                self._save_score()
                self.view.draw_game_over(self.model)
                return

            elif event_type == 'level_complete':
                self._state = STATE_LEVEL_COMPLETE
                self.view.draw_level_complete(self.model.level)
                self._level_pause = 2.0
                return

        # Render
        self.view.render(self.model)

    def _handle_gameover(self):
        """Handle game over state - wait for restart."""
        # Press start to return to menu
        if self.buttons.d_fell:
            self._state = STATE_MENU
            self.model.reset()
            self.view.draw_splash(self.model.high_score)

    def _handle_level_complete(self):
        """Handle level complete state."""
        self._level_pause -= 0.016
        if self._level_pause <= 0:
            self._state = STATE_PLAYING
            self.view.draw_initial(self.model)

    def _save_score(self):
        """Save high score if beaten."""
        total_score = self.model.pacman1.score + self.model.pacman2.score
        if total_score > self.get_high_score():
            self.set_high_score(total_score)

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'view'):
            self.view.cleanup()
        self.audio.unload_all()
        self.audio.stop()
