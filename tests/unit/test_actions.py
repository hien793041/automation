"""Unit tests for actions."""


from rokbot.actions.action_factory import ActionFactory
from rokbot.actions.gather_action import GatherAction
from rokbot.core.state_machine import StateMachine


def test_action_factory_creates_gather(bot_config):
    sm = StateMachine(bot_config)
    action = ActionFactory.create("gather", bot_config, sm)
    assert isinstance(action, GatherAction)


def test_action_factory_unknown_action(bot_config):
    sm = StateMachine(bot_config)
    action = ActionFactory.create("nonexistent", bot_config, sm)
    assert action is None
