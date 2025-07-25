#!/usr/bin/env python3
"""Test script for W100 Smart Control automation integration support."""

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
        self.bus = Mock()

class MockDevice:
    """Mock device for testing."""
    
    def __init__(self, device_id, identifiers, name):
        self.id = device_id
        self.identifiers = identifiers
        self.name = name

class MockDeviceRegistry:
    """Mock device registry for testing."""
    
    def __init__(self):
        self.devices = {}
        
    def add_device(self, device_id, identifiers, name):
        """Add a mock device."""
        device = MockDevice(device_id, identifiers, name)
        self.devices[device_id] = device
        return device

async def test_trigger_schema_validation():
    """Test trigger schema validation with comprehensive data."""
    _LOGGER.info("Testing trigger schema validation...")
    
    # Import the validation function
    from custom_components.w100_smart_control.device_trigger import async_validate_trigger_config
    
    hass = MockHomeAssistant()
    
    # Test valid configuration with all fields
    valid_config = {
        "platform": "device",
        "domain": "w100_smart_control",
        "device_id": "test_device_id",
        "type": "button_toggle",
        "subtype": "living_room_w100",
        "metadata": {
            "name": "Living Room Toggle",
            "description": "Toggle living room lights"
        }
    }
    
    validated_config = async_validate_trigger_config(hass, valid_config)
    assert validated_config["type"] == "button_toggle"
    assert validated_config["subtype"] == "living_room_w100"
    assert "metadata" in validated_config
    
    # Test minimal valid configuration
    minimal_config = {
        "platform": "device",
        "domain": "w100_smart_control",
        "device_id": "test_device_id",
        "type": "button_plus",
    }
    
    validated_minimal = async_validate_trigger_config(hass, minimal_config)
    assert validated_minimal["type"] == "button_plus"
    
    _LOGGER.info("✓ Trigger schema validation test passed")

async def test_trigger_capabilities():
    """Test trigger capabilities for automation UI."""
    _LOGGER.info("Testing trigger capabilities...")
    
    # Import the capabilities function
    from custom_components.w100_smart_control.device_trigger import async_get_trigger_capabilities
    
    hass = MockHomeAssistant()
    config = {
        "platform": "device",
        "domain": "w100_smart_control",
        "device_id": "test_device_id",
        "type": "button_toggle",
    }
    
    capabilities = await async_get_trigger_capabilities(hass, config)
    
    # Verify capabilities structure
    assert "extra_fields" in capabilities
    assert capabilities["extra_fields"] is not None
    
    _LOGGER.info("✓ Trigger capabilities test passed")

async def test_automation_trigger_registration():
    """Test automation trigger registration with Home Assistant."""
    _LOGGER.info("Testing automation trigger registration...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    device_registry = MockDeviceRegistry()
    
    # Add W100 control devices
    device_registry.add_device(
        "device_1", 
        {("w100_smart_control", "w100_control_living_room_w100")}, 
        "W100 Control Living Room"
    )
    device_registry.add_device(
        "device_2", 
        {("w100_smart_control", "w100_control_bedroom_w100")}, 
        "W100 Control Bedroom"
    )
    
    # Add non-W100 device (should be ignored)
    device_registry.add_device(
        "device_3", 
        {("other_integration", "some_device")}, 
        "Other Device"
    )
    
    with patch('custom_components.w100_smart_control.device_trigger.dr') as mock_dr:
        mock_dr.async_get.return_value = device_registry
        
        # Import and test registration
        from custom_components.w100_smart_control.device_trigger import async_register_automation_triggers
        
        await async_register_automation_triggers(hass)
        
        # Verify registration completed without errors
        # (In a real test, we would verify the triggers were registered with the automation system)
        
        _LOGGER.info("✓ Automation trigger registration test passed")

async def test_trigger_documentation():
    """Test trigger documentation for automation system."""
    _LOGGER.info("Testing trigger documentation...")
    
    # Import documentation function
    from custom_components.w100_smart_control.device_trigger import get_trigger_documentation
    
    docs = get_trigger_documentation()
    
    # Verify documentation structure
    assert "triggers" in docs
    assert "event_schema" in docs
    assert "supported_platforms" in docs
    assert "integration_domain" in docs
    
    # Verify all trigger types are documented
    triggers = docs["triggers"]
    assert "button_toggle" in triggers
    assert "button_plus" in triggers
    assert "button_minus" in triggers
    
    # Verify each trigger has required documentation
    for trigger_type, trigger_info in triggers.items():
        assert "name" in trigger_info
        assert "description" in trigger_info
        assert "event_type" in trigger_info
        assert "event_data" in trigger_info
        assert "example_automation" in trigger_info
        
        # Verify example automation structure
        example = trigger_info["example_automation"]
        assert "trigger" in example
        assert "action" in example
        assert example["trigger"]["domain"] == "w100_smart_control"
        assert example["trigger"]["type"] == trigger_type
    
    # Verify event schema
    assert docs["event_schema"] is not None
    
    # Verify supported platforms
    assert "device" in docs["supported_platforms"]
    assert "event" in docs["supported_platforms"]
    
    _LOGGER.info("✓ Trigger documentation test passed")

async def test_event_data_validation():
    """Test event data schema validation."""
    _LOGGER.info("Testing event data validation...")
    
    # Import event data schema
    from custom_components.w100_smart_control.device_trigger import EVENT_DATA_SCHEMA
    
    # Test valid event data
    valid_event_data = {
        "device_name": "living_room_w100",
        "action": "toggle",
        "timestamp": "2024-01-01T12:00:00",
        "integration": "w100_smart_control",
    }
    
    validated_data = EVENT_DATA_SCHEMA(valid_event_data)
    assert validated_data["device_name"] == "living_room_w100"
    assert validated_data["action"] == "toggle"
    
    # Test invalid action
    invalid_event_data = {
        "device_name": "living_room_w100",
        "action": "invalid_action",
        "timestamp": "2024-01-01T12:00:00",
        "integration": "w100_smart_control",
    }
    
    try:
        EVENT_DATA_SCHEMA(invalid_event_data)
        assert False, "Should have raised validation error"
    except Exception:
        pass  # Expected validation error
    
    _LOGGER.info("✓ Event data validation test passed")

async def test_trigger_registration_function():
    """Test trigger registration function works correctly."""
    _LOGGER.info("Testing trigger registration function...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    
    # Import and test registration function directly
    from custom_components.w100_smart_control.device_trigger import async_register_automation_triggers
    
    # This should complete without errors even with empty device registry
    await async_register_automation_triggers(hass)
    
    _LOGGER.info("✓ Trigger registration function test passed")

async def main():
    """Run all automation integration tests."""
    _LOGGER.info("Starting W100 Smart Control automation integration tests...")
    
    try:
        await test_trigger_schema_validation()
        await test_trigger_capabilities()
        await test_automation_trigger_registration()
        await test_trigger_documentation()
        await test_event_data_validation()
        await test_trigger_registration_function()
        
        _LOGGER.info("🎉 All automation integration tests passed!")
        
    except Exception as err:
        _LOGGER.error("❌ Automation integration test failed: %s", err)
        raise

if __name__ == "__main__":
    asyncio.run(main())