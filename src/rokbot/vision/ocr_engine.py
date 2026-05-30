"""OCR engine for reading UI text and verifying detections.

Uses pytesseract (Tesseract OCR) as the primary engine.
"""

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

    def __init__(self, lang: str = "eng"):
        """lang: tesseract language code (e.g., 'eng', 'vie', 'eng+vie')."""
        self.lang = lang
        self._engine = None
        self._load_engine()

    def _load_engine(self) -> None:
        """Lazy-load pytesseract."""
        try:
            import pytesseract

            # Verify tesseract is accessible
            pytesseract.get_tesseract_version()
            self._engine = pytesseract
            logger.info(f"Tesseract OCR engine loaded (lang={self.lang})")
        except ImportError:
            logger.error("pytesseract not installed; OCR unavailable")
        except Exception as e:
            logger.error(f"Tesseract failed to load: {e}")

    def read(self, image: np.ndarray, roi: Optional[Tuple[int, int, int, int]] = None) -> List[OCRResult]:
        """Read text from image, optionally within an ROI."""
        if self._engine is None:
            logger.warning("OCR engine not loaded; skipping OCR")
            return []

        if roi is not None:
            x1, y1, x2, y2 = roi
            image = image[y1:y2, x1:x2]

        try:
            return self._read_tesseract(image, roi)
        except Exception as e:
            logger.warning(f"OCR read failed: {e}")
            return []

    def _read_tesseract(
        self, image: np.ndarray, roi: Optional[Tuple[int, int, int, int]]
    ) -> List[OCRResult]:
        results: List[OCRResult] = []

        # Tesseract expects RGB or grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        data = self._engine.image_to_data(
            gray,
            lang=self.lang,
            config='--psm 6',
            output_type=self._engine.Output.DICT,
        )

        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if not text or conf <= 0:
                continue

            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            x1, y1, x2, y2 = x, y, x + w, y + h
            if roi is not None:
                rx, ry, _, _ = roi
                x1 += rx
                y1 += ry
                x2 += rx
                y2 += ry

            results.append(
                OCRResult(
                    text=text,
                    confidence=conf / 100.0,
                    bbox=(x1, y1, x2, y2),
                )
            )

        logger.debug(f"OCR read {len(results)} text blocks")
        return results

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
