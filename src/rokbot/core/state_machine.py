"""State machine orchestrator for ROK Bot Engine v2."""

import time
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

from loguru import logger

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

    def __init__(self, config: BotConfig):
        self.config = config
        self.context = StateContext(max_retries=config.max_retry_attempts)
        self.transitions = TransitionRegistry()
        self._state_handlers: Dict[str, Callable] = {}
        self._running = False

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

        # Execute state handler
        handler = self._state_handlers.get(current_state)
        if handler:
            handler(self)

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
