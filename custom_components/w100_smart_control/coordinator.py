"""Data update coordinator for W100 Smart Control."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import STATE_UNAVAILABLE

# Generic thermostat domain constant
GENERIC_THERMOSTAT_DOMAIN = "generic_thermostat"

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
        self._thermostat_configs: dict[str, dict[str, Any]] = {}
        self._storage = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_thermostats")
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Load persisted thermostat data
        await self._async_load_thermostat_data()
        
        # Clean up any orphaned thermostats
        await self._async_cleanup_orphaned_thermostats()
        
        # Set up entity state change listeners for created thermostats
        await self._async_setup_thermostat_listeners()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from W100 device."""
        try:
            # Periodically validate thermostat entities (every 10 updates)
            if not hasattr(self, '_validation_counter'):
                self._validation_counter = 0
            
            self._validation_counter += 1
            if self._validation_counter >= 10:
                self._validation_counter = 0
                # Run validation in background to avoid blocking the update
                self.hass.async_create_task(self.async_cleanup_invalid_thermostats())
            
            # Basic data structure - will be expanded in later tasks
            return {
                "device_name": self.config.get("w100_device_name"),
                "status": "connected",
                "last_update": self.hass.helpers.utcnow(),
                "created_thermostats": len(self._created_thermostats),
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with W100 device: {err}") from err

    async def _async_load_thermostat_data(self) -> None:
        """Load persisted thermostat data from storage."""
        try:
            data = await self._storage.async_load()
            if data:
                self._created_thermostats = data.get("created_thermostats", [])
                self._thermostat_configs = data.get("thermostat_configs", {})
                _LOGGER.debug(
                    "Loaded %d thermostats from storage for entry %s",
                    len(self._created_thermostats),
                    self.entry.entry_id
                )
        except Exception as err:
            _LOGGER.warning("Failed to load thermostat data: %s", err)
            self._created_thermostats = []
            self._thermostat_configs = {}

    async def _async_save_thermostat_data(self) -> None:
        """Save thermostat data to storage."""
        try:
            data = {
                "created_thermostats": self._created_thermostats,
                "thermostat_configs": self._thermostat_configs,
            }
            await self._storage.async_save(data)
            _LOGGER.debug("Saved thermostat data to storage")
        except Exception as err:
            _LOGGER.error("Failed to save thermostat data: %s", err)

    async def _async_cleanup_orphaned_thermostats(self) -> None:
        """Clean up orphaned thermostats that exist in registry but not in our tracking."""
        try:
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)
            
            # Find all entities associated with this integration entry
            integration_entities = [
                entry for entry in entity_registry.entities.values()
                if entry.config_entry_id == self.entry.entry_id
                and entry.entity_id.startswith("climate.")
            ]
            
            orphaned_entities = []
            for entity_entry in integration_entities:
                entity_id = entity_entry.entity_id
                
                # Check if this is a thermostat we created but lost track of
                if (entity_id not in self._created_thermostats and 
                    entity_entry.original_name and 
                    "W100" in entity_entry.original_name and 
                    "Thermostat" in entity_entry.original_name):
                    
                    orphaned_entities.append(entity_id)
                    _LOGGER.warning("Found orphaned thermostat: %s", entity_id)
            
            # Clean up orphaned entities
            for entity_id in orphaned_entities:
                try:
                    await self._async_remove_thermostat_entity(entity_id)
                    _LOGGER.info("Cleaned up orphaned thermostat: %s", entity_id)
                except Exception as err:
                    _LOGGER.error("Failed to clean up orphaned thermostat %s: %s", entity_id, err)
                    
        except Exception as err:
            _LOGGER.error("Failed to cleanup orphaned thermostats: %s", err)

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
            
            # Set up state change listener for the new thermostat
            self.hass.helpers.event.async_track_state_change_event(
                entity_id,
                self._async_thermostat_state_changed
            )
            
            # Save thermostat data to persistent storage
            await self._async_save_thermostat_data()
            
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
            # Create device entry for the thermostat
            device_id = await self._async_create_thermostat_device(entity_id, config)
            
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
                await self._async_setup_thermostat_config(entity_id, config, device_id)
            else:
                # Platform is available, create entity directly
                _LOGGER.debug("Creating generic thermostat entity directly")
                await self._async_setup_thermostat_entity(entity_id, config, device_id)
                
        except Exception as err:
            _LOGGER.error("Failed to create thermostat entity %s: %s", entity_id, err)
            raise

    async def _async_create_thermostat_device(self, entity_id: str, config: dict[str, Any]) -> str:
        """Create device entry for the thermostat."""
        try:
            device_registry = dr.async_get(self.hass)
            w100_device_name = self.config.get("w100_device_name", "w100")
            
            # Create device entry
            device_entry = device_registry.async_get_or_create(
                config_entry_id=self.entry.entry_id,
                identifiers={(DOMAIN, f"thermostat_{entity_id}")},
                name=config.get("name", f"W100 {w100_device_name} Thermostat"),
                manufacturer="W100 Smart Control",
                model="Generic Thermostat",
                sw_version="1.0.0",
            )
            
            _LOGGER.debug("Created device entry %s for thermostat %s", device_entry.id, entity_id)
            return device_entry.id
            
        except Exception as err:
            _LOGGER.error("Failed to create device entry for thermostat %s: %s", entity_id, err)
            raise

    async def _async_setup_thermostat_config(self, entity_id: str, config: dict[str, Any], device_id: str) -> None:
        """Set up thermostat configuration through Home Assistant's config system."""
        # For now, we'll store the configuration and let the integration
        # handle the entity creation in the climate platform
        # This is a placeholder for the actual implementation
        _LOGGER.debug("Setting up thermostat configuration for %s with device %s", entity_id, device_id)
        
        # Store the thermostat configuration in the coordinator
        if not hasattr(self, '_thermostat_configs'):
            self._thermostat_configs = {}
        
        # Add device_id to config for entity registry integration
        config_with_device = {**config, "device_id": device_id}
        self._thermostat_configs[entity_id] = config_with_device
        
    async def _async_setup_thermostat_entity(self, entity_id: str, config: dict[str, Any], device_id: str) -> None:
        """Set up the thermostat entity directly."""
        # This is a placeholder for direct entity creation
        # The actual implementation will depend on how we integrate with
        # Home Assistant's generic_thermostat platform
        _LOGGER.debug("Setting up thermostat entity %s with device %s", entity_id, device_id)
        
        # Store the thermostat configuration for later use
        if not hasattr(self, '_thermostat_configs'):
            self._thermostat_configs = {}
        
        # Add device_id to config for entity registry integration
        config_with_device = {**config, "device_id": device_id}
        self._thermostat_configs[entity_id] = config_with_device
        
        # Register the entity in the entity registry
        await self._async_register_thermostat_entity(entity_id, config_with_device)

    async def _async_register_thermostat_entity(self, entity_id: str, config: dict[str, Any]) -> None:
        """Register thermostat entity in the entity registry."""
        try:
            entity_registry = er.async_get(self.hass)
            
            # Create entity registry entry
            entity_registry.async_get_or_create(
                domain="climate",
                platform=DOMAIN,
                unique_id=config.get("unique_id", f"{DOMAIN}_{entity_id}"),
                suggested_object_id=entity_id.split(".")[-1],
                config_entry=self.entry,
                device_id=config.get("device_id"),
                original_name=config.get("name"),
                entity_category=None,
            )
            
            _LOGGER.debug("Registered thermostat entity %s in registry", entity_id)
            
        except Exception as err:
            _LOGGER.error("Failed to register thermostat entity %s: %s", entity_id, err)
            raise

    async def async_remove_generic_thermostat(self, entity_id: str) -> None:
        """Remove a created generic thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat to remove
        """
        try:
            await self._async_remove_thermostat_entity(entity_id)
            
            # Remove from our tracking
            if entity_id in self._created_thermostats:
                self._created_thermostats.remove(entity_id)
            
            # Remove configuration if stored
            if entity_id in self._thermostat_configs:
                del self._thermostat_configs[entity_id]
            
            # Save updated data to storage
            await self._async_save_thermostat_data()
            
            _LOGGER.info("Removed generic thermostat %s", entity_id)
                
        except Exception as err:
            _LOGGER.error("Failed to remove generic thermostat %s: %s", entity_id, err)
            raise HomeAssistantError(f"Failed to remove generic thermostat: {err}") from err

    async def _async_remove_thermostat_entity(self, entity_id: str) -> None:
        """Remove thermostat entity from registry and disable it."""
        try:
            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.async_get(entity_id)
            
            if entity_entry:
                # First try to disable the entity to stop it gracefully
                entity_registry.async_update_entity(
                    entity_id, 
                    disabled_by=er.RegistryEntryDisabler.INTEGRATION
                )
                
                # Wait a moment for the entity to be disabled
                await self.hass.async_add_executor_job(lambda: None)
                
                # Remove from entity registry
                entity_registry.async_remove(entity_id)
                _LOGGER.debug("Removed thermostat entity %s from registry", entity_id)
                
                # Also clean up any associated device if it's no longer needed
                await self._async_cleanup_device_if_orphaned(entity_entry.device_id)
            else:
                _LOGGER.debug("Thermostat entity %s not found in registry", entity_id)
                
        except Exception as err:
            _LOGGER.error("Failed to remove thermostat entity %s: %s", entity_id, err)
            raise

    async def _async_cleanup_device_if_orphaned(self, device_id: str | None) -> None:
        """Clean up device entry if it has no more entities."""
        if not device_id:
            return
            
        try:
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)
            
            # Check if device has any remaining entities
            device_entities = [
                entry for entry in entity_registry.entities.values()
                if entry.device_id == device_id
            ]
            
            # If no entities remain and device was created by this integration, remove it
            if not device_entities:
                device_entry = device_registry.async_get(device_id)
                if (device_entry and 
                    device_entry.config_entries and 
                    self.entry.entry_id in device_entry.config_entries):
                    
                    device_registry.async_remove_device(device_id)
                    _LOGGER.debug("Removed orphaned device %s", device_id)
                    
        except Exception as err:
            _LOGGER.warning("Failed to cleanup orphaned device %s: %s", device_id, err)

    async def async_update_generic_thermostat(self, entity_id: str, config: dict[str, Any]) -> None:
        """Update configuration of an existing generic thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat to update
            config: New configuration dictionary
        """
        try:
            if entity_id not in self._created_thermostats:
                raise HomeAssistantError(f"Thermostat {entity_id} not managed by this integration")
            
            # Validate the new configuration
            heater_entity = config.get(CONF_HEATER_SWITCH)
            target_sensor = config.get(CONF_TEMPERATURE_SENSOR)
            
            if heater_entity and not self.hass.states.get(heater_entity):
                raise HomeAssistantError(f"Heater entity {heater_entity} not found")
            
            if target_sensor and not self.hass.states.get(target_sensor):
                raise HomeAssistantError(f"Temperature sensor {target_sensor} not found")
            
            # Update stored configuration
            old_config = self._thermostat_configs.get(entity_id, {})
            updated_config = {**old_config, **config}
            
            # Ensure precision is compatible with W100 (0.5°C increments)
            precision = updated_config.get(CONF_PRECISION, DEFAULT_PRECISION)
            if precision != 0.5:
                _LOGGER.warning(
                    "Adjusting thermostat precision from %s to 0.5°C for W100 compatibility",
                    precision
                )
                updated_config[CONF_PRECISION] = 0.5
            
            # Check if critical configuration changed that requires recreation
            critical_changes = self._check_critical_config_changes(old_config, updated_config)
            
            if critical_changes:
                _LOGGER.info(
                    "Critical configuration changes detected for %s, recreating thermostat",
                    entity_id
                )
                await self._async_recreate_thermostat(entity_id, updated_config)
            else:
                # Just update the configuration
                self._thermostat_configs[entity_id] = updated_config
                await self._async_update_thermostat_entity(entity_id, updated_config)
            
            # Save updated configuration to storage
            await self._async_save_thermostat_data()
            
            _LOGGER.info("Updated generic thermostat %s configuration", entity_id)
            
        except Exception as err:
            _LOGGER.error("Failed to update generic thermostat %s: %s", entity_id, err)
            raise HomeAssistantError(f"Failed to update generic thermostat: {err}") from err

    def _check_critical_config_changes(self, old_config: dict[str, Any], new_config: dict[str, Any]) -> bool:
        """Check if configuration changes require thermostat recreation."""
        critical_keys = ["heater", "target_sensor", "unique_id"]
        
        for key in critical_keys:
            if old_config.get(key) != new_config.get(key):
                return True
        
        return False

    async def _async_recreate_thermostat(self, entity_id: str, config: dict[str, Any]) -> None:
        """Recreate a thermostat with new configuration."""
        try:
            # Remove the old thermostat
            await self._async_remove_thermostat_entity(entity_id)
            
            # Wait a moment for cleanup
            await asyncio.sleep(1)
            
            # Create new thermostat with updated configuration
            device_id = config.get("device_id")
            if not device_id:
                device_id = await self._async_create_thermostat_device(entity_id, config)
                config["device_id"] = device_id
            
            await self._async_setup_thermostat_entity(entity_id, config, device_id)
            
            # Update stored configuration
            self._thermostat_configs[entity_id] = config
            
            # Set up state listener for the recreated thermostat
            self.hass.helpers.event.async_track_state_change_event(
                entity_id,
                self._async_thermostat_state_changed
            )
            
            _LOGGER.info("Successfully recreated thermostat %s", entity_id)
            
        except Exception as err:
            _LOGGER.error("Failed to recreate thermostat %s: %s", entity_id, err)
            raise

    async def _async_update_thermostat_entity(self, entity_id: str, config: dict[str, Any]) -> None:
        """Update thermostat entity with new configuration."""
        try:
            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.async_get(entity_id)
            
            if entity_entry:
                # Update entity registry entry with new name if needed
                friendly_name = config.get("name")
                if friendly_name and friendly_name != entity_entry.original_name:
                    entity_registry.async_update_entity(
                        entity_id,
                        original_name=friendly_name,
                        name=friendly_name
                    )
                
                # For generic thermostat, we need to trigger a reload of the entity
                # This is typically handled by the platform, but we can signal the need for update
                _LOGGER.debug("Updated thermostat entity registry for %s", entity_id)
            
        except Exception as err:
            _LOGGER.error("Failed to update thermostat entity %s: %s", entity_id, err)
            raise

    async def async_remove_all_thermostats(self) -> None:
        """Remove all thermostats created by this integration entry."""
        try:
            thermostats_to_remove = self._created_thermostats.copy()
            
            for entity_id in thermostats_to_remove:
                try:
                    await self.async_remove_generic_thermostat(entity_id)
                except Exception as err:
                    _LOGGER.error("Error removing thermostat %s during cleanup: %s", entity_id, err)
            
            # Clear all data
            self._created_thermostats.clear()
            self._thermostat_configs.clear()
            
            # Save cleared data
            await self._async_save_thermostat_data()
            
            _LOGGER.info("Removed all thermostats for integration entry %s", self.entry.entry_id)
            
        except Exception as err:
            _LOGGER.error("Failed to remove all thermostats: %s", err)
            raise HomeAssistantError(f"Failed to remove all thermostats: {err}") from err

    @property
    def created_thermostats(self) -> list[str]:
        """Return list of created thermostat entity IDs."""
        return self._created_thermostats.copy()

    @property
    def thermostat_configs(self) -> dict[str, dict[str, Any]]:
        """Return thermostat configurations."""
        return self._thermostat_configs.copy()

    async def async_update_config(self, new_config: dict[str, Any]) -> None:
        """Update integration configuration and apply to created thermostats."""
        try:
            # Update the config entry data
            old_config = self.config.copy()
            self.config = {**old_config, **new_config}
            
            # Update the entry data
            self.hass.config_entries.async_update_entry(
                self.entry, data=self.config
            )
            
            # Apply configuration changes to created thermostats if needed
            for entity_id in self._created_thermostats:
                try:
                    # Check if thermostat-specific config needs updating
                    thermostat_config = self._thermostat_configs.get(entity_id, {})
                    
                    # Update thermostat name if device name changed
                    if "w100_device_name" in new_config:
                        new_device_name = new_config["w100_device_name"]
                        old_device_name = old_config.get("w100_device_name", "")
                        
                        if new_device_name != old_device_name:
                            # Update thermostat name
                            new_name = f"W100 {new_device_name.replace('_', ' ').title()} Thermostat"
                            thermostat_config["name"] = new_name
                            self._thermostat_configs[entity_id] = thermostat_config
                            
                            # Update entity registry
                            await self._async_update_thermostat_entity(entity_id, thermostat_config)
                    
                except Exception as err:
                    _LOGGER.error("Failed to update thermostat %s with new config: %s", entity_id, err)
            
            # Save updated thermostat configurations
            await self._async_save_thermostat_data()
            
            _LOGGER.info("Updated integration configuration")
            
        except Exception as err:
            _LOGGER.error("Failed to update integration configuration: %s", err)
            raise HomeAssistantError(f"Failed to update configuration: {err}") from err

    async def async_on_entry_update(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle integration entry updates."""
        try:
            # Update our stored entry reference
            self.entry = entry
            old_config = self.config.copy()
            self.config = entry.data
            
            # Check if any thermostat-affecting configuration changed
            config_changed = False
            
            # Check for device name changes
            old_device_name = old_config.get("w100_device_name", "")
            new_device_name = self.config.get("w100_device_name", "")
            
            if old_device_name != new_device_name:
                config_changed = True
                _LOGGER.info(
                    "Device name changed from '%s' to '%s', updating thermostats",
                    old_device_name, new_device_name
                )
            
            # Apply configuration changes to created thermostats
            if config_changed:
                await self._async_apply_config_changes(old_config, self.config)
            
            _LOGGER.debug("Processed entry update for %s", entry.entry_id)
            
        except Exception as err:
            _LOGGER.error("Error handling entry update: %s", err)

    async def _async_apply_config_changes(self, old_config: dict[str, Any], new_config: dict[str, Any]) -> None:
        """Apply configuration changes to existing thermostats."""
        try:
            for entity_id in self._created_thermostats:
                thermostat_config = self._thermostat_configs.get(entity_id, {})
                config_updated = False
                
                # Update thermostat name if device name changed
                old_device_name = old_config.get("w100_device_name", "")
                new_device_name = new_config.get("w100_device_name", "")
                
                if old_device_name != new_device_name and new_device_name:
                    new_name = f"W100 {new_device_name.replace('_', ' ').title()} Thermostat"
                    thermostat_config["name"] = new_name
                    config_updated = True
                
                # Save updated configuration
                if config_updated:
                    self._thermostat_configs[entity_id] = thermostat_config
                    await self._async_update_thermostat_entity(entity_id, thermostat_config)
                    _LOGGER.debug("Updated thermostat %s with new configuration", entity_id)
            
            # Save all changes to storage
            if self._created_thermostats:
                await self._async_save_thermostat_data()
                
        except Exception as err:
            _LOGGER.error("Error applying configuration changes to thermostats: %s", err)

    async def async_validate_thermostat_entities(self) -> list[str]:
        """Validate that all created thermostats still exist and are accessible.
        
        Returns:
            List of entity IDs that are no longer valid
        """
        invalid_entities = []
        
        try:
            entity_registry = er.async_get(self.hass)
            
            for entity_id in self._created_thermostats:
                # Check if entity exists in registry
                entity_entry = entity_registry.async_get(entity_id)
                if not entity_entry:
                    invalid_entities.append(entity_id)
                    _LOGGER.warning("Thermostat entity %s no longer exists in registry", entity_id)
                    continue
                
                # Check if entity state is available
                state = self.hass.states.get(entity_id)
                if not state or state.state == STATE_UNAVAILABLE:
                    _LOGGER.warning("Thermostat entity %s is unavailable", entity_id)
                    # Don't mark as invalid just for being unavailable, as it might recover
                
                # Validate that the underlying entities still exist
                thermostat_config = self._thermostat_configs.get(entity_id, {})
                heater_entity = thermostat_config.get("heater")
                target_sensor = thermostat_config.get("target_sensor")
                
                if heater_entity and not self.hass.states.get(heater_entity):
                    _LOGGER.warning(
                        "Heater entity %s for thermostat %s no longer exists",
                        heater_entity, entity_id
                    )
                
                if target_sensor and not self.hass.states.get(target_sensor):
                    _LOGGER.warning(
                        "Temperature sensor %s for thermostat %s no longer exists",
                        target_sensor, entity_id
                    )
            
        except Exception as err:
            _LOGGER.error("Error validating thermostat entities: %s", err)
        
        return invalid_entities

    async def async_cleanup_invalid_thermostats(self) -> None:
        """Clean up thermostats that are no longer valid."""
        try:
            invalid_entities = await self.async_validate_thermostat_entities()
            
            for entity_id in invalid_entities:
                try:
                    # Remove from our tracking
                    if entity_id in self._created_thermostats:
                        self._created_thermostats.remove(entity_id)
                    
                    # Remove configuration if stored
                    if entity_id in self._thermostat_configs:
                        del self._thermostat_configs[entity_id]
                    
                    _LOGGER.info("Cleaned up invalid thermostat %s", entity_id)
                    
                except Exception as err:
                    _LOGGER.error("Error cleaning up invalid thermostat %s: %s", entity_id, err)
            
            # Save updated data if we removed any thermostats
            if invalid_entities:
                await self._async_save_thermostat_data()
                
        except Exception as err:
            _LOGGER.error("Error during invalid thermostat cleanup: %s", err)

    async def _async_setup_thermostat_listeners(self) -> None:
        """Set up state change listeners for created thermostats."""
        try:
            for entity_id in self._created_thermostats:
                # Set up state change listener for each thermostat
                self.hass.helpers.event.async_track_state_change_event(
                    entity_id,
                    self._async_thermostat_state_changed
                )
                _LOGGER.debug("Set up state listener for thermostat %s", entity_id)
                
        except Exception as err:
            _LOGGER.error("Error setting up thermostat listeners: %s", err)

    @callback
    def _async_thermostat_state_changed(self, event) -> None:
        """Handle thermostat state changes."""
        try:
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            
            if not entity_id or entity_id not in self._created_thermostats:
                return
            
            # Log significant state changes
            if new_state and old_state:
                if new_state.state != old_state.state:
                    _LOGGER.debug(
                        "Thermostat %s state changed from %s to %s",
                        entity_id, old_state.state, new_state.state
                    )
                
                # Check for temperature changes
                old_temp = old_state.attributes.get("temperature")
                new_temp = new_state.attributes.get("temperature")
                if old_temp != new_temp:
                    _LOGGER.debug(
                        "Thermostat %s temperature changed from %s to %s",
                        entity_id, old_temp, new_temp
                    )
            
            # Handle entity becoming unavailable
            if new_state and new_state.state == STATE_UNAVAILABLE:
                _LOGGER.warning("Thermostat %s became unavailable", entity_id)
                # Schedule validation to check if it recovers
                self.hass.async_create_task(
                    self._async_delayed_validation(entity_id)
                )
            
        except Exception as err:
            _LOGGER.error("Error handling thermostat state change: %s", err)

    async def _async_delayed_validation(self, entity_id: str) -> None:
        """Perform delayed validation of a thermostat entity."""
        try:
            # Wait a bit to see if the entity recovers
            await asyncio.sleep(30)
            
            # Check if entity is still unavailable
            state = self.hass.states.get(entity_id)
            if not state or state.state == STATE_UNAVAILABLE:
                _LOGGER.warning(
                    "Thermostat %s still unavailable after 30 seconds, running validation",
                    entity_id
                )
                await self.async_cleanup_invalid_thermostats()
            else:
                _LOGGER.debug("Thermostat %s recovered", entity_id)
                
        except Exception as err:
            _LOGGER.error("Error in delayed validation for %s: %s", entity_id, err)

    async def async_cleanup(self) -> None:
        """Clean up coordinator resources."""
        try:
            # Remove all thermostats created by this integration
            await self.async_remove_all_thermostats()
            
            # Clean up storage
            try:
                await self._storage.async_remove()
                _LOGGER.debug("Removed thermostat storage for entry %s", self.entry.entry_id)
            except Exception as err:
                _LOGGER.warning("Failed to remove thermostat storage: %s", err)
            
            _LOGGER.info("Cleaned up W100 coordinator for entry %s", self.entry.entry_id)
            
        except Exception as err:
            _LOGGER.error("Error during coordinator cleanup: %s", err)