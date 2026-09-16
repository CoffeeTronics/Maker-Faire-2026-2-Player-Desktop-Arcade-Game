"""
analog_waveform_explorer.py — Analog Waveform Explorer
=======================================================
Board: Dev Board / Ruler Baseboard

A triggered single-sweep oscilloscope display for analog signals on pins A0–A5.
The scope waits for a rising edge at mid-scale, captures exactly WAVE_W samples
(pre-trigger + post-trigger), freezes the display, then arms again immediately.
All samples in each frame are taken without any LCD activity, so the waveform
is always continuous and phase-stable.

Hardware
--------
  board.A0–A5 — Analog inputs (all six channels available)
  board.D3    — USER button: short press = next scale, long press = next channel
  LCD         — 240×135 ST7789 via Ruler baseboard

Controls
--------
  Short press D3  (< 0.8 s) : step horizontal scale through 6 presets
  Long press  D3  (≥ 0.8 s) : step channel  A0 → A1 → … → A5 (wraps)

Horizontal scale presets
------------------------
  The effective sample interval is limited by CircuitPython loop overhead
  (~170 µs) and ADC read time (oversample × ~64 µs).  Nominal and effective
  values are shown below; the frequency/period readout uses the measured
  effective interval so it is accurate regardless of scale.

  Nominal   Oversample  Effective   Window    Useful signal range
  --------  ----------  ---------   ------    -------------------
  10ms/px      4        ~10 ms      2.32 s    ~0.4–10 Hz
   5ms/px      4        ~5 ms       1.16 s    ~1–20 Hz
   2ms/px      4        ~2 ms        464 ms   ~4–50 Hz
   1ms/px      4        ~1.1 ms      232 ms   ~10–100 Hz
  500µs/px     4        ~612 µs      116 ms   ~50–165 Hz
  200µs/px     1        ~242 µs       46 ms   ~100–400 Hz

Trigger
-------
  Rising edge at mid-scale (ADC value 32768 = 1.65 V on a 3.3 V rail).
  _PRETRIG (= WAVE_W // 5 = 46) samples captured before the crossing are
  prepended so the waveform begins just before the trigger point (x = 46).
  The LCD is never refreshed during capture, so each frame contains only
  continuously-sampled, gap-free data.  The pre-trigger buffer must be fully
  refilled with fresh samples between frames before a new trigger is accepted,
  preventing mis-timed samples from LCD SPI activity appearing in the display.

ADC noise
---------
  lcd.display.auto_refresh is set to False and lcd.display.refresh() is only
  called between capture frames.  Leaving auto_refresh enabled causes the ST7789
  SPI bus to run continuously at ~60 Hz, coupling noise into the ADC and
  producing visible distortion at 5–20 Hz.  Explicit refresh eliminates this.

Frequency / period readout
--------------------------
  Frequency and period are derived from the elapsed time between the trigger
  point and the next rising mid-scale crossing found in the captured frame,
  divided by the actual number of samples between those crossings.  Using real
  elapsed time (rather than the nominal scale interval) corrects for the
  CircuitPython loop overhead that makes fast scales run slower than nominal.

  If no second crossing is found within the capture window — because the signal
  period is longer than the window, the signal is DC, or the amplitude does not
  reach mid-scale — the frequency and period fields show "---".  Select a slower
  scale to bring more than one period into view.

Display layout
--------------
  y=  2  "ANALOG WAVEFORM EXPLORER"           white
  y= 11  "A0  3.28Vpp  10.0Hz  100.0ms"       channel colour
           │   │         │       └ period
           │   │         └ frequency (measured from capture timestamps)
           │   └ peak-to-peak voltage across the captured frame
           └ active channel (A0–A5)
  y= 21  "10ms/px  2.32s"                     gray  (nominal scale + window)
  y= 32  ┌── triggered waveform 232×90 px ─┐
          │  x=46: trigger crossing          │
          │  bitmap, background + trace      │
          └───────────────────────────────────┘
  y=124  "PRESS=scale  HOLD=ch"               gray

Usage
-----
  from analog_waveform_explorer import run
  run()

  For measuring actual loop and ADC timings with a logic analyser, use the
  companion script timing_diagnostic.py instead of this module.  Note that
  timing_diagnostic.py is a standalone diagnostic tool and may not reflect
  the latest scale table or refresh behaviour of this module.
"""

import board
import displayio
import bitmaptools
import time
from analog_io import AnalogInput
from lcd_display import LCDDisplay, Colors
from digital_io import EdgeDetector

# ---------------------------------------------------------------------------
# Channel table
# ---------------------------------------------------------------------------

_PINS   = [board.A0, board.A1, board.A2, board.A3, board.A4, board.A5]
_NAMES  = ["A0", "A1", "A2", "A3", "A4", "A5"]
_COLORS = [
    Colors.CYAN,
    Colors.GREEN,
    Colors.YELLOW,
    Colors.ORANGE,
    Colors.RED,
    Colors.PURPLE,
]

# ---------------------------------------------------------------------------
# Horizontal scale presets: (display label, nominal interval µs, oversample count)
#
# Effective minimum sample interval = loop_overhead (~178 µs) + oversample * ADC_read (~64 µs).
# Scales slower than ~440 µs use oversample=4 for noise reduction.
# 200 µs/px uses oversample=1 (~242 µs effective) — genuinely faster than 500 µs/px (~612 µs).
# 100 µs/px is omitted: it cannot be achieved with the current loop overhead and is
# indistinguishable from 200 µs/px regardless of oversample count.
# ---------------------------------------------------------------------------

_SCALES = [
    ("10ms/px", 10000, 4),   # effective ~10 ms,  2.32 s window
    (" 5ms/px",  5000, 4),   # effective ~5 ms,   1.16 s
    (" 2ms/px",  2000, 4),   # effective ~2 ms,   464 ms
    (" 1ms/px",  1000, 4),   # effective ~1.1 ms, 232 ms (measured)
    ("500us/px",  500, 4),   # effective ~612 µs, 116 ms
    ("200us/px",  200, 1),   # effective ~242 µs,  46 ms  (oversample=1)
]

_DEFAULT_SCALE    = 0      # 10ms/px — 2.32 s window, good for 1 Hz
_REFRESH_EVERY    = 100    # check LCD refresh every N main-loop iterations
_BTN_EVERY        = 20     # poll button every N iterations (~1 ms at target loop rate)
_LONG_PRESS_S     = 0.8    # seconds to distinguish long press from short press

# ---------------------------------------------------------------------------
# Waveform geometry
# ---------------------------------------------------------------------------

WAVE_X = 4
WAVE_Y = 32
WAVE_W = 232    # display width (240) minus 4 px margin each side
WAVE_H = 90

_VREF    = 3.3
_ADC_MAX = 65535

# ---------------------------------------------------------------------------
# Trigger constants
# ---------------------------------------------------------------------------

_PRETRIG   = WAVE_W // 5   # 46 pre-trigger samples; trigger crossing appears at x=46
_ST_ARMED  = 0             # waiting for rising edge
_ST_CAPTURE = 1            # collecting post-trigger samples


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    """Initialise hardware and enter the Analog Waveform Explorer main loop.

    Blocks indefinitely — call this as the last statement in code.py.
    """

    # -- Hardware ------------------------------------------------------------
    lcd = LCDDisplay()
    btn = EdgeDetector(board.D3)
    lcd.backlight_on()
    lcd.display.auto_refresh = False   # SPI only fires during explicit refresh()

    # -- State ---------------------------------------------------------------
    ch_idx    = 0
    scale_idx = _DEFAULT_SCALE
    adc       = AnalogInput(_PINS[ch_idx])
    raw       = 0

    interval_ns    = _SCALES[scale_idx][1] * 1000   # µs → ns
    next_sample_ns = time.monotonic_ns()
    loop_tick      = 0
    btn_tick       = 0
    press_start    = None   # time.monotonic() when D3 was pressed, or None

    # -- Trigger state -------------------------------------------------------
    pretrig_buf  = [0] * _PRETRIG   # rolling circular pre-trigger buffer
    pretrig_pos  = 0
    pretrig_fill = 0               # counts fresh samples since last ARMED entry (max _PRETRIG)
    capture_buf       = [0] * WAVE_W    # frozen complete frame shown on LCD
    state             = _ST_ARMED
    cap_count         = 0               # post-trigger samples collected
    frame_ready       = False
    prev_raw          = _ADC_MAX        # start high so first crossing is a genuine rising edge
    threshold         = _ADC_MAX // 2   # mid-scale trigger level
    t_capture_start   = 0               # now_ns when trigger fires
    actual_interval_us = _SCALES[scale_idx][1]  # updated at end of each capture

    # -- LCD layout ----------------------------------------------------------
    group, _ = lcd.make_group(Colors.BLACK)

    lcd.add_label(group, "ANALOG WAVEFORM EXPLORER",
                  120, 2, color=Colors.WHITE, scale=1)

    info_lbl = lcd.add_label(group, "",
                             120, 11, color=_COLORS[ch_idx], scale=1)

    scale_lbl = lcd.add_label(group, "",
                              120, 21, color=Colors.GRAY, scale=1)

    lcd.add_label(group, "PRESS=scale  HOLD=ch",
                  120, 124, color=Colors.GRAY, scale=1)

    # -- Waveform bitmap -----------------------------------------------------
    wave_bitmap  = displayio.Bitmap(WAVE_W, WAVE_H, 2)
    wave_palette = displayio.Palette(2)
    wave_palette[0] = 0x001018   # very dark background defines the waveform zone
    wave_palette[1] = _COLORS[ch_idx]

    group.append(displayio.TileGrid(
        wave_bitmap, pixel_shader=wave_palette, x=WAVE_X, y=WAVE_Y,
    ))

    # -- Inner helpers -------------------------------------------------------

    def scale_window_str():
        """Return a display string like '10ms/px  2.32s' for the current scale."""
        label, interval_us, _ = _SCALES[scale_idx]
        window_ms = WAVE_W * interval_us // 1000
        if window_ms >= 2000:
            return "{}  {:.2f}s".format(label, window_ms / 1000)
        if window_ms >= 1:
            return "{}  {}ms".format(label, window_ms)
        return "{}  {}us".format(label, WAVE_W * interval_us)

    def reset_trigger():
        nonlocal state, cap_count, frame_ready, pretrig_pos, pretrig_fill, prev_raw
        state        = _ST_ARMED
        cap_count    = 0
        frame_ready  = False
        pretrig_pos  = 0
        pretrig_fill = 0   # buffer contents are stale; disallow trigger until refilled
        prev_raw     = _ADC_MAX

    def switch_channel():
        nonlocal adc, ch_idx
        adc.deinit()
        ch_idx = (ch_idx + 1) % len(_PINS)
        adc    = AnalogInput(_PINS[ch_idx])
        wave_palette[1] = _COLORS[ch_idx]
        reset_trigger()

    def step_scale():
        nonlocal scale_idx, interval_ns, next_sample_ns
        scale_idx      = (scale_idx + 1) % len(_SCALES)
        interval_ns    = _SCALES[scale_idx][1] * 1000
        next_sample_ns = time.monotonic_ns()
        scale_lbl.text = scale_window_str()
        reset_trigger()

    def redraw():
        """Repaint the waveform bitmap from the frozen capture_buf.

        Reads linearly — no circular wrapping — because capture_buf is a
        complete, time-ordered frame.  Each column is a vertical bar from the
        previous sample's y to the current one so the trace is always connected.
        """
        wave_bitmap.fill(0)
        prev_y = None
        for x in range(WAVE_W):
            r  = capture_buf[x]
            yc = WAVE_H - 1 - int(r / _ADC_MAX * (WAVE_H - 1))
            if prev_y is None:
                y_lo = max(0, yc - 1)
                y_hi = min(WAVE_H - 1, yc + 1)
            else:
                y_lo = min(prev_y, yc)
                y_hi = max(prev_y, yc)
            bitmaptools.draw_line(wave_bitmap, x, y_lo, x, y_hi, 1)
            prev_y = yc

    # -- Initialise display --------------------------------------------------
    scale_lbl.text = scale_window_str()
    lcd.display.refresh()

    # -- Main loop -----------------------------------------------------------
    while True:
        now_ns = time.monotonic_ns()

        btn_tick += 1
        if btn_tick >= _BTN_EVERY:
            btn_tick = 0
            btn.update()

            if btn.fell:
                press_start = time.monotonic()

            if btn.rose and press_start is not None:
                held = time.monotonic() - press_start
                press_start = None
                if held >= _LONG_PRESS_S:
                    switch_channel()
                else:
                    step_scale()

        # ADC + trigger state machine
        if now_ns >= next_sample_ns:
            next_sample_ns = now_ns + interval_ns
            oversample = _SCALES[scale_idx][2]
            acc = 0
            for _ in range(oversample):
                acc += adc.raw
            raw = acc // oversample

            if state == _ST_ARMED:
                pretrig_buf[pretrig_pos] = raw
                pretrig_pos = (pretrig_pos + 1) % _PRETRIG
                if pretrig_fill < _PRETRIG:
                    pretrig_fill += 1

                if pretrig_fill >= _PRETRIG and raw >= threshold and prev_raw < threshold:
                    # Rising edge — buffer is full of fresh samples, safe to trigger
                    for i in range(_PRETRIG):
                        capture_buf[i] = pretrig_buf[(pretrig_pos + i) % _PRETRIG]
                    capture_buf[_PRETRIG] = raw
                    cap_count = 1
                    t_capture_start = now_ns
                    state = _ST_CAPTURE

            elif state == _ST_CAPTURE:
                capture_buf[_PRETRIG + cap_count] = raw
                cap_count += 1
                if cap_count >= WAVE_W - _PRETRIG:
                    # Compute actual average sample interval from measured elapsed time.
                    # (WAVE_W - _PRETRIG - 1) intervals span from trigger sample to last sample.
                    elapsed_ns = now_ns - t_capture_start
                    n_intervals = WAVE_W - _PRETRIG - 1
                    if elapsed_ns > 0 and n_intervals > 0:
                        actual_interval_us = elapsed_ns // (n_intervals * 1000)
                    frame_ready  = True
                    state        = _ST_ARMED
                    cap_count    = 0
                    pretrig_fill = 0   # entering ARMED fresh; refill before allowing trigger

            prev_raw = raw

        # LCD: refresh exactly once per captured frame, never during ARMED waiting.
        # Any lcd.display.refresh() blocks Python for ~101 ms (SPI write).  If that
        # gap landed in the ARMED pre-trigger window it would embed a mis-timed sample
        # in capture_buf and corrupt the left side of the waveform.  By only refreshing
        # when a new frame is ready we guarantee the pretrig buffer fills with
        # uninterrupted, evenly-spaced samples.
        loop_tick += 1
        if loop_tick >= _REFRESH_EVERY:
            loop_tick = 0
            if frame_ready and state != _ST_CAPTURE:
                redraw()
                frame_ready = False

                buf_min = min(capture_buf)
                buf_max = max(capture_buf)
                vpp = (buf_max - buf_min) * _VREF / _ADC_MAX

                # Period: distance from trigger point to the next rising edge crossing.
                # Use actual_interval_us (measured from capture timestamps) rather than
                # the nominal scale setting — at fast scales the ADC read time (~256 µs
                # for 4 oversamples) exceeds the nominal interval, so the real interval
                # is significantly longer than nominal and must be measured directly.
                interval_us = actual_interval_us
                period_samples = 0
                prev_s = capture_buf[_PRETRIG]
                for i in range(_PRETRIG + 1, WAVE_W):
                    curr_s = capture_buf[i]
                    if curr_s >= threshold and prev_s < threshold:
                        period_samples = i - _PRETRIG
                        break
                    prev_s = curr_s

                if period_samples > 0:
                    period_us = period_samples * interval_us
                    freq = 1_000_000 / period_us
                    if freq >= 1000:
                        f_str = "{:.1f}kHz".format(freq / 1000)
                    else:
                        f_str = "{:.1f}Hz".format(freq)
                    if period_us >= 1_000_000:
                        p_str = "{:.2f}s".format(period_us / 1_000_000)
                    elif period_us >= 1000:
                        p_str = "{:.1f}ms".format(period_us / 1000)
                    else:
                        p_str = "{:.0f}us".format(period_us)
                    fp_str = "{} {}".format(f_str, p_str)
                else:
                    fp_str = "---"

                info_lbl.text  = "{} {:.2f}Vpp {}".format(
                    _NAMES[ch_idx], vpp, fp_str)
                info_lbl.color = _COLORS[ch_idx]
                lcd.display.refresh()
                # Resync ADC timer and reset pretrig after the 101 ms SPI block.
                pretrig_fill   = 0
                next_sample_ns = time.monotonic_ns() + interval_ns
