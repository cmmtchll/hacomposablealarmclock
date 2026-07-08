"""Tests for integration setup."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.hacomposablealarmclock.const import DOMAIN, EVENT_ALARM_TRIGGERED


async def test_setup_and_unload_entry(hass: HomeAssistant, setup_integration) -> None:
    """Test setting up and unloading the integration."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_create_alarm_and_trigger_event(hass: HomeAssistant, setup_integration) -> None:
    """Test creating a virtual alarm and triggering it."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    events: list[dict] = []

    def _capture(event) -> None:
        events.append(dict(event.data))

    unsub = hass.bus.async_listen(EVENT_ALARM_TRIGGERED, _capture)

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "kids_room",
            "alarm_name": "Kids Room",
            "alarm_time": "07:00:00",
            "enabled": True,
            "target_entities": ["light.kids_room_lamp"],
        },
        blocking=True,
    )

    await hass.services.async_call(
        DOMAIN,
        "trigger_alarm",
        {"alarm_id": "kids_room"},
        blocking=True,
    )
    await hass.async_block_till_done()

    unsub()

    assert events
    assert events[-1]["alarm_id"] == "kids_room"
