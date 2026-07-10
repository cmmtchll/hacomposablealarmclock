# Home Assistant Quality Scale Mapping

This document maps repository implementation to Home Assistant Quality Scale expectations.

## Tier summary

- Bronze: targeted and largely implemented.
- Silver: targeted and largely implemented.
- Gold: partially implemented, with exemptions documented.
- Platinum: targeted with strict typing and async dependency patterns.

## Key implemented patterns

- Config flow, unique IDs, and setup validation.
- Service-layer alarm validation with translated errors for invalid input and missing alarms.
- Action-based `alarm_manage` service for Devices and Services with dry-run validation.
- Flow-first options UX for alarm CRUD from the integration page.
- Runtime data in `ConfigEntry.runtime_data`.
- Config entry unload/reload behavior.
- Startup reconciliation removes stale per-alarm entities and devices that no longer exist in stored alarm configuration.
- Logging for availability transitions.
- Diagnostics with secret redaction.
- Repairs issue and fix flow for enabled alarms without any targets.
- Entity translation keys and icon translations.
- Async API dependency with injected websession.
- Strict type annotations in integration modules.

## Exemptions in current scaffold

- Discovery and discovery update flow.
- Brand assets are prepared locally and pending publication in `home-assistant/brands`.

## Dynamic device modeling evidence

- Each virtual alarm is represented as its own device with per-alarm entities (button, sensors, switch, and time entity).
- Registry reconciliation removes stale per-alarm entities and devices when alarms are deleted or no longer exist.
- Tests cover per-alarm entity creation, deletion cleanup, stale registry cleanup, and cross-entry scoping behavior.

See the authoritative status file:

- `custom_components/hacomposablealarmclock/quality_scale.yaml`
