# Changelog

All notable changes to the W100 Climate Blueprint will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5] - 2024-12-29

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

## [0.4] - 2024-12-29

## v0.4 - Beep Control Feature
- Added comprehensive beep control with three modes:
  - Enable Beep: Always beep
  - Disable Beep: Never beep  
  - On-Mode Change: Smart beeping for important events only
- Beeps on temperature setpoint changes and manual on/off
- Excludes beeps from automatic workarounds
- Added fan_beep_switch and beep_mode inputs
- Maintains beep state across restarts

## v0.3 - Temperature Sensor Workaround
- Added automatic detection of stuck heater scenarios
- When fan sensor reads 30°C but room is cooler:
  - Temporarily turns off smart thermostat
  - Runs fan at speed 6 for 2 minutes
  - Forces air circulation for accurate temperature reading
- Prevents fan from stopping heating prematurely

## v0.2 - Performance Optimization
- Changed mode from "single" to "parallel" (max: 8)
- Improved responsiveness for button presses and state changes
- Better handling of concurrent triggers

## v0.1 - Initial Release
- Complete PID-controlled fan with W100 remote integration
- Smart thermostat integration
- W100 display sync for temperature/humidity
- Heat/cool mode switching
- Fan speed control in cool mode
- Temperature control in heat mode
- Idle speed and warm level management 