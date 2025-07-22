#!/usr/bin/env python3
"""Test script for customization step validation."""

import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Mock Home Assistant components
class MockHass:
    def __init__(self):
        self.states = Mock()
        self.states.get = Mock(return_value=None)

class MockEntityRegistry:
    def __init__(self):
        self.entities = {}

async def test_customization_step():
    """Test customization step configuration."""
    
    # Import the config flow class
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
    
    # Mock entity validation methods
    flow._async_validate_entity = AsyncMock(return_value=True)
    flow._async_get_entities_by_domain = AsyncMock(return_value=["sensor.test_humidity"])
    flow._async_create_entry = AsyncMock(return_value={"type": "create_entry"})
    
    print("Testing customization step...")
    
    # Test with default values
    test_input = {
        CONF_HEATING_TEMPERATURE: DEFAULT_HEATING_TEMPERATURE,
        CONF_IDLE_TEMPERATURE: DEFAULT_IDLE_TEMPERATURE,
        CONF_HEATING_WARM_LEVEL: DEFAULT_HEATING_WARM_LEVEL,
        CONF_IDLE_WARM_LEVEL: DEFAULT_IDLE_WARM_LEVEL,
        CONF_IDLE_FAN_SPEED: DEFAULT_IDLE_FAN_SPEED,
        CONF_SWING_MODE: DEFAULT_SWING_MODE,
        CONF_BEEP_MODE: DEFAULT_BEEP_MODE,
    }
    
    try:
        result = await flow.async_step_customization(test_input)
        print(f"✓ Customization step completed successfully")
        print(f"  Result type: {result.get('type', 'unknown')}")
        
        # Verify configuration was stored
        expected_keys = [
            CONF_HEATING_TEMPERATURE, CONF_IDLE_TEMPERATURE,
            CONF_HEATING_WARM_LEVEL, CONF_IDLE_WARM_LEVEL,
            CONF_IDLE_FAN_SPEED, CONF_SWING_MODE, CONF_BEEP_MODE
        ]
        
        for key in expected_keys:
            if key in flow._config:
                print(f"  ✓ {key}: {flow._config[key]}")
            else:
                print(f"  ✗ Missing configuration key: {key}")
        
        return True
        
    except Exception as e:
        print(f"✗ Customization step failed: {e}")
        return False

async def test_customization_validation():
    """Test customization input validation."""
    
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.config_flow import W100ConfigFlow
    from w100_smart_control.const import (
        CONF_HEATING_TEMPERATURE, CONF_IDLE_TEMPERATURE,
        CONF_HEATING_WARM_LEVEL, CONF_IDLE_WARM_LEVEL,
        CONF_IDLE_FAN_SPEED, CONF_SWING_MODE, CONF_BEEP_MODE
    )
    
    hass = MockHass()
    flow = W100ConfigFlow()
    flow.hass = hass
    flow._config = {"w100_device_name": "test_w100"}
    
    # Mock methods
    flow._async_validate_entity = AsyncMock(return_value=False)  # Simulate validation failure
    flow._async_get_entities_by_domain = AsyncMock(return_value=["sensor.test_humidity"])
    
    print("Testing customization validation...")
    
    # Test with invalid humidity sensor
    test_input = {
        CONF_HEATING_TEMPERATURE: 25.0,
        CONF_IDLE_TEMPERATURE: 20.0,
        CONF_HEATING_WARM_LEVEL: "3",
        CONF_IDLE_WARM_LEVEL: "1",
        CONF_IDLE_FAN_SPEED: "5",
        CONF_SWING_MODE: "horizontal",
        CONF_BEEP_MODE: "Enable Beep",
        "humidity_sensor": "sensor.invalid_humidity"
    }
    
    try:
        result = await flow.async_step_customization(test_input)
        
        if result.get("type") == "form" and "errors" in result:
            print("✓ Validation correctly detected invalid humidity sensor")
            print(f"  Errors: {result['errors']}")
            return True
        else:
            print("✗ Validation should have failed for invalid humidity sensor")
            return False
            
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Running customization step tests...\n")
    
    test1_passed = await test_customization_step()
    test2_passed = await test_customization_validation()
    
    print(f"\nTest Results:")
    print(f"  Customization step: {'PASS' if test1_passed else 'FAIL'}")
    print(f"  Validation test: {'PASS' if test2_passed else 'FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n✓ All customization tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))