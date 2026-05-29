"""Pytest configuration and shared fixtures."""

import pytest

from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine


@pytest.fixture
def bot_config() -> BotConfig:
    return BotConfig()


@pytest.fixture
def state_machine(bot_config: BotConfig) -> StateMachine:
    return StateMachine(bot_config)
