# ROK Bot Engine v2 - Feature Checklist

> File này dùng để theo dõi tiến độ implement các tính năng.  
> Đánh dấu `[x]` khi hoàn thành, `[~]` khi đang làm, `[ ]` khi chưa bắt đầu.

---

## 1. Game Actions (Action Layer)

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 1.1 | **Gather** (Thu thập tài nguyên) | `src/rokbot/actions/gather_action.py` | `[ ]` | - Implement `can_execute()`: check gather node visible + troops available<br>- Implement `execute()` flow:<br>  1. Detect gather node trên bản đồ<br>  2. Tap vào node<br>  3. Tap "Gather" button<br>  4. Chọn số lượng quân / commander<br>  5. Confirm march<br>- Handle state: `NODE_SELECTED` → `TROOP_SELECT` → `MARCHING` → `GATHERING` |
| 1.2 | **Alliance Help** (Giúp đồng minh) | `src/rokbot/actions/alliance_help_action.py` | `[ ]` | - Implement `can_execute()`: detect help button available<br>- Implement `execute()`:<br>  1. Mở alliance menu<br>  2. Tap "Help All" / từng help button<br>  3. Verify đã help xong |
| 1.3 | **Scout** (Trinh sát) | `src/rokbot/actions/scout_action.py` | `[~]` | - ✅ `can_execute()`: Template matching tìm bubble "Thăm dò" + kiểm tra đang ở city view<br>- ✅ `execute()`: Tự động vào thành phố nếu đang ở world map → Tap tòa nhà → Popup → Gửi<br>- ⏳ Cần template: `in_city_icon.png`, `enter_city_icon.png` (góc dưới phải)<br>- ⏳ Cần template: `scout_button.png`, `scout_send.png` (popup)<br>- ⏳ Handle scout report popup |
| 1.4 | **Train Troops** (Luyện quân) | `src/rokbot/actions/train_troops_action.py` | `[ ]` | - Implement `can_execute()`: check barracks free + đủ resources<br>- Implement `execute()`:<br>  1. Navigate đến barracks / stable / range / siege<br>  2. Tap train slot trống<br>  3. Chọn loại quân + số lượng<br>  4. Confirm train<br>  5. Handle speedup nếu config cho phép |
| 1.5 | **Reconnect** (Xử lý mất kết nối) | `src/rokbot/actions/reconnect_action.py` | `[x]` | - ✅ `can_execute()`: OCR detect disconnect keywords + fallback heuristic màu sắc<br>- ✅ `execute()`:<br>  1. OCR tìm button text (reconnect/retry/ok/confirm)<br>  2. Tap button qua PC Input (pyautogui)<br>  3. Wait 5s + verify lại bằng screenshot<br>  4. Retry tối đa 3 lần<br>- Cần cài `paddleocr` để OCR hoạt động tốt, nếu không sẽ dùng fallback heuristic |
| 1.6 | **Action Factory** | `src/rokbot/actions/action_factory.py` | `[x]` | - ✅ Đã register đầy đủ: gather, alliance_help, scout, train_troops, reconnect<br>- Priority queue theo config `actions.yaml`<br>- Chọn action phù hợp dựa trên state + priority |
| 1.7 | **Wire Action → State Machine** | `src/rokbot/core/state_machine.py` | `[x]` | - ✅ Tích hợp Action Factory vào `_tick()` (`_evaluate_and_execute_actions`)<br>- ✅ Gọi `action.can_execute()` trước khi `execute()`<br>- ✅ Handle action result (success/fail) để update context |

---

## 2. Vision Pipeline (Nhận diện hình ảnh)

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 2.1 | **Template Matching (primary)** | `src/rokbot/vision/template_matcher.py` | `[x]` | - ✅ OpenCV template matching là backend chính<br>- ✅ ROI + multi-scale support<br>- Templates lưu trong `data/templates/` |
| 2.2 | **OCR Engine** | `src/rokbot/vision/ocr_engine.py` | `[x]` | - ✅ Đã chuyển sang Tesseract OCR (`pytesseract`)<br>- ✅ Hoạt động ổn định trên Windows, không lỗi backend<br>- Đọc text từ screenshot, trả về bbox + confidence |
| 2.3 | **Template Fallback** | `src/rokbot/vision/template_matcher.py` | `[x]` | - ✅ OpenCV template matching trong ROI cụ thể<br>- ✅ Dùng khi YOLO + OCR đều fail (hiện tại là primary cho small UI)<br>- ✅ Templates lưu trong `data/templates/` |
| 2.4 | **Confidence Calibration** | — | `[x]` | - ❌ File `confidence_calibrator.py` đã xóa<br>- Thresholds được định nghĩa trực tiếp trong code/config |
| 2.5 | **Vision Integration với State Machine** | `src/rokbot/core/state_machine.py` | `[ ]` | - Implement `_infer_next_state()`:<br>  1. Chụp screenshot<br>  2. Chạy YOLO detect<br>  3. (Optional) OCR verify<br>  4. Map detections → `BotState`<br>  5. Return next state |
| 2.6 | **YOLO Model Preparation** | `models/yolo/` | `[ ]` | - Chuẩn bị hoặc download model `rok_ui_v8.pt`<br>- Export ONNX: `rok_ui_v8.onnx`<br>- Tạo `labels.yaml` mapping class IDs |

---

## 3. Humanization Engine (Giả lập ngườii thật)

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 3.1 | **Timing Engine** | `src/rokbot/humanization/timing_engine.py` | `[ ]` | - Implement sampler từ phân phối:<br>  - Gaussian: reaction time, decision time<br>  - Log-normal: click intervals<br>  - Exponential: break durations<br>- Dùng params từ `config/bot.yaml` (`reaction_time_mu`, `click_interval_shape`, etc.) |
| 3.2 | **Movement Engine** | `src/rokbot/humanization/movement_engine.py` | `[x]` | - ✅ Quadratic Bezier curves với perpendicular control offset<br>- ✅ Fitts's Law cho movement duration<br>- ✅ Micro-jitter per point<br>- ✅ Tích hợp vào `PCInput.tap()` / `swipe()` |
| 3.3 | **Decision Engine** | `src/rokbot/humanization/decision_engine.py` | `[ ]` | - Fatigue model: sigmoid curve sau 2h<br>- Distraction probability ↑ theo fatigue<br>- Misclick rate (`base_misclick_rate`)<br>- Change-mind rate |
| 3.4 | **Session Manager** | `src/rokbot/humanization/session_manager.py` | `[ ]` | - Schedule-aware activity probability<br>- Bimodal session lengths<br>- Poisson break intervals<br>- Tự động pause/resume bot theo schedule |
| 3.5 | **Biometric Profile** | — | `[x]` | - ❌ File `biometric_profile.py` đã xóa<br>- Profile được load từ `config/humanization.yaml` hoặc JSON timing profile |
| 3.6 | **Error Simulator** | `src/rokbot/humanization/error_simulator.py` | `[ ]` | - Random misclick gần target (không phải hoàn toàn random)<br>- Occasional pause ("distracted")<br>- Double-tap nếu không thấy phản hồi |
| 3.7 | **Validation** | Tests / Analytics | `[ ]` | - Timing: KS-test p > 0.05 so với human data<br>- Movement: DTW distance < threshold<br>- Session: Chi-square p > 0.05 |

---

## 4. PC Controller (Windows Game Client)

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 4.1 | **Window Manager** | `src/rokbot/pc_controller/window_manager.py` | `[x]` | - ✅ Tìm cửa sổ game bằng `win32gui.EnumWindows`<br>- ✅ Theo dõi window handle, lấy client rect<br>- Config `window_title` trong `config/bot.yaml` |
| 4.2 | **Window Capture** | `src/rokbot/pc_controller/window_capture.py` | `[x]` | - ✅ Chụp screenshot bằng `PIL.ImageGrab.grab(bbox=...)`<br>- ✅ Trả về numpy array BGR (OpenCV format) |
| 4.3 | **PC Input** | `src/rokbot/pc_controller/pc_input.py` | `[x]` | - ✅ Click chuột bằng `pyautogui.click()` (tọa độ tương đối cửa sổ)<br>- ✅ Swipe/drag, scroll, key press (ESC = back)<br>- FAILSAFE enabled (kéo chuột ra góc màn hình để dừng khẩn cấp) |
| 4.4 | **Emulator Layer** | — | `[x]` | - ✅ Đã xóa toàn bộ (ADB, scrcpy, emulator_manager, adb_input)<br>- Bot chỉ hỗ trợ PC client (Windows) |

---

## 5. State Machine (Điều phối)

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 5.1 | **Main Loop** | `src/rokbot/core/state_machine.py` | `[x]` | - ✅ Vòng lặp `_tick()` đang chạy<br>- ✅ StateMachine đã nhận `pc_input`, `window_capture`, `ocr_engine`<br>- ✅ Tích hợp Action Factory vào `_tick()` (`_evaluate_and_execute_actions`)<br>- ✅ Actions được sort theo priority, chạy 1 action/tick |
| 5.2 | **State Context** | `src/rokbot/core/state_context.py` | `[~]` | - ✅ Đã có tracking state, retry count, timestamps<br>- Có thể cần thêm: action history, screenshot history |
| 5.3 | **Stuck Detection** | `src/rokbot/core/state_machine.py` | `[~]` | - ✅ `is_stuck()` theo `stuck_threshold_seconds` (60s)<br>- Có thể fine-tune threshold theo state |
| 5.4 | **Recovery Sequence** | `src/rokbot/core/state_machine.py` | `[ ]` | - Implement `_enter_recovery()` đầy đủ:<br>  1. Press Back (1-3 lần)<br>  2. Wait 2-5s<br>  3. Press Home<br>  4. Relaunch game nếu cần<br>- Max retry: `max_retry_attempts` (default 3) |
| 5.5 | **State Transitions** | `src/rokbot/core/state_transitions.py` | `[ ]` | - Define `TransitionRule` cho các state chuyển đổi hợp lệ<br>- Validate transition trước khi chuyển<br>- Log transition với metadata |
| 5.6 | **Exception Handling** | `src/rokbot/core/exceptions.py` | `[~]` | - ✅ Đã có `RecoveryError`, `StuckError`<br>- Có thể thêm: `VisionError`, `ActionError`, `ConnectionError` |

---

## 6. Telemetry & Data Collection

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 6.1 | **Human Recorder** | — | `[x]` | - ❌ `scripts/record_human.py` và `rokbot/telemetry/` đã xóa<br>- Humanization params cấu hình qua `config/humanization.yaml` |
| 6.2 | **Distribution Fitting** | `scripts/fit_distributions.py` | `[ ]` | - Chạy sau khi có recordings<br>- Input: `data/human_recordings/`<br>- Fit: Gaussian, Log-normal, Exponential params<br>- Output: update `config/bot.yaml` hoặc profile |
| 6.3 | **Session Logger** | — | `[x]` | - ❌ `src/rokbot/telemetry/` đã xóa<br>- Logging qua `loguru` vào `data/bot_telemetry/` |
| 6.4 | **Telemetry Collector** | — | `[x]` | - ❌ `src/rokbot/telemetry/` đã xóa |
| 6.5 | **Compare Human vs Bot** | `scripts/compare_human_bot.py` | `[ ]` | - Dùng sau khi bot chạy được<br>- So sánh phân phối timing, movement<br>- Validate humanization quality |

---

## 7. Model Training

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 7.1 | **Template Library** | `data/templates/` | `[~]` | - Thu thập/cập nhật template cho UI elements<br>- Tổ chức theo flow (gather_flow, error_states, common_ui) |
| 7.2 | **Template Evaluation** | — | `[ ]` | - Đo precision/recall của template matching trên screenshot samples<br>- Cập nhật thresholds trong code/config |
| 7.3 | **OCR Training** | `src/training/ocr/ocr_train.py` | `[ ]` | - Fine-tune Tesseract cho font ROK-specific<br>- Target: accuracy > 98% |
| 7.4 | **OCR Evaluation** | `src/training/ocr/ocr_evaluate.py` | `[ ]` | - Đánh giá OCR accuracy trên test set |
| 7.5 | **Dataset Management** | `src/training/data/` | `[ ]` | - Tổ chức folder: train/val/test<br>- Đảm bảo balance class labels |

---

## 8. Anti-Detection

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 8.1 | **Behavioral Biometrics** | Humanization Layer | `[ ]` | - Consistent profile across sessions<br>- Không thay đổi random mỗi action |
| 8.2 | **Timing Randomization** | Timing Engine | `[ ]` | - Distribution-based (KHÔNG phải uniform random)<br>- Phải giống phân phối người thật |
| 8.3 | **Emulator Fingerprint** | — | `[x]` | - ❌ Không áp dụng; bot chạy trên PC client Windows |
| 8.4 | **Session Realism** | Session Manager | `[ ]` | - Không chạy 24/7 liên tục<br>- Realistic hours (evening heavy)<br>- Natural breaks |

---

## 9. Config & Infrastructure

| # | Tính năng | File chính | Trạng thái | Việc cần làm chi tiết |
|---|-----------|------------|------------|----------------------|
| 9.1 | **Bot Config Loader** | `src/rokbot/core/config.py` | `[x]` | - ✅ Default config đã cập nhật (bỏ daily_quest, thêm reconnect)<br>- ✅ `main.py` load `config/bot.yaml` + merge `config/actions.yaml` (priorities)<br>- Support env var override |
| 9.2 | **Actions Config** | `config/actions.yaml` | `[x]` | - ✅ Đã update: bỏ `daily_quest`, thêm `reconnect` (priority 0, timeout 30s)<br>- Có thể thêm params cụ thể per action |
| 9.3 | **Makefile Commands** | `Makefile` | `[~]` | - ✅ Đã có: install, test, lint, format, run<br>- Có thể thêm: `make record`, `make train`, `make calibrate` |
| 9.4 | **Tests** | `tests/` | `[~]` | - Unit tests cho từng module<br>- Integration tests cho full pipeline<br>- Statistical tests cho humanization<br>- ✅ Script test nhanh: `scripts/test_reconnect.py`, `scripts/test_scout_action.py` |
| 9.5 | **Requirements** | `requirements.txt` | `[x]` | - ✅ Đã có: ultralytics, opencv-python, loguru, numpy, scipy<br>- ✅ Thêm: `pyautogui`, `pywin32` cho PC controller<br>- ✅ Thêm: `pytesseract` cho OCR (thay thế paddleocr/paddlepaddle)<br>- Có thể thêm nếu thiếu |

---

## Roadmap đề xuất (thứ tự implement)

```
Phase 1: Foundation (có thể chạy được)
├── [ ] 9.1 Config loader hoàn chỉnh
├── [x] 4.1 PC Controller (WindowManager + WindowCapture + PCInput)
├── [ ] 2.1 YOLO model ready
├── [ ] 2.5 Vision integration (state inference)
├── [ ] 5.4 Recovery sequence
└── [ ] 1.6 Action Factory + 1.7 Wire vào State Machine

Phase 2: Game Actions
├── [ ] 1.1 Gather (quan trọng nhất)
├── [ ] 1.2 Alliance Help (đơn giản nhất)
├── [ ] 1.3 Scout
├── [ ] 1.4 Train Troops
└── [x] 1.5 Reconnect (xử lý disconnect)

Phase 3: Humanization
├── [x] 3.1 Timing Engine
├── [x] 3.2 Movement Engine
├── [x] 3.3 Decision Engine
├── [x] 3.4 Session Manager
└── [x] 3.6 Error Simulator

Phase 4: Polish
├── [ ] 2.2 OCR Verification
├── [ ] 2.3 Template Fallback
├── [ ] 4.5 Input Queue + 4.6 Input Verifier
├── [ ] 6.3 Session Logger + 6.4 Telemetry
├── [ ] 8.x Anti-Detection hardening
└── [ ] 9.4 Tests hoàn chỉnh
```

---

## Notes

- **Quan trọng**: Các action hiện tại đều return `True` (stub). Bot sẽ không thực sự làm gì trong game cho đến khi implement xong.
- **Model YOLO**: Nếu không train được ngay, có thể dùng template matching tạm thời để test action logic.
- **Humanization**: Có thể bỏ qua Phase 3 ban đầu để test action cho ổn, sau đó thêm humanization sau.
- **PC Client**: Bot hiện đang hỗ trợ bản PC (Windows) qua `pyautogui` + `win32gui`. Không còn dùng emulator/ADB.
- **Window Title**: Nếu game của bạn là bản tiếng Việt, sửa `window_title` trong `config/bot.yaml` thành `"Rise of Kingdoms"` (hoặc tên cửa sổ tương ứng).
