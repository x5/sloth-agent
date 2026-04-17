"""Tests for CircuitBreaker state machine."""

import time

import pytest

from sloth_agent.errors.circuit_breaker import CircuitBreaker


class TestClosedState:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == "closed"

    def test_can_execute_when_closed(self):
        cb = CircuitBreaker()
        assert cb.can_execute() is True

    def test_below_threshold_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"


class TestOpenState:
    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"

    def test_cannot_execute_when_open(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.can_execute() is False

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure()
        assert cb.state == "open"
        time.sleep(1.1)
        assert cb.can_execute() is True
        assert cb.state == "half_open"


class TestHalfOpenState:
    def test_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        # Force to half_open
        cb.last_failure_time = time.time() - 1
        cb.can_execute()
        assert cb.state == "half_open"
        cb.record_success()
        assert cb.state == "closed"

    def test_failure_reopens_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        cb.last_failure_time = time.time() - 1
        cb.can_execute()
        assert cb.state == "half_open"
        cb.record_failure()
        assert cb.state == "open"

    def test_half_open_attempts_limited(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0, half_open_max=1)
        cb.record_failure()
        cb.last_failure_time = time.time() - 1
        assert cb.can_execute() is True
        cb.record_half_open_attempt()
        # Second attempt should be blocked
        assert cb.can_execute() is False


class TestReset:
    def test_reset_clears_all_state(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        cb.reset()
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.last_failure_time == 0
        assert cb.half_open_attempts == 0
