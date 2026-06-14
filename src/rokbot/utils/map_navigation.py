"""Shared map navigation helpers for actions."""

import random
from typing import Tuple

import numpy as np
from loguru import logger


class MapNavigationMixin:
    """Mixin providing city/world state detection and navigation helpers.

    Expects the subclass to define:
        - CITY_ICON_ROI_RATIO: Tuple[float, float, float, float]
        - _city_matcher: TemplateMatcher instance
        - state_machine: with pc_input attribute

    The subclass should also inherit from BaseAction (or otherwise provide
    ``human_delay`` and ``random_point_in_bbox``) so the navigation pauses are
    humanized.
    """

    def random_point_in_bbox(
        self,
        bbox: Tuple[int, int, int, int],
        jitter_sigma: float = 0.0,
        edge_margin: int = 0,
    ) -> Tuple[int, int]:
        """Return a random point inside a bounding box with optional jitter.

        This mixin version delegates to the BaseAction implementation when
        available; otherwise it falls back to a plain uniform sample.
        """
        base_impl = getattr(super(), "random_point_in_bbox", None)
        if callable(base_impl):
            return base_impl(bbox, jitter_sigma=jitter_sigma, edge_margin=edge_margin)

        x1, y1, x2, y2 = bbox
        if edge_margin:
            x1 += edge_margin
            y1 += edge_margin
            x2 = max(x1 + 1, x2 - edge_margin)
            y2 = max(y1 + 1, y2 - edge_margin)
        px = random.randint(x1, max(x1, x2 - 1))
        py = random.randint(y1, max(y1, y2 - 1))
        return (px, py)

    @staticmethod
    def roi_from_ratio(
        image: np.ndarray, ratio: Tuple[float, float, float, float]
    ) -> Tuple[int, int, int, int]:
        """Convert ratio (x1, y1, x2, y2) to pixel coordinates."""
        h, w = image.shape[:2]
        x1 = int(w * ratio[0])
        y1 = int(h * ratio[1])
        x2 = int(w * ratio[2])
        y2 = int(h * ratio[3])
        return (x1, y1, x2, y2)

    def _detect_city_state(self, image: np.ndarray) -> str:
        """Detect city/world state from bottom-right icon.

        Returns one of: 'in_city', 'in_world', 'unknown'.
        """
        ratio = getattr(self, "CITY_ICON_ROI_RATIO", (0.75, 0.75, 1.0, 1.0))
        roi = self.roi_from_ratio(image, ratio)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        matcher = getattr(self, "_city_matcher", None)
        if matcher is None:
            return "unknown"

        in_city_matches = matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            return "in_city"

        enter_matches = matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            return "in_world"

        return "unknown"

    def _ensure_in_city(self, image: np.ndarray) -> bool:
        """Ensure we are in city view. Tap enter-city icon if on world map.

        Returns True if we are (or successfully switched to) city view.
        """
        ratio = getattr(self, "CITY_ICON_ROI_RATIO", (0.75, 0.75, 1.0, 1.0))
        roi = self.roi_from_ratio(image, ratio)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        matcher = getattr(self, "_city_matcher", None)
        pc_input = getattr(self.state_machine, "pc_input", None) if hasattr(self, "state_machine") else None
        if matcher is None or pc_input is None:
            return False

        in_city_matches = matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            logger.debug("Already in city view")
            return True

        enter_matches = matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            best = max(enter_matches, key=lambda m: m.confidence)
            bx1, by1, bx2, by2 = best.bbox
            cx, cy = self.random_point_in_bbox((bx1, by1, bx2, by2), edge_margin=2)
            cx += roi_x1
            cy += roi_y1
            logger.info(f"In world — entering city at ({cx}, {cy})")
            pc_input.tap(cx, cy)
            self.human_delay("transition_wait", fallback_seconds=1.5)
            return True

        logger.warning("Could not determine city/world state")
        return False

    def _ensure_in_world(self, image: np.ndarray) -> bool:
        """Ensure we are in world view. Tap city-exit icon if in city.

        Returns True if we are (or successfully switched to) world view.
        """
        ratio = getattr(self, "CITY_ICON_ROI_RATIO", (0.75, 0.75, 1.0, 1.0))
        roi = self.roi_from_ratio(image, ratio)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        matcher = getattr(self, "_city_matcher", None)
        pc_input = getattr(self.state_machine, "pc_input", None) if hasattr(self, "state_machine") else None
        if matcher is None or pc_input is None:
            return False

        enter_matches = matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            logger.debug("Already in world view")
            return True

        in_city_matches = matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            best = max(in_city_matches, key=lambda m: m.confidence)
            bx1, by1, bx2, by2 = best.bbox
            cx, cy = self.random_point_in_bbox((bx1, by1, bx2, by2), edge_margin=2)
            cx += roi_x1
            cy += roi_y1
            logger.info(f"In city — switching to world map at ({cx}, {cy})")
            pc_input.tap(cx, cy)
            self.human_delay("transition_wait", fallback_seconds=1.5)
            return True

        logger.warning("Could not determine city/world state")
        return False
