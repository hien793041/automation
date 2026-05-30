"""Scouting action using template matching."""

import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.humanization.timing_engine import TimingEngine
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class ScoutAction(BaseAction):
    """Action to send scouts by tapping the Scout Camp building."""

    SCOUT_TEMPLATES_DIR = Path("data/templates/scout")
    SHARED_TEMPLATES_DIR = Path("data/templates")
    SCOUT_TEMPLATES = ["tham_do", "scout_icon"]  # text bubble, icon
    BUILDING_OFFSET_Y_RATIO = 1.2  # tap below the bubble/icon, roughly building center
    POST_TAP_WAIT = 1.5

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
        self._timing = TimingEngine(
            profile_path=config.humanization.profile_path
            if config.humanization.profile_path and config.humanization.profile_path.exists()
            else None
        )
        self._humanization_enabled = config.humanization.enabled

    def _human_delay(self, distribution: str = "click_interval", fallback_seconds: float = 0.5) -> None:
        """Sleep using humanized timing if enabled, otherwise use fallback."""
        if self._humanization_enabled:
            delay_ms = self._timing.sample(distribution)
            time.sleep(max(0.05, delay_ms / 1000.0))
        else:
            time.sleep(fallback_seconds)

    def _random_point_in_bbox(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """Return a random point inside a bounding box for humanized clicking."""
        x1, y1, x2, y2 = bbox
        px = random.randint(x1, max(x1, x2 - 1))
        py = random.randint(y1, max(y1, y2 - 1))
        return (px, py)

    def _roi_from_ratio(self, image: np.ndarray, ratio: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
        """Convert ratio (x1, y1, x2, y2) to pixel coords."""
        h, w = image.shape[:2]
        x1 = int(w * ratio[0])
        y1 = int(h * ratio[1])
        x2 = int(w * ratio[2])
        y2 = int(h * ratio[3])
        return (x1, y1, x2, y2)

    def _ensure_in_city(self, image: np.ndarray) -> bool:
        """Check if we are in city view. If not, tap the enter-city icon.

        Returns True if we are (or successfully switched to) city view.
        """
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        # 1. Already in city? Look for "Space" / map icon
        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            best = max(in_city_matches, key=lambda m: m.confidence)
            logger.debug(f"Already in city view (in_city_icon conf={best.confidence:.2f})")
            return True

        # 2. Not in city — look for enter-city (castle) icon in same spot
        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            best = max(enter_matches, key=lambda m: m.confidence)
            # Translate back to full-image coords
            bx1, by1, bx2, by2 = best.bbox
            cx = roi_x1 + random.randint(bx1, max(bx1, bx2 - 1))
            cy = roi_y1 + random.randint(by1, max(by1, by2 - 1))
            logger.debug(f"Not in city — tapping enter_city_icon at ({cx}, {cy}) conf={best.confidence:.2f})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(1.0, 3.0))  # Wait for city view transition
            return True

        logger.warning("Could not determine city/world state from bottom-right icon")
        return False

    def _detect_city_state(self, image: np.ndarray) -> str:
        """Detect city/world state from bottom-right icon.

        Returns one of: 'in_city', 'in_world', 'unknown'.
        """
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            best = max(in_city_matches, key=lambda m: m.confidence)
            logger.debug(f"in_city_icon detected (conf={best.confidence:.2f})")
            return "in_city"

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            best = max(enter_matches, key=lambda m: m.confidence)
            logger.debug(f"enter_city_icon detected (conf={best.confidence:.2f})")
            return "in_world"

        return "unknown"

    def can_execute(self) -> bool:
        """Return True if scout is actionable (in city or can enter city)."""
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        city_state = self._detect_city_state(image)
        if city_state == "unknown":
            logger.debug("Cannot determine city/world state — skipping scout")
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
            self.on_failure("Could not determine city/world state")
            return False
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

        # 3. Wait for the scout menu/popup to open
        time.sleep(random.uniform(1.0, 3.0))

        # 4. Tap buttons in the popup sequentially, re-capturing after each tap
        #    because later buttons only appear after earlier ones are pressed.
        # Sequence: scout_button -> scout_send (x2) -> scout_confirm
        popup_sequence = ["scout_button", "scout_send", "scout_send", "scout_confirm"]
        for idx, tpl in enumerate(popup_sequence, start=2):
            time.sleep(random.uniform(1.0, 3.0))  # wait for UI to settle before finding button
            self.state_machine.pc_input.move_to_safe_zone()
            popup_image = self.state_machine.screen_capture.capture()
            if popup_image is None:
                continue
            btn_matches = self._matcher.match(popup_image, template_name=tpl)
            if btn_matches:
                btn = max(btn_matches, key=lambda m: m.confidence)
                bx, by = self._random_point_in_bbox(btn.bbox)
                logger.info(f"[Scout] Step {idx}/5: Tapping '{tpl}' at ({bx}, {by})")
                self.state_machine.pc_input.tap(bx, by)
                time.sleep(random.uniform(1.0, 3.0))  # wait for popup UI to fully transition
            else:
                # Button not found — try to close popup and restart flow
                close_matches = self._matcher.match(popup_image, template_name="close_popup")
                if close_matches:
                    close_btn = max(close_matches, key=lambda m: m.confidence)
                    cx, cy = self._random_point_in_bbox(close_btn.bbox)
                    logger.info(f"[Scout] Button '{tpl}' not found — closing popup at ({cx}, {cy})")
                    self.state_machine.pc_input.tap(cx, cy)
                    time.sleep(random.uniform(1.0, 3.0))
                return False

        # Ensure we end up in city view after scouting (UI may switch to world map)
        self.state_machine.pc_input.move_to_safe_zone()
        final_image = self.state_machine.screen_capture.capture()
        if final_image is not None:
            self._ensure_in_city(final_image)

        time.sleep(random.uniform(1.0, 3.0))  # post-execution delay before next cycle
        return True
