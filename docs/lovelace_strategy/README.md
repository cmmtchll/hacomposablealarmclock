# Custom Dashboard Strategy Setup

This strategy lets users create a Composable Alarm Clock dashboard from Home Assistant's Add dashboard dialog.

## Files

- `docs/lovelace_strategy/hacomposablealarmclock-dashboard-strategy.js` — Full management dashboard (workspace summary, CRUD buttons, per-alarm entity cards).
- `docs/lovelace_strategy/hacomposablealarmclock-clockface-strategy.js` — Single-device clock face display (prominent time, day/date, alarm enabled state and alarm time).

## Install in Home Assistant

1. Copy the desired strategy file(s) into your Home Assistant config directory:
   - `hacomposablealarmclock-dashboard-strategy.js` → `/config/www/hacomposablealarmclock-dashboard-strategy.js`
   - `hacomposablealarmclock-clockface-strategy.js` → `/config/www/hacomposablealarmclock-clockface-strategy.js`
2. Restart Home Assistant or reload frontend resources.
3. Open Home Assistant:
   - Settings -> Dashboards
   - Top-right menu -> Resources
4. Add a module resource for each file you copied:
   - URL: `/local/hacomposablealarmclock-dashboard-strategy.js` — Type: `module`
   - URL: `/local/hacomposablealarmclock-clockface-strategy.js` — Type: `module`
5. Refresh browser (hard refresh recommended).

## Create a dashboard from the strategy

1. Go to Settings -> Dashboards.
2. Select Add dashboard.
3. Under Community dashboards, pick the desired strategy:
   - **Composable Alarm Clock** — full management view
   - **Composable Alarm Clock — Clock Face** — dedicated alarm clock display
4. Confirm title/icon and create.

## What the management dashboard generates (`hacomposablealarmclock-dashboard-strategy.js`)

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

## What the clock face dashboard generates (`hacomposablealarmclock-clockface-strategy.js`)

- Prominent live clock — large `HH:MM` display using HA Jinja2 `now()` (auto-refreshes every ~60 s).
- Day and date sub-header — weekday name and full date beneath the clock.
- Per-alarm status section — for each configured alarm:
   - **Enabled** tile card (tap to toggle on/off)
   - **Alarm time** tile card (tap for detail/edit)

Designed to be used on a dedicated wall-mounted tablet or phone running the HA Companion App in kiosk mode.

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
