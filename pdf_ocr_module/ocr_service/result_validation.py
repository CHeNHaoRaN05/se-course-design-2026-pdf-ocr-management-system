"""Bound persisted result payloads before correction or in-memory exports."""
import json
import math

MAX_EXPORT_BYTES = 8 * 1024 * 1024


def validate_result(data, require_geometry=False):
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        raise ValueError("Invalid stored OCR result")
    if not isinstance(data.get("blocks", []), list) or not isinstance(data.get("tables", []), list):
        raise ValueError("Invalid result blocks/tables")
    if require_geometry or data.get("tables"):
        if any(type(data.get(k)) is not int or data[k] <= 0 for k in ("width", "height")):
            raise ValueError("Stored result lacks valid page dimensions")
    for block in data.get("blocks", []):
        if not isinstance(block, dict) or not isinstance(block.get("text"), str) or type(block.get("id")) is not int:
            raise ValueError("Invalid stored block")
        bbox = block.get("bbox")
        if bbox is not None and (not isinstance(bbox, list) or len(bbox) != 4 or
            any(type(x) not in (int, float) or not math.isfinite(x) for x in bbox)):
            raise ValueError("Invalid stored block coordinates")
    for table in data.get("tables", []):
        if not isinstance(table, dict) or not isinstance(table.get("cells"), list):
            raise ValueError("Invalid stored table")
        if sum(len(row) if isinstance(row, list) else 100001 for row in table["cells"]) > 5000:
            raise ValueError("Table exceeds 5000 cells")
        if any(not isinstance(cell, str) for row in table["cells"] for cell in row):
            raise ValueError("Table cells must be text")
        if require_geometry:
            for name in ("x_lines", "y_lines"):
                lines = table.get(name)
                if not isinstance(lines, list) or len(lines) < 2 or any(
                    type(x) not in (int, float) or not math.isfinite(x) for x in lines):
                    raise ValueError("Stored table lacks valid grid coordinates")
                if any(a >= b for a, b in zip(lines, lines[1:])):
                    raise ValueError("Table grid must be increasing")
    return data


def check_export_size(pages):
    if len(pages) > 100:
        raise ValueError("Export at most 100 pages at a time")
    for page in pages:
        validate_result(page.get("result"))
    size = 0
    for part in json.JSONEncoder(ensure_ascii=False).iterencode(pages):
        size += len(part.encode("utf-8"))
        if size > MAX_EXPORT_BYTES:
            raise ValueError("Export exceeds 8 MiB; select fewer pages")
