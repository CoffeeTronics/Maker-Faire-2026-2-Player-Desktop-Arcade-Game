# Snake Game - Unified Launcher Integration
# For 128x64 RGB Matrix (4 panels, rotated 90°) with Joystick and Buttons

import time

from base_game import BaseGame
from joystick import UP, DOWN, LEFT, RIGHT
from games.snake.model import SnakeModel
from games.snake.view import SnakeView


class SnakeGame(BaseGame):

    NAME = "Snake"
    HIGH_SCORE_SLOT = 0

    def setup(self):
        high_score = self.get_high_score()
        self.model = SnakeModel(high_score=high_score)
        self.view = SnakeView(self.display.display, self.audio)

        self._last_tick = 0.0
        self._in_menu = True  # Start in menu state (splash shown automatically)
        self._wait_for_input = False  # Wait for input after losing a life

    def _get_tick_rate(self):
        """Calculate tick rate based on score - faster as score increases."""
        BASE_TICK = 0.12    # Starting speed
        MIN_TICK = 0.05     # Fastest speed
        # Decrease tick time by 0.005s per point, down to MIN_TICK
        tick = BASE_TICK - (self.model.score * 0.005)
        return max(MIN_TICK, tick)

    def run(self):
        while True:
            self.buttons.update()

            # Check for game switch (Button D)
            if self.buttons.c_fell:  # Select = switch game
                print("Button C pressed")
                self._save_score()
                return "switch"

            # Menu state: wait for joystick to start
            if self._in_menu:
                self.view.blink_start_prompt()
                direction = self.joystick.get_direction()
                if direction is not None or self.buttons.d_fell:  # Start button
                    print("Button D pressed")
                    self._in_menu = False
                    self.view.hide_start_menu()
                    self.view.update_score(self.model.score)
                    self.view.update_high_score(self.model.high_score)
                    self.view.update_lives(self.model.lives)
                    self.view.render(self.model)
                    self._last_tick = time.monotonic()
                    time.sleep(0.2)
                    continue
                time.sleep(0.033)
                continue

            # Wait for player input after losing a life
            if self._wait_for_input:
                direction = self.joystick.get_direction()
                if direction is not None or self.buttons.d_fell:  # Start button
                    print("Button D pressed")
                    self._wait_for_input = False
                    self._last_tick = time.monotonic()
                time.sleep(0.033)
                continue

            # Poll joystick for direction
            self._poll_joystick()

            # Button A toggles demo mode
            if self.buttons.a_fell:
                self.model.toggle_demo()

            now = time.monotonic()
            if now - self._last_tick >= self._get_tick_rate():
                self._last_tick = now
                event = self.model.step()

                if event == "ate_food":
                    self.view.update_score(self.model.score)
                    self.view.update_high_score(self.model.high_score)
                    if not self.model.demo_mode:
                        self.view.play_food_sfx()
                        self._save_score()

                elif event == "hit":
                    # Lost a life but not game over
                    self.view.flash_red()
                    if not self.model.demo_mode:
                        self.view.play_life_lost_sfx()
                    time.sleep(1.0)
                    self.view.update_lives(self.model.lives)
                    self.view.render(self.model)
                    self._wait_for_input = True

                elif event == "game_over":
                    if not self.model.demo_mode:
                        self.view.play_gameover_sfx()
                    self.view.flash_red()
                    self.view.show_game_over(self.model.score, self.model.high_score)
                    self._save_score()
                    return "gameover"

                self.view.render(self.model)

            time.sleep(0.005)

    def _poll_joystick(self):
        """Read joystick and set snake direction."""
        if self.model.demo_mode:
            return

        direction = self.joystick.get_direction()
        if direction is not None or self.buttons.d_fell:  # Start button
                    print("Button D pressed")
            self.model.set_direction(direction)

    def _save_score(self):
        if self.model.score > self.get_high_score():
            self.set_high_score(self.model.score)

    def cleanup(self):
        if hasattr(self, "view"):
            self.view.cleanup()
        self.audio.unload_all()
        self.audio.stop()
