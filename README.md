# ROK Bot Engine v2

**Python-Centric | Accuracy-First | Humanization-Engine**

## Overview

ROK Bot Engine v2 is a next-generation automation framework for Rise of Kingdoms, built with Python. It runs against the **PC client** on Windows using computer vision (template matching + OCR) and a data-driven humanization engine that simulates real human behavioral distributions.

## Key Features

- **Vision Pipeline**: Template matching + OCR verification
- **Humanization Engine**: Distribution-based timing, Bezier movement paths, cognitive state simulation
- **State Machine**: Robust state tracking with stuck detection and recovery
- **Anti-Detection**: Behavioral biometrics, consistent profiles, no process modification
- **PC Integration**: Direct interaction with the Windows game window via `win32gui` + `pyautogui`

## Quick Start

```bash
# Setup environment
make install-dev

# Start bot
make run
```

## Project Structure

See `PROJECT_STRUCTURE_V2.md` for full directory layout.

## Technical Details

See `TECHNICAL_NOTE_V2.md` for architecture, performance targets, and development workflow.

## Requirements

- Python 3.11+
- Windows PC with Rise of Kingdoms PC client
- (Optional) CUDA for GPU inference

## License

MIT
