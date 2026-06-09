"""Bezier + jerk-limited movement engine for human-like touch paths."""

import math
from typing import List, Tuple

import numpy as np
from loguru import logger


class MovementEngine:
    """Generates human-like trajectories using quadratic Bezier curves."""

    def __init__(
        self,
        fitts_a: float = 100.0,  # ms intercept
        fitts_b: float = 50.0,   # ms/bit slope
        control_offset_ratio: float = 0.10,
        step_ms: float = 10.0,
        jitter_sigma: float = 1.5,
    ):
        self.fitts_a = fitts_a
        self.fitts_b = fitts_b
        self.control_offset_ratio = control_offset_ratio
        self.step_ms = step_ms
        self.jitter_sigma = jitter_sigma

    def _quadratic_bezier(
        self, p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, num_points: int
    ) -> np.ndarray:
        """Generate points on a quadratic Bezier curve."""
        t = np.linspace(0, 1, num_points).reshape(-1, 1)
        return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2

    def _fitts_duration(self, distance: float, target_width: float = 50.0) -> float:
        """Calculate movement duration using Fitts's Law."""
        index_of_difficulty = math.log2(distance / target_width + 1)
        return self.fitts_a + self.fitts_b * index_of_difficulty

    def generate_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        target_width: float = 50.0,
    ) -> List[Tuple[int, int]]:
        """Generate a human-like touch path from start to end."""
        p0 = np.array(start, dtype=np.float64)
        p2 = np.array(end, dtype=np.float64)

        distance = np.linalg.norm(p2 - p0)
        if distance < 1:
            return [start]

        duration_ms = self._fitts_duration(distance, target_width)
        num_points = max(3, int(duration_ms / self.step_ms))

        # Control point with perpendicular offset
        mid = (p0 + p2) / 2
        direction = p2 - p0
        perp = np.array([-direction[1], direction[0]], dtype=np.float64)
        norm = np.linalg.norm(perp)
        if norm > 0:
            perp = perp / norm
        offset = distance * self.control_offset_ratio * np.random.choice([-1, 1])
        p1 = mid + perp * offset

        points = self._quadratic_bezier(p0, p1, p2, num_points)

        # Add micro-jitter (skip first and last points to preserve exact targets)
        jitter = np.random.normal(0, self.jitter_sigma, points.shape)
        jitter[0] = 0
        jitter[-1] = 0
        points = points + jitter

        # Convert to integer tuples
        path = [(int(round(x)), int(round(y))) for x, y in points]
        logger.debug(f"Generated path: {len(path)} points, duration={duration_ms:.0f}ms")
        return path
