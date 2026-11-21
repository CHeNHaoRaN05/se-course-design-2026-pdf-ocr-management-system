"""Verify official model files against the checked-in SHA256 manifest."""
import hashlib
import json
from pathlib import Path
from .config import PACKAGE_ROOT


def verify_file(path, expected):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024*1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError(f"Model checksum mismatch: {path}")
    return digest.hexdigest()


def verify_official(settings):
    manifest = json.loads((PACKAGE_ROOT / "models/manifest.json").read_text(encoding="utf-8"))
    return {name:verify_file(path, manifest[name]["sha256"]) for name, path in (
        ("detector", settings.detector_weights), ("recognizer", settings.recognizer_weights))}
