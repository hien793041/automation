"""Evaluate YOLO model: mAP, precision, recall."""

from pathlib import Path

from ultralytics import YOLO


def evaluate(
    model_path: Path = Path("models/yolo/rok_ui_v8.pt"),
    data_yaml: Path = Path("src/training/data/dataset.yaml"),
):
    model = YOLO(str(model_path))
    metrics = model.val(data=str(data_yaml))
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP75: {metrics.box.map75:.4f}")


if __name__ == "__main__":
    evaluate()
