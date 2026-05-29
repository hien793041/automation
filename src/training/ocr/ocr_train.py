"""PaddleOCR fine-tuning script."""

from pathlib import Path


def train(
    data_dir: Path = Path("src/training/data/ocr"),
    epochs: int = 50,
    batch_size: int = 32,
):
    # TODO: implement PaddleOCR fine-tuning
    print("OCR training not yet implemented")


if __name__ == "__main__":
    train()
