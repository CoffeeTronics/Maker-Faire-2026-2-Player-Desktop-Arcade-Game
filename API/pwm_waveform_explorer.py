"""
pwm_waveform_explorer.py — PWM Waveform Explorer
==================================================
Board: Dev Board / Ruler Baseboard

An interactive oscilloscope-style tool for exploring PWM signals.
Students adjust frequency and duty cycle with two controls and see the
result on the LCD, hear the tone through the speaker, and observe duty
cycle as LED brightness — three simultaneous feedback channels.

Hardware
--------
  board.D3    — User button   (press  → step frequency preset)
  board.A5    — Cap touch pad (touch  → step duty cycle + 10 %)
  board.LED   — On-board LED  (brightness tracks duty cycle)
  board.DAC   — Speaker output (sine tone at selected frequency)
  LCD         — 240 × 135 ST7789 via Ruler baseboard

Controls
--------
  D3 press   : 100 → 200 → 500 → 1k → 2k → 3k Hz  (wraps)
  A5 touch   : 0 → 10 → 20 → … → 100 → 0 %         (wraps)

Display behaviour
-----------------
  Option B — Row flash   : changed-parameter row briefly whites out
  Option D — Running wave: waveform scrolls continuously left;
             shape updates instantly on any parameter change

  The waveform uses vectorio rectangles — three for HIGH segments
  (bright green, top bar) and three for LOW segments (dim green,
  bottom bar).  Each frame only x and width are updated; no string
  building or label redraws.

Waveform geometry (px)
-----------------------
  Waveform zone  : x=4, y=56, w=232, h=50
  HIGH bar       : y=56, h=5    (bright green)
  LOW bar        : y=101, h=5   (dim green)
  Dark gap       : y=61 – y=101 (background shows between bars)
  2 periods shown across 232 px  →  116 px per period

Notes
-----
  Audio degrades above ~2 kHz because the DAC sine buffer shrinks to
  very few samples at higher frequencies (8 000 Hz sample rate cap).
  The LCD waveform and LED remain accurate at all frequencies.

Example Usage
-----
import pykit_explorer
from pwm_waveform_explorer import run
run()

"""

import board
import digitalio
import displayio
import vectorio
import time
from lcd_display import LCDDisplay, Colors
from digital_io import EdgeDetector
from cap_touch import CapTouch
from audio_out import AudioOutput

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FREQ_PRESETS   = [100, 200, 500, 1000, 2000, 3000]  # Hz
DUTY_STEPS     = list(range(0, 101, 10))             # 0, 10, 20 … 100 %

PERIOD_CHARS   = 9     # phase steps per waveform period (controls scroll speed)
SHIFT_INTERVAL = 0.07  # seconds between phase steps
FLASH_DURATION = 0.15  # seconds for the row-highlight flash
AUDIO_VOLUME   = 0.25  # peak sine volume (0.0 – 1.0); scaled by duty cycle

# Waveform display geometry (all in pixels)
WAVE_X    = 4           # left edge
WAVE_W    = 232         # width  (4 px margin each side of 240 px display)
WAVE_Y    = 56          # top of waveform zone
WAVE_H    = 50          # total height of waveform zone
HIGH_H    = 5           # height of HIGH signal bar
LOW_H     = 5           # height of LOW signal bar
HIGH_Y    = WAVE_Y                       # top of HIGH bar
LOW_Y     = WAVE_Y + WAVE_H - LOW_H     # top of LOW bar  (= 88)
PERIOD_PX = WAVE_W // 2                 # pixels per period (= 116)

# Waveform palette indices
_BG   = 0   # very dark green — background / dead zone
_HIGH = 1   # bright green    — HIGH signal
_LOW  = 2   # dim green       — LOW signal

# ---------------------------------------------------------------------------
# Bit-bang PWM  (board.LED does not support hardware PWM)
# ---------------------------------------------------------------------------

class BitBangPWM:
    """Flicker-free LED brightness control using a sigma-delta accumulator.

    A time-based PWM approach fails here because the main loop is too slow
    relative to any useful PWM frequency: the LCD SPI refresh takes ~5 ms per
    iteration, so a 5 000 Hz period (200 µs) produces 25 full cycles between
    each update() call.  The pin only switches when update() runs, so the
    output is effectively random — hence the visible flicker.

    Sigma-delta sidesteps this entirely.  On every update() call, the duty
    fraction is added to an accumulator.  When the accumulator reaches 1.0 the
    pin goes HIGH and the accumulator wraps.  Over any N calls, exactly
    round(duty * N) of them will be HIGH, regardless of how fast or slowly the
    main loop runs.  This gives the smoothest possible brightness at whatever
    rate update() is actually called.

    The duty_cycle property matches the pwmio.PWMOut interface (0 – 65535).
    """

    def __init__(self, pin):
        self._pin = digitalio.DigitalInOut(pin)
        self._pin.direction = digitalio.Direction.OUTPUT
        self._pin.value = False
        self._duty        = 0.0   # 0.0 – 1.0
        self._accumulator = 0.0

    @property
    def duty_cycle(self) -> int:
        """Raw duty cycle (0 – 65535)."""
        return int(self._duty * 65535)

    @duty_cycle.setter
    def duty_cycle(self, value: int):
        self._duty = max(0, min(65535, int(value))) / 65535

    def update(self):
        """Advance the accumulator and set the pin.  Call every main-loop iteration."""
        self._accumulator += self._duty
        if self._accumulator >= 1.0:
            self._pin.value = True
            self._accumulator -= 1.0
        else:
            self._pin.value = False

    def deinit(self):
        self._pin.value = False
        self._pin.deinit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    """Initialise hardware and enter the PWM Waveform Explorer main loop.

    Blocks indefinitely — call this as the last statement in code.py.
    """

    # -- Hardware ------------------------------------------------------------
    lcd   = LCDDisplay()
    btn   = EdgeDetector(board.D3)
    cap   = CapTouch(board.A5)
    audio = AudioOutput()
    led   = BitBangPWM(board.LED)

    lcd.backlight_on()

    # -- State ---------------------------------------------------------------
    freq_idx     = 3      # start at 1 000 Hz
    duty_idx     = 5      # start at 50 %
    flash_until  = 0.0
    flash_target = "none"   # "freq" | "duty" | "none"

    # -- LCD layout ----------------------------------------------------------
    #
    #   y=  2  "PWM WAVEFORM EXPLORER"      scale=1  white
    #   y= 14  "FREQ   1000 Hz"             scale=2  cyan
    #   y= 34  "DUTY     50 %"              scale=2  yellow
    #   y= 56  ══ HIGH bar (vectorio) ══     5 px    bright green
    #   y= 61  ── dark gap ──              40 px    background
    #   y=101  ══ LOW  bar (vectorio) ══    5 px    dim green
    #   y=120  "D3=freq   A5=duty"          scale=1  gray
    #
    group, _ = lcd.make_group(Colors.BLACK)

    lcd.add_label(group, "PWM WAVEFORM EXPLORER",
                  120,   2, color=Colors.WHITE,  scale=1)
    freq_lbl = lcd.add_label(group, "",
                             120,  14, color=Colors.CYAN,   scale=2)
    duty_lbl = lcd.add_label(group, "",
                             120,  34, color=Colors.YELLOW, scale=2)
    lcd.add_label(group, "USER=freq   CAP TOUCH=duty",
                  120, 120, color=Colors.GRAY,   scale=1)

    # -- Waveform vectorio setup ---------------------------------------------

    wave_pal    = displayio.Palette(3)
    wave_pal[_BG]   = 0x000800   # very dark green
    wave_pal[_HIGH] = 0x00FF00   # bright green
    wave_pal[_LOW]  = 0x004000   # dim green

    # Background fills the entire waveform zone
    group.append(vectorio.Rectangle(
        pixel_shader=wave_pal, color_index=_BG,
        x=WAVE_X, y=WAVE_Y, width=WAVE_W, height=WAVE_H,
    ))

    # Three rects for HIGH segments; three for LOW segments.
    # Pre-created hidden — update_wave() positions and reveals them each frame.
    high_rects = []
    for _ in range(3):
        r = vectorio.Rectangle(
            pixel_shader=wave_pal, color_index=_HIGH,
            x=WAVE_X, y=HIGH_Y, width=1, height=HIGH_H,
        )
        r.hidden = True
        group.append(r)
        high_rects.append(r)

    low_rects = []
    for _ in range(3):
        r = vectorio.Rectangle(
            pixel_shader=wave_pal, color_index=_HIGH,
            x=WAVE_X, y=LOW_Y, width=1, height=LOW_H,
        )
        r.hidden = True
        group.append(r)
        low_rects.append(r)

    # -- Inner helpers -------------------------------------------------------

    def update_wave(duty_pct, phase):
        """Reposition HIGH and LOW rectangles for the current duty/phase.

        Parameters
        ----------
        duty_pct : duty cycle percentage (0 – 100)
        phase    : scroll step index (0 … PERIOD_CHARS-1)

        For each of four candidate periods (-1, 0, 1, 2) the HIGH and LOW
        segments are clipped to the visible window [WAVE_X, WAVE_X+WAVE_W].
        Up to three clipped segments of each type are assigned to the
        pre-allocated rectangles; any unused rects are hidden.
        """
        high_px   = round(duty_pct / 100 * PERIOD_PX)
        low_px    = PERIOD_PX - high_px
        phase_off = round(phase / PERIOD_CHARS * PERIOD_PX)

        hi_idx = lo_idx = 0

        for n in range(-1, 3):
            origin = WAVE_X + n * PERIOD_PX - phase_off

            # HIGH segment: starts at origin, width = high_px
            x0 = max(WAVE_X, origin)
            x1 = min(WAVE_X + WAVE_W, origin + high_px)
            if x1 > x0 and hi_idx < 3:
                r = high_rects[hi_idx]
                r.x = x0
                r.width = x1 - x0
                r.hidden = False
                hi_idx += 1

            # LOW segment: starts at origin + high_px, width = low_px
            x0 = max(WAVE_X, origin + high_px)
            x1 = min(WAVE_X + WAVE_W, origin + high_px + low_px)
            if x1 > x0 and lo_idx < 3:
                r = low_rects[lo_idx]
                r.x = x0
                r.width = x1 - x0
                r.hidden = False
                lo_idx += 1

        for i in range(hi_idx, 3):
            high_rects[i].hidden = True
        for i in range(lo_idx, 3):
            low_rects[i].hidden = True

    def apply_settings(flash="none"):
        nonlocal flash_until, flash_target

        freq = FREQ_PRESETS[freq_idx]
        duty = DUTY_STEPS[duty_idx]

        freq_lbl.text  = "FREQ {:>5} Hz".format(freq)
        duty_lbl.text  = "DUTY {:>4} %".format(duty)
        led.duty_cycle = int(duty / 100 * 65535)

        if duty == 0:
            audio.stop()
        else:
            vol = max(0.05, (duty / 100) * AUDIO_VOLUME)
            audio.play_tone(freq, volume=vol)

        if flash == "freq":
            freq_lbl.color = Colors.WHITE
            flash_until    = time.monotonic() + FLASH_DURATION
            flash_target   = "freq"
        elif flash == "duty":
            duty_lbl.color = Colors.WHITE
            flash_until    = time.monotonic() + FLASH_DURATION
            flash_target   = "duty"

    # -- Initialise ----------------------------------------------------------
    phase      = 0
    next_shift = time.monotonic()

    update_wave(DUTY_STEPS[duty_idx], phase)
    apply_settings()

    # -- Main loop -----------------------------------------------------------
    while True:
        now = time.monotonic()

        btn.update()
        cap.update()
        led.update()

        if btn.fell:                                 # D3 → next frequency
            freq_idx = (freq_idx + 1) % len(FREQ_PRESETS)
            apply_settings(flash="freq")

        if cap.just_touched:                         # A5 → next duty cycle
            duty_idx = (duty_idx + 1) % len(DUTY_STEPS)
            update_wave(DUTY_STEPS[duty_idx], phase)
            apply_settings(flash="duty")

        if flash_target != "none" and now >= flash_until:   # Option B: restore
            if flash_target == "freq":
                freq_lbl.color = Colors.CYAN
            else:
                duty_lbl.color = Colors.YELLOW
            flash_target = "none"

        if now >= next_shift:                        # Option D: scroll
            phase      = (phase + 1) % PERIOD_CHARS
            update_wave(DUTY_STEPS[duty_idx], phase)
            next_shift = now + SHIFT_INTERVAL
