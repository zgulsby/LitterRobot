from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.notifier import _is_above_threshold, _should_notify
from src.whisker_client import RobotStatus


def make_robot(drawer_level: int | None = None, is_drawer_full: bool = False) -> RobotStatus:
    return RobotStatus(
        serial="ABC123",
        name="Test Robot",
        is_drawer_full=is_drawer_full,
        drawer_level=drawer_level,
    )


class TestShouldNotify:
    def test_no_prior_state(self):
        assert _should_notify("ABC123", {}, dedup_hours=12) is True

    def test_within_dedup_window(self):
        recent = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        state = {"ABC123": {"last_notified": recent}}
        assert _should_notify("ABC123", state, dedup_hours=12) is False

    def test_outside_dedup_window(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
        state = {"ABC123": {"last_notified": old}}
        assert _should_notify("ABC123", state, dedup_hours=12) is True


class TestIsAboveThreshold:
    def test_lr4_above_threshold(self):
        assert _is_above_threshold(make_robot(drawer_level=90), threshold=80) is True

    def test_lr4_below_threshold(self):
        assert _is_above_threshold(make_robot(drawer_level=50), threshold=80) is False

    def test_lr4_at_threshold(self):
        assert _is_above_threshold(make_robot(drawer_level=80), threshold=80) is True

    def test_lr3_full(self):
        assert _is_above_threshold(make_robot(is_drawer_full=True), threshold=80) is True

    def test_lr3_not_full(self):
        assert _is_above_threshold(make_robot(is_drawer_full=False), threshold=80) is False
