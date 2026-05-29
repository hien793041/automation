"""Mathematical utilities for distribution sampling."""

import math

import numpy as np


def sample_gaussian(mu: float, sigma: float) -> float:
    """Sample from Gaussian distribution, clamped to positive."""
    return max(0.0, float(np.random.normal(mu, sigma)))


def sample_log_normal(shape: float, scale: float) -> float:
    """Sample from log-normal distribution."""
    return float(np.random.lognormal(mean=math.log(scale), sigma=shape))


def sample_exponential(lambda_param: float) -> float:
    """Sample from exponential distribution."""
    return float(np.random.exponential(1.0 / lambda_param))


def sample_bimodal(mu1: float, sigma1: float, weight1: float, mu2: float, sigma2: float) -> float:
    """Sample from bimodal Gaussian mixture."""
    if np.random.random() < weight1:
        return sample_gaussian(mu1, sigma1)
    return sample_gaussian(mu2, sigma2)
