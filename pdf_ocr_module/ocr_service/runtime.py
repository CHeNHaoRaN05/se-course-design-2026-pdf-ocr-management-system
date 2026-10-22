"""Configure the inference process and keep all caches in service storage."""
import os
import site
import sys
from threading import Lock

_handles = []
_lock = Lock()
_paddle = None


def load_paddle(settings):
    global _paddle
    with _lock:
        if _paddle is not None:
            return _paddle
        cache = settings.storage / "runtime"
        cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("NO_ALBUMENTATIONS_UPDATE", "1")
        os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        os.environ.setdefault("MPLCONFIGDIR", str(cache / "matplotlib"))
        os.environ.setdefault("PADDLE_HOME", str(cache / "paddle"))
        os.environ.setdefault("XDG_CACHE_HOME", str(cache))
        if os.name == "nt":
            from pathlib import Path
            for base in site.getsitepackages():
                for directory in Path(base).glob("nvidia/*/bin"):
                    _handles.append(os.add_dll_directory(str(directory)))
        sys.path.insert(0, str(settings.vendor))
        # Paddle 3.0 initializes a legacy home cache during import.
        expanduser = os.path.expanduser
        os.path.expanduser = lambda path: str(cache) if path == "~" else expanduser(path)
        try:
            import paddle
            _paddle = paddle
        finally:
            os.path.expanduser = expanduser
        return _paddle
