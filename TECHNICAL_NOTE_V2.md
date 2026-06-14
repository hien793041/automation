# ROK Bot Engine v2 - Technical Note
## Python-Centric | Accuracy-First | Humanization-Engine
### For Kimi Code Analysis

---

## 1. PHILOSOPHY SHIFT

**v1 (C#)**: Windows desktop app, UI-first, template matching, quick demo.
**v2 (Python)**: Accuracy-first, data-driven, ML-based vision, humanization engine.

| Aspect | v1 | v2 |
|--------|----|----|
| Language | C# | Python + optional Rust |
| Vision | Template matching | YOLO + OCR + Template fallback |
| Humanization | Basic jitter | Distribution-based biometric model |
| UI | WPF dashboard | Minimal CLI / optional web |
| Data | None | Human recordings + fitted distributions |
| Accuracy | ~70-85% | Target >95% |
| Anti-detection | Random delays | Behavioral biometric simulation |

---

## 2. VISION PIPELINE (Accuracy Engine)

### 2.1 Detection Pipeline

```
Input: Screenshot (1920x1080)
    |
    V
Stage 1: Template Matching
  - Detect UI elements via OpenCV template matching
  - Output: bbox + class + confidence
  - Threshold: class-dependent (0.5-0.9)
    |
    +-- Match found --> Use template result
    |
    +-- No match --> Stage 2
                  |
                  V
          Stage 2: OCR Verification
            - Read text near expected region
            - Verify context
            - Example: "Gather" text near gather_btn bbox
                  |
                  +-- Match --> Use
                  |
                  +-- Mismatch --> Fail / retry
```

### 2.2 Template Matching

**File**: `rokbot/vision/template_matcher.py`

**Responsibility**: Detect UI elements via OpenCV template matching with optional ROI and multi-scale support.

**Key Design**:
- Per-class thresholds defined in code/config
- Higher threshold for critical elements (e.g., connection_lost = 0.92)
- Lower threshold for small/variable elements (e.g., icon_marching = 0.75)

**Output**: List of detection results (class_name, confidence, bbox, center)

**Fallback**: OCR or heuristic color checks

### 2.3 OCR Engine with Context Verification

**File**: `rokbot/vision/ocr_engine.py`

**Responsibility**: Read text from screenshots and verify detections.

**Key Design**:
- Tesseract OCR backend (`pytesseract`)
- ROI targeting: only process specific regions
- Timer parsing: HH:MM:SS, MM:SS formats
- Context verification: read text near detected bbox to confirm class

**Example**: Template detects "gather_btn" but OCR reads "Attack" nearby -> mismatch, reject detection

---

## 3. HUMANIZATION ENGINE (Core Differentiator)

### 3.1 Philosophy

> Humanization is NOT adding random noise.
> Humanization is SIMULATING the statistical distribution of real human behavior.

**Data Flow**:
```
Human Gameplay Recording
  -> Extract timing, movement, decision data
  -> Fit to statistical distributions
  -> Sample from distributions during bot execution
  -> Compare bot telemetry vs human data
```

### 3.2 Timing Engine

**File**: `rokbot/humanization/timing_engine.py`

**Responsibility**: Sample delays from fitted human distributions.

**Supported Distributions**:
- Gaussian: reaction time, decision time
- Log-normal: click intervals
- Exponential: break durations
- Bimodal (2 Gaussian mixture): session lengths

**Key**: Each bot instance loads ONE consistent distribution profile, not random per-action.

### 3.3 Movement Engine

**File**: `rokbot/humanization/movement_engine.py`

**Responsibility**: Generate human-like mouse/touch trajectories.

**Key Design**:
- Quadratic Bezier curve with perpendicular control point offset
- Fitts Law for movement duration: MT = a + b * log2(D/W + 1)
- Micro-jitter per point (Gaussian noise)
- Jerk profile loaded from human data (optional)

**Parameters**:
- Control point offset: 5-15% of distance
- Step duration: 10ms per point
- Jitter: sigma=1.5 pixels
- Fitts intercept a=100ms, slope b=50ms/bit

### 3.4 Decision Engine

**File**: `rokbot/humanization/decision_engine.py`

**Responsibility**: Simulate human cognitive state affecting decisions.

**Cognitive State**:
- Fatigue: 0-1, sigmoid curve, steep after 2 hours
- Distraction probability: base 0.08 + fatigue * 0.15
- Focus: 1.0 -> 0.3 as fatigue increases
- Frustration: 0-1, increases with errors

**Behaviors**:
- Distracted: pause, look away (random long delay)
- Misclick: base 1% * fatigue * difficulty
- Change mind: base 2% + frustration * 5%
- Reaction time: base * focus_multiplier + fatigue_penalty

### 3.5 Session Manager

**File**: `rokbot/humanization/session_manager.py`

**Responsibility**: Manage human-like session patterns.

**Schedule**:
- Sleep (2-8 AM): 5% active probability
- Work (9-17): 30% active probability
- Evening (18-1): 70% active probability

**Session Length**: Bimodal distribution
- 60% short sessions: Normal(1.5h, 0.3h)
- 40% long sessions: Normal(5h, 0.8h)

**Breaks**: Exponential(15min) + 5min minimum
**Break Interval**: Poisson process, lambda=2 hours

---

## 4. STATE MACHINE (Robustness Engine)

### 4.1 Design

**File**: `rokbot/core/state_machine.py`

**States**: UNKNOWN, IDLE, NODE_SELECTED, TROOP_SELECT, MARCHING, GATHERING, GATHER_COMPLETE, WAREHOUSE_FULL, CONNECTION_LOST, VIP_POPUP, CAPTCHA, ERROR_RECOVERY

**Transitions**: Defined per state with conditions and priorities
- Critical states checked first (CAPTCHA, CONNECTION_LOST)
- Normal states inferred from YOLO detections
- Error recovery triggered by stuck detector

**Stuck Detection**: Track state history, if same state for N consecutive checks -> stuck
**Recovery**: Back button -> wait -> if still stuck -> home -> relaunch app

### 4.2 State Context

**File**: `rokbot/core/state_context.py`

**Tracks**:
- Current state + history (last N states with timestamps)
- Confidence scores per detection
- Retry counts per transition
- Timeout timers

---

## 5. DATA COLLECTION (Foundation)

### 5.1 Human Recorder

> Removed: `scripts/record_human.py` and the `rokbot/telemetry/` package have been deleted.
>
> Humanization parameters are now defined in `config/humanization.yaml` or loaded from an optional JSON timing profile.

If you collect human gameplay data externally, store it under `data/human_recordings/` and use `scripts/fit_distributions.py` to derive parameters.

### 5.2 Distribution Fitting

**File**: `scripts/fit_distributions.py`

**Fits**:
- Gaussian: reaction time (scipy.stats.norm.fit)
- Log-normal: click intervals (scipy.stats.lognorm.fit)
- Bimodal: session lengths (sklearn.mixture.GaussianMixture, n_components=2)

**Validation**: KS-test goodness of fit, p-value threshold

---

## 6. ANTI-DETECTION STRATEGY

### 6.1 Multi-Layer Defense

| Layer | Technique | Detection Risk |
|-------|-----------|---------------|
| Process | No game process modification | Undetectable |
| Memory | No injection/hook | Undetectable |
| Network | Normal request pattern | Low risk |
| Input | Windows PC input (`pyautogui` + `win32gui`) | Low risk |
| Timing | Distribution-based (not random) | Medium risk |
| Behavior | Fatigue, distraction, errors | Medium risk |
| Device | PC client, no emulator | Low risk |

### 6.2 Biometric Profile

**Concept**: Each bot instance uses ONE consistent human profile loaded from `config/humanization.yaml` or an optional JSON timing profile. This creates consistent "personality" across sessions.

**Profile includes**:
- Timing distributions (reaction, click interval, decision)
- Movement parameters (Fitts's law, jitter)
- Personality traits (base distraction rate, fatigue rate)

The same `DecisionEngine` instance is shared between `StateMachine`, `PCInput`, and every `BaseAction`, so fatigue and frustration accumulate consistently.

---

## 7. PERFORMANCE TARGETS

| Metric | Target | Measurement |
|--------|--------|-------------|
| YOLO detection mAP | >0.95 | COCO metrics on validation set |
| OCR accuracy | >98% | Character-level on test set |
| State detection accuracy | >95% | End-to-end on gameplay video |
| False positive rate | <2% | Per-class on validation |
| Reaction time realism | KS-test p>0.05 vs human | Statistical test |
| Movement trajectory realism | DTW distance < threshold | Dynamic Time Warping |
| Session pattern realism | Chi-square p>0.05 vs human | Distribution comparison |
| Total action cycle | <3s (excluding waits) | Benchmark |

---

## 8. TESTING STRATEGY

### 8.1 Vision Tests

**File**: `tests/test_vision_accuracy.py`

- Load YOLO model
- Iterate validation dataset
- Calculate precision/recall per class
- Assert precision > 0.90, recall > 0.90

### 8.2 Humanization Tests

**File**: `tests/test_humanization_realism.py`

- **Timing**: KS-test (scipy.stats.ks_2samp) comparing bot vs human reaction times. Assert p > 0.05
- **Movement**: DTW (fastdtw) comparing bot vs human trajectories. Assert distance < threshold
- **Session**: Chi-square test on session length distributions

---

## 9. DEPENDENCIES

```toml
[tool.poetry.dependencies]
python = "^3.11"

# Vision
opencv-python = "^4.8.1"
pytesseract = "^0.3.13"       # OCR

# PC input
pyautogui = "^0.9.54"
pywin32 = "^300"

# Scientific
numpy = "^1.24.0"
scipy = "^1.11.0"
scikit-learn = "^1.3.0"        # GMM for bimodal fitting

# Data
pydantic = "^2.0.0"            # Config models
loguru = "^0.7.0"              # Logging

# Optional: Rust extension
maturin = { version = "^1.0.0", optional = true }

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
black = "^23.0.0"
ruff = "^0.1.0"

[tool.poetry.group.notebook.dependencies]
jupyter = "^1.0.0"
matplotlib = "^3.7.0"
seaborn = "^0.12.0"
plotly = "^5.15.0"
```

---

## 10. KEY TECHNICAL DECISIONS

| Decision | Rationale |
|----------|-----------|
| Python primary | Best CV/ML ecosystem (YOLO, PaddleOCR) |
| Template matching + OCR | Robust enough for PC UI, simpler maintenance |
| OCR verification | Reduce false positives in ambiguous states (Tesseract) |
| Distribution-based humanization | Statistically indistinguishable from human |
| Per-class confidence threshold | Optimize precision/recall per UI element |
| YAML-driven humanization | Foundation for realistic behavior simulation |
| Optional Rust extensions | Performance bottleneck optimization only |
| Modular architecture | Easy to swap vision/humanization components |

---

## 11. DEVELOPMENT WORKFLOW

```
Phase 1: Data Collection (1-2 weeks)
  - Record 5-10 human players (2-4h each)
  - Extract timing, movement, decision data
  - Annotate screenshots for YOLO training

Phase 2: Vision Training (1-2 weeks)
  - Train YOLOv8 on annotated dataset
  - Fine-tune OCR for ROK fonts
  - Calibrate per-class confidence thresholds
  - Validate on held-out test set

Phase 3: Humanization Fitting (1 week)
  - Fit distributions to human data
  - Implement timing/movement/decision engines
  - Validate with statistical tests (KS, DTW)

Phase 4: Integration (1-2 weeks)
  - Integrate vision + humanization + state machine
  - Implement error recovery
  - End-to-end testing on real gameplay

Phase 5: Optimization (ongoing)
  - Profile performance bottlenecks
  - Rust extensions if needed
  - Continuous model improvement
```

---

*Document Version: 2.0*
*Focus: Accuracy-First, Humanization-Engine, Python-Centric*
*Date: 2026-05-29*
