"""Debug script: capture game window, find 'how_far' template,
and inspect the area 100 px to the right of the match.

Usage:
    python scripts/debug_how_far.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
from loguru import logger

from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.template_matcher import TemplateMatcher


def main():
    logger.info("=== How-Far Detector Debug ===")

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

    # Search for how_far template
    matches = matcher.match(image, template_name="how_far", threshold=0.75)
    if not matches:
        logger.warning("how_far.png not found on screen")
        cv2.imshow("Result - not found", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    best = max(matches, key=lambda m: m.confidence)
    x1, y1, x2, y2 = best.bbox
    conf = best.confidence

    logger.info(f"how_far found: bbox=({x1},{y1},{x2},{y2}) conf={conf:.2f}")

    # Draw original bbox (green)
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
    label = f"how_far {conf:.2f}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(vis, (x1, y1 - th - 8), (x1 + tw + 4, y1), (0, 255, 0), -1)
    cv2.putText(vis, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    # Compute expanded bbox (100 px to the right)
    ex2 = min(x2 + 100, w)  # clamp to image width
    expanded_bbox = (x2, y1, ex2, y2)

    # Draw expanded area (red)
    cv2.rectangle(vis, (expanded_bbox[0], expanded_bbox[1]), (expanded_bbox[2], expanded_bbox[3]), (0, 0, 255), 2)
    cv2.putText(vis, "+100px", (x2 + 4, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # Arrow from original to expanded
    cv2.arrowedLine(vis, (x2, (y1 + y2) // 2), (ex2, (y1 + y2) // 2), (0, 0, 255), 2, tipLength=0.15)

    # Crop the expanded region
    crop = image[y1:y2, x2:ex2]
    if crop.size == 0:
        logger.warning("Expanded crop is empty (template at right edge?)")
    else:
        # Simple analysis: convert to grayscale and show mean brightness
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mean_val = float(gray.mean())
        std_val = float(gray.std())
        logger.info(f"Expanded region stats: mean={mean_val:.1f}, std={std_val:.1f}")

        # Save crop
        out_crop = Path("data/debug/how_far_expanded_crop.png")
        out_crop.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_crop), crop)
        logger.info(f"Saved expanded crop to {out_crop}")

        # Also save a slightly larger context crop for easier viewing
        ctx_x1 = max(0, x1 - 20)
        ctx_y1 = max(0, y1 - 20)
        ctx_x2 = min(w, ex2 + 20)
        ctx_y2 = min(h, y2 + 20)
        ctx_crop = image[ctx_y1:ctx_y2, ctx_x1:ctx_x2]
        out_ctx = Path("data/debug/how_far_context.png")
        cv2.imwrite(str(out_ctx), ctx_crop)
        logger.info(f"Saved context crop to {out_ctx}")

    # Show result
    scale = min(1.0, 1200 / max(w, h))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))

    cv2.imshow("How-Far Debug (green=match, red=+100px)", vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Save annotated full image
    out_full = Path("data/debug/how_far_result.png")
    cv2.imwrite(str(out_full), vis)
    logger.info(f"Saved annotated result to {out_full}")


if __name__ == "__main__":
    main()
