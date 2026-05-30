"""Screenshot capture for the ROK PC game window."""

from typing import Optional

import cv2
import numpy as np
import win32gui
import win32ui
from loguru import logger

from rokbot.pc_controller.window_manager import WindowManager


class WindowCapture:
    """Captures screenshots of the game window."""

    def __init__(self, window_manager: WindowManager):
        self.window_manager = window_manager

    def capture(self) -> Optional[np.ndarray]:
        """Capture the game client area and return as BGR numpy array."""
        if not self.window_manager.is_window_valid():
            logger.error("Cannot capture: game window not found")
            return None

        rect = self.window_manager.get_client_rect()
        if rect is None:
            return None

        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        # Bring window to foreground before capture to avoid overlapping windows
        try:
            hwnd = self.window_manager.hwnd
            if not win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            logger.debug(f"Could not bring window to foreground: {e}")

        # Capture via ImageGrab
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            image = np.array(screenshot)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            logger.debug(f"Window captured (ImageGrab fallback): {image.shape}")
            return image
        except Exception as e:
            logger.error(f"Window capture failed: {e}")
            return None

    def save_screenshot(self, path: str) -> bool:
        """Capture and save to disk."""
        image = self.capture()
        if image is None:
            return False
        cv2.imwrite(path, image)
        logger.info(f"Screenshot saved to {path}")
        return True
