"""Time platform for virtual alarm due time."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ComposableAlarmConfigEntry
from .const import SIGNAL_ALARM_CHANGED
from .entity import ComposableAlarmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComposableAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up per-alarm time entities for this entry."""
    manager = entry.runtime_data.manager
    known_alarms: set[str] = set()
    unloading = False

    @callback
    def _mark_unloading() -> None:
        nonlocal unloading
        unloading = True

    entry.async_on_unload(_mark_unloading)

    @callback
    def _async_add_alarm_entity_job(alarm_id: str) -> None:
        if hass.is_stopping or unloading:
            return
        if manager.async_get_alarm(alarm_id) is None:
            return
        if alarm_id in known_alarms:
            return
        known_alarms.add(alarm_id)
        async_add_entities([AlarmTimeEntity(manager, alarm_id, entry.entry_id)])

    def _async_add_alarm_entity(alarm_id: str) -> None:
        if hass.is_stopping or unloading:
            return
        hass.add_job(_async_add_alarm_entity_job, alarm_id)

    for alarm in manager.async_list_alarms():
        _async_add_alarm_entity_job(alarm.alarm_id)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ALARM_CHANGED, _async_add_alarm_entity)
    )


class AlarmTimeEntity(ComposableAlarmEntity, TimeEntity):
    """Represent virtual alarm due time."""

    _attr_translation_key = "alarm_time"

    def __init__(self, manager, alarm_id: str, entry_id: str) -> None:
        super().__init__(manager, alarm_id, entry_id)
        self._attr_unique_id = f"{entry_id}_{alarm_id}_alarm_time"

    @property
    def native_value(self) -> time | None:
        """Return alarm time as a time object."""
        alarm = self._manager.async_get_alarm(self._alarm_id)
        if alarm is None:
            return None
        return _parse_time(alarm.alarm_time)

    async def async_set_value(self, value: time) -> None:
        """Set alarm time via time entity."""
        await self._manager.async_set_alarm_time(
            self._alarm_id,
            value.strftime("%H:%M:%S"),
        )


def _parse_time(value: str) -> time:
    """Parse HH:MM or HH:MM:SS."""
    parts = value.split(":")
    if len(parts) == 2:
        return time(hour=int(parts[0]), minute=int(parts[1]))
    return time(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2]))
