"""Gather Gem action — specialized flow for collecting gems on the world map.

Uses the game window capture (single-window mode).
Implements a random-walk strategy using arrow keys, with a 50 km radius limit
from the city center. Distance is read via OCR around the city_center icon.
"""

import random
import re
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.utils.map_navigation import MapNavigationMixin
from rokbot.vision.ocr_engine import OCREngine
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class GemRandomWalker:
    """Random-walk state machine for arrow-key map navigation.

    Each key press moves ~1 tile (1 km). Tracks visited tiles so the bot
    does not loop over the same area. Backtracks when it hits a dead end.
    Includes humanization parameters so movement looks natural.
    """

    DIRECTIONS = {
        "up": (0, 1),
        "down": (0, -1),
        "left": (-1, 0),
        "right": (1, 0),
    }
    OPPOSITES = {"up": "down", "down": "up", "left": "right", "right": "left"}

    # Base hold duration (will be randomized per step)
    HOLD_DURATION_MIN = 0.35
    HOLD_DURATION_MAX = 0.65

    # Humanization params
    REACTION_DELAY_MIN = 0.10
    REACTION_DELAY_MAX = 0.40
    LONG_PAUSE_CHANCE = 0.10
    LONG_PAUSE_MIN = 3.0
    LONG_PAUSE_MAX = 5.0
    DOUBLE_STEP_CHANCE = 0.15

    def __init__(self, radius: int = 50):
        self.radius = radius
        self.home_pos = (0, 0)
        self.current_pos = (0, 0)
        self.visited: set = {(0, 0)}
        self.history: List[str] = []  # directions taken

    def distance_from_home(self) -> float:
        dx = self.current_pos[0] - self.home_pos[0]
        dy = self.current_pos[1] - self.home_pos[1]
        return (dx * dx + dy * dy) ** 0.5

    def is_within_radius(self, pos: Tuple[int, int]) -> bool:
        dx = pos[0] - self.home_pos[0]
        dy = pos[1] - self.home_pos[1]
        return (dx * dx + dy * dy) ** 0.5 <= self.radius

    def get_valid_directions(self) -> List[str]:
        """Return directions that stay inside radius and lead to unvisited tiles."""
        valid = []
        for direction, (dx, dy) in self.DIRECTIONS.items():
            next_pos = (self.current_pos[0] + dx, self.current_pos[1] + dy)
            if self.is_within_radius(next_pos) and next_pos not in self.visited:
                valid.append(direction)
        return valid

    def move(self, direction: str) -> Tuple[int, int]:
        """Move one step in the given direction."""
        dx, dy = self.DIRECTIONS[direction]
        self.current_pos = (self.current_pos[0] + dx, self.current_pos[1] + dy)
        self.visited.add(self.current_pos)
        self.history.append(direction)
        return self.current_pos

    def backtrack(self) -> Optional[str]:
        """Undo the last move by returning the opposite direction key."""
        if not self.history:
            return None
        last = self.history.pop()
        opposite = self.OPPOSITES[last]
        dx, dy = self.DIRECTIONS[opposite]
        self.current_pos = (self.current_pos[0] + dx, self.current_pos[1] + dy)
        return opposite


class GatherGemAction(BaseAction, MapNavigationMixin):
    """Action to gather gems using random-walk arrow-key exploration."""

    TEMPLATES_DIR = Path("data/templates/gathergem")
    SHARED_TEMPLATES_DIR = Path("data/templates")

    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)
    GEM_AVAILABLE_TEMPLATES = [
        "gem_available0",
        "gem_available1",
        "gem_available2",
        "gem_available3",
        "gem_available4",
        "gem_available5",
    ]
    MAX_MOVEMENT_STEPS = 200
    MAX_ACTIVE_TROOPS = 4
    TROOP_STATUS_TEMPLATES = [
        "gathering",
        "backing",
        "moving",
        "building",
        "attacking",
        "attacking1",
    ]

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self.MAX_ACTIVE_TROOPS = self.get_action_config("max_troops", 4)
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
        self._ocr = OCREngine(lang="eng")

    # ------------------------------------------------------------------ #
    # Helpers kept from original file
    # ------------------------------------------------------------------ #

    def _find_gems(self, image: np.ndarray) -> List:
        """Search for any gem_available template within the central map area."""
        h, w = image.shape[:2]
        margin_x = int(w * 0.08)
        margin_y = int(h * 0.08)
        roi = (margin_x, margin_y, w - margin_x, h - margin_y)

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

        raw_matches.sort(key=lambda m: m.confidence, reverse=True)
        kept = []
        min_dist = 40
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
                logger.info(
                    f"[GatherGem] Found '{m.template_name}' conf={m.confidence:.2f} at ({cx}, {cy})"
                )
        return kept

    def _click_gather_sequence(self) -> bool:
        """Click through the gathering UI sequence after selecting a gem."""
        steps = [
            ("gem_icon", "Clicking gem_icon"),
            ("gather_btn", "Clicking gather_btn"),
            ("new_troop", "Clicking new_troop"),
            ("send_troop", "Clicking send_troop"),
        ]
        for tpl_name, label in steps:
            self.state_machine.pc_input.move_to_safe_zone()
            self.pre_action_delay()
            image = self.state_machine.screen_capture.capture()
            if image is None:
                logger.warning(f"[GatherGem] Screenshot failed during {tpl_name}")
                return False
            matches = self._matcher.match(image, template_name=tpl_name, threshold=0.75)
            if not matches:
                logger.warning(f"[GatherGem] {tpl_name} not found — aborting sequence")
                return False
            best = max(matches, key=lambda m: m.confidence)
            x, y = self.random_point_in_bbox(best.bbox, jitter_sigma=1.0, edge_margin=2)
            logger.info(f"[GatherGem] {label} at ({x}, {y}) conf={best.confidence:.2f}")
            self.state_machine.pc_input.tap(x, y)
            self.human_delay("click_interval", fallback_seconds=1.0)
        logger.info("[GatherGem] Gather sequence completed successfully")
        return True

    def _scan_and_click_gem(self, image: np.ndarray) -> bool:
        """Scan for gem_available and if found click it and run the gather sequence."""
        gem_matches = self._find_gems(image)
        if gem_matches:
            gem = gem_matches[0]
            cx, cy = gem.center
            logger.info(f"[GatherGem] Clicking gem_available center at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            self.human_delay("menu_wait", fallback_seconds=1.5)
            return self._click_gather_sequence()
        return False

    def _click_city_center(self) -> bool:
        """Click city_center to reset camera to the city center."""
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        matches = self._matcher.match(image, template_name="city_center", threshold=0.75)
        if not matches:
            logger.info("[GatherGem] city_center not found")
            return False
        best = max(matches, key=lambda m: m.confidence)
        cx, cy = self.random_point_in_bbox(best.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[GatherGem] Clicking city_center at ({cx}, {cy}) conf={best.confidence:.2f}")
        self.state_machine.pc_input.tap(cx, cy)
        self.human_delay("transition_wait", fallback_seconds=1.5)
        return True

    def _open_resource_menu(self) -> bool:
        """Hold-click enter_city_icon and click resource_button to open the resource menu."""
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        roi = self.roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]
        enter_matches = self._city_matcher.match(
            roi_image, template_name="enter_city_icon", threshold=0.80
        )
        if not enter_matches:
            logger.info("[GatherGem] enter_city_icon not found")
            return False

        enter_btn = max(enter_matches, key=lambda m: m.confidence)
        ex1, ey1, ex2, ey2 = enter_btn.bbox
        abs_ex = roi_x1 + (ex1 + ex2) // 2
        abs_ey = roi_y1 + (ey1 + ey2) // 2
        self.state_machine.pc_input.hold_click_at(abs_ex, abs_ey, 3.0)

        self.human_delay("reaction_time", fallback_seconds=0.5)
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        resource_matches = self._matcher.match(
            image, template_name="resource_button", threshold=0.75
        )
        if not resource_matches:
            logger.info("[GatherGem] resource_button not found")
            return False
        resource_btn = max(resource_matches, key=lambda m: m.confidence)
        rx, ry = self.random_point_in_bbox(resource_btn.bbox, jitter_sigma=1.0, edge_margin=2)

        # Use the centralized humanized hold-click helper instead of direct pyautogui.
        self.state_machine.pc_input.hold_click_at(rx, ry, 3.0)
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

    # ------------------------------------------------------------------ #
    # NEW: Distance reader + random walk
    # ------------------------------------------------------------------ #

    def _read_distance_km(self, image: np.ndarray) -> Optional[int]:
        """Find city_center and read the white distance text near it (e.g. '50 KM').

        Expands ~60 px around the city_center template and runs OCR.
        Returns the numeric distance in kilometres, or None if unreadable.
        """
        matches = self._matcher.match(
            image, template_name="city_center", threshold=0.70
        )
        if not matches:
            return None
        best = max(matches, key=lambda m: m.confidence)
        x1, y1, x2, y2 = best.bbox
        ih, iw = image.shape[:2]
        margin = 60

        rx1 = max(0, x1 - margin)
        ry1 = max(0, y1 - margin)
        rx2 = min(iw, x2 + margin)
        ry2 = min(ih, y2 + margin)
        roi = (rx1, ry1, rx2, ry2)

        # Try psm 6 first (proven to read '30KM' reliably), fallback to psm 7
        for psm in ("--psm 6", "--psm 7"):
            results = self._ocr.read(image, roi=roi, config=psm)
            for res in results:
                text = res.text.upper().replace(" ", "")
                if "KM" in text:
                    m = re.search(r"(\d+)", text)
                    if m:
                        km = int(m.group(1))
                        logger.info(
                            f"[GatherGem] OCR distance read: {km} KM near city_center "
                            f"(psm={psm}, conf={res.confidence:.2f})"
                        )
                        return km

        logger.debug("[GatherGem] No 'KM' text found near city_center")
        return None

    def _is_gem_occupied(self, image: np.ndarray, gem) -> bool:
        """Check whether a gem_available match already has a gathering troop on it."""
        cx, cy = gem.center
        for gt in ("gem_gathering", "gem_gathering1"):
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
                        return True
        return False

    # ------------------------------------------------------------------ #
    # BaseAction interface
    # ------------------------------------------------------------------ #

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

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

        # ---- 1. Ensure world view -------------------------------------
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        city_state = self._detect_city_state(image)
        if city_state == "in_city":
            roi = self.roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
            roi_x1, roi_y1, roi_x2, roi_y2 = roi
            roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]
            in_matches = self._city_matcher.match(
                roi_image, template_name="in_city_icon", threshold=0.80
            )
            if in_matches:
                in_btn = max(in_matches, key=lambda m: m.confidence)
                ix1, iy1, ix2, iy2 = in_btn.bbox
                cx = roi_x1 + (ix1 + ix2) // 2
                cy = roi_y1 + (iy1 + iy2) // 2

                # Humanization: randomly use the Space hotkey instead of clicking.
                if self._use_hotkey_for_city_toggle():
                    logger.info("[GatherGem] In city — switching to world via Space hotkey")
                    self.state_machine.pc_input.press_key("space")
                else:
                    logger.info(f"[GatherGem] In city — switching to world at ({cx}, {cy})")
                    self.state_machine.pc_input.tap(cx, cy)
                self.human_delay("transition_wait", fallback_seconds=2.0)

        # ---- 2. Reset to city center ----------------------------------
        logger.info("[GatherGem] Clicking city_center to reset position")
        if not self._click_city_center():
            logger.warning("[GatherGem] city_center not found, continuing anyway")

        # ---- 3. Open resource menu ------------------------------------
        logger.info("[GatherGem] Opening resource menu")
        if not self._open_resource_menu():
            return False

        # ---- 4. Random walk with arrow keys ---------------------------
        walker = GemRandomWalker(radius=50)
        backtrack_count = 0
        max_backtracks = 30  # safety valve

        for step in range(self.MAX_MOVEMENT_STEPS):
            self.human_delay("reaction_time", fallback_seconds=1.5)
            image = self.state_machine.screen_capture.capture()
            if image is None:
                # fallback: random move when capture fails
                direction = random.choice(list(walker.DIRECTIONS.keys()))
                logger.info(f"[GatherGem] Capture failed — moving {direction}")
                hold_dur = random.uniform(walker.HOLD_DURATION_MIN, walker.HOLD_DURATION_MAX)
                self.state_machine.pc_input.hold_key_native(direction, hold_dur)
                self.human_delay("transition_wait", fallback_seconds=2.0)
                walker.move(direction)
                continue

            # --- A. Try to find and gather a gem ----------------------
            gem_matches = self._find_gems(image)
            if gem_matches:
                gem = gem_matches[0]
                if not self._is_gem_occupied(image, gem):
                    cx, cy = gem.center
                    logger.info(f"[GatherGem] Clicking gem_available at ({cx}, {cy})")
                    self.state_machine.pc_input.tap(cx, cy)
                    self.human_delay("menu_wait", fallback_seconds=1.5)

                    if self._click_gather_sequence():
                        logger.info("[GatherGem] Troop sent — returning to city center")
                        self._click_city_center()
                        return True

                    # Sequence failed — reopen menu and retry from here
                    logger.info("[GatherGem] Sequence failed — reopening resource menu")
                    if not self._open_resource_menu():
                        return False
                    continue
                else:
                    logger.info("[GatherGem] Gem occupied — will move away")

            # --- B. Read real distance from city center (sanity check)
            # Only run OCR every 5 steps and when near the radius limit to
            # avoid burning CPU/Tesseract on every single tile.
            should_check_ocr = (
                step % 5 == 0
                and walker.distance_from_home() > walker.radius * 0.8
            )
            if should_check_ocr:
                ocr_km = self._read_distance_km(image)
                if ocr_km is not None and ocr_km > walker.radius:
                    logger.warning(
                        f"[GatherGem] OCR says {ocr_km} KM > radius {walker.radius}; "
                        "forcing backtrack"
                    )
                    bt = walker.backtrack()
                    if bt:
                        hold_dur = random.uniform(walker.HOLD_DURATION_MIN, walker.HOLD_DURATION_MAX)
                        self.state_machine.pc_input.hold_key_native(bt, hold_dur)
                        self.human_delay("transition_wait", fallback_seconds=2.0)
                    continue

            # --- C. Pick next direction --------------------------------
            valid = walker.get_valid_directions()
            if valid:
                direction = random.choice(valid)
                walker.move(direction)
                backtrack_count = 0
                logger.info(
                    f"[GatherGem] Step {step + 1}/{self.MAX_MOVEMENT_STEPS} — "
                    f"moving {direction} | pos={walker.current_pos} | "
                    f"visited={len(walker.visited)}"
                )
            else:
                # Dead end → backtrack
                if backtrack_count >= max_backtracks:
                    logger.warning("[GatherGem] Too many backtracks — giving up")
                    break
                bt = walker.backtrack()
                if bt is None:
                    logger.info("[GatherGem] Back at home with no moves left — done")
                    break
                backtrack_count += 1
                logger.info(
                    f"[GatherGem] Dead end — backtracking with {bt} | "
                    f"pos={walker.current_pos}"
                )
                hold_dur = random.uniform(walker.HOLD_DURATION_MIN, walker.HOLD_DURATION_MAX)
                self.state_machine.pc_input.hold_key_native(bt, hold_dur)
                self.human_delay("transition_wait", fallback_seconds=2.0)
                continue

            # Humanization: reaction delay before pressing key (thinking time)
            self.human_delay("reaction_time", fallback_seconds=0.25)
            hold_dur = random.uniform(walker.HOLD_DURATION_MIN, walker.HOLD_DURATION_MAX)
            self.state_machine.pc_input.hold_key_native(direction, hold_dur)
            self.human_delay("transition_wait", fallback_seconds=2.0)

            # Humanization: occasional long pause (looking around the map)
            if random.random() < walker.LONG_PAUSE_CHANCE:
                pause = random.uniform(walker.LONG_PAUSE_MIN, walker.LONG_PAUSE_MAX)
                logger.info(f"[GatherGem] Humanization: long pause {pause:.1f}s to look around")
                self.human_delay("decision_time", fallback_seconds=pause, min_seconds=pause)

            # Humanization: double-step (occasionally hold a bit longer = 2 tiles)
            if random.random() < walker.DOUBLE_STEP_CHANCE:
                next_pos = (
                    walker.current_pos[0] + walker.DIRECTIONS[direction][0],
                    walker.current_pos[1] + walker.DIRECTIONS[direction][1],
                )
                if walker.is_within_radius(next_pos) and next_pos not in walker.visited:
                    walker.move(direction)
                    logger.info(f"[GatherGem] Humanization: double-step {direction} | pos={walker.current_pos}")
                    hold_dur = random.uniform(walker.HOLD_DURATION_MIN, walker.HOLD_DURATION_MAX)
                    self.state_machine.pc_input.hold_key_native(direction, hold_dur)
                    self.human_delay("transition_wait", fallback_seconds=2.0)

        logger.info("[GatherGem] No gems found after max movement steps")
        return False
