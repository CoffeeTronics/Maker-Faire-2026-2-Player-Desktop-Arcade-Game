# pong_model.py - MODEL (MVC pattern)
# For 128x64 RGB Matrix (4 panels, rotated 90°)

import random

# Display dimensions
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

# Paddle dimensions
PADDLE_WIDTH = 3
PADDLE_HEIGHT = 16
PADDLE_MARGIN = 2  # Distance from edge

# Ball dimensions
BALL_SIZE = 3

# Game settings
PADDLE_SPEED = 3
BALL_SPEED_X_BASE = 1.9      # Starting speed (doubled for 60fps)
BALL_SPEED_X_MAX = 5.0       # Max speed at high scores
BALL_SPEED_Y = 2.5           # Vertical speed component
WINNING_SCORE = 5

# AI settings
AI_REACTION_DELAY = 0.1  # Slight delay for AI to seem more human
AI_SPEED_FACTOR = 0.8    # AI moves slightly slower than max


class InputState:
    """Holds current input state from joysticks."""
    def __init__(self):
        # Player 1 (left paddle)
        self.up = False
        self.down = False
        # Player 2 (right paddle) - only used in 2-player mode
        self.p2_up = False
        self.p2_down = False


class Paddle:
    """A single paddle."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.score = 0

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    def move_up(self, speed=PADDLE_SPEED):
        self.y = max(0, self.y - speed)

    def move_down(self, speed=PADDLE_SPEED):
        self.y = min(DISPLAY_HEIGHT - self.height, self.y + speed)

    def center_y(self):
        return self.y + self.height / 2


class Ball:
    """The pong ball."""
    def __init__(self):
        self.reset()

    def reset(self, speed_x=BALL_SPEED_X_BASE):
        self.x = DISPLAY_WIDTH / 2 - BALL_SIZE / 2
        self.y = DISPLAY_HEIGHT / 2 - BALL_SIZE / 2
        # Random direction with given speed
        self.vx = speed_x * (1 if random.random() > 0.5 else -1)
        self.vy = BALL_SPEED_Y * (random.random() * 2 - 1)

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + BALL_SIZE

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + BALL_SIZE

    def center_y(self):
        return self.y + BALL_SIZE / 2

    def update(self):
        self.x += self.vx
        self.y += self.vy

        # Bounce off top/bottom walls
        if self.y <= 0:
            self.y = 0
            self.vy = abs(self.vy)
        elif self.y >= DISPLAY_HEIGHT - BALL_SIZE:
            self.y = DISPLAY_HEIGHT - BALL_SIZE
            self.vy = -abs(self.vy)


class PongModel:
    """Game state and logic for Pong."""

    def __init__(self):
        # Player 1 paddle on left
        self.player = Paddle(
            PADDLE_MARGIN,
            (DISPLAY_HEIGHT - PADDLE_HEIGHT) // 2
        )
        # Player 2 / AI paddle on right
        self.ai = Paddle(
            DISPLAY_WIDTH - PADDLE_MARGIN - PADDLE_WIDTH,
            (DISPLAY_HEIGHT - PADDLE_HEIGHT) // 2
        )
        self.ball = Ball()
        self.game_over = False
        self.winner = None
        self.paused = False
        self.serve_delay = 0
        self.high_score = 0
        self.player_mode = 2  # 1 = vs AI, 2 = vs Player 2

    def set_player_mode(self, mode):
        """Set 1 or 2 player mode."""
        self.player_mode = mode

    def reset(self):
        """Reset for new game."""
        self.player.score = 0
        self.ai.score = 0
        self.player.y = (DISPLAY_HEIGHT - PADDLE_HEIGHT) // 2
        self.ai.y = (DISPLAY_HEIGHT - PADDLE_HEIGHT) // 2
        self.ball.reset(BALL_SPEED_X_BASE)
        self.game_over = False
        self.winner = None
        self.paused = False
        self.serve_delay = 30  # Brief pause before ball moves

    def _get_current_speed(self):
        """Calculate ball speed based on player score."""
        total_score = self.player.score + self.ai.score
        # Lerp from BASE to MAX over ~8 points
        t = min(total_score / 8.0, 1.0)
        return BALL_SPEED_X_BASE + t * (BALL_SPEED_X_MAX - BALL_SPEED_X_BASE)

    def update(self, input_state):
        """Update game state. Returns list of events."""
        events = []

        if self.game_over or self.paused:
            return events

        # Serve delay countdown
        if self.serve_delay > 0:
            self.serve_delay -= 1
            return events

        # Player paddle movement
        if input_state.up:
            self.player.move_up()
        if input_state.down:
            self.player.move_down()

        # Right paddle movement (AI or Player 2)
        if self.player_mode == 2:
            # 2-player: P2 controls right paddle
            if input_state.p2_up:
                self.ai.move_up()
            if input_state.p2_down:
                self.ai.move_down()
        else:
            # 1-player: AI controls right paddle
            self._update_ai()

        # Ball movement
        self.ball.update()

        # Check paddle collisions
        if self._check_paddle_collision(self.player):
            events.append("hit")
        elif self._check_paddle_collision(self.ai):
            events.append("hit")

        # Check scoring
        if self.ball.left <= 0:
            # AI scores
            self.ai.score += 1
            events.append("score_ai")
            if self.ai.score >= WINNING_SCORE:
                self.game_over = True
                self.winner = "ai"
                events.append("gameover")
            else:
                self.ball.reset(self._get_current_speed())
                self.serve_delay = 30
        elif self.ball.right >= DISPLAY_WIDTH:
            # Player scores
            self.player.score += 1
            events.append("score_player")
            if self.player.score >= WINNING_SCORE:
                self.game_over = True
                self.winner = "player"
                events.append("gameover")
                # Update high score (player's winning score)
                if self.player.score > self.high_score:
                    self.high_score = self.player.score
            else:
                self.ball.reset(self._get_current_speed())
                self.serve_delay = 30

        return events

    def _check_paddle_collision(self, paddle):
        """Check and handle ball collision with a paddle."""
        # Check if ball overlaps paddle
        if (self.ball.right >= paddle.left and
            self.ball.left <= paddle.right and
            self.ball.bottom >= paddle.top and
            self.ball.top <= paddle.bottom):

            # Bounce ball
            if paddle == self.player:
                self.ball.x = paddle.right
                self.ball.vx = abs(self.ball.vx)
            else:
                self.ball.x = paddle.left - BALL_SIZE
                self.ball.vx = -abs(self.ball.vx)

            # Adjust vertical velocity based on hit position
            hit_pos = (self.ball.center_y() - paddle.center_y()) / (PADDLE_HEIGHT / 2)
            self.ball.vy = hit_pos * BALL_SPEED_Y * 2

            # Slight speed increase on each hit
            self.ball.vx *= 1.02

            return True
        return False

    def _update_ai(self):
        """Simple AI that tracks the ball."""
        # Only move if ball is coming toward AI
        if self.ball.vx > 0:
            target_y = self.ball.center_y()
            paddle_center = self.ai.center_y()

            # Add some reaction threshold
            if target_y < paddle_center - 2:
                self.ai.move_up(PADDLE_SPEED * AI_SPEED_FACTOR)
            elif target_y > paddle_center + 2:
                self.ai.move_down(PADDLE_SPEED * AI_SPEED_FACTOR)
