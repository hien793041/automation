"""State context: tracks history, confidence, retries, and timeouts."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class StateRecord:
    """Single state observation."""

    state: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0
    detections: List[dict] = field(default_factory=list)


@dataclass
class TransitionRecord:
    """Record of a state transition attempt."""

    from_state: str
    to_state: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = False


class StateContext:
    """Maintains context across state machine execution."""

    def __init__(self, history_limit: int = 50, max_retries: int = 3):
        self.history_limit = history_limit
        self.max_retries = max_retries
        self._history: List[StateRecord] = []
        self._transitions: List[TransitionRecord] = []
        self._retry_counts: dict = {}
        self._state_start_time: Optional[datetime] = None

    @property
    def current_state(self) -> Optional[str]:
        if not self._history:
            return None
        return self._history[-1].state

    def record_state(self, state: str, confidence: float = 0.0, detections: Optional[List[dict]] = None) -> None:
        """Record a new state observation."""
        record = StateRecord(
            state=state,
            confidence=confidence,
            detections=detections or [],
        )
        self._history.append(record)
        if len(self._history) > self.history_limit:
            self._history.pop(0)

        if self._state_start_time is None or (self._history and self._history[-1].state != state):
            self._state_start_time = datetime.utcnow()
            self._retry_counts[state] = 0

    def record_transition(self, from_state: str, to_state: str, success: bool) -> None:
        """Record a transition attempt."""
        self._transitions.append(
            TransitionRecord(from_state=from_state, to_state=to_state, success=success)
        )

    def increment_retry(self, state: str) -> int:
        """Increment retry count for a state and return new count."""
        self._retry_counts[state] = self._retry_counts.get(state, 0) + 1
        return self._retry_counts[state]

    def time_in_current_state(self) -> float:
        """Return seconds spent in the current state."""
        if self._state_start_time is None:
            return 0.0
        return (datetime.utcnow() - self._state_start_time).total_seconds()

    def is_stuck(self, threshold_seconds: float) -> bool:
        """Check if bot has been in the same state too long."""
        return self.time_in_current_state() > threshold_seconds

    def reset_stuck_timer(self) -> None:
        """Reset the stuck timer so idle periods don't trigger false positives."""
        self._state_start_time = datetime.utcnow()
