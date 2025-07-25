"""Config flow for W100 Smart Control integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.components import mqtt

from .exceptions import (
    W100IntegrationError,
    W100DeviceError,
    W100MQTTError,
    W100EntityError,
    W100ConfigurationError,
    W100ErrorCodes,
)
from .error_messages import (
    W100ErrorMessages,
    W100ConfigFlowMessages,
    W100DiagnosticInfo,
)
from .const import (
    DOMAIN,
    CONF_W100_DEVICE_NAME,
    CONF_CLIMATE_ENTITY_TYPE,
    CONF_EXISTING_CLIMATE_ENTITY,
    CONF_GENERIC_THERMOSTAT_CONFIG,
    CONF_HEATING_TEMPERATURE,
    CONF_IDLE_TEMPERATURE,
    CONF_HEATING_WARM_LEVEL,
    CONF_IDLE_WARM_LEVEL,
    CONF_IDLE_FAN_SPEED,
    CONF_SWING_MODE,
    CONF_BEEP_MODE,
    CONF_HUMIDITY_SENSOR,
    CONF_BACKUP_HUMIDITY_SENSOR,
    CONF_HEATER_SWITCH,
    CONF_TEMPERATURE_SENSOR,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_TARGET_TEMP,
    CONF_COLD_TOLERANCE,
    CONF_HOT_TOLERANCE,
    CONF_PRECISION,
    DEFAULT_HEATING_TEMPERATURE,
    DEFAULT_IDLE_TEMPERATURE,
    DEFAULT_HEATING_WARM_LEVEL,
    DEFAULT_IDLE_WARM_LEVEL,
    DEFAULT_IDLE_FAN_SPEED,
    DEFAULT_SWING_MODE,
    DEFAULT_BEEP_MODE,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_TARGET_TEMP,
    DEFAULT_COLD_TOLERANCE,
    DEFAULT_HOT_TOLERANCE,
    DEFAULT_PRECISION,
    CLIMATE_ENTITY_TYPES,
    WARM_LEVELS,
    FAN_SPEEDS,
    SWING_MODES,
    BEEP_MODES,
    PRECISION_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class EntityNotFoundError(ConfigValidationError):
    """Raised when required entity is not found."""
    pass


class W100DeviceNotFoundError(ConfigValidationError):
    """Raised when W100 device is not accessible via Zigbee2MQTT."""
    pass


class W100ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for W100 Smart Control."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config: dict[str, Any] = {}
        self._discovered_w100_devices: list[str] = []
        self._available_climate_entities: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate MQTT is available
                if not mqtt.async_get_mqtt(self.hass):
                    errors["base"] = "mqtt_not_configured"
                else:
                    # Store initial config and proceed to device discovery
                    self._config.update(user_input)
                    return await self.async_step_device_selection()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during initial setup")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default="W100 Smart Control"): str,
            }),
            errors=errors,
            description_placeholders={
                "docs_url": "https://github.com/your-username/w100-smart-control"
            },
        )

    async def async_step_device_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle W100 device selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate selected W100 device
                device_name = user_input[CONF_W100_DEVICE_NAME]
                if await self._async_validate_w100_device(device_name):
                    self._config.update(user_input)
                    return await self.async_step_climate_selection()
                else:
                    errors[CONF_W100_DEVICE_NAME] = "device_not_found"
            except W100DeviceNotFoundError:
                errors[CONF_W100_DEVICE_NAME] = "device_not_accessible"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error validating W100 device")
                errors["base"] = "unknown"

        # Discover available W100 devices
        try:
            self._discovered_w100_devices = await self._async_discover_w100_devices()
        except W100DeviceNotFoundError as err:
            _LOGGER.warning("W100 device discovery failed: %s", err)
            errors["base"] = "discovery_failed"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error discovering W100 devices")
            errors["base"] = "discovery_failed"

        if not self._discovered_w100_devices and not errors:
            errors["base"] = "no_devices_found"

        device_options = [
            selector.SelectOptionDict(value=device, label=device)
            for device in self._discovered_w100_devices
        ]

        # If no devices found, provide helpful guidance
        if not device_options and not errors:
            return self.async_show_form(
                step_id="device_selection",
                data_schema=vol.Schema({}),
                errors={"base": "no_devices_found"},
                description_placeholders={
                    "device_count": "0",
                    "zigbee2mqtt_topic": "zigbee2mqtt/bridge/devices",
                    "docs_url": "https://github.com/your-username/w100-smart-control#setup"
                },
            )

        return self.async_show_form(
            step_id="device_selection",
            data_schema=vol.Schema({
                vol.Required(CONF_W100_DEVICE_NAME): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=device_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._discovered_w100_devices))
            },
        )

    async def async_step_climate_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle climate entity selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                climate_type = user_input[CONF_CLIMATE_ENTITY_TYPE]
                
                if climate_type == "existing":
                    # Check if any climate entities are available
                    if not self._available_climate_entities:
                        errors[CONF_CLIMATE_ENTITY_TYPE] = "no_climate_entities_available"
                    else:
                        # Validate existing climate entity is provided and valid
                        entity_id = user_input.get(CONF_EXISTING_CLIMATE_ENTITY)
                        if not entity_id:
                            errors[CONF_EXISTING_CLIMATE_ENTITY] = "entity_required"
                        else:
                            validation_result = await self._async_validate_climate_entity(entity_id)
                            if validation_result["valid"]:
                                self._config.update(user_input)
                                return await self.async_step_customization()
                            else:
                                errors[CONF_EXISTING_CLIMATE_ENTITY] = validation_result["error"]
                elif climate_type == "generic":
                    self._config.update(user_input)
                    return await self.async_step_generic_thermostat()
                else:
                    errors[CONF_CLIMATE_ENTITY_TYPE] = "invalid_selection"
            except EntityNotFoundError:
                errors[CONF_EXISTING_CLIMATE_ENTITY] = "entity_not_accessible"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error validating climate entity")
                errors["base"] = "unknown"

        # Get available climate entities
        try:
            self._available_climate_entities = await self._async_get_climate_entities()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Error getting climate entities")
            errors["base"] = "entity_discovery_failed"

        # Create climate entity options with additional info
        climate_options = []
        for entity_id in self._available_climate_entities:
            # Get entity state to show current mode/temperature
            state = self.hass.states.get(entity_id)
            if state:
                current_temp = state.attributes.get("current_temperature", "Unknown")
                hvac_mode = state.state
                label = f"{entity_id} (Mode: {hvac_mode}, Temp: {current_temp}°C)"
            else:
                label = entity_id
            
            climate_options.append(
                selector.SelectOptionDict(value=entity_id, label=label)
            )

        # Build schema based on available entities
        schema_dict = {
            vol.Required(CONF_CLIMATE_ENTITY_TYPE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="existing", label="Use existing climate entity"),
                        selector.SelectOptionDict(value="generic", label="Create new generic thermostat"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        # Add climate entity selector - show if entities are available
        if climate_options:
            # Make the climate entity selection conditional based on user's choice
            # If user previously selected "existing", make it required
            previous_selection = user_input.get(CONF_CLIMATE_ENTITY_TYPE) if user_input else None
            if previous_selection == "existing":
                schema_dict[vol.Required(CONF_EXISTING_CLIMATE_ENTITY)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=climate_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            else:
                schema_dict[vol.Optional(CONF_EXISTING_CLIMATE_ENTITY)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=climate_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
        else:
            # No climate entities available - show informational message
            if not errors:
                errors["base"] = "no_climate_entities"

        return self.async_show_form(
            step_id="climate_selection",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "climate_count": str(len(self._available_climate_entities)),
                "w100_device": self._config.get(CONF_W100_DEVICE_NAME, "Unknown")
            },
        )

    async def async_step_generic_thermostat(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle generic thermostat configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate required entities
                heater_switch = user_input[CONF_HEATER_SWITCH]
                temp_sensor = user_input[CONF_TEMPERATURE_SENSOR]
                
                if not await self._async_validate_entity(heater_switch, "switch"):
                    errors[CONF_HEATER_SWITCH] = "entity_not_found"
                elif not await self._async_validate_entity(temp_sensor, "sensor"):
                    errors[CONF_TEMPERATURE_SENSOR] = "entity_not_found"
                else:
                    # Store generic thermostat config
                    self._config[CONF_GENERIC_THERMOSTAT_CONFIG] = user_input
                    return await self.async_step_customization()
            except EntityNotFoundError as err:
                _LOGGER.error("Entity validation failed: %s", err)
                errors["base"] = "entity_not_accessible"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error validating generic thermostat config")
                errors["base"] = "unknown"

        # Get available switch and sensor entities
        switch_entities = await self._async_get_entities_by_domain("switch")
        sensor_entities = await self._async_get_entities_by_domain("sensor")

        switch_options = [
            selector.SelectOptionDict(value=entity_id, label=entity_id)
            for entity_id in switch_entities
        ]
        sensor_options = [
            selector.SelectOptionDict(value=entity_id, label=entity_id)
            for entity_id in sensor_entities
        ]

        return self.async_show_form(
            step_id="generic_thermostat",
            data_schema=vol.Schema({
                vol.Required(CONF_HEATER_SWITCH): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=switch_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_TEMPERATURE_SENSOR): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sensor_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=15, step=0.5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=25, max=50, step=0.5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10, max=30, step=0.5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_COLD_TOLERANCE, default=DEFAULT_COLD_TOLERANCE): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1, max=2.0, step=0.1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_HOT_TOLERANCE, default=DEFAULT_HOT_TOLERANCE): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1, max=2.0, step=0.1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_PRECISION, default=DEFAULT_PRECISION): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=str(p), label=f"{p}°C")
                            for p in PRECISION_OPTIONS
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )

    async def async_step_customization(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle customization options step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate optional humidity sensors if provided
                humidity_sensor = user_input.get(CONF_HUMIDITY_SENSOR)
                backup_humidity_sensor = user_input.get(CONF_BACKUP_HUMIDITY_SENSOR)
                
                if humidity_sensor and not await self._async_validate_entity(humidity_sensor, "sensor"):
                    errors[CONF_HUMIDITY_SENSOR] = "entity_not_found"
                elif backup_humidity_sensor and not await self._async_validate_entity(backup_humidity_sensor, "sensor"):
                    errors[CONF_BACKUP_HUMIDITY_SENSOR] = "entity_not_found"
                else:
                    # Store customization config and create entry
                    self._config.update(user_input)
                    return await self._async_create_entry()
            except EntityNotFoundError:
                errors["base"] = "entity_not_accessible"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error validating customization config")
                errors["base"] = "unknown"

        # Get available sensor entities for humidity
        sensor_entities = await self._async_get_entities_by_domain("sensor")
        sensor_options = [
            selector.SelectOptionDict(value=entity_id, label=entity_id)
            for entity_id in sensor_entities
        ]

        return self.async_show_form(
            step_id="customization",
            data_schema=vol.Schema({
                vol.Optional(CONF_HEATING_TEMPERATURE, default=DEFAULT_HEATING_TEMPERATURE): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=15, max=35, step=0.5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_IDLE_TEMPERATURE, default=DEFAULT_IDLE_TEMPERATURE): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=15, max=35, step=0.5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_HEATING_WARM_LEVEL, default=DEFAULT_HEATING_WARM_LEVEL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=level, label=f"Level {level}")
                            for level in WARM_LEVELS
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_IDLE_WARM_LEVEL, default=DEFAULT_IDLE_WARM_LEVEL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=level, label=f"Level {level}")
                            for level in WARM_LEVELS
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_IDLE_FAN_SPEED, default=DEFAULT_IDLE_FAN_SPEED): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=speed, label=f"Speed {speed}")
                            for speed in FAN_SPEEDS
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_SWING_MODE, default=DEFAULT_SWING_MODE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=mode, label=mode.title())
                            for mode in SWING_MODES
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_BEEP_MODE, default=DEFAULT_BEEP_MODE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=mode, label=mode)
                            for mode in BEEP_MODES
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_HUMIDITY_SENSOR): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sensor_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_BACKUP_HUMIDITY_SENSOR): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sensor_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )

    async def _async_create_entry(self) -> FlowResult:
        """Create the config entry."""
        # Generate unique ID based on W100 device name
        device_name = self._config[CONF_W100_DEVICE_NAME]
        await self.async_set_unique_id(f"{DOMAIN}_{device_name}")
        self._abort_if_unique_id_configured()

        title = f"W100 Smart Control ({device_name})"
        
        return self.async_create_entry(
            title=title,
            data=self._config,
        )

    async def _async_discover_w100_devices(self) -> list[str]:
        """Discover available W100 devices via Zigbee2MQTT."""
        try:
            # Get MQTT client
            mqtt_client = mqtt.async_get_mqtt(self.hass)
            if not mqtt_client:
                raise W100DeviceNotFoundError("MQTT not configured")

            _LOGGER.debug("Starting W100 device discovery via Zigbee2MQTT")
            
            discovered_devices = []
            
            # Try primary discovery method - Zigbee2MQTT bridge API
            try:
                bridge_devices = await self._async_get_zigbee2mqtt_devices()
                _LOGGER.debug("Retrieved %d devices from Zigbee2MQTT bridge", len(bridge_devices))
                
                # Filter for W100 devices based on device information
                for device_info in bridge_devices:
                    if self._is_w100_device(device_info):
                        device_name = device_info.get("friendly_name")
                        if not device_name:
                            # Fallback to IEEE address if no friendly name
                            device_name = device_info.get("ieee_address")
                        
                        if device_name:
                            _LOGGER.debug("Found potential W100 device: %s", device_name)
                            # Validate device accessibility via MQTT
                            if await self._async_validate_w100_mqtt_topics(device_name):
                                discovered_devices.append(device_name)
                                _LOGGER.info("Validated W100 device: %s", device_name)
                            else:
                                _LOGGER.warning(
                                    "W100 device %s found in bridge but MQTT topics not accessible", 
                                    device_name
                                )
                
            except Exception as bridge_err:
                _LOGGER.warning("Bridge discovery failed, trying fallback method: %s", bridge_err)
                # Try fallback discovery method
                fallback_devices = await self._async_fallback_device_discovery()
                discovered_devices.extend(fallback_devices)
            
            if not discovered_devices:
                _LOGGER.warning("No accessible W100 devices found")
                # Don't raise exception here - let the UI handle the empty list
                return []
            
            _LOGGER.info("Successfully discovered %d accessible W100 devices", len(discovered_devices))
            return sorted(discovered_devices)  # Sort for consistent ordering
            
        except W100DeviceNotFoundError:
            # Re-raise our custom exceptions
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error during W100 device discovery: %s", err)
            raise W100DeviceNotFoundError(f"Device discovery failed: {err}") from err

    async def _async_validate_w100_device(self, device_name: str) -> bool:
        """Validate that W100 device is accessible via Zigbee2MQTT."""
        try:
            if not device_name:
                _LOGGER.warning("Empty device name provided for validation")
                return False
            
            # Check if device is in discovered list (if discovery was run)
            if self._discovered_w100_devices and device_name not in self._discovered_w100_devices:
                _LOGGER.warning("W100 device %s not found in discovered devices list", device_name)
                # Still try to validate directly in case discovery missed it
            
            # Validate MQTT topics are accessible - this is the definitive test
            if not await self._async_validate_w100_mqtt_topics(device_name):
                _LOGGER.warning("W100 device %s MQTT topics not accessible", device_name)
                return False
            
            # Additional validation - check if device responds to get request
            if not await self._async_test_w100_device_response(device_name):
                _LOGGER.warning("W100 device %s does not respond to requests", device_name)
                return False
                
            _LOGGER.debug("W100 device %s validated successfully", device_name)
            return True
                
        except Exception as err:
            _LOGGER.error("Failed to validate W100 device %s: %s", device_name, err)
            raise W100DeviceNotFoundError(f"Device validation failed: {err}") from err

    async def _async_get_climate_entities(self) -> list[str]:
        """Get list of available climate entities."""
        return await self._async_get_entities_by_domain("climate")

    async def _async_get_entities_by_domain(self, domain: str) -> list[str]:
        """Get list of entities by domain."""
        try:
            entity_registry = async_get_entity_registry(self.hass)
            entities = [
                entry.entity_id
                for entry in entity_registry.entities.values()
                if entry.entity_id.startswith(f"{domain}.")
                and not entry.disabled_by
            ]
            _LOGGER.debug("Found %d %s entities", len(entities), domain)
            return sorted(entities)
        except Exception as err:
            _LOGGER.error("Failed to get %s entities: %s", domain, err)
            return []

    async def _async_validate_climate_entity(self, entity_id: str) -> dict[str, Any]:
        """Validate that climate entity exists and supports required features."""
        try:
            # Basic entity validation
            if not entity_id.startswith("climate."):
                _LOGGER.warning("Entity %s is not a climate entity", entity_id)
                return {"valid": False, "error": "not_climate_entity"}

            state = self.hass.states.get(entity_id)
            if state is None:
                _LOGGER.warning("Climate entity %s not found in state registry", entity_id)
                return {"valid": False, "error": "entity_not_found"}

            # Check if entity is available
            if state.state == "unavailable":
                _LOGGER.warning("Climate entity %s is unavailable", entity_id)
                return {"valid": False, "error": "entity_unavailable"}

            # Validate required climate features for W100 integration
            attributes = state.attributes
            
            # Check for required HVAC modes (heat and off are minimum)
            hvac_modes = attributes.get("hvac_modes", [])
            if "heat" not in hvac_modes:
                _LOGGER.warning("Climate entity %s does not support heat mode", entity_id)
                return {"valid": False, "error": "heat_mode_not_supported"}
            
            if "off" not in hvac_modes:
                _LOGGER.warning("Climate entity %s does not support off mode", entity_id)
                return {"valid": False, "error": "off_mode_not_supported"}

            # Check for temperature control support
            if "temperature" not in attributes.get("supported_features", []):
                # Check if target_temperature attribute exists as alternative
                if "target_temperature" not in attributes:
                    _LOGGER.warning("Climate entity %s does not support temperature control", entity_id)
                    return {"valid": False, "error": "temperature_control_not_supported"}

            # Check for current temperature sensor
            if "current_temperature" not in attributes:
                _LOGGER.warning("Climate entity %s does not provide current temperature", entity_id)
                return {"valid": False, "error": "current_temperature_not_available"}

            # Validate temperature ranges are reasonable
            min_temp = attributes.get("min_temp")
            max_temp = attributes.get("max_temp")
            
            if min_temp is not None and max_temp is not None:
                if min_temp >= max_temp:
                    _LOGGER.warning("Climate entity %s has invalid temperature range", entity_id)
                    return {"valid": False, "error": "invalid_temperature_range"}
                
                # Check if temperature range is compatible with W100 (15-35°C typical)
                if max_temp < 25 or min_temp > 15:
                    _LOGGER.warning(
                        "Climate entity %s temperature range may not be suitable for W100 control", 
                        entity_id
                    )
                    # This is a warning, not a failure
            
            # Check precision for W100 compatibility (should support 0.5°C steps)
            precision = attributes.get("precision", 1.0)
            if precision > 1.0:
                _LOGGER.warning(
                    "Climate entity %s precision (%s°C) may not be optimal for W100 control", 
                    entity_id, precision
                )
                # This is a warning, not a failure

            _LOGGER.debug("Climate entity %s validated successfully", entity_id)
            return {"valid": True, "error": None}
            
        except Exception as err:
            _LOGGER.error("Failed to validate climate entity %s: %s", entity_id, err)
            raise EntityNotFoundError(f"Climate entity validation failed: {err}") from err

    async def _async_validate_entity(self, entity_id: str, expected_domain: str) -> bool:
        """Validate that entity exists and has expected domain."""
        try:
            if not entity_id or not isinstance(entity_id, str):
                _LOGGER.warning("Invalid entity ID provided: %s", entity_id)
                return False

            if not entity_id.startswith(f"{expected_domain}."):
                _LOGGER.warning("Entity %s does not match expected domain %s", entity_id, expected_domain)
                return False

            state = self.hass.states.get(entity_id)
            if state is None:
                _LOGGER.warning("Entity %s not found in state registry", entity_id)
                return False

            # Check if entity is available
            if state.state == "unavailable":
                _LOGGER.warning("Entity %s is currently unavailable", entity_id)
                return False

            _LOGGER.debug("Entity %s validated successfully", entity_id)
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to validate entity %s: %s", entity_id, err)
            raise EntityNotFoundError(f"Entity validation failed: {err}") from err

    async def _async_validate_entities_exist_and_accessible(self, config: dict[str, Any]) -> dict[str, str]:
        """Validate that all configured entities exist and are accessible."""
        errors = {}
        
        try:
            # Validate climate entity if using existing
            if config.get(CONF_CLIMATE_ENTITY_TYPE) == "existing":
                climate_entity = config.get(CONF_EXISTING_CLIMATE_ENTITY)
                if climate_entity:
                    validation_result = await self._async_validate_climate_entity(climate_entity)
                    if not validation_result["valid"]:
                        errors[CONF_EXISTING_CLIMATE_ENTITY] = validation_result["error"]
                else:
                    errors[CONF_EXISTING_CLIMATE_ENTITY] = "entity_required"
            
            # Validate generic thermostat entities if using generic
            elif config.get(CONF_CLIMATE_ENTITY_TYPE) == "generic":
                generic_config = config.get(CONF_GENERIC_THERMOSTAT_CONFIG, {})
                
                heater_switch = generic_config.get(CONF_HEATER_SWITCH)
                if heater_switch:
                    if not await self._async_validate_entity(heater_switch, "switch"):
                        errors[CONF_HEATER_SWITCH] = "entity_not_found"
                else:
                    errors[CONF_HEATER_SWITCH] = "entity_required"
                
                temp_sensor = generic_config.get(CONF_TEMPERATURE_SENSOR)
                if temp_sensor:
                    if not await self._async_validate_entity(temp_sensor, "sensor"):
                        errors[CONF_TEMPERATURE_SENSOR] = "entity_not_found"
                else:
                    errors[CONF_TEMPERATURE_SENSOR] = "entity_required"
            
            # Validate optional humidity sensors
            humidity_sensor = config.get(CONF_HUMIDITY_SENSOR)
            if humidity_sensor and not await self._async_validate_entity(humidity_sensor, "sensor"):
                errors[CONF_HUMIDITY_SENSOR] = "entity_not_found"
            
            backup_humidity_sensor = config.get(CONF_BACKUP_HUMIDITY_SENSOR)
            if backup_humidity_sensor and not await self._async_validate_entity(backup_humidity_sensor, "sensor"):
                errors[CONF_BACKUP_HUMIDITY_SENSOR] = "entity_not_found"
                
        except Exception as err:
            _LOGGER.error("Failed to validate entities: %s", err)
            errors["base"] = "entity_validation_failed"
        
        return errors

    async def _async_get_zigbee2mqtt_devices(self) -> list[dict]:
        """Get device list from Zigbee2MQTT bridge."""
        try:
            # Get MQTT client
            mqtt_client = mqtt.async_get_mqtt(self.hass)
            if not mqtt_client:
                raise W100DeviceNotFoundError("MQTT not configured")

            # Set up a future to receive the bridge response
            response_future = asyncio.Future()
            devices_data = []

            def message_received(msg):
                """Handle bridge response message."""
                try:
                    payload = json.loads(msg.payload)
                    if isinstance(payload, list):
                        devices_data.extend(payload)
                    elif isinstance(payload, dict):
                        if "devices" in payload:
                            devices_data.extend(payload["devices"])
                        elif payload:  # Single device response
                            devices_data.append(payload)
                    
                    if not response_future.done():
                        response_future.set_result(devices_data)
                except (json.JSONDecodeError, KeyError) as err:
                    _LOGGER.warning("Failed to parse Zigbee2MQTT bridge response: %s", err)
                    if not response_future.done():
                        response_future.set_result([])

            # Subscribe to bridge devices topic
            bridge_topic = "zigbee2mqtt/bridge/devices"
            unsubscribe = await mqtt_client.async_subscribe(
                bridge_topic, message_received, qos=0
            )

            try:
                # Request device list from bridge
                await mqtt_client.async_publish(
                    "zigbee2mqtt/bridge/request/devices", "", qos=0
                )

                # Wait for response with timeout
                devices = await asyncio.wait_for(response_future, timeout=10.0)
                _LOGGER.debug("Retrieved %d devices from Zigbee2MQTT bridge", len(devices))
                return devices

            finally:
                # Clean up subscription
                unsubscribe()

        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout waiting for Zigbee2MQTT bridge response")
            # Try alternative method - check for existing device state topics
            return await self._async_fallback_device_discovery()
        except Exception as err:
            _LOGGER.error("Failed to get Zigbee2MQTT devices: %s", err)
            return []

    async def _async_fallback_device_discovery(self) -> list[str]:
        """Fallback device discovery by scanning MQTT state topics."""
        try:
            _LOGGER.debug("Attempting fallback W100 device discovery")
            
            # Get MQTT client
            mqtt_client = mqtt.async_get_mqtt(self.hass)
            if not mqtt_client:
                return []
            
            discovered_devices = []
            
            # Set up a future to collect potential device names
            discovery_future = asyncio.Future()
            potential_devices = set()
            
            def topic_message_received(msg):
                """Handle messages from zigbee2mqtt topics to identify devices."""
                try:
                    topic_parts = msg.topic.split('/')
                    if len(topic_parts) >= 2 and topic_parts[0] == 'zigbee2mqtt':
                        device_name = topic_parts[1]
                        
                        # Skip bridge and other system topics
                        if device_name not in ['bridge', 'log']:
                            # Try to parse the payload to see if it looks like W100 data
                            try:
                                payload = json.loads(msg.payload)
                                if isinstance(payload, dict):
                                    # Check for W100-like properties
                                    w100_indicators = ['action', 'temperature', 'humidity', 'battery']
                                    if any(indicator in payload for indicator in w100_indicators):
                                        potential_devices.add(device_name)
                                        _LOGGER.debug("Found potential W100 device via fallback: %s", device_name)
                            except json.JSONDecodeError:
                                pass  # Not JSON, skip
                                
                except Exception as err:
                    _LOGGER.debug("Error processing fallback discovery message: %s", err)
            
            # Subscribe to all zigbee2mqtt device topics
            fallback_topic = "zigbee2mqtt/+/+"  # This will catch state and action topics
            unsubscribe = await mqtt_client.async_subscribe(
                fallback_topic, topic_message_received, qos=0
            )
            
            try:
                # Wait a bit to collect messages
                await asyncio.sleep(3.0)
                
                # Validate each potential device
                for device_name in potential_devices:
                    if await self._async_validate_w100_mqtt_topics(device_name):
                        discovered_devices.append(device_name)
                        _LOGGER.info("Validated W100 device via fallback: %s", device_name)
                
            finally:
                # Clean up subscription
                unsubscribe()
            
            _LOGGER.debug("Fallback discovery found %d devices", len(discovered_devices))
            return discovered_devices
            
        except Exception as err:
            _LOGGER.error("Fallback device discovery failed: %s", err)
            return []

    def _is_w100_device(self, device_info: dict) -> bool:
        """Check if device is an Aqara W100 based on device information."""
        try:
            # Check model identifier - most reliable method
            model_id = device_info.get("model_id")
            if model_id and "W100" in model_id.upper():
                return True
            
            # Check definition model
            definition = device_info.get("definition", {})
            model = definition.get("model", "")
            if model and "W100" in model.upper():
                return True
            
            # Check manufacturer and model combination
            manufacturer = device_info.get("manufacturer") or definition.get("vendor", "")
            if manufacturer and "aqara" in manufacturer.lower():
                # Check various model name fields
                model_fields = [
                    device_info.get("model", ""),
                    definition.get("description", ""),
                    definition.get("model", ""),
                ]
                
                for model_field in model_fields:
                    if model_field and ("w100" in model_field.lower() or 
                                      ("smart" in model_field.lower() and "control" in model_field.lower())):
                        return True
            
            # Check device type - W100 is typically a sensor with specific capabilities
            device_type = device_info.get("type") or definition.get("type", "")
            if device_type == "EndDevice":  # W100 is typically an end device
                # Check for W100-specific exposed features
                exposes = definition.get("exposes", [])
                if isinstance(exposes, list):
                    exposed_features = set()
                    for expose in exposes:
                        if isinstance(expose, dict):
                            exposed_features.add(expose.get("property", ""))
                    
                    # W100 typically exposes: action, temperature, humidity, battery
                    w100_features = {"action", "temperature", "humidity"}
                    if w100_features.issubset(exposed_features):
                        return True
            
            
            # Additional check for action values typical of W100
            if isinstance(exposes, list):
                for expose in exposes:
                    if (expose.get("property") == "action" and 
                        isinstance(expose.get("values"), list)):
                        action_values = set(expose["values"])
                        w100_actions = {"double", "plus", "minus"}
                        if w100_actions.issubset(action_values):
                            return True
            
            return False
            
        except Exception as err:
            _LOGGER.debug("Error checking if device is W100: %s", err)
            return False

    async def _async_test_w100_device_response(self, device_name: str) -> bool:
        """Test if W100 device responds to MQTT requests."""
        try:
            from .const import MQTT_W100_STATE_TOPIC
            
            # Get MQTT client
            mqtt_client = mqtt.async_get_mqtt(self.hass)
            if not mqtt_client:
                return False

            # Set up future for response validation
            response_future = asyncio.Future()
            received_response = False

            def response_message_received(msg):
                """Handle device response message."""
                nonlocal received_response
                try:
                    payload = json.loads(msg.payload)
                    if isinstance(payload, dict):
                        # Check for any valid W100 response data
                        valid_fields = ["temperature", "humidity", "battery", "linkquality", "action"]
                        if any(field in payload for field in valid_fields):
                            received_response = True
                            if not response_future.done():
                                response_future.set_result(True)
                except json.JSONDecodeError:
                    pass  # Invalid JSON, continue waiting

            # Subscribe to device state topic
            state_topic = MQTT_W100_STATE_TOPIC.format(device_name)
            unsubscribe = await mqtt_client.async_subscribe(
                state_topic, response_message_received, qos=0
            )

            try:
                # Send a get request to the device
                get_topic = f"zigbee2mqtt/{device_name}/get"
                await mqtt_client.async_publish(get_topic, '{"state":""}', qos=0)
                
                # Wait for response with shorter timeout
                try:
                    await asyncio.wait_for(response_future, timeout=3.0)
                    return True
                except asyncio.TimeoutError:
                    return received_response  # Return true if we got any response during the wait

            finally:
                # Clean up subscription
                unsubscribe()

        except Exception as err:
            _LOGGER.debug("Failed to test W100 device response for %s: %s", device_name, err)
            return False

    async def _async_validate_w100_mqtt_topics(self, device_name: str) -> bool:
        """Validate that W100 device MQTT topics are accessible."""
        try:
            from .const import MQTT_W100_STATE_TOPIC
            
            # Get MQTT client
            mqtt_client = mqtt.async_get_mqtt(self.hass)
            if not mqtt_client:
                return False

            # Set up future for topic validation
            validation_future = asyncio.Future()
            received_valid_message = False

            def state_message_received(msg):
                """Handle state topic message."""
                nonlocal received_valid_message
                try:
                    payload = json.loads(msg.payload)
                    # Check if payload contains expected W100 fields
                    if isinstance(payload, dict) and any(
                        key in payload for key in ["temperature", "humidity", "battery", "linkquality"]
                    ):
                        received_valid_message = True
                        if not validation_future.done():
                            validation_future.set_result(True)
                except json.JSONDecodeError:
                    pass  # Invalid JSON, continue waiting

            # Subscribe to device state topic
            state_topic = MQTT_W100_STATE_TOPIC.format(device_name)
            
            state_unsubscribe = await mqtt_client.async_subscribe(
                state_topic, state_message_received, qos=0
            )

            try:
                # First, try to get a recent state message
                try:
                    await asyncio.wait_for(validation_future, timeout=2.0)
                    return True
                except asyncio.TimeoutError:
                    pass

                # If no recent message, request device state
                get_topic = f"zigbee2mqtt/{device_name}/get"
                await mqtt_client.async_publish(get_topic, '{"state":""}', qos=0)
                
                # Wait for response to our get request
                try:
                    await asyncio.wait_for(validation_future, timeout=5.0)
                    return True
                except asyncio.TimeoutError:
                    # Last attempt - check if we received any valid message during the process
                    return received_valid_message

            finally:
                # Clean up subscription
                state_unsubscribe()

        except Exception as err:
            _LOGGER.error("Failed to validate W100 MQTT topics for %s: %s", device_name, err)
            return False

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for W100 Smart Control."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._coordinator = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        # Get coordinator to check for created thermostats
        coordinator_data = self.hass.data.get(DOMAIN, {})
        self._coordinator = coordinator_data.get(self.config_entry.entry_id)
        
        if user_input is not None:
            # Handle thermostat management actions
            action = user_input.get("action")
            
            if action == "manage_thermostats" and self._coordinator:
                return await self.async_step_manage_thermostats()
            elif action == "update_config":
                return await self.async_step_update_config()
            else:
                return self.async_create_entry(title="", data=user_input)

        # Build options based on current configuration
        options_schema = {}
        
        # Show thermostat management if we have created thermostats
        if self._coordinator and self._coordinator.created_thermostats:
            options_schema[vol.Optional("action")] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value="manage_thermostats", 
                            label="Manage Created Thermostats"
                        ),
                        selector.SelectOptionDict(
                            value="update_config", 
                            label="Update Integration Configuration"
                        ),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        else:
            options_schema[vol.Optional("action")] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value="update_config", 
                            label="Update Integration Configuration"
                        ),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema),
            description_placeholders={
                "created_thermostats": str(len(self._coordinator.created_thermostats) if self._coordinator else 0),
                "device_name": self.config_entry.data.get(CONF_W100_DEVICE_NAME, "Unknown"),
            }
        )

    async def async_step_manage_thermostats(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage created thermostats."""
        if not self._coordinator:
            return self.async_abort(reason="coordinator_not_found")

        errors = {}
        
        if user_input is not None:
            action = user_input.get("thermostat_action")
            thermostat_id = user_input.get("thermostat_id")
            
            try:
                if action == "remove" and thermostat_id:
                    await self._coordinator.async_remove_generic_thermostat(thermostat_id)
                    return self.async_create_entry(
                        title="", 
                        data={"thermostat_removed": thermostat_id}
                    )
                elif action == "remove_all":
                    await self._coordinator.async_remove_all_thermostats()
                    return self.async_create_entry(
                        title="", 
                        data={"all_thermostats_removed": True}
                    )
            except Exception as err:
                _LOGGER.error("Error managing thermostats: %s", err)
                errors["base"] = "thermostat_management_failed"

        # Get current thermostats
        thermostats = self._coordinator.created_thermostats
        if not thermostats:
            return self.async_abort(reason="no_thermostats_found")

        thermostat_options = []
        for entity_id in thermostats:
            # Get entity state for display
            state = self.hass.states.get(entity_id)
            if state:
                label = f"{entity_id} (Current: {state.state})"
            else:
                label = f"{entity_id} (Unavailable)"
            
            thermostat_options.append(
                selector.SelectOptionDict(value=entity_id, label=label)
            )

        return self.async_show_form(
            step_id="manage_thermostats",
            data_schema=vol.Schema({
                vol.Required("thermostat_action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="remove", label="Remove Selected Thermostat"),
                            selector.SelectOptionDict(value="remove_all", label="Remove All Thermostats"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("thermostat_id"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=thermostat_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )

    async def async_step_update_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Update integration configuration."""
        if user_input is not None:
            try:
                # Update the coordinator configuration if available
                if self._coordinator:
                    await self._coordinator.async_update_config(user_input)
                else:
                    # Fallback: update config entry directly
                    new_data = {**self.config_entry.data, **user_input}
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )
                
                return self.async_create_entry(title="", data=user_input)
            except Exception as err:
                _LOGGER.error("Failed to update configuration: %s", err)
                return self.async_show_form(
                    step_id="update_config",
                    errors={"base": "config_update_failed"},
                    data_schema=self._get_update_config_schema(),
                )

        return self.async_show_form(
            step_id="update_config",
            data_schema=self._get_update_config_schema(),
        )

    def _get_update_config_schema(self) -> vol.Schema:
        """Get the schema for updating configuration."""
        current_config = self.config_entry.data
        
        return vol.Schema({
            vol.Optional(
                CONF_HEATING_TEMPERATURE, 
                default=current_config.get(CONF_HEATING_TEMPERATURE, DEFAULT_HEATING_TEMPERATURE)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=15, max=35, step=0.5, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_IDLE_TEMPERATURE, 
                default=current_config.get(CONF_IDLE_TEMPERATURE, DEFAULT_IDLE_TEMPERATURE)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=15, max=35, step=0.5, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_BEEP_MODE, 
                default=current_config.get(CONF_BEEP_MODE, DEFAULT_BEEP_MODE)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=mode, label=mode)
                        for mode in BEEP_MODES
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })