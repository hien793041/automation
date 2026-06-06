"""Alliance help action using template matching."""

import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class AllianceHelpAction(BaseAction):
    """Action to tap alliance help button when available."""

    TEMPLATES_DIR = Path("data/templates")
    HELP_TEMPLATE = "help_btn"

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self._matcher = TemplateMatcher(
            templates_dir=self.TEMPLATES_DIR,
            threshold=0.75,
        )
        self._pending_bbox: Optional[Tuple[int, int, int, int]] = None

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

        matches = self._matcher.match(image, template_name=self.HELP_TEMPLATE, threshold=0.75)
        if matches:
            best = max(matches, key=lambda m: m.confidence)
            self._pending_bbox = best.bbox
            logger.info(f"[Help] {self.HELP_TEMPLATE} FOUND at {best.center} conf={best.confidence:.2f}")
            return True

        self._pending_bbox = None
        logger.debug("[Help] help_btn not found")
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

        if self._pending_bbox is not None:
            hx, hy = self._random_point_in_bbox(self._pending_bbox)
            logger.info(f"[Help] Tapping help_btn at ({hx}, {hy})")
            self.state_machine.pc_input.tap(hx, hy)
            self._pending_bbox = None
            time.sleep(random.uniform(1.0, 3.0))
            return True

        # Fallback: re-find if pending was lost
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        matches = self._matcher.match(image, template_name=self.HELP_TEMPLATE, threshold=0.75)
        if not matches:
            logger.info("[Help] help_btn disappeared")
            return False

        btn = max(matches, key=lambda m: m.confidence)
        hx, hy = self._random_point_in_bbox(btn.bbox)
        logger.info(f"[Help] Tapping help_btn at ({hx}, {hy})")
        self.state_machine.pc_input.tap(hx, hy)
        time.sleep(random.uniform(1.0, 3.0))
        return True