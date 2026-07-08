"""Shared entity helpers for Composable Alarm Clock."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
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
            name=self.alarm_name,
            entry_type=None,
        )
