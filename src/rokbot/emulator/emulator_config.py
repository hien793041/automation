"""Emulator settings and configuration models."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EmulatorSettings:
    """Emulator runtime settings."""

    resolution: tuple = (1920, 1080)
    dpi: int = 420
    ram_mb: int = 4096
    cpu_cores: int = 4
    abi: str = "x86_64"
    root_access: bool = False
    gps_location: tuple = field(default_factory=lambda: (10.7769, 106.7009))  # Ho Chi Minh City
