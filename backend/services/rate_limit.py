"""Tiny in-memory limiter for login attempts (per process). For multi-server deployments, use Redis."""
import time
from collections import defaultdict, deque

_attempts: dict[str, deque] = defaultdict(deque)


def is_blocked(key: str, max_attempts: int = 5, window_seconds: int = 900) -> bool:
    now = time.monotonic()
    q = _attempts[key]
    while q and now - q[0] > window_seconds:
        q.popleft()
    return len(q) >= max_attempts


def record_failure(key: str) -> None:
    _attempts[key].append(time.monotonic())


def reset(key: str) -> None:
    _attempts.pop(key, None)
