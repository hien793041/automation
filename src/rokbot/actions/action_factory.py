"""Action registry and factory."""

from typing import TYPE_CHECKING, Dict, Optional, Type

from loguru import logger

from rokbot.actions.alliance_help_action import AllianceHelpAction
from rokbot.actions.barbarian_attack_action import BarbarianAttackAction
from rokbot.actions.base_action import BaseAction
from rokbot.actions.gather_action import GatherAction
from rokbot.actions.gather_gem_action import GatherGemAction
from rokbot.actions.reconnect_action import ReconnectAction
from rokbot.actions.scout_action import ScoutAction
from rokbot.actions.scout_cave_high_action import ScoutCaveHighAction
from rokbot.actions.scout_cave_low_action import ScoutCaveLowAction
from rokbot.actions.train_troops_action import TrainTroopsAction
from rokbot.actions.villager_help_action import VillagerHelpAction
from rokbot.core.config import BotConfig

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class ActionFactory:
    """Factory for creating action instances."""

    _registry: Dict[str, Type[BaseAction]] = {
        "gather": GatherAction,
        "gather_gem": GatherGemAction,
        "alliance_help": AllianceHelpAction,
        "barbarian_attack": BarbarianAttackAction,
        "scout": ScoutAction,
        "scout_cave_high": ScoutCaveHighAction,
        "scout_cave_low": ScoutCaveLowAction,
        "train_troops": TrainTroopsAction,

        "villager_help": VillagerHelpAction,
        "reconnect": ReconnectAction,
    }

    @classmethod
    def create(cls, action_name: str, config: BotConfig, state_machine: Optional["StateMachine"]) -> Optional[BaseAction]:
        """Create an action instance by name (built-in or user combo)."""
        action_class = cls._registry.get(action_name)
        if action_class is not None:
            return action_class(config, state_machine)

        # Try user-defined combo from combos.yaml
        from rokbot.actions.combo_loader import ComboLoader
        from rokbot.actions.dynamic_combo_action import DynamicComboAction

        combo_sequence = ComboLoader.get_combo(action_name)
        if combo_sequence:
            logger.debug(f"Creating dynamic combo '{action_name}' with sequence: {combo_sequence}")
            return DynamicComboAction(config, state_machine, combo_name=action_name, action_sequence=combo_sequence)

        logger.error(f"Unknown action '{action_name}'")
        return None

    @classmethod
    def register(cls, name: str, action_class: Type[BaseAction]) -> None:
        """Register a new action type."""
        cls._registry[name] = action_class
        logger.info(f"Registered action '{name}' -> {action_class.__name__}")

    @classmethod
    def list_actions(cls) -> list:
        """List all registered action and combo names."""
        from rokbot.actions.combo_loader import ComboLoader
        return list(cls._registry.keys()) + ComboLoader.list_combos()
