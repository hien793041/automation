"""Distribution-based timing engine for human-like delays."""

import json
import random
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from loguru import logger

from rokbot.utils.math_utils import sample_gaussian, sample_log_normal, sample_exponential


class TimingEngine:
    """Samples delays from fitted human timing distributions."""

    def __init__(self, profile_path: Optional[Path] = None):
        self._distributions: Dict[str, dict] = {}
        if profile_path and profile_path.exists():
            self.load_profile(profile_path)
        else:
            self._set_defaults()

    def _set_defaults(self) -> None:
        """Set default distribution parameters."""
        self._distributions = {
            "reaction_time": {"type": "gaussian", "mu": 350.0, "sigma": 80.0},
            "click_interval": {"type": "log_normal", "shape": 0.8, "scale": 1.2},
            "decision_time": {"type": "gaussian", "mu": 600.0, "sigma": 200.0},
            "break_duration": {"type": "exponential", "lambda": 0.004},  # ~250s mean
        }

    def load_profile(self, path: Path) -> None:
        """Load fitted distributions from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            self._distributions = json.load(f)
        logger.info(f"Loaded timing profile from {path}")

    def sample(self, distribution_name: str) -> float:
        """Sample a delay in milliseconds."""
        dist = self._distributions.get(distribution_name)
        if dist is None:
            logger.warning(f"Unknown distribution '{distribution_name}'; returning 0")
            return 0.0

        dist_type = dist.get("type", "gaussian")
        if dist_type == "gaussian":
            return sample_gaussian(dist["mu"], dist["sigma"])
        elif dist_type == "log_normal":
            return sample_log_normal(dist["shape"], dist["scale"])
        elif dist_type == "exponential":
            return sample_exponential(dist["lambda"])
        else:
            logger.warning(f"Unsupported distribution type '{dist_type}'")
            return 0.0

    def reaction_delay(self) -> float:
        """Sample reaction time delay in ms."""
        return self.sample("reaction_time")

    def click_delay(self) -> float:
        """Sample inter-click delay in ms."""
        return self.sample("click_interval")

    def decision_delay(self) -> float:
        """Sample decision delay in ms."""
        return self.sample("decision_time")
