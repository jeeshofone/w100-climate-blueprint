#!/usr/bin/env python3
"""Test script for W100 Smart Control user-friendly error messages."""

import sys
import os
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

# Add the custom component to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'w100_smart_control'))

# Import error handling classes
try:
    from error_messages import (
        W100ErrorMessages,
        W100ConfigFlowMessages,
        W100DiagnosticInfo,
    )
    from exceptions import (
        W100DeviceError,
        W100MQTTError,
        W100EntityError,
        W100ConfigurationError,
        W100ErrorCodes,
    )
except ImportError:
    # Handle relative imports for testing
    import importlib.util
    
    # Load exceptions module
    exceptions_spec = importlib.util.spec_from_file_location(
        "exceptions", 
        os.path.join(os.path.dirname(__file__), 'custom_components', 'w100_smart_control', 'exceptions.py')
    )
    exceptions_module = importlib.util.module_from_spec(exceptions_spec)
    exceptions_spec.loader.exec_module(exceptions_module)
    
    # Load error_messages module
    error_messages_spec = importlib.util.spec_from_file_location(
        "error_messages", 
        os.path.join(os.path.dirname(__file__), 'custom_components', 'w100_smart_control', 'error_messages.py')
    )
    error_messages_module = importlib.util.module_from_spec(error_messages_spec)
    
    # Inject exceptions module into error_messages namespace
    sys.modules['custom_components.w100_smart_control.exceptions'] = exceptions_module
    error_messages_spec.loader.exec_module(error_messages_module)
    
    # Import the classes
    W100ErrorMessages = error_messages_module.W100ErrorMessages
    W100ConfigFlowMessages = error_messages_module.W100ConfigFlowMessages
    W100DiagnosticInfo = error_messages_module.W100DiagnosticInfo
    W100DeviceError = exceptions_module.W100DeviceError
    W100MQTTError = exceptions_module.W100MQTTError
    W100EntityError = exceptions_module.W100EntityError
    W100ConfigurationError = exceptions_module.W100ConfigurationError
    W100ErrorCodes = exceptions_module.W100ErrorCodes

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_error_message_formatting():
    """Test that error messages are properly formatted."""
    print("Testing error message formatting...")
    
    # Test device error
    device_error = W100DeviceError("living_room_w100", "Connection timeout", W100ErrorCodes.DEVICE_COMMUNICATION_FAILED)
    formatted_message = W100ErrorMessages.format_error_message(
        device_error.error_code,
        {"device_name": "living_room_w100"}
    )
    
    assert "Communication Failed" in formatted_message
    assert "living_room_w100" in formatted_message
    print("✓ Device error message formatted correctly")
    
    # Test MQTT error
    mqtt_error = W100MQTTError("Connection refused", "test/topic", W100ErrorCodes.MQTT_CONNECTION_FAILED)
    formatted_message = W100ErrorMessages.format_error_message(mqtt_error.error_code)
    
    assert "MQTT Connection Failed" in formatted_message
    print("✓ MQTT error message formatted correctly")
    
    # Test entity error
    entity_error = W100EntityError("climate.test", "Entity not found", W100ErrorCodes.ENTITY_NOT_FOUND)
    formatted_message = W100ErrorMessages.format_error_message(
        entity_error.error_code,
        {"entity_id": "climate.test"}
    )
    
    assert "Climate Entity Not Found" in formatted_message
    assert "climate.test" in formatted_message
    print("✓ Entity error message formatted correctly")


def test_troubleshooting_guidance():
    """Test that troubleshooting guidance is provided."""
    print("\nTesting troubleshooting guidance...")
    
    # Test device troubleshooting
    guidance = W100ErrorMessages.get_troubleshooting_steps(W100ErrorCodes.DEVICE_NOT_FOUND)
    assert len(guidance) > 0
    assert any("Zigbee2MQTT" in step for step in guidance)
    print("✓ Device troubleshooting guidance provided")
    
    # Test MQTT troubleshooting
    guidance = W100ErrorMessages.get_troubleshooting_steps(W100ErrorCodes.MQTT_CONNECTION_FAILED)
    assert len(guidance) > 0
    assert any("MQTT" in step for step in guidance)
    print("✓ MQTT troubleshooting guidance provided")
    
    # Test entity troubleshooting
    guidance = W100ErrorMessages.get_troubleshooting_steps(W100ErrorCodes.ENTITY_NOT_FOUND)
    assert len(guidance) > 0
    assert any("entity" in step.lower() for step in guidance)
    print("✓ Entity troubleshooting guidance provided")


def test_documentation_links():
    """Test that documentation links are provided."""
    print("\nTesting documentation links...")
    
    # Test device documentation
    doc_link = W100ErrorMessages.get_documentation_link(W100ErrorCodes.DEVICE_NOT_FOUND)
    assert doc_link.startswith("https://")
    print("✓ Device documentation link provided")
    
    # Test MQTT documentation
    doc_link = W100ErrorMessages.get_documentation_link(W100ErrorCodes.MQTT_CONNECTION_FAILED)
    assert doc_link.startswith("https://")
    print("✓ MQTT documentation link provided")
    
    # Test unknown error code
    doc_link = W100ErrorMessages.get_documentation_link("UNKNOWN_ERROR")
    assert doc_link.startswith("https://")
    print("✓ Default documentation link provided for unknown errors")


def test_config_flow_messages():
    """Test configuration flow messages."""
    print("\nTesting configuration flow messages...")
    
    # Test step descriptions
    assert "user" in W100ConfigFlowMessages.STEP_DESCRIPTIONS
    assert "Zigbee2MQTT" in W100ConfigFlowMessages.STEP_DESCRIPTIONS["device_selection"]
    print("✓ Configuration step descriptions provided")
    
    # Test error messages
    assert "no_mqtt" in W100ConfigFlowMessages.ERROR_MESSAGES
    assert "MQTT integration" in W100ConfigFlowMessages.ERROR_MESSAGES["no_mqtt"]
    print("✓ Configuration error messages provided")
    
    # Test success messages
    assert "device_found" in W100ConfigFlowMessages.SUCCESS_MESSAGES
    assert "accessible" in W100ConfigFlowMessages.SUCCESS_MESSAGES["device_found"]
    print("✓ Configuration success messages provided")
    
    # Test help text
    assert "device_selection" in W100ConfigFlowMessages.HELP_TEXT
    assert "paired" in W100ConfigFlowMessages.HELP_TEXT["device_selection"]
    print("✓ Configuration help text provided")


def test_error_info_structure():
    """Test that error info has proper structure."""
    print("\nTesting error info structure...")
    
    # Test device error info
    error_info = W100ErrorMessages.get_error_info(W100ErrorCodes.DEVICE_NOT_FOUND)
    required_keys = ["title", "message", "guidance", "documentation"]
    
    for key in required_keys:
        assert key in error_info, f"Missing key: {key}"
    
    assert isinstance(error_info["guidance"], list)
    assert len(error_info["guidance"]) > 0
    print("✓ Error info structure is correct")
    
    # Test unknown error code
    error_info = W100ErrorMessages.get_error_info("UNKNOWN_ERROR_CODE")
    for key in required_keys:
        assert key in error_info, f"Missing key in unknown error: {key}"
    
    assert "Unknown Error" in error_info["title"]
    print("✓ Unknown error handling works correctly")


def test_diagnostic_info():
    """Test diagnostic information generation."""
    print("\nTesting diagnostic information...")
    
    # Mock Home Assistant and coordinator
    mock_hass = Mock()
    mock_hass.config.version = "2023.12.0"
    mock_hass.services.has_service.return_value = True
    mock_hass.config.components = ["zigbee2mqtt", "mqtt"]
    
    mock_coordinator = Mock()
    mock_coordinator._device_states = {
        "living_room_w100": {
            "last_action": "toggle",
            "last_action_time": "2023-12-01T10:00:00"
        }
    }
    mock_coordinator._device_configs = {
        "living_room_w100": {
            "existing_climate_entity": "climate.living_room"
        }
    }
    mock_coordinator._mqtt_subscriptions = {
        "living_room_w100": ["topic1", "topic2"]
    }
    mock_coordinator._device_thermostats = {
        "living_room_w100": ["climate.w100_living_room"]
    }
    
    # Test system info
    system_info = W100DiagnosticInfo.get_system_info(mock_hass)
    assert "home_assistant_version" in system_info
    assert system_info["mqtt_available"] is True
    assert system_info["zigbee2mqtt_detected"] is True
    print("✓ System diagnostic info generated correctly")
    
    # Test device info
    device_info = W100DiagnosticInfo.get_device_info(mock_coordinator, "living_room_w100")
    assert device_info["device_name"] == "living_room_w100"
    assert device_info["device_available"] is True
    assert device_info["last_action"] == "toggle"
    print("✓ Device diagnostic info generated correctly")
    
    # Test diagnostic report
    report = W100DiagnosticInfo.format_diagnostic_report(mock_hass, mock_coordinator, "living_room_w100")
    assert "W100 Smart Control Diagnostic Report" in report
    assert "living_room_w100" in report
    assert "2023.12.0" in report
    print("✓ Diagnostic report formatted correctly")


def test_error_categories():
    """Test that all error categories are covered."""
    print("\nTesting error categories...")
    
    # Test that all error codes have corresponding messages
    error_codes_to_test = [
        W100ErrorCodes.DEVICE_NOT_FOUND,
        W100ErrorCodes.DEVICE_UNAVAILABLE,
        W100ErrorCodes.MQTT_CONNECTION_FAILED,
        W100ErrorCodes.ENTITY_NOT_FOUND,
        W100ErrorCodes.CONFIG_INVALID,
        W100ErrorCodes.THERMOSTAT_CREATE_FAILED,
        W100ErrorCodes.COORDINATOR_SETUP_FAILED,
    ]
    
    for error_code in error_codes_to_test:
        error_info = W100ErrorMessages.get_error_info(error_code)
        assert error_info["title"] != "Unknown Error", f"No error info for {error_code}"
        assert len(error_info["guidance"]) > 0, f"No guidance for {error_code}"
    
    print("✓ All major error categories have proper error messages")


def test_contextual_error_messages():
    """Test that error messages include context when provided."""
    print("\nTesting contextual error messages...")
    
    # Test with device context
    context = {"device_name": "bedroom_w100", "entity_id": "climate.bedroom"}
    message = W100ErrorMessages.format_error_message(W100ErrorCodes.ENTITY_NOT_FOUND, context)
    
    assert "bedroom_w100" in message
    assert "climate.bedroom" in message
    print("✓ Error messages include device and entity context")
    
    # Test without context
    message = W100ErrorMessages.format_error_message(W100ErrorCodes.ENTITY_NOT_FOUND)
    assert "Climate Entity Not Found" in message
    print("✓ Error messages work without context")


def main():
    """Run all user-friendly error message tests."""
    print("W100 Smart Control User-Friendly Error Messages Tests")
    print("=" * 60)
    
    try:
        test_error_message_formatting()
        test_troubleshooting_guidance()
        test_documentation_links()
        test_config_flow_messages()
        test_error_info_structure()
        test_diagnostic_info()
        test_error_categories()
        test_contextual_error_messages()
        
        print("\n" + "=" * 60)
        print("🎉 All user-friendly error message tests passed!")
        print("\nUser-friendly features verified:")
        print("✓ Clear, descriptive error messages")
        print("✓ Step-by-step troubleshooting guidance")
        print("✓ Documentation links for further help")
        print("✓ Configuration flow guidance")
        print("✓ Diagnostic information generation")
        print("✓ Contextual error messages")
        print("✓ Comprehensive error coverage")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())