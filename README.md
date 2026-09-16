# PyKit Ruler — CircuitPython Module Library

Before starting, please read the **PyKit_Python_Primer_Print_Friendly.pdf** file. Open it in your PDF reader or browser of choice.

**Note:** You do **NOT** need to be proficient in Python programming to use this kit. The PyKit_Python_Primer_Print_Friendly document
teaches everything you to know to use this kit and build cool projects.

**Important Note:**  If you have problems after downloading the GitHub repo, when opening the PowerPoint file where the file gives the message: "PowerPoint found a problem with content.....PowerPoint can attempt to repair the file"
in the GitHub repo, click on the link to the file *UC_CircuitPython_Workshop.pptx* and click the **Download raw file** button to download the file. Then open normally.

## Workshop/Hackathon Reference

This library provides APIs for all of the hardware on the Microchip Curiosity PyKit Explorer.

- **Module Quick Reference** — find out what each module can do
- **Choosing Modules for Your Project** — work out which modules you need for a specific purpose
- **Minimal Examples** — copy-paste starting points to get up and running quickly

---

## Game Launcher

The default `code.py` is a **unified game launcher** that automatically discovers and cycles through games in the `/games/` folder. Press **Button C (Select)** at any time to switch to the next game.

### Included Games

| Game       | Description                                                      | Controls                                                              | Lives |
| ---------- | ---------------------------------------------------------------- | --------------------------------------------------------------------- | ----- |
| **Snake**  | Classic snake game — eat food to grow, avoid walls and yourself  | Joystick to move, A to toggle demo mode, D to start                   | 3     |
| **Tetris** | Horizontal Tetris — pieces move left to right                    | Joystick Up/Down to move, Right for soft drop, A to rotate, B to drop | —     |
| **Pong**   | Classic paddle game vs AI opponent                               | Joystick Up/Down to move paddle, A or D to start                      | —     |

### Game Flow

1. **Transition Screen** — Shows "Next game..." with the game name for 3 seconds
2. **Splash Screen** — Each game displays its unique splash screen BMP
3. **Gameplay** — Play until game over or press Button C (Select) to switch
4. **Game Over Screen** — Shows game-specific game over BMP with audio
5. **Return to Launcher** — Automatically cycles to the next game

### Assets

#### Audio Files (`/AudioFiles/`)

| File                                   | Used By       | Description         |
| -------------------------------------- | ------------- | ------------------- |
| `210.wav`                              | Snake, Tetris, Pong | Food/rotate/hit SFX |
| `140.wav`                              | Snake         | Game over sound     |
| `Tetris (GB) (21)-line_clear.wav`      | Tetris        | Line clear sound    |
| `Tetris (GB) (27)-piece_landed.wav`    | Tetris        | Piece landed sound  |
| `gameover_man.wav`                     | Tetris, Pong  | Game over sound     |
| `smb_coin.wav`                         | Pong          | Score sound         |

> **Audio Format**: All WAV files must be **mono, 16-bit PCM, 22050 Hz** for CircuitPython compatibility.

#### Legacy Assets (`/Sprites/`)

The following BMP files are included for future games or reference but are not used by the current game launcher:

- `snake_splash.bmp`, `SI_splash.bmp`, `mario_splash.bmp` — Splash screens
- `Game_Over_Snake.bmp`, `Game_Over_SI.bmp`, `Game_Over_SMB.bmp` — Game over screens

Current games (Snake, Tetris, Pong) use programmatically-drawn splash and game over screens to conserve memory.

### High Scores

High scores are stored in non-volatile memory (NVM) and persist across power cycles. Each game has a dedicated slot:

| Slot | Game                    |
| ---- | ----------------------- |
| 0    | Snake                   |
| 1    | Tetris                  |
| 2    | Pong                    |
| 3-29 | Available for new games |

### Adding New Games

See **[games/GAME_README.md](games/GAME_README.md)** for detailed instructions on creating and adding your own games to the launcher.

---

## Hardware Pin Assignments

Pin assignments for the Mini Arcade Cabinet hardware on Curiosity PyKit Explorer.

### RGB Matrix Display (64x32 HUB75)

| Function | PyKit Pin | MCU Pin |
| -------- | --------- | ------- |
| R1       | A0        | PB04    |
| G1       | A1        | PB05    |
| B1       | A2        | PB06    |
| R2       | A3        | PB07    |
| G2       | A4        | PB08    |
| B2       | A5        | PB09    |
| CLK      | D8        | PB00    |
| LAT      | D9        | PB01    |
| OE       | D13       | PB23    |
| ADDR A   | D0        | —       |
| ADDR B   | D1        | —       |
| ADDR C   | D2        | —       |
| ADDR D   | D3        | —       |

> **Note:** ADDR D (D3) is only used for panels taller than 16 pixels (e.g., 32-row panels).

### Joystick (4-Direction Digital)

| Direction | PyKit Pin  | Pull   |
| --------- | ---------- | ------ |
| Up        | LCD_SCK    | DOWN   |
| Down      | LCD_CS     | DOWN   |
| Left      | LCD_BL     | DOWN   |
| Right     | LCD_MOSI   | DOWN   |

All joystick inputs are **active HIGH** with internal pull-down resistors.

### Arcade Buttons

| Button   | PyKit Pin | Function      | Pull   |
| -------- | --------- | ------------- | ------ |
| A        | D4        | Action 1      | DOWN   |
| B        | D5        | Action 2      | DOWN   |
| C        | D6        | Select        | DOWN   |
| D        | D7        | Start / Switch Game | DOWN |

All button inputs are **active HIGH** with internal pull-down resistors.

### Audio Output

Audio is output via the built-in DAC on `board.DAC` (pin PA02).

---

## Directory Layout

All modules live flat in `/API` on the CIRCUITPY drive (Adafruit libraries stay in `/lib`):

```text
CIRCUITPY/
├── code.py                  ← Unified game launcher
├── base_game.py             ← Base class for all games
├── high_scores.py           ← NVM high score manager
├── games/                   ← Game folder (auto-discovered)
│   ├── GAME_README.md       ← Instructions for adding games
│   ├── snake/               ← Snake game
│   ├── space_impact/        ← Space Impact game
│   └── mario/               ← Super Mario game
├── Sprites/                 ← BMP images (splash screens, sprites)
├── AudioFiles/              ← WAV audio files (mono, 22050Hz)
├── lib/                     ← Adafruit / third-party libraries
│   ├── asyncio/
│   ├── adafruit_st7789.mpy
│   └── ...
└── API/                     ← PyKit Ruler modules
    ├── digital_io.py        ← Dev board modules
    ├── analog_io.py
    ├── pwm_out.py
    ├── cap_touch.py
    ├── servo_control.py
    ├── uart_comms.py
    ├── i2c_bus.py
    ├── spi_bus.py
    ├── hid_input.py
    ├── cpu_temp.py
    ├── ble_uart.py
    ├── can_bus.py
    ├── neopixels.py         ← Ruler baseboard modules
    ├── lcd_display.py
    ├── imu_sensor.py
    ├── audio_out.py
    ├── sd_card.py
    ├── bme680.py            ← I2C breakout modules (QWIIC)
    ├── apds9960.py
    ├── async_tasks.py       ← Utility modules
    ├── pwm_waveform_explorer.py  ← Tools
    ├── analog_waveform_explorer.py
    └── synthio_sound_lab.py
```

---

## Module Quick Reference

### Dev Board Modules

| Module            | Class(es)                                             | What it does                                                                          |
| ----------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `digital_io`    | `DigitalOutput`, `DigitalInput`, `EdgeDetector` | Read buttons/switches; drive LEDs and relays; detect press/release edges              |
| `analog_io`     | `AnalogInput`, `AnalogOutput`                     | Read voltages from sensors (A0–A5); output DC voltage from DAC (board.DAC only)      |
| `pwm_out`       | `PWMOutput`                                         | Variable duty-cycle signal; LED dimming; buzzer tones; motor speed control            |
| `cap_touch`     | `CapTouch`                                          | Capacitive touch detect/release on board.A5 (CAP1)                                    |
| `servo_control` | `ServoController`                                   | Position standard RC servo 0°–180°; sweep animations                               |
| `uart_comms`    | `UARTComms`                                         | Send/receive strings over hardware UART (DEBUG or any UART)                           |
| `i2c_bus`       | `I2CBus`                                            | Scan I2C bus; raw register reads/writes; returns bus object for Adafruit drivers      |
| `hid_input`     | `HIDKeyboard`, `HIDMouse`, `JoystickMouse`      | USB HID keyboard typing and key combos; mouse movement and clicks; joystick → mouse  |
| `cpu_temp`      | `CPUTemperature`                                    | On-chip temperature in °C and °F; threshold checks; formatted logging strings       |
| `ble_uart`      | `BLEUart`                                           | Reset RNBD451 BLE module; send/receive strings wirelessly; connection status tracking |
| `spi_bus`       | `SPIBus`                                            | General-purpose SPI transactions with automatic CS and bus locking                    |
| `can_bus`       | `CANBus`                                            | Send and receive CAN frames at 250 kbps; bus state monitoring                         |

### Ruler Baseboard Modules

| Module          | Class(es)       | What it does                                                                                                                                                                                                                                        |
| --------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `neopixels`   | `NeoPixels`   | Drive 5 RGB LEDs; solid colours; chase, rainbow, pulse animations; bar-graph value mapping                                                                                                                                                          |
| `lcd_display` | `LCDDisplay`  | Init 240×135 ST7789 LCD; backlight control;`make_group()` creates a persistent display group with swappable background colour; `add_label()` adds a centred text label to a group; load & position BMP sprites; bounce and IMU-driven movement |
| `imu_sensor`  | `IMUSensor`   | Read acceleration, gyro, magnetometer; tilt angles; tilt direction; sprite delta for IMU controls                                                                                                                                                   |
| `audio_out`   | `AudioOutput` | Sine tone generation at any frequency; WAV file playback; play scales                                                                                                                                                                               |
| `sd_card`     | `SDCard`      | Mount SD card; read/write/append text files; CSV data logging; filesystem utilities                                                                                                                                                                 |

### I2C Breakout Modules (QWIIC)

Both breakout modules require an `I2CBus` instance from `i2c_bus.py`. Pass its
`.bus` property when constructing a sensor object.

| Module       | Class(es)          | What it does                                                                                                                                                                                                                    |
| ------------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bme680`   | `BME680Sensor`   | Read temperature, humidity, barometric pressure (sea-level adjusted), and gas resistance (VOC / air quality); threshold level helpers; formatted strings for LCD or logging                                                     |
| `apds9960` | `APDS9960Sensor` | Three modes switchable at runtime:**Proximity** (0–255 distance), **Gesture** (UP/DOWN/LEFT/RIGHT swipe detection), **Color** (16-bit RGBC with 8-bit NeoPixel conversion); constants for all gesture values |

### Utility Modules

| Module          | Class(es)       | What it does                                                                             |
| --------------- | --------------- | ---------------------------------------------------------------------------------------- |
| `async_tasks` | `AsyncRunner` | Lightweight asyncio wrapper; add coroutines and run them concurrently with a single call |

### Tools

Ready-to-run programs that combine multiple modules. Each exposes a single
`run()` entry point.

| Tool                         | What it does                                                                                                                                                                                                    |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pwm_waveform_explorer`    | Interactive oscilloscope: D3 steps frequency (100–3 kHz), A5 steps duty cycle (0–100 %);`<br>`live waveform on LCD, sine tone through speaker, LED brightness tracks duty cycle                           |
| `analog_waveform_explorer` | Triggered oscilloscope: short press D3 steps timebase (10 ms/px → 200 µs/px), long press cycles channels A0–A5; displays Vpp, frequency, and period; per-channel colour coding; max useful signal ~400 Hz |
| `synthio_sound_lab`        | Theremin synthesiser: IMU tilt y → pitch, tilt x → volume (3° dead zone), APDS proximity → pitch bend up;`<br>`D3 cycles waveform (SINE/SQUA/SAW/TRI); optional USB MIDI output                         |

---

## Choosing Modules for Your Project

Think through what your project needs to **sense**, **process**, and **output**:

```
INPUTS                          OUTPUTS
──────                          ───────
digital_io   ← buttons          digital_io    → LEDs, relays
analog_io    ← sensors          pwm_out       → motors, buzzers
cap_touch    ← touch pad        servo_control → servo position
imu_sensor   ← motion/tilt      neopixels     → RGB feedback
bme680       ← temp/humidity    lcd_display   → graphics
apds9960     ← proximity        audio_out     → sound / music
apds9960     ← gesture          ble_uart      → wireless data
apds9960     ← color            sd_card       → data logging
i2c_bus      ← I2C devices      hid_input     → PC automation
spi_bus      ← SPI devices      synthio       → real-time synthesis
uart_comms   ← serial devices
can_bus      ← CAN network
```

Common multi-module patterns:

| Goal                 | Modules                                                          |
| -------------------- | ---------------------------------------------------------------- |
| Theremin synthesiser | `imu_sensor` + `apds9960` + `synthio` + `lcd_display`    |
| PWM visualiser       | `digital_io` + `cap_touch` + `audio_out` + `lcd_display` |
| Data logger          | `bme680` + `sd_card` + `lcd_display`                       |
| BLE sensor stream    | `imu_sensor` + `bme680` + `ble_uart`                       |
| Gesture game         | `apds9960` + `neopixels` + `lcd_display`                   |

---

## How to use the API

1. At the top of `code.py`, add `import pykit_explorer`. This allows the user to leverage the functionality of the API to greatly simplify their project.
2. To use individual libraries in the API, import that filename and the name of the class and/or variables you want to use. See example below.

```python
import pykit_explorer
from digital_io import DigitalInput, EdgeDetector
from neopixels  import NeoPixels, RED, GREEN
from imu_sensor import IMUSensor
```

3. You do **not** need to copy modules you are not using.

---

## Minimal Example #1 — Blink the onboard LED

```python
import pykit_explorer
from digital_io import DigitalOutput

led = DigitalOutput(board.LED)

while True:
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)
```

## Minimal Example #2 — Read User Button

```python
import pykit_explorer
from digital_io import DigitalInput

btn = DigitalInput(board.D3)

while True:
    print(f'Value:	    {btn.value}')
    print(f'is pressed: {btn.is_pressed()}')
```

---

## Minimal Example #3 — Toggle LED on button press

```python
import pykit_explorer
from digital_io import DigitalOutput, EdgeDetector

led = DigitalOutput(board.LED)
btn = EdgeDetector(board.D3)

while True:
    btn.update()
    if btn.fell:
        led.toggle()
    time.sleep(0.01)
```

---

## Minimal Example #4 — NeoPixels

```python
import pykit_explorer
from neopixels import NeoPixels, Colors

px = NeoPixels()  # 5 LEDs, brightness 0.1

px.fill(Colors.RED)
print("All Neopixels should be red")
time.sleep(1)
px.set(2, Colors.GREEN)
print("Pixel 2 should be green")
time.sleep(1)
px.color_chase(Colors.BLUE)
print("Neopixels should chase blue")
px.rainbow_cycle(cycles=2)
print("Neopixels should cycle through rainbow colors")
px.off()
```

---

## Minimal Example #5-1 — Tilt-controlled NeoPixel colours

```python
import pykit_explorer
from imu_sensor import IMUSensor
from neopixels  import NeoPixels, Colors, OFF

imu = IMUSensor()
px  = NeoPixels()

while True:
    direction = imu.tilt_direction()
    if direction == "LEFT":
        px.fill(Colors.RED)
    elif direction == "RIGHT":
        px.fill(Colors.BLUE)
    elif direction == "UP":
        px.fill(Colors.GREEN)
    elif direction == "DOWN":
        px.fill(Colors.YELLOW)
    else:
        px.off()
```

---

## Minimal Example #5-2 — NeoPixel & IMU shake detection

```python
import pykit_explorer
from imu_sensor import IMUSensor
from neopixels import NeoPixels, Colors, OFF

imu = IMUSensor()
px  = NeoPixels()

while True:
    imu.print_all()
    if imu.is_shaking():
        px.fill(Colors.	WHITE)
        time.sleep(0.2)
    else:
        px.off()
    time.sleep(0.1)
```

---

## Minimal Example #6-1 — BLE temperature logger

```python
import pykit_explorer
from ble_uart import BLEUart
from cpu_temp import CPUTemperature

ble  = BLEUart()
temp = CPUTemperature()

while True:
    ble.poll()  # process connection status messages
    if ble.connected:
        ble.send(f"Temp: {temp.formatted_string()}\n")
        print(f"Temp: {temp.formatted_string()}")
    time.sleep(2)
```

## Minimal Example #6-2 — Receiving BLE Commands

```python
import pykit_explorer
from ble_uart import BLEUart
from neopixels import NeoPixels, Colors, OFF

ble  = BLEUart()
px  = NeoPixels()

while True:
    cmd = ble.receive().strip()
    if cmd == 'RED': px.fill(Colors.RED)
    elif cmd == 'GREEN': px.fill(Colors.GREEN)
    elif cmd == 'OFF': px.off()
    if cmd:
	    print(f"Got: {repr(cmd)}")
    time.sleep(0.05)
```

---

## Minimal Example #7 — APDS9960 gesture → WAV audio

```python
import pykit_explorer
from i2c_bus import I2CBus
from apds9960 import APDS9960Sensor, Gestures, Gesture_Names
from audio_out import AudioOutput

my_i2c = I2CBus()
sensor = APDS9960Sensor(my_i2c.bus)
audio  = AudioOutput()

sensor.enable_gesture()

while True:
    g = sensor.wait_for_gesture()
    if g == Gestures.GESTURE_UP:
        audio.play_wav("AudioFiles/304.wav")
    elif g == Gestures.GESTURE_DOWN:
        audio.play_wav("AudioFiles/140.wav")
    elif g == Gestures.GESTURE_LEFT:
        audio.play_wav("AudioFiles/210.wav")
    elif g == Gestures.GESTURE_RIGHT:
        audio.play_wav("AudioFiles/320.wav")
```

---

## Minimal Example #8 — APDS9960 color → NeoPixels

```python
import pykit_explorer
from i2c_bus import I2CBus
from apds9960 import APDS9960Sensor
from neopixels import NeoPixels

my_i2c = I2CBus()
sensor = APDS9960Sensor(my_i2c.bus)
px     = NeoPixels()

sensor.enable_color()

while True:
    px.fill(sensor.color_as_neopixel())
    time.sleep(0.1)
```

## Minimal Example #9 — ==BME==680 air quality display

```python
import pykit_explorer
from i2c_bus import I2CBus
from bme680 import BME680Sensor
from neopixels import NeoPixels, Colors

my_i2c = I2CBus()
sensor = BME680Sensor(my_i2c.bus, elevation_m=362)
px     = NeoPixels()

while True:
    sensor.print_all()
    level = sensor.temperature_level()
    if level == "LOW":
        px.fill(Colors.BLUE)
    elif level == "MED":
        px.fill(Colors.GREEN)
    elif level == "HIGH":
        px.fill(Colors.YELLOW)
    else:
        px.fill(Colors.RED)
    time.sleep(1)
```

## Minimal Example #10 — Display a BMP image on the LCD

Place your `.bmp` image files in the `/Images` folder on the CIRCUITPY drive.

```python
import pykit_explorer
from lcd_display import LCDDisplay

lcd = LCDDisplay()
lcd.backlight_on()

# load_sprite() loads the BMP and returns a positioned displayio.Group
group = lcd.load_sprite("/Images/Bluey_Family.BMP")
lcd.display.root_group = group

while True:
    pass
```

> **Note:** BMP images should match the display resolution (240×135) for best results.
> Supported format: indexed colour BMP (16 or 256 colours).

---

## Minimal Example #11 — LCD as a serial terminal

CircuitPython automatically redirects `print()` output to an attached display.
This example initialises the LCD and then uses `print()` as a simple terminal.

```python
import pykit_explorer
from lcd_display import LCDDisplay

lcd = LCDDisplay()
lcd.backlight_on()

x = 0

while True:
    print("Hello World:", x)
    x += 1
    time.sleep(1)
```

> **Note:** Once the display is initialised, `print()` output appears on both
> the LCD and the USB serial console automatically.

---

## Minimal Example #12 — Colored LCD labels with live data

Four coloured labels (Red, Green, Blue, White) with adjacent value labels that
update every 0.5 seconds with fake sensor data.

```python
import pykit_explorer
import random
from lcd_display import LCDDisplay, Colors

lcd = LCDDisplay()
lcd.backlight_on()

group, _ = lcd.make_group(Colors.BLACK)

LABEL_COLORS = [Colors.RED, Colors.GREEN, Colors.BLUE, Colors.WHITE]
LABEL_NAMES  = ["Label 1", "Label 2", "Label 3", "Label 4"]
Y_POSITIONS  = [20, 50, 80, 110]

name_labels  = []
value_labels = []

for i in range(4):
    name_lbl = lcd.add_label(group, LABEL_NAMES[i], 60, Y_POSITIONS[i],
                             color=LABEL_COLORS[i], scale=2)
    value_lbl = lcd.add_label(group, "0.00", 180, Y_POSITIONS[i],
                              color=LABEL_COLORS[i], scale=2)
    name_labels.append(name_lbl)
    value_labels.append(value_lbl)

while True:
    for i in range(4):
        value_labels[i].text = f"{random.uniform(0, 100):.2f}"
    time.sleep(0.5)
```

---

## Minimal Example #13 — Rolling coloured text labels on the LCD

Requires `adafruit_bitmap_font` and `adafruit_display_text` in `/lib`, and a
`.bdf` font file in the `/Fonts` folder on the CIRCUITPY drive.
Text strings rotate down through the four lines every second while
the line colours stay fixed.

```python
import pykit_explorer
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from lcd_display import LCDDisplay, Colors

lcd = LCDDisplay()
lcd.backlight_on()

# Load font
font = bitmap_font.load_font("/Fonts/Helvetica-Bold-16.bdf")

LINE_COLORS = [Colors.PURPLE, Colors.BLUE, Colors.RED, Colors.GREEN] # Colours for each line of text
LINE_Y = [20, 50, 80, 110] # Y positions for each line of text

# Create four text labels with fixed colours and positions
labels = []
for i in range(4):
    text_area = label.Label(font, text="", color=LINE_COLORS[i])
    text_area.x = 0
    text_area.y = LINE_Y[i]
    labels.append(text_area)

# Text strings that will roll through the lines
texts = [
    "Lorem ipsum dolor sit amet",
    "consectetur adipiscing elit",
    "sed do eiusmod tempor",
    "labore et dolore magna aliqua",
]

# Build display group
group = displayio.Group()
for lbl in labels:
    group.append(lbl)
lcd.display.root_group = group

# Assign initial text
for i in range(4):
    labels[i].text = texts[i]

while True:
    time.sleep(1)
    # Rotate text strings: last item moves to front
    texts = [texts[-1]] + texts[:-1]
    for i in range(4):
        labels[i].text = texts[i]
```

> **Note:** Colour values are 24-bit hex `0xRRGGBB`. Font files (`.bdf`) should be
> placed in the `/Fonts` folder on the CIRCUITPY drive.

---

## Minimal Example #14 — Concurrent NeoPixel blinks with AsyncRunner

Requires the `asyncio` library in `/lib`.

```python
import pykit_explorer
from neopixels import NeoPixels, Colors, OFF
from async_tasks import AsyncRunner

pixels = NeoPixels()

async def blink(pixel: int, interval: float, count: int, color: tuple):
    for _ in range(count):
        pixels.set(pixel, color)
        await AsyncRunner.sleep(interval)
        pixels.set(pixel, OFF)
        await AsyncRunner.sleep(interval)

runner = AsyncRunner()
runner.add(blink(0, 0.30, 15, Colors.PURPLE))
runner.add(blink(1, 0.75, 10, Colors.GREEN))
runner.add(blink(2, 1.00, 10, Colors.RED))
runner.add(blink(3, 0.50, 10, Colors.YELLOW))
runner.add(blink(4, 0.25, 15, Colors.BLUE))
runner.run()
```

> **Note:** All tasks run cooperatively — use `await AsyncRunner.sleep()` (not
> `time.sleep()`) to yield control between tasks.

---

## Minimal Example #15 — CPU temperature on LCD, serial, and BLE

Combines `cpu_temp`, `lcd_display`, and `ble_uart` to read the CPU temperature
and display it on the LCD with colour-coded thresholds, print to the serial
console, and send over BLE. Messages received from the connected device are
displayed on the LCD and scrolled automatically if longer than 20 characters,
with the duration calculated so the full message always completes one pass.
Connection and disconnection events show a status banner. The display reverts
to the temperature readout when the message expires.

`make_group()` creates the single persistent display group. `add_label()`
creates the temperature label. `make_scroll_label()` creates the BLE message
label — it owns all scroll state internally so the main loop stays simple.

```python
import pykit_explorer
from cpu_temp    import CPUTemperature
from lcd_display import LCDDisplay, Colors
from ble_uart    import BLEUart

# Colour thresholds (°C)
THRESH_WARN   = 30.0
THRESH_HOT    = 35.0
TEMP_INTERVAL = 1.0

# Initialise hardware
lcd  = LCDDisplay()
temp = CPUTemperature()
ble  = BLEUart()
lcd.backlight_on()

group, bg = lcd.make_group(Colors.BLACK)

temp_lbl = lcd.add_label(group, "--.- C", 120, 55, color=Colors.GREEN, scale=3)
ble_lbl  = lcd.make_scroll_label(group, 120, 55)

temp_next = 0.0

while True:
    now      = time.monotonic()
    incoming = ble.poll()

    if ble.just_connected:
        bg[0] = Colors.BLACK
        ble_lbl.set("Connected")

    if ble.just_disconnected:
        bg[0] = Colors.BLACK
        ble_lbl.set("Disconnected")

    if incoming:
        bg[0] = Colors.DARK_BLUE
        ble_lbl.set(incoming.strip())

    if now >= temp_next:
        c         = temp.celsius
        temp_next = now + TEMP_INTERVAL

        if c < THRESH_WARN:
            temp_lbl.color = Colors.GREEN
        elif c <= THRESH_HOT:
            temp_lbl.color = Colors.ORANGE
        else:
            temp_lbl.color = Colors.RED
        temp_lbl.text = f"{c:.1f} C"
        print(f"CPU Temp: {c:.1f} C")
        if ble.connected:
            ble.send(f"Temp: {c:.1f}C\n")

    if ble_lbl.update(now):
        temp_lbl.hidden = True
    else:
        temp_lbl.hidden = False
        bg[0]           = Colors.BLACK
```

---

## Tools

Standalone diagnostic scripts that help you explore and verify hardware
capabilities on the PyKit Explorer. Copy the script into `code.py` and run it
to inspect your board — no extra libraries needed beyond the `/API` modules.

---

### PWM Pin Identifier

Scans every pin on the PyKit Explorer and reports which pins are available for
PWM output, which are PWM-capable but blocked by a board-level peripheral,
and which have no PWM support at all.
Results are printed in a consistent order: working PWM pins first, then
prevented pins with the reason, then non-PWM pins. Useful before writing any
PWM-based driver to confirm which pins are actually free to use.

```python
import pykit_explorer

from pwm_pins import PWMPinScanner

scanner = PWMPinScanner()
scanner.scan()
scanner.report()
```

### I2C Bus Scanner

Scans the I2C bus and reports every device address found, a candidate device
name based on a built-in address lookup table, and a confirmed device name read
directly from the hardware via the WHO_AM_I or chip ID register.

Covers all on-board devices (ICM-20948 IMU, ==BME==680, APDS9960) as well as a
wide range of common QWIIC breakout modules.

```python
import pykit_explorer
from i2c_scan import I2CScanner

scanner = I2CScanner()
scanner.scan()
scanner.report()
scanner.deinit()
```

**Reading the output:**

Each found device prints as two lines:

```text
  0x69  ICM-20948 (IMU)
        WHO_AM_I @ 0x00: 0xEA → ICM-20948
```

- The first line shows the hex address and the candidate name from the address
  lookup table. Where multiple devices share an address, all possibilities are
  listed separated by `/`.
- The second line shows the WHO_AM_I register address, the raw value read back,
  and the confirmed device name. If the value does not match any known ID,
  `unrecognised` is shown — this may indicate a device variant not yet in the
  lookup table. If no WHO_AM_I register is defined for that address, the second
  line is omitted.

Results are also available programmatically via `scanner.results`, a list of
dicts with keys `address`, `candidate`, `who_am_i`, and `confirmed`.

### Register-Level Peek / Poke

A REPL-friendly utility for reading and writing individual hardware registers
on any I2C or SPI device by address. Think of it as a lightweight version of
what you would do with Microchip's MPLAB Data Visualizer, but running entirely
in Python on the board itself. Useful for exploring a device's register map,
verifying that a configuration write took effect, or reading raw sensor output
without a full driver.

Both `I2CDevice` and `SPIDevice` expose the same interface:

| Method                     | Description                                            |
| -------------------------- | ------------------------------------------------------ |
| `peek(register)`         | Read one register and print its value                  |
| `peek(register, length)` | Burst-read and print*length* consecutive registers   |
| `poke(register, value)`  | Write one byte and confirm with an automatic readback  |
| `dump(start, end)`       | Read and print every register from*start* to *end* |

Values are always shown as hex, decimal, and binary so they can be read
directly against a datasheet register map.

**I2C example — ICM-20948 IMU at address 0x69:**

```python
import pykit_explorer

from reg_peek_poke import I2CDevice

imu = I2CDevice(0x69)

imu.peek(0x00)           # Read WHO_AM_I — should return 0xEA
imu.dump(0x00, 0x06)     # Dump the first 7 registers
imu.poke(0x06, 0x01)     # Write PWR_MGMT_1 to wake the IMU from sleep

imu.deinit()
```

**SPI example — 25AA040A EEPROM read/write using `SPIBus`:**

The 25AA040A is a 512-byte serial EEPROM. Use the `SPIBus` module from `/API` for clean,
automatic CS management and multi-byte transactions.

**Wiring — 25AA040A to PyKit Explorer:**

| 25AA040A Pin | Description  | PyKit Pin |
| ------------ | ------------ | --------- |
| 1            | CS           | D9        |
| 2            | SO (MISO)    | D8        |
| 3            | GND          | 3V3       |
| 4            | VSS (ground) | GND       |
| 5            | SI (MOSI)    | D10       |
| 6            | SCK          | D11       |
| 7            | HOLD         | 3V3       |
| 8            | VCC          | 3V3       |

> **Note:** Pull up unused control pins (HOLD on pin 7) to VCC (3V3).
> For a breadboard-friendly setup, place a 10 kΩ resistor between HOLD and VCC, or simply tie it directly to VCC if no hold control is needed.

```python
import pykit_explorer
import time

from spi_bus import SPIBus

# Initialize SPI bus (1 MHz, uses board.CS by default)
spi = SPIBus(baudrate=1_000_000)

def read_status():
    """Read EEPROM status register"""
    response = spi.write_then_read(bytes([0x05]), 1)
    return response[0]

def write_enable():
    """Send WREN instruction before write operations"""
    spi.write(bytes([0x06]))

def write_byte(addr, data):
    """Write single byte to EEPROM address"""
    write_enable()
    time.sleep(0.001)
    spi.write(bytes([0x02, addr, data]))
    time.sleep(0.005)  # Wait for write to complete

def read_byte(addr):
    """Read single byte from EEPROM address"""
    response = spi.write_then_read(bytes([0x03, addr]), 1)
    return response[0]

# Test: write pattern to addresses 0x00–0x03
print("Writing pattern [0x55, 0xAA, 0x33, 0xCC]...")
pattern = [0x55, 0xAA, 0x33, 0xCC]
for addr, val in enumerate(pattern):
    write_byte(addr, val)

# Read back and verify
print("Reading back...")
for addr, expected in enumerate(pattern):
    read_val = read_byte(addr)
    status = "✓" if read_val == expected else "✗"
    print(f"{status} Address 0x{addr:02X}: 0x{read_val:02X} (expected 0x{expected:02X})")

spi.deinit()
```

**SPI EEPROM command reference (25AA040A protocol):**

| Command | Code | Format             | Purpose                        |
| ------- | ---- | ------------------ | ------------------------------ |
| READ    | 0x03 | 0x03 [addr]        | Read byte at address           |
| WRITE   | 0x02 | 0x02 [addr] [data] | Write byte at address          |
| RDSR    | 0x05 | 0x05               | Read status register (WIP bit) |
| WREN    | 0x06 | 0x06               | Write Enable before any write  |
| WRDI    | 0x04 | 0x04               | Write Disable (clear WIP)      |

**Implementation notes:**

- **SPIBus class:** Provides automatic CS management and configurable baudrate/polarity/phase.
- **write_then_read():** Combines command send and response read in a single CS-low transaction — ideal for EEPROM operations.
- **Write sequence:** Always call `write_enable()` (WREN, 0x06) before any write operation.
- **Timing:** Wait ≥5 ms after write operations for the EEPROM to complete the internal write cycle.
- **Multi-byte writes:** For sequential writes, extend the WRITE command to include consecutive address+data pairs without re-enabling.

  **SPI example — generic sensor on board.CS:**

```python
import pykit_explorer
import board

from reg_peek_poke import SPIDevice

# Default convention: bit 7 = 1 for read, bit 7 = 0 for write.
# Works with ICM-20948, LSM6DS, BMI160, and most MEMS sensors.
# Override read_bit / write_mask for devices with a different protocol.
dev = SPIDevice(board.CS)

dev.peek(0x0F)            # Read the WHO_AM_I / device ID register
dev.dump(0x00, 0x1F)      # Dump the first 32 registers
dev.poke(0x10, 0x00)      # Write 0x00 to register 0x10

dev.deinit()
```

**Reading the output:**

`peek` and `dump` print one line per register in a fixed-column table:

```text
  Addr   Hex    Dec  Bin
  ---------------------------------
  0x00   0xEA  234  1110 1010
  0x01   0x00    0  0000 0000
```

`poke` prints the written value followed by an immediate readback. If the
readback does not match what was written, a warning is shown — this is normal
for read-only bits, reserved fields, or registers where the hardware masks
certain bits:

```text
  Wrote 0x01 → register 0x06
  Readback:  0x01    1  0000 0001
```

All methods also return their results for programmatic use: `peek` returns an
int (or bytearray when *length* > 1), and `dump` returns a dict mapping each
register address to its value.

### PWM Waveform Explorer

An interactive oscilloscope-style tool for understanding PWM signals.
Students adjust frequency and duty cycle in real time and see the effect
across three simultaneous feedback channels: a scrolling graphical waveform
on the LCD, a sine tone through the speaker, and LED brightness — all
updating instantly with every button press.

**Controls**

| Input              | Action                                                         |
| ------------------ | -------------------------------------------------------------- |
| USER button (D3)   | Step frequency: 100 → 200 → 500 → 1k → 2k → 3k Hz (wraps) |
| CAP TOUCH pad (A5) | Step duty cycle: 0 → 10 → 20 → … → 100 → 0 % (wraps)     |

**What you see on the LCD**

```
PWM WAVEFORM EXPLORER
FREQ   1000 Hz          ← flashes white on change
DUTY     50 %           ← flashes white on change

══════════              ← HIGH signal (bright green, scrolling)

══════════              ← LOW signal  (bright green, scrolling)

USER=freq   CAP TOUCH=duty
```

The waveform scrolls continuously left so the signal appears live.
When a parameter changes, the corresponding row briefly flashes white
to confirm which value was updated. The speaker volume scales with
duty cycle — 0 % is silent, 100 % is loudest.

```python
import pykit_explorer
from pwm_waveform_explorer import run

run()
```

---

### Analog Waveform Explorer

A triggered oscilloscope-style display for all six analog input pins (A0–A5).
The scope waits for a rising edge on the selected channel, captures a complete
frame of samples, freezes it on the LCD, then immediately arms for the next
trigger. Because the display only updates when a full frame is ready, the
waveform is always stable and phase-aligned — it does not scroll.

Each channel has a distinct colour so you can tell at a glance which signal
you are watching: A0=cyan, A1=green, A2=yellow, A3=orange, A4=red, A5=purple.

**Controls**

| Input                    | Action                                                                  |
| ------------------------ | ----------------------------------------------------------------------- |
| Short press D3 (< 0.8 s) | Step timebase: 10ms/px → 5ms → 2ms → 1ms → 500µs → 200µs (wraps) |
| Long press D3 (≥ 0.8 s) | Next channel: A0→A1→A2→A3→A4→A5 (wraps)                            |

**Timebase guide — choosing the right scale**

Pick the scale where your signal fills roughly half the display width or more.
If the waveform looks like a flat line, the signal is too slow — use a slower
(higher ms/px) scale. If it looks like a solid block of colour, the signal is
too fast — use a faster (lower ms/px) scale.

| Scale      | Window | Good for    |
| ---------- | ------ | ----------- |
| 10 ms/px   | 2.32 s | 0.4–10 Hz  |
| 5 ms/px    | 1.16 s | 1–20 Hz    |
| 2 ms/px    | 464 ms | 4–50 Hz    |
| 1 ms/px    | 232 ms | 10–100 Hz  |
| 500 µs/px | 116 ms | 50–165 Hz  |
| 200 µs/px | 46 ms  | 100–400 Hz |

> **Maximum frequency:** ~400 Hz. Above this the sample rate (≈ 4 kHz) no
> longer provides enough points per cycle for a recognisable waveform.
> The hardware limit is set by CircuitPython loop overhead, not the ADC itself.

**What you see on the LCD**

```
ANALOG WAVEFORM EXPLORER
A0  3.28Vpp  10.0Hz  100.0ms   <- channel | peak-to-peak voltage | freq | period
10ms/px  2.32s                 <- current timebase and capture window

+-------------------------------+
|      *                        |  <- frozen triggered waveform
|   *     *                     |     trigger crossing is at x=46 (20% from left)
|*           *               *  |     amplitude fills full height = 3.3 Vpp
|              *           *    |
|                *       *      |
|                  *   *        |
|                    *          |
+-------------------------------+

PRESS=scale  HOLD=ch
```

**Reading the measurements**

- **Vpp** — peak-to-peak voltage across the captured frame. A 0–3.3 V
  signal reads 3.30 Vpp. A signal that only swings between 1 V and 2 V
  reads 1.00 Vpp.
- **Frequency / Period** — measured from the trigger crossing to the next
  rising mid-scale crossing in the same frame. Shows `---` if only one
  cycle fits (or less than one cycle) — select a slower scale to bring a
  second crossing into view.

**Trigger**

The scope triggers on a rising edge through 1.65 V (mid-scale on a 3.3 V
rail). If the display freezes and never updates, check that:

1. The signal is actually crossing 1.65 V on its rising edge.
2. The signal amplitude is large enough to cross mid-scale (a 0.1 V signal
   sitting at 1.0 V will never trigger).
3. The timebase is not so slow that each frame takes a very long time to fill
   (at 10 ms/px a frame takes 2.32 s to capture).

```python
import pykit_explorer
from analog_waveform_explorer import run

run()
```

---

### Synthio Sound Lab

A real-time theremin-style synthesizer driven entirely by onboard sensors.
Tilt the board to sweep pitch across four octaves, tilt the opposite axis to
control volume, and hover your hand over the proximity sensor to bend the note
up by up to two semitones — all while watching the parameters update live on
the LCD.  Four waveforms (sine, square, sawtooth, triangle) let students hear
how waveshape changes timbre.  Optional USB MIDI output is enabled
automatically when the host supports it.

The note plays continuously. Tilting forward or back controls volume —
a 3° dead zone around flat keeps the output silent until you intentionally
tilt. Keeping the board flat silences the output without stopping synthesis.

**Controls**

| Input                        | Action                                                    |
| ---------------------------- | --------------------------------------------------------- |
| USER button (D3)             | Cycle waveform: SINE → SQUARE → SAW → TRIANGLE (wraps) |
| Tilt left / right (Y-axis)   | Pitch sweep across the selected range                     |
| Tilt forward / back (X-axis) | Volume: <3° = silent, 45° = full                        |
| Hand near APDS proximity     | Pitch bends up by 0 to +2 semitones (closer = more bend)  |

**What you see on the LCD**

```
   SYNTHIO SOUND LAB
   WAVE  SINE               <- current waveform (purple)
   NOTE C4    262Hz         <- note name + frequency (cyan)

VOL |||||||||               <- green bar, width = volume
BND ||                      <- orange bar, width = bend amount
    ----------|----------   <- cyan needle tracks tilt position

   D3=wave   TILT=vol
```

Requires the ICM20948 IMU (on-board) and an APDS9960 proximity breakout
connected to the QWIIC connector.

```python
import pykit_explorer
from synthio_sound_lab import run

run()
```

---

- **HID** requires `usb_hid.enable()` in `boot.py`.
- **WAV files** must be mono, 16-bit PCM, ≤ 22 050 Hz.
- **CAN** requires two boards (or a CAN analyser) to verify message exchange.
- **Breakout modules** (`bme680`, `apds9960`) connect via the QWIIC connector and require `i2c_bus.py` on the drive. Always pass `i2c_bus_instance.bus` to the sensor constructor, not the `I2CBus` object itself.
- **APDS9960 modes** are mutually exclusive — always call `enable_proximity()`, `enable_gesture()`, or `enable_color()` before reading, and only one at a time.
