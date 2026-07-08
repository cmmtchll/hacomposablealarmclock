"""Test fixtures for Composable Alarm Clock integration."""

from __future__ import annotations

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hacomposablealarmclock.const import DOMAIN


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Household Alarm Clocks",
        unique_id=DOMAIN,
        data={
            CONF_NAME: "Household Alarm Clocks",
        },
    )


@pytest.fixture
def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """Set up the integration from a config entry."""
    mock_config_entry.add_to_hass(hass)
    return mock_config_entry
