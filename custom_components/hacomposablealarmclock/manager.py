"""Virtual alarm clock manager and scheduler."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
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

LOGGER = logging.getLogger(__name__)


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


class AlarmValidationError(ValueError):
    """Raised when an alarm definition or operation is invalid."""

    def __init__(
        self,
        translation_key: str,
        *,
        message: str,
        placeholders: dict[str, str] | None = None,
    ) -> None:
        """Initialize validation error details."""
        super().__init__(message)
        self.translation_key = translation_key
        self.translation_placeholders = placeholders or {}


class AlarmNotFoundError(AlarmValidationError):
    """Raised when an alarm lookup fails."""

    def __init__(self, alarm_id: str) -> None:
        """Initialize alarm-not-found error details."""
        super().__init__(
            "alarm_not_found",
            message=f"Alarm '{alarm_id}' was not found",
            placeholders={"alarm_id": alarm_id},
        )


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
            try:
                alarm = _alarm_from_storage(raw_alarm)
            except AlarmValidationError as err:
                LOGGER.warning(
                    "Skipping invalid stored alarm for entry %s: %s",
                    self._entry_id,
                    err,
                )
                continue
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
        validated_alarm = _normalize_alarm(alarm)

        async with self._lock:
            self._alarms[validated_alarm.alarm_id] = validated_alarm
            self._schedule_alarm(validated_alarm)
            await self._async_save()

        async_dispatcher_send(
            self._hass,
            SIGNAL_ALARM_CHANGED,
            validated_alarm.alarm_id,
        )

    async def async_delete_alarm(self, alarm_id: str) -> None:
        """Delete an alarm and cancel its schedule."""
        if alarm_id not in self._alarms:
            raise AlarmNotFoundError(alarm_id)

        async with self._lock:
            self._alarms.pop(alarm_id)
            unsub = self._scheduled.pop(alarm_id, None)
            if unsub is not None:
                unsub()
            await self._async_save()

        async_dispatcher_send(self._hass, SIGNAL_ALARM_REMOVED, alarm_id)

    async def async_set_enabled(self, alarm_id: str, enabled: bool) -> None:
        """Update enabled flag for an alarm."""
        alarm = self.async_get_alarm(alarm_id)
        if alarm is None:
            raise AlarmNotFoundError(alarm_id)

        await self.async_upsert_alarm(replace(alarm, enabled=enabled))

    async def async_set_alarm_time(self, alarm_id: str, alarm_time_str: str) -> None:
        """Update alarm time for an alarm."""
        alarm = self.async_get_alarm(alarm_id)
        if alarm is None:
            raise AlarmNotFoundError(alarm_id)

        await self.async_upsert_alarm(replace(alarm, alarm_time=alarm_time_str))

    async def async_trigger_alarm_now(self, alarm_id: str) -> None:
        """Trigger an alarm immediately."""
        alarm = self.async_get_alarm(alarm_id)
        if alarm is None:
            raise AlarmNotFoundError(alarm_id)

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
            domain, service = _split_service_call(service_call)
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
        await self._store.async_save(
            {"alarms": [asdict(alarm) for alarm in self._alarms.values()]}
        )


def _parse_alarm_time(value: str) -> time:
    """Parse HH:MM or HH:MM:SS time."""
    parts = value.split(":")
    if len(parts) not in (2, 3):
        raise ValueError("Alarm time must be HH:MM or HH:MM:SS")

    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    return time(hour=hour, minute=minute, second=second)


def _split_service_call(value: str) -> tuple[str, str]:
    """Split and validate a domain.service target."""
    normalized_value = value.strip()
    if normalized_value.count(".") != 1:
        raise AlarmValidationError(
            "invalid_target_service",
            message=(f"Target service '{value}' must use the 'domain.service' format"),
            placeholders={"service": normalized_value or value},
        )

    domain, service = normalized_value.split(".", 1)
    if not domain or not service:
        raise AlarmValidationError(
            "invalid_target_service",
            message=(f"Target service '{value}' must use the 'domain.service' format"),
            placeholders={"service": normalized_value or value},
        )
    return domain, service


def _normalize_alarm(alarm: AlarmClock) -> AlarmClock:
    """Validate and canonicalize an alarm definition."""
    alarm_id = alarm.alarm_id.strip()
    if not alarm_id:
        raise AlarmValidationError(
            "invalid_alarm_id",
            message="Alarm ID cannot be empty",
        )

    name = alarm.name.strip()
    if not name:
        raise AlarmValidationError(
            "invalid_alarm_name",
            message="Alarm name cannot be empty",
        )

    try:
        normalized_time = _parse_alarm_time(alarm.alarm_time).isoformat()
    except ValueError as err:
        raise AlarmValidationError(
            "invalid_alarm_time",
            message=f"Alarm time '{alarm.alarm_time}' is invalid",
            placeholders={"value": alarm.alarm_time},
        ) from err

    normalized_target_entities = [
        entity_id.strip() for entity_id in alarm.target_entities if entity_id.strip()
    ]
    normalized_target_services = [
        f"{domain}.{service}"
        for domain, service in (
            _split_service_call(value) for value in alarm.target_services
        )
    ]

    return replace(
        alarm,
        alarm_id=alarm_id,
        name=name,
        alarm_time=normalized_time,
        target_entities=normalized_target_entities,
        target_services=normalized_target_services,
    )


def _alarm_from_storage(raw_alarm: Mapping[str, Any]) -> AlarmClock:
    """Build a validated alarm from persisted storage."""
    try:
        last_triggered_iso = raw_alarm.get("last_triggered_iso")
        if last_triggered_iso is not None:
            datetime.fromisoformat(str(last_triggered_iso))

        return _normalize_alarm(
            AlarmClock(
                alarm_id=str(raw_alarm["alarm_id"]),
                name=str(raw_alarm["name"]),
                alarm_time=str(raw_alarm["alarm_time"]),
                enabled=bool(raw_alarm.get("enabled", True)),
                target_entities=[str(x) for x in raw_alarm.get("target_entities", [])],
                target_services=[str(x) for x in raw_alarm.get("target_services", [])],
                last_triggered_iso=(
                    str(last_triggered_iso) if last_triggered_iso is not None else None
                ),
            )
        )
    except AlarmValidationError:
        raise
    except (KeyError, TypeError, ValueError) as err:
        raise AlarmValidationError(
            "invalid_alarm_time",
            message=f"Stored alarm definition is invalid: {err}",
        ) from err


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
