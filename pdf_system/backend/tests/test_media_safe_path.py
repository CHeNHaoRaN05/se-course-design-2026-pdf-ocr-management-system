"""Regression: safe_path must be deterministic under Windows 8.3 short names."""
import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


main_media = _load("main_media", "pdf_system/backend/core/media.py")
ocr_media = _load("ocr_media", "pdf_ocr_module/ocr_service/media.py")

IMPLEMENTATIONS = [
    (main_media.safe_path, main_media.MediaError),
    (ocr_media.safe_path, ocr_media.MediaError),
]


@pytest.mark.parametrize("safe_path,error", IMPLEMENTATIONS)
def test_normal_keys_stay_under_storage(tmp_path, safe_path, error):
    for key in ("uploads/a.bin", "pages/j/t-1.png", "a.bin"):
        path = safe_path(tmp_path, key)
        assert path.is_absolute()
        assert path == Path(os.path.abspath(os.path.join(str(tmp_path), key)))


@pytest.mark.parametrize("safe_path,error", IMPLEMENTATIONS)
def test_traversal_and_absolute_keys_rejected(tmp_path, safe_path, error):
    for key in ("", "..", "../outside.bin", "uploads/../../escape.bin", "/etc/passwd"):
        with pytest.raises(error):
            safe_path(tmp_path, key)


@pytest.mark.parametrize("safe_path,error", IMPLEMENTATIONS)
def test_concurrent_calls_are_deterministic(tmp_path, safe_path, error):
    key = "uploads/concurrent.pdf"
    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(lambda _: safe_path(tmp_path, key), range(200)))
    assert len(set(paths)) == 1


def test_both_modules_agree(tmp_path):
    for key in ("uploads/a.bin", "pages/j/t-1.png", "../escape.bin"):
        outcomes = []
        for safe_path, error in IMPLEMENTATIONS:
            try:
                outcomes.append(("ok", str(safe_path(tmp_path, key))))
            except error as exc:
                outcomes.append(("err", str(exc)))
        assert outcomes[0] == outcomes[1]
