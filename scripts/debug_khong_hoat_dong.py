"""Debug script: detect khong_hoat_dong_text and show which ones are inside exception_train.

Usage (with venv activated):
    python scripts/debug_khong_hoat_dong.py
    python scripts/debug_khong_hoat_dong.py --threshold 0.60

Output:
    - Console log with every khong_hoat_dong_text detection and exception overlay
    - Annotated image saved to data/debug/khong_hoat_dong_<timestamp>.png
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np
from loguru import logger

from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.template_matcher import TemplateMatcher


SHARED_DIR = Path("data/templates")
TRAIN_DIR = Path("data/templates/train")

COLOR_KHD = (0, 255, 0)       # green = khong_hoat_dong
COLOR_KHD_SKIP = (0, 0, 255)  # red = inside exception_train (skipped)
COLOR_EXC = (0, 165, 255)     # orange = exception_train


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Debug khong_hoat_dong_text detection")
    parser.add_argument("--threshold", type=float, default=0.60,
                        help="Match threshold for khong_hoat_dong_text (default 0.60)")
    parser.add_argument("--exc-threshold", type=float, default=0.70,
                        help="Match threshold for exception_train (default 0.70)")
    args = parser.parse_args()

    logger.info("=== Debug: Khong Hoat Dong Text ===")

    wm = WindowManager()
    if wm.hwnd is None:
        logger.error("Game window not found!")
        return 1

    cap = WindowCapture(wm)
    shared_matcher = TemplateMatcher(templates_dir=SHARED_DIR, threshold=args.threshold)
    train_matcher = TemplateMatcher(templates_dir=TRAIN_DIR, threshold=args.exc_threshold)

    image = cap.capture()
    if image is None:
        logger.error("Capture failed")
        return 1

    h, w = image.shape[:2]
    vis = image.copy()

    # 1. Detect exception_train
    exc_matches = train_matcher.match(
        image, template_name="exception_train",
        threshold=args.exc_threshold, max_matches=10
    )
    logger.info(f"exception_train detections: {len(exc_matches)}")
    for em in exc_matches:
        x1, y1, x2, y2 = em.bbox
        logger.info(f"  exception_train conf={em.confidence:.2f} bbox=({x1},{y1},{x2},{y2})")
        cv2.rectangle(vis, (x1, y1), (x2, y2), COLOR_EXC, 2)
        cv2.putText(vis, f"exc {em.confidence:.2f}", (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_EXC, 1)

    # 2. Detect khong_hoat_dong_text with LOW threshold to see all candidates
    khd_matches = shared_matcher.match(
        image, template_name="khong_hoat_dong_text",
        threshold=args.threshold, max_matches=20
    )
    logger.info(f"khong_hoat_dong_text detections: {len(khd_matches)}")

    valid_count = 0
    for km in khd_matches:
        kx, ky = km.center
        x1, y1, x2, y2 = km.bbox

        # Check if inside any exception_train bbox
        inside_exc = False
        for em in exc_matches:
            ex1, ey1, ex2, ey2 = em.bbox
            if ex1 <= kx <= ex2 and ey1 <= ky <= ey2:
                inside_exc = True
                break

        status = "SKIP (inside exception)" if inside_exc else "VALID"
        logger.info(
            f"  khong_hoat_dong_text conf={km.confidence:.2f} center=({kx},{ky}) "
            f"bbox=({x1},{y1},{x2},{y2})  [{status}]"
        )

        color = COLOR_KHD_SKIP if inside_exc else COLOR_KHD
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vis, f"{km.confidence:.2f}", (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        if not inside_exc:
            valid_count += 1

    logger.info(f"Valid (non-exception) khong_hoat_dong_text: {valid_count}")

    # Show & save
    scale = min(1.0, 1200 / max(w, h))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))

    win_title = ("KHD Debug (green=valid, red=inside exception, orange=exception_train) "
                 "— press any key")
    cv2.imshow(win_title, vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"data/debug/khong_hoat_dong_{timestamp}.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)
    logger.info(f"Saved annotated image to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
