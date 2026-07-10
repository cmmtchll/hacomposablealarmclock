"""Tests for Composable Alarm Clock config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.hacomposablealarmclock.const import (
    ATTR_ALARM_ID,
    DEFAULT_ENTRY_TITLE,
    DOMAIN,
)


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_ENTRY_TITLE,
        },
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEFAULT_ENTRY_TITLE


async def test_user_flow_single_instance(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test duplicate setup is aborted."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: DEFAULT_ENTRY_TITLE},
    )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_options_flow_add_alarm(hass: HomeAssistant, mock_config_entry) -> None:
    """Test adding an alarm from options flow."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    init_result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    assert init_result["type"] is FlowResultType.FORM

    select_result = await hass.config_entries.options.async_configure(
        init_result["flow_id"],
        {"operation": "add_alarm"},
    )
    assert select_result["type"] is FlowResultType.FORM
    assert select_result["step_id"] == "add_alarm"

    create_result = await hass.config_entries.options.async_configure(
        select_result["flow_id"],
        {
            "alarm_id": "school_day",
            "alarm_name": "School Day",
            "alarm_time": "07:10:00",
            "enabled": True,
            "target_entities": [],
            "target_services": "",
        },
    )
    assert create_result["type"] is FlowResultType.CREATE_ENTRY


async def test_options_flow_workspace_defaults_round_trip(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test workspace default targets are saved from options flow."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    init_result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    workspace_step = await hass.config_entries.options.async_configure(
        init_result["flow_id"],
        {"operation": "workspace_defaults"},
    )
    assert workspace_step["type"] is FlowResultType.FORM
    assert workspace_step["step_id"] == "workspace_defaults"

    result = await hass.config_entries.options.async_configure(
        workspace_step["flow_id"],
        {
            "default_target_entities": ["light.kids_room"],
            "default_target_services": "notify.mobile_app_parent, script.wakeup",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["default_target_entities"] == ["light.kids_room"]
    assert result["data"]["default_target_services"] == [
        "notify.mobile_app_parent",
        "script.wakeup",
    ]


async def test_options_flow_select_alarm_requires_existing_alarms(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test mutation operations abort when no alarms exist."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    init_result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    result = await hass.config_entries.options.async_configure(
        init_result["flow_id"],
        {"operation": "edit_alarm"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_alarms"


async def test_options_flow_add_alarm_validation_error_shows_form(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test add-alarm validation errors keep flow on the add step."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    init_result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    add_step = await hass.config_entries.options.async_configure(
        init_result["flow_id"],
        {"operation": "add_alarm"},
    )
    assert add_step["step_id"] == "add_alarm"

    result = await hass.config_entries.options.async_configure(
        add_step["flow_id"],
        {
            "alarm_id": "school_day",
            "alarm_name": "School Day",
            "alarm_time": "07:10:00",
            "enabled": True,
            "target_entities": [],
            "target_services": "not_a_service",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_alarm"
    assert result["errors"]["base"] == "invalid_target_service"


async def test_options_flow_delete_alarm_confirm_required(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test delete-alarm step requires explicit confirmation."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "school_day",
            "alarm_name": "School Day",
            "alarm_time": "07:10:00",
            "enabled": True,
        },
        blocking=True,
    )

    init_result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    select_alarm = await hass.config_entries.options.async_configure(
        init_result["flow_id"],
        {"operation": "delete_alarm"},
    )
    assert select_alarm["step_id"] == "select_alarm"

    delete_step = await hass.config_entries.options.async_configure(
        select_alarm["flow_id"],
        {ATTR_ALARM_ID: "school_day"},
    )
    assert delete_step["step_id"] == "delete_alarm"

    confirm_required = await hass.config_entries.options.async_configure(
        delete_step["flow_id"],
        {"confirm": False},
    )
    assert confirm_required["type"] is FlowResultType.FORM
    assert confirm_required["errors"]["base"] == "confirm_required"

    deleted = await hass.config_entries.options.async_configure(
        delete_step["flow_id"],
        {"confirm": True},
    )
    assert deleted["type"] is FlowResultType.CREATE_ENTRY


async def test_options_flow_clone_and_toggle_alarm(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test clone and toggle operations mutate alarm state as expected."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "school_day",
            "alarm_name": "School Day",
            "alarm_time": "07:10:00",
            "enabled": True,
        },
        blocking=True,
    )

    init_clone = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    select_clone = await hass.config_entries.options.async_configure(
        init_clone["flow_id"],
        {"operation": "clone_alarm"},
    )
    clone_step = await hass.config_entries.options.async_configure(
        select_clone["flow_id"],
        {ATTR_ALARM_ID: "school_day"},
    )
    cloned = await hass.config_entries.options.async_configure(
        clone_step["flow_id"],
        {
            "alarm_id": "school_day_copy",
            "alarm_name": "School Day Copy",
            "alarm_time": "07:15:00",
            "enabled": True,
            "target_entities": [],
            "target_services": "",
        },
    )
    assert cloned["type"] is FlowResultType.CREATE_ENTRY

    init_toggle = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    select_toggle = await hass.config_entries.options.async_configure(
        init_toggle["flow_id"],
        {"operation": "toggle_alarm"},
    )
    toggle_step = await hass.config_entries.options.async_configure(
        select_toggle["flow_id"],
        {ATTR_ALARM_ID: "school_day_copy"},
    )
    toggled = await hass.config_entries.options.async_configure(
        toggle_step["flow_id"],
        {"enabled": False},
    )
    assert toggled["type"] is FlowResultType.CREATE_ENTRY

    list_result = await hass.services.async_call(
        DOMAIN,
        "alarm_manage",
        {"action": "list"},
        blocking=True,
        return_response=True,
    )
    alarms = list_result["alarms"]
    assert isinstance(alarms, list)
    clone = next(
        alarm
        for alarm in alarms
        if isinstance(alarm, dict)
        and str(alarm.get("alarm_id")) == "school_day_copy"
    )
    assert isinstance(clone, dict)
    clone = clone
    assert clone["enabled"] is False


async def test_options_flow_edit_alarm_form_and_update(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test edit-alarm form path and successful update submission."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "alarm_id": "school_day",
            "alarm_name": "School Day",
            "alarm_time": "07:10:00",
            "enabled": True,
            "target_entities": ["light.kids_room"],
            "target_services": "notify.mobile_app_parent",
        },
        blocking=True,
    )

    init_result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    select_step = await hass.config_entries.options.async_configure(
        init_result["flow_id"],
        {"operation": "edit_alarm"},
    )
    assert select_step["type"] is FlowResultType.FORM
    assert select_step["step_id"] == "select_alarm"

    edit_form = await hass.config_entries.options.async_configure(
        select_step["flow_id"],
        {ATTR_ALARM_ID: "school_day"},
    )
    assert edit_form["type"] is FlowResultType.FORM
    assert edit_form["step_id"] == "edit_alarm"

    edited = await hass.config_entries.options.async_configure(
        edit_form["flow_id"],
        {
            "alarm_name": "School Day Updated",
            "alarm_time": "07:20:00",
            "enabled": False,
            "target_entities": ["light.kids_room"],
            "target_services": "notify.mobile_app_parent",
        },
    )
    assert edited["type"] is FlowResultType.CREATE_ENTRY

    list_result = await hass.services.async_call(
        DOMAIN,
        "alarm_manage",
        {"action": "list"},
        blocking=True,
        return_response=True,
    )
    alarms = list_result["alarms"]
    assert isinstance(alarms, list)
    alarm = next(
        item
        for item in alarms
        if isinstance(item, dict) and str(item.get("alarm_id")) == "school_day"
    )
    assert isinstance(alarm, dict)
    assert alarm["alarm_name"] == "School Day Updated"
    assert alarm["alarm_time"] == "07:20:00"
    assert alarm["enabled"] is False
