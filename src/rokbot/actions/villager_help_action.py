"""Villager help action for accidentally clicked villagers."""

import random
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.utils.map_navigation import MapNavigationMixin
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class VillagerHelpAction(BaseAction, MapNavigationMixin):
    """Tap a villager and confirm to help them."""

    TEMPLATES_DIR = Path("data/templates")
    VILLAGER_TEMPLATE = "dan_lang"
    CONFIRM_TEMPLATE = "confirm_dan_lang"

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self._matcher = TemplateMatcher(
            templates_dir=self.TEMPLATES_DIR,
            threshold=0.75,
        )

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        matches = self._matcher.match(image, template_name=self.VILLAGER_TEMPLATE, threshold=0.75)
        if matches:
            best = max(matches, key=lambda m: m.confidence)
            logger.info(f"[Villager] {self.VILLAGER_TEMPLATE} FOUND at {best.center} conf={best.confidence:.2f}")
            return True

        logger.debug("[Villager] dan_lang not found")
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
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        villager_matches = self._matcher.match(image, template_name=self.VILLAGER_TEMPLATE, threshold=0.75)
        if not villager_matches:
            logger.info("[Villager] dan_lang disappeared")
            return False

        villager = max(villager_matches, key=lambda m: m.confidence)
        bx1, by1, bx2, by2 = villager.bbox
        cx = (bx1 + bx2) // 2
        cy = (by1 + by2) // 2

        # Tap below the villager icon ~100px to select the help option
        offset_y = random.randint(90, 110)
        img_h = image.shape[0]
        tap_y = min(img_h - 1, cy + offset_y)
        logger.info(f"[Villager] Step 1/2: Tapping below villager at ({cx}, {tap_y}) (offset +{offset_y})")
        self.state_machine.pc_input.tap(cx, tap_y)
        self.human_delay("menu_wait", fallback_seconds=1.5)

        # Confirm the action
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        confirm_image = self.state_machine.screen_capture.capture()
        if confirm_image is None:
            return False

        confirm_matches = self._matcher.match(confirm_image, template_name=self.CONFIRM_TEMPLATE, threshold=0.75)
        if confirm_matches:
            confirm_btn = max(confirm_matches, key=lambda m: m.confidence)
            cfx, cfy = self.random_point_in_bbox(confirm_btn.bbox, jitter_sigma=1.0, edge_margin=2)
            logger.info(f"[Villager] Step 2/2: Tapping confirm at ({cfx}, {cfy})")
            self.state_machine.pc_input.tap(cfx, cfy)
            self.human_delay("click_interval", fallback_seconds=1.5)
            return True

        logger.info("[Villager] confirm_dan_lang not found")
        return False
