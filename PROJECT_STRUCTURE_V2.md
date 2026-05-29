# ROK Bot Engine v2 - Project Structure
## Python-Centric | Accuracy-First | Humanization-Engine

```
rok-bot-engine/
├── 📁 src/
│   ├── 📁 rokbot/                          # Main Python package
│   │   ├── __init__.py
│   │   ├── 📁 core/                         # Core engine
│   │   │   ├── __init__.py
│   │   │   ├── state_machine.py             # State machine orchestrator
│   │   │   ├── state_transitions.py         # Transition rules & guards
│   │   │   ├── state_context.py             # Context: history, confidence, retries
│   │   │   ├── config.py                    # Pydantic config models
│   │   │   └── exceptions.py                # BotException, StuckError, etc.
│   │   │
│   │   ├── 📁 vision/                       # Computer Vision layer
│   │   │   ├── __init__.py
│   │   │   ├── yolo_detector.py             # YOLOv8 UI element detection
│   │   │   ├── ocr_engine.py                # PaddleOCR / EasyOCR wrapper
│   │   │   ├── template_matcher.py          # OpenCV fallback matching
│   │   │   ├── screen_capture.py            # ADB screencap / scrcpy
│   │   │   ├── image_preprocessor.py        # Resize, denoise, enhance
│   │   │   ├── region_of_interest.py        # ROI selector & manager
│   │   │   └── confidence_calibrator.py     # Per-class threshold tuning
│   │   │
│   │   ├── 📁 humanization/                  # Humanization engine (CRITICAL)
│   │   │   ├── __init__.py
│   │   │   ├── timing_engine.py             # Distribution-based delays
│   │   │   ├── movement_engine.py           # Bezier + jerk-limited paths
│   │   │   ├── decision_engine.py           # Fatigue, distraction, emotion
│   │   │   ├── error_simulator.py           # Misclick, wrong-button
│   │   │   ├── session_manager.py           # Bimodal sessions, Poisson breaks
│   │   │   ├── biometric_profile.py         # Human data profile loader
│   │   │   └── distributions/               # Fitted distributions
│   │   │       ├── reaction_time.json       # Gaussian(mu,sigma) from real data
│   │   │       ├── click_interval.json      # Log-normal params
│   │   │       ├── session_length.json      # Bimodal distribution
│   │   │       ├── movement_jerk.json       # Jerk profile data
│   │   │       └── break_interval.json      # Poisson lambda parameter
│   │   │
│   │   ├── 📁 actions/                       # Game actions
│   │   │   ├── __init__.py
│   │   │   ├── base_action.py               # Abstract base
│   │   │   ├── gather_action.py             # Resource gathering
│   │   │   ├── alliance_help_action.py      # Alliance help
│   │   │   ├── daily_quest_action.py        # Daily quests
│   │   │   ├── scout_action.py              # Scouting
│   │   │   ├── train_troops_action.py       # Training troops
│   │   │   └── action_factory.py            # Action registry & factory
│   │   │
│   │   ├── 📁 emulator/                      # Emulator management
│   │   │   ├── __init__.py
│   │   │   ├── adb_client.py                # ADB wrapper
│   │   │   ├── scrcpy_client.py             # Scrcpy streaming
│   │   │   ├── emulator_manager.py          # LDPlayer/MEmu control
│   │   │   ├── device_profile.py            # Device fingerprint spoofing
│   │   │   └── emulator_config.py           # Emulator settings
│   │   │
│   │   ├── 📁 input/                         # Input execution
│   │   │   ├── __init__.py
│   │   │   ├── adb_input.py                 # adb shell input tap/swipe
│   │   │   ├── input_queue.py               # Action queue with timestamps
│   │   │   ├── input_verifier.py            # Feedback loop: verify execution
│   │   │   └── input_logger.py              # Input telemetry logging
│   │   │
│   │   ├── 📁 telemetry/                     # Data collection & logging
│   │   │   ├── __init__.py
│   │   │   ├── telemetry_collector.py       # Collect bot metrics
│   │   │   ├── human_recorder.py            # Record human gameplay
│   │   │   ├── session_logger.py            # Per-session log
│   │   │   └── analytics_exporter.py        # Export for analysis
│   │   │
│   │   ├── 📁 utils/                         # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── logger.py                    # Structured logging (loguru)
│   │   │   ├── retry_policy.py              # Exponential backoff + jitter
│   │   │   ├── stuck_detector.py            # Stuck detection & recovery
│   │   │   ├── image_utils.py               # Image I/O, conversion
│   │   │   └── math_utils.py              # Gaussian, log-normal sampling
│   │   │
│   │   └── main.py                           # Entry point
│   │
│   ├── 📁 training/                          # Model training
│   │   ├── 📁 data/
│   │   │   ├── 📁 raw/                       # Raw screenshots
│   │   │   ├── 📁 annotated/                 # LabelImg / Roboflow output
│   │   │   ├── 📁 augmented/                 # Augmented images
│   │   │   └── dataset.yaml                  # YOLO dataset config
│   │   ├── 📁 models/
│   │   │   ├── yolo_train.py                 # Ultralytics training script
│   │   │   ├── yolo_export.py                # Export to ONNX/CoreML
│   │   │   └── yolo_evaluate.py              # mAP, precision, recall
│   │   ├── 📁 ocr/
│   │   │   ├── ocr_train.py                  # PaddleOCR fine-tuning
│   │   │   └── ocr_evaluate.py               # Accuracy evaluation
│   │   └── requirements.txt
│   │
│   └── 📁 rust_perf/                         # Rust performance modules (optional)
│       ├── Cargo.toml
│       ├── src/
│       │   ├── lib.rs
│       │   ├── screen_capture.rs             # Fast screen capture
│       │   ├── image_buffer.rs               # Shared memory frame buffer
│       │   └── input_injector.rs             # Low-latency input
│       └── pyproject.toml                    # maturin for Python bindings
│
├── 📁 config/
│   ├── bot.yaml                              # Main bot configuration
│   ├── emulator.yaml                         # Emulator settings
│   ├── vision.yaml                           # YOLO / OCR / Template params
│   ├── humanization.yaml                     # Humanization parameters
│   ├── actions.yaml                          # Action definitions & priorities
│   └── templates_meta.yaml                   # Template metadata
│
├── 📁 models/
│   ├── 📁 yolo/
│   │   ├── rok_ui_v8.pt                      # YOLOv8 trained model
│   │   ├── rok_ui_v8.onnx                    # ONNX export for inference
│   │   └── labels.yaml                       # Class names & IDs
│   ├── 📁 ocr/
│   │   └── paddleocr_model/                  # Fine-tuned OCR model
│   └── 📁 templates/                         # Fallback template images
│       ├── 📁 gather_flow/
│       ├── 📁 error_states/
│       └── 📁 common_ui/
│
├── 📁 data/
│   ├── 📁 human_recordings/                  # Human gameplay data
│   │   ├── 📁 player_001/
│   │   │   ├── session_2026_05_20_14_30/
│   │   │   │   ├── screenshots/              # Timed screenshots
│   │   │   │   ├── touch_events.jsonl        # x, y, timestamp, pressure
│   │   │   │   ├── timing_data.jsonl           # Reaction times, intervals
│   │   │   │   └── session_metadata.json
│   │   │   └── fitted_distributions.json     # Fitted params per player
│   │   └── 📁 player_002/
│   │       └── ...
│   ├── 📁 bot_telemetry/                     # Bot runtime telemetry
│   │   └── 📁 sessions/
│   └── 📁 analysis/                          # Analysis output
│       ├── timing_distribution.png
│       ├── movement_heatmap.png
│       └── human_vs_bot_comparison.html
│
├── 📁 scripts/
│   ├── setup_env.sh                          # Setup Python + Rust env
│   ├── setup_adb.sh                          # ADB setup
│   ├── start_bot.py                          # Start bot with config
│   ├── record_human.py                       # Record human gameplay
│   ├── train_yolo.py                         # Train YOLO model
│   ├── fit_distributions.py                  # Fit human data to distributions
│   └── compare_human_bot.py                  # Compare telemetry
│
├── 📁 tests/
│   ├── 📁 unit/
│   │   ├── test_state_machine.py
│   │   ├── test_vision.py
│   │   ├── test_humanization.py
│   │   └── test_actions.py
│   ├── 📁 integration/
│   │   ├── test_full_gather_flow.py
│   │   ├── test_vision_accuracy.py
│   │   └── test_humanization_realism.py
│   ├── 📁 fixtures/
│   │   ├── screenshots/
│   │   └── mock_data/
│   └── conftest.py
│
├── 📁 docs/
│   ├── ARCHITECTURE.md
│   ├── VISION_PIPELINE.md
│   ├── HUMANIZATION_ENGINE.md
│   ├── DATA_COLLECTION.md
│   ├── MODEL_TRAINING.md
│   └── ANTI_DETECTION.md
│
├── 📁 notebooks/
│   ├── 01_explore_screenshots.ipynb
│   ├── 02_train_yolo.ipynb
│   ├── 03_fit_distributions.ipynb
│   ├── 04_analyze_human_data.ipynb
│   └── 05_compare_human_bot.ipynb
│
├── pyproject.toml                            # Poetry / setuptools
├── poetry.lock                               # Locked dependencies
├── requirements.txt                            # Alternative install
├── .python-version                           # pyenv version
├── .gitignore
├── Makefile                                  # Common tasks
└── README.md
```
