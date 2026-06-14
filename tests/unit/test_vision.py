"""Unit tests for vision pipeline."""

import numpy as np

from rokbot.vision.image_preprocessor import ImagePreprocessor
from rokbot.vision.region_of_interest import ROIManager


def test_preprocessor_resize():
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    preprocessor = ImagePreprocessor(target_size=(640, 360))
    out = preprocessor.process(img)
    assert out.shape[:2] == (360, 640)


def test_roi_manager():
    roi_mgr = ROIManager()
    roi = roi_mgr.get("top_bar")
    assert roi is not None
    assert roi.name == "top_bar"
