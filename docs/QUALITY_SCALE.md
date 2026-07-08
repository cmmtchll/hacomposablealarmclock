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
- Runtime data in `ConfigEntry.runtime_data`.
- Config entry unload/reload behavior.
- Logging for availability transitions.
- Diagnostics with secret redaction.
- Entity translation keys and icon translations.
- Async API dependency with injected websession.
- Strict type annotations in integration modules.

## Exemptions in current scaffold

- Discovery and discovery update flow.
- Brand assets are prepared locally and pending publication in `home-assistant/brands`.
- Repair flow.
- Some advanced lifecycle rules not relevant to a single-endpoint MVP.

See the authoritative status file:

- `custom_components/hacomposablealarmclock/quality_scale.yaml`
