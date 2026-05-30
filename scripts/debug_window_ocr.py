"""Debug script: find game window, capture screenshot, run OCR, save annotated image.

Usage (with venv activated):
    python scripts/debug_window_ocr.py

Output:
    - Console log with window info and detected text
    - Annotated image saved to data/debug/window_ocr_<timestamp>.png
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
    logger.info("=== Debug: Window + OCR ===")

    config = BotConfig()
    window_title = config.pc.window_title if hasattr(config, "pc") else "Rise of Kingdoms"

    # 1. Find game window
    wm = WindowManager(window_title_substring=window_title)
    if not wm.is_window_valid():
        logger.error(f"Game window not found (looking for '{window_title}')")
        return 1

    rect = wm.get_window_rect()
    client_rect = wm.get_client_rect()
    client_size = wm.get_client_size()

    logger.info(f"Window title : {window_title}")
    logger.info(f"Window hwnd  : {wm.hwnd}")
    logger.info(f"Window rect  : {rect}")           # (left, top, right, bottom)
    logger.info(f"Client rect  : {client_rect}")    # (left, top, right, bottom)
    logger.info(f"Client size  : {client_size}")    # (width, height)

    # 2. Capture screenshot
    capture = WindowCapture(wm)
    image = capture.capture()
    if image is None:
        logger.error("Screenshot failed")
        return 1

    logger.info(f"Screenshot shape: {image.shape}")

    # 3. OCR
    ocr = OCREngine(lang=config.vision.ocr_lang)
    results = ocr.read(image)

    logger.info(f"OCR detected {len(results)} text blocks:")
    logger.info("-" * 60)
    for i, res in enumerate(results, 1):
        x1, y1, x2, y2 = res.bbox
        logger.info(f"{i:3d}. '{res.text}' (conf={res.confidence:.2f}) @ ({x1},{y1},{x2},{y2})")
    logger.info("-" * 60)

    # 4. Draw annotations
    annotated = image.copy()
    h, w = annotated.shape[:2]

    for i, res in enumerate(results, 1):
        x1, y1, x2, y2 = res.bbox
        # Draw rectangle
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        # Draw text label
        label = f"{i}: {res.text}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 4), (x1 + tw, y1), (0, 255, 0), -1)
        cv2.putText(annotated, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # Draw center crosshair
    cx, cy = w // 2, h // 2
    cv2.drawMarker(annotated, (cx, cy), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)
    cv2.putText(annotated, f"CENTER ({cx},{cy})", (cx + 15, cy - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # Draw button search region (45%-85% height, 20%-80% width)
    r_x1, r_x2 = int(w * 0.20), int(w * 0.80)
    r_y1, r_y2 = int(h * 0.45), int(h * 0.85)
    cv2.rectangle(annotated, (r_x1, r_y1), (r_x2, r_y2), (255, 0, 0), 2)
    cv2.putText(annotated, "BUTTON_REGION", (r_x1, r_y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # 5. Save image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"data/debug/window_ocr_{timestamp}.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), annotated)
    logger.info(f"Annotated image saved to: {out_path.absolute()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
