"""The Composable Alarm Clock integration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, NoReturn

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_platform,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers import (
    issue_registry as ir,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.service import ServiceValidationError
from homeassistant.util import slugify

from .const import (
    ATTR_ACTION,
    ATTR_ALARM_ID,
    ATTR_ALARM_NAME,
    ATTR_ALARM_TIME,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DRY_RUN,
    ATTR_ENABLED,
    ATTR_TARGET_ENTITIES,
    ATTR_TARGET_SERVICES,
    DOMAIN,
    ISSUE_ALARMS_WITHOUT_TARGETS,
    PLATFORMS,
    SIGNAL_ALARM_CHANGED,
    SIGNAL_ALARM_REMOVED,
    RuntimeData,
)
from .manager import AlarmClock, AlarmClockManager, AlarmValidationError

type ComposableAlarmConfigEntry = ConfigEntry[RuntimeData]

_ALARM_ENTITY_UNIQUE_ID_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("button", "trigger_now"),
    ("sensor", "next_due"),
    ("sensor", "last_triggered"),
    ("sensor", "configuration"),
    ("sensor", "status"),
    ("switch", "enabled"),
    ("time", "alarm_time"),
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration via YAML (unused) and shared services."""
    del config
    supported_actions = {
        "create",
        "update",
        "upsert",
        "delete",
        "enable",
        "disable",
        "trigger_now",
        "list",
    }

    def _raise_service_validation_error(error: AlarmValidationError) -> NoReturn:
        """Convert manager validation errors to translated service errors."""
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key=error.translation_key,
            translation_placeholders=error.translation_placeholders,
        ) from error

    def _require_alarm_id(value: Any) -> str:
        """Normalize and validate an alarm ID from service input."""
        alarm_id = str(value).strip()
        if not alarm_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_alarm_id",
            )
        return alarm_id

    async def _require_runtime(call_data: dict[str, Any]) -> RuntimeData:
        config_entry_id = call_data.get(ATTR_CONFIG_ENTRY_ID)
        return _resolve_runtime_data(hass, config_entry_id)

    async def _handle_alarm_manage(call_data: dict[str, Any]) -> dict[str, Any]:
        """Execute action-based alarm management."""
        runtime_data = await _require_runtime(call_data)

        action = str(call_data.get(ATTR_ACTION, "")).strip().lower()
        if action not in supported_actions:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_action",
                translation_placeholders={"action": action or "<empty>"},
            )

        dry_run = bool(call_data.get(ATTR_DRY_RUN, False))

        if action == "list":
            alarms = [
                _alarm_to_dict(alarm)
                for alarm in runtime_data.manager.async_list_alarms()
            ]
            return {
                "ok": True,
                "action": action,
                "dry_run": dry_run,
                "changed": False,
                "alarms": alarms,
                "count": len(alarms),
            }

        if action in {"delete", "enable", "disable", "trigger_now", "update", "upsert"}:
            alarm_id = _require_alarm_id(call_data.get(ATTR_ALARM_ID))
            existing_alarm = runtime_data.manager.async_get_alarm(alarm_id)
        else:
            alarm_id = _require_alarm_id(
                call_data.get(ATTR_ALARM_ID)
                or slugify(str(call_data.get(ATTR_ALARM_NAME, "")))
            )
            existing_alarm = runtime_data.manager.async_get_alarm(alarm_id)

        if action == "delete":
            if existing_alarm is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="alarm_not_found",
                    translation_placeholders={"alarm_id": alarm_id},
                )
            if not dry_run:
                await runtime_data.manager.async_delete_alarm(alarm_id)
            return {
                "ok": True,
                "action": action,
                "dry_run": dry_run,
                "changed": not dry_run,
                "alarm_id": alarm_id,
            }

        if action in {"enable", "disable"}:
            if existing_alarm is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="alarm_not_found",
                    translation_placeholders={"alarm_id": alarm_id},
                )
            enabled_value = action == "enable"
            if not dry_run:
                await runtime_data.manager.async_set_enabled(alarm_id, enabled_value)
            return {
                "ok": True,
                "action": action,
                "dry_run": dry_run,
                "changed": not dry_run,
                "alarm_id": alarm_id,
                "enabled": enabled_value,
            }

        if action == "trigger_now":
            if existing_alarm is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="alarm_not_found",
                    translation_placeholders={"alarm_id": alarm_id},
                )
            if not dry_run:
                await runtime_data.manager.async_trigger_alarm_now(alarm_id)
            return {
                "ok": True,
                "action": action,
                "dry_run": dry_run,
                "changed": not dry_run,
                "alarm_id": alarm_id,
            }

        if action == "create":
            alarm_name = str(call_data.get(ATTR_ALARM_NAME, "")).strip()
            alarm_time = str(call_data.get(ATTR_ALARM_TIME, "")).strip()
            if not alarm_name:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_alarm_name",
                )
            if not alarm_time:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_alarm_time",
                )

            alarm = AlarmClock(
                alarm_id=alarm_id,
                name=alarm_name,
                alarm_time=alarm_time,
                enabled=bool(call_data.get(ATTR_ENABLED, True)),
                target_entities=_coerce_str_list(call_data.get(ATTR_TARGET_ENTITIES)),
                target_services=_coerce_str_list(call_data.get(ATTR_TARGET_SERVICES)),
            )
            try:
                if not dry_run:
                    await runtime_data.manager.async_upsert_alarm(alarm)
            except AlarmValidationError as err:
                _raise_service_validation_error(err)

            return {
                "ok": True,
                "action": action,
                "dry_run": dry_run,
                "changed": not dry_run,
                "alarm": _alarm_to_dict(alarm),
            }

        if existing_alarm is None and action == "update":
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="alarm_not_found",
                translation_placeholders={"alarm_id": alarm_id},
            )

        if action in {"update", "upsert"}:
            has_mutation_fields = any(
                key in call_data
                for key in (
                    ATTR_ALARM_NAME,
                    ATTR_ALARM_TIME,
                    ATTR_ENABLED,
                    ATTR_TARGET_ENTITIES,
                    ATTR_TARGET_SERVICES,
                )
            )
            if not has_mutation_fields and action == "update":
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="no_update_fields",
                )

            if existing_alarm is None:
                alarm_name = str(call_data.get(ATTR_ALARM_NAME, "")).strip()
                alarm_time = str(call_data.get(ATTR_ALARM_TIME, "")).strip()
                if not alarm_name:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="invalid_alarm_name",
                    )
                if not alarm_time:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="invalid_alarm_time",
                    )

                alarm = AlarmClock(
                    alarm_id=alarm_id,
                    name=alarm_name,
                    alarm_time=alarm_time,
                    enabled=bool(call_data.get(ATTR_ENABLED, True)),
                    target_entities=_coerce_str_list(call_data.get(ATTR_TARGET_ENTITIES)),
                    target_services=_coerce_str_list(call_data.get(ATTR_TARGET_SERVICES)),
                )
            else:
                alarm = AlarmClock(
                    alarm_id=alarm_id,
                    name=(
                        str(call_data[ATTR_ALARM_NAME]).strip()
                        if ATTR_ALARM_NAME in call_data
                        else existing_alarm.name
                    ),
                    alarm_time=(
                        str(call_data[ATTR_ALARM_TIME])
                        if ATTR_ALARM_TIME in call_data
                        else existing_alarm.alarm_time
                    ),
                    enabled=(
                        bool(call_data[ATTR_ENABLED])
                        if ATTR_ENABLED in call_data
                        else existing_alarm.enabled
                    ),
                    target_entities=(
                        _coerce_str_list(call_data.get(ATTR_TARGET_ENTITIES))
                        if ATTR_TARGET_ENTITIES in call_data
                        else existing_alarm.target_entities
                    ),
                    target_services=(
                        _coerce_str_list(call_data.get(ATTR_TARGET_SERVICES))
                        if ATTR_TARGET_SERVICES in call_data
                        else existing_alarm.target_services
                    ),
                    last_triggered_iso=existing_alarm.last_triggered_iso,
                )

            try:
                if not dry_run:
                    await runtime_data.manager.async_upsert_alarm(alarm)
            except AlarmValidationError as err:
                _raise_service_validation_error(err)

            return {
                "ok": True,
                "action": action,
                "dry_run": dry_run,
                "changed": not dry_run,
                "alarm": _alarm_to_dict(alarm),
            }

        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_action",
            translation_placeholders={"action": action},
        )

    async def async_handle_alarm_manage(call: ServiceCall) -> dict[str, Any]:
        """Handle action-based alarm management."""
        return await _handle_alarm_manage(dict(call.data))

    async def async_handle_create_alarm(call: ServiceCall) -> None:
        """Create or replace a virtual alarm clock."""
        payload = dict(call.data)
        payload[ATTR_ACTION] = "create"
        payload[ATTR_DRY_RUN] = False
        await _handle_alarm_manage(payload)

    async def async_handle_update_alarm(call: ServiceCall) -> None:
        """Update an existing virtual alarm clock."""
        payload = dict(call.data)
        payload[ATTR_ACTION] = "update"
        payload[ATTR_DRY_RUN] = False
        await _handle_alarm_manage(payload)

    async def async_handle_delete_alarm(call: ServiceCall) -> None:
        """Delete a virtual alarm clock."""
        payload = dict(call.data)
        payload[ATTR_ACTION] = "delete"
        payload[ATTR_DRY_RUN] = False
        await _handle_alarm_manage(payload)

    async def async_handle_trigger_alarm(call: ServiceCall) -> None:
        """Trigger an alarm immediately."""
        payload = dict(call.data)
        payload[ATTR_ACTION] = "trigger_now"
        payload[ATTR_DRY_RUN] = False
        await _handle_alarm_manage(payload)

    if not hass.services.has_service(DOMAIN, "alarm_manage"):
        hass.services.async_register(
            DOMAIN,
            "alarm_manage",
            async_handle_alarm_manage,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, "create_alarm"):
        hass.services.async_register(DOMAIN, "create_alarm", async_handle_create_alarm)

    if not hass.services.has_service(DOMAIN, "update_alarm"):
        hass.services.async_register(DOMAIN, "update_alarm", async_handle_update_alarm)

    if not hass.services.has_service(DOMAIN, "delete_alarm"):
        hass.services.async_register(DOMAIN, "delete_alarm", async_handle_delete_alarm)

    if not hass.services.has_service(DOMAIN, "trigger_alarm"):
        hass.services.async_register(
            DOMAIN,
            "trigger_alarm",
            async_handle_trigger_alarm,
        )

    async def _sync_repairs_on_alarm_change(_alarm_id: str) -> None:
        await _async_sync_repairs_issues(hass)

    async def _sync_removed_alarm(alarm_id: str) -> None:
        await _async_sync_repairs_issues(hass)
        await _async_reconcile_alarm_registries(hass, removed_alarm_id=alarm_id)

    if not hass.data.get(f"{DOMAIN}_repairs_dispatcher_setup"):
        unsub_changed = async_dispatcher_connect(
            hass,
            SIGNAL_ALARM_CHANGED,
            lambda alarm_id: hass.add_job(_sync_repairs_on_alarm_change, alarm_id),
        )
        unsub_removed = async_dispatcher_connect(
            hass,
            SIGNAL_ALARM_REMOVED,
            lambda alarm_id: hass.add_job(_sync_removed_alarm, alarm_id),
        )
        hass.data[f"{DOMAIN}_repairs_dispatcher_setup"] = [unsub_changed, unsub_removed]

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComposableAlarmConfigEntry,
) -> bool:
    """Set up Composable Alarm Clock from a config entry."""
    manager = AlarmClockManager(hass=hass, entry_id=entry.entry_id)
    await manager.async_initialize()

    entry.runtime_data = RuntimeData(manager=manager)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await _async_reconcile_alarm_registries(hass, entry_id=entry.entry_id)
    await _async_sync_repairs_issues(hass)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ComposableAlarmConfigEntry,
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.manager.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
        await _async_sync_repairs_issues(hass)
    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ComposableAlarmConfigEntry,
) -> None:
    """Reload a config entry."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def _async_reconcile_alarm_registries(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
    removed_alarm_id: str | None = None,
) -> None:
    """Remove stale per-alarm entities and devices from Home Assistant registries."""
    runtime_data_by_entry = hass.data.get(DOMAIN, {})
    entity_registry = er.async_get(hass)

    entry_ids = [entry_id] if entry_id is not None else list(runtime_data_by_entry)
    stale_alarm_ids: set[str] = set()

    for current_entry_id in entry_ids:
        runtime_data = runtime_data_by_entry.get(current_entry_id)
        if runtime_data is None:
            continue

        live_alarm_ids = {
            alarm.alarm_id for alarm in runtime_data.manager.async_list_alarms()
        }
        candidate_alarm_ids = (
            {removed_alarm_id}
            if removed_alarm_id is not None
            else _registered_alarm_ids_for_entry(entity_registry, current_entry_id)
        )

        for alarm_id in candidate_alarm_ids - live_alarm_ids:
            stale_alarm_ids.add(alarm_id)
            for entity_domain, suffix in _ALARM_ENTITY_UNIQUE_ID_SUFFIXES:
                entity_id = entity_registry.async_get_entity_id(
                    entity_domain,
                    DOMAIN,
                    f"{current_entry_id}_{alarm_id}_{suffix}",
                )
                if entity_id is None:
                    continue
                await _async_remove_live_entity(hass, entity_id)
                entity_registry.async_remove(entity_id)

    device_registry = dr.async_get(hass)
    for alarm_id in stale_alarm_ids:
        if any(
            runtime_data.manager.async_get_alarm(alarm_id) is not None
            for runtime_data in runtime_data_by_entry.values()
        ):
            continue

        device = device_registry.async_get_device(identifiers={(DOMAIN, alarm_id)})
        if device is not None and not er.async_entries_for_device(
            entity_registry,
            device.id,
        ):
            device_registry.async_remove_device(device.id)


def _registered_alarm_ids_for_entry(
    entity_registry: er.EntityRegistry,
    entry_id: str,
) -> set[str]:
    """Return alarm IDs represented by this config entry's entity registry rows."""
    alarm_ids: set[str] = set()
    prefix = f"{entry_id}_"

    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry_id):
        if entity_entry.platform != DOMAIN or not entity_entry.unique_id.startswith(
            prefix
        ):
            continue
        alarm_id = _alarm_id_from_unique_id(entity_entry.unique_id, entry_id)
        if alarm_id is not None:
            alarm_ids.add(alarm_id)

    return alarm_ids


def _alarm_id_from_unique_id(unique_id: str, entry_id: str) -> str | None:
    """Extract an alarm ID from a per-alarm entity unique ID."""
    prefix = f"{entry_id}_"
    if not unique_id.startswith(prefix):
        return None

    alarm_id_with_suffix = unique_id.removeprefix(prefix)
    for _entity_domain, suffix in _ALARM_ENTITY_UNIQUE_ID_SUFFIXES:
        suffix_marker = f"_{suffix}"
        if alarm_id_with_suffix.endswith(suffix_marker):
            return alarm_id_with_suffix[: -len(suffix_marker)]
    return None


async def _async_remove_live_entity(hass: HomeAssistant, entity_id: str) -> None:
    """Remove an active entity from its loaded platform before registry cleanup."""
    for platform in entity_platform.async_get_platforms(hass, DOMAIN):
        if entity_id not in platform.entities:
            continue
        await platform.async_remove_entity(entity_id)
        return


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


def _alarm_to_dict(alarm: AlarmClock) -> dict[str, Any]:
    """Serialize one alarm for service responses."""
    return {
        ATTR_ALARM_ID: alarm.alarm_id,
        ATTR_ALARM_NAME: alarm.name,
        ATTR_ALARM_TIME: alarm.alarm_time,
        ATTR_ENABLED: alarm.enabled,
        ATTR_TARGET_ENTITIES: list(alarm.target_entities),
        ATTR_TARGET_SERVICES: list(alarm.target_services),
        "last_triggered_iso": alarm.last_triggered_iso,
    }


def _resolve_runtime_data(
    hass: HomeAssistant,
    config_entry_id: Any | None,
) -> RuntimeData:
    """Resolve runtime data from config entry ID or single configured entry."""
    entries: dict[str, RuntimeData] = hass.data.get(DOMAIN, {})
    runtime_entries = {
        entry_id: runtime_data
        for entry_id, runtime_data in entries.items()
        if isinstance(runtime_data, RuntimeData)
    }
    if not runtime_entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="integration_not_configured",
        )

    if config_entry_id is None:
        if len(runtime_entries) == 1:
            return next(iter(runtime_entries.values()))
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_id_required",
        )

    entry_id = str(config_entry_id).strip()
    if not entry_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_config_entry_id",
        )

    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_found",
            translation_placeholders={"entry_id": entry_id},
        )

    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_loaded",
            translation_placeholders={"entry_id": entry_id},
        )

    runtime_data = runtime_entries.get(entry_id)
    if runtime_data is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_loaded",
            translation_placeholders={"entry_id": entry_id},
        )
    return runtime_data


async def _async_sync_repairs_issues(hass: HomeAssistant) -> None:
    """Create or clear actionable repair issues based on runtime alarm state."""
    runtime_entries = hass.data.get(DOMAIN, {})
    alarms_without_targets: list[str] = []

    for entry_id, runtime_data in runtime_entries.items():
        if not isinstance(runtime_data, RuntimeData):
            continue
        for alarm in runtime_data.manager.async_list_alarms():
            if (
                alarm.enabled
                and not alarm.target_entities
                and not alarm.target_services
            ):
                alarms_without_targets.append(f"{entry_id}:{alarm.alarm_id}")

    if alarms_without_targets:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ALARMS_WITHOUT_TARGETS,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_ALARMS_WITHOUT_TARGETS,
            translation_placeholders={"count": str(len(alarms_without_targets))},
            data={"alarms": alarms_without_targets},
        )
        return

    ir.async_delete_issue(hass, DOMAIN, ISSUE_ALARMS_WITHOUT_TARGETS)
