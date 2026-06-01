"""Capture game window, draw grid, and optionally search + mark templates."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np
from PIL import ImageGrab

from rokbot.core.config import BotConfig
from rokbot.pc_controller.window_manager import WindowManager
from rokbot.vision.template_matcher import TemplateMatcher


def draw_grid_3x3(image: np.ndarray, w: int, h: int) -> None:
    cell_w = w // 3
    cell_h = h // 3
    color = (0, 255, 0)
    thickness = 2
    for row in range(3):
        for col in range(3):
            x1 = col * cell_w
            y1 = row * cell_h
            x2 = (col + 1) * cell_w if col < 2 else w
            y2 = (row + 1) * cell_h if row < 2 else h
            cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
            number = row * 3 + col + 1
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            cv2.putText(image, str(number), (cx - 15, cy + 15), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)


def draw_horizontal_strips(image: np.ndarray, w: int, h: int, parts: int) -> None:
    cell_h = h // parts
    color_line = (0, 255, 0)
    color_text = (0, 0, 255)
    thickness = 2
    for i in range(parts):
        y1 = i * cell_h
        y2 = (i + 1) * cell_h if i < parts - 1 else h
        cv2.line(image, (0, y1), (w, y1), color_line, thickness)
        cy = (y1 + y2) // 2
        cv2.putText(image, str(i + 1), (w // 2 - 20, cy + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, color_text, 3)
    cv2.line(image, (0, h), (w, h), color_line, thickness)


def draw_vertical_strips(image: np.ndarray, w: int, h: int, parts: int) -> None:
    cell_w = w // parts
    color_line = (0, 255, 0)
    color_text = (0, 0, 255)
    thickness = 2
    for i in range(parts):
        x1 = i * cell_w
        x2 = (i + 1) * cell_w if i < parts - 1 else w
        cv2.line(image, (x1, 0), (x1, h), color_line, thickness)
        cx = (x1 + x2) // 2
        cy = h // 2
        cv2.putText(image, str(i + 1), (cx - 20, cy + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, color_text, 3)
    cv2.line(image, (w, 0), (w, h), color_line, thickness)


def get_part_roi(mode: str, part: int, parts: int, w: int, h: int):
    """Return (x1, y1, x2, y2) for a given part number (1-based)."""
    if mode == "grid":
        idx = part - 1
        row = idx // 3
        col = idx % 3
        cell_w = w // 3
        cell_h = h // 3
        x1 = col * cell_w
        y1 = row * cell_h
        x2 = (col + 1) * cell_w if col < 2 else w
        y2 = (row + 1) * cell_h if row < 2 else h
        return (x1, y1, x2, y2)
    elif mode == "horizontal":
        cell_h = h // parts
        y1 = (part - 1) * cell_h
        y2 = part * cell_h if part < parts else h
        return (0, y1, w, y2)
    else:
        cell_w = w // parts
        x1 = (part - 1) * cell_w
        x2 = part * cell_w if part < parts else w
        return (x1, 0, x2, h)


def search_and_mark(image: np.ndarray, matcher: TemplateMatcher, template_name: str, roi: tuple = None) -> list:
    """Search template and draw bounding boxes. Returns list of matches."""
    search_img = image
    offset_x, offset_y = 0, 0
    if roi is not None:
        x1, y1, x2, y2 = roi
        search_img = image[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1

    matches = matcher.match(search_img, template_name=template_name, max_matches=10)
    if matches:
        for i, m in enumerate(matches):
            bx1, by1, bx2, by2 = m.bbox
            abs_x1 = bx1 + offset_x
            abs_y1 = by1 + offset_y
            abs_x2 = bx2 + offset_x
            abs_y2 = by2 + offset_y
            cv2.rectangle(image, (abs_x1, abs_y1), (abs_x2, abs_y2), (255, 0, 0), 2)
            label = f"{i+1}: {m.confidence:.2f}"
            cv2.putText(image, label, (abs_x1, abs_y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture game window with grid overlay and optional template search")
    parser.add_argument("--mode", choices=["grid", "horizontal", "vertical"], default="vertical", help="grid=3x3, horizontal=rows, vertical=columns")
    parser.add_argument("--parts", type=int, default=12, help="Number of parts")
    parser.add_argument("--templates", nargs="+", default=None, help="Template name(s) to search (e.g. gathering backing moving)")
    parser.add_argument("--template-dir", type=str, default="data/templates/gather", help="Folder containing the template(s)")
    parser.add_argument("--part", type=int, default=None, help="Part number to search in (1-based). Omit to search full screen.")
    parser.add_argument("--threshold", type=float, default=0.75, help="Template matching threshold")
    args = parser.parse_args()

    config = BotConfig()
    wm = WindowManager(window_title_substring=config.pc.window_title)
    if not wm.is_window_valid():
        print("Game window not found")
        return 1

    rect = wm.get_client_rect()
    if rect is None:
        print("Could not get window rect")
        return 1

    left, top, right, bottom = rect
    w = right - left
    h = bottom - top

    screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
    image = np.array(screenshot)
    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    if args.mode == "grid":
        draw_grid_3x3(image_bgr, w, h)
        out_name = "debug_grid.png"
        print("Mode: 3x3 grid")
    elif args.mode == "horizontal":
        draw_horizontal_strips(image_bgr, w, h, args.parts)
        out_name = f"debug_horizontal_{args.parts}.png"
        print(f"Mode: horizontal ({args.parts} strips)")
    else:
        draw_vertical_strips(image_bgr, w, h, args.parts)
        out_name = f"debug_vertical_{args.parts}.png"
        print(f"Mode: vertical ({args.parts} strips)")

    matcher = None
    if args.templates:
        matcher = TemplateMatcher(templates_dir=Path(args.template_dir), threshold=args.threshold)

    # Search & mark
    if matcher and args.part:
        roi = get_part_roi(args.mode, args.part, args.parts, w, h)
        for tpl in args.templates:
            matches = search_and_mark(image_bgr, matcher, tpl, roi)
            print(f"\nTemplate '{tpl}' found {len(matches)} time(s) in part {args.part} (ROI: {roi}):")
            for i, m in enumerate(matches, 1):
                abs_bbox = (m.bbox[0] + roi[0], m.bbox[1] + roi[1], m.bbox[2] + roi[0], m.bbox[3] + roi[1])
                print(f"  Match {i}: conf={m.confidence:.3f}, bbox={abs_bbox}")
    elif matcher:
        for tpl in args.templates:
            matches = search_and_mark(image_bgr, matcher, tpl)
            print(f"\nTemplate '{tpl}' found {len(matches)} time(s) on full screen:")
            for i, m in enumerate(matches, 1):
                print(f"  Match {i}: conf={m.confidence:.3f}, bbox={m.bbox}")

    out_path = Path(out_name)
    cv2.imwrite(str(out_path), image_bgr)
    print(f"\nSaved to: {out_path.resolve()}")
    print(f"Window size: {w}x{h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
