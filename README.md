# Composable Alarm Clock Home Assistant Integration

Composable Alarm Clock creates virtual alarm-clock devices in Home Assistant.

Each virtual alarm has:

- A daily alarm time
- An enabled toggle
- Optional target entities and target services to activate when due

This is designed for "alarm panels" in Home Assistant dashboards (for example, kids rooms), while allowing parents to monitor whether alarms are set and enabled.

## What this repository includes

- Async integration code in `custom_components/hacomposablealarmclock`
- One integration entry that can host many virtual alarms
- Persistent storage + local scheduling for alarm due events
- Dynamic entities per alarm:
   - `switch` for enabled/disabled
   - `time` for alarm time
   - `button` for manual trigger-now
   - `sensor` for next due, last triggered, configuration, and status
- Workspace-level summary entity:
   - `sensor` for workspace overview (alarm count + compact alarm snapshot list)
- Service actions to create, update, delete, and trigger alarms
- Unified action-based service in Devices and Services: `hacomposablealarmclock.alarm_manage`
- Flow-first alarm management from integration options (add/edit/delete/clone/toggle)
- Event emission when alarms are due: `hacomposablealarmclock_alarm_triggered`
- Diagnostics output with stored alarm definitions
- Repairs issue + fix flow when enabled alarms have no targets
- Tests using `pytest-homeassistant-custom-component`

## Quick start

1. Clone this repository.
2. Create a Python virtual environment.
3. Install development dependencies:
   - `pip install -r requirements-dev.txt`
4. Run tests:
   - `pytest`
5. Run linting:
   - `ruff check .`
6. Run typing checks:
   - `mypy custom_components tests`

## Local Home Assistant testing

1. Create a Home Assistant test config directory, for example `./config`.
2. Copy `custom_components/hacomposablealarmclock` into your HA config under `config/custom_components/`.
3. Start Home Assistant.
4. Go to Settings -> Devices & services -> Add integration.
5. Add "Composable Alarm Clock" and complete setup.
6. Open the integration Options to manage alarms with guided forms.

## Service actions

- `hacomposablealarmclock.alarm_manage`
   - Unified action-based service for Devices and Services.
   - Actions: `create`, `update`, `upsert`, `delete`, `enable`, `disable`, `trigger_now`, `list`.
   - Optional `config_entry_id` targets a specific integration entry.
   - Supports `dry_run: true` to validate changes without persisting.

- `hacomposablealarmclock.create_alarm`
   - Creates or replaces one virtual alarm.
- `hacomposablealarmclock.update_alarm`
   - Updates an existing virtual alarm.
- `hacomposablealarmclock.delete_alarm`
   - Deletes a virtual alarm.
- `hacomposablealarmclock.trigger_alarm`
   - Triggers a virtual alarm immediately.

## Alarm trigger behavior

When an alarm is due (or manually triggered), the integration:

1. Fires event `hacomposablealarmclock_alarm_triggered`
2. Calls `homeassistant.turn_on` for configured target entities
3. Calls any configured target services (`domain.service`)

This lets you fan out to lights, speakers, scripts, scenes, and mobile notification services.

Service inputs are validated before alarms are stored or triggered:

- Alarm IDs and names must be non-empty.
- Alarm times must be valid daily times in `HH:MM` or `HH:MM:SS` format.
- Target services must use `domain.service` format.
- Update, delete, and trigger actions return a translated validation error when the alarm does not exist.

## Bronze/Silver/Gold/Platinum notes

Home Assistant requires all tier rules below the target tier to be met.

- Bronze: baseline UI setup, tests, docs, unique IDs.
- Silver: robust runtime behavior, reauth, unloading, ownership, high coverage.
- Gold: diagnostics, translation quality, reconfiguration, strong docs.
- Platinum: strict typing, async dependency model, injected websession.

This scaffold includes a practical implementation for many rules and records exemptions in:

- `custom_components/hacomposablealarmclock/quality_scale.yaml`
- `docs/QUALITY_SCALE.md`
- `branding/README.md`

## Known limitations in initial scaffold

- Discovery protocols are not yet implemented.
- Brand images are included locally but not yet published to `home-assistant/brands`.

## License

MIT
