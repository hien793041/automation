"""Screen capture via ADB screencap and optional scrcpy streaming."""

import io
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger

from rokbot.core.config import EmulatorConfig


class ScreenCapture:
    """Captures emulator screenshots."""

    def __init__(self, config: EmulatorConfig):
        self.config = config
        self.device_serial = config.device_serial

    def _adb_cmd(self, cmd: list) -> list:
        """Build adb command with optional device serial."""
        base = ["adb"]
        if self.device_serial:
            base += ["-s", self.device_serial]
        return base + cmd

    def capture(self) -> Optional[np.ndarray]:
        """Capture screenshot via adb and return as numpy array."""
        try:
            result = subprocess.run(
                self._adb_cmd(["shell", "screencap", "-p"]),
                capture_output=True,
                check=True,
            )
            # ADB on Windows uses CRLF; normalize for PNG parsing
            png_data = result.stdout.replace(b"\r\n", b"\n")
            image = cv2.imdecode(np.frombuffer(png_data, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                logger.error("Failed to decode screenshot from ADB")
                return None
            logger.debug(f"Screenshot captured: {image.shape}")
            return image
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB screencap failed: {e}")
            return None
        except FileNotFoundError:
            logger.error("adb not found in PATH")
            return None

    def save_screenshot(self, path: Path) -> bool:
        """Capture and save screenshot to file."""
        image = self.capture()
        if image is None:
            return False
        cv2.imwrite(str(path), image)
        logger.info(f"Screenshot saved to {path}")
        return True
