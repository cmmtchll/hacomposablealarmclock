"""Sensor platform for Composable Alarm Clock."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ComposableAlarmConfigEntry
from .const import SIGNAL_ALARM_CHANGED, SIGNAL_ALARM_REMOVED
from .entity import ComposableAlarmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComposableAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up per-alarm sensors for this entry."""
    manager = entry.runtime_data.manager
    known_alarms: set[str] = set()

    def _create_entities_for_alarm(alarm_id: str) -> list[SensorEntity]:
        return [
            NextDueSensor(manager, alarm_id, entry.entry_id),
            LastTriggeredSensor(manager, alarm_id, entry.entry_id),
        ]

    def _async_add_alarm_entities(alarm_id: str) -> None:
        if manager.async_get_alarm(alarm_id) is None:
            return
        if alarm_id in known_alarms:
            return
        known_alarms.add(alarm_id)
        async_add_entities(_create_entities_for_alarm(alarm_id))

    for alarm in manager.async_list_alarms():
        _async_add_alarm_entities(alarm.alarm_id)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            SIGNAL_ALARM_CHANGED,
            _async_add_alarm_entities,
        )
    )

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            SIGNAL_ALARM_REMOVED,
            lambda _alarm_id: None,
        )
    )


class NextDueSensor(ComposableAlarmEntity, SensorEntity):
    """Expose next due timestamp for one virtual alarm."""

    _attr_translation_key = "next_due"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        manager,
        alarm_id: str,
        entry_id: str,
    ) -> None:
        super().__init__(manager, alarm_id, entry_id)
        self._attr_unique_id = f"{entry_id}_{alarm_id}_next_due"

    @property
    def native_value(self) -> datetime | None:
        """Return next due timestamp for this alarm."""
        return self._manager.async_next_due(self._alarm_id)


class LastTriggeredSensor(ComposableAlarmEntity, SensorEntity):
    """Expose last triggered timestamp for one virtual alarm."""

    _attr_translation_key = "last_triggered"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        manager,
        alarm_id: str,
        entry_id: str,
    ) -> None:
        super().__init__(manager, alarm_id, entry_id)
        self._attr_unique_id = f"{entry_id}_{alarm_id}_last_triggered"

    @property
    def native_value(self) -> datetime | None:
        """Return last triggered timestamp for this alarm."""
        alarm = self._manager.async_get_alarm(self._alarm_id)
        if alarm is None or alarm.last_triggered_iso is None:
            return None
        parsed = datetime.fromisoformat(alarm.last_triggered_iso)
        return parsed
