"""Input execution via ADB shell input."""

import time
from typing import List, Tuple

from loguru import logger

from rokbot.emulator.adb_client import ADBClient
from rokbot.humanization.movement_engine import MovementEngine
from rokbot.humanization.timing_engine import TimingEngine


class ADBInput:
    """Execute touch inputs through ADB with humanization."""

    def __init__(
        self,
        adb: ADBClient,
        timing: TimingEngine,
        movement: MovementEngine,
    ):
        self.adb = adb
        self.timing = timing
        self.movement = movement

    def tap(self, x: int, y: int, humanize: bool = True) -> None:
        """Tap at coordinates with optional humanization."""
        if humanize:
            delay = self.timing.reaction_delay()
            time.sleep(delay / 1000.0)
        self.adb.tap(x, y)
        logger.debug(f"Tapped ({x}, {y})")

    def swipe(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        humanize: bool = True,
    ) -> None:
        """Swipe from start to end with humanized path."""
        if humanize:
            path = self.movement.generate_path(start, end)
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                # ADB swipe with short duration between intermediate points
                self.adb.swipe(x1, y1, x2, y2, duration_ms=10)
                time.sleep(0.01)
        else:
            self.adb.swipe(start[0], start[1], end[0], end[1])

    def key_back(self) -> None:
        """Press Android back button."""
        self.adb.keyevent(4)
        logger.debug("Pressed BACK")

    def key_home(self) -> None:
        """Press Android home button."""
        self.adb.keyevent(3)
        logger.debug("Pressed HOME")
