"""
high_scores.py - Centralized NVM High Score Manager
====================================================

Manages high scores for all games using the microcontroller's
Non-Volatile Memory (NVM). Scores persist across power cycles.

NVM Layout (64 bytes):
    Bytes 0-3:   Magic marker "GSv1" (Game Scores v1)
    Bytes 4-5:   Slot 0 high score (uint16) - Snake
    Bytes 6-7:   Slot 1 high score (uint16) - Space Impact
    Bytes 8-9:   Slot 2 high score (uint16) - Mario
    Bytes 10-63: Slots 3-29 reserved for future games

Usage Examples
--------------

Games typically access high scores through BaseGame methods, but the
HighScoreManager can also be used directly:

    from high_scores import HighScoreManager

    # Initialize manager (loads existing scores from NVM)
    hs = HighScoreManager()

    # Get a high score (slot 0 = Snake, 1 = Space Impact, 2 = Mario)
    current = hs.get(0)
    print(f"Snake high score: {current}")

    # Set a high score (only saves if higher than current)
    hs.set(0, 150)  # Only updates if 150 > current

    # Force set a score (overwrites regardless of current value)
    hs.force_set(0, 100)

    # Reset a single game's score
    hs.reset(0)

    # Reset all scores to zero
    hs.reset_all()

In a game class inheriting from BaseGame, use the convenience methods:

    class MyGame(BaseGame):
        HIGH_SCORE_SLOT = 3  # Assign unique slot

        def run(self, switch_detector):
            # Get this game's high score
            high = self.get_high_score()

            # Save new high score (only if higher)
            if score > high:
                self.set_high_score(score)
"""

import struct
import microcontroller

_NVM_MAGIC = b"GSv1"
_NVM_HEADER_SIZE = 4
_NVM_SLOT_SIZE = 2
_NVM_MAX_SLOTS = 30
_NVM_TOTAL_SIZE = _NVM_HEADER_SIZE + (_NVM_SLOT_SIZE * _NVM_MAX_SLOTS)  # 64 bytes


class HighScoreManager:
    """Manages high scores for all games using NVM persistence."""

    def __init__(self):
        """Initialize the high score manager and load existing scores."""
        self._scores = [0] * _NVM_MAX_SLOTS
        self._available = self._nvm_available()
        if self._available:
            self._load()

    @staticmethod
    def _nvm_available():
        """Check if this board has NVM support with enough space."""
        nvm = getattr(microcontroller, "nvm", None)
        if nvm is None:
            return False
        return len(nvm) >= _NVM_TOTAL_SIZE

    def _load(self):
        """Load all high scores from NVM."""
        if not self._available:
            return

        raw = bytes(microcontroller.nvm[0:_NVM_TOTAL_SIZE])
        magic = raw[0:_NVM_HEADER_SIZE]

        if magic != _NVM_MAGIC:
            self._scores = [0] * _NVM_MAX_SLOTS
            return

        for i in range(_NVM_MAX_SLOTS):
            offset = _NVM_HEADER_SIZE + (i * _NVM_SLOT_SIZE)
            try:
                self._scores[i] = struct.unpack("<H", raw[offset:offset + _NVM_SLOT_SIZE])[0]
            except Exception:
                self._scores[i] = 0

    def save(self):
        """Persist all high scores to NVM."""
        if not self._available:
            return

        data = bytearray(_NVM_TOTAL_SIZE)
        data[0:_NVM_HEADER_SIZE] = _NVM_MAGIC

        for i in range(_NVM_MAX_SLOTS):
            offset = _NVM_HEADER_SIZE + (i * _NVM_SLOT_SIZE)
            score = min(self._scores[i], 65535)
            data[offset:offset + _NVM_SLOT_SIZE] = struct.pack("<H", score)

        try:
            microcontroller.nvm[0:_NVM_TOTAL_SIZE] = bytes(data)
        except Exception:
            pass

    def get(self, slot):
        """Get the high score for a game slot.

        Parameters
        ----------
        slot : int
            Game slot number (0-29)

        Returns
        -------
        int
            High score, or 0 if slot is invalid
        """
        if 0 <= slot < _NVM_MAX_SLOTS:
            return self._scores[slot]
        return 0

    def set(self, slot, score):
        """Set the high score for a game slot (only if higher).

        Parameters
        ----------
        slot : int
            Game slot number (0-29)
        score : int
            New score to set (only saved if higher than current)
        """
        if 0 <= slot < _NVM_MAX_SLOTS:
            if score > self._scores[slot]:
                self._scores[slot] = min(score, 65535)
                self.save()

    def force_set(self, slot, score):
        """Force set a high score regardless of current value.

        Parameters
        ----------
        slot : int
            Game slot number (0-29)
        score : int
            Score to set
        """
        if 0 <= slot < _NVM_MAX_SLOTS:
            self._scores[slot] = min(score, 65535)
            self.save()

    def reset_all(self):
        """Reset all high scores to zero."""
        self._scores = [0] * _NVM_MAX_SLOTS
        self.save()

    def reset(self, slot):
        """Reset a single game's high score to zero."""
        if 0 <= slot < _NVM_MAX_SLOTS:
            self._scores[slot] = 0
            self.save()
