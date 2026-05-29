"""Export YOLO model to ONNX / CoreML."""

from pathlib import Path

from ultralytics import YOLO


def export(
    model_path: Path = Path("models/yolo/rok_ui_v8.pt"),
    format: str = "onnx",
):
    model = YOLO(str(model_path))
    model.export(format=format)


if __name__ == "__main__":
    export()
