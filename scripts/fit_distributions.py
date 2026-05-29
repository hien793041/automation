#!/usr/bin/env python3
"""Fit human data to statistical distributions."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.mixture import GaussianMixture

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def fit_gaussian(data: np.ndarray):
    mu, sigma = stats.norm.fit(data)
    ks_stat, p_value = stats.kstest(data, "norm", args=(mu, sigma))
    return {"type": "gaussian", "mu": float(mu), "sigma": float(sigma), "ks_pvalue": float(p_value)}


def fit_log_normal(data: np.ndarray):
    shape, loc, scale = stats.lognorm.fit(data, floc=0)
    return {"type": "log_normal", "shape": float(shape), "scale": float(scale)}


def fit_bimodal(data: np.ndarray):
    gmm = GaussianMixture(n_components=2, random_state=42)
    gmm.fit(data.reshape(-1, 1))
    weights = gmm.weights_.tolist()
    means = gmm.means_.flatten().tolist()
    covars = np.sqrt(gmm.covariances_.flatten()).tolist()
    return {
        "type": "bimodal_gaussian",
        "components": [
            {"weight": weights[i], "mu": means[i], "sigma": covars[i]} for i in range(2)
        ],
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fit distributions to human data")
    parser.add_argument("--input-dir", default="data/human_recordings")
    parser.add_argument("--output", default="data/human_recordings/fitted_distributions.json")
    args = parser.parse_args()

    # Placeholder: load data from JSONL files
    print("Fitting distributions... (implement data loading)")
    results = {}
    # TODO: load timing_data.jsonl and fit

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved fitted distributions to {args.output}")


if __name__ == "__main__":
    main()
