"""Reconnect action for handling connection lost / disconnect."""

import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class ReconnectAction(BaseAction):
    """Action to reconnect when the game loses connection."""

    TEMPLATES_DIR = Path("data/templates")
    RECONNECT_TEMPLATE = "reconnect"

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self._matcher = TemplateMatcher(
            templates_dir=self.TEMPLATES_DIR,
            threshold=0.75,
        )

    def _random_point_in_bbox(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        x1, y1, x2, y2 = bbox
        px = random.randint(x1, max(x1, x2 - 1))
        py = random.randint(y1, max(y1, y2 - 1))
        return (px, py)

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        matches = self._matcher.match(image, template_name=self.RECONNECT_TEMPLATE, threshold=0.75)
        if matches:
            best = max(matches, key=lambda m: m.confidence)
            logger.info(f"[Reconnect] {self.RECONNECT_TEMPLATE} FOUND at {best.center} conf={best.confidence:.2f}")
            return True

        logger.debug("[Reconnect] reconnect not found")
        return False

    def execute(self) -> bool:
        if self.state_machine is None:
            self.on_failure("StateMachine not available")
            return False
        if self.state_machine.screen_capture is None:
            self.on_failure("ScreenCapture not available")
            return False
        if self.state_machine.pc_input is None:
            self.on_failure("PCInput not available")
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        matches = self._matcher.match(image, template_name=self.RECONNECT_TEMPLATE, threshold=0.75)
        if not matches:
            logger.info("[Reconnect] reconnect disappeared")
            return False

        btn = max(matches, key=lambda m: m.confidence)
        rx, ry = self._random_point_in_bbox(btn.bbox)
        logger.info(f"[Reconnect] Tapping reconnect at ({rx}, {ry})")
        self.state_machine.pc_input.tap(rx, ry)
        time.sleep(random.uniform(3.0, 5.0))  # wait for game to reload
        return True
