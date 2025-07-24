"""Sensor platform for W100 Smart Control integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)

from .const import (
    DOMAIN,
    CONF_W100_DEVICE_NAME,
    CONF_HUMIDITY_SENSOR,
    CONF_BACKUP_HUMIDITY_SENSOR,
)
from .coordinator import W100Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up W100 sensor entities from a config entry."""
    coordinator: W100Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    device_name = config_entry.data.get(CONF_W100_DEVICE_NAME)
    if not device_name:
        _LOGGER.error("No W100 device name found in config entry")
        return
    
    sensors = []
    
    # Create humidity sensor that mirrors W100 display values
    sensors.append(W100HumiditySensor(coordinator, config_entry, device_name))
    
    # Create status sensor for integration mode and last action
    sensors.append(W100StatusSensor(coordinator, config_entry, device_name))
    
    # Create diagnostic sensors for MQTT connection and integration errors
    sensors.append(W100ConnectionSensor(coordinator, config_entry, device_name))
    sensors.append(W100DiagnosticSensor(coordinator, config_entry, device_name))
    
    async_add_entities(sensors)
    _LOGGER.info(
        "Added %d sensor entities for W100 device %s",
        len(sensors),
        device_name,
    )


class W100BaseSensor(SensorEntity):
    """Base class for W100 sensor entities."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the W100 sensor."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._device_name = device_name
        self._sensor_type = sensor_type
        
        # Generate unique entity ID
        self._attr_unique_id = f"{DOMAIN}_{device_name}_{sensor_type}"
        self._attr_name = f"W100 {device_name.replace('_', ' ').title()} {sensor_type.replace('_', ' ').title()}"
        
        # Set up device info for logical device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"w100_control_{device_name}")},
            name=f"W100 Control for {device_name.replace('_', ' ').title()}",
            manufacturer="W100 Smart Control Integration",
            model="Climate Controller",
            sw_version="1.0.0",
            configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
        )
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.last_update_success
    
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._coordinator.async_add_listener(self.async_write_ha_state)
        
        # Register this sensor entity with the coordinator for proper registry integration
        await self._coordinator.async_register_sensor_entity(
            self._device_name, self.entity_id, self._sensor_type
        )
    
    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        self._coordinator.async_remove_listener(self.async_write_ha_state)


class W100HumiditySensor(W100BaseSensor):
    """Humidity sensor that mirrors W100 display values from MQTT."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the humidity sensor."""
        super().__init__(coordinator, config_entry, device_name, "humidity")
        
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:water-percent"
    
    @property
    def native_value(self) -> int | None:
        """Return the humidity value from W100 display."""
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        return device_state.get("humidity")
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        
        attributes = {
            "w100_device_name": self._device_name,
            "integration_version": "1.0.0",
            "sensor_type": "humidity_display",
            "data_source": "W100 MQTT Display",
        }
        
        # Add humidity sensor configuration if available
        humidity_sensor = self._config_entry.data.get(CONF_HUMIDITY_SENSOR)
        backup_humidity_sensor = self._config_entry.data.get(CONF_BACKUP_HUMIDITY_SENSOR)
        
        if humidity_sensor:
            attributes["primary_humidity_sensor"] = humidity_sensor
        if backup_humidity_sensor:
            attributes["backup_humidity_sensor"] = backup_humidity_sensor
        
        # Add last update time
        if device_state.get("last_update"):
            attributes["last_updated"] = device_state["last_update"]
        
        return attributes


class W100StatusSensor(W100BaseSensor):
    """Status sensor for current integration mode and last W100 action processed."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the status sensor."""
        super().__init__(coordinator, config_entry, device_name, "status")
        
        self._attr_icon = "mdi:information-outline"
    
    @property
    def native_value(self) -> str | None:
        """Return the current integration status."""
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        
        # Determine status based on device state
        if not device_state:
            return "disconnected"
        
        last_action = device_state.get("last_action")
        if last_action:
            return f"active - last: {last_action}"
        
        return "connected"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        
        attributes = {
            "w100_device_name": self._device_name,
            "integration_version": "1.0.0",
            "sensor_type": "status",
        }
        
        # Add device state information
        if device_state:
            attributes.update({
                "last_action": device_state.get("last_action"),
                "last_action_time": device_state.get("last_action_time"),
                "display_mode": device_state.get("display_mode"),
                "connection_status": device_state.get("connection_status", "connected"),
                "current_mode": device_state.get("current_mode"),
            })
        
        # Add coordinator information
        coordinator_data = self._coordinator.data
        if coordinator_data:
            attributes.update({
                "created_thermostats": coordinator_data.get("created_thermostats", 0),
                "coordinator_status": coordinator_data.get("status", "unknown"),
                "last_coordinator_update": coordinator_data.get("last_update"),
            })
        
        return attributes


class W100ConnectionSensor(W100BaseSensor):
    """Diagnostic sensor for MQTT connection status."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the connection sensor."""
        super().__init__(coordinator, config_entry, device_name, "connection")
        
        self._attr_icon = "mdi:wifi"
        self._attr_entity_category = "diagnostic"
    
    @property
    def native_value(self) -> str | None:
        """Return the MQTT connection status."""
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        
        if not device_state:
            return "disconnected"
        
        # Check if we've received recent MQTT messages
        last_action_time = device_state.get("last_action_time")
        if last_action_time:
            # If we have recent activity, connection is good
            time_diff = datetime.now() - last_action_time
            if time_diff.total_seconds() < 300:  # 5 minutes
                return "connected"
        
        # Check coordinator status
        if self._coordinator.last_update_success:
            return "connected"
        
        return "disconnected"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        
        attributes = {
            "w100_device_name": self._device_name,
            "integration_version": "1.0.0",
            "sensor_type": "connection",
        }
        
        # Add MQTT connection details
        if device_state:
            last_action_time = device_state.get("last_action_time")
            if last_action_time:
                time_diff = datetime.now() - last_action_time
                attributes["seconds_since_last_action"] = int(time_diff.total_seconds())
        
        # Add coordinator connection info
        attributes.update({
            "coordinator_last_update_success": self._coordinator.last_update_success,
            "coordinator_last_exception": str(self._coordinator.last_exception) if self._coordinator.last_exception else None,
        })
        
        return attributes


class W100DiagnosticSensor(W100BaseSensor):
    """Diagnostic sensor for integration errors and troubleshooting."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator, config_entry, device_name, "diagnostic")
        
        self._attr_icon = "mdi:bug-outline"
        self._attr_entity_category = "diagnostic"
    
    @property
    def native_value(self) -> str | None:
        """Return the diagnostic status."""
        if self._coordinator.last_exception:
            return f"error: {type(self._coordinator.last_exception).__name__}"
        
        if not self._coordinator.last_update_success:
            return "update_failed"
        
        return "ok"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic information for troubleshooting."""
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        
        attributes = {
            "w100_device_name": self._device_name,
            "integration_version": "1.0.0",
            "sensor_type": "diagnostic",
        }
        
        # Add error information
        if self._coordinator.last_exception:
            attributes.update({
                "last_exception": str(self._coordinator.last_exception),
                "exception_type": type(self._coordinator.last_exception).__name__,
            })
        
        # Add configuration information for troubleshooting
        config_data = self._config_entry.data
        attributes.update({
            "config_entry_id": self._config_entry.entry_id,
            "climate_entity_type": config_data.get("climate_entity_type"),
            "existing_climate_entity": config_data.get("existing_climate_entity"),
            "beep_mode": config_data.get("beep_mode"),
        })
        
        # Add device state for troubleshooting
        if device_state:
            attributes.update({
                "device_current_mode": device_state.get("current_mode"),
                "device_target_temperature": device_state.get("target_temperature"),
                "device_current_temperature": device_state.get("current_temperature"),
                "device_fan_speed": device_state.get("fan_speed"),
            })
        
        # Add coordinator statistics
        coordinator_data = self._coordinator.data
        if coordinator_data:
            attributes.update({
                "total_device_states": len(coordinator_data.get("device_states", {})),
                "created_thermostats_count": coordinator_data.get("created_thermostats", 0),
            })
        
        return attributes