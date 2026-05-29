"""Collect bot runtime metrics."""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger


@dataclass
class BotMetrics:
    """Snapshot of bot metrics."""

    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    state: str = "UNKNOWN"
    uptime_seconds: float = 0.0
    actions_executed: int = 0
    actions_failed: int = 0
    detections_per_frame: int = 0
    avg_inference_ms: float = 0.0
    current_fatigue: float = 0.0


class TelemetryCollector:
    """Collect and aggregate bot telemetry."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._metrics: List[BotMetrics] = []
        self._start_time = time.monotonic()

    def record(self, metrics: BotMetrics) -> None:
        """Record a metrics snapshot."""
        metrics.uptime_seconds = time.monotonic() - self._start_time
        self._metrics.append(metrics)

    def save(self, session_id: str) -> Path:
        """Save telemetry to JSON."""
        path = self.output_dir / f"{session_id}_telemetry.json"
        data = [m.__dict__ for m in self._metrics]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved telemetry ({len(self._metrics)} snapshots) to {path}")
        return path
