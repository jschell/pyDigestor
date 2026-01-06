"""Tests for rate limiter."""

import time
import pytest

from pydigestor.utils.rate_limit import RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(calls_per_minute=60)
        assert limiter.calls_per_minute == 60
        assert limiter.min_interval == 1.0  # 60 seconds / 60 calls
        assert limiter.last_call_time is None

    def test_init_custom_rate(self):
        """Test RateLimiter with custom rate."""
        limiter = RateLimiter(calls_per_minute=30)
        assert limiter.calls_per_minute == 30
        assert limiter.min_interval == 2.0  # 60 seconds / 30 calls

    def test_first_call_no_wait(self):
        """Test that first call doesn't wait."""
        limiter = RateLimiter(calls_per_minute=60)
        wait_time = limiter.wait_if_needed()
        assert wait_time == 0.0

    def test_rate_limit_enforces_delay(self):
        """Test that rate limiter enforces delay between calls."""
        limiter = RateLimiter(calls_per_minute=60)  # 1 call per second

        start = time.time()
        limiter.wait_if_needed()  # First call - no wait
        limiter.wait_if_needed()  # Second call - should wait ~1 second
        elapsed = time.time() - start

        # Should have waited approximately 1 second
        assert elapsed >= 0.9  # Allow small timing variance

    def test_multiple_calls_respect_rate_limit(self):
        """Test multiple calls respect rate limit."""
        limiter = RateLimiter(calls_per_minute=120)  # 2 calls per second

        start = time.time()
        for _ in range(3):
            limiter.wait_if_needed()
        elapsed = time.time() - start

        # 3 calls at 2/second should take ~1 second
        assert elapsed >= 0.9

    def test_slow_calls_no_wait(self):
        """Test that slow calls don't accumulate wait time."""
        limiter = RateLimiter(calls_per_minute=60)

        limiter.wait_if_needed()  # First call
        time.sleep(1.1)  # Wait longer than rate limit
        wait_time = limiter.wait_if_needed()  # Second call - shouldn't wait

        assert wait_time == 0.0

    def test_reset(self):
        """Test resetting the rate limiter."""
        limiter = RateLimiter(calls_per_minute=60)

        limiter.wait_if_needed()
        assert limiter.last_call_time is not None

        limiter.reset()
        assert limiter.last_call_time is None

    def test_thread_safety(self):
        """Test rate limiter is thread-safe."""
        import threading

        limiter = RateLimiter(calls_per_minute=60)
        results = []

        def make_call():
            wait_time = limiter.wait_if_needed()
            results.append(wait_time)

        # Create multiple threads
        threads = [threading.Thread(target=make_call) for _ in range(5)]

        start = time.time()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        elapsed = time.time() - start

        # All 5 threads should have completed
        assert len(results) == 5

        # Should have taken at least 4 seconds (5 calls at 1/second)
        assert elapsed >= 3.9

    def test_reddit_rate_limit(self):
        """Test Reddit's 30 requests/minute rate limit."""
        limiter = RateLimiter(calls_per_minute=30)

        # Should allow 2 seconds between calls
        assert limiter.min_interval == 2.0

        start = time.time()
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        assert elapsed >= 1.9
