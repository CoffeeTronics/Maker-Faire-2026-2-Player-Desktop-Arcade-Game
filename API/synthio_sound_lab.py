"""
synthio_sound_lab.py — Synthio Sound Lab
=========================================
Board: Dev Board / Ruler Baseboard

A real-time theremin-style synthesizer controlled by onboard sensors.
Tilt the board left/right to change pitch, tilt forward/back for volume,
and wave your hand over the proximity sensor to bend the note up.

Hardware
--------
  board.D3    — User button   (press  → cycle waveform)
  board.A5    — Cap touch pad (hold   → note ON, release → note OFF)
  board.DAC   — Speaker output (synthio audio chain)
  LCD         — 240 × 135 ST7789 via Ruler baseboard
  IMU         — ICM20948 on shared I2C bus
  APDS9960    — Proximity sensor on QWIIC / shared I2C bus

Controls
--------
  D3 press          : SINE → SQUARE → SAW → TRIANGLE (wraps)
  A5 hold           : note ON while touched; OFF on release (theremin model)
  Tilt left/right   : pitch C2–C6 across ±45° (Y-axis)
  Tilt forward/back : volume 0–100 % across 0–45° (X-axis, absolute)
  Hand closer       : pitch bends up by up to +2 semitones (proximity)

Display
-------
  WAVE row     : current waveform name, purple, scale 2
  NOTE row     : note name + frequency, cyan, scale 2
  VOL bar      : green bar, width proportional to volume
  BND bar      : orange bar, width proportional to pitch bend amount
  Pitch needle : cyan marker showing tilt_y position across track

Audio chain
-----------
  synthio.Synthesizer → audiomixer.Mixer → audioio.AudioOut(board.DAC)
  Sample rate: 22 050 Hz, mono 16-bit signed

MIDI output
-----------
  Sent on USB MIDI channel 1 if usb_midi is available.
  Note-on on A5 touch, note-off on release.
  Note changes while held send note-off / note-on pairs.

Example Usage
-----
import pykit_explorer
from synthio_sound_lab import run
run() 

"""

import array
import math
import board
import time
import displayio
import vectorio
import terminalio
from adafruit_display_text import label as _label

import audioio
import synthio

from lcd_display import LCDDisplay, Colors
from digital_io import EdgeDetector
from i2c_bus import I2CBus
from imu_sensor import IMUSensor
from apds9960 import APDS9960Sensor

# ---------------------------------------------------------------------------
# Optional MIDI output (channel 1)
# ---------------------------------------------------------------------------

try:
    import usb_midi
    _midi_out = usb_midi.ports[1]
except (ImportError, IndexError):
    _midi_out = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WAVE_NAMES   = ["SINE", "SQUA", "SAW ", "TRI "]

MIDI_LOW     = 74 #C6 #36 C2  — lowest note (tilt_y = -45°)
MIDI_HIGH    = 108 #C8 #84 C6  — highest note (tilt_y = +45°)
TILT_LOW     = -45.0    # degrees
TILT_HIGH    =  45.0    # degrees
TILT_VOL_MAX =  45.0    # degrees of |tilt_x| → full volume
TILT_VOL_DEAD =  3.0   # degrees — below this |tilt_x| = silence

ALPHA        = 0.2      # IIR smoothing coefficient for tilt_y

PROX_DEAD    = 10       # proximity values below this = no bend
PROX_MAX     = 255
BEND_ST_MAX  = 2.0      # max pitch bend in semitones

SAMPLE_RATE  = 22050
WAVE_LEN     = 256      # samples per waveform buffer

DISPLAY_INTERVAL = 0.10     # seconds between label text updates
PROX_INTERVAL    = 0.05     # seconds between proximity reads

# Deadbands — suppress updates smaller than these to prevent IMU jitter
# from causing audible micro-modulation of pitch and volume
FREQ_DEADBAND    = 1.5      # Hz  — ~1/40th semitone at C6, inaudible
AMP_DEADBAND     = 0.015    # 0–1 — 1.5% volume change minimum

# Display geometry (pixels)
BAR_LABEL_X  = 4
BAR_X        = 28
BAR_W        = 208
BAR_H        = 8
BAR_VOL_Y    = 56
BAR_BEND_Y   = 70
TRACK_X      = 4
TRACK_W      = 232
TRACK_H      = 2
NEEDLE_W     = 4
NEEDLE_H     = 10
NEEDLE_Y     = 84       # top of needle; track line at NEEDLE_Y + NEEDLE_H // 2

# ---------------------------------------------------------------------------
# Waveform buffers  (signed 16-bit, WAVE_LEN samples each)
# ---------------------------------------------------------------------------

def _make_sine() -> array.array:
    buf = array.array("h", [0] * WAVE_LEN)
    for i in range(WAVE_LEN):
        buf[i] = int(math.sin(math.pi * 2.0 * i / WAVE_LEN) * 32767)
    return buf


def _make_square() -> array.array:
    buf  = array.array("h", [0] * WAVE_LEN)
    half = WAVE_LEN // 2
    for i in range(WAVE_LEN):
        buf[i] = 32767 if i < half else -32767
    return buf


def _make_saw() -> array.array:
    buf = array.array("h", [0] * WAVE_LEN)
    for i in range(WAVE_LEN):
        buf[i] = int((i / (WAVE_LEN - 1)) * 65534 - 32767)
    return buf


def _make_triangle() -> array.array:
    buf  = array.array("h", [0] * WAVE_LEN)
    half = WAVE_LEN // 2
    for i in range(WAVE_LEN):
        if i < half:
            buf[i] = int((i / (half - 1)) * 65534 - 32767)
        else:
            buf[i] = int(((WAVE_LEN - 1 - i) / (half - 1)) * 65534 - 32767)
    return buf


# ---------------------------------------------------------------------------
# Note helpers
# ---------------------------------------------------------------------------

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _midi_to_hz(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz  (A4 = 440 Hz)."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def _note_name(midi_note: int) -> str:
    """Return a short note name, e.g. 'C4' or 'A#3'."""
    name   = _NOTE_NAMES[midi_note % 12]
    octave = (midi_note // 12) - 1
    return "{}{}".format(name, octave)


def _tilt_to_midi(tilt_y: float) -> int:
    """Map tilt_angle_y in degrees (clamped to ±45°) to a MIDI note number."""
    clamped = max(TILT_LOW, min(TILT_HIGH, tilt_y))
    span    = TILT_HIGH - TILT_LOW
    return int(MIDI_LOW + (clamped - TILT_LOW) / span * (MIDI_HIGH - MIDI_LOW))


# ---------------------------------------------------------------------------
# MIDI helpers
# ---------------------------------------------------------------------------

def _send_note_on(midi_note: int, velocity: int = 100):
    if _midi_out is not None:
        _midi_out.write(bytes([0x90, midi_note & 0x7F, velocity & 0x7F]))


def _send_note_off(midi_note: int):
    if _midi_out is not None:
        _midi_out.write(bytes([0x80, midi_note & 0x7F, 0]))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    """Initialise hardware and enter the Synthio Sound Lab main loop.

    Blocks indefinitely — call this as the last statement in code.py.
    """

    # -- Waveforms -----------------------------------------------------------
    waveforms = [_make_sine(), _make_square(), _make_saw(), _make_triangle()]

    # -- Audio chain ---------------------------------------------------------
    # No audiomixer — drive AudioOut directly from synthio.
    # Volume is controlled via note.amplitude (0.0–1.0) instead.
    audio = audioio.AudioOut(board.DAC)
    synth = synthio.Synthesizer(sample_rate=SAMPLE_RATE)
    audio.play(synth)

    # -- Synthio note --------------------------------------------------------
    current_note = synthio.Note(frequency=_midi_to_hz(60), waveform=waveforms[0],
                                amplitude=0.0)

    # -- Hardware ------------------------------------------------------------
    lcd  = LCDDisplay()
    btn  = EdgeDetector(board.D3)
    i2c  = I2CBus()
    imu  = IMUSensor(i2c=i2c.bus)
    apds = APDS9960Sensor(i2c.bus)
    apds.enable_proximity()

    lcd.backlight_on()

    # -- LCD layout ----------------------------------------------------------
    #
    #   y=  2  "SYNTHIO SOUND LAB"    scale=1  white
    #   y= 14  "WAVE  SINE"           scale=2  purple
    #   y= 34  "NOTE C4    262Hz"     scale=2  cyan
    #   y= 56  VOL  bar (green,  8 px)
    #   y= 70  BND  bar (orange, 8 px)
    #   y= 84  pitch needle (cyan, 4×10 px) on track (gray, 2 px)
    #   y=120  "D3=wave   A5=play"    scale=1  gray
    #
    group, _ = lcd.make_group(Colors.BLACK)

    lcd.add_label(group, "SYNTHIO SOUND LAB",
                  120,   2, color=Colors.WHITE,  scale=1)
    wave_lbl = lcd.add_label(group, "WAVE  SINE",
                              120,  14, color=Colors.PURPLE, scale=2)
    note_lbl = lcd.add_label(group, "NOTE C4    262Hz",
                              120,  34, color=Colors.CYAN,   scale=2)
    lcd.add_label(group, "D3=wave   TILT=vol",
                  120, 120, color=Colors.GRAY,   scale=1)

    # Small left-aligned bar labels ("VOL" / "BND")
    group.append(_label.Label(
        terminalio.FONT, text="VOL", color=Colors.GRAY, scale=1,
        anchor_point=(0.0, 0.0), anchored_position=(BAR_LABEL_X, BAR_VOL_Y)))
    group.append(_label.Label(
        terminalio.FONT, text="BND", color=Colors.GRAY, scale=1,
        anchor_point=(0.0, 0.0), anchored_position=(BAR_LABEL_X, BAR_BEND_Y)))

    # -- Vectorio bars and needle --------------------------------------------

    vol_pal     = displayio.Palette(2)
    vol_pal[0]  = 0x003000   # dark green (background)
    vol_pal[1]  = 0x00CC00   # green (fill)

    bend_pal    = displayio.Palette(2)
    bend_pal[0] = 0x200800   # dark orange (background)
    bend_pal[1] = 0xFF6000   # orange (fill)

    track_pal    = displayio.Palette(1)
    track_pal[0] = 0x222222  # dark grey track line

    needle_pal    = displayio.Palette(1)
    needle_pal[0] = 0x00FFFF  # cyan needle

    # VOL bar: background then fill (fill drawn on top)
    group.append(vectorio.Rectangle(
        pixel_shader=vol_pal, color_index=0,
        x=BAR_X, y=BAR_VOL_Y, width=BAR_W, height=BAR_H))
    vol_rect = vectorio.Rectangle(
        pixel_shader=vol_pal, color_index=1,
        x=BAR_X, y=BAR_VOL_Y, width=1, height=BAR_H)
    vol_rect.hidden = True
    group.append(vol_rect)

    # BEND bar: background then fill
    group.append(vectorio.Rectangle(
        pixel_shader=bend_pal, color_index=0,
        x=BAR_X, y=BAR_BEND_Y, width=BAR_W, height=BAR_H))
    bend_rect = vectorio.Rectangle(
        pixel_shader=bend_pal, color_index=1,
        x=BAR_X, y=BAR_BEND_Y, width=1, height=BAR_H)
    bend_rect.hidden = True
    group.append(bend_rect)

    # Pitch track (thin horizontal line at the vertical midpoint of the needle)
    group.append(vectorio.Rectangle(
        pixel_shader=track_pal, color_index=0,
        x=TRACK_X, y=NEEDLE_Y + NEEDLE_H // 2,
        width=TRACK_W, height=TRACK_H))

    # Pitch needle (moves horizontally)
    needle_rect = vectorio.Rectangle(
        pixel_shader=needle_pal, color_index=0,
        x=TRACK_X, y=NEEDLE_Y, width=NEEDLE_W, height=NEEDLE_H)
    group.append(needle_rect)

    # -- State ---------------------------------------------------------------
    wave_idx      = 0
    smooth_tilt_y = 0.0
    smooth_tilt_x = 0.0
    current_midi  = 60          # last MIDI note sent to MIDI out
    prox          = 0
    last_freq     = 0.0         # last value written to current_note.frequency
    last_amp      = 0.0         # last value written to current_note.amplitude
    next_display  = time.monotonic()
    next_prox     = time.monotonic()

    # Note plays continuously; volume (note.amplitude) acts as the gate
    synth.press(current_note)
    _send_note_on(current_midi)

    # -- Main loop -----------------------------------------------------------
    while True:
        now = time.monotonic()

        btn.update()

        # D3: cycle waveform
        if btn.fell:
            wave_idx = (wave_idx + 1) % len(WAVE_NAMES)
            current_note.waveform = waveforms[wave_idx]
            wave_lbl.text = "WAVE  {}".format(WAVE_NAMES[wave_idx])

        # -- IMU: compute pitch (tilt_y) and volume (tilt_x) -----------------
        raw_tilt_y    = imu.tilt_angle_y
        raw_tilt_x    = imu.tilt_angle_x
        smooth_tilt_y = ALPHA * raw_tilt_y + (1.0 - ALPHA) * smooth_tilt_y
        smooth_tilt_x = ALPHA * raw_tilt_x + (1.0 - ALPHA) * smooth_tilt_x

        midi_note      = _tilt_to_midi(smooth_tilt_y)
        base_freq      = _midi_to_hz(midi_note)
        clamped_tilt_y = max(TILT_LOW, min(TILT_HIGH, smooth_tilt_y))

        vol_tilt = abs(smooth_tilt_x)
        if vol_tilt < TILT_VOL_DEAD:
            volume = 0.0
        else:
            volume = min(vol_tilt, TILT_VOL_MAX) / TILT_VOL_MAX
        if abs(volume - last_amp) >= AMP_DEADBAND:
            current_note.amplitude = volume
            last_amp = volume

        # -- Proximity: pitch bend (throttled read) ---------------------------
        if now >= next_prox:
            prox      = apds.proximity
            next_prox = now + PROX_INTERVAL

        if prox >= PROX_DEAD:
            bend_st = (prox - PROX_DEAD) / (PROX_MAX - PROX_DEAD) * BEND_ST_MAX
        else:
            bend_st = 0.0

        # -- Update synthio note frequency ------------------------------------
        new_freq = base_freq * (2.0 ** (bend_st / 12.0))
        if abs(new_freq - last_freq) >= FREQ_DEADBAND:
            current_note.frequency = new_freq
            last_freq = new_freq

        # -- Update vectorio graphics -----------------------------------------

        # Pitch needle: maps clamped_tilt_y to x position across TRACK_W
        needle_x      = int(TRACK_X + (clamped_tilt_y - TILT_LOW)
                            / (TILT_HIGH - TILT_LOW) * (TRACK_W - NEEDLE_W))
        needle_rect.x = needle_x

        # VOL bar fill width
        vol_w = int(volume * BAR_W)
        if vol_w > 0:
            vol_rect.width  = vol_w
            vol_rect.hidden = False
        else:
            vol_rect.hidden = True

        # BEND bar fill width
        bend_w = int(bend_st / BEND_ST_MAX * BAR_W)
        if bend_w > 0:
            bend_rect.width  = bend_w
            bend_rect.hidden = False
        else:
            bend_rect.hidden = True

        # -- Throttled label updates ------------------------------------------
        if now >= next_display:
            next_display = now + DISPLAY_INTERVAL

            note_lbl.text = "NOTE {:3s} {:5d}Hz".format(
                _note_name(midi_note), int(base_freq))

            # Track MIDI note changes and send MIDI output
            if midi_note != current_midi:
                _send_note_off(current_midi)
                _send_note_on(midi_note)
                current_midi = midi_note
