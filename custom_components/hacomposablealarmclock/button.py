"""Button platform for Composable Alarm Clock."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up per-alarm button entities for this entry."""
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
        async_add_entities([AlarmTriggerNowButton(manager, alarm_id, entry.entry_id)])

    def _async_add_alarm_entity(alarm_id: str) -> None:
        if hass.is_stopping or unloading:
            return
        hass.add_job(_async_add_alarm_entity_job, alarm_id)

    for alarm in manager.async_list_alarms():
        _async_add_alarm_entity_job(alarm.alarm_id)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ALARM_CHANGED, _async_add_alarm_entity)
    )


class AlarmTriggerNowButton(ComposableAlarmEntity, ButtonEntity):
    """Allow triggering one virtual alarm immediately from the device page."""

    _attr_translation_key = "trigger_now"

    def __init__(self, manager, alarm_id: str, entry_id: str) -> None:
        """Initialize button entity."""
        super().__init__(manager, alarm_id, entry_id)
        self._attr_unique_id = f"{entry_id}_{alarm_id}_trigger_now"

    async def async_press(self) -> None:
        """Trigger the alarm immediately."""
        await self._manager.async_trigger_alarm_now(self._alarm_id)
