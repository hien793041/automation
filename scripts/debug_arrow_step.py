"""Debug script: measure how far one arrow-key press/hold moves the map.

Captures a "before" screenshot, sends the key, waits, captures "after",
then compares a centre patch between the two frames using template matching.

Usage (with venv activated):
    # Test a single quick TAP
    python scripts/debug_arrow_step.py --direction right --duration 0

    # If pyautogui doesn't work with the game, try system-level keyboard input
    python scripts/debug_arrow_step.py --direction right --duration 0 --use-keybd-event
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import time

import cv2
import numpy as np
from loguru import logger

from rokbot.pc_controller.window_capture import WindowCapture
from rokbot.pc_controller.window_manager import WindowManager


def measure_shift(before: np.ndarray, after: np.ndarray, patch_size: int = 400, search_margin: int = 300):
    h, w = before.shape[:2]
    px = (w - patch_size) // 2
    py = (h - patch_size) // 2
    patch = before[py:py + patch_size, px:px + patch_size]

    sx1 = max(0, px - search_margin)
    sy1 = max(0, py - search_margin)
    sx2 = min(w, px + patch_size + search_margin)
    sy2 = min(h, py + patch_size + search_margin)
    search_area = after[sy1:sy2, sx1:sx2]

    gray_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    gray_search = cv2.cvtColor(search_area, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(gray_search, gray_patch, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    match_x = sx1 + max_loc[0]
    match_y = sy1 + max_loc[1]
    dx = match_x - px
    dy = match_y - py
    return dx, dy, float(max_val)


def activate_window_pyautogui(title_substring: str) -> bool:
    """Try to activate the game window via pyautogui."""
    try:
        import pyautogui
        windows = pyautogui.getWindowsWithTitle(title_substring)
        for win in windows:
            if title_substring.lower() in win.title.lower():
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(0.3)
                return True
    except Exception as e:
        logger.debug(f"pyautogui activate failed: {e}")
    return False


def send_key_pyautogui(direction: str, duration: float):
    import pyautogui
    if duration <= 0:
        pyautogui.press(direction)
        logger.info(f"Sent (pyautogui): press('{direction}')")
    else:
        pyautogui.keyDown(direction)
        time.sleep(duration)
        pyautogui.keyUp(direction)
        logger.info(f"Sent (pyautogui): hold('{direction}', {duration:.3f}s)")


def send_key_keybd_event(direction: str, duration: float):
    import win32api
    import win32con

    VK_MAP = {
        "up": win32con.VK_UP,
        "down": win32con.VK_DOWN,
        "left": win32con.VK_LEFT,
        "right": win32con.VK_RIGHT,
    }
    vk = VK_MAP.get(direction)
    if vk is None:
        raise ValueError(f"Unknown direction: {direction}")

    win32api.keybd_event(vk, 0, 0, 0)
    logger.info(f"Sent (keybd_event): keyDown {direction}")
    if duration > 0:
        time.sleep(duration)
    else:
        time.sleep(0.05)
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
    logger.info(f"Sent (keybd_event): keyUp {direction}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug arrow-key step size")
    parser.add_argument("--direction", required=True,
                        choices=["up", "down", "left", "right"],
                        help="Arrow key to test")
    parser.add_argument("--duration", type=float, default=0.0,
                        help="Seconds to hold the key (0 = tap, default 0)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Wait after key before capturing 'after' (default 1.0)")
    parser.add_argument("--count", type=int, default=1,
                        help="Number of trials (default 1)")
    parser.add_argument("--patch-size", type=int, default=400,
                        help="Centre patch size in pixels (default 400)")
    parser.add_argument("--use-keybd-event", action="store_true",
                        help="Use win32api.keybd_event instead of pyautogui (bypasses some anti-bot blocks)")
    args = parser.parse_args()

    logger.info("=== Debug: Arrow Key Step Size ===")
    logger.info(f"Direction: {args.direction}, duration: {args.duration}s, trials: {args.count}")

    wm = WindowManager()
    if wm.hwnd is None:
        logger.error("Game window not found!")
        return 1

    cap = WindowCapture(wm)

    # Activate window robustly
    activated = activate_window_pyautogui("Rise of Kingdoms")
    if not activated:
        logger.warning("pyautogui.activate() failed, falling back to SetForegroundWindow")
        import win32gui
        try:
            win32gui.SetForegroundWindow(wm.hwnd)
            time.sleep(0.3)
        except Exception:
            pass

    out_dir = Path("data/debug/arrow_step")
    out_dir.mkdir(parents=True, exist_ok=True)

    offsets = []

    for trial in range(1, args.count + 1):
        logger.info(f"--- Trial {trial}/{args.count} ---")

        # Capture BEFORE
        before = cap.capture()
        if before is None:
            logger.error("Before-capture failed")
            continue

        # Send key
        if args.use_keybd_event:
            send_key_keybd_event(args.direction, args.duration)
        else:
            send_key_pyautogui(args.direction, args.duration)

        time.sleep(args.delay)

        # Capture AFTER
        after = cap.capture()
        if after is None:
            logger.error("After-capture failed")
            continue

        dx, dy, conf = measure_shift(before, after, patch_size=args.patch_size)
        dist = (dx * dx + dy * dy) ** 0.5
        offsets.append((dx, dy, dist))
        logger.info(f"OFFSET: dx={dx:+4d}, dy={dy:+4d}, distance={dist:.1f}px, match_conf={conf:.3f}")

        if conf < 0.5:
            logger.warning("Match confidence low — map may have moved too far or terrain changed")

        # Save annotated images
        bh, bw = before.shape[:2]
        px = (bw - args.patch_size) // 2
        py = (bh - args.patch_size) // 2

        vis_before = before.copy()
        cv2.rectangle(vis_before, (px, py), (px + args.patch_size, py + args.patch_size),
                      (0, 255, 0), 2)
        cv2.putText(vis_before, "PATCH", (px, py - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        vis_after = after.copy()
        ax = px + dx
        ay = py + dy
        cv2.rectangle(vis_after, (ax, ay), (ax + args.patch_size, ay + args.patch_size),
                      (0, 0, 255), 2)
        cv2.putText(vis_after, f"PATCH moved dx={dx} dy={dy}", (ax, ay - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        cv2.imwrite(str(out_dir / f"trial_{trial:02d}_before.png"), vis_before)
        cv2.imwrite(str(out_dir / f"trial_{trial:02d}_after.png"), vis_after)

    if offsets:
        logger.info("--- Summary ---")
        avg_dx = sum(o[0] for o in offsets) / len(offsets)
        avg_dy = sum(o[1] for o in offsets) / len(offsets)
        avg_dist = sum(o[2] for o in offsets) / len(offsets)
        logger.info(f"Average offset: dx={avg_dx:+.1f}, dy={avg_dy:+.1f}, distance={avg_dist:.1f}px")
        logger.info(f"Saved images to {out_dir}")
    else:
        logger.warning("No successful trials")

    return 0


if __name__ == "__main__":
    sys.exit(main())
