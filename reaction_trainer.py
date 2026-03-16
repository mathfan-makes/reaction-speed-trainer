#!/usr/bin/env python3
"""
Reaction time trainer for use with a Makey Makey and a 2x2 foil target board.
Runs fullscreen. Arrow keys map to target positions:

    ┌───────┐  ┌───────┐
    │ TL(↑) │  │ TR(→) │
    └───────┘  └───────┘
    ┌───────┐  ┌───────┐
    │ BL(←) │  │ BR(↓) │
    └───────┘  └───────┘

  python reaction_trainer.py
"""

import pygame
import random
import time
import csv
import os
import datetime
import statistics
import sys

# -------------
# Configuration
# -------------

FPS = 60

# Colors
BG_COLOR = (30, 30, 40)
CIRCLE_IDLE = (60, 60, 75)
CIRCLE_BORDER = (80, 80, 100)
CIRCLE_LIT = (0, 220, 120)
TEXT_COLOR = (220, 220, 230)
TEXT_DIM = (120, 120, 140)
ACCENT = (255, 160, 40)
REST_COLOR = (80, 80, 100)
FLASH_HIT = (20, 60, 30)
FLASH_MISS = (60, 20, 20)

# Arrow key -> target index
KEY_MAP = {
    pygame.K_UP: 0,     # TL
    pygame.K_RIGHT: 1,  # TR
    pygame.K_LEFT: 2,   # BL
    pygame.K_DOWN: 3,   # BR
}

# Target index -> position name (matches the 2x2 grid the player sees)
TARGET_NAMES = {0: "TL", 1: "TR", 2: "BL", 3: "BR"}

# Timing
BLANK_FLASH_MS = 125            # blank between reps (visual reset)
RANDOM_DELAY_MIN_MS = 300       # random delay mode: min wait after blank
RANDOM_DELAY_MAX_MS = 1200      # random delay mode: max wait after blank
TIMED_DURATION_S = 30           # timed mode session length

# Session
REPS_PER_SESSION = 10           # for blitz and random_delay modes

# Data file
CSV_FILE = "reaction_data.csv"

# Layout globals (computed in main based on screen size)
# All sizes are designed for 600px height, then scaled proportionally.
WINDOW_WIDTH = 0
WINDOW_HEIGHT = 0
scale = 1.0                     # screen height / 600
PAD_SIZE = 0
PAD_CORNER = 0
GRID_CX = 0
GRID_CY = 0
GRID_GAP = 0
TARGET_POSITIONS = {}

# Pygame globals (initialized in main)
screen = None
font_large = None
font_med = None
font_small = None
clock = None

# ---------------
# Drawing helpers
# ---------------

def draw_text(text, font, color, center):
    rendered = font.render(text, True, color)
    screen.blit(rendered, rendered.get_rect(center=center))


def draw_targets(lit_target=None):
    half = PAD_SIZE // 2
    for idx, (cx, cy) in TARGET_POSITIONS.items():
        color = CIRCLE_LIT if idx == lit_target else CIRCLE_IDLE
        rect = pygame.Rect(cx - half, cy - half, PAD_SIZE, PAD_SIZE)
        # Border
        border_rect = rect.inflate(6, 6)
        pygame.draw.rect(screen, CIRCLE_BORDER, border_rect, border_radius=PAD_CORNER + 2)
        # Fill
        pygame.draw.rect(screen, color, rect, border_radius=PAD_CORNER)
        # Center dot
        dot_color = (255, 255, 255) if idx == lit_target else (90, 90, 110)
        pygame.draw.circle(screen, dot_color, (cx, cy), max(4, int(6 * scale)))

    # Center rest position indicator
    s10 = int(10 * scale)
    pygame.draw.circle(screen, REST_COLOR, (GRID_CX, GRID_CY), max(4, int(6 * scale)), 1)
    pygame.draw.line(screen, REST_COLOR, (GRID_CX - s10, GRID_CY), (GRID_CX + s10, GRID_CY), 1)
    pygame.draw.line(screen, REST_COLOR, (GRID_CX, GRID_CY - s10), (GRID_CX, GRID_CY + s10), 1)


def check_quit(event):
    if event.type == pygame.QUIT:
        return True
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return True
    return False


# -------
# Screens
# -------

def title_screen():
    selected = 0
    modes = ["blitz", "random_delay", "timed"]
    labels = ["Blitz", "Random Delay", "Timed"]
    descs = [
        "10 reps -- targets fire as fast as possible",
        "10 reps -- random 300-1200 ms pause between targets",
        "30 seconds -- blitz pacing, as many reps as you can",
    ]

    cx = WINDOW_WIDTH // 2

    while True:
        for event in pygame.event.get():
            if check_quit(event):
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(modes)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(modes)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return modes[selected]

        screen.fill(BG_COLOR)
        draw_text("REACTION TRAINER", font_large, ACCENT, (cx, int(80 * scale)))

        # Mini target grid as decoration
        mini_size = int(40 * scale)
        mini_half = mini_size // 2
        for idx, (tx, ty) in TARGET_POSITIONS.items():
            mini_cx = int(cx + (tx - GRID_CX) * 0.3)
            mini_cy = int(175 * scale + (ty - GRID_CY) * 0.3)
            color = CIRCLE_LIT if idx == 0 else CIRCLE_IDLE
            mini_rect = pygame.Rect(mini_cx - mini_half, mini_cy - mini_half, mini_size, mini_size)
            pygame.draw.rect(screen, color, mini_rect, border_radius=int(6 * scale))

        # Mode selection
        box_w = int(500 * scale)
        for i, (label, desc) in enumerate(zip(labels, descs)):
            y = int((300 + i * 70) * scale)
            if i == selected:
                rect = pygame.Rect(cx - box_w // 2, y - int(25 * scale), box_w, int(55 * scale))
                pygame.draw.rect(screen, (50, 50, 65), rect, border_radius=8)
                pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=8)
                draw_text(f"> {label}", font_med, ACCENT, (cx, y))
            else:
                draw_text(label, font_med, TEXT_DIM, (cx, y))
            draw_text(desc, font_small, TEXT_DIM, (cx, y + int(22 * scale)))

        draw_text("UP/DOWN to select  -  SPACE to start  -  ESC to quit", font_small, TEXT_DIM,
                  (cx, WINDOW_HEIGHT - int(40 * scale)))

        pygame.display.flip()
        clock.tick(FPS)


def run_trial(target, deadline=None):
    # Light a target, wait for a key. Returns (struck, ms, result) or None on quit/timeout.
    prompt_time = time.perf_counter()

    while True:
        if deadline and time.perf_counter() >= deadline:
            return None

        for event in pygame.event.get():
            if check_quit(event):
                return None
            if event.type == pygame.KEYDOWN and event.key in KEY_MAP:
                reaction_ms = (time.perf_counter() - prompt_time) * 1000
                struck = KEY_MAP[event.key]
                result = "HIT" if struck == target else "MISS"
                return (struck, reaction_ms, result)

        screen.fill(BG_COLOR)
        draw_targets(lit_target=target)
        pygame.display.flip()
        clock.tick(FPS)


def summary_screen(results, mode, duration_s=None):
    # Returns True to play again, False to quit
    hit_times = [ms for _, _, ms, r in results if r == "HIT"]
    num_hits = len(hit_times)
    cx = WINDOW_WIDTH // 2
    col_offset = int(100 * scale)
    row_height = int(45 * scale)

    while True:
        for event in pygame.event.get():
            if check_quit(event):
                return False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return True

        screen.fill(BG_COLOR)

        draw_text("SESSION COMPLETE", font_large, ACCENT, (cx, int(80 * scale)))
        mode_labels = {"blitz": "Blitz", "random_delay": "Random Delay", "timed": "Timed"}
        draw_text(mode_labels[mode], font_med, TEXT_DIM, (cx, int(120 * scale)))

        y = int(180 * scale)

        # Accuracy
        draw_text("Accuracy", font_med, TEXT_DIM, (cx - col_offset, y))
        draw_text(f"{num_hits} / {len(results)}", font_med, TEXT_COLOR, (cx + col_offset, y))
        y += row_height

        # Median reaction time (hits only)
        draw_text("Median", font_med, TEXT_DIM, (cx - col_offset, y))
        if hit_times:
            draw_text(f"{statistics.median(hit_times):.0f} ms", font_med, TEXT_COLOR, (cx + col_offset, y))
        else:
            draw_text("--", font_med, TEXT_COLOR, (cx + col_offset, y))
        y += row_height

        # Fastest
        draw_text("Fastest", font_med, TEXT_DIM, (cx - col_offset, y))
        if hit_times:
            draw_text(f"{min(hit_times):.0f} ms", font_med, CIRCLE_LIT, (cx + col_offset, y))
        else:
            draw_text("--", font_med, TEXT_COLOR, (cx + col_offset, y))
        y += row_height

        # Timed mode: correct hits per second
        if mode == "timed" and duration_s and duration_s > 0:
            draw_text("Hits/sec", font_med, TEXT_DIM, (cx - col_offset, y))
            draw_text(f"{num_hits / duration_s:.1f}", font_med, TEXT_COLOR, (cx + col_offset, y))
            y += row_height

        draw_text("SPACE for another session  -  ESC to quit", font_small, TEXT_DIM,
                  (cx, WINDOW_HEIGHT - int(40 * scale)))

        pygame.display.flip()
        clock.tick(FPS)


# ----
# Main
# ----

def main():
    global screen, font_large, font_med, font_small, clock
    global WINDOW_WIDTH, WINDOW_HEIGHT, scale
    global PAD_SIZE, PAD_CORNER, GRID_CX, GRID_CY, GRID_GAP, TARGET_POSITIONS

    pygame.init()

    # Go fullscreen, then read the actual surface size
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    WINDOW_WIDTH, WINDOW_HEIGHT = screen.get_size()
    pygame.display.set_caption("Reaction Trainer")
    clock = pygame.time.Clock()

    # Scale everything relative to 600px design height
    scale = WINDOW_HEIGHT / 600
    font_large = pygame.font.Font(None, int(56 * scale))
    font_med = pygame.font.Font(None, int(28 * scale))
    font_small = pygame.font.Font(None, int(20 * scale))

    # Compute grid layout for this screen size
    PAD_SIZE = int(130 * scale)
    PAD_CORNER = int(12 * scale)
    GRID_GAP = int(180 * scale)
    GRID_CX = WINDOW_WIDTH // 2
    GRID_CY = WINDOW_HEIGHT // 2 - int(20 * scale)
    TARGET_POSITIONS = {
        0: (GRID_CX - GRID_GAP // 2, GRID_CY - GRID_GAP // 2),  # top-left
        1: (GRID_CX + GRID_GAP // 2, GRID_CY - GRID_GAP // 2),  # top-right
        2: (GRID_CX - GRID_GAP // 2, GRID_CY + GRID_GAP // 2),  # bottom-left
        3: (GRID_CX + GRID_GAP // 2, GRID_CY + GRID_GAP // 2),  # bottom-right
    }

    # CSV setup -- save next to the script
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CSV_FILE)
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="") as f:
            csv.writer(f).writerow([
                "timestamp", "session_id", "rep", "mode",
                "target_shown", "target_struck", "reaction_ms", "result",
            ])

    while True:
        mode = title_screen()
        if mode is None:
            break

        session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_csv = {"blitz": "BLITZ", "random_delay": "RANDOM_DELAY", "timed": "TIMED"}[mode]
        results = []  # list of (target_shown, target_struck, reaction_ms, result)

        # 3-2-1 countdown
        quit_requested = False
        for count in [3, 2, 1]:
            start = pygame.time.get_ticks()
            while pygame.time.get_ticks() - start < 600:
                for event in pygame.event.get():
                    if check_quit(event):
                        quit_requested = True
                if quit_requested:
                    break
                screen.fill(BG_COLOR)
                draw_targets()
                draw_text(str(count), font_large, ACCENT, (WINDOW_WIDTH // 2, GRID_CY))
                pygame.display.flip()
                clock.tick(FPS)
            if quit_requested:
                break
        if quit_requested:
            break

        # --- Session loop ---
        session_start = time.perf_counter()
        deadline = session_start + TIMED_DURATION_S if mode == "timed" else None
        rep = 0

        while True:
            rep += 1

            # Check rep limit for non-timed modes
            if mode != "timed" and rep > REPS_PER_SESSION:
                break

            target = random.randint(0, 3)
            trial = run_trial(target, deadline=deadline)

            if trial is None:
                # Distinguish time-expired from user-quit
                if deadline and time.perf_counter() >= deadline:
                    break  # time's up, show summary
                else:
                    quit_requested = True
                    break

            struck, reaction_ms, result = trial
            results.append((target, struck, reaction_ms, result))

            # Log to CSV
            with open(csv_path, "a", newline="") as f:
                csv.writer(f).writerow([
                    datetime.datetime.now().isoformat(), session_id, rep, mode_csv,
                    TARGET_NAMES[target], TARGET_NAMES[struck],
                    round(reaction_ms, 1), result,
                ])

            # Tinted blank flash (hit/miss feedback)
            flash_bg = FLASH_HIT if result == "HIT" else FLASH_MISS
            blank_start = pygame.time.get_ticks()
            while pygame.time.get_ticks() - blank_start < BLANK_FLASH_MS:
                for event in pygame.event.get():
                    if check_quit(event):
                        pygame.quit()
                        sys.exit()
                screen.fill(flash_bg)
                draw_targets()
                pygame.display.flip()
                clock.tick(FPS)

            # Random delay before next target (random_delay mode only, not after last rep)
            if mode == "random_delay" and rep < REPS_PER_SESSION:
                delay_ms = random.randint(RANDOM_DELAY_MIN_MS, RANDOM_DELAY_MAX_MS)
                delay_start = pygame.time.get_ticks()
                while pygame.time.get_ticks() - delay_start < delay_ms:
                    for event in pygame.event.get():
                        if check_quit(event):
                            pygame.quit()
                            sys.exit()
                    screen.fill(BG_COLOR)
                    draw_targets()
                    pygame.display.flip()
                    clock.tick(FPS)

        if quit_requested:
            break

        # Show summary
        if results:
            duration_s = time.perf_counter() - session_start if mode == "timed" else None
            if not summary_screen(results, mode, duration_s):
                break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
