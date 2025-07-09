# OFF Mode Simulation - Step by Step User Experience

## Test Scenario: Complete OFF Mode User Journey

**Goal**: Verify that when smart thermostat is OFF, the W100 can control fan speed properly.

---

## Simulation Setup

**Initial State**:
- Smart Thermostat: `climate.smart_office_fan_controller3`
  - state: "heat"
  - temperature: 22°C
  - current_temperature: 21.5°C
- Physical Fan: `climate.office_fan`
  - hvac_mode: "heat"
  - temperature: 30°C
  - fan_mode: "3"
- W100: `Tempcontrol00`
  - sensor: "external"
  - external_temperature: 22 (showing thermostat target)
- Heat Mode Boolean: `input_boolean.office_fan_heat_mode` = "on"

---

## Test 1: Turn Smart Thermostat OFF

### User Action: Set smart thermostat to OFF via Home Assistant

#### Expected Behavior:
1. Physical fan switches to fan_only mode
2. W100 display shows fan speed (3)
3. W100 buttons control fan speed

#### Actual Execution:

**Step 1**: Smart thermostat state changes from "heat" to "off"

**Step 2**: `smart_thermostat_state` trigger fires (line 176)
```yaml
- platform: state
  entity_id: climate.smart_office_fan_controller3
  id: smart_thermostat_state
  to: "off"  # ✅ TRIGGERS
```

**Step 3**: Smart Thermostat Idle/Off action executes (lines 368-425)

*Condition Check*:
```yaml
- condition: trigger
  id: smart_thermostat_state              # ✅ TRUE
- condition: not
  conditions:
    - condition: state
      entity_id: climate.smart_office_fan_controller3
      state: heat                         # ✅ TRUE (NOT heat = TRUE, state is "off")
- condition: or
  conditions:
    - condition: state
      entity_id: climate.smart_office_fan_controller3
      state: "off"                        # ✅ TRUE
```

*Physical Fan Actions*:
```yaml
# Fan switches to fan_only mode
- service: climate.set_hvac_mode
  target:
    entity_id: climate.office_fan
  data:
    hvac_mode: fan_only                   # ✅ EXECUTED

# Fan speed set to idle speed (3)
- service: climate.set_fan_mode
  target:
    entity_id: climate.office_fan
  data:
    fan_mode: "3"                         # ✅ EXECUTED

# Other settings configured...
```

**Step 4**: `w100_sync` trigger fires due to smart thermostat state change (line 222)

**Step 5**: W100 sync logic executes (lines 604-683)

*Variable Calculation*:
```yaml
current_sensor_mode: "external"
current_ext_temp: 22                     # Was showing temperature
smart_mode: "off"                        # Now "off"
target_temp: 22                          # Stale value
fan_speed: 3                             # Current fan speed
```

*Condition Evaluation*:
```yaml
# Heat mode check
- condition: state
  entity_id: climate.smart_office_fan_controller3
  state: heat                             # ❌ FALSE (state is "off")

# Cool mode check  
- condition: state
  entity_id: climate.smart_office_fan_controller3
  state: cool                             # ❌ FALSE (state is "off")

# Default action executes
- condition: template
  value_template: "{{ current_sensor_mode != 'external' or current_ext_temp != fan_speed }}"
  # "external" != "external" OR 22 != 3 = FALSE OR TRUE = TRUE ✅
```

*W100 Display Update*:
```yaml
- service: number.set_value
  target:
    entity_id: "number.Tempcontrol00_external_temperature"
  data:
    value: "3"                            # ✅ W100 now shows fan speed
```

#### Result: ✅ **PARTIAL SUCCESS**
- Physical fan: ✅ Switched to fan_only mode at speed 3
- W100 display: ✅ Shows fan speed (3)
- Ready for fan speed control: ❓ **TO BE TESTED**

---

## Test 2: Increase Fan Speed with W100 + Button

### User Action: Press W100 + button (single press)

#### Expected Behavior:
Fan speed increases from 3 to 4, W100 display updates to show 4

#### Actual Execution:

**Step 1**: MQTT message received
```yaml
Topic: zigbee2mqtt/Tempcontrol00/action
Payload: single_plus
```

**Step 2**: `w100_plus` trigger fires (line 196)

**Step 3**: W100 Plus action executes (lines 476-538)

*Condition Check*:
```yaml
- choose:
    - conditions:
        - condition: state
          entity_id: climate.smart_office_fan_controller3
          state: heat                     # ❌ FALSE (state is "off")
    - conditions:
        - condition: state
          entity_id: climate.smart_office_fan_controller3
          state: cool                     # ❌ FALSE (state is "off")
```

**CRITICAL FAILURE**: No condition matches! Smart thermostat is in "off" state.

**Step 4**: No default action exists - **NOTHING HAPPENS**

#### Result: ❌ **COMPLETE FAILURE**
- Fan speed: ❌ Remains at 3 (no change)
- W100 display: ❌ Still shows 3 (no update)
- User experience: ❌ Button press ignored

---

## Test 3: Decrease Fan Speed with W100 - Button

### User Action: Press W100 - button (single press)

#### Expected Behavior:
Fan speed decreases from 3 to 2, W100 display updates to show 2

#### Actual Execution:

**Step 1**: MQTT message received
```yaml
Topic: zigbee2mqtt/Tempcontrol00/action
Payload: single_minus
```

**Step 2**: `w100_minus` trigger fires (line 210)

**Step 3**: W100 Minus action executes (lines 540-602)

*Same condition check as plus button*:
```yaml
- choose:
    - conditions:
        - condition: state
          entity_id: climate.smart_office_fan_controller3
          state: heat                     # ❌ FALSE (state is "off")
    - conditions:
        - condition: state
          entity_id: climate.smart_office_fan_controller3
          state: cool                     # ❌ FALSE (state is "off")
```

**CRITICAL FAILURE**: Same issue - no condition matches.

#### Result: ❌ **COMPLETE FAILURE**
- Fan speed: ❌ Remains at 3 (no change)
- W100 display: ❌ Still shows 3 (no update)
- User experience: ❌ Button press ignored

---

## Test 4: Toggle Mode with W100 Center Button

### User Action: Double-tap W100 center button

#### Expected Behavior:
Smart thermostat turns back to heat mode

#### Actual Execution:

**Step 1**: MQTT message received
```yaml
Topic: zigbee2mqtt/Tempcontrol00/action
Payload: double_center
```

**Step 2**: `w100_toggle` trigger fires (line 196)

**Step 3**: W100 Toggle action executes (lines 432-474)

*Condition Check*:
```yaml
- choose:
    - conditions:
        - condition: state
          entity_id: climate.smart_office_fan_controller3
          state: cool                     # ❌ FALSE (state is "off")
```

**Step 4**: Default action executes (lines 451-474)
```yaml
default:
  - service: climate.set_hvac_mode
    target:
      entity_id: climate.smart_office_fan_controller3
    data:
      hvac_mode: cool                     # ⚠️ WRONG! Should be "heat"
```

#### Result: ❌ **INCORRECT BEHAVIOR**
- Smart thermostat: ❌ Set to "cool" mode (should be "heat")
- User expectation: ❌ Expected off → heat, got off → cool
- Logic error: ❌ Toggle behavior is wrong

---

## Test 5: Manual Fan Control via Home Assistant

### User Action: Manually change fan speed via Home Assistant interface

#### Expected Behavior:
W100 display updates to show new fan speed

#### Actual Execution:

**Step 1**: User sets fan speed to 5 via HA
```yaml
service: climate.set_fan_mode
target:
  entity_id: climate.office_fan
data:
  fan_mode: "5"
```

**Step 2**: Fan fan_mode attribute changes from "3" to "5"

**Step 3**: `w100_sync` trigger fires (line 228)
```yaml
- platform: state
  entity_id: climate.office_fan
  attribute: fan_mode
  id: w100_sync                           # ✅ TRIGGERS
```

**Step 4**: W100 sync logic executes (lines 604-683)

*Variable Calculation*:
```yaml
current_sensor_mode: "external"
current_ext_temp: 3                      # Current W100 display
smart_mode: "off"                        # Still "off"
target_temp: 22                          # Stale
fan_speed: 5                             # ✅ New fan speed
```

*Default Action Executes*:
```yaml
- condition: template
  value_template: "{{ current_sensor_mode != 'external' or current_ext_temp != fan_speed }}"
  # "external" != "external" OR 3 != 5 = FALSE OR TRUE = TRUE ✅

- service: number.set_value
  target:
    entity_id: "number.Tempcontrol00_external_temperature"
  data:
    value: "5"                            # ✅ W100 updated to show 5
```

#### Result: ✅ **SUCCESS**
- Fan speed: ✅ Changed to 5
- W100 display: ✅ Updated to show 5
- Sync working: ✅ Manual changes reflected on W100

---

## Summary of OFF Mode Functionality

### ✅ **What Works**:
1. **Smart thermostat OFF transition** - Physical fan switches to fan_only mode
2. **W100 display sync** - Shows fan speed when thermostat is off
3. **Manual fan control sync** - W100 updates when fan speed changed via HA

### ❌ **What's Broken**:
1. **W100 + button** - Does nothing when thermostat is off
2. **W100 - button** - Does nothing when thermostat is off  
3. **W100 toggle button** - Sets thermostat to "cool" instead of "heat"
4. **Direct fan speed control** - No way to control fan via W100 when thermostat is off

### 🔴 **Critical User Experience Issues**:

#### Issue 1: Non-functional W100 Remote
- **Problem**: W100 +/- buttons become completely non-functional
- **Impact**: Users cannot control fan speed via the remote
- **Workaround**: Must use Home Assistant interface

#### Issue 2: Confusing Toggle Behavior  
- **Problem**: Double-tap center button sets thermostat to "cool" mode
- **Impact**: Unexpected behavior, users expect off → heat
- **Confusion**: "Cool" mode may not be configured or desired

#### Issue 3: Inconsistent Control Logic
- **Problem**: Blueprint assumes thermostat always controls fan
- **Impact**: When thermostat is off, there's no direct fan control path
- **Design flaw**: Missing "direct fan control" mode

---

## Required Fixes

### 1. Add Default Actions for W100 Buttons
```yaml
# In w100_plus section, add:
default:
  # Control fan directly when thermostat is off
  - variables:
      current_fan: "{{ state_attr(fan_entity, 'fan_mode') | int(1) }}"
      new_fan: "{{ [current_fan + 1, 9] | min }}"
  - service: climate.set_fan_mode
    target:
      entity_id: !input fan_climate_entity
    data:
      fan_mode: "{{ new_fan | string }}"
```

### 2. Fix Toggle Button Logic
```yaml
# Add condition for "off" state:
- conditions:
    - condition: state
      entity_id: !input smart_thermostat_entity
      state: "off"
  sequence:
    - service: climate.set_hvac_mode
      target:
        entity_id: !input smart_thermostat_entity
      data:
        hvac_mode: heat  # off → heat (correct behavior)
```

### 3. Add Direct Fan Control Mode
Consider adding a mode where W100 controls fan directly without thermostat involvement.

---

## Conclusion

**OFF Mode Status**: 🔴 **SEVERELY BROKEN**

The blueprint successfully transitions the physical fan to fan_only mode and updates the W100 display, but **completely fails to provide W100 remote control functionality**. Users are left with a non-functional remote when the thermostat is off, defeating the purpose of the W100 integration.

**Priority**: **CRITICAL** - This breaks core functionality and user expectations.
