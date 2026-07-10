"""Unit tests for manager helper functions and edge branches."""

from __future__ import annotations

from datetime import time

import pytest

from custom_components.hacomposablealarmclock.manager import (
    AlarmClock,
    AlarmClockManager,
    AlarmNotFoundError,
    AlarmValidationError,
    _alarm_from_storage,
    _next_due_datetime_utc,
    _parse_alarm_time,
    _split_service_call,
)


def test_parse_alarm_time_variants_and_errors() -> None:
    """Test alarm time parser accepts HH:MM[:SS] and rejects invalid shapes."""
    assert _parse_alarm_time("07:30") == time(7, 30)
    assert _parse_alarm_time("07:30:10") == time(7, 30, 10)

    with pytest.raises(ValueError):
        _parse_alarm_time("07")


def test_split_service_call_valid_and_invalid() -> None:
    """Test target service parser validates domain.service format."""
    assert _split_service_call("notify.mobile_app") == ("notify", "mobile_app")

    with pytest.raises(AlarmValidationError):
        _split_service_call("not_a_service")

    with pytest.raises(AlarmValidationError):
        _split_service_call(".")


def test_alarm_from_storage_validation() -> None:
    """Test loading alarm definitions from persisted mappings."""
    loaded = _alarm_from_storage(
        {
            "alarm_id": "kids_room",
            "name": "Kids Room",
            "alarm_time": "07:00:00",
            "enabled": True,
            "target_entities": ["light.kids_room"],
            "target_services": ["notify.mobile_app"],
            "last_triggered_iso": "2026-01-01T07:00:00+00:00",
        }
    )
    assert loaded.alarm_id == "kids_room"

    with pytest.raises(AlarmValidationError):
        _alarm_from_storage(
            {
                "alarm_id": "kids_room",
                "name": "Kids Room",
                "alarm_time": "07:00:00",
                "last_triggered_iso": "not-a-date",
            }
        )


async def test_manager_missing_alarm_errors_and_disabled_next_due(hass) -> None:
    """Test manager edge branches for missing alarms and disabled schedule."""
    manager = AlarmClockManager(hass, "entry_1")

    with pytest.raises(AlarmNotFoundError):
        await manager.async_set_alarm_time("missing", "07:00:00")

    with pytest.raises(AlarmNotFoundError):
        await manager.async_trigger_alarm_now("missing")

    await manager.async_upsert_alarm(
        AlarmClock(
            alarm_id="kids_room",
            name="Kids Room",
            alarm_time="07:00:00",
            enabled=False,
            target_entities=[],
            target_services=[],
        )
    )

    assert manager.async_next_due("kids_room") is None


def test_next_due_datetime_returns_timezone_aware_utc() -> None:
    """Test next-due helper always returns a timezone-aware UTC datetime."""
    due = _next_due_datetime_utc("07:00:00")
    assert due.tzinfo is not None
