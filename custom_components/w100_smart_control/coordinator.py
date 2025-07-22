"""Data update coordinator for W100 Smart Control."""
from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import async_get_platforms
# Generic thermostat domain constant
GENERIC_THERMOSTAT_DOMAIN = "generic_thermostat"
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN, 
    UPDATE_INTERVAL_SECONDS,
    CONF_GENERIC_THERMOSTAT_CONFIG,
    CONF_HEATER_SWITCH,
    CONF_TEMPERATURE_SENSOR,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_TARGET_TEMP,
    CONF_COLD_TOLERANCE,
    CONF_HOT_TOLERANCE,
    CONF_PRECISION,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_TARGET_TEMP,
    DEFAULT_COLD_TOLERANCE,
    DEFAULT_HOT_TOLERANCE,
    DEFAULT_PRECISION,
)

_LOGGER = logging.getLogger(__name__)


class W100Coordinator(DataUpdateCoordinator):
    """Class to manage fetching W100 data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.config = entry.data
        self._created_thermostats: list[str] = []
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from W100 device."""
        try:
            # Basic data structure - will be expanded in later tasks
            return {
                "device_name": self.config.get("w100_device_name"),
                "status": "connected",
                "last_update": self.hass.helpers.utcnow(),
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with W100 device: {err}") from err

    async def async_create_generic_thermostat(self, config: dict[str, Any]) -> str:
        """Create a generic thermostat entity with W100-compatible settings.
        
        Args:
            config: Generic thermostat configuration dictionary
            
        Returns:
            str: The entity ID of the created thermostat
            
        Raises:
            HomeAssistantError: If thermostat creation fails
        """
        try:
            # Extract configuration with defaults
            heater_entity = config.get(CONF_HEATER_SWITCH)
            target_sensor = config.get(CONF_TEMPERATURE_SENSOR)
            min_temp = config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)
            max_temp = config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)
            target_temp = config.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP)
            cold_tolerance = config.get(CONF_COLD_TOLERANCE, DEFAULT_COLD_TOLERANCE)
            hot_tolerance = config.get(CONF_HOT_TOLERANCE, DEFAULT_HOT_TOLERANCE)
            precision = config.get(CONF_PRECISION, DEFAULT_PRECISION)
            
            # Validate required entities exist
            if not self.hass.states.get(heater_entity):
                raise HomeAssistantError(f"Heater entity {heater_entity} not found")
            
            if not self.hass.states.get(target_sensor):
                raise HomeAssistantError(f"Temperature sensor {target_sensor} not found")
            
            # Generate unique entity ID and name
            w100_device_name = self.config.get("w100_device_name", "w100")
            base_name = f"w100_{self._sanitize_name(w100_device_name)}_thermostat"
            entity_id = await self._generate_unique_entity_id(base_name)
            friendly_name = f"W100 {w100_device_name.replace('_', ' ').title()} Thermostat"
            
            # Ensure precision is compatible with W100 (0.5°C increments)
            if precision != 0.5:
                _LOGGER.warning(
                    "Adjusting thermostat precision from %s to 0.5°C for W100 compatibility",
                    precision
                )
                precision = 0.5
            
            # Create generic thermostat configuration
            thermostat_config = {
                "name": friendly_name,
                "heater": heater_entity,
                "target_sensor": target_sensor,
                "min_temp": min_temp,
                "max_temp": max_temp,
                "target_temp": target_temp,
                "cold_tolerance": cold_tolerance,
                "hot_tolerance": hot_tolerance,
                "precision": precision,
                "initial_hvac_mode": "off",
                "unique_id": f"{DOMAIN}_{entity_id}",
            }
            
            # Create the generic thermostat entity
            await self._async_create_thermostat_entity(entity_id, thermostat_config)
            
            # Track created thermostat for cleanup
            self._created_thermostats.append(entity_id)
            
            _LOGGER.info(
                "Created generic thermostat %s for W100 device %s",
                entity_id,
                w100_device_name
            )
            
            return entity_id
            
        except Exception as err:
            _LOGGER.error("Failed to create generic thermostat: %s", err)
            raise HomeAssistantError(f"Failed to create generic thermostat: {err}") from err

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in entity IDs."""
        # Convert to lowercase and replace non-alphanumeric characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        return sanitized.strip('_')

    async def _generate_unique_entity_id(self, base_name: str) -> str:
        """Generate a unique entity ID for the thermostat."""
        entity_registry = er.async_get(self.hass)
        
        # Start with the base name
        entity_id = f"climate.{base_name}"
        counter = 1
        
        # Check if entity ID already exists in registry or in our created list
        while (entity_registry.async_get(entity_id) is not None or 
               entity_id in self._created_thermostats):
            entity_id = f"climate.{base_name}_{counter}"
            counter += 1
        
        return entity_id

    async def _async_create_thermostat_entity(self, entity_id: str, config: dict[str, Any]) -> None:
        """Create the actual generic thermostat entity.
        
        This method handles the creation of the generic thermostat entity
        using Home Assistant's generic_thermostat platform.
        """
        try:
            # Get the generic_thermostat platform
            platform = None
            for platform_info in async_get_platforms(self.hass, GENERIC_THERMOSTAT_DOMAIN):
                if platform_info.domain == GENERIC_THERMOSTAT_DOMAIN:
                    platform = platform_info.platform
                    break
            
            if platform is None:
                # If platform is not loaded, we need to set up the configuration
                # This will be handled by Home Assistant's configuration system
                _LOGGER.debug("Generic thermostat platform not loaded, creating configuration entry")
                
                # Create a configuration entry for the generic thermostat
                # This approach allows Home Assistant to manage the entity lifecycle
                await self._async_setup_thermostat_config(entity_id, config)
            else:
                # Platform is available, create entity directly
                _LOGGER.debug("Creating generic thermostat entity directly")
                await self._async_setup_thermostat_entity(entity_id, config)
                
        except Exception as err:
            _LOGGER.error("Failed to create thermostat entity %s: %s", entity_id, err)
            raise

    async def _async_setup_thermostat_config(self, entity_id: str, config: dict[str, Any]) -> None:
        """Set up thermostat configuration through Home Assistant's config system."""
        # For now, we'll store the configuration and let the integration
        # handle the entity creation in the climate platform
        # This is a placeholder for the actual implementation
        _LOGGER.debug("Setting up thermostat configuration for %s", entity_id)
        
        # Store the thermostat configuration in the coordinator
        if not hasattr(self, '_thermostat_configs'):
            self._thermostat_configs = {}
        
        self._thermostat_configs[entity_id] = config
        
    async def _async_setup_thermostat_entity(self, entity_id: str, config: dict[str, Any]) -> None:
        """Set up the thermostat entity directly."""
        # This is a placeholder for direct entity creation
        # The actual implementation will depend on how we integrate with
        # Home Assistant's generic_thermostat platform
        _LOGGER.debug("Setting up thermostat entity %s", entity_id)
        
        # Store the thermostat configuration for later use
        if not hasattr(self, '_thermostat_configs'):
            self._thermostat_configs = {}
        
        self._thermostat_configs[entity_id] = config

    async def async_remove_generic_thermostat(self, entity_id: str) -> None:
        """Remove a created generic thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat to remove
        """
        try:
            if entity_id in self._created_thermostats:
                # Remove from entity registry
                entity_registry = er.async_get(self.hass)
                if entity_registry.async_get(entity_id):
                    entity_registry.async_remove(entity_id)
                
                # Remove from our tracking
                self._created_thermostats.remove(entity_id)
                
                # Remove configuration if stored
                if hasattr(self, '_thermostat_configs') and entity_id in self._thermostat_configs:
                    del self._thermostat_configs[entity_id]
                
                _LOGGER.info("Removed generic thermostat %s", entity_id)
            else:
                _LOGGER.warning("Thermostat %s not found in created thermostats list", entity_id)
                
        except Exception as err:
            _LOGGER.error("Failed to remove generic thermostat %s: %s", entity_id, err)
            raise HomeAssistantError(f"Failed to remove generic thermostat: {err}") from err

    @property
    def created_thermostats(self) -> list[str]:
        """Return list of created thermostat entity IDs."""
        return self._created_thermostats.copy()

    @property
    def thermostat_configs(self) -> dict[str, dict[str, Any]]:
        """Return thermostat configurations."""
        return getattr(self, '_thermostat_configs', {}).copy()

    async def async_cleanup(self) -> None:
        """Clean up coordinator resources."""
        # Clean up created thermostats
        for entity_id in self._created_thermostats.copy():
            try:
                await self.async_remove_generic_thermostat(entity_id)
            except Exception as err:
                _LOGGER.error("Error cleaning up thermostat %s: %s", entity_id, err)
        
        _LOGGER.debug("Cleaning up W100 coordinator")