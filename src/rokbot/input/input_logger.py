"""Input telemetry logging."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger


@dataclass
class InputEvent:
    """Log entry for a single input event."""

    event_type: str
    params: dict
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    humanized_delay_ms: Optional[float] = None
    intended_target: Optional[tuple] = None
    actual_target: Optional[tuple] = None


class InputLogger:
    """Log all input events for telemetry and debugging."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._events: List[InputEvent] = []

    def log(self, event: InputEvent) -> None:
        """Log an input event."""
        self._events.append(event)
        logger.debug(f"Input logged: {event.event_type} at {event.timestamp}")

    def save_session(self, session_id: str) -> Path:
        """Save accumulated events to JSONL."""
        path = self.log_dir / f"{session_id}_inputs.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for event in self._events:
                f.write(json.dumps(asdict(event), default=str) + "\n")
        logger.info(f"Saved {len(self._events)} input events to {path}")
        return path
