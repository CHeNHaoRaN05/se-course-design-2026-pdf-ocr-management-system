"""Execute a configured handwriting detector in an isolated Torch process."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    for arg in ("image", "output", "weights"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    cache = Path(args.output).parent
    os.environ.setdefault("YOLO_CONFIG_DIR", str(cache / "yolo"))
    os.environ.setdefault("MPLCONFIGDIR", str(cache / "matplotlib"))
    from ultralytics import YOLO
    result = YOLO(args.weights).predict(args.image, imgsz=960, conf=.15, iou=.45, device="cpu", verbose=False)[0]
    Path(args.output).write_text(json.dumps(result.boxes.xyxy.cpu().tolist()), encoding="utf-8")


if __name__ == "__main__":
    main()

