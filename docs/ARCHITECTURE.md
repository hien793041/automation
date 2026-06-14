# Architecture Overview

## Layers

1. **Vision Layer**: OpenCV template matching + Tesseract OCR
2. **Humanization Layer**: Timing, movement, decision, session engines
3. **State Machine Layer**: Orchestration, context, transitions, recovery
4. **Action Layer**: Game-specific actions with factory pattern
5. **PC Controller Layer**: `win32gui` + `pyautogui` window/input interaction

## Data Flow

```
Screenshot -> Vision Pipeline -> State Inference -> Humanized Input -> PC game window
                   |                                    |
                   v                                    v
            Template Matcher                     Telemetry Log (optional)
```

## Design Principles

- Modularity: Easy to swap vision or humanization components
- Testability: Statistical tests for realism
- Observability: Logging per session via `loguru`
