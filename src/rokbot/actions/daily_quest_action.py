"""Daily quest action."""

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine


class DailyQuestAction(BaseAction):
    """Action to complete daily quests."""

    def __init__(self, config: BotConfig, state_machine: StateMachine):
        super().__init__(config, state_machine)

    def can_execute(self) -> bool:
        # TODO: check if daily quests are available
        return True

    def execute(self) -> bool:
        # TODO: claim daily quest rewards
        return True
