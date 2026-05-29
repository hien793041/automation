"""Record human gameplay for data collection."""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from loguru import logger


@dataclass
class TouchEvent:
    """Human touch event record."""

    x: int
    y: int
    action: str  # down, move, up
    pressure: float
    timestamp: float


@dataclass
class TimingEvent:
    """Human timing event record."""

    event_type: str
    duration_ms: float
    context: str
    timestamp: float


@dataclass
class SessionData:
    """Aggregated human session data."""

    player_id: str
    session_id: str
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    touch_events: List[TouchEvent] = field(default_factory=list)
    timing_events: List[TimingEvent] = field(default_factory=list)
    screenshots_count: int = 0


class HumanRecorder:
    """Record human gameplay sessions."""

    def __init__(self, output_dir: Path, player_id: str = "player_001"):
        self.output_dir = output_dir
        self.player_id = player_id
        self.session_dir = output_dir / player_id / f"session_{datetime.utcnow().strftime('%Y_%m_%d_%H_%M')}"
        self.screenshot_dir = self.session_dir / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.data = SessionData(player_id=player_id, session_id=self.session_dir.name)
        self._screenshot_counter = 0

    def record_touch(self, event: TouchEvent) -> None:
        """Record a touch event."""
        self.data.touch_events.append(event)

    def record_timing(self, event: TimingEvent) -> None:
        """Record a timing event."""
        self.data.timing_events.append(event)

    def save_screenshot(self, image: np.ndarray) -> Path:
        """Save a timed screenshot."""
        self._screenshot_counter += 1
        path = self.screenshot_dir / f"screenshot_{self._screenshot_counter:05d}.png"
        cv2.imwrite(str(path), image)
        self.data.screenshots_count = self._screenshot_counter
        return path

    def save_session(self) -> Path:
        """Save session JSON."""
        path = self.session_dir / "session_metadata.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data.__dict__, f, indent=2, default=lambda o: asdict(o) if hasattr(o, "__dataclass_fields__") else str(o))

        touch_path = self.session_dir / "touch_events.jsonl"
        with open(touch_path, "w", encoding="utf-8") as f:
            for ev in self.data.touch_events:
                f.write(json.dumps(asdict(ev)) + "\n")

        timing_path = self.session_dir / "timing_data.jsonl"
        with open(timing_path, "w", encoding="utf-8") as f:
            for ev in self.data.timing_events:
                f.write(json.dumps(asdict(ev)) + "\n")

        logger.info(f"Saved human session to {self.session_dir}")
        return self.session_dir
