"""State transition rules and guards for ROK Bot Engine v2."""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from rokbot.core.state_context import StateContext


TransitionGuard = Callable[[StateContext], bool]


@dataclass
class TransitionRule:
    """Defines a valid state transition."""

    from_states: List[str]
    to_state: str
    guard: Optional[TransitionGuard] = None
    priority: int = 0  # Higher = evaluated first
    description: str = ""


class TransitionRegistry:
    """Registry of all valid state transitions."""

    CRITICAL_STATES = ["CAPTCHA", "CONNECTION_LOST", "VIP_POPUP"]

    def __init__(self):
        self._rules: List[TransitionRule] = []
        self._build_default_rules()

    def _build_default_rules(self) -> None:
        """Register default ROK state transitions."""
        # Critical overrides
        self.add_rule(
            TransitionRule(
                from_states=["*"],
                to_state="CAPTCHA",
                priority=100,
                description="Captcha detected",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["*"],
                to_state="CONNECTION_LOST",
                priority=99,
                description="Connection lost popup",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["*"],
                to_state="VIP_POPUP",
                priority=98,
                description="VIP popup blocking UI",
            )
        )

        # Normal gather flow
        self.add_rule(
            TransitionRule(
                from_states=["IDLE"],
                to_state="NODE_SELECTED",
                priority=10,
                description="Gather node selected on map",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["NODE_SELECTED"],
                to_state="TROOP_SELECT",
                priority=10,
                description="Troop selection screen open",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["TROOP_SELECT"],
                to_state="MARCHING",
                priority=10,
                description="March started",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["MARCHING"],
                to_state="GATHERING",
                priority=10,
                description="Troops arrived at node",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["GATHERING"],
                to_state="GATHER_COMPLETE",
                priority=10,
                description="Gather timer finished",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["GATHER_COMPLETE"],
                to_state="WAREHOUSE_FULL",
                priority=9,
                description="Warehouse capacity reached",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["GATHER_COMPLETE", "WAREHOUSE_FULL"],
                to_state="IDLE",
                priority=8,
                description="Return to idle/map",
            )
        )

        # Error recovery
        self.add_rule(
            TransitionRule(
                from_states=["*"],
                to_state="ERROR_RECOVERY",
                priority=50,
                description="Stuck or error detected",
            )
        )
        self.add_rule(
            TransitionRule(
                from_states=["ERROR_RECOVERY"],
                to_state="IDLE",
                priority=10,
                description="Recovery complete",
            )
        )

    def add_rule(self, rule: TransitionRule) -> None:
        """Add a transition rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def get_valid_transitions(
        self, context: StateContext, available_detections: List[str]
    ) -> List[TransitionRule]:
        """Return valid transitions sorted by priority."""
        current = context.current_state or "UNKNOWN"
        valid: List[TransitionRule] = []
        for rule in self._rules:
            if "*" in rule.from_states or current in rule.from_states:
                if rule.guard is None or rule.guard(context):
                    valid.append(rule)
        return valid
