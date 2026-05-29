"""Action queue with timestamps for replay and verification."""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from loguru import logger


@dataclass
class QueuedInput:
    """A single queued input event."""

    action: str  # tap, swipe, key
    params: dict
    scheduled_time: datetime
    executed: bool = False
    execute_time: Optional[datetime] = None


class InputQueue:
    """Queue inputs with scheduled execution times."""

    def __init__(self):
        self._queue: List[QueuedInput] = []

    def add(self, action: str, params: dict, delay_ms: float = 0) -> None:
        """Add an input to the queue."""
        scheduled = datetime.utcnow() + __import__("datetime").timedelta(milliseconds=delay_ms)
        self._queue.append(QueuedInput(action=action, params=params, scheduled_time=scheduled))

    def pending(self) -> List[QueuedInput]:
        """Return inputs that are scheduled and not yet executed."""
        now = datetime.utcnow()
        return [inp for inp in self._queue if not inp.executed and inp.scheduled_time <= now]

    def mark_executed(self, inp: QueuedInput) -> None:
        """Mark an input as executed."""
        inp.executed = True
        inp.execute_time = datetime.utcnow()

    def clear(self) -> None:
        """Clear the queue."""
        self._queue.clear()
