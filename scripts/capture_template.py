"""Capture a template from the game window.

Usage:
    .venv/Scripts/python scripts/capture_template.py --name in_city_icon
    .venv/Scripts/python scripts/capture_template.py --name enter_city_icon --roi 0.75 0.75 1.0 1.0

The captured image is saved to data/templates/<name>.png.
"""

import argparse
import sys
from pathlib import Path

import cv2
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager


def main():
    parser = argparse.ArgumentParser(description="Capture a template from the game window")
    parser.add_argument("--name", required=True, help="Template name (e.g. in_city_icon)")
    parser.add_argument(
        "--roi",
        nargs=4,
        type=float,
        default=[0.0, 0.0, 1.0, 1.0],
        metavar=("x1", "y1", "x2", "y2"),
        help="ROI as ratios of screen size (default: full screen)",
    )
    parser.add_argument("--output-dir", default="data/templates", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.png"

    wm = WindowManager()
    capture = WindowCapture(wm)

    logger.info("Capturing game window...")
    image = capture.capture()
    if image is None:
        logger.error("Failed to capture game window")
        sys.exit(1)

    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(v * (w if i % 2 == 0 else h)) for i, v in enumerate(args.roi)]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    cropped = image[y1:y2, x1:x2]
    cv2.imwrite(str(out_path), cropped)
    logger.info(f"Saved template to {out_path} ({cropped.shape[1]}x{cropped.shape[0]})")

    # Quick preview
    preview = cv2.resize(cropped, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    cv2.imshow(f"Template: {args.name} (press any key to close)", preview)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
