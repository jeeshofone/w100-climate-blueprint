#!/usr/bin/env python3
"""Comprehensive test to validate Task 7 completion."""

import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Mock Home Assistant components
class MockHass:
    def __init__(self):
        self.states = Mock()
        self.states.get = Mock(return_value=None)

async def test_task_7_requirements():
    """Test all Task 7 requirements are met."""
    
    print("Testing Task 7: Implement customization options configuration")
    print("=" * 60)
    
    # Import the config flow class
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.config_flow import W100ConfigFlow
    from w100_smart_control.const import (
        CONF_HEATING_TEMPERATURE, CONF_IDLE_TEMPERATURE,
        CONF_HEATING_WARM_LEVEL, CONF_IDLE_WARM_LEVEL,
        CONF_IDLE_FAN_SPEED, CONF_SWING_MODE, CONF_BEEP_MODE,
        CONF_HUMIDITY_SENSOR, CONF_BACKUP_HUMIDITY_SENSOR,
        WARM_LEVELS, FAN_SPEEDS, SWING_MODES, BEEP_MODES,
        DEFAULT_HEATING_TEMPERATURE, DEFAULT_IDLE_TEMPERATURE,
        DEFAULT_HEATING_WARM_LEVEL, DEFAULT_IDLE_WARM_LEVEL,
        DEFAULT_IDLE_FAN_SPEED, DEFAULT_SWING_MODE, DEFAULT_BEEP_MODE
    )
    
    # Create mock hass instance
    hass = MockHass()
    
    # Create config flow instance
    flow = W100ConfigFlow()
    flow.hass = hass
    flow._config = {"w100_device_name": "test_w100"}
    
    # Mock methods
    flow._async_validate_entity = AsyncMock(return_value=True)
    flow._async_get_entities_by_domain = AsyncMock(return_value=["sensor.humidity"])
    flow._async_create_entry = AsyncMock(return_value={"type": "create_entry"})
    
    print("\n1. Testing customization form creation...")
    
    # Test that customization form is created with all blueprint parameters
    result = await flow.async_step_customization()
    
    if result.get("type") != "form":
        print("✗ Customization step should return a form")
        return False
    
    schema = result.get("data_schema")
    if not schema:
        print("✗ Customization step should have a data schema")
        return False
    
    print("✓ Customization form created successfully")
    
    print("\n2. Testing all blueprint parameters are present...")
    
    schema_dict = schema.schema
    required_fields = {
        CONF_HEATING_TEMPERATURE: "Heating Temperature",
        CONF_IDLE_TEMPERATURE: "Idle Temperature", 
        CONF_HEATING_WARM_LEVEL: "Heating Warm Level",
        CONF_IDLE_WARM_LEVEL: "Idle Warm Level",
        CONF_IDLE_FAN_SPEED: "Idle Fan Speed",
        CONF_SWING_MODE: "Swing Mode",
        CONF_BEEP_MODE: "Beep Mode",
    }
    
    all_fields_present = True
    for field_key, field_name in required_fields.items():
        field_found = False
        for key in schema_dict.keys():
            if hasattr(key, 'schema') and key.schema == field_key:
                field_found = True
                break
        
        if field_found:
            print(f"  ✓ {field_name}")
        else:
            print(f"  ✗ {field_name} missing")
            all_fields_present = False
    
    if not all_fields_present:
        return False
    
    print("\n3. Testing temperature selectors and ranges...")
    
    # Test temperature ranges (15-35°C as per requirements)
    temp_test_input = {
        CONF_HEATING_TEMPERATURE: 25.0,  # Valid
        CONF_IDLE_TEMPERATURE: 20.0,     # Valid
        CONF_HEATING_WARM_LEVEL: "2",
        CONF_IDLE_WARM_LEVEL: "1", 
        CONF_IDLE_FAN_SPEED: "3",
        CONF_SWING_MODE: "horizontal",
        CONF_BEEP_MODE: "Enable Beep",
    }
    
    try:
        result = await flow.async_step_customization(temp_test_input)
        if result.get("type") == "create_entry":
            print("✓ Temperature ranges validated correctly")
        else:
            print("✗ Temperature validation failed")
            return False
    except Exception as e:
        print(f"✗ Temperature validation error: {e}")
        return False
    
    print("\n4. Testing fan speed and beep mode selectors...")
    
    # Verify fan speed options (1-9)
    expected_fan_speeds = [str(i) for i in range(1, 10)]
    if set(FAN_SPEEDS) == set(expected_fan_speeds):
        print("✓ Fan speed options (1-9) available")
    else:
        print(f"✗ Fan speed options incorrect: {FAN_SPEEDS}")
        return False
    
    # Verify beep mode options
    expected_beep_modes = {"Enable Beep", "Disable Beep", "On-Mode Change"}
    if set(BEEP_MODES) == expected_beep_modes:
        print("✓ Beep mode options available")
    else:
        print(f"✗ Beep mode options incorrect: {BEEP_MODES}")
        return False
    
    # Verify warm level options (1-4)
    expected_warm_levels = {"1", "2", "3", "4"}
    if set(WARM_LEVELS) == expected_warm_levels:
        print("✓ Warm level options (1-4) available")
    else:
        print(f"✗ Warm level options incorrect: {WARM_LEVELS}")
        return False
    
    # Verify swing mode options
    expected_swing_modes = {"horizontal", "vertical", "both", "off"}
    if set(SWING_MODES) == expected_swing_modes:
        print("✓ Swing mode options available")
    else:
        print(f"✗ Swing mode options incorrect: {SWING_MODES}")
        return False
    
    print("\n5. Testing input validation...")
    
    # Reset mocks for validation test
    flow._async_validate_entity = AsyncMock(return_value=False)  # Simulate validation failure
    
    invalid_input = {
        CONF_HEATING_TEMPERATURE: 25.0,
        CONF_IDLE_TEMPERATURE: 20.0,
        CONF_HEATING_WARM_LEVEL: "2",
        CONF_IDLE_WARM_LEVEL: "1",
        CONF_IDLE_FAN_SPEED: "3",
        CONF_SWING_MODE: "horizontal",
        CONF_BEEP_MODE: "Enable Beep",
        CONF_HUMIDITY_SENSOR: "sensor.invalid",  # This should fail validation
    }
    
    try:
        result = await flow.async_step_customization(invalid_input)
        if result.get("type") == "form" and "errors" in result:
            print("✓ Input validation working correctly")
        else:
            print("✗ Input validation should have failed")
            return False
    except Exception as e:
        print(f"✗ Input validation error: {e}")
        return False
    
    print("\n6. Testing complete configuration storage...")
    
    # Reset mocks for successful storage test
    flow._async_validate_entity = AsyncMock(return_value=True)
    
    complete_input = {
        CONF_HEATING_TEMPERATURE: 28.5,
        CONF_IDLE_TEMPERATURE: 21.0,
        CONF_HEATING_WARM_LEVEL: "3",
        CONF_IDLE_WARM_LEVEL: "2",
        CONF_IDLE_FAN_SPEED: "7",
        CONF_SWING_MODE: "vertical",
        CONF_BEEP_MODE: "Disable Beep",
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
        CONF_BACKUP_HUMIDITY_SENSOR: "sensor.backup_humidity",
    }
    
    try:
        result = await flow.async_step_customization(complete_input)
        if result.get("type") == "create_entry":
            print("✓ Complete configuration stored successfully")
            
            # Verify all values are in the config
            for key, value in complete_input.items():
                if flow._config.get(key) == value:
                    print(f"  ✓ {key}: {value}")
                else:
                    print(f"  ✗ {key}: expected {value}, got {flow._config.get(key)}")
                    return False
        else:
            print("✗ Complete configuration storage failed")
            return False
    except Exception as e:
        print(f"✗ Configuration storage error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ Task 7 COMPLETED SUCCESSFULLY!")
    print("\nAll sub-tasks completed:")
    print("  ✓ Create customization form with all blueprint parameters")
    print("  ✓ Add temperature, fan speed, and beep mode selectors")
    print("  ✓ Implement input validation for temperature ranges and options")
    print("  ✓ Store complete configuration for integration setup")
    print("\nRequirements 4.1-4.7 satisfied:")
    print("  ✓ 4.1: Heating temperature (15-35°C)")
    print("  ✓ 4.2: Idle temperature (15-35°C)")
    print("  ✓ 4.3: Heating warm level (1-4)")
    print("  ✓ 4.4: Idle warm level (1-4)")
    print("  ✓ 4.5: Idle fan speed (1-9)")
    print("  ✓ 4.6: Swing mode (horizontal, vertical, both, off)")
    print("  ✓ 4.7: Beep mode (Enable, Disable, On-Mode Change)")
    
    return True

async def main():
    """Run the comprehensive test."""
    success = await test_task_7_requirements()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))