# PyKit Explorer Development Guidelines

## RGB Matrix Display (128x64, 4 panels rotated 90 degrees)

### Performance
- **BIT_DEPTH**: Use 2 for best framerate (~60fps). Use 3 for more colors but ~30fps. Higher values cause significant lag.
- **Game loop sleep**: Use `time.sleep(0.016)` for ~60fps, `time.sleep(0.033)` for ~30fps
- **SPI baudrate**: Use 8MHz for shift register controls. Lower speeds cause sluggish input response.

### Rendering - Avoid Flashing
- **Never create/destroy objects every frame** - causes flashing and GC pressure
- **Use dirty-rectangle rendering**: Only erase/redraw sprites when position actually changes
- **Cache object positions**: Compare previous vs current, skip redraw if unchanged
- **Copy cached lists**: When passing cached data to view, use `list()` to copy, don't store references
- **Terrain scrolling**: Only update columns that changed (diff previous vs current positions)

### Sprite/Animation Sizes
- **Cap animation sizes**: Explosions and effects must have max radius (e.g., `r = min(frame + 2, 6)`)
- **Cap both draw AND erase**: If you cap draw radius, cap erase radius the same way

## Input Handling

### Shift Register Layout (3x CD74HC165E daisy-chained)
```
U1 (Player 1): Joystick (A-D) + Buttons 1-4 (E-H)
U2 (Player 2): Joystick (A-D) + Buttons 1-4 (E-H)
U3 (Admin):    Unused (A-D) + 1P, 2P, Start, Select (E-H)
```

Access via `ShiftRegisterControls`:
- `controls.p1` / `controls.p2` - PlayerState with joystick and btn1-4
- `controls.admin` - AdminState with one_player, two_player, start, select

### Button Mapping for Games
- **Player buttons** (btn1-4): Game actions (jump, shoot, etc.)
- **Admin buttons**: Menu/system functions only
  - `admin.one_player_fell` / `admin.two_player_fell` - Mode selection
  - `admin.start_fell` - Start game (use this, not action buttons)
  - `admin.select_fell` - Skip/switch game

### DAS (Delayed Auto Shift)
For held inputs (joystick directions), implement DAS:
```python
DAS_DELAY = 10   # frames before repeat starts
DAS_REPEAT = 3   # frames between repeats
```
Track `das_timer` per direction. On initial press, act immediately. While held, wait DAS_DELAY then repeat every DAS_REPEAT frames.

### Edge Detection
Use `_prev_*` flags for actions that should only trigger once per press (jump, shoot, bomb).

## Memory Management

### Object Pooling
Pre-allocate pools for frequently created objects:
```python
self.bullets = [Bullet() for _ in range(MAX_BULLETS)]
self.explosions = [Explosion() for _ in range(MAX_EXPLOSIONS)]
```
Reuse by setting `active = True/False`, never create new instances during gameplay.

### Caching
- Cache calculated values (visible craters, block positions)
- Use `_cache_offset` to invalidate only when underlying data changes
- Pre-allocate cache arrays with fixed size

## Game Modes

### 1-Player vs 2-Player
- Track mode with `player_mode` variable (1 or 2)
- In 1-player mode, AI controls the opponent
- Only process P2 inputs when `player_mode == 2`

### Simple AI Pattern (for opponent)
```python
def _update_ai(self):
    # Move towards player with offset
    if self.enemy.x < self.player.x - threshold:
        self.enemy.x += speed
    elif self.enemy.x > self.player.x + threshold:
        self.enemy.x -= speed
    
    # Random actions on timer
    self._ai_timer += 1
    if self._ai_timer >= interval:
        self._ai_timer = 0
        # Perform action (shoot, drop bomb, etc.)
```

## Audio

### WAV File Requirements
- **Format**: Mono, 16-bit PCM, 22050 Hz sample rate
- Files stored in `/AudioFiles/` folder

### Direct WaveFile Loading (Recommended)
Use direct WaveFile loading instead of the preload system for reliable playback:
```python
# In __init__:
from audiocore import WaveFile
self._wav_hit_f = open("/AudioFiles/hit.wav", "rb")
self._sfx_hit = WaveFile(self._wav_hit_f)

# To play (recreate WaveFile after seeking):
def _play_preloaded(self, wav_file, sfx, interrupt=True):
    if sfx is None or self._audio is None:
        return
    # Skip if already playing and we don't want to interrupt
    if not interrupt and self._audio.is_playing:
        return
    if self._audio.is_playing:
        self._audio.stop()
    wav_file.seek(0)
    from audiocore import WaveFile
    new_sfx = WaveFile(wav_file)
    self._audio._audio.play(new_sfx)

# In cleanup:
self._wav_hit_f.close()
```

### Frequent Sound Effects (Rapid Playback)
For sounds that play rapidly (dot eating, collecting coins):
- Use `interrupt=False` to skip if already playing, prevents glitchy overlapping
- NEVER use `play_wav()` - it's blocking and causes game slowdown
- NEVER use `play_wav_async()` - it opens new file handles every call, causing memory leaks and glitches
- Always preload sounds at init and reuse the file handles

### Order of Operations - CRITICAL
**Draw screen BEFORE playing audio** to prevent slowdown:
```python
# WRONG - audio plays slow while screen draws
self.view.play_sfx("gameover")
self.view.show_game_over(winner)  # Heavy pixel work interferes with audio

# CORRECT - screen draws first, then audio plays cleanly
self.view.show_game_over(winner)  # Do heavy pixel work first
self.view.play_sfx("gameover")    # Then play audio uninterrupted
```
CPU-intensive operations (clear_bitmap, drawing) during audio playback cause the first half of sounds to play slowly.

## Game State Sequences

### Multi-Phase Transitions
When a sequence has multiple phases (e.g., crash -> explosion -> reset -> resume):
- **Phases must be SEQUENTIAL, not simultaneous**
- Use `phase` variable (1, 2, 3...) and `timer` for each phase
- Only transition to next phase when current phase timer expires
- Example respawn:
  1. Phase 1: Explosion animates, player hidden, world stopped
  2. Phase 2: World reset, player visible but stationary
  3. Phase 3: Resume normal gameplay

## Terrain/Graphics

### Semi-Circular Shapes
For rounded craters/bowls, use the circle equation:
```python
depth_ratio = (1.0 - (d * d) / (radius * radius)) ** 0.5
depth = int(depth_ratio * max_depth)
```
Where `d` is distance from center.

### Crater Rendering
- Draw background color (_BG/black) inside craters, not surface color
- Surface line should stop at crater edges

## Display Panel Configuration (FlippedBitmap)

The 128x64 display uses 4 chained 64x32 panels rotated 90° CW. Due to cable routing (reversed order), panels need software compensation:

| X Region | Panel | Transformation |
|----------|-------|----------------|
| 0-31     | 4     | 180° flip |
| 32-63    | 3     | No flip |
| 64-95    | 2     | 180° flip |
| 96-127   | 1     | No flip |

**Always use FlippedBitmap wrapper for drawing:**
```python
from matrix_display import FlippedBitmap, WIDTH, HEIGHT
raw_bitmap = displayio.Bitmap(WIDTH, HEIGHT, num_colors)
bitmap = FlippedBitmap(raw_bitmap)   # Use for ALL drawing
bitmap[x, y] = color                  # Coordinates auto-transformed
tg = displayio.TileGrid(raw_bitmap, pixel_shader=palette)  # Raw for TileGrid
```

## HUD Updates (Performance)

Never clear and redraw the entire HUD when only one value changes:
```python
# WRONG - clears 1024 pixels every score change
def _draw_hud(self):
    for y in range(8):
        for x in range(128):
            self._bitmap[x, y] = _BG  # Slow!
    # redraw everything...

# CORRECT - only update changed portion
def _draw_hud_p1_score(self, score):
    # Clear only P1 score area (28 pixels wide)
    for y in range(6):
        for x in range(28):
            self._bitmap[x, y + 1] = _BG
    draw_tiny_text(self._bitmap, f"{score}", 1, 1, _P1)
```

## Maze/Grid-Based Games

### Maze Definition
Use text-based ASCII maps for fastest loading (no parsing overhead):
```python
MAZE_DATA = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # W=wall, .=dot
    "W......W......-WW-......W......W",  # o=power pellet
    # ... each row MUST be exactly the same length
]
```
**Critical**: Verify all rows have identical length or you'll get index errors.

### Grid Collision
Use grid coordinates (not pixels) for collision detection:
```python
def is_wall(self, gx, gy):
    if gx < 0 or gx >= GRID_W or gy < 0 or gy >= GRID_H:
        return True
    return self.maze[gy][gx] == WALL
```
