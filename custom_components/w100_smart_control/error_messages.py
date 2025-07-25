"""User-friendly error messages and troubleshooting guidance for W100 Smart Control."""
from __future__ import annotations

from typing import Any

try:
    from .exceptions import W100ErrorCodes
except ImportError:
    # Handle case when running as standalone module for testing
    try:
        from exceptions import W100ErrorCodes
    except ImportError:
        # Define error codes locally for testing
        class W100ErrorCodes:
            DEVICE_NOT_FOUND = "W100_DEVICE_NOT_FOUND"
            DEVICE_UNAVAILABLE = "W100_DEVICE_UNAVAILABLE"
            DEVICE_COMMUNICATION_FAILED = "W100_DEVICE_COMM_FAILED"
            MQTT_CONNECTION_FAILED = "W100_MQTT_CONN_FAILED"
            MQTT_PUBLISH_FAILED = "W100_MQTT_PUBLISH_FAILED"
            MQTT_SUBSCRIBE_FAILED = "W100_MQTT_SUBSCRIBE_FAILED"
            ENTITY_NOT_FOUND = "W100_ENTITY_NOT_FOUND"
            ENTITY_UNAVAILABLE = "W100_ENTITY_UNAVAILABLE"
            ENTITY_OPERATION_FAILED = "W100_ENTITY_OP_FAILED"
            CONFIG_INVALID = "W100_CONFIG_INVALID"
            CONFIG_VALIDATION_FAILED = "W100_CONFIG_VALIDATION_FAILED"
            THERMOSTAT_CREATE_FAILED = "W100_THERMOSTAT_CREATE_FAILED"
            THERMOSTAT_REMOVE_FAILED = "W100_THERMOSTAT_REMOVE_FAILED"
            COORDINATOR_SETUP_FAILED = "W100_COORDINATOR_SETUP_FAILED"
            INTEGRATION_SETUP_FAILED = "W100_INTEGRATION_SETUP_FAILED"


class W100ErrorMessages:
    """User-friendly error messages and troubleshooting guidance."""
    
    # Device-related error messages
    DEVICE_ERRORS = {
        W100ErrorCodes.DEVICE_NOT_FOUND: {
            "title": "W100 Device Not Found",
            "message": "The W100 device could not be found in your Zigbee2MQTT setup.",
            "guidance": [
                "1. Verify the W100 device is paired with Zigbee2MQTT",
                "2. Check that the device name matches exactly (case-sensitive)",
                "3. Ensure Zigbee2MQTT is running and accessible",
                "4. Try refreshing the device list in the configuration"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#device-setup"
        },
        W100ErrorCodes.DEVICE_UNAVAILABLE: {
            "title": "W100 Device Unavailable",
            "message": "The W100 device is currently unavailable or not responding.",
            "guidance": [
                "1. Check if the device has power and is within Zigbee range",
                "2. Verify Zigbee2MQTT can communicate with the device",
                "3. Try restarting the W100 device by removing and reinserting batteries",
                "4. Check Zigbee2MQTT logs for connectivity issues"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#troubleshooting"
        },
        W100ErrorCodes.DEVICE_COMMUNICATION_FAILED: {
            "title": "Communication Failed",
            "message": "Failed to communicate with the W100 device.",
            "guidance": [
                "1. Ensure Zigbee2MQTT is running and responsive",
                "2. Check MQTT broker connectivity",
                "3. Verify the device is still paired and responsive",
                "4. Try restarting Home Assistant and Zigbee2MQTT"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#mqtt-setup"
        }
    }
    
    # MQTT-related error messages
    MQTT_ERRORS = {
        W100ErrorCodes.MQTT_CONNECTION_FAILED: {
            "title": "MQTT Connection Failed",
            "message": "Unable to connect to the MQTT broker for W100 communication.",
            "guidance": [
                "1. Verify MQTT integration is installed and configured in Home Assistant",
                "2. Check MQTT broker is running and accessible",
                "3. Ensure Zigbee2MQTT is connected to the same MQTT broker",
                "4. Verify MQTT credentials and connection settings"
            ],
            "documentation": "https://www.home-assistant.io/integrations/mqtt/"
        },
        W100ErrorCodes.MQTT_PUBLISH_FAILED: {
            "title": "MQTT Publish Failed",
            "message": "Failed to send commands to the W100 device via MQTT.",
            "guidance": [
                "1. Check MQTT broker connectivity and permissions",
                "2. Verify Zigbee2MQTT is receiving messages",
                "3. Ensure the W100 device topic is correct",
                "4. Check for MQTT broker resource limits"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#mqtt-troubleshooting"
        },
        W100ErrorCodes.MQTT_SUBSCRIBE_FAILED: {
            "title": "MQTT Subscription Failed",
            "message": "Failed to subscribe to W100 device messages.",
            "guidance": [
                "1. Verify MQTT integration has proper permissions",
                "2. Check if the MQTT topic exists and is accessible",
                "3. Ensure Zigbee2MQTT is publishing to the expected topics",
                "4. Try restarting the integration"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#mqtt-topics"
        }
    }
    
    # Entity-related error messages
    ENTITY_ERRORS = {
        W100ErrorCodes.ENTITY_NOT_FOUND: {
            "title": "Climate Entity Not Found",
            "message": "The target climate entity could not be found.",
            "guidance": [
                "1. Verify the climate entity exists and is available",
                "2. Check the entity ID is spelled correctly",
                "3. Ensure the climate entity is not disabled",
                "4. Try selecting a different climate entity"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#climate-entity-setup"
        },
        W100ErrorCodes.ENTITY_UNAVAILABLE: {
            "title": "Climate Entity Unavailable",
            "message": "The target climate entity is currently unavailable.",
            "guidance": [
                "1. Check if the climate entity's underlying device is working",
                "2. Verify the climate integration is functioning properly",
                "3. Try restarting the climate entity's integration",
                "4. Check Home Assistant logs for related errors"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#entity-troubleshooting"
        },
        W100ErrorCodes.ENTITY_OPERATION_FAILED: {
            "title": "Climate Operation Failed",
            "message": "Failed to control the climate entity.",
            "guidance": [
                "1. Verify the climate entity supports the requested operation",
                "2. Check if the climate entity is in a controllable state",
                "3. Ensure you have permission to control the entity",
                "4. Try controlling the entity manually to test functionality"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#climate-control"
        }
    }
    
    # Configuration error messages
    CONFIG_ERRORS = {
        W100ErrorCodes.CONFIG_INVALID: {
            "title": "Invalid Configuration",
            "message": "The integration configuration contains invalid settings.",
            "guidance": [
                "1. Review all configuration settings for typos or invalid values",
                "2. Ensure temperature ranges are logical (min < max)",
                "3. Verify entity IDs exist and are accessible",
                "4. Check that all required fields are filled"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#configuration"
        },
        W100ErrorCodes.CONFIG_VALIDATION_FAILED: {
            "title": "Configuration Validation Failed",
            "message": "The configuration could not be validated.",
            "guidance": [
                "1. Check that all referenced entities exist",
                "2. Verify temperature sensors provide numeric values",
                "3. Ensure heater switches are controllable",
                "4. Validate all entity IDs are correct"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#validation"
        }
    }
    
    # Thermostat error messages
    THERMOSTAT_ERRORS = {
        W100ErrorCodes.THERMOSTAT_CREATE_FAILED: {
            "title": "Thermostat Creation Failed",
            "message": "Failed to create the generic thermostat entity.",
            "guidance": [
                "1. Verify the heater switch entity exists and is controllable",
                "2. Check the temperature sensor provides valid readings",
                "3. Ensure entity IDs don't conflict with existing entities",
                "4. Try using different entity names"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#thermostat-setup"
        },
        W100ErrorCodes.THERMOSTAT_REMOVE_FAILED: {
            "title": "Thermostat Removal Failed",
            "message": "Failed to remove the generic thermostat entity.",
            "guidance": [
                "1. Try removing the entity manually from the entity registry",
                "2. Restart Home Assistant and try again",
                "3. Check for automations or scripts using the thermostat",
                "4. Remove the integration and reconfigure if necessary"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#troubleshooting"
        }
    }
    
    # Critical error messages
    CRITICAL_ERRORS = {
        W100ErrorCodes.COORDINATOR_SETUP_FAILED: {
            "title": "Integration Setup Failed",
            "message": "The W100 Smart Control integration failed to initialize.",
            "guidance": [
                "1. Check Home Assistant logs for detailed error information",
                "2. Verify all dependencies (MQTT, Zigbee2MQTT) are working",
                "3. Try removing and re-adding the integration",
                "4. Ensure you have the latest version of the integration"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#installation"
        },
        W100ErrorCodes.INTEGRATION_SETUP_FAILED: {
            "title": "Integration Initialization Failed",
            "message": "The integration could not be set up properly.",
            "guidance": [
                "1. Restart Home Assistant completely",
                "2. Check for conflicting integrations or custom components",
                "3. Verify Home Assistant version compatibility",
                "4. Review the integration logs for specific errors"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#compatibility"
        }
    }
    
    @classmethod
    def get_error_info(cls, error_code: str) -> dict[str, Any]:
        """Get user-friendly error information for an error code."""
        # Search through all error categories
        for error_category in [
            cls.DEVICE_ERRORS,
            cls.MQTT_ERRORS,
            cls.ENTITY_ERRORS,
            cls.CONFIG_ERRORS,
            cls.THERMOSTAT_ERRORS,
            cls.CRITICAL_ERRORS,
        ]:
            if error_code in error_category:
                return error_category[error_code]
        
        # Default error info for unknown codes
        return {
            "title": "Unknown Error",
            "message": f"An unexpected error occurred (Code: {error_code})",
            "guidance": [
                "1. Check the Home Assistant logs for more details",
                "2. Try restarting the integration",
                "3. Report this issue if it persists",
                "4. Include the error code and logs when reporting"
            ],
            "documentation": "https://github.com/your-repo/w100-hacs-integration#support"
        }
    
    @classmethod
    def format_error_message(cls, error_code: str, context: dict[str, Any] | None = None) -> str:
        """Format a user-friendly error message with context."""
        error_info = cls.get_error_info(error_code)
        
        message = f"{error_info['title']}: {error_info['message']}"
        
        if context:
            if "device_name" in context:
                message += f" (Device: {context['device_name']})"
            if "entity_id" in context:
                message += f" (Entity: {context['entity_id']})"
        
        return message
    
    @classmethod
    def get_troubleshooting_steps(cls, error_code: str) -> list[str]:
        """Get troubleshooting steps for an error code."""
        error_info = cls.get_error_info(error_code)
        return error_info.get("guidance", [])
    
    @classmethod
    def get_documentation_link(cls, error_code: str) -> str:
        """Get documentation link for an error code."""
        error_info = cls.get_error_info(error_code)
        return error_info.get("documentation", "https://github.com/your-repo/w100-hacs-integration")


class W100ConfigFlowMessages:
    """User-friendly messages for configuration flow."""
    
    STEP_DESCRIPTIONS = {
        "user": "Set up your W100 Smart Control integration by selecting a W100 device from your Zigbee2MQTT setup.",
        "device_selection": "Choose the W100 device you want to control. Make sure it's paired with Zigbee2MQTT.",
        "climate_selection": "Select an existing climate entity or create a new generic thermostat.",
        "thermostat_config": "Configure the generic thermostat settings for your heating system.",
        "customization": "Customize the W100 behavior and advanced features."
    }
    
    ERROR_MESSAGES = {
        "no_mqtt": "MQTT integration is required but not found. Please install and configure the MQTT integration first.",
        "no_zigbee2mqtt": "Zigbee2MQTT integration not detected. Please ensure Zigbee2MQTT is running and connected.",
        "no_w100_devices": "No W100 devices found in Zigbee2MQTT. Please pair your W100 device first.",
        "device_unavailable": "The selected W100 device is not responding. Please check the device and try again.",
        "entity_not_found": "The selected climate entity could not be found. Please choose a different entity.",
        "entity_unavailable": "The selected climate entity is currently unavailable. Please try again later.",
        "invalid_temperature": "Temperature values must be between -50°C and 50°C.",
        "invalid_tolerance": "Tolerance values must be between 0.1°C and 5.0°C.",
        "heater_not_found": "The selected heater switch could not be found.",
        "sensor_not_found": "The selected temperature sensor could not be found.",
        "duplicate_entity": "An entity with this name already exists. Please choose a different name."
    }
    
    SUCCESS_MESSAGES = {
        "device_found": "W100 device found and accessible!",
        "entity_validated": "Climate entity validated successfully!",
        "thermostat_created": "Generic thermostat created successfully!",
        "setup_complete": "W100 Smart Control integration set up successfully!"
    }
    
    HELP_TEXT = {
        "device_selection": "Select your W100 device from the list. If you don't see your device, make sure it's paired with Zigbee2MQTT and try refreshing.",
        "climate_entity": "Choose an existing climate entity to control, or create a new generic thermostat if you don't have one.",
        "thermostat_setup": "Configure your heating system by selecting the heater switch and temperature sensor.",
        "temperature_ranges": "Set comfortable temperature ranges. The W100 uses 0.5°C increments.",
        "advanced_features": "Enable advanced features like stuck heater detection and beep feedback."
    }


class W100DiagnosticInfo:
    """Diagnostic information for troubleshooting."""
    
    @staticmethod
    def get_system_info(hass) -> dict[str, Any]:
        """Get system diagnostic information."""
        return {
            "home_assistant_version": hass.config.version,
            "mqtt_available": hass.services.has_service("mqtt", "publish"),
            "zigbee2mqtt_detected": "zigbee2mqtt" in hass.config.components,
            "integration_version": "1.0.0",  # This would be dynamic in real implementation
        }
    
    @staticmethod
    def get_device_info(coordinator, device_name: str) -> dict[str, Any]:
        """Get device diagnostic information."""
        device_state = coordinator._device_states.get(device_name, {})
        device_config = coordinator._device_configs.get(device_name, {})
        
        return {
            "device_name": device_name,
            "device_available": bool(device_state),
            "last_action": device_state.get("last_action"),
            "last_action_time": device_state.get("last_action_time"),
            "mqtt_topics_subscribed": len(coordinator._mqtt_subscriptions.get(device_name, [])),
            "climate_entity": device_config.get("existing_climate_entity"),
            "created_thermostats": coordinator._device_thermostats.get(device_name, []),
        }
    
    @staticmethod
    def format_diagnostic_report(hass, coordinator, device_name: str) -> str:
        """Format a diagnostic report for support."""
        system_info = W100DiagnosticInfo.get_system_info(hass)
        device_info = W100DiagnosticInfo.get_device_info(coordinator, device_name)
        
        report = f"""
W100 Smart Control Diagnostic Report
====================================

System Information:
- Home Assistant Version: {system_info['home_assistant_version']}
- MQTT Available: {system_info['mqtt_available']}
- Zigbee2MQTT Detected: {system_info['zigbee2mqtt_detected']}
- Integration Version: {system_info['integration_version']}

Device Information:
- Device Name: {device_info['device_name']}
- Device Available: {device_info['device_available']}
- Last Action: {device_info['last_action']}
- Last Action Time: {device_info['last_action_time']}
- MQTT Topics: {device_info['mqtt_topics_subscribed']}
- Climate Entity: {device_info['climate_entity']}
- Created Thermostats: {len(device_info['created_thermostats'])}

Please include this report when seeking support.
"""
        return report.strip()