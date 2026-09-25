# Pacman Model - Game State and Logic
# For 128x64 RGB Matrix (4 panels, rotated 90°) with 2-player support

# Display/Grid constants
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
CELL_SIZE = 4
HUD_HEIGHT = 8
GRID_W = 32  # 128 / 4
GRID_H = 14  # (64 - 8) / 4

# Cell types
EMPTY = 0
WALL = 1
DOT = 2
PELLET = 3
GHOST_HOUSE = 4

# Direction constants (dx, dy)
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
NONE = (0, 0)

# Ghost states
GHOST_SCATTER = 0
GHOST_CHASE = 1
GHOST_FRIGHTENED = 2
GHOST_EATEN = 3

# Maze layout: 32x14 grid (each row MUST be exactly 32 chars)
# W=wall, .=dot, o=power pellet, -=empty/tunnel, G=ghost house, P=player spawn
#        0         1         2         3
#        0123456789012345678901234567890123456789
MAZE_DATA = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "W......W......-WW-......W......W",
    "WoWWWW.W.WWWW.-WW-.WWWW.W.WWWWoW",
    "W.WWWW.W.WWWW.-WW-.WWWW.W.WWWW.W",
    "W..............................W",
    "W.WW.WWWWW.WW.-WW-.WW.WWWWW.WW.W",
    "W....W.....WWGGGGWW.....W.....WW",
    "WWWW.W.WWW.WWGGGGWW.WWW.W.WWWWWW",
    "W....W.....WW----WW.....W......W",
    "W.WWWWWWWW.WWWWWWWW.WWWWWWWWWW.W",
    "W..............................W",
    "W.WWWW.WWWWWW.-WW-.WWWWWW.WWWW.W",
    "Wo....W......-PP--......W.....oW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

# P1 spawn: bottom-left area, P2 spawn: bottom-right area
P1_SPAWN = (7, 12)
P2_SPAWN = (24, 12)

# Ghost spawns (in ghost house area)
GHOST_SPAWNS = [(14, 6), (15, 6), (16, 6), (17, 6)]
GHOST_SCATTER_TARGETS = [(0, 0), (31, 0), (0, 13), (31, 13)]


class Pacman:
    """Single Pacman entity."""
    __slots__ = ('x', 'y', 'spawn_x', 'spawn_y', 'direction', 'next_direction',
                 'player_id', 'score', 'anim_frame', 'move_timer', 'speed')

    def __init__(self, start_x, start_y, player_id):
        self.x = float(start_x)
        self.y = float(start_y)
        self.spawn_x = start_x
        self.spawn_y = start_y
        self.direction = RIGHT if player_id == 1 else LEFT
        self.next_direction = None
        self.player_id = player_id
        self.score = 0
        self.anim_frame = 0
        self.move_timer = 0.0
        self.speed = 0.15  # Seconds per cell

    def reset(self):
        """Reset to spawn position."""
        self.x = float(self.spawn_x)
        self.y = float(self.spawn_y)
        self.direction = RIGHT if self.player_id == 1 else LEFT
        self.next_direction = None
        self.anim_frame = 0
        self.move_timer = 0.0

    @property
    def grid_x(self):
        return int(self.x + 0.5)

    @property
    def grid_y(self):
        return int(self.y + 0.5)


class Ghost:
    """Single ghost entity."""
    __slots__ = ('x', 'y', 'spawn_x', 'spawn_y', 'direction', 'state',
                 'behavior', 'color_idx', 'frightened_timer', 'move_timer', 'speed')

    def __init__(self, start_x, start_y, behavior, color_idx):
        self.x = float(start_x)
        self.y = float(start_y)
        self.spawn_x = start_x
        self.spawn_y = start_y
        self.direction = UP
        self.state = GHOST_SCATTER
        self.behavior = behavior  # 0=blinky, 1=pinky, 2=inky, 3=clyde
        self.color_idx = color_idx
        self.frightened_timer = 0.0
        self.move_timer = 0.0
        self.speed = 0.18  # Slightly slower than Pacman

    def reset(self):
        """Reset to spawn position."""
        self.x = float(self.spawn_x)
        self.y = float(self.spawn_y)
        self.direction = UP
        self.state = GHOST_SCATTER
        self.frightened_timer = 0.0
        self.move_timer = 0.0

    @property
    def grid_x(self):
        return int(self.x + 0.5)

    @property
    def grid_y(self):
        return int(self.y + 0.5)


class PacmanModel:
    """Main game state for 2-player Pacman."""

    MAX_LIVES = 3
    FRIGHTENED_TIME = 6.0  # Seconds ghosts stay frightened
    DOT_SCORE = 10
    PELLET_SCORE = 50
    GHOST_SCORE = 200

    def __init__(self, high_score=0):
        self.maze = []  # 2D array of cell types (walls only, immutable)
        self.dots = []  # 2D array of dot presence
        self.pellets = set()  # Set of (x, y) for power pellets

        self.pacman1 = None
        self.pacman2 = None
        self.ghosts = []

        self.lives = self.MAX_LIVES
        self.game_over = False
        self.level = 1
        self.dots_remaining = 0
        self.high_score = high_score
        self.player_mode = 2  # 1 or 2 players

        self._load_maze()
        self._spawn_entities()

    def _load_maze(self):
        """Parse MAZE_DATA into maze structure."""
        self.maze = []
        self.dots = []
        self.pellets = set()
        self.dots_remaining = 0

        for y, row in enumerate(MAZE_DATA):
            maze_row = []
            dot_row = []
            for x, char in enumerate(row):
                if char == 'W':
                    maze_row.append(WALL)
                    dot_row.append(False)
                elif char == '.':
                    maze_row.append(EMPTY)
                    dot_row.append(True)
                    self.dots_remaining += 1
                elif char == 'o':
                    maze_row.append(EMPTY)
                    dot_row.append(False)
                    self.pellets.add((x, y))
                elif char == 'G':
                    maze_row.append(GHOST_HOUSE)
                    dot_row.append(False)
                elif char == 'P':
                    maze_row.append(EMPTY)
                    dot_row.append(False)
                else:  # '-' or other
                    maze_row.append(EMPTY)
                    dot_row.append(False)
            self.maze.append(maze_row)
            self.dots.append(dot_row)

    def _spawn_entities(self):
        """Create Pacmen and ghosts."""
        self.pacman1 = Pacman(P1_SPAWN[0], P1_SPAWN[1], 1)
        self.pacman2 = Pacman(P2_SPAWN[0], P2_SPAWN[1], 2)

        # Ghost colors: 5=red, 6=pink, 7=cyan, 8=orange
        self.ghosts = []
        for i, (gx, gy) in enumerate(GHOST_SPAWNS):
            self.ghosts.append(Ghost(gx, gy, i, 5 + i))

    def reset(self):
        """Reset for new game."""
        self._load_maze()
        self.pacman1.reset()
        self.pacman1.score = 0
        self.pacman2.reset()
        self.pacman2.score = 0
        for ghost in self.ghosts:
            ghost.reset()
        self.lives = self.MAX_LIVES
        self.game_over = False
        self.level = 1

    def set_player_mode(self, mode):
        """Set 1-player or 2-player mode."""
        self.player_mode = mode
        if mode == 1:
            # In 1-player mode, hide P2 off-screen
            self.pacman2.x = -10
            self.pacman2.y = -10

    def reset_positions(self):
        """Reset positions only (after death)."""
        self.pacman1.reset()
        self.pacman2.reset()
        for ghost in self.ghosts:
            ghost.reset()

    def is_wall(self, gx, gy):
        """Check if grid position is a wall."""
        if gx < 0 or gx >= GRID_W or gy < 0 or gy >= GRID_H:
            return True
        return self.maze[gy][gx] == WALL

    def can_move(self, gx, gy, direction):
        """Check if can move in direction from grid position."""
        nx = gx + direction[0]
        ny = gy + direction[1]
        return not self.is_wall(nx, ny)

    def _move_pacman(self, pacman, dt):
        """Move a single Pacman, return events."""
        events = []
        pacman.move_timer += dt

        if pacman.move_timer < pacman.speed:
            return events
        pacman.move_timer = 0.0

        gx, gy = pacman.grid_x, pacman.grid_y

        # Try next_direction first (buffered input)
        if pacman.next_direction and self.can_move(gx, gy, pacman.next_direction):
            pacman.direction = pacman.next_direction
            pacman.next_direction = None

        # Move in current direction if possible
        if self.can_move(gx, gy, pacman.direction):
            pacman.x += pacman.direction[0]
            pacman.y += pacman.direction[1]
            pacman.anim_frame = (pacman.anim_frame + 1) % 3

            # Check dot collection
            nx, ny = pacman.grid_x, pacman.grid_y
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                if self.dots[ny][nx]:
                    self.dots[ny][nx] = False
                    self.dots_remaining -= 1
                    pacman.score += self.DOT_SCORE
                    events.append(('dot', pacman.player_id))

                if (nx, ny) in self.pellets:
                    self.pellets.remove((nx, ny))
                    pacman.score += self.PELLET_SCORE
                    self._frighten_ghosts()
                    events.append(('pellet', pacman.player_id))

        # Update high score
        total_score = self.pacman1.score + self.pacman2.score
        if total_score > self.high_score:
            self.high_score = total_score

        return events

    def _frighten_ghosts(self):
        """Set all ghosts to frightened state."""
        for ghost in self.ghosts:
            if ghost.state != GHOST_EATEN:
                ghost.state = GHOST_FRIGHTENED
                ghost.frightened_timer = self.FRIGHTENED_TIME
                # Reverse direction
                ghost.direction = (-ghost.direction[0], -ghost.direction[1])

    def _move_ghost(self, ghost, dt):
        """Move a single ghost with simple AI."""
        ghost.move_timer += dt

        # Update frightened timer
        if ghost.state == GHOST_FRIGHTENED:
            ghost.frightened_timer -= dt
            if ghost.frightened_timer <= 0:
                ghost.state = GHOST_CHASE

        speed = ghost.speed * 1.5 if ghost.state == GHOST_EATEN else ghost.speed
        if ghost.state == GHOST_FRIGHTENED:
            speed = ghost.speed * 0.6  # Slower when frightened

        if ghost.move_timer < speed:
            return
        ghost.move_timer = 0.0

        gx, gy = ghost.grid_x, ghost.grid_y

        # Get target based on state and behavior
        if ghost.state == GHOST_EATEN:
            target = GHOST_SPAWNS[ghost.behavior]
            if gx == target[0] and gy == target[1]:
                ghost.state = GHOST_SCATTER
        elif ghost.state == GHOST_FRIGHTENED:
            target = self._get_flee_target(ghost)
        elif ghost.state == GHOST_CHASE:
            target = self._get_chase_target(ghost)
        else:  # SCATTER
            target = GHOST_SCATTER_TARGETS[ghost.behavior]

        # Choose best direction toward target
        best_dir = ghost.direction
        best_dist = 9999

        for d in [UP, DOWN, LEFT, RIGHT]:
            # Can't reverse direction (except when frightened)
            if ghost.state != GHOST_FRIGHTENED:
                if d[0] == -ghost.direction[0] and d[1] == -ghost.direction[1]:
                    continue
            nx, ny = gx + d[0], gy + d[1]
            if not self.is_wall(nx, ny):
                dist = abs(nx - target[0]) + abs(ny - target[1])
                if dist < best_dist:
                    best_dist = dist
                    best_dir = d

        ghost.direction = best_dir
        if self.can_move(gx, gy, ghost.direction):
            ghost.x += ghost.direction[0]
            ghost.y += ghost.direction[1]

    def _get_chase_target(self, ghost):
        """Get target for chase mode based on ghost behavior."""
        # Find nearest pacman
        d1 = abs(ghost.x - self.pacman1.x) + abs(ghost.y - self.pacman1.y)
        d2 = abs(ghost.x - self.pacman2.x) + abs(ghost.y - self.pacman2.y)
        target_pac = self.pacman1 if d1 <= d2 else self.pacman2

        if ghost.behavior == 0:  # Blinky: direct chase
            return (target_pac.grid_x, target_pac.grid_y)
        elif ghost.behavior == 1:  # Pinky: 4 ahead
            tx = target_pac.grid_x + target_pac.direction[0] * 4
            ty = target_pac.grid_y + target_pac.direction[1] * 4
            return (max(0, min(GRID_W - 1, tx)), max(0, min(GRID_H - 1, ty)))
        elif ghost.behavior == 2:  # Inky: random-ish
            return (target_pac.grid_x, target_pac.grid_y)
        else:  # Clyde: chase if far, scatter if close
            dist = abs(ghost.x - target_pac.x) + abs(ghost.y - target_pac.y)
            if dist > 8:
                return (target_pac.grid_x, target_pac.grid_y)
            else:
                return GHOST_SCATTER_TARGETS[ghost.behavior]

    def _get_flee_target(self, ghost):
        """Get target to flee from players."""
        # Move away from nearest player
        d1 = abs(ghost.x - self.pacman1.x) + abs(ghost.y - self.pacman1.y)
        d2 = abs(ghost.x - self.pacman2.x) + abs(ghost.y - self.pacman2.y)
        nearest = self.pacman1 if d1 <= d2 else self.pacman2
        # Target opposite corner
        tx = GRID_W - 1 if nearest.grid_x < GRID_W // 2 else 0
        ty = GRID_H - 1 if nearest.grid_y < GRID_H // 2 else 0
        return (tx, ty)

    def _check_ghost_collisions(self):
        """Check Pacman-Ghost collisions, return events."""
        events = []
        pacmen = [self.pacman1] if self.player_mode == 1 else [self.pacman1, self.pacman2]
        for pacman in pacmen:
            for ghost in self.ghosts:
                if ghost.state == GHOST_EATEN:
                    continue
                # AABB collision with tolerance
                if abs(pacman.x - ghost.x) < 0.8 and abs(pacman.y - ghost.y) < 0.8:
                    if ghost.state == GHOST_FRIGHTENED:
                        # Eat ghost
                        ghost.state = GHOST_EATEN
                        pacman.score += self.GHOST_SCORE
                        events.append(('ate_ghost', pacman.player_id))
                    else:
                        # Pacman dies
                        events.append(('death', pacman.player_id))
        return events

    def update(self, dt, p1_dir=None, p2_dir=None):
        """Update game state. Returns list of events."""
        if self.game_over:
            return []

        events = []

        # Set buffered directions from input
        if p1_dir:
            self.pacman1.next_direction = p1_dir
        if p2_dir and self.player_mode == 2:
            self.pacman2.next_direction = p2_dir

        # Move Pacmen
        events.extend(self._move_pacman(self.pacman1, dt))
        if self.player_mode == 2:
            events.extend(self._move_pacman(self.pacman2, dt))

        # Move ghosts
        for ghost in self.ghosts:
            self._move_ghost(ghost, dt)

        # Check collisions
        collision_events = self._check_ghost_collisions()
        events.extend(collision_events)

        # Handle deaths
        for event in collision_events:
            if event[0] == 'death':
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over = True
                    events.append(('game_over', None))
                else:
                    self.reset_positions()
                    events.append(('life_lost', None))
                break  # Only one death per frame

        # Check win condition
        if self.dots_remaining <= 0 and len(self.pellets) == 0:
            self.level += 1
            self._load_maze()
            self.reset_positions()
            events.append(('level_complete', None))

        return events
