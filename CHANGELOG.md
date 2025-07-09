# Changelog

All notable changes to the W100 Climate Blueprint will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10] - 2025-01-03

### Fixed
- **CRITICAL**: W100 display bouncing every few seconds resolved
- Removed conflicting hvac_action trigger that caused infinite loop
- The issue: hvac_action "idle" trigger fired while state was "heat", causing conflicting actions
- W100 display now stays stable in heat mode regardless of hvac_action (idle/heating)

### Root Cause
- Smart thermostat hvac_action bounces between "idle" and "heating" when satisfied
- This triggered "Smart Thermostat Idle/Off" action even when state was "heat"
- Created feedback loop: hvac_action→fan mode change→W100 sync→repeat

### Solution
- Removed hvac_action "idle" trigger from smart_thermostat_state ID
- Now only actual state changes ("idle"/"off") trigger fan mode changes
- W100 display remains consistent when thermostat is in heat mode but idle

## [0.9] - 2025-01-03

### Fixed
- **CRITICAL**: Smart Thermostat PID compatibility issue resolved
- Smart Thermostat PID component doesn't set hvac_mode attribute (it's null)
- Reverted v0.7/v0.8 changes that checked hvac_mode attribute back to checking state
- W100 display now correctly shows temperature setpoint when smart thermostat state is "heat"
- This fixes the issue where W100 showed fan speed instead of temperature in heat mode

### Technical Details
- Smart Thermostat PID sets state to "heat"/"cool"/"off" but hvac_mode remains null
- Blueprint now checks entity state instead of hvac_mode attribute for compatibility

## [0.8] - 2025-01-03

### Fixed
- W100 was still showing fan speed instead of temperature when thermostat in heat mode but idle
- Added condition to prevent "Smart Thermostat Idle/Off" action from running when hvac_mode is heat
- Added forced W100 display sync after heat mode is enabled to ensure correct display
- This ensures temperature is always shown when in heat mode, regardless of idle/heating state

## [0.7] - 2025-01-03

### Fixed
- W100 display was constantly switching between temperature and fan speed values
- Changed all state checks to use hvac_mode attribute instead of state
- The issue occurred when smart thermostat was in heat mode but idle state
- Now correctly shows temperature setpoint in heat mode regardless of idle/heating state

## [0.6] - 2025-01-03

### Fixed
- W100 display mode logic now correctly uses external mode for all custom values
- Previously, fan speed display in cool mode incorrectly used internal mode
- Internal mode only shows W100's own sensor readings and ignores MQTT values
- All display updates now properly use external mode to ensure custom values are shown

### Changed
- W100 always uses external sensor mode when displaying any custom values
- Simplified display logic - external mode for everything (temperature setpoint or fan speed)

## [0.5] - 2024-07-03

### Changed
- Removed all debug logging for cleaner operation
- Optimized W100 display sync to only update when values have changed
- Optimized humidity sync to only update when value has changed
- Removed unnecessary time pattern triggers for W100 sync (was every 5 seconds)
- Removed unnecessary time pattern trigger for humidity sync (was every 2 minutes)
- Reduced unnecessary MQTT traffic and network overhead

### Improved
- Better performance with event-driven updates instead of polling
- W100 display now only updates on actual value changes
- Cleaner logs without debug messages

## [0.4] - 2024-07-02

### Added
- Comprehensive beep control with three modes:
  - Enable Beep: Always beep
  - Disable Beep: Never beep  
  - On-Mode Change: Smart beeping for important events only
- Beeps on temperature setpoint changes and manual on/off
- New inputs: fan_beep_switch and beep_mode

### Changed
- Excludes beeps from automatic workarounds
- Maintains beep state across restarts

## [0.3] - 2024-07-02

### Added
- Automatic detection of stuck heater scenarios
- Temperature sensor workaround feature
- When fan sensor reads 30°C but room is cooler:
  - Temporarily turns off smart thermostat
  - Runs fan at speed 6 for 2 minutes
  - Forces air circulation for accurate temperature reading

### Fixed
- Prevents fan from stopping heating prematurely

## [0.2] - 2024-07-02

### Changed
- Changed mode from "single" to "parallel" (max: 8)

### Improved
- Enhanced responsiveness for button presses and state changes
- Better handling of concurrent triggers

## [0.1] - 2024-07-01

### Added
- Complete PID-controlled fan with W100 remote integration
- Smart thermostat integration
- W100 display sync for temperature/humidity
- Heat/cool mode switching
- Fan speed control in cool mode
- Temperature control in heat mode
- Idle speed and warm level management 