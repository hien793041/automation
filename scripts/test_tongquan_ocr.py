"""Test script: find tongquan.png -> click -> wait 2s -> OCR text."""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

from rokbot.core.config import BotConfig
from rokbot.pc_controller.pc_input import PCInput
from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.ocr_engine import OCREngine
from rokbot.vision.template_matcher import TemplateMatcher


def main() -> int:
    logger.info("=== Test: tongquan -> click -> OCR ===")

    # 1. Setup
    config = BotConfig()
    wm = WindowManager(window_title_substring=config.pc.window_title)
    if not wm.is_window_valid():
        logger.error("Game window not found")
        return 1

    cap = WindowCapture(wm)
    pc_input = PCInput(wm)
    matcher = TemplateMatcher(templates_dir=Path("data/templates"), threshold=0.75)
    ocr = OCREngine(lang=config.vision.ocr_lang)

    # 2. Capture & find tongquan
    image = cap.capture()
    if image is None:
        logger.error("Capture failed")
        return 1

    matches = matcher.match(image, template_name="tongquan")
    if not matches:
        logger.error("tongquan.png not found")
        return 1

    match = max(matches, key=lambda m: m.confidence)
    cx, cy = match.center
    logger.info(f"tongquan FOUND at ({cx}, {cy}) conf={match.confidence:.2f}")

    # 3. Click (randomized within bbox for safety)
    x1, y1, x2, y2 = match.bbox
    tap_x = random.randint(x1, max(x1, x2 - 1))
    tap_y = random.randint(y1, max(y1, y2 - 1))
    pc_input.tap(tap_x, tap_y)
    logger.info(f"Clicked at ({tap_x}, {tap_y})")

    # 4. Wait 2s
    time.sleep(2.0)

    # 5. Re-capture & OCR
    image2 = cap.capture()
    if image2 is None:
        logger.error("Second capture failed")
        return 1

    results = ocr.read(image2)
    logger.info(f"OCR detected {len(results)} text blocks:")
    for i, res in enumerate(results, 1):
        print(f"  {i}. '{res.text}' (conf={res.confidence:.2f}) @ {res.bbox}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
