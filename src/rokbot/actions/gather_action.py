"""Gather action for collecting resources on the world map."""

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.utils.map_navigation import MapNavigationMixin
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class GatherAction(BaseAction, MapNavigationMixin):
    """Action to gather resources on the world map."""

    TEMPLATES_DIR = Path("data/templates/gather")
    SHARED_TEMPLATES_DIR = Path("data/templates")
    TROOP_TEMPLATES_DIR = Path("data/templates/shared/troops")

    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)
    # RESOURCE_ICONS = ["corn_icon", "wood_icon", "stone_icon", "gold_icon"]
    RESOURCE_ICONS = ["corn_icon", "wood_icon", "stone_icon"]

    # Stop gathering when this many troops are already active
    MAX_ACTIVE_TROOPS = 4
    TROOP_STATUS_TEMPLATES = ["gathering", "backing", "moving", "building", "attacking", "attacking1"]

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        # MAX_ACTIVE_TROOPS is intentionally hardcoded to avoid confusion with
        # config overrides. Adjust the class constant above if needed.
        self._matcher = TemplateMatcher(
            templates_dir=self.TEMPLATES_DIR,
            threshold=0.75,
        )
        self._city_matcher = TemplateMatcher(
            templates_dir=self.SHARED_TEMPLATES_DIR,
            threshold=0.80,
        )
        self._troop_matcher = TemplateMatcher(
            templates_dir=self.TROOP_TEMPLATES_DIR,
            threshold=0.75,
        )

    def _count_active_troops(self, image: np.ndarray) -> int:
        """Count gathering/backing/moving troop icons on the world map."""
        total = 0
        for tpl_name in self.TROOP_STATUS_TEMPLATES:
            matches = self._troop_matcher.match(
                image, template_name=tpl_name, threshold=0.75, max_matches=10
            )
            count = len(matches)
            if count:
                logger.debug(f"[Gather] Found {count} '{tpl_name}' icon(s)")
                total += count
        if total:
            logger.info(f"[Gather] Active troop count = {total}")
        return total

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        # Count active troop icons (gathering/backing/moving/building)
        active_count = self._count_active_troops(image)
        if active_count >= self.MAX_ACTIVE_TROOPS:
            logger.info(f"[Gather] Active troops ({active_count}) >= max ({self.MAX_ACTIVE_TROOPS}) — stopping")
            return False

        city_state = self._detect_city_state(image)
        if city_state == "unknown":
            logger.debug("[Gather] can_execute: city state unknown")
            return False

        if city_state == "in_city":
            logger.info("[Gather] In city — will switch to world map in execute()")
            return True

        # Need Find button visible on world map
        find_matches = self._matcher.match(image, template_name="world_find_btn", threshold=0.75)
        if not find_matches:
            logger.debug("[Gather] can_execute: world_find_btn not found")
            return False

        logger.debug("[Gather] can_execute: ready")
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

        # Capture initial screen
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        # Ensure we are in world view
        city_state = self._detect_city_state(image)
        if city_state == "in_city":
            logger.info("[Gather] In city — switching to world map")
            if not self._ensure_in_world(image):
                self.on_failure("Could not switch to world view")
                return False
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
        elif city_state == "unknown":
            logger.warning("[Gather] Unknown city/world state — retrying after delay")
            self.human_delay("decision_time", fallback_seconds=1.0)
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
            if image is not None:
                city_state = self._detect_city_state(image)
            if city_state == "unknown":
                logger.warning("[Gather] Still unknown — pressing ESC")
                self.state_machine.pc_input.key_back()
                self.human_delay("post_error_wait", fallback_seconds=1.5)
                self.on_failure("Could not determine city/world state")
                return False
            elif city_state == "in_city":
                if not self._ensure_in_world(image):
                    self.on_failure("Could not switch to world view")
                    return False
                self.state_machine.pc_input.move_to_safe_zone()
                image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed after world transition")
            return False

        # Re-check active troop count after ensuring world view
        active_count = self._count_active_troops(image)
        if active_count >= self.MAX_ACTIVE_TROOPS:
            logger.info(f"[Gather] Active troops ({active_count}) >= max ({self.MAX_ACTIVE_TROOPS}) — stopping")
            return False

        # 1. Tap "Find" button on world map
        find_matches = self._matcher.match(image, template_name="world_find_btn", threshold=0.75)
        if not find_matches:
            logger.info("[Gather] world_find_btn not found")
            return False
        find_btn = max(find_matches, key=lambda m: m.confidence)
        fx, fy = self.random_point_in_bbox(find_btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[Gather] Step 1/6: Tapping 'Find' at ({fx}, {fy})")
        self.state_machine.pc_input.tap(fx, fy)
        self.human_delay("menu_wait", fallback_seconds=1.5)

        # 2. Select resource type (corn / stone / wood)
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        resource_image = self.state_machine.screen_capture.capture()
        if resource_image is None:
            return False

        # Find all visible resource types and pick one.
        # Humanization: occasionally change mind and pick the second-best option
        # instead of the highest-confidence one, simulating a player hesitating.
        available_resources = []
        for name in self.RESOURCE_ICONS:
            res_matches = self._matcher.match(resource_image, template_name=name, threshold=0.75)
            if res_matches:
                best = max(res_matches, key=lambda m: m.confidence)
                available_resources.append((name, best))
                logger.debug(f"[Gather] Found '{name}' conf={best.confidence:.2f} at {best.center}")

        if not available_resources:
            logger.info("[Gather] No resource icon found")
            return False

        # Sort by confidence so the first entry is the "obvious" choice.
        available_resources.sort(key=lambda x: x[1].confidence, reverse=True)
        chosen_name, resource_match = available_resources[0]

        # Change-of-mind: if multiple resources are visible, sometimes switch to
        # another one. Add a short hesitation pause before deciding.
        if len(available_resources) > 1:
            if self._decision is not None and self._decision.change_mind():
                self.human_delay("decision_time", fallback_seconds=0.6)
                alt_name, alt_match = available_resources[1]
                chosen_name = alt_name
                resource_match = alt_match
                logger.info(
                    f"[Gather] Step 2/6: Change of mind — switching from "
                    f"'{available_resources[0][0]}' to '{chosen_name}' "
                    f"conf={resource_match.confidence:.2f}"
                )
            else:
                logger.info(
                    f"[Gather] Step 2/6: Found '{chosen_name}' conf={resource_match.confidence:.2f}"
                )
        else:
            logger.info(
                f"[Gather] Step 2/6: Found '{chosen_name}' conf={resource_match.confidence:.2f}"
            )

        rx, ry = self.random_point_in_bbox(resource_match.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[Gather] Tapping '{chosen_name}' at ({rx}, {ry})")
        self.state_machine.pc_input.tap(rx, ry)
        self.human_delay("menu_wait", fallback_seconds=1.5)

        # 3. Tap "Find" in menu
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        menu_image = self.state_machine.screen_capture.capture()
        if menu_image is None:
            return False
        menu_find_matches = self._matcher.match(menu_image, template_name="menu_find_btn", threshold=0.75)
        if not menu_find_matches:
            logger.info("[Gather] menu_find_btn not found")
            return False
        menu_find_btn = max(menu_find_matches, key=lambda m: m.confidence)
        mfx, mfy = self.random_point_in_bbox(menu_find_btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[Gather] Step 3/6: Tapping 'Find' in menu at ({mfx}, {mfy})")
        self.state_machine.pc_input.tap(mfx, mfy)
        self.human_delay("menu_wait", fallback_seconds=2.0)

        # 4. Tap Gather button
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        gather_image = self.state_machine.screen_capture.capture()
        if gather_image is None:
            return False
        gather_matches = self._matcher.match(gather_image, template_name="gather_btn", threshold=0.75)
        if not gather_matches:
            logger.info("[Gather] gather_btn not found")
            return False
        gather_btn = max(gather_matches, key=lambda m: m.confidence)
        gx, gy = self.random_point_in_bbox(gather_btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[Gather] Step 4/6: Tapping 'Gather' at ({gx}, {gy})")
        self.state_machine.pc_input.tap(gx, gy)
        self.human_delay("click_interval", fallback_seconds=1.5)

        # 5. Tap New Troop
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        new_troop_image = self.state_machine.screen_capture.capture()
        if new_troop_image is None:
            return False
        new_matches = self._matcher.match(new_troop_image, template_name="new_troop", threshold=0.75)
        if not new_matches:
            logger.info("[Gather] new_troop not found")
            return False
        new_btn = max(new_matches, key=lambda m: m.confidence)
        nx, ny = self.random_point_in_bbox(new_btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[Gather] Step 5/6: Tapping 'New Troop' at ({nx}, {ny})")
        self.state_machine.pc_input.tap(nx, ny)
        self.human_delay("click_interval", fallback_seconds=1.5)

        # 6. Tap Send Troop
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        send_image = self.state_machine.screen_capture.capture()
        if send_image is None:
            return False
        send_matches = self._matcher.match(send_image, template_name="send_troop", threshold=0.75)
        if not send_matches:
            logger.info("[Gather] send_troop not found")
            return False
        send_btn = max(send_matches, key=lambda m: m.confidence)
        sx, sy = self.random_point_in_bbox(send_btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[Gather] Step 6/6: Tapping 'Send Troop' at ({sx}, {sy})")
        self.state_machine.pc_input.tap(sx, sy)
        self.human_delay("click_interval", fallback_seconds=1.5)
        return True
