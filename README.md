# Aqara W100 Smart Control Integration

# THIS IS A WORK IN PROGRESS AND IS UNTESTED

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Integration-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)
[![GitHub Release](https://img.shields.io/github/release/w100-climate-blueprint/w100-smart-control.svg)](https://github.com/w100-climate-blueprint/w100-smart-control/releases)

A comprehensive Home Assistant integration for seamless climate control using Aqara W100 devices. Transform your W100 remote into a powerful climate controller with GUI configuration, automatic device discovery, and all the advanced features from the proven blueprint - now with zero YAML configuration required.

## ✨ HACS Integration - Zero Configuration Required

**Transform your W100 setup from complex YAML to simple GUI configuration:**

- 🎯 **One-Click Installation**: Install directly through HACS with zero manual setup
- 🖱️ **GUI Configuration**: Complete setup through Home Assistant's integration UI
- 🔍 **Auto Discovery**: Automatically finds your W100 devices via Zigbee2MQTT
- 🏠 **Built-in Thermostat**: Optionally creates generic thermostats - no external dependencies
- 📱 **Multi-Device Support**: Configure multiple W100 devices independently
- 🔄 **Blueprint Migration**: Easy migration from existing blueprint setups

**Status**: 🟢 **Ready for HACS** - All blueprint functionality preserved in modern integration format

## Features

🎯 **GUI Configuration** - Complete setup through Home Assistant's integration interface  
🔍 **Auto Discovery** - Automatically detects W100 devices via Zigbee2MQTT  
🏠 **Built-in Thermostat** - Creates generic thermostats with optimal W100 settings  
🎛️ **W100 Remote Control** - Full button functionality with display synchronization  
🌡️ **Precise Temperature Control** - 0.5°C increments for fine-tuned comfort  
🔊 **Smart Beep Control** - Configurable audio feedback (Enable/Disable/On-Mode Change)  
💨 **Dual Mode Operation** - Heat mode with temperature control, off mode with fan speed control  
📊 **Real-time Display Sync** - Temperature, humidity, and status updates on W100 display  
📱 **Multi-Device Support** - Configure multiple W100 devices independently  
🔄 **Advanced Features** - Stuck heater workaround, startup initialization, error handling  

## Requirements

### Required Components

1. **Zigbee2MQTT or ZHA**
   - For W100 device communication and control
   - Required for remote control and display functionality

2. **MQTT Integration** (if using Zigbee2MQTT)
   - Built into Home Assistant
   - Required for W100 device communication

### Compatible Hardware

- **Aqara W100 Zigbee Temperature/Humidity Remote**
- Any climate entity supported by Home Assistant
- Any temperature sensor supported by Home Assistant (for generic thermostat creation)
- Any switch entity supported by Home Assistant (for generic thermostat heater control)

### Optional Dependencies

The integration can work with existing climate entities or create new generic thermostats:
- **Existing Climate Entities**: Any Home Assistant climate entity (Tuya Local, Smart Thermostat PID, etc.)
- **Generic Thermostat**: Built-in Home Assistant generic thermostat platform (no external dependencies)

## Installation

### Method 1: HACS (Recommended)

1. **Install via HACS:**
   ```
   HACS → Integrations → Explore & Download Repositories
   Search: "Aqara W100 Smart Control"
   ```

2. **Restart Home Assistant**

3. **Add Integration:**
   ```
   Settings → Devices & Services → Add Integration
   Search: "Aqara W100 Smart Control"
   ```

### Method 2: Manual Installation

1. **Download Integration:**
   - Download the latest release from [GitHub Releases](https://github.com/w100-climate-blueprint/w100-smart-control/releases)
   - Extract the `custom_components/w100_smart_control` folder

2. **Copy to Home Assistant:**
   ```
   Copy to: config/custom_components/w100_smart_control/
   ```

3. **Restart Home Assistant**

4. **Add Integration:**
   ```
   Settings → Devices & Services → Add Integration
   Search: "Aqara W100 Smart Control"
   ```

### Prerequisites

Before installation, ensure you have:
- ✅ W100 device paired with Zigbee2MQTT or ZHA
- ✅ MQTT integration configured (if using Zigbee2MQTT)
- ✅ Temperature sensors available in Home Assistant
- ✅ Climate entities or switches for heater control (if using existing entities)

## Configuration

The integration provides a step-by-step GUI configuration process:

### Step 1: Device Discovery
- Automatically scans for available W100 devices via Zigbee2MQTT
- Select your W100 device from the discovered list
- Validates device accessibility and MQTT topics

### Step 2: Climate Entity Selection
Choose one of two options:

#### Option A: Use Existing Climate Entity
- Select from existing climate entities in your Home Assistant
- Validates entity supports required features (temperature control, heat/off modes)

#### Option B: Create New Generic Thermostat
- **Heater Switch**: Switch entity that controls your heater
- **Temperature Sensor**: Sensor entity for current temperature readings
- **Min/Max Temperature**: Temperature range (default: 7-35°C)
- **Target Temperature**: Initial temperature setpoint (default: 21°C)
- **Tolerances**: Cold/hot tolerance for switching (default: 0.3°C)
- **Precision**: Temperature step size (default: 0.5°C for W100 compatibility)

### Step 3: Customization Options

| Setting | Default | Description |
|---------|---------|-------------|
| **Heating Temperature** | 30°C | Temperature when actively heating |
| **Idle Temperature** | 22°C | Temperature when maintaining |
| **Heating Warm Level** | 4 | Heat level when actively heating (1-4) |
| **Idle Warm Level** | 1 | Heat level when maintaining (1-4) |
| **Idle Fan Speed** | 3 | Fan speed when thermostat is off (1-9) |
| **Swing Mode** | horizontal | Fan oscillation (horizontal/vertical/both/off) |
| **Beep Mode** | On-Mode Change | Audio feedback behavior |
| **Humidity Sensor** | - | Primary humidity sensor for W100 display |
| **Backup Humidity Sensor** | - | Fallback humidity sensor |

### Beep Control Modes

- **Enable Beep**: Audio feedback for all operations
- **Disable Beep**: No audio feedback
- **On-Mode Change**: Smart beeping only for temperature changes and mode switching

## Usage

### Basic Operation

1. **Heat Mode**: 
   - Set climate entity to desired temperature via Home Assistant or W100 remote
   - System automatically maintains target temperature
   - W100 display shows current and target temperature

2. **Off Mode**:
   - Climate entity is off, but W100 remote still functional
   - Use W100 remote to control fan speed directly (1-9)
   - W100 display shows fan speed and humidity

### W100 Remote Controls

- **Double-tap center button**: Toggle between heat and off modes
- **Plus buttons**: Increase temperature (heat mode) or fan speed (off mode) by 0.5°C/1 level
- **Minus buttons**: Decrease temperature (heat mode) or fan speed (off mode) by 0.5°C/1 level
- **Display**: Shows current temperature, target temperature, fan speed, and humidity

### Entities Created

The integration creates several entities for each configured W100 device:

#### Climate Entity
- **`climate.w100_[device_name]`**: Main climate control interface
- Proxies operations to your selected climate entity
- Handles W100 button presses and display updates

#### Sensor Entities
- **`sensor.w100_[device_name]_humidity`**: Current humidity from W100 display
- **`sensor.w100_[device_name]_status`**: Current mode and last action
- **`sensor.w100_[device_name]_connection`**: Connection status and diagnostics

#### Switch Entities
- **`switch.w100_[device_name]_beep`**: Control beep functionality
- **`switch.w100_[device_name]_advanced_features`**: Enable/disable advanced features

### Advanced Features

#### Stuck Heater Workaround
- Automatically detects when temperature sensor gets stuck
- Temporarily adjusts operation to force accurate readings
- Prevents premature heating shutdown

#### Smart Display Synchronization
- Real-time temperature and humidity updates on W100
- Automatic mode detection and appropriate value display
- Startup initialization with current system values
- Debounced updates to prevent display flickering

#### Device Triggers
- Automation triggers for W100 button presses
- Available in Home Assistant's automation editor
- Trigger types: `button_plus`, `button_minus`, `button_toggle`

## Troubleshooting

### Common Issues

**Integration not appearing in HACS:**
- Ensure HACS is installed and updated
- Check that the repository is added to HACS default repositories
- Try refreshing HACS repository list

**W100 device not discovered:**
- Verify W100 is paired with Zigbee2MQTT or ZHA
- Check device name matches exactly (case-sensitive)
- Ensure MQTT integration is configured and connected
- Verify Zigbee2MQTT is publishing device data

**Configuration flow errors:**
- Check that all required entities exist and are accessible
- Verify temperature sensors are providing numeric values
- Ensure climate entities support heat and off modes
- Check Home Assistant logs for detailed error messages

**W100 remote not responding:**
- Verify MQTT topics are correct in Zigbee2MQTT
- Check that W100 device is online and responsive
- Test W100 manually in Zigbee2MQTT or ZHA
- Review integration logs for MQTT communication errors

**Generic thermostat creation fails:**
- Ensure heater switch entity exists and is controllable
- Verify temperature sensor provides numeric values
- Check that entity IDs don't conflict with existing entities
- Review Home Assistant logs for creation errors

### Debug Logging

Enable debug logging for detailed troubleshooting:

```yaml
logger:
  default: info
  logs:
    custom_components.w100_smart_control: debug
```

Monitor these log entries:
- W100 device discovery and validation
- MQTT message handling and responses
- Climate entity operations and state changes
- Generic thermostat creation and management
- Configuration flow steps and validation

### Getting Help

1. **Check Logs**: Enable debug logging and review Home Assistant logs
2. **Verify Setup**: Ensure all prerequisites are met and entities exist
3. **Test Components**: Test W100 and climate entities independently
4. **Report Issues**: Create detailed issue reports with logs and configuration

## Migration from Blueprint

### Automatic Migration

The integration includes a migration wizard to help transition from the existing blueprint:

1. **Detection**: Automatically detects existing blueprint automations
2. **Import**: Imports compatible settings from blueprint configuration
3. **Validation**: Validates that all entities still exist and are accessible
4. **Guidance**: Provides step-by-step migration instructions

### Manual Migration Steps

1. **Install Integration**: Follow installation instructions above
2. **Configure W100**: Use the same W100 device name from your blueprint
3. **Map Entities**: Select the same climate entities used in your blueprint
4. **Transfer Settings**: Use the same temperature, fan speed, and beep settings
5. **Test Functionality**: Verify W100 remote works as expected
6. **Disable Blueprint**: Disable or remove the old blueprint automation

### Coexistence Mode

The integration can coexist with blueprint automations during migration:
- Both systems can operate simultaneously for testing
- Integration takes precedence for W100 control when both are active
- Gradual migration allows testing before full transition

### Settings Mapping

| Blueprint Setting | Integration Equivalent |
|------------------|----------------------|
| `w100_device_name` | Device selection in config flow |
| `smart_thermostat_entity` | Climate entity selection |
| `heating_temperature` | Heating Temperature setting |
| `idle_temperature` | Idle Temperature setting |
| `heating_warm_level` | Heating Warm Level setting |
| `idle_warm_level` | Idle Warm Level setting |
| `idle_fan_speed` | Idle Fan Speed setting |
| `swing_mode` | Swing Mode setting |
| `beep_mode` | Beep Mode setting |
| `humidity_sensor` | Humidity Sensor setting |
| `backup_humidity_sensor` | Backup Humidity Sensor setting |

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

### Integration Releases
- **v1.0.0**: 🎯 **HACS Integration** - Complete transformation from blueprint to modern Home Assistant integration
  - GUI configuration flow with device discovery
  - Built-in generic thermostat creation
  - Multi-device support with independent operation
  - All blueprint functionality preserved and enhanced
  - HACS compliance with proper validation workflows

### Blueprint Legacy (Preserved for Reference)
- **v0.11.3**: 0.5°C precision control for finer temperature adjustments
- **v0.11.2**: Eliminated MQTT timeout errors by using Home Assistant services
- **v0.11**: Complete rewrite fixing OFF mode control and display bouncing
- **v0.10**: Attempted display bouncing fix (incomplete)
- **v0.9**: Smart Thermostat PID compatibility improvements
- **v0.8-v0.1**: Progressive feature additions and bug fixes

## Contributing

Contributions are welcome! Please read our contributing guidelines:

### Development Setup
1. Fork the repository
2. Create a development branch
3. Make your changes
4. Test with a local Home Assistant instance
5. Ensure all GitHub Actions pass
6. Submit a pull request

### Code Standards
- Follow Home Assistant integration patterns
- Include unit tests for new functionality
- Update documentation for user-facing changes
- Ensure HACS validation passes

### Reporting Issues
- Use the issue template
- Include Home Assistant version and integration version
- Provide relevant logs with debug logging enabled
- Include configuration details (sanitized)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits and Acknowledgments

- **Home Assistant Community** - For the excellent platform and integration patterns
- **HACS Team** - For the community store infrastructure
- **Zigbee2MQTT Project** - For reliable Zigbee device communication
- **Blueprint Users** - For testing, feedback, and feature requests that shaped this integration

## Support

### Community Support
- 🐛 **Issues**: [GitHub Issues](https://github.com/w100-climate-blueprint/w100-smart-control/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/w100-climate-blueprint/w100-smart-control/discussions)
- 📖 **Documentation**: This README and integration help text

### Show Your Support
If you find this integration useful:
- ⭐ Star this repository
- 🔄 Share with others who have W100 devices
- 💡 Contribute improvements or suggestions
- 📝 Help improve documentation

---

**Compatibility**: This integration works with any climate entity in Home Assistant and can create generic thermostats for heater/switch combinations. While originally designed for fan/heater combos, it's adaptable to various heating systems. 
