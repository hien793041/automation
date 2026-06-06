"""Dynamic combo action that runs a user-defined sequence of actions."""

import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
from loguru import logger

from rokbot.actions.action_factory import ActionFactory
from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class DynamicComboAction(BaseAction):
    """Execute a sequence of actions defined by the user in combos.yaml."""

    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)

    def __init__(
        self,
        config: BotConfig,
        state_machine: Optional["StateMachine"] = None,
        combo_name: str = "dynamic_combo",
        action_sequence: Optional[List[str]] = None,
    ):
        super().__init__(config, state_machine)
        self.combo_name = combo_name
        self.action_sequence = action_sequence or []
        self._pending_action_name: Optional[str] = None
        self._pending_action_instance: Optional[BaseAction] = None
        self._city_matcher = TemplateMatcher(
            templates_dir=Path("data/templates"),
            threshold=0.80,
        )

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

    def _ensure_in_city(self, image: np.ndarray) -> bool:
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            return True

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            best = max(enter_matches, key=lambda m: m.confidence)
            bx1, by1, bx2, by2 = best.bbox
            cx = roi_x1 + random.randint(bx1, max(bx1, bx2 - 1))
            cy = roi_y1 + random.randint(by1, max(by1, by2 - 1))
            logger.info(f"[{self.combo_name}] In world — entering city at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(1.0, 3.0))
            return True

        logger.warning(f"[{self.combo_name}] Could not determine city/world state")
        return False

    def _ensure_in_world(self, image: np.ndarray) -> bool:
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            return True

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            best = max(in_city_matches, key=lambda m: m.confidence)
            bx1, by1, bx2, by2 = best.bbox
            cx = roi_x1 + random.randint(bx1, max(bx1, bx2 - 1))
            cy = roi_y1 + random.randint(by1, max(by1, by2 - 1))
            logger.info(f"[{self.combo_name}] In city — switching to world map at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(1.0, 3.0))
            return True

        logger.warning(f"[{self.combo_name}] Could not determine city/world state")
        return False

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self._pending_action_name = None
        self._pending_action_instance = None

        for action_name in self.action_sequence:
            action = ActionFactory.create(action_name, self.config, self.state_machine)
            if action is None:
                continue
            try:
                if action.can_execute():
                    self._pending_action_name = action_name
                    self._pending_action_instance = action
                    logger.debug(f"[{self.combo_name}] {action_name} can_execute=True")
                    return True
            except Exception as e:
                logger.warning(f"[{self.combo_name}] {action_name} can_execute failed: {e}")

        logger.debug(f"[{self.combo_name}] No sub-action available")
        return False

    def execute(self) -> bool:
        if self.state_machine is None:
            self.on_failure("StateMachine not available")
            return False

        if self._pending_action_instance is None:
            # Re-evaluate if pending was lost
            if not self.can_execute():
                logger.info(f"[{self.combo_name}] No action available")
                return False

        action = self._pending_action_instance
        action_name = self._pending_action_name
        if action is None:
            return False

        # City/world transition helpers based on action type
        world_actions = {"barbarian_attack", "scout_cave_high"}
        city_actions = {"scout", "train_troops", "scout_cave_low", "combo_scout_train"}
        no_map_check_actions = {"villager_help", "alliance_help", "barbarian_attack"}

        if action_name in city_actions or action_name in world_actions:
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
            if image is not None:
                city_state = self._detect_city_state(image)
                if action_name in city_actions and city_state == "in_world":
                    logger.info(f"[{self.combo_name}] City action '{action_name}' pending but in world — entering city")
                    if not self._ensure_in_city(image):
                        logger.warning(f"[{self.combo_name}] Failed to enter city")
                        return False
                    time.sleep(random.uniform(1.5, 2.5))
                elif action_name in world_actions and city_state == "in_city":
                    logger.info(f"[{self.combo_name}] World action '{action_name}' pending but in city — switching to world")
                    if not self._ensure_in_world(image):
                        logger.warning(f"[{self.combo_name}] Failed to enter world")
                        return False
                    time.sleep(random.uniform(1.0, 2.0))
                elif city_state == "unknown":
                    logger.warning(f"[{self.combo_name}] Unknown city/world state — retrying in 1s")
                    time.sleep(1.0)
                    self.state_machine.pc_input.move_to_safe_zone()
                    image = self.state_machine.screen_capture.capture()
                    if image is not None:
                        city_state = self._detect_city_state(image)
                    if city_state == "unknown":
                        logger.warning(f"[{self.combo_name}] Still unknown — pressing ESC")
                        self.state_machine.pc_input.key_back()
                        time.sleep(random.uniform(1.0, 2.0))
                        return False
                    elif action_name in city_actions and city_state == "in_world":
                        logger.info(f"[{self.combo_name}] City action '{action_name}' pending but in world after retry — entering city")
                        if not self._ensure_in_city(image):
                            logger.warning(f"[{self.combo_name}] Failed to enter city")
                            return False
                        time.sleep(random.uniform(1.5, 2.5))
                    elif action_name in world_actions and city_state == "in_city":
                        logger.info(f"[{self.combo_name}] World action '{action_name}' pending but in city after retry — switching to world")
                        if not self._ensure_in_world(image):
                            logger.warning(f"[{self.combo_name}] Failed to enter world")
                            return False
                        time.sleep(random.uniform(1.0, 2.0))

        logger.info(f"[{self.combo_name}] Running '{action_name}'")
        try:
            success = action.execute()
            if success:
                action.on_success()
                return True
            else:
                action.on_failure(f"{action_name} returned False in combo")
                return False
            raise
        except Exception as e:
            logger.exception(f"[{self.combo_name}] {action_name} failed: {e}")
            action.on_failure(str(e))
            return False
