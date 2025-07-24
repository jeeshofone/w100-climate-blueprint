"""The Aqara W100 Smart Control integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import W100Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the W100 Smart Control integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up W100 Smart Control from a config entry with proper registry integration."""
    coordinator = W100Coordinator(hass, entry)
    
    # Set up coordinator (load persisted data, cleanup orphaned entities, register devices)
    await coordinator.async_setup()
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up entry update listener
    entry.async_on_unload(
        entry.add_update_listener(async_update_entry)
    )
    
    # Forward setup to platforms with proper device registry integration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info(
        "W100 Smart Control integration setup complete with device registry integration for entry %s",
        entry.entry_id
    )
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Clean up all thermostats and resources when integration is removed
        await coordinator.async_cleanup()
    
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    # Get coordinator if it exists
    coordinator_data = hass.data.get(DOMAIN, {})
    coordinator = coordinator_data.get(entry.entry_id)
    
    if coordinator:
        # Remove all thermostats created by this integration
        try:
            await coordinator.async_remove_all_thermostats()
            _LOGGER.info("Removed all thermostats for deleted integration entry %s", entry.entry_id)
        except Exception as err:
            _LOGGER.error("Error removing thermostats during entry removal: %s", err)
        
        # Clean up storage
        try:
            await coordinator._storage.async_remove()
            await coordinator._device_storage.async_remove()
            _LOGGER.debug("Removed storage for deleted integration entry %s", entry.entry_id)
        except Exception as err:
            _LOGGER.warning("Failed to remove storage during entry removal: %s", err)


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update config entry."""
    coordinator_data = hass.data.get(DOMAIN, {})
    coordinator = coordinator_data.get(entry.entry_id)
    
    if coordinator:
        try:
            await coordinator.async_on_entry_update(hass, entry)
            _LOGGER.debug("Updated coordinator for entry %s", entry.entry_id)
        except Exception as err:
            _LOGGER.error("Error updating coordinator for entry %s: %s", entry.entry_id, err)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)