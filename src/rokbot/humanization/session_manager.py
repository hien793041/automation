"""Manages human-like session patterns: schedule, length, breaks."""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from loguru import logger


@dataclass
class SessionSchedule:
    """Daily activity schedule."""

    sleep_start: int = 2   # 2 AM
    sleep_end: int = 8     # 8 AM
    work_start: int = 9    # 9 AM
    work_end: int = 17     # 5 PM
    evening_start: int = 18
    evening_end: int = 1   # 1 AM next day (wrap)


class SessionManager:
    """Manages bimodal session lengths and Poisson breaks."""

    def __init__(
        self,
        schedule: Optional[SessionSchedule] = None,
        short_session_mu: float = 1.5,      # hours
        short_session_sigma: float = 0.3,
        long_session_mu: float = 5.0,       # hours
        long_session_sigma: float = 0.8,
        short_session_weight: float = 0.6,
        break_lambda_hours: float = 2.0,
        min_break_minutes: float = 5.0,
    ):
        self.schedule = schedule or SessionSchedule()
        self.short_session_mu = short_session_mu
        self.short_session_sigma = short_session_sigma
        self.long_session_mu = long_session_mu
        self.long_session_sigma = long_session_sigma
        self.short_session_weight = short_session_weight
        self.break_lambda_hours = break_lambda_hours
        self.min_break_minutes = min_break_minutes

        self._session_start: Optional[datetime] = None
        self._next_break: Optional[datetime] = None

    def should_be_active(self, now: Optional[datetime] = None) -> bool:
        """Return True if the simulated human would be playing now."""
        now = now or datetime.utcnow()
        hour = now.hour

        # Evening (18-23) and late night (0-1)
        if hour >= self.schedule.evening_start or hour < self.schedule.evening_end:
            return random.random() < 0.70
        # Work hours
        if self.schedule.work_start <= hour < self.schedule.work_end:
            return random.random() < 0.30
        # Sleep hours
        if self.schedule.sleep_start <= hour < self.schedule.sleep_end:
            return random.random() < 0.05

        return random.random() < 0.30

    def sample_session_length_hours(self) -> float:
        """Sample session length from bimodal distribution."""
        if random.random() < self.short_session_weight:
            length = np.random.normal(self.short_session_mu, self.short_session_sigma)
        else:
            length = np.random.normal(self.long_session_mu, self.long_session_sigma)
        return max(0.25, length)

    def sample_break_minutes(self) -> float:
        """Sample break duration from exponential + minimum."""
        exp_minutes = np.random.exponential(1.0 / self.break_lambda_hours * 60)
        return self.min_break_minutes + exp_minutes

    def sample_break_interval_minutes(self) -> float:
        """Sample interval between breaks from Poisson process."""
        return np.random.exponential(self.break_lambda_hours * 60)

    def start_session(self) -> None:
        """Record session start and schedule first break."""
        self._session_start = datetime.utcnow()
        interval = self.sample_break_interval_minutes()
        self._next_break = self._session_start + timedelta(minutes=interval)
        logger.info(
            f"Session started at {self._session_start}, next break in {interval:.0f}min"
        )

    def check_break(self) -> bool:
        """Check if it's time for a break."""
        if self._next_break is None:
            return False
        return datetime.utcnow() >= self._next_break
