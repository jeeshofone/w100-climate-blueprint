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

    async def async_handle_w100_action(self, action: str) -> None:
        """Handle W100 button press actions."""
        try:
            _LOGGER.debug(
                "Handling W100 action %s for device %s",
                action,
                self._device_name,
            )
            
            current_state = self.target_climate_state
            if not current_state:
                _LOGGER.warning(
                    "Target climate entity %s not available for W100 action",
                    self._target_climate_entity,
                )
                return
            
            current_hvac_mode = current_state.state
            current_temp = current_state.attributes.get("temperature", 21)
            
            if action == "double":
                # Toggle between heat and off modes
                if current_hvac_mode == HVACMode.HEAT:
                    await self.async_set_hvac_mode(HVACMode.OFF)
                else:
                    await self.async_set_hvac_mode(HVACMode.HEAT)
                    
            elif action == "plus":
                # Increase temperature when in heat mode
                if current_hvac_mode == HVACMode.HEAT:
                    new_temp = min(current_temp + self.target_temperature_step, self.max_temp)
                    await self.async_set_temperature(temperature=new_temp)
                    
            elif action == "minus":
                # Decrease temperature when in heat mode
                if current_hvac_mode == HVACMode.HEAT:
                    new_temp = max(current_temp - self.target_temperature_step, self.min_temp)
                    await self.async_set_temperature(temperature=new_temp)
            
            _LOGGER.debug(
                "Completed W100 action %s for device %s",
                action,
                self._device_name,
            )
            
        except Exception as err:
            _LOGGER.error(
                "Failed to handle W100 action %s for %s: %s",
                action,
                self._device_name,
                err,
            )