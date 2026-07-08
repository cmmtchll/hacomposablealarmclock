"""Virtual alarm clock manager and scheduler."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ALARM_ID,
    ATTR_ALARM_NAME,
    ATTR_SCHEDULED_AT,
    ATTR_TARGET_ENTITIES,
    ATTR_TARGET_SERVICES,
    DOMAIN,
    EVENT_ALARM_TRIGGERED,
    SIGNAL_ALARM_CHANGED,
    SIGNAL_ALARM_REMOVED,
    STORAGE_VERSION,
)


@dataclass(slots=True)
class AlarmClock:
    """A virtual alarm clock definition."""

    alarm_id: str
    name: str
    alarm_time: str
    enabled: bool
    target_entities: list[str]
    target_services: list[str]
    last_triggered_iso: str | None = None


class AlarmClockManager:
    """Persist and schedule virtual alarm clocks."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize manager."""
        self._hass = hass
        self._entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}",
        )
        self._alarms: dict[str, AlarmClock] = {}
        self._scheduled: dict[str, CALLBACK_TYPE] = {}
        self._lock = asyncio.Lock()

    async def async_initialize(self) -> None:
        """Load persisted data and initialize schedules."""
        data = await self._store.async_load() or {}
        for raw_alarm in data.get("alarms", []):
            alarm = AlarmClock(
                alarm_id=str(raw_alarm["alarm_id"]),
                name=str(raw_alarm["name"]),
                alarm_time=str(raw_alarm["alarm_time"]),
                enabled=bool(raw_alarm.get("enabled", True)),
                target_entities=[str(x) for x in raw_alarm.get("target_entities", [])],
                target_services=[str(x) for x in raw_alarm.get("target_services", [])],
                last_triggered_iso=(
                    str(raw_alarm["last_triggered_iso"])
                    if raw_alarm.get("last_triggered_iso")
                    else None
                ),
            )
            self._alarms[alarm.alarm_id] = alarm
            self._schedule_alarm(alarm)

    async def async_shutdown(self) -> None:
        """Cancel all scheduled callbacks."""
        for unsub in self._scheduled.values():
            unsub()
        self._scheduled.clear()

    def async_get_alarm(self, alarm_id: str) -> AlarmClock | None:
        """Return one alarm by ID."""
        return self._alarms.get(alarm_id)

    def async_list_alarms(self) -> list[AlarmClock]:
        """Return all alarms."""
        return list(self._alarms.values())

    async def async_upsert_alarm(self, alarm: AlarmClock) -> None:
        """Create or update an alarm and reschedule it."""
        async with self._lock:
            self._alarms[alarm.alarm_id] = alarm
            self._schedule_alarm(alarm)
            await self._async_save()

        async_dispatcher_send(self._hass, SIGNAL_ALARM_CHANGED, alarm.alarm_id)

    async def async_delete_alarm(self, alarm_id: str) -> None:
        """Delete an alarm and cancel its schedule."""
        async with self._lock:
            self._alarms.pop(alarm_id, None)
            unsub = self._scheduled.pop(alarm_id, None)
            if unsub is not None:
                unsub()
            await self._async_save()

        async_dispatcher_send(self._hass, SIGNAL_ALARM_REMOVED, alarm_id)

    async def async_set_enabled(self, alarm_id: str, enabled: bool) -> None:
        """Update enabled flag for an alarm."""
        alarm = self._alarms[alarm_id]
        await self.async_upsert_alarm(
            AlarmClock(
                alarm_id=alarm.alarm_id,
                name=alarm.name,
                alarm_time=alarm.alarm_time,
                enabled=enabled,
                target_entities=alarm.target_entities,
                target_services=alarm.target_services,
                last_triggered_iso=alarm.last_triggered_iso,
            )
        )

    async def async_set_alarm_time(self, alarm_id: str, alarm_time_str: str) -> None:
        """Update alarm time for an alarm."""
        alarm = self._alarms[alarm_id]
        await self.async_upsert_alarm(
            AlarmClock(
                alarm_id=alarm.alarm_id,
                name=alarm.name,
                alarm_time=alarm_time_str,
                enabled=alarm.enabled,
                target_entities=alarm.target_entities,
                target_services=alarm.target_services,
                last_triggered_iso=alarm.last_triggered_iso,
            )
        )

    async def async_trigger_alarm_now(self, alarm_id: str) -> None:
        """Trigger an alarm immediately."""
        alarm = self._alarms[alarm_id]
        await self._async_fire_alarm(alarm, dt_util.utcnow())
        self._schedule_alarm(alarm)

    def async_next_due(self, alarm_id: str) -> datetime | None:
        """Return next due datetime in UTC for one alarm."""
        alarm = self._alarms.get(alarm_id)
        if alarm is None or not alarm.enabled:
            return None
        return _next_due_datetime_utc(alarm.alarm_time)

    def _schedule_alarm(self, alarm: AlarmClock) -> None:
        """Schedule the next due callback for an alarm."""
        unsub = self._scheduled.pop(alarm.alarm_id, None)
        if unsub is not None:
            unsub()

        if not alarm.enabled:
            return

        due_utc = _next_due_datetime_utc(alarm.alarm_time)

        @callback
        def _handle_due(_: datetime) -> None:
            self._hass.async_create_task(self._async_handle_due(alarm.alarm_id))

        self._scheduled[alarm.alarm_id] = async_track_point_in_time(
            self._hass,
            _handle_due,
            due_utc,
        )

    async def _async_handle_due(self, alarm_id: str) -> None:
        """Handle one scheduled due callback."""
        current_alarm = self._alarms.get(alarm_id)
        if current_alarm is None:
            return
        if not current_alarm.enabled:
            self._schedule_alarm(current_alarm)
            return

        await self._async_fire_alarm(current_alarm, dt_util.utcnow())
        self._schedule_alarm(current_alarm)

    async def _async_fire_alarm(self, alarm: AlarmClock, when_utc: datetime) -> None:
        """Fire alarm event and forward notifications to configured targets."""
        alarm.last_triggered_iso = when_utc.isoformat()
        await self._async_save()

        self._hass.bus.async_fire(
            EVENT_ALARM_TRIGGERED,
            {
                ATTR_ALARM_ID: alarm.alarm_id,
                ATTR_ALARM_NAME: alarm.name,
                ATTR_SCHEDULED_AT: when_utc.isoformat(),
                ATTR_TARGET_ENTITIES: alarm.target_entities,
                ATTR_TARGET_SERVICES: alarm.target_services,
            },
        )

        if alarm.target_entities:
            await self._hass.services.async_call(
                "homeassistant",
                "turn_on",
                {"entity_id": alarm.target_entities},
                blocking=False,
            )

        for service_call in alarm.target_services:
            if "." not in service_call:
                continue
            domain, service = service_call.split(".", 1)
            await self._hass.services.async_call(
                domain,
                service,
                {
                    ATTR_ALARM_ID: alarm.alarm_id,
                    ATTR_ALARM_NAME: alarm.name,
                },
                blocking=False,
            )

        async_dispatcher_send(self._hass, SIGNAL_ALARM_CHANGED, alarm.alarm_id)

    async def _async_save(self) -> None:
        """Persist all alarm data."""
        await self._store.async_save({"alarms": [asdict(a) for a in self._alarms.values()]})


def _parse_alarm_time(value: str) -> time:
    """Parse HH:MM or HH:MM:SS time."""
    parts = value.split(":")
    if len(parts) not in (2, 3):
        raise ValueError("Alarm time must be HH:MM or HH:MM:SS")

    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    return time(hour=hour, minute=minute, second=second)


def _next_due_datetime_utc(alarm_time_str: str) -> datetime:
    """Calculate the next due datetime in UTC for the alarm time in local tz."""
    alarm_time = _parse_alarm_time(alarm_time_str)
    now_local = dt_util.now()
    due_local = now_local.replace(
        hour=alarm_time.hour,
        minute=alarm_time.minute,
        second=alarm_time.second,
        microsecond=0,
    )
    if due_local <= now_local:
        due_local = due_local + timedelta(days=1)
    return dt_util.as_utc(due_local)
