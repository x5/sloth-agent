"""CircuitBreaker — three-state machine: closed → open → half_open → closed.

Prevents repeated calls to continuously failing providers.
"""

from __future__ import annotations

import time


class CircuitBreaker:
    """Circuit breaker for a single provider.

    State transitions:
        closed ──(failures >= threshold)──> open
        open ──(recovery_timeout elapsed)──> half_open
        half_open ──(success)──> closed
        half_open ──(failure)──> open
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,
        half_open_max: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

        self.failure_count = 0
        self.state: str = "closed"
        self.last_failure_time: float = 0
        self.half_open_attempts = 0

    def can_execute(self) -> bool:
        """Check whether a request may be sent."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                self.half_open_attempts = 0
                return True
            return False

        if self.state == "half_open":
            return self.half_open_attempts < self.half_open_max

        return False

    def record_success(self) -> None:
        """Record a successful call."""
        self.failure_count = 0
        self.state = "closed"
        self.half_open_attempts = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == "half_open":
            # Failure in half_open → back to open
            self.state = "open"
        elif self.failure_count >= self.failure_threshold:
            self.state = "open"

    def record_half_open_attempt(self) -> None:
        """Track a probe attempt in half_open state."""
        self.half_open_attempts += 1

    def reset(self) -> None:
        """Manually reset to closed state."""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = 0
        self.half_open_attempts = 0
