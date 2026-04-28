"""Sliding-window rate limiter with cool-down.

Protects the bot from runaway behavior — if it tries to post more than
`max_per_minute` messages in any rolling 60-second window, the circuit opens
and rejects all acquires for `cooldown_seconds`. Optional callbacks fire on
open and close so the bot can notify an admin.
"""
import logging
import time
from collections import deque
from typing import Callable, Optional


class CircuitBreaker:
    def __init__(
        self,
        max_per_minute: int,
        cooldown_seconds: int,
        on_open: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._max = max_per_minute
        self._cooldown = cooldown_seconds
        self._on_open = on_open
        self._on_close = on_close
        self._clock = clock
        self._timestamps: deque[float] = deque()
        self._opened_at: Optional[float] = None

    def acquire(self) -> bool:
        """Return True if a send is allowed (and record it). False if blocked."""
        now = self._clock()

        if self._opened_at is not None:
            if now - self._opened_at >= self._cooldown:
                self._close()
            else:
                return False

        cutoff = now - 60
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

        if len(self._timestamps) >= self._max:
            self._open(now)
            return False

        self._timestamps.append(now)
        return True

    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if self._clock() - self._opened_at >= self._cooldown:
            self._close()
            return False
        return True

    def _open(self, now: float) -> None:
        self._opened_at = now
        logging.warning("Circuit breaker opened: too many messages in last 60s")
        self._safe_callback(self._on_open)

    def _close(self) -> None:
        self._opened_at = None
        self._timestamps.clear()
        logging.info("Circuit breaker closed: cool-down expired")
        self._safe_callback(self._on_close)

    @staticmethod
    def _safe_callback(cb: Optional[Callable[[], None]]) -> None:
        if cb is None:
            return
        try:
            cb()
        except Exception:
            logging.exception("Circuit breaker callback raised")
