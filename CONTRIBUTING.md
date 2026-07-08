# Contributing

## Development setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements-dev.txt`
3. Run tests and quality checks:
   - `pytest`
   - `ruff check .`
   - `mypy custom_components tests`

## Pull request expectations

- Keep changes typed and asynchronous.
- Add or update tests for behavior changes.
- Update documentation and `quality_scale.yaml` when rules are implemented or exempted.
- Keep user-facing text translatable via `strings.json`.

## Home Assistant quality scale workflow

When implementing a rule:

1. Add code and tests.
2. Document behavior in README and docs files.
3. Mark the rule status in `custom_components/hacomposablealarmclock/quality_scale.yaml`.
4. If exempt, include a short, concrete reason.
