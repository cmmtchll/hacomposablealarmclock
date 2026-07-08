"""Tests for integration setup."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import ServiceValidationError

from custom_components.hacomposablealarmclock import manager as manager_module
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


async def test_create_alarm_and_trigger_event(
    hass: HomeAssistant, setup_integration
) -> None:
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


async def test_create_alarm_rejects_invalid_time(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test create alarm rejects invalid time input."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "create_alarm",
            {
                "alarm_id": "kids_room",
                "alarm_name": "Kids Room",
                "alarm_time": "25:99:99",
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "invalid_alarm_time"


async def test_create_alarm_rejects_invalid_target_service(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test create alarm rejects malformed target service values."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "create_alarm",
            {
                "alarm_id": "kids_room",
                "alarm_name": "Kids Room",
                "alarm_time": "07:00:00",
                "target_services": ["not_a_service"],
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "invalid_target_service"


async def test_trigger_alarm_rejects_missing_alarm(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test trigger alarm returns a validation error for unknown alarms."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "trigger_alarm",
            {"alarm_id": "missing"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "alarm_not_found"


async def test_delete_alarm_rejects_missing_alarm(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test delete alarm returns a validation error for unknown alarms."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "delete_alarm",
            {"alarm_id": "missing"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "alarm_not_found"


async def test_setup_skips_invalid_stored_alarm(
    hass: HomeAssistant,
    setup_integration,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test setup skips malformed stored alarms instead of failing the entry."""
    entry = setup_integration

    monkeypatch.setattr(
        manager_module.Store,
        "async_load",
        AsyncMock(
            return_value={
                "alarms": [
                    {
                        "alarm_id": "kids_room",
                        "name": "Kids Room",
                        "alarm_time": "not-a-time",
                        "enabled": True,
                    }
                ]
            }
        ),
    )
    caplog.set_level(logging.WARNING)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    manager = hass.data[DOMAIN][entry.entry_id].manager
    assert manager.async_list_alarms() == []
    assert "Skipping invalid stored alarm" in caplog.text
