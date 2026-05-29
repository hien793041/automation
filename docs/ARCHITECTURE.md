# Architecture Overview

## Layers

1. **Vision Layer**: YOLOv8 + PaddleOCR + OpenCV template fallback
2. **Humanization Layer**: Timing, movement, decision, session engines
3. **State Machine Layer**: Orchestration, context, transitions, recovery
4. **Action Layer**: Game-specific actions with factory pattern
5. **Emulator Layer**: ADB / scrcpy abstraction
6. **Telemetry Layer**: Recording, logging, analytics

## Data Flow

```
Screenshot -> Vision Pipeline -> State Inference -> Humanized Input -> ADB -> Emulator
                   |                                    |
                   v                                    v
            Confidence Calibrator                 Telemetry Log
```

## Design Principles

- Modularity: Easy to swap vision or humanization components
- Testability: Statistical tests for realism
- Observability: Full telemetry per session
