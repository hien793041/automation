"""Resource gathering action."""

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine


class GatherAction(BaseAction):
    """Action to send troops to gather resources."""

    def __init__(self, config: BotConfig, state_machine: StateMachine):
        super().__init__(config, state_machine)

    def can_execute(self) -> bool:
        # TODO: check if gather node is visible and troops available
        return True

    def execute(self) -> bool:
        # TODO: implement gather flow
        # 1. Detect gather node
        # 2. Tap node
        # 3. Tap gather button
        # 4. Select troops
        # 5. Confirm march
        return True
