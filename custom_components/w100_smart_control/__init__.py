"""The Aqara W100 Smart Control integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import W100Coordinator
from .error_messages import W100ErrorMessages, W100DiagnosticInfo

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
    
    # Register automation triggers with Home Assistant
    try:
        from .device_trigger import async_register_automation_triggers
        await async_register_automation_triggers(hass)
    except Exception as err:
        _LOGGER.warning("Failed to register automation triggers: %s", err)
    
    # Register diagnostic services
    await async_setup_services(hass)
    
    _LOGGER.info(
        "W100 Smart Control integration setup complete with device registry integration for entry %s",
        entry.entry_id
    )
    
    return True


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up diagnostic and troubleshooting services."""
    
    async def handle_get_diagnostic_info(call) -> None:
        """Handle get diagnostic info service call."""
        device_name = call.data.get("device_name")
        entry_id = call.data.get("entry_id")
        
        # Find coordinator
        coordinator = None
        if entry_id and entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][entry_id]
        elif hass.data[DOMAIN]:
            # Use first available coordinator if no entry_id specified
            coordinator = next(iter(hass.data[DOMAIN].values()))
        
        if not coordinator:
            _LOGGER.error("No W100 coordinator found for diagnostic info request")
            return
        
        # Generate diagnostic report
        if not device_name:
            device_name = coordinator.config.get("w100_device_name", "unknown")
        
        diagnostic_info = coordinator.get_diagnostic_info(device_name)
        
        # Log the diagnostic info (user can find it in logs)
        _LOGGER.info("W100 Diagnostic Information:\n%s", diagnostic_info)
        
        # Also fire an event with the diagnostic info
        hass.bus.async_fire(
            f"{DOMAIN}_diagnostic_info",
            {
                "device_name": device_name,
                "diagnostic_info": diagnostic_info,
                "timestamp": hass.helpers.utcnow().isoformat(),
            }
        )
    
    async def handle_validate_setup(call) -> None:
        """Handle validate setup service call."""
        entry_id = call.data.get("entry_id")
        
        # Find coordinator
        coordinator = None
        if entry_id and entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][entry_id]
        elif hass.data[DOMAIN]:
            # Use first available coordinator if no entry_id specified
            coordinator = next(iter(hass.data[DOMAIN].values()))
        
        if not coordinator:
            _LOGGER.error("No W100 coordinator found for setup validation")
            return
        
        # Validate setup
        validation_result = await coordinator.async_validate_setup()
        
        # Log validation results
        if validation_result["valid"]:
            _LOGGER.info("W100 setup validation passed")
        else:
            _LOGGER.warning("W100 setup validation found issues")
        
        for error in validation_result["errors"]:
            _LOGGER.error("Setup Error: %s", error["message"])
            
        for warning in validation_result["warnings"]:
            _LOGGER.warning("Setup Warning: %s", warning["message"])
        
        # Fire event with validation results
        hass.bus.async_fire(
            f"{DOMAIN}_validation_result",
            {
                "valid": validation_result["valid"],
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"],
                "device_status": validation_result["device_status"],
                "timestamp": hass.helpers.utcnow().isoformat(),
            }
        )
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        "get_diagnostic_info",
        handle_get_diagnostic_info,
        schema=vol.Schema({
            vol.Optional("device_name"): str,
            vol.Optional("entry_id"): str,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        "validate_setup",
        handle_validate_setup,
        schema=vol.Schema({
            vol.Optional("entry_id"): str,
        })
    )


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