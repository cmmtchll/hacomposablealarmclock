"""Tests for internal helper functions."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.service import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import hacomposablealarmclock as init_module
from custom_components.hacomposablealarmclock.const import (
    DOMAIN,
    ISSUE_ALARMS_WITHOUT_TARGETS,
    RuntimeData,
)
from custom_components.hacomposablealarmclock.manager import (
    AlarmClock,
    AlarmClockManager,
)


def _translation_key(exc: ServiceValidationError) -> str:
    return str(exc.translation_key)


def test_coerce_str_list_variants() -> None:
    """Test coercion helper normalizes list-like service payloads."""
    assert init_module._coerce_str_list(None) == []
    assert init_module._coerce_str_list("notify.mobile_app") == ["notify.mobile_app"]
    assert init_module._coerce_str_list("a, b, ,c") == ["a", "b", "c"]
    assert init_module._coerce_str_list([" x ", 3, ""]) == ["x", "3"]

    with pytest.raises(ServiceValidationError) as exc_info:
        init_module._coerce_str_list(123)
    assert _translation_key(exc_info.value) == "invalid_list_input"


def test_alarm_id_from_unique_id_parses_and_rejects() -> None:
    """Test unique ID parsing helper for per-alarm entities."""
    entry_id = "entry_1"
    assert (
        init_module._alarm_id_from_unique_id(
            f"{entry_id}_kids_room_next_due",
            entry_id,
        )
        == "kids_room"
    )
    assert init_module._alarm_id_from_unique_id("bad_prefix", entry_id) is None
    assert (
        init_module._alarm_id_from_unique_id(
            f"{entry_id}_kids_room_unknown_suffix",
            entry_id,
        )
        is None
    )


async def test_resolve_runtime_data_validation_paths(hass) -> None:
    """Test runtime resolution helper returns expected translated errors."""
    with pytest.raises(ServiceValidationError) as exc_not_configured:
        init_module._resolve_runtime_data(hass, None)
    assert _translation_key(exc_not_configured.value) == "integration_not_configured"

    manager_1 = AlarmClockManager(hass, "entry_1")
    manager_2 = AlarmClockManager(hass, "entry_2")

    hass.data.setdefault(DOMAIN, {})["entry_1"] = RuntimeData(manager=manager_1)
    hass.data.setdefault(DOMAIN, {})["entry_2"] = RuntimeData(manager=manager_2)

    with pytest.raises(ServiceValidationError) as exc_required:
        init_module._resolve_runtime_data(hass, None)
    assert _translation_key(exc_required.value) == "config_entry_id_required"

    with pytest.raises(ServiceValidationError) as exc_invalid:
        init_module._resolve_runtime_data(hass, "  ")
    assert _translation_key(exc_invalid.value) == "invalid_config_entry_id"

    with pytest.raises(ServiceValidationError) as exc_missing:
        init_module._resolve_runtime_data(hass, "missing")
    assert _translation_key(exc_missing.value) == "config_entry_not_found"


async def test_resolve_runtime_data_not_loaded_and_missing_runtime(hass) -> None:
    """Test entry state and runtime presence checks for explicit config entry IDs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Household Alarm Clocks",
        unique_id=DOMAIN,
        data={CONF_NAME: "Household Alarm Clocks"},
    )
    entry.add_to_hass(hass)

    manager = AlarmClockManager(hass, entry.entry_id)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = RuntimeData(manager=manager)

    with pytest.raises(ServiceValidationError) as exc_not_loaded:
        init_module._resolve_runtime_data(hass, entry.entry_id)
    assert _translation_key(exc_not_loaded.value) == "config_entry_not_loaded"

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Keep at least one runtime entry so explicit-ID validation reaches
    # the missing-runtime branch instead of integration_not_configured.
    hass.data[DOMAIN]["other_entry"] = RuntimeData(
        manager=AlarmClockManager(hass, "other_entry")
    )
    hass.data[DOMAIN][entry.entry_id] = object()
    with pytest.raises(ServiceValidationError) as exc_missing_runtime:
        init_module._resolve_runtime_data(hass, entry.entry_id)
    assert _translation_key(exc_missing_runtime.value) == "config_entry_not_loaded"


async def test_async_sync_repairs_issues_creates_and_clears_issue(
    hass,
    setup_integration,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test repair issue sync helper creates and clears issues as state changes."""
    entry = setup_integration
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Add a non-runtime value to ensure filtering path is covered.
    hass.data[DOMAIN]["not_runtime"] = object()

    create_issue_calls: list[dict[str, Any]] = []
    delete_issue_calls: list[tuple[str, str]] = []

    def _create_issue(*_args, **kwargs) -> None:
        create_issue_calls.append(kwargs)

    def _delete_issue(_hass, domain: str, issue_id: str) -> None:
        delete_issue_calls.append((domain, issue_id))

    monkeypatch.setattr(ir, "async_create_issue", _create_issue)
    monkeypatch.setattr(ir, "async_delete_issue", _delete_issue)

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

    await init_module._async_sync_repairs_issues(hass)
    assert create_issue_calls
    assert create_issue_calls[-1]["translation_key"] == ISSUE_ALARMS_WITHOUT_TARGETS

    await hass.services.async_call(
        DOMAIN,
        "update_alarm",
        {
            "alarm_id": "untargeted",
            "target_entities": ["light.bedroom"],
            "target_services": "",
        },
        blocking=True,
    )

    await init_module._async_sync_repairs_issues(hass)
    assert delete_issue_calls
    assert delete_issue_calls[-1] == (DOMAIN, ISSUE_ALARMS_WITHOUT_TARGETS)


def test_alarm_to_dict_serializes_fields() -> None:
    """Test service response serialization helper."""
    alarm = AlarmClock(
        alarm_id="kids_room",
        name="Kids Room",
        alarm_time="07:00:00",
        enabled=True,
        target_entities=["light.kids_room"],
        target_services=["script.wakeup"],
        last_triggered_iso="2026-01-01T07:00:00+00:00",
    )

    result = init_module._alarm_to_dict(alarm)

    assert result["alarm_id"] == "kids_room"
    assert result["target_entities"] == ["light.kids_room"]
    assert result["target_services"] == ["script.wakeup"]


def test_registered_alarm_ids_for_entry_parses_registry_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test extraction of alarm IDs from per-entry entity registry rows."""
    entry_id = "entry_1"

    row_ok = MagicMock(platform=DOMAIN, unique_id=f"{entry_id}_kids_room_next_due")
    row_other_platform = MagicMock(
        platform="sensor",
        unique_id=f"{entry_id}_foo_status",
    )
    row_other_prefix = MagicMock(platform=DOMAIN, unique_id="different_prefix")

    monkeypatch.setattr(
        init_module.er,
        "async_entries_for_config_entry",
        lambda _registry, _entry_id: [row_ok, row_other_platform, row_other_prefix],
    )

    result = init_module._registered_alarm_ids_for_entry(MagicMock(), entry_id)

    assert result == {"kids_room"}
