"""YOLOv8 UI element detector with per-class confidence calibration."""

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from loguru import logger

from rokbot.core.config import BotConfig
from rokbot.vision.confidence_calibrator import ConfidenceCalibrator


class DetectionResult:
    """Result of a YOLO detection."""

    def __init__(
        self,
        class_name: str,
        confidence: float,
        bbox: Tuple[int, int, int, int],  # x1, y1, x2, y2
    ):
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox

    @property
    def center(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) // 2, (y1 + y2) // 2

    def __repr__(self) -> str:
        return f"DetectionResult({self.class_name}, conf={self.confidence:.3f}, bbox={self.bbox})"


class YOLODetector:
    """Detects UI elements using YOLOv8 with per-class thresholds."""

    DEFAULT_THRESHOLDS = {
        "connection_lost": 0.92,
        "captcha": 0.92,
        "vip_popup": 0.90,
        "gather_btn": 0.85,
        "march_btn": 0.85,
        "icon_marching": 0.75,
        "icon_gathering": 0.75,
    }

    def __init__(self, config: BotConfig):
        self.config = config
        self.model_path = config.vision.yolo_model_path
        self._model = None
        self._calibrator = ConfidenceCalibrator()
        self._thresholds: dict = dict(self.DEFAULT_THRESHOLDS)
        self._load_model()

    def _load_model(self) -> None:
        """Lazy-load YOLOv8 model."""
        try:
            from ultralytics import YOLO

            if self.model_path.exists():
                self._model = YOLO(str(self.model_path))
                logger.info(f"Loaded YOLO model from {self.model_path}")
            else:
                logger.warning(f"YOLO model not found at {self.model_path}")
        except ImportError:
            logger.error("ultralytics not installed; YOLO detection unavailable")

    def detect(self, image: np.ndarray) -> List[DetectionResult]:
        """Run detection on a screenshot and return high-confidence results."""
        if self._model is None:
            logger.warning("YOLO model not loaded; skipping detection")
            return []

        results = self._model.predict(image, verbose=False)
        detections: List[DetectionResult] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                class_name = result.names.get(cls_id, f"class_{cls_id}")
                threshold = self._thresholds.get(class_name, self.config.vision.confidence_threshold)

                if conf >= threshold:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    detections.append(
                        DetectionResult(
                            class_name=class_name,
                            confidence=conf,
                            bbox=(x1, y1, x2, y2),
                        )
                    )

        logger.debug(f"YOLO detected {len(detections)} elements above threshold")
        return detections

    def update_thresholds(self, thresholds: dict) -> None:
        """Update per-class thresholds (e.g., from calibration)."""
        self._thresholds.update(thresholds)
        logger.info(f"Updated thresholds for {len(thresholds)} classes")
