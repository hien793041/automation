"""Scout Cave action — sends scouts to cave coordinates on the world map."""

import random
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.utils.map_navigation import MapNavigationMixin
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class ScoutCaveHighAction(BaseAction, MapNavigationMixin):
    """Action to scout caves by entering coordinates on the world map."""

    TEMPLATES_DIR = Path("data/templates/scoutcave")
    SHARED_TEMPLATES_DIR = Path("data/templates")
    CAVE_CSV = Path("data/cave_map.csv")

    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)

    # Cave icon variants for blinking exclamation mark handling
    CAVE_TEMPLATES = ["cave", "cave1", "cave2"]

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
        # List of (x, y, type, csv_index)
        self._caves: List[Tuple[int, int, str, int]] = []
        self._cave_index = 0
        self._df: Optional[pd.DataFrame] = None
        self._load_caves()

    def _load_caves(self) -> None:
        """Load cave coordinates from CSV. Prioritize 'High' type, skip Done caves."""
        if not self.CAVE_CSV.exists():
            logger.warning(f"[ScoutCaveHigh] Cave CSV not found: {self.CAVE_CSV}")
            return
        try:
            self._df = pd.read_csv(self.CAVE_CSV)
            if "Done" not in self._df.columns:
                self._df["Done"] = 0

            done_count = (self._df["Done"] == 1).sum()
            pending = self._df[(self._df["Done"] != 1) & (self._df["Type"].str.strip().str.lower() == "high")].copy()
            # Sort: by Zone, then by X/Y for optimal scout movement
            pending = pending.sort_values(by=["Zone", "X_Coordinate", "Y_Coordinate"])

            self._caves = []
            for original_idx, row in pending.iterrows():
                try:
                    x = int(row["X_Coordinate"])
                    y = int(row["Y_Coordinate"])
                    cave_type = str(row.get("Type", "")).strip()
                    self._caves.append((x, y, cave_type, original_idx))
                except (ValueError, KeyError):
                    continue

            high_count = sum(1 for _, _, t, _ in self._caves if t.lower() == "high")
            logger.info(f"[ScoutCaveHigh] Loaded {len(self._caves)} pending caves ({high_count} High), skipped {done_count} done caves from {self.CAVE_CSV}")
        except Exception as e:
            logger.error(f"[ScoutCaveHigh] Failed to load caves: {e}")

    def _mark_done(self, csv_index: int) -> None:
        """Mark a cave as done in the CSV file."""
        if self._df is not None and 0 <= csv_index < len(self._df):
            self._df.at[csv_index, "Done"] = 1
            try:
                self._df.to_csv(self.CAVE_CSV, index=False)
                logger.info(f"[ScoutCaveHigh] Marked cave index {csv_index} as Done")
            except Exception as e:
                logger.error(f"[ScoutCaveHigh] Failed to save CSV: {e}")

    def _find_cave(self, image: np.ndarray, retries: int = 3) -> Optional[Tuple[int, int, Tuple[int, int, int, int]]]:
        """Find cave icon with retries for blinking exclamation mark.
        Returns (center_x, center_y, bbox).
        """
        for attempt in range(retries):
            for tpl_name in self.CAVE_TEMPLATES:
                matches = self._matcher.match(image, template_name=tpl_name, threshold=0.70)
                if matches:
                    best = max(matches, key=lambda m: m.confidence)
                    logger.info(f"[ScoutCaveHigh] Found '{tpl_name}' conf={best.confidence:.2f} at {best.center}")
                    return (*best.center, best.bbox)
            if attempt < retries - 1:
                logger.debug(f"[ScoutCaveHigh] Cave not found, retry {attempt + 1}/{retries}")
                self.human_delay("reaction_time", fallback_seconds=0.5)
                self.state_machine.pc_input.move_to_safe_zone()
                image = self.state_machine.screen_capture.capture()
        logger.info("[ScoutCaveHigh] No cave icon found after retries")
        return None

    def _check_tongquan_tab(self, image: np.ndarray) -> bool:
        """Open tongquan tab if needed. Returns True if tab is open."""
        tongquan_matches = self._matcher.match(image, template_name="tongquan", threshold=0.75)
        if tongquan_matches:
            btn = max(tongquan_matches, key=lambda m: m.confidence)
            bx, by = self.random_point_in_bbox(btn.bbox, jitter_sigma=1.0, edge_margin=2)
            logger.info(f"[ScoutCaveHigh] Opening tongquan tab at ({bx}, {by})")
            self.state_machine.pc_input.tap(bx, by)
            self.human_delay("menu_wait", fallback_seconds=1.0)
            return True

        tongquan_opened = self._matcher.match(image, template_name="tongquan_opened", threshold=0.75)
        if tongquan_opened:
            logger.debug("[ScoutCaveHigh] tongquan tab already open")
            return True

        return False

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False
        if not self._caves:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        city_state = self._detect_city_state(image)
        if city_state == "unknown":
            logger.info("[ScoutCaveHigh] can_execute: city state unknown")
            return False

        # Open tongquan and check scout_available (works in both city and world)
        if not self._check_tongquan_tab(image):
            logger.info("[ScoutCaveHigh] tongquan tab not available")
            return False
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        scout_avail = self._matcher.match(image, template_name="scout_available", threshold=0.75)
        scout_avail1 = self._matcher.match(image, template_name="scout_available1", threshold=0.75)
        if scout_avail or scout_avail1:
            logger.info("[ScoutCaveHigh] scout_available found — ready to scout cave")
            return True
        else:
            logger.info("[ScoutCaveHigh] scout_available not found — skipping")
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
        if not self._caves:
            self.on_failure("No caves loaded")
            return False

        # 0. Open tongquan tab (works in both city and world) and check scout_available
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        city_state = self._detect_city_state(image)
        if city_state == "unknown":
            logger.warning("[ScoutCaveHigh] Unknown state — retrying after delay")
            self.human_delay("decision_time", fallback_seconds=1.0)
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
            if image is not None:
                city_state = self._detect_city_state(image)
            if city_state == "unknown":
                self.state_machine.pc_input.key_back()
                self.human_delay("post_error_wait", fallback_seconds=1.5)
                self.on_failure("Could not determine city/world state")
                return False

        if not self._check_tongquan_tab(image):
            self.on_failure("tongquan tab not available")
            return False
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        scout_avail = self._matcher.match(image, template_name="scout_available", threshold=0.75)
        scout_avail1 = self._matcher.match(image, template_name="scout_available1", threshold=0.75)
        if not scout_avail and not scout_avail1:
            logger.info("[ScoutCaveHigh] scout_available not found in tongquan — skipping")
            return False
        logger.info("[ScoutCaveHigh] scout_available found in tongquan — proceeding")

        # Ensure world map for cave scouting (if currently in city)
        if city_state == "in_city":
            logger.info("[ScoutCaveHigh] Switching to world map")
            if not self._ensure_in_world(image):
                self.on_failure("Could not switch to world view")
                return False
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
            if image is None:
                self.on_failure("Screenshot failed after world transition")
                return False

        # Pick next cave
        cave_x, cave_y, cave_type, csv_idx = self._caves[self._cave_index]
        self._cave_index = (self._cave_index + 1) % len(self._caves)
        logger.info(f"[ScoutCaveHigh] Target cave: ({cave_x}, {cave_y}) Type={cave_type}")

        # 1. Tap Find area icon on world map
        find_matches = self._matcher.match(image, template_name="find_area", threshold=0.75)
        if not find_matches:
            logger.info("[ScoutCaveHigh] find_area not found")
            return False
        find_btn = max(find_matches, key=lambda m: m.confidence)
        fcx, fcy = find_btn.center
        offset = random.randint(50, 200)
        fx = fcx - offset
        fy = fcy
        logger.info(f"[ScoutCaveHigh] Step 1/7: Tapping left of 'Find' at ({fx}, {fy}) offset={offset}")
        self.state_machine.pc_input.tap(fx, fy)
        self.human_delay("menu_wait", fallback_seconds=1.5)

        # 2. Find the Find button inside popup to derive X/Y input positions
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        find_btn_matches = self._matcher.match(image, template_name="find_btn", threshold=0.75)
        if not find_btn_matches:
            logger.info("[ScoutCaveHigh] find_btn not found in popup")
            return False
        find_btn = max(find_btn_matches, key=lambda m: m.confidence)
        fbx, fby = find_btn.center

        # 3. Tap X input (left of find_btn by ~300px, randomized for humanization)
        offset_x = random.randint(280, 300)
        input_x_x = fbx - offset_x
        input_x_y = fby
        logger.info(f"[ScoutCaveHigh] Step 2/7: Tapping X input at ({input_x_x}, {input_x_y}) offset={offset_x}")
        self.state_machine.pc_input.tap(input_x_x, input_x_y)
        self.human_delay("reaction_time", fallback_seconds=0.3)
        self.state_machine.pc_input.type_text(str(cave_x))
        self.human_delay("click_interval", fallback_seconds=0.5)

        # 4. Tap Y input (left of find_btn by ~100px, randomized for humanization)
        offset_y = random.randint(70, 110)
        input_y_x = fbx - offset_y
        input_y_y = fby
        logger.info(f"[ScoutCaveHigh] Step 3/7: Tapping Y input at ({input_y_x}, {input_y_y}) offset={offset_y}")
        self.state_machine.pc_input.tap(input_y_x, input_y_y)
        self.human_delay("reaction_time", fallback_seconds=0.3)
        self.state_machine.pc_input.type_text(str(cave_y))
        self.human_delay("click_interval", fallback_seconds=0.5)

        # 5. Tap Find button to search coordinates
        cfx, cfy = self.random_point_in_bbox(find_btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[ScoutCaveHigh] Step 4/7: Tapping coordinate 'Find' at ({cfx}, {cfy})")
        self.state_machine.pc_input.tap(cfx, cfy)
        self.human_delay("transition_wait", fallback_seconds=3.0, min_seconds=2.0)  # Wait for map to load

        # 5. Find cave icon (with retries for blinking exclamation)
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        cave_result = self._find_cave(image, retries=3)
        if cave_result is None:
            logger.info("[ScoutCaveHigh] No cave found at this coordinate — skipping")
            return False
        cvx, cvy, cave_bbox = cave_result
        cx1, cy1, cx2, cy2 = cave_bbox
        click_x = cvx
        click_y = cy2
        logger.info(f"[ScoutCaveHigh] Step 5/7: Tapping cave bottom center at ({click_x}, {click_y})")
        self.state_machine.pc_input.tap(click_x, click_y)
        self.human_delay("menu_wait", fallback_seconds=1.5)

        # 6. Tap Scout button
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        scout_matches = self._matcher.match(image, template_name="scout_btn", threshold=0.75)
        if not scout_matches:
            logger.info("[ScoutCaveHigh] scout_btn not found")
            return False
        scout_btn = max(scout_matches, key=lambda m: m.confidence)
        sx, sy = self.random_point_in_bbox(scout_btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[ScoutCaveHigh] Step 6/7: Tapping 'Scout' at ({sx}, {sy})")
        self.state_machine.pc_input.tap(sx, sy)
        self.human_delay("click_interval", fallback_seconds=1.5)

        # 7. Tap Send button
        self.state_machine.pc_input.move_to_safe_zone()
        self.pre_action_delay()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        send_matches = self._matcher.match(image, template_name="send_btn", threshold=0.75)
        if not send_matches:
            logger.info("[ScoutCaveHigh] send_btn not found")
            return False
        send_btn = max(send_matches, key=lambda m: m.confidence)
        send_x, send_y = self.random_point_in_bbox(send_btn.bbox, jitter_sigma=1.0, edge_margin=2)
        logger.info(f"[ScoutCaveHigh] Step 7/7: Tapping 'Send' at ({send_x}, {send_y})")
        self.state_machine.pc_input.tap(send_x, send_y)
        self.human_delay("click_interval", fallback_seconds=1.5)

        # Mark cave as done after successful send
        self._mark_done(csv_idx)
        return True
