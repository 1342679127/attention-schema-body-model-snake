# -*- coding: utf-8 -*-
"""
param_search_stats.py
Parameter search with statistics - full English version.
Parameter ranges: RESOLUTION {1, 2, 4} × MEMORY_TIMEOUT {5, 10, 20, 40, 80} × UPDATE_INTERVAL {1, 2, 5, 10, 20}
Each combo: 30 repeats, 1000 steps per run.
Outputs: mean ± std, p-value, Cohen's d vs baselines.
Bridge logic: external death monitoring (snake length drops from >40 to 40), no modification to snake.py.
"""

import os
import sys
import time
import random
import numpy as np
from scipy import stats
from contextlib import redirect_stdout

# Disable display
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.display.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME | pygame.HIDDEN)


# ============================================================
# Parameter configuration
# ============================================================
RESOLUTIONS = [1, 2, 4]
MEMORY_TIMEOUTS = [5, 10, 20, 40, 80]
UPDATE_INTERVALS = [1, 2, 5, 10, 20]

STEPS_LIMIT = 1000
N_REPEATS = 30

BASELINE_FILE = "baseline_report.txt"
REPORT_FILE = "param_search_report.txt"


# ============================================================
# External death monitoring (bridge logic, does NOT modify snake.py)
# ============================================================
def run_single_repeat(res, interval, timeout, seed):
    """
    Run one simulation with given parameters and seed.
    Death detection: snake length drops from >40 to 40.
    """
    import snake
    import importlib
    importlib.reload(snake)
    
    snake.RESOLUTION = res
    snake.UPDATE_INTERVAL = interval
    snake.MEMORY_TIMEOUT = timeout
    
    from snake import SnakeGame
    
    random.seed(seed)
    
    game = SnakeGame()
    game.reset_game()
    game.draw = lambda: None
    game.handle_events = lambda: None
    
    death_counter = 0
    max_len = len(game.snake)
    total_steps = 0
    
    while total_steps < STEPS_LIMIT:
        if game.game_over:
            if game.win:
                break
            game.reset_game()
            continue
        
        prev_len = len(game.snake)
        game.move_snake()
        total_steps += 1
        
        curr_len = len(game.snake)
        
        # Death detected: length reset from >40 to 40
        if curr_len == 40 and prev_len > 40:
            death_counter += 1
        
        if curr_len > max_len:
            max_len = curr_len
        
        if game.win:
            break
    
    return death_counter, max_len


def run_combo(res, interval, timeout):
    """
    Run one parameter combination for N_REPEATS times.
    Returns summary statistics.
    """
    max_lens = []
    deaths = []
    base_seed = hash((res, interval, timeout)) % 1000000
    
    for i in range(N_REPEATS):
        seed = base_seed + i * 10007
        with open(os.devnull, 'w') as devnull:
            with redirect_stdout(devnull):
                d, m = run_single_repeat(res, interval, timeout, seed)
        max_lens.append(m)
        deaths.append(d)
    
    return {
        'max_lens': max_lens,
        'deaths': deaths,
        'max_len_mean': np.mean(max_lens),
        'max_len_std': np.std(max_lens, ddof=1),
        'death_mean': np.mean(deaths),
    }


# ============================================================
# Read baseline report (extract means and raw data)
# ============================================================
def read_baseline_report():
    try:
        with open(BASELINE_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        import re
        # Extract means
        fp_match = re.search(r'First-person reactive baseline:\n\s+Mean max length: ([\d.]+) ± ([\d.]+)', content)
        tp_match = re.search(r'Third-person omniscient baseline:\n\s+Mean max length: ([\d.]+) ± ([\d.]+)', content)
        # Extract raw data arrays
        fp_raw = re.search(r'First-person reactive baseline:\n\s+Mean max length: [\d.]+\n\s+Raw data: \[(.*?)\]', content, re.DOTALL)
        tp_raw = re.search(r'Third-person omniscient baseline:\n\s+Mean max length: [\d.]+\n\s+Raw data: \[(.*?)\]', content, re.DOTALL)
        
        baseline = {}
        if fp_match:
            baseline['first_mean'] = float(fp_match.group(1))
            baseline['first_std'] = float(fp_match.group(2))
        if tp_match:
            baseline['third_mean'] = float(tp_match.group(1))
            baseline['third_std'] = float(tp_match.group(2))
        if fp_raw:
            baseline['first_raw'] = [float(x.strip()) for x in fp_raw.group(1).split(',')]
        if tp_raw:
            baseline['third_raw'] = [float(x.strip()) for x in tp_raw.group(1).split(',')]
        return baseline
    except FileNotFoundError:
        print("ERROR: baseline_report.txt not found. Please run baseline_stats.py first.")
        return None


# ============================================================
# Main
# ============================================================
def main():
    # Calculate number of valid combinations (only those with interval < timeout)
    total_combos = sum(1 for res in RESOLUTIONS
                       for timeout in MEMORY_TIMEOUTS
                       for interval in UPDATE_INTERVALS
                       if interval < timeout)

    print("=" * 60)
    print("Attention Schema Parameter Search - Statistics")
    print(f"Total parameter combinations (valid): {total_combos}")
    print(f"Repeats per combo: {N_REPEATS}, steps per run: {STEPS_LIMIT}")
    print(f"Total simulations: {total_combos * N_REPEATS}")
    print("=" * 60)

    baseline = read_baseline_report()
    if baseline is None:
        return

    print(f"\nBaselines loaded:")
    print(f"  First-person reactive: {baseline['first_mean']:.2f} ± {baseline['first_std']:.2f}")
    print(f"  Third-person omniscient: {baseline['third_mean']:.2f} ± {baseline['third_std']:.2f}")

    start_time = time.time()
    results = []
    idx = 0

    # Iterate over all parameter combinations, skipping invalid ones
    for res in RESOLUTIONS:
        for timeout in MEMORY_TIMEOUTS:
            for interval in UPDATE_INTERVALS:
                # Skip combinations where update interval >= memory timeout
                # because the map would never accumulate any information
                if interval >= timeout:
                    continue

                idx += 1
                print(f"\n[{idx}/{total_combos}] RES={res}, TIMEOUT={timeout}, INTERVAL={interval}")

                stats_dict = run_combo(res, interval, timeout)
                max_lens = stats_dict['max_lens']
                first_raw = baseline.get('first_raw', [baseline['first_mean']] * 30)
                third_raw = baseline.get('third_raw', [baseline['third_mean']] * 30)

                # Independent t-test vs first-person baseline (unequal variance)
                t1, p1 = stats.ttest_ind(max_lens, first_raw, equal_var=False)
                d1 = (stats_dict['max_len_mean'] - baseline['first_mean']) / stats_dict['max_len_std']

                # Independent t-test vs third-person baseline
                t3, p3 = stats.ttest_ind(max_lens, third_raw, equal_var=False)
                d3 = (stats_dict['max_len_mean'] - baseline['third_mean']) / stats_dict['max_len_std']

                print(f"  Mean max length: {stats_dict['max_len_mean']:.2f} ± {stats_dict['max_len_std']:.2f}")
                print(f"  Mean deaths: {stats_dict['death_mean']:.2f}")
                print(f"  vs First-person: p={p1:.4f}, d={d1:.2f}")
                print(f"  vs Third-person: p={p3:.4f}, d={d3:.2f}")

                results.append({
                    'res': res,
                    'timeout': timeout,
                    'interval': interval,
                    'mean': stats_dict['max_len_mean'],
                    'std': stats_dict['max_len_std'],
                    'death_mean': stats_dict['death_mean'],
                    'p_vs_first': p1,
                    'd_vs_first': d1,
                    'p_vs_third': p3,
                    'd_vs_third': d3,
                })

    elapsed = time.time() - start_time
    print(f"\nExperiment finished! Total time: {elapsed:.1f} sec ({elapsed/60:.1f} min)")

    # Find the best combination (highest mean max length)
    best = max(results, key=lambda x: x['mean'])

    print("\n" + "=" * 60)
    print("Statistical Report")
    print("=" * 60)
    print(f"\n[Optimal parameter combination]")
    print(f"  RESOLUTION = {best['res']}")
    print(f"  MEMORY_TIMEOUT = {best['timeout']}")
    print(f"  UPDATE_INTERVAL = {best['interval']}")
    print(f"  Mean max length = {best['mean']:.2f} ± {best['std']:.2f}")
    print(f"  Mean deaths = {best['death_mean']:.2f}")
    print(f"  vs First-person baseline: p={best['p_vs_first']:.4f}, d={best['d_vs_first']:.2f}")
    print(f"  vs Third-person baseline: p={best['p_vs_third']:.4f}, d={best['d_vs_third']:.2f}")

    # Write the final report to file
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("Attention Schema Parameter Search - Statistical Report\n")
        f.write("=" * 60 + "\n\n")

        f.write("[Parameter Configuration]\n")
        f.write(f"  RESOLUTION: {RESOLUTIONS}\n")
        f.write(f"  MEMORY_TIMEOUT: {MEMORY_TIMEOUTS}\n")
        f.write(f"  UPDATE_INTERVAL: {UPDATE_INTERVALS}\n")
        f.write(f"  Total valid combinations (interval < timeout): {total_combos}\n")
        f.write(f"  Repeats per combo: {N_REPEATS}\n")
        f.write(f"  Steps per run: {STEPS_LIMIT}\n\n")

        f.write("[Baseline Performance]\n")
        f.write(f"  First-person reactive: {baseline['first_mean']:.2f} ± {baseline['first_std']:.2f}\n")
        f.write(f"  Third-person omniscient: {baseline['third_mean']:.2f} ± {baseline['third_std']:.2f}\n\n")

        f.write("-" * 60 + "\n")
        f.write("[Optimal Parameter Combination]\n")
        f.write("-" * 60 + "\n")
        f.write(f"  RESOLUTION = {best['res']}\n")
        f.write(f"  MEMORY_TIMEOUT = {best['timeout']}\n")
        f.write(f"  UPDATE_INTERVAL = {best['interval']}\n")
        f.write(f"  Mean max length = {best['mean']:.2f} ± {best['std']:.2f}\n")
        f.write(f"  Mean deaths = {best['death_mean']:.2f}\n")
        f.write(f"  vs First-person baseline: p={best['p_vs_first']:.4f}, d={best['d_vs_first']:.2f}\n")
        f.write(f"  vs Third-person baseline: p={best['p_vs_third']:.4f}, d={best['d_vs_third']:.2f}\n\n")

        f.write("-" * 60 + "\n")
        f.write("[Top 5 Ranking (by mean max length)]\n")
        f.write("-" * 60 + "\n")
        sorted_r = sorted(results, key=lambda x: x['mean'], reverse=True)
        f.write("Rank\tRES\tTIMEOUT\tINTERVAL\tMean±SD\tDeaths\tp_vs_first\td\n")
        for rank, r in enumerate(sorted_r[:5], 1):
            sig = "**" if r['p_vs_first'] < 0.05 else ("*" if r['p_vs_first'] < 0.1 else "ns")
            f.write(f"{rank}\t{r['res']}\t{r['timeout']}\t{r['interval']}\t")
            f.write(f"{r['mean']:.2f}±{r['std']:.2f}\t{r['death_mean']:.2f}\t")
            f.write(f"{r['p_vs_first']:.4f}{sig}\t{r['d_vs_first']:.2f}\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("End of Report\n")
        f.write("=" * 60 + "\n")

    print(f"\nReport saved to: {REPORT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()