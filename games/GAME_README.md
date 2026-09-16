# Adding New Games to the Game Launcher

This document explains how to add new games to the unified game launcher on the
PyKit Explorer. The launcher automatically discovers games in this folder and
cycles through them in order.

## Quick Start

1. Create a new folder under `/games/` with your game name (e.g., `games/my_game/`)
2. Add an `__init__.py` that exports a class inheriting from `BaseGame`
3. Implement the required methods: `setup()`, `run()`, `cleanup()`
4. (Optional) Add splash screen and game over BMP files to `/Sprites/`
5. (Optional) Add audio files to `/AudioFiles/`

The launcher will automatically discover and include your game on the next boot.

---

## Folder Structure

Each game must be in its own subfolder under `/games/`:

```
games/
├── GAME_README.md          # This file
├── your_game/
│   ├── __init__.py         # REQUIRED: Exports your game class
│   ├── model.py            # Game logic (recommended)
│   ├── view.py             # Display/rendering (recommended)
│   └── ...                 # Any other game-specific files
```

## Required: `__init__.py`

Your game folder MUST contain an `__init__.py` file that exports a single
game class inheriting from `BaseGame`. The launcher auto-discovers games
by scanning for this pattern.

Example `__init__.py`:

```python
import time
import gc
from base_game import BaseGame


class MyGame(BaseGame):
    NAME = "My Awesome Game"    # Display name shown in launcher
    HIGH_SCORE_SLOT = 3         # Unique slot (0-29), see table below

    def setup(self):
        """Initialize game-specific resources."""
        # Show calibration message if using tilt controls
        self.imu.calibrate(samples=30)
        
        # Initialize your game model and view
        # self.model = MyGameModel()
        # self.view = MyGameView(self.lcd.display, self.px, self.audio)
        
        # Create game-specific inputs if needed
        # self.button = digitalio.DigitalInOut(board.D3)
        
    def run(self, switch_detector):
        """Main game loop. Return True to switch to next game."""
        while True:
            # ALWAYS check for game switch first
            switch_detector.update()
            if switch_detector.fell:
                return True  # Switch to next game
            
            # Your game logic here
            # ...
            
            # Periodic garbage collection for long games
            gc.collect()
            
            time.sleep(0.033)  # ~30 FPS
            
    def cleanup(self):
        """Release game-specific resources."""
        # Deinit any game-specific inputs
        # self.button.deinit()
        
        # Stop audio and clear NeoPixels
        self.audio.stop()
        self.px.off()
```

---

## BaseGame Class Reference

Your game class inherits from `BaseGame` (`/base_game.py`) which provides:

### Shared Hardware (available as `self.*`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `self.lcd` | `LCDDisplay` | 240x135 TFT display |
| `self.imu` | `IMUSensor` | Accelerometer/gyroscope (ICM-20948) |
| `self.px` | `NeoPixels` | 5 RGB LEDs |
| `self.audio` | `AudioOutput` | DAC audio output |
| `self.high_scores` | `HighScoreManager` | NVM persistence |

### Required Class Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `NAME` | `str` | Display name shown during game transition |
| `HIGH_SCORE_SLOT` | `int` | Unique slot number 0-29 for high score storage |

### Required Methods

| Method | Description |
|--------|-------------|
| `setup()` | Initialize game-specific resources (sprites, inputs, etc.) |
| `run(switch_detector)` | Main game loop. Return `True` to switch games. |
| `cleanup()` | Release game-specific resources before switching |

### High Score Methods

| Method | Description |
|--------|-------------|
| `self.get_high_score()` | Get this game's persisted high score |
| `self.set_high_score(score)` | Save a new high score (if higher than current) |

---

## High Score Slots

Each game needs a unique slot number (0-29). Current assignments:

| Slot | Game |
|------|------|
| 0 | Snake |
| 1 | Space Impact |
| 2 | Super Mario |
| 3-29 | **Available** |

**Important**: When adding a new game, pick the next available slot number
and update this table.

---

## Game-Specific Inputs

Games can create their own button/touch inputs in `setup()`. Always release
them in `cleanup()` to avoid resource conflicts when switching games.

```python
import board
import digitalio
from cap_touch import CapTouch

class MyGame(BaseGame):
    def setup(self):
        # Fire button on D3
        self._btn = digitalio.DigitalInOut(board.D3)
        self._btn.direction = digitalio.Direction.INPUT
        self._btn.pull = digitalio.Pull.UP
        
        # Touch sensor on CAP1
        self._touch = CapTouch()
        
    def cleanup(self):
        self._btn.deinit()
        self._touch.deinit()
        self.px.off()
```

---

## IMU Calibration

If your game uses tilt controls, calibrate the IMU at the start of `setup()`:

```python
def setup(self):
    # Show message to user
    self._show_message("Place board flat...")
    
    # Calibrate (takes ~1 second with 30 samples)
    self.imu.calibrate(samples=30)
    
    # Use calibrated readings in your game loop
    ax, ay, az = self.imu.calibrated_acceleration
```

---

## Splash Screens

To show a splash screen when your game loads:

1. Create a 240x135 BMP image (4-bit or 8-bit indexed color)
2. Save it to `/Sprites/` (e.g., `my_game_splash.bmp`)
3. Load it in your view's `__init__`:

```python
import adafruit_imageload
import displayio

class MyGameView:
    def __init__(self, display, px, audio):
        self._display = display
        self._root = displayio.Group()
        display.root_group = self._root
        
        # Load splash screen
        try:
            bmp, pal = adafruit_imageload.load(
                "/Sprites/my_game_splash.bmp",
                bitmap=displayio.Bitmap, palette=displayio.Palette)
            self._splash = displayio.TileGrid(bmp, pixel_shader=pal)
            self._root.append(self._splash)
        except Exception as e:
            print(f"Splash load failed: {e}")
            # Fallback to text
```

**BMP Format Tips:**
- 4-bit (16 colors) = ~16KB, best for memory-constrained situations
- 8-bit (256 colors) = ~32KB, better color depth
- Use indexed color, not RGB

---

## Game Over Screens

To show a game over screen:

1. Create a 240x135 BMP (use 4-bit for best memory compatibility)
2. Save to `/Sprites/` (e.g., `Game_Over_MyGame.bmp`)
3. **Release resources before loading** to avoid memory fragmentation:

```python
def show_game_over(self):
    # Release sprites and audio to free memory
    self._release_resources()
    gc.collect()
    
    # Create fresh display group
    self._root = displayio.Group()
    self._display.root_group = self._root
    
    try:
        bmp, pal = adafruit_imageload.load(
            "/Sprites/Game_Over_MyGame.bmp",
            bitmap=displayio.Bitmap, palette=displayio.Palette)
        self._root.append(displayio.TileGrid(bmp, pixel_shader=pal))
    except Exception as e:
        # Fallback to text if BMP fails to load
        print(f"Game over BMP failed: {e}")
```

---

## Audio

### Audio Format Requirements

All WAV files must be:
- **Mono** (single channel)
- **16-bit PCM**
- **22050 Hz** sample rate

To convert audio files:
```bash
ffmpeg -i input.wav -ac 1 -ar 22050 output.wav
```

### Preloading Sounds

For responsive audio, preload sounds in your view:

```python
_SOUNDS = {
    "jump": "/AudioFiles/my_jump.wav",
    "coin": "/AudioFiles/my_coin.wav",
    "gameover": "/AudioFiles/my_gameover.wav",
}

class MyGameView:
    def __init__(self, display, px, audio):
        self._audio = audio
        for name, path in _SOUNDS.items():
            try:
                self._audio.preload_wav(name, path)
            except Exception as e:
                print(f"Failed to preload {name}: {e}")
    
    def play_sfx(self, name):
        if self._audio:
            self._audio.play_preloaded(name)
```

---

## NeoPixel Patterns

Use the 5 NeoPixels for game feedback:

```python
def update_neopixels(self, model):
    # Pixel 0: game mode indicator
    self.px[0] = 0x0000FF  # Blue = playing
    
    # Pixels 1-3: lives display
    for i in range(3):
        self.px[i + 1] = 0x00FF00 if i < model.lives else 0x000000
    
    # Pixel 4: special indicator
    self.px[4] = 0xFF0000 if model.danger else 0x000000
```

---

## Memory Management

CircuitPython has limited RAM (~100KB). Tips for avoiding memory issues:

1. **Call `gc.collect()` regularly** — every ~90 frames or after releasing resources
2. **Use sprite pools** — reuse sprites instead of creating/destroying them
3. **Lazy load BMPs** — load splash first, release it, then load game sprites
4. **Release resources before game over** — free memory before loading game over BMP
5. **Use 4-bit BMPs** — half the size of 8-bit BMPs

---

## MVC Architecture (Recommended)

For maintainable code, separate your game into:

| File | Responsibility |
|------|----------------|
| `__init__.py` | Game class, input handling, main loop |
| `model.py` | Game state, logic, collision detection |
| `view.py` | Display, sprites, audio, NeoPixels |

The model knows nothing about the display; the view knows nothing about game
rules. The game class (`__init__.py`) coordinates between them.

---

## Example: Minimal Game

```python
# games/minimal/__init__.py
import time
from base_game import BaseGame


class MinimalGame(BaseGame):
    NAME = "Minimal"
    HIGH_SCORE_SLOT = 10

    def setup(self):
        group, _ = self.lcd.make_group(0x000080)  # Blue background
        self.lcd.add_label(group, "Minimal Game", 120, 50, 0xFFFFFF, scale=2)
        self.lcd.add_label(group, "D11 to switch", 120, 90, 0xFFFF00)
        self.lcd.display.root_group = group

    def run(self, switch_detector):
        while True:
            switch_detector.update()
            if switch_detector.fell:
                return True
            time.sleep(0.1)

    def cleanup(self):
        self.px.off()
```

---

## Troubleshooting

### Game not discovered
- Check that `__init__.py` exists in your game folder
- Ensure your class inherits from `BaseGame`
- Check the serial console for import errors

### Memory allocation failed
- Release resources before loading large BMPs
- Use 4-bit instead of 8-bit BMPs
- Reduce sprite pool sizes
- Call `gc.collect()` after releasing resources

### Audio glitchy or silent
- Verify WAV is mono, 16-bit, 22050 Hz
- Check file path starts with `/` (e.g., `/AudioFiles/sound.wav`)
- Ensure audio isn't unloaded while still playing

### Display corruption after game over
- Create a fresh `displayio.Group()` for game over screen
- Set `display.root_group` to the new group
- Don't reuse the old display group after releasing sprites
