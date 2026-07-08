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
- Quick management buttons:
   - Open Integrations
   - Open Devices
   - List alarms
   - Add sample alarm
   - Enable sample
   - Disable sample
   - Trigger sample
   - Delete sample
- One simple card per alarm device with only:
   - Enabled/disabled switch
   - Alarm time entity
   - Alarm name as the card title

## Notes

- If no alarm entities exist yet, the dashboard shows an instructional message.
- The strategy builds from current device/entity registry data each time the dashboard is generated.
- Guided CRUD remains in integration Options flow.

## Adding your own dashboard modify/add actions

You can customize the generated strategy file and add buttons for your own actions.

Examples in `generate()`:
- Use a button with `action: "perform-action"` and `perform_action: "hacomposablealarmclock.alarm_manage"`.
- Set `data.action` to `create`, `update`, `upsert`, `enable`, or `disable`.
- Use fixed sample values for fast operations from the dashboard.

Tip: if you need fully guided create/update (free-form fields), keep using Integration Options because Lovelace buttons do not prompt for full form input.
