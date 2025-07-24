"""Device trigger platform for W100 Smart Control integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# W100 button action types
TRIGGER_TYPE_BUTTON_TOGGLE = "button_toggle"
TRIGGER_TYPE_BUTTON_PLUS = "button_plus"
TRIGGER_TYPE_BUTTON_MINUS = "button_minus"

# All supported trigger types
TRIGGER_TYPES = {
    TRIGGER_TYPE_BUTTON_TOGGLE,
    TRIGGER_TYPE_BUTTON_PLUS,
    TRIGGER_TYPE_BUTTON_MINUS,
}

# Trigger schema
TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for W100 devices."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    
    if not device:
        return []
    
    # Check if this is a W100 control device (logical device created by our integration)
    w100_control_identifier = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN and identifier[1].startswith("w100_control_"):
            w100_control_identifier = identifier[1]
            break
    
    if not w100_control_identifier:
        return []
    
    # Extract device name from identifier (w100_control_device_name -> device_name)
    device_name = w100_control_identifier.replace("w100_control_", "")
    
    # Return available triggers for this W100 device
    triggers = []
    
    triggers.append({
        CONF_PLATFORM: "device",
        CONF_DOMAIN: DOMAIN,
        CONF_DEVICE_ID: device_id,
        CONF_TYPE: TRIGGER_TYPE_BUTTON_TOGGLE,
        "subtype": device_name,
        "metadata": {
            "name": f"W100 {device_name.replace('_', ' ').title()} Toggle Button",
            "description": "Triggered when the center button is double-pressed (toggle heat/off)",
        },
    })
    
    triggers.append({
        CONF_PLATFORM: "device",
        CONF_DOMAIN: DOMAIN,
        CONF_DEVICE_ID: device_id,
        CONF_TYPE: TRIGGER_TYPE_BUTTON_PLUS,
        "subtype": device_name,
        "metadata": {
            "name": f"W100 {device_name.replace('_', ' ').title()} Plus Button",
            "description": "Triggered when the plus button is pressed (increase temp/fan speed)",
        },
    })
    
    triggers.append({
        CONF_PLATFORM: "device",
        CONF_DOMAIN: DOMAIN,
        CONF_DEVICE_ID: device_id,
        CONF_TYPE: TRIGGER_TYPE_BUTTON_MINUS,
        "subtype": device_name,
        "metadata": {
            "name": f"W100 {device_name.replace('_', ' ').title()} Minus Button",
            "description": "Triggered when the minus button is pressed (decrease temp/fan speed)",
        },
    })
    
    _LOGGER.debug(
        "Found %d triggers for W100 device %s (device_id: %s)",
        len(triggers),
        device_name,
        device_id,
    )
    
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger for W100 button actions."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(config[CONF_DEVICE_ID])
    
    if not device:
        _LOGGER.error("Device not found: %s", config[CONF_DEVICE_ID])
        return lambda: None
    
    # Extract device name from device identifiers
    device_name = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN and identifier[1].startswith("w100_control_"):
            device_name = identifier[1].replace("w100_control_", "")
            break
    
    if not device_name:
        _LOGGER.error("W100 device name not found for device: %s", config[CONF_DEVICE_ID])
        return lambda: None
    
    trigger_type = config[CONF_TYPE]
    
    # Map trigger types to W100 action events
    action_map = {
        TRIGGER_TYPE_BUTTON_TOGGLE: "toggle",
        TRIGGER_TYPE_BUTTON_PLUS: "plus",
        TRIGGER_TYPE_BUTTON_MINUS: "minus",
    }
    
    w100_action = action_map.get(trigger_type)
    if not w100_action:
        _LOGGER.error("Unknown trigger type: %s", trigger_type)
        return lambda: None
    
    # Create event trigger configuration
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: f"{DOMAIN}_button_action",
            event_trigger.CONF_EVENT_DATA: {
                "device_name": device_name,
                "action": w100_action,
            },
        }
    )
    
    _LOGGER.debug(
        "Attaching W100 trigger: device=%s, type=%s, action=%s",
        device_name,
        trigger_type,
        w100_action,
    )
    
    # Attach the event trigger
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """List trigger capabilities for W100 devices."""
    # No additional capabilities needed for W100 button triggers
    return {}


def async_validate_trigger_config(hass: HomeAssistant, config: ConfigType) -> ConfigType:
    """Validate trigger configuration."""
    return TRIGGER_SCHEMA(config)