# -*- coding: utf-8 -*-
"""
Snake · A* Control + Real-time Decision Panel
Board: 20x20, step interval: 300ms, initial length: 40
Changes: wall collision does not kill, top bar shows death count and max length, auto-reset
"""

import pygame
import random
import heapq
import sys

# ====== Constants ======
COLS = 20
ROWS = 20
CELL_SIZE = 20
GRID_WIDTH = COLS * CELL_SIZE
GRID_HEIGHT = ROWS * CELL_SIZE
INFO_HEIGHT = 40
PANEL_WIDTH = 200
WIDTH = GRID_WIDTH + PANEL_WIDTH
HEIGHT = GRID_HEIGHT + INFO_HEIGHT
FPS = 60
MOVE_INTERVAL = 300          # 300ms per step

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 180, 0)
INFO_BG = (30, 30, 40)
PANEL_BG = (20, 22, 30)
TEXT_COLOR = (200, 210, 230)
HIGHLIGHT = (255, 200, 100)
WARN_COLOR = (255, 80, 80)

# ====== A* Algorithm ======
def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def astar(start, goal, obstacles, width, height):
    if start == goal:
        return []
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: manhattan(start, goal)}
    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path
        for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)):
            neighbor = (current[0]+dx, current[1]+dy)
            if not (0 <= neighbor[0] < width and 0 <= neighbor[1] < height):
                continue
            if neighbor in obstacles:
                continue
            tentative_g = g_score[current] + 1
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + manhattan(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return []

# ====== Game Class ======
class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("A* Snake · Decision Panel")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 18)
        self.small_font = pygame.font.Font(None, 15)
        self.big_font = pygame.font.Font(None, 48)
        self.decision_log = []
        self.current_action = "Straight"
        self.last_move_time = pygame.time.get_ticks()
        # ----- New statistics variables -----
        self.death_count = 0          # number of deaths (due to self-collision)
        self.max_length = 0           # historical maximum snake length
        self.reset_game()

    def reset_game(self):
        """Reset snake, food, steps, score; keep death count and max length"""
        start_x = COLS // 2
        start_y = ROWS // 2
        self.snake = [(start_x - i, start_y) for i in range(40)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.steps = 0
        self.game_over = False
        self.win = False
        self.spawn_food()
        self.decision_log.clear()
        # Update max length
        if len(self.snake) > self.max_length:
            self.max_length = len(self.snake)

    def spawn_food(self):
        if len(self.snake) >= COLS * ROWS:
            self.win = True
            self.game_over = True
            return
        for _ in range(2000):
            fx = random.randint(0, COLS-1)
            fy = random.randint(0, ROWS-1)
            if (fx, fy) not in self.snake:
                self.food = (fx, fy)
                return
        for y in range(ROWS):
            for x in range(COLS):
                if (x, y) not in self.snake:
                    self.food = (x, y)
                    return

    def decide_action(self):
        head = self.snake[0]
        obstacles = set(self.snake[1:])

        safe_dirs = []
        for d in ((1,0), (-1,0), (0,1), (0,-1)):
            if d == (-self.direction[0], -self.direction[1]):
                continue
            nx, ny = head[0]+d[0], head[1]+d[1]
            if 0 <= nx < COLS and 0 <= ny < ROWS and (nx, ny) not in obstacles:
                safe_dirs.append(d)

        path = astar(head, self.food, obstacles, COLS, ROWS)
        path_len = len(path)

        if path_len >= 1:
            next_cell = path[0]
            target_dir = (next_cell[0] - head[0], next_cell[1] - head[1])
            decision_info = f"Path len {path_len}"
        elif safe_dirs:
            target_dir = min(safe_dirs, key=lambda d: manhattan((head[0]+d[0], head[1]+d[1]), self.food))
            decision_info = "No path, go greedy"
        else:
            # No safe direction → death (self-collision or stuck)
            self.game_over = True
            return "Straight", self.direction, 0, 0, "No safe dir!"

        if target_dir == self.direction:
            action = "Straight"
        elif (target_dir[0], target_dir[1]) == (self.direction[1], -self.direction[0]):
            action = "Right"
        elif (target_dir[0], target_dir[1]) == (-self.direction[1], self.direction[0]):
            action = "Left"
        else:
            action = "Straight"

        self.decision_log.append({
            "action": action,
            "safe_dirs": len(safe_dirs),
            "path_len": path_len,
            "decision": decision_info,
            "step": self.steps
        })
        if len(self.decision_log) > 20:
            self.decision_log.pop(0)

        return action, target_dir, len(safe_dirs), path_len, decision_info

    def move_snake(self):
        if self.game_over:
            return False

        action, target_dir, safe_cnt, path_len, info = self.decide_action()
        self.current_action = action

        if target_dir != (-self.direction[0], -self.direction[1]):
            self.direction = target_dir
        self.next_direction = self.direction

        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # ===== Change 1: wall collision does not kill, just stuck =====
        if new_head[0] < 0 or new_head[0] >= COLS or new_head[1] < 0 or new_head[1] >= ROWS:
            # Hit wall, do nothing and return
            return False

        will_eat = (new_head == self.food)
        tail = None
        if not will_eat:
            tail = self.snake.pop()

        if new_head in self.snake:
            if tail is not None:
                self.snake.append(tail)
            # Self-collision → death, increment death count and reset
            self.death_count += 1
            # Update max length
            if len(self.snake) > self.max_length:
                self.max_length = len(self.snake)
            self.reset_game()
            return False

        self.snake.insert(0, new_head)
        self.steps += 1

        if will_eat:
            self.score += 1
            self.spawn_food()
            if len(self.snake) >= COLS * ROWS:
                self.win = True
                self.game_over = True
        # Update max length every step
        if len(self.snake) > self.max_length:
            self.max_length = len(self.snake)
        return True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Manual reset: clear death count and max length as well
                    self.death_count = 0
                    self.max_length = 0
                    self.reset_game()
                    self.max_length = len(self.snake)  # update after reset
                    continue
                # Keyboard control (for debugging, can override automatic decision)
                if self.game_over:
                    continue
                if event.key == pygame.K_UP:
                    self.next_direction = (0, -1)
                elif event.key == pygame.K_DOWN:
                    self.next_direction = (0, 1)
                elif event.key == pygame.K_LEFT:
                    self.next_direction = (-1, 0)
                elif event.key == pygame.K_RIGHT:
                    self.next_direction = (1, 0)

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_move_time >= MOVE_INTERVAL:
            self.move_snake()
            self.last_move_time = now

    def draw_panel(self):
        panel_x = GRID_WIDTH
        panel_y = INFO_HEIGHT
        panel_w = PANEL_WIDTH
        panel_h = GRID_HEIGHT
        pygame.draw.rect(self.screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.line(self.screen, (60,70,90), (panel_x, panel_y), (panel_x, panel_y+panel_h), 2)

        title = self.small_font.render("Decision Panel", True, HIGHLIGHT)
        self.screen.blit(title, (panel_x+10, panel_y+10))

        action_text = self.font.render(f"Action: {self.current_action}", True, WHITE)
        self.screen.blit(action_text, (panel_x+10, panel_y+35))

        y_offset = panel_y + 60
        for i, entry in enumerate(reversed(self.decision_log[-6:])):
            if i == 0:
                color = (255, 255, 180)
            else:
                color = (180, 180, 200)
            if entry['safe_dirs'] == 0:
                color = WARN_COLOR
            line = f"Safe:{entry['safe_dirs']}  Path:{entry['path_len']}"
            text = self.small_font.render(line, True, color)
            self.screen.blit(text, (panel_x+10, y_offset))
            y_offset += 20
            if y_offset > panel_y + panel_h - 20:
                break

        if self.game_over:
            warn = self.font.render("!!! Game Over", True, WARN_COLOR)
            self.screen.blit(warn, (panel_x+10, panel_y+panel_h-40))

    def draw(self):
        self.screen.fill(BLACK)

        # ----- Change 2: top info bar adds statistics -----
        info_rect = pygame.Rect(0, 0, WIDTH, INFO_HEIGHT)
        pygame.draw.rect(self.screen, INFO_BG, info_rect)
        # Left part: score, length, steps
        left_text = f"Score:{self.score}  Len:{len(self.snake)}  Steps:{self.steps}"
        score_text = self.font.render(left_text, True, TEXT_COLOR)
        self.screen.blit(score_text, (10, 10))
        # Right part: death count, max length
        right_text = f"Deaths:{self.death_count}  MaxLen:{self.max_length}"
        stats_text = self.font.render(right_text, True, HIGHLIGHT)
        # Position to the right
        text_width = stats_text.get_width()
        self.screen.blit(stats_text, (WIDTH - text_width - 20, 10))

        # Grid
        offset_y = INFO_HEIGHT
        for x in range(0, GRID_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, (40,40,40), (x, offset_y), (x, offset_y+GRID_HEIGHT), 1)
        for y in range(0, GRID_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, (40,40,40), (0, offset_y+y), (GRID_WIDTH, offset_y+y), 1)

        # Food
        fx, fy = self.food
        cx = fx * CELL_SIZE + CELL_SIZE//2
        cy = fy * CELL_SIZE + CELL_SIZE//2 + offset_y
        pygame.draw.circle(self.screen, RED, (cx, cy), CELL_SIZE//2 - 2)

        # Snake
        for idx, (sx, sy) in enumerate(self.snake):
            x = sx * CELL_SIZE
            y = sy * CELL_SIZE + offset_y
            color = DARK_GREEN if idx == 0 else GREEN
            pygame.draw.rect(self.screen, color, (x+1, y+1, CELL_SIZE-2, CELL_SIZE-2))
            if idx == 0:
                dx, dy = self.direction
                if dx == 1:
                    eye1 = (x+CELL_SIZE-6, y+4)
                    eye2 = (x+CELL_SIZE-6, y+CELL_SIZE-6)
                elif dx == -1:
                    eye1 = (x+4, y+4)
                    eye2 = (x+4, y+CELL_SIZE-6)
                elif dy == -1:
                    eye1 = (x+4, y+4)
                    eye2 = (x+CELL_SIZE-6, y+4)
                else:
                    eye1 = (x+4, y+CELL_SIZE-6)
                    eye2 = (x+CELL_SIZE-6, y+CELL_SIZE-6)
                pygame.draw.circle(self.screen, WHITE, eye1, 3)
                pygame.draw.circle(self.screen, WHITE, eye2, 3)
                pygame.draw.circle(self.screen, BLACK, (eye1[0]+dx*2, eye1[1]+dy*2), 1)
                pygame.draw.circle(self.screen, BLACK, (eye2[0]+dx*2, eye2[1]+dy*2), 1)

        # Panel
        self.draw_panel()

        # Game over overlay (but game does not really stop, because auto-reset after self-collision)
        if self.game_over:
            overlay = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0, 180))
            self.screen.blit(overlay, (0, offset_y))
            msg = "You Win!" if self.win else "Game Over"
            color = (255, 215, 0) if self.win else (255, 80, 80)
            text = self.big_font.render(msg, True, color)
            text_rect = text.get_rect(center=(GRID_WIDTH//2, offset_y + GRID_HEIGHT//2 - 20))
            self.screen.blit(text, text_rect)
            sub = self.font.render("Press R to restart", True, (200,200,200))
            sub_rect = sub.get_rect(center=(GRID_WIDTH//2, offset_y + GRID_HEIGHT//2 + 40))
            self.screen.blit(sub, sub_rect)

        pygame.display.flip()

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    game = SnakeGame()
    game.run()