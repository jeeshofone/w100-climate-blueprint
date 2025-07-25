#!/usr/bin/env python3
"""Test script for W100 Smart Control registry integration."""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

class MockHomeAssistant:
    """Mock Home Assistant instance for testing."""
    
    def __init__(self):
        self.data = {}
        self.states = Mock()
        self.config_entries = Mock()
        self.helpers = Mock()
        self.config = Mock()
        self.config.config_dir = "/tmp/test_config"
        
    async def async_create_task(self, coro):
        """Mock async_create_task."""
        return await coro

class MockConfigEntry:
    """Mock config entry for testing."""
    
    def __init__(self):
        self.entry_id = "test_entry_id"
        self.data = {
            "w100_device_name": "living_room_w100",
            "climate_entity_type": "existing",
            "existing_climate_entity": "climate.living_room_thermostat",
            "beep_mode": "On-Mode Change",
            "heating_temperature": 25.0,
            "idle_temperature": 20.0,
        }
        
    def add_update_listener(self, callback):
        """Mock add_update_listener."""
        return Mock()
        
    def async_on_unload(self, callback):
        """Mock async_on_unload."""
        pass

class MockDeviceRegistry:
    """Mock device registry for testing."""
    
    def __init__(self):
        self.devices = {}
        
    def async_get_or_create(self, **kwargs):
        """Mock device creation."""
        device_id = f"device_{len(self.devices)}"
        device = Mock()
        device.id = device_id
        device.identifiers = kwargs.get("identifiers", set())
        device.name = kwargs.get("name", "Test Device")
        device.manufacturer = kwargs.get("manufacturer", "Test")
        device.model = kwargs.get("model", "Test Model")
        
        self.devices[device_id] = device
        _LOGGER.info("Created mock device: %s (%s)", device.name, device_id)
        return device
        
    def async_get_device(self, identifiers):
        """Mock device lookup."""
        for device in self.devices.values():
            if device.identifiers == identifiers:
                return device
        return None
        
    def async_get(self, device_id):
        """Mock device get by ID."""
        return self.devices.get(device_id)

class MockEntityRegistry:
    """Mock entity registry for testing."""
    
    def __init__(self):
        self.entities = {}
        
    def async_get_or_create(self, **kwargs):
        """Mock entity creation."""
        entity_id = kwargs.get("suggested_object_id", f"test_entity_{len(self.entities)}")
        entity = Mock()
        entity.entity_id = f"{kwargs.get('domain', 'test')}.{entity_id}"
        entity.unique_id = kwargs.get("unique_id", f"unique_{len(self.entities)}")
        entity.device_id = kwargs.get("device_id")
        entity.original_name = kwargs.get("original_name", "Test Entity")
        
        self.entities[entity.entity_id] = entity
        _LOGGER.info("Created mock entity: %s (%s)", entity.original_name, entity.entity_id)
        return entity
        
    def async_update_entity(self, entity_id, **kwargs):
        """Mock entity update."""
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            for key, value in kwargs.items():
                setattr(entity, key, value)
            _LOGGER.info("Updated mock entity: %s", entity_id)

async def test_device_registry_integration():
    """Test W100 device registry integration."""
    _LOGGER.info("Testing W100 device registry integration...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    device_registry = MockDeviceRegistry()
    entity_registry = MockEntityRegistry()
    
    # Mock the registry imports
    with patch('custom_components.w100_smart_control.coordinator.dr') as mock_dr, \
         patch('custom_components.w100_smart_control.coordinator.er') as mock_er:
        
        mock_dr.async_get.return_value = device_registry
        mock_er.async_get.return_value = entity_registry
        
        # Import and test the coordinator
        from custom_components.w100_smart_control.coordinator import W100Coordinator
        
        coordinator = W100Coordinator(hass, entry)
        
        # Test logical device creation (not physical W100 device)
        device_name = "living_room_w100"
        device_id = await coordinator._async_create_logical_device(device_name)
        
        # Verify logical device was created
        assert device_id in device_registry.devices
        device = device_registry.devices[device_id]
        assert "W100 Control" in device.name
        assert device.manufacturer == "W100 Smart Control Integration"
        assert device.model == "Climate Controller"
        
        _LOGGER.info("✓ Logical device creation test passed")
        
        # Test proxy climate entity registration
        entity_id = "climate.w100_living_room_control"
        await coordinator.async_register_proxy_climate_entity(device_name, entity_id)
        
        # Verify entity was created and linked to device
        climate_entities = [e for e in entity_registry.entities.values() 
                          if e.entity_id.startswith("climate.")]
        assert len(climate_entities) > 0
        
        climate_entity = climate_entities[0]
        assert climate_entity.device_id == device_id
        assert "w100_smart_control" in climate_entity.unique_id
        
        _LOGGER.info("✓ Proxy climate entity registration test passed")

async def test_climate_entity_device_info():
    """Test climate entity device info configuration."""
    _LOGGER.info("Testing climate entity device info...")
    
    # Mock the climate entity setup
    with patch('custom_components.w100_smart_control.climate.DOMAIN', 'w100_smart_control'):
        from custom_components.w100_smart_control.climate import W100ClimateEntity
        
        # Create mock coordinator and config entry
        coordinator = Mock()
        config_entry = MockConfigEntry()
        
        # Create climate entity
        climate_entity = W100ClimateEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            target_climate_entity="climate.test_thermostat",
            device_name="test_w100"
        )
        
        # Check device info (should reference logical device, not physical W100)
        device_info = climate_entity._attr_device_info
        assert device_info is not None
        assert device_info["manufacturer"] == "W100 Smart Control Integration"
        assert device_info["model"] == "Climate Controller"
        assert "w100_control_test_w100" in str(device_info["identifiers"])
        assert "configuration_url" in device_info
        
        _LOGGER.info("✓ Climate entity device info test passed")

async def test_entity_customization_support():
    """Test entity customization support."""
    _LOGGER.info("Testing entity customization support...")
    
    # Mock entity registry
    entity_registry = MockEntityRegistry()
    
    with patch('custom_components.w100_smart_control.coordinator.er') as mock_er:
        mock_er.async_get.return_value = entity_registry
        
        from custom_components.w100_smart_control.coordinator import W100Coordinator
        
        hass = MockHomeAssistant()
        entry = MockConfigEntry()
        coordinator = W100Coordinator(hass, entry)
        
        # Test thermostat entity registration with customization
        entity_id = "climate.test_thermostat"
        config = {
            "unique_id": "w100_test_thermostat",
            "name": "Test W100 Thermostat",
            "device_id": "test_device_id"
        }
        
        await coordinator._async_register_thermostat_entity(entity_id, config)
        
        # Verify entity was registered with customization support
        assert entity_id in entity_registry.entities
        entity = entity_registry.entities[entity_id]
        assert entity.unique_id == "w100_test_thermostat"
        assert entity.original_name == "Test W100 Thermostat"
        
        _LOGGER.info("✓ Entity customization support test passed")

async def test_no_zigbee2mqtt_conflicts():
    """Test that integration doesn't conflict with Zigbee2MQTT device registration."""
    _LOGGER.info("Testing no conflicts with Zigbee2MQTT...")
    
    device_registry = MockDeviceRegistry()
    
    # Simulate existing Zigbee2MQTT device
    z2m_device = device_registry.async_get_or_create(
        config_entry_id="zigbee2mqtt_entry",
        identifiers={("zigbee2mqtt", "living_room_w100")},
        name="Aqara W100 Living Room",
        manufacturer="Aqara",
        model="W100",
        via_device=("zigbee2mqtt", "coordinator")
    )
    
    with patch('custom_components.w100_smart_control.coordinator.dr') as mock_dr:
        mock_dr.async_get.return_value = device_registry
        
        from custom_components.w100_smart_control.coordinator import W100Coordinator
        
        hass = MockHomeAssistant()
        entry = MockConfigEntry()
        coordinator = W100Coordinator(hass, entry)
        
        # Create our logical device
        device_name = "living_room_w100"
        logical_device_id = await coordinator._async_create_logical_device(device_name)
        
        # Verify we created a separate logical device, not conflicting with Z2M
        logical_device = device_registry.devices[logical_device_id]
        
        # Check identifiers are different
        z2m_identifiers = {("zigbee2mqtt", "living_room_w100")}
        logical_identifiers = {("w100_smart_control", "w100_control_living_room_w100")}
        
        assert z2m_device.identifiers == z2m_identifiers
        assert logical_device.identifiers == logical_identifiers
        assert z2m_device.identifiers != logical_device.identifiers
        
        # Check manufacturers are different
        assert z2m_device.manufacturer == "Aqara"
        assert logical_device.manufacturer == "W100 Smart Control Integration"
        
        _LOGGER.info("✓ No Zigbee2MQTT conflicts test passed")

async def main():
    """Run all registry integration tests."""
    _LOGGER.info("Starting W100 Smart Control registry integration tests...")
    
    try:
        await test_device_registry_integration()
        await test_climate_entity_device_info()
        await test_entity_customization_support()
        await test_no_zigbee2mqtt_conflicts()
        
        _LOGGER.info("🎉 All registry integration tests passed!")
        
    except Exception as err:
        _LOGGER.error("❌ Registry integration test failed: %s", err)
        raise

if __name__ == "__main__":
    asyncio.run(main())