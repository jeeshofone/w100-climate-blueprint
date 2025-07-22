#!/usr/bin/env python3
"""Test script to validate complete customization configuration storage."""

import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Mock Home Assistant components
class MockHass:
    def __init__(self):
        self.states = Mock()
        self.states.get = Mock(return_value=None)

async def test_complete_configuration_storage():
    """Test that complete configuration is stored properly."""
    
    # Import the config flow class
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.config_flow import W100ConfigFlow
    from w100_smart_control.const import (
        CONF_HEATING_TEMPERATURE, CONF_IDLE_TEMPERATURE,
        CONF_HEATING_WARM_LEVEL, CONF_IDLE_WARM_LEVEL,
        CONF_IDLE_FAN_SPEED, CONF_SWING_MODE, CONF_BEEP_MODE,
        CONF_HUMIDITY_SENSOR, CONF_BACKUP_HUMIDITY_SENSOR
    )
    
    # Create mock hass instance
    hass = MockHass()
    
    # Create config flow instance
    flow = W100ConfigFlow()
    flow.hass = hass
    flow._config = {
        "w100_device_name": "test_w100",
        "climate_entity_type": "existing",
        "existing_climate_entity": "climate.test"
    }
    
    # Mock methods
    flow._async_validate_entity = AsyncMock(return_value=True)
    flow._async_get_entities_by_domain = AsyncMock(return_value=["sensor.humidity", "sensor.backup_humidity"])
    
    # Mock the create entry method to capture the final config
    final_config = {}
    async def mock_create_entry():
        final_config.update(flow._config)
        return {"type": "create_entry", "title": "Test", "data": flow._config}
    
    flow._async_create_entry = mock_create_entry
    
    print("Testing complete customization configuration storage...\n")
    
    # Test with all customization options
    test_input = {
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
        result = await flow.async_step_customization(test_input)
        
        if result.get("type") == "create_entry":
            print("✓ Configuration entry created successfully")
            
            # Verify all customization options are stored
            expected_config = {
                "w100_device_name": "test_w100",
                "climate_entity_type": "existing", 
                "existing_climate_entity": "climate.test",
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
            
            all_present = True
            for key, expected_value in expected_config.items():
                if key in final_config:
                    actual_value = final_config[key]
                    if actual_value == expected_value:
                        print(f"  ✓ {key}: {actual_value}")
                    else:
                        print(f"  ✗ {key}: expected {expected_value}, got {actual_value}")
                        all_present = False
                else:
                    print(f"  ✗ Missing configuration key: {key}")
                    all_present = False
            
            if all_present:
                print("\n✓ All customization options stored correctly!")
                return True
            else:
                print("\n✗ Some customization options not stored correctly!")
                return False
        else:
            print("✗ Configuration entry creation failed")
            return False
            
    except Exception as e:
        print(f"✗ Complete configuration test failed: {e}")
        return False

async def test_optional_fields():
    """Test that optional fields work correctly."""
    
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.config_flow import W100ConfigFlow
    from w100_smart_control.const import (
        CONF_HEATING_TEMPERATURE, CONF_IDLE_TEMPERATURE,
        CONF_HEATING_WARM_LEVEL, CONF_IDLE_WARM_LEVEL,
        CONF_IDLE_FAN_SPEED, CONF_SWING_MODE, CONF_BEEP_MODE,
        DEFAULT_HEATING_TEMPERATURE, DEFAULT_IDLE_TEMPERATURE,
        DEFAULT_HEATING_WARM_LEVEL, DEFAULT_IDLE_WARM_LEVEL,
        DEFAULT_IDLE_FAN_SPEED, DEFAULT_SWING_MODE, DEFAULT_BEEP_MODE
    )
    
    hass = MockHass()
    flow = W100ConfigFlow()
    flow.hass = hass
    flow._config = {"w100_device_name": "test_w100"}
    
    # Mock methods
    flow._async_validate_entity = AsyncMock(return_value=True)
    flow._async_get_entities_by_domain = AsyncMock(return_value=[])
    
    final_config = {}
    async def mock_create_entry():
        final_config.update(flow._config)
        return {"type": "create_entry", "title": "Test", "data": flow._config}
    
    flow._async_create_entry = mock_create_entry
    
    print("\nTesting optional fields with defaults...")
    
    # Test with minimal input (no optional humidity sensors)
    test_input = {
        CONF_HEATING_TEMPERATURE: DEFAULT_HEATING_TEMPERATURE,
        CONF_IDLE_TEMPERATURE: DEFAULT_IDLE_TEMPERATURE,
        CONF_HEATING_WARM_LEVEL: DEFAULT_HEATING_WARM_LEVEL,
        CONF_IDLE_WARM_LEVEL: DEFAULT_IDLE_WARM_LEVEL,
        CONF_IDLE_FAN_SPEED: DEFAULT_IDLE_FAN_SPEED,
        CONF_SWING_MODE: DEFAULT_SWING_MODE,
        CONF_BEEP_MODE: DEFAULT_BEEP_MODE,
        # No humidity sensors provided
    }
    
    try:
        result = await flow.async_step_customization(test_input)
        
        if result.get("type") == "create_entry":
            print("✓ Configuration with defaults created successfully")
            
            # Verify required fields are present
            required_fields = [
                CONF_HEATING_TEMPERATURE, CONF_IDLE_TEMPERATURE,
                CONF_HEATING_WARM_LEVEL, CONF_IDLE_WARM_LEVEL,
                CONF_IDLE_FAN_SPEED, CONF_SWING_MODE, CONF_BEEP_MODE
            ]
            
            all_present = True
            for field in required_fields:
                if field in final_config:
                    print(f"  ✓ {field}: {final_config[field]}")
                else:
                    print(f"  ✗ Missing required field: {field}")
                    all_present = False
            
            # Verify optional fields are not present (or None)
            optional_fields = ["humidity_sensor", "backup_humidity_sensor"]
            for field in optional_fields:
                if field not in final_config or final_config[field] is None:
                    print(f"  ✓ Optional field {field} correctly omitted")
                else:
                    print(f"  ⚠ Optional field {field} present: {final_config[field]}")
            
            if all_present:
                print("\n✓ Default configuration handled correctly!")
                return True
            else:
                print("\n✗ Some required fields missing!")
                return False
        else:
            print("✗ Default configuration creation failed")
            return False
            
    except Exception as e:
        print(f"✗ Optional fields test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Testing Complete Customization Implementation...\n")
    
    test1_passed = await test_complete_configuration_storage()
    test2_passed = await test_optional_fields()
    
    print(f"\nTest Results:")
    print(f"  Complete configuration storage: {'PASS' if test1_passed else 'FAIL'}")
    print(f"  Optional fields handling: {'PASS' if test2_passed else 'FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n✓ Complete customization implementation validated!")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))