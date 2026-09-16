"""
audio_out.py — DAC & WAV Audio Output
=======================================
Board: Ruler Baseboard

Provides audio output modes:
  1. Sine tone — generates a pure sine wave at a specified frequency
  2. WAV playback — plays mono 16-bit PCM WAV files (≤22 kHz)
  3. Preloaded sounds — cache sounds for fast, non-blocking playback

Hardware: board.DAC — dedicated audio DAC output pin
"""

import array
import math
import board
import time
from audiocore import RawSample, WaveFile

try:
    from audioio import AudioOut
except ImportError:
    try:
        from audiopwmio import PWMAudioOut as AudioOut
    except ImportError:
        AudioOut = None


class AudioOutput:
    """Play sine tones and WAV files through the board DAC."""

    def __init__(self, pin=board.DAC):
        if AudioOut is None:
            raise RuntimeError("No AudioOut available on this board.")
        self._audio = AudioOut(pin)
        self._tone_sample = None
        self._preloaded = {}  # name -> (file_handle, WaveFile)

    # -- Preloaded sounds ----------------------------------------------------

    def preload_wav(self, name, path):
        """Preload a WAV file for fast non-blocking playback.

        Parameters
        ----------
        name : str - identifier for this sound
        path : str - path to WAV file

        Example
        -------
        audio.preload_wav("shoot", "/AudioFiles/shoot.wav")
        audio.preload_wav("explosion", "/AudioFiles/explosion.wav")
        """
        try:
            if name in self._preloaded:
                self.unload_wav(name)
            fh = open(path, "rb")
            wave = WaveFile(fh)
            self._preloaded[name] = (fh, wave)
        except Exception as e:
            print(f"Failed to preload {name}: {e}")

    def play_preloaded(self, name):
        """Play a preloaded sound non-blocking.

        Parameters
        ----------
        name : str - identifier used in preload_wav()

        Returns True if sound started, False if not found/error.
        """
        if name not in self._preloaded:
            print(f"Audio: {name} not in preloaded ({list(self._preloaded.keys())})")
            return False
        try:
            fh, wave = self._preloaded[name]
            # Seek back to start for replay
            fh.seek(0)
            wave = WaveFile(fh)
            self._preloaded[name] = (fh, wave)
            if self._audio.playing:
                self._audio.stop()
            self._audio.play(wave)
            return True
        except Exception as e:
            print(f"Play error {name}: {e}")
            return False

    def unload_wav(self, name):
        """Unload a preloaded sound to free memory."""
        if name in self._preloaded:
            try:
                fh, wave = self._preloaded[name]
                fh.close()
            except:
                pass
            del self._preloaded[name]

    def unload_all(self):
        """Unload all preloaded sounds."""
        for name in list(self._preloaded.keys()):
            self.unload_wav(name)

    # -- Sine tone -----------------------------------------------------------

    def _make_sine(self, frequency, volume=0.1):
        sample_rate = 8000
        a, b = sample_rate, frequency
        while b:
            a, b = b, a % b
        g = a
        num_cycles = frequency // g
        length = sample_rate // g
        buf = array.array("H", [0] * length)
        for i in range(length):
            buf[i] = int((1 + math.sin(math.pi * 2 * num_cycles * i / length))
                         * volume * (2 ** 15 - 1))
        return RawSample(buf)

    def play_tone(self, frequency=1000, volume=0.1, duration=None):
        """Generate and play a sine wave tone."""
        sample = self._make_sine(frequency, volume)
        self._audio.play(sample, loop=True)
        if duration is not None:
            time.sleep(duration)
            self.stop()

    def play_scale(self, notes=None, duration_each=0.3, volume=0.1):
        """Play a list of frequencies in sequence (blocking)."""
        if notes is None:
            notes = [262, 294, 330, 349, 392, 440, 494, 523]
        for freq in notes:
            self.play_tone(freq, volume=volume, duration=duration_each)

    # -- WAV playback --------------------------------------------------------

    def play_wav(self, path, loop=False):
        """Play a WAV file (blocking unless loop=True)."""
        wave_file = open(path, "rb")
        wave = WaveFile(wave_file)
        self._audio.play(wave, loop=loop)
        if not loop:
            while self._audio.playing:
                pass
            wave_file.close()

    def play_wav_async(self, path):
        """Play a WAV file non-blocking. File closes when playback ends."""
        try:
            wave_file = open(path, "rb")
            wave = WaveFile(wave_file)
            if self._audio.playing:
                self._audio.stop()
            self._audio.play(wave)
        except Exception as e:
            print(f"play_wav_async error: {e}")

    # -- Control -------------------------------------------------------------

    def stop(self):
        """Stop any currently playing audio."""
        self._audio.stop()

    @property
    def is_playing(self):
        """True while audio is currently playing."""
        return self._audio.playing

    def deinit(self):
        """Release audio hardware and all preloaded sounds."""
        self.stop()
        self.unload_all()
        self._audio.deinit()