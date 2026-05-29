"""Feedback loop: verify input execution via screenshots."""

import time
from typing import Callable, Optional

import numpy as np
from loguru import logger

from rokbot.vision.screen_capture import ScreenCapture


class InputVerifier:
    """Verify that inputs produced expected screen changes."""

    def __init__(
        self,
        screen_capture: ScreenCapture,
        verify_interval_seconds: float = 1.0,
        max_wait_seconds: float = 5.0,
    ):
        self.capture = screen_capture
        self.verify_interval = verify_interval_seconds
        self.max_wait = max_wait_seconds

    def verify_change(
        self,
        baseline: np.ndarray,
        predicate: Callable[[np.ndarray], bool],
    ) -> bool:
        """Wait for screen to satisfy predicate after input."""
        deadline = time.monotonic() + self.max_wait
        while time.monotonic() < deadline:
            time.sleep(self.verify_interval)
            screenshot = self.capture.capture()
            if screenshot is not None and predicate(screenshot):
                logger.debug("Input verified: screen changed as expected")
                return True
        logger.warning("Input verification timed out")
        return False

    def verify_no_change(
        self,
        baseline: np.ndarray,
        threshold: float = 0.99,
    ) -> bool:
        """Verify screen remained unchanged (for failed taps)."""
        time.sleep(self.verify_interval)
        screenshot = self.capture.capture()
        if screenshot is None:
            return False
        # Simple pixel difference ratio
        diff = np.mean(np.abs(screenshot.astype(float) - baseline.astype(float)))
        max_diff = 255.0
        similarity = 1.0 - (diff / max_diff)
        logger.debug(f"Screen similarity after input: {similarity:.4f}")
        return similarity >= threshold
