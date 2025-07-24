#!/usr/bin/env python3
"""Simple test to verify advanced features are implemented correctly."""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from w100_smart_control.climate import W100ClimateEntity, STUCK_HEATER_CHECK_INTERVAL, DEBOUNCE_DELAY


def test_advanced_features_initialization():
    """Test that advanced features are properly initialized."""
    print("Testing advanced features initialization...")
    
    # Mock dependencies
    mock_coordinator = Mock()
    mock_config_entry = Mock()
    mock_config_entry.data = {
        'beep_mode': 'On-Mode Change',
        'heating_temperature': 25,
        'idle_temperature': 20,
    }
    
    # Create climate entity
    climate_entity = W100ClimateEntity(
        coordinator=mock_coordinator,
        config_entry=mock_config_entry,
        target_climate_entity="climate.test_thermostat",
        device_name="test_w100"
    )
    
    # Check that advanced feature attributes are initialized
    assert hasattr(climate_entity, '_last_button_press')
    assert hasattr(climate_entity, '_debounce_task')
    assert hasattr(climate_entity, '_stuck_heater_tracker')
    assert hasattr(climate_entity, '_last_temp_check')
    assert hasattr(climate_entity, '_last_temp_value')
    assert hasattr(climate_entity, '_heater_start_time')
    assert hasattr(climate_entity, '_startup_initialized')
    assert hasattr(climate_entity, '_beep_mode')
    assert hasattr(climate_entity, '_heating_temperature')
    assert hasattr(climate_entity, '_idle_temperature')
    
    # Check configuration values
    assert climate_entity._beep_mode == 'On-Mode Change'
    assert climate_entity._heating_temperature == 25
    assert climate_entity._idle_temperature == 20
    
    print("✓ Advanced features initialization test passed")


def test_advanced_methods_exist():
    """Test that all advanced feature methods exist."""
    print("Testing advanced feature methods exist...")
    
    # Mock dependencies
    mock_coordinator = Mock()
    mock_config_entry = Mock()
    mock_config_entry.data = {}
    
    # Create climate entity
    climate_entity = W100ClimateEntity(
        coordinator=mock_coordinator,
        config_entry=mock_config_entry,
        target_climate_entity="climate.test_thermostat",
        device_name="test_w100"
    )
    
    # Check that advanced feature methods exist
    assert hasattr(climate_entity, '_setup_advanced_features')
    assert hasattr(climate_entity, '_startup_initialization')
    assert hasattr(climate_entity, '_check_stuck_heater')
    assert hasattr(climate_entity, '_implement_stuck_heater_workaround')
    assert hasattr(climate_entity, '_debounced_button_handler')
    assert hasattr(climate_entity, '_execute_button_action')
    assert hasattr(climate_entity, '_handle_toggle_button_advanced')
    assert hasattr(climate_entity, '_handle_plus_button_advanced')
    assert hasattr(climate_entity, '_handle_minus_button_advanced')
    assert hasattr(climate_entity, '_send_beep_command')
    
    print("✓ Advanced feature methods exist test passed")


def test_constants_defined():
    """Test that advanced feature constants are properly defined."""
    print("Testing advanced feature constants...")
    
    # Import the constants from the climate module
    from w100_smart_control.climate import (
        STUCK_HEATER_CHECK_INTERVAL,
        STUCK_HEATER_TEMP_THRESHOLD,
        STUCK_HEATER_TIME_THRESHOLD,
        DEBOUNCE_DELAY,
        STARTUP_INIT_DELAY
    )
    
    # Check that constants are properly defined
    assert isinstance(STUCK_HEATER_CHECK_INTERVAL, timedelta)
    assert STUCK_HEATER_CHECK_INTERVAL == timedelta(minutes=5)
    
    assert isinstance(STUCK_HEATER_TEMP_THRESHOLD, (int, float))
    assert STUCK_HEATER_TEMP_THRESHOLD == 0.5
    
    assert isinstance(STUCK_HEATER_TIME_THRESHOLD, timedelta)
    assert STUCK_HEATER_TIME_THRESHOLD == timedelta(minutes=15)
    
    assert isinstance(DEBOUNCE_DELAY, (int, float))
    assert DEBOUNCE_DELAY == 2.0
    
    assert isinstance(STARTUP_INIT_DELAY, (int, float))
    assert STARTUP_INIT_DELAY == 5.0
    
    print("✓ Advanced feature constants test passed")


async def test_debounce_logic():
    """Test that debounce logic works correctly."""
    print("Testing debounce logic...")
    
    # Mock dependencies
    mock_coordinator = Mock()
    mock_config_entry = Mock()
    mock_config_entry.data = {}
    
    # Create climate entity
    climate_entity = W100ClimateEntity(
        coordinator=mock_coordinator,
        config_entry=mock_config_entry,
        target_climate_entity="climate.test_thermostat",
        device_name="test_w100"
    )
    
    # Mock the execute_button_action method
    climate_entity._execute_button_action = AsyncMock()
    
    # Test first button press - should execute
    await climate_entity._debounced_button_handler("plus")
    climate_entity._execute_button_action.assert_called_once_with("plus")
    
    # Reset mock
    climate_entity._execute_button_action.reset_mock()
    
    # Test rapid second button press - should be debounced
    await climate_entity._debounced_button_handler("plus")
    climate_entity._execute_button_action.assert_not_called()
    
    print("✓ Debounce logic test passed")


def main():
    """Run all tests."""
    print("Running advanced features tests...\n")
    
    try:
        # Run synchronous tests
        test_advanced_features_initialization()
        test_advanced_methods_exist()
        test_constants_defined()
        
        # Run asynchronous tests
        asyncio.run(test_debounce_logic())
        
        print("\n✅ All advanced features tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())