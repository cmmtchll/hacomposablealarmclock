"""Tests for integration setup."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.service import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

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


async def test_alarm_manage_create_list_and_delete(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test alarm_manage can create, list, and delete alarms."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    create_result = await hass.services.async_call(
        DOMAIN,
        "alarm_manage",
        {
            "action": "create",
            "alarm_id": "kitchen",
            "alarm_name": "Kitchen",
            "alarm_time": "06:30:00",
            "enabled": True,
        },
        blocking=True,
        return_response=True,
    )
    assert create_result["ok"] is True
    assert create_result["action"] == "create"

    list_result = await hass.services.async_call(
        DOMAIN,
        "alarm_manage",
        {"action": "list"},
        blocking=True,
        return_response=True,
    )
    assert list_result["count"] == 1
    assert list_result["alarms"][0]["alarm_id"] == "kitchen"

    delete_result = await hass.services.async_call(
        DOMAIN,
        "alarm_manage",
        {"action": "delete", "alarm_id": "kitchen"},
        blocking=True,
        return_response=True,
    )
    assert delete_result["ok"] is True
    assert delete_result["action"] == "delete"


async def test_alarm_manage_update_requires_mutation_fields(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test alarm_manage update fails when no mutable fields are supplied."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "office",
            "alarm_name": "Office",
            "alarm_time": "07:15:00",
        },
        blocking=True,
    )

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "alarm_manage",
            {"action": "update", "alarm_id": "office"},
            blocking=True,
            return_response=True,
        )

    assert exc_info.value.translation_key == "no_update_fields"


async def test_alarm_manage_dry_run_does_not_persist(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test alarm_manage dry_run validates without writing state."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.services.async_call(
        DOMAIN,
        "alarm_manage",
        {
            "action": "create",
            "alarm_id": "guest_room",
            "alarm_name": "Guest Room",
            "alarm_time": "08:00:00",
            "dry_run": True,
        },
        blocking=True,
        return_response=True,
    )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["changed"] is False

    list_result = await hass.services.async_call(
        DOMAIN,
        "alarm_manage",
        {"action": "list"},
        blocking=True,
        return_response=True,
    )
    assert list_result["count"] == 0


async def test_alarm_manage_rejects_invalid_action(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test alarm_manage rejects unsupported actions."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "alarm_manage",
            {"action": "explode"},
            blocking=True,
            return_response=True,
        )

    assert exc_info.value.translation_key == "invalid_action"


async def test_alarm_manage_requires_config_entry_id_for_multi_entry(
    hass: HomeAssistant,
) -> None:
    """Test service requires config_entry_id when multiple entries are loaded."""
    entry_1 = MockConfigEntry(
        domain=DOMAIN,
        title="Alarm Workspace 1",
        unique_id=f"{DOMAIN}_1",
        data={CONF_NAME: "Alarm Workspace 1"},
    )
    entry_2 = MockConfigEntry(
        domain=DOMAIN,
        title="Alarm Workspace 2",
        unique_id=f"{DOMAIN}_2",
        data={CONF_NAME: "Alarm Workspace 2"},
    )
    entry_1.add_to_hass(hass)
    entry_2.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry_1.entry_id)
    assert await hass.config_entries.async_setup(entry_2.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "alarm_manage",
            {"action": "list"},
            blocking=True,
            return_response=True,
        )

    assert exc_info.value.translation_key == "config_entry_id_required"


async def test_repair_issue_created_for_enabled_alarm_without_targets(
    hass: HomeAssistant, setup_integration
) -> None:
    """Test repair issue is created for enabled alarms with no targets."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "config_entry_id": entry.entry_id,
            "alarm_id": "untargeted",
            "alarm_name": "Untargeted",
            "alarm_time": "07:00:00",
            "enabled": True,
            "target_entities": [],
            "target_services": "",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, "alarms_without_targets")
    assert issue is not None
    assert issue.is_fixable is True
