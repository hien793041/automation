"""Clone farm action for managing multiple farm accounts simultaneously.

This action is intentionally isolated from the main account focus flow. It
rotates through a configurable list of clone emulator windows (e.g. LDPlayer
instances named "HIN ONE" .. "HIN FOUR") and runs a short gather sequence on
each one:

    in the world -> find_btn -> find_resource -> gather_btn -> new_troop -> send_troop

Because every clone has its own game window, the action creates a dedicated
``WindowManager``, ``WindowCapture`` and ``PCInput`` for the clone it is
currently handling. It does NOT reuse ``state_machine.pc_input`` (which targets
the main "Rise of Kingdoms" window) so the main account actions are not
affected.

Recommended usage: run clone_farm in a separate bot process so window focus
jumps between clone emulators only, never interfering with the main account
bot.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.pc_controller.pc_input import PCInput
from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class CloneFarmAction(BaseAction):
    """Farm gathering action for clone accounts running in separate windows."""

    TEMPLATES_DIR = Path("data/templates/clone_farm")
    # Default clone window titles. Override via config/actions.yaml.
    DEFAULT_CLONE_TITLES = [
        "HIN ONE",
        "HIN TWO",
        "HIN THREE",
        "HIN FOUR",
    ]

    DEFAULT_MAX_ACTIVE_TROOPS = 1
    # Count both gathering and backing troops as "busy". Backing means the troop
    # has finished gathering and is currently returning, so we should not send
    # another troop yet.
    TROOP_STATUS_TEMPLATES = ["gathering", "backing"]

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)

        self._clone_titles = self.get_action_config("clone_window_titles", self.DEFAULT_CLONE_TITLES)
        if isinstance(self._clone_titles, str):
            self._clone_titles = [self._clone_titles]

        self._max_active_troops = int(self.get_action_config("max_active_troops", self.DEFAULT_MAX_ACTIVE_TROOPS))
        self._current_clone_index = 0

        self._matcher = TemplateMatcher(
            templates_dir=self.TEMPLATES_DIR,
            threshold=0.75,
        )

    # ------------------------------------------------------------------
    # Per-clone helpers
    # ------------------------------------------------------------------
    def _get_current_clone_title(self) -> Optional[str]:
        if not self._clone_titles:
            return None
        return self._clone_titles[self._current_clone_index % len(self._clone_titles)]

    def _advance_clone_index(self) -> None:
        if self._clone_titles:
            self._current_clone_index = (self._current_clone_index + 1) % len(self._clone_titles)

    def _create_clone_controller(self, window_title: str) -> Optional[Tuple[WindowManager, WindowCapture, PCInput]]:
        """Create a dedicated window manager/capture/input triple for one clone."""
        try:
            wm = WindowManager(window_title_substring=window_title)
            if wm.hwnd is None:
                logger.warning(f"[CloneFarm] Clone window not found: '{window_title}'")
                return None

            capture = WindowCapture(window_manager=wm)

            humanization_config = None
            if self.config is not None:
                humanization_config = getattr(self.config, "humanization", None)

            pc_input = PCInput(
                window_manager=wm,
                humanization_config=humanization_config,
            )
            # Share the StateMachine decision engine if available so fatigue and
            # frustration accumulate consistently across clones.
            if self.state_machine is not None:
                shared_decision = getattr(self.state_machine, "_decision_engine", None)
                if shared_decision is not None:
                    pc_input.share_decision_engine(shared_decision)

            return wm, capture, pc_input
        except Exception as e:
            logger.error(f"[CloneFarm] Failed to create controller for '{window_title}': {e}")
            return None

    def _count_active_troops(self, image: np.ndarray) -> int:
        """Count gathering/backing troop icons on the world map."""
        total = 0
        for tpl_name in self.TROOP_STATUS_TEMPLATES:
            matches = self._matcher.match(image, template_name=tpl_name, threshold=0.75, max_matches=10)
            count = len(matches)
            if count:
                logger.debug(f"[CloneFarm] Found {count} '{tpl_name}' icon(s)")
                total += count
        if total:
            logger.info(f"[CloneFarm] Active troop count = {total}")
        return total

    def _detect_city_state(self, image: np.ndarray) -> str:
        """Detect city/world state using clone-specific templates.

        Returns one of: 'in_city', 'in_world', 'unknown'.
        """
        # Direct full-screen match is enough for the large in_world/in_city icons
        for tpl_name in ["in_world", "in_city"]:
            matches = self._matcher.match(image, template_name=tpl_name, threshold=0.75)
            if matches:
                return "in_world" if tpl_name == "in_world" else "in_city"
        return "unknown"

    def _tap_template(
        self,
        image: np.ndarray,
        template_name: str,
        pc_input: PCInput,
        step_name: str,
        threshold: float = 0.75,
        post_delay_distribution: str = "click_interval",
        post_delay_fallback: float = 1.5,
    ) -> bool:
        """Find a template and tap it. Returns True if found and tapped."""
        matches = self._matcher.match(image, template_name=template_name, threshold=threshold)
        if not matches:
            logger.info(f"[CloneFarm] {step_name}: '{template_name}' not found")
            return False

        btn = max(matches, key=lambda m: m.confidence)
        x, y = self.random_point_in_bbox(btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[CloneFarm] {step_name}: tapping '{template_name}' at ({x}, {y}) conf={btn.confidence:.2f}")
        pc_input.tap(x, y)
        self.human_delay(post_delay_distribution, fallback_seconds=post_delay_fallback)
        return True

    # ------------------------------------------------------------------
    # BaseAction interface
    # ------------------------------------------------------------------
    def can_execute(self) -> bool:
        if self.config is None:
            return False

        # Clone farm only needs its own windows to exist. We check the current
        # target window here so the state machine can skip us when none of the
        # clones are available.
        title = self._get_current_clone_title()
        if title is None:
            return False

        # Lightweight check: does the clone window exist right now?
        try:
            wm = WindowManager(window_title_substring=title)
            if wm.hwnd is None:
                logger.debug(f"[CloneFarm] can_execute: window '{title}' not found")
                self._advance_clone_index()
                return False
        except Exception as e:
            logger.warning(f"[CloneFarm] can_execute error for '{title}': {e}")
            self._advance_clone_index()
            return False

        return True

    def execute(self) -> bool:
        title = self._get_current_clone_title()
        if title is None:
            self.on_failure("No clone window titles configured")
            return False

        logger.info(f"[CloneFarm] Handling clone window: '{title}'")

        controller = self._create_clone_controller(title)
        if controller is None:
            self._advance_clone_index()
            self.on_failure(f"Clone window not available: '{title}'")
            return False

        wm, capture, pc_input = controller

        # Move mouse to safe zone of the clone window so it does not cover UI.
        pc_input.move_to_safe_zone()
        self.pre_action_delay()

        image = capture.capture()
        if image is None:
            self._advance_clone_index()
            self.on_failure(f"Failed to capture clone window '{title}'")
            return False

        # 0. Ensure we are on the world map.
        city_state = self._detect_city_state(image)
        if city_state == "in_city":
            logger.info(f"[CloneFarm] '{title}' in city — switching to world map")
            if not self._tap_template(
                image,
                "in_world",
                pc_input,
                step_name="Switch to world",
                post_delay_fallback=2.0,
            ):
                # Fallback: try Space hotkey through the clone's own input.
                pc_input.press_key("space")
                self.human_delay("transition_wait", fallback_seconds=2.0)

            image = capture.capture()
            if image is None:
                self._advance_clone_index()
                self.on_failure(f"Screenshot failed after world transition on '{title}'")
                return False

            city_state = self._detect_city_state(image)
            if city_state != "in_world":
                self._advance_clone_index()
                self.on_failure(f"Could not switch clone '{title}' to world map")
                return False
        elif city_state == "unknown":
            logger.warning(f"[CloneFarm] '{title}' city/world state unknown — pressing ESC")
            pc_input.key_back()
            self.human_delay("post_error_wait", fallback_seconds=1.5)
            self._advance_clone_index()
            self.on_failure(f"Unknown city/world state for clone '{title}'")
            return False

        # 1. Check available gathering capacity.
        active_count = self._count_active_troops(image)
        if active_count >= self._max_active_troops:
            logger.info(
                f"[CloneFarm] '{title}' active troops ({active_count}) >= max "
                f"({self._max_active_troops}) — skipping, not a failure"
            )
            self._advance_clone_index()
            # Return True so the state machine does not treat "all troops busy"
            # as an action failure / retry condition.
            return True

        # 2. Tap Find button on world map.
        if not self._tap_template(
            image,
            "find_btn",
            pc_input,
            step_name="Step 1/5",
            post_delay_distribution="transition_wait",
            post_delay_fallback=3.0,
        ):
            self._advance_clone_index()
            self.on_failure(f"find_btn not found on '{title}'")
            return False

        # 3. Tap Find Resource (select resource type).
        # Retry a few times because the resource menu can take a moment to appear.
        resource_found = False
        resource_match = None
        for attempt in range(1, 4):
            image = capture.capture()
            if image is None:
                self._advance_clone_index()
                self.on_failure(f"Screenshot failed before find_resource on '{title}'")
                return False

            matches = self._matcher.match(image, template_name="find_resource", threshold=0.75)
            if matches:
                resource_match = max(matches, key=lambda m: m.confidence)
                resource_found = True
                logger.info(
                    f"[CloneFarm] Step 2/5: found 'find_resource' conf={resource_match.confidence:.2f} "
                    f"(attempt {attempt}/3)"
                )
                break

            logger.debug(f"[CloneFarm] find_resource not found (attempt {attempt}/3), waiting...")
            self.human_delay("menu_wait", fallback_seconds=1.5)

        if not resource_found or resource_match is None:
            pc_input.key_back()
            self.human_delay("post_error_wait", fallback_seconds=1.0)
            self._advance_clone_index()
            self.on_failure(f"find_resource not found on '{title}'")
            return False

        rx, ry = self.random_point_in_bbox(resource_match.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[CloneFarm] Step 2/5: tapping 'find_resource' at ({rx}, {ry})")
        pc_input.tap(rx, ry)
        self.human_delay("transition_wait", fallback_seconds=3.0)

        # 4. Tap Gather button.
        image = capture.capture()
        if image is None:
            self._advance_clone_index()
            self.on_failure(f"Screenshot failed before gather_btn on '{title}'")
            return False

        if not self._tap_template(
            image,
            "gather_btn",
            pc_input,
            step_name="Step 3/5",
            post_delay_distribution="menu_wait",
            post_delay_fallback=2.0,
        ):
            pc_input.key_back()
            self.human_delay("post_error_wait", fallback_seconds=1.0)
            self._advance_clone_index()
            self.on_failure(f"gather_btn not found on '{title}'")
            return False

        # 5. Tap New Troop.
        image = capture.capture()
        if image is None:
            self._advance_clone_index()
            self.on_failure(f"Screenshot failed before new_troop on '{title}'")
            return False

        if not self._tap_template(
            image,
            "new_troop",
            pc_input,
            step_name="Step 4/5",
            post_delay_distribution="menu_wait",
            post_delay_fallback=2.0,
        ):
            pc_input.key_back()
            self.human_delay("post_error_wait", fallback_seconds=1.0)
            self._advance_clone_index()
            self.on_failure(f"new_troop not found on '{title}'")
            return False

        # 6. Tap Send Troop.
        image = capture.capture()
        if image is None:
            self._advance_clone_index()
            self.on_failure(f"Screenshot failed before send_troop on '{title}'")
            return False

        if not self._tap_template(
            image,
            "send_troop",
            pc_input,
            step_name="Step 5/5",
            post_delay_distribution="menu_wait",
            post_delay_fallback=2.0,
        ):
            pc_input.key_back()
            self.human_delay("post_error_wait", fallback_seconds=1.0)
            self._advance_clone_index()
            self.on_failure(f"send_troop not found on '{title}'")
            return False

        # Success: move to next clone on the next invocation.
        logger.info(f"[CloneFarm] Successfully sent troop from clone '{title}'")
        self._advance_clone_index()
        self.on_success()
        return True
