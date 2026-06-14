"""Debug script: capture game window, detect gem_available templates, draw results.

Usage:
    python scripts/debug_gem_detector.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import random

import cv2
from loguru import logger

from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.template_matcher import TemplateMatcher


def random_point_in_bbox(bbox):
    x1, y1, x2, y2 = bbox
    px = random.randint(x1, max(x1, x2 - 1))
    py = random.randint(y1, max(y1, y2 - 1))
    return px, py


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Debug gem_available detection")
    parser.add_argument("--threshold", type=float, default=0.75, help="Match threshold (default 0.75)")
    parser.add_argument("--roi-margin", type=float, default=0.08, help="Margin ratio to exclude UI edges (default 0.08 = 8%%)")
    args = parser.parse_args()

    logger.info("=== Gem Detector Debug ===")

    wm = WindowManager()
    if wm.hwnd is None:
        logger.error("Game window not found!")
        return

    cap = WindowCapture(wm)
    matcher = TemplateMatcher(
        templates_dir=Path("data/templates/gathergem"),
        threshold=args.threshold,
    )

    image = cap.capture()
    if image is None:
        logger.error("Capture failed")
        return

    # Make a copy for drawing
    vis = image.copy()
    h, w = vis.shape[:2]

    # Compute center ROI to ignore UI edges (top/bottom/left/right bars)
    margin_x = int(w * args.roi_margin)
    margin_y = int(h * args.roi_margin)
    roi = (margin_x, margin_y, w - margin_x, h - margin_y)
    cv2.rectangle(vis, (roi[0], roi[1]), (roi[2], roi[3]), (255, 0, 0), 2)
    cv2.putText(vis, "Search ROI", (roi[0] + 4, roi[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    gem_templates = [f"gem_available{i}" for i in range(6)]
    total = 0

    for tpl_name in gem_templates:
        matches = matcher.match(image, template_name=tpl_name, threshold=args.threshold, max_matches=10, roi=roi)
        if matches:
            for m in matches:
                total += 1
                x1, y1, x2, y2 = m.bbox
                conf = m.confidence
                cx, cy = random_point_in_bbox(m.bbox)

                # Draw bbox
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Draw center dot
                cv2.circle(vis, (cx, cy), 4, (0, 0, 255), -1)
                # Label
                label = f"{tpl_name} {conf:.2f}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(vis, (x1, y1 - th - 8), (x1 + tw + 4, y1), (0, 255, 0), -1)
                cv2.putText(vis, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

                logger.info(f"Found {tpl_name} conf={conf:.2f} bbox=({x1},{y1},{x2},{y2}) center=({cx},{cy})")

    logger.info(f"Total gem detections: {total}")

    # Show result
    scale = min(1.0, 1200 / max(w, h))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))

    win_title = f"Gem Detector (thr={args.threshold}, roi_margin={args.roi_margin}) - press any key"
    cv2.imshow(win_title, vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Also save to disk
    out_path = Path("data/debug/gem_detector_result.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)
    logger.info(f"Saved result to {out_path}")


if __name__ == "__main__":
    main()
