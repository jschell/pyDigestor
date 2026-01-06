"""Rate limiting utilities for API calls."""

import time
from threading import Lock
from typing import Optional


class RateLimiter:
    """
    Thread-safe rate limiter for API calls.

    Enforces a maximum number of calls per minute to respect API rate limits.
    """

    def __init__(self, calls_per_minute: int = 30):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum number of API calls allowed per minute
        """
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute  # Seconds between calls
        self.last_call_time: Optional[float] = None
        self.lock = Lock()

    def wait_if_needed(self) -> float:
        """
        Wait if necessary to respect rate limit.

        Returns:
            Time waited in seconds (0 if no wait was needed)
        """
        with self.lock:
            current_time = time.time()

            if self.last_call_time is None:
                # First call - no wait needed
                self.last_call_time = current_time
                return 0.0

            # Calculate time since last call
            time_since_last_call = current_time - self.last_call_time

            # If we're within the rate limit, wait
            if time_since_last_call < self.min_interval:
                wait_time = self.min_interval - time_since_last_call
                time.sleep(wait_time)
                self.last_call_time = time.time()
                return wait_time

            # No wait needed
            self.last_call_time = current_time
            return 0.0

    def reset(self):
        """Reset the rate limiter state."""
        with self.lock:
            self.last_call_time = None
