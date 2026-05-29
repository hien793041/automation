#!/usr/bin/env python3
"""Record human gameplay session."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rokbot.telemetry.human_recorder import HumanRecorder
from rokbot.vision.screen_capture import ScreenCapture
from rokbot.core.config import EmulatorConfig


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Record human gameplay")
    parser.add_argument("--player-id", default="player_001")
    parser.add_argument("--output", default="data/human_recordings")
    args = parser.parse_args()

    recorder = HumanRecorder(Path(args.output), player_id=args.player_id)
    capture = ScreenCapture(EmulatorConfig())

    print("Recording... Press Ctrl+C to stop")
    try:
        while True:
            image = capture.capture()
            if image is not None:
                recorder.save_screenshot(image)
            # TODO: record touch events via ADB getevent
    except KeyboardInterrupt:
        pass

    recorder.save_session()
    print(f"Session saved to {recorder.session_dir}")


if __name__ == "__main__":
    main()
