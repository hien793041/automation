"""Reconnect action for handling connection lost / disconnect."""

import time
from typing import Optional, Tuple

import cv2
import numpy as np
from loguru import logger

from typing import TYPE_CHECKING, Optional

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class ReconnectAction(BaseAction):
    """Action to reconnect when the game loses connection."""

    # Keywords that indicate a disconnect / reconnect screen
    DISCONNECT_KEYWORDS = [
        # English
        "connection",
        "lost",
        "disconnected",
        "reconnect",
        "retry",
        "network",
        "unstable",
        # Vietnamese
        "mất kết nối",
        "ngắt kết nối",
        "kết nối lại",
        "thử lại",
        "mạng",
        "đã ngắt",
    ]

    # Keywords that appear on the button we should tap
    BUTTON_KEYWORDS = [
        # English
        "reconnect",
        "retry",
        "ok",
        "confirm",
        "yes",
        # Vietnamese
        "xác nhận",
        "kết nối lại",
        "thử lại",
        "đồng ý",
    ]

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self.max_tap_attempts = 3
        self.post_tap_wait_seconds = 5

    def can_execute(self) -> bool:
        """Check if the screen shows a disconnect / connection-lost state."""
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        # Also react if the state machine itself thinks we are disconnected
        if self.state_machine.context.current_state == "CONNECTION_LOST":
            return True

        image = self.state_machine.screen_capture.capture()
        if image is None:
            logger.warning("ReconnectAction.can_execute: screenshot failed")
            return False

        return self._is_disconnect_screen(image)

    def execute(self) -> bool:
        """Tap the reconnect button and verify we are back in game."""
        if self.state_machine is None:
            self.on_failure("StateMachine not available")
            return False
        if self.state_machine.screen_capture is None:
            self.on_failure("ScreenCapture not available")
            return False
        if self.state_machine.pc_input is None:
            self.on_failure("PCInput not available")
            return False

        for attempt in range(1, self.max_tap_attempts + 1):
            logger.info(f"Reconnect attempt {attempt}/{self.max_tap_attempts}")

            image = self.state_machine.screen_capture.capture()
            if image is None:
                logger.warning("Failed to capture screen for reconnect")
                time.sleep(1)
                continue

            # Find reconnect button
            button_center = self._find_reconnect_button(image)
            if button_center is None:
                logger.warning("Reconnect button not found, trying center fallback")
                h, w = image.shape[:2]
                button_center = (w // 2, int(h * 0.65))

            x, y = button_center
            logger.info(f"Tapping reconnect button at ({x}, {y})")
            self.state_machine.pc_input.tap(x, y)

            # Wait for game to reload
            time.sleep(self.post_tap_wait_seconds)

            # Verify we are reconnected
            if self._verify_reconnected():
                self.on_success()
                return True

            # Short back-off before next attempt
            time.sleep(2)

        self.on_failure("Max reconnect attempts reached")
        return False

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _is_disconnect_screen(self, image: np.ndarray) -> bool:
        """Return True if the image looks like a disconnect popup."""
        # 1. Try OCR-based detection
        if self.state_machine is not None and self.state_machine.ocr_engine is not None:
            try:
                results = self.state_machine.ocr_engine.read(image)
                for res in results:
                    text_lower = res.text.lower()
                    if any(kw in text_lower for kw in self.DISCONNECT_KEYWORDS):
                        logger.debug(f"Disconnect keyword detected: '{res.text}'")
                        return True
            except Exception as e:
                logger.warning(f"OCR failed in disconnect detection: {e}")

        # 2. Fallback: simple colour heuristic
        # Disconnect popups usually have a dark semi-transparent overlay
        # and a central dialog box.
        return self._detect_by_color_heuristic(image)

    def _detect_by_color_heuristic(self, image: np.ndarray) -> bool:
        """Rough heuristic: look for a dark uniform region in the centre."""
        h, w = image.shape[:2]
        # Focus on central area where popup usually sits
        y1, y2 = int(h * 0.25), int(h * 0.75)
        x1, x2 = int(w * 0.15), int(w * 0.85)
        roi = image[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_brightness = gray.mean()
        std_brightness = gray.std()
        # Popup overlay is dark (low mean) and fairly uniform (low std)
        is_dark = mean_brightness < 90
        is_uniform = std_brightness < 60
        logger.debug(
            f"Disconnect heuristic: mean={mean_brightness:.1f}, std={std_brightness:.1f}"
        )
        return is_dark and is_uniform

    def _find_reconnect_button(
        self, image: np.ndarray
    ) -> Optional[Tuple[int, int]]:
        """Find the centre of the reconnect / retry / ok button.
        
        Only considers buttons in the central-lower area of the screen
        to avoid tapping on edge text/watermarks.
        """
        if self.state_machine is None or self.state_machine.ocr_engine is None:
            return None

        h, w = image.shape[:2]
        # Valid button region: center horizontally, lower half vertically
        min_x, max_x = int(w * 0.20), int(w * 0.80)
        min_y, max_y = int(h * 0.45), int(h * 0.85)

        try:
            results = self.state_machine.ocr_engine.read(image)
            for res in results:
                text_lower = res.text.lower()
                if any(kw in text_lower for kw in self.BUTTON_KEYWORDS):
                    x1, y1, x2, y2 = res.bbox
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    # Ignore if outside valid button region
                    if not (min_x <= cx <= max_x and min_y <= cy <= max_y):
                        logger.debug(f"Ignoring '{res.text}' at ({cx}, {cy}) – outside button region")
                        continue
                    logger.debug(f"Found button '{res.text}' at ({cx}, {cy})")
                    return (cx, cy)
        except Exception as e:
            logger.warning(f"OCR failed in button search: {e}")

        return None

    def _verify_reconnected(self) -> bool:
        """Capture a new screenshot and confirm disconnect screen is gone."""
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        still_disconnected = self._is_disconnect_screen(image)
        if still_disconnected:
            logger.info("Still on disconnect screen after tap")
            return False

        logger.info("Disconnect screen cleared – reconnect successful")
        return True
