"""Scout Cave action — sends scouts to cave coordinates on the world map."""

import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class ScoutCaveLowAction(BaseAction):
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
            logger.warning(f"[ScoutCaveLow] Cave CSV not found: {self.CAVE_CSV}")
            return
        try:
            self._df = pd.read_csv(self.CAVE_CSV)
            if "Done" not in self._df.columns:
                self._df["Done"] = 0

            done_count = (self._df["Done"] == 1).sum()
            pending = self._df[(self._df["Done"] != 1) & (self._df["Type"].str.strip().str.lower() != "high")].copy()
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
            logger.info(f"[ScoutCaveLow] Loaded {len(self._caves)} pending caves ({high_count} High), skipped {done_count} done caves from {self.CAVE_CSV}")
        except Exception as e:
            logger.error(f"[ScoutCaveLow] Failed to load caves: {e}")

    def _mark_done(self, csv_index: int) -> None:
        """Mark a cave as done in the CSV file."""
        if self._df is not None and 0 <= csv_index < len(self._df):
            self._df.at[csv_index, "Done"] = 1
            try:
                self._df.to_csv(self.CAVE_CSV, index=False)
                logger.info(f"[ScoutCaveLow] Marked cave index {csv_index} as Done")
            except Exception as e:
                logger.error(f"[ScoutCaveLow] Failed to save CSV: {e}")

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

    def _ensure_in_world(self, image: np.ndarray) -> bool:
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            logger.debug("[ScoutCaveLow] Already in world view")
            return True

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            best = max(in_city_matches, key=lambda m: m.confidence)
            bx1, by1, bx2, by2 = best.bbox
            cx = roi_x1 + random.randint(bx1, max(bx1, bx2 - 1))
            cy = roi_y1 + random.randint(by1, max(by1, by2 - 1))
            logger.info(f"[ScoutCaveLow] Switching to world map at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(1.0, 3.0))
            return True

        logger.warning("[ScoutCaveLow] Could not determine city/world state")
        return False

    def _ensure_in_city(self, image: np.ndarray) -> bool:
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            logger.debug("[ScoutCaveLow] Already in city view")
            return True

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            best = max(enter_matches, key=lambda m: m.confidence)
            bx1, by1, bx2, by2 = best.bbox
            cx = roi_x1 + random.randint(bx1, max(bx1, bx2 - 1))
            cy = roi_y1 + random.randint(by1, max(by1, by2 - 1))
            logger.info(f"[ScoutCaveLow] Switching to city view at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(1.0, 3.0))
            return True

        logger.warning("[ScoutCaveLow] Could not determine city/world state")
        return False

    def _find_cave(self, image: np.ndarray, retries: int = 3) -> Optional[Tuple[int, int, Tuple[int, int, int, int]]]:
        """Find cave icon with retries for blinking exclamation mark.
        Returns (center_x, center_y, bbox).
        """
        for attempt in range(retries):
            for tpl_name in self.CAVE_TEMPLATES:
                matches = self._matcher.match(image, template_name=tpl_name, threshold=0.70)
                if matches:
                    best = max(matches, key=lambda m: m.confidence)
                    logger.info(f"[ScoutCaveLow] Found '{tpl_name}' conf={best.confidence:.2f} at {best.center}")
                    return (*best.center, best.bbox)
            if attempt < retries - 1:
                logger.debug(f"[ScoutCaveLow] Cave not found, retry {attempt + 1}/{retries}")
                time.sleep(0.5)
                self.state_machine.pc_input.move_to_safe_zone()
                image = self.state_machine.screen_capture.capture()
        logger.info("[ScoutCaveLow] No cave icon found after retries")
        return None

    def _check_tongquan_tab(self, image: np.ndarray) -> bool:
        """Open tongquan tab if needed. Returns True if tab is open."""
        tongquan_matches = self._matcher.match(image, template_name="tongquan", threshold=0.75)
        if tongquan_matches:
            btn = max(tongquan_matches, key=lambda m: m.confidence)
            bx, by = self._random_point_in_bbox(btn.bbox)
            logger.info(f"[ScoutCaveLow] Opening tongquan tab at ({bx}, {by})")
            self.state_machine.pc_input.tap(bx, by)
            time.sleep(random.uniform(0.8, 1.2))
            return True

        tongquan_opened = self._matcher.match(image, template_name="tongquan_opened", threshold=0.75)
        if tongquan_opened:
            logger.debug("[ScoutCaveLow] tongquan tab already open")
            return True

        return False

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        city_state = self._detect_city_state(image)
        if city_state == "unknown":
            logger.info("[ScoutCaveLow] can_execute: city state unknown")
            return False

        # Open tongquan and check scout_available (works in both city and world)
        if not self._check_tongquan_tab(image):
            logger.info("[ScoutCaveLow] tongquan tab not available")
            return False
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        scout_avail = self._matcher.match(image, template_name="scout_available", threshold=0.75)
        scout_avail1 = self._matcher.match(image, template_name="scout_available1", threshold=0.75)
        if scout_avail or scout_avail1:
            logger.info("[ScoutCaveLow] scout_available found — ready to scout cave")
            return True
        else:
            logger.info("[ScoutCaveLow] scout_available not found — skipping")
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

        # 0. Ensure city view
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        city_state = self._detect_city_state(image)
        if city_state == "in_world":
            logger.info("[ScoutCaveLow] Switching to city view")
            if not self._ensure_in_city(image):
                self.on_failure("Could not switch to city view")
                return False
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
        elif city_state == "unknown":
            logger.warning("[ScoutCaveLow] Unknown state — retrying in 1s")
            time.sleep(1.0)
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
            if image is not None:
                city_state = self._detect_city_state(image)
            if city_state == "unknown":
                self.state_machine.pc_input.key_back()
                time.sleep(random.uniform(1.0, 2.0))
                self.on_failure("Could not determine city/world state")
                return False
            elif city_state == "in_world":
                if not self._ensure_in_city(image):
                    self.on_failure("Could not switch to city view")
                    return False
                self.state_machine.pc_input.move_to_safe_zone()
                image = self.state_machine.screen_capture.capture()

        if image is None:
            self.on_failure("Screenshot failed after city transition")
            return False

        # 1. Open tongquan and check scout_available
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
            logger.info("[ScoutCaveLow] scout_available not found in tongquan — skipping")
            return False
        logger.info("[ScoutCaveLow] scout_available found in tongquan — proceeding")

        # 2. Click scout building in city
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        building_matches = self._matcher.match(image, template_name="scout_building", threshold=0.75)
        if not building_matches:
            logger.info("[ScoutCaveLow] scout_building not found")
            return False
        building_btn = max(building_matches, key=lambda m: m.confidence)
        bbx, bby = self._random_point_in_bbox(building_btn.bbox)
        logger.info(f"[ScoutCaveLow] Step 2/6: Tapping scout_building at ({bbx}, {bby})")
        self.state_machine.pc_input.tap(bbx, bby)
        time.sleep(random.uniform(1.0, 2.0))

        # 3. Click scout_button in popup
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        scout_btn_matches = self._matcher.match(image, template_name="scout_button", threshold=0.75)
        if not scout_btn_matches:
            logger.info("[ScoutCaveLow] scout_button not found")
            return False
        scout_btn = max(scout_btn_matches, key=lambda m: m.confidence)
        sbx, sby = self._random_point_in_bbox(scout_btn.bbox)
        logger.info(f"[ScoutCaveLow] Step 3/6: Tapping scout_button at ({sbx}, {sby})")
        self.state_machine.pc_input.tap(sbx, sby)
        time.sleep(random.uniform(1.0, 2.0))

        # 4. Click cave_tab
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        cave_tab_matches = self._matcher.match(image, template_name="cave_tab", threshold=0.75)
        if not cave_tab_matches:
            logger.info("[ScoutCaveLow] cave_tab not found")
            return False
        cave_tab = max(cave_tab_matches, key=lambda m: m.confidence)
        ctx, cty = self._random_point_in_bbox(cave_tab.bbox)
        logger.info(f"[ScoutCaveLow] Step 4/6: Tapping cave_tab at ({ctx}, {cty})")
        self.state_machine.pc_input.tap(ctx, cty)
        time.sleep(random.uniform(1.0, 2.0))

        # 5. Find go_btn and click at its bottom
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        go_matches = self._matcher.match(image, template_name="go_btn", threshold=0.75)
        if not go_matches:
            logger.info("[ScoutCaveLow] go_btn not found")
            return False
        go_btn = max(go_matches, key=lambda m: m.confidence)
        gx1, gy1, gx2, gy2 = go_btn.bbox
        click_x = (gx1 + gx2) // 2
        click_y = gy2
        logger.info(f"[ScoutCaveLow] Step 5/6: Tapping go_btn bottom at ({click_x}, {click_y})")
        self.state_machine.pc_input.tap(click_x, click_y)
        time.sleep(3.0)

        # 6. Tap scout_btn (in scoutcave folder)
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        scout_matches = self._matcher.match(image, template_name="scout_btn", threshold=0.75)
        if not scout_matches:
            logger.info("[ScoutCaveLow] scout_btn not found")
            return False
        scout_btn = max(scout_matches, key=lambda m: m.confidence)
        sx, sy = self._random_point_in_bbox(scout_btn.bbox)
        logger.info(f"[ScoutCaveLow] Step 6/6: Tapping 'Scout' at ({sx}, {sy})")
        self.state_machine.pc_input.tap(sx, sy)
        time.sleep(random.uniform(1.0, 2.0))

        # 7. Tap Send button
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False
        send_matches = self._matcher.match(image, template_name="send_btn", threshold=0.75)
        if not send_matches:
            logger.info("[ScoutCaveLow] send_btn not found")
            return False
        send_btn = max(send_matches, key=lambda m: m.confidence)
        send_x, send_y = self._random_point_in_bbox(send_btn.bbox)
        logger.info(f"[ScoutCaveLow] Step 7/7: Tapping 'Send' at ({send_x}, {send_y})")
        self.state_machine.pc_input.tap(send_x, send_y)
        time.sleep(random.uniform(1.0, 2.0))
        return True
