"""Shared entity helpers for Composable Alarm Clock."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_ALARM_CHANGED, SIGNAL_ALARM_REMOVED
from .manager import AlarmClockManager


class ComposableAlarmEntity(Entity):
    """Base entity for Composable Alarm Clock entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        manager: AlarmClockManager,
        alarm_id: str,
        entry_id: str,
    ) -> None:
        """Initialize base entity."""
        self._manager = manager
        self._alarm_id = alarm_id
        self._entry_id = entry_id

    @property
    def available(self) -> bool:
        """Return if the backing alarm exists."""
        return self._manager.async_get_alarm(self._alarm_id) is not None

    @property
    def alarm_name(self) -> str:
        """Return alarm display name."""
        alarm = self._manager.async_get_alarm(self._alarm_id)
        return alarm.name if alarm else self._alarm_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._alarm_id)},
            manufacturer="Composable Alarm Clock",
            model="Virtual Alarm Clock",
            translation_key="alarm_device",
            translation_placeholders={"name": self.alarm_name},
            via_device=(DOMAIN, f"{self._entry_id}_workspace"),
            entry_type=None,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to manager signals to keep entity state in sync."""

        @callback
        def _handle_changed(alarm_id: str) -> None:
            if alarm_id != self._alarm_id:
                return
            if self.platform is None or self.hass.is_stopping:
                return
            # Dispatcher callbacks can arrive off-loop; schedule state writes safely.
            self.hass.add_job(self.async_write_ha_state)

        @callback
        def _handle_removed(alarm_id: str) -> None:
            if alarm_id != self._alarm_id:
                return
            if self.platform is None or self.hass.is_stopping:
                return
            self.hass.add_job(self.async_write_ha_state)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALARM_CHANGED,
                _handle_changed,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALARM_REMOVED,
                _handle_removed,
            )
        )
