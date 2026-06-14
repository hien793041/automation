"""Debug script: find both 'fort_icon' and 'how_far' on screen,
compute vertical/horizontal offsets between each fort_icon and its
nearest how_far neighbour.

Usage:
    python scripts/debug_fort_howfar_pair.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
from loguru import logger

from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.template_matcher import TemplateMatcher


def main():
    logger.info("=== Fort-Icon / How-Far Pair Debug ===")

    wm = WindowManager()
    if wm.hwnd is None:
        logger.error("Game window not found!")
        return

    cap = WindowCapture(wm)
    matcher = TemplateMatcher(
        templates_dir=Path("data/templates/rallyfort"),
        threshold=0.75,
    )

    image = cap.capture()
    if image is None:
        logger.error("Capture failed")
        return

    vis = image.copy()
    h, w = vis.shape[:2]

    # Detect both templates
    fort_matches = matcher.match(image, template_name="fort_icon", threshold=0.75, max_matches=10)
    howfar_matches = matcher.match(image, template_name="how_far", threshold=0.75, max_matches=10)

    logger.info(f"fort_icon detections: {len(fort_matches)}")
    logger.info(f"how_far detections: {len(howfar_matches)}")

    if not fort_matches or not howfar_matches:
        logger.warning("Missing one or both templates on screen")
        cv2.imshow("Result", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    # Pair each fort_icon with the how_far on the SAME ROW (smallest |dy|)
    MAX_DY = 80  # pixels; if |dy| exceeds this they are on different rows
    pairs = []
    for fm in fort_matches:
        fx, fy = fm.center
        nearest = None
        min_dy = float("inf")
        for hm in howfar_matches:
            hx, hy = hm.center
            dy = abs(fy - hy)
            if dy < min_dy:
                min_dy = dy
                nearest = hm
        if nearest and min_dy <= MAX_DY:
            dx = nearest.center[0] - fx
            dy_signed = nearest.center[1] - fy
            dist = math.hypot(dx, dy_signed)
            pairs.append((fm, nearest, dx, dy_signed, dist))
        else:
            raw_dy = nearest.center[1] - fy if nearest else 0
            logger.warning(
                f"fort_icon at ({fx},{fy}) has no how_far on the same row "
                f"(min |dy|={min_dy:.1f}, raw dy={raw_dy:+d}) — increase MAX_DY if needed"
            )

    # Draw and log
    for idx, (fm, hm, dx, dy_signed, dist) in enumerate(pairs, 1):
        fx, fy = fm.center
        hx, hy = hm.center

        logger.info(
            f"Pair #{idx}: fort_icon=({fx},{fy}) how_far=({hx},{hy}) "
            f"offset=(dx={dx:+d}, dy={dy_signed:+d}) distance={dist:.1f}px"
        )

        # Draw fort_icon bbox (green)
        fx1, fy1, fx2, fy2 = fm.bbox
        cv2.rectangle(vis, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)
        cv2.putText(vis, f"fort#{idx}", (fx1, fy1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Draw how_far bbox (red)
        hx1, hy1, hx2, hy2 = hm.bbox
        cv2.rectangle(vis, (hx1, hy1), (hx2, hy2), (0, 0, 255), 2)
        cv2.putText(vis, f"km#{idx}", (hx1, hy1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Draw line between centers
        cv2.line(vis, (fx, fy), (hx, hy), (255, 0, 255), 1)

        # Label offset near fort_icon
        label = f"dx={dx:+d} dy={dy_signed:+d}"
        cv2.putText(vis, label, (fx, fy2 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    # Show result
    scale = min(1.0, 1200 / max(w, h))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))

    cv2.imshow("Fort-Icon / How-Far Pairing (green=fort, red=km)", vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Save
    out_path = Path("data/debug/fort_howfar_pair.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)
    logger.info(f"Saved result to {out_path}")


if __name__ == "__main__":
    main()
