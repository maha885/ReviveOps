"""Tests for the in-memory rate limiter and concurrency limiter."""

import threading
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services import limits
from app.services.limits import (
    ConcurrencyLimiter,
    RateLimited,
    RateLimiter,
    TooManyConcurrent,
    client_key,
)


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make(n=3, **kw):
    clock = FakeClock()
    return RateLimiter(n, clock=clock, **kw), clock


def test_allows_n_then_blocks():
    rl, _ = make(3)
    assert [rl.allow("a") for _ in range(4)] == [True, True, True, False]


def test_window_slides():
    rl, clock = make(2)
    assert rl.allow("a")
    clock.t += 30
    assert rl.allow("a")
    assert not rl.allow("a")
    clock.t += 31  # first hit (t=0) expired, second (t=30) not
    assert rl.allow("a")
    assert not rl.allow("a")


def test_keys_independent():
    rl, _ = make(1)
    assert rl.allow("a")
    assert not rl.allow("a")
    assert rl.allow("b")


def test_retry_after():
    rl, clock = make(1)
    rl.check("a")
    clock.t += 20
    with pytest.raises(RateLimited) as e:
        rl.check("a")
    assert e.value.retry_after == 40
    clock.t += 39.5
    with pytest.raises(RateLimited) as e:
        rl.check("a")
    assert e.value.retry_after == 1


def test_blocked_attempts_do_not_extend_window():
    rl, clock = make(1)
    rl.check("a")
    for _ in range(5):
        clock.t += 10
        rl.allow("a")
    clock.t += 11  # 61s since the only recorded hit
    assert rl.allow("a")


def test_key_table_bounded_and_stale_pruned():
    rl, clock = make(5, max_keys=10)
    for i in range(1000):
        rl.allow(f"ip{i}")
        assert rl.tracked_keys() <= 10
    clock.t += 61
    rl.allow("fresh")
    assert rl.tracked_keys() <= 10


def test_eviction_prefers_stale_keys():
    rl, clock = make(5, max_keys=3)
    rl.allow("old")
    clock.t += 61
    rl.allow("x")
    rl.allow("y")
    rl.allow("z")  # table full: "old" is stale and should go
    assert rl.tracked_keys() == 3
    assert "old" not in rl._hits


def test_limit_read_at_call_time():
    rl = RateLimiter(lambda: settings.scan_rate_per_minute, clock=FakeClock())
    old = settings.scan_rate_per_minute
    try:
        settings.scan_rate_per_minute = 1
        assert rl.allow("a")
        assert not rl.allow("a")
    finally:
        settings.scan_rate_per_minute = old


def test_zero_limit_not_disabled():
    rl = RateLimiter(0, clock=FakeClock())
    assert rl.allow("a")
    assert not rl.allow("a")


def test_reset():
    rl, _ = make(1)
    rl.allow("a")
    rl.reset()
    assert rl.allow("a")


def test_concurrency_rejects_at_cap_and_releases():
    cl = ConcurrencyLimiter(2)
    with cl.slot():
        with cl.slot():
            assert cl.active == 2
            with pytest.raises(TooManyConcurrent):
                with cl.slot():
                    pass
            assert cl.active == 2  # failed attempt did not leak or release
    assert cl.active == 0
    with cl.slot():
        pass


def test_concurrency_releases_on_exception():
    cl = ConcurrencyLimiter(1)
    with pytest.raises(ValueError):
        with cl.slot():
            raise ValueError("boom")
    assert cl.active == 0
    assert cl.try_acquire()


def test_concurrency_direct_context_manager():
    cl = ConcurrencyLimiter(1)
    with cl:
        with pytest.raises(TooManyConcurrent):
            with cl:
                pass
    assert cl.active == 0


def test_rate_limiter_thread_safety():
    rl = RateLimiter(50)
    results = []

    def work():
        for _ in range(20):
            results.append(rl.allow("same"))

    threads = [threading.Thread(target=work) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(results) == 200
    assert sum(results) == 50


def test_concurrency_thread_safety():
    cl = ConcurrencyLimiter(3)
    gate = threading.Barrier(10)
    acquired = []

    def work():
        gate.wait()
        acquired.append(cl.try_acquire())

    threads = [threading.Thread(target=work) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sum(acquired) == 3
    assert cl.active == 3


def test_client_key():
    assert client_key(SimpleNamespace(client=SimpleNamespace(host="1.2.3.4"))) == "1.2.3.4"
    assert client_key(SimpleNamespace(client=None)) == "unknown"


def test_default_instances_resettable():
    limits.scan_rate_limiter.reset()
    assert limits.extraction_limiter.active == 0
