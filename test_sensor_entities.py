#!/usr/bin/env python3
"""Test script for W100 Smart Control sensor entities."""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

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
            "humidity_sensor": "sensor.living_room_humidity",
            "backup_humidity_sensor": "sensor.backup_humidity",
        }

class MockCoordinator:
    """Mock coordinator for testing."""
    
    def __init__(self):
        self.last_update_success = True
        self.last_exception = None
        self.data = {
            "device_name": "living_room_w100",
            "status": "connected",
            "last_update": datetime.now(),
            "created_thermostats": 1,
            "device_states": {
                "living_room_w100": {
                    "humidity": 45,
                    "last_action": "toggle",
                    "last_action_time": datetime.now() - timedelta(minutes=2),
                    "display_mode": "temperature",
                    "connection_status": "connected",
                    "current_mode": "heat",
                    "target_temperature": 22.0,
                    "current_temperature": 21.5,
                    "fan_speed": 3,
                    "last_update": datetime.now(),
                }
            }
        }
        self._listeners = []
    
    def async_add_listener(self, callback):
        """Mock add listener."""
        self._listeners.append(callback)
    
    def async_remove_listener(self, callback):
        """Mock remove listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

async def test_humidity_sensor():
    """Test W100 humidity sensor."""
    _LOGGER.info("Testing W100 humidity sensor...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Import and test the sensor
    from custom_components.w100_smart_control.sensor import W100HumiditySensor
    
    sensor = W100HumiditySensor(coordinator, entry, "living_room_w100")
    
    # Test basic properties
    assert sensor.unique_id == "w100_smart_control_living_room_w100_humidity"
    assert "W100 Living Room W100 Humidity" in sensor.name
    assert sensor.device_class == "humidity"
    assert sensor.native_unit_of_measurement == "%"
    assert sensor.available is True
    
    # Test humidity value
    assert sensor.native_value == 45
    
    # Test attributes
    attributes = sensor.extra_state_attributes
    assert attributes["w100_device_name"] == "living_room_w100"
    assert attributes["sensor_type"] == "humidity_display"
    assert attributes["primary_humidity_sensor"] == "sensor.living_room_humidity"
    assert attributes["backup_humidity_sensor"] == "sensor.backup_humidity"
    
    _LOGGER.info("✓ Humidity sensor test passed")

async def test_status_sensor():
    """Test W100 status sensor."""
    _LOGGER.info("Testing W100 status sensor...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Import and test the sensor
    from custom_components.w100_smart_control.sensor import W100StatusSensor
    
    sensor = W100StatusSensor(coordinator, entry, "living_room_w100")
    
    # Test basic properties
    assert sensor.unique_id == "w100_smart_control_living_room_w100_status"
    assert "W100 Living Room W100 Status" in sensor.name
    assert sensor.available is True
    
    # Test status value
    assert sensor.native_value == "active - last: toggle"
    
    # Test attributes
    attributes = sensor.extra_state_attributes
    assert attributes["w100_device_name"] == "living_room_w100"
    assert attributes["sensor_type"] == "status"
    assert attributes["last_action"] == "toggle"
    assert attributes["display_mode"] == "temperature"
    assert attributes["current_mode"] == "heat"
    assert attributes["created_thermostats"] == 1
    
    _LOGGER.info("✓ Status sensor test passed")

async def test_connection_sensor():
    """Test W100 connection sensor."""
    _LOGGER.info("Testing W100 connection sensor...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Import and test the sensor
    from custom_components.w100_smart_control.sensor import W100ConnectionSensor
    
    sensor = W100ConnectionSensor(coordinator, entry, "living_room_w100")
    
    # Test basic properties
    assert sensor.unique_id == "w100_smart_control_living_room_w100_connection"
    assert "W100 Living Room W100 Connection" in sensor.name
    assert sensor.available is True
    assert sensor.entity_category == "diagnostic"
    
    # Test connection status (should be connected due to recent activity)
    assert sensor.native_value == "connected"
    
    # Test attributes
    attributes = sensor.extra_state_attributes
    assert attributes["w100_device_name"] == "living_room_w100"
    assert attributes["sensor_type"] == "connection"
    assert attributes["coordinator_last_update_success"] is True
    assert "seconds_since_last_action" in attributes
    
    _LOGGER.info("✓ Connection sensor test passed")

async def test_diagnostic_sensor():
    """Test W100 diagnostic sensor."""
    _LOGGER.info("Testing W100 diagnostic sensor...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Import and test the sensor
    from custom_components.w100_smart_control.sensor import W100DiagnosticSensor
    
    sensor = W100DiagnosticSensor(coordinator, entry, "living_room_w100")
    
    # Test basic properties
    assert sensor.unique_id == "w100_smart_control_living_room_w100_diagnostic"
    assert "W100 Living Room W100 Diagnostic" in sensor.name
    assert sensor.available is True
    assert sensor.entity_category == "diagnostic"
    
    # Test diagnostic status (should be ok)
    assert sensor.native_value == "ok"
    
    # Test attributes
    attributes = sensor.extra_state_attributes
    assert attributes["w100_device_name"] == "living_room_w100"
    assert attributes["sensor_type"] == "diagnostic"
    assert attributes["config_entry_id"] == "test_entry_id"
    assert attributes["climate_entity_type"] == "existing"
    assert attributes["existing_climate_entity"] == "climate.living_room_thermostat"
    assert attributes["device_current_mode"] == "heat"
    assert attributes["device_target_temperature"] == 22.0
    assert attributes["total_device_states"] == 1
    
    _LOGGER.info("✓ Diagnostic sensor test passed")

async def test_sensor_platform_setup():
    """Test sensor platform setup."""
    _LOGGER.info("Testing sensor platform setup...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    hass.data["w100_smart_control"] = {"test_entry_id": MockCoordinator()}
    
    entry = MockConfigEntry()
    entities_added = []
    
    def mock_add_entities(entities):
        entities_added.extend(entities)
    
    # Import and test the setup
    from custom_components.w100_smart_control.sensor import async_setup_entry
    
    await async_setup_entry(hass, entry, mock_add_entities)
    
    # Verify entities were created
    assert len(entities_added) == 4
    
    entity_types = [type(entity).__name__ for entity in entities_added]
    assert "W100HumiditySensor" in entity_types
    assert "W100StatusSensor" in entity_types
    assert "W100ConnectionSensor" in entity_types
    assert "W100DiagnosticSensor" in entity_types
    
    _LOGGER.info("✓ Sensor platform setup test passed")

async def main():
    """Run all sensor entity tests."""
    _LOGGER.info("Starting W100 Smart Control sensor entity tests...")
    
    try:
        await test_humidity_sensor()
        await test_status_sensor()
        await test_connection_sensor()
        await test_diagnostic_sensor()
        await test_sensor_platform_setup()
        
        _LOGGER.info("🎉 All sensor entity tests passed!")
        
    except Exception as err:
        _LOGGER.error("❌ Sensor entity test failed: %s", err)
        raise

if __name__ == "__main__":
    asyncio.run(main())