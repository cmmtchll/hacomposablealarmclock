"""Config flow for Composable Alarm Clock."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TimeSelector,
    TimeSelectorConfig,
)

from .const import (
    ATTR_ALARM_ID,
    ATTR_ALARM_NAME,
    ATTR_ALARM_TIME,
    ATTR_ENABLED,
    ATTR_TARGET_ENTITIES,
    ATTR_TARGET_SERVICES,
    CONF_DEFAULT_TARGET_ENTITIES,
    CONF_DEFAULT_TARGET_SERVICES,
    DEFAULT_ENTRY_TITLE,
    DOMAIN,
)
from .manager import AlarmClock, AlarmValidationError


def _user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Build setup/reconfigure form schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME,
                default=defaults.get(CONF_NAME, DEFAULT_ENTRY_TITLE),
            ): TextSelector(
                TextSelectorConfig()
            ),
        }
    )


class ComposableAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Composable Alarm Clock."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            title = user_input[CONF_NAME].strip() or DEFAULT_ENTRY_TITLE
            return self.async_create_entry(
                title=title,
                data={CONF_NAME: title},
            )

        return self.async_show_form(step_id="user", data_schema=_user_schema())

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """No-op reauth flow for local-only integration."""
        del entry_data
        return self.async_abort(reason="reauth_not_supported")

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """No-op reauth flow for local-only integration."""
        del user_input
        return self.async_abort(reason="reauth_not_supported")

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a reconfiguration flow."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            title = user_input[CONF_NAME].strip() or DEFAULT_ENTRY_TITLE
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_mismatch()
            return self.async_update_and_abort(
                entry,
                data_updates={CONF_NAME: title},
                reason="reconfigure_successful",
            )

        defaults = {
            CONF_NAME: entry.data.get(CONF_NAME, entry.title or DEFAULT_ENTRY_TITLE),
        }

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(defaults),
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        del config_entry
        return ComposableAlarmOptionsFlow()


class ComposableAlarmOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Composable Alarm Clock."""

    def __init__(self) -> None:
        """Initialize options flow state."""
        self._operation: str | None = None
        self._selected_alarm_id: str | None = None

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose an options operation."""
        if user_input is not None:
            self._operation = str(user_input["operation"])
            if self._operation == "workspace_defaults":
                return await self.async_step_workspace_defaults()
            if self._operation == "add_alarm":
                return await self.async_step_add_alarm()
            if self._operation in {
                "edit_alarm",
                "delete_alarm",
                "clone_alarm",
                "toggle_alarm",
            }:
                if not self._alarm_options:
                    return self.async_abort(reason="no_alarms")
                return await self.async_step_select_alarm()
            return self.async_abort(reason="unknown_operation")

        schema = vol.Schema(
            {
                vol.Required("operation", default="add_alarm"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            "add_alarm",
                            "edit_alarm",
                            "delete_alarm",
                            "clone_alarm",
                            "toggle_alarm",
                            "workspace_defaults",
                        ],
                        translation_key="options_operation",
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_workspace_defaults(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage workspace default options."""
        if user_input is not None:
            user_input[CONF_DEFAULT_TARGET_SERVICES] = _coerce_list_input(
                user_input.get(CONF_DEFAULT_TARGET_SERVICES)
            )
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DEFAULT_TARGET_ENTITIES,
                    default=list(
                        self.config_entry.options.get(CONF_DEFAULT_TARGET_ENTITIES, [])
                    ),
                ): EntitySelector(EntitySelectorConfig(multiple=True)),
                vol.Optional(
                    CONF_DEFAULT_TARGET_SERVICES,
                    default=", ".join(
                        self.config_entry.options.get(CONF_DEFAULT_TARGET_SERVICES, [])
                    ),
                ): TextSelector(TextSelectorConfig()),
            }
        )

        return self.async_show_form(step_id="workspace_defaults", data_schema=schema)

    async def async_step_add_alarm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create a new alarm via options flow."""
        manager = self._manager
        if manager is None:
            return self.async_abort(reason="runtime_unavailable")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await manager.async_upsert_alarm(
                    AlarmClock(
                        alarm_id=(
                            str(user_input.get(ATTR_ALARM_ID, "")).strip()
                            or str(user_input[ATTR_ALARM_NAME])
                            .strip()
                            .lower()
                            .replace(" ", "_")
                        ),
                        name=str(user_input[ATTR_ALARM_NAME]).strip(),
                        alarm_time=str(user_input[ATTR_ALARM_TIME]),
                        enabled=bool(user_input.get(ATTR_ENABLED, True)),
                        target_entities=_coerce_list_input(
                            user_input.get(ATTR_TARGET_ENTITIES)
                        ),
                        target_services=_coerce_list_input(
                            user_input.get(ATTR_TARGET_SERVICES)
                        ),
                    )
                )
            except AlarmValidationError as err:
                errors["base"] = err.translation_key
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))

        schema = vol.Schema(
            {
                vol.Optional(ATTR_ALARM_ID): TextSelector(TextSelectorConfig()),
                vol.Required(ATTR_ALARM_NAME): TextSelector(TextSelectorConfig()),
                vol.Required(ATTR_ALARM_TIME): TimeSelector(TimeSelectorConfig()),
                vol.Required(ATTR_ENABLED, default=True): BooleanSelector(
                    BooleanSelectorConfig()
                ),
                vol.Optional(ATTR_TARGET_ENTITIES): EntitySelector(
                    EntitySelectorConfig(multiple=True)
                ),
                vol.Optional(ATTR_TARGET_SERVICES): TextSelector(TextSelectorConfig()),
            }
        )

        return self.async_show_form(
            step_id="add_alarm",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_select_alarm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select an alarm before a mutation operation."""
        if user_input is not None:
            self._selected_alarm_id = str(user_input[ATTR_ALARM_ID])
            if self._operation == "edit_alarm":
                return await self.async_step_edit_alarm()
            if self._operation == "delete_alarm":
                return await self.async_step_delete_alarm()
            if self._operation == "clone_alarm":
                return await self.async_step_clone_alarm()
            if self._operation == "toggle_alarm":
                return await self.async_step_toggle_alarm()
            return self.async_abort(reason="unknown_operation")

        schema = vol.Schema(
            {
                vol.Required(ATTR_ALARM_ID): SelectSelector(
                    SelectSelectorConfig(options=self._alarm_options)
                )
            }
        )
        return self.async_show_form(step_id="select_alarm", data_schema=schema)

    async def async_step_edit_alarm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit a selected alarm."""
        manager = self._manager
        alarm = self._selected_alarm
        if manager is None:
            return self.async_abort(reason="runtime_unavailable")
        if alarm is None:
            return self.async_abort(reason="alarm_not_found")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await manager.async_upsert_alarm(
                    AlarmClock(
                        alarm_id=alarm.alarm_id,
                        name=str(user_input[ATTR_ALARM_NAME]).strip(),
                        alarm_time=str(user_input[ATTR_ALARM_TIME]),
                        enabled=bool(user_input[ATTR_ENABLED]),
                        target_entities=_coerce_list_input(
                            user_input.get(ATTR_TARGET_ENTITIES)
                        ),
                        target_services=_coerce_list_input(
                            user_input.get(ATTR_TARGET_SERVICES)
                        ),
                        last_triggered_iso=alarm.last_triggered_iso,
                    )
                )
            except AlarmValidationError as err:
                errors["base"] = err.translation_key
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))

        schema = vol.Schema(
            {
                vol.Required(ATTR_ALARM_NAME, default=alarm.name): TextSelector(
                    TextSelectorConfig()
                ),
                vol.Required(ATTR_ALARM_TIME, default=alarm.alarm_time): TimeSelector(
                    TimeSelectorConfig()
                ),
                vol.Required(ATTR_ENABLED, default=alarm.enabled): BooleanSelector(
                    BooleanSelectorConfig()
                ),
                vol.Optional(
                    ATTR_TARGET_ENTITIES,
                    default=list(alarm.target_entities),
                ): EntitySelector(EntitySelectorConfig(multiple=True)),
                vol.Optional(
                    ATTR_TARGET_SERVICES,
                    default=", ".join(alarm.target_services),
                ): TextSelector(TextSelectorConfig()),
            }
        )
        return self.async_show_form(
            step_id="edit_alarm",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_delete_alarm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Delete a selected alarm."""
        manager = self._manager
        alarm = self._selected_alarm
        if manager is None:
            return self.async_abort(reason="runtime_unavailable")
        if alarm is None:
            return self.async_abort(reason="alarm_not_found")

        if user_input is not None:
            if not bool(user_input.get("confirm")):
                return self.async_show_form(
                    step_id="delete_alarm",
                    data_schema=vol.Schema(
                        {
                            vol.Required("confirm", default=False): BooleanSelector(
                                BooleanSelectorConfig()
                            )
                        }
                    ),
                    errors={"base": "confirm_required"},
                )
            await manager.async_delete_alarm(alarm.alarm_id)
            return self.async_create_entry(data=dict(self.config_entry.options))

        schema = vol.Schema(
            {
                vol.Required("confirm", default=False): BooleanSelector(
                    BooleanSelectorConfig()
                )
            }
        )
        return self.async_show_form(step_id="delete_alarm", data_schema=schema)

    async def async_step_clone_alarm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Clone a selected alarm to a new alarm ID."""
        manager = self._manager
        alarm = self._selected_alarm
        if manager is None:
            return self.async_abort(reason="runtime_unavailable")
        if alarm is None:
            return self.async_abort(reason="alarm_not_found")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await manager.async_upsert_alarm(
                    AlarmClock(
                        alarm_id=str(user_input[ATTR_ALARM_ID]).strip(),
                        name=str(user_input[ATTR_ALARM_NAME]).strip(),
                        alarm_time=str(user_input[ATTR_ALARM_TIME]),
                        enabled=bool(user_input[ATTR_ENABLED]),
                        target_entities=_coerce_list_input(
                            user_input.get(ATTR_TARGET_ENTITIES)
                        ),
                        target_services=_coerce_list_input(
                            user_input.get(ATTR_TARGET_SERVICES)
                        ),
                    )
                )
            except AlarmValidationError as err:
                errors["base"] = err.translation_key
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))

        schema = vol.Schema(
            {
                vol.Required(
                    ATTR_ALARM_ID,
                    default=f"{alarm.alarm_id}_copy",
                ): TextSelector(TextSelectorConfig()),
                vol.Required(
                    ATTR_ALARM_NAME,
                    default=f"{alarm.name} Copy",
                ): TextSelector(
                    TextSelectorConfig()
                ),
                vol.Required(ATTR_ALARM_TIME, default=alarm.alarm_time): TimeSelector(
                    TimeSelectorConfig()
                ),
                vol.Required(ATTR_ENABLED, default=alarm.enabled): BooleanSelector(
                    BooleanSelectorConfig()
                ),
                vol.Optional(
                    ATTR_TARGET_ENTITIES,
                    default=list(alarm.target_entities),
                ): EntitySelector(EntitySelectorConfig(multiple=True)),
                vol.Optional(
                    ATTR_TARGET_SERVICES,
                    default=", ".join(alarm.target_services),
                ): TextSelector(TextSelectorConfig()),
            }
        )
        return self.async_show_form(
            step_id="clone_alarm",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_toggle_alarm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Toggle enabled state for a selected alarm."""
        manager = self._manager
        alarm = self._selected_alarm
        if manager is None:
            return self.async_abort(reason="runtime_unavailable")
        if alarm is None:
            return self.async_abort(reason="alarm_not_found")

        if user_input is not None:
            await manager.async_set_enabled(
                alarm.alarm_id,
                bool(user_input[ATTR_ENABLED]),
            )
            return self.async_create_entry(data=dict(self.config_entry.options))

        schema = vol.Schema(
            {
                vol.Required(ATTR_ENABLED, default=alarm.enabled): BooleanSelector(
                    BooleanSelectorConfig()
                )
            }
        )
        return self.async_show_form(step_id="toggle_alarm", data_schema=schema)

    @property
    def _manager(self):
        """Return runtime manager for this config entry when available."""
        runtime_by_entry = self.hass.data.get(DOMAIN, {})
        runtime_data = runtime_by_entry.get(self.config_entry.entry_id)
        return None if runtime_data is None else runtime_data.manager

    @property
    def _alarm_options(self) -> list[str]:
        """Return alarm IDs available for selection."""
        manager = self._manager
        if manager is None:
            return []
        return sorted(alarm.alarm_id for alarm in manager.async_list_alarms())

    @property
    def _selected_alarm(self) -> AlarmClock | None:
        """Return currently selected alarm object."""
        if self._selected_alarm_id is None:
            return None
        manager = self._manager
        if manager is None:
            return None
        return manager.async_get_alarm(self._selected_alarm_id)


def _coerce_list_input(value: Any) -> list[str]:
    """Normalize text or sequence values into a list of non-empty strings."""
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = value.split(",") if "," in value else [value]
        return [item.strip() for item in raw_items if item.strip()]

    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]

    return [str(value).strip()] if str(value).strip() else []
