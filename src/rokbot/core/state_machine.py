"""State machine orchestrator for ROK Bot Engine v2."""

import time
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

from loguru import logger

from rokbot.actions.action_factory import ActionFactory
from rokbot.core.config import BotConfig
from rokbot.core.exceptions import RecoveryError, StuckError
from rokbot.core.state_context import StateContext
from rokbot.core.state_transitions import TransitionRegistry, TransitionRule


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
        self._state_handlers: Dict[str, Callable] = {}
        self._running = False
        self.pc_input = pc_input
        self.screen_capture = screen_capture
        self.ocr_engine = ocr_engine
        self._actions = self._load_actions()

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

    def register_handler(self, state: BotState, handler: Callable[["StateMachine"], None]) -> None:
        """Register a handler function for a state."""
        self._state_handlers[state.name] = handler

    def start(self) -> None:
        """Start the state machine loop."""
        self._running = True
        logger.info("State machine started")
        self.context.record_state(BotState.UNKNOWN.name)

        while self._running:
            try:
                self._tick()
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
        current_state = self.context.current_state or BotState.UNKNOWN.name

        # Check stuck condition
        if self.context.is_stuck(self.config.stuck_threshold_seconds):
            raise StuckError(f"Stuck in {current_state} for {self.context.time_in_current_state():.0f}s")

        # Determine next state (placeholder for vision integration)
        next_state = self._infer_next_state()

        if next_state and next_state != current_state:
            logger.info(f"Transition: {current_state} -> {next_state}")
            self.context.record_transition(current_state, next_state, success=True)
            self.context.record_state(next_state)

        # Evaluate and execute actions by priority
        self._evaluate_and_execute_actions()

        # Execute state handler (legacy, can be removed once all actions are migrated)
        handler = self._state_handlers.get(current_state)
        if handler:
            handler(self)

    def _evaluate_and_execute_actions(self) -> None:
        """Run through enabled actions in priority order and execute the first available one."""
        for action_name in self._get_action_priority_order():
            action = self._actions[action_name]
            try:
                if action.can_execute():
                    logger.info(f"Executing action: {action_name}")
                    success = action.execute()
                    if success:
                        action.on_success()
                    else:
                        action.on_failure("Execution returned False")
                    # Only run one action per tick
                    break
            except Exception as e:
                logger.exception(f"Action {action_name} failed: {e}")
                action.on_failure(str(e))

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
