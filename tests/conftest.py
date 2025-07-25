"""Global test configuration for W100 Smart Control integration."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.device_registry import DeviceRegistry

# Import the integration components
import sys
import os

# Add the custom components directory to the path
custom_components_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components')
sys.path.insert(0, custom_components_path)

# Add the specific integration path
integration_path = os.path.join(custom_components_path, 'w100_smart_control')
sys.path.insert(0, integration_path)

try:
    from const import DOMAIN
except ImportError:
    # Fallback for testing
    DOMAIN = "w100_smart_control"


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.states = Mock()
    hass.services = Mock()
    hass.config_entries = Mock()
    hass.bus = Mock()
    hass.helpers = Mock()
    
    # Mock common service calls
    hass.services.has_service.return_value = True
    hass.services.async_call = AsyncMock()
    
    # Mock state management
    hass.states.get.return_value = None
    hass.states.async_all.return_value = []
    
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {
        "w100_device_name": "test_w100",
        "existing_climate_entity": "climate.test",
        "heating_temperature": 22.0,
        "idle_temperature": 18.0,
        "beep_mode": "Enable Beep"
    }
    entry.options = {}
    entry.title = "W100 Smart Control Test"
    return entry


@pytest.fixture
def mock_entity_registry():
    """Create a mock entity registry."""
    registry = Mock(spec=EntityRegistry)
    registry.entities = {}
    registry.async_get.return_value = None
    registry.async_get_or_create = Mock()
    registry.async_update_entity = Mock()
    return registry


@pytest.fixture
def mock_device_registry():
    """Create a mock device registry."""
    registry = Mock(spec=DeviceRegistry)
    registry.devices = {}
    registry.async_get.return_value = None
    registry.async_get_or_create = Mock()
    registry.async_get_device = Mock()
    return registry


@pytest.fixture
def mock_mqtt():
    """Mock MQTT integration."""
    with patch('homeassistant.components.mqtt.async_get_mqtt') as mock:
        mqtt_client = Mock()
        mqtt_client.async_subscribe = AsyncMock()
        mqtt_client.async_publish = AsyncMock()
        mock.return_value = mqtt_client
        yield mqtt_client


@pytest.fixture
def mock_climate_entity():
    """Mock climate entity state."""
    state = Mock()
    state.entity_id = "climate.test"
    state.state = "heat"
    state.attributes = {
        "temperature": 20.0,
        "current_temperature": 19.5,
        "hvac_modes": ["off", "heat"],
        "supported_features": 1
    }
    return state


@pytest.fixture
def mock_switch_entity():
    """Mock switch entity state."""
    state = Mock()
    state.entity_id = "switch.test_heater"
    state.state = STATE_OFF
    state.attributes = {}
    return state


@pytest.fixture
def mock_sensor_entity():
    """Mock sensor entity state."""
    state = Mock()
    state.entity_id = "sensor.test_temperature"
    state.state = "20.5"
    state.attributes = {
        "device_class": "temperature",
        "unit_of_measurement": "°C"
    }
    return state


@pytest.fixture
def mock_w100_devices():
    """Mock discovered W100 devices."""
    return [
        {
            "friendly_name": "living_room_w100",
            "model": "WXKG07LM",
            "ieee": "0x00158d0001234567"
        },
        {
            "friendly_name": "bedroom_w100", 
            "model": "WXKG07LM",
            "ieee": "0x00158d0001234568"
        }
    ]


@pytest.fixture
def mock_zigbee2mqtt_devices(mock_w100_devices):
    """Mock Zigbee2MQTT device list."""
    return mock_w100_devices + [
        {
            "friendly_name": "other_device",
            "model": "OTHER_MODEL",
            "ieee": "0x00158d0001234569"
        }
    ]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


# Async test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock Home Assistant test utilities
@pytest.fixture
def mock_async_setup_entry():
    """Mock async_setup_entry."""
    with patch('custom_components.w100_smart_control.async_setup_entry') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_async_unload_entry():
    """Mock async_unload_entry."""
    with patch('custom_components.w100_smart_control.async_unload_entry') as mock:
        mock.return_value = True
        yield mock


# Integration-specific fixtures
@pytest.fixture
def mock_coordinator():
    """Mock W100 coordinator."""
    coordinator = Mock()
    coordinator.data = {}
    coordinator.last_update_success = True
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_setup = AsyncMock()
    coordinator.async_cleanup = AsyncMock()
    coordinator._device_states = {}
    coordinator._created_thermostats = []
    return coordinator


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "w100_device_name": "living_room_w100",
        "climate_entity_type": "existing",
        "existing_climate_entity": "climate.living_room",
        "heating_temperature": 22.0,
        "idle_temperature": 18.0,
        "heating_warm_level": 3,
        "idle_warm_level": 1,
        "idle_fan_speed": "low",
        "swing_mode": "off",
        "beep_mode": "Enable Beep",
        "humidity_sensor": "sensor.humidity",
        "backup_humidity_sensor": "sensor.backup_humidity"
    }


@pytest.fixture
def sample_thermostat_config():
    """Sample thermostat configuration for testing."""
    return {
        "heater_switch": "switch.heater",
        "temperature_sensor": "sensor.temperature",
        "min_temp": 15.0,
        "max_temp": 25.0,
        "target_temp": 20.0,
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
        "precision": 0.5
    }