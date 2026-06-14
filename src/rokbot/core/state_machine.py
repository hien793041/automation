"""State machine orchestrator for ROK Bot Engine v2."""

import random
import time
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

import pyautogui
from loguru import logger

from rokbot.actions.action_factory import ActionFactory
from rokbot.core.config import BotConfig
from rokbot.core.exceptions import RecoveryError, StuckError
from rokbot.core.state_context import StateContext
from rokbot.core.state_transitions import TransitionRegistry
from rokbot.humanization.decision_engine import DecisionEngine
from rokbot.humanization.session_manager import SessionManager
from rokbot.humanization.timing_engine import TimingEngine
from rokbot.vision.template_matcher import TemplateMatcher


class BotState(Enum):
    """Canonical bot states."""

    UNKNOWN = auto()
    IDLE = auto()
    NODE_SELECTED = auto()
    TROOP_SELECT = auto()
    MARCHING = auto()
    GATHERING = auto()
    GATHER_COMPLETE = auto()
    WAREHOUSE_FULL = auto()
    CONNECTION_LOST = auto()
    VIP_POPUP = auto()
    CAPTCHA = auto()
    ERROR_RECOVERY = auto()


class StateMachine:
    """Orchestrates bot execution via state transitions."""

    def __init__(
        self,
        config: BotConfig,
        pc_input=None,
        screen_capture=None,
        ocr_engine=None,
    ):
        self.config = config
        self.context = StateContext(max_retries=config.max_retry_attempts)
        self.transitions = TransitionRegistry()
        self._running = False
        self.pc_input = pc_input
        self.screen_capture = screen_capture
        self.ocr_engine = ocr_engine
        self._actions = self._load_actions()
        self._chat_matcher = TemplateMatcher(
            templates_dir=Path("data/templates"),
            threshold=0.75,
        )
        self.context.record_state(BotState.UNKNOWN.name)
        self._session_manager: Optional[SessionManager] = None
        self._decision_engine: Optional[DecisionEngine] = None
        self._timing: Optional[TimingEngine] = None
        self._capture_fail_count = 0
        self._max_capture_failures = 3
        self._action_fail_counts: dict[str, int] = {}
        if config.humanization.enabled:
            self._timing = TimingEngine(
                profile_path=config.humanization.profile_path,
                distributions=config.humanization.timing,
            )
            if config.humanization.schedule_enabled:
                self._session_manager = SessionManager()
                self._session_manager.start_session()
            self._decision_engine = DecisionEngine(
                fatigue_half_life_hours=config.humanization.fatigue_half_life_hours,
                base_distraction_rate=config.humanization.base_distraction_rate,
                base_misclick_rate=config.humanization.base_misclick_rate,
            )
            # Share the cognitive model with PCInput so fatigue/misclick state
            # is consistent across input and action layers.
            if self.pc_input is not None:
                self.pc_input.share_decision_engine(self._decision_engine)
            logger.info("Humanization integrated into StateMachine")

    def _load_actions(self):
        """Load enabled actions from the factory."""
        actions = {}
        for name in self.config.actions.enabled_actions:
            action = ActionFactory.create(name, self.config, self)
            if action:
                actions[name] = action
                logger.info(f"Loaded action: {name}")
        return actions

    def _get_action_priority_order(self) -> List[str]:
        """Return action names sorted by priority (lower number = higher priority)."""
        def get_priority(name: str) -> int:
            return self.config.actions.priorities.get(name, 999)
        return sorted(self._actions.keys(), key=get_priority)

    def start(self) -> None:
        """Start the state machine loop."""
        self._running = True
        logger.info("State machine started")
        self.context.record_state(BotState.UNKNOWN.name)

        while self._running:
            try:
                self._tick()
            except pyautogui.FailSafeException:
                logger.error("PyAutoGUI fail-safe triggered (mouse moved to corner) — stopping immediately")
                self.stop()
                return
            except StuckError as e:
                logger.warning(f"Stuck detected: {e}")
                self._enter_recovery()
            except RecoveryError as e:
                logger.error(f"Recovery failed: {e}")
                self.stop()
            except Exception as e:
                logger.exception(f"Unexpected error in state machine: {e}")
                self._enter_recovery()

            time.sleep(self.config.screenshot_interval_seconds)

    def stop(self) -> None:
        """Stop the state machine loop."""
        self._running = False
        logger.info("State machine stopped")

    def _tick(self) -> None:
        """Single state machine tick."""
        # Abort early if the game window is gone or minimized
        if self.pc_input is not None:
            if not self.pc_input.window_manager.is_window_valid():
                logger.error("Game window not found — stopping state machine")
                self.stop()
                return
            rect = self.pc_input.window_manager.get_client_rect()
            if rect is None or (rect[2] - rect[0]) <= 0 or (rect[3] - rect[1]) <= 0:
                logger.error("Game window has zero size (minimized?) — stopping state machine")
                self.stop()
                return

        current_state = self.context.current_state or BotState.UNKNOWN.name

        # Session / break management
        if self._session_manager and not self._session_manager.should_be_active():
            logger.info("Session manager: outside active hours — sleeping 60s")
            time.sleep(60)
            return

        if self._session_manager and self._session_manager.check_break():
            break_min = self._session_manager.sample_break_minutes()
            logger.info(f"Session manager: taking a break for {break_min:.0f} minutes")
            time.sleep(break_min * 60)
            self._session_manager.start_session()
            return

        # Dismiss blocking overlays (chat, guides, etc.)
        capture_ok = self._dismiss_overlays()
        if not capture_ok:
            self._capture_fail_count += 1
            if self._capture_fail_count >= self._max_capture_failures:
                logger.error(f"Capture failed {self._capture_fail_count} consecutive times — stopping")
                self.stop()
                return
        else:
            self._capture_fail_count = 0

        # Check stuck condition
        if self.context.is_stuck(self.config.stuck_threshold_seconds):
            raise StuckError(f"Stuck in {current_state} for {self.context.time_in_current_state():.0f}s")

        # Cognitive state update
        if self._decision_engine:
            self._decision_engine.update()
            if self._decision_engine.is_distracted():
                delay = self._decision_engine.reaction_time_multiplier() * random.uniform(2, 5)
                logger.debug(f"Decision engine: distracted — adding {delay:.1f}s delay")
                if self._timing:
                    delay = max(delay, self._timing.sample("decision_time") / 1000.0)
                time.sleep(delay)

        # Determine next state (placeholder for vision integration)
        next_state = self._infer_next_state()

        if next_state and next_state != current_state:
            logger.info(f"Transition: {current_state} -> {next_state}")
            self.context.record_transition(current_state, next_state, success=True)
            self.context.record_state(next_state)

        # Evaluate and execute actions by priority
        self._evaluate_and_execute_actions()

    def _evaluate_and_execute_actions(self) -> None:
        """Run through enabled actions in priority order and execute the first available one.

        Each action is retried up to ``max_retry_attempts`` before the state
        machine gives up and stops, so transient UI glitches don't immediately
        kill a long-running session.
        """
        for action_name in self._get_action_priority_order():
            action = self._actions[action_name]
            try:
                if action.can_execute():
                    logger.info(f"Executing action: {action_name}")
                    success = action.execute()
                    if success:
                        action.on_success()
                        self.context.reset_stuck_timer()
                        self._action_fail_counts.pop(action_name, None)
                        # Only run one action per tick
                        break

                    action.on_failure("Execution returned False")
                    fails = self._action_fail_counts.get(action_name, 0) + 1
                    self._action_fail_counts[action_name] = fails
                    logger.warning(
                        f"Action {action_name} failed ({fails}/{self.config.max_retry_attempts})"
                    )
                    if fails >= self.config.max_retry_attempts:
                        logger.error(
                            f"Action {action_name} exceeded max retries — stopping state machine"
                        )
                        self.stop()
                    # Only run one action per tick
                    break
            except Exception as e:
                logger.exception(f"Action {action_name} failed: {e}")
                action.on_failure(str(e))
                fails = self._action_fail_counts.get(action_name, 0) + 1
                self._action_fail_counts[action_name] = fails
                logger.warning(
                    f"Action {action_name} raised exception ({fails}/{self.config.max_retry_attempts})"
                )
                if fails >= self.config.max_retry_attempts:
                    logger.error(
                        f"Action {action_name} exceeded max retries — stopping state machine"
                    )
                    self.stop()
                # Only run one action per tick
                break

    def _dismiss_overlays(self) -> bool:
        """Close chat/guide windows if detected.

        Returns True if capture succeeded, False otherwise.
        """
        if self.screen_capture is None or self.pc_input is None:
            return True
        image = self.screen_capture.capture()
        if image is None:
            return False

        for template_name, label in [("close_chat", "chat"), ("guide_close", "guide")]:
            matches = self._chat_matcher.match(image, template_name=template_name)
            if matches:
                best = max(matches, key=lambda m: m.confidence)
                bx1, by1, bx2, by2 = best.bbox
                cx = random.randint(bx1, max(bx1, bx2 - 1))
                cy = random.randint(by1, max(by1, by2 - 1))
                logger.info(f"[StateMachine] Closing {label} at ({cx}, {cy}) conf={best.confidence:.2f}")
                self.pc_input.move_to_safe_zone()
                self.pc_input.tap(cx, cy)
                if self._timing:
                    time.sleep(max(0.05, self._timing.sample("click_interval") / 1000.0))
                else:
                    time.sleep(random.uniform(0.5, 1.0))
                # Only dismiss one overlay per tick to avoid mis-clicks
                break
        return True

    def _infer_next_state(self) -> Optional[str]:
        """Infer next state from detections (placeholder)."""
        # TODO: integrate vision pipeline to infer state
        return None

    def _enter_recovery(self) -> None:
        """Enter error recovery state."""
        retries = self.context.increment_retry("ERROR_RECOVERY")
        if retries > self.config.max_retry_attempts:
            raise RecoveryError(f"Max recovery attempts ({self.config.max_retry_attempts}) exceeded")

        logger.warning(f"Entering recovery (attempt {retries})")
        self.context.record_state(BotState.ERROR_RECOVERY.name)
        # TODO: implement recovery sequence (back -> wait -> home -> relaunch)
