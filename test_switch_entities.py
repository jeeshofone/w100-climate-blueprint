#!/usr/bin/env python3
"""Test script for W100 Smart Control switch entities."""

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

class MockCoordinator:
    """Mock coordinator for testing."""
    
    def __init__(self):
        self.last_update_success = True
        self.last_exception = None
        self._device_configs = {
            "living_room_w100": {
                "beep_mode": "On-Mode Change",
                "stuck_heater_workaround_enabled": True,
                "display_sync_enabled": True,
                "debounce_enabled": True,
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
    
    async def _async_save_device_data(self):
        """Mock save device data."""
        pass

class MockRestoreState:
    """Mock restore state."""
    
    def __init__(self, state="on"):
        self.state = state

async def test_beep_control_switch():
    """Test W100 beep control switch."""
    _LOGGER.info("Testing W100 beep control switch...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Import and test the switch
    from custom_components.w100_smart_control.switch import W100BeepControlSwitch
    
    switch = W100BeepControlSwitch(coordinator, entry, "living_room_w100")
    
    # Test basic properties
    assert switch.unique_id == "w100_smart_control_living_room_w100_beep_control"
    assert "W100 Living Room W100 Beep Control" in switch.name
    assert switch.available is True
    assert switch.is_on is True  # Default enabled for "On-Mode Change"
    assert switch.icon == "mdi:volume-high"
    
    # Test turn off
    await switch.async_turn_off()
    assert switch.is_on is False
    
    # Test turn on
    await switch.async_turn_on()
    assert switch.is_on is True
    
    # Test attributes
    attributes = switch.extra_state_attributes
    assert attributes["w100_device_name"] == "living_room_w100"
    assert attributes["switch_type"] == "beep_control"
    assert attributes["beep_mode"] == "On-Mode Change"
    assert "description" in attributes
    
    _LOGGER.info("✓ Beep control switch test passed")

async def test_stuck_heater_workaround_switch():
    """Test W100 stuck heater workaround switch."""
    _LOGGER.info("Testing W100 stuck heater workaround switch...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Import and test the switch
    from custom_components.w100_smart_control.switch import W100StuckHeaterWorkaroundSwitch
    
    switch = W100StuckHeaterWorkaroundSwitch(coordinator, entry, "living_room_w100")
    
    # Test basic properties
    assert switch.unique_id == "w100_smart_control_living_room_w100_stuck_heater_workaround"
    assert "Stuck Heater Workaround" in switch.name
    assert switch.available is True
    assert switch.is_on is True  # Default enabled
    assert switch.icon == "mdi:wrench"
    assert switch.entity_category == "config"
    
    # Test turn off
    await switch.async_turn_off()
    assert switch.is_on is False
    
    # Test turn on
    await switch.async_turn_on()
    assert switch.is_on is True
    
    # Test attributes
    attributes = switch.extra_state_attributes
    assert attributes["w100_device_name"] == "living_room_w100"
    assert attributes["switch_type"] == "stuck_heater_workaround"
    assert attributes["feature"] == "stuck_heater_workaround"
    assert attributes["check_interval_minutes"] == 5
    assert attributes["temperature_threshold_celsius"] == 0.5
    assert attributes["time_threshold_minutes"] == 15
    
    _LOGGER.info("✓ Stuck heater workaround switch test passed")

async def test_display_sync_switch():
    """Test W100 display sync switch."""
    _LOGGER.info("Testing W100 display sync switch...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Import and test the switch
    from custom_components.w100_smart_control.switch import W100DisplaySyncSwitch
    
    switch = W100DisplaySyncSwitch(coordinator, entry, "living_room_w100")
    
    # Test basic properties
    assert switch.unique_id == "w100_smart_control_living_room_w100_display_sync"
    assert "Display Sync" in switch.name
    assert switch.available is True
    assert switch.is_on is True  # Default enabled
    assert switch.icon == "mdi:monitor-dashboard"
    assert switch.entity_category == "config"
    
    # Test turn off
    await switch.async_turn_off()
    assert switch.is_on is False
    
    # Test turn on
    await switch.async_turn_on()
    assert switch.is_on is True
    
    # Test attributes
    attributes = switch.extra_state_attributes
    assert attributes["w100_device_name"] == "living_room_w100"
    assert attributes["switch_type"] == "display_sync"
    assert attributes["feature"] == "display_synchronization"
    assert "sync_modes" in attributes
    assert attributes["update_delay_seconds"] == 2
    
    _LOGGER.info("✓ Display sync switch test passed")

async def test_debounce_switch():
    """Test W100 debounce switch."""
    _LOGGER.info("Testing W100 debounce switch...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Import and test the switch
    from custom_components.w100_smart_control.switch import W100DebounceSwitch
    
    switch = W100DebounceSwitch(coordinator, entry, "living_room_w100")
    
    # Test basic properties
    assert switch.unique_id == "w100_smart_control_living_room_w100_debounce"
    assert "Debounce" in switch.name
    assert switch.available is True
    assert switch.is_on is True  # Default enabled
    assert switch.icon == "mdi:timer-outline"
    assert switch.entity_category == "config"
    
    # Test turn off
    await switch.async_turn_off()
    assert switch.is_on is False
    
    # Test turn on
    await switch.async_turn_on()
    assert switch.is_on is True
    
    # Test attributes
    attributes = switch.extra_state_attributes
    assert attributes["w100_device_name"] == "living_room_w100"
    assert attributes["switch_type"] == "debounce"
    assert attributes["feature"] == "button_debouncing"
    assert attributes["debounce_delay_seconds"] == 2.0
    assert attributes["toggle_debounce_seconds"] == 1.0
    
    _LOGGER.info("✓ Debounce switch test passed")

async def test_switch_state_persistence():
    """Test switch state persistence."""
    _LOGGER.info("Testing switch state persistence...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    entry = MockConfigEntry()
    coordinator = MockCoordinator()
    
    # Mock restore state
    with patch('custom_components.w100_smart_control.switch.W100BaseSwitch.async_get_last_state') as mock_restore:
        mock_restore.return_value = MockRestoreState("off")
        
        from custom_components.w100_smart_control.switch import W100BeepControlSwitch
        
        switch = W100BeepControlSwitch(coordinator, entry, "living_room_w100")
        
        # Simulate adding to hass (which restores state)
        await switch.async_added_to_hass()
        
        # Should restore to "off" state
        assert switch.is_on is False
        
    _LOGGER.info("✓ Switch state persistence test passed")

async def test_switch_platform_setup():
    """Test switch platform setup."""
    _LOGGER.info("Testing switch platform setup...")
    
    # Set up mocks
    hass = MockHomeAssistant()
    hass.data["w100_smart_control"] = {"test_entry_id": MockCoordinator()}
    
    entry = MockConfigEntry()
    entities_added = []
    
    def mock_add_entities(entities):
        entities_added.extend(entities)
    
    # Import and test the setup
    from custom_components.w100_smart_control.switch import async_setup_entry
    
    await async_setup_entry(hass, entry, mock_add_entities)
    
    # Verify entities were created
    assert len(entities_added) == 4
    
    entity_types = [type(entity).__name__ for entity in entities_added]
    assert "W100BeepControlSwitch" in entity_types
    assert "W100StuckHeaterWorkaroundSwitch" in entity_types
    assert "W100DisplaySyncSwitch" in entity_types
    assert "W100DebounceSwitch" in entity_types
    
    _LOGGER.info("✓ Switch platform setup test passed")

async def main():
    """Run all switch entity tests."""
    _LOGGER.info("Starting W100 Smart Control switch entity tests...")
    
    try:
        await test_beep_control_switch()
        await test_stuck_heater_workaround_switch()
        await test_display_sync_switch()
        await test_debounce_switch()
        await test_switch_state_persistence()
        await test_switch_platform_setup()
        
        _LOGGER.info("🎉 All switch entity tests passed!")
        
    except Exception as err:
        _LOGGER.error("❌ Switch entity test failed: %s", err)
        raise

if __name__ == "__main__":
    asyncio.run(main())