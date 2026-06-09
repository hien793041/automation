"""Debug script: test distance OCR around the city_center icon.

Usage (with venv activated):
    python scripts/debug_gem_distance.py

Output:
    - Console log with detected city_center bbox and parsed KM
    - Annotated image saved to data/debug/gem_distance_<timestamp>.png
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


TEMPLATES_DIR = Path("data/templates/gathergem")
EXPAND_MARGIN = 60  # px around city_center


def upscale(image: np.ndarray, scale: int = 3) -> np.ndarray:
    """Resize image by integer scale using nearest-neighbor (keeps sharp edges)."""
    h, w = image.shape[:2]
    return cv2.resize(image, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)


def try_ocr_configs(crop: np.ndarray, lang: str = "eng"):
    """Try multiple Tesseract configs and return all raw results."""
    import pytesseract

    if len(crop.shape) == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop

    # Preprocess variants
    variants = [
        ("gray", gray),
        ("gray_up3x", upscale(gray, 3)),
        ("invert", cv2.bitwise_not(gray)),
        ("invert_up3x", upscale(cv2.bitwise_not(gray), 3)),
        ("binary", cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)[1]),
        ("binary_up3x", upscale(cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)[1], 3)),
    ]

    # PSM modes to try
    psms = [6, 7, 8, 13]

    all_results = []
    for name, img in variants:
        for psm in psms:
            config = f"--psm {psm}"
            try:
                data = pytesseract.image_to_data(
                    img,
                    lang=lang,
                    config=config,
                    output_type=pytesseract.Output.DICT,
                )
                n = len(data["text"])
                for i in range(n):
                    text = data["text"][i].strip()
                    conf = int(data["conf"][i])
                    if not text:
                        continue
                    all_results.append({
                        "variant": name,
                        "psm": psm,
                        "text": text,
                        "conf": conf,
                        "bbox": (data["left"][i], data["top"][i],
                                 data["left"][i] + data["width"][i],
                                 data["top"][i] + data["height"][i]),
                    })
            except Exception as e:
                logger.debug(f"OCR failed for {name} psm={psm}: {e}")

    return all_results


def parse_km(text: str) -> int | None:
    """Extract 'XX' from strings like '30KM', '30 KM', '30 K M'."""
    import re
    upper = text.upper().replace(" ", "")
    if "KM" in upper:
        m = re.search(r"(\d+)", upper)
        if m:
            return int(m.group(1))
    return None


def main() -> int:
    logger.info("=== Debug: Gem Distance OCR ===")

    wm = WindowManager()
    if wm.hwnd is None:
        logger.error("Game window not found!")
        return 1

    cap = WindowCapture(wm)
    matcher = TemplateMatcher(templates_dir=TEMPLATES_DIR, threshold=0.70)

    image = cap.capture()
    if image is None:
        logger.error("Capture failed")
        return 1

    h, w = image.shape[:2]
    vis = image.copy()

    # 1. Find city_center
    matches = matcher.match(image, template_name="city_center", threshold=0.70)
    if not matches:
        logger.warning("city_center template not found on screen")
        cv2.imshow("Result — city_center NOT found", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return 0

    best = max(matches, key=lambda m: m.confidence)
    cx1, cy1, cx2, cy2 = best.bbox
    conf = best.confidence
    logger.info(f"city_center found: bbox=({cx1},{cy1},{cx2},{cy2}) conf={conf:.2f}")

    # Draw city_center bbox (green)
    cv2.rectangle(vis, (cx1, cy1), (cx2, cy2), (0, 255, 0), 2)
    label = f"city_center {conf:.2f}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(vis, (cx1, cy1 - th - 8), (cx1 + tw + 4, cy1), (0, 255, 0), -1)
    cv2.putText(vis, label, (cx1 + 2, cy1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    # 2. Expanded ROI
    rx1 = max(0, cx1 - EXPAND_MARGIN)
    ry1 = max(0, cy1 - EXPAND_MARGIN)
    rx2 = min(w, cx2 + EXPAND_MARGIN)
    ry2 = min(h, cy2 + EXPAND_MARGIN)

    cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)
    cv2.putText(vis, f"+{EXPAND_MARGIN}px OCR zone", (rx1 + 4, ry1 - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 3. Crop and try multiple OCR configs
    crop = image[ry1:ry2, rx1:rx2]
    if crop.size == 0:
        logger.warning("Expanded crop is empty")
    else:
        logger.info("Running OCR with multiple preprocess + psm combinations...")
        results = try_ocr_configs(crop)
        logger.info(f"Total raw OCR lines across all configs: {len(results)}")

        # Print top unique results sorted by confidence desc
        seen_texts = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x["conf"], reverse=True):
            if r["text"] not in seen_texts:
                seen_texts.add(r["text"])
                unique_results.append(r)

        for r in unique_results[:20]:
            logger.info(
                f"  [variant={r['variant']}, psm={r['psm']}] "
                f"'{r['text']}' (conf={r['conf']})"
            )

        # Parse KM
        parsed_km = None
        for r in unique_results:
            km = parse_km(r["text"])
            if km is not None:
                parsed_km = km
                logger.info(f"  >>> Parsed distance: {parsed_km} KM <<<")
                # Draw winning bbox (magenta) on vis — note bbox is relative to crop
                bx1, by1, bx2, by2 = r["bbox"]
                abs_bx1 = rx1 + bx1
                abs_by1 = ry1 + by1
                abs_bx2 = rx1 + bx2
                abs_by2 = ry2 + by2
                cv2.rectangle(vis, (abs_bx1, abs_by1), (abs_bx2, abs_by2), (255, 0, 255), 3)
                break

        if parsed_km is None:
            logger.warning("No 'XX KM' pattern parsed from any OCR config")

        # Save preprocessed crops for manual inspection
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)[1]
        out_dir = Path("data/debug")
        out_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_dir / "gem_distance_ocr_gray.png"), gray)
        cv2.imwrite(str(out_dir / "gem_distance_ocr_binary.png"), binary)
        cv2.imwrite(str(out_dir / "gem_distance_ocr_gray_up3x.png"), upscale(gray, 3))
        cv2.imwrite(str(out_dir / "gem_distance_ocr_binary_up3x.png"), upscale(binary, 3))
        logger.info("Saved preprocessed crops to data/debug/gem_distance_ocr_*.png")

    # 4. Show & save annotated full image
    scale = min(1.0, 1200 / max(w, h))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))

    win_title = "Gem Distance Debug (green=city_center, red=OCR zone, magenta=KM match)"
    cv2.imshow(win_title, vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"data/debug/gem_distance_{timestamp}.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)
    logger.info(f"Saved annotated image to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
