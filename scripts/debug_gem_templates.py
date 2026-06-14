"""Debug script: detect gem_available (0/1/2) and gem_gathering templates,
visualise them, and measure distances between occupied/unoccupied pairs.

Usage (with venv activated):
    python scripts/debug_gem_templates.py
    python scripts/debug_gem_templates.py --threshold 0.70

Output:
    - Console log with every detection and pair distances
    - Annotated image saved to data/debug/gem_templates_<timestamp>.png
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import math

import cv2
from loguru import logger

from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.template_matcher import TemplateMatcher

TEMPLATES_DIR = Path("data/templates/gathergem")

# Templates to search
AVAILABLE_TEMPLATES = ["gem_available0", "gem_available1", "gem_available2"]
GATHERING_TEMPLATES = ["gem_gathering", "gem_gathering1"]

# Colours (BGR)
COLOR_AVAILABLE = (0, 255, 0)   # green
COLOR_GATHERING = (0, 0, 255)   # red
COLOR_PAIR_LINE = (255, 0, 255) # magenta


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Debug gem template detection")
    parser.add_argument("--threshold", type=float, default=0.80,
                        help="Match threshold (default 0.80)")
    parser.add_argument("--pair-dist", type=int, default=100,
                        help="Max pixel distance to draw pair lines (default 100)")
    args = parser.parse_args()

    logger.info("=== Debug: Gem Templates ===")

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

    detections = []  # list of dicts: {name, bbox, center, confidence, kind}

    # 1. Detect gem_available templates
    logger.info("--- gem_available detections ---")
    for tpl_name in AVAILABLE_TEMPLATES:
        matches = matcher.match(image, template_name=tpl_name,
                                threshold=args.threshold, max_matches=10)
        for m in matches:
            cx, cy = m.center
            detections.append({
                "name": m.template_name,
                "bbox": m.bbox,
                "center": (cx, cy),
                "confidence": m.confidence,
                "kind": "available",
            })
            logger.info(
                f"{m.template_name:20s} conf={m.confidence:.2f} center=({cx:4d},{cy:4d}) "
                f"bbox={m.bbox}"
            )
            # Draw
            x1, y1, x2, y2 = m.bbox
            cv2.rectangle(vis, (x1, y1), (x2, y2), COLOR_AVAILABLE, 2)
            label = f"{m.template_name} {m.confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            cv2.rectangle(vis, (x1, y1 - th - 6), (x1 + tw + 2, y1), COLOR_AVAILABLE, -1)
            cv2.putText(vis, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # 2. Detect gem_gathering templates
    logger.info("--- gem_gathering detections ---")
    for tpl_name in GATHERING_TEMPLATES:
        matches = matcher.match(image, template_name=tpl_name,
                                threshold=args.threshold, max_matches=10)
        for m in matches:
            cx, cy = m.center
            detections.append({
                "name": m.template_name,
                "bbox": m.bbox,
                "center": (cx, cy),
                "confidence": m.confidence,
                "kind": "gathering",
            })
            logger.info(
                f"{m.template_name:20s} conf={m.confidence:.2f} center=({cx:4d},{cy:4d}) "
                f"bbox={m.bbox}"
            )
            # Draw
            x1, y1, x2, y2 = m.bbox
            cv2.rectangle(vis, (x1, y1), (x2, y2), COLOR_GATHERING, 2)
            label = f"{m.template_name} {m.confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            cv2.rectangle(vis, (x1, y1 - th - 6), (x1 + tw + 2, y1), COLOR_GATHERING, -1)
            cv2.putText(vis, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # 3. Pair analysis: for every available, find nearest gathering
    logger.info("--- pair analysis (available vs gathering) ---")
    avail_list = [d for d in detections if d["kind"] == "available"]
    gather_list = [d for d in detections if d["kind"] == "gathering"]

    for a in avail_list:
        ax, ay = a["center"]
        nearest = None
        min_dist = float("inf")
        for g in gather_list:
            gx, gy = g["center"]
            dist = math.hypot(ax - gx, ay - gy)
            if dist < min_dist:
                min_dist = dist
                nearest = g

        if nearest:
            status = "OCCUPIED" if min_dist < 80 else "FREE"
            logger.info(
                f"{a['name']} @ ({ax},{ay})  →  nearest {nearest['name']} @ "
                f"({nearest['center'][0]},{nearest['center'][1]})  "
                f"dist={min_dist:.1f}px  [{status}]"
            )
            if min_dist <= args.pair_dist:
                cv2.line(vis, (ax, ay), nearest["center"], COLOR_PAIR_LINE, 1)
                mid_x = (ax + nearest["center"][0]) // 2
                mid_y = (ay + nearest["center"][1]) // 2
                cv2.putText(vis, f"{min_dist:.0f}px", (mid_x, mid_y - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_PAIR_LINE, 1)
        else:
            logger.info(f"{a['name']} @ ({ax},{ay})  →  no gathering found  [FREE]")

    # 4. Show & save
    logger.info(f"Total detections: available={len(avail_list)}, gathering={len(gather_list)}")

    scale = min(1.0, 1200 / max(w, h))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))

    win_title = (f"Gem Templates (green=available, red=gathering, magenta=pair<{args.pair_dist}px) "
                 f"- press any key")
    cv2.imshow(win_title, vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"data/debug/gem_templates_{timestamp}.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)
    logger.info(f"Saved annotated image to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
