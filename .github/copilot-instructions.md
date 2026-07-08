# Copilot Instructions For This Repo

## Scope

These instructions apply to the entire repository.

## Integration architecture

- Domain: `hacomposablealarmclock`
- Use `AlarmClockManager` in `manager.py` for storage, scheduling, and trigger dispatch.
- Keep entity classes thin; entities read/write manager state only.
- Model each virtual alarm as a device with switch/time/sensor entities.

## Required checks for code changes

- `pytest`
- `ruff check .`
- `mypy custom_components tests`

## Required update files when behavior changes

- `README.md`
- `docs/QUALITY_SCALE.md`
- `custom_components/hacomposablealarmclock/quality_scale.yaml`
- Tests under `tests/`

## Quality scale policy

- Prefer implementing a rule over exempting it.
- If exempting a rule, document a concrete technical reason.
- Never mark a rule as done without matching code and test evidence.
