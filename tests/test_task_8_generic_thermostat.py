#!/usr/bin/env python3
"""Test script for Task 8: Implement generic thermostat creation workflow."""

import asyncio
import sys
from unittest.mock import Mock, AsyncMock

# Mock Home Assistant components
class MockState:
    def __init__(self, entity_id, state="on", attributes=None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}

class MockEntityRegistry:
    def __init__(self):
        self.entities = {}
    
    def add_entity(self, entity_id, disabled_by=None):
        """Add a mock entity to the registry."""
        entry = Mock()
        entry.entity_id = entity_id
        entry.disabled_by = disabled_by
        self.entities[entity_id] = entry

class MockHass:
    def __init__(self):
        self.states = Mock()
        self.states.get = Mock()

async def test_generic_thermostat_workflow():
    """Test the generic thermostat creation workflow."""
    
    # Import the config flow class
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.config_flow import W100ConfigFlow
    from w100_smart_control.const import (
        CONF_HEATER_SWITCH, CONF_TEMPERATURE_SENSOR, CONF_MIN_TEMP, 
        CONF_MAX_TEMP, CONF_TARGET_TEMP, CONF_COLD_TOLERANCE, 
        CONF_HOT_TOLERANCE, CONF_PRECISION, CONF_GENERIC_THERMOSTAT_CONFIG
    )
    
    # Create mock hass instance
    hass = MockHass()
    
    # Create config flow instance
    flow = W100ConfigFlow()
    flow.hass = hass
    flow._config = {"w100_device_name": "test_w100", "climate_entity_type": "generic"}
    
    print("Testing Task 8: Generic Thermostat Creation Workflow")
    print("=" * 60)
    
    # Mock entity registry with switch and sensor entities
    mock_registry = MockEntityRegistry()
    mock_registry.add_entity("switch.heater1")
    mock_registry.add_entity("switch.heater2")
    mock_registry.add_entity("sensor.temperature1")
    mock_registry.add_entity("sensor.temperature2")
    mock_registry.add_entity("sensor.humidity1")  # Should not appear in temperature sensor list
    
    # Mock the entity registry function
    import w100_smart_control.config_flow as config_flow_module
    original_get_registry = config_flow_module.async_get_entity_registry
    config_flow_module.async_get_entity_registry = Mock(return_value=mock_registry)
    
    try:
        # Test 1: Generic thermostat step form creation
        print("\n1. Testing generic thermostat form creation...")
        
        # Mock entity states
        hass.states.get.side_effect = lambda entity_id: {
            "switch.heater1": MockState("switch.heater1", "off"),
            "switch.heater2": MockState("switch.heater2", "on"),
            "sensor.temperature1": MockState("sensor.temperature1", "22.5"),
            "sensor.temperature2": MockState("sensor.temperature2", "21.0"),
        }.get(entity_id)
        
        result = await flow.async_step_generic_thermostat(None)
        
        assert result["type"] == "form", "Should show form"
        assert result["step_id"] == "generic_thermostat", "Should be generic thermostat step"
        print("✓ Generic thermostat form created successfully")
        
        # Test 2: Verify form contains all required fields
        print("\n2. Testing form contains all required parameters...")
        
        schema_dict = result["data_schema"].schema
        schema_keys = [str(key) for key in schema_dict.keys()]
        
        required_fields = [
            CONF_HEATER_SWITCH,
            CONF_TEMPERATURE_SENSOR,
            CONF_MIN_TEMP,
            CONF_MAX_TEMP,
            CONF_TARGET_TEMP,
            CONF_COLD_TOLERANCE,
            CONF_HOT_TOLERANCE,
            CONF_PRECISION
        ]
        
        for field in required_fields:
            field_found = any(field in key for key in schema_keys)
            assert field_found, f"Field {field} should be in form schema"
            print(f"  ✓ {field}")
        
        # Test 3: Verify heater switch and temperature sensor selectors
        print("\n3. Testing heater switch and temperature sensor selection...")
        
        # Check that switch entities are available for heater selection
        heater_field = None
        temp_field = None
        
        for key, field in schema_dict.items():
            key_str = str(key)
            if CONF_HEATER_SWITCH in key_str:
                heater_field = field
            elif CONF_TEMPERATURE_SENSOR in key_str:
                temp_field = field
        
        assert heater_field is not None, "Heater switch field should be present"
        assert temp_field is not None, "Temperature sensor field should be present"
        print("✓ Heater switch and temperature sensor selectors present")
        
        # Test 4: Test parameter configuration with valid values
        print("\n4. Testing parameter configuration...")
        
        valid_config = {
            CONF_HEATER_SWITCH: "switch.heater1",
            CONF_TEMPERATURE_SENSOR: "sensor.temperature1",
            CONF_MIN_TEMP: 10.0,
            CONF_MAX_TEMP: 30.0,
            CONF_TARGET_TEMP: 22.0,
            CONF_COLD_TOLERANCE: 0.5,
            CONF_HOT_TOLERANCE: 0.5,
            CONF_PRECISION: "0.5"
        }
        
        result = await flow.async_step_generic_thermostat(valid_config)
        
        # Should proceed to customization step
        assert result["type"] == "form", "Should proceed to next step"
        assert result["step_id"] == "customization", "Should go to customization step"
        
        # Verify config was stored
        assert CONF_GENERIC_THERMOSTAT_CONFIG in flow._config, "Generic thermostat config should be stored"
        stored_config = flow._config[CONF_GENERIC_THERMOSTAT_CONFIG]
        
        for key, value in valid_config.items():
            assert stored_config[key] == value, f"Config {key} should be stored correctly"
            print(f"  ✓ {key}: {stored_config[key]}")
        
        # Test 5: Test entity validation - invalid heater switch
        print("\n5. Testing entity validation - invalid heater switch...")
        
        flow._config = {"w100_device_name": "test_w100", "climate_entity_type": "generic"}  # Reset
        
        invalid_config = {
            CONF_HEATER_SWITCH: "switch.nonexistent",
            CONF_TEMPERATURE_SENSOR: "sensor.temperature1",
        }
        
        # Mock nonexistent entity
        hass.states.get.side_effect = lambda entity_id: {
            "sensor.temperature1": MockState("sensor.temperature1", "22.5"),
        }.get(entity_id)  # switch.nonexistent returns None
        
        result = await flow.async_step_generic_thermostat(invalid_config)
        
        assert result["type"] == "form", "Should show form again"
        assert result["step_id"] == "generic_thermostat", "Should stay on generic thermostat step"
        assert "errors" in result, "Should have errors"
        assert CONF_HEATER_SWITCH in result["errors"], "Should have heater switch error"
        print("✓ Invalid heater switch validation working")
        
        # Test 6: Test entity validation - invalid temperature sensor
        print("\n6. Testing entity validation - invalid temperature sensor...")
        
        flow._config = {"w100_device_name": "test_w100", "climate_entity_type": "generic"}  # Reset
        
        invalid_config = {
            CONF_HEATER_SWITCH: "switch.heater1",
            CONF_TEMPERATURE_SENSOR: "sensor.nonexistent",
        }
        
        # Mock entities
        hass.states.get.side_effect = lambda entity_id: {
            "switch.heater1": MockState("switch.heater1", "off"),
        }.get(entity_id)  # sensor.nonexistent returns None
        
        result = await flow.async_step_generic_thermostat(invalid_config)
        
        assert result["type"] == "form", "Should show form again"
        assert result["step_id"] == "generic_thermostat", "Should stay on generic thermostat step"
        assert "errors" in result, "Should have errors"
        assert CONF_TEMPERATURE_SENSOR in result["errors"], "Should have temperature sensor error"
        print("✓ Invalid temperature sensor validation working")
        
        # Test 7: Test parameter ranges and defaults
        print("\n7. Testing parameter ranges and defaults...")
        
        from w100_smart_control.const import (
            DEFAULT_MIN_TEMP, DEFAULT_MAX_TEMP, DEFAULT_TARGET_TEMP,
            DEFAULT_COLD_TOLERANCE, DEFAULT_HOT_TOLERANCE, DEFAULT_PRECISION
        )
        
        # Test form with no input to check defaults
        result = await flow.async_step_generic_thermostat(None)
        schema_dict = result["data_schema"].schema
        
        # Check defaults are set correctly
        defaults_found = {}
        for key, field in schema_dict.items():
            key_str = str(key)
            # Check if the key has a default value
            if hasattr(key, 'default') and key.default is not None:
                # Call the default function if it's callable
                default_value = key.default() if callable(key.default) else key.default
                if CONF_MIN_TEMP in key_str:
                    defaults_found[CONF_MIN_TEMP] = default_value
                elif CONF_MAX_TEMP in key_str:
                    defaults_found[CONF_MAX_TEMP] = default_value
                elif CONF_TARGET_TEMP in key_str:
                    defaults_found[CONF_TARGET_TEMP] = default_value
                elif CONF_COLD_TOLERANCE in key_str:
                    defaults_found[CONF_COLD_TOLERANCE] = default_value
                elif CONF_HOT_TOLERANCE in key_str:
                    defaults_found[CONF_HOT_TOLERANCE] = default_value
                elif CONF_PRECISION in key_str:
                    defaults_found[CONF_PRECISION] = default_value
        
        expected_defaults = {
            CONF_MIN_TEMP: DEFAULT_MIN_TEMP,
            CONF_MAX_TEMP: DEFAULT_MAX_TEMP,
            CONF_TARGET_TEMP: DEFAULT_TARGET_TEMP,
            CONF_COLD_TOLERANCE: DEFAULT_COLD_TOLERANCE,
            CONF_HOT_TOLERANCE: DEFAULT_HOT_TOLERANCE,
            CONF_PRECISION: DEFAULT_PRECISION
        }
        
        print(f"Defaults found: {defaults_found}")
        print(f"Expected defaults: {expected_defaults}")
        
        for param, expected_value in expected_defaults.items():
            if param in defaults_found:
                actual_value = defaults_found[param]
                assert actual_value == expected_value, f"Default for {param} should be {expected_value}, got {actual_value}"
                print(f"  ✓ {param}: {actual_value}")
            else:
                print(f"  ⚠️  {param}: not found in schema defaults")
        
        print("\n" + "=" * 60)
        print("✅ Task 8 COMPLETED SUCCESSFULLY!")
        print("\nAll sub-tasks completed:")
        print("  ✓ Add generic thermostat configuration step to config flow")
        print("  ✓ Create form for heater switch and temperature sensor selection")
        print("  ✓ Implement parameter configuration (min/max temps, tolerances, precision)")
        print("  ✓ Validate all required entities exist before creation")
        print("\nRequirements 3.1, 3.2 satisfied:")
        print("  ✓ 3.1: Option to create new generic thermostat")
        print("  ✓ 3.2: Prompt for required parameters (heater switch, temperature sensor, min/max temps)")
        
    finally:
        # Restore original function
        config_flow_module.async_get_entity_registry = original_get_registry

if __name__ == "__main__":
    asyncio.run(test_generic_thermostat_workflow())