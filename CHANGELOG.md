# Changelog

All notable changes to the W100 Climate Blueprint will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.11] - 2025-01-XX

### 🔴 CRITICAL FIXES - MAJOR RELEASE
- **FIXED**: OFF mode W100 control completely rewritten - buttons now fully functional
- **FIXED**: W100 display bouncing finally resolved - addressed actual root cause
- **FIXED**: Toggle button behavior corrected (OFF → HEAT, not OFF → COOL)
- **FIXED**: Direct fan speed control when thermostat is OFF

### Breaking Changes
- OFF mode now provides full W100 remote functionality (was completely broken)
- Toggle button behavior changed to correct logic (OFF ↔ HEAT cycle)
- Removed dead code for non-existent 'idle' state

### Technical Improvements
- Replaced overly broad trigger with specific state transitions
- Added debouncing (100ms) to prevent rapid successive updates
- Standardized state checking throughout blueprint
- Removed redundant and dead code sections

### Root Causes Addressed
- Line 222-223: Replaced broad trigger that fired on hvac_action changes
- Lines 479-482, 543-546: Added default cases for OFF state handling
- Lines 451-455: Fixed toggle logic for correct state transitions
- Lines 180-181: Removed non-existent 'idle' state from triggers

### User Experience
- W100 remote now fully functional in all thermostat modes
- No more display bouncing between temperature and fan speed
- Intuitive toggle behavior (OFF ↔ HEAT cycle)
- Seamless mode switching with appropriate display values

## [0.10] - 2025-01-03

### ⚠️ CRITICAL ISSUE - INCOMPLETE FIX
- **MISLEADING**: Claims to fix W100 display bouncing but root cause remains unfixed
- **ANALYSIS**: Detailed code analysis reveals the main trigger (line 222) was NOT removed
- **STATUS**: W100 display will continue bouncing between temperature and fan speed
- **EVIDENCE**: See ROUTING_ANALYSIS.md and TRIGGER_SIMULATION.md for proof

### What Was Actually Changed
- Removed hvac_action attribute trigger (lines 182-186) - this was NOT the main problem
- Added forced W100 sync after heat mode activation
- Enhanced display logic conditions

### Root Cause Still Present
- Line 222-223: w100_sync trigger still fires on ANY smart thermostat state change
- hvac_action bouncing (heating ↔ idle) continues to trigger display updates
- Default logic flaw causes fan speed display even when in heat mode
- Creates infinite cycle: hvac_action change → w100_sync → display flip → repeat

### Required Fix
- See PROPER_FIX.md for the actual solution needed in v0.11
- Must fix overly broad trigger and default logic conditions

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