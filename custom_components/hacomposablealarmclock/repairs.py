"""Repairs flows for Composable Alarm Clock."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant

from . import _async_sync_repairs_issues
from .const import DOMAIN, ISSUE_ALARMS_WITHOUT_TARGETS, RuntimeData


class DisableUntargetedAlarmsRepairFlow(RepairsFlow):
    """Disable enabled alarms that have no configured targets."""

    def __init__(self, alarms: list[str]) -> None:
        """Initialize repair flow data."""
        self._alarms = alarms

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Show confirmation for disabling untargeted alarms."""
        if user_input is not None:
            for alarm_ref in self._alarms:
                entry_id, _, alarm_id = alarm_ref.partition(":")
                runtime_data = self.hass.data.get(DOMAIN, {}).get(entry_id)
                if not isinstance(runtime_data, RuntimeData):
                    continue
                if runtime_data.manager.async_get_alarm(alarm_id) is None:
                    continue
                await runtime_data.manager.async_set_enabled(alarm_id, False)

            await _async_sync_repairs_issues(self.hass)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create fix flow for a repair issue."""
    del hass
    if issue_id == ISSUE_ALARMS_WITHOUT_TARGETS:
        alarms = [str(item) for item in (data or {}).get("alarms", [])]
        return DisableUntargetedAlarmsRepairFlow(alarms)

    raise ValueError(f"Unknown issue_id: {issue_id}")
