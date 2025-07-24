#!/usr/bin/env python3
"""Test script for W100 Smart Control entity registry integration."""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

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

class MockConfigEntry:
    """Mock config entry for testing."""
    
    def __init__(self):
        self.entry_id = "test_entry_id"
        self.data = {
            "w100_device_name": "living_room_w100",
            "climate_entity_type": "existing",
            "existing_climate_entity": "climate.living_room_thermostat",
            "beep_mode": "On-Mode Change",
        }

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
        entity.entity_category = kwargs.get("entity_category")
        entity.original_icon = kwargs.get("original_icon")
        
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

class MockCoordinator:
    """Mock coordinator for testing."""
    
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.last_update_success = True
        self._device_configs = {}
        
    async def _async_create_logical_device(self, device_name):
        """Mock logical device creation."""
        return f"logical_device_{device_name}"
        
    async def _async_save_device_data(self):
        """Mock save device data."""
        pass

async def test_sensor_entity_registry_integration():
    """Test sensor entity registry integration."""
    _LOGGER.info("Testing sensor entity registry integration...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    device_registry = MockDeviceRegistry()
    entity_registry = MockEntityRegistry()
    
    with patch('custom_components.w100_smart_control.coordinator.dr') as mock_dr, \
         patch('custom_components.w100_smart_control.coordinator.er') as mock_er:
        
        mock_dr.async_get.return_value = device_registry
        mock_er.async_get.return_value = entity_registry
        
        # Import coordinator and create instance
        from custom_components.w100_smart_control.coordinator import W100Coordinator
        coordinator = W100Coordinator(hass, entry)
        
        # Test sensor entity registration
        device_name = "living_room_w100"
        entity_id = "sensor.w100_living_room_w100_humidity"
        sensor_type = "humidity"
        
        await coordinator.async_register_sensor_entity(device_name, entity_id, sensor_type)
        
        # Verify logical device was created
        logical_device_identifiers = {("w100_smart_control", "w100_control_living_room_w100")}
        logical_device = None
        for device in device_registry.devices.values():
            if device.identifiers == logical_device_identifiers:
                logical_device = device
                break
        
        assert logical_device is not None
        assert "W100 Control" in logical_device.name
        
        # Verify sensor entity was registered
        sensor_entities = [e for e in entity_registry.entities.values() 
                          if e.entity_id.startswith("sensor.")]
        assert len(sensor_entities) > 0
        
        sensor_entity = sensor_entities[0]
        assert sensor_entity.unique_id == "w100_smart_control_living_room_w100_humidity"
        assert sensor_entity.device_id == logical_device.id
        assert sensor_entity.original_icon == "mdi:water-percent"
        assert sensor_entity.entity_category is None  # Humidity is not diagnostic
        
        _LOGGER.info("✓ Sensor entity registry integration test passed")

async def test_switch_entity_registry_integration():
    """Test switch entity registry integration."""
    _LOGGER.info("Testing switch entity registry integration...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    device_registry = MockDeviceRegistry()
    entity_registry = MockEntityRegistry()
    
    with patch('custom_components.w100_smart_control.coordinator.dr') as mock_dr, \
         patch('custom_components.w100_smart_control.coordinator.er') as mock_er:
        
        mock_dr.async_get.return_value = device_registry
        mock_er.async_get.return_value = entity_registry
        
        # Import coordinator and create instance
        from custom_components.w100_smart_control.coordinator import W100Coordinator
        coordinator = W100Coordinator(hass, entry)
        
        # Test switch entity registration
        device_name = "living_room_w100"
        entity_id = "switch.w100_living_room_w100_beep_control"
        switch_type = "beep_control"
        
        await coordinator.async_register_switch_entity(device_name, entity_id, switch_type)
        
        # Verify logical device was created
        logical_device_identifiers = {("w100_smart_control", "w100_control_living_room_w100")}
        logical_device = None
        for device in device_registry.devices.values():
            if device.identifiers == logical_device_identifiers:
                logical_device = device
                break
        
        assert logical_device is not None
        assert "W100 Control" in logical_device.name
        
        # Verify switch entity was registered
        switch_entities = [e for e in entity_registry.entities.values() 
                          if e.entity_id.startswith("switch.")]
        assert len(switch_entities) > 0
        
        switch_entity = switch_entities[0]
        assert switch_entity.unique_id == "w100_smart_control_living_room_w100_beep_control"
        assert switch_entity.device_id == logical_device.id
        assert switch_entity.original_icon == "mdi:volume-high"
        assert switch_entity.entity_category is None  # Beep control is not config
        
        _LOGGER.info("✓ Switch entity registry integration test passed")

async def test_diagnostic_sensor_categorization():
    """Test diagnostic sensor entity categorization."""
    _LOGGER.info("Testing diagnostic sensor categorization...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    device_registry = MockDeviceRegistry()
    entity_registry = MockEntityRegistry()
    
    with patch('custom_components.w100_smart_control.coordinator.dr') as mock_dr, \
         patch('custom_components.w100_smart_control.coordinator.er') as mock_er:
        
        mock_dr.async_get.return_value = device_registry
        mock_er.async_get.return_value = entity_registry
        
        # Import coordinator and create instance
        from custom_components.w100_smart_control.coordinator import W100Coordinator
        coordinator = W100Coordinator(hass, entry)
        
        # Test diagnostic sensor registration
        device_name = "living_room_w100"
        entity_id = "sensor.w100_living_room_w100_diagnostic"
        sensor_type = "diagnostic"
        
        await coordinator.async_register_sensor_entity(device_name, entity_id, sensor_type)
        
        # Verify diagnostic sensor was categorized correctly
        diagnostic_entities = [e for e in entity_registry.entities.values() 
                              if e.entity_category == "diagnostic"]
        assert len(diagnostic_entities) > 0
        
        diagnostic_entity = diagnostic_entities[0]
        assert diagnostic_entity.unique_id == "w100_smart_control_living_room_w100_diagnostic"
        assert diagnostic_entity.original_icon == "mdi:bug-outline"
        assert diagnostic_entity.entity_category == "diagnostic"
        
        _LOGGER.info("✓ Diagnostic sensor categorization test passed")

async def test_config_switch_categorization():
    """Test config switch entity categorization."""
    _LOGGER.info("Testing config switch categorization...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    device_registry = MockDeviceRegistry()
    entity_registry = MockEntityRegistry()
    
    with patch('custom_components.w100_smart_control.coordinator.dr') as mock_dr, \
         patch('custom_components.w100_smart_control.coordinator.er') as mock_er:
        
        mock_dr.async_get.return_value = device_registry
        mock_er.async_get.return_value = entity_registry
        
        # Import coordinator and create instance
        from custom_components.w100_smart_control.coordinator import W100Coordinator
        coordinator = W100Coordinator(hass, entry)
        
        # Test config switch registration
        device_name = "living_room_w100"
        entity_id = "switch.w100_living_room_w100_display_sync"
        switch_type = "display_sync"
        
        await coordinator.async_register_switch_entity(device_name, entity_id, switch_type)
        
        # Verify config switch was categorized correctly
        config_entities = [e for e in entity_registry.entities.values() 
                          if e.entity_category == "config"]
        assert len(config_entities) > 0
        
        config_entity = config_entities[0]
        assert config_entity.unique_id == "w100_smart_control_living_room_w100_display_sync"
        assert config_entity.original_icon == "mdi:monitor-dashboard"
        assert config_entity.entity_category == "config"
        
        _LOGGER.info("✓ Config switch categorization test passed")

async def main():
    """Run all entity registry integration tests."""
    _LOGGER.info("Starting W100 Smart Control entity registry integration tests...")
    
    try:
        await test_sensor_entity_registry_integration()
        await test_switch_entity_registry_integration()
        await test_diagnostic_sensor_categorization()
        await test_config_switch_categorization()
        
        _LOGGER.info("🎉 All entity registry integration tests passed!")
        
    except Exception as err:
        _LOGGER.error("❌ Entity registry integration test failed: %s", err)
        raise

if __name__ == "__main__":
    asyncio.run(main())