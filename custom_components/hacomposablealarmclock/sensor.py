"""Sensor platform for Composable Alarm Clock."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ComposableAlarmConfigEntry
from .const import DOMAIN, SIGNAL_ALARM_CHANGED, SIGNAL_ALARM_REMOVED
from .entity import ComposableAlarmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComposableAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up per-alarm sensors for this entry."""
    manager = entry.runtime_data.manager
    known_alarms: set[str] = set()
    unloading = False

    @callback
    def _mark_unloading() -> None:
        nonlocal unloading
        unloading = True

    entry.async_on_unload(_mark_unloading)

    async_add_entities([WorkspaceOverviewSensor(manager, entry.entry_id)])

    def _create_entities_for_alarm(alarm_id: str) -> list[SensorEntity]:
        return [
            NextDueSensor(manager, alarm_id, entry.entry_id),
            LastTriggeredSensor(manager, alarm_id, entry.entry_id),
            AlarmConfigSensor(manager, alarm_id, entry.entry_id),
            AlarmStatusSensor(manager, alarm_id, entry.entry_id),
        ]

    @callback
    def _async_add_alarm_entities_job(alarm_id: str) -> None:
        if hass.is_stopping or unloading:
            return
        if manager.async_get_alarm(alarm_id) is None:
            return
        if alarm_id in known_alarms:
            return
        known_alarms.add(alarm_id)
        async_add_entities(_create_entities_for_alarm(alarm_id))

    def _async_add_alarm_entities(alarm_id: str) -> None:
        if hass.is_stopping or unloading:
            return
        hass.add_job(_async_add_alarm_entities_job, alarm_id)

    for alarm in manager.async_list_alarms():
        _async_add_alarm_entities_job(alarm.alarm_id)

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


class WorkspaceOverviewSensor(SensorEntity):
    """Expose top-level overview for all configured alarms."""

    _attr_translation_key = "workspace_overview"
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager, entry_id: str) -> None:
        """Initialize workspace overview sensor."""
        self._manager = manager
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_workspace_overview"

    @property
    def native_value(self) -> int:
        """Return number of configured alarms."""
        return len(self._manager.async_list_alarms())

    @property
    def native_unit_of_measurement(self) -> str:
        """Return unit for configured alarm count."""
        return "alarms"

    @property
    def device_info(self) -> DeviceInfo:
        """Return workspace device details so the integration always has a device."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_workspace")},
            manufacturer="Composable Alarm Clock",
            model="Alarm Workspace",
            name="Alarm Workspace",
            entry_type=None,
        )

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, Any]]]:
        """Return compact view of all configured alarms for tracking."""
        alarms = sorted(
            self._manager.async_list_alarms(),
            key=lambda alarm: alarm.alarm_id,
        )
        return {
            "alarms": [
                {
                    "alarm_id": alarm.alarm_id,
                    "name": alarm.name,
                    "alarm_time": alarm.alarm_time,
                    "enabled": alarm.enabled,
                    "target_entities_count": len(alarm.target_entities),
                    "target_services_count": len(alarm.target_services),
                    "last_triggered": alarm.last_triggered_iso,
                }
                for alarm in alarms
            ]
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to alarm changes so this summary updates immediately."""

        @callback
        def _handle_alarm_changed(_alarm_id: str) -> None:
            if self.platform is None or self.hass.is_stopping:
                return
            self.hass.add_job(self.async_write_ha_state)

        @callback
        def _handle_alarm_removed(_alarm_id: str) -> None:
            if self.platform is None or self.hass.is_stopping:
                return
            self.hass.add_job(self.async_write_ha_state)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALARM_CHANGED,
                _handle_alarm_changed,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALARM_REMOVED,
                _handle_alarm_removed,
            )
        )


class AlarmState(StrEnum):
    """High-level alarm state for status tracking."""

    DISABLED = "disabled"
    SCHEDULED = "scheduled"


class AlarmStatusSensor(ComposableAlarmEntity, SensorEntity):
    """Expose runtime status for one virtual alarm."""

    _attr_translation_key = "status"
    _attr_options = [AlarmState.DISABLED, AlarmState.SCHEDULED]

    def __init__(
        self,
        manager,
        alarm_id: str,
        entry_id: str,
    ) -> None:
        super().__init__(manager, alarm_id, entry_id)
        self._attr_unique_id = f"{entry_id}_{alarm_id}_status"

    @property
    def native_value(self) -> str | None:
        """Return current status for this alarm."""
        alarm = self._manager.async_get_alarm(self._alarm_id)
        if alarm is None:
            return None
        return AlarmState.SCHEDULED if alarm.enabled else AlarmState.DISABLED

    @property
    def extra_state_attributes(self) -> dict[str, str | bool | int | list[str] | None]:
        """Return tracking attributes to inspect alarm behavior."""
        alarm = self._manager.async_get_alarm(self._alarm_id)
        if alarm is None:
            return {}

        next_due = self._manager.async_next_due(self._alarm_id)
        last_triggered = (
            datetime.fromisoformat(alarm.last_triggered_iso)
            if alarm.last_triggered_iso is not None
            else None
        )

        return {
            "alarm_id": alarm.alarm_id,
            "alarm_name": alarm.name,
            "alarm_time": alarm.alarm_time,
            "enabled": alarm.enabled,
            "next_due": next_due.isoformat() if next_due else None,
            "last_triggered": last_triggered.isoformat() if last_triggered else None,
            "target_entities_count": len(alarm.target_entities),
            "target_services_count": len(alarm.target_services),
        }


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


class AlarmConfigSensor(ComposableAlarmEntity, SensorEntity):
    """Expose configuration details for one virtual alarm."""

    _attr_translation_key = "configuration"
    _attr_native_unit_of_measurement = "targets"

    def __init__(
        self,
        manager,
        alarm_id: str,
        entry_id: str,
    ) -> None:
        super().__init__(manager, alarm_id, entry_id)
        self._attr_unique_id = f"{entry_id}_{alarm_id}_configuration"

    @property
    def native_value(self) -> int | None:
        """Return total configured targets for this alarm."""
        alarm = self._manager.async_get_alarm(self._alarm_id)
        if alarm is None:
            return None
        return len(alarm.target_entities) + len(alarm.target_services)

    @property
    def extra_state_attributes(self) -> dict[str, str | bool | list[str] | None]:
        """Return full alarm configuration attributes."""
        alarm = self._manager.async_get_alarm(self._alarm_id)
        if alarm is None:
            return {}

        return {
            "alarm_id": alarm.alarm_id,
            "alarm_name": alarm.name,
            "alarm_time": alarm.alarm_time,
            "enabled": alarm.enabled,
            "target_entities": alarm.target_entities,
            "target_services": alarm.target_services,
            "last_triggered": alarm.last_triggered_iso,
        }
