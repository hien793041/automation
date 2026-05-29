"""Image I/O and conversion utilities."""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger


def load_image(path: Path) -> Optional[np.ndarray]:
    """Load an image from disk."""
    image = cv2.imread(str(path))
    if image is None:
        logger.warning(f"Failed to load image: {path}")
    return image


def save_image(path: Path, image: np.ndarray) -> None:
    """Save an image to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def resize(image: np.ndarray, width: Optional[int] = None, height: Optional[int] = None) -> np.ndarray:
    """Resize image maintaining aspect ratio if only one dimension given."""
    h, w = image.shape[:2]
    if width is None and height is None:
        return image
    if width is None:
        ratio = height / h
        width = int(w * ratio)
    elif height is None:
        ratio = width / w
        height = int(h * ratio)
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)


def to_rgb(image: np.ndarray) -> np.ndarray:
    """Convert BGR to RGB."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def to_bgr(image: np.ndarray) -> np.ndarray:
    """Convert RGB to BGR."""
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
