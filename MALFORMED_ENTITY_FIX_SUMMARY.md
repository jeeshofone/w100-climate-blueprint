# Malformed Entity ID Fix Summary

## Problem
Both Kogan and Philips automations were failing with malformed entity_id errors:

**Kogan Error:**
```
Message malformed: not a valid value for dictionary value @ data['actions'][0]['choose'][0]['sequence'][0]['choose'][1]['sequence'][2]['choose'][0]['sequence'][0]['entity_id']
```

**Philips Error:**
```
Message malformed: not a valid value for dictionary value @ data['actions'][0]['choose'][0]['sequence'][0]['choose'][0]['sequence'][2]['target']['entity_id']
```

## Root Cause
The blueprint was using `sun.sun` as default values for optional inputs, and directly referencing optional inputs with `!input` in service calls without checking if they exist.

### Issues Found:
1. **`sun.sun` defaults** - Caused runtime errors when accessing non-existent attributes
2. **Direct `!input` usage for optional entities** - Caused malformed entity_id when empty
3. **Missing conditional checks** - Optional entities used without existence validation
4. **Problematic trigger** - Philips fan preset trigger referenced optional input

## Solutions Applied

### 1. Replace `sun.sun` with Empty String Defaults
```yaml
# BEFORE (problematic)
fan_entity:
  default: "sun.sun"

# AFTER (fixed)
fan_entity:
  default: ""
```

### 2. Add Conditional Logic for Optional Entities
```yaml
# BEFORE (problematic)
- service: select.select_option
  target:
    entity_id: !input fan_warm_level_entity

# AFTER (fixed)
- choose:
    - conditions:
        - condition: template
          value_template: "{{ warm_level_entity != '' }}"
      sequence:
        - service: select.select_option
          target:
            entity_id: "{{ warm_level_entity }}"
```

### 3. Fix Beep Switch References
```yaml
# BEFORE (problematic)
- condition: template
  value_template: "{{ device_type == 'kogan_bladeless' and beep_mode == 'Enable Beep' }}"
sequence:
  - service: switch.turn_on
    target:
      entity_id: !input fan_beep_switch

# AFTER (fixed)
- condition: template
  value_template: "{{ device_type == 'kogan_bladeless' and beep_switch != '' and beep_mode == 'Enable Beep' }}"
sequence:
  - service: switch.turn_on
    target:
      entity_id: "{{ beep_switch }}"
```

### 4. Remove Problematic Trigger
Removed the Philips fan preset mode trigger that referenced optional input:
```yaml
# REMOVED (was causing startup errors)
- platform: state
  entity_id: !input fan_entity
  attribute: preset_mode
  id: w100_sync
```

## Key Principles Applied

1. **Only required inputs in triggers** - Never use optional inputs in trigger section
2. **Empty string defaults** - Much better than `sun.sun` hack
3. **Conditional entity usage** - Always check `{{ entity != '' }}` before using optional entities
4. **Template entity_id** - Use `entity_id: "{{ variable }}"` instead of `entity_id: !input optional_input`

## Validation Results

After fixes:
- ✅ YAML syntax valid
- ✅ Blueprint structure valid  
- ✅ **0 problematic references** found by analyzer
- ✅ All entity_id references properly validated
- ✅ Both Kogan and Philips configurations should work

## Files Changed
- `blueprint.yaml` - Main blueprint with all fixes applied
- Added conditional logic for 3 `fan_warm_level_entity` usages
- Fixed 11 `fan_beep_switch` references with existence checks
- Removed 1 problematic trigger
- Updated all `sun.sun` references to empty string checks

## Testing Recommendation
Test both device types:
1. Kogan with all optional entities provided
2. Kogan with minimal required entities only
3. Philips with all optional entities provided  
4. Philips with minimal required entities only
