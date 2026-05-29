"""Human biometric profile loader for consistent bot personality."""

import json
from pathlib import Path
from typing import Dict, Optional

from loguru import logger


class BiometricProfile:
    """Consistent human-like personality profile."""

    def __init__(self, profile_path: Optional[Path] = None):
        self.timing_distributions: Dict[str, dict] = {}
        self.movement_jerk_profile: Dict[str, float] = {}
        self.personality: Dict[str, float] = {
            "base_distraction_rate": 0.08,
            "base_fatigue_rate": 0.5,
            "base_misclick_rate": 0.01,
            "aggression": 0.5,
        }
        self.profile_id: str = "default"

        if profile_path and profile_path.exists():
            self.load(profile_path)

    def load(self, path: Path) -> None:
        """Load profile from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.timing_distributions = data.get("timing_distributions", {})
        self.movement_jerk_profile = data.get("movement_jerk_profile", {})
        self.personality = data.get("personality", self.personality)
        self.profile_id = data.get("profile_id", path.stem)
        logger.info(f"Loaded biometric profile '{self.profile_id}' from {path}")

    def save(self, path: Path) -> None:
        """Save profile to JSON."""
        data = {
            "profile_id": self.profile_id,
            "timing_distributions": self.timing_distributions,
            "movement_jerk_profile": self.movement_jerk_profile,
            "personality": self.personality,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved biometric profile to {path}")
