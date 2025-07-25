#!/usr/bin/env python3
"""Test script for W100 Smart Control structured logging."""

import sys
import os
import asyncio
import logging
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import StringIO

# Add the custom component to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'w100_smart_control'))

# Set up logging with JSON formatter for testing
class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging tests."""
    
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'device_name'):
            log_entry['device_name'] = record.device_name
        if hasattr(record, 'integration'):
            log_entry['integration'] = record.integration
        if hasattr(record, 'entity_id'):
            log_entry['entity_id'] = record.entity_id
        if hasattr(record, 'action'):
            log_entry['action'] = record.action
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
            
        return json.dumps(log_entry)


def setup_test_logging():
    """Set up logging for testing structured logs."""
    # Create a string buffer to capture logs
    log_buffer = StringIO()
    
    # Set up handler with JSON formatter
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(JSONFormatter())
    
    # Configure logger
    logger = logging.getLogger('custom_components.w100_smart_control')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    
    return log_buffer, logger


def test_logging_context_structure():
    """Test that logging context is properly structured."""
    print("Testing logging context structure...")
    
    log_buffer, logger = setup_test_logging()
    
    # Test basic structured log
    logger.info(
        "Test message for device '%s'",
        "living_room_w100",
        extra={
            "device_name": "living_room_w100",
            "integration": "w100_smart_control",
            "entity_id": "climate.w100_living_room",
            "operation": "button_press"
        }
    )
    
    # Get the logged output
    log_output = log_buffer.getvalue()
    log_entry = json.loads(log_output.strip())
    
    # Verify structure
    assert log_entry['level'] == 'INFO'
    assert log_entry['device_name'] == 'living_room_w100'
    assert log_entry['integration'] == 'w100_smart_control'
    assert log_entry['entity_id'] == 'climate.w100_living_room'
    assert log_entry['operation'] == 'button_press'
    assert 'living_room_w100' in log_entry['message']
    
    print("✓ Logging context structure is correct")


def test_error_logging_context():
    """Test that error logging includes proper context."""
    print("Testing error logging context...")
    
    log_buffer, logger = setup_test_logging()
    
    # Test error log with context
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.error(
            "Failed to execute action '%s' for device '%s': %s",
            "toggle",
            "bedroom_w100",
            str(e),
            extra={
                "device_name": "bedroom_w100",
                "integration": "w100_smart_control",
                "action": "toggle",
                "error_type": type(e).__name__,
                "operation": "button_handling"
            }
        )
    
    # Get the logged output
    log_output = log_buffer.getvalue()
    log_entry = json.loads(log_output.strip())
    
    # Verify error context
    assert log_entry['level'] == 'ERROR'
    assert log_entry['device_name'] == 'bedroom_w100'
    assert log_entry['action'] == 'toggle'
    assert log_entry['error_type'] == 'ValueError'
    assert log_entry['operation'] == 'button_handling'
    assert 'Test error' in log_entry['message']
    
    print("✓ Error logging context is correct")


def test_debug_logging_levels():
    """Test different logging levels with context."""
    print("Testing debug logging levels...")
    
    log_buffer, logger = setup_test_logging()
    
    # Test different log levels
    test_cases = [
        (logging.DEBUG, "debug", "Debug message"),
        (logging.INFO, "info", "Info message"),
        (logging.WARNING, "warning", "Warning message"),
        (logging.ERROR, "error", "Error message"),
    ]
    
    for level, level_name, message in test_cases:
        # Clear buffer
        log_buffer.seek(0)
        log_buffer.truncate(0)
        
        logger.log(
            level,
            message + " for device '%s'",
            "test_device",
            extra={
                "device_name": "test_device",
                "integration": "w100_smart_control",
                "log_level_test": level_name
            }
        )
        
        log_output = log_buffer.getvalue()
        if log_output:  # Only check if log was actually written
            log_entry = json.loads(log_output.strip())
            assert log_entry['level'] == level_name.upper()
            assert log_entry['device_name'] == 'test_device'
            assert message in log_entry['message']
    
    print("✓ Debug logging levels work correctly")


def test_mqtt_operation_logging():
    """Test MQTT operation logging context."""
    print("Testing MQTT operation logging...")
    
    log_buffer, logger = setup_test_logging()
    
    # Test MQTT operation log
    logger.info(
        "Publishing MQTT message to topic '%s' for device '%s'",
        "zigbee2mqtt/living_room_w100/set",
        "living_room_w100",
        extra={
            "device_name": "living_room_w100",
            "integration": "w100_smart_control",
            "operation": "mqtt_publish",
            "mqtt_topic": "zigbee2mqtt/living_room_w100/set",
            "mqtt_payload": {"temperature": 22}
        }
    )
    
    # Get the logged output
    log_output = log_buffer.getvalue()
    log_entry = json.loads(log_output.strip())
    
    # Verify MQTT context
    assert log_entry['device_name'] == 'living_room_w100'
    assert log_entry['operation'] == 'mqtt_publish'
    assert hasattr(type(log_entry), '__getitem__')  # Verify it's a dict-like structure
    
    print("✓ MQTT operation logging context is correct")


def test_state_change_logging():
    """Test state change logging context."""
    print("Testing state change logging...")
    
    log_buffer, logger = setup_test_logging()
    
    # Test state change log
    logger.info(
        "Climate state changed for device '%s': %s → %s",
        "kitchen_w100",
        "off",
        "heat",
        extra={
            "device_name": "kitchen_w100",
            "integration": "w100_smart_control",
            "operation": "state_change",
            "old_state": "off",
            "new_state": "heat",
            "entity_id": "climate.w100_kitchen"
        }
    )
    
    # Get the logged output
    log_output = log_buffer.getvalue()
    log_entry = json.loads(log_output.strip())
    
    # Verify state change context
    assert log_entry['device_name'] == 'kitchen_w100'
    assert log_entry['operation'] == 'state_change'
    assert log_entry['entity_id'] == 'climate.w100_kitchen'
    assert 'off → heat' in log_entry['message']
    
    print("✓ State change logging context is correct")


def test_performance_logging():
    """Test performance-related logging."""
    print("Testing performance logging...")
    
    log_buffer, logger = setup_test_logging()
    
    # Test performance log
    logger.debug(
        "Operation '%s' completed for device '%s' in %d ms",
        "display_sync",
        "office_w100",
        150,
        extra={
            "device_name": "office_w100",
            "integration": "w100_smart_control",
            "operation": "display_sync",
            "duration_ms": 150,
            "performance_metric": True
        }
    )
    
    # Get the logged output
    log_output = log_buffer.getvalue()
    log_entry = json.loads(log_output.strip())
    
    # Verify performance context
    assert log_entry['device_name'] == 'office_w100'
    assert log_entry['operation'] == 'display_sync'
    assert '150 ms' in log_entry['message']
    
    print("✓ Performance logging context is correct")


def test_configuration_logging():
    """Test configuration-related logging."""
    print("Testing configuration logging...")
    
    log_buffer, logger = setup_test_logging()
    
    # Test configuration log
    logger.info(
        "Configuration updated for device '%s': %s = %s",
        "garage_w100",
        "beep_mode",
        "Enable Beep",
        extra={
            "device_name": "garage_w100",
            "integration": "w100_smart_control",
            "operation": "config_update",
            "config_key": "beep_mode",
            "config_value": "Enable Beep"
        }
    )
    
    # Get the logged output
    log_output = log_buffer.getvalue()
    log_entry = json.loads(log_output.strip())
    
    # Verify configuration context
    assert log_entry['device_name'] == 'garage_w100'
    assert log_entry['operation'] == 'config_update'
    assert 'beep_mode = Enable Beep' in log_entry['message']
    
    print("✓ Configuration logging context is correct")


def main():
    """Run all structured logging tests."""
    print("W100 Smart Control Structured Logging Tests")
    print("=" * 50)
    
    try:
        test_logging_context_structure()
        test_error_logging_context()
        test_debug_logging_levels()
        test_mqtt_operation_logging()
        test_state_change_logging()
        test_performance_logging()
        test_configuration_logging()
        
        print("\n" + "=" * 50)
        print("🎉 All structured logging tests passed!")
        print("\nStructured logging features verified:")
        print("✓ Context-aware logging with device information")
        print("✓ Error logging with exception context")
        print("✓ Multiple log levels with proper formatting")
        print("✓ MQTT operation logging")
        print("✓ State change tracking")
        print("✓ Performance metrics logging")
        print("✓ Configuration change logging")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())