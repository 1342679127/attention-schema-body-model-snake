# -*- coding: utf-8 -*-
"""
baseline_stats.py
Two baselines (first-person reactive + third-person omniscient) each run 30 times, 1000 steps per run.
Output: mean snake length ± standard deviation
"""

import os
import sys
import time
import random
import numpy as np
from contextlib import redirect_stdout

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.display.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME | pygame.HIDDEN)


STEPS_LIMIT = 1000
N_REPEATS = 30


# ====== First-person reactive baseline ======
def run_first_perspective(seed):
    from firstperspective import SnakeGame
    random.seed(seed)
    game = SnakeGame()
    game.reset_game()
    game.death_count = 0
    max_len = len(game.snake)
    steps = 0
    while steps < STEPS_LIMIT:
        if game.game_over:
            break
        game.move_snake()
        steps += 1
        if len(game.snake) > max_len:
            max_len = len(game.snake)
        if game.win:
            break
    return game.death_count, max_len


# ====== Third-person omniscient baseline ======
def run_third_perspective(seed):
    from thirdperspective import SnakeGame
    random.seed(seed)
    game = SnakeGame()
    game.reset_game()
    game.death_count = 0
    max_len = len(game.snake)
    steps = 0
    while steps < STEPS_LIMIT:
        if game.game_over:
            break
        game.move_snake()
        steps += 1
        if len(game.snake) > max_len:
            max_len = len(game.snake)
        if game.win:
            break
    return game.death_count, max_len


# ====== Run a single baseline ======
def run_baseline(baseline_func, name):
    max_lens = []
    deaths = []
    print(f"\n{name}")
    for i in range(N_REPEATS):
        seed = hash((name, i)) % 1000000
        with open(os.devnull, 'w') as devnull:
            with redirect_stdout(devnull):
                d, m = baseline_func(seed)
        max_lens.append(m)
        deaths.append(d)
        print(f"  [{i+1}/{N_REPEATS}] deaths={d}, max_len={m}")
    
    return {
        'max_len_mean': np.mean(max_lens),
        'max_len_std': np.std(max_lens, ddof=1),
        'max_lens_raw': max_lens,
        'death_mean': np.mean(deaths),
    }


# ====== Main ======
def main():
    print("=" * 60)
    print(f"Two baselines, each run {N_REPEATS} times, {STEPS_LIMIT} steps per run")
    print("=" * 60)
    
    start = time.time()
    
    first = run_baseline(run_first_perspective, "First-person reactive baseline")
    third = run_baseline(run_third_perspective, "Third-person omniscient baseline")
    
    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed:.1f} sec ({elapsed/60:.1f} min)")
    
    print("\n" + "=" * 60)
    print("Baseline statistical results")
    print("=" * 60)
    print(f"First-person reactive: {first['max_len_mean']:.2f} ± {first['max_len_std']:.2f}")
    print(f"Third-person omniscient: {third['max_len_mean']:.2f} ± {third['max_len_std']:.2f}")
    
    # Save baseline report
    with open("baseline_report.txt", "w", encoding="utf-8") as f:
        f.write("Baseline Statistical Report\n")
        f.write("=" * 60 + "\n")
        f.write(f"Repeats: {N_REPEATS}\n")
        f.write(f"Max steps: {STEPS_LIMIT}\n\n")
        f.write("First-person reactive baseline:\n")
        f.write(f"  Mean max length: {first['max_len_mean']:.2f} ± {first['max_len_std']:.2f}\n")
        f.write(f"  Raw data: {first['max_lens_raw']}\n\n")
        f.write("Third-person omniscient baseline:\n")
        f.write(f"  Mean max length: {third['max_len_mean']:.2f} ± {third['max_len_std']:.2f}\n")
        f.write(f"  Raw data: {third['max_lens_raw']}\n")
    
    print("\nReport saved: baseline_report.txt")


if __name__ == "__main__":
    main()