"""OpenCV template matching fallback for vision pipeline."""

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from loguru import logger


class TemplateMatch:
    """Result of a template match."""

    def __init__(
        self,
        template_name: str,
        confidence: float,
        bbox: Tuple[int, int, int, int],
    ):
        self.template_name = template_name
        self.confidence = confidence
        self.bbox = bbox

    @property
    def center(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) // 2, (y1 + y2) // 2

    def __repr__(self) -> str:
        return f"TemplateMatch({self.template_name}, conf={self.confidence:.3f})"


class TemplateMatcher:
    """Fallback template matcher using OpenCV."""

    def __init__(self, templates_dir: Path, threshold: float = 0.75):
        self.templates_dir = templates_dir
        self.threshold = threshold
        self._templates: dict = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load template images from disk."""
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return

        for path in self.templates_dir.rglob("*.png"):
            name = path.stem
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is not None:
                self._templates[name] = image

        logger.info(f"Loaded {len(self._templates)} templates from {self.templates_dir}")

    def match(
        self,
        image: np.ndarray,
        template_name: Optional[str] = None,
        roi: Optional[Tuple[int, int, int, int]] = None,
        threshold: Optional[float] = None,
    ) -> List[TemplateMatch]:
        """Match templates against an image."""
        if not self._templates:
            return []

        thr = threshold if threshold is not None else self.threshold

        if roi is not None:
            x1, y1, x2, y2 = roi
            search_image = image[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        else:
            search_image = image
            offset_x, offset_y = 0, 0

        if len(search_image.shape) == 3:
            search_gray = cv2.cvtColor(search_image, cv2.COLOR_BGR2GRAY)
        else:
            search_gray = search_image

        if template_name:
            if template_name not in self._templates:
                logger.debug(f"Template '{template_name}' not loaded (file missing)")
                return []
            templates = {template_name: self._templates[template_name]}
        else:
            templates = self._templates
        matches: List[TemplateMatch] = []

        for name, template in templates.items():
            if template is None:
                continue
            result = cv2.matchTemplate(search_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            logger.debug(f"Template '{name}' best confidence = {max_val:.3f} (threshold={thr})")

            if max_val >= thr:
                h, w = template.shape[:2]
                top_left = (max_loc[0] + offset_x, max_loc[1] + offset_y)
                bbox = (top_left[0], top_left[1], top_left[0] + w, top_left[1] + h)
                matches.append(TemplateMatch(template_name=name, confidence=max_val, bbox=bbox))

        logger.debug(f"Template matched {len(matches)} templates")
        return matches
