"""Evaluate real OCR predictions against independently transcribed page text."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import time
import unicodedata


def normalize(text, keep_whitespace=False):
    value = unicodedata.normalize("NFKC", text)
    return value if keep_whitespace else "".join(value.split())


def edit_distance(reference, prediction):
    """Levenshtein distance with O(min(n,m)) auxiliary memory."""
    if len(reference) > 10000 or len(prediction) > 10000 or len(reference)*len(prediction) > 25_000_000:
        raise ValueError("Page text exceeds CER computation limit (10000 characters / 25M pairs)")
    if reference == prediction:
        return 0
    if len(reference) < len(prediction):
        reference, prediction = prediction, reference
    previous = list(range(len(prediction) + 1))
    for i, left in enumerate(reference, 1):
        current = [i]
        for j, right in enumerate(prediction, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def read_rows(path):
    if Path(path).stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Manifest exceeds 32 MiB")
    rows = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError(f"Line {number}: expected a nonempty string id")
        if row["id"] in rows:
            raise ValueError(f"Duplicate id: {row['id']}")
        if not isinstance(row.get("text"), str):
            raise ValueError(f"Line {number}: text must be a string")
        if len(row["text"]) > 10000:
            raise ValueError("Page text exceeds 10000 characters")
        if not isinstance(row.get("category", "uncategorized"), str):
            raise ValueError(f"Line {number}: category must be a string")
        rows[row["id"]] = row
    return rows


def evaluate(references, predictions, *, min_pages=200, keep_whitespace=False):
    if type(min_pages) is not int or min_pages < 1:
        raise ValueError("min_pages must be a positive integer")
    if len(references) < min_pages:
        raise ValueError(f"Need at least {max(1, min_pages)} labeled pages, got {len(references)}")
    if references.keys() != predictions.keys():
        raise ValueError("Prediction IDs must exactly match reference IDs (no missing or extra pages)")
    pages, groups = [], defaultdict(lambda: {"pages": 0, "reference_characters": 0, "edits": 0})
    for ident, row in references.items():
        reference = normalize(row["text"], keep_whitespace)
        predicted = normalize(predictions[ident]["text"], keep_whitespace)
        if not reference.strip():
            raise ValueError(f"Reference page {ident} must contain text")
        errors = edit_distance(reference, predicted)
        category = row.get("category", "uncategorized")
        result = {"id": ident, "category": category, "reference_characters": len(reference), "edits": errors}
        seconds = predictions[ident].get("seconds")
        if seconds is not None:
            try:
                valid_seconds = type(seconds) in (float, int) and math.isfinite(seconds) and seconds >= 0
            except OverflowError:
                valid_seconds = False
            if not valid_seconds:
                raise ValueError(f"Invalid seconds for {ident}")
            result["seconds"] = seconds
        pages.append(result)
        group = groups[category]
        group["pages"] += 1
        group["reference_characters"] += len(reference)
        group["edits"] += errors
    def metrics(values):
        total = sum(item["reference_characters"] for item in values)
        edits = sum(item["edits"] for item in values)
        return {"reference_characters": total, "edits": edits, "cer": edits / total if total else None,
                "character_accuracy": 1 - edits / total if total else None,
                "accuracy_definition": "1 - CER (unclamped); normalized Unicode code points"}
    if not sum(page["reference_characters"] for page in pages):
        raise ValueError("Reference corpus must contain text")
    timings = sorted(page["seconds"] for page in pages if "seconds" in page)
    return {"pages": len(pages), "min_pages": min_pages, "acceptance_min_pages": 200,
            "sample_threshold_met": len(pages) >= min_pages,
            "acceptance_page_threshold_met": len(pages) >= 200 and min_pages >= 200,
            "independent_labels_verified": False,
            "accuracy_acceptance_passed": None,
            "denominator": "NFKC-normalized Unicode code points after optional whitespace removal", "normalization": "NFKC" + ("" if keep_whitespace else "; remove whitespace"),
            "overall": metrics(pages),
            "categories": {name: {**group, **metrics([group])} for name, group in sorted(groups.items())},
            "timing": {"measured_pages": len(timings), "p95_seconds": timings[math.ceil(.95 * len(timings)) - 1]
                       if timings else None, "complete": len(timings) == len(pages),
                       "coverage": len(timings)/len(pages), "method": "nearest-rank over measured pages"},
            "page_results": pages}


def recognize(references, manifest_path):
    from .backend import PaddleBackend
    from .config import Settings
    from .media import inspect_media, render_page
    cfg = Settings()
    engine = PaddleBackend(cfg)
    # Explicit warm-up loads both models outside every page's stopwatch.
    import numpy as np
    engine.general_boxes(np.full((64, 64, 3), 255, dtype=np.uint8))
    engine.recognizer("official")
    rows = {}
    for ident, row in references.items():
        path = (manifest_path.parent / row["file"]).resolve()
        media_type, count = inspect_media(path, cfg)
        page_no = row.get("page_no", 1)
        if not isinstance(page_no, int) or isinstance(page_no, bool) or not 1 <= page_no <= count:
            raise ValueError(f"Invalid page_no for {ident}")
        started = time.perf_counter()
        with render_page(path, media_type, page_no, 144, cfg.max_pixels) as image:
            result = engine.recognize(image, {"mode": "general", "recognition_model": "official",
                                             "dpi": 144, "tables": False, "min_confidence": .5})
        rows[ident] = {"id": ident, "text": result["text"], "seconds": time.perf_counter() - started}
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("references", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--predictions", type=Path)
    mode.add_argument("--run-ocr", action="store_true")
    parser.add_argument("--min-pages", type=int, default=200)
    parser.add_argument("--development-sample", action="store_true", help="Allow fewer than 200 pages; never an acceptance result")
    parser.add_argument("--keep-whitespace", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.min_pages < 1:
            raise ValueError("min_pages must be a positive integer")
        if args.min_pages < 200 and not args.development_sample:
            raise ValueError("Acceptance requires at least 200 pages; use --development-sample for diagnostics")
        references = read_rows(args.references)
        if len(references) < max(1, args.min_pages):
            raise ValueError(f"Need at least {max(1, args.min_pages)} labeled pages, got {len(references)}")
        predictions = read_rows(args.predictions) if args.predictions else recognize(references, args.references)
        report = evaluate(references, predictions, min_pages=args.min_pages, keep_whitespace=args.keep_whitespace)
        report["reference_sha256"] = hashlib.sha256(args.references.read_bytes()).hexdigest()
        report["source"] = "supplied_predictions" if args.predictions else "PaddleBackend"
        if args.predictions:
            report["prediction_sha256"] = hashlib.sha256(args.predictions.read_bytes()).hexdigest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except (ValueError, OSError, KeyError, OverflowError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
