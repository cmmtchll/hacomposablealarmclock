"""Tests for sensor entities."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.hacomposablealarmclock.const import (
    DOMAIN,
    SIGNAL_ALARM_CHANGED,
    SIGNAL_ALARM_REMOVED,
)


async def test_sensor_entities_created(
    hass: HomeAssistant,
    setup_integration,
) -> None:
    """Test sensors are created for a virtual alarm."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    workspace = hass.states.get("sensor.alarm_workspace_workspace_overview")
    assert workspace is not None
    assert workspace.state == "0"

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
    configuration = hass.states.get("sensor.kids_room_configuration")
    status = hass.states.get("sensor.kids_room_status")
    enabled = hass.states.get("switch.kids_room_enabled")
    alarm_time = hass.states.get("time.kids_room_alarm_time")
    trigger_now = hass.states.get("button.kids_room_trigger_now")
    workspace = hass.states.get("sensor.alarm_workspace_workspace_overview")

    assert next_due is not None
    assert last_triggered is not None
    assert configuration is not None
    assert status is not None
    assert enabled is not None
    assert alarm_time is not None
    assert trigger_now is not None
    assert workspace is not None
    assert workspace.state == "1"


async def test_workspace_overview_includes_alarm_snapshot(
    hass: HomeAssistant,
    setup_integration,
) -> None:
    """Test workspace overview exposes compact alarm snapshots."""
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
            "target_entities": ["light.kids_room_lamp", "switch.kids_fan"],
            "target_services": ["notify.mobile_app_parent"],
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    workspace = hass.states.get("sensor.alarm_workspace_workspace_overview")

    assert workspace is not None
    assert workspace.state == "1"
    alarms = workspace.attributes["alarms"]
    assert len(alarms) == 1
    assert alarms[0]["alarm_id"] == "kids_room"
    assert alarms[0]["target_entities_count"] == 2
    assert alarms[0]["target_services_count"] == 1


async def test_alarm_config_and_status_attributes(
    hass: HomeAssistant,
    setup_integration,
) -> None:
    """Test per-alarm config and status sensors expose expected attributes."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "kids_room",
            "alarm_name": "Kids Room",
            "alarm_time": "06:45:00",
            "enabled": False,
            "target_entities": ["light.kids_room_lamp", "switch.kids_fan"],
            "target_services": ["script.wake_kids"],
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    config_state = hass.states.get("sensor.kids_room_configuration")
    status_state = hass.states.get("sensor.kids_room_status")

    assert config_state is not None
    assert status_state is not None

    assert config_state.state == "3"
    assert config_state.attributes["alarm_time"] == "06:45:00"
    assert config_state.attributes["enabled"] is False
    assert config_state.attributes["target_entities"] == [
        "light.kids_room_lamp",
        "switch.kids_fan",
    ]
    assert config_state.attributes["target_services"] == ["script.wake_kids"]

    assert status_state.state == "disabled"
    assert status_state.attributes.get("device_class") == "enum"
    assert status_state.attributes["alarm_id"] == "kids_room"
    assert status_state.attributes["target_entities_count"] == 2
    assert status_state.attributes["target_services_count"] == 1


async def test_alarm_entities_are_removed_after_delete(
    hass: HomeAssistant,
    setup_integration,
) -> None:
    """Test per-alarm entities and device are removed after deleting the alarm."""
    entry = setup_integration

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "kids_room",
            "alarm_name": "Kids Room",
            "alarm_time": "07:15:00",
            "enabled": True,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "delete_alarm",
        {"alarm_id": "kids_room"},
        blocking=True,
    )
    await hass.async_block_till_done()

    for entity_id in (
        "button.kids_room_trigger_now",
        "sensor.kids_room_next_due",
        "sensor.kids_room_last_triggered",
        "sensor.kids_room_configuration",
        "sensor.kids_room_status",
        "switch.kids_room_enabled",
        "time.kids_room_alarm_time",
    ):
        assert hass.states.get(entity_id) is None

    entity_registry = er.async_get(hass)
    for entity_domain, suffix in (
        ("button", "trigger_now"),
        ("sensor", "next_due"),
        ("sensor", "last_triggered"),
        ("sensor", "configuration"),
        ("sensor", "status"),
        ("switch", "enabled"),
        ("time", "alarm_time"),
    ):
        assert (
            entity_registry.async_get_entity_id(
                entity_domain,
                DOMAIN,
                f"{entry.entry_id}_kids_room_{suffix}",
            )
            is None
        )

    device_registry = dr.async_get(hass)
    assert device_registry.async_get_device(identifiers={(DOMAIN, "kids_room")}) is None

    workspace = hass.states.get("sensor.alarm_workspace_workspace_overview")
    assert workspace is not None
    assert workspace.state == "0"


async def test_stale_alarm_entities_are_removed_on_setup(
    hass: HomeAssistant,
    setup_integration,
) -> None:
    """Test setup reconciles stale registry entries for deleted alarms."""
    entry = setup_integration
    device_registry = dr.async_get(hass)
    stale_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "stale_alarm")},
    )
    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_stale_alarm_next_due",
        config_entry=entry,
        device_id=stale_device.id,
        suggested_object_id="stale_alarm_next_due",
    )

    assert entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_stale_alarm_next_due",
    )
    assert device_registry.async_get_device(identifiers={(DOMAIN, "stale_alarm")})

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert (
        entity_registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            f"{entry.entry_id}_stale_alarm_next_due",
        )
        is None
    )
    assert (
        device_registry.async_get_device(identifiers={(DOMAIN, "stale_alarm")})
        is None
    )


async def test_existing_alarm_entities_are_restored_on_reload(
    hass: HomeAssistant,
    setup_integration,
) -> None:
    """Test pre-existing alarms get their entities on integration reload."""
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

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.kids_room_next_due") is not None
    assert hass.states.get("sensor.kids_room_last_triggered") is not None
    assert hass.states.get("sensor.kids_room_configuration") is not None
    assert hass.states.get("sensor.kids_room_status") is not None
    assert hass.states.get("switch.kids_room_enabled") is not None
    assert hass.states.get("time.kids_room_alarm_time") is not None


async def test_alarm_changed_dispatch_from_executor_is_thread_safe(
    hass: HomeAssistant,
    setup_integration,
    caplog,
) -> None:
    """Test alarm-changed dispatcher callback is safe from executor thread."""
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
    await hass.async_block_till_done()

    caplog.set_level(logging.ERROR)
    caplog.clear()

    await hass.async_add_executor_job(
        async_dispatcher_send,
        hass,
        SIGNAL_ALARM_CHANGED,
        "kids_room",
    )
    await hass.async_block_till_done()

    assert (
        "calls async_write_ha_state from a thread other than the event loop"
        not in caplog.text
    )
    assert "is not the running loop" not in caplog.text


async def test_alarm_removed_dispatch_from_executor_is_thread_safe(
    hass: HomeAssistant,
    setup_integration,
    caplog,
) -> None:
    """Test alarm-removed dispatcher callback is safe from executor thread."""
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
    await hass.async_block_till_done()

    caplog.set_level(logging.ERROR)
    caplog.clear()

    await hass.async_add_executor_job(
        async_dispatcher_send,
        hass,
        SIGNAL_ALARM_REMOVED,
        "kids_room",
    )
    await hass.async_block_till_done()

    assert (
        "calls async_write_ha_state from a thread other than the event loop"
        not in caplog.text
    )


async def test_dispatch_after_unload_does_not_log_thread_or_pending_task_errors(
    hass: HomeAssistant,
    setup_integration,
    caplog,
) -> None:
    """Test dispatcher signals after unload do not create thread/pending-task errors."""
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
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    caplog.set_level(logging.ERROR)
    caplog.clear()

    await hass.async_add_executor_job(
        async_dispatcher_send,
        hass,
        SIGNAL_ALARM_CHANGED,
        "kids_room",
    )
    await hass.async_add_executor_job(
        async_dispatcher_send,
        hass,
        SIGNAL_ALARM_REMOVED,
        "kids_room",
    )
    await hass.async_block_till_done()

    assert (
        "calls async_write_ha_state from a thread other than the event loop"
        not in caplog.text
    )
    assert "Task was destroyed but it is pending" not in caplog.text
    assert "is not the running loop" not in caplog.text
