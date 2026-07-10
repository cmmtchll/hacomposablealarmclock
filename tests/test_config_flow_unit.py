"""Direct unit tests for config flow branch behavior."""

from __future__ import annotations

from homeassistant.const import CONF_NAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hacomposablealarmclock.config_flow import (
    ComposableAlarmConfigFlow,
    ComposableAlarmOptionsFlow,
    _coerce_list_input,
)
from custom_components.hacomposablealarmclock.const import (
    ATTR_ALARM_ID,
    DEFAULT_ENTRY_TITLE,
    DOMAIN,
    RuntimeData,
)
from custom_components.hacomposablealarmclock.manager import (
    AlarmClock,
    AlarmClockManager,
)


def test_coerce_list_input_variants() -> None:
    """Test options-flow list coercion helper."""
    assert _coerce_list_input(None) == []
    assert _coerce_list_input("a") == ["a"]
    assert _coerce_list_input("a, b, , c") == ["a", "b", "c"]
    assert _coerce_list_input(["x", " ", 3]) == ["x", "3"]
    assert _coerce_list_input(("x", "y")) == ["x", "y"]


async def test_config_flow_reauth_steps_abort(hass) -> None:
    """Test both reauth entry points abort for local-only integration."""
    flow = ComposableAlarmConfigFlow()
    flow.hass = hass

    result_reauth = await flow.async_step_reauth({"foo": "bar"})
    result_confirm = await flow.async_step_reauth_confirm({"confirm": True})

    assert result_reauth["reason"] == "reauth_not_supported"
    assert result_confirm["reason"] == "reauth_not_supported"


async def test_config_flow_reconfigure_unknown_entry_aborts(hass) -> None:
    """Test reconfigure aborts when the entry cannot be resolved."""
    flow = ComposableAlarmConfigFlow()
    flow.hass = hass
    flow.context = {"entry_id": "missing"}

    result = await flow.async_step_reconfigure()

    assert result["reason"] == "unknown"


async def test_config_flow_reconfigure_form_defaults(hass) -> None:
    """Test reconfigure form includes defaults from the existing entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Household Alarm Clocks",
        unique_id=DOMAIN,
        data={CONF_NAME: "Household Alarm Clocks"},
    )
    entry.add_to_hass(hass)

    flow = ComposableAlarmConfigFlow()
    flow.hass = hass
    flow.context = {"entry_id": entry.entry_id}

    result = await flow.async_step_reconfigure()

    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"


async def test_options_flow_runtime_unavailable_branches(hass) -> None:
    """Test options branches abort cleanly when runtime data is unavailable."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Household Alarm Clocks",
        unique_id=DOMAIN,
        data={CONF_NAME: "Household Alarm Clocks"},
    )
    entry.add_to_hass(hass)

    flow = ComposableAlarmOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    assert (await flow.async_step_add_alarm())["reason"] == "runtime_unavailable"

    flow._selected_alarm_id = "kids_room"
    assert (await flow.async_step_edit_alarm())["reason"] == "runtime_unavailable"
    assert (await flow.async_step_delete_alarm())["reason"] == "runtime_unavailable"
    assert (await flow.async_step_clone_alarm())["reason"] == "runtime_unavailable"
    assert (await flow.async_step_toggle_alarm())["reason"] == "runtime_unavailable"


async def test_options_flow_alarm_not_found_branches(hass) -> None:
    """Test selected-alarm operations abort when selected alarm does not exist."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Household Alarm Clocks",
        unique_id=DOMAIN,
        data={CONF_NAME: "Household Alarm Clocks"},
    )
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = RuntimeData(
        manager=AlarmClockManager(hass, entry.entry_id)
    )

    flow = ComposableAlarmOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    flow._selected_alarm_id = "missing_alarm"

    assert (await flow.async_step_edit_alarm())["reason"] == "alarm_not_found"
    assert (await flow.async_step_delete_alarm())["reason"] == "alarm_not_found"
    assert (await flow.async_step_clone_alarm())["reason"] == "alarm_not_found"
    assert (await flow.async_step_toggle_alarm())["reason"] == "alarm_not_found"


async def test_options_flow_select_alarm_unknown_operation_aborts(hass) -> None:
    """Test select-alarm step aborts if operation is unknown."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Household Alarm Clocks",
        unique_id=DOMAIN,
        data={CONF_NAME: "Household Alarm Clocks"},
    )
    entry.add_to_hass(hass)

    manager = AlarmClockManager(hass, entry.entry_id)
    manager._alarms["kids_room"] = AlarmClock(
        alarm_id="kids_room",
        name="Kids Room",
        alarm_time="07:00:00",
        enabled=True,
        target_entities=[],
        target_services=[],
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = RuntimeData(manager=manager)

    flow = ComposableAlarmOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    flow._operation = "unsupported"

    result = await flow.async_step_select_alarm({ATTR_ALARM_ID: "kids_room"})

    assert result["reason"] == "unknown_operation"


async def test_config_flow_user_blank_name_defaults_title(hass) -> None:
    """Test blank user-provided title falls back to default."""
    started = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    result = await hass.config_entries.flow.async_configure(
        started["flow_id"],
        {CONF_NAME: "   "},
    )

    assert result["type"] == "create_entry"
    assert result["title"] == DEFAULT_ENTRY_TITLE
