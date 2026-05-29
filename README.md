# ROK Bot Engine v2

**Python-Centric | Accuracy-First | Humanization-Engine**

## Overview

ROK Bot Engine v2 is a next-generation automation framework for Rise of Kingdoms, built with Python. It replaces v1's template-matching approach with a ML-powered vision pipeline (YOLOv8 + OCR) and a data-driven humanization engine that simulates real human behavioral distributions.

## Key Features

- **Vision Pipeline**: Three-stage detection (YOLO -> OCR verification -> Template fallback)
- **Humanization Engine**: Distribution-based timing, Bezier movement paths, cognitive state simulation
- **State Machine**: Robust state tracking with stuck detection and recovery
- **Anti-Detection**: Behavioral biometrics, consistent profiles, no process modification
- **Telemetry**: Human gameplay recording and statistical validation

## Quick Start

```bash
# Setup environment
make install-dev

# Configure emulator ADB
bash scripts/setup_adb.sh

# Start bot
make run
```

## Project Structure

See `PROJECT_STRUCTURE_V2.md` for full directory layout.

## Technical Details

See `TECHNICAL_NOTE_V2.md` for architecture, performance targets, and development workflow.

## Requirements

- Python 3.11+
- Android emulator with ADB (LDPlayer / MEmu / BlueStacks)
- (Optional) CUDA for GPU inference

## License

MIT
