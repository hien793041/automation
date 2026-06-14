"""Dynamic combo action that runs a user-defined sequence of actions."""

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from loguru import logger

from rokbot.actions.action_factory import ActionFactory
from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.utils.map_navigation import MapNavigationMixin
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class DynamicComboAction(BaseAction, MapNavigationMixin):
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
        self._action_cache: dict[str, BaseAction] = {}
        self._city_matcher = TemplateMatcher(
            templates_dir=Path("data/templates"),
            threshold=0.80,
        )

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self._pending_action_name = None
        self._pending_action_instance = None

        for action_name in self.action_sequence:
            action = self._action_cache.get(action_name)
            if action is None:
                action = ActionFactory.create(action_name, self.config, self.state_machine)
                if action is not None:
                    self._action_cache[action_name] = action
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
            self.pre_action_delay()
            image = self.state_machine.screen_capture.capture()
            if image is not None:
                city_state = self._detect_city_state(image)
                if action_name in city_actions and city_state == "in_world":
                    logger.info(f"[{self.combo_name}] City action '{action_name}' pending but in world — entering city")
                    if not self._ensure_in_city(image):
                        logger.warning(f"[{self.combo_name}] Failed to enter city")
                        return False
                    self.human_delay("transition_wait", fallback_seconds=2.0)
                elif action_name in world_actions and city_state == "in_city":
                    logger.info(f"[{self.combo_name}] World action '{action_name}' pending but in city — switching to world")
                    if not self._ensure_in_world(image):
                        logger.warning(f"[{self.combo_name}] Failed to enter world")
                        return False
                    self.human_delay("transition_wait", fallback_seconds=1.5)
                elif city_state == "unknown":
                    logger.warning(f"[{self.combo_name}] Unknown city/world state — retrying after delay")
                    self.human_delay("decision_time", fallback_seconds=1.0)
                    self.state_machine.pc_input.move_to_safe_zone()
                    image = self.state_machine.screen_capture.capture()
                    if image is not None:
                        city_state = self._detect_city_state(image)
                    if city_state == "unknown":
                        logger.warning(f"[{self.combo_name}] Still unknown — pressing ESC")
                        self.state_machine.pc_input.key_back()
                        self.human_delay("post_error_wait", fallback_seconds=1.5)
                        return False
                    elif action_name in city_actions and city_state == "in_world":
                        logger.info(f"[{self.combo_name}] City action '{action_name}' pending but in world after retry — entering city")
                        if not self._ensure_in_city(image):
                            logger.warning(f"[{self.combo_name}] Failed to enter city")
                            return False
                        self.human_delay("transition_wait", fallback_seconds=2.0)
                    elif action_name in world_actions and city_state == "in_city":
                        logger.info(f"[{self.combo_name}] World action '{action_name}' pending but in city after retry — switching to world")
                        if not self._ensure_in_world(image):
                            logger.warning(f"[{self.combo_name}] Failed to enter world")
                            return False
                        self.human_delay("transition_wait", fallback_seconds=1.5)

        logger.info(f"[{self.combo_name}] Running '{action_name}'")
        try:
            success = action.execute()
            if success:
                action.on_success()
                return True
            else:
                action.on_failure(f"{action_name} returned False in combo")
                return False
        except Exception as e:
            logger.exception(f"[{self.combo_name}] {action_name} failed: {e}")
            action.on_failure(str(e))
            return False
