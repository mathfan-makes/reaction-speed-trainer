#!/usr/bin/env python3
"""
Analyzes reaction_data.csv and generates charts + console stats.
Charts are saved as PNGs next to the CSV.

  python analyze_reactions.py                    # all modes
  python analyze_reactions.py --mode TIMED       # just timed sessions
"""

import argparse
import sys
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# -------------
# Configuration
# -------------

CHART_DIR = None  # set from CSV path at runtime
OUTPUT_SUFFIX = "all"
CHART_STYLE = {
    "figure.facecolor": "#1e1e28",
    "axes.facecolor": "#1e1e28",
    "axes.edgecolor": "#555568",
    "axes.labelcolor": "#dddde6",
    "text.color": "#dddde6",
    "xtick.color": "#aaaabc",
    "ytick.color": "#aaaabc",
    "grid.color": "#333348",
    "grid.alpha": 0.5,
}
ACCENT = "#ffa028"
GREEN = "#00dc78"
RED = "#dc3232"
BLUE = "#4a9eff"
EARLY_REPS = 5    # reps considered "early" for fatigue analysis
LATE_REPS = 5     # reps considered "late"


def load_data(csv_path):
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    print(f"Loaded {len(df)} trials across {df['session_id'].nunique()} sessions")
    print(f"Date range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
    print(f"Modes used: {', '.join(df['mode'].unique())}")
    print()
    return df


def filter_by_mode(df, mode):
    normalized_mode = mode.upper()
    if normalized_mode == "ALL":
        return df, normalized_mode

    available_modes = sorted(df["mode"].dropna().unique())
    filtered = df[df["mode"].str.upper() == normalized_mode].copy()
    if filtered.empty:
        print(f"Error: mode '{mode}' not found in data.")
        print(f"Available modes: ALL, {', '.join(available_modes)}")
        sys.exit(1)

    print(f"Filtering to mode: {normalized_mode}")
    print(f"Retained {len(filtered)} trials across {filtered['session_id'].nunique()} sessions")
    print()
    return filtered, normalized_mode


def summary_stats(df):
    hits = df[df["result"] == "HIT"].copy()
    if hits.empty:
        print("No successful hits recorded yet.")
        return

    session_stats = hits.groupby("session_id")["reaction_ms"].agg(
        ["count", "median", "mean", "std", "min", "max"]
    ).round(1)
    session_stats.columns = ["Hits", "Median", "Mean", "StdDev", "Best", "Worst"]

    print("=" * 72)
    print("Per-Session Summary")
    print("=" * 72)
    print(session_stats.to_string())
    print()

    # Overall
    print(f"Overall median:  {hits['reaction_ms'].median():.1f} ms")
    print(f"Overall mean:    {hits['reaction_ms'].mean():.1f} ms")
    print(f"Overall best:    {hits['reaction_ms'].min():.1f} ms")
    print(f"Total timeouts:  {len(df[df['result'] == 'timeout'])}")
    print()


def chart_session_trend(df):
    hits = df[df["result"] == "HIT"]
    session_order = hits.groupby("session_id")["timestamp"].min().sort_values().index
    medians = hits.groupby("session_id")["reaction_ms"].median().reindex(session_order)

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        x = range(len(medians))
        ax.plot(x, medians.values, color=ACCENT, marker="o", markersize=6,
                linewidth=2, zorder=5)
        ax.fill_between(x, medians.values, alpha=0.15, color=ACCENT)

        ax.set_xlabel("Session")
        ax.set_ylabel("Median Reaction Time (ms)")
        ax.set_title("Median Reaction Time by Session", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"S{i+1}" for i in x], fontsize=9)
        ax.grid(True, axis="y")
        # Zoom y-axis to data range with padding
        y_min = medians.min() - 15
        y_max = medians.max() + 15
        ax.set_ylim(y_min, y_max)
        ax.yaxis.set_major_locator(ticker.MultipleLocator(10))

        plt.tight_layout()
        path = os.path.join(CHART_DIR, f"chart_session_trend_{OUTPUT_SUFFIX}.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"Saved: {path}")


def chart_histogram(df):
    hits = df[df["result"] == "HIT"]["reaction_ms"]

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))

        bins = np.arange(
            max(150, int(hits.min() // 10 * 10)),
            int(hits.max() // 10 * 10) + 20,
            10
        )
        ax.hist(hits, bins=bins, color=BLUE, edgecolor="#2a2a3a", alpha=0.85)

        # Median line
        med = hits.median()
        ax.axvline(med, color=ACCENT, linewidth=2, linestyle="--", label=f"Median: {med:.0f} ms")

        ax.set_xlabel("Reaction Time (ms)")
        ax.set_ylabel("Frequency")
        ax.set_title("Distribution of All Reaction Times", fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(True, axis="y")

        plt.tight_layout()
        path = os.path.join(CHART_DIR, f"chart_histogram_{OUTPUT_SUFFIX}.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"Saved: {path}")


def chart_fatigue(df):
    hits = df[df["result"] == "HIT"].copy()
    max_rep = hits.groupby("session_id")["rep"].max()

    early = hits[hits["rep"] <= EARLY_REPS]
    late_mask = hits.apply(lambda row: row["rep"] > max_rep.get(row["session_id"], 20) - LATE_REPS, axis=1)
    late = hits[late_mask]

    session_order = hits.groupby("session_id")["timestamp"].min().sort_values().index

    early_avg = early.groupby("session_id")["reaction_ms"].mean().reindex(session_order)
    late_avg = late.groupby("session_id")["reaction_ms"].mean().reindex(session_order)

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(session_order))
        width = 0.35

        ax.bar(x - width/2, early_avg.values, width, color=GREEN, alpha=0.85,
               label=f"First {EARLY_REPS} reps")
        ax.bar(x + width/2, late_avg.values, width, color=RED, alpha=0.85,
               label=f"Last {LATE_REPS} reps")

        ax.set_xlabel("Session")
        ax.set_ylabel("Avg Reaction Time (ms)")
        ax.set_title("Fatigue Effect: Early vs. Late Reps", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"S{i+1}" for i in x], fontsize=9)
        ax.legend()
        ax.grid(True, axis="y")

        plt.tight_layout()
        path = os.path.join(CHART_DIR, f"chart_fatigue_{OUTPUT_SUFFIX}.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"Saved: {path}")


def chart_boxplot(df):
    hits = df[df["result"] == "HIT"]
    session_order = hits.groupby("session_id")["timestamp"].min().sort_values().index

    data_by_session = [hits[hits["session_id"] == sid]["reaction_ms"].values for sid in session_order]

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))

        bp = ax.boxplot(data_by_session, patch_artist=True, widths=0.6,
                        medianprops=dict(color=RED, linewidth=2),
                        whiskerprops=dict(color="#888"),
                        capprops=dict(color="#888"),
                        flierprops=dict(marker="o", markerfacecolor="#888", markersize=4, alpha=0.5))

        for patch in bp["boxes"]:
            patch.set_facecolor(ACCENT)
            patch.set_alpha(0.6)

        ax.set_xlabel("Session")
        ax.set_ylabel("Reaction Time (ms)")
        ax.set_title("Reaction Time Spread by Session", fontsize=14, fontweight="bold")
        ax.set_xticklabels([f"S{i+1}" for i in range(len(data_by_session))], fontsize=9)
        ax.grid(True, axis="y")

        plt.tight_layout()
        path = os.path.join(CHART_DIR, f"chart_boxplot_{OUTPUT_SUFFIX}.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"Saved: {path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze reaction training CSV data.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        help="Path to reaction_data.csv. Defaults to reaction_data.csv next to this script.",
    )
    parser.add_argument(
        "--mode",
        default="ALL",
        help="Mode to analyze: ALL, TIMED, BLITZ, RANDOM_DELAY, etc.",
    )
    return parser.parse_args()


def main():
    global CHART_DIR, OUTPUT_SUFFIX

    args = parse_args()

    # Determine CSV path
    if args.csv_path:
        csv_path = args.csv_path
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, "reaction_data.csv")

    if not os.path.exists(csv_path):
        print(f"No data file found at: {csv_path}")
        print("Run reaction_trainer.py first to generate data.")
        sys.exit(1)

    CHART_DIR = os.path.dirname(os.path.abspath(csv_path))

    df = load_data(csv_path)
    df, selected_mode = filter_by_mode(df, args.mode)
    OUTPUT_SUFFIX = selected_mode.lower()

    if len(df) < 2:
        print("Not enough data to analyze. Run more sessions first.")
        sys.exit(1)

    summary_stats(df)

    print("Generating charts...")
    chart_session_trend(df)
    chart_histogram(df)
    chart_fatigue(df)
    chart_boxplot(df)
    print(f"\nDone. All charts saved alongside the CSV file with suffix '{OUTPUT_SUFFIX}'.")


if __name__ == "__main__":
    main()
