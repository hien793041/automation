"""Entry point for ROK Bot Engine v2."""

import argparse
import sys
from pathlib import Path

from loguru import logger

from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine
from rokbot.utils.logger import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ROK Bot Engine v2")
    parser.add_argument("--config", type=Path, default=Path("config/bot.yaml"), help="Path to bot config")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--dry-run", action="store_true", help="Run without executing inputs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(Path("data/bot_telemetry/sessions"), level=args.log_level)

    logger.info("=" * 50)
    logger.info("ROK Bot Engine v2 starting")
    logger.info("=" * 50)

    # Load configuration
    config = BotConfig()
    # TODO: load from YAML if available
    logger.info(f"Config loaded: {config.project_name}")

    if args.dry_run:
        logger.info("DRY RUN mode enabled - no inputs will be executed")

    # Initialize and start state machine
    state_machine = StateMachine(config)
    try:
        state_machine.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        state_machine.stop()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1

    logger.info("ROK Bot Engine v2 stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
