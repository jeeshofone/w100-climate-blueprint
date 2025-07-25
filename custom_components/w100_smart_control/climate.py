"""Climate platform for W100 Smart Control integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
    STATE_ON,
    STATE_OFF,
)

from .const import (
    DOMAIN, 
    CONF_W100_DEVICE_NAME, 
    CONF_EXISTING_CLIMATE_ENTITY,
    CONF_BEEP_MODE,
    CONF_HEATING_TEMPERATURE,
    CONF_IDLE_TEMPERATURE,
    DEFAULT_BEEP_MODE,
    DEFAULT_HEATING_TEMPERATURE,
    DEFAULT_IDLE_TEMPERATURE,
)
from .coordinator import W100Coordinator
from .exceptions import (
    W100IntegrationError,
    W100DeviceError,
    W100EntityError,
    W100RecoverableError,
    W100ErrorCodes,
)

_LOGGER = logging.getLogger(__name__)

# Advanced feature constants
STUCK_HEATER_CHECK_INTERVAL = timedelta(minutes=5)
STUCK_HEATER_TEMP_THRESHOLD = 0.5  # °C - if temp doesn't change by this much, heater might be stuck
STUCK_HEATER_TIME_THRESHOLD = timedelta(minutes=15)  # Time to wait before considering heater stuck
DEBOUNCE_DELAY = 2.0  # seconds - delay between rapid button presses
STARTUP_INIT_DELAY = 5.0  # seconds - delay before initializing displays on startup


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up W100 climate entities from a config entry."""
    coordinator: W100Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Get the target climate entity from configuration
    target_climate_entity = config_entry.data.get(CONF_EXISTING_CLIMATE_ENTITY)
    device_name = config_entry.data.get(CONF_W100_DEVICE_NAME)
    
    if target_climate_entity and device_name:
        # Create W100 climate entity that wraps the target climate entity
        w100_climate = W100ClimateEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            target_climate_entity=target_climate_entity,
            device_name=device_name,
        )
        async_add_entities([w100_climate])
        _LOGGER.info(
            "Added W100 climate entity for device %s wrapping %s",
            device_name,
            target_climate_entity,
        )


class W100ClimateEntity(ClimateEntity):
    """Climate entity that wraps a target climate entity with W100 functionality."""

    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        target_climate_entity: str,
        device_name: str,
    ) -> None:
        """Initialize the W100 climate entity."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._target_climate_entity = target_climate_entity
        self._device_name = device_name
        
        # Generate unique entity ID
        self._attr_unique_id = f"{DOMAIN}_{device_name}_climate"
        self._attr_name = f"W100 {device_name.replace('_', ' ').title()}"
        
        # Enhanced logging context
        self._log_context = {
            "device_name": device_name,
            "target_entity": target_climate_entity,
            "entity_id": self._attr_unique_id,
            "integration": DOMAIN,
        }
        
        _LOGGER.info(
            "Initializing W100 climate entity for device '%s' targeting '%s'",
            device_name,
            target_climate_entity,
            extra=self._log_context
        )
        
        # Set up device info for logical device (not physical W100 device)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"w100_control_{device_name}")},
            name=f"W100 Control for {device_name.replace('_', ' ').title()}",
            manufacturer="W100 Smart Control Integration",
            model="Climate Controller",
            sw_version="1.0.0",
            hw_version="1.0",
            configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
            suggested_area="Living Room",
        )
        
        # Advanced feature state tracking
        self._last_button_press = None
        self._debounce_task = None
        self._stuck_heater_tracker = None
        self._last_temp_check = None
        self._last_temp_value = None
        self._heater_start_time = None
        self._startup_initialized = False
        
        # Configuration from entry
        self._beep_mode = config_entry.data.get(CONF_BEEP_MODE, DEFAULT_BEEP_MODE)
        self._heating_temperature = config_entry.data.get(CONF_HEATING_TEMPERATURE, DEFAULT_HEATING_TEMPERATURE)
        self._idle_temperature = config_entry.data.get(CONF_IDLE_TEMPERATURE, DEFAULT_IDLE_TEMPERATURE)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Check if coordinator is available and target climate entity exists
        if not self._coordinator.last_update_success:
            return False
        
        target_state = self.hass.states.get(self._target_climate_entity)
        return target_state is not None

    @property
    def target_climate_state(self):
        """Get the current state of the target climate entity."""
        return self.hass.states.get(self._target_climate_entity)

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.attributes.get("current_temperature")
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.attributes.get("temperature")
        return None

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current HVAC mode."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.state
        return None

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available HVAC modes."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.attributes.get("hvac_modes", [])
        return []

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.attributes.get("min_temp", 7)
        return 7

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.attributes.get("max_temp", 35)
        return 35

    @property
    def target_temperature_step(self) -> float:
        """Return the supported step of target temperature."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.attributes.get("target_temp_step", 0.5)
        return 0.5

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.attributes.get("unit_of_measurement", UnitOfTemperature.CELSIUS)
        return UnitOfTemperature.CELSIUS

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        target_state = self.target_climate_state
        if target_state:
            return target_state.attributes.get("supported_features", ClimateEntityFeature.TARGET_TEMPERATURE)
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes with registry integration info."""
        attributes = {}
        
        # Add W100-specific attributes
        attributes["w100_device_name"] = self._device_name
        attributes["target_climate_entity"] = self._target_climate_entity
        attributes["integration_version"] = "1.0.0"
        attributes["device_manufacturer"] = "Aqara"
        attributes["device_model"] = "W100 Smart Control"
        
        # Add configuration attributes for customization
        attributes["beep_mode"] = self._beep_mode
        attributes["heating_temperature"] = self._heating_temperature
        attributes["idle_temperature"] = self._idle_temperature
        
        # Add device state from coordinator if available
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        if device_state:
            attributes["w100_last_action"] = device_state.get("last_action")
            attributes["w100_display_mode"] = device_state.get("display_mode")
            attributes["w100_connection_status"] = device_state.get("connection_status", "connected")
        
        # Add registry information for troubleshooting
        attributes["unique_id"] = self._attr_unique_id
        attributes["device_registry_id"] = f"{DOMAIN}_{self._device_name}"
        
        return attributes

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        try:
            # Validate target entity exists
            target_state = self.hass.states.get(self._target_climate_entity)
            if not target_state:
                raise W100EntityError(
                    self._target_climate_entity,
                    "Target climate entity not found",
                    W100ErrorCodes.ENTITY_NOT_FOUND
                )
            
            # Call the target climate entity's set_hvac_mode service
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {
                        "entity_id": self._target_climate_entity,
                        "hvac_mode": hvac_mode,
                    },
                    blocking=True,
                )
            except Exception as err:
                raise W100EntityError(
                    self._target_climate_entity,
                    f"Failed to set HVAC mode: {err}",
                    W100ErrorCodes.ENTITY_OPERATION_FAILED
                ) from err
            
            # Update W100 display after mode change (non-critical)
            try:
                await self._coordinator.async_sync_w100_display(self._device_name)
            except Exception as err:
                _LOGGER.warning("Failed to sync W100 display after mode change: %s", err)
                # Continue - display sync failure is not critical
            
            _LOGGER.debug(
                "Set HVAC mode to %s for %s via target entity %s",
                hvac_mode,
                self._device_name,
                self._target_climate_entity,
            )
            
        except W100IntegrationError:
            # Re-raise W100 specific errors
            raise
        except Exception as err:
            _LOGGER.error(
                "Unexpected error setting HVAC mode %s for %s: %s",
                hvac_mode,
                self._device_name,
                err,
            )
            raise W100EntityError(
                self._target_climate_entity,
                f"Unexpected error setting HVAC mode: {err}",
                W100ErrorCodes.ENTITY_OPERATION_FAILED
            ) from err

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        try:
            temperature = kwargs.get(ATTR_TEMPERATURE)
            if temperature is None:
                _LOGGER.warning("No temperature provided in set_temperature call")
                return
            
            # Validate target entity exists
            target_state = self.hass.states.get(self._target_climate_entity)
            if not target_state:
                raise W100EntityError(
                    self._target_climate_entity,
                    "Target climate entity not found",
                    W100ErrorCodes.ENTITY_NOT_FOUND
                )
            
            # Call the target climate entity's set_temperature service
            service_data = {
                "entity_id": self._target_climate_entity,
                ATTR_TEMPERATURE: temperature,
            }
            
            # Include HVAC mode if provided
            hvac_mode = kwargs.get("hvac_mode")
            if hvac_mode:
                service_data["hvac_mode"] = hvac_mode
            
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    service_data,
                    blocking=True,
                )
            except Exception as err:
                raise W100EntityError(
                    self._target_climate_entity,
                    f"Failed to set temperature: {err}",
                    W100ErrorCodes.ENTITY_OPERATION_FAILED
                ) from err
            
            # Update W100 display after temperature change (non-critical)
            try:
                await self._coordinator.async_sync_w100_display(self._device_name)
            except Exception as err:
                _LOGGER.warning("Failed to sync W100 display after temperature change: %s", err)
                # Continue - display sync failure is not critical
            
            _LOGGER.debug(
                "Set temperature to %s°C for %s via target entity %s",
                temperature,
                self._device_name,
                self._target_climate_entity,
            )
            
        except W100IntegrationError:
            # Re-raise W100 specific errors
            raise
        except Exception as err:
            _LOGGER.error(
                "Unexpected error setting temperature for %s: %s",
                self._device_name,
                err,
            )
            raise W100EntityError(
                self._target_climate_entity,
                f"Unexpected error setting temperature: {err}",
                W100ErrorCodes.ENTITY_OPERATION_FAILED
            ) from err

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Listen for coordinator updates
        self.async_on_remove(
            self._coordinator.async_add_listener(self._handle_coordinator_update)
        )
        
        # Set up MQTT listeners for W100 button presses
        await self._setup_w100_listeners()
        
        # Set up advanced features
        await self._setup_advanced_features()

    async def _setup_w100_listeners(self) -> None:
        """Set up MQTT listeners for W100 button presses and register with proper unique ID."""
        try:
            # Register this proxy climate entity with the coordinator for W100 events
            # This also handles logical device registry integration
            await self._coordinator.async_register_proxy_climate_entity(
                self._device_name, self.entity_id
            )
            
            _LOGGER.debug(
                "Set up W100 listeners for device %s, entity %s with proper registry integration",
                self._device_name,
                self.entity_id,
            )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to set up W100 listeners for %s: %s",
                self._device_name,
                err,
            )

    async def async_handle_w100_button(self, action: str) -> None:
        """Handle W100 button press actions with enhanced logic and debouncing."""
        # Use debounced handler for all button presses
        await self._debounced_button_handler(action)

    async def _handle_toggle_button(self, current_hvac_mode: str) -> None:
        """Handle W100 toggle button (double press) - switches between heat and off modes."""
        # Redirect to advanced version
        await self._handle_toggle_button_advanced(current_hvac_mode)

    async def _handle_plus_button(self, current_hvac_mode: str, current_temp: float, current_state) -> None:
        """Handle W100 plus button - increases temperature in heat mode or fan speed in other modes."""
        # Redirect to advanced version
        await self._handle_plus_button_advanced(current_hvac_mode, current_temp, current_state)

    async def _handle_minus_button(self, current_hvac_mode: str, current_temp: float, current_state) -> None:
        """Handle W100 minus button - decreases temperature in heat mode or fan speed in other modes."""
        # Redirect to advanced version
        await self._handle_minus_button_advanced(current_hvac_mode, current_temp, current_state)

    async def _adjust_fan_speed(self, current_state, increase: bool = True) -> None:
        """Adjust fan speed if the climate entity supports it."""
        try:
            # Check if fan mode is supported
            supported_features = self.supported_features
            if not (supported_features & ClimateEntityFeature.FAN_MODE):
                _LOGGER.debug(
                    "Climate entity %s does not support fan mode control",
                    self._target_climate_entity,
                )
                return
            
            current_fan_mode = current_state.attributes.get("fan_mode")
            fan_modes = current_state.attributes.get("fan_modes", [])
            
            if not fan_modes or not current_fan_mode:
                _LOGGER.debug(
                    "No fan modes available for %s",
                    self._target_climate_entity,
                )
                return
            
            # Try numeric fan speed adjustment first
            try:
                current_speed = int(current_fan_mode)
                if increase:
                    new_speed = min(current_speed + 1, 9)
                else:
                    new_speed = max(current_speed - 1, 1)
                
                new_fan_mode = str(new_speed)
                
                if new_fan_mode in fan_modes and new_fan_mode != current_fan_mode:
                    await self.hass.services.async_call(
                        "climate",
                        "set_fan_mode",
                        {
                            "entity_id": self._target_climate_entity,
                            "fan_mode": new_fan_mode,
                        },
                        blocking=True,
                    )
                    
                    _LOGGER.info(
                        "W100 %s: %s fan speed from %s to %s",
                        self._device_name,
                        "increased" if increase else "decreased",
                        current_fan_mode,
                        new_fan_mode,
                    )
                    return
                    
            except (ValueError, TypeError):
                # Fall back to list-based fan mode adjustment
                pass
            
            # Try list-based fan mode adjustment
            try:
                current_index = fan_modes.index(current_fan_mode)
                if increase and current_index < len(fan_modes) - 1:
                    new_fan_mode = fan_modes[current_index + 1]
                elif not increase and current_index > 0:
                    new_fan_mode = fan_modes[current_index - 1]
                else:
                    _LOGGER.debug(
                        "Cannot %s fan speed for %s (current: %s, at %s)",
                        "increase" if increase else "decrease",
                        self._target_climate_entity,
                        current_fan_mode,
                        "maximum" if increase else "minimum",
                    )
                    return
                
                await self.hass.services.async_call(
                    "climate",
                    "set_fan_mode",
                    {
                        "entity_id": self._target_climate_entity,
                        "fan_mode": new_fan_mode,
                    },
                    blocking=True,
                )
                
                _LOGGER.info(
                    "W100 %s: %s fan mode from %s to %s",
                    self._device_name,
                    "increased" if increase else "decreased",
                    current_fan_mode,
                    new_fan_mode,
                )
                
            except (ValueError, IndexError):
                _LOGGER.debug(
                    "Cannot adjust fan speed for %s (current: %s, available: %s)",
                    self._target_climate_entity,
                    current_fan_mode,
                    fan_modes,
                )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to adjust fan speed for %s: %s",
                self._target_climate_entity,
                err,
            )

    async def _setup_advanced_features(self) -> None:
        """Set up advanced blueprint features."""
        try:
            # Set up stuck heater monitoring
            self.async_on_remove(
                async_track_time_interval(
                    self.hass,
                    self._check_stuck_heater,
                    STUCK_HEATER_CHECK_INTERVAL
                )
            )
            
            # Schedule startup initialization
            self.hass.async_create_task(self._startup_initialization())
            
            _LOGGER.debug("Advanced features set up for W100 device %s", self._device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to set up advanced features for %s: %s", self._device_name, err)

    async def _startup_initialization(self) -> None:
        """Initialize W100 display values on startup."""
        try:
            # Wait for startup delay to allow entities to stabilize
            await asyncio.sleep(STARTUP_INIT_DELAY)
            
            # Initialize W100 display with current climate state
            await self._coordinator.async_sync_w100_display(self._device_name)
            
            # Send beep if configured for startup
            if self._beep_mode in ["Enable Beep", "On-Mode Change"]:
                await self._send_beep_command("startup")
            
            self._startup_initialized = True
            
            _LOGGER.info("W100 %s startup initialization completed", self._device_name)
            
        except Exception as err:
            _LOGGER.error("Failed to initialize W100 %s on startup: %s", self._device_name, err)

    async def _check_stuck_heater(self, now: datetime) -> None:
        """Check if heater is stuck and implement workaround."""
        try:
            target_state = self.target_climate_state
            if not target_state or target_state.state != HVACMode.HEAT:
                # Reset tracking if not in heat mode
                self._last_temp_check = None
                self._last_temp_value = None
                self._heater_start_time = None
                return
            
            current_temp = target_state.attributes.get("current_temperature")
            target_temp = target_state.attributes.get("temperature")
            
            if current_temp is None or target_temp is None:
                return
            
            # Track when heating started
            if self._heater_start_time is None:
                self._heater_start_time = now
                self._last_temp_check = now
                self._last_temp_value = current_temp
                return
            
            # Check if enough time has passed for stuck heater detection
            if now - self._heater_start_time < STUCK_HEATER_TIME_THRESHOLD:
                return
            
            # Check if temperature has changed significantly
            if self._last_temp_value is not None:
                temp_change = abs(current_temp - self._last_temp_value)
                time_since_check = now - self._last_temp_check
                
                # If temperature hasn't changed much in the check interval, heater might be stuck
                if (temp_change < STUCK_HEATER_TEMP_THRESHOLD and 
                    time_since_check >= STUCK_HEATER_CHECK_INTERVAL and
                    current_temp < target_temp - 1.0):  # Still significantly below target
                    
                    _LOGGER.warning(
                        "Stuck heater detected for %s: temp change %.1f°C in %s minutes, implementing workaround",
                        self._device_name,
                        temp_change,
                        time_since_check.total_seconds() / 60
                    )
                    
                    await self._implement_stuck_heater_workaround()
            
            # Update tracking values
            self._last_temp_check = now
            self._last_temp_value = current_temp
            
        except Exception as err:
            _LOGGER.error("Error checking stuck heater for %s: %s", self._device_name, err)

    async def _implement_stuck_heater_workaround(self) -> None:
        """Implement stuck heater workaround by cycling the heater."""
        try:
            # Get the heater entity from generic thermostat config if available
            heater_entity = None
            
            # Try to find heater entity from thermostat config
            thermostat_config = self._config_entry.data.get("generic_thermostat_config", {})
            if thermostat_config:
                heater_entity = thermostat_config.get("heater_switch")
            
            if not heater_entity:
                _LOGGER.warning("Cannot implement stuck heater workaround: heater entity not found")
                return
            
            # Check if heater entity exists
            heater_state = self.hass.states.get(heater_entity)
            if not heater_state:
                _LOGGER.warning("Heater entity %s not found for stuck heater workaround", heater_entity)
                return
            
            _LOGGER.info("Implementing stuck heater workaround for %s: cycling heater %s", 
                        self._device_name, heater_entity)
            
            # Turn off heater for 30 seconds, then let thermostat control it again
            await self.hass.services.async_call(
                "switch", "turn_off",
                {"entity_id": heater_entity},
                blocking=True
            )
            
            # Wait 30 seconds
            await asyncio.sleep(30)
            
            # The generic thermostat will automatically turn it back on if needed
            _LOGGER.info("Stuck heater workaround completed for %s", self._device_name)
            
            # Reset tracking to avoid immediate re-triggering
            self._heater_start_time = datetime.now()
            self._last_temp_check = None
            self._last_temp_value = None
            
        except Exception as err:
            _LOGGER.error("Failed to implement stuck heater workaround for %s: %s", self._device_name, err)

    async def _debounced_button_handler(self, action: str) -> None:
        """Handle button press with debouncing to prevent rapid successive presses."""
        try:
            current_time = datetime.now()
            
            # Check if this is too soon after the last button press
            if (self._last_button_press and 
                (current_time - self._last_button_press).total_seconds() < DEBOUNCE_DELAY):
                _LOGGER.debug(
                    "Debouncing W100 button press %s for %s (too soon after last press)",
                    action, self._device_name
                )
                return
            
            # Cancel any pending debounce task
            if self._debounce_task and not self._debounce_task.done():
                self._debounce_task.cancel()
            
            # Update last button press time
            self._last_button_press = current_time
            
            # Execute the button action
            await self._execute_button_action(action)
            
        except Exception as err:
            _LOGGER.error("Error in debounced button handler for %s: %s", self._device_name, err)

    async def _execute_button_action(self, action: str) -> None:
        """Execute the actual button action logic."""
        try:
            _LOGGER.debug(
                "Executing W100 button action '%s' for device '%s'",
                action,
                self._device_name,
                extra={**self._log_context, "action": action}
            )
            
            current_state = self.target_climate_state
            if not current_state:
                _LOGGER.warning(
                    "Target climate entity '%s' not available for W100 button action",
                    self._target_climate_entity,
                    extra={**self._log_context, "action": action, "target_state": "unavailable"}
                )
                return
            
            current_hvac_mode = current_state.state
            current_temp = current_state.attributes.get("temperature", 21)
            
            action_context = {
                **self._log_context,
                "action": action,
                "current_mode": current_hvac_mode,
                "current_temp": current_temp,
            }
            
            # Handle different button actions based on current mode
            if action == "double":
                await self._handle_toggle_button_advanced(current_hvac_mode)
            elif action == "plus":
                await self._handle_plus_button_advanced(current_hvac_mode, current_temp, current_state)
            elif action == "minus":
                await self._handle_minus_button_advanced(current_hvac_mode, current_temp, current_state)
            else:
                _LOGGER.warning(
                    "Unknown W100 button action '%s' for device '%s'",
                    action,
                    self._device_name,
                    extra=action_context
                )
                return
            
            # Send beep feedback if configured
            if self._beep_mode in ["Enable Beep", "On-Mode Change"]:
                await self._send_beep_command(action)
            
            _LOGGER.info(
                "Successfully executed W100 button action '%s' for device '%s' (mode: %s → %s)",
                action,
                self._device_name,
                current_hvac_mode,
                "toggled" if action == "double" else "adjusted",
                extra=action_context
            )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to execute W100 button action '%s' for device '%s': %s",
                action,
                self._device_name,
                err,
                extra={**self._log_context, "action": action, "error_type": type(err).__name__}
            )

    async def _handle_toggle_button_advanced(self, current_hvac_mode: str) -> None:
        """Handle W100 toggle button with advanced features."""
        try:
            # Toggle between heat and off modes
            if current_hvac_mode == HVACMode.HEAT:
                target_mode = HVACMode.OFF
            else:
                target_mode = HVACMode.HEAT
            
            # Check if target mode is supported
            supported_modes = self.hvac_modes
            if target_mode not in supported_modes:
                _LOGGER.warning(
                    "Target HVAC mode %s not supported by %s (supported: %s)",
                    target_mode, self._target_climate_entity, supported_modes,
                )
                return
            
            await self.async_set_hvac_mode(target_mode)
            
            # Reset stuck heater tracking when mode changes
            if target_mode == HVACMode.HEAT:
                self._heater_start_time = datetime.now()
            else:
                self._heater_start_time = None
            
            self._last_temp_check = None
            self._last_temp_value = None
            
            _LOGGER.info("W100 %s toggle: switched from %s to %s mode", 
                        self._device_name, current_hvac_mode, target_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to handle advanced toggle button for %s: %s", self._device_name, err)

    async def _handle_plus_button_advanced(self, current_hvac_mode: str, current_temp: float, current_state) -> None:
        """Handle W100 plus button with advanced features."""
        try:
            if current_hvac_mode == HVACMode.HEAT:
                # Increase temperature by the step amount
                step = self.target_temperature_step
                new_temp = min(current_temp + step, self.max_temp)
                
                if new_temp == current_temp:
                    _LOGGER.info("W100 %s plus: temperature already at maximum (%s°C)", 
                                self._device_name, current_temp)
                    return
                
                await self.async_set_temperature(temperature=new_temp)
                
                _LOGGER.info("W100 %s plus: increased temperature from %s°C to %s°C",
                            self._device_name, current_temp, new_temp)
                
            elif current_hvac_mode in [HVACMode.FAN_ONLY, HVACMode.COOL]:
                # Try to increase fan speed if supported
                await self._adjust_fan_speed(current_state, increase=True)
                
            else:
                _LOGGER.debug("W100 %s plus button not applicable in mode %s", 
                             self._device_name, current_hvac_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to handle advanced plus button for %s: %s", self._device_name, err)

    async def _handle_minus_button_advanced(self, current_hvac_mode: str, current_temp: float, current_state) -> None:
        """Handle W100 minus button with advanced features."""
        try:
            if current_hvac_mode == HVACMode.HEAT:
                # Decrease temperature by the step amount
                step = self.target_temperature_step
                new_temp = max(current_temp - step, self.min_temp)
                
                if new_temp == current_temp:
                    _LOGGER.info("W100 %s minus: temperature already at minimum (%s°C)",
                                self._device_name, current_temp)
                    return
                
                await self.async_set_temperature(temperature=new_temp)
                
                _LOGGER.info("W100 %s minus: decreased temperature from %s°C to %s°C",
                            self._device_name, current_temp, new_temp)
                
            elif current_hvac_mode in [HVACMode.FAN_ONLY, HVACMode.COOL]:
                # Try to decrease fan speed if supported
                await self._adjust_fan_speed(current_state, increase=False)
                
            else:
                _LOGGER.debug("W100 %s minus button not applicable in mode %s",
                             self._device_name, current_hvac_mode)
            
        except Exception as err:
            _LOGGER.error("Failed to handle advanced minus button for %s: %s", self._device_name, err)

    async def _send_beep_command(self, action: str) -> None:
        """Send beep command to W100 device based on beep mode configuration."""
        try:
            if self._beep_mode == "Disable Beep":
                return
            
            # Determine if beep should be sent based on mode and action
            should_beep = False
            
            if self._beep_mode == "Enable Beep":
                should_beep = True
            elif self._beep_mode == "On-Mode Change":
                # Only beep on mode changes and temperature changes
                should_beep = action in ["double", "plus", "minus", "startup"]
            
            if not should_beep:
                return
            
            # Send beep command via MQTT
            beep_topic = f"zigbee2mqtt/{self._device_name}/set"
            beep_payload = {"beep": True}
            
            await self.hass.services.async_call(
                "mqtt", "publish",
                {
                    "topic": beep_topic,
                    "payload": str(beep_payload).replace("'", '"'),
                },
                blocking=False
            )
            
            _LOGGER.debug("Sent beep command to W100 %s for action %s", self._device_name, action)
            
        except Exception as err:
            _LOGGER.error("Failed to send beep command to W100 %s: %s", self._device_name, err)

    async def async_handle_w100_button(self, action: str) -> None:
        """Handle W100 button press actions with enhanced logic and debouncing."""
        # Use debounced handler for all button presses
        await self._debounced_button_handler(action)

    async def async_handle_w100_action(self, action: str) -> None:
        """Handle W100 button press actions (legacy method - redirects to new method)."""
        await self.async_handle_w100_button(action)