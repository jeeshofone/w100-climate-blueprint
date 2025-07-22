#!/usr/bin/env python3
"""Test script for climate selection UI improvements."""

import asyncio
import sys
from unittest.mock import Mock, AsyncMock
import voluptuous as vol

# Mock Home Assistant components
class MockState:
    def __init__(self, entity_id, state="heat", attributes=None):
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

async def test_climate_ui_improvements():
    """Test UI improvements for climate entity selection."""
    
    # Import the config flow class
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.config_flow import W100ConfigFlow
    
    # Create mock hass instance
    hass = MockHass()
    
    # Create config flow instance
    flow = W100ConfigFlow()
    flow.hass = hass
    flow._config = {"w100_device_name": "test_w100"}
    
    print("Testing climate selection UI improvements...")
    
    # Mock entity registry
    mock_registry = MockEntityRegistry()
    mock_registry.add_entity("climate.thermostat1")
    
    # Mock the entity registry function
    import w100_smart_control.config_flow as config_flow_module
    original_get_registry = config_flow_module.async_get_entity_registry
    config_flow_module.async_get_entity_registry = Mock(return_value=mock_registry)
    
    try:
        # Test 1: Test that selecting "existing" without available entities shows error
        print("\n1. Testing 'existing' selection with no available entities...")
        flow._available_climate_entities = []  # No entities available
        
        user_input = {
            "climate_entity_type": "existing"
        }
        
        result = await flow.async_step_climate_selection(user_input)
        print(f"Result type: {result['type']}")
        print(f"Errors: {result.get('errors', {})}")
        assert result["type"] == "form", "Should show form again"
        assert "climate_entity_type" in result["errors"], "Should have climate entity type error"
        assert result["errors"]["climate_entity_type"] == "no_climate_entities_available", "Should show correct error"
        
        # Test 2: Test that selecting "existing" with missing entity shows error
        print("\n2. Testing 'existing' selection with missing entity...")
        flow._available_climate_entities = ["climate.thermostat1"]  # Entities available
        
        user_input = {
            "climate_entity_type": "existing"
            # Note: no existing_climate_entity provided
        }
        
        result = await flow.async_step_climate_selection(user_input)
        print(f"Result type: {result['type']}")
        print(f"Errors: {result.get('errors', {})}")
        assert result["type"] == "form", "Should show form again"
        assert "existing_climate_entity" in result["errors"], "Should have existing entity error"
        assert result["errors"]["existing_climate_entity"] == "entity_required", "Should show entity required error"
        
        # Test 3: Test form schema changes based on previous selection
        print("\n3. Testing form schema with 'existing' selection...")
        flow._available_climate_entities = ["climate.thermostat1"]
        
        # Mock state for display
        hass.states.get.return_value = MockState("climate.thermostat1", "heat", {"current_temperature": 22.5})
        
        # Simulate user selecting "existing" (this would be in user_input during validation)
        user_input_with_existing = {
            "climate_entity_type": "existing"
        }
        
        result = await flow.async_step_climate_selection(user_input_with_existing)
        print(f"Result type: {result['type']}")
        
        # Check schema - the existing_climate_entity should be required when "existing" is selected
        schema_dict = result['data_schema'].schema
        schema_keys = [str(key) for key in schema_dict.keys()]
        print(f"Schema keys: {schema_keys}")
        
        # Find the existing_climate_entity key and check if it's required
        existing_entity_key = None
        for key in schema_dict.keys():
            if "existing_climate_entity" in str(key):
                existing_entity_key = key
                break
        
        if existing_entity_key:
            # Check if it's a Required field by looking at the key type
            is_required = str(type(existing_entity_key).__name__) == "Required"
            print(f"Existing climate entity field required: {is_required}")
            print(f"Key type: {type(existing_entity_key).__name__}")
        
        # Test 4: Test successful flow with valid entity
        print("\n4. Testing successful flow with valid entity...")
        flow._config = {"w100_device_name": "test_w100"}  # Reset config
        flow._available_climate_entities = ["climate.thermostat1"]
        
        valid_state = MockState(
            "climate.thermostat1",
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
        
        user_input = {
            "climate_entity_type": "existing",
            "existing_climate_entity": "climate.thermostat1"
        }
        
        result = await flow.async_step_climate_selection(user_input)
        print(f"Result type: {result['type']}")
        print(f"Step ID: {result.get('step_id', 'N/A')}")
        assert result["type"] == "form", "Should proceed to next step"
        assert result.get("step_id") == "customization", "Should go to customization step"
        
        print("\n✅ All climate UI improvement tests passed!")
        
    finally:
        # Restore original function
        config_flow_module.async_get_entity_registry = original_get_registry

if __name__ == "__main__":
    asyncio.run(test_climate_ui_improvements())