"""Constants for the W100 Smart Control integration."""

DOMAIN = "w100_smart_control"

# Configuration keys
CONF_W100_DEVICE_NAME = "w100_device_name"
CONF_CLIMATE_ENTITY_TYPE = "climate_entity_type"
CONF_EXISTING_CLIMATE_ENTITY = "existing_climate_entity"
CONF_GENERIC_THERMOSTAT_CONFIG = "generic_thermostat_config"
CONF_HEATING_TEMPERATURE = "heating_temperature"
CONF_IDLE_TEMPERATURE = "idle_temperature"
CONF_HEATING_WARM_LEVEL = "heating_warm_level"
CONF_IDLE_WARM_LEVEL = "idle_warm_level"
CONF_IDLE_FAN_SPEED = "idle_fan_speed"
CONF_SWING_MODE = "swing_mode"
CONF_BEEP_MODE = "beep_mode"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_BACKUP_HUMIDITY_SENSOR = "backup_humidity_sensor"

# Generic thermostat configuration keys
CONF_HEATER_SWITCH = "heater_switch"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_TARGET_TEMP = "target_temp"
CONF_COLD_TOLERANCE = "cold_tolerance"
CONF_HOT_TOLERANCE = "hot_tolerance"
CONF_PRECISION = "precision"

# Default values
DEFAULT_HEATING_TEMPERATURE = 30
DEFAULT_IDLE_TEMPERATURE = 22
DEFAULT_HEATING_WARM_LEVEL = "4"
DEFAULT_IDLE_WARM_LEVEL = "1"
DEFAULT_IDLE_FAN_SPEED = "3"
DEFAULT_SWING_MODE = "horizontal"
DEFAULT_BEEP_MODE = "On-Mode Change"
DEFAULT_MIN_TEMP = 7
DEFAULT_MAX_TEMP = 35
DEFAULT_TARGET_TEMP = 21
DEFAULT_COLD_TOLERANCE = 0.3
DEFAULT_HOT_TOLERANCE = 0.3
DEFAULT_PRECISION = 0.5

# Options
CLIMATE_ENTITY_TYPES = ["existing", "generic"]
WARM_LEVELS = ["1", "2", "3", "4"]
FAN_SPEEDS = [str(i) for i in range(1, 10)]
SWING_MODES = ["horizontal", "vertical", "both", "off"]
BEEP_MODES = ["Enable Beep", "Disable Beep", "On-Mode Change"]
PRECISION_OPTIONS = [0.1, 0.5, 1.0]

# MQTT topics (will be formatted with device name)
MQTT_W100_ACTION_TOPIC = "zigbee2mqtt/{}/action"
MQTT_W100_STATE_TOPIC = "zigbee2mqtt/{}"
MQTT_W100_SET_TOPIC = "zigbee2mqtt/{}/set"

# W100 Actions
W100_ACTION_TOGGLE = "double"
W100_ACTION_PLUS = "plus"
W100_ACTION_MINUS = "minus"

# Update intervals
UPDATE_INTERVAL_SECONDS = 30
DISPLAY_UPDATE_DELAY_SECONDS = 1