"""Barbarian attack action for farming resources and experience."""

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


class BarbarianAttackAction(BaseAction):
    """Action to attack barbarians on the world map."""

    TEMPLATES_DIR = Path("data/templates/barbarian")
    SHARED_TEMPLATES_DIR = Path("data/templates")

    # Bottom-right corner ROI where city/map toggle icon lives
    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)
    TROOP_AVAIL_TEMPLATES = ["troops_available", "troops_available1"]

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self._matcher = TemplateMatcher(
            templates_dir=self.TEMPLATES_DIR,
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
        self._last_success_time: Optional[float] = None
        self._cooldown_seconds = 10.0

    def _human_delay(self, distribution: str = "click_interval", fallback_seconds: float = 0.5) -> None:
        if self._humanization_enabled:
            delay_ms = self._timing.sample(distribution)
            time.sleep(max(0.05, delay_ms / 1000.0))
        else:
            time.sleep(fallback_seconds)

    def _random_point_in_bbox(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        x1, y1, x2, y2 = bbox
        px = random.randint(x1, max(x1, x2 - 1))
        py = random.randint(y1, max(y1, y2 - 1))
        return (px, py)

    def _roi_from_ratio(self, image: np.ndarray, ratio: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
        h, w = image.shape[:2]
        x1 = int(w * ratio[0])
        y1 = int(h * ratio[1])
        x2 = int(w * ratio[2])
        y2 = int(h * ratio[3])
        return (x1, y1, x2, y2)

    def _detect_city_state(self, image: np.ndarray) -> str:
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            return "in_city"

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            return "in_world"

        return "unknown"

    def _ensure_in_world(self, image: np.ndarray) -> bool:
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            logger.debug("Already in world view")
            return True

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            best = max(in_city_matches, key=lambda m: m.confidence)
            bx1, by1, bx2, by2 = best.bbox
            cx = roi_x1 + random.randint(bx1, max(bx1, bx2 - 1))
            cy = roi_y1 + random.randint(by1, max(by1, by2 - 1))
            logger.info(f"[Barbarian] In city — switching to world map at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(1.0, 3.0))
            return True

        logger.warning("Could not determine city/world state")
        return False

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        city_state = self._detect_city_state(image)
        if city_state == "unknown":
            logger.debug("[Barbarian] can_execute: city state unknown")
            return False

        if city_state == "in_city":
            logger.info("[Barbarian] In city — will switch to world map in execute()")
            return True

        # In world — check troops_available first
        avail_matches = self._matcher.match(image, template_name="troops_available", threshold=0.80)
        if not avail_matches:
            logger.debug("[Barbarian] can_execute: no troops available")
            return False

        # Check Find button visible
        find_matches = self._matcher.match(image, template_name="world_find_btn", threshold=0.80)
        if not find_matches:
            logger.debug("[Barbarian] can_execute: world_find_btn not found")
            return False

        logger.debug("[Barbarian] can_execute: ready")
        return True

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

        # Cooldown check
        if self._last_success_time is not None:
            elapsed = time.time() - self._last_success_time
            if elapsed < self._cooldown_seconds:
                logger.debug(f"Barbarian attack cooldown: {self._cooldown_seconds - elapsed:.0f}s remaining")
                return False

        # 0. Verify troops are available FIRST (works in both city and world)
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        avail_found = False
        avail_name = None
        for tpl in self.TROOP_AVAIL_TEMPLATES:
            avail_matches = self._matcher.match(image, template_name=tpl, threshold=0.80)
            if avail_matches:
                avail_btn = max(avail_matches, key=lambda m: m.confidence)
                avail_found = True
                avail_name = tpl
                logger.info(f"[Barbarian] Step 0/7: {tpl} confirmed conf={avail_btn.confidence:.2f}")
                break
        if not avail_found:
            logger.info("[Barbarian] Step 0/7: no troops available — passing")
            return False

        # Ensure we are in world view
        city_state = self._detect_city_state(image)
        if city_state == "in_city":
            logger.info("[Barbarian] In city — switching to world map")
            if not self._ensure_in_world(image):
                self.on_failure("Could not switch to world view")
                return False
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
        elif city_state == "unknown":
            self.on_failure("Could not determine city/world state")
            return False
        if image is None:
            self.on_failure("Screenshot failed after world transition")
            return False

        # 1. Tap "Find" button on world map
        find_matches = self._matcher.match(image, template_name="world_find_btn", threshold=0.80)
        if not find_matches:
            logger.debug("Find button not found on world map")
            return False
        find_btn = max(find_matches, key=lambda m: m.confidence)
        fx, fy = self._random_point_in_bbox(find_btn.bbox)
        logger.info(f"[Barbarian] Step 1/7: Tapping 'Find' on world map at ({fx}, {fy})")
        self.state_machine.pc_input.tap(fx, fy)
        time.sleep(random.uniform(1.0, 3.0))

        # 2. Select barbarian from the menu
        # self.state_machine.pc_input.move_to_safe_zone()
        # menu_image = self.state_machine.screen_capture.capture()
        # if menu_image is None:
        #     return False
        # select_matches = self._matcher.match(menu_image, template_name="select_barbarian", threshold=0.80)
        # if not select_matches:
        #     logger.debug("Barbarian select option not found")
        #     return False
        # select_btn = max(select_matches, key=lambda m: m.confidence)
        # sx, sy = self._random_point_in_bbox(select_btn.bbox)
        # logger.info(f"[Barbarian] Step 2/7: Tapping 'Select Barbarian' at ({sx}, {sy})")
        # self.state_machine.pc_input.tap(sx, sy)
        # time.sleep(random.uniform(1.0, 3.0))

        # 3. Tap "Find" button inside the menu to search nearby barbarians
        self.state_machine.pc_input.move_to_safe_zone()
        search_image = self.state_machine.screen_capture.capture()
        if search_image is None:
            return False
        menu_find_matches = self._matcher.match(search_image, template_name="menu_find_btn", threshold=0.80)
        if not menu_find_matches:
            logger.debug("Menu Find button not found")
            return False
        menu_find_btn = max(menu_find_matches, key=lambda m: m.confidence)
        mfx, mfy = self._random_point_in_bbox(menu_find_btn.bbox)
        logger.info(f"[Barbarian] Step 3/7: Tapping 'Find' in menu at ({mfx}, {mfy})")
        self.state_machine.pc_input.tap(mfx, mfy)
        time.sleep(random.uniform(1.8, 2.2))

        # 4. Tap Attack button on the barbarian popup
        self.state_machine.pc_input.move_to_safe_zone()
        attack_image = self.state_machine.screen_capture.capture()
        if attack_image is None:
            return False
        attack_matches = self._matcher.match(attack_image, template_name="attack_button", threshold=0.80)
        if not attack_matches:
            logger.debug("Attack button not found")
            return False
        attack_btn = max(attack_matches, key=lambda m: m.confidence)
        ax, ay = self._random_point_in_bbox(attack_btn.bbox)
        logger.info(f"[Barbarian] Step 4/7: Tapping 'Attack' at ({ax}, {ay})")
        self.state_machine.pc_input.tap(ax, ay)
        time.sleep(random.uniform(1.0, 3.0))

        # 5. Choose troop attack
        self.state_machine.pc_input.move_to_safe_zone()
        choose_image = self.state_machine.screen_capture.capture()
        if choose_image is None:
            return False
        choose_matches = self._matcher.match(choose_image, template_name="choose_troop_attack", threshold=0.80)
        if not choose_matches:
            logger.info("[Barbarian] choose_troop_attack not found")
            return False
        choose_btn = max(choose_matches, key=lambda m: m.confidence)
        chx, chy = self._random_point_in_bbox(choose_btn.bbox)
        logger.info(f"[Barbarian] Step 5/7: Tapping 'Choose Troop Attack' at ({chx}, {chy})")
        self.state_machine.pc_input.tap(chx, chy)
        time.sleep(random.uniform(1.0, 3.0))

        # 6. Use existing troops (pre-configured) — check both templates
        self.state_machine.pc_input.move_to_safe_zone()
        troop_image = self.state_machine.screen_capture.capture()
        if troop_image is None:
            return False

        existing_btn = None
        existing_name = None
        for tpl in ["existing_troops", "existing_troops1"]:
            matches = self._matcher.match(troop_image, template_name=tpl, threshold=0.80)
            if matches:
                existing_btn = max(matches, key=lambda m: m.confidence)
                existing_name = tpl
                break

        if existing_btn is not None:
            ex, ey = self._random_point_in_bbox(existing_btn.bbox)
            logger.info(f"[Barbarian] Step 6/7: Tapping '{existing_name}' at ({ex}, {ey})")
            self.state_machine.pc_input.tap(ex, ey)
            time.sleep(random.uniform(1.0, 3.0))
            return True

        logger.info("[Barbarian] existing_troops / existing_troops1 not found")
        return False

    def on_success(self) -> None:
        super().on_success()
        self._last_success_time = time.time()
