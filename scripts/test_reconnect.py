"""Quick test script for ReconnectAction on PC client.

Usage (with venv activated):
    python scripts/test_reconnect.py

The script will continuously check for a disconnect screen every 2 seconds
and attempt to reconnect if detected.
"""

import sys
import time
from pathlib import Path

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

from rokbot.actions.reconnect_action import ReconnectAction
from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine
from rokbot.pc_controller import PCInput, WindowCapture, WindowManager
from rokbot.vision.ocr_engine import OCREngine


def main() -> int:
    # Prevent multiple instances
    import psutil
    current_pid = psutil.Process().pid
    script_name = Path(__file__).name
    for proc in psutil.process_iter(['pid', 'cmdline']):
        if proc.info['pid'] != current_pid and proc.info['cmdline']:
            cmd = ' '.join(proc.info['cmdline'])
            if script_name in cmd and 'python' in cmd:
                logger.error(f"Another instance of {script_name} is already running (pid={proc.info['pid']}). Exiting.")
                return 1

    logger.info("=== Reconnect Action Test (PC Client) ===")

    # Minimal config
    config = BotConfig()

    # Init PC controller
    window_manager = WindowManager(window_title_substring="Rise of Kingdoms")
    if not window_manager.is_window_valid():
        logger.error("Game window not found. Please launch Rise of Kingdoms first.")
        return 1

    screen = WindowCapture(window_manager)
    pc_input = PCInput(window_manager)
    ocr = OCREngine(lang=config.vision.ocr_lang)

    # Dummy state machine (just enough for the action to work)
    state_machine = StateMachine(
        config,
        pc_input=pc_input,
        screen_capture=screen,
        ocr_engine=ocr,
    )

    action = ReconnectAction(config, state_machine)

    logger.info("Monitoring for disconnect screen... Press Ctrl+C to stop.")

    try:
        while True:
            if action.can_execute():
                logger.info("Disconnect detected! Attempting reconnect...")
                success = action.execute()
                logger.info(f"Reconnect result: {'SUCCESS' if success else 'FAILED'}")
                if success:
                    logger.info("Back in game. Continuing to monitor...")
            else:
                logger.debug("No disconnect detected.")
            time.sleep(2.0)
    except KeyboardInterrupt:
        logger.info("Stopped by user.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
