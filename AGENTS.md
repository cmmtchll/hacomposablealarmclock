# Agent Instructions

This file defines practical guidelines for coding agents working in this repository.

## Primary objective

Maintain a Home Assistant custom integration that targets Platinum-tier engineering practices while clearly tracking exemptions.

## Coding standards

- Use async APIs only; avoid blocking I/O.
- Keep type annotations complete in integration modules.
- Prefer shared helper modules for repeated patterns.
- Keep Home Assistant lifecycle behavior correct (`async_setup`, `async_setup_entry`, unload/reload).

## Quality standards

- New behavior requires tests.
- Keep diagnostics output redacted for secrets.
- Ensure entities have stable unique IDs.
- Store runtime objects in `ConfigEntry.runtime_data`.

## Documentation standards

- Update README for user-visible changes.
- Update `docs/QUALITY_SCALE.md` and `quality_scale.yaml` for rule status changes.
- Add troubleshooting guidance for failures that users can act on.

## Editing policy for agents

- Keep commits and diffs focused.
- Do not change unrelated files.
- Prefer explicit exceptions over silent failures.
- Use concise comments for non-obvious logic.
