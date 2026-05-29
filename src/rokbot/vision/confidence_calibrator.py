"""Per-class confidence threshold calibration based on validation metrics."""

import json
from pathlib import Path
from typing import Dict, List

from loguru import logger


class ClassMetrics:
    """Validation metrics for a single class."""

    def __init__(self, class_name: str):
        self.class_name = class_name
        self.confidences: List[float] = []
        self.tp = 0
        self.fp = 0
        self.fn = 0

    def add(self, confidence: float, is_true_positive: bool) -> None:
        self.confidences.append(confidence)
        if is_true_positive:
            self.tp += 1
        else:
            self.fp += 1

    def precision_at(self, threshold: float) -> float:
        tp = sum(1 for c, is_tp in zip(self.confidences, [True] * self.tp + [False] * self.fp) if c >= threshold and is_tp)
        fp = sum(1 for c, is_tp in zip(self.confidences, [True] * self.tp + [False] * self.fp) if c >= threshold and not is_tp)
        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)


class ConfidenceCalibrator:
    """Calibrates per-class confidence thresholds to achieve target precision."""

    def __init__(self, target_precision: float = 0.95):
        self.target_precision = target_precision
        self._metrics: Dict[str, ClassMetrics] = {}

    def add_result(self, class_name: str, confidence: float, is_true_positive: bool) -> None:
        """Add a validation result."""
        if class_name not in self._metrics:
            self._metrics[class_name] = ClassMetrics(class_name)
        self._metrics[class_name].add(confidence, is_true_positive)

    def calibrate(self) -> Dict[str, float]:
        """Compute optimal threshold per class."""
        thresholds: Dict[str, float] = {}
        for name, metrics in self._metrics.items():
            sorted_conf = sorted(set(metrics.confidences), reverse=True)
            best_threshold = 0.5
            best_precision = 0.0
            for threshold in sorted_conf:
                precision = metrics.precision_at(threshold)
                if precision >= self.target_precision and precision >= best_precision:
                    best_precision = precision
                    best_threshold = threshold
            thresholds[name] = round(best_threshold, 3)
            logger.info(
                f"Calibrated '{name}': threshold={best_threshold}, precision={best_precision:.3f}"
            )
        return thresholds

    def save(self, path: Path) -> None:
        """Save calibration results to JSON."""
        thresholds = self.calibrate()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(thresholds, f, indent=2)
        logger.info(f"Saved calibration to {path}")

    def load(self, path: Path) -> Dict[str, float]:
        """Load calibration results from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            thresholds = json.load(f)
        logger.info(f"Loaded calibration from {path}: {len(thresholds)} classes")
        return thresholds
