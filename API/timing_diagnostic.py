"""
timing_diagnostic.py — Timing diagnostic for Analog Waveform Explorer
=======================================================================
Toggles three GPIO pins so a Saleae Logic Analyzer can measure actual
timings in the main loop.

Connections
-----------
  A1 → Channel 0 : HIGH during each ADC sample block (oversample reads)
  A2 → Channel 1 : HIGH during redraw() + display.refresh() combined
  A3 → Channel 2 : Toggles every main-loop iteration (period = loop speed)

Run this instead of the normal analog_waveform_explorer.run() to capture
timing data.  Feed A0 with your signal generator as usual.

What to measure in Saleae
--------------------------
  A1 pulse width   → actual ADC sample duration (oversample × read time)
  A1 period        → actual interval between samples (compare to nominal)
  A2 pulse width   → total LCD update time (redraw + SPI refresh)
  A3 period        → main-loop iteration time (no-ADC and ADC iterations
                     will differ; observe both)

Note
----
  This is a standalone diagnostic tool.  The scale table and oversample
  counts below are kept in sync with analog_waveform_explorer.py but may
  drift if that module is updated.  The rolling display used here is
  intentionally simpler than the triggered capture in the main module —
  the goal is timing measurement, not waveform quality.
"""

import board
import displayio
import bitmaptools
import digitalio
import time
from analog_io import AnalogInput
from lcd_display import LCDDisplay, Colors
from digital_io import EdgeDetector

# ---------------------------------------------------------------------------
# Diagnostic output pins (inputs to the Saleae)
# ---------------------------------------------------------------------------

def _make_diag(pin):
    d = digitalio.DigitalInOut(pin)
    d.direction = digitalio.Direction.OUTPUT
    d.value = False
    return d

_pin_adc  = _make_diag(board.A1)   # HIGH during ADC sample block
_pin_lcd  = _make_diag(board.A2)   # HIGH during full LCD update block
_pin_loop = _make_diag(board.A3)   # toggles every main-loop iteration

# ---------------------------------------------------------------------------
# Scale table — must match analog_waveform_explorer._SCALES
# (label, nominal interval µs, oversample count)
# ---------------------------------------------------------------------------

_SCALES = [
    ("10ms/px", 10000, 4),
    (" 5ms/px",  5000, 4),
    (" 2ms/px",  2000, 4),
    (" 1ms/px",  1000, 4),
    ("500us/px",  500, 4),
    ("200us/px",  200, 1),
]

_DEFAULT_SCALE    = 3      # 1ms/px — good middle ground for measurement
_REFRESH_INTERVAL = 0.15   # seconds between LCD redraws
_REFRESH_EVERY    = 100
_LONG_PRESS_S     = 0.8
_BTN_EVERY        = 20

WAVE_W = 232
WAVE_H = 90
WAVE_X = 4
WAVE_Y = 32
_ADC_MAX = 65535


def run():
    lcd = LCDDisplay()
    btn = EdgeDetector(board.D3)
    lcd.backlight_on()
    lcd.display.auto_refresh = False

    scale_idx      = _DEFAULT_SCALE
    adc            = AnalogInput(board.A0)
    sample_buf     = [0] * WAVE_W
    write_pos      = 0
    raw            = 0
    interval_ns    = _SCALES[scale_idx][1] * 1000
    next_sample_ns = time.monotonic_ns()
    next_refresh   = time.monotonic() + _REFRESH_INTERVAL
    loop_tick      = 0
    btn_tick       = 0
    press_start    = None

    group, _ = lcd.make_group(Colors.BLACK)
    lcd.add_label(group, "TIMING DIAGNOSTIC", 120, 2,
                  color=Colors.WHITE, scale=1)
    lcd.add_label(group, "A1=ADC  A2=LCD  A3=loop", 120, 11,
                  color=Colors.GRAY, scale=1)
    scale_lbl = lcd.add_label(group, _SCALES[scale_idx][0], 120, 21,
                               color=Colors.CYAN, scale=1)

    wave_bitmap  = displayio.Bitmap(WAVE_W, WAVE_H, 2)
    wave_palette = displayio.Palette(2)
    wave_palette[0] = 0x001018
    wave_palette[1] = Colors.CYAN
    group.append(displayio.TileGrid(
        wave_bitmap, pixel_shader=wave_palette, x=WAVE_X, y=WAVE_Y,
    ))
    lcd.display.refresh()

    def redraw():
        wave_bitmap.fill(0)
        prev_y = None
        for x in range(WAVE_W):
            r  = sample_buf[(write_pos + x) % WAVE_W]
            yc = WAVE_H - 1 - int(r / _ADC_MAX * (WAVE_H - 1))
            if prev_y is None:
                y_lo = max(0, yc - 1)
                y_hi = min(WAVE_H - 1, yc + 1)
            else:
                y_lo = min(prev_y, yc)
                y_hi = max(prev_y, yc)
            bitmaptools.draw_line(wave_bitmap, x, y_lo, x, y_hi, 1)
            prev_y = yc

    while True:
        now_ns = time.monotonic_ns()

        # Sparse button polling — matches main module behaviour
        btn_tick += 1
        if btn_tick >= _BTN_EVERY:
            btn_tick = 0
            btn.update()
            if btn.fell:
                press_start = time.monotonic()
            if btn.rose and press_start is not None:
                held = time.monotonic() - press_start
                press_start = None
                if held < _LONG_PRESS_S:
                    scale_idx      = (scale_idx + 1) % len(_SCALES)
                    interval_ns    = _SCALES[scale_idx][1] * 1000
                    next_sample_ns = time.monotonic_ns()
                    for i in range(WAVE_W):
                        sample_buf[i] = 0
                    scale_lbl.text = _SCALES[scale_idx][0]

        # ADC sample — A1 HIGH for the duration of the reads
        if now_ns >= next_sample_ns:
            next_sample_ns = now_ns + interval_ns
            oversample = _SCALES[scale_idx][2]
            _pin_adc.value = True
            acc = 0
            for _ in range(oversample):
                acc += adc.raw
            raw = acc // oversample
            _pin_adc.value = False
            sample_buf[write_pos] = raw
            write_pos = (write_pos + 1) % WAVE_W

        # LCD refresh — A2 HIGH for the entire update block
        loop_tick += 1
        if loop_tick >= _REFRESH_EVERY:
            loop_tick = 0
            now_s = time.monotonic()
            if now_s >= next_refresh:
                next_refresh = now_s + _REFRESH_INTERVAL
                _pin_lcd.value = True
                redraw()
                lcd.display.refresh()
                _pin_lcd.value = False

        # Loop-rate toggle — A3 flips every iteration
        _pin_loop.value = not _pin_loop.value
