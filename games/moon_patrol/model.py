# moon_patrol/model.py - MODEL (MVC pattern)
# 2-Player Moon Patrol for 128x64 RGB Matrix
# P1: Buggy (drives, jumps, shoots) vs P2: UFO (flies, drops bombs)

import random

# Display dimensions
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

# Zone definitions
HUD_HEIGHT = 8
UFO_ZONE_TOP = 8
UFO_ZONE_BOTTOM = 24
GROUND_Y = 53
TERRAIN_Y = 54

# Entity dimensions
BUGGY_WIDTH = 12
BUGGY_HEIGHT = 8
UFO_WIDTH = 10
UFO_HEIGHT = 6
BULLET_WIDTH = 2
BULLET_HEIGHT = 3
BOMB_WIDTH = 4
BOMB_HEIGHT = 4

# Physics
SCROLL_SPEED = 1.5
BUGGY_SPEED = 1.0
BUGGY_JUMP_VY = -2.5
GRAVITY = 0.3
MAX_FALL_SPEED = 6.0
UFO_SPEED = 1.0
BULLET_SPEED = -5.0
BOMB_SPEED = 3.0

# Gameplay
BUGGY_INITIAL_LIVES = 3
UFO_INITIAL_HP = 5
SHOOT_COOLDOWN = 4
BOMB_COOLDOWN = 8
INVINCIBLE_FRAMES = 90

# Terrain generation
TERRAIN_SEGMENT_LENGTH = 128
MIN_CRATER_GAP = 50


class InputState:
    """Input state for both players."""
    def __init__(self):
        # Player 1 (Buggy)
        self.p1_left = False
        self.p1_right = False
        self.p1_jump = False
        self.p1_shoot = False
        # Player 2 (UFO)
        self.p2_left = False
        self.p2_right = False
        self.p2_up = False
        self.p2_down = False
        self.p2_bomb = False


class Buggy:
    """Player 1's moon buggy."""
    def __init__(self):
        self.x = 20.0
        self.y = float(GROUND_Y - BUGGY_HEIGHT)
        self.vy = 0.0
        self.on_ground = True
        self.lives = BUGGY_INITIAL_LIVES
        self.invincible = 0
        self.shoot_cooldown = 0
        self.respawning = False
        self.respawn_timer = 0
        self.respawn_phase = 0  # 0=none, 1=explosion, 2=stationary

    def jump(self):
        if self.on_ground:
            self.vy = BUGGY_JUMP_VY
            self.on_ground = False
            return True
        return False

    def update(self):
        """Update physics. Returns True if landed this frame."""
        landed = False
        if not self.on_ground:
            self.vy = min(self.vy + GRAVITY, MAX_FALL_SPEED)
            self.y += self.vy
            if self.y >= GROUND_Y - BUGGY_HEIGHT:
                self.y = float(GROUND_Y - BUGGY_HEIGHT)
                self.vy = 0.0
                self.on_ground = True
                landed = True
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.invincible > 0:
            self.invincible -= 1
        return landed

    def hit(self):
        """Take damage. Returns True if still alive."""
        if self.invincible > 0:
            return True
        self.lives -= 1
        if self.lives > 0:
            self.invincible = INVINCIBLE_FRAMES
        return self.lives > 0


class UFO:
    """Player 2's UFO."""
    def __init__(self):
        self.x = float(DISPLAY_WIDTH - UFO_WIDTH - 10)
        self.y = float((UFO_ZONE_TOP + UFO_ZONE_BOTTOM) // 2 - UFO_HEIGHT // 2)
        self.hp = UFO_INITIAL_HP
        self.bomb_cooldown = 0
        self.anim_frame = 0

    def update(self):
        self.anim_frame = (self.anim_frame + 1) % 30
        if self.bomb_cooldown > 0:
            self.bomb_cooldown -= 1

    def hit(self):
        """Take damage. Returns True if still alive."""
        self.hp -= 1
        return self.hp > 0


class Bullet:
    """Buggy's upward-firing bullet."""
    __slots__ = ('x', 'y', 'active')

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.active = False

    def fire(self, start_x, start_y):
        self.x = start_x
        self.y = start_y
        self.active = True

    def update(self):
        if self.active:
            self.y += BULLET_SPEED
            if self.y < HUD_HEIGHT:
                self.active = False


class Bomb:
    """UFO's downward-falling bomb."""
    __slots__ = ('x', 'y', 'active')

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.active = False

    def drop(self, start_x, start_y):
        self.x = start_x
        self.y = start_y
        self.active = True

    def update(self):
        if self.active:
            self.y += BOMB_SPEED
            if self.y > DISPLAY_HEIGHT:
                self.active = False


class Explosion:
    """Visual explosion effect."""
    __slots__ = ('x', 'y', 'frame', 'active')

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.frame = 0
        self.active = False

    def start(self, cx, cy):
        self.x = cx
        self.y = cy
        self.frame = 0
        self.active = True

    def update(self):
        if self.active:
            self.frame += 1
            if self.frame > 15:
                self.active = False


class TerrainManager:
    """Scrolling terrain with craters."""
    def __init__(self):
        self.offset = 0.0
        self.segments = []
        self.difficulty = 1
        # Pre-allocated cache for visible craters (avoid allocation each frame)
        self._visible_cache = [(0.0, 0)] * 10
        self._visible_count = 0
        self._cache_offset = -1
        self._generate_initial()

    def reset(self):
        """Reset terrain for new game with flat start."""
        self.offset = 0.0
        self.segments = []
        self._visible_count = 0
        self._cache_offset = -1
        self._generate_initial()

    def _generate_segment(self, start_x, first_segment=False):
        """Generate craters for one segment."""
        craters = []
        # First segment starts later for flat ground runway
        if first_segment:
            x = 80  # Give player flat ground at start
        else:
            x = random.randint(20, 40)
        while x < TERRAIN_SEGMENT_LENGTH - 20:
            width = random.choice([9, 12, 15, 18])
            craters.append((start_x + x, width))
            gap = max(MIN_CRATER_GAP - self.difficulty * 2, 30)
            x += width + random.randint(gap, gap + 20)
        return craters

    def _generate_initial(self):
        for i in range(3):
            start = i * TERRAIN_SEGMENT_LENGTH
            self.segments.extend(self._generate_segment(start, first_segment=(i == 0)))

    def update(self):
        self.offset += SCROLL_SPEED
        # Remove craters that scrolled off left
        while self.segments and self.segments[0][0] + self.segments[0][1] < self.offset:
            self.segments.pop(0)
        # Generate new craters on right if needed
        if self.segments:
            rightmost = max(c[0] + c[1] for c in self.segments)
        else:
            rightmost = self.offset
        while rightmost < self.offset + DISPLAY_WIDTH + TERRAIN_SEGMENT_LENGTH:
            new_craters = self._generate_segment(int(rightmost) + random.randint(30, 50))
            if new_craters:
                self.segments.extend(new_craters)
                rightmost = max(c[0] + c[1] for c in new_craters)
            else:
                rightmost += TERRAIN_SEGMENT_LENGTH

    def get_visible_craters(self):
        """Return cached list of (screen_x, width) for visible craters."""
        curr_offset = int(self.offset)
        if curr_offset == self._cache_offset:
            return self._visible_cache[:self._visible_count]

        # Rebuild cache
        self._visible_count = 0
        for world_x, width in self.segments:
            screen_x = world_x - self.offset
            if -width < screen_x < DISPLAY_WIDTH + width:
                if self._visible_count < len(self._visible_cache):
                    self._visible_cache[self._visible_count] = (screen_x, width)
                    self._visible_count += 1
        self._cache_offset = curr_offset
        return self._visible_cache[:self._visible_count]

    def is_over_crater(self, screen_x, obj_width):
        """Check if position is over a crater."""
        center_x = screen_x + obj_width / 2
        for i in range(self._visible_count):
            crater_x, crater_w = self._visible_cache[i]
            if crater_x <= center_x < crater_x + crater_w:
                return True
        return False


class MoonPatrolModel:
    """Main game state for 2-player Moon Patrol."""

    MAX_BULLETS = 4
    MAX_BOMBS = 3
    MAX_EXPLOSIONS = 6

    def __init__(self):
        self.buggy = Buggy()
        self.ufo = UFO()
        self.terrain = TerrainManager()

        # Pre-allocated pools
        self.bullets = [Bullet() for _ in range(self.MAX_BULLETS)]
        self.bombs = [Bomb() for _ in range(self.MAX_BOMBS)]
        self.explosions = [Explosion() for _ in range(self.MAX_EXPLOSIONS)]

        # Game state
        self.game_over = False
        self.winner = None
        self.distance = 0
        self.score = 0
        self.player_mode = 2  # 1 or 2 player mode

        # AI state for 1-player mode
        self._ai_move_timer = 0
        self._ai_target_x = 0.0
        self._ai_bomb_timer = 0

        # Input edge detection
        self._prev_p1_jump = False
        self._prev_p1_shoot = False
        self._prev_p2_bomb = False

    def reset(self):
        """Reset for new game with flat ground start."""
        self.buggy = Buggy()
        self.ufo = UFO()
        self.terrain.reset()
        for b in self.bullets:
            b.active = False
        for b in self.bombs:
            b.active = False
        for e in self.explosions:
            e.active = False
        self.game_over = False
        self.winner = None
        self.distance = 0
        self.score = 0
        self._prev_p1_jump = False
        self._prev_p1_shoot = False
        self._prev_p2_bomb = False

    def set_player_mode(self, mode):
        """Set 1 or 2 player mode."""
        self.player_mode = mode

    def _update_ufo_ai(self):
        """AI control for UFO in 1-player mode."""
        # Move towards position above buggy with some offset
        self._ai_move_timer += 1
        
        # Update target every 30 frames
        if self._ai_move_timer >= 30:
            self._ai_move_timer = 0
            # Target slightly ahead of buggy with some randomness
            self._ai_target_x = self.buggy.x + random.randint(-20, 40)
        
        # Move UFO towards target
        if self.ufo.x < self._ai_target_x - 5:
            self.ufo.x = min(DISPLAY_WIDTH - UFO_WIDTH, self.ufo.x + UFO_SPEED)
        elif self.ufo.x > self._ai_target_x + 5:
            self.ufo.x = max(0, self.ufo.x - UFO_SPEED)
        
        # Random vertical movement
        if random.random() < 0.02:
            if random.random() < 0.5:
                self.ufo.y = max(UFO_ZONE_TOP, self.ufo.y - UFO_SPEED)
            else:
                self.ufo.y = min(UFO_ZONE_BOTTOM - UFO_HEIGHT, self.ufo.y + UFO_SPEED)
        
        # Drop bombs periodically when over buggy
        self._ai_bomb_timer += 1
        if self._ai_bomb_timer >= 45:  # Every ~1.5 sec
            # Only drop if roughly above buggy
            if abs(self.ufo.x - self.buggy.x) < 25:
                if self.ufo.bomb_cooldown <= 0 and self._drop_bomb():
                    self._ai_bomb_timer = 0
                    return True
        return False

    def _spawn_explosion(self, x, y):
        for exp in self.explosions:
            if not exp.active:
                exp.start(x, y)
                return

    def _fire_bullet(self):
        for bullet in self.bullets:
            if not bullet.active:
                bx = self.buggy.x + BUGGY_WIDTH // 2 - BULLET_WIDTH // 2
                by = self.buggy.y - BULLET_HEIGHT
                bullet.fire(bx, by)
                self.buggy.shoot_cooldown = SHOOT_COOLDOWN
                return True
        return False

    def _drop_bomb(self):
        for bomb in self.bombs:
            if not bomb.active:
                bx = self.ufo.x + UFO_WIDTH // 2 - BOMB_WIDTH // 2
                by = self.ufo.y + UFO_HEIGHT
                bomb.drop(bx, by)
                self.ufo.bomb_cooldown = BOMB_COOLDOWN
                return True
        return False

    def _check_collisions(self):
        """Check all collisions. Returns list of events."""
        events = []

        # Bullets vs UFO
        for bullet in self.bullets:
            if bullet.active:
                if (bullet.x < self.ufo.x + UFO_WIDTH and
                    bullet.x + BULLET_WIDTH > self.ufo.x and
                    bullet.y < self.ufo.y + UFO_HEIGHT and
                    bullet.y + BULLET_HEIGHT > self.ufo.y):
                    bullet.active = False
                    self._spawn_explosion(self.ufo.x + UFO_WIDTH // 2,
                                         self.ufo.y + UFO_HEIGHT // 2)
                    if not self.ufo.hit():
                        events.append("ufo_destroyed")
                    else:
                        events.append("ufo_hit")
                    self.score += 100

        # Bombs vs Buggy
        for bomb in self.bombs:
            if bomb.active and self.buggy.invincible == 0:
                if (bomb.x < self.buggy.x + BUGGY_WIDTH and
                    bomb.x + BOMB_WIDTH > self.buggy.x and
                    bomb.y < self.buggy.y + BUGGY_HEIGHT and
                    bomb.y + BOMB_HEIGHT > self.buggy.y):
                    bomb.active = False
                    self._spawn_explosion(self.buggy.x + BUGGY_WIDTH // 2,
                                         self.buggy.y + BUGGY_HEIGHT // 2)
                    if not self.buggy.hit():
                        events.append("buggy_destroyed")
                    else:
                        events.append("buggy_hit")

        return events

    def update(self, inp):
        """Update game state. Returns list of events."""
        events = []

        if self.game_over:
            return events

        # Handle respawn phases
        if self.buggy.respawning:
            self.buggy.respawn_timer -= 1
            
            if self.buggy.respawn_phase == 1:
                # Phase 1: explosion playing, terrain STOPPED
                if self.buggy.respawn_timer <= 0:
                    # Transition to phase 2: reset terrain and wait
                    self.terrain.reset()
                    self.buggy.x = 20.0
                    self.buggy.y = float(GROUND_Y - BUGGY_HEIGHT)
                    self.buggy.vy = 0.0
                    self.buggy.on_ground = True
                    self.buggy.respawn_phase = 2
                    self.buggy.respawn_timer = 30  # 1 sec stationary on flat ground
                return events
                
            elif self.buggy.respawn_phase == 2:
                # Phase 2: stationary on flat ground (80px ahead), no scrolling
                if self.buggy.respawn_timer <= 0:
                    self.buggy.respawning = False
                    self.buggy.respawn_phase = 0
                    events.append("respawn")
                return events

        # Update terrain scroll
        self.terrain.update()
        self.distance += SCROLL_SPEED
        self.score += 1

        # --- Player 1 (Buggy) ---
        if inp.p1_left:
            self.buggy.x = max(0, self.buggy.x - BUGGY_SPEED)
        if inp.p1_right:
            self.buggy.x = min(DISPLAY_WIDTH // 2, self.buggy.x + BUGGY_SPEED)

        # Jump (edge triggered)
        if inp.p1_jump and not self._prev_p1_jump:
            if self.buggy.jump():
                events.append("jump")
        self._prev_p1_jump = inp.p1_jump

        # Shoot (edge triggered)
        if inp.p1_shoot and not self._prev_p1_shoot:
            if self.buggy.shoot_cooldown <= 0 and self._fire_bullet():
                events.append("shoot")
        self._prev_p1_shoot = inp.p1_shoot

        # Update buggy physics
        landed = self.buggy.update()

        # Check crater collision - both on landing AND while walking on ground
        if self.buggy.on_ground and not self.buggy.respawning and self.terrain.is_over_crater(self.buggy.x, BUGGY_WIDTH):
            self._spawn_explosion(self.buggy.x + BUGGY_WIDTH // 2,
                                 self.buggy.y + BUGGY_HEIGHT // 2)
            if not self.buggy.hit():
                events.append("buggy_destroyed")
            else:
                events.append("crater_fall")
                # Phase 1: explosion plays, buggy hidden, terrain stopped
                self.buggy.respawning = True
                self.buggy.respawn_phase = 1
                self.buggy.respawn_timer = 20  # explosion duration
                self.buggy.y = -100  # Hide buggy off screen

        # --- Player 2 (UFO) or AI ---
        if self.player_mode == 2:
            # 2-player: P2 controls UFO
            if inp.p2_left:
                self.ufo.x = max(0, self.ufo.x - UFO_SPEED)
            if inp.p2_right:
                self.ufo.x = min(DISPLAY_WIDTH - UFO_WIDTH, self.ufo.x + UFO_SPEED)
            if inp.p2_up:
                self.ufo.y = max(UFO_ZONE_TOP, self.ufo.y - UFO_SPEED)
            if inp.p2_down:
                self.ufo.y = min(UFO_ZONE_BOTTOM - UFO_HEIGHT, self.ufo.y + UFO_SPEED)

            # Drop bomb (edge triggered)
            if inp.p2_bomb and not self._prev_p2_bomb:
                if self.ufo.bomb_cooldown <= 0 and self._drop_bomb():
                    events.append("bomb_drop")
            self._prev_p2_bomb = inp.p2_bomb
        else:
            # 1-player: AI controls UFO
            if self._update_ufo_ai():
                events.append("bomb_drop")

        self.ufo.update()

        # --- Update projectiles ---
        for bullet in self.bullets:
            bullet.update()
        for bomb in self.bombs:
            bomb.update()
        for exp in self.explosions:
            exp.update()

        # --- Collisions ---
        events.extend(self._check_collisions())

        # --- Win conditions ---
        if self.buggy.lives <= 0:
            self.game_over = True
            self.winner = "ufo"
            events.append("gameover")
        elif self.ufo.hp <= 0:
            self.game_over = True
            self.winner = "buggy"
            events.append("victory")

        return events
