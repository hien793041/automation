"""Alliance help action using template matching."""

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.utils.map_navigation import MapNavigationMixin
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class AllianceHelpAction(BaseAction, MapNavigationMixin):
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

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
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
            hx, hy = self.random_point_in_bbox(self._pending_bbox, jitter_sigma=1.0, edge_margin=2)
            logger.info(f"[Help] Tapping help_btn at ({hx}, {hy})")
            self.state_machine.pc_input.tap(hx, hy)
            self._pending_bbox = None
            self.human_delay("click_interval", fallback_seconds=1.5)
            return True

        # Fallback: re-find if pending was lost
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        matches = self._matcher.match(image, template_name=self.HELP_TEMPLATE, threshold=0.75)
        if not matches:
            logger.info("[Help] help_btn disappeared")
            return False

        btn = max(matches, key=lambda m: m.confidence)
        hx, hy = self.random_point_in_bbox(btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[Help] Tapping help_btn at ({hx}, {hy})")
        self.state_machine.pc_input.tap(hx, hy)
        self.human_delay("click_interval", fallback_seconds=1.5)
        return True
