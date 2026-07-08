"""Config flow for Composable Alarm Clock."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_DEFAULT_TARGET_ENTITIES,
    CONF_DEFAULT_TARGET_SERVICES,
    DEFAULT_ENTRY_TITLE,
    DOMAIN,
)


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

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
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
            return self.async_update_reload_and_abort(
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
        return ComposableAlarmOptionsFlow(config_entry)


class ComposableAlarmOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Composable Alarm Clock."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage integration options."""
        if user_input is not None:
            user_input[CONF_DEFAULT_TARGET_SERVICES] = [
                service.strip()
                for service in str(user_input.get(CONF_DEFAULT_TARGET_SERVICES, "")).split(","
                )
                if service.strip()
            ]
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_DEFAULT_TARGET_ENTITIES): EntitySelector(
                    EntitySelectorConfig(multiple=True)
                ),
                vol.Optional(
                    CONF_DEFAULT_TARGET_SERVICES,
                    default=", ".join(
                        self.config_entry.options.get(CONF_DEFAULT_TARGET_SERVICES, [])
                    ),
                ): TextSelector(TextSelectorConfig()),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
