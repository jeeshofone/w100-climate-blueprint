# The Proper Fix for W100 Display Bouncing

## Root Cause Summary
The W100 display bouncing is caused by:
1. **Overly broad w100_sync trigger** (line 222-223) that fires on ANY smart thermostat change
2. **Faulty default logic** in w100_sync that incorrectly shows fan speed when in heat mode
3. **Race conditions** from multiple simultaneous triggers

## Required Changes

### 1. Fix the Overly Broad Trigger (Lines 222-223)

**CURRENT (PROBLEMATIC):**
```yaml
- platform: state
  entity_id: !input smart_thermostat_entity
  id: w100_sync
```

**FIXED:**
```yaml
- platform: state
  entity_id: !input smart_thermostat_entity
  id: w100_sync
  from: 
    - "heat"
    - "off"
  to:
    - "heat" 
    - "off"
```

**Rationale**: Only trigger on actual state transitions between heat and off modes, not on attribute changes.

### 2. Fix the smart_thermostat_state Trigger (Lines 175-181)

**CURRENT (LIKELY BROKEN):**
```yaml
- platform: state
  entity_id: !input smart_thermostat_entity
  id: smart_thermostat_state
  to:
    - "idle"
    - "off"
```

**FIXED:**
```yaml
- platform: state
  entity_id: !input smart_thermostat_entity
  id: smart_thermostat_state
  to: "off"
```

**Rationale**: Smart Thermostat PID doesn't have "idle" state, only "heat" and "off".

### 3. Fix the W100 Sync Logic Default Action (Lines 665-683)

**CURRENT (PROBLEMATIC):**
```yaml
default:
  - condition: template
    value_template: "{{ current_sensor_mode != 'external' or current_ext_temp != fan_speed }}"
  - service: select.select_option
    target:
      entity_id: "select.{{ w100_name }}_sensor"
    data:
      option: external
  - service: number.set_value
    target:
      entity_id: "number.{{ w100_name }}_external_temperature"
    data:
      value: "{{ fan_speed }}"
```

**FIXED:**
```yaml
default:
  # Only update if we're actually in off/idle mode AND display needs updating
  - condition: and
    conditions:
      - condition: not
        conditions:
          - condition: state
            entity_id: !input smart_thermostat_entity
            state: heat
      - condition: template
        value_template: "{{ current_sensor_mode != 'external' or current_ext_temp != fan_speed }}"
  - service: select.select_option
    target:
      entity_id: "select.{{ w100_name }}_sensor"
    data:
      option: external
  - service: number.set_value
    target:
      entity_id: "number.{{ w100_name }}_external_temperature"
    data:
      value: "{{ fan_speed }}"
```

**Rationale**: Don't show fan speed when smart thermostat is in heat mode.

### 4. Add Debouncing to Prevent Rapid Updates

**ADD AFTER LINE 607:**
```yaml
# Debounce rapid successive triggers
- delay:
    milliseconds: 100
```

### 5. Remove Redundant Triggers

**REMOVE** the current_temperature trigger (lines 224-226) as it's not needed for display sync:
```yaml
# REMOVE THIS:
- platform: state
  entity_id: !input smart_thermostat_entity
  attribute: current_temperature
  id: w100_sync
```

## Complete Fixed Trigger Section

```yaml
trigger:
  # Office fan heat mode trigger
  - platform: state
    entity_id: !input heat_mode_boolean
    id: office_fan_heat_mode
  # Smart thermostat state trigger - FIXED
  - platform: state
    entity_id: !input smart_thermostat_entity
    id: smart_thermostat_state
    to: "off"
  # Smart thermostat temperature change trigger (for beep)
  - platform: state
    entity_id: !input smart_thermostat_entity
    attribute: temperature
    id: smart_temp_change
  # Smart thermostat mode change trigger (for beep)
  - platform: state
    entity_id: !input smart_thermostat_entity
    id: smart_mode_change
    to:
      - "heat"
      - "off"
  # W100 button triggers
  - platform: mqtt
    topic: zigbee2mqtt/{{ w100_name }}/action
    payload: double_center
    id: w100_toggle
  - platform: mqtt
    topic: zigbee2mqtt/{{ w100_name }}/action
    payload: single_plus
    id: w100_plus
  - platform: mqtt
    topic: zigbee2mqtt/{{ w100_name }}/action
    payload: double_plus
    id: w100_plus
  - platform: mqtt
    topic: zigbee2mqtt/{{ w100_name }}/action
    payload: single_minus
    id: w100_minus
  - platform: mqtt
    topic: zigbee2mqtt/{{ w100_name }}/action
    payload: double_minus
    id: w100_minus
  # W100 sync triggers - FIXED
  - platform: state
    entity_id: !input smart_thermostat_entity
    attribute: temperature
    id: w100_sync
  - platform: state
    entity_id: !input smart_thermostat_entity
    id: w100_sync
    from: 
      - "heat"
      - "off"
    to:
      - "heat" 
      - "off"
  - platform: state
    entity_id: !input fan_climate_entity
    attribute: fan_mode
    id: w100_sync
  # W100 startup trigger
  - platform: homeassistant
    event: start
    id: w100_init
  # W100 humidity sync trigger
  - platform: state
    entity_id: !input humidity_sensor
    id: w100_humidity
  # Fan temperature monitor for stuck heater workaround
  - platform: state
    entity_id: !input fan_climate_entity
    attribute: current_temperature
    id: fan_temp_monitor
  - platform: time_pattern
    minutes: '/1'
    seconds: '30'
    id: fan_temp_monitor
```

## Testing Strategy

After implementing the fix:

1. **Monitor hvac_action changes**: Verify w100_sync doesn't fire on hvac_action bouncing
2. **Test state transitions**: Verify display updates correctly on heat ↔ off transitions
3. **Check display stability**: Confirm no bouncing between temperature and fan speed
4. **Validate button controls**: Ensure W100 remote still works correctly

## Version Update Required

This should be released as **v0.11** with proper fix documentation, not v0.10 which contains misleading claims.
