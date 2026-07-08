"""The Composable Alarm Clock integration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.service import ServiceValidationError
from homeassistant.util import slugify

from .const import (
    ATTR_ALARM_ID,
    ATTR_ALARM_NAME,
    ATTR_ALARM_TIME,
    ATTR_ENABLED,
    ATTR_TARGET_ENTITIES,
    ATTR_TARGET_SERVICES,
    DOMAIN,
    PLATFORMS,
    RuntimeData,
)
from .manager import AlarmClock, AlarmClockManager


type ComposableAlarmConfigEntry = ConfigEntry[RuntimeData]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration via YAML (unused) and shared services."""
    del config

    async def _require_single_runtime() -> RuntimeData:
        entries: dict[str, RuntimeData] = hass.data.get(DOMAIN, {})
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="integration_not_configured",
            )
        return next(iter(entries.values()))

    async def async_handle_create_alarm(call: ServiceCall) -> None:
        """Create or replace a virtual alarm clock."""
        runtime_data = await _require_single_runtime()

        alarm_name = str(call.data[ATTR_ALARM_NAME]).strip()
        alarm_id = str(call.data.get(ATTR_ALARM_ID) or slugify(alarm_name)).strip()
        if not alarm_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_alarm_id",
            )

        alarm = AlarmClock(
            alarm_id=alarm_id,
            name=alarm_name,
            alarm_time=str(call.data[ATTR_ALARM_TIME]),
            enabled=bool(call.data.get(ATTR_ENABLED, True)),
            target_entities=_coerce_str_list(call.data.get(ATTR_TARGET_ENTITIES)),
            target_services=_coerce_str_list(call.data.get(ATTR_TARGET_SERVICES)),
        )
        await runtime_data.manager.async_upsert_alarm(alarm)

    async def async_handle_update_alarm(call: ServiceCall) -> None:
        """Update an existing virtual alarm clock."""
        runtime_data = await _require_single_runtime()
        alarm_id = str(call.data[ATTR_ALARM_ID])

        existing_alarm = runtime_data.manager.async_get_alarm(alarm_id)
        if existing_alarm is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="alarm_not_found",
                translation_placeholders={"alarm_id": alarm_id},
            )

        alarm = AlarmClock(
            alarm_id=alarm_id,
            name=str(call.data.get(ATTR_ALARM_NAME, existing_alarm.name)).strip(),
            alarm_time=str(call.data.get(ATTR_ALARM_TIME, existing_alarm.alarm_time)),
            enabled=bool(call.data.get(ATTR_ENABLED, existing_alarm.enabled)),
            target_entities=_coerce_str_list(
                call.data.get(ATTR_TARGET_ENTITIES, existing_alarm.target_entities)
            ),
            target_services=_coerce_str_list(
                call.data.get(ATTR_TARGET_SERVICES, existing_alarm.target_services)
            ),
        )
        await runtime_data.manager.async_upsert_alarm(alarm)

    async def async_handle_delete_alarm(call: ServiceCall) -> None:
        """Delete a virtual alarm clock."""
        runtime_data = await _require_single_runtime()
        await runtime_data.manager.async_delete_alarm(str(call.data[ATTR_ALARM_ID]))

    async def async_handle_trigger_alarm(call: ServiceCall) -> None:
        """Trigger an alarm immediately."""
        runtime_data = await _require_single_runtime()
        await runtime_data.manager.async_trigger_alarm_now(str(call.data[ATTR_ALARM_ID]))

    if not hass.services.has_service(DOMAIN, "create_alarm"):
        hass.services.async_register(DOMAIN, "create_alarm", async_handle_create_alarm)

    if not hass.services.has_service(DOMAIN, "update_alarm"):
        hass.services.async_register(DOMAIN, "update_alarm", async_handle_update_alarm)

    if not hass.services.has_service(DOMAIN, "delete_alarm"):
        hass.services.async_register(DOMAIN, "delete_alarm", async_handle_delete_alarm)

    if not hass.services.has_service(DOMAIN, "trigger_alarm"):
        hass.services.async_register(DOMAIN, "trigger_alarm", async_handle_trigger_alarm)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ComposableAlarmConfigEntry) -> bool:
    """Set up Composable Alarm Clock from a config entry."""
    manager = AlarmClockManager(hass=hass, entry_id=entry.entry_id)
    await manager.async_initialize()

    entry.runtime_data = RuntimeData(manager=manager)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ComposableAlarmConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.manager.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ComposableAlarmConfigEntry) -> None:
    """Reload a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


def _coerce_str_list(value: Any) -> list[str]:
    """Convert service call input into a clean list of strings."""
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = value.split(",") if "," in value else [value]
        return [item.strip() for item in raw_items if item.strip()]

    if isinstance(value, Sequence):
        result: list[str] = []
        for item in value:
            item_str = str(item).strip()
            if item_str:
                result.append(item_str)
        return result

    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="invalid_list_input",
    )
