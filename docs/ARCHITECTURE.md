# Architecture

## Runtime flow

1. Config flow creates one local workspace entry.
2. Config entry setup initializes `AlarmClockManager` and loads persisted alarms.
3. Each alarm is scheduled locally for its next due time.
4. Dynamic entities are created per alarm device.
5. When due, integration fires an event and forwards alerts to configured targets.

## Module layout

- `manager.py`: Alarm persistence, scheduling, trigger dispatch.
- `entity.py`: Shared base entity and virtual device metadata.
- `sensor.py`: Next-due and last-triggered sensors.
- `switch.py`: Alarm enabled toggle entity.
- `time.py`: Alarm-time entity.
- `config_flow.py`: Setup and reconfigure flows.
- `diagnostics.py`: Stored alarm diagnostics payload.

## Design goals

- Full async behavior.
- Strict typing and maintainable boundaries.
- Clear test seams for alarm service lifecycle and event behavior.
