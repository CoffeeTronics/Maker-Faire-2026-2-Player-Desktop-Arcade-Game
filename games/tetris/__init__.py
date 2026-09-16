# Tetris Game - Unified Launcher Integration
# For 128x64 RGB Matrix (4 panels, rotated 90°) with Joystick and Buttons
# Horizontal Tetris: pieces move left to right
#
# Controls:
# - Joystick Up/Down: Move piece up/down
# - Joystick Right: Soft drop (faster move right)
# - Button A: Rotate piece
# - Button B: Hard drop (instant move to right edge)
# - Button D: Game switch

import time
import gc

from base_game import BaseGame
from games.tetris.model import TetrisModel, InputState
from games.tetris.view import TetrisView

STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAMEOVER = 2


class TetrisGame(BaseGame):

    NAME = "Tetris"
    HIGH_SCORE_SLOT = 1  # Reusing Space Impact's slot

    def setup(self):
        gc.collect()
        print(f"Tetris setup start RAM: {gc.mem_free()}")

        self._input_state = InputState()

        gc.collect()
        self.model = TetrisModel()
        gc.collect()
        print(f"After model RAM: {gc.mem_free()}")

        self.view = TetrisView(self.display.display, self.audio)
        gc.collect()
        print(f"After view RAM: {gc.mem_free()}")

        self._state = STATE_MENU
        self._gameover_time = 0
        self._frame = 0

        self.model.high_score = self.get_high_score()

        gc.collect()
        print(f"Tetris setup done RAM: {gc.mem_free()}")

    def run(self):
        while True:
            self.buttons.update()

            # Check for game switch (Button D)
            if self.buttons.c_fell:  # Select = switch game
                print("Button C pressed")
                self._save_score()
                return "switch"

            self._read_inputs()

            if self._state == STATE_MENU:
                self.view.blink_start_prompt()
                # Start on button A or B
                if self.buttons.a_fell or self.buttons.b_fell or self.buttons.d_fell:  # Start button
                    print("Button D pressed")
                    self.model.reset()
                    self.view.hide_start_menu()
                    self._state = STATE_PLAYING
                    self._frame = 0
                    time.sleep(0.1)
                    continue
                time.sleep(0.033)
                continue

            if self._state == STATE_GAMEOVER:
                elapsed = time.monotonic() - self._gameover_time
                audio_done = not self.view.is_audio_playing()
                if elapsed >= 2.5 and audio_done:
                    self.view.stop_audio()
                    return "gameover"
                time.sleep(0.033)
                continue

            # Game playing state
            events = self.model.update(self._input_state)

            for event in events:
                if event == "rotate":
                    self.view.play_sfx("rotate")
                elif event == "land":
                    self.view.play_sfx("land")
                elif event == "drop":
                    self.view.play_sfx("drop")
                elif event.startswith("clear_"):
                    self.view.play_sfx("clear")
                elif event == "gameover":
                    self.view.play_sfx("gameover")
                    self.view.show_game_over()
                    self._state = STATE_GAMEOVER
                    self._gameover_time = time.monotonic()
                    self._save_score()

            if self._state == STATE_PLAYING:
                self.view.draw(self.model)

            self._frame += 1
            if self._frame % 90 == 0:
                gc.collect()

            time.sleep(0.033)

    def _read_inputs(self):
        """Read joystick and buttons into InputState."""
        self._input_state.up = self.joystick.up
        self._input_state.down = self.joystick.down
        self._input_state.right = self.joystick.right  # Soft drop (faster right)
        self._input_state.rotate = self.buttons.a_pressed
        self._input_state.drop = self.buttons.b_pressed

    def _save_score(self):
        if self.model.score > self.get_high_score():
            self.set_high_score(self.model.score)

    def cleanup(self):
        if hasattr(self, 'view'):
            self.view.cleanup()
        self.audio.unload_all()
        self.audio.stop()
