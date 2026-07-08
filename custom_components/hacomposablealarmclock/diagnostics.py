"""Diagnostics support for Composable Alarm Clock."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import ComposableAlarmConfigEntry

TO_REDACT: set[str] = set()


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ComposableAlarmConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    del hass

    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "alarms": [
            asdict(alarm)
            for alarm in entry.runtime_data.manager.async_list_alarms()
        ],
    }
