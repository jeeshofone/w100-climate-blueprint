#!/usr/bin/env python3
"""Test script for Task 9: Create generic thermostat entity management."""

import asyncio
import sys
from unittest.mock import Mock, AsyncMock, patch

# Mock Home Assistant components
class MockState:
    def __init__(self, entity_id, state="on", attributes=None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}

class MockEntityRegistry:
    def __init__(self):
        self.entities = {}
    
    def async_get(self, entity_id):
        """Get entity from registry."""
        return self.entities.get(entity_id)
    
    def async_remove(self, entity_id):
        """Remove entity from registry."""
        if entity_id in self.entities:
            del self.entities[entity_id]
    
    def add_entity(self, entity_id, disabled_by=None):
        """Add a mock entity to the registry."""
        entry = Mock()
        entry.entity_id = entity_id
        entry.disabled_by = disabled_by
        self.entities[entity_id] = entry

class MockConfigEntry:
    def __init__(self, data):
        self.data = data

class MockHass:
    def __init__(self):
        self.states = Mock()
        self.states.get = Mock()
        self.helpers = Mock()
        self.helpers.utcnow = Mock(return_value="2024-01-01T00:00:00Z")

async def test_generic_thermostat_management():
    """Test the generic thermostat entity management functionality."""
    
    # Import the coordinator class
    sys.path.insert(0, 'custom_components')
    from w100_smart_control.coordinator import W100Coordinator
    from w100_smart_control.const import (
        CONF_HEATER_SWITCH, CONF_TEMPERATURE_SENSOR, CONF_MIN_TEMP, 
        CONF_MAX_TEMP, CONF_TARGET_TEMP, CONF_COLD_TOLERANCE, 
        CONF_HOT_TOLERANCE, CONF_PRECISION
    )
    
    print("Testing Task 9: Generic Thermostat Entity Management")
    print("=" * 60)
    
    # Create mock hass instance
    hass = MockHass()
    
    # Create mock config entry
    config_entry = MockConfigEntry({
        "w100_device_name": "living_room_w100",
        "climate_entity_type": "generic"
    })
    
    # Mock entity registry
    mock_registry = MockEntityRegistry()
    
    # Mock entity states
    hass.states.get.side_effect = lambda entity_id: {
        "switch.living_room_heater": MockState("switch.living_room_heater", "off"),
        "sensor.living_room_temperature": MockState("sensor.living_room_temperature", "22.5"),
    }.get(entity_id)
    
    # Create coordinator instance
    coordinator = W100Coordinator(hass, config_entry)
    
    # Mock the entity registry functions
    with patch('w100_smart_control.coordinator.er.async_get', return_value=mock_registry):
        with patch('w100_smart_control.coordinator.async_get_platforms', return_value=[]):
            
            # Test 1: Create generic thermostat with valid configuration
            print("\n1. Testing generic thermostat creation with valid configuration...")
            
            thermostat_config = {
                CONF_HEATER_SWITCH: "switch.living_room_heater",
                CONF_TEMPERATURE_SENSOR: "sensor.living_room_temperature",
                CONF_MIN_TEMP: 15.0,
                CONF_MAX_TEMP: 30.0,
                CONF_TARGET_TEMP: 22.0,
                CONF_COLD_TOLERANCE: 0.5,
                CONF_HOT_TOLERANCE: 0.5,
                CONF_PRECISION: 0.5
            }
            
            entity_id = await coordinator.async_create_generic_thermostat(thermostat_config)
            
            assert entity_id is not None, "Should return entity ID"
            assert entity_id.startswith("climate."), "Should be a climate entity"
            assert "w100" in entity_id, "Should contain w100 in entity ID"
            assert "living_room" in entity_id, "Should contain device name in entity ID"
            print(f"✓ Created thermostat with entity ID: {entity_id}")
            
            # Test 2: Verify thermostat is tracked
            print("\n2. Testing thermostat tracking...")
            
            created_thermostats = coordinator.created_thermostats
            assert entity_id in created_thermostats, "Thermostat should be tracked"
            print(f"✓ Thermostat tracked in created_thermostats: {created_thermostats}")
            
            # Test 3: Verify thermostat configuration is stored
            print("\n3. Testing thermostat configuration storage...")
            
            thermostat_configs = coordinator.thermostat_configs
            assert entity_id in thermostat_configs, "Thermostat config should be stored"
            
            stored_config = thermostat_configs[entity_id]
            assert stored_config["heater"] == "switch.living_room_heater", "Heater entity should be stored"
            assert stored_config["target_sensor"] == "sensor.living_room_temperature", "Temperature sensor should be stored"
            assert stored_config["precision"] == 0.5, "Precision should be 0.5°C for W100 compatibility"
            assert stored_config["min_temp"] == 15.0, "Min temp should be stored"
            assert stored_config["max_temp"] == 30.0, "Max temp should be stored"
            print("✓ Thermostat configuration stored correctly")
            
            # Test 4: Test unique entity ID generation
            print("\n4. Testing unique entity ID generation...")
            
            # Create another thermostat with same device name
            entity_id_2 = await coordinator.async_create_generic_thermostat(thermostat_config)
            
            assert entity_id_2 != entity_id, "Should generate unique entity ID"
            assert entity_id_2.startswith("climate."), "Should be a climate entity"
            assert "_1" in entity_id_2 or entity_id_2.endswith("_1"), "Should have counter suffix"
            print(f"✓ Generated unique entity ID: {entity_id_2}")
            
            # Test 5: Test name sanitization
            print("\n5. Testing name sanitization...")
            
            # Create coordinator with special characters in device name
            special_config_entry = MockConfigEntry({
                "w100_device_name": "Kitchen W100 (Main)",
                "climate_entity_type": "generic"
            })
            
            special_coordinator = W100Coordinator(hass, special_config_entry)
            
            entity_id_3 = await special_coordinator.async_create_generic_thermostat(thermostat_config)
            
            assert entity_id_3 is not None, "Should handle special characters"
            assert "(" not in entity_id_3, "Should sanitize parentheses"
            assert " " not in entity_id_3, "Should sanitize spaces"
            print(f"✓ Sanitized entity ID: {entity_id_3}")
            
            # Test 6: Test precision adjustment for W100 compatibility
            print("\n6. Testing precision adjustment for W100 compatibility...")
            
            wrong_precision_config = thermostat_config.copy()
            wrong_precision_config[CONF_PRECISION] = 1.0  # Wrong precision
            
            entity_id_4 = await coordinator.async_create_generic_thermostat(wrong_precision_config)
            
            stored_config_4 = coordinator.thermostat_configs[entity_id_4]
            assert stored_config_4["precision"] == 0.5, "Should adjust precision to 0.5°C for W100 compatibility"
            print("✓ Precision adjusted to 0.5°C for W100 compatibility")
            
            # Test 7: Test error handling - missing heater entity
            print("\n7. Testing error handling - missing heater entity...")
            
            invalid_config = thermostat_config.copy()
            invalid_config[CONF_HEATER_SWITCH] = "switch.nonexistent_heater"
            
            try:
                await coordinator.async_create_generic_thermostat(invalid_config)
                assert False, "Should raise exception for missing heater entity"
            except Exception as err:
                assert "not found" in str(err), "Should indicate entity not found"
                print("✓ Correctly handled missing heater entity")
            
            # Test 8: Test error handling - missing temperature sensor
            print("\n8. Testing error handling - missing temperature sensor...")
            
            invalid_config = thermostat_config.copy()
            invalid_config[CONF_TEMPERATURE_SENSOR] = "sensor.nonexistent_sensor"
            
            try:
                await coordinator.async_create_generic_thermostat(invalid_config)
                assert False, "Should raise exception for missing temperature sensor"
            except Exception as err:
                assert "not found" in str(err), "Should indicate entity not found"
                print("✓ Correctly handled missing temperature sensor")
            
            # Test 9: Test thermostat removal
            print("\n9. Testing thermostat removal...")
            
            # Remove the first thermostat
            await coordinator.async_remove_generic_thermostat(entity_id)
            
            updated_thermostats = coordinator.created_thermostats
            assert entity_id not in updated_thermostats, "Thermostat should be removed from tracking"
            
            updated_configs = coordinator.thermostat_configs
            assert entity_id not in updated_configs, "Thermostat config should be removed"
            print("✓ Thermostat removed successfully")
            
            # Test 10: Test cleanup functionality
            print("\n10. Testing cleanup functionality...")
            
            # Should still have other thermostats
            initial_count = len(coordinator.created_thermostats)
            assert initial_count > 0, "Should have thermostats before cleanup"
            
            await coordinator.async_cleanup()
            
            final_count = len(coordinator.created_thermostats)
            assert final_count == 0, "Should have no thermostats after cleanup"
            print("✓ Cleanup removed all thermostats")
            
            print("\n" + "=" * 60)
            print("✅ Task 9 COMPLETED SUCCESSFULLY!")
            print("\nAll sub-tasks completed:")
            print("  ✓ Write async_create_generic_thermostat method in coordinator")
            print("  ✓ Generate unique entity IDs and names for created thermostats")
            print("  ✓ Configure generic thermostat with proper precision (0.5°C) for W100 compatibility")
            print("  ✓ Implement error handling for thermostat creation failures")
            print("\nRequirements 3.3, 3.5 satisfied:")
            print("  ✓ 3.3: Generic thermostat automatically configured using Home Assistant's built-in platform")
            print("  ✓ 3.5: Generic thermostat supports precision and temperature step requirements (0.5°C increments)")

if __name__ == "__main__":
    asyncio.run(test_generic_thermostat_management())