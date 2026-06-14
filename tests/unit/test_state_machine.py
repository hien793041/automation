"""Unit tests for state machine."""


from rokbot.core.state_machine import BotState, StateMachine


def test_state_machine_initial_state(bot_config):
    sm = StateMachine(bot_config)
    assert sm.context.current_state == BotState.UNKNOWN.name


def test_state_machine_stuck_detection(bot_config):
    sm = StateMachine(bot_config)
    sm.context.record_state(BotState.IDLE.name)
    # Manually set start time far in the past to simulate stuck
    from datetime import datetime, timedelta
    sm.context._state_start_time = datetime.utcnow() - timedelta(seconds=9999)
    assert sm.context.is_stuck(bot_config.stuck_threshold_seconds)
