"""Unit tests for humanization engine."""


from rokbot.humanization.decision_engine import DecisionEngine
from rokbot.humanization.movement_engine import MovementEngine
from rokbot.humanization.timing_engine import TimingEngine


def test_timing_engine_samples_positive():
    engine = TimingEngine()
    for _ in range(100):
        assert engine.reaction_delay() >= 0
        assert engine.click_delay() >= 0


def test_movement_engine_generates_path():
    engine = MovementEngine()
    path = engine.generate_path((100, 100), (400, 400))
    assert len(path) >= 2
    assert path[0] == (100, 100)


def test_decision_engine_fatigue_increases():
    engine = DecisionEngine()
    initial = engine.state.fatigue
    # Simulate passage of time by updating with old start
    from datetime import datetime, timedelta
    engine.state.session_start = datetime.utcnow() - timedelta(hours=4)
    engine.update()
    assert engine.state.fatigue > initial
