# Testing

## Test stack

- `pytest-homeassistant-custom-component`
- `pytest-cov`

## Run tests

- `pytest`

## Focus areas

- Config flow success and failure paths.
- Integration setup and unload behavior.
- Sensor entity creation and expected state presence.
- Diagnostics redaction.

## Additional checks

- `ruff check .`
- `mypy custom_components tests`

## Coverage target

Target at least 95% integration module coverage for Silver quality guidance.
