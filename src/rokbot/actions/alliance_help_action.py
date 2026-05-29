"""Alliance help action."""

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine


class AllianceHelpAction(BaseAction):
    """Action to help alliance members."""

    def __init__(self, config: BotConfig, state_machine: StateMachine):
        super().__init__(config, state_machine)

    def can_execute(self) -> bool:
        # TODO: check if help button is available
        return True

    def execute(self) -> bool:
        # TODO: open alliance help and tap help all
        return True
