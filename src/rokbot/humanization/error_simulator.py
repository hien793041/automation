"""Simulates human-like errors: misclicks, wrong-button presses."""

import random
from typing import Tuple

from loguru import logger

from rokbot.humanization.decision_engine import DecisionEngine


class ErrorSimulator:
    """Injects realistic human errors into input execution."""

    def __init__(self, decision_engine: DecisionEngine, max_misclick_distance: int = 30):
        self.decision = decision_engine
        self.max_misclick_distance = max_misclick_distance

    def maybe_misclick(
        self, target: Tuple[int, int], difficulty: float = 1.0
    ) -> Tuple[int, int]:
        """Return possibly offset target to simulate a misclick."""
        if self.decision.should_misclick(difficulty):
            offset_x = random.randint(-self.max_misclick_distance, self.max_misclick_distance)
            offset_y = random.randint(-self.max_misclick_distance, self.max_misclick_distance)
            actual = (target[0] + offset_x, target[1] + offset_y)
            logger.info(f"Simulated misclick: target={target}, actual={actual}")
            return actual
        return target

