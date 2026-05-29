"""Abstract base class for all bot actions."""

from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger

from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine


class BaseAction(ABC):
    """Base class for game actions."""

    def __init__(self, config: BotConfig, state_machine: Optional[StateMachine] = None):
        self.config = config
        self.state_machine = state_machine
        self.name = self.__class__.__name__

    @abstractmethod
    def can_execute(self) -> bool:
        """Return True if preconditions for this action are met."""
        pass

    @abstractmethod
    def execute(self) -> bool:
        """Execute the action. Return True on success."""
        pass

    def on_success(self) -> None:
        """Hook called after successful execution."""
        logger.info(f"Action {self.name} completed successfully")

    def on_failure(self, reason: str) -> None:
        """Hook called after failed execution."""
        logger.warning(f"Action {self.name} failed: {reason}")
