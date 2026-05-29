# Model Training

## YOLOv8

### Prepare Dataset
1. Annotate screenshots with LabelImg / Roboflow
2. Export to YOLO format
3. Update `src/training/data/dataset.yaml`

### Train
```bash
python scripts/train_yolo.py --epochs 100 --imgsz 640
```

### Evaluate
```bash
python src/training/models/yolo_evaluate.py
```

### Export
```bash
python src/training/models/yolo_export.py --format onnx
```

## OCR

Fine-tune PaddleOCR for ROK-specific fonts:
```bash
python src/training/ocr/ocr_train.py
```

## Targets

- YOLO mAP > 0.95
- OCR accuracy > 98%
