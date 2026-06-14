#!/usr/bin/env python3
"""Compare human vs bot telemetry."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from scipy.stats import ks_2samp


def compare_reaction_times(human_times: np.ndarray, bot_times: np.ndarray) -> dict:
    stat, p = ks_2samp(human_times, bot_times)
    return {"ks_statistic": float(stat), "p_value": float(p), "indistinguishable": p > 0.05}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Compare human vs bot data")
    parser.add_argument("--human", required=True, help="Path to human timing JSON")
    parser.add_argument("--bot", required=True, help="Path to bot timing JSON")
    args = parser.parse_args()

    print(f"Comparing {args.human} vs {args.bot}... (implement data loading)")
    # TODO: load and compare


if __name__ == "__main__":
    main()
