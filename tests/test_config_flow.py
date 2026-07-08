"""Tests for Composable Alarm Clock config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.hacomposablealarmclock.const import DEFAULT_ENTRY_TITLE, DOMAIN


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
