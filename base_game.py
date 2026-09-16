"""
base_game.py - Base class for all games
=======================================

All games must inherit from BaseGame and implement the required methods.
See games/GAME_README.md for detailed instructions on creating new games.
"""


class BaseGame:
    """Abstract base class that all games must inherit from.

    Games receive shared hardware resources in the constructor and must
    implement setup(), run(), and cleanup() methods.
    """

    NAME = "Unnamed Game"
    HIGH_SCORE_SLOT = -1  # Must be overridden with unique slot number (0-29)
    GAME_OVER_IMAGE = None  # Path to game-over BMP, e.g. "/Sprites/Game_Over_X.bmp"
    GAME_OVER_SOUND = None  # Path to game-over WAV, e.g. "/AudioFiles/gameover.wav"

    def __init__(self, display, joystick, buttons, audio, high_score_manager):
        """Initialize with shared hardware resources.

        Parameters
        ----------
        display : MatrixDisplay
            Shared RGB Matrix display instance (64x32)
        joystick : Joystick
            Shared 4-direction joystick instance
        buttons : ButtonSet
            Shared 4-button arcade button set (A, B, C, D)
        audio : AudioOutput
            Shared audio output instance
        high_score_manager : HighScoreManager
            Shared high score persistence manager
        """
        self.display = display
        self.joystick = joystick
        self.buttons = buttons
        self.audio = audio
        self.high_scores = high_score_manager

    def setup(self):
        """Initialize game-specific resources.

        Called once before the game loop starts. Use this to:
        - Create display groups and sprites
        - Initialize game-specific inputs (buttons, touch pads)
        - Set up the game model and view
        - Calibrate sensors if needed

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement setup()")

    def run(self):
        """Main game loop.

        Returns
        -------
        str or bool
            - "gameover" if the game ended due to player losing all lives
            - "switch" or True if user requested game switch (Button D press)
            - "victory" if player completed the game
            - False for other exit reasons

        Must be implemented by subclasses. Typical structure:

            while True:
                self.buttons.update()
                if self.buttons.d_fell:
                    return "switch"

                # Game logic here...
                if game_over:
                    return "gameover"
                time.sleep(0.033)
        """
        raise NotImplementedError("Subclasses must implement run()")

    def cleanup(self):
        """Release game-specific resources before switching.

        Called after run() returns. Use this to:
        - deinit() any game-specific inputs (buttons, touch pads)
        - Clear display groups
        - Stop any playing audio

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement cleanup()")

    def get_high_score(self):
        """Get this game's high score from persistent storage."""
        if self.HIGH_SCORE_SLOT < 0:
            return 0
        return self.high_scores.get(self.HIGH_SCORE_SLOT)

    def set_high_score(self, score):
        """Set this game's high score in persistent storage."""
        if self.HIGH_SCORE_SLOT < 0:
            return
        self.high_scores.set(self.HIGH_SCORE_SLOT, score)
