# -*- coding: utf-8 -*-
"""
Snake · Hybrid Resolution Map Version (adjustable coarse granularity)
- Food and snake head remain 1-pixel accurate
- Snake body and background use a uniform coarse granularity parameter RESOLUTION (adjustable)
- Update cycle and forget cycle are independently adjustable
- All decision logic remains completely unchanged
"""

import pygame
import random
import heapq
import sys

# ====== Adjustable Parameters ======
UPDATE_INTERVAL = 2       # Map update cycle (update every N steps)
MEMORY_TIMEOUT = 3     # Memory forget cycle (forget if not updated for more than N steps)
RESOLUTION = 1            # Coarse granularity for snake body and background (1=exact, 2,3,5,...)

# ====== Constants ======
COLS = 20
ROWS = 20
CELL_SIZE = 20
GRID_WIDTH = COLS * CELL_SIZE
GRID_HEIGHT = ROWS * CELL_SIZE
INFO_HEIGHT = 60
VIEW_WIDTH = 9
VIEW_DEPTH = 9
VIEW_WINDOW_WIDTH = 200
PANEL_WIDTH = 200
MAP_PANEL_WIDTH = 200
WIDTH = GRID_WIDTH + VIEW_WINDOW_WIDTH + PANEL_WIDTH + MAP_PANEL_WIDTH
HEIGHT = GRID_HEIGHT + INFO_HEIGHT
FPS = 60
MOVE_INTERVAL = 300

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 180, 0)
INFO_BG = (30, 30, 40)
VIEW_BG = (10, 12, 18)
PANEL_BG = (20, 22, 30)
MAP_BG = (15, 17, 25)
SNAKE_HEAD = (46, 204, 113)
SNAKE_BODY = (39, 174, 96)
SNAKE_BORDER = (26, 122, 66)
FOOD_COLOR = (241, 196, 15)
GRID_COLOR = (22, 26, 34)
TEXT_COLOR = (200, 210, 230)
VIEW_BORDER = (80, 90, 110)
HIGHLIGHT_COLOR = (255, 0, 0)
STATS_COLOR = (255, 200, 100)

# Map colors
UNKNOWN_COLOR = (40, 40, 50)       # Unexplored area (dark grey)
EMPTY_COLOR = (60, 60, 80)         # Explored empty space
OBSTACLE_COLOR = (200, 50, 50)     # Snake body (red)
FOOD_MEMORY_COLOR = (255, 0, 0)    # Food (red)
HEAD_MARK_COLOR = (255, 255, 0)    # Snake head (yellow)
ORIGIN_COLOR = (0, 255, 255)

# Map state constants
UNKNOWN = -1
EMPTY = 0
OBSTACLE = 1
FOOD = 2

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def astar_on_map(start, goal, map_state, width, height):
    """Run A* on the internal map, unknown cells are passable, snake body is obstacle"""
    if start == goal:
        return []
    if map_state[goal[1]][goal[0]] == OBSTACLE:
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
            if map_state[neighbor[1]][neighbor[0]] == OBSTACLE:
                continue
            tentative_g = g_score[current] + 1
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + manhattan(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return []

class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Snake · Hybrid Resolution Version")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 18)
        self.small_font = pygame.font.Font(None, 15)
        self.big_font = pygame.font.Font(None, 48)

        self.decision_log = []
        self.current_action = "Straight"
        self.path_len = 0
        self.food_visible = False
        self.obstacle_count = 0
        self.death_count = 0
        self.max_length = 0
        self.max_steps = 0
        self.record_log = []

        self.step_counter = 0
        self.steps_to_go = 3
        self.chosen_direction = None

        # Internal map: 20×20, stores state
        self.map_state = [[UNKNOWN for _ in range(COLS)] for _ in range(ROWS)]
        # Last update step for each cell
        self.map_last_update = [[0 for _ in range(COLS)] for _ in range(ROWS)]

        self.last_move_time = pygame.time.get_ticks()
        self.reset_game()

    def reset_game(self):
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
        self.last_move_time = pygame.time.get_ticks()
        self.decision_log = []
        self.step_counter = 0
        self.chosen_direction = None
        # Reset map: all unknown
        for y in range(ROWS):
            for x in range(COLS):
                self.map_state[y][x] = UNKNOWN
                self.map_last_update[y][x] = 0

    def spawn_food(self):
        if len(self.snake) >= COLS * ROWS:
            self.win = True
            self.game_over = True
            return
        for _ in range(2000):
            fx = random.randint(0, COLS - 1)
            fy = random.randint(0, ROWS - 1)
            if (fx, fy) not in self.snake:
                self.food = (fx, fy)
                return
        for y in range(ROWS):
            for x in range(COLS):
                if (x, y) not in self.snake:
                    self.food = (x, y)
                    return

    def record_death(self, reason="Unknown"):
        self.death_count += 1
        print(f"!!! Death reason: {reason} !!!")
        if len(self.snake) > self.max_length:
            self.max_length = len(self.snake)
        if self.steps > self.max_steps:
            self.max_steps = self.steps
        self.reset_game()

    def get_local_vision(self):
        """Return 9×9 vision, each cell as (color, dist)"""
        if self.game_over:
            return [[(BLACK, i+1) for i in range(VIEW_DEPTH)] for _ in range(VIEW_WIDTH)]
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        left_vec = (-dy, dx)
        half = VIEW_WIDTH // 2
        vision = []
        for col in range(VIEW_WIDTH):
            offset = col - half
            col_data = []
            for step in range(1, VIEW_DEPTH + 1):
                cx = head_x + dx * step + left_vec[0] * offset
                cy = head_y + dy * step + left_vec[1] * offset
                color = BLACK
                if 0 <= cx < COLS and 0 <= cy < ROWS:
                    if (cx, cy) in self.snake:
                        color = SNAKE_BODY
                    elif (cx, cy) == self.food:
                        color = FOOD_COLOR
                col_data.append((color, step))
            vision.append(col_data)
        return vision

    def update_internal_map(self, vision):
        """
        Update internal map (20×20):
        - Food and snake head remain 1-pixel accurate
        - Snake body and background use coarse granularity (RESOLUTION)
        - Coarse granularity: set all cells in the block to the corresponding state
        """
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        left_vec = (-dy, dx)
        half = VIEW_WIDTH // 2
        res = max(1, RESOLUTION)  # ensure at least 1

        # ---- Update from vision ----
        for col in range(VIEW_WIDTH):
            offset = col - half
            for row in range(VIEW_DEPTH):
                color, _ = vision[col][row]
                cx = head_x + dx * (row+1) + left_vec[0] * offset
                cy = head_y + dy * (row+1) + left_vec[1] * offset
                if not (0 <= cx < COLS and 0 <= cy < ROWS):
                    continue
                # Update map based on color, but food is written exactly
                if color == FOOD_COLOR:
                    self.map_state[cy][cx] = FOOD
                    self.map_last_update[cy][cx] = self.steps
                elif color == SNAKE_BODY:
                    # Write snake body with coarse granularity
                    block_x = (cx // res) * res
                    block_y = (cy // res) * res
                    for by in range(block_y, min(block_y+res, ROWS)):
                        for bx in range(block_x, min(block_x+res, COLS)):
                            self.map_state[by][bx] = OBSTACLE
                            self.map_last_update[by][bx] = self.steps
                elif color == BLACK:
                    # Write empty space with coarse granularity (skip if block already recorded)
                    block_x = (cx // res) * res
                    block_y = (cy // res) * res
                    already = False
                    for by in range(block_y, min(block_y+res, ROWS)):
                        for bx in range(block_x, min(block_x+res, COLS)):
                            if self.map_state[by][bx] != UNKNOWN:
                                already = True
                                break
                        if already:
                            break
                    if not already:
                        for by in range(block_y, min(block_y+res, ROWS)):
                            for bx in range(block_x, min(block_x+res, COLS)):
                                self.map_state[by][bx] = EMPTY
                                self.map_last_update[by][bx] = self.steps

        # ---- Mark entire snake body as obstacle (ensure all body parts are marked) ----
        for sx, sy in self.snake:
            if 0 <= sx < COLS and 0 <= sy < ROWS:
                # Write snake body with coarse granularity (but head will be overwritten later)
                block_x = (sx // res) * res
                block_y = (sy // res) * res
                for by in range(block_y, min(block_y+res, ROWS)):
                    for bx in range(block_x, min(block_x+res, COLS)):
                        self.map_state[by][bx] = OBSTACLE
                        self.map_last_update[by][bx] = self.steps
        # But head position should not be marked as obstacle (start point is head)
        head_x, head_y = self.snake[0]
        # Head position is empty (but will be covered by head color during drawing), but for decision head is not obstacle
        # However we keep it as empty so that starting point is clear.
        # But we allow the coarse block containing head to be marked as obstacle? No, because head is the start.
        # So we need to set the head cell to EMPTY (while preserving update step)
        self.map_state[head_y][head_x] = EMPTY
        self.map_last_update[head_y][head_x] = self.steps

        # ---- Mark food (exact) ----
        fx, fy = self.food
        if 0 <= fx < COLS and 0 <= fy < ROWS:
            self.map_state[fy][fx] = FOOD
            self.map_last_update[fy][fx] = self.steps

    def expire_memory(self):
        """Clear cells not updated for more than MEMORY_TIMEOUT steps"""
        expired = 0
        for y in range(ROWS):
            for x in range(COLS):
                if self.map_state[y][x] != UNKNOWN:
                    if self.steps - self.map_last_update[y][x] > MEMORY_TIMEOUT:
                        self.map_state[y][x] = UNKNOWN
                        expired += 1
        if expired > 0:
            print(f"Memory expired: cleared {expired} cells")

    def dir_to_action(self, target_dir):
        if target_dir == self.direction:
            return "straight"
        elif target_dir == (-self.direction[1], self.direction[0]):
            return "left"
        elif target_dir == (self.direction[1], -self.direction[0]):
            return "right"
        else:
            return "straight"

    def decide_action_from_map(self):
        """Decision based on 20×20 map, priority: body > food > random"""
        head = self.snake[0]
        head_x, head_y = head

        # Check map for body (state OBSTACLE) and food
        has_body = any(self.map_state[y][x] == OBSTACLE for y in range(ROWS) for x in range(COLS))
        has_food = any(self.map_state[y][x] == FOOD for y in range(ROWS) for x in range(COLS))

        # Find nearest food
        food_rel = None
        if has_food:
            food_positions = [(x, y) for y in range(ROWS) for x in range(COLS) if self.map_state[y][x] == FOOD]
            if food_positions:
                food_rel = min(food_positions, key=lambda p: manhattan(head, p))

        # Safe directions (completely based on map)
        safe_dirs = []
        for d in ((1,0), (-1,0), (0,1), (0,-1)):
            if d == (-self.direction[0], -self.direction[1]):
                continue
            nx, ny = head_x + d[0], head_y + d[1]
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                continue
            if self.map_state[ny][nx] == OBSTACLE:
                continue
            safe_dirs.append(d)

        print(f"\n--- Step {self.steps} ---")
        print(f"Head: ({head_x},{head_y}) Dir: {self.direction}")
        map_body = sum(1 for y in range(ROWS) for x in range(COLS) if self.map_state[y][x] == OBSTACLE)
        map_food = sum(1 for y in range(ROWS) for x in range(COLS) if self.map_state[y][x] == FOOD)
        print(f"Map body count: {map_body}, food count: {map_food}, actual snake length: {len(self.snake)}")
        print(f"Map has body: {has_body}, has food: {has_food}")
        if has_food:
            print(f"Nearest food coord: {food_rel}")

        # ---------- 1. Has body -> A* ----------
        if has_body:
            print("Decision branch: A* (based on map)")
            if food_rel is not None:
                goal = food_rel
            else:
                goal = head
            path = astar_on_map(head, goal, self.map_state, COLS, ROWS) if goal != head else []
            if path:
                target_dir = (path[0][0] - head_x, path[0][1] - head_y)
                path_len = len(path)
                print(f"A* path length {path_len}, first step direction {target_dir}")
            else:
                if safe_dirs:
                    target_dir = min(safe_dirs, key=lambda d: manhattan((head_x+d[0], head_y+d[1]), (food_rel if food_rel else head)))
                else:
                    target_dir = self.direction
                path_len = 0
                print("A* failed, using safe greedy")
            action = self.dir_to_action(target_dir)
            return action, target_dir, path_len, has_food

        # ---------- 2. No body, has food -> chase directly ----------
        if not has_body and has_food and food_rel is not None:
            print("Decision branch: chase food directly (based on map)")
            dx = food_rel[0] - head_x
            dy = food_rel[1] - head_y
            if dx == 0 and dy == 0:
                target_dir = self.direction
            elif abs(dx) >= abs(dy):
                target_dir = (1 if dx > 0 else -1, 0)
            else:
                target_dir = (0, 1 if dy > 0 else -1)
            # Safety check
            nx, ny = head_x + target_dir[0], head_y + target_dir[1]
            if not (0 <= nx < COLS and 0 <= ny < ROWS) or self.map_state[ny][nx] == OBSTACLE:
                if safe_dirs:
                    target_dir = min(safe_dirs, key=lambda d: manhattan((head_x+d[0], head_y+d[1]), food_rel))
                else:
                    target_dir = self.direction
            action = self.dir_to_action(target_dir)
            print(f"Target direction: {target_dir}")
            return action, target_dir, 0, has_food

        # ---------- 3. Completely empty -> random every 3 steps ----------
        if not has_body and not has_food:
            print("Decision branch: completely empty random")
            if self.step_counter == 0:
                self.chosen_direction = random.choice(['straight', 'left', 'right'])
                self.steps_to_go = 3
            if self.chosen_direction == 'straight':
                target_dir = self.direction
            elif self.chosen_direction == 'left':
                target_dir = (-self.direction[1], self.direction[0])
            else:
                target_dir = (self.direction[1], -self.direction[0])
            action = self.dir_to_action(target_dir)
            self.step_counter += 1
            if self.step_counter >= self.steps_to_go:
                self.step_counter = 0
                self.chosen_direction = None
            print(f"Random direction: {self.chosen_direction}")
            return action, target_dir, 0, has_food

        # ---------- Default ----------
        target_dir = self.direction
        action = self.dir_to_action(target_dir)
        return action, target_dir, 0, has_food

    def move_snake(self):
        if self.game_over:
            return False
    
        vision = self.get_local_vision()
    
        if self.steps % UPDATE_INTERVAL == 0:
            self.update_internal_map(vision)
    
        self.expire_memory()
    
        action, target_dir, path_len, food_vis = self.decide_action_from_map()
        self.current_action = action.capitalize()
        self.path_len = path_len
        self.food_visible = food_vis
        self.obstacle_count = sum(1 for y in range(ROWS) for x in range(COLS) if self.map_state[y][x] == OBSTACLE)
    
        old_dir = self.direction
    
        if action == 'left':
            self.next_direction = (-self.direction[1], self.direction[0])
        elif action == 'right':
            self.next_direction = (self.direction[1], -self.direction[0])
        else:
            self.next_direction = self.direction
    
        if self.next_direction != (-self.direction[0], -self.direction[1]):
            self.direction = self.next_direction
    
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        nx, ny = new_head
        print(f"Attempt move: ({head_x},{head_y}) -> ({nx},{ny})")
    
        # ============================================================
        # 撞墙处理（修改部分：左右都不安全时，三个方向轮流随机选）
        # ============================================================
        if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS:
            print("!!! Wall collision !!!")
            left_dir = (-old_dir[1], old_dir[0])
            right_dir = (old_dir[1], -old_dir[0])
            lx, ly = head_x + left_dir[0], head_y + left_dir[1]
            rx, ry = head_x + right_dir[0], head_y + right_dir[1]
    
            # 检查左右方向是否有蛇身（真实蛇身）
            left_has_body = (lx, ly) in self.snake[1:]
            right_has_body = (rx, ry) in self.snake[1:]
    
            if not left_has_body:
                # 左边安全，左转
                self.direction = left_dir
            elif not right_has_body:
                # 右边安全，右转
                self.direction = right_dir
            else:
                # 左右都有蛇身，三个方向轮流随机选（左、右、直）
                straight_dir = old_dir
                options = [left_dir, right_dir, straight_dir]
                idx = self.step_counter % 3
                self.direction = options[idx]
                self.step_counter += 1   # 下次换下一个方向
    
            self.next_direction = self.direction
            self.chosen_direction = None
            return False
    
        # ============================================================
        # 正常移动
        # ============================================================
        will_eat = (new_head == self.food)
        tail = None
        if not will_eat:
            tail = self.snake.pop()
    
        if new_head in self.snake:
            if tail:
                self.snake.append(tail)
            self.record_death(f"Collided with self, target ({nx},{ny}) in body")
            return False
    
        self.snake.insert(0, new_head)
        self.steps += 1
    
        print(f"Move successful, new head ({nx},{ny}), steps {self.steps}")
    
        if will_eat:
            self.score += 1
            self.spawn_food()
            print("Ate food!")
            if len(self.snake) >= COLS * ROWS:
                self.win = True
                self.game_over = True
        return True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset_game()
                    self.death_count = 0
                    self.max_length = len(self.snake)
                    self.max_steps = 0
                    self.record_log.clear()
                    continue
                if event.key == pygame.K_m:
                    self.record_log.append((self.steps, len(self.snake)))
                    if len(self.record_log) > 10:
                        self.record_log.pop(0)
                    continue
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

    def draw(self):
        self.screen.fill(BLACK)
        info_rect = pygame.Rect(0, 0, WIDTH, INFO_HEIGHT)
        pygame.draw.rect(self.screen, INFO_BG, info_rect)
        pygame.draw.line(self.screen, (60, 70, 90), (0, INFO_HEIGHT-1), (WIDTH, INFO_HEIGHT-1), 2)
        y0 = 6
        stats1 = self.small_font.render(f"Deaths:{self.death_count}  MaxLen:{self.max_length}  MaxSteps:{self.max_steps}", True, STATS_COLOR)
        self.screen.blit(stats1, (10, y0))
        stats2 = self.small_font.render(f"Current Len:{len(self.snake)}  Steps:{self.steps}", True, STATS_COLOR)
        self.screen.blit(stats2, (10, y0+20))
        if self.record_log:
            last = self.record_log[-1]
            rec_text = self.small_font.render(f"Last record: steps={last[0]}, len={last[1]}", True, (200,200,255))
            self.screen.blit(rec_text, (10, y0+40))

        offset_y = INFO_HEIGHT

        # Main grid
        pygame.draw.rect(self.screen, BLACK, (0, offset_y, GRID_WIDTH, GRID_HEIGHT))
        for x in range(0, GRID_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, offset_y), (x, offset_y+GRID_HEIGHT), 1)
        for y in range(0, GRID_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, offset_y+y), (GRID_WIDTH, offset_y+y), 1)

        fx, fy = self.food
        cx = fx * CELL_SIZE + CELL_SIZE//2
        cy = fy * CELL_SIZE + CELL_SIZE//2 + offset_y
        pygame.draw.circle(self.screen, RED, (cx, cy), CELL_SIZE//2 - 2)

        for idx, (sx, sy) in enumerate(self.snake):
            x = sx * CELL_SIZE
            y = sy * CELL_SIZE + offset_y
            is_head = (idx == 0)
            pad = 1 if is_head else 2
            rect = (x + pad, y + pad, CELL_SIZE - 2*pad, CELL_SIZE - 2*pad)
            if is_head:
                color = SNAKE_HEAD
            else:
                factor = 0.7 + 0.3 * (idx / len(self.snake))
                color = (int(39*factor), int(174*factor), int(96*factor))
            pygame.draw.rect(self.screen, color, rect, border_radius=4 if is_head else 3)
            pygame.draw.rect(self.screen, SNAKE_BORDER, rect, 1, border_radius=4 if is_head else 3)
            if is_head:
                dx, dy = self.direction
                if dx == 1:
                    eye1 = (x+13, y+4); eye2 = (x+13, y+12)
                elif dx == -1:
                    eye1 = (x+4, y+4); eye2 = (x+4, y+12)
                elif dy == -1:
                    eye1 = (x+4, y+4); eye2 = (x+12, y+4)
                else:
                    eye1 = (x+4, y+13); eye2 = (x+12, y+13)
                for ex, ey in (eye1, eye2):
                    pygame.draw.circle(self.screen, WHITE, (ex, ey), 3)
                    pygame.draw.circle(self.screen, (10,26,16), (ex+dx, ey+dy), 1)

        # Local view
        view_x = GRID_WIDTH + 10
        view_y = offset_y + 10
        view_w = VIEW_WINDOW_WIDTH - 20
        view_h = GRID_HEIGHT - 20
        pygame.draw.rect(self.screen, VIEW_BG, (view_x, view_y, view_w, view_h))
        pygame.draw.rect(self.screen, VIEW_BORDER, (view_x, view_y, view_w, view_h), 2)
        title = self.small_font.render(f"Local View ({VIEW_WIDTH}x{VIEW_DEPTH})", True, (150,160,180))
        self.screen.blit(title, (view_x+6, view_y+2))
        vision = self.get_local_vision()
        block_size = 16
        gap = 1
        col_width = block_size + gap
        row_height = block_size + gap
        total_width = VIEW_WIDTH * col_width
        total_height = VIEW_DEPTH * row_height
        start_x = view_x + (view_w - total_width)//2
        start_y = view_y + 22
        for col in range(VIEW_WIDTH):
            for row in range(VIEW_DEPTH):
                x = start_x + col * col_width
                y = start_y + row * row_height
                color, dist = vision[col][row]
                rect = pygame.Rect(x, y, block_size, block_size)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, VIEW_BORDER, rect, 1)
                if col == VIEW_WIDTH // 2:
                    pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, rect, 2)
                if dist > 0:
                    num_text = self.small_font.render(str(dist), True, (255,255,255) if color==BLACK else (0,0,0))
                    text_rect = num_text.get_rect(center=rect.center)
                    self.screen.blit(num_text, text_rect)

        # Decision panel
        panel_x = GRID_WIDTH + VIEW_WINDOW_WIDTH
        panel_y = offset_y
        panel_w = PANEL_WIDTH
        panel_h = GRID_HEIGHT
        pygame.draw.rect(self.screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.line(self.screen, (60,70,90), (panel_x, panel_y), (panel_x, panel_y+panel_h), 2)
        title2 = self.small_font.render("Decision Info", True, (255,200,100))
        self.screen.blit(title2, (panel_x+10, panel_y+10))
        action_text = self.font.render(f"Action: {self.current_action}", True, WHITE)
        self.screen.blit(action_text, (panel_x+10, panel_y+35))
        path_text = self.font.render(f"Path len: {self.path_len}", True, WHITE)
        self.screen.blit(path_text, (panel_x+10, panel_y+55))
        food_vis_text = self.font.render(f"Food visible: {'Yes' if self.food_visible else 'No'}", True, WHITE)
        self.screen.blit(food_vis_text, (panel_x+10, panel_y+75))
        obs_text = self.font.render(f"Obstacles in view: {self.obstacle_count}", True, WHITE)
        self.screen.blit(obs_text, (panel_x+10, panel_y+95))
        help_text = self.small_font.render("M: record stats   R: reset", True, (150,150,200))
        self.screen.blit(help_text, (panel_x+10, panel_y+panel_h-30))

        # Internal map panel (20×20)
        map_panel_x = GRID_WIDTH + VIEW_WINDOW_WIDTH + PANEL_WIDTH
        map_panel_y = offset_y
        map_panel_w = MAP_PANEL_WIDTH
        map_panel_h = GRID_HEIGHT
        pygame.draw.rect(self.screen, MAP_BG, (map_panel_x, map_panel_y, map_panel_w, map_panel_h))
        pygame.draw.line(self.screen, (60,70,90), (map_panel_x, map_panel_y), (map_panel_x, map_panel_y+map_panel_h), 2)
        title3 = self.small_font.render("Internal Map (20×20)", True, (150,200,255))
        self.screen.blit(title3, (map_panel_x+10, map_panel_y+10))

        # Calculate cell size
        margin = 20
        draw_area_w = map_panel_w - 2*margin
        draw_area_h = map_panel_h - 2*margin - 30
        cell_size = min(draw_area_w // COLS, draw_area_h // ROWS)
        if cell_size < 2:
            cell_size = 2
        total_w = cell_size * COLS
        total_h = cell_size * ROWS
        offset_x = map_panel_x + margin + (draw_area_w - total_w)//2
        offset_y_map = map_panel_y + margin + 30 + (draw_area_h - total_h)//2

        # Draw map
        for y in range(ROWS):
            for x in range(COLS):
                status = self.map_state[y][x]
                if status == UNKNOWN:
                    color = UNKNOWN_COLOR
                elif status == EMPTY:
                    color = EMPTY_COLOR
                elif status == OBSTACLE:
                    color = OBSTACLE_COLOR
                elif status == FOOD:
                    color = FOOD_MEMORY_COLOR
                else:
                    color = UNKNOWN_COLOR
                # Overwrite head position with yellow
                if (x, y) == self.snake[0]:
                    color = HEAD_MARK_COLOR
                px = offset_x + x * cell_size
                py = offset_y_map + y * cell_size
                rect = pygame.Rect(px, py, cell_size, cell_size)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (50,50,60), rect, 1)

        # Legend
        legend_y = map_panel_y + map_panel_h - 50
        colors = [
            (UNKNOWN_COLOR, "Unknown"),
            (EMPTY_COLOR, "Empty"),
            (OBSTACLE_COLOR, "Obstacle"),
            (FOOD_MEMORY_COLOR, "Food"),
            (HEAD_MARK_COLOR, "Head")
        ]
        x_legend = map_panel_x + 10
        for col, label in colors:
            pygame.draw.rect(self.screen, col, (x_legend, legend_y, 10, 10))
            text = self.small_font.render(label, True, (200,200,200))
            self.screen.blit(text, (x_legend+14, legend_y-2))
            x_legend += 70
            if x_legend > map_panel_x + map_panel_w - 20:
                legend_y += 18
                x_legend = map_panel_x + 10

        if self.game_over:
            overlay = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,180))
            self.screen.blit(overlay, (0, offset_y))
            msg = "You Win!" if self.win else "Game Over"
            color = (241,196,15) if self.win else (255,107,122)
            text = self.big_font.render(msg, True, color)
            text_rect = text.get_rect(center=(GRID_WIDTH//2, offset_y+GRID_HEIGHT//2-20))
            self.screen.blit(text, text_rect)
            sub = self.font.render("Press R to restart", True, (200,200,220))
            sub_rect = sub.get_rect(center=(GRID_WIDTH//2, offset_y+GRID_HEIGHT//2+40))
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