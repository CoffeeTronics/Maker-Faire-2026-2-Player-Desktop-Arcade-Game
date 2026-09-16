"""
pwm_out.py — PWM Output
========================
Board: Dev Board

Provides a PWM output wrapper for LED dimming, buzzer tones, motor speed
control, or any signal that needs a variable duty cycle or frequency.

PWM-capable pins (verified on this board):
  D0–D7, D13, A0–A5 (not all; run PWM_pins_avail.py to enumerate on your build)

Use this module for:
  - Dimming LEDs
  - Generating tones on a passive buzzer
  - Controlling motor speed via a driver board
  - Any application needing a variable duty cycle square wave
"""

import board
import pwmio
import time


class PWMOutput:
    """Control a single PWM output pin.

    Parameters
    ----------
    pin          : PWM-capable board pin
    frequency    : PWM frequency in Hz (default 5 000 Hz — good for LEDs)
    duty_cycle   : initial duty cycle 0–65535 (default 0 = off)

    Example - Fade an LED in and out - use a oscilloscope, logic analyzer, or multimeter in duty cycle mode to see the effect
    -------
import pykit_explorer
from pwm_out import PWMOutput
pwm = PWMOutput(board.D5, frequency=1000)
pwm.duty_percent = 50      # 50% duty cycle
while True:
    pwm.fade_in(duration=1.0)  # fade in over 1 second
    pwm.fade_out(duration=1.0) # fade out over 1 second

    """

    def __init__(self, pin=board.D5, frequency: int = 5000, duty_cycle: int = 0):
        self._pwm = pwmio.PWMOut(pin, frequency=frequency, duty_cycle=duty_cycle)

    # -- Duty cycle ----------------------------------------------------------

    @property
    def duty_cycle(self) -> int:
        """Raw duty cycle value (0–65535)."""
        return self._pwm.duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value: int):
        self._pwm.duty_cycle = max(0, min(65535, int(value)))

    @property
    def duty_percent(self) -> float:
        """Duty cycle as a percentage (0.0–100.0)."""
        return (self._pwm.duty_cycle / 65535) * 100.0

    @duty_percent.setter
    def duty_percent(self, percent: float):
        """Set duty cycle from a percentage (0.0–100.0)."""
        self._pwm.duty_cycle = int((max(0.0, min(100.0, percent)) / 100.0) * 65535)

    # -- Frequency -----------------------------------------------------------

    @property
    def frequency(self) -> int:
        return self._pwm.frequency

    @frequency.setter
    def frequency(self, hz: int):
        self._pwm.frequency = hz

    # -- Convenience helpers -------------------------------------------------

    def off(self):
        """Set duty cycle to 0 (output off)."""
        self.duty_cycle = 0

    def full_on(self):
        """Set duty cycle to 100% (output fully on)."""
        self.duty_cycle = 65535

    def fade_in(self, duration: float = 1.0, steps: int = 100):
        """Ramp duty cycle from 0% to 100% over *duration* seconds (blocking)."""
        delay = duration / steps
        for i in range(steps + 1):
            self.duty_percent = i
            time.sleep(delay)

    def fade_out(self, duration: float = 1.0, steps: int = 100):
        """Ramp duty cycle from 100% to 0% over *duration* seconds (blocking)."""
        delay = duration / steps
        for i in range(steps, -1, -1):
            self.duty_percent = i
            time.sleep(delay)

    def beep(self, frequency: int = 1000, duration: float = 0.1):
        """Emit a short tone at *frequency* Hz for *duration* seconds (blocking).

        Best used with a passive buzzer connected to the pin.
        """
        old_freq = self._pwm.frequency
        self._pwm.frequency = frequency
        self.duty_percent = 50
        time.sleep(duration)
        self.off()
        self._pwm.frequency = old_freq

    def deinit(self):
        self._pwm.deinit()
