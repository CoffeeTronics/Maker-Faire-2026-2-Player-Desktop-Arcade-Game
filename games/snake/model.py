# model.py - Snake Game Model (MVC pattern)
# Ported for 128x64 RGB Matrix with 64x32 grid (2x2 pixels per cell)

import struct
import microcontroller

UP    = (0, -1)
DOWN  = (0,  1)
LEFT  = (-1, 0)
RIGHT = (1,  0)

GRID_W = 64
GRID_H = 32


class SnakeModel:
    """Pure game state -- no hardware references.

    Attributes (all public -- read by the View via the Controller):
        snake      -- list of (x, y) tuples; index 0 is the head
        direction  -- current movement direction (UP/DOWN/LEFT/RIGHT)
        food       -- (x, y) position of the current food pellet
        score      -- points scored this round
        high_score -- best score ever (managed externally by HighScoreManager)
        lives      -- remaining lives (starts at 3)
        game_over  -- True when all lives are lost
        demo_mode  -- True when the AI is playing automatically
    """

    def __init__(self, high_score=0):
        self.snake     = []
        self.direction = RIGHT
        self.food      = (GRID_W // 3, GRID_H // 3)
        self.grow      = 0
        self.score     = 0
        self.high_score = high_score
        self.lives     = 3
        self.game_over = False
        self.demo_mode = False
        self.reset(reset_score=True)

    def reset(self, reset_score=True):
        """Reset the snake to its starting position."""
        self.snake = [(GRID_W // 2 + i, GRID_H // 2)
                      for i in range(1, -3, -1)]
        self.direction = RIGHT
        self.grow = 0
        if reset_score:
            self.score = 0
            self.lives = 3
            self.game_over = False

    def toggle_demo(self):
        """Flip between manual play and AI demo mode."""
        self.demo_mode = not self.demo_mode
        return self.demo_mode

    def set_direction(self, new_dir):
        """Accept a new direction (rejects 180-degree reversals)."""
        rev = (-self.direction[0], -self.direction[1])
        if new_dir != rev:
            self.direction = new_dir

    def step(self):
        """Advance the game by one tick.

        Returns
        -------
        None         -- normal move
        "ate_food"   -- snake ate food this tick
        "hit"        -- snake hit wall or self, lost a life
        "game_over"  -- snake lost all lives
        """
        if self.demo_mode:
            self._ai_step()

        dx, dy = self.direction
        nx = self.snake[0][0] + dx
        ny = self.snake[0][1] + dy

        # Wall collision
        if nx < 0 or ny < 0 or nx >= GRID_W or ny >= GRID_H:
            return self._handle_death()
        # Self collision
        if (nx, ny) in self.snake:
            return self._handle_death()

        self.snake.insert(0, (nx, ny))

        event = None
        if (nx, ny) == self.food:
            if not self.demo_mode:
                self.score += 1
                if self.score > self.high_score:
                    self.high_score = self.score
            self.grow += 2
            self._place_food()
            event = "ate_food"

        if self.grow > 0:
            self.grow -= 1
        else:
            self.snake.pop()

        return event

    def _handle_death(self):
        """Handle snake death - lose a life or game over."""
        if self.demo_mode:
            # Demo mode: just reset, no lives
            self.reset(reset_score=False)
            return "hit"

        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
            return "game_over"
        else:
            # Reset snake position but keep score
            self.snake = [(GRID_W // 2 + i, GRID_H // 2)
                          for i in range(1, -3, -1)]
            self.direction = RIGHT
            self.grow = 0
            return "hit"

    def _place_food(self):
        """Find an empty cell for the next food pellet."""
        start = ((self.food[0] + 7) % GRID_W, (self.food[1] + 5) % GRID_H)
        snake_set = set(self.snake)
        for dy in range(GRID_H):
            for dx in range(GRID_W):
                x = (start[0] + dx) % GRID_W
                y = (start[1] + dy) % GRID_H
                if (x, y) not in snake_set:
                    self.food = (x, y)
                    return

    def _ai_step(self):
        """AI autopilot for demo mode."""
        head = self.snake[0]
        body_set = set(self.snake)
        rev = (-self.direction[0], -self.direction[1])

        for d in self._neighbors_preferring_food(head, self.food):
            if d == rev:
                continue
            nx, ny = head[0] + d[0], head[1] + d[1]
            if not self._would_collide((nx, ny), body_set):
                self.direction = d
                return

        nx, ny = head[0] + self.direction[0], head[1] + self.direction[1]
        if not self._would_collide((nx, ny), body_set):
            return

        for d in (RIGHT, DOWN, LEFT, UP):
            if d == rev:
                continue
            nx, ny = head[0] + d[0], head[1] + d[1]
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                self.direction = d
                return

    @staticmethod
    def _neighbors_preferring_food(head, target):
        hx, hy = head
        fx, fy = target
        dx = 1 if fx > hx else (-1 if fx < hx else 0)
        dy = 1 if fy > hy else (-1 if fy < hy else 0)
        if abs(fx - hx) >= abs(fy - hy):
            ordered = [(dx, 0), (0, dy), (-dx, 0), (0, -dy)]
        else:
            ordered = [(0, dy), (dx, 0), (0, -dy), (-dx, 0)]
        out = []
        for d in ordered + [RIGHT, LEFT, DOWN, UP]:
            if d not in out:
                out.append(d)
        return out

    @staticmethod
    def _would_collide(pos, body_set):
        x, y = pos
        return x < 0 or y < 0 or x >= GRID_W or y >= GRID_H or pos in body_set
