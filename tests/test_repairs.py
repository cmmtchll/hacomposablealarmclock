"""Tests for repair flows."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.hacomposablealarmclock.const import DOMAIN
from custom_components.hacomposablealarmclock.repairs import (
    DisableUntargetedAlarmsRepairFlow,
    async_create_fix_flow,
)


async def test_create_fix_flow_unknown_issue_raises(hass) -> None:
    """Test unknown issue IDs are rejected."""
    with pytest.raises(ValueError):
        await async_create_fix_flow(hass, "unknown_issue", None)


async def test_disable_untargeted_alarms_flow_shows_confirmation_form(hass) -> None:
    """Test initial repair step presents a confirmation form."""
    flow = DisableUntargetedAlarmsRepairFlow([])
    flow.hass = hass

    result = await flow.async_step_init()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_disable_untargeted_alarms_flow_disables_matching_alarms(
    hass,
    setup_integration,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test repair flow disables alarms referenced in issue payload."""
    entry = setup_integration
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "untargeted",
            "alarm_name": "Untargeted",
            "alarm_time": "07:00:00",
            "enabled": True,
            "target_entities": [],
            "target_services": "",
        },
        blocking=True,
    )

    sync_mock = AsyncMock()
    monkeypatch.setattr(
        "custom_components.hacomposablealarmclock.repairs._async_sync_repairs_issues",
        sync_mock,
    )

    flow = DisableUntargetedAlarmsRepairFlow(
        [
            f"{entry.entry_id}:untargeted",
            "missing_entry:missing_alarm",
        ]
    )
    flow.hass = hass

    result = await flow.async_step_init(user_input={})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
    sync_mock.assert_awaited_once()

    runtime = hass.data[DOMAIN][entry.entry_id]
    alarm = runtime.manager.async_get_alarm("untargeted")
    assert alarm is not None
    assert alarm.enabled is False
