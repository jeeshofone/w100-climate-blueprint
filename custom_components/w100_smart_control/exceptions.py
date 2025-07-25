"""Custom exception classes for W100 Smart Control integration."""
from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class W100IntegrationError(HomeAssistantError):
    """Base exception for W100 Smart Control integration."""
    
    def __init__(self, message: str, error_code: str | None = None) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.error_code = error_code


class W100DeviceError(W100IntegrationError):
    """Exception for W100 device-related errors."""
    
    def __init__(self, device_name: str, message: str, error_code: str | None = None) -> None:
        """Initialize the device error."""
        super().__init__(f"W100 device '{device_name}': {message}", error_code)
        self.device_name = device_name


class W100MQTTError(W100IntegrationError):
    """Exception for MQTT communication errors."""
    
    def __init__(self, message: str, topic: str | None = None, error_code: str | None = None) -> None:
        """Initialize the MQTT error."""
        topic_info = f" (topic: {topic})" if topic else ""
        super().__init__(f"MQTT error{topic_info}: {message}", error_code)
        self.topic = topic


class W100EntityError(W100IntegrationError):
    """Exception for entity operation errors."""
    
    def __init__(self, entity_id: str, message: str, error_code: str | None = None) -> None:
        """Initialize the entity error."""
        super().__init__(f"Entity '{entity_id}': {message}", error_code)
        self.entity_id = entity_id


class W100ConfigurationError(W100IntegrationError):
    """Exception for configuration-related errors."""
    
    def __init__(self, message: str, config_key: str | None = None, error_code: str | None = None) -> None:
        """Initialize the configuration error."""
        config_info = f" (config: {config_key})" if config_key else ""
        super().__init__(f"Configuration error{config_info}: {message}", error_code)
        self.config_key = config_key


class W100ThermostatError(W100IntegrationError):
    """Exception for generic thermostat operation errors."""
    
    def __init__(self, thermostat_id: str, message: str, error_code: str | None = None) -> None:
        """Initialize the thermostat error."""
        super().__init__(f"Thermostat '{thermostat_id}': {message}", error_code)
        self.thermostat_id = thermostat_id


class W100RegistryError(W100IntegrationError):
    """Exception for entity/device registry operation errors."""
    
    def __init__(self, message: str, registry_type: str | None = None, error_code: str | None = None) -> None:
        """Initialize the registry error."""
        registry_info = f" ({registry_type} registry)" if registry_type else ""
        super().__init__(f"Registry error{registry_info}: {message}", error_code)
        self.registry_type = registry_type


class W100RecoverableError(W100IntegrationError):
    """Exception for recoverable errors that don't require integration shutdown."""
    
    def __init__(self, message: str, retry_after: int | None = None, error_code: str | None = None) -> None:
        """Initialize the recoverable error."""
        super().__init__(message, error_code)
        self.retry_after = retry_after  # Seconds to wait before retry


class W100CriticalError(W100IntegrationError):
    """Exception for critical errors that require integration shutdown or restart."""
    
    def __init__(self, message: str, requires_restart: bool = False, error_code: str | None = None) -> None:
        """Initialize the critical error."""
        super().__init__(message, error_code)
        self.requires_restart = requires_restart


# Error code constants
class W100ErrorCodes:
    """Error codes for W100 integration."""
    
    # Device errors
    DEVICE_NOT_FOUND = "W100_DEVICE_NOT_FOUND"
    DEVICE_UNAVAILABLE = "W100_DEVICE_UNAVAILABLE"
    DEVICE_COMMUNICATION_FAILED = "W100_DEVICE_COMM_FAILED"
    
    # MQTT errors
    MQTT_CONNECTION_FAILED = "W100_MQTT_CONN_FAILED"
    MQTT_PUBLISH_FAILED = "W100_MQTT_PUBLISH_FAILED"
    MQTT_SUBSCRIBE_FAILED = "W100_MQTT_SUBSCRIBE_FAILED"
    MQTT_TOPIC_INVALID = "W100_MQTT_TOPIC_INVALID"
    
    # Entity errors
    ENTITY_NOT_FOUND = "W100_ENTITY_NOT_FOUND"
    ENTITY_UNAVAILABLE = "W100_ENTITY_UNAVAILABLE"
    ENTITY_OPERATION_FAILED = "W100_ENTITY_OP_FAILED"
    ENTITY_STATE_INVALID = "W100_ENTITY_STATE_INVALID"
    
    # Configuration errors
    CONFIG_INVALID = "W100_CONFIG_INVALID"
    CONFIG_MISSING = "W100_CONFIG_MISSING"
    CONFIG_VALIDATION_FAILED = "W100_CONFIG_VALIDATION_FAILED"
    
    # Thermostat errors
    THERMOSTAT_CREATE_FAILED = "W100_THERMOSTAT_CREATE_FAILED"
    THERMOSTAT_REMOVE_FAILED = "W100_THERMOSTAT_REMOVE_FAILED"
    THERMOSTAT_UPDATE_FAILED = "W100_THERMOSTAT_UPDATE_FAILED"
    
    # Registry errors
    REGISTRY_OPERATION_FAILED = "W100_REGISTRY_OP_FAILED"
    DEVICE_REGISTRY_FAILED = "W100_DEVICE_REG_FAILED"
    ENTITY_REGISTRY_FAILED = "W100_ENTITY_REG_FAILED"
    
    # Critical errors
    COORDINATOR_SETUP_FAILED = "W100_COORDINATOR_SETUP_FAILED"
    INTEGRATION_SETUP_FAILED = "W100_INTEGRATION_SETUP_FAILED"
    DATA_CORRUPTION = "W100_DATA_CORRUPTION"