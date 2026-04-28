from circuit_breaker import CircuitBreaker


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_acquire_allowed_under_limit():
    cb = CircuitBreaker(max_per_minute=5, cooldown_seconds=60, clock=FakeClock())
    for _ in range(5):
        assert cb.acquire() is True


def test_acquire_blocked_at_limit():
    clock = FakeClock()
    cb = CircuitBreaker(max_per_minute=3, cooldown_seconds=60, clock=clock)
    for _ in range(3):
        cb.acquire()
    assert cb.acquire() is False


def test_on_open_called_when_limit_hit():
    calls = []
    clock = FakeClock()
    cb = CircuitBreaker(
        max_per_minute=2,
        cooldown_seconds=60,
        clock=clock,
        on_open=lambda: calls.append("open"),
    )
    cb.acquire()
    cb.acquire()
    cb.acquire()
    assert calls == ["open"]


def test_on_open_called_only_once_per_open_cycle():
    calls = []
    clock = FakeClock()
    cb = CircuitBreaker(
        max_per_minute=1,
        cooldown_seconds=60,
        clock=clock,
        on_open=lambda: calls.append("open"),
    )
    cb.acquire()
    for _ in range(5):
        cb.acquire()
    assert calls == ["open"]


def test_cooldown_blocks_acquires():
    clock = FakeClock()
    cb = CircuitBreaker(max_per_minute=2, cooldown_seconds=60, clock=clock)
    cb.acquire()
    cb.acquire()
    cb.acquire()  # opens

    clock.advance(30)
    assert cb.acquire() is False
    clock.advance(29)
    assert cb.acquire() is False


def test_cooldown_expires_and_circuit_closes():
    closed = []
    clock = FakeClock()
    cb = CircuitBreaker(
        max_per_minute=2,
        cooldown_seconds=60,
        clock=clock,
        on_close=lambda: closed.append("close"),
    )
    cb.acquire()
    cb.acquire()
    cb.acquire()  # opens
    clock.advance(60)
    assert cb.acquire() is True
    assert closed == ["close"]


def test_sliding_window_drops_old_timestamps():
    clock = FakeClock()
    cb = CircuitBreaker(max_per_minute=3, cooldown_seconds=60, clock=clock)
    cb.acquire()
    clock.advance(30)
    cb.acquire()
    cb.acquire()
    clock.advance(31)
    # First acquire is now > 60s old, should not count
    assert cb.acquire() is True


def test_failing_callback_does_not_break_breaker():
    def boom():
        raise RuntimeError("kaboom")

    clock = FakeClock()
    cb = CircuitBreaker(max_per_minute=1, cooldown_seconds=60, clock=clock, on_open=boom)
    cb.acquire()
    # Should not raise, just log
    assert cb.acquire() is False
