"""ROI selector and manager for targeted vision processing."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class ROI:
    """Region of Interest definition."""

    name: str
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def crop(self, image: np.ndarray) -> np.ndarray:
        return image[self.y1 : self.y2, self.x1 : self.x2]

    def contains(self, point: Tuple[int, int]) -> bool:
        x, y = point
        return self.x1 <= x < self.x2 and self.y1 <= y < self.y2


class ROIManager:
    """Manages named ROIs for efficient vision processing."""

    DEFAULT_ROIS = {
        "top_bar": ROI("top_bar", 0, 0, 1920, 120),
        "bottom_bar": ROI("bottom_bar", 0, 960, 1920, 1080),
        "center_dialog": ROI("center_dialog", 560, 240, 1360, 840),
        "minimap": ROI("minimap", 1620, 0, 1920, 300),
        "resource_bar": ROI("resource_bar", 300, 0, 1620, 80),
    }

    def __init__(self, screen_size: Tuple[int, int] = (1920, 1080)):
        self.screen_size = screen_size
        self._rois: Dict[str, ROI] = dict(self.DEFAULT_ROIS)

    def add(self, roi: ROI) -> None:
        """Add or overwrite an ROI."""
        self._rois[roi.name] = roi

    def get(self, name: str) -> Optional[ROI]:
        """Retrieve an ROI by name."""
        return self._rois.get(name)

    def list_names(self) -> List[str]:
        """List all registered ROI names."""
        return list(self._rois.keys())

    def draw(self, image: np.ndarray, color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> np.ndarray:
        """Draw all ROIs on an image for debugging."""
        annotated = image.copy()
        for roi in self._rois.values():
            cv2.rectangle(annotated, (roi.x1, roi.y1), (roi.x2, roi.y2), color, thickness)
            cv2.putText(
                annotated,
                roi.name,
                (roi.x1 + 5, roi.y1 + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )
        return annotated
