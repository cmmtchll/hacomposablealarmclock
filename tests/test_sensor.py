"""Tests for sensor entities."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.hacomposablealarmclock.const import DOMAIN


async def test_sensor_entities_created(
    hass: HomeAssistant,
    setup_integration,
) -> None:
    """Test sensors are created for a virtual alarm."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "kids_room",
            "alarm_name": "Kids Room",
            "alarm_time": "07:30:00",
            "enabled": True,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    next_due = hass.states.get("sensor.kids_room_next_due")
    last_triggered = hass.states.get("sensor.kids_room_last_triggered")
    enabled = hass.states.get("switch.kids_room_enabled")
    alarm_time = hass.states.get("time.kids_room_alarm_time")

    assert next_due is not None
    assert last_triggered is not None
    assert enabled is not None
    assert alarm_time is not None
