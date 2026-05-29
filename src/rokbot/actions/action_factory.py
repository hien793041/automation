"""Action registry and factory."""

from typing import Dict, Optional, Type

from loguru import logger

from rokbot.actions.alliance_help_action import AllianceHelpAction
from rokbot.actions.base_action import BaseAction
from rokbot.actions.daily_quest_action import DailyQuestAction
from rokbot.actions.gather_action import GatherAction
from rokbot.actions.scout_action import ScoutAction
from rokbot.actions.train_troops_action import TrainTroopsAction
from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine


class ActionFactory:
    """Factory for creating action instances."""

    _registry: Dict[str, Type[BaseAction]] = {
        "gather": GatherAction,
        "alliance_help": AllianceHelpAction,
        "daily_quest": DailyQuestAction,
        "scout": ScoutAction,
        "train_troops": TrainTroopsAction,
    }

    @classmethod
    def create(cls, action_name: str, config: BotConfig, state_machine: StateMachine) -> Optional[BaseAction]:
        """Create an action instance by name."""
        action_class = cls._registry.get(action_name)
        if action_class is None:
            logger.error(f"Unknown action '{action_name}'")
            return None
        return action_class(config, state_machine)

    @classmethod
    def register(cls, name: str, action_class: Type[BaseAction]) -> None:
        """Register a new action type."""
        cls._registry[name] = action_class
        logger.info(f"Registered action '{name}' -> {action_class.__name__}")

    @classmethod
    def list_actions(cls) -> list:
        """List all registered action names."""
        return list(cls._registry.keys())
