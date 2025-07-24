"""Switch platform for W100 Smart Control integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    CONF_W100_DEVICE_NAME,
    CONF_BEEP_MODE,
    DEFAULT_BEEP_MODE,
)
from .coordinator import W100Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up W100 switch entities from a config entry."""
    coordinator: W100Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    device_name = config_entry.data.get(CONF_W100_DEVICE_NAME)
    if not device_name:
        _LOGGER.error("No W100 device name found in config entry")
        return
    
    switches = []
    
    # Create beep control switch
    switches.append(W100BeepControlSwitch(coordinator, config_entry, device_name))
    
    # Create advanced feature switches
    switches.append(W100StuckHeaterWorkaroundSwitch(coordinator, config_entry, device_name))
    switches.append(W100DisplaySyncSwitch(coordinator, config_entry, device_name))
    switches.append(W100DebounceSwitch(coordinator, config_entry, device_name))
    
    async_add_entities(switches)
    _LOGGER.info(
        "Added %d switch entities for W100 device %s",
        len(switches),
        device_name,
    )


class W100BaseSwitch(SwitchEntity, RestoreEntity):
    """Base class for W100 switch entities."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
        switch_type: str,
        default_state: bool = True,
    ) -> None:
        """Initialize the W100 switch."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._device_name = device_name
        self._switch_type = switch_type
        self._default_state = default_state
        self._is_on = default_state
        
        # Generate unique entity ID
        self._attr_unique_id = f"{DOMAIN}_{device_name}_{switch_type}"
        self._attr_name = f"W100 {device_name.replace('_', ' ').title()} {switch_type.replace('_', ' ').title()}"
        
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
    
    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on
    
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == "on"
        else:
            self._is_on = self._default_state
        
        # Add coordinator listener
        self._coordinator.async_add_listener(self.async_write_ha_state)
        
        # Register this switch entity with the coordinator for proper registry integration
        await self._coordinator.async_register_switch_entity(
            self._device_name, self.entity_id, self._switch_type
        )
        
        # Apply initial state to coordinator
        await self._async_apply_state()
    
    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        self._coordinator.async_remove_listener(self.async_write_ha_state)
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._is_on = True
        await self._async_apply_state()
        if self.hass is not None:
            self.async_write_ha_state()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._is_on = False
        await self._async_apply_state()
        if self.hass is not None:
            self.async_write_ha_state()
    
    async def _async_apply_state(self) -> None:
        """Apply the switch state to the coordinator/integration."""
        # Override in subclasses
        pass
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "w100_device_name": self._device_name,
            "integration_version": "1.0.0",
            "switch_type": self._switch_type,
            "default_state": self._default_state,
        }


class W100BeepControlSwitch(W100BaseSwitch):
    """Switch to control W100 beep functionality."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the beep control switch."""
        # Default to enabled based on beep mode configuration
        beep_mode = config_entry.data.get(CONF_BEEP_MODE, DEFAULT_BEEP_MODE)
        default_enabled = beep_mode != "Disable Beep"
        
        super().__init__(coordinator, config_entry, device_name, "beep_control", default_enabled)
        
        self._attr_icon = "mdi:volume-high"
        self._beep_mode = beep_mode
    
    async def _async_apply_state(self) -> None:
        """Apply beep control state to the coordinator."""
        try:
            # Update coordinator's beep settings for this device
            device_config = self._coordinator._device_configs.get(self._device_name, {})
            
            if self._is_on:
                # Enable beep - use configured beep mode or default
                device_config[CONF_BEEP_MODE] = self._beep_mode if self._beep_mode != "Disable Beep" else "On-Mode Change"
            else:
                # Disable beep
                device_config[CONF_BEEP_MODE] = "Disable Beep"
            
            # Update coordinator configuration
            self._coordinator._device_configs[self._device_name] = device_config
            
            # Save configuration
            await self._coordinator._async_save_device_data()
            
            _LOGGER.debug(
                "Applied beep control state %s for device %s (mode: %s)",
                "on" if self._is_on else "off",
                self._device_name,
                device_config.get(CONF_BEEP_MODE)
            )
            
        except Exception as err:
            _LOGGER.error("Failed to apply beep control state for %s: %s", self._device_name, err)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = super().extra_state_attributes
        attributes.update({
            "beep_mode": self._beep_mode,
            "current_beep_setting": "Disable Beep" if not self._is_on else self._beep_mode,
            "description": "Controls W100 beep functionality for button presses and mode changes",
        })
        return attributes


class W100StuckHeaterWorkaroundSwitch(W100BaseSwitch):
    """Switch to enable/disable stuck heater workaround feature."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the stuck heater workaround switch."""
        super().__init__(coordinator, config_entry, device_name, "stuck_heater_workaround", True)
        
        self._attr_icon = "mdi:wrench"
        self._attr_entity_category = "config"
    
    async def _async_apply_state(self) -> None:
        """Apply stuck heater workaround state to the coordinator."""
        try:
            # Update coordinator's advanced feature settings
            device_config = self._coordinator._device_configs.get(self._device_name, {})
            device_config["stuck_heater_workaround_enabled"] = self._is_on
            
            self._coordinator._device_configs[self._device_name] = device_config
            await self._coordinator._async_save_device_data()
            
            _LOGGER.debug(
                "Applied stuck heater workaround state %s for device %s",
                "enabled" if self._is_on else "disabled",
                self._device_name
            )
            
        except Exception as err:
            _LOGGER.error("Failed to apply stuck heater workaround state for %s: %s", self._device_name, err)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = super().extra_state_attributes
        attributes.update({
            "feature": "stuck_heater_workaround",
            "description": "Automatically resets heater when temperature gets stuck",
            "check_interval_minutes": 5,
            "temperature_threshold_celsius": 0.5,
            "time_threshold_minutes": 15,
        })
        return attributes


class W100DisplaySyncSwitch(W100BaseSwitch):
    """Switch to enable/disable W100 display synchronization."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the display sync switch."""
        super().__init__(coordinator, config_entry, device_name, "display_sync", True)
        
        self._attr_icon = "mdi:monitor-dashboard"
        self._attr_entity_category = "config"
    
    async def _async_apply_state(self) -> None:
        """Apply display sync state to the coordinator."""
        try:
            # Update coordinator's display sync settings
            device_config = self._coordinator._device_configs.get(self._device_name, {})
            device_config["display_sync_enabled"] = self._is_on
            
            self._coordinator._device_configs[self._device_name] = device_config
            await self._coordinator._async_save_device_data()
            
            _LOGGER.debug(
                "Applied display sync state %s for device %s",
                "enabled" if self._is_on else "disabled",
                self._device_name
            )
            
        except Exception as err:
            _LOGGER.error("Failed to apply display sync state for %s: %s", self._device_name, err)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = super().extra_state_attributes
        attributes.update({
            "feature": "display_synchronization",
            "description": "Synchronizes W100 display with climate entity state",
            "sync_modes": ["temperature", "fan_speed", "humidity"],
            "update_delay_seconds": 2,
        })
        return attributes


class W100DebounceSwitch(W100BaseSwitch):
    """Switch to enable/disable button press debouncing."""
    
    def __init__(
        self,
        coordinator: W100Coordinator,
        config_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the debounce switch."""
        super().__init__(coordinator, config_entry, device_name, "debounce", True)
        
        self._attr_icon = "mdi:timer-outline"
        self._attr_entity_category = "config"
    
    async def _async_apply_state(self) -> None:
        """Apply debounce state to the coordinator."""
        try:
            # Update coordinator's debounce settings
            device_config = self._coordinator._device_configs.get(self._device_name, {})
            device_config["debounce_enabled"] = self._is_on
            
            self._coordinator._device_configs[self._device_name] = device_config
            await self._coordinator._async_save_device_data()
            
            _LOGGER.debug(
                "Applied debounce state %s for device %s",
                "enabled" if self._is_on else "disabled",
                self._device_name
            )
            
        except Exception as err:
            _LOGGER.error("Failed to apply debounce state for %s: %s", self._device_name, err)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = super().extra_state_attributes
        attributes.update({
            "feature": "button_debouncing",
            "description": "Prevents rapid successive button presses from causing issues",
            "debounce_delay_seconds": 2.0,
            "toggle_debounce_seconds": 1.0,
        })
        return attributes