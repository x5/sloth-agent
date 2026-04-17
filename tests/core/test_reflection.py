"""Tests for Reflection and StuckDetector (plan Task 9)."""

from sloth_agent.core.reflection import Reflection, StuckDetector


def test_reflection_model():
    r = Reflection(
        error_category="syntax",
        root_cause="Missing colon on line 42",
        learnings=["Always check syntax before running"],
        action="retry_same",
        confidence=0.9,
    )
    assert r.error_category == "syntax"
    assert r.action == "retry_same"


def test_stuck_detector_not_stuck_initially():
    detector = StuckDetector(window=[])
    assert detector.is_stuck() is False


def test_stuck_detector_detects_same_category():
    r1 = Reflection(error_category="syntax", root_cause="missing colon", learnings=[], action="retry_same", confidence=0.9)
    r2 = Reflection(error_category="syntax", root_cause="missing comma", learnings=[], action="retry_same", confidence=0.8)
    r3 = Reflection(error_category="syntax", root_cause="missing semicolon", learnings=[], action="retry_same", confidence=0.7)
    detector = StuckDetector(window=[r1, r2, r3])
    assert detector.is_stuck() is True


def test_stuck_detector_action_escalation():
    detector = StuckDetector(window=[])
    assert detector.get_unstuck_action() in ("retry_different", "replan", "abort")


def test_stuck_detector_escalates_with_retries():
    detector = StuckDetector(window=[])
    # First stuck → retry_different
    detector.window.append(Reflection(error_category="logic", root_cause="off by one", learnings=[], action="retry_same", confidence=0.5))
    assert detector.get_unstuck_action() == "retry_different"

    # Second stuck → replan
    detector.window.append(Reflection(error_category="logic", root_cause="wrong loop", learnings=[], action="retry_same", confidence=0.4))
    assert detector.get_unstuck_action() == "replan"

    # Third stuck → abort
    detector.window.append(Reflection(error_category="logic", root_cause="bad design", learnings=[], action="retry_same", confidence=0.3))
    assert detector.get_unstuck_action() == "abort"


def test_stuck_detector_reset():
    r = Reflection(error_category="syntax", root_cause="x", learnings=[], action="retry_same", confidence=0.5)
    detector = StuckDetector(window=[r])
    detector.reset()
    assert detector.window == []
    assert detector.is_stuck() is False
