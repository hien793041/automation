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
│   │   │   ├── ocr_engine.py                # Tesseract OCR wrapper
│   │   │   ├── template_matcher.py          # OpenCV template matching
│   │   │   ├── image_preprocessor.py        # Resize, denoise, enhance
│   │   │   └── region_of_interest.py        # ROI selector & manager
│   │   │
│   │   ├── 📁 humanization/                  # Humanization engine
│   │   │   ├── __init__.py
│   │   │   ├── timing_engine.py             # Distribution-based delays
│   │   │   ├── movement_engine.py           # Bezier + Fitts's-law paths
│   │   │   ├── decision_engine.py           # Fatigue, distraction, emotion
│   │   │   ├── error_simulator.py           # Misclick injection
│   │   │   └── session_manager.py           # Bimodal sessions, Poisson breaks
│   │   │
│   │   ├── 📁 actions/                       # Game actions
│   │   │   ├── __init__.py
│   │   │   ├── base_action.py               # Abstract base + humanization helpers
│   │   │   ├── action_factory.py            # Action registry & factory
│   │   │   ├── combo_loader.py              # Load combos.yaml
│   │   │   ├── dynamic_combo_action.py      # User-defined action sequences
│   │   │   ├── gather_action.py             # Resource gathering
│   │   │   ├── gather_gem_action.py         # Gem gathering
│   │   │   ├── scout_action.py              # Scouting
│   │   │   ├── scout_cave_high_action.py    # High-level cave scouting
│   │   │   ├── scout_cave_low_action.py     # Low-level cave scouting
│   │   │   ├── train_troops_action.py       # Training troops
│   │   │   ├── alliance_help_action.py      # Alliance help
│   │   │   ├── villager_help_action.py      # Villager help
│   │   │   ├── rally_fort_action.py         # Rally barbarian forts
│   │   │   ├── barbarian_attack_action.py   # Attack barbarians
│   │   │   └── reconnect_action.py          # Handle disconnect
│   │   │
│   │   ├── 📁 pc_controller/                 # Windows PC integration
│   │   │   ├── __init__.py
│   │   │   ├── window_manager.py            # Find/activate game window
│   │   │   ├── window_capture.py            # Screenshot via PIL
│   │   │   └── pc_input.py                  # Mouse/keyboard via pyautogui
│   │   │
│   │   ├── 📁 utils/                         # Shared utilities
│   │   │   ├── __init__.py
│   │   │   ├── logger.py                    # Structured logging (loguru)
│   │   │   ├── math_utils.py                # Gaussian, log-normal sampling
│   │   │   └── map_navigation.py            # City/world navigation mixin
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
│   │   │   ├── ocr_train.py                  # Tesseract fine-tuning
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
│   ├── humanization.yaml                     # Humanization parameters
│   ├── actions.yaml                          # Action definitions & priorities
│   └── combos.yaml                           # User-defined action sequences
│
├── 📁 models/
│   ├── 📁 yolo/
│   │   ├── rok_ui_v8.pt                      # YOLOv8 trained model
│   │   ├── rok_ui_v8.onnx                    # ONNX export for inference
│   │   └── labels.yaml                       # Class names & IDs
│   ├── 📁 ocr/
│   │   └── tesseract_model/                  # Fine-tuned OCR model (optional)
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
│   ├── start_bot.py                          # Start bot with config
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
