# Vision Pipeline

## Three-Stage Detection

### Stage 1: YOLOv8
- Detect all UI elements simultaneously
- Per-class confidence thresholds (learned from validation)
- High confidence (>0.85) -> direct use
- Medium confidence (0.5-0.85) -> OCR verification

### Stage 2: OCR Verification
- Read text near detected bbox
- Confirm context (e.g., "Gather" near gather_btn)
- Mismatch -> reject or fallback

### Stage 3: Template Fallback
- OpenCV template matching in specific ROI
- Last resort for critical states

## Calibration

Run `scripts/train_yolo.py` and validate on held-out test set.
Update thresholds via `ConfidenceCalibrator` to achieve target precision.
