"""Scouting action."""

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine


class ScoutAction(BaseAction):
    """Action to send scouts."""

    def __init__(self, config: BotConfig, state_machine: StateMachine):
        super().__init__(config, state_machine)

    def can_execute(self) -> bool:
        # TODO: check if scouts are available
        return True

    def execute(self) -> bool:
        # TODO: send scouts to explore fog
        return True
