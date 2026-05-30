"""Test template matching + OCR ROI on the game window.

Usage (with venv activated):
    python scripts/test_template_ocr.py

Output:
    - Console log with template match results and OCR ROI results
    - Debug image saved to data/debug/template_test_<timestamp>.png
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np
from loguru import logger

from rokbot.core.config import BotConfig
from rokbot.pc_controller import WindowCapture, WindowManager
from rokbot.vision.ocr_engine import OCREngine


def main() -> int:
    logger.info("=== Test Template Matching + OCR ROI ===")

    config = BotConfig()
    wm = WindowManager(window_title_substring=config.pc.window_title)
    if not wm.is_window_valid():
        logger.error("Game window not found")
        return 1

    cap = WindowCapture(wm)
    image = cap.capture()
    if image is None:
        logger.error("Capture failed")
        return 1

    h, w = image.shape[:2]
    logger.info(f"Screenshot: {w}x{h}")

    # Load template
    template_path = Path("data/templates/tham_do.png")
    if not template_path.exists():
        logger.error(f"Template not found: {template_path}")
        return 1

    template = cv2.imread(str(template_path))
    th, tw = template.shape[:2]
    logger.info(f"Template size: {tw}x{th}")

    # 1. Template Matching
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    logger.info(f"Template match max confidence: {max_val:.3f}")

    annotated = image.copy()
    if max_val >= 0.75:
        x, y = max_loc
        cv2.rectangle(annotated, (x, y), (x + tw, y + th), (0, 0, 255), 3)
        cv2.putText(annotated, f"Thang do: {max_val:.2f}", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        logger.info(f"Template found at ({x}, {y}) -> ({x+tw}, {y+th})")
    else:
        logger.warning("Template not found (confidence < 0.75)")

    # 2. OCR ROI - try on the area where template was found, or center-upper area
    ocr = OCREngine(lang=config.vision.ocr_lang)

    # ROI around expected bubble area (center-ish upper)
    roi_x1, roi_x2 = int(w * 0.35), int(w * 0.55)
    roi_y1, roi_y2 = int(h * 0.35), int(h * 0.50)
    roi = (roi_x1, roi_y1, roi_x2, roi_y2)

    logger.info(f"OCR ROI: ({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2})")
    roi_results = ocr.read(image, roi=roi)
    logger.info(f"OCR ROI detected {len(roi_results)} blocks:")
    for res in roi_results:
        logger.info(f"  - '{res.text}' (conf={res.confidence:.2f}) @ {res.bbox}")
        x1, y1, x2, y2 = res.bbox
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 255, 0), 2)
        cv2.putText(annotated, res.text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    # Draw ROI rectangle
    cv2.rectangle(annotated, (roi_x1, roi_y1), (roi_x2, roi_y2), (255, 0, 255), 2)
    cv2.putText(annotated, "OCR_ROI", (roi_x1, roi_y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

    # 3. Full-screen OCR (for comparison)
    full_results = ocr.read(image)
    tham_do_blocks = [r for r in full_results if "thăm" in r.text.lower() or "dò" in r.text.lower()]
    logger.info(f"Full-screen OCR found {len(tham_do_blocks)} blocks with 'tham'/'do':")
    for res in tham_do_blocks:
        logger.info(f"  - '{res.text}' (conf={res.confidence:.2f}) @ {res.bbox}")

    # Save annotated image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"data/debug/template_test_{timestamp}.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), annotated)
    logger.info(f"Annotated image saved to: {out_path.absolute()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
