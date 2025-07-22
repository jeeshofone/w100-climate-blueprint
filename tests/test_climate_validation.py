#!/usr/bin/env python3
"""Test script for climate entity validation functionality."""

import asyncio
import sys
from unittest.mock import Mock, AsyncMock

# Mock Home Assistant components
class MockState:
    def __init__(self, entity_id, state="heat", attributes=None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}

class MockHass:
    def __init__(self):
        self.states = Mock()
        self.states.get = Mock()

async def test_climate_validation():
    """Test climate entity validation logic."""
    
    # Import the config flow class
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.config_flow import W100ConfigFlow
    
    # Create mock hass instance
    hass = MockHass()
    
    # Create config flow instance
    flow = W100ConfigFlow()
    flow.hass = hass
    
    print("Testing climate entity validation...")
    
    # Test 1: Valid climate entity
    print("\n1. Testing valid climate entity...")
    valid_state = MockState(
        "climate.test_thermostat",
        "heat",
        {
            "hvac_modes": ["heat", "off", "cool"],
            "supported_features": ["temperature"],
            "current_temperature": 22.5,
            "target_temperature": 24.0,
            "min_temp": 7,
            "max_temp": 35,
            "precision": 0.5
        }
    )
    hass.states.get.return_value = valid_state
    
    result = await flow._async_validate_climate_entity("climate.test_thermostat")
    print(f"Result: {result}")
    assert result["valid"] == True, "Valid climate entity should pass validation"
    
    # Test 2: Climate entity without heat mode
    print("\n2. Testing climate entity without heat mode...")
    invalid_state = MockState(
        "climate.no_heat",
        "cool",
        {
            "hvac_modes": ["cool", "off"],
            "supported_features": ["temperature"],
            "current_temperature": 22.5,
            "target_temperature": 24.0
        }
    )
    hass.states.get.return_value = invalid_state
    
    result = await flow._async_validate_climate_entity("climate.no_heat")
    print(f"Result: {result}")
    assert result["valid"] == False, "Climate entity without heat mode should fail"
    assert result["error"] == "heat_mode_not_supported", "Should return correct error"
    
    # Test 3: Climate entity without off mode
    print("\n3. Testing climate entity without off mode...")
    invalid_state = MockState(
        "climate.no_off",
        "heat",
        {
            "hvac_modes": ["heat", "cool"],
            "supported_features": ["temperature"],
            "current_temperature": 22.5,
            "target_temperature": 24.0
        }
    )
    hass.states.get.return_value = invalid_state
    
    result = await flow._async_validate_climate_entity("climate.no_off")
    print(f"Result: {result}")
    assert result["valid"] == False, "Climate entity without off mode should fail"
    assert result["error"] == "off_mode_not_supported", "Should return correct error"
    
    # Test 4: Non-existent entity
    print("\n4. Testing non-existent entity...")
    hass.states.get.return_value = None
    
    result = await flow._async_validate_climate_entity("climate.nonexistent")
    print(f"Result: {result}")
    assert result["valid"] == False, "Non-existent entity should fail"
    assert result["error"] == "entity_not_found", "Should return correct error"
    
    # Test 5: Unavailable entity
    print("\n5. Testing unavailable entity...")
    unavailable_state = MockState("climate.unavailable", "unavailable")
    hass.states.get.return_value = unavailable_state
    
    result = await flow._async_validate_climate_entity("climate.unavailable")
    print(f"Result: {result}")
    assert result["valid"] == False, "Unavailable entity should fail"
    assert result["error"] == "entity_unavailable", "Should return correct error"
    
    # Test 6: Non-climate entity
    print("\n6. Testing non-climate entity...")
    result = await flow._async_validate_climate_entity("switch.test")
    print(f"Result: {result}")
    assert result["valid"] == False, "Non-climate entity should fail"
    assert result["error"] == "not_climate_entity", "Should return correct error"
    
    print("\n✅ All climate validation tests passed!")

if __name__ == "__main__":
    asyncio.run(test_climate_validation())