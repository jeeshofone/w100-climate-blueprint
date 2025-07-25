# W100 Climate Blueprint

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1+-blue.svg)](https://www.home-assistant.io/)
[![Blueprint](https://img.shields.io/badge/Blueprint-v0.12.1-green.svg)](blueprint.yaml)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

A comprehensive Home Assistant blueprint for intelligent climate control using PID-controlled fan/heater combos with W100 Zigbee remote integration. Supports both Kogan Smarterhome Bladeless Fan and Philips Fan Heater devices. Features advanced temperature sensor workarounds, smart beep control, and seamless display synchronization.

## ✅ v0.12.1 - MALFORMED ENTITY_ID ERRORS FIXED

**Critical bug fix release addressing automation creation failures:**

- ✅ **Fixed Malformed Entity_ID Errors**: Resolved automation creation failures for both device types
- ✅ **Enhanced Entity Validation**: All entity_id references now have safe fallbacks for HA validation
- ✅ **Service Call Format Fixed**: Corrected number.set_value service call structure
- ✅ **Conditional Logic Preserved**: Optional entity handling still works as intended
- ✅ **Programmatic Analysis Tools**: Added blueprint analyzer for future debugging

**Status**: 🟢 **Production Ready** - All known entity_id validation issues resolved  
**Upgrade**: **REQUIRED** for users experiencing automation creation errors

## Recent Fixes (v0.12.1)

### 🚨 **Critical Issue Resolved**
Both Kogan and Philips automations were failing with:
```
Message malformed: not a valid value for dictionary value @ data['actions'][0]['choose'][0]['sequence'][0]['choose'][X]['sequence'][2]['choose'][0]['sequence'][0]['entity_id']
```

### 🔧 **Root Cause & Solution**
**Problem**: Home Assistant validates ALL entity_id references at automation creation time, regardless of conditional logic. Template variables resolving to empty strings caused malformed entity_id errors.

**Solution**: Implemented entity_id fallback pattern:
```yaml
entity_id: "{{ variable_name if variable_name != '' else 'sun.sun' }}"
```

This ensures:
- ✅ Valid entity_id for HA validation (always resolves to existing entity)
- ✅ Conditional logic preserved (prevents execution when input empty)
- ✅ No runtime errors (sun.sun exists but won't be called due to conditions)

### 📊 **Validation Results**
- ✅ 16 entity_id references updated with fallback logic
- ✅ 1 service call format corrected
- ✅ YAML syntax validated
- ✅ Blueprint structure verified
- ✅ Both device types tested

## Features

🌡️ **PID Temperature Control** - Precise temperature regulation using smart thermostat integration  
🎛️ **W100 Remote Integration** - Full control via Zigbee remote with display sync  
🔄 **Temperature Sensor Workaround** - Automatic detection and correction of stuck heater scenarios  
🔊 **Smart Beep Control** - Configurable audio feedback modes (Kogan only)  
💨 **Dual Mode Operation** - Heat mode with temperature control, cool mode with fan speed control  
📊 **Real-time Display Sync** - Temperature, humidity, and status updates on W100 display  
⚡ **Parallel Processing** - Optimized for responsive control with multiple concurrent triggers  
🛡️ **Robust Entity Handling** - Safe fallbacks for all optional entity references

## Dependencies

This blueprint requires the following Home Assistant integrations:

### Required Components

1. **[Smart Thermostat PID](https://github.com/ScratMan/HASmartThermostat)**
   - Advanced PID controller for precise temperature control
   - Install via HACS or manual installation

2. **[Tuya Local](https://github.com/make-all/tuya-local)** (for Kogan devices)
   - For Kogan Smarterhome bladeless heater fan control
   - Provides climate and switch entities for the fan

3. **Zigbee2MQTT or ZHA**
   - For W100 remote device integration
   - Required for remote control and display functionality

### Compatible Hardware

- **Kogan Smarterhome Bladeless Heater Fan** (via Tuya Local)
- **Philips Fan Heater** (via local integration)
- **W100 Zigbee Temperature/Humidity Remote** 
- Any temperature sensor supported by Home Assistant
- Any humidity sensor supported by Home Assistant

## Installation

### Step 1: Install Dependencies

1. **Install Smart Thermostat PID via HACS:**
   ```
   HACS → Integrations → ⋮ → Custom repositories
   Repository: https://github.com/ScratMan/HASmartThermostat
   Category: Integration
   ```

2. **Install Tuya Local via HACS:**
   ```
   HACS → Integrations → Search "Tuya Local"
   ```

3. **Configure your Kogan fan in Tuya Local**
4. **Pair your W100 device with Zigbee2MQTT/ZHA**

### Step 2: Configure Required Entities

#### Smart Thermostat Configuration
Add to your `configuration.yaml`:

```yaml
climate:
  - platform: smart_thermostat
    name: Smart Bedroom Fan Controller
    unique_id: smart_bedroom_fan_pid
    heater: input_boolean.bedroom_fan_heat_mode
    target_sensor: sensor.bedroom_temp
    outdoor_sensor: sensor.outdoor_temperature
    min_temp: 17
    max_temp: 28
    target_temp: 22
    keep_alive:
      seconds: 60
    away_temp: 20
    eco_temp: 21
    boost_temp: 24
    kp: 100
    ki: 0
    kd: 0
    pwm: 00:15:00
    debug: true
```

#### Input Boolean for Heat Mode
```yaml
input_boolean:
  bedroom_fan_heat_mode:
    name: Bedroom Fan Heat Mode
    icon: mdi:radiator
```

### Step 3: Import Blueprint

1. **Download the blueprint:**
   - Copy the raw content of [`blueprint.yaml`](blueprint.yaml)

2. **Import in Home Assistant:**
   ```
   Settings → Automations & Scenes → Blueprints → Import Blueprint
   ```
   - Paste the blueprint YAML content

3. **Create automation from blueprint:**
   ```
   Settings → Automations & Scenes → Create Automation → Use Blueprint
   ```

## Configuration

### Required Inputs

| Input | Description | Example |
|-------|-------------|---------|
| **W100 Device Name** | Exact case-sensitive name from Zigbee2MQTT | `Tempcontrol00` |
| **Heat Mode Boolean** | Input boolean controlling heating mode | `input_boolean.bedroom_fan_heat_mode` |
| **Fan Climate Entity** | The fan's climate entity from Tuya Local | `climate.bedroom_fan` |
| **Fan Warm Level Entity** | Select entity for heating levels | `select.bedroom_fan_warm_level` |
| **Smart Thermostat Entity** | PID controller climate entity | `climate.smart_bedroom_fan_controller` |
| **Humidity Sensor** | Primary humidity sensor | `sensor.bedroom_humidity_group` |
| **Fan Beep Switch** | Switch controlling fan beep sounds | `switch.bedroom_fan_beep` |

### Optional Settings

| Setting | Default | Description |
|---------|---------|-------------|
| **Backup Humidity Sensor** | - | Fallback humidity sensor |
| **Heating Temperature** | 30°C | Temperature when actively heating |
| **Idle Temperature** | 22°C | Temperature when maintaining |
| **Heating Warm Level** | 4 | Heat level when actively heating |
| **Idle Warm Level** | 1 | Heat level when maintaining |
| **Idle Fan Speed** | 3 | Fan speed when thermostat is idle |
| **Swing Mode** | horizontal | Fan oscillation mode |
| **Beep Mode** | On-Mode Change | Beep control behavior |

### Beep Control Modes

- **Enable Beep**: Fan beeps for all operations
- **Disable Beep**: Fan never beeps  
- **On-Mode Change**: Smart beeping only for temperature changes and manual on/off

## Usage

### Basic Operation

1. **Heat Mode**: 
   - Set smart thermostat to desired temperature
   - Fan automatically heats to reach target
   - PID controller maintains precise temperature

2. **Fan Mode**:
   - Use W100 remote or Home Assistant to control fan speed
   - Manual fan speed control (1-9)
   - Automatic idle speed when thermostat off

### W100 Remote Controls

- **Double-tap center**: Toggle between heat/fan mode
- **Single/Double +**: Increase temperature (heat mode) or fan speed (cool mode)  
- **Single/Double -**: Decrease temperature (heat mode) or fan speed (cool mode)
- **Display**: Shows current temperature, target temperature, and humidity

### Advanced Features

#### Temperature Sensor Workaround
- Automatically detects when fan sensor reads 30°C but room is cooler
- Temporarily switches to fan-only mode for 2 minutes
- Forces air circulation for accurate temperature reading
- Prevents premature heating shutdown

#### Smart Display Sync
- Real-time temperature and humidity updates on W100
- Always uses external sensor mode for custom value display
- Shows temperature setpoint in heat mode, fan speed (1-9) in cool mode
- Startup initialization and automatic sync on value changes

## Troubleshooting

### Common Issues

**Malformed entity_id errors (FIXED in v0.12.1):**
```
Message malformed: not a valid value for dictionary value @ data['actions'][0]['choose'][0]['sequence'][0]['choose'][X]['sequence'][2]['choose'][0]['sequence'][0]['entity_id']
```
- **Solution**: Update to v0.12.1 - all entity_id validation issues resolved
- **Root cause**: HA validates entity_id references at automation creation time
- **Technical details**: See [MALFORMED_ENTITY_FIX_SUMMARY.md](MALFORMED_ENTITY_FIX_SUMMARY.md)

**W100 not responding:**
- Verify exact device name case sensitivity
- Check Zigbee2MQTT connection
- Ensure MQTT broker is running

**Fan speed not setting correctly:**
- Check if `idle_fan_speed` setting matches your fan's capabilities
- Verify fan climate entity supports fan modes 1-9
- Review automation traces for errors

**Temperature sensor workaround activating too often:**
- Adjust fan placement for better air circulation
- Check temperature sensor locations
- Review automation logs for trigger frequency

**Beep control not working:**
- Verify beep switch entity exists and controls fan beeps
- Test switch manually in Developer Tools
- Check automation traces for beep-related actions

### Debug Mode

Enable debug logging by setting the smart thermostat's `debug: true` and monitor these attributes:
- `control_output`: PID output percentage
- `proportional`: P term value  
- `integral`: I term value
- `derivative`: D term value
- `error`: Temperature error

### Blueprint Analysis Tool

For advanced troubleshooting, use the included analyzer:
```bash
python analyze_blueprint.py blueprint.yaml
```

This tool can:
- Identify problematic entity_id references
- Trace exact error paths from HA error messages
- Validate blueprint structure and syntax
- Analyze specific input configurations

## Example Configurations

### Bedroom Setup
```yaml
# Quiet operation with minimal beeps
beep_mode: "Disable Beep"
idle_fan_speed: "2"
heating_temperature: 22
idle_temperature: 20
```

### Living Room Setup  
```yaml
# Responsive control with feedback
beep_mode: "On-Mode Change"
idle_fan_speed: "4"
heating_temperature: 24
swing_mode: "both"
```

### Office Setup
```yaml
# Full feedback and control
beep_mode: "Enable Beep"
idle_fan_speed: "3"
heating_temperature: 23
idle_temperature: 21
```

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

- **v0.12.1**: 🚨 **CRITICAL FIX** - Resolved malformed entity_id errors for both device types with fallback patterns
- **v0.12.0**: ✅ **MULTI-DEVICE SUPPORT** - Complete Philips Fan Heater integration alongside Kogan support
- **v0.11.3**: ✅ **0.5°C PRECISION** - W100 buttons now adjust temperature by 0.5°C for finer control
- **v0.11.2**: ✅ **MQTT REMOVED** - Eliminated timeout errors by using only HA services
- **v0.11**: ✅ **ALL ISSUES FIXED** - Complete rewrite of OFF mode control & proper display bouncing fix
- **v0.10**: ⚠️ **INCOMPLETE FIX** - Claims to fix W100 display bouncing but root cause remains (see ROUTING_ANALYSIS.md)
- **v0.9**: Fixed Smart Thermostat PID compatibility - reverted to state checks instead of hvac_mode
- **v0.8**: Fixed W100 showing fan speed when thermostat in heat mode but idle
- **v0.7**: Fixed W100 display flip-flopping by using hvac_mode instead of state checks
- **v0.6**: Fixed W100 display mode logic - always uses external mode for custom values
- **v0.5**: Performance optimized with event-driven updates, removed debug logging
- **v0.4**: Beep control feature with three configurable modes
- **v0.3**: Temperature sensor workaround for stuck heater scenarios  
- **v0.2**: Performance optimization with parallel mode
- **v0.1**: Initial release with PID control and W100 integration

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits and Acknowledgments

- **[Smart Thermostat PID](https://github.com/ScratMan/HASmartThermostat)** by ScratMan - Core PID temperature control
- **[Tuya Local](https://github.com/make-all/tuya-local)** by make-all - Local control for Tuya devices
- **Home Assistant Community** - For continuous support and inspiration

## Support

If you find this project useful, consider:
- ⭐ Starring this repository
- 🐛 Reporting bugs or requesting features
- 💡 Contributing improvements
- 📖 Improving documentation

---

**Note**: This blueprint is designed for the Kogan Smarterhome bladeless heater fan but may be adaptable to other similar fan/heater combinations with appropriate entity modifications. 