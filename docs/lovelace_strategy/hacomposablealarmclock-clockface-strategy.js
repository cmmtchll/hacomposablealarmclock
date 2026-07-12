/**
 * Composable Alarm Clock — Clock Face Dashboard Strategy
 *
 * Generates a single-device alarm clock display with:
 *   - Prominent live clock (HH:MM, auto-updates every minute via HA Jinja2 now())
 *   - Day and date sub-header
 *   - Per-alarm status: enabled/disabled toggle and alarm time
 *
 * Register this file as a Lovelace resource (module) and select
 * "Composable Alarm Clock — Clock Face" when adding a new dashboard.
 */
class HACACClockFaceStrategy extends HTMLElement {
  static getCreateSuggestions() {
    return {
      title: "Alarm Clock Face",
      icon: "mdi:clock-digital",
    };
  }

  static noEditor = true;

  static async generate(config, hass) {
    const domain = "hacomposablealarmclock";

    const [devices, entities] = await Promise.all([
      hass.callWS({ type: "config/device_registry/list" }),
      hass.callWS({ type: "config/entity_registry/list" }),
    ]);

    const integrationDevices = devices.filter((device) => {
      if (!Array.isArray(device.identifiers)) {
        return false;
      }
      return device.identifiers.some(
        (identifier) => Array.isArray(identifier) && identifier[0] === domain
      );
    });

    const deviceIds = new Set(integrationDevices.map((device) => device.id));

    const integrationEntities = entities.filter((entity) => {
      if (entity.disabled_by || entity.hidden_by) {
        return false;
      }
      return deviceIds.has(entity.device_id);
    });

    const alarmDevices = integrationDevices
      .filter((device) => !String(device.name || "").toLowerCase().includes("workspace"))
      .sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));

    // ── Clock + date card ────────────────────────────────────────────────────
    // Uses HA Jinja2 now() which re-evaluates every ~60 s in markdown cards.
    const clockCard = {
      type: "markdown",
      content: [
        "<div style=\"text-align:center; padding: 1.5em 0 0.5em\">",
        "  <div style=\"font-size:5.5em; font-weight:300; letter-spacing:0.05em; line-height:1; font-family:monospace\">",
        "    {{ now().strftime('%H:%M') }}",
        "  </div>",
        "  <div style=\"font-size:1.6em; font-weight:400; margin-top:0.5em; color:var(--secondary-text-color)\">",
        "    {{ now().strftime('%A') }}",
        "  </div>",
        "  <div style=\"font-size:1.1em; margin-top:0.15em; color:var(--disabled-text-color)\">",
        "    {{ now().strftime('%B %-d, %Y') }}",
        "  </div>",
        "</div>",
      ].join("\n"),
    };

    // ── Per-alarm status cards ───────────────────────────────────────────────
    const alarmSections = [];

    for (const device of alarmDevices) {
      const deviceEntityIds = integrationEntities
        .filter((entity) => entity.device_id === device.id)
        .map((entity) => entity.entity_id)
        .sort();

      const switchId = deviceEntityIds.find((id) => id.startsWith("switch."));
      const timeId = deviceEntityIds.find((id) => id.startsWith("time."));

      if (!switchId && !timeId) {
        continue;
      }

      const rowCards = [];

      if (switchId) {
        rowCards.push({
          type: "tile",
          entity: switchId,
          name: "Enabled",
          icon: "mdi:alarm",
          tap_action: { action: "toggle" },
        });
      }

      if (timeId) {
        rowCards.push({
          type: "tile",
          entity: timeId,
          name: "Alarm time",
          icon: "mdi:clock-outline",
          tap_action: { action: "more-info" },
        });
      }

      alarmSections.push(
        {
          type: "heading",
          heading: device.name || "Alarm",
          icon: "mdi:alarm-panel",
        },
        {
          type: "grid",
          columns: 2,
          square: false,
          cards: rowCards,
        }
      );
    }

    if (alarmDevices.length === 0) {
      alarmSections.push({
        type: "markdown",
        content:
          "No alarms configured yet.\n\n" +
          "Add alarms in Settings → Integrations → Composable Alarm Clock → Configure.",
      });
    }

    // ── View assembly ────────────────────────────────────────────────────────
    return {
      title: config.title || "Alarm Clock",
      views: [
        {
          title: "Clock",
          path: "alarm-clock-face",
          type: "sections",
          max_columns: 1,
          sections: [
            {
              type: "grid",
              cards: [clockCard],
            },
            {
              type: "grid",
              cards: alarmSections,
            },
          ],
        },
      ],
    };
  }
}

customElements.define(
  "ll-strategy-dashboard-hacomposablealarmclock-clockface",
  HACACClockFaceStrategy
);

window.customStrategies = window.customStrategies || [];
window.customStrategies.push({
  type: "hacomposablealarmclock-clockface",
  strategyType: "dashboard",
  name: "Composable Alarm Clock — Clock Face",
  description:
    "Single-device alarm clock display: prominent live time, day/date, and per-alarm enabled state + set time.",
  documentationURL: "https://github.com/cmmtchll/hacomposablealarmclock",
});
