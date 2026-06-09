"""Entry point for ROK Bot Engine v2 (PC Client)."""

import argparse
import sys
from pathlib import Path

import yaml
from loguru import logger

from rokbot.actions.action_factory import ActionFactory
from rokbot.core.config import BotConfig
from rokbot.core.state_machine import StateMachine
from rokbot.pc_controller import PCInput, WindowCapture, WindowManager
from rokbot.utils.logger import setup_logging
from rokbot.vision.ocr_engine import OCREngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ROK Bot Engine v2")
    parser.add_argument("--config", type=Path, default=Path("config/bot.yaml"), help="Path to bot config")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--dry-run", action="store_true", help="Run without executing inputs")
    parser.add_argument("--actions", type=str, default=None, help="Comma-separated action names, or 'all'")
    return parser.parse_args()


def select_actions_interactive() -> list:
    """Show interactive menu to select actions."""
    all_actions = sorted(ActionFactory.list_actions())
    print("\n" + "=" * 40)
    print("ROK Bot — Select Actions")
    print("=" * 40)
    print("0. Run ALL actions")
    for i, name in enumerate(all_actions, start=1):
        print(f"{i}. {name}")
    print("=" * 40)

    while True:
        try:
            choice = input("Enter number(s) separated by comma (e.g. 1,3 or 0): ").strip()
            if not choice:
                continue
            indices = [int(x.strip()) for x in choice.split(",")]
            if 0 in indices:
                return all_actions
            selected = []
            for idx in indices:
                if 1 <= idx <= len(all_actions):
                    selected.append(all_actions[idx - 1])
            if selected:
                return selected
            print("Invalid selection. Please try again.")
        except (ValueError, KeyboardInterrupt):
            print("Invalid input. Please try again.")


def load_config(path: Path, enabled_actions: list) -> BotConfig:
    """Load bot config from YAML, merging actions.yaml if present."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Merge actions.yaml for per-action priorities
    actions_path = Path("config/actions.yaml")
    if actions_path.exists():
        with open(actions_path, "r", encoding="utf-8") as f:
            actions_raw = yaml.safe_load(f)
        if actions_raw and "actions" in actions_raw:
            enabled = []
            priorities = {}
            for name, cfg in actions_raw["actions"].items():
                if cfg.get("enabled", False):
                    enabled.append(name)
                if "priority" in cfg:
                    priorities[name] = cfg["priority"]
            data.setdefault("actions", {})
            data["actions"]["enabled_actions"] = enabled
            data["actions"]["priorities"] = priorities

    # Override with CLI-selected actions
    data.setdefault("actions", {})
    data["actions"]["enabled_actions"] = enabled_actions

    return BotConfig(**data)


def main() -> int:
    args = parse_args()
    setup_logging(Path("data/bot_telemetry/sessions"), level=args.log_level)

    logger.info("=" * 50)
    logger.info("ROK Bot Engine v2 starting (PC Client)")
    logger.info("=" * 50)

    # Determine which actions to run
    if args.actions:
        if args.actions.lower() == "all":
            selected_actions = ActionFactory.list_actions()
        else:
            selected_actions = [a.strip() for a in args.actions.split(",")]
    else:
        selected_actions = select_actions_interactive()

    logger.info(f"Selected actions: {selected_actions}")

    # Load configuration
    config = load_config(args.config, selected_actions)
    logger.info(f"Config loaded: {config.project_name}")

    if args.dry_run:
        logger.info("DRY RUN mode enabled - no inputs will be executed")

    # Initialize PC controller
    window_title = config.pc.window_title
    window_manager = WindowManager(window_title_substring=window_title)
    if not window_manager.is_window_valid():
        logger.error(
            f"Game window not found (looking for '{window_title}').\n"
            "Please launch Rise of Kingdoms first."
        )
        return 1

    screen_capture = WindowCapture(window_manager)
    pc_input = PCInput(window_manager, humanization_config=config.humanization)
    ocr_engine = OCREngine(lang=config.vision.ocr_lang)

    # Initialize and start state machine
    state_machine = StateMachine(
        config,
        pc_input=pc_input,
        screen_capture=screen_capture,
        ocr_engine=ocr_engine,
    )
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
