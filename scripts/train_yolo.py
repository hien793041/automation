#!/usr/bin/env python3
"""Train YOLOv8 model on annotated dataset."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ultralytics import YOLO


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Train YOLOv8")
    parser.add_argument("--data", default="src/training/data/dataset.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--model", default="yolov8n.pt")
    args = parser.parse_args()

    model = YOLO(args.model)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz)
    print("Training complete")


if __name__ == "__main__":
    main()
