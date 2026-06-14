"""Scouting action using template matching."""

import random
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.utils.map_navigation import MapNavigationMixin
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class ScoutAction(BaseAction, MapNavigationMixin):
    """Action to send scouts by tapping the Scout Camp building."""

    SCOUT_TEMPLATES_DIR = Path("data/templates/scout")
    SHARED_TEMPLATES_DIR = Path("data/templates")
    SCOUT_TEMPLATES = ["tham_do", "scout_icon"]  # text bubble, icon
    BUILDING_OFFSET_Y_RATIO = 1.2  # tap below the bubble/icon, roughly building center

    # Bottom-right corner ROI where city/map toggle icon lives
    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self._matcher = TemplateMatcher(
            templates_dir=self.SCOUT_TEMPLATES_DIR,
            threshold=0.80,
        )
        self._city_matcher = TemplateMatcher(
            templates_dir=self.SHARED_TEMPLATES_DIR,
            threshold=0.80,
        )

    def can_execute(self) -> bool:
        """Return True if scout is actionable (in city or can enter city)."""
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        city_state = self._detect_city_state(image)
        if city_state == "unknown":
            logger.warning("[Scout] Unknown city/world state — pressing ESC to dismiss popup")
            self.state_machine.pc_input.key_back()
            self.human_delay("post_error_wait", fallback_seconds=1.5)
            return False

        if city_state == "in_world":
            # We are on world map; execute() will enter city first
            return True

        # city_state == "in_city" — look for scout bubble
        for tpl in self.SCOUT_TEMPLATES:
            matches = self._matcher.match(image, template_name=tpl, threshold=0.80)
            if matches:
                return True
        return False

    def execute(self) -> bool:
        """Tap the Scout Camp building and attempt to send a scout."""
        if self.state_machine is None:
            self.on_failure("StateMachine not available")
            return False
        if self.state_machine.screen_capture is None:
            self.on_failure("ScreenCapture not available")
            return False
        if self.state_machine.pc_input is None:
            self.on_failure("PCInput not available")
            return False

        # 0. Make sure we are in city view
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        city_state = self._detect_city_state(image)
        if city_state == "in_world":
            logger.debug("On world map — entering city first")
            if not self._ensure_in_city(image):
                self.on_failure("Could not enter city view")
                return False
            # Re-capture after transition
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
        elif city_state == "unknown":
            logger.warning("[Scout] Unknown city/world state — retrying after delay")
            self.human_delay("decision_time", fallback_seconds=1.0)
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
            if image is not None:
                city_state = self._detect_city_state(image)
            if city_state == "unknown":
                logger.warning("[Scout] Still unknown — pressing ESC to dismiss popup")
                self.state_machine.pc_input.key_back()
                self.human_delay("post_error_wait", fallback_seconds=1.5)
                self.on_failure("Could not determine city/world state")
                return False
            elif city_state == "in_world":
                logger.debug("On world map after retry — entering city first")
                if not self._ensure_in_city(image):
                    self.on_failure("Could not enter city view")
                    return False
                self.state_machine.pc_input.move_to_safe_zone()
                image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed after city transition")
            return False

        # 1. Find the scout bubble
        match = None
        for tpl in self.SCOUT_TEMPLATES:
            matches = self._matcher.match(image, template_name=tpl, threshold=0.80)
            if matches:
                match = max(matches, key=lambda m: m.confidence)
                logger.debug(f"Found scout indicator: '{tpl}' (conf={match.confidence:.2f})")
                break

        if match is None:
            logger.debug("Scout indicator not found — skipping this cycle")
            return False
        x1, y1, x2, y2 = match.bbox
        cx, cy = match.center
        bubble_h = y2 - y1

        # 2. Tap on the building below the bubble
        building_x = cx + random.randint(-15, 15)
        building_y = int(y2 + bubble_h * self.BUILDING_OFFSET_Y_RATIO) + random.randint(-10, 10)

        logger.info(f"[Scout] Step 1/5: Tapping Scout Camp at ({building_x}, {building_y})")
        self.state_machine.pc_input.tap(building_x, building_y)
        self.human_delay("menu_wait", fallback_seconds=1.0)

        # 3. Tap buttons in the popup sequentially, re-capturing after each tap
        #    because later buttons only appear after earlier ones are pressed.
        # Sequence: scout_button -> scout_send (x2) -> scout_confirm
        popup_sequence = ["scout_button", "scout_send", "scout_send", "scout_confirm"]
        scout_send_count = 0
        for idx, tpl in enumerate(popup_sequence, start=2):
            self.human_delay("reaction_time", fallback_seconds=0.3)
            self.state_machine.pc_input.move_to_safe_zone()
            popup_image = self.state_machine.screen_capture.capture()
            if popup_image is None:
                continue
            btn_matches = self._matcher.match(popup_image, template_name=tpl)
            if btn_matches:
                btn = max(btn_matches, key=lambda m: m.confidence)
                bx, by = self.random_point_in_bbox(btn.bbox, jitter_sigma=1.0, edge_margin=2)
                logger.info(f"[Scout] Step {idx}/5: Tapping '{tpl}' at ({bx}, {by})")
                self.state_machine.pc_input.tap(bx, by)

                # Long delay only for the 2nd scout_send (needs ~1.5s for UI to transition)
                if tpl == "scout_send":
                    scout_send_count += 1
                    if scout_send_count == 1:
                        self.human_delay("menu_wait", fallback_seconds=1.9)
                    else:
                        self.human_delay("click_interval", fallback_seconds=0.5)
                else:
                    self.human_delay("click_interval", fallback_seconds=0.5)
            else:
                # Button not found — try to close popup and restart flow
                close_matches = self._matcher.match(popup_image, template_name="close_popup")
                if close_matches:
                    close_btn = max(close_matches, key=lambda m: m.confidence)
                    close_x, close_y = self.random_point_in_bbox(close_btn.bbox, jitter_sigma=1.0, edge_margin=2)
                    logger.info(f"[Scout] Button '{tpl}' not found — closing popup at ({close_x}, {close_y})")
                    self.state_machine.pc_input.tap(close_x, close_y)
                    self.human_delay("click_interval", fallback_seconds=0.8)
                return False

        # Ensure we end up in city view after scouting (UI may switch to world map)
        self.state_machine.pc_input.move_to_safe_zone()
        self.human_delay("transition_wait", fallback_seconds=1.0)
        final_image = self.state_machine.screen_capture.capture()
        if final_image is not None:
            self._ensure_in_city(final_image)

        self.human_delay("click_interval", fallback_seconds=1.5)
        return True
