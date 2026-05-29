"""PaddleOCR wrapper with ROI targeting and context verification."""

import re
from typing import List, Optional, Tuple

import cv2
import numpy as np
from loguru import logger


class OCRResult:
    """Result of OCR text detection."""

    def __init__(
        self,
        text: str,
        confidence: float,
        bbox: Tuple[int, int, int, int],
    ):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox

    def __repr__(self) -> str:
        return f"OCRResult('{self.text}', conf={self.confidence:.3f})"


class OCREngine:
    """OCR engine for reading UI text and verifying detections."""

    TIMER_PATTERNS = [
        re.compile(r"(\d{1,2}):(\d{2}):(\d{2})"),  # HH:MM:SS
        re.compile(r"(\d{1,2}):(\d{2})"),          # MM:SS
    ]

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._engine = None
        self._load_engine()

    def _load_engine(self) -> None:
        """Lazy-load PaddleOCR engine."""
        try:
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=self.use_gpu,
                show_log=False,
            )
            logger.info("PaddleOCR engine loaded")
        except ImportError:
            logger.error("paddleocr not installed; OCR unavailable")

    def read(self, image: np.ndarray, roi: Optional[Tuple[int, int, int, int]] = None) -> List[OCRResult]:
        """Read text from image, optionally within an ROI."""
        if self._engine is None:
            logger.warning("OCR engine not loaded; skipping OCR")
            return []

        if roi is not None:
            x1, y1, x2, y2 = roi
            image = image[y1:y2, x1:x2]

        result = self._engine.ocr(image, cls=True)
        ocr_results: List[OCRResult] = []

        if result is None or result[0] is None:
            return ocr_results

        for line in result[0]:
            if line is None:
                continue
            bbox_points, (text, conf) = line
            pts = np.array(bbox_points, dtype=np.int32)
            x1, y1 = pts[:, 0].min(), pts[:, 1].min()
            x2, y2 = pts[:, 0].max(), pts[:, 1].max()
            if roi is not None:
                x1 += roi[0]
                y1 += roi[1]
                x2 += roi[0]
                y2 += roi[1]
            ocr_results.append(OCRResult(text=text, confidence=conf, bbox=(x1, y1, x2, y2)))

        logger.debug(f"OCR read {len(ocr_results)} text blocks")
        return ocr_results

    def verify_context(
        self,
        image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        expected_text: str,
        margin: int = 20,
    ) -> bool:
        """Verify that expected text appears near a bbox."""
        x1, y1, x2, y2 = bbox
        roi = (
            max(0, x1 - margin),
            max(0, y1 - margin),
            x2 + margin,
            y2 + margin,
        )
        results = self.read(image, roi=roi)
        for res in results:
            if expected_text.lower() in res.text.lower():
                return True
        return False

    def parse_timer(self, text: str) -> Optional[int]:
        """Parse a timer string into total seconds."""
        for pattern in self.TIMER_PATTERNS:
            match = pattern.match(text.strip())
            if match:
                groups = list(map(int, match.groups()))
                if len(groups) == 3:
                    return groups[0] * 3600 + groups[1] * 60 + groups[2]
                elif len(groups) == 2:
                    return groups[0] * 60 + groups[1]
        return None
