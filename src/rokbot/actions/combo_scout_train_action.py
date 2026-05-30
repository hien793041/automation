"""Combo action: Scout + Train Troops in one cycle."""

from typing import TYPE_CHECKING, Optional

from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.actions.scout_action import ScoutAction
from rokbot.actions.train_troops_action import TrainTroopsAction
from rokbot.core.config import BotConfig

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class ComboScoutTrainAction(BaseAction):
    """Executes Scout first, then Train Troops if scout is not available."""

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self._scout = ScoutAction(config, state_machine)
        self._train = TrainTroopsAction(config, state_machine)

    def can_execute(self) -> bool:
        """Return True if either scout or train can run."""
        if self._scout.can_execute():
            return True
        if self._train.can_execute():
            return True
        return False

    def execute(self) -> bool:
        """Run scout first; if not available, run train troops."""
        # Try scout first
        if self._scout.can_execute():
            logger.info("[Combo] Running scout step")
            success = self._scout.execute()
            if success:
                self._scout.on_success()
                return True
            else:
                self._scout.on_failure("Scout step failed in combo")

        # Fall back to train troops
        if self._train.can_execute():
            logger.info("[Combo] Running train troops step")
            success = self._train.execute()
            if success:
                self._train.on_success()
                return True
            else:
                logger.info("[Combo] Train troops step returned False")
                return False

        logger.info("[Combo] Neither scout nor train is available")
        return False
