"""
pwm_pins.py — PWM Pin Scanner
==============================
Board: Dev Board

Scans all board pins and classifies each one by its PWM capability:

  PWM on             — pin successfully claimed a PWM timer
  PWM capable        — pin supports PWM but its timer is held by a system
                       peripheral (e.g. LCD backlight, status LED); the pin
                       cannot be used for PWM while the board firmware holds
                       that timer
  No PWM             — pin has no PWM capability at all

Results are returned as three lists and can be printed in a consistent,
sorted order via ``report()``.

Use this module for:
  - Discovering which pins are available for pwmio.PWMOut on your build
  - Debugging timer conflicts between user code and board-level peripherals
  - Generating a reference list before writing PWM-based drivers

Example - Scan and report PWM capabilities
-------
import pykit_explorer
from pwm_pins import PWMPinScanner
scanner = PWMPinScanner()
scanner.scan()
scanner.report()

"""

import board
import microcontroller
import pwmio


class PWMPinScanner:
    """Scan all board pins and classify them by PWM capability.

    Attributes
    ----------
    pwm_on         : list of pin name strings that have working PWM
    pwm_prevented  : list of (pin_name, reason) tuples — PWM capable but
                     blocked by a system peripheral or timer conflict
    pwm_off        : list of pin name strings with no PWM capability

    Example - Scan and report PWM capabilities for each pin
    -------
import pykit_explorer
from pwm_pins import PWMPinScanner
scanner = PWMPinScanner()
scanner.scan()
scanner.report()
# Access results directly
print(f"\nPWM on: {scanner.pwm_on}")
print(f"\nPWM prevented: {scanner.pwm_prevented}")
print(f"\nNo PWM: {scanner.pwm_off}")

    """

    def __init__(self):
        self.pwm_on = []
        self.pwm_prevented = []
        self.pwm_off = []
        self._pwm_capable = []  # internal: (pin_name, pin) for blocker probing

    def scan(self):
        """Scan all board pins and populate pwm_on, pwm_prevented, pwm_off."""
        self.pwm_on = []
        self.pwm_prevented = []
        self.pwm_off = []
        self._pwm_capable = []

        for pin_name in dir(board):
            pin = getattr(board, pin_name)
            if not isinstance(pin, microcontroller.Pin):
                continue

            p = None
            try:
                p = pwmio.PWMOut(pin)
                self._pwm_capable.append((pin_name, pin))
                self.pwm_on.append(pin_name)
            except ValueError:
                self.pwm_off.append(pin_name)
            except RuntimeError:
                reason = self._find_blocker(pin_name)
                self.pwm_prevented.append((pin_name, reason))
            finally:
                if p is not None:
                    p.deinit()

    def _find_blocker(self, blocked_pin_name):
        """Return a human-readable reason string for a timer conflict."""
        for prev_name, prev_pin in self._pwm_capable:
            probe = None
            try:
                probe = pwmio.PWMOut(prev_pin)
            except RuntimeError:
                return "timer conflict with {}".format(prev_name)
            finally:
                if probe is not None:
                    probe.deinit()
        return "timer held by system peripheral"

    def report(self):
        """Print scan results: PWM on, then PWM prevented, then no PWM."""
        if not self.pwm_on and not self.pwm_prevented and not self.pwm_off:
            print("No scan results — call scan() first.")
            return

        for pin_name in self.pwm_on:
            print("PWM on:", pin_name)

        for pin_name, reason in self.pwm_prevented:
            print("PWM capable but prevented ({}) ->".format(reason), pin_name)

        for pin_name in self.pwm_off:
            print("No PWM on:", pin_name)
