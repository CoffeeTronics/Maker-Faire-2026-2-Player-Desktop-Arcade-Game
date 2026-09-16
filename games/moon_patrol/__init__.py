# Moon Patrol - 2-Player Game for 128x64 RGB Matrix
# ==================================================
# P1 (Buggy): Drives across moon, jumps craters, shoots at UFO
# P2 (UFO): Flies overhead, drops bombs on buggy
#
# Controls:
# - P1 Joystick Left/Right: Move buggy
# - P1 Joystick Up / Button A: Jump
# - P1 Button B: Shoot
# - P2 Joystick: Move UFO (4-way)
# - P2 Button A or B: Drop bomb
# - Admin Select (C): Switch game

import time
import gc

from base_game import BaseGame
from games.moon_patrol.model import MoonPatrolModel, InputState
from games.moon_patrol.view import MoonPatrolView

STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAMEOVER = 2


class MoonPatrolGame(BaseGame):

    NAME = "Moon Patrol"
    HIGH_SCORE_SLOT = 3

    def setup(self):
        gc.collect()
        print(f"Moon Patrol setup start RAM: {gc.mem_free()}")

        self._input = InputState()
        gc.collect()

        self.model = MoonPatrolModel()
        gc.collect()
        print(f"After model RAM: {gc.mem_free()}")

        self.view = MoonPatrolView(self.display.display, self.audio)
        gc.collect()
        print(f"After view RAM: {gc.mem_free()}")

        self._state = STATE_MENU
        self._gameover_time = 0
        self._frame = 0

        # Get P2 controls reference
        self._p2 = self.buttons._controls.p2
        # Get admin controls for 1P/2P buttons
        self._admin = self.buttons._controls.admin

        gc.collect()
        print(f"Moon Patrol setup done RAM: {gc.mem_free()}")

    def run(self):
        while True:
            self.buttons.update()

            # Check for game switch (Button C / Select)
            if self.buttons.c_fell:
                print("Button C pressed - switching game")
                return "switch"

            self._read_inputs()

            if self._state == STATE_MENU:
                self.view.blink_start_prompt()
                # Debug: print admin button states every 30 frames
                if self._frame % 30 == 0:
                    print(f"Menu: 1P={self._admin.one_player_fell} 2P={self._admin.two_player_fell}")
                # Select 1-Player mode
                if self._admin.one_player_fell:
                    print("1-Player button pressed")
                    self.view.set_player_mode(1)
                    time.sleep(0.1)
                    continue
                # Select 2-Player mode
                if self._admin.two_player_fell:
                    print("2-Player button pressed")
                    self.view.set_player_mode(2)
                    time.sleep(0.1)
                    continue
                # Start button only starts the game
                if self._admin.start_fell:
                    player_mode = self.view.get_player_mode()
                    print(f"Starting game - {player_mode} player")
                    self.model.reset()
                    self.model.set_player_mode(player_mode)
                    self.view.hide_start_menu()
                    self._state = STATE_PLAYING
                    self._frame = 0
                    time.sleep(0.1)
                    continue
                time.sleep(0.016)
                continue

            if self._state == STATE_GAMEOVER:
                elapsed = time.monotonic() - self._gameover_time
                audio_done = not self.view.is_audio_playing()
                if elapsed >= 3.0 and audio_done:
                    self.view.stop_audio()
                    return "gameover"
                time.sleep(0.016)
                continue

            # Playing state
            events = self.model.update(self._input)

            for event in events:
                if event == "jump":
                    self.view.play_sfx("jump")
                elif event == "shoot":
                    self.view.play_sfx("shoot")
                elif event == "bomb_drop":
                    self.view.play_sfx("bomb")
                elif event in ("ufo_hit", "buggy_hit", "crater_fall"):
                    self.view.play_sfx("hit")
                elif event in ("ufo_destroyed", "buggy_destroyed"):
                    self.view.play_sfx("explosion")
                elif event == "gameover":
                    self.view.play_sfx("explosion")
                    self.view.show_game_over(self.model.winner)
                    self._state = STATE_GAMEOVER
                    self._gameover_time = time.monotonic()
                    self._save_score()
                elif event == "victory":
                    self.view.play_sfx("explosion")
                    self.view.show_game_over(self.model.winner)
                    self._state = STATE_GAMEOVER
                    self._gameover_time = time.monotonic()
                    self._save_score()

            if self._state == STATE_PLAYING:
                self.view.draw(self.model)

            self._frame += 1
            if self._frame % 90 == 0:
                gc.collect()

            time.sleep(0.016)

    def _read_inputs(self):
        """Map hardware inputs to InputState for both players."""
        # Player 1 (Buggy) - uses main joystick and buttons A/B
        self._input.p1_left = self.joystick.left
        self._input.p1_right = self.joystick.right
        self._input.p1_jump = self.joystick.up or self.buttons.a_pressed
        self._input.p1_shoot = self.buttons.b_pressed

        # Player 2 (UFO) - uses P2 joystick and buttons
        self._input.p2_left = self._p2.left
        self._input.p2_right = self._p2.right
        self._input.p2_up = self._p2.up
        self._input.p2_down = self._p2.down
        self._input.p2_bomb = self._p2.btn1 or self._p2.btn2

    def _save_score(self):
        if self.model.score > self.get_high_score():
            self.set_high_score(self.model.score)

    def cleanup(self):
        if hasattr(self, 'view'):
            self.view.cleanup()
        self.audio.unload_all()
        self.audio.stop()
