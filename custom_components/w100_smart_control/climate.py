"""Climate platform for W100 Smart Control integration."""
from __future__ import annotations

import logging
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
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)

from .const import DOMAIN, CONF_W100_DEVICE_NAME, CONF_EXISTING_CLIMATE_ENTITY
from .coordinator import W100Coordinator

_LOGGER = logging.getLogger(__name__)


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
        
        # Set up device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_name)},
            name=f"W100 {device_name.replace('_', ' ').title()}",
            manufacturer="Aqara",
            model="W100",
            sw_version="1.0.0",
        )

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
        """Return additional state attributes."""
        attributes = {}
        
        # Add W100-specific attributes
        attributes["w100_device_name"] = self._device_name
        attributes["target_climate_entity"] = self._target_climate_entity
        
        # Add device state from coordinator if available
        device_state = self._coordinator.data.get("device_states", {}).get(self._device_name, {})
        if device_state:
            attributes["w100_last_action"] = device_state.get("last_action")
            attributes["w100_display_mode"] = device_state.get("display_mode")
        
        return attributes

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        try:
            # Call the target climate entity's set_hvac_mode service
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": self._target_climate_entity,
                    "hvac_mode": hvac_mode,
                },
                blocking=True,
            )
            
            # Update W100 display after mode change
            await self._coordinator.async_sync_w100_display(self._device_name)
            
            _LOGGER.debug(
                "Set HVAC mode to %s for %s via target entity %s",
                hvac_mode,
                self._device_name,
                self._target_climate_entity,
            )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to set HVAC mode %s for %s: %s",
                hvac_mode,
                self._device_name,
                err,
            )
            raise

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        try:
            temperature = kwargs.get(ATTR_TEMPERATURE)
            if temperature is None:
                _LOGGER.warning("No temperature provided in set_temperature call")
                return
            
            # Call the target climate entity's set_temperature service
            service_data = {
                "entity_id": self._target_climate_entity,
                ATTR_TEMPERATURE: temperature,
            }
            
            # Include HVAC mode if provided
            hvac_mode = kwargs.get("hvac_mode")
            if hvac_mode:
                service_data["hvac_mode"] = hvac_mode
            
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                service_data,
                blocking=True,
            )
            
            # Update W100 display after temperature change
            await self._coordinator.async_sync_w100_display(self._device_name)
            
            _LOGGER.debug(
                "Set temperature to %s°C for %s via target entity %s",
                temperature,
                self._device_name,
                self._target_climate_entity,
            )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to set temperature for %s: %s",
                self._device_name,
                err,
            )
            raise

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

    async def _setup_w100_listeners(self) -> None:
        """Set up MQTT listeners for W100 button presses."""
        try:
            # Register this climate entity with the coordinator for W100 events
            await self._coordinator.async_register_w100_climate_entity(
                self._device_name, self.entity_id
            )
            
            _LOGGER.debug(
                "Set up W100 listeners for device %s, entity %s",
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
        """Handle W100 button press actions with enhanced logic."""
        try:
            _LOGGER.debug(
                "Handling W100 button action %s for device %s",
                action,
                self._device_name,
            )
            
            current_state = self.target_climate_state
            if not current_state:
                _LOGGER.warning(
                    "Target climate entity %s not available for W100 button action",
                    self._target_climate_entity,
                )
                return
            
            current_hvac_mode = current_state.state
            current_temp = current_state.attributes.get("temperature", 21)
            
            # Handle different button actions based on current mode
            if action == "double":
                await self._handle_toggle_button(current_hvac_mode)
            elif action == "plus":
                await self._handle_plus_button(current_hvac_mode, current_temp, current_state)
            elif action == "minus":
                await self._handle_minus_button(current_hvac_mode, current_temp, current_state)
            else:
                _LOGGER.warning(
                    "Unknown W100 button action %s for device %s",
                    action,
                    self._device_name,
                )
                return
            
            _LOGGER.debug(
                "Completed W100 button action %s for device %s",
                action,
                self._device_name,
            )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to handle W100 button action %s for %s: %s",
                action,
                self._device_name,
                err,
            )

    async def _handle_toggle_button(self, current_hvac_mode: str) -> None:
        """Handle W100 toggle button (double press) - switches between heat and off modes."""
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
                    target_mode,
                    self._target_climate_entity,
                    supported_modes,
                )
                return
            
            await self.async_set_hvac_mode(target_mode)
            
            _LOGGER.info(
                "W100 %s toggle: switched from %s to %s mode",
                self._device_name,
                current_hvac_mode,
                target_mode,
            )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to handle toggle button for %s: %s",
                self._device_name,
                err,
            )

    async def _handle_plus_button(self, current_hvac_mode: str, current_temp: float, current_state) -> None:
        """Handle W100 plus button - increases temperature in heat mode or fan speed in other modes."""
        try:
            if current_hvac_mode == HVACMode.HEAT:
                # Increase temperature by the step amount
                step = self.target_temperature_step
                new_temp = min(current_temp + step, self.max_temp)
                
                if new_temp == current_temp:
                    _LOGGER.info(
                        "W100 %s plus: temperature already at maximum (%s°C)",
                        self._device_name,
                        current_temp,
                    )
                    return
                
                await self.async_set_temperature(temperature=new_temp)
                
                _LOGGER.info(
                    "W100 %s plus: increased temperature from %s°C to %s°C",
                    self._device_name,
                    current_temp,
                    new_temp,
                )
                
            elif current_hvac_mode in [HVACMode.FAN_ONLY, HVACMode.COOL]:
                # Try to increase fan speed if supported
                await self._adjust_fan_speed(current_state, increase=True)
                
            else:
                _LOGGER.debug(
                    "W100 %s plus button not applicable in mode %s",
                    self._device_name,
                    current_hvac_mode,
                )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to handle plus button for %s: %s",
                self._device_name,
                err,
            )

    async def _handle_minus_button(self, current_hvac_mode: str, current_temp: float, current_state) -> None:
        """Handle W100 minus button - decreases temperature in heat mode or fan speed in other modes."""
        try:
            if current_hvac_mode == HVACMode.HEAT:
                # Decrease temperature by the step amount
                step = self.target_temperature_step
                new_temp = max(current_temp - step, self.min_temp)
                
                if new_temp == current_temp:
                    _LOGGER.info(
                        "W100 %s minus: temperature already at minimum (%s°C)",
                        self._device_name,
                        current_temp,
                    )
                    return
                
                await self.async_set_temperature(temperature=new_temp)
                
                _LOGGER.info(
                    "W100 %s minus: decreased temperature from %s°C to %s°C",
                    self._device_name,
                    current_temp,
                    new_temp,
                )
                
            elif current_hvac_mode in [HVACMode.FAN_ONLY, HVACMode.COOL]:
                # Try to decrease fan speed if supported
                await self._adjust_fan_speed(current_state, increase=False)
                
            else:
                _LOGGER.debug(
                    "W100 %s minus button not applicable in mode %s",
                    self._device_name,
                    current_hvac_mode,
                )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to handle minus button for %s: %s",
                self._device_name,
                err,
            )

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

    async def async_handle_w100_action(self, action: str) -> None:
        """Handle W100 button press actions (legacy method - redirects to new method)."""
        await self.async_handle_w100_button(action)