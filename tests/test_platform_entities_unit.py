"""Unit tests for platform entity helpers and per-alarm entities."""

from __future__ import annotations

from datetime import time
from typing import Any, cast

from custom_components.hacomposablealarmclock.button import AlarmTriggerNowButton
from custom_components.hacomposablealarmclock.entity import ComposableAlarmEntity
from custom_components.hacomposablealarmclock.manager import AlarmClock
from custom_components.hacomposablealarmclock.switch import AlarmEnabledSwitch
from custom_components.hacomposablealarmclock.time import AlarmTimeEntity, _parse_time


class FakeManager:
    """Simple manager stub for entity unit tests."""

    def __init__(self) -> None:
        self.alarms: dict[str, AlarmClock] = {}
        self.enabled_calls: list[tuple[str, bool]] = []
        self.time_calls: list[tuple[str, str]] = []
        self.trigger_calls: list[str] = []

    def async_get_alarm(self, alarm_id: str) -> AlarmClock | None:
        return self.alarms.get(alarm_id)

    async def async_set_enabled(self, alarm_id: str, enabled: bool) -> None:
        self.enabled_calls.append((alarm_id, enabled))

    async def async_set_alarm_time(self, alarm_id: str, alarm_time: str) -> None:
        self.time_calls.append((alarm_id, alarm_time))

    async def async_trigger_alarm_now(self, alarm_id: str) -> None:
        self.trigger_calls.append(alarm_id)

    def async_next_due(self, _alarm_id: str):
        return None


def _alarm(enabled: bool = True) -> AlarmClock:
    return AlarmClock(
        alarm_id="kids_room",
        name="Kids Room",
        alarm_time="07:30:00",
        enabled=enabled,
        target_entities=[],
        target_services=[],
    )


def test_base_entity_availability_name_and_device_info() -> None:
    """Test base entity helper properties."""
    manager = FakeManager()
    manager.alarms["kids_room"] = _alarm()

    entity = ComposableAlarmEntity(cast(Any, manager), "kids_room", "entry_1")

    assert entity.available is True
    assert entity.alarm_name == "Kids Room"
    assert entity.device_info["identifiers"] == {
        ("hacomposablealarmclock", "kids_room")
    }

    empty_manager = FakeManager()
    missing_entity = ComposableAlarmEntity(
        cast(Any, empty_manager),
        "kids_room",
        "entry_1",
    )
    assert missing_entity.available is False
    assert missing_entity.alarm_name == "kids_room"


async def test_button_press_triggers_alarm() -> None:
    """Test trigger-now button forwards to manager."""
    manager = FakeManager()
    manager.alarms["kids_room"] = _alarm()

    button = AlarmTriggerNowButton(cast(Any, manager), "kids_room", "entry_1")
    await button.async_press()

    assert manager.trigger_calls == ["kids_room"]


async def test_switch_reflects_and_updates_enabled_state() -> None:
    """Test enabled switch state and calls."""
    manager = FakeManager()
    manager.alarms["kids_room"] = _alarm(enabled=True)

    switch = AlarmEnabledSwitch(cast(Any, manager), "kids_room", "entry_1")
    assert switch.is_on is True

    manager_disabled = FakeManager()
    manager_disabled.alarms["kids_room"] = _alarm(enabled=False)
    switch_disabled = AlarmEnabledSwitch(
        cast(Any, manager_disabled),
        "kids_room",
        "entry_1",
    )
    assert switch_disabled.is_on is False

    await switch.async_turn_on()
    await switch.async_turn_off()

    assert manager.enabled_calls == [("kids_room", True), ("kids_room", False)]


async def test_time_entity_native_value_and_setter() -> None:
    """Test time entity parses and writes alarm time."""
    manager = FakeManager()
    manager.alarms["kids_room"] = _alarm()

    alarm_time = AlarmTimeEntity(cast(Any, manager), "kids_room", "entry_1")

    assert alarm_time.native_value == time(7, 30, 0)

    await alarm_time.async_set_value(time(8, 5, 6))
    assert manager.time_calls == [("kids_room", "08:05:06")]

    manager.alarms.clear()
    assert alarm_time.native_value is None


def test_parse_time_helper_variants() -> None:
    """Test HH:MM and HH:MM:SS parsing helper."""
    assert _parse_time("07:45") == time(7, 45)
    assert _parse_time("07:45:30") == time(7, 45, 30)
