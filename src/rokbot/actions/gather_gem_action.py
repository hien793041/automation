"""Gather Gem action — specialized flow for collecting gems on the world map.

Uses the game window capture (single-window mode).
"""

import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class GatherGemAction(BaseAction):
    """Action to gather gems. Flow differs from standard resource gathering."""

    TEMPLATES_DIR = Path("data/templates/gathergem")
    SHARED_TEMPLATES_DIR = Path("data/templates")

    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)
    GEM_AVAILABLE_TEMPLATES = ["gem_available0", "gem_available1", "gem_available3", "gem_available4", "gem_available5"]
    MAX_MOVEMENT_STEPS = 20
    MAX_ACTIVE_TROOPS = 4
    TROOP_STATUS_TEMPLATES = ["gathering", "backing", "moving", "building"]

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self._matcher = TemplateMatcher(
            templates_dir=self.TEMPLATES_DIR,
            threshold=0.75,
        )
        self._city_matcher = TemplateMatcher(
            templates_dir=self.SHARED_TEMPLATES_DIR,
            threshold=0.80,
        )
        self._troop_matcher = TemplateMatcher(
            templates_dir=Path("data/templates/shared/troops"),
            threshold=0.75,
        )

    def _random_point_in_bbox(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        x1, y1, x2, y2 = bbox
        px = random.randint(x1, max(x1, x2 - 1))
        py = random.randint(y1, max(y1, y2 - 1))
        return (px, py)

    def _roi_from_ratio(self, image: np.ndarray, ratio: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
        h, w = image.shape[:2]
        x1 = int(w * ratio[0])
        y1 = int(h * ratio[1])
        x2 = int(w * ratio[2])
        y2 = int(h * ratio[3])
        return (x1, y1, x2, y2)

    def _detect_city_state(self, image: np.ndarray) -> str:
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            return "in_city"

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            return "in_world"

        return "unknown"

    def _hold_click_at(self, x: int, y: int, duration: float) -> None:
        """Hold mouse click at window-relative coordinates."""
        import pyautogui
        rect = self.state_machine.pc_input.window_manager.get_client_rect()
        if rect is None:
            logger.error("[GatherGem] Cannot hold click: game window not found")
            return
        left, top, _, _ = rect
        abs_x = left + x
        abs_y = top + y
        # Move to absolute screen position without clicking, then hold
        pyautogui.moveTo(abs_x, abs_y, duration=0.2)
        pyautogui.mouseDown()
        try:
            time.sleep(duration)
        finally:
            pyautogui.mouseUp()
        logger.info(f"[GatherGem] Held click at window ({x}, {y}) -> screen ({abs_x}, {abs_y}) for {duration:.2f}s")

    def _find_gems(self, image: np.ndarray) -> List:
        """Search for any gem_available template within the central map area.
        Uses stricter threshold and global NMS to reduce false positives.
        """
        h, w = image.shape[:2]
        margin_x = int(w * 0.08)
        margin_y = int(h * 0.08)
        roi = (margin_x, margin_y, w - margin_x, h - margin_y)

        # Collect raw matches from all templates
        raw_matches = []
        for tpl_name in self.GEM_AVAILABLE_TEMPLATES:
            matches = self._matcher.match(
                image,
                template_name=tpl_name,
                threshold=0.80,
                max_matches=10,
                roi=roi,
            )
            if matches:
                for m in matches:
                    raw_matches.append(m)

        # Global NMS: keep only the best match within a radius
        raw_matches.sort(key=lambda m: m.confidence, reverse=True)
        kept = []
        min_dist = 40  # pixels; NMS radius
        for m in raw_matches:
            cx, cy = m.center
            too_close = False
            for k in kept:
                kx, ky = k.center
                if ((cx - kx) ** 2 + (cy - ky) ** 2) < min_dist ** 2:
                    too_close = True
                    break
            if not too_close:
                kept.append(m)
                logger.info(f"[GatherGem] Found '{m.template_name}' conf={m.confidence:.2f} at ({cx}, {cy})")
        return kept

    def _click_gather_sequence(self) -> bool:
        """After clicking a gem_available, click through the gathering UI sequence.
        If any step fails, return False so the bot can retry with another gem.
        """
        steps = [
            ("gem_icon", "Clicking gem_icon"),
            ("gather_btn", "Clicking gather_btn"),
            ("new_troop", "Clicking new_troop"),
            ("send_troop", "Clicking send_troop"),
        ]
        for tpl_name, label in steps:
            image = self.state_machine.screen_capture.capture()
            if image is None:
                logger.warning(f"[GatherGem] Screenshot failed during {tpl_name}")
                return False
            matches = self._matcher.match(image, template_name=tpl_name, threshold=0.75)
            if not matches:
                logger.warning(f"[GatherGem] {tpl_name} not found — aborting sequence")
                return False
            best = max(matches, key=lambda m: m.confidence)
            x, y = self._random_point_in_bbox(best.bbox)
            logger.info(f"[GatherGem] {label} at ({x}, {y}) conf={best.confidence:.2f}")
            self.state_machine.pc_input.tap(x, y)
            time.sleep(random.uniform(0.8, 1.5))
        logger.info("[GatherGem] Gather sequence completed successfully")
        return True

    def _scan_and_click_gem(self, image: np.ndarray) -> bool:
        """Scan for gem_available and if found, click it and run the gather sequence."""
        gem_matches = self._find_gems(image)
        if gem_matches:
            gem = gem_matches[0]
            cx, cy = gem.center
            logger.info(f"[GatherGem] Clicking gem_available center at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(1.0, 2.0))
            return self._click_gather_sequence()
        return False

    def _click_city_center(self) -> bool:
        """Click city_center to reset camera to the city center."""
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        matches = self._matcher.match(image, template_name="city_center", threshold=0.75)
        if not matches:
            logger.info("[GatherGem] city_center not found")
            return False
        best = max(matches, key=lambda m: m.confidence)
        cx, cy = self._random_point_in_bbox(best.bbox)
        logger.info(f"[GatherGem] Clicking city_center at ({cx}, {cy}) conf={best.confidence:.2f}")
        self.state_machine.pc_input.tap(cx, cy)
        time.sleep(random.uniform(1.0, 2.0))
        return True

    def _open_resource_menu(self) -> bool:
        """Hold-click enter_city_icon and click resource_button to open the resource menu."""
        # Move mouse away from UI before capture
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        # Find enter_city_icon
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]
        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if not enter_matches:
            logger.info("[GatherGem] enter_city_icon not found")
            return False

        enter_btn = max(enter_matches, key=lambda m: m.confidence)
        ex1, ey1, ex2, ey2 = enter_btn.bbox
        abs_ex = roi_x1 + (ex1 + ex2) // 2
        abs_ey = roi_y1 + (ey1 + ey2) // 2
        self._hold_click_at(abs_ex, abs_ey, 3.0)

        # Hover resource_button
        time.sleep(0.5)
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        resource_matches = self._matcher.match(image, template_name="resource_button", threshold=0.75)
        if not resource_matches:
            logger.info("[GatherGem] resource_button not found")
            return False
        resource_btn = max(resource_matches, key=lambda m: m.confidence)
        rx, ry = self._random_point_in_bbox(resource_btn.bbox)
        import pyautogui
        rect = self.state_machine.pc_input.window_manager.get_client_rect()
        if rect:
            left, top, _, _ = rect
            pyautogui.moveTo(left + rx, top + ry, duration=0)
        time.sleep(1.5)

        # Click top-left of resource_button
        bx1, by1, _, _ = resource_btn.bbox
        self.state_machine.pc_input.tap(bx1, by1)
        return True

    def _count_active_troops(self, image: np.ndarray) -> int:
        """Count gathering/backing/moving/building troop icons on the world map."""
        total = 0
        for tpl_name in self.TROOP_STATUS_TEMPLATES:
            matches = self._troop_matcher.match(
                image, template_name=tpl_name, threshold=0.75, max_matches=10
            )
            count = len(matches)
            if count:
                logger.debug(f"[GatherGem] Found {count} '{tpl_name}' icon(s)")
                total += count
        if total:
            logger.info(f"[GatherGem] Active troop count = {total}")
        return total

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        # Count active troop icons (gathering/backing/moving/building)
        active_count = self._count_active_troops(image)
        if active_count >= self.MAX_ACTIVE_TROOPS:
            logger.info(
                f"[GatherGem] Active troops ({active_count}) >= max ({self.MAX_ACTIVE_TROOPS}) — bypassing"
            )
            return False

        city_state = self._detect_city_state(image)
        if city_state in ("in_city", "in_world"):
            return True

        logger.debug("[GatherGem] can_execute: city/world state unknown")
        return False

    def execute(self) -> bool:
        if self.state_machine is None:
            self.on_failure("StateMachine not available")
            return False
        if self.state_machine.screen_capture is None:
            self.on_failure("ScreenCapture not available")
            return False
        if self.state_machine.pc_input is None:
            self.on_failure("PCInput not available")
            return False

        # Ensure world view first
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        city_state = self._detect_city_state(image)
        if city_state == "in_city":
            roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
            roi_x1, roi_y1, roi_x2, roi_y2 = roi
            roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]
            in_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
            if in_matches:
                in_btn = max(in_matches, key=lambda m: m.confidence)
                ix1, iy1, ix2, iy2 = in_btn.bbox
                cx = roi_x1 + (ix1 + ix2) // 2
                cy = roi_y1 + (iy1 + iy2) // 2
                logger.info(f"[GatherGem] In city — switching to world at ({cx}, {cy})")
                self.state_machine.pc_input.tap(cx, cy)
                time.sleep(random.uniform(1.0, 3.0))

        # Click city_center to return to center, then open resource menu
        logger.info("[GatherGem] Clicking city_center to reset position")
        if not self._click_city_center():
            logger.warning("[GatherGem] city_center not found, continuing anyway")

        # Open resource menu once at the beginning
        logger.info("[GatherGem] Opening resource menu")
        if not self._open_resource_menu():
            return False

        # Main loop: scan → if no gem, move; if sequence fails, reopen menu
        arrow_keys = ["up", "down", "left", "right"]
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        prev_key = None

        for step in range(self.MAX_MOVEMENT_STEPS):
            time.sleep(2.0)
            image = self.state_machine.screen_capture.capture()
            if image is None:
                key = random.choice(arrow_keys)
                logger.info(f"[GatherGem] Moving {key} (screenshot failed)")
                self.state_machine.pc_input.hold_key(key, 0.5)
                time.sleep(2.0)
                prev_key = key
                continue

            gem_matches = self._find_gems(image)
            if gem_matches:
                gem = gem_matches[0]
                cx, cy = gem.center

                # Check gem_gathering BEFORE clicking — if someone is already on it, skip
                gathering_templates = ["gem_gathering", "gem_gathering1"]
                already_gathered = False
                for gt in gathering_templates:
                    gathering_matches = self._matcher.match(
                        image, template_name=gt, threshold=0.70
                    )
                    if gathering_matches:
                        for gm in gathering_matches:
                            gcx, gcy = gm.center
                            if ((gcx - cx) ** 2 + (gcy - cy) ** 2) < 80 ** 2:
                                logger.info(
                                    f"[GatherGem] '{gt}' conf={gm.confidence:.2f} near gem "
                                    f"at ({cx}, {cy}) — skipping"
                                )
                                already_gathered = True
                                break
                    if already_gathered:
                        break

                if already_gathered:
                    # Skip this gem and move on
                    key = random.choice(arrow_keys)
                    if prev_key and key == opposites.get(prev_key):
                        key = random.choice(arrow_keys)
                    prev_key = key
                    logger.info(f"[GatherGem] Gem occupied — moving {key}")
                    self.state_machine.pc_input.hold_key(key, 0.5)
                    time.sleep(2.0)
                    continue

                # Safe to click
                logger.info(f"[GatherGem] Clicking gem_available at ({cx}, {cy})")
                self.state_machine.pc_input.tap(cx, cy)
                time.sleep(random.uniform(1.0, 2.0))

                if self._click_gather_sequence():
                    # After sending troop, click city_center to reset camera
                    # then return so the next run starts from center
                    logger.info("[GatherGem] Troop sent — returning to city center")
                    self._click_city_center()
                    return True

                # Sequence failed — reopen resource menu and retry without moving
                logger.info("[GatherGem] Sequence failed — reopening resource menu")
                if not self._open_resource_menu():
                    return False
                continue

            # No gem found — move to next position (avoid reversing immediately)
            key = random.choice(arrow_keys)
            if prev_key and key == opposites.get(prev_key):
                key = random.choice(arrow_keys)
            prev_key = key
            logger.info(f"[GatherGem] No gem found — moving {key}")
            self.state_machine.pc_input.hold_key(key, 0.5)
            time.sleep(2.0)

        logger.info("[GatherGem] No gems found after max movement steps")
        return False
