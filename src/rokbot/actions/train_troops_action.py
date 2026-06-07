"""Train troops action for producing units in the city."""

import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.humanization.timing_engine import TimingEngine
from rokbot.vision.template_matcher import TemplateMatcher

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class TrainTroopsAction(BaseAction):
    """Action to train troops by tapping training buildings."""

    TEMPLATES_DIR = Path("data/templates/train")
    SHARED_TEMPLATES_DIR = Path("data/templates")

    # Bottom-right corner ROI where city/map toggle icon lives
    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)

    COMPLETED_ICONS = ["t2_bo_completed", "t2_cung_completed", "t1_da_completed", "t2_ngua_completed", "t3_bo_completed"]
    TRAIN_ICONS = ["bo_train", "cung_train", "da_train", "ngua_train"]
    AVAIL_TEMPLATES = ["train_available", "train_available1", "train_available2"]

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
        self._tab_matcher = TemplateMatcher(
            templates_dir=self.SHARED_TEMPLATES_DIR,
            threshold=0.75,
        )

        self._timing = TimingEngine(
            profile_path=config.humanization.profile_path
            if config.humanization.profile_path and config.humanization.profile_path.exists()
            else None
        )
        self._humanization_enabled = config.humanization.enabled

    def _human_delay(self, distribution: str = "click_interval", fallback_seconds: float = 0.5) -> None:
        if self._humanization_enabled:
            delay_ms = self._timing.sample(distribution)
            time.sleep(max(0.05, delay_ms / 1000.0))
        else:
            time.sleep(fallback_seconds)

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

    def _ensure_in_city(self, image: np.ndarray) -> bool:
        roi = self._roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]

        in_city_matches = self._city_matcher.match(roi_image, template_name="in_city_icon", threshold=0.80)
        if in_city_matches:
            best = max(in_city_matches, key=lambda m: m.confidence)
            logger.debug(f"Already in city view (in_city_icon conf={best.confidence:.2f})")
            return True

        enter_matches = self._city_matcher.match(roi_image, template_name="enter_city_icon", threshold=0.80)
        if enter_matches:
            best = max(enter_matches, key=lambda m: m.confidence)
            bx1, by1, bx2, by2 = best.bbox
            cx = roi_x1 + random.randint(bx1, max(bx1, bx2 - 1))
            cy = roi_y1 + random.randint(by1, max(by1, by2 - 1))
            logger.info(f"[Train] In world — entering city at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(1.0, 3.0))
            return True

        logger.warning("Could not determine city/world state")
        return False

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

    def _open_tongquan_and_get_idle_bbox(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Open the 'Tong Quan' tab if needed and look for 'khong_hoat_dong_text.png'.

        Returns the bounding box of the text template if found.
        """
        # Check if tab is already open
        opened_matches = self._tab_matcher.match(image, template_name="tongquan_opened", threshold=0.75)
        if not opened_matches:
            # Try to open the tab
            tab_matches = self._tab_matcher.match(image, template_name="tongquan", threshold=0.75)
            if tab_matches:
                tab_btn = max(tab_matches, key=lambda m: m.confidence)
                tx, ty = self._random_point_in_bbox(tab_btn.bbox)
                logger.info(f"[Train] Opening Tong Quan tab at ({tx}, {ty}) conf={tab_btn.confidence:.2f}")
                self.state_machine.pc_input.tap(tx, ty)
                time.sleep(random.uniform(1.5, 2.5))
                # Re-capture after opening
                self.state_machine.pc_input.move_to_safe_zone()
                image = self.state_machine.screen_capture.capture()
                if image is None:
                    return None
            else:
                logger.debug("[Train] tongquan icon not found")
                return None

        # Template match for 'Không hoạt động' text
        text_matches = self._tab_matcher.match(image, template_name="khong_hoat_dong_text", threshold=0.70)
        if text_matches:
            best = max(text_matches, key=lambda m: m.confidence)
            logger.info(f"[Train] Detected 'khong_hoat_dong_text' at {best.bbox} conf={best.confidence:.2f}")
            return best.bbox

        logger.debug("[Train] khong_hoat_dong_text not found")
        return None

    def can_execute(self) -> bool:
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        city_state = self._detect_city_state(image)
        if city_state == "in_world":
            logger.info("[Train] In world map — will enter city in execute()")
            return True
        if city_state == "unknown":
            logger.warning("[Train] Unknown city/world state — pressing ESC to dismiss popup")
            self.state_machine.pc_input.key_back()
            time.sleep(random.uniform(1.0, 2.0))
            return False

        # Check completed troops first (always collect before training)
        for completed_name in self.COMPLETED_ICONS:
            completed_matches = self._matcher.match(image, template_name=completed_name, threshold=0.70)
            if completed_matches:
                best = max(completed_matches, key=lambda m: m.confidence)
                logger.info(f"[Train] {completed_name} FOUND at {best.center} conf={best.confidence:.2f}")
                return True
            else:
                # Debug: show best confidence even if below threshold
                debug_matches = self._matcher.match(image, template_name=completed_name, threshold=0.30)
                if debug_matches:
                    best = max(debug_matches, key=lambda m: m.confidence)
                    logger.debug(f"[Train] {completed_name} best conf={best.confidence:.2f} (below 0.70)")

        # Check Tong Quan tab for idle buildings
        if self._open_tongquan_and_get_idle_bbox(image) is not None:
            return True

        logger.info("[Train] can_execute: nothing found")
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

        # 0. Ensure we are in city view
        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed")
            return False

        city_state = self._detect_city_state(image)
        if city_state == "in_world":
            logger.info("[Train] In world map — entering city")
            if not self._ensure_in_city(image):
                self.on_failure("Could not enter city view")
                return False
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
        elif city_state == "unknown":
            logger.warning("[Train] Unknown city/world state — retrying in 1s")
            time.sleep(1.0)
            self.state_machine.pc_input.move_to_safe_zone()
            image = self.state_machine.screen_capture.capture()
            if image is not None:
                city_state = self._detect_city_state(image)
            if city_state == "unknown":
                logger.warning("[Train] Still unknown — pressing ESC to dismiss popup")
                self.state_machine.pc_input.key_back()
                time.sleep(random.uniform(1.0, 2.0))
                self.on_failure("Could not determine city/world state")
                return False
            elif city_state == "in_world":
                logger.info("[Train] In world map after retry — entering city")
                if not self._ensure_in_city(image):
                    self.on_failure("Could not enter city view")
                    return False
                self.state_machine.pc_input.move_to_safe_zone()
                image = self.state_machine.screen_capture.capture()
        if image is None:
            self.on_failure("Screenshot failed after city transition")
            return False

        # 1. Check and collect completed troops first
        for completed_name in self.COMPLETED_ICONS:
            completed_matches = self._matcher.match(image, template_name=completed_name, threshold=0.75)
            if completed_matches:
                completed_btn = max(completed_matches, key=lambda m: m.confidence)
                cx, cy = self._random_point_in_bbox(completed_btn.bbox)
                logger.info(f"[Train] Step 1/3: Collecting {completed_name} at ({cx}, {cy})")
                self.state_machine.pc_input.tap(cx, cy)
                time.sleep(random.uniform(1.0, 3.0))
                return True

        # 2. Verify idle buildings via Tong Quan tab and click directly on the text
        idle_bbox = self._open_tongquan_and_get_idle_bbox(image)
        if idle_bbox is None:
            logger.info("[Train] No idle buildings confirmed in Tong Quan")
            return False

        # Click on the 'Không hoạt động' text to jump to the building
        bx1, by1, bx2, by2 = idle_bbox
        cx = (bx1 + bx2) // 2
        cy = (by1 + by2) // 2
        logger.info(f"[Train] Step 2/3: Tapping 'Không hoạt động' at ({cx}, {cy})")
        self.state_machine.pc_input.tap(cx, cy)
        time.sleep(random.uniform(2.0, 3.0))  # wait for game to pan to building and open popup

        # 4. In popup, find one of the 4 troop type icons
        self.state_machine.pc_input.move_to_safe_zone()
        popup_image = self.state_machine.screen_capture.capture()
        if popup_image is None:
            return False

        train_match = None
        train_name = None
        for icon_name in self.TRAIN_ICONS:
            icon_matches = self._matcher.match(popup_image, template_name=icon_name, threshold=0.75)
            if icon_matches:
                train_match = max(icon_matches, key=lambda m: m.confidence)
                train_name = icon_name
                logger.info(f"[Train] Step 3/5: Found '{icon_name}' conf={train_match.confidence:.2f}")
                break

        if train_match is None:
            logger.info("[Train] No troop type icon found — closing popup")
            close_matches = self._matcher.match(popup_image, template_name="close_popup")
            if close_matches:
                close_btn = max(close_matches, key=lambda m: m.confidence)
                clx, cly = self._random_point_in_bbox(close_btn.bbox)
                logger.info(f"[Train] Closing popup at ({clx}, {cly})")
                self.state_machine.pc_input.tap(clx, cly)
                time.sleep(random.uniform(1.0, 3.0))
            return False

        tx, ty = self._random_point_in_bbox(train_match.bbox)
        logger.info(f"[Train] Step 4/6: Tapping '{train_name}' at ({tx}, {ty})")
        self.state_machine.pc_input.tap(tx, ty)
        time.sleep(random.uniform(1.0, 3.0))

        # 5. Find and tap the corresponding *_selected.png
        self.state_machine.pc_input.move_to_safe_zone()
        selected_image = self.state_machine.screen_capture.capture()
        if selected_image is None:
            return False

        selected_name = train_name.replace("_train", "_selected")
        selected_matches = self._matcher.match(selected_image, template_name=selected_name, threshold=0.75)
        if selected_matches:
            selected_btn = max(selected_matches, key=lambda m: m.confidence)
            sx, sy = self._random_point_in_bbox(selected_btn.bbox)
            logger.info(f"[Train] Step 5/6: Tapping '{selected_name}' at ({sx}, {sy})")
            self.state_machine.pc_input.tap(sx, sy)
            time.sleep(random.uniform(1.0, 3.0))
        else:
            logger.info(f"[Train] '{selected_name}' not found — proceeding without selection")

        # 6. Find and tap train_confirm
        self.state_machine.pc_input.move_to_safe_zone()
        confirm_image = self.state_machine.screen_capture.capture()
        if confirm_image is None:
            return False

        confirm_matches = self._matcher.match(confirm_image, template_name="train_confirm", threshold=0.75)
        if confirm_matches:
            confirm_btn = max(confirm_matches, key=lambda m: m.confidence)
            cfx, cfy = self._random_point_in_bbox(confirm_btn.bbox)
            logger.info(f"[Train] Step 6/6: Tapping train_confirm at ({cfx}, {cfy})")
            self.state_machine.pc_input.tap(cfx, cfy)
            time.sleep(random.uniform(1.0, 3.0))
            return True

        # No train_confirm — close popup
        logger.info("[Train] train_confirm not found — closing popup")
        close_matches = self._matcher.match(confirm_image, template_name="close_popup")
        if close_matches:
            close_btn = max(close_matches, key=lambda m: m.confidence)
            clx, cly = self._random_point_in_bbox(close_btn.bbox)
            logger.info(f"[Train] Closing popup at ({clx}, {cly})")
            self.state_machine.pc_input.tap(clx, cly)
            time.sleep(random.uniform(1.0, 3.0))
        return False