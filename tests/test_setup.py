"""Test basic setup and imports."""
import pytest


def test_imports():
    """Test that basic imports work."""
    # Test that we can import pytest
    assert pytest is not None
    
    # Test that we can import basic Python modules
    import sys
    import os
    assert sys is not None
    assert os is not None


def test_domain_constant():
    """Test that we can access the domain constant."""
    from conftest import DOMAIN
    assert DOMAIN == "w100_smart_control"


def test_mock_fixtures(mock_hass, mock_config_entry):
    """Test that our mock fixtures work."""
    assert mock_hass is not None
    assert mock_config_entry is not None
    assert mock_config_entry.domain == "w100_smart_control"


@pytest.mark.asyncio
async def test_async_functionality():
    """Test that async functionality works."""
    import asyncio
    
    async def dummy_async_function():
        await asyncio.sleep(0.001)
        return "success"
    
    result = await dummy_async_function()
    assert result == "success"


def test_home_assistant_imports():
    """Test that Home Assistant imports work."""
    try:
        from homeassistant.core import HomeAssistant
        from homeassistant.config_entries import ConfigEntry
        assert HomeAssistant is not None
        assert ConfigEntry is not None
    except ImportError as e:
        pytest.fail(f"Failed to import Home Assistant components: {e}")


def test_testing_utilities():
    """Test that testing utilities are available."""
    try:
        import pytest_homeassistant_custom_component
        assert pytest_homeassistant_custom_component is not None
    except ImportError as e:
        pytest.fail(f"Failed to import Home Assistant testing utilities: {e}")