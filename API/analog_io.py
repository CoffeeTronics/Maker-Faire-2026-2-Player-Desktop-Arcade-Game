"""
analog_io.py — Analog Input / Output
=====================================
Board: Dev Board

Provides helpers for reading analog voltages (ADC) and writing analog voltages
via the on-board DAC.

Analog Input
------------
  Pins: A0–A5
  Resolution: 16-bit raw value (0–65535), auto-scaled to voltage by helper.

Analog Output (DAC)
-------------------
  Pin: board.DAC  ← the ONLY analog output capable pin on this board (PA02).
  Note: "AnalogOut on non-DAC pins" is listed as FAIL in the test suite.
  Always use board.DAC for analog voltage output.

Use this module for:
  - Reading potentiometers, light sensors, temperature sensors (analog)
  - Generating a DC bias or slow-varying voltage (DAC)
  - Driving the DAC through a sine/sawtooth waveform (see AudioOut for audio)
"""

import board
import time
from analogio import AnalogIn, AnalogOut

# Supply voltage reference (3.3 V for this board)
VREF = 3.3

# ADC full-scale count
ADC_MAX = 65535


# ---------------------------------------------------------------------------
# Analog Input
# ---------------------------------------------------------------------------

class AnalogInput:
    """Read an analog voltage from a pin.

    Parameters
    ----------
    pin : board pin — any of board.A0 … board.A5

Example - Read ADC values (voltage, raw, percent)
-------
import pykit_explorer
from analog_io import AnalogInput
adc = AnalogInput(board.A0)
print(adc.voltage)   # float, 0.0 - 3.3 V
print(adc.raw)       # int,   0 - 65535
print(adc.percent)   # float, 0.0 - 100.0 %

"""

    def __init__(self, pin=board.A0):
        self._adc = AnalogIn(pin)

    @property
    def raw(self) -> int:
        """16-bit raw ADC reading (0–65535)."""
        return self._adc.value

    @property
    def voltage(self) -> float:
        """Scaled voltage in volts (0.0–3.3 V)."""
        return (self._adc.value * VREF) / ADC_MAX

    @property
    def percent(self) -> float:
        """Percentage of full-scale (0.0–100.0)."""
        return (self._adc.value / ADC_MAX) * 100.0

    def deinit(self):
        self._adc.deinit()


# ---------------------------------------------------------------------------
# Analog Output (DAC)
# ---------------------------------------------------------------------------

class AnalogOutput:
    """Write an analog voltage using the on-board DAC.

    Parameters
    ----------
    pin : must be board.DAC — the only analog output capable pin on this board

Example - Set DAC voltage and perform sweep
-------
import pykit_explorer
from analog_io import AnalogOutput
dac = AnalogOutput()
dac.voltage = 1.65   # ~mid-scale
dac.voltage = 0.0
dac.raw = 32768      # equivalent
dac.raw = 0
dac.sweep()         # sweep from 0 to 3.3 V and back (blocking)

"""

    def __init__(self, pin=board.DAC):
        self._dac = AnalogOut(pin)
        self._raw = 0

    @property
    def raw(self) -> int:
        return self._raw

    @raw.setter
    def raw(self, value: int):
        """Set raw 16-bit DAC value (0–65535)."""
        self._raw = max(0, min(65535, int(value)))
        self._dac.value = self._raw

    @property
    def voltage(self) -> float:
        return (self._raw * VREF) / ADC_MAX

    @voltage.setter
    def voltage(self, volts: float):
        """Set output voltage in volts (0.0–3.3 V)."""
        self._raw = int((max(0.0, min(VREF, volts)) / VREF) * ADC_MAX)
        self._dac.value = self._raw

    def sweep(self, start_v: float = 0.0, end_v: float = VREF,
              step_v: float = 0.05, delay: float = 0.01):
        """Sweep the DAC output from start_v to end_v (blocking).

        Parameters
        ----------
        start_v : starting voltage
        end_v   : ending voltage
        step_v  : voltage increment per step
        delay   : seconds between steps
        """
        v = start_v
        direction = 1 if end_v >= start_v else -1
        while (direction == 1 and v <= end_v) or (direction == -1 and v >= end_v):
            self.voltage = v
            time.sleep(delay)
            v += direction * step_v

    def deinit(self):
        self._dac.deinit()
