"""Cognitive state simulation: fatigue, distraction, emotion."""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger


@dataclass
class CognitiveState:
    """Current cognitive state of the simulated human."""

    fatigue: float = 0.0  # 0-1
    frustration: float = 0.0  # 0-1
    focus: float = 1.0  # 0-1
    distraction_probability: float = 0.08
    session_start: datetime = field(default_factory=datetime.utcnow)
    error_count: int = 0


class DecisionEngine:
    """Simulates human cognitive state affecting decisions and timing."""

    def __init__(
        self,
        fatigue_half_life_hours: float = 2.0,
        base_distraction_rate: float = 0.08,
        base_misclick_rate: float = 0.01,
    ):
        self.fatigue_half_life_hours = fatigue_half_life_hours
        self.base_distraction_rate = base_distraction_rate
        self.base_misclick_rate = base_misclick_rate
        self.state = CognitiveState()
        self._last_update = datetime.utcnow()

    def update(self) -> None:
        """Update cognitive state based on elapsed session time."""
        now = datetime.utcnow()
        elapsed_hours = (now - self.state.session_start).total_seconds() / 3600.0

        # Fatigue sigmoid curve, steep after 2 hours
        k = 5.0 / self.fatigue_half_life_hours
        self.state.fatigue = 1.0 / (1.0 + math.exp(-k * (elapsed_hours - self.fatigue_half_life_hours)))

        # Focus decreases with fatigue
        self.state.focus = max(0.3, 1.0 - self.state.fatigue * 0.7)

        # Distraction increases with fatigue
        self.state.distraction_probability = self.base_distraction_rate + self.state.fatigue * 0.15

        self._last_update = now

    def is_distracted(self) -> bool:
        """Check if currently distracted."""
        self.update()
        return random.random() < self.state.distraction_probability

    def should_misclick(self, difficulty: float = 1.0) -> bool:
        """Determine if next click should be a misclick."""
        self.update()
        rate = self.base_misclick_rate * (1 + self.state.fatigue) * difficulty
        return random.random() < rate

    def change_mind(self) -> bool:
        """Determine if the simulated human changes their mind."""
        self.update()
        rate = 0.02 + self.state.frustration * 0.05
        return random.random() < rate

    def reaction_time_multiplier(self) -> float:
        """Return multiplier for reaction time based on focus."""
        self.update()
        return 1.0 / max(self.state.focus, 0.3) + self.state.fatigue * 0.3

    def record_error(self) -> None:
        """Record an error to increase frustration."""
        self.state.error_count += 1
        self.state.frustration = min(1.0, self.state.frustration + 0.1)
        logger.debug(f"Error recorded: count={self.state.error_count}, frustration={self.state.frustration:.2f}")

    def record_success(self) -> None:
        """Record a success to reduce frustration."""
        self.state.frustration = max(0.0, self.state.frustration - 0.05)
