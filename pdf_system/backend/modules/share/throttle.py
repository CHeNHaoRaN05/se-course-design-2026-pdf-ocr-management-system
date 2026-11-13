"""Single-host request throttling. Multi-worker deployments require a shared rate limiter."""
from collections import OrderedDict
import threading
import time

_lock = threading.Lock()
_windows = OrderedDict()


def allow(client: str, limit: int = 30, seconds: int = 60) -> bool:
    current = time.monotonic()
    with _lock:
        while _windows and next(iter(_windows.values()))[0] <= current - seconds:
            _windows.popitem(last=False)
        start, count = _windows.get(client, (current, 0))
        if count >= limit:
            return False
        _windows[client] = (start, count + 1)
        if len(_windows) > 10000:
            _windows.popitem(last=False)
        return True
