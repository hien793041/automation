#!/usr/bin/env python3
"""Convenience script to start the bot with config."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rokbot.main import main

if __name__ == "__main__":
    sys.exit(main())
