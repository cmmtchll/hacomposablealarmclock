"""Tests for diagnostics output."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.hacomposablealarmclock.const import DOMAIN

from custom_components.hacomposablealarmclock.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_api_key(
    hass: HomeAssistant,
    setup_integration,
) -> None:
    """Test diagnostics output includes virtual alarms."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "kids_room",
            "alarm_name": "Kids Room",
            "alarm_time": "07:00:00",
            "enabled": True,
        },
        blocking=True,
    )

    data = await async_get_config_entry_diagnostics(hass, entry)

    assert "alarms" in data
    assert data["alarms"][0]["alarm_id"] == "kids_room"
