"""Debug script: detect troop-completed icons on screen.

Usage (with venv activated):
    python scripts/debug_train_troop_complete.py
    python scripts/debug_train_troop_complete.py --threshold 0.70

Output:
    - Console log with every completed-troop detection
    - Annotated image saved to data/debug/train_complete_<timestamp>.png
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

COMPLETED_ICONS = [
    "t1_da_completed",
    "t2_bo_completed",
    "t2_cung_completed",
    "t2_ngua_completed",
    "t3_bo_completed",
]

COLOR_COMPLETED = (0, 255, 255)  # cyan


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Debug troop-complete detection")
    parser.add_argument("--threshold", type=float, default=0.70,
                        help="Match threshold (default 0.70)")
    args = parser.parse_args()

    logger.info("=== Debug: Train Troop Complete ===")

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

    total = 0
    logger.info("--- completed icon detections ---")
    for tpl_name in COMPLETED_ICONS:
        matches = matcher.match(
            image, template_name=tpl_name,
            threshold=args.threshold, max_matches=10
        )
        for m in matches:
            total += 1
            cx, cy = m.center
            logger.info(
                f"{m.template_name:20s} conf={m.confidence:.2f} center=({cx:4d},{cy:4d}) "
                f"bbox={m.bbox}"
            )
            x1, y1, x2, y2 = m.bbox
            cv2.rectangle(vis, (x1, y1), (x2, y2), COLOR_COMPLETED, 2)
            label = f"{m.template_name} {m.confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            cv2.rectangle(vis, (x1, y1 - th - 6), (x1 + tw + 2, y1), COLOR_COMPLETED, -1)
            cv2.putText(vis, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

        if not matches:
            # Show best conf even if below threshold for tuning
            debug = matcher.match(image, template_name=tpl_name, threshold=0.30, max_matches=1)
            if debug:
                best = max(debug, key=lambda m: m.confidence)
                logger.debug(f"{tpl_name:20s} best conf={best.confidence:.2f} (below {args.threshold})")

    logger.info(f"Total completed detections: {total}")

    # Show & save
    scale = min(1.0, 1200 / max(w, h))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))

    win_title = f"Train Complete Debug (cyan=completed, thr={args.threshold}) — press any key"
    cv2.imshow(win_title, vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"data/debug/train_complete_{timestamp}.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)
    logger.info(f"Saved annotated image to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
