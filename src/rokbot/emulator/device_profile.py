"""Device fingerprint spoofing configuration."""

import json
from pathlib import Path
from typing import Optional

from loguru import logger


class DeviceProfile:
    """Emulator device fingerprint for anti-detection."""

    def __init__(self, profile_path: Optional[Path] = None):
        self.manufacturer = "samsung"
        self.model = "SM-G988B"
        self.android_version = "11"
        self.api_level = 30
        self.display_resolution = (1080, 2400)
        self.dpi = 420
        self.device_id: Optional[str] = None

        if profile_path and profile_path.exists():
            self.load(profile_path)

    def load(self, path: Path) -> None:
        """Load device profile from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.__dict__.update(data)
        logger.info(f"Loaded device profile from {path}")

    def save(self, path: Path) -> None:
        """Save device profile to JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, indent=2)
        logger.info(f"Saved device profile to {path}")
