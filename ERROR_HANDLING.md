# W100 Smart Control - Error Handling and Troubleshooting

This document provides comprehensive information about error handling and troubleshooting for the W100 Smart Control integration.

## User-Friendly Error Messages

The integration provides clear, descriptive error messages with specific guidance for common issues. Each error includes:

- **Clear Title**: Descriptive error title
- **Detailed Message**: Explanation of what went wrong
- **Troubleshooting Steps**: Step-by-step guidance to resolve the issue
- **Documentation Links**: Links to relevant documentation

## Common Error Categories

### Device Errors

#### W100 Device Not Found
**Message**: The W100 device could not be found in your Zigbee2MQTT setup.

**Troubleshooting Steps**:
1. Verify the W100 device is paired with Zigbee2MQTT
2. Check that the device name matches exactly (case-sensitive)
3. Ensure Zigbee2MQTT is running and accessible
4. Try refreshing the device list in the configuration

#### W100 Device Unavailable
**Message**: The W100 device is currently unavailable or not responding.

**Troubleshooting Steps**:
1. Check if the device has power and is within Zigbee range
2. Verify Zigbee2MQTT can communicate with the device
3. Try restarting the W100 device by removing and reinserting batteries
4. Check Zigbee2MQTT logs for connectivity issues

### MQTT Errors

#### MQTT Connection Failed
**Message**: Unable to connect to the MQTT broker for W100 communication.

**Troubleshooting Steps**:
1. Verify MQTT integration is installed and configured in Home Assistant
2. Check MQTT broker is running and accessible
3. Ensure Zigbee2MQTT is connected to the same MQTT broker
4. Verify MQTT credentials and connection settings

#### MQTT Publish Failed
**Message**: Failed to send commands to the W100 device via MQTT.

**Troubleshooting Steps**:
1. Check MQTT broker connectivity and permissions
2. Verify Zigbee2MQTT is receiving messages
3. Ensure the W100 device topic is correct
4. Check for MQTT broker resource limits

### Entity Errors

#### Climate Entity Not Found
**Message**: The target climate entity could not be found.

**Troubleshooting Steps**:
1. Verify the climate entity exists and is available
2. Check the entity ID is spelled correctly
3. Ensure the climate entity is not disabled
4. Try selecting a different climate entity

#### Climate Entity Unavailable
**Message**: The target climate entity is currently unavailable.

**Troubleshooting Steps**:
1. Check if the climate entity's underlying device is working
2. Verify the climate integration is functioning properly
3. Try restarting the climate entity's integration
4. Check Home Assistant logs for related errors

### Configuration Errors

#### Invalid Configuration
**Message**: The integration configuration contains invalid settings.

**Troubleshooting Steps**:
1. Review all configuration settings for typos or invalid values
2. Ensure temperature ranges are logical (min < max)
3. Verify entity IDs exist and are accessible
4. Check that all required fields are filled

#### Configuration Validation Failed
**Message**: The configuration could not be validated.

**Troubleshooting Steps**:
1. Check that all referenced entities exist
2. Verify temperature sensors provide numeric values
3. Ensure heater switches are controllable
4. Validate all entity IDs are correct

### Thermostat Errors

#### Thermostat Creation Failed
**Message**: Failed to create the generic thermostat entity.

**Troubleshooting Steps**:
1. Verify the heater switch entity exists and is controllable
2. Check the temperature sensor provides valid readings
3. Ensure entity IDs don't conflict with existing entities
4. Try using different entity names

## Diagnostic Services

The integration provides diagnostic services to help troubleshoot issues:

### Get Diagnostic Information

**Service**: `w100_smart_control.get_diagnostic_info`

Generates a comprehensive diagnostic report including:
- Home Assistant version information
- MQTT and Zigbee2MQTT status
- Device availability and last activity
- Climate entity status
- Created thermostat information

**Usage**:
```yaml
service: w100_smart_control.get_diagnostic_info
data:
  device_name: "living_room_w100"  # Optional
```

### Validate Setup

**Service**: `w100_smart_control.validate_setup`

Validates the current setup and identifies common issues:
- MQTT connectivity
- Device availability
- Entity status
- Configuration validation

**Usage**:
```yaml
service: w100_smart_control.validate_setup
```

## Configuration Flow Guidance

The configuration flow provides helpful guidance at each step:

### Device Selection
- **Help**: Select your W100 device from the list. If you don't see your device, make sure it's paired with Zigbee2MQTT and try refreshing.
- **Common Issues**: Device not appearing, device unavailable

### Climate Entity Selection
- **Help**: Choose an existing climate entity to control, or create a new generic thermostat if you don't have one.
- **Common Issues**: Entity not found, entity unavailable

### Thermostat Setup
- **Help**: Configure your heating system by selecting the heater switch and temperature sensor.
- **Common Issues**: Invalid entities, conflicting names

### Temperature Configuration
- **Help**: Set comfortable temperature ranges. The W100 uses 0.5°C increments.
- **Common Issues**: Invalid temperature ranges, precision mismatch

## Logging and Error Reporting

### Log Levels

The integration uses structured logging with different levels:

- **DEBUG**: Detailed operation information for troubleshooting
- **INFO**: Important operations and successful completions
- **WARNING**: Recoverable errors and degraded functionality
- **ERROR**: Failures that require attention

### Error Context

All error messages include contextual information:
- Device name
- Entity IDs
- Operation being performed
- Error codes for reference

### Example Log Entry

```
2023-12-01 10:00:00 ERROR (MainThread) [custom_components.w100_smart_control.climate] 
W100 Error: Climate Entity Not Found: The target climate entity could not be found. (Device: living_room_w100) (Entity: climate.nonexistent)

2023-12-01 10:00:01 INFO (MainThread) [custom_components.w100_smart_control.climate] 
Troubleshooting steps: 1. Verify the climate entity exists and is available; 2. Check the entity ID is spelled correctly; 3. Ensure the climate entity is not disabled; 4. Try selecting a different climate entity
```

## Getting Help

### Diagnostic Report

When seeking help, always include a diagnostic report:

1. Call the diagnostic service:
   ```yaml
   service: w100_smart_control.get_diagnostic_info
   ```

2. Check Home Assistant logs for the diagnostic report

3. Include the report when reporting issues

### Common Support Information

When reporting issues, include:
- Home Assistant version
- Integration version
- W100 device model and firmware
- Zigbee2MQTT version
- MQTT broker type and version
- Relevant log entries with error messages
- Diagnostic report

### Documentation Links

- [Installation Guide](https://github.com/your-repo/w100-hacs-integration#installation)
- [Configuration Guide](https://github.com/your-repo/w100-hacs-integration#configuration)
- [Troubleshooting Guide](https://github.com/your-repo/w100-hacs-integration#troubleshooting)
- [MQTT Setup](https://github.com/your-repo/w100-hacs-integration#mqtt-setup)
- [Support Forum](https://github.com/your-repo/w100-hacs-integration/discussions)

## Error Recovery

The integration includes automatic error recovery for:

- **Temporary MQTT disconnections**: Automatic reconnection and subscription restoration
- **Device unavailability**: Graceful degradation and recovery when device comes back online
- **Entity state issues**: Fallback behaviors and retry mechanisms
- **Display sync failures**: Non-critical failures don't interrupt main functionality

## Prevention Tips

To prevent common issues:

1. **Keep dependencies updated**: Regularly update Home Assistant, MQTT broker, and Zigbee2MQTT
2. **Monitor device batteries**: Replace W100 device batteries before they're completely drained
3. **Maintain good Zigbee coverage**: Ensure W100 devices are within good Zigbee range
4. **Regular backups**: Backup Home Assistant configuration including integration settings
5. **Monitor logs**: Regularly check logs for warnings that might indicate developing issues