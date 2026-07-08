"""Switch platform for virtual alarm enabled state."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntryState
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
    """Set up per-alarm switch entities for this entry."""
    manager = entry.runtime_data.manager
    known_alarms: set[str] = set()

    @callback
    def _async_add_alarm_entity_job(alarm_id: str) -> None:
        if hass.is_stopping or entry.state is not ConfigEntryState.LOADED:
            return
        if manager.async_get_alarm(alarm_id) is None:
            return
        if alarm_id in known_alarms:
            return
        known_alarms.add(alarm_id)
        async_add_entities([AlarmEnabledSwitch(manager, alarm_id, entry.entry_id)])

    def _async_add_alarm_entity(alarm_id: str) -> None:
        if hass.is_stopping or entry.state is not ConfigEntryState.LOADED:
            return
        hass.add_job(_async_add_alarm_entity_job, alarm_id)

    for alarm in manager.async_list_alarms():
        _async_add_alarm_entity_job(alarm.alarm_id)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ALARM_CHANGED, _async_add_alarm_entity)
    )


class AlarmEnabledSwitch(ComposableAlarmEntity, SwitchEntity):
    """Represent virtual alarm enabled state."""

    _attr_translation_key = "enabled"

    def __init__(self, manager, alarm_id: str, entry_id: str) -> None:
        super().__init__(manager, alarm_id, entry_id)
        self._attr_unique_id = f"{entry_id}_{alarm_id}_enabled"

    @property
    def is_on(self) -> bool:
        """Return whether the alarm is enabled."""
        alarm = self._manager.async_get_alarm(self._alarm_id)
        return bool(alarm and alarm.enabled)

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the virtual alarm."""
        del kwargs
        await self._manager.async_set_enabled(self._alarm_id, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the virtual alarm."""
        del kwargs
        await self._manager.async_set_enabled(self._alarm_id, False)
