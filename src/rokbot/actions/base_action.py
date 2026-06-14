"""Abstract base class for all bot actions."""

import random
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Tuple

from loguru import logger

from rokbot.core.config import BotConfig

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class BaseAction(ABC):
    """Base class for game actions.

    Provides shared humanization helpers so every action can sample delays,
    add micro-jitter to click targets, and report cognitive state without
    re-implementing the same logic.
    """

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        self.config = config
        self.state_machine = state_machine
        self.name = self.__class__.__name__

        self._humanization_enabled = bool(
            config.humanization.enabled if config and config.humanization else False
        )
        self._timing: Optional["TimingEngine"] = None
        self._decision: Optional["DecisionEngine"] = None

        if self._humanization_enabled:
            from rokbot.humanization.decision_engine import DecisionEngine
            from rokbot.humanization.timing_engine import TimingEngine

            profile_path = None
            if config and config.humanization and config.humanization.profile_path:
                profile_path = config.humanization.profile_path

            self._timing = TimingEngine(profile_path=profile_path)

            # Share the StateMachine's DecisionEngine when available so fatigue
            # and frustration accumulate across the whole session.
            shared_decision = getattr(state_machine, "_decision_engine", None)
            if shared_decision is not None:
                self._decision = shared_decision
            else:
                fatigue_half_life = 2.0
                base_distraction = 0.08
                base_misclick = 0.01
                if config and config.humanization:
                    fatigue_half_life = config.humanization.fatigue_half_life_hours
                    base_distraction = config.humanization.base_distraction_rate
                    base_misclick = config.humanization.base_misclick_rate
                self._decision = DecisionEngine(
                    fatigue_half_life_hours=fatigue_half_life,
                    base_distraction_rate=base_distraction,
                    base_misclick_rate=base_misclick,
                )

    # ------------------------------------------------------------------
    # Humanization helpers
    # ------------------------------------------------------------------
    def human_delay(
        self,
        distribution: str = "click_interval",
        fallback_seconds: float = 0.5,
        min_seconds: float = 0.05,
    ) -> None:
        """Sleep using the configured human timing distribution.

        Args:
            distribution: Name of the distribution to sample (e.g. reaction_time,
                click_interval, decision_time, break_duration).
            fallback_seconds: Fixed sleep when humanization is disabled.
            min_seconds: Minimum sleep to avoid zero-length delays.
        """
        if self._humanization_enabled and self._timing is not None:
            delay_ms = self._timing.sample(distribution)
            delay_s = max(min_seconds, delay_ms / 1000.0)
        else:
            delay_s = fallback_seconds
        time.sleep(delay_s)

    def pre_action_delay(self) -> None:
        """Short reaction delay before an action begins."""
        self.human_delay("reaction_time", fallback_seconds=0.2)

    def post_action_delay(self) -> None:
        """Short interval after an action completes."""
        self.human_delay("click_interval", fallback_seconds=0.5)

    def random_point_in_bbox(
        self,
        bbox: Tuple[int, int, int, int],
        jitter_sigma: float = 0.0,
        edge_margin: int = 0,
    ) -> Tuple[int, int]:
        """Return a random point inside a bounding box with optional jitter.

        Args:
            bbox: (x1, y1, x2, y2) in pixel coordinates.
            jitter_sigma: Standard deviation of Gaussian jitter added to the
                chosen point. Useful for simulating imprecise human taps.
            edge_margin: Number of pixels to avoid near the bbox edges.
        """
        x1, y1, x2, y2 = bbox
        if edge_margin:
            x1 += edge_margin
            y1 += edge_margin
            x2 = max(x1 + 1, x2 - edge_margin)
            y2 = max(y1 + 1, y2 - edge_margin)

        px = random.randint(x1, max(x1, x2 - 1))
        py = random.randint(y1, max(y1, y2 - 1))

        if jitter_sigma and self._humanization_enabled:
            px = int(round(random.gauss(px, jitter_sigma)))
            py = int(round(random.gauss(py, jitter_sigma)))

        # Clamp back to original bbox to stay inside the target.
        orig_x1, orig_y1, orig_x2, orig_y2 = bbox
        px = max(orig_x1, min(px, orig_x2 - 1))
        py = max(orig_y1, min(py, orig_y2 - 1))
        return (px, py)

    def humanized_tap(
        self,
        x: int,
        y: int,
        post_delay_distribution: str = "click_interval",
        post_delay_fallback: float = 0.5,
    ) -> None:
        """Tap a coordinate and then apply a humanized post-click delay."""
        if self.state_machine is None or self.state_machine.pc_input is None:
            logger.warning(f"[{self.name}] Cannot humanized_tap: pc_input unavailable")
            return
        self.state_machine.pc_input.tap(x, y)
        self.human_delay(post_delay_distribution, fallback_seconds=post_delay_fallback)

    def humanized_tap_match(
        self,
        match,
        post_delay_distribution: str = "click_interval",
        post_delay_fallback: float = 0.5,
        jitter_sigma: float = 0.0,
        edge_margin: int = 0,
    ) -> Tuple[int, int]:
        """Tap the center of a template match with humanization.

        Returns the point that was tapped.
        """
        x, y = self.random_point_in_bbox(
            match.bbox, jitter_sigma=jitter_sigma, edge_margin=edge_margin
        )
        self.humanized_tap(x, y, post_delay_distribution, post_delay_fallback)
        return (x, y)

    def record_success(self) -> None:
        """Report a successful step to the cognitive model."""
        if self._decision is not None:
            self._decision.record_success()

    def record_error(self) -> None:
        """Report an error to the cognitive model (increases frustration)."""
        if self._decision is not None:
            self._decision.record_error()

    def get_action_config(self, key: str, default=None):
        """Return a per-action setting from config/actions.yaml if present."""
        if self.config is None or self.config.actions is None:
            return default
        # Common action name mapping from class name.
        name_map = {
            "GatherAction": "gather",
            "GatherGemAction": "gather_gem",
            "RallyFortAction": "rally_fort",
            "ScoutAction": "scout",
            "TrainTroopsAction": "train_troops",
            "BarbarianAttackAction": "barbarian_attack",
            "ScoutCaveHighAction": "scout_cave_high",
            "ScoutCaveLowAction": "scout_cave_low",
            "AllianceHelpAction": "alliance_help",
            "VillagerHelpAction": "villager_help",
            "ReconnectAction": "reconnect",
            "DynamicComboAction": "dynamic_combo",
        }
        action_name = name_map.get(self.name, self.name)
        action_cfg = self.config.actions.action_configs.get(action_name, {})
        return action_cfg.get(key, default)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------
    @abstractmethod
    def can_execute(self) -> bool:
        """Return True if preconditions for this action are met."""
        pass

    @abstractmethod
    def execute(self) -> bool:
        """Execute the action. Return True on success."""
        pass

    def on_success(self) -> None:
        """Hook called after successful execution."""
        logger.info(f"Action {self.name} completed successfully")
        self.record_success()

    def on_failure(self, reason: str) -> None:
        """Hook called after failed execution."""
        logger.warning(f"Action {self.name} failed: {reason}")
        self.record_error()
