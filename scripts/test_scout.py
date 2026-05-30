"""Test ScoutAction independently.

Usage (with venv activated):
    python scripts/test_scout.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

from rokbot.actions.scout_action import ScoutAction
from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine
from rokbot.pc_controller import PCInput, WindowCapture, WindowManager
from rokbot.vision.ocr_engine import OCREngine


def main() -> int:
    logger.info("=== Scout Action Test ===")

    config = BotConfig()
    wm = WindowManager(window_title_substring=config.pc.window_title)
    if not wm.is_window_valid():
        logger.error("Game window not found")
        return 1

    state_machine = StateMachine(
        config,
        pc_input=PCInput(wm),
        screen_capture=WindowCapture(wm),
        ocr_engine=OCREngine(lang=config.vision.ocr_lang),
    )

    action = ScoutAction(config, state_machine)

    if not action.can_execute():
        logger.warning("ScoutAction.can_execute() returned False (Scout Camp bubble not visible)")
        return 0

    logger.info("Scout bubble detected! Executing...")
    success = action.execute()
    logger.info(f"ScoutAction result: {'SUCCESS' if success else 'FAILED'}")

    if success:
        logger.info("Building tapped. If a scout popup opened, please capture it for the next step.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
