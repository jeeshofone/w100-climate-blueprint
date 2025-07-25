#!/usr/bin/env python3
"""Test script for W100 Smart Control exception handling."""

import sys
import os
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

# Add the custom component to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'w100_smart_control'))

# Import exception classes
from exceptions import (
    W100IntegrationError,
    W100DeviceError,
    W100MQTTError,
    W100EntityError,
    W100ConfigurationError,
    W100ThermostatError,
    W100RegistryError,
    W100RecoverableError,
    W100CriticalError,
    W100ErrorCodes,
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_exception_hierarchy():
    """Test that exception hierarchy is correct."""
    print("Testing exception hierarchy...")
    
    # Test base exception
    base_error = W100IntegrationError("Base error", "TEST_CODE")
    assert isinstance(base_error, Exception)
    assert base_error.error_code == "TEST_CODE"
    print("✓ Base exception works")
    
    # Test device error
    device_error = W100DeviceError("test_device", "Device error", W100ErrorCodes.DEVICE_NOT_FOUND)
    assert isinstance(device_error, W100IntegrationError)
    assert device_error.device_name == "test_device"
    assert device_error.error_code == W100ErrorCodes.DEVICE_NOT_FOUND
    print("✓ Device exception works")
    
    # Test MQTT error
    mqtt_error = W100MQTTError("MQTT error", "test/topic", W100ErrorCodes.MQTT_CONNECTION_FAILED)
    assert isinstance(mqtt_error, W100IntegrationError)
    assert mqtt_error.topic == "test/topic"
    assert mqtt_error.error_code == W100ErrorCodes.MQTT_CONNECTION_FAILED
    print("✓ MQTT exception works")
    
    # Test entity error
    entity_error = W100EntityError("climate.test", "Entity error", W100ErrorCodes.ENTITY_NOT_FOUND)
    assert isinstance(entity_error, W100IntegrationError)
    assert entity_error.entity_id == "climate.test"
    assert entity_error.error_code == W100ErrorCodes.ENTITY_NOT_FOUND
    print("✓ Entity exception works")
    
    # Test configuration error
    config_error = W100ConfigurationError("Config error", "test_key", W100ErrorCodes.CONFIG_INVALID)
    assert isinstance(config_error, W100IntegrationError)
    assert config_error.config_key == "test_key"
    assert config_error.error_code == W100ErrorCodes.CONFIG_INVALID
    print("✓ Configuration exception works")
    
    # Test thermostat error
    thermostat_error = W100ThermostatError("climate.thermostat", "Thermostat error", W100ErrorCodes.THERMOSTAT_CREATE_FAILED)
    assert isinstance(thermostat_error, W100IntegrationError)
    assert thermostat_error.thermostat_id == "climate.thermostat"
    assert thermostat_error.error_code == W100ErrorCodes.THERMOSTAT_CREATE_FAILED
    print("✓ Thermostat exception works")
    
    # Test registry error
    registry_error = W100RegistryError("Registry error", "entity", W100ErrorCodes.REGISTRY_OPERATION_FAILED)
    assert isinstance(registry_error, W100IntegrationError)
    assert registry_error.registry_type == "entity"
    assert registry_error.error_code == W100ErrorCodes.REGISTRY_OPERATION_FAILED
    print("✓ Registry exception works")
    
    # Test recoverable error
    recoverable_error = W100RecoverableError("Recoverable error", 30, W100ErrorCodes.DEVICE_UNAVAILABLE)
    assert isinstance(recoverable_error, W100IntegrationError)
    assert recoverable_error.retry_after == 30
    assert recoverable_error.error_code == W100ErrorCodes.DEVICE_UNAVAILABLE
    print("✓ Recoverable exception works")
    
    # Test critical error
    critical_error = W100CriticalError("Critical error", True, W100ErrorCodes.COORDINATOR_SETUP_FAILED)
    assert isinstance(critical_error, W100IntegrationError)
    assert critical_error.requires_restart is True
    assert critical_error.error_code == W100ErrorCodes.COORDINATOR_SETUP_FAILED
    print("✓ Critical exception works")
    
    print("All exception tests passed!")


def test_error_codes():
    """Test that error codes are properly defined."""
    print("\nTesting error codes...")
    
    # Test device error codes
    assert hasattr(W100ErrorCodes, 'DEVICE_NOT_FOUND')
    assert hasattr(W100ErrorCodes, 'DEVICE_UNAVAILABLE')
    assert hasattr(W100ErrorCodes, 'DEVICE_COMMUNICATION_FAILED')
    print("✓ Device error codes defined")
    
    # Test MQTT error codes
    assert hasattr(W100ErrorCodes, 'MQTT_CONNECTION_FAILED')
    assert hasattr(W100ErrorCodes, 'MQTT_PUBLISH_FAILED')
    assert hasattr(W100ErrorCodes, 'MQTT_SUBSCRIBE_FAILED')
    assert hasattr(W100ErrorCodes, 'MQTT_TOPIC_INVALID')
    print("✓ MQTT error codes defined")
    
    # Test entity error codes
    assert hasattr(W100ErrorCodes, 'ENTITY_NOT_FOUND')
    assert hasattr(W100ErrorCodes, 'ENTITY_UNAVAILABLE')
    assert hasattr(W100ErrorCodes, 'ENTITY_OPERATION_FAILED')
    assert hasattr(W100ErrorCodes, 'ENTITY_STATE_INVALID')
    print("✓ Entity error codes defined")
    
    # Test configuration error codes
    assert hasattr(W100ErrorCodes, 'CONFIG_INVALID')
    assert hasattr(W100ErrorCodes, 'CONFIG_MISSING')
    assert hasattr(W100ErrorCodes, 'CONFIG_VALIDATION_FAILED')
    print("✓ Configuration error codes defined")
    
    # Test thermostat error codes
    assert hasattr(W100ErrorCodes, 'THERMOSTAT_CREATE_FAILED')
    assert hasattr(W100ErrorCodes, 'THERMOSTAT_REMOVE_FAILED')
    assert hasattr(W100ErrorCodes, 'THERMOSTAT_UPDATE_FAILED')
    print("✓ Thermostat error codes defined")
    
    # Test registry error codes
    assert hasattr(W100ErrorCodes, 'REGISTRY_OPERATION_FAILED')
    assert hasattr(W100ErrorCodes, 'DEVICE_REGISTRY_FAILED')
    assert hasattr(W100ErrorCodes, 'ENTITY_REGISTRY_FAILED')
    print("✓ Registry error codes defined")
    
    # Test critical error codes
    assert hasattr(W100ErrorCodes, 'COORDINATOR_SETUP_FAILED')
    assert hasattr(W100ErrorCodes, 'INTEGRATION_SETUP_FAILED')
    assert hasattr(W100ErrorCodes, 'DATA_CORRUPTION')
    print("✓ Critical error codes defined")
    
    print("All error code tests passed!")


def test_exception_messages():
    """Test that exception messages are properly formatted."""
    print("\nTesting exception messages...")
    
    # Test device error message
    device_error = W100DeviceError("living_room_w100", "Connection timeout", W100ErrorCodes.DEVICE_COMMUNICATION_FAILED)
    expected_msg = "W100 device 'living_room_w100': Connection timeout"
    assert str(device_error) == expected_msg
    print("✓ Device error message formatted correctly")
    
    # Test MQTT error message
    mqtt_error = W100MQTTError("Connection refused", "zigbee2mqtt/living_room_w100/action", W100ErrorCodes.MQTT_CONNECTION_FAILED)
    expected_msg = "MQTT error (topic: zigbee2mqtt/living_room_w100/action): Connection refused"
    assert str(mqtt_error) == expected_msg
    print("✓ MQTT error message formatted correctly")
    
    # Test entity error message
    entity_error = W100EntityError("climate.living_room", "Entity not available", W100ErrorCodes.ENTITY_UNAVAILABLE)
    expected_msg = "Entity 'climate.living_room': Entity not available"
    assert str(entity_error) == expected_msg
    print("✓ Entity error message formatted correctly")
    
    # Test configuration error message
    config_error = W100ConfigurationError("Invalid temperature range", "heating_temperature", W100ErrorCodes.CONFIG_VALIDATION_FAILED)
    expected_msg = "Configuration error (config: heating_temperature): Invalid temperature range"
    assert str(config_error) == expected_msg
    print("✓ Configuration error message formatted correctly")
    
    print("All exception message tests passed!")


async def test_exception_handling_integration():
    """Test exception handling in integration context."""
    print("\nTesting exception handling integration...")
    
    # Test that exceptions can be caught and re-raised properly
    try:
        raise W100DeviceError("test_device", "Test error", W100ErrorCodes.DEVICE_NOT_FOUND)
    except W100IntegrationError as e:
        assert isinstance(e, W100DeviceError)
        assert e.error_code == W100ErrorCodes.DEVICE_NOT_FOUND
        print("✓ Exception catching and re-raising works")
    
    # Test exception chaining
    try:
        try:
            raise ValueError("Original error")
        except ValueError as e:
            raise W100EntityError("climate.test", "Wrapped error", W100ErrorCodes.ENTITY_OPERATION_FAILED) from e
    except W100EntityError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)
        print("✓ Exception chaining works")
    
    print("All integration tests passed!")


def main():
    """Run all exception handling tests."""
    print("W100 Smart Control Exception Handling Tests")
    print("=" * 50)
    
    try:
        test_exception_hierarchy()
        test_error_codes()
        test_exception_messages()
        asyncio.run(test_exception_handling_integration())
        
        print("\n" + "=" * 50)
        print("🎉 All exception handling tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())