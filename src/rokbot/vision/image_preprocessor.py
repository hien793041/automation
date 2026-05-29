"""Image preprocessing: resize, denoise, enhance."""

from typing import Optional, Tuple

import cv2
import numpy as np
from loguru import logger


class ImagePreprocessor:
    """Preprocess screenshots before vision inference."""

    def __init__(
        self,
        target_size: Optional[Tuple[int, int]] = None,
        denoise: bool = True,
        enhance_contrast: bool = True,
    ):
        self.target_size = target_size
        self.denoise = denoise
        self.enhance_contrast = enhance_contrast

    def process(self, image: np.ndarray) -> np.ndarray:
        """Apply full preprocessing pipeline."""
        if self.target_size is not None:
            image = self._resize(image, self.target_size)
        if self.denoise:
            image = self._denoise(image)
        if self.enhance_contrast:
            image = self._enhance_contrast(image)
        return image

    @staticmethod
    def _resize(image: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
        return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def _denoise(image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)

    @staticmethod
    def _enhance_contrast(image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def normalize(image: np.ndarray) -> np.ndarray:
        return image.astype(np.float32) / 255.0
