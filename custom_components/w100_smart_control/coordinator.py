"""Data update coordinator for W100 Smart Control."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.components import mqtt
from homeassistant.components.mqtt.models import ReceiveMessage

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
    CONF_W100_DEVICE_NAME,
    CONF_HUMIDITY_SENSOR,
    CONF_BACKUP_HUMIDITY_SENSOR,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_TARGET_TEMP,
    DEFAULT_COLD_TOLERANCE,
    DEFAULT_HOT_TOLERANCE,
    DEFAULT_PRECISION,
    MQTT_W100_ACTION_TOPIC,
    MQTT_W100_STATE_TOPIC,
    MQTT_W100_SET_TOPIC,
    W100_ACTION_TOGGLE,
    W100_ACTION_PLUS,
    W100_ACTION_MINUS,
    DISPLAY_UPDATE_DELAY_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class W100Coordinator(DataUpdateCoordinator):
    """Class to manage fetching W100 data with multi-device support."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.config = entry.data
        self._created_thermostats: list[str] = []
        self._thermostat_configs: dict[str, dict[str, Any]] = {}
        self._storage = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_thermostats")
        
        # Multi-device state tracking - each device operates independently
        self._device_states: dict[str, dict[str, Any]] = {}
        self._device_configs: dict[str, dict[str, Any]] = {}
        self._device_thermostats: dict[str, list[str]] = {}  # device_name -> [thermostat_entity_ids]
        self._mqtt_subscriptions: dict[str, list[str]] = {}  # device_name -> [topic_list]
        self._last_action_time: dict[str, datetime] = {}
        
        # Multi-device storage for persistence
        self._device_storage = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_devices")
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    async def async_setup(self) -> None:
        """Set up the coordinator with multi-device support."""
        # Load persisted device and thermostat data
        await self._async_load_device_data()
        await self._async_load_thermostat_data()
        
        # Clean up any orphaned thermostats
        await self._async_cleanup_orphaned_thermostats()
        
        # Set up entity state change listeners for created thermostats
        await self._async_setup_thermostat_listeners()
        
        # Set up MQTT listeners for all configured W100 devices
        await self._async_setup_all_mqtt_listeners()
        
        # Initialize device states for all devices
        await self._async_initialize_all_device_states()

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
            
            # Update device states from MQTT
            await self._async_update_device_states()
            
            # Sync W100 displays with current climate states
            await self._async_sync_all_displays()
            
            # Return current state data
            device_name = self.config.get(CONF_W100_DEVICE_NAME, "unknown")
            device_state = self._device_states.get(device_name, {})
            
            return {
                "device_name": device_name,
                "device_state": device_state,
                "status": "connected" if device_state else "disconnected",
                "last_update": datetime.now(),
                "created_thermostats": len(self._created_thermostats),
                "device_states": self._device_states.copy(),
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with W100 device: {err}") from err

    async def _async_load_device_data(self) -> None:
        """Load persisted device data from storage."""
        try:
            data = await self._device_storage.async_load()
            if data:
                self._device_configs = data.get("device_configs", {})
                self._device_thermostats = data.get("device_thermostats", {})
                _LOGGER.debug(
                    "Loaded %d device configurations from storage for entry %s",
                    len(self._device_configs),
                    self.entry.entry_id
                )
                
                # Migrate single device config to multi-device format if needed
                await self._async_migrate_single_device_config()
        except Exception as err:
            _LOGGER.warning("Failed to load device data: %s", err)
            self._device_configs = {}
            self._device_thermostats = {}
            # Try to migrate from single device config
            await self._async_migrate_single_device_config()

    async def _async_migrate_single_device_config(self) -> None:
        """Migrate single device configuration to multi-device format."""
        try:
            # Check if we have old single-device config format
            device_name = self.config.get(CONF_W100_DEVICE_NAME)
            if device_name and device_name not in self._device_configs:
                _LOGGER.info("Migrating single device config to multi-device format for %s", device_name)
                
                # Create device config from entry data
                device_config = {
                    CONF_W100_DEVICE_NAME: device_name,
                    CONF_CLIMATE_ENTITY_TYPE: self.config.get(CONF_CLIMATE_ENTITY_TYPE),
                    CONF_EXISTING_CLIMATE_ENTITY: self.config.get(CONF_EXISTING_CLIMATE_ENTITY),
                    CONF_GENERIC_THERMOSTAT_CONFIG: self.config.get(CONF_GENERIC_THERMOSTAT_CONFIG, {}),
                    CONF_HEATING_TEMPERATURE: self.config.get(CONF_HEATING_TEMPERATURE, DEFAULT_HEATING_TEMPERATURE),
                    CONF_IDLE_TEMPERATURE: self.config.get(CONF_IDLE_TEMPERATURE, DEFAULT_IDLE_TEMPERATURE),
                    CONF_HEATING_WARM_LEVEL: self.config.get(CONF_HEATING_WARM_LEVEL, DEFAULT_HEATING_WARM_LEVEL),
                    CONF_IDLE_WARM_LEVEL: self.config.get(CONF_IDLE_WARM_LEVEL, DEFAULT_IDLE_WARM_LEVEL),
                    CONF_IDLE_FAN_SPEED: self.config.get(CONF_IDLE_FAN_SPEED, DEFAULT_IDLE_FAN_SPEED),
                    CONF_SWING_MODE: self.config.get(CONF_SWING_MODE, DEFAULT_SWING_MODE),
                    CONF_BEEP_MODE: self.config.get(CONF_BEEP_MODE, DEFAULT_BEEP_MODE),
                    CONF_HUMIDITY_SENSOR: self.config.get(CONF_HUMIDITY_SENSOR),
                    CONF_BACKUP_HUMIDITY_SENSOR: self.config.get(CONF_BACKUP_HUMIDITY_SENSOR),
                }
                
                # Store device config
                self._device_configs[device_name] = device_config
                
                # Initialize device thermostat tracking
                if device_name not in self._device_thermostats:
                    self._device_thermostats[device_name] = []
                
                # Save migrated data
                await self._async_save_device_data()
                
                _LOGGER.info("Successfully migrated device config for %s", device_name)
                
        except Exception as err:
            _LOGGER.error("Failed to migrate single device config: %s", err)

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

    async def _async_setup_thermostat_listeners(self) -> None:
        """Set up state change listeners for created thermostats."""
        try:
            for entity_id in self._created_thermostats:
                self.hass.helpers.event.async_track_state_change_event(
                    entity_id,
                    self._async_thermostat_state_changed
                )
            
            _LOGGER.debug("Set up state listeners for %d thermostats", len(self._created_thermostats))
            
        except Exception as err:
            _LOGGER.error("Failed to set up thermostat listeners: %s", err)

    @callback
    def _async_thermostat_state_changed(self, event) -> None:
        """Handle thermostat state changes."""
        try:
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            
            if not entity_id or not new_state:
                return
            
            _LOGGER.debug(
                "Thermostat %s state changed from %s to %s",
                entity_id,
                old_state.state if old_state else "unknown",
                new_state.state
            )
            
            # Trigger display sync when thermostat state changes
            # Find which device this thermostat belongs to
            device_name = None
            for dev_name, thermostats in self._device_thermostats.items():
                if entity_id in thermostats:
                    device_name = dev_name
                    break
            
            # Fallback to primary device if not found in device thermostats
            if not device_name:
                device_name = self.config.get(CONF_W100_DEVICE_NAME)
            
            if device_name:
                self.hass.async_create_task(
                    self.async_sync_w100_display(device_name)
                )
            
        except Exception as err:
            _LOGGER.error("Error handling thermostat state change: %s", err)

    async def async_cleanup_invalid_thermostats(self) -> None:
        """Clean up invalid or orphaned thermostats."""
        try:
            entity_registry = er.async_get(self.hass)
            invalid_thermostats = []
            
            for entity_id in self._created_thermostats:
                entity_entry = entity_registry.async_get(entity_id)
                if not entity_entry:
                    invalid_thermostats.append(entity_id)
                    continue
                
                # Check if the entity still exists in the state machine
                state = self.hass.states.get(entity_id)
                if not state:
                    invalid_thermostats.append(entity_id)
            
            # Remove invalid thermostats
            for entity_id in invalid_thermostats:
                try:
                    await self.async_remove_generic_thermostat(entity_id)
                    _LOGGER.info("Cleaned up invalid thermostat: %s", entity_id)
                except Exception as err:
                    _LOGGER.error("Failed to clean up invalid thermostat %s: %s", entity_id, err)
            
            if invalid_thermostats:
                _LOGGER.info("Cleaned up %d invalid thermostats", len(invalid_thermostats))
            
        except Exception as err:
            _LOGGER.error("Failed to cleanup invalid thermostats: %s", err)

    async def _async_save_device_data(self) -> None:
        """Save device data to storage."""
        try:
            data = {
                "device_configs": self._device_configs,
                "device_thermostats": self._device_thermostats,
            }
            await self._device_storage.async_save(data)
            _LOGGER.debug("Saved device data to storage")
        except Exception as err:
            _LOGGER.error("Failed to save device data: %s", err)

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
            
            # Associate thermostat with device
            device_name = self.config.get(CONF_W100_DEVICE_NAME, "unknown")
            if device_name not in self._device_thermostats:
                self._device_thermostats[device_name] = []
            self._device_thermostats[device_name].append(entity_id)
            
            # Set up state change listener for the new thermostat
            self.hass.helpers.event.async_track_state_change_event(
                entity_id,
                self._async_thermostat_state_changed
            )
            
            # Save thermostat and device data to persistent storage
            await self._async_save_thermostat_data()
            await self._async_save_device_data()
            
            _LOGGER.info(
                "Created generic thermostat %s for W100 device %s",
                entity_id,
                w100_device_name
            )
            
            return entity_id
            
        except Exception as err:
            _LOGGER.error("Failed to create generic thermostat: %s", err)
            raise HomeAssistantError(f"Failed to create generic thermostat: {err}") from err

    async def async_create_device_thermostat(self, device_name: str, config: dict[str, Any]) -> str:
        """Create a generic thermostat entity for a specific W100 device.
        
        Args:
            device_name: Name of the W100 device
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
            
            # Generate unique entity ID and name for this device
            base_name = f"w100_{self._sanitize_name(device_name)}_thermostat"
            entity_id = await self._generate_unique_entity_id(base_name)
            friendly_name = f"W100 {device_name.replace('_', ' ').title()} Thermostat"
            
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
                "unique_id": f"{DOMAIN}_{device_name}_{entity_id}",
                "device_name": device_name,
            }
            
            # Create the generic thermostat entity
            await self._async_create_thermostat_entity(entity_id, thermostat_config)
            
            # Track created thermostat for cleanup
            self._created_thermostats.append(entity_id)
            
            # Associate thermostat with specific device
            if device_name not in self._device_thermostats:
                self._device_thermostats[device_name] = []
            self._device_thermostats[device_name].append(entity_id)
            
            # Set up state change listener for the new thermostat
            self.hass.helpers.event.async_track_state_change_event(
                entity_id,
                self._async_thermostat_state_changed
            )
            
            # Save thermostat and device data to persistent storage
            await self._async_save_thermostat_data()
            await self._async_save_device_data()
            
            _LOGGER.info(
                "Created generic thermostat %s for W100 device %s",
                entity_id,
                device_name
            )
            
            return entity_id
            
        except Exception as err:
            _LOGGER.error("Failed to create generic thermostat for device %s: %s", device_name, err)
            raise HomeAssistantError(f"Failed to create generic thermostat for device {device_name}: {err}") from err

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
            
            # Remove from device thermostat tracking
            for device_name, thermostats in self._device_thermostats.items():
                if entity_id in thermostats:
                    thermostats.remove(entity_id)
                    _LOGGER.debug("Removed thermostat %s from device %s tracking", entity_id, device_name)
                    break
            
            # Remove configuration if stored
            if entity_id in self._thermostat_configs:
                del self._thermostat_configs[entity_id]
            
            # Save updated data to storage
            await self._async_save_thermostat_data()
            await self._async_save_device_data()
            
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
                        original_name=friendly_name
                    )
                    _LOGGER.debug("Updated thermostat %s name to %s", entity_id, friendly_name)
            
        except Exception as err:
            _LOGGER.error("Failed to update thermostat entity %s: %s", entity_id, err)
            raise

    async def _async_setup_all_mqtt_listeners(self) -> None:
        """Set up MQTT listeners for all configured W100 devices."""
        try:
            # Check if MQTT is available
            if not self.hass.services.has_service("mqtt", "publish"):
                _LOGGER.error("MQTT integration not available, cannot set up W100 listeners")
                return
            
            # Clean up any existing subscriptions first
            await self._async_cleanup_all_mqtt_subscriptions()
            
            # Set up listeners for each configured device
            devices_to_setup = []
            
            # Add devices from device configs (multi-device format)
            for device_name in self._device_configs:
                devices_to_setup.append(device_name)
            
            # Add device from main config (backward compatibility)
            main_device = self.config.get(CONF_W100_DEVICE_NAME)
            if main_device and main_device not in devices_to_setup:
                devices_to_setup.append(main_device)
            
            if not devices_to_setup:
                _LOGGER.warning("No W100 devices configured, skipping MQTT setup")
                return
            
            # Set up MQTT listeners for each device
            for device_name in devices_to_setup:
                await self._async_setup_device_mqtt_listeners(device_name)
            
            _LOGGER.info("Successfully set up MQTT listeners for %d W100 devices", len(devices_to_setup))
            
        except Exception as err:
            _LOGGER.error("Failed to set up MQTT listeners for W100 devices: %s", err)

    async def _async_setup_device_mqtt_listeners(self, device_name: str) -> None:
        """Set up MQTT listeners for a specific W100 device."""
        try:
            if not device_name:
                _LOGGER.warning("Empty device name provided for MQTT setup")
                return
            
            # Initialize device subscription tracking
            if device_name not in self._mqtt_subscriptions:
                self._mqtt_subscriptions[device_name] = []
            
            # Set up action listener
            action_topic = MQTT_W100_ACTION_TOPIC.format(device_name)
            
            @callback
            def handle_w100_action(msg: ReceiveMessage) -> None:
                """Handle W100 action messages."""
                try:
                    action = msg.payload
                    _LOGGER.debug("Received W100 action: %s from device %s", action, device_name)
                    
                    # Validate action
                    if action not in [W100_ACTION_TOGGLE, W100_ACTION_PLUS, W100_ACTION_MINUS]:
                        _LOGGER.debug("Unknown W100 action received from %s: %s", device_name, action)
                        return
                    
                    # Schedule action handling
                    self.hass.async_create_task(
                        self.async_handle_w100_action(action, device_name)
                    )
                except Exception as err:
                    _LOGGER.error("Error handling W100 action message from %s: %s", device_name, err)
            
            # Subscribe to action topic
            await mqtt.async_subscribe(self.hass, action_topic, handle_w100_action, 0)
            self._mqtt_subscriptions[device_name].append(action_topic)
            _LOGGER.debug("Subscribed to W100 action topic: %s", action_topic)
            
            # Set up state listener
            state_topic = MQTT_W100_STATE_TOPIC.format(device_name)
            
            @callback
            def handle_w100_state(msg: ReceiveMessage) -> None:
                """Handle W100 state messages."""
                try:
                    if not msg.payload:
                        return
                        
                    payload = json.loads(msg.payload)
                    _LOGGER.debug("Received W100 state: %s from device %s", payload, device_name)
                    
                    # Update device state with validation
                    if device_name not in self._device_states:
                        self._device_states[device_name] = {}
                    
                    # Only update with valid state data
                    valid_keys = ["temperature", "humidity", "battery", "linkquality", "voltage"]
                    filtered_payload = {
                        key: value for key, value in payload.items() 
                        if key in valid_keys and value is not None
                    }
                    
                    if filtered_payload:
                        self._device_states[device_name].update({
                            **filtered_payload,
                            "last_seen": datetime.now(),
                        })
                        
                        # Trigger coordinator update
                        self.async_set_updated_data(self.data)
                    
                except json.JSONDecodeError as err:
                    _LOGGER.warning("Invalid JSON in W100 state message from %s: %s", device_name, err)
                except Exception as err:
                    _LOGGER.error("Error handling W100 state message from %s: %s", device_name, err)
            
            # Subscribe to state topic
            await mqtt.async_subscribe(self.hass, state_topic, handle_w100_state, 0)
            self._mqtt_subscriptions[device_name].append(state_topic)
            _LOGGER.debug("Subscribed to W100 state topic: %s", state_topic)
            
            _LOGGER.info("Successfully set up MQTT listeners for W100 device: %s", device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to set up MQTT listeners for W100 device %s: %s", device_name, err)

    async def _async_setup_mqtt_listeners(self) -> None:
        """Legacy method - redirects to new multi-device MQTT setup."""
        await self._async_setup_all_mqtt_listeners()

    async def _async_initialize_all_device_states(self) -> None:
        """Initialize device states for all configured devices."""
        try:
            # Initialize state for primary device from config entry
            device_name = self.config.get(CONF_W100_DEVICE_NAME)
            if device_name:
                await self._async_initialize_device_state(device_name, self.config)
            
            # Initialize states for additional devices from device configs
            for device_name, device_config in self._device_configs.items():
                if device_name not in self._device_states:
                    await self._async_initialize_device_state(device_name, device_config)
            
            _LOGGER.debug("Initialized states for %d devices", len(self._device_states))
            
        except Exception as err:
            _LOGGER.error("Failed to initialize all device states: %s", err)

    async def _async_initialize_device_state(self, device_name: str, device_config: dict[str, Any]) -> None:
        """Initialize device state for a specific device."""
        try:
            if not device_name:
                _LOGGER.warning("No device name provided for state initialization")
                return
            
            # Initialize device state if not exists
            if device_name not in self._device_states:
                self._device_states[device_name] = {
                    "device_name": device_name,
                    "current_mode": "off",
                    "target_temperature": device_config.get(CONF_IDLE_TEMPERATURE, DEFAULT_TARGET_TEMP),
                    "current_temperature": None,
                    "fan_speed": int(device_config.get(CONF_IDLE_FAN_SPEED, DEFAULT_IDLE_FAN_SPEED)),
                    "humidity": None,
                    "last_action": None,
                    "last_action_time": None,
                    "display_mode": "temperature",
                    "beep_enabled": device_config.get(CONF_BEEP_MODE, DEFAULT_BEEP_MODE) != "Disable Beep",
                    "last_seen": None,
                    "last_update": datetime.now(),
                    "config": device_config.copy(),
                    "status": "initialized",
                }
                
                _LOGGER.debug("Initialized device state for %s", device_name)
            else:
                # Update existing state with current config
                self._device_states[device_name]["config"] = device_config.copy()
                self._device_states[device_name]["last_update"] = datetime.now()
                _LOGGER.debug("Updated device state config for %s", device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to initialize device state for %s: %s", device_name, err)

    async def _async_initialize_device_states(self) -> None:
        """Legacy method - redirects to new multi-device initialization."""
        await self._async_initialize_all_device_states()

    async def _async_update_device_states(self) -> None:
        """Update device states from current climate entity states for all devices."""
        try:
            # Update primary device from config entry
            device_name = self.config.get(CONF_W100_DEVICE_NAME)
            if device_name and device_name in self._device_states:
                await self._async_update_single_device_state(device_name, self.config)
            
            # Update additional devices from device configs
            for device_name, device_config in self._device_configs.items():
                if device_name in self._device_states:
                    await self._async_update_single_device_state(device_name, device_config)
            
        except Exception as err:
            _LOGGER.error("Failed to update device states: %s", err)

    async def _async_update_single_device_state(self, device_name: str, device_config: dict[str, Any]) -> None:
        """Update device state for a single device."""
        try:
            if device_name not in self._device_states:
                _LOGGER.debug("Device %s not in states, initializing", device_name)
                await self._async_initialize_device_state(device_name, device_config)
                return
            
            device_state = self._device_states[device_name]
            
            # Get climate entity (existing or created)
            climate_entity_id = device_config.get(CONF_EXISTING_CLIMATE_ENTITY)
            
            # If no existing climate entity, check for created thermostats for this device
            if not climate_entity_id:
                device_thermostats = self._device_thermostats.get(device_name, [])
                if device_thermostats:
                    climate_entity_id = device_thermostats[0]  # Use first created thermostat for this device
            
            if climate_entity_id:
                climate_state = self.hass.states.get(climate_entity_id)
                if climate_state and climate_state.state != STATE_UNAVAILABLE:
                    # Update device state from climate entity
                    device_state.update({
                        "current_mode": climate_state.state,
                        "target_temperature": climate_state.attributes.get("temperature"),
                        "current_temperature": climate_state.attributes.get("current_temperature"),
                        "last_update": datetime.now(),
                        "status": "connected",
                        "climate_entity_id": climate_entity_id,
                    })
                else:
                    device_state.update({
                        "status": "climate_unavailable",
                        "last_update": datetime.now(),
                    })
            else:
                device_state.update({
                    "status": "no_climate_entity",
                    "last_update": datetime.now(),
                })
            
            # Update humidity from sensor if configured
            humidity_sensor = device_config.get(CONF_HUMIDITY_SENSOR)
            if humidity_sensor:
                humidity_state = self.hass.states.get(humidity_sensor)
                if humidity_state and humidity_state.state not in [STATE_UNAVAILABLE, "unknown"]:
                    try:
                        humidity_value = float(humidity_state.state)
                        device_state["humidity"] = humidity_value
                        device_state["humidity_sensor_status"] = "connected"
                    except (ValueError, TypeError):
                        device_state["humidity_sensor_status"] = "invalid_value"
                else:
                    device_state["humidity_sensor_status"] = "unavailable"
            
            # Update backup humidity sensor if configured
            backup_humidity_sensor = device_config.get(CONF_BACKUP_HUMIDITY_SENSOR)
            if backup_humidity_sensor and device_state.get("humidity") is None:
                backup_humidity_state = self.hass.states.get(backup_humidity_sensor)
                if backup_humidity_state and backup_humidity_state.state not in [STATE_UNAVAILABLE, "unknown"]:
                    try:
                        humidity_value = float(backup_humidity_state.state)
                        device_state["humidity"] = humidity_value
                        device_state["backup_humidity_sensor_status"] = "connected"
                    except (ValueError, TypeError):
                        device_state["backup_humidity_sensor_status"] = "invalid_value"
                else:
                    device_state["backup_humidity_sensor_status"] = "unavailable"
            
        except Exception as err:
            _LOGGER.error("Failed to update device state for %s: %s", device_name, err)

    async def async_handle_w100_action(self, action: str, device_name: str) -> None:
        """Handle W100 button actions with debouncing and error recovery."""
        try:
            # Enhanced debouncing with per-action tracking
            now = datetime.now()
            debounce_key = f"{device_name}_{action}"
            last_action_time = self._last_action_time.get(debounce_key)
            
            # Different debounce times for different actions
            debounce_time = 0.5  # Default debounce
            if action == W100_ACTION_TOGGLE:
                debounce_time = 1.0  # Longer debounce for toggle to prevent accidental double-toggles
            
            if last_action_time and (now - last_action_time).total_seconds() < debounce_time:
                _LOGGER.debug("Debouncing rapid W100 action %s from %s (%.2fs since last)", 
                             action, device_name, (now - last_action_time).total_seconds())
                return
            
            self._last_action_time[debounce_key] = now
            
            # Update device state
            if device_name not in self._device_states:
                await self._async_initialize_device_states()
            
            if device_name in self._device_states:
                self._device_states[device_name].update({
                    "last_action": action,
                    "last_action_time": now,
                })
            
            # Get climate entity to control - check device-specific config first
            device_config = self._device_configs.get(device_name, self.config)
            climate_entity_id = device_config.get(CONF_EXISTING_CLIMATE_ENTITY)
            
            # If no existing climate entity, check for created thermostats for this device
            if not climate_entity_id:
                device_thermostats = self._device_thermostats.get(device_name, [])
                if device_thermostats:
                    climate_entity_id = device_thermostats[0]  # Use first created thermostat for this device
                elif self._created_thermostats:
                    # Fallback to any created thermostat
                    climate_entity_id = self._created_thermostats[0]
            
            if not climate_entity_id:
                _LOGGER.warning("No climate entity configured for W100 device %s", device_name)
                return
            
            climate_state = self.hass.states.get(climate_entity_id)
            if not climate_state:
                _LOGGER.warning("Climate entity %s not found for W100 device %s", climate_entity_id, device_name)
                return
            
            if climate_state.state == STATE_UNAVAILABLE:
                _LOGGER.warning("Climate entity %s is unavailable, cannot process W100 action %s", 
                               climate_entity_id, action)
                return
            
            _LOGGER.info("Processing W100 action %s from device %s for climate entity %s", 
                        action, device_name, climate_entity_id)
            
            # Handle different actions
            if action == W100_ACTION_TOGGLE:
                await self._async_handle_toggle_action(climate_entity_id, climate_state, device_name)
            elif action == W100_ACTION_PLUS:
                await self._async_handle_plus_action(climate_entity_id, climate_state, device_name)
            elif action == W100_ACTION_MINUS:
                await self._async_handle_minus_action(climate_entity_id, climate_state, device_name)
            else:
                _LOGGER.warning("Unknown W100 action received: %s from device %s", action, device_name)
                return
            
            # Also route action to registered W100 climate entities for this device
            await self._async_route_action_to_w100_entities(action, device_name)
            
            # Schedule display sync after action with delay to allow state to settle
            self.hass.async_create_task(self._async_delayed_display_sync(device_name))
            
        except Exception as err:
            _LOGGER.error("Failed to handle W100 action %s from device %s: %s", action, device_name, err)
    
    async def _async_delayed_display_sync(self, device_name: str) -> None:
        """Sync W100 display after a delay to allow state changes to settle."""
        try:
            await asyncio.sleep(DISPLAY_UPDATE_DELAY_SECONDS)
            await self.async_sync_w100_display(device_name)
        except Exception as err:
            _LOGGER.error("Failed to sync W100 display for %s: %s", device_name, err)

    async def _async_handle_toggle_action(self, climate_entity_id: str, climate_state, device_name: str) -> None:
        """Handle W100 toggle action (double press) - toggles between heat and off modes."""
        try:
            current_mode = climate_state.state
            target_mode = "heat" if current_mode == "off" else "off"
            
            _LOGGER.info("W100 %s toggle: %s -> %s", device_name, current_mode, target_mode)
            
            # Check if target mode is supported
            supported_modes = climate_state.attributes.get("hvac_modes", [])
            if target_mode not in supported_modes:
                _LOGGER.warning("Climate entity %s does not support mode %s (supported: %s)", 
                               climate_entity_id, target_mode, supported_modes)
                return
            
            # Execute mode change
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": climate_entity_id, "hvac_mode": target_mode},
                blocking=True,
            )
            
            _LOGGER.info("Successfully toggled climate %s from %s to %s mode via W100 %s", 
                        climate_entity_id, current_mode, target_mode, device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to handle toggle action for %s: %s", climate_entity_id, err)

    async def _async_handle_plus_action(self, climate_entity_id: str, climate_state, device_name: str) -> None:
        """Handle W100 plus action - increases temperature in heat mode or fan speed in fan mode."""
        try:
            current_mode = climate_state.state
            
            if current_mode == "heat":
                # Increase temperature by 0.5°C (W100 compatible increment)
                current_temp = climate_state.attributes.get("temperature")
                if current_temp is None:
                    current_temp = DEFAULT_TARGET_TEMP
                    _LOGGER.warning("No current temperature found for %s, using default %s", 
                                   climate_entity_id, DEFAULT_TARGET_TEMP)
                
                max_temp = climate_state.attributes.get("max_temp", DEFAULT_MAX_TEMP)
                new_temp = min(float(current_temp) + 0.5, float(max_temp))
                
                if new_temp == current_temp:
                    _LOGGER.info("W100 %s plus: temperature already at maximum (%s°C)", 
                                device_name, current_temp)
                    return
                
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": climate_entity_id, "temperature": new_temp},
                    blocking=True,
                )
                _LOGGER.info("W100 %s plus: increased temperature from %s°C to %s°C for %s", 
                            device_name, current_temp, new_temp, climate_entity_id)
                
            elif current_mode == "fan":
                # Increase fan speed (if supported)
                current_fan_speed = climate_state.attributes.get("fan_mode", "1")
                fan_modes = climate_state.attributes.get("fan_modes", [])
                
                if not fan_modes:
                    _LOGGER.debug("Climate entity %s does not support fan modes", climate_entity_id)
                    return
                
                try:
                    # Try numeric fan speed adjustment
                    fan_speed_num = int(current_fan_speed)
                    new_fan_speed = min(fan_speed_num + 1, 9)
                    new_fan_speed_str = str(new_fan_speed)
                    
                    if new_fan_speed_str in fan_modes:
                        await self.hass.services.async_call(
                            "climate",
                            "set_fan_mode",
                            {"entity_id": climate_entity_id, "fan_mode": new_fan_speed_str},
                            blocking=True,
                        )
                        _LOGGER.info("W100 %s plus: increased fan speed from %s to %s for %s", 
                                    device_name, current_fan_speed, new_fan_speed_str, climate_entity_id)
                    else:
                        _LOGGER.debug("Fan speed %s not supported by %s (available: %s)", 
                                     new_fan_speed_str, climate_entity_id, fan_modes)
                        
                except (ValueError, TypeError):
                    # Try to find next fan mode in list
                    try:
                        current_index = fan_modes.index(current_fan_speed)
                        if current_index < len(fan_modes) - 1:
                            new_fan_mode = fan_modes[current_index + 1]
                            await self.hass.services.async_call(
                                "climate",
                                "set_fan_mode",
                                {"entity_id": climate_entity_id, "fan_mode": new_fan_mode},
                                blocking=True,
                            )
                            _LOGGER.info("W100 %s plus: increased fan mode from %s to %s for %s", 
                                        device_name, current_fan_speed, new_fan_mode, climate_entity_id)
                    except (ValueError, IndexError):
                        _LOGGER.debug("Cannot increase fan speed for %s (current: %s, available: %s)", 
                                     climate_entity_id, current_fan_speed, fan_modes)
            else:
                _LOGGER.debug("W100 %s plus action not applicable in mode %s", device_name, current_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to handle plus action for %s: %s", climate_entity_id, err)

    async def _async_handle_minus_action(self, climate_entity_id: str, climate_state, device_name: str) -> None:
        """Handle W100 minus action - decreases temperature in heat mode or fan speed in fan mode."""
        try:
            current_mode = climate_state.state
            
            if current_mode == "heat":
                # Decrease temperature by 0.5°C (W100 compatible increment)
                current_temp = climate_state.attributes.get("temperature")
                if current_temp is None:
                    current_temp = DEFAULT_TARGET_TEMP
                    _LOGGER.warning("No current temperature found for %s, using default %s", 
                                   climate_entity_id, DEFAULT_TARGET_TEMP)
                
                min_temp = climate_state.attributes.get("min_temp", DEFAULT_MIN_TEMP)
                new_temp = max(float(current_temp) - 0.5, float(min_temp))
                
                if new_temp == current_temp:
                    _LOGGER.info("W100 %s minus: temperature already at minimum (%s°C)", 
                                device_name, current_temp)
                    return
                
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": climate_entity_id, "temperature": new_temp},
                    blocking=True,
                )
                _LOGGER.info("W100 %s minus: decreased temperature from %s°C to %s°C for %s", 
                            device_name, current_temp, new_temp, climate_entity_id)
                
            elif current_mode == "fan":
                # Decrease fan speed (if supported)
                current_fan_speed = climate_state.attributes.get("fan_mode", "1")
                fan_modes = climate_state.attributes.get("fan_modes", [])
                
                if not fan_modes:
                    _LOGGER.debug("Climate entity %s does not support fan modes", climate_entity_id)
                    return
                
                try:
                    # Try numeric fan speed adjustment
                    fan_speed_num = int(current_fan_speed)
                    new_fan_speed = max(fan_speed_num - 1, 1)
                    new_fan_speed_str = str(new_fan_speed)
                    
                    if new_fan_speed_str in fan_modes:
                        await self.hass.services.async_call(
                            "climate",
                            "set_fan_mode",
                            {"entity_id": climate_entity_id, "fan_mode": new_fan_speed_str},
                            blocking=True,
                        )
                        _LOGGER.info("W100 %s minus: decreased fan speed from %s to %s for %s", 
                                    device_name, current_fan_speed, new_fan_speed_str, climate_entity_id)
                    else:
                        _LOGGER.debug("Fan speed %s not supported by %s (available: %s)", 
                                     new_fan_speed_str, climate_entity_id, fan_modes)
                        
                except (ValueError, TypeError):
                    # Try to find previous fan mode in list
                    try:
                        current_index = fan_modes.index(current_fan_speed)
                        if current_index > 0:
                            new_fan_mode = fan_modes[current_index - 1]
                            await self.hass.services.async_call(
                                "climate",
                                "set_fan_mode",
                                {"entity_id": climate_entity_id, "fan_mode": new_fan_mode},
                                blocking=True,
                            )
                            _LOGGER.info("W100 %s minus: decreased fan mode from %s to %s for %s", 
                                        device_name, current_fan_speed, new_fan_mode, climate_entity_id)
                    except (ValueError, IndexError):
                        _LOGGER.debug("Cannot decrease fan speed for %s (current: %s, available: %s)", 
                                     climate_entity_id, current_fan_speed, fan_modes)
            else:
                _LOGGER.debug("W100 %s minus action not applicable in mode %s", device_name, current_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to handle minus action for %s: %s", climate_entity_id, err)

    async def _async_sync_all_displays(self) -> None:
        """Sync all W100 displays with current states."""
        try:
            for device_name in self._device_states:
                await self.async_sync_w100_display(device_name)
        except Exception as err:
            _LOGGER.error("Failed to sync all displays: %s", err)

    async def async_sync_w100_display(self, device_name: str) -> None:
        """Enhanced W100 display synchronization system.
        
        Implements comprehensive display synchronization with:
        - Temperature display in heat mode
        - Fan speed display in off/fan modes  
        - Humidity synchronization with sensor values
        - Display mode switching based on climate entity state
        - Error handling and fallback mechanisms
        
        Requirements: 5.4, 5.5, 8.3
        """
        try:
            if device_name not in self._device_states:
                _LOGGER.debug("Device %s not in device states, initializing", device_name)
                await self._async_initialize_device_states()
                if device_name not in self._device_states:
                    _LOGGER.warning("Failed to initialize device state for %s", device_name)
                    return
            
            device_state = self._device_states[device_name]
            
            # Get climate entity state - use device-specific config
            device_config = self._device_configs.get(device_name, self.config)
            climate_entity_id = device_config.get(CONF_EXISTING_CLIMATE_ENTITY)
            
            # If no existing climate entity, check for created thermostats for this device
            if not climate_entity_id:
                device_thermostats = self._device_thermostats.get(device_name, [])
                if device_thermostats:
                    climate_entity_id = device_thermostats[0]  # Use first created thermostat for this device
                elif self._created_thermostats:
                    # Fallback to any created thermostat
                    climate_entity_id = self._created_thermostats[0]
            
            if not climate_entity_id:
                _LOGGER.debug("No climate entity configured for device %s, skipping display sync", device_name)
                return
            
            climate_state = self.hass.states.get(climate_entity_id)
            if not climate_state or climate_state.state == STATE_UNAVAILABLE:
                _LOGGER.debug("Climate entity %s unavailable for device %s, using fallback display", 
                             climate_entity_id, device_name)
                await self._async_sync_fallback_display(device_name, device_state)
                return
            
            # Check if MQTT is available
            if not self.hass.services.has_service("mqtt", "publish"):
                _LOGGER.debug("MQTT not available, skipping display sync for %s", device_name)
                return
            
            # Prepare comprehensive display update payload
            display_payload = {}
            current_mode = climate_state.state
            
            # Handle display mode switching based on climate entity state
            if current_mode == "heat":
                await self._async_sync_heat_mode_display(
                    device_name, device_state, climate_state, display_payload
                )
            elif current_mode == "off":
                await self._async_sync_off_mode_display(
                    device_name, device_state, climate_state, display_payload
                )
            elif current_mode == "fan":
                await self._async_sync_fan_mode_display(
                    device_name, device_state, climate_state, display_payload
                )
            elif current_mode == "cool":
                await self._async_sync_cool_mode_display(
                    device_name, device_state, climate_state, display_payload
                )
            else:
                _LOGGER.debug("Unknown climate mode %s for %s, using default display", 
                             current_mode, device_name)
                await self._async_sync_default_display(
                    device_name, device_state, climate_state, display_payload
                )
            
            # Add humidity synchronization with sensor values
            await self._async_sync_humidity_display(device_name, device_state, display_payload)
            
            # Add additional W100 specific display parameters
            await self._async_sync_advanced_display_features(
                device_name, device_state, climate_state, display_payload
            )
            
            # Send display update via MQTT with retry logic
            await self._async_send_display_update(device_name, display_payload)
            
            # Update device state tracking
            device_state.update({
                "last_display_sync": datetime.now(),
                "last_sync_mode": current_mode,
                "last_sync_payload": display_payload.copy(),
            })
            
            _LOGGER.debug("Successfully synced W100 display for %s in mode %s", 
                         device_name, current_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to sync W100 display for %s: %s", device_name, err)
            # Attempt fallback display sync
            try:
                await self._async_sync_fallback_display(device_name, self._device_states.get(device_name, {}))
            except Exception as fallback_err:
                _LOGGER.error("Fallback display sync also failed for %s: %s", device_name, fallback_err)

    async def _async_sync_heat_mode_display(self, device_name: str, device_state: dict, 
                                          climate_state, display_payload: dict) -> None:
        """Sync display for heat mode - shows temperature."""
        try:
            # Get device-specific configuration
            device_config = self._device_configs.get(device_name, self.config)
            
            # Get target temperature from climate entity
            target_temp = climate_state.attributes.get("temperature")
            if target_temp is None:
                # Fallback to configured heating temperature
                target_temp = device_config.get(CONF_HEATING_TEMPERATURE, DEFAULT_HEATING_TEMPERATURE)
                _LOGGER.debug("No target temperature from climate entity, using configured heating temp %s°C", 
                             target_temp)
            
            # Ensure temperature is within valid range
            min_temp = climate_state.attributes.get("min_temp", DEFAULT_MIN_TEMP)
            max_temp = climate_state.attributes.get("max_temp", DEFAULT_MAX_TEMP)
            target_temp = max(min_temp, min(max_temp, float(target_temp)))
            
            # Set temperature display
            display_payload["temperature"] = target_temp
            device_state["display_mode"] = "temperature"
            device_state["target_temperature"] = target_temp
            
            # Add current temperature for reference
            current_temp = climate_state.attributes.get("current_temperature")
            if current_temp is not None:
                display_payload["current_temperature"] = float(current_temp)
                device_state["current_temperature"] = float(current_temp)
            
            # Set heating warm level
            warm_level = device_config.get(CONF_HEATING_WARM_LEVEL, DEFAULT_HEATING_WARM_LEVEL)
            display_payload["warm_level"] = int(warm_level)
            
            _LOGGER.debug("W100 %s heat mode display: temp=%s°C, warm_level=%s", 
                         device_name, target_temp, warm_level)
            
        except Exception as err:
            _LOGGER.error("Failed to sync heat mode display for %s: %s", device_name, err)
            # Fallback to basic temperature display
            display_payload["temperature"] = DEFAULT_HEATING_TEMPERATURE
            device_state["display_mode"] = "temperature"

    async def _async_sync_off_mode_display(self, device_name: str, device_state: dict, 
                                         climate_state, display_payload: dict) -> None:
        """Sync display for off mode - shows fan speed."""
        try:
            # Get device-specific configuration
            device_config = self._device_configs.get(device_name, self.config)
            
            # Get configured idle fan speed
            idle_fan_speed = device_config.get(CONF_IDLE_FAN_SPEED, DEFAULT_IDLE_FAN_SPEED)
            fan_speed = int(idle_fan_speed)
            
            # Set fan speed display
            display_payload["fan_speed"] = fan_speed
            device_state["display_mode"] = "fan_speed"
            device_state["fan_speed"] = fan_speed
            
            # Set idle temperature for reference
            idle_temp = device_config.get(CONF_IDLE_TEMPERATURE, DEFAULT_IDLE_TEMPERATURE)
            display_payload["idle_temperature"] = float(idle_temp)
            
            # Set idle warm level
            idle_warm_level = device_config.get(CONF_IDLE_WARM_LEVEL, DEFAULT_IDLE_WARM_LEVEL)
            display_payload["warm_level"] = int(idle_warm_level)
            
            # Add swing mode
            swing_mode = device_config.get(CONF_SWING_MODE, DEFAULT_SWING_MODE)
            display_payload["swing_mode"] = swing_mode
            
            _LOGGER.debug("W100 %s off mode display: fan_speed=%s, idle_temp=%s°C, swing=%s", 
                         device_name, fan_speed, idle_temp, swing_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to sync off mode display for %s: %s", device_name, err)
            # Fallback to basic fan speed display
            display_payload["fan_speed"] = int(DEFAULT_IDLE_FAN_SPEED)
            device_state["display_mode"] = "fan_speed"

    async def _async_sync_fan_mode_display(self, device_name: str, device_state: dict, 
                                         climate_state, display_payload: dict) -> None:
        """Sync display for fan mode - shows current fan speed."""
        try:
            # Get current fan speed from climate entity
            current_fan_speed = climate_state.attributes.get("fan_mode", "1")
            
            try:
                fan_speed_num = int(current_fan_speed)
            except (ValueError, TypeError):
                # Try to map named fan speeds to numbers
                fan_speed_mapping = {
                    "low": 1, "medium": 3, "high": 6, "auto": 3,
                    "quiet": 1, "normal": 3, "turbo": 9
                }
                fan_speed_num = fan_speed_mapping.get(current_fan_speed.lower(), 3)
                _LOGGER.debug("Mapped fan speed '%s' to %s for %s", 
                             current_fan_speed, fan_speed_num, device_name)
            
            # Ensure fan speed is in valid range (1-9)
            fan_speed_num = max(1, min(9, fan_speed_num))
            
            # Set fan speed display
            display_payload["fan_speed"] = fan_speed_num
            device_state["display_mode"] = "fan_speed"
            device_state["fan_speed"] = fan_speed_num
            
            # Add swing mode if supported
            swing_mode = climate_state.attributes.get("swing_mode")
            if swing_mode:
                display_payload["swing_mode"] = swing_mode
            else:
                # Use configured swing mode
                swing_mode = self.config.get(CONF_SWING_MODE, DEFAULT_SWING_MODE)
                display_payload["swing_mode"] = swing_mode
            
            _LOGGER.debug("W100 %s fan mode display: fan_speed=%s, swing=%s", 
                         device_name, fan_speed_num, swing_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to sync fan mode display for %s: %s", device_name, err)
            # Fallback to default fan speed
            display_payload["fan_speed"] = 3
            device_state["display_mode"] = "fan_speed"

    async def _async_sync_cool_mode_display(self, device_name: str, device_state: dict, 
                                          climate_state, display_payload: dict) -> None:
        """Sync display for cool mode - shows temperature and fan speed."""
        try:
            # Get target temperature
            target_temp = climate_state.attributes.get("temperature", DEFAULT_TARGET_TEMP)
            target_temp = float(target_temp)
            
            # Set temperature display
            display_payload["temperature"] = target_temp
            device_state["target_temperature"] = target_temp
            
            # Get fan speed for cooling
            current_fan_speed = climate_state.attributes.get("fan_mode", "3")
            try:
                fan_speed_num = int(current_fan_speed)
            except (ValueError, TypeError):
                fan_speed_num = 3
            
            fan_speed_num = max(1, min(9, fan_speed_num))
            display_payload["fan_speed"] = fan_speed_num
            device_state["fan_speed"] = fan_speed_num
            
            # Set display mode to show both temperature and fan
            device_state["display_mode"] = "temperature_fan"
            
            _LOGGER.debug("W100 %s cool mode display: temp=%s°C, fan_speed=%s", 
                         device_name, target_temp, fan_speed_num)
            
        except Exception as err:
            _LOGGER.error("Failed to sync cool mode display for %s: %s", device_name, err)
            # Fallback to temperature display
            display_payload["temperature"] = DEFAULT_TARGET_TEMP
            device_state["display_mode"] = "temperature"

    async def _async_sync_default_display(self, device_name: str, device_state: dict, 
                                        climate_state, display_payload: dict) -> None:
        """Sync display for unknown/default modes."""
        try:
            # Default to showing temperature if available
            target_temp = climate_state.attributes.get("temperature")
            if target_temp is not None:
                display_payload["temperature"] = float(target_temp)
                device_state["display_mode"] = "temperature"
                device_state["target_temperature"] = float(target_temp)
            else:
                # Fallback to fan speed
                fan_speed = int(self.config.get(CONF_IDLE_FAN_SPEED, DEFAULT_IDLE_FAN_SPEED))
                display_payload["fan_speed"] = fan_speed
                device_state["display_mode"] = "fan_speed"
                device_state["fan_speed"] = fan_speed
            
            _LOGGER.debug("W100 %s default display mode: %s", 
                         device_name, device_state["display_mode"])
            
        except Exception as err:
            _LOGGER.error("Failed to sync default display for %s: %s", device_name, err)

    async def _async_sync_humidity_display(self, device_name: str, device_state: dict, 
                                         display_payload: dict) -> None:
        """Sync humidity display with sensor values."""
        try:
            # Get device-specific configuration
            device_config = self._device_configs.get(device_name, self.config)
            humidity_value = None
            
            # Try primary humidity sensor
            humidity_sensor = device_config.get(CONF_HUMIDITY_SENSOR)
            if humidity_sensor:
                humidity_state = self.hass.states.get(humidity_sensor)
                if humidity_state and humidity_state.state not in [STATE_UNAVAILABLE, "unknown"]:
                    try:
                        humidity_value = float(humidity_state.state)
                        _LOGGER.debug("Got humidity %s%% from primary sensor %s for %s", 
                                     humidity_value, humidity_sensor, device_name)
                    except (ValueError, TypeError):
                        _LOGGER.debug("Invalid humidity value from primary sensor %s: %s", 
                                     humidity_sensor, humidity_state.state)
            
            # Try backup humidity sensor if primary failed
            if humidity_value is None:
                backup_humidity_sensor = device_config.get(CONF_BACKUP_HUMIDITY_SENSOR)
                if backup_humidity_sensor:
                    backup_state = self.hass.states.get(backup_humidity_sensor)
                    if backup_state and backup_state.state not in [STATE_UNAVAILABLE, "unknown"]:
                        try:
                            humidity_value = float(backup_state.state)
                            _LOGGER.debug("Got humidity %s%% from backup sensor %s for %s", 
                                         humidity_value, backup_humidity_sensor, device_name)
                        except (ValueError, TypeError):
                            _LOGGER.debug("Invalid humidity value from backup sensor %s: %s", 
                                         backup_humidity_sensor, backup_state.state)
            
            # Use existing device state humidity if no sensors available
            if humidity_value is None:
                humidity_value = device_state.get("humidity")
                if humidity_value is not None:
                    _LOGGER.debug("Using cached humidity %s%% for %s", humidity_value, device_name)
            
            # Set humidity in display payload if available
            if humidity_value is not None:
                # Ensure humidity is in valid range (0-100%)
                humidity_value = max(0, min(100, humidity_value))
                display_payload["humidity"] = humidity_value
                device_state["humidity"] = humidity_value
                _LOGGER.debug("W100 %s humidity display: %s%%", device_name, humidity_value)
            else:
                _LOGGER.debug("No humidity data available for %s", device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to sync humidity display for %s: %s", device_name, err)

    async def _async_sync_advanced_display_features(self, device_name: str, device_state: dict, 
                                                  climate_state, display_payload: dict) -> None:
        """Sync advanced W100 display features and parameters."""
        try:
            # Get device-specific configuration
            device_config = self._device_configs.get(device_name, self.config)
            
            # Add beep mode configuration
            beep_mode = device_config.get(CONF_BEEP_MODE, DEFAULT_BEEP_MODE)
            if beep_mode == "Enable Beep":
                display_payload["beep"] = True
            elif beep_mode == "Disable Beep":
                display_payload["beep"] = False
            elif beep_mode == "On-Mode Change":
                # Enable beep only for mode changes
                display_payload["beep_on_change"] = True
            
            device_state["beep_enabled"] = beep_mode != "Disable Beep"
            
            # Add display brightness/intensity if supported
            # This could be extended based on W100 capabilities
            display_payload["display_brightness"] = 100  # Full brightness
            
            # Add last action information for display context
            last_action = device_state.get("last_action")
            if last_action:
                display_payload["last_action"] = last_action
                
                # Add action timestamp for display timeout
                last_action_time = device_state.get("last_action_time")
                if last_action_time:
                    time_since_action = (datetime.now() - last_action_time).total_seconds()
                    display_payload["action_age"] = int(time_since_action)
            
            # Add device status indicators
            display_payload["status"] = "online"
            display_payload["last_update"] = datetime.now().isoformat()
            
            _LOGGER.debug("W100 %s advanced display features: beep=%s, brightness=100", 
                         device_name, beep_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to sync advanced display features for %s: %s", device_name, err)

    async def _async_sync_fallback_display(self, device_name: str, device_state: dict) -> None:
        """Sync fallback display when climate entity is unavailable."""
        try:
            fallback_payload = {}
            
            # Use last known good values or defaults
            if device_state.get("display_mode") == "temperature":
                temp = device_state.get("target_temperature", DEFAULT_HEATING_TEMPERATURE)
                fallback_payload["temperature"] = float(temp)
            else:
                fan_speed = device_state.get("fan_speed", int(DEFAULT_IDLE_FAN_SPEED))
                fallback_payload["fan_speed"] = int(fan_speed)
            
            # Add humidity if available
            humidity = device_state.get("humidity")
            if humidity is not None:
                fallback_payload["humidity"] = float(humidity)
            
            # Add status indicator
            fallback_payload["status"] = "offline"
            fallback_payload["beep"] = False  # Disable beep in fallback mode
            
            await self._async_send_display_update(device_name, fallback_payload)
            
            _LOGGER.debug("Sent fallback display update for %s: %s", device_name, fallback_payload)
            
        except Exception as err:
            _LOGGER.error("Failed to send fallback display for %s: %s", device_name, err)

    async def _async_send_display_update(self, device_name: str, display_payload: dict) -> None:
        """Send display update via MQTT with retry logic."""
        if not display_payload:
            _LOGGER.debug("No display data to send for %s", device_name)
            return
        
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                set_topic = MQTT_W100_SET_TOPIC.format(device_name)
                payload_json = json.dumps(display_payload, default=str)
                
                await mqtt.async_publish(
                    self.hass,
                    set_topic,
                    payload_json,
                    qos=0,
                    retain=False
                )
                
                _LOGGER.debug("Sent W100 display update for %s via %s (attempt %d): %s", 
                             device_name, set_topic, attempt + 1, display_payload)
                return  # Success, exit retry loop
                
            except Exception as err:
                _LOGGER.warning("Failed to send display update for %s (attempt %d/%d): %s", 
                               device_name, attempt + 1, max_retries, err)
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    _LOGGER.error("Failed to send display update for %s after %d attempts", 
                                 device_name, max_retries)
                    raise

    # Keep the old method name for backward compatibility
    async def _async_sync_w100_display(self, device_name: str) -> None:
        """Legacy method - redirects to new enhanced sync method."""
        await self.async_sync_w100_display(device_name)

    async def async_cleanup(self) -> None:
        """Clean up coordinator resources for all devices."""
        try:
            # Unsubscribe from MQTT topics for all devices
            await self._async_cleanup_all_mqtt_subscriptions()
            
            # Clean up created thermostats if requested
            for entity_id in self._created_thermostats.copy():
                try:
                    await self.async_remove_generic_thermostat(entity_id)
                except Exception as err:
                    _LOGGER.warning("Failed to cleanup thermostat %s: %s", entity_id, err)
            
            # Clear all device tracking
            self._device_states.clear()
            self._device_configs.clear()
            self._device_thermostats.clear()
            self._last_action_time.clear()
            
            _LOGGER.info("Coordinator cleanup completed for all devices")
            
        except Exception as err:
            _LOGGER.error("Failed to cleanup coordinator: %s", err)

    @property
    def created_thermostats(self) -> list[str]:
        """Return list of created thermostat entity IDs."""
        return self._created_thermostats.copy()

    @property
    def device_states(self) -> dict[str, dict[str, Any]]:
        """Return current device states."""
        return self._device_states.copy()

    def get_device_state(self, device_name: str) -> dict[str, Any] | None:
        """Get state for a specific device."""
        return self._device_states.get(device_name)

    def get_thermostat_config(self, entity_id: str) -> dict[str, Any] | None:
        """Get configuration for a specific thermostat."""
        return self._thermostat_configs.get(entity_id)

    async def async_add_device(self, device_name: str, device_config: dict[str, Any]) -> None:
        """Add a new W100 device to the coordinator."""
        try:
            if not device_name:
                raise ValueError("Device name cannot be empty")
            
            if device_name in self._device_configs:
                _LOGGER.warning("Device %s already exists, updating configuration", device_name)
            
            # Store device configuration
            self._device_configs[device_name] = device_config.copy()
            
            # Initialize device thermostat tracking
            if device_name not in self._device_thermostats:
                self._device_thermostats[device_name] = []
            
            # Initialize device state
            await self._async_initialize_device_state(device_name, device_config)
            
            # Set up MQTT listeners for the new device
            await self._async_setup_device_mqtt_listeners(device_name)
            
            # Save device data to storage
            await self._async_save_device_data()
            
            _LOGGER.info("Successfully added W100 device: %s", device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to add W100 device %s: %s", device_name, err)
            raise

    async def async_remove_device(self, device_name: str) -> None:
        """Remove a W100 device from the coordinator without affecting other devices."""
        try:
            if not device_name:
                raise ValueError("Device name cannot be empty")
            
            if device_name not in self._device_configs:
                _LOGGER.warning("Device %s not found in configurations", device_name)
                return
            
            # Remove all thermostats associated with this device
            device_thermostats = self._device_thermostats.get(device_name, [])
            for thermostat_id in device_thermostats.copy():
                try:
                    await self.async_remove_generic_thermostat(thermostat_id)
                    _LOGGER.info("Removed thermostat %s for device %s", thermostat_id, device_name)
                except Exception as err:
                    _LOGGER.error("Failed to remove thermostat %s for device %s: %s", thermostat_id, device_name, err)
            
            # Clean up MQTT subscriptions for this device
            await self._async_cleanup_device_mqtt_subscriptions(device_name)
            
            # Remove device from tracking
            if device_name in self._device_configs:
                del self._device_configs[device_name]
            
            if device_name in self._device_thermostats:
                del self._device_thermostats[device_name]
            
            if device_name in self._device_states:
                del self._device_states[device_name]
            
            # Clean up device-specific action times
            keys_to_remove = [key for key in self._last_action_time.keys() if key.startswith(f"{device_name}_")]
            for key in keys_to_remove:
                del self._last_action_time[key]
            
            # Save updated device data to storage
            await self._async_save_device_data()
            
            _LOGGER.info("Successfully removed W100 device: %s", device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to remove W100 device %s: %s", device_name, err)
            raise

    async def async_update_device_config(self, device_name: str, device_config: dict[str, Any]) -> None:
        """Update configuration for a specific W100 device."""
        try:
            if not device_name:
                raise ValueError("Device name cannot be empty")
            
            if device_name not in self._device_configs:
                _LOGGER.warning("Device %s not found, adding as new device", device_name)
                await self.async_add_device(device_name, device_config)
                return
            
            old_config = self._device_configs[device_name].copy()
            
            # Update device configuration
            self._device_configs[device_name] = device_config.copy()
            
            # Update device state with new config
            await self._async_initialize_device_state(device_name, device_config)
            
            # Check if MQTT setup needs to be refreshed
            if old_config.get(CONF_W100_DEVICE_NAME) != device_config.get(CONF_W100_DEVICE_NAME):
                # Device name changed, need to update MQTT subscriptions
                await self._async_cleanup_device_mqtt_subscriptions(device_name)
                await self._async_setup_device_mqtt_listeners(device_name)
            
            # Save updated device data to storage
            await self._async_save_device_data()
            
            _LOGGER.info("Successfully updated configuration for W100 device: %s", device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to update configuration for W100 device %s: %s", device_name, err)
            raise

    def get_device_config(self, device_name: str) -> dict[str, Any] | None:
        """Get configuration for a specific device."""
        return self._device_configs.get(device_name)

    def get_device_thermostats(self, device_name: str) -> list[str]:
        """Get list of thermostat entity IDs for a specific device."""
        return self._device_thermostats.get(device_name, []).copy()

    def list_devices(self) -> list[str]:
        """Get list of all configured device names."""
        devices = list(self._device_configs.keys())
        
        # Add primary device from config if not already in list
        primary_device = self.config.get(CONF_W100_DEVICE_NAME)
        if primary_device and primary_device not in devices:
            devices.append(primary_device)
        
        return sorted(devices)

    async def async_remove_all_thermostats(self) -> None:
        """Remove all thermostats created by this integration."""
        try:
            thermostats_to_remove = self._created_thermostats.copy()
            
            for entity_id in thermostats_to_remove:
                try:
                    await self.async_remove_generic_thermostat(entity_id)
                    _LOGGER.info("Removed thermostat %s during cleanup", entity_id)
                except Exception as err:
                    _LOGGER.error("Failed to remove thermostat %s during cleanup: %s", entity_id, err)
            
            # Clear all tracking data
            self._created_thermostats.clear()
            self._thermostat_configs.clear()
            
            # Save empty data to storage
            await self._async_save_thermostat_data()
            
            _LOGGER.info("Removed all thermostats for integration")
            
        except Exception as err:
            _LOGGER.error("Failed to remove all thermostats: %s", err)

    async def async_on_entry_update(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle config entry updates."""
        try:
            # Update stored config
            old_config = self.config
            self.config = entry.data
            
            # Check if W100 device name changed
            old_device_name = old_config.get(CONF_W100_DEVICE_NAME)
            new_device_name = self.config.get(CONF_W100_DEVICE_NAME)
            
            if old_device_name != new_device_name:
                _LOGGER.info("Primary W100 device name changed from %s to %s", old_device_name, new_device_name)
                
                # Clean up old MQTT subscriptions for the old device
                if old_device_name:
                    await self._async_cleanup_device_mqtt_subscriptions(old_device_name)
                
                # Set up new MQTT subscriptions for the new device
                if new_device_name:
                    await self._async_setup_device_mqtt_listeners(new_device_name)
                
                # Update device states and configs
                if old_device_name and old_device_name in self._device_states:
                    # Move device state to new name
                    if new_device_name:
                        self._device_states[new_device_name] = self._device_states.pop(old_device_name)
                        
                        # Update device configs as well
                        if old_device_name in self._device_configs:
                            self._device_configs[new_device_name] = self._device_configs.pop(old_device_name)
                            self._device_configs[new_device_name][CONF_W100_DEVICE_NAME] = new_device_name
                        
                        # Update device thermostat tracking
                        if old_device_name in self._device_thermostats:
                            self._device_thermostats[new_device_name] = self._device_thermostats.pop(old_device_name)
                
                # Initialize new device state if needed
                await self._async_initialize_all_device_states()
                
                # Save updated device data
                await self._async_save_device_data()
            
            # Check if other configuration changed that affects thermostats
            await self._async_handle_config_changes(old_config, self.config)
            
            # Trigger data refresh
            await self.async_refresh()
            
            _LOGGER.debug("Handled config entry update")
            
        except Exception as err:
            _LOGGER.error("Failed to handle config entry update: %s", err)

    async def _async_cleanup_all_mqtt_subscriptions(self) -> None:
        """Clean up all existing MQTT subscriptions for all devices."""
        try:
            for device_name, topics in self._mqtt_subscriptions.items():
                for topic in topics:
                    try:
                        await mqtt.async_unsubscribe(self.hass, topic)
                        _LOGGER.debug("Unsubscribed from MQTT topic: %s for device %s", topic, device_name)
                    except Exception as err:
                        _LOGGER.warning("Failed to unsubscribe from %s for device %s: %s", topic, device_name, err)
            
            self._mqtt_subscriptions.clear()
            
        except Exception as err:
            _LOGGER.error("Failed to cleanup all MQTT subscriptions: %s", err)

    async def _async_cleanup_device_mqtt_subscriptions(self, device_name: str) -> None:
        """Clean up MQTT subscriptions for a specific device."""
        try:
            if device_name in self._mqtt_subscriptions:
                topics = self._mqtt_subscriptions[device_name]
                for topic in topics:
                    try:
                        await mqtt.async_unsubscribe(self.hass, topic)
                        _LOGGER.debug("Unsubscribed from MQTT topic: %s for device %s", topic, device_name)
                    except Exception as err:
                        _LOGGER.warning("Failed to unsubscribe from %s for device %s: %s", topic, device_name, err)
                
                del self._mqtt_subscriptions[device_name]
                _LOGGER.debug("Cleaned up MQTT subscriptions for device %s", device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to cleanup MQTT subscriptions for device %s: %s", device_name, err)

    async def _async_cleanup_mqtt_subscriptions(self) -> None:
        """Legacy method - redirects to new multi-device cleanup."""
        await self._async_cleanup_all_mqtt_subscriptions()

    async def _async_handle_config_changes(self, old_config: dict[str, Any], new_config: dict[str, Any]) -> None:
        """Handle configuration changes that affect existing thermostats."""
        try:
            # Check if generic thermostat configuration changed
            old_generic_config = old_config.get(CONF_GENERIC_THERMOSTAT_CONFIG, {})
            new_generic_config = new_config.get(CONF_GENERIC_THERMOSTAT_CONFIG, {})
            
            if old_generic_config != new_generic_config and self._created_thermostats:
                _LOGGER.info("Generic thermostat configuration changed, updating thermostats")
                
                # Update all created thermostats with new configuration
                for entity_id in self._created_thermostats:
                    try:
                        await self.async_update_generic_thermostat(entity_id, new_generic_config)
                    except Exception as err:
                        _LOGGER.error("Failed to update thermostat %s with new config: %s", entity_id, err)
            
            # Check if other settings changed that affect display sync
            display_affecting_keys = [
                CONF_HEATING_TEMPERATURE,
                CONF_IDLE_TEMPERATURE,
                CONF_IDLE_FAN_SPEED,
                CONF_BEEP_MODE,
            ]
            
            config_changed = any(
                old_config.get(key) != new_config.get(key)
                for key in display_affecting_keys
            )
            
            if config_changed:
                _LOGGER.debug("Display-affecting configuration changed, updating device states")
                
                # Update primary device config in device configs
                primary_device = new_config.get(CONF_W100_DEVICE_NAME)
                if primary_device:
                    if primary_device not in self._device_configs:
                        self._device_configs[primary_device] = {}
                    
                    # Update device config with new values
                    for key in display_affecting_keys:
                        if key in new_config:
                            self._device_configs[primary_device][key] = new_config[key]
                
                await self._async_initialize_all_device_states()
                await self._async_sync_all_displays()
                
                # Save updated device data
                await self._async_save_device_data()
            
        except Exception as err:
            _LOGGER.error("Failed to handle config changes: %s", err)

    async def async_register_w100_climate_entity(self, device_name: str, entity_id: str) -> None:
        """Register a W100 climate entity for button press handling."""
        try:
            # Initialize device climate entities tracking if not exists
            if not hasattr(self, '_device_climate_entities'):
                self._device_climate_entities = {}
            
            if device_name not in self._device_climate_entities:
                self._device_climate_entities[device_name] = []
            
            # Add entity to device tracking if not already present
            if entity_id not in self._device_climate_entities[device_name]:
                self._device_climate_entities[device_name].append(entity_id)
                
                _LOGGER.debug(
                    "Registered W100 climate entity %s for device %s",
                    entity_id,
                    device_name,
                )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to register W100 climate entity %s for device %s: %s",
                entity_id,
                device_name,
                err,
            )

    async def _async_route_action_to_w100_entities(self, action: str, device_name: str) -> None:
        """Route W100 action to registered W100 climate entities."""
        try:
            if not hasattr(self, '_device_climate_entities'):
                return
            
            climate_entities = self._device_climate_entities.get(device_name, [])
            if not climate_entities:
                return
            
            # Route action to all registered W100 climate entities for this device
            for entity_id in climate_entities:
                try:
                    # Get the entity from the entity registry
                    entity = self.hass.data.get("entity_components", {}).get("climate")
                    if entity:
                        climate_entity = entity.get_entity(entity_id)
                        if climate_entity and hasattr(climate_entity, 'async_handle_w100_button'):
                            await climate_entity.async_handle_w100_button(action)
                        elif climate_entity and hasattr(climate_entity, 'async_handle_w100_action'):
                            # Fallback to legacy method for backward compatibility
                            await climate_entity.async_handle_w100_action(action)
                            _LOGGER.debug(
                                "Routed W100 action %s to climate entity %s for device %s",
                                action,
                                entity_id,
                                device_name,
                            )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to route W100 action %s to entity %s: %s",
                        action,
                        entity_id,
                        err,
                    )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to route W100 action %s to entities for device %s: %s",
                action,
                device_name,
                err,
            )