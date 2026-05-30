"""Train troops action."""

from typing import TYPE_CHECKING, Optional

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class TrainTroopsAction(BaseAction):
    """Action to train troops in barracks."""

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)

    def can_execute(self) -> bool:
        # TODO: check if barracks are free and resources available
        return True

    def execute(self) -> bool:
        # TODO: navigate to barracks and train troops
        return True
