"""Export telemetry data for external analysis."""

import json
from pathlib import Path
from typing import List

import numpy as np
from loguru import logger


class AnalyticsExporter:
    """Export bot and human data for analysis."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_timing_distribution(
        self, human_times: List[float], bot_times: List[float], filename: str = "timing_distribution"
    ) -> Path:
        """Export timing data as JSON for plotting."""
        path = self.output_dir / f"{filename}.json"
        data = {
            "human": human_times,
            "bot": bot_times,
            "human_stats": {
                "mean": float(np.mean(human_times)),
                "std": float(np.std(human_times)),
            },
            "bot_stats": {
                "mean": float(np.mean(bot_times)),
                "std": float(np.std(bot_times)),
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Exported timing distribution to {path}")
        return path
