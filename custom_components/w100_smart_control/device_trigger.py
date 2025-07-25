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

# Trigger schema with comprehensive validation
TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Optional("subtype"): cv.string,  # Device name for filtering
        vol.Optional("metadata"): dict,  # Additional metadata for UI
    }
)

# Event data schema for validation
EVENT_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("device_name"): cv.string,
        vol.Required("action"): vol.In(["toggle", "plus", "minus"]),
        vol.Required("timestamp"): cv.string,
        vol.Required("integration"): cv.string,
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
    # Return capabilities for automation UI
    return {
        "extra_fields": vol.Schema(
            {
                vol.Optional("description"): cv.string,
                vol.Optional("enabled", default=True): cv.boolean,
            }
        )
    }


def async_validate_trigger_config(hass: HomeAssistant, config: ConfigType) -> ConfigType:
    """Validate trigger configuration."""
    return TRIGGER_SCHEMA(config)


async def async_register_automation_triggers(hass: HomeAssistant) -> None:
    """Register W100 triggers with Home Assistant automation system."""
    try:
        # Get device registry to find all W100 control devices
        device_registry = dr.async_get(hass)
        
        w100_devices = []
        for device in device_registry.devices.values():
            for identifier in device.identifiers:
                if identifier[0] == DOMAIN and identifier[1].startswith("w100_control_"):
                    w100_devices.append(device)
                    break
        
        _LOGGER.info(
            "Registered %d W100 devices for automation triggers",
            len(w100_devices)
        )
        
        # Log available trigger types for documentation
        for device in w100_devices:
            device_name = None
            for identifier in device.identifiers:
                if identifier[0] == DOMAIN and identifier[1].startswith("w100_control_"):
                    device_name = identifier[1].replace("w100_control_", "")
                    break
            
            if device_name:
                _LOGGER.debug(
                    "W100 device %s (ID: %s) supports triggers: %s",
                    device_name,
                    device.id,
                    ", ".join(TRIGGER_TYPES)
                )
        
    except Exception as err:
        _LOGGER.error("Failed to register automation triggers: %s", err)


def get_trigger_documentation() -> dict[str, Any]:
    """Get comprehensive trigger documentation for automation system."""
    return {
        "triggers": {
            TRIGGER_TYPE_BUTTON_TOGGLE: {
                "name": "W100 Toggle Button",
                "description": "Triggered when the center button is double-pressed (toggle heat/off)",
                "event_type": f"{DOMAIN}_button_action",
                "event_data": {
                    "action": "toggle",
                    "device_name": "string",
                    "timestamp": "ISO datetime string",
                    "integration": DOMAIN,
                },
                "example_automation": {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "[device_id]",
                        "type": TRIGGER_TYPE_BUTTON_TOGGLE,
                    },
                    "action": {
                        "service": "light.toggle",
                        "target": {"entity_id": "light.living_room"},
                    },
                },
            },
            TRIGGER_TYPE_BUTTON_PLUS: {
                "name": "W100 Plus Button",
                "description": "Triggered when the plus button is pressed (increase temp/fan speed)",
                "event_type": f"{DOMAIN}_button_action",
                "event_data": {
                    "action": "plus",
                    "device_name": "string",
                    "timestamp": "ISO datetime string",
                    "integration": DOMAIN,
                },
                "example_automation": {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "[device_id]",
                        "type": TRIGGER_TYPE_BUTTON_PLUS,
                    },
                    "action": {
                        "service": "light.turn_on",
                        "target": {"entity_id": "light.living_room"},
                        "data": {"brightness_step_pct": 10},
                    },
                },
            },
            TRIGGER_TYPE_BUTTON_MINUS: {
                "name": "W100 Minus Button",
                "description": "Triggered when the minus button is pressed (decrease temp/fan speed)",
                "event_type": f"{DOMAIN}_button_action",
                "event_data": {
                    "action": "minus",
                    "device_name": "string",
                    "timestamp": "ISO datetime string",
                    "integration": DOMAIN,
                },
                "example_automation": {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "[device_id]",
                        "type": TRIGGER_TYPE_BUTTON_MINUS,
                    },
                    "action": {
                        "service": "light.turn_on",
                        "target": {"entity_id": "light.living_room"},
                        "data": {"brightness_step_pct": -10},
                    },
                },
            },
        },
        "event_schema": EVENT_DATA_SCHEMA,
        "supported_platforms": ["device", "event"],
        "integration_domain": DOMAIN,
    }