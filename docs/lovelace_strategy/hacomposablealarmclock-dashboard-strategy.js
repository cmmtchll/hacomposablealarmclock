class HACACDashboardStrategy extends HTMLElement {
  static getCreateSuggestions() {
    return {
      title: "Composable Alarm Clock",
      icon: "mdi:alarm-panel",
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

      return device.identifiers.some((identifier) => {
        return Array.isArray(identifier) && identifier[0] === domain;
      });
    });

    const deviceIds = new Set(integrationDevices.map((device) => device.id));

    const integrationEntities = entities.filter((entity) => {
      if (entity.disabled_by || entity.hidden_by) {
        return false;
      }

      if (!deviceIds.has(entity.device_id)) {
        return false;
      }

      return true;
    });

    const workspaceEntities = integrationEntities
      .filter((entity) => entity.original_name === "Workspace overview")
      .map((entity) => entity.entity_id)
      .sort();

    const alarmDevices = integrationDevices
      .filter((device) => !String(device.name || "").toLowerCase().includes("workspace"))
      .sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));

    const cards = [];

    cards.push({
      type: "markdown",
      content:
        "# Composable Alarm Clock\n\n" +
        "Simple alarm overview: each card shows alarm name, enabled state, and alarm time.\n" +
        "Use the quick actions below to open management screens or run sample add/list actions.",
    });

    if (workspaceEntities.length > 0) {
      cards.push({
        type: "entities",
        title: "Workspace",
        show_header_toggle: false,
        entities: workspaceEntities,
      });
    }

    cards.push({
      type: "grid",
      columns: 4,
      square: false,
      cards: [
        {
          type: "button",
          name: "Open Integrations",
          icon: "mdi:cog",
          tap_action: {
            action: "navigate",
            navigation_path: "/config/integrations",
          },
        },
        {
          type: "button",
          name: "Open Devices",
          icon: "mdi:devices",
          tap_action: {
            action: "navigate",
            navigation_path: "/config/devices/dashboard",
          },
        },
        {
          type: "button",
          name: "List alarms",
          icon: "mdi:format-list-bulleted",
          tap_action: {
            action: "perform-action",
            perform_action: "hacomposablealarmclock.alarm_manage",
            data: { action: "list" },
          },
        },
        {
          type: "button",
          name: "Add sample alarm",
          icon: "mdi:plus-circle",
          tap_action: {
            action: "perform-action",
            perform_action: "hacomposablealarmclock.alarm_manage",
            data: {
              action: "upsert",
              alarm_id: "sample_0730",
              alarm_name: "Sample Alarm",
              alarm_time: "07:30:00",
              enabled: true,
            },
          },
        },
        {
          type: "button",
          name: "Enable sample",
          icon: "mdi:toggle-switch",
          tap_action: {
            action: "perform-action",
            perform_action: "hacomposablealarmclock.alarm_manage",
            data: {
              action: "enable",
              alarm_id: "sample_0730",
            },
          },
        },
        {
          type: "button",
          name: "Disable sample",
          icon: "mdi:toggle-switch-off",
          tap_action: {
            action: "perform-action",
            perform_action: "hacomposablealarmclock.alarm_manage",
            data: {
              action: "disable",
              alarm_id: "sample_0730",
            },
          },
        },
        {
          type: "button",
          name: "Trigger sample",
          icon: "mdi:bell-ring",
          tap_action: {
            action: "perform-action",
            perform_action: "hacomposablealarmclock.alarm_manage",
            data: {
              action: "trigger_now",
              alarm_id: "sample_0730",
            },
          },
        },
        {
          type: "button",
          name: "Delete sample",
          icon: "mdi:delete",
          tap_action: {
            action: "perform-action",
            perform_action: "hacomposablealarmclock.alarm_manage",
            data: {
              action: "delete",
              alarm_id: "sample_0730",
            },
          },
          confirmation: {
            text: "Delete sample alarm sample_0730?",
          },
        },
      ],
    });

    for (const device of alarmDevices) {
      const deviceEntityIds = integrationEntities
        .filter((entity) => entity.device_id === device.id)
        .map((entity) => entity.entity_id)
        .sort();

      const enabledEntity = deviceEntityIds.find((entityId) => entityId.startsWith("switch."));
      const timeEntity = deviceEntityIds.find((entityId) => entityId.startsWith("time."));

      if (!enabledEntity && !timeEntity) {
        continue;
      }

      const alarmEntities = [];
      if (enabledEntity) {
        alarmEntities.push({ entity: enabledEntity, name: "Enabled" });
      }
      if (timeEntity) {
        alarmEntities.push({ entity: timeEntity, name: "Alarm time" });
      }

      cards.push({
        type: "entities",
        title: `${device.name || "Alarm"}`,
        show_header_toggle: false,
        entities: alarmEntities,
      });
    }

    if (alarmDevices.length === 0) {
      cards.push({
        type: "markdown",
        content:
          "## No alarms found yet\n\n" +
          "Create alarms in Settings -> Devices and services -> Composable Alarm Clock -> Configure.",
      });
    }

    return {
      title: config.title || "Composable Alarm Clock",
      views: [
        {
          title: "Workspace",
          path: "alarm-workspace",
          type: "sections",
          max_columns: 4,
          sections: [
            {
              type: "grid",
              cards,
            },
          ],
        },
      ],
    };
  }
}

customElements.define("ll-strategy-dashboard-hacomposablealarmclock-dashboard", HACACDashboardStrategy);

window.customStrategies = window.customStrategies || [];
window.customStrategies.push({
  type: "hacomposablealarmclock-dashboard",
  strategyType: "dashboard",
  name: "Composable Alarm Clock",
  description: "Auto-generate a dashboard for Composable Alarm Clock devices and entities.",
  documentationURL: "https://github.com/cmmtchll/hacomposablealarmclock",
});
