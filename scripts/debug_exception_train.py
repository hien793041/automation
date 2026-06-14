"""Debug script: detect exception_train icons (buildings under upgrade).

Usage (with venv activated):
    python scripts/debug_exception_train.py
    python scripts/debug_exception_train.py --threshold 0.75

Output:
    - Console log with every exception_train detection
    - Annotated image saved to data/debug/exception_train_<timestamp>.png
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
from loguru import logger

from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.template_matcher import TemplateMatcher

TEMPLATES_DIR = Path("data/templates/train")
TEMPLATE_NAME = "exception_train"
COLOR_EXCEPTION = (0, 165, 255)  # orange


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Debug exception_train detection")
    parser.add_argument("--threshold", type=float, default=0.70,
                        help="Match threshold (default 0.70)")
    parser.add_argument("--max-matches", type=int, default=10,
                        help="Max detections (default 10)")
    args = parser.parse_args()

    logger.info("=== Debug: Exception Train ===")

    wm = WindowManager()
    if wm.hwnd is None:
        logger.error("Game window not found!")
        return 1

    cap = WindowCapture(wm)
    matcher = TemplateMatcher(templates_dir=TEMPLATES_DIR, threshold=args.threshold)

    image = cap.capture()
    if image is None:
        logger.error("Capture failed")
        return 1

    h, w = image.shape[:2]
    vis = image.copy()

    matches = matcher.match(
        image,
        template_name=TEMPLATE_NAME,
        threshold=args.threshold,
        max_matches=args.max_matches,
    )

    logger.info(f"--- {TEMPLATE_NAME} detections ---")
    if matches:
        for m in matches:
            cx, cy = m.center
            x1, y1, x2, y2 = m.bbox
            logger.info(
                f"{m.template_name:20s} conf={m.confidence:.2f} center=({cx:4d},{cy:4d}) "
                f"bbox={m.bbox}"
            )
            cv2.rectangle(vis, (x1, y1), (x2, y2), COLOR_EXCEPTION, 2)
            label = f"{m.template_name} {m.confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            cv2.rectangle(vis, (x1, y1 - th - 6), (x1 + tw + 2, y1), COLOR_EXCEPTION, -1)
            cv2.putText(vis, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    else:
        logger.warning(f"No '{TEMPLATE_NAME}' found above threshold {args.threshold}")
        # Show best conf below threshold for tuning
        debug = matcher.match(image, template_name=TEMPLATE_NAME, threshold=0.30, max_matches=1)
        if debug:
            best = max(debug, key=lambda m: m.confidence)
            logger.info(f"Best match: conf={best.confidence:.2f} at {best.center} (below threshold)")

    logger.info(f"Total detections: {len(matches)}")

    # Show & save
    scale = min(1.0, 1200 / max(w, h))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))

    win_title = f"Exception Train Debug (orange={TEMPLATE_NAME}, thr={args.threshold}) — press any key"
    cv2.imshow(win_title, vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"data/debug/exception_train_{timestamp}.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)
    logger.info(f"Saved annotated image to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
