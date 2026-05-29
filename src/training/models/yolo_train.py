"""Ultralytics YOLOv8 training script."""

from pathlib import Path

from ultralytics import YOLO


def train(
    data_yaml: Path = Path("src/training/data/dataset.yaml"),
    model: str = "yolov8n.pt",
    epochs: int = 100,
    imgsz: int = 640,
    device: str = "cpu",
):
    yolo = YOLO(model)
    yolo.train(data=str(data_yaml), epochs=epochs, imgsz=imgsz, device=device)


if __name__ == "__main__":
    train()
