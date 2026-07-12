# ![Composable Alarm Clock](branding/logo.svg)

<div align="center">

[![Home Assistant Integration](branding/icon.svg)](https://www.home-assistant.io/)

*Flexible, composable virtual alarm management for Home Assistant*

</div>

---

## About

Composable Alarm Clock creates **virtual alarm-clock devices** in Home Assistant that users explicitly define. Rather than auto-discovering devices, this integration provides a centralized platform where you:

- Create and manage multiple alarms in one place
- Define alarm times, enabled states, and target actions
- Build automations and helpers around a consistent alarm entity structure
- Dynamically determine when to set the next alarm based on a unified alarm registry

Each virtual alarm has:

- A daily alarm time
- An enabled toggle
- Optional target entities and target services to activate when due

This is ideal for "alarm panels" in Home Assistant dashboards (for example, kids' rooms), while allowing parents to monitor whether alarms are set and enabled.

**Key benefit:** A unified alarm registry makes it simple to build helpers, automations, and logic around your alarms—all from a single, easy-to-query set of entities.

## Use Cases

- **Alarm management panels** for family members or guests
- **Automation helpers** that reference alarm state to determine next wake-up time
- **Dynamic scheduling** based on multiple alarm entities
- **Multi-target activation** (lights, speakers, notifications) when alarms trigger
- **Service-based alarm control** from scripts, automations, and dashboards

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
- Dynamic cleanup of remnant entities and devices

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

## Lovelace dashboard template

This repository includes a dashboard template at:

- `docs/LOVELACE_DASHBOARD.yaml`

What it includes:

- Flow-aligned alarm management controls using `hacomposablealarmclock.alarm_manage`
- Buttons for legacy services (`create_alarm`, `update_alarm`, `delete_alarm`, `trigger_alarm`)
- Visualization cards for workspace overview and per-alarm status/timeline

How to use:

1. Open Home Assistant and create a new dashboard (or edit an existing one in YAML mode).
2. Copy the contents of `docs/LOVELACE_DASHBOARD.yaml` into the dashboard YAML.
3. Replace each `REPLACE_...` entity placeholder with real entity IDs from Developer Tools -> States.
4. Update sample `alarm_id`, names, times, and targets to match your environment.

## Lovelace custom dashboard strategy

This repository also includes a custom dashboard strategy scaffold:

- `docs/lovelace_strategy/hacomposablealarmclock-dashboard-strategy.js`

This strategy can appear under Home Assistant's **Add dashboard** dialog (Community dashboards) once loaded as a frontend module resource.

Setup guide:

- `docs/lovelace_strategy/README.md`

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
   - Deletes a virtual alarm and removes its per-alarm entities and device.
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

On setup, the integration reconciles stored alarm definitions with Home Assistant's entity and device registries. Stale per-alarm entities or devices left behind by earlier versions or interruptions are automatically cleaned up.

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

Local branding directory layout is included in this repository under:

- `brands/custom_integrations/hacomposablealarmclock/`

To use local branding in Home Assistant before upstream publication, copy the repository `brands` folder into your Home Assistant config directory.

## Known limitations in initial scaffold

- Discovery protocols are not implemented (devices are user-created).
- Brand images are included locally and can be used via the local `brands` folder, but are not yet published to `home-assistant/brands`.

## License

MIT
