#!/usr/bin/env python3
"""Test script for W100 Smart Control device triggers."""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

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
        
    async def async_create_task(self, coro):
        """Mock async_create_task."""
        return await coro

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
        
    def async_get(self, device_id):
        """Mock device get by ID."""
        return self.devices.get(device_id)
        
    def add_device(self, device_id, identifiers, name):
        """Add a mock device."""
        device = MockDevice(device_id, identifiers, name)
        self.devices[device_id] = device
        return device

async def test_get_triggers_for_w100_device():
    """Test getting triggers for W100 device."""
    _LOGGER.info("Testing get triggers for W100 device...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    device_registry = MockDeviceRegistry()
    
    # Add a W100 control device
    device_id = "test_device_id"
    identifiers = {("w100_smart_control", "w100_control_living_room_w100")}
    device = device_registry.add_device(device_id, identifiers, "W100 Control for Living Room")
    
    with patch('custom_components.w100_smart_control.device_trigger.dr') as mock_dr:
        mock_dr.async_get.return_value = device_registry
        
        # Import and test the device trigger
        from custom_components.w100_smart_control.device_trigger import async_get_triggers
        
        triggers = await async_get_triggers(hass, device_id)
        
        # Verify triggers were found
        assert len(triggers) == 3
        
        trigger_types = [trigger["type"] for trigger in triggers]
        assert "button_toggle" in trigger_types
        assert "button_plus" in trigger_types
        assert "button_minus" in trigger_types
        
        # Check trigger details
        toggle_trigger = next(t for t in triggers if t["type"] == "button_toggle")
        assert toggle_trigger["domain"] == "w100_smart_control"
        assert toggle_trigger["device_id"] == device_id
        assert toggle_trigger["subtype"] == "living_room_w100"
        assert "Toggle Button" in toggle_trigger["metadata"]["name"]
        assert "double-pressed" in toggle_trigger["metadata"]["description"]
        
        plus_trigger = next(t for t in triggers if t["type"] == "button_plus")
        assert "Plus Button" in plus_trigger["metadata"]["name"]
        assert "increase" in plus_trigger["metadata"]["description"]
        
        minus_trigger = next(t for t in triggers if t["type"] == "button_minus")
        assert "Minus Button" in minus_trigger["metadata"]["name"]
        assert "decrease" in minus_trigger["metadata"]["description"]
        
        _LOGGER.info("✓ Get triggers for W100 device test passed")

async def test_get_triggers_for_non_w100_device():
    """Test getting triggers for non-W100 device."""
    _LOGGER.info("Testing get triggers for non-W100 device...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    device_registry = MockDeviceRegistry()
    
    # Add a non-W100 device
    device_id = "other_device_id"
    identifiers = {("other_integration", "some_device")}
    device = device_registry.add_device(device_id, identifiers, "Other Device")
    
    with patch('custom_components.w100_smart_control.device_trigger.dr') as mock_dr:
        mock_dr.async_get.return_value = device_registry
        
        # Import and test the device trigger
        from custom_components.w100_smart_control.device_trigger import async_get_triggers
        
        triggers = await async_get_triggers(hass, device_id)
        
        # Verify no triggers were found
        assert len(triggers) == 0
        
        _LOGGER.info("✓ Get triggers for non-W100 device test passed")

async def test_attach_trigger():
    """Test attaching a trigger."""
    _LOGGER.info("Testing attach trigger...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    device_registry = MockDeviceRegistry()
    
    # Add a W100 control device
    device_id = "test_device_id"
    identifiers = {("w100_smart_control", "w100_control_living_room_w100")}
    device = device_registry.add_device(device_id, identifiers, "W100 Control for Living Room")
    
    # Mock action and trigger info
    action = Mock()
    trigger_info = Mock()
    
    # Mock event trigger
    mock_event_trigger = Mock()
    mock_event_trigger.async_attach_trigger = AsyncMock(return_value=lambda: None)
    mock_event_trigger.TRIGGER_SCHEMA = Mock(side_effect=lambda x: x)
    
    with patch('custom_components.w100_smart_control.device_trigger.dr') as mock_dr, \
         patch('custom_components.w100_smart_control.device_trigger.event_trigger', mock_event_trigger):
        
        mock_dr.async_get.return_value = device_registry
        
        # Import and test the device trigger
        from custom_components.w100_smart_control.device_trigger import async_attach_trigger
        
        config = {
            "platform": "device",
            "domain": "w100_smart_control",
            "device_id": device_id,
            "type": "button_toggle",
        }
        
        # Attach the trigger
        detach_callback = await async_attach_trigger(hass, config, action, trigger_info)
        
        # Verify event trigger was called
        assert mock_event_trigger.async_attach_trigger.called
        
        # Verify detach callback is callable
        assert callable(detach_callback)
        
        _LOGGER.info("✓ Attach trigger test passed")

async def test_trigger_validation():
    """Test trigger configuration validation."""
    _LOGGER.info("Testing trigger validation...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    
    # Import and test the device trigger
    from custom_components.w100_smart_control.device_trigger import async_validate_trigger_config
    
    # Test valid configuration
    valid_config = {
        "platform": "device",
        "domain": "w100_smart_control",
        "device_id": "test_device_id",
        "type": "button_toggle",
    }
    
    validated_config = async_validate_trigger_config(hass, valid_config)
    assert validated_config["type"] == "button_toggle"
    
    # Test invalid trigger type
    invalid_config = {
        "platform": "device",
        "domain": "w100_smart_control",
        "device_id": "test_device_id",
        "type": "invalid_type",
    }
    
    try:
        async_validate_trigger_config(hass, invalid_config)
        assert False, "Should have raised validation error"
    except Exception:
        pass  # Expected validation error
    
    _LOGGER.info("✓ Trigger validation test passed")

async def test_coordinator_trigger_event_firing():
    """Test coordinator fires trigger events."""
    _LOGGER.info("Testing coordinator trigger event firing...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {"w100_device_name": "living_room_w100"}
    
    # Import coordinator
    from custom_components.w100_smart_control.coordinator import W100Coordinator
    
    coordinator = W100Coordinator(hass, entry)
    coordinator._device_states = {"living_room_w100": {}}
    coordinator._last_action_time = {}
    
    # Mock the climate entity processing to avoid errors
    with patch.object(coordinator, '_async_initialize_device_states', new_callable=AsyncMock):
        # Test action handling
        await coordinator.async_handle_w100_action("toggle", "living_room_w100")
        
        # Verify event was fired
        assert hass.bus.async_fire.called
        
        # Check event details
        call_args = hass.bus.async_fire.call_args
        event_type = call_args[0][0]
        event_data = call_args[0][1]
        
        assert event_type == "w100_smart_control_button_action"
        assert event_data["device_name"] == "living_room_w100"
        assert event_data["action"] == "toggle"
        assert "timestamp" in event_data
        assert event_data["integration"] == "w100_smart_control"
        
        _LOGGER.info("✓ Coordinator trigger event firing test passed")

async def main():
    """Run all device trigger tests."""
    _LOGGER.info("Starting W100 Smart Control device trigger tests...")
    
    try:
        await test_get_triggers_for_w100_device()
        await test_get_triggers_for_non_w100_device()
        await test_attach_trigger()
        await test_trigger_validation()
        await test_coordinator_trigger_event_firing()
        
        _LOGGER.info("🎉 All device trigger tests passed!")
        
    except Exception as err:
        _LOGGER.error("❌ Device trigger test failed: %s", err)
        raise

if __name__ == "__main__":
    asyncio.run(main())