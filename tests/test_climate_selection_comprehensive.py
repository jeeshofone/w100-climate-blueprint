#!/usr/bin/env python3
"""Comprehensive test script for climate entity selection functionality."""

import asyncio
import sys
from unittest.mock import Mock, AsyncMock

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

async def test_climate_selection_comprehensive():
    """Test comprehensive climate entity selection scenarios."""
    
    # Import the config flow class
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.config_flow import W100ConfigFlow
    
    # Create mock hass instance
    hass = MockHass()
    
    # Create config flow instance
    flow = W100ConfigFlow()
    flow.hass = hass
    flow._config = {"w100_device_name": "test_w100"}
    
    print("Testing comprehensive climate entity selection...")
    
    # Mock entity registry
    mock_registry = MockEntityRegistry()
    mock_registry.add_entity("climate.thermostat1")
    mock_registry.add_entity("climate.thermostat2")
    mock_registry.add_entity("climate.disabled_thermostat", disabled_by="user")
    
    # Mock the entity registry function
    import w100_smart_control.config_flow as config_flow_module
    original_get_registry = config_flow_module.async_get_entity_registry
    config_flow_module.async_get_entity_registry = Mock(return_value=mock_registry)
    
    try:
        # Test 1: Get available climate entities
        print("\n1. Testing climate entity discovery...")
        climate_entities = await flow._async_get_climate_entities()
        print(f"Found climate entities: {climate_entities}")
        assert "climate.thermostat1" in climate_entities, "Should find enabled climate entities"
        assert "climate.thermostat2" in climate_entities, "Should find all enabled climate entities"
        assert "climate.disabled_thermostat" not in climate_entities, "Should not include disabled entities"
        
        # Test 2: Test climate selection with valid existing entity
        print("\n2. Testing climate selection with valid existing entity...")
        # Set available climate entities for the flow
        flow._available_climate_entities = ["climate.thermostat1", "climate.thermostat2"]
        
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
        
        # This should succeed and move to customization step
        result = await flow.async_step_climate_selection(user_input)
        print(f"Result type: {result['type']}")
        print(f"Step ID: {result.get('step_id', 'N/A')}")
        print(f"Errors: {result.get('errors', {})}")
        if result["type"] == "form" and result.get("step_id") == "climate_selection":
            print("Form was shown again, likely due to validation error")
        assert result["type"] == "form", "Should proceed to next step"
        if result.get("step_id") == "customization":
            print("✅ Successfully moved to customization step")
        elif result.get("step_id") == "climate_selection":
            print("⚠️  Form shown again - checking for validation issues")
        
        # For this test, we expect to move to customization step
        assert result.get("step_id") == "customization", f"Should go to customization step, got {result.get('step_id')}"
        
        # Test 3: Test climate selection with invalid entity
        print("\n3. Testing climate selection with invalid entity...")
        flow._config = {"w100_device_name": "test_w100"}  # Reset config
        flow._available_climate_entities = ["climate.no_heat"]  # Set available entities
        
        invalid_state = MockState(
            "climate.no_heat",
            "cool",
            {
                "hvac_modes": ["cool", "off"],  # Missing heat mode
                "supported_features": ["temperature"],
                "current_temperature": 22.5,
                "target_temperature": 24.0
            }
        )
        hass.states.get.return_value = invalid_state
        
        user_input = {
            "climate_entity_type": "existing",
            "existing_climate_entity": "climate.no_heat"
        }
        
        result = await flow.async_step_climate_selection(user_input)
        print(f"Result type: {result['type']}")
        print(f"Errors: {result.get('errors', {})}")
        assert result["type"] == "form", "Should show form again with errors"
        assert "existing_climate_entity" in result["errors"], "Should have climate entity error"
        assert result["errors"]["existing_climate_entity"] == "heat_mode_not_supported", "Should show correct error"
        
        # Test 4: Test climate selection with generic thermostat option
        print("\n4. Testing climate selection with generic thermostat option...")
        flow._config = {"w100_device_name": "test_w100"}  # Reset config
        flow._available_climate_entities = []  # No climate entities available
        
        user_input = {
            "climate_entity_type": "generic"
        }
        
        result = await flow.async_step_climate_selection(user_input)
        print(f"Result type: {result['type']}")
        assert result["type"] == "form", "Should proceed to next step"
        assert result["step_id"] == "generic_thermostat", "Should go to generic thermostat step"
        
        # Test 5: Test climate selection form display
        print("\n5. Testing climate selection form display...")
        flow._config = {"w100_device_name": "test_w100"}  # Reset config
        flow._available_climate_entities = ["climate.thermostat1", "climate.thermostat2"]
        
        # Mock states for display
        hass.states.get.side_effect = lambda entity_id: {
            "climate.thermostat1": MockState("climate.thermostat1", "heat", {"current_temperature": 22.5}),
            "climate.thermostat2": MockState("climate.thermostat2", "off", {"current_temperature": 20.0})
        }.get(entity_id)
        
        result = await flow.async_step_climate_selection(None)
        print(f"Result type: {result['type']}")
        print(f"Schema keys: {list(result['data_schema'].schema.keys())}")
        assert result["type"] == "form", "Should show form"
        assert result["step_id"] == "climate_selection", "Should be climate selection step"
        
        # Verify schema contains both options
        schema_keys = [str(key) for key in result['data_schema'].schema.keys()]
        assert any("climate_entity_type" in key for key in schema_keys), "Should have climate entity type selector"
        assert any("existing_climate_entity" in key for key in schema_keys), "Should have existing entity selector"
        
        print("\n✅ All comprehensive climate selection tests passed!")
        
    finally:
        # Restore original function
        config_flow_module.async_get_entity_registry = original_get_registry

if __name__ == "__main__":
    asyncio.run(test_climate_selection_comprehensive())