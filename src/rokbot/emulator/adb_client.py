"""ADB wrapper for emulator communication."""

import subprocess
from pathlib import Path
from typing import List, Optional

from loguru import logger


class ADBClient:
    """Minimal ADB client wrapper."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5555, device_serial: Optional[str] = None):
        self.host = host
        self.port = port
        self.device_serial = device_serial

    def _build_cmd(self, args: List[str]) -> List[str]:
        cmd = ["adb"]
        if self.device_serial:
            cmd += ["-s", self.device_serial]
        return cmd + args

    def connect(self) -> bool:
        """Connect to ADB server/device."""
        try:
            result = subprocess.run(self._build_cmd(["connect", f"{self.host}:{self.port}"]), capture_output=True, text=True, check=True)
            logger.info(f"ADB connect: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB connect failed: {e}")
            return False

    def shell(self, command: str) -> str:
        """Run shell command on device."""
        result = subprocess.run(self._build_cmd(["shell", command]), capture_output=True, text=True, check=True)
        return result.stdout

    def tap(self, x: int, y: int) -> None:
        """Tap screen at coordinates."""
        self.shell(f"input tap {x} {y}")
        logger.debug(f"ADB tap ({x}, {y})")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Swipe from (x1,y1) to (x2,y2)."""
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        logger.debug(f"ADB swipe ({x1},{y1}) -> ({x2},{y2}) {duration_ms}ms")

    def keyevent(self, keycode: int) -> None:
        """Send keyevent."""
        self.shell(f"input keyevent {keycode}")

    def screenshot(self) -> bytes:
        """Capture screenshot as PNG bytes."""
        result = subprocess.run(self._build_cmd(["shell", "screencap", "-p"]), capture_output=True, check=True)
        return result.stdout.replace(b"\r\n", b"\n")
