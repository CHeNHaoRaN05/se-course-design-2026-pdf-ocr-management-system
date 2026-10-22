"""Paddle inference adapter: detection, perspective crops and CTC recognition."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile

import cv2
import numpy as np
import yaml

from .tables import ruled_tables
from .config import PACKAGE_ROOT
from .runtime import load_paddle


class PaddleBackend:
    def __init__(self, settings):
        self.cfg = settings
        self.vendor = settings.vendor
        self.paddle = load_paddle(settings)
        self.paddle.set_device(settings.device)
        self.recognizers = {}
        self.detector = None

    def strict_load(self, model, weights):
        if not weights.is_file():
            raise FileNotFoundError(f"Model not installed: {weights}")
        state = self.paddle.load(str(weights))
        expected = model.state_dict()
        if set(state) != set(expected) or any(list(state[k].shape) != list(expected[k].shape) for k in expected):
            raise RuntimeError("Checkpoint keys/shapes do not match model architecture")
        model.set_state_dict({k: v.astype(expected[k].dtype) for k, v in state.items()})
        model.eval()

    def recognizer(self, name):
        if name in self.recognizers:
            return self.recognizers[name]
        from ppocr.data import create_operators
        from ppocr.modeling.architectures import build_model
        from ppocr.postprocess import build_post_process
        cfg = yaml.safe_load((PACKAGE_ROOT / "configs/recognizer.yml").read_text(encoding="utf-8"))
        cfg["Global"]["character_dict_path"] = str(self.vendor / "ppocr/utils/dict/ppocrv5_dict.txt")
        cfg["Global"]["infer_mode"] = True
        decoder = build_post_process(cfg["PostProcess"], cfg["Global"])
        n = len(decoder.character)
        arch = copy.deepcopy(cfg["Architecture"])
        arch["Head"]["out_channels_list"] = {"CTCLabelDecode": n, "SARLabelDecode": n+2, "NRTRLabelDecode": n+3}
        model = build_model(arch)
        weights = self.cfg.recognizer_weights if name == "official" else self.cfg.custom_recognizer
        if weights is None:
            raise ValueError("Custom recognition model is not configured")
        self.strict_load(model, weights)
        ops = []
        for op in copy.deepcopy(cfg["Eval"]["dataset"]["transforms"]):
            key = next(iter(op))
            if "Label" in key:
                continue
            if key == "RecResizeImg":
                op[key]["infer_mode"] = True
            if key == "KeepKeys":
                op[key]["keep_keys"] = ["image"]
            ops.append(op)
        self.recognizers[name] = model, decoder, create_operators(ops, cfg["Global"])
        return self.recognizers[name]

    def recognize_crop(self, crop, name):
        from ppocr.data import transform
        if crop.shape[0] < 1 or crop.shape[1] / crop.shape[0] * 48 > 4096:
            raise ValueError("Text crop too wide; split into shorter lines")
        model, decoder, ops = self.recognizer(name)
        ok, encoded = cv2.imencode(".png", crop)
        if not ok:
            raise ValueError("Invalid crop")
        batch = transform({"image": encoded.tobytes()}, ops)
        # Prevent pathological long lines from allocating unbounded attention tensors.
        if batch is None or batch[0].shape[-1] > 4096:
            raise ValueError("Text crop is invalid or too wide; split it into shorter lines")
        with self.paddle.no_grad():
            result = decoder(model(self.paddle.to_tensor(batch[0][None])))[0]
        return str(result[0]), float(result[1])

    def general_boxes(self, image):
        from ppocr.data import create_operators, transform
        from ppocr.modeling.architectures import build_model
        from ppocr.postprocess import build_post_process
        if self.detector is None:
            config = yaml.safe_load((PACKAGE_ROOT / "configs/detector.yml").read_text(encoding="utf-8"))
            model = build_model(config["Architecture"])
            self.strict_load(model, self.cfg.detector_weights)
            operators = create_operators([
                {"DetResizeForTest": {"limit_side_len": 960, "limit_type": "max"}},
                {"NormalizeImage": {"std": [0.229, .224, .225], "mean": [.485, .456, .406], "scale": "1./255.", "order": "hwc"}},
                {"ToCHWImage": None}, {"KeepKeys": {"keep_keys": ["image", "shape"]}},
            ])
            self.detector = model, build_post_process(config["PostProcess"]), operators
        model, postprocess, ops = self.detector
        batch, shape = transform({"image": image}, ops)
        with self.paddle.no_grad():
            prediction = model(self.paddle.to_tensor(batch[None]))
        return postprocess(prediction, shape[None])[0]["points"]

    def handwriting_boxes(self, image):
        # Torch executes in a separate process to avoid native-library conflicts.
        if self.cfg.handwriting_detector is None:
            raise ValueError("Handwriting detector is not configured")
        with tempfile.TemporaryDirectory(dir=self.cfg.storage) as directory:
            source, target = Path(directory) / "input.png", Path(directory) / "boxes.json"
            cv2.imencode(".png", image)[1].tofile(source)
            process = subprocess.run([str(self.cfg.torch_python), "-m", "ocr_service.yolo_runner",
                            "--image", str(source), "--output", str(target),
                            "--weights", str(self.cfg.handwriting_detector)],
                           cwd=Path(__file__).resolve().parent.parent,
                           check=False, timeout=180, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode:
                raise RuntimeError("YOLO subprocess failed: " + process.stderr.decode("utf-8", errors="replace")[-4000:])
            boxes = json.loads(target.read_text(encoding="utf-8"))
        return [np.array([[x1,y1], [x2,y1], [x2,y2], [x1,y2]], dtype=np.float32) for x1,y1,x2,y2 in boxes]

    def recognize(self, image, options):
        from tools.infer.utility import get_rotate_crop_image
        array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        boxes = self.general_boxes(array) if options["mode"] == "general" else self.handwriting_boxes(array)
        # Reading order is a heuristic: horizontal lines, top to bottom, left to right.
        boxes = sorted(boxes, key=lambda b: (b[0][1], b[0][0]))
        # PaddleOCR's horizontal reading-order heuristic, without importing its CLI.
        for i in range(len(boxes) - 1):
            for j in range(i, -1, -1):
                if abs(boxes[j+1][0][1] - boxes[j][0][1]) < 10 and boxes[j+1][0][0] < boxes[j][0][0]:
                    boxes[j], boxes[j+1] = boxes[j+1], boxes[j]
                else:
                    break
        width, height = image.size
        blocks = []
        for box in boxes:
            box = np.asarray(box, dtype=np.float32)
            box[:, 0] = np.clip(box[:, 0], 0, width-1)
            box[:, 1] = np.clip(box[:, 1], 0, height-1)
            if np.ptp(box[:, 0]) < 2 or np.ptp(box[:, 1]) < 2:
                continue
            crop = get_rotate_crop_image(array, box.copy())
            text, confidence = self.recognize_crop(crop, options["recognition_model"])
            if not np.isfinite(confidence):
                confidence = 0.0
            blocks.append(dict(id=len(blocks)+1, text=text, confidence=max(0., min(1., confidence)),
                bbox=[float(box[:,0].min()/width), float(box[:,1].min()/height),
                      float(box[:,0].max()/width), float(box[:,1].max()/height)],
                needs_review=confidence < options["min_confidence"]))
        return dict(width=width, height=height, blocks=blocks, text="\n".join(b["text"] for b in blocks),
                    tables=ruled_tables(image, blocks) if options["tables"] else [],
                    corrected=False, mode=options["mode"], recognition_model=options["recognition_model"],
                    warnings=["Low-confidence text is preserved for correction; all OCR output may contain errors"] +
                    (["Only regular ruled grids supported; no grid found does not mean there is no table"] if options["tables"] else []))

