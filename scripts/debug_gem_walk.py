"""Debug script: test the random-walk arrow-key strategy without full gem logic.

Usage (with venv activated):
    # Dry-run: only logs, no real key presses
    python scripts/debug_gem_walk.py --dry-run --steps 30

    # Live: actually presses arrow keys in the game window
    python scripts/debug_gem_walk.py --steps 30 --key-duration 0.12

Output:
    - Console log of every step / backtrack
    - Summary of visited tiles and path taken
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import random
import time

from loguru import logger

from rokbot.actions.gather_gem_action import GemRandomWalker


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug Gem Random Walk")
    parser.add_argument("--steps", type=int, default=50, help="Max steps (default 50)")
    parser.add_argument("--radius", type=int, default=50, help="Radius in km (default 50)")
    parser.add_argument("--key-duration", type=float, default=0.12, help="Seconds to hold each arrow key (default 0.12)")
    parser.add_argument("--delay", type=float, default=0.8, help="Seconds between steps (default 0.8)")
    parser.add_argument("--dry-run", action="store_true", help="Log only, do not send real key presses")
    args = parser.parse_args()

    logger.info("=== Debug: Gem Random Walk ===")
    logger.info(f"Config: radius={args.radius}km, max_steps={args.steps}, key_duration={args.key_duration}s, dry_run={args.dry_run}")

    walker = GemRandomWalker(radius=args.radius)
    walker.KEY_HOLD_DURATION = args.key_duration

    pc_input = None
    if not args.dry_run:
        from rokbot.pc_controller.window_manager import WindowManager
        from rokbot.pc_controller.pc_input import PCInput

        wm = WindowManager()
        if wm.hwnd is None:
            logger.error("Game window not found! Use --dry-run to test logic without a window.")
            return 1
        pc_input = PCInput(wm)
        logger.info("Game window found — live key presses ENABLED")
        logger.warning("Make sure the game is focused and on the WORLD MAP. Press Ctrl+C to abort.")
        time.sleep(2.0)
    else:
        logger.info("Dry-run mode — no real keys will be pressed")

    backtrack_count = 0
    max_backtracks = 30

    for step in range(args.steps):
        valid = walker.get_valid_directions()

        if valid:
            direction = random.choice(valid)
            walker.move(direction)
            backtrack_count = 0
            logger.info(
                f"Step {step + 1:3d}/{args.steps} | MOVE  {direction:5s} | "
                f"pos={walker.current_pos} | visited={len(walker.visited)} | "
                f"dist_from_home={walker.distance_from_home():.1f}km"
            )
        else:
            if backtrack_count >= max_backtracks:
                logger.warning("Too many consecutive backtracks — stopping")
                break
            bt = walker.backtrack()
            if bt is None:
                logger.info("Back at home with no moves left — stopping")
                break
            backtrack_count += 1
            logger.info(
                f"Step {step + 1:3d}/{args.steps} | BACK  {bt:5s} | "
                f"pos={walker.current_pos} | visited={len(walker.visited)} | "
                f"bt#{backtrack_count}"
            )

        if pc_input:
            key = direction if valid else bt
            pc_input.hold_key(key, walker.KEY_HOLD_DURATION)

        time.sleep(args.delay)

    logger.info("--- Walk finished ---")
    logger.info(f"Final position      : {walker.current_pos}")
    logger.info(f"Tiles visited       : {len(walker.visited)}")
    logger.info(f"Path history length : {len(walker.history)}")
    logger.info(f"Max distance reached: {max((x*x + y*y)**0.5 for x, y in walker.visited):.1f}km")

    # Print a tiny ASCII grid of the walked area (compact)
    if walker.visited:
        xs = [p[0] for p in walker.visited]
        ys = [p[1] for p in walker.visited]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        if max(max_x - min_x, max_y - min_y) <= 40:
            logger.info("Visited grid (H=home, *=visited, C=current):")
            for y in range(max_y, min_y - 1, -1):
                row = ""
                for x in range(min_x, max_x + 1):
                    if (x, y) == walker.current_pos:
                        row += "C"
                    elif (x, y) == walker.home_pos:
                        row += "H"
                    elif (x, y) in walker.visited:
                        row += "*"
                    else:
                        row += "."
                logger.info("  " + row)
        else:
            logger.info("Walked area too large to print ASCII grid (>40 tiles)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
