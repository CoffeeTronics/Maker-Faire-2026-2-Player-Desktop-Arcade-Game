"""
servo_control.py — Servo Motor Control
========================================
Board: Dev Board

Drives a standard RC servo (50 Hz PWM, 1–2 ms pulse width) using the
adafruit_motor library.

Requires
--------
  circuitpython_motor library  (adafruit_motor)

Hardware
--------
  Default pin: board.A5 (PWM capable, used in the servo test)
  Any other PWM-capable pin also works — see PWM_pins_avail.py.

Use this module for:
  - Pan/tilt camera mounts
  - Robot arms or grippers
  - Throttle or steering mechanisms
"""

import board
import pwmio
from adafruit_motor import servo


class ServoController:
    """Position a standard RC servo motor.

    Parameters
    ----------
    pin          : PWM-capable board pin (default board.A5)
    min_pulse    : minimum pulse width in µs (default 750 — adjust for your servo)
    max_pulse    : maximum pulse width in µs (default 2250 — adjust for your servo)

    Example
    -------
import pykit_explorer
from servo_control import ServoController
srv = ServoController(board.A5)
srv.angle = 90      # centre
srv.sweep()         # 0° → 180° → 0°, blocking
    """

    def __init__(self, pin=board.A5, min_pulse: int = 750, max_pulse: int = 2250):
        self._pwm = pwmio.PWMOut(pin, duty_cycle=2**15, frequency=50)
        self._servo = servo.Servo(self._pwm, min_pulse=min_pulse, max_pulse=max_pulse)

    @property
    def angle(self) -> float:
        """Current servo angle in degrees (0–180)."""
        return self._servo.angle

    @angle.setter
    def angle(self, degrees: float):
        """Move servo to *degrees* (0.0–180.0)."""
        self._servo.angle = max(0.0, min(180.0, degrees))

    def sweep(self, start: float = 0.0, end: float = 180.0,
              step: float = 5.0, delay: float = 0.05, cycles: int = 1):
        """Sweep from *start* to *end* degrees and back, *cycles* times (blocking).

        Parameters
        ----------
        start  : start angle in degrees
        end    : end angle in degrees
        step   : degrees per move
        delay  : seconds between each step
        cycles : how many full back-and-forth sweeps to perform
        """
        import time
        for _ in range(cycles):
            a = start
            while a <= end:
                self.angle = a
                time.sleep(delay)
                a += step
            a = end
            while a >= start:
                self.angle = a
                time.sleep(delay)
                a -= step

    def centre(self):
        """Move to 90° (centre position)."""
        self.angle = 90.0

    def deinit(self):
        self._pwm.deinit()
