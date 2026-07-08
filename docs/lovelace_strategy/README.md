# Custom Dashboard Strategy Setup

This strategy lets users create a Composable Alarm Clock dashboard from Home Assistant's Add dashboard dialog.

## Files

- `docs/lovelace_strategy/hacomposablealarmclock-dashboard-strategy.js`

## Install in Home Assistant

1. Copy `hacomposablealarmclock-dashboard-strategy.js` into your Home Assistant config directory:
   - Destination: `/config/www/hacomposablealarmclock-dashboard-strategy.js`
2. Restart Home Assistant or reload frontend resources.
3. Open Home Assistant:
   - Settings -> Dashboards
   - Top-right menu -> Resources
4. Add a module resource:
   - URL: `/local/hacomposablealarmclock-dashboard-strategy.js`
   - Type: `module`
5. Refresh browser (hard refresh recommended).

## Create a dashboard from the strategy

1. Go to Settings -> Dashboards.
2. Select Add dashboard.
3. Under Community dashboards, pick Composable Alarm Clock.
4. Confirm title/icon and create.

## What it generates

- Workspace markdown + workspace summary entities.
- Quick service action buttons:
  - list
  - dry-run list
- Per-alarm control cards (switch/time/button).
- Per-alarm telemetry cards (sensor entities).
- A trigger-now button for each alarm device.

## Notes

- If no alarm entities exist yet, the dashboard shows an instructional message.
- The strategy builds from current device/entity registry data each time the dashboard is generated.
- Guided CRUD remains in integration Options flow.
