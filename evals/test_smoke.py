"""Tests for eval smoke test."""

from evals.smoke_test import run_smoke_test


def test_smoke_test_passes():
    """Smoke test should pass with all mock components available."""
    result = run_smoke_test()
    assert result.passed is True
    assert len(result.steps) >= 5
    assert result.error is None
