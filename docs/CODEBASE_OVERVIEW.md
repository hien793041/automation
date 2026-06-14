# ROK Bot Engine v2 — Codebase Overview

> **Scope**: Tổng quan kiến trúc, tính năng chính, và đánh giá chất lượng code hiện tại.  
> **Updated**: 2026-06-09  
> **Status**: Refactored and cleaned; full action-layer humanization integrated.

---

## 1. Tổng quan

ROK Bot Engine v2 là bot automation cho **Rise of Kingdoms (ROK) PC Client**, chạy trên Windows. Bot sử dụng:

- **Computer Vision**: YOLOv8 (primary), OpenCV template matching (fallback), Tesseract OCR (text verification).
- **PC Controller**: Tương tác trực tiếp với cửa sổ game qua `win32gui` + `pyautogui`.
- **State Machine**: Quản lý trạng thái bot và điều phối các action theo priority.
- **Humanization**: Cơ chế anti-detection (đang ở trạng thái partial integration).

---

## 2. Project Structure

```
rok-bot/
├── config/                    # YAML configs
│   ├── bot.yaml               # Master config (actions, interval, thresholds)
│   ├── actions.yaml           # Per-action flags & priorities
│   ├── combos.yaml            # User-defined action sequences
│   └── humanization.yaml      # Timing/movement/fatigue distributions
│
├── src/
│   ├── rokbot/                # Core bot package (~59 files)
│   │   ├── main.py            # CLI entry point
│   │   ├── core/              # Orchestration layer
│   │   │   ├── config.py          # Pydantic v2 BotConfig
│   │   │   ├── state_machine.py   # Main loop & tick logic
│   │   │   ├── state_context.py   # State history & stuck tracking
│   │   │   ├── state_transitions.py # Transition rules registry
│   │   │   └── exceptions.py      # BotException hierarchy
│   │   ├── actions/           # Game automation actions
│   │   │   ├── base_action.py         # Abstract BaseAction
│   │   │   ├── action_factory.py      # Registry + factory
│   │   │   ├── combo_loader.py        # Load combos.yaml
│   │   │   ├── dynamic_combo_action.py # Sequence wrapper
│   │   │   ├── gather_action.py
│   │   │   ├── scout_action.py
│   │   │   ├── train_troops_action.py
│   │   │   ├── alliance_help_action.py
│   │   │   ├── reconnect_action.py
│   │   │   ├── barbarian_attack_action.py
│   │   │   ├── gather_gem_action.py
│   │   │   ├── rally_fort_action.py
│   │   │   ├── scout_cave_high_action.py
│   │   │   ├── scout_cave_low_action.py
│   │   │   └── villager_help_action.py
│   │   ├── vision/            # Computer vision pipeline
│   │   │   ├── template_matcher.py
│   │   │   ├── ocr_engine.py
│   │   │   ├── image_preprocessor.py
│   │   │   └── region_of_interest.py
│   │   ├── pc_controller/     # Windows PC integration
│   │   │   ├── window_manager.py
│   │   │   ├── window_capture.py
│   │   │   └── pc_input.py
│   │   ├── humanization/      # Anti-detection engine
│   │   │   ├── timing_engine.py       # Delay distributions
│   │   │   ├── movement_engine.py     # Bezier mouse paths
│   │   │   ├── session_manager.py     # Break scheduling
│   │   │   ├── decision_engine.py     # Fatigue / distraction / frustration
│   │   │   └── error_simulator.py     # Misclick injection
│   │   └── utils/             # Shared utilities
│   │       ├── logger.py
│   │       ├── math_utils.py
│   │       └── map_navigation.py      # City/world navigation mixin
│   ├── training/              # YOLO & OCR training (standalone)
│   │   ├── models/yolo_train.py
│   │   └── ocr/ocr_train.py
│   └── rust_perf/             # Rust extension scaffolding (unused)
│
├── scripts/                   # Debug & dev utilities
│   ├── capture_grid.py
│   ├── capture_template.py
│   ├── debug_how_far.py
│   ├── debug_gem_detector.py
│   ├── compare_human_bot.py
│   └── ...
│
├── tests/                     # Minimal test coverage
│   ├── conftest.py
│   ├── unit/                  # ~4 files, ~6-8 assertions
│   └── integration/           # 3 skeleton tests
│
├── data/
│   ├── templates/             # OpenCV template images
│   └── bot_telemetry/         # Session logs
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   ├── ANTI_DETECTION.md
│   ├── HUMANIZATION_ENGINE.md
│   ├── VISION_PIPELINE.md
│   ├── MODEL_TRAINING.md
│   ├── DATA_COLLECTION.md
│   └── CODEBASE_OVERVIEW.md   # This file
│
├── models/yolo/               # Trained YOLO weights
├── requirements.txt           # Runtime deps (PC stack)
└── pyproject.toml             # Build deps (chưa đồng bộ với requirements)
```

---

## 3. Tính năng chính

### 3.1. Resource Gathering
- Auto chạy chuỗi 6 bước: Find → Resource → Find → Gather → New Troop → Send.
- Giới hạn số troop đang đi gather (`max_troops`).
- Tự động chuyển giữa City và World Map.

### 3.2. Scouting
- Nhận diện Scout Camp qua template matching.
- Tự động tap building và navigate popup sequence.
- **Scout Cave**: 2 variant (high/low) cho cave scouting.

### 3.3. Training Troops
- Detect troop training completed → collect.
- Dùng tab "Tổng Quan" (Overview) để tìm idle building và start training.

### 3.4. Alliance Help & Reconnect
- Template matching để tap help buttons.
- Auto reconnect khi mất kết nối.

### 3.5. Dynamic Combos
- Ngườ dùng định nghĩa action chains trong `config/combos.yaml`.
- `DynamicComboAction` tự động detect city/world state và switch map.

### 3.6. Humanization Engine
- `TimingEngine`: Delay theo Gaussian/log-normal/exponential distributions (dùng trong `BaseAction`, `PCInput`, `StateMachine`).
- `MovementEngine`: Quadratic Bezier + Fitts's Law (dùng trong `PCInput` cho mouse path).
- `SessionManager`: Lên lịch nghỉ giải lao (dùng trong `StateMachine`).
- `DecisionEngine`: Mô phỏng fatigue, focus, distraction (chia sẻ giữa `StateMachine`, `PCInput`, và mọi action).
- `ErrorSimulator`: Inject misclick (dùng trong `PCInput`).

### 3.7. Vision Pipeline
- **YOLOv8**: Primary detection với per-class confidence thresholds.
- **Template Matching**: OpenCV `TM_CCOEFF_NORMED` fallback.
- **OCR**: Tesseract (`pytesseract`) cho text verification và timer parsing.
- **Image Preprocessing**: Resize, denoise, CLAHE contrast enhancement.

---

## 4. Architecture Flow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   main.py   │────▶│  StateMachine    │────▶│  ActionFactory  │
│  (entry)    │     │  (main loop)     │     │  (create action)│
└─────────────┘     └──────────────────┘     └─────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌─────────────────┐  ┌──────────────┐
│ WindowCapture│  │   PCInput       │  │ OCREngine    │
│ (screenshot) │  │ (click/tap)     │  │ (text read)  │
└──────────────┘  └─────────────────┘  └──────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ Vision Pipeline: YOLO → Template → OCR       │
└──────────────────────────────────────────────┘
```

**Tick Loop** (mỗi `screenshot_interval_seconds`, mặc định 2s):
1. Capture screenshot.
2. Dismiss overlays (chat, guide).
3. Check stuck condition.
4. Evaluate actions theo priority order.
5. Execute action đầu tiên thỏa `can_execute()`.
6. Sleep until next tick.

---

## 5. Vấn đề & Đề xuất tối ưu

### 🔴 High Priority — Cần xử lý sớm

#### A. Code Duplication trong Actions (~6 file bị ảnh hưởng)
Hầu hết các action đều duplicate cùng một pattern:

| Function | Duplicate trong |
|----------|-----------------|
| `_random_point_in_bbox` | `GatherAction`, `ScoutAction`, `TrainTroopsAction`, `AllianceHelpAction`, `ReconnectAction`, `DynamicComboAction` |
| `_roi_from_ratio` | `GatherAction`, `ScoutAction`, `TrainTroopsAction`, `DynamicComboAction` |
| `_detect_city_state` / `_ensure_in_city` / `_ensure_in_world` | `GatherAction`, `ScoutAction`, `TrainTroopsAction`, `DynamicComboAction` |

**Đề xuất**: Tạo mixin/helper `MapNavigationMixin` hoặc `CityStateHelper` trong `src/rokbot/utils/` hoặc `src/rokbot/pc_controller/`.

```python
# Ví dụ ý tưởng
class MapNavigationMixin:
    def _random_point_in_bbox(self, bbox): ...
    def _ensure_in_city(self, pc_input, timeout=10): ...
    def _ensure_in_world(self, pc_input, timeout=10): ...
    def _detect_city_state(self, image) -> Literal["city", "world", "unknown"]: ...
```

#### B. Dead Code — Đã dọn dẹp

| Module/File | Tình trạng |
|-------------|-----------|
| `vision/screen_capture.py` (ADB) | **Đã xóa** |
| `vision/yolo_detector.py` | **Đã xóa** |
| `utils/stuck_detector.py` | **Đã xóa** (thay thế bởi `StateContext.is_stuck()`) |
| `utils/retry_policy.py` | **Đã xóa** |
| `utils/image_utils.py` | **Đã xóa** |
| `input/` subsystem (3 files) | **Đã xóa** |
| `telemetry/` package (4 files) | **Đã xóa** |
| `humanization/biometric_profile.py` | **Đã xóa** |
| `scripts/record_human.py` | **Đã xóa** (phụ thuộc `ScreenCapture` đã xóa) |
| `StateMachine._state_handlers` | **Đã xóa** |
| `config/emulator.yaml`, `config/vision.yaml`, `config/actions_full.yaml`, `config/scout_only.yaml`, `config/templates_meta.yaml` | **Đã xóa** |

#### C. Config Mismatch (đã giải quyết)

| Vấn đề | Chi tiết |
|--------|----------|
| `vision.yaml` ghi `ocr.engine: paddleocr` | **Đã xóa** `config/vision.yaml`; code dùng `pytesseract` từ `bot.yaml` |
| `bot.yaml` có `ocr_lang: eng+vie` | Giá trị từ `bot.yaml` được dùng |
| `pyproject.toml` thiếu PC deps | Đã thêm `pytesseract`, `pyautogui`, `pywin32`; bỏ `paddleocr` dư |

**Trạng thái**: Các file config legacy đã được xóa; `config/humanization.yaml` được load runtime trong `main.py`.

#### D. Emulator Config Bloat (đã giải quyết)
- `EmulatorConfig` trong `BotConfig` và `config/emulator.yaml` là legacy từ phiên bản Android emulator.
- Bot hiện tại là PC-only.

**Trạng thái**: `EmulatorConfig`, `config/emulator.yaml`, và các ADB reference đã được xóa.

---

### 🟡 Medium Priority — Cải thiện chất lượng

#### E. Hardcoded Resolution
- `ROIManager.DEFAULT_ROIS` và `_roi_from_ratio` đều assume 1920×1080.
- Không có abstraction layer cho resolution khác.

**Đề xuất**: Thêm `ResolutionAdapter` scale ROI theo tỷ lệ so với reference resolution.

#### F. Unreachable Code
- `DynamicComboAction.execute()` có `raise` đứng sau `return False` → unreachable.

**Đề xuất**: Xóa dòng `raise` thừa.

#### G. Inconsistent Logging
- `TrainTroopsAction` log step count không nhất quán: `"Step 3/5"` → `"Step 4/6"` → `"Step 5/6"`.

**Đề xuất**: Fix denominator.

---

### 🟢 Low Priority — Nice to have

#### H. Test Coverage
- Hiện tại chỉ ~6-8 assertions cho cả codebase.
- Cần unit tests cho `TemplateMatcher`, `OCREngine`, `YOLODetector`, và các action helpers.

#### I. Rust Module
- `src/rust_perf/` là scaffolding PyO3/Maturin nhưng chưa implement.
- Nếu không cần performance-critical path, có thể xóa để giảm clutter.

---

## 6. Quick Win Checklist

Những thay đổi nhỏ, impact lớn, ít rủi ro:

- [ ] **Extract `MapNavigationMixin`** — giảm ~150 dòng duplicate.
- [x] **Xóa `utils/stuck_detector.py`** — dead code.
- [x] **Xóa `utils/retry_policy.py`** — dead code.
- [x] **Xóa `utils/image_utils.py`** — dead code.
- [x] **Xóa `input/` package** — dead subsystem.
- [x] **Xóa `telemetry/` package** — dead subsystem.
- [x] **Xóa `vision/screen_capture.py`** — dead code.
- [x] **Xóa `_state_handlers` legacy** — dọn dẹp `StateMachine`.
- [x] **Xóa `DynamicComboAction` unreachable `raise`** — bug nhỏ.
- [x] **Fix `TrainTroopsAction` step logging** — polish.
- [x] **Đồng bộ `requirements.txt` ↔ `pyproject.toml`** — tránh lỗi cài đặt.
- [x] **Xóa `config/vision.yaml`** (`paddleocr` → `pytesseract`) — tránh confusion.

---

## 7. Humanization — Quyết định quan trọng

Đây là subsystem lớn nhất đang ở trạng thái **"đã viết nhưng chưa dùng"**:

| Module | Đã viết | Đã dùng | Ghi chú |
|--------|---------|---------|---------|
| `TimingEngine` | ✅ | ✅ | Dùng trong `BaseAction`, `PCInput`, `StateMachine` |
| `MovementEngine` | ✅ | ✅ | Dùng trong `PCInput` cho mouse path |
| `SessionManager` | ✅ | ✅ | Dùng trong `StateMachine` cho break scheduling |
| `DecisionEngine` | ✅ | ✅ | Chia sẻ giữa `StateMachine`, `PCInput`, và mọi action |
| `ErrorSimulator` | ✅ | ✅ | Dùng trong `PCInput` cho misclick injection |
| `BiometricProfile` | ❌ | — | **Đã xóa**; profile được load qua JSON timing profile hoặc `config/humanization.yaml` |

**Trạng thái**: Toàn bộ humanization subsystem đã được integrate vào runtime.

---

## 8. Tóm tắt

| Metric | Giá trị |
|--------|---------|
| Total Python files (rokbot) | ~59 |
| Entry points | 1 (`main.py`) |
| Actions implemented | 11 built-in + dynamic combos |
| Vision backends | YOLOv8, OpenCV, Tesseract |
| Test coverage | ~6-8 assertions (cần mở rộng) |
| Dead / orphan modules | ~0 (cleanup complete) |
| Duplicate helpers | ~3 functions × 4-6 files |

---

## 9. Changelog (2026-06-09)

### Đã thực hiện

- ✅ **Tạo `MapNavigationMixin`** (`src/rokbot/utils/map_navigation.py`) — gom `_random_point_in_bbox`, `roi_from_ratio`, `_detect_city_state`, `_ensure_in_city`, `_ensure_in_world`.
- ✅ **Refactor 11 action files** để inherit `MapNavigationMixin` — loại bỏ ~150 dòng duplicate.
- ✅ **Integrate humanization vào main loop**:
  - `PCInput` giờ dùng `TimingEngine` (reaction delay), `MovementEngine` (Bezier swipe path), `ErrorSimulator` (misclick injection).
  - `StateMachine` giờ có `SessionManager` (break scheduling, active-hour checks) và `DecisionEngine` (fatigue, distraction, delay injection).
- ✅ **Xóa dead code**:
  - `src/rokbot/input/` package (3 files)
  - `src/rokbot/telemetry/` package (4 files)
  - `src/rokbot/utils/stuck_detector.py`
  - `src/rokbot/utils/retry_policy.py`
  - `src/rokbot/utils/image_utils.py`
  - `src/rokbot/vision/screen_capture.py` (ADB legacy)
  - `src/rokbot/vision/yolo_detector.py`
  - `src/rokbot/humanization/biometric_profile.py`
  - `scripts/record_human.py`
  - Legacy `_state_handlers` trong `StateMachine`
  - `config/emulator.yaml`, `config/vision.yaml`, `config/actions_full.yaml`, `config/scout_only.yaml`, `config/templates_meta.yaml`
- ✅ **Fix bugs nhỏ**:
  - Xóa unreachable `raise` trong `DynamicComboAction.execute()`
  - Fix `TrainTroopsAction` step logging (consistent 1/5 → 5/5)
  - Fix `MovementEngine` jitter — giữ nguyên điểm đầu/cuối
  - Fix `StateMachine` initial state (`UNKNOWN` ngay sau init)
- ✅ **Đồng bộ config**:
  - `pyproject.toml`: thêm `pytesseract`, `pyautogui`, `pywin32`; bỏ `paddleocr`, `paddlepaddle`
  - Xóa `config/vision.yaml`, `config/emulator.yaml`, và các config preset không dùng
  - `main.py` load `config/humanization.yaml` runtime và merge vào `HumanizationConfig`

**Kết luận**: Codebase đã được dọn dẹp đáng kể. Dead code được loại bỏ, humanization được integrate đầy đủ, và code duplication giảm ~150 dòng. Tất cả tests pass.

---

## 10. Changelog (2026-06-14) — Full action-layer humanization

### Đã thực hiện

- ✅ **Centralize humanization in `BaseAction`** (`src/rokbot/actions/base_action.py`):
  - Shared `TimingEngine` instance for every action.
  - Shared `DecisionEngine` from `StateMachine` so fatigue/frustration are consistent across the whole session.
  - Helpers: `human_delay`, `pre_action_delay`, `post_action_delay`, `decision_delay`, `random_point_in_bbox`, `humanized_tap`, `humanized_tap_match`, `record_success`, `record_error`.
- ✅ **Humanize `MapNavigationMixin`**:
  - `random_point_in_bbox` now supports Gaussian jitter and edge margin.
  - `_ensure_in_city` / `_ensure_in_world` use `transition_wait` distribution instead of `time.sleep(random.uniform(...))`.
- ✅ **Humanize `PCInput`**:
  - `key_back`, `type_text`, `scroll` now apply reaction/click-interval delays.
  - `share_decision_engine()` lets `StateMachine` propagate cognitive state to the input layer.
- ✅ **Add new timing distributions** in `TimingEngine` and `config/humanization.yaml`:
  - `transition_wait`, `menu_wait`, `post_error_wait`.
- ✅ **Refactor all actions** to use shared humanization helpers instead of hard-coded sleeps:
  - `barbarian_attack`, `gather`, `gather_gem`
  - `scout`, `train_troops`, `rally_fort`
  - `scout_cave_high`, `scout_cave_low`
  - `alliance_help`, `villager_help`, `reconnect`, `dynamic_combo`
- ✅ **Remove unused methods**: `BaseAction.decision_delay`, `PCInput.key_home`, `ErrorSimulator.maybe_wrong_button`, `TimingEngine.decision_delay`, `SessionManager.sample_session_length_hours`
- ✅ **Remove duplicate `TimingEngine` / `_human_delay()`** from `BarbarianAttackAction`, `ScoutAction`, `TrainTroopsAction`.
- ✅ **Update docs**: `docs/HUMANIZATION_ENGINE.md` now documents BaseAction integration and action-layer coverage.

**Kết luận**: Every bot action now samples delays from fitted distributions and reports success/error to a shared cognitive model, making behavior significantly harder to distinguish from a real player. All existing tests pass.

---

## 11. Changelog (2026-06-14) — Input layer & config hardening

### Đã thực hiện
- ✅ **Fix runtime bug**: `resource_name` → `chosen_name` typo in `gather_action.py`.
- ✅ **Load `config/humanization.yaml` at runtime** (`src/rokbot/main.py`):
  - Merge `timing`, `movement`, `session` blocks into `HumanizationConfig`.
  - `TimingEngine` now uses configured distributions when no JSON profile is provided.
- ✅ **Expand `HumanizationConfig`** (`src/rokbot/core/config.py`) with `timing`, `movement`, `session` fields.
- ✅ **Harden `PCInput`** (`src/rokbot/pc_controller/pc_input.py`):
  - Activate game window before every input method (`tap`, `swipe`, `scroll`, `type_text`, `press_key`, `hold_key`, `hold_key_native`, `hold_click_at`, `move_to_safe_zone`).
  - Set `pyautogui.PAUSE = 0` and rely entirely on `TimingEngine`.
  - `tap()` now moves the cursor along a Bezier path generated by `MovementEngine`.
  - Add `hold_click_at()` humanized helper used by `GatherGemAction`.
  - Humanize `hold_key` / `hold_key_native` with reaction delays, key-up safety, and fatigue-based duration jitter.
  - Humanize `move_to_safe_zone()` with a short Bezier path.
- ✅ **Humanize `StateMachine._dismiss_overlays()`** — overlay close delay now samples from `click_interval`.
- ✅ **Read `max_troops` from `config/actions.yaml`** in `GatherAction`, `GatherGemAction`, `RallyFortAction` via new `BaseAction.get_action_config()` helper.
- ✅ **Fix `GatherGemAction` hold-click** — remove direct `pyautogui`/`time.sleep` code; use centralized `PCInput.hold_click_at()` and randomized click targets.
- ✅ **Fix `ScoutCaveLowAction` step numbering** (`Step 2/6` → `Step 2/7`, etc.).
- ✅ **Update `config/actions.yaml`**: add `gather_gem`, `scout_cave_high`, `scout_cave_low`, `barbarian_attack` with `max_troops` defaults.
- ✅ **Migrate `pyproject.toml` linter config** từ `[tool.ruff]` sang `[tool.ruff.lint]`.
- ✅ **Clean lint**: `ruff check .` pass.

**Kết luận**: Input layer now consistently focuses the game window and moves the mouse like a human. Config files are actually loaded and used. All existing tests pass.
