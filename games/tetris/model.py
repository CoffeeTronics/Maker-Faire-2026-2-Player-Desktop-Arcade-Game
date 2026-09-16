# tetris_model.py - MODEL (MVC pattern)
# For 128x64 RGB Matrix (4 panels, rotated 90°) - Horizontal Tetris (pieces move left to right)

import random

# Display dimensions
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

# Board dimensions - rotated for horizontal play
# Pieces spawn on left, move right. "Lines" are vertical columns.
CELL_SIZE = 4
BOARD_WIDTH = 28   # Horizontal length (pieces move this direction)
BOARD_HEIGHT = 14  # Vertical height (14 rows = 56px)

# Board position on screen
BOARD_X = 4
BOARD_Y = 4

# Piece definitions (standard tetrominos)
# Rotated 90 degrees so they spawn facing right
PIECES = {
    'I': [
        [(0,0), (0,1), (0,2), (0,3)],
        [(0,0), (1,0), (2,0), (3,0)],
    ],
    'O': [
        [(0,0), (1,0), (0,1), (1,1)],
    ],
    'T': [
        [(0,0), (0,1), (0,2), (1,1)],
        [(0,0), (1,0), (2,0), (1,1)],
        [(1,0), (1,1), (1,2), (0,1)],
        [(1,0), (0,1), (1,1), (2,1)],
    ],
    'S': [
        [(0,1), (0,2), (1,0), (1,1)],
        [(0,0), (1,0), (1,1), (2,1)],
    ],
    'Z': [
        [(0,0), (0,1), (1,1), (1,2)],
        [(0,1), (1,0), (1,1), (2,0)],
    ],
    'J': [
        [(0,0), (1,0), (1,1), (1,2)],
        [(0,0), (0,1), (1,0), (2,0)],
        [(0,0), (0,1), (0,2), (1,2)],
        [(0,1), (1,1), (2,0), (2,1)],
    ],
    'L': [
        [(0,0), (0,1), (0,2), (1,0)],
        [(0,0), (1,0), (2,0), (2,1)],
        [(1,0), (1,1), (1,2), (0,2)],
        [(0,0), (0,1), (1,1), (2,1)],
    ],
}

# Piece colors (palette indices)
PIECE_COLORS = {
    'I': 1,  # Cyan
    'O': 2,  # Yellow
    'T': 3,  # Purple
    'S': 4,  # Green
    'Z': 5,  # Red
    'J': 6,  # Blue
    'L': 7,  # Orange
}

# Game speeds (frames per move right)
INITIAL_DROP_FRAMES = 30
MIN_DROP_FRAMES = 5
FRAMES_DECREASE_PER_LEVEL = 3


class InputState:
    """Holds current input state from joystick/buttons."""
    def __init__(self):
        self.up = False      # Move piece up
        self.down = False    # Move piece down
        self.right = False   # Soft drop (faster move right)
        self.rotate = False  # Button A
        self.drop = False    # Button B (hard drop to right edge)


class Piece:
    """A moving tetromino piece."""
    def __init__(self, piece_type=None, board_height=BOARD_HEIGHT):
        if piece_type is None:
            piece_type = random.choice(list(PIECES.keys()))
        self.type = piece_type
        self.rotation = 0
        self.x = 0  # Start at left edge
        self.y = board_height // 2 - 1  # Center vertically
        self.color = PIECE_COLORS[piece_type]
        # Cached blocks - avoid allocation each frame
        self._cached_blocks = [(0, 0), (0, 0), (0, 0), (0, 0)]
        self._cache_x = None
        self._cache_y = None
        self._cache_rot = None

    def get_blocks(self):
        """Get current block positions relative to board (cached)."""
        if self.x == self._cache_x and self.y == self._cache_y and self.rotation == self._cache_rot:
            return self._cached_blocks
        # Recalculate and update cache in-place
        rotations = PIECES[self.type]
        blocks = rotations[self.rotation % len(rotations)]
        for i, (bx, by) in enumerate(blocks):
            self._cached_blocks[i] = (self.x + bx, self.y + by)
        # Trim if piece has fewer than 4 blocks (shouldn't happen for tetris)
        self._cache_x = self.x
        self._cache_y = self.y
        self._cache_rot = self.rotation
        return self._cached_blocks

    def get_rotated_blocks(self, direction=1):
        """Get block positions after rotation."""
        rotations = PIECES[self.type]
        new_rotation = (self.rotation + direction) % len(rotations)
        blocks = rotations[new_rotation]
        return [(self.x + bx, self.y + by) for bx, by in blocks]


class TetrisModel:
    """Game state and logic for horizontal Tetris."""

    def __init__(self):
        # Board: 0 = empty, 1-7 = piece color
        # board[y][x] where x is horizontal position
        self.board = [[0] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]
        self.current_piece = None
        self.next_piece = None
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.high_score = 0

        # Timing
        self.drop_timer = 0
        self.drop_frames = INITIAL_DROP_FRAMES
        self.move_timer = 0
        self.move_delay = 3  # Frames between repeated moves (auto-repeat rate)
        self.move_das = 10   # Frames before auto-repeat starts (DAS)

        # Input state tracking for edge detection
        self._prev_rotate = False
        self._prev_drop = False
        self._prev_up = False
        self._prev_down = False

    def reset(self):
        """Reset for new game."""
        self.board = [[0] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]
        self.current_piece = Piece()
        self.next_piece = Piece()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.drop_timer = 0
        self.drop_frames = INITIAL_DROP_FRAMES
        self.move_timer = 0
        self._prev_rotate = False
        self._prev_drop = False
        self._prev_up = False
        self._prev_down = False

    def update(self, input_state):
        """Update game state. Returns list of events."""
        events = []

        if self.game_over:
            return events

        if self.current_piece is None:
            self._spawn_piece()
            if self.game_over:
                events.append("gameover")
                return events

        # Handle rotation (edge triggered)
        if input_state.rotate and not self._prev_rotate:
            if self._try_rotate():
                events.append("rotate")
        self._prev_rotate = input_state.rotate

        # Handle hard drop (edge triggered) - instant move to right
        if input_state.drop and not self._prev_drop:
            drop_distance = self._hard_drop()
            self.score += drop_distance * 2
            events.append("drop")
            self._lock_piece()
            cleared = self._clear_lines()
            if cleared > 0:
                events.append(f"clear_{cleared}")
            self._spawn_piece()
            if self.game_over:
                events.append("gameover")
            self._prev_drop = input_state.drop
            return events
        self._prev_drop = input_state.drop

        # Handle vertical movement with DAS (Delayed Auto Shift)
        # First press: move immediately. Hold: wait DAS frames, then repeat at move_delay rate
        if input_state.up or input_state.down:
            just_pressed = (input_state.up and not self._prev_up) or (input_state.down and not self._prev_down)
            if just_pressed:
                # Immediate move on first press
                if input_state.up:
                    self._try_move(0, -1)
                elif input_state.down:
                    self._try_move(0, 1)
                self.move_timer = self.move_das  # Start DAS countdown
            elif self.move_timer <= 0:
                # Auto-repeat after DAS
                if input_state.up:
                    self._try_move(0, -1)
                elif input_state.down:
                    self._try_move(0, 1)
                self.move_timer = self.move_delay  # Faster repeat rate
            else:
                self.move_timer -= 1
        else:
            self.move_timer = 0
        self._prev_up = input_state.up
        self._prev_down = input_state.down

        # Handle soft drop (faster move right when holding right)
        drop_speed = self.drop_frames
        if input_state.right:
            drop_speed = max(2, drop_speed // 4)

        # Natural movement to the right
        self.drop_timer += 1
        if self.drop_timer >= drop_speed:
            self.drop_timer = 0
            if not self._try_move(1, 0):  # Move right
                # Piece hit the right wall or another piece
                events.append("land")
                self._lock_piece()
                cleared = self._clear_lines()
                if cleared > 0:
                    events.append(f"clear_{cleared}")
                self._spawn_piece()
                if self.game_over:
                    events.append("gameover")

        return events

    def _spawn_piece(self):
        """Spawn the next piece on the left side."""
        self.current_piece = self.next_piece if self.next_piece else Piece()
        self.next_piece = Piece()

        # Check if spawn position is valid
        if not self._is_valid_position(self.current_piece.get_blocks()):
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score

    def _is_valid_position(self, blocks):
        """Check if block positions are valid (in bounds and not overlapping)."""
        for x, y in blocks:
            if y < 0 or y >= BOARD_HEIGHT:
                return False
            if x >= BOARD_WIDTH:
                return False
            if x >= 0 and self.board[y][x] != 0:
                return False
        return True

    def _try_move(self, dx, dy):
        """Try to move piece. Returns True if successful."""
        if self.current_piece is None:
            return False

        self.current_piece.x += dx
        self.current_piece.y += dy

        if self._is_valid_position(self.current_piece.get_blocks()):
            return True
        else:
            # Revert
            self.current_piece.x -= dx
            self.current_piece.y -= dy
            return False

    def _try_rotate(self):
        """Try to rotate piece. Returns True if successful."""
        if self.current_piece is None:
            return False

        new_blocks = self.current_piece.get_rotated_blocks()
        if self._is_valid_position(new_blocks):
            rotations = PIECES[self.current_piece.type]
            self.current_piece.rotation = (self.current_piece.rotation + 1) % len(rotations)
            return True

        # Try wall kicks (shift up/down to fit)
        for kick in [-1, 1, -2, 2]:
            self.current_piece.y += kick
            new_blocks = self.current_piece.get_rotated_blocks()
            if self._is_valid_position(new_blocks):
                rotations = PIECES[self.current_piece.type]
                self.current_piece.rotation = (self.current_piece.rotation + 1) % len(rotations)
                return True
            self.current_piece.y -= kick

        return False

    def _hard_drop(self):
        """Move piece instantly to right edge. Returns distance moved."""
        distance = 0
        while self._try_move(1, 0):
            distance += 1
        return distance

    def _lock_piece(self):
        """Lock current piece into the board."""
        if self.current_piece is None:
            return

        for x, y in self.current_piece.get_blocks():
            if 0 <= y < BOARD_HEIGHT and 0 <= x < BOARD_WIDTH:
                self.board[y][x] = self.current_piece.color

        self.current_piece = None

    def _clear_lines(self):
        """Clear completed vertical columns. Returns number cleared."""
        cleared = 0

        # Check columns from right to left
        x = BOARD_WIDTH - 1
        while x >= 0:
            if all(self.board[y][x] != 0 for y in range(BOARD_HEIGHT)):
                # Remove this column - shift everything right of spawn leftward
                for shift_x in range(x, BOARD_WIDTH - 1):
                    for y in range(BOARD_HEIGHT):
                        self.board[y][shift_x] = self.board[y][shift_x + 1]
                # Clear rightmost column
                for y in range(BOARD_HEIGHT):
                    self.board[y][BOARD_WIDTH - 1] = 0
                cleared += 1
            else:
                x -= 1

        if cleared > 0:
            # Score: 100, 300, 500, 800 for 1-4 lines
            line_scores = [0, 100, 300, 500, 800]
            self.score += line_scores[min(cleared, 4)] * self.level
            self.lines += cleared

            # Level up every 10 lines
            new_level = (self.lines // 10) + 1
            if new_level > self.level:
                self.level = new_level
                self.drop_frames = max(MIN_DROP_FRAMES,
                    INITIAL_DROP_FRAMES - (self.level - 1) * FRAMES_DECREASE_PER_LEVEL)

        return cleared

    def get_ghost_blocks(self):
        """Get positions where piece would land (ghost piece)."""
        if self.current_piece is None:
            return []

        # Save position
        orig_x = self.current_piece.x

        # Move right until invalid
        while self._try_move(1, 0):
            pass

        ghost = self.current_piece.get_blocks()

        # Restore position
        self.current_piece.x = orig_x

        return ghost
