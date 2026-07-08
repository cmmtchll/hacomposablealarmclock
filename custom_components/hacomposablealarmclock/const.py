"""Constants for the Composable Alarm Clock integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.const import Platform

DOMAIN = "hacomposablealarmclock"
NAME = "Composable Alarm Clock"

CONF_DEFAULT_TARGET_ENTITIES = "default_target_entities"
CONF_DEFAULT_TARGET_SERVICES = "default_target_services"

ATTR_ALARM_ID = "alarm_id"
ATTR_ALARM_NAME = "alarm_name"
ATTR_ALARM_TIME = "alarm_time"
ATTR_ACTION = "action"
ATTR_DRY_RUN = "dry_run"
ATTR_ENABLED = "enabled"
ATTR_TARGET_ENTITIES = "target_entities"
ATTR_TARGET_SERVICES = "target_services"
ATTR_SCHEDULED_AT = "scheduled_at"

DEFAULT_ENTRY_TITLE = "Household Alarm Clocks"

STORAGE_VERSION = 1

SIGNAL_ALARM_CHANGED = f"{DOMAIN}_alarm_changed"
SIGNAL_ALARM_REMOVED = f"{DOMAIN}_alarm_removed"

EVENT_ALARM_TRIGGERED = f"{DOMAIN}_alarm_triggered"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.TIME]

if TYPE_CHECKING:
    from .manager import AlarmClockManager


@dataclass(slots=True)
class RuntimeData:
    """Runtime data stored in ConfigEntry.runtime_data."""

    manager: AlarmClockManager
