"""Stuck detection and recovery."""

from collections import deque
from typing import Optional

from loguru import logger


class StuckDetector:
    """Detect when bot is stuck by monitoring state history."""

    def __init__(self, window_size: int = 10, threshold: int = 8):
        self.window_size = window_size
        self.threshold = threshold
        self._history: deque = deque(maxlen=window_size)

    def record(self, state: str) -> None:
        """Record a state observation."""
        self._history.append(state)

    def is_stuck(self) -> bool:
        """Return True if stuck (same state dominates recent history)."""
        if len(self._history) < self.window_size:
            return False
        most_common = max(set(self._history), key=lambda s: self._history.count(s))
        count = self._history.count(most_common)
        stuck = count >= self.threshold
        if stuck:
            logger.warning(f"Stuck detected: state '{most_common}' observed {count}/{self.window_size} times")
        return stuck

    def reset(self) -> None:
        """Clear history after recovery."""
        self._history.clear()
