"""Rally Fort action — join or start a fort rally from within the city.

This action ensures the bot is inside the city before attempting to interact
with the rally UI.  If the bot is on the world map it will click the
"enter city" icon first.

TODO: implement the actual rally flow (fort list → select fort → join rally).
"""

import random
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from loguru import logger

from rokbot.actions.base_action import BaseAction
from rokbot.core.config import BotConfig
from rokbot.vision.template_matcher import TemplateMatcher
from rokbot.utils.map_navigation import MapNavigationMixin

if TYPE_CHECKING:
    from rokbot.core.state_machine import StateMachine


class RallyFortAction(BaseAction, MapNavigationMixin):
    """Action to rally a fort.  Must be executed inside the city."""

    TEMPLATES_DIR = Path("data/templates/rallyfort")
    SHARED_TEMPLATES_DIR = Path("data/templates")

    # ROI where the in-city / enter-city icon lives (bottom-right corner)
    CITY_ICON_ROI_RATIO: Tuple[float, float, float, float] = (0.75, 0.75, 1.0, 1.0)

    MAX_ACTIVE_TROOPS = 4
    TROOP_STATUS_TEMPLATES = ["gathering", "backing", "moving", "building", "attacking", "attacking1"]

    # Cooldown after a failed rally search (no suitable fort found)
    COOLDOWN_SECONDS = (20, 30)

    # Offset from fort_icon center to how_far text (left, up)
    # Calibrated from debug screenshot: fort_icon on right, km text on upper-left
    HOW_FAR_OFFSET: Tuple[int, int] = (-1060, -165)
    # Crop size around the expected how_far position (width, height)
    HOW_FAR_CROP_SIZE: Tuple[int, int] = (140, 50)
    MAX_KM = 45

    def __init__(self, config: BotConfig, state_machine: Optional["StateMachine"] = None):
        super().__init__(config, state_machine)
        self._last_failed_at: Optional[float] = None
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

    # ------------------------------------------------------------------
    # Helper methods (shared pattern with GatherGemAction)
    # ------------------------------------------------------------------

    def _read_km_from_crop(self, crop: np.ndarray, label: str = "") -> int:
        """OCR a km crop. Returns the numeric value or -1."""
        import uuid

        if crop.size == 0:
            logger.debug(f"[RallyFort] Empty km crop {label}")
            return -1

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Mask bright pixels (white text) → black text on white background
        _, bright_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        # Invert: text becomes black, background becomes white
        inverted = cv2.bitwise_not(bright_mask)

        # Skip the left pin icon (~35 px)
        h, w = inverted.shape
        pin_width = min(40, w // 3)
        text_crop = inverted[:, pin_width:]

        # Upscale 2x for better OCR
        text_crop = cv2.resize(text_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Also try OTSU on the inverted image
        otsu = cv2.threshold(text_crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        whitelist = "-c tessedit_char_whitelist=0123456789KMkm "
        candidates = []
        configs = [
            ("inv_psm7", text_crop, f"--psm 7 {whitelist}"),
            ("inv_psm8", text_crop, f"--psm 8 {whitelist}"),
            ("otsu_psm7", otsu, f"--psm 7 {whitelist}"),
            ("otsu_psm8", otsu, f"--psm 8 {whitelist}"),
        ]

        for name, img, cfg in configs:
            text = pytesseract.image_to_string(img, config=cfg).strip()
            candidates.append((name, text))

        logger.debug(f"[RallyFort] OCR {label}: {candidates}")

        # Pick candidate with digits, prefer longer match
        best_text = ""
        for name, txt in candidates:
            if re.search(r'\d', txt):
                if len(txt) > len(best_text):
                    best_text = txt

        numbers = re.findall(r'\d+', best_text)
        if numbers:
            km = max(int(n) for n in numbers)
            logger.info(f"[RallyFort] OCR {label} parsed km={km} from '{best_text}'")
            return km
        logger.warning(f"[RallyFort] OCR {label} failed on all candidates")
        return -1

    def _count_active_troops(self, image: np.ndarray) -> int:
        """Count gathering/backing/moving/building troop icons on the world map."""
        total = 0
        for tpl_name in self.TROOP_STATUS_TEMPLATES:
            matches = self._troop_matcher.match(
                image, template_name=tpl_name, threshold=0.75, max_matches=10
            )
            count = len(matches)
            if count:
                logger.debug(f"[RallyFort] Found {count} '{tpl_name}' icon(s)")
                total += count
        if total:
            logger.info(f"[RallyFort] Active troop count = {total}")
        return total

    def _ensure_in_city(self) -> bool:
        """If on the world map, click the enter-city icon and wait.

        Returns True once we are confident we are inside the city.
        """
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        self.state_machine.pc_input.move_to_safe_zone()
        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        city_state = self._detect_city_state(image)

        if city_state == "in_city":
            logger.info("[RallyFort] Already in city")
            return True

        if city_state == "in_world":
            # Click enter_city_icon to go inside
            roi = self.roi_from_ratio(image, self.CITY_ICON_ROI_RATIO)
            roi_x1, roi_y1, roi_x2, roi_y2 = roi
            roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]
            enter_matches = self._city_matcher.match(
                roi_image, template_name="enter_city_icon", threshold=0.80
            )
            if not enter_matches:
                logger.warning("[RallyFort] enter_city_icon not found despite state=in_world")
                return False

            btn = max(enter_matches, key=lambda m: m.confidence)
            cx = roi_x1 + (btn.bbox[0] + btn.bbox[2]) // 2
            cy = roi_y1 + (btn.bbox[1] + btn.bbox[3]) // 2
            logger.info(f"[RallyFort] Clicking enter_city_icon at ({cx}, {cy})")
            self.state_machine.pc_input.tap(cx, cy)
            time.sleep(random.uniform(4.0, 6.0))

            # Re-check
            image = self.state_machine.screen_capture.capture()
            if image is None:
                logger.warning("[RallyFort] Screenshot failed after entering city")
                return False
            city_state = self._detect_city_state(image)
            logger.info(f"[RallyFort] City state after click: {city_state}")
            if city_state == "in_city":
                return True
            return False

        logger.warning("[RallyFort] Cannot determine city/world state")
        return False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def can_execute(self) -> bool:
        """Return True if we are either in the city or able to enter it,
        active troops are below the max limit, and cooldown has expired."""
        if self.state_machine is None or self.state_machine.screen_capture is None:
            return False

        if self._last_failed_at is not None:
            elapsed = time.time() - self._last_failed_at
            cooldown = random.uniform(self.COOLDOWN_SECONDS[0], self.COOLDOWN_SECONDS[1])
            if elapsed < cooldown:
                logger.debug(
                    f"[RallyFort] Cooldown active ({elapsed:.1f}s / {cooldown:.1f}s) — bypassing"
                )
                return False
            self._last_failed_at = None

        image = self.state_machine.screen_capture.capture()
        if image is None:
            return False

        active_count = self._count_active_troops(image)
        if active_count >= self.MAX_ACTIVE_TROOPS:
            logger.info(
                f"[RallyFort] Active troops ({active_count}) >= max ({self.MAX_ACTIVE_TROOPS}) — bypassing"
            )
            return False

        city_state = self._detect_city_state(image)
        if city_state in ("in_city", "in_world"):
            return True

        logger.debug("[RallyFort] can_execute: city/world state unknown")
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

        # Step 1 — make sure we are inside the city
        if not self._ensure_in_city():
            self.on_failure("Could not enter city")
            return False

        # Step 2 — click sequence inside the city
        max_retries = 5

        for attempt in range(1, max_retries + 1):
            # --- find and click fort_building1 ---
            image = self.state_machine.screen_capture.capture()
            if image is None:
                logger.warning("[RallyFort] Screenshot failed during fort_building1")
                return False

            matches = self._matcher.match(image, template_name="fort_building1", threshold=0.75)
            if not matches:
                logger.warning("[RallyFort] fort_building1 not found — aborting")
                return False

            best = max(matches, key=lambda m: m.confidence)
            x, y = self.random_point_in_bbox(best.bbox)
            logger.info(f"[RallyFort] Clicking fort_building1 at ({x}, {y}) conf={best.confidence:.2f}")
            self.state_machine.pc_input.tap(x, y)
            time.sleep(random.uniform(1.0, 2.0))

            # --- check if fort_icon appears (correct building) ---
            image = self.state_machine.screen_capture.capture()
            if image is None:
                logger.warning("[RallyFort] Screenshot failed after clicking fort_building1")
                return False

            fort_icon_matches = self._matcher.match(image, template_name="fort_icon", threshold=0.75)
            if fort_icon_matches:
                # Correct building — continue with the rest of the sequence
                break

            # Wrong building — look for close_building to dismiss it and retry from the top
            logger.info(f"[RallyFort] fort_icon not found (attempt {attempt}/{max_retries}) — looking for close_building")
            close_matches = self._matcher.match(image, template_name="close_building", threshold=0.75)
            if close_matches:
                best_close = max(close_matches, key=lambda m: m.confidence)
                cx, cy = self.random_point_in_bbox(best_close.bbox)
                logger.info(f"[RallyFort] Clicking close_building at ({cx}, {cy}) conf={best_close.confidence:.2f}")
                self.state_machine.pc_input.tap(cx, cy)
                time.sleep(random.uniform(1.0, 2.0))
            else:
                logger.warning("[RallyFort] close_building not found either — aborting")
                return False
        else:
            logger.warning(f"[RallyFort] Failed to open correct fort building after {max_retries} retries")
            return False

        # --- remaining sequence after fort_icon is confirmed ---
        # Rally board is open — find all fort icons and all how_far texts,
        # pair them by row (smallest |dy|), then pick first one < MAX_KM.
        image = self.state_machine.screen_capture.capture()
        if image is None:
            logger.warning("[RallyFort] Screenshot failed on rally board")
            return False

        fort_matches = self._matcher.match(
            image, template_name="fort_icon", threshold=0.75, max_matches=10
        )
        howfar_matches = self._matcher.match(
            image, template_name="how_far", threshold=0.75, max_matches=10
        )
        if not fort_matches:
            logger.warning("[RallyFort] No fort_icon found on rally board")
            return False

        # Sort forts top-to-bottom
        fort_matches.sort(key=lambda m: m.center[1])

        # Pair each fort with the nearest how_far by vertical distance
        MAX_PAIR_DY = 80
        pairs = []
        for fm in fort_matches:
            fx, fy = fm.center
            best_hf = None
            min_dy = float("inf")
            for hm in howfar_matches:
                dy = abs(fy - hm.center[1])
                if dy < min_dy:
                    min_dy = dy
                    best_hf = hm
            if best_hf and min_dy <= MAX_PAIR_DY:
                pairs.append((fm, best_hf))
            else:
                # Fallback: use known offset from debug_rally.png (-903, -51)
                logger.debug(f"[RallyFort] fort_icon at ({fx},{fy}) no how_far template found, using offset fallback")
                off_x, off_y = -903, -51
                cx = int(fx + off_x)
                cy = int(fy + off_y)
                cw, ch = 220, 60  # wide enough for pin icon + km text
                x1 = max(0, cx - cw // 2)
                y1 = max(0, cy - ch // 2)
                x2 = min(image.shape[1], cx + cw // 2)
                y2 = min(image.shape[0], cy + ch // 2)
                if x2 > x1 and y2 > y1:
                    # Create a synthetic match object for fallback
                    from rokbot.vision.template_matcher import TemplateMatch
                    synth = TemplateMatch(
                        bbox=(x1, y1, x2, y2),
                        center=(cx, cy),
                        confidence=0.5,
                        template_name="how_far_fallback"
                    )
                    pairs.append((fm, synth))

        if not pairs:
            logger.warning("[RallyFort] No fort_icon+how_far pairs found on rally board")
            close_matches = self._matcher.match(image, template_name="close_building", threshold=0.75)
            if close_matches:
                best_close = max(close_matches, key=lambda m: m.confidence)
                cx, cy = self.random_point_in_bbox(best_close.bbox)
                logger.info(f"[RallyFort] Clicking close_building at ({cx}, {cy}) conf={best_close.confidence:.2f}")
                self.state_machine.pc_input.tap(cx, cy)
                time.sleep(random.uniform(0.5, 1.0))
            return False

        chosen_fort = None
        for fm, hm in pairs:
            cx, cy = fm.center
            # Expand crop around how_far: tight vertical crop to avoid avatar below,
            # extend right to capture the km text
            hx1, hy1, hx2, hy2 = hm.bbox
            margin_y = 3   # tight vertical margin — text is at same height as the pin icon
            margin_x = 10
            crop = image[max(0, hy1 - margin_y):min(image.shape[0], hy2 + margin_y),
                         max(0, hx1 - margin_x):min(image.shape[1], hx2 + 150)]
            km = self._read_km_from_crop(crop, label=f"fort=({cx},{cy})")
            if km == -1:
                logger.info(f"[RallyFort] Skipping fort_icon at ({cx},{cy}) — km unreadable (OCR failed)")
            elif km >= self.MAX_KM:
                logger.info(f"[RallyFort] Skipping fort_icon at ({cx},{cy}) — km={km} (too far, max={self.MAX_KM})")
            else:
                chosen_fort = fm
                logger.info(f"[RallyFort] Selected fort_icon at ({cx},{cy}) — km={km} (< {self.MAX_KM})")
                break

        if chosen_fort is None:
            logger.warning(f"[RallyFort] No rally found under {self.MAX_KM} KM — closing board and starting cooldown")
            self._last_failed_at = time.time()
            close_matches = self._matcher.match(image, template_name="close_building", threshold=0.75)
            if close_matches:
                best_close = max(close_matches, key=lambda m: m.confidence)
                cx, cy = self.random_point_in_bbox(best_close.bbox)
                logger.info(f"[RallyFort] Clicking close_building at ({cx}, {cy}) conf={best_close.confidence:.2f}")
                self.state_machine.pc_input.tap(cx, cy)
                time.sleep(random.uniform(0.5, 1.0))
            else:
                self.state_machine.pc_input.key_back()
                time.sleep(random.uniform(0.5, 1.0))
            return False

        # Click the chosen fort_icon
        x, y = self.random_point_in_bbox(chosen_fort.bbox)
        logger.info(f"[RallyFort] Clicking chosen fort_icon at ({x}, {y})")
        self.state_machine.pc_input.tap(x, y)
        time.sleep(random.uniform(1.0, 2.0))

        # Click click_to_join
        image = self.state_machine.screen_capture.capture()
        if image is None:
            logger.warning("[RallyFort] Screenshot failed during click_to_join")
            return False

        matches = self._matcher.match(image, template_name="click_to_join", threshold=0.75)
        if not matches:
            logger.warning("[RallyFort] click_to_join not found — looking for close_building")
            close_matches = self._matcher.match(image, template_name="close_building", threshold=0.75)
            if close_matches:
                best_close = max(close_matches, key=lambda m: m.confidence)
                cx, cy = self.random_point_in_bbox(best_close.bbox)
                logger.info(f"[RallyFort] Clicking close_building at ({cx}, {cy}) conf={best_close.confidence:.2f}")
                self.state_machine.pc_input.tap(cx, cy)
                time.sleep(random.uniform(0.5, 1.0))
            else:
                self.state_machine.pc_input.key_back()
                time.sleep(random.uniform(0.5, 1.0))
            return False

        best = max(matches, key=lambda m: m.confidence)
        x, y = self.random_point_in_bbox(best.bbox)
        logger.info(f"[RallyFort] Clicking click_to_join at ({x}, {y}) conf={best.confidence:.2f}")
        self.state_machine.pc_input.tap(x, y)
        time.sleep(random.uniform(1.0, 2.0))

        # --- new_troop → send_troop sequence ---
        image = self.state_machine.screen_capture.capture()
        if image is None:
            logger.warning("[RallyFort] Screenshot failed during new_troop")
            return False

        matches = self._matcher.match(image, template_name="new_troop", threshold=0.75)
        if not matches:
            logger.warning("[RallyFort] new_troop not found — pressing ESC and restarting")
            self.state_machine.pc_input.key_back()
            time.sleep(random.uniform(0.5, 1.0))
            return False

        best = max(matches, key=lambda m: m.confidence)
        x, y = self.random_point_in_bbox(best.bbox)
        logger.info(f"[RallyFort] Clicking new_troop at ({x}, {y}) conf={best.confidence:.2f}")
        self.state_machine.pc_input.tap(x, y)
        time.sleep(random.uniform(1.0, 2.0))

        image = self.state_machine.screen_capture.capture()
        if image is None:
            logger.warning("[RallyFort] Screenshot failed during send_troop")
            return False

        matches = self._matcher.match(image, template_name="send_troop", threshold=0.75)
        if not matches:
            logger.warning("[RallyFort] send_troop not found — aborting")
            return False

        best = max(matches, key=lambda m: m.confidence)
        x, y = self.random_point_in_bbox(best.bbox)
        logger.info(f"[RallyFort] Clicking send_troop at ({x}, {y}) conf={best.confidence:.2f}")
        self.state_machine.pc_input.tap(x, y)
        time.sleep(random.uniform(1.0, 2.0))

        # Optional confirmation step
        image = self.state_machine.screen_capture.capture()
        if image is not None:
            confirm_matches = self._matcher.match(image, template_name="confirm_send_if_have", threshold=0.75)
            if confirm_matches:
                best_confirm = max(confirm_matches, key=lambda m: m.confidence)
                cx, cy = self.random_point_in_bbox(best_confirm.bbox)
                logger.info(f"[RallyFort] Clicking confirm_send_if_have at ({cx}, {cy}) conf={best_confirm.confidence:.2f}")
                self.state_machine.pc_input.tap(cx, cy)
                time.sleep(random.uniform(1.0, 2.0))

        logger.info("[RallyFort] Rally join sequence completed")
        return True