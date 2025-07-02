# Beep Control Feature Documentation

## Overview

Version 0.4 of the Office Fan W100 Smart Control blueprint introduces a comprehensive beep control feature that allows you to manage when your fan/heater makes audible feedback sounds.

## Configuration

### Required Entities

1. **Fan Beep Switch**: A switch entity that controls your fan's beep function
   - Example: `switch.bedroom_fan_beep`
   - This switch must be exposed by your fan's integration (e.g., via SmartIR or direct integration)

### Beep Modes

The blueprint offers three beep control modes:

#### 1. **Enable Beep**
- The beep switch is always ON
- Fan will beep for all its normal operations
- Suitable if you want full audible feedback

#### 2. **Disable Beep**
- The beep switch is always OFF
- Fan will never beep
- Suitable for quiet environments or nighttime use

#### 3. **On-Mode Change** (Default)
- Smart beeping only for important events
- Beeps when:
  - Smart thermostat temperature setpoint changes
  - Smart thermostat turns on/off (except during automatic workarounds)
- Does NOT beep for:
  - Routine operations
  - Stuck heater workaround actions
  - Normal fan speed adjustments

## How It Works

### Beep Sequence
When a beep is triggered in "On-Mode Change" mode:
1. Turn beep switch OFF
2. Wait 200ms
3. Turn beep switch ON (triggers beep)
4. Wait 500ms
5. Turn beep switch OFF (ready for next beep)

This sequence ensures a clean, single beep sound.

### Smart Context Detection
The blueprint intelligently detects when NOT to beep:
- During the stuck heater workaround (temperature sensor correction)
- When changes are made by automations rather than users

## Setup Instructions

1. **Identify Your Beep Switch Entity**
   - Check your fan's entities in Developer Tools → States
   - Look for a switch entity that controls beeping
   - Example: `switch.bedroom_fan_beep`

2. **Configure the Blueprint**
   - When setting up the automation using this blueprint:
   - Select your fan's beep switch in the "Fan Beep Switch" field
   - Choose your preferred "Beep Mode"

3. **Test Your Configuration**
   - Change the smart thermostat temperature - should beep in "On-Mode Change"
   - Turn the smart thermostat on/off - should beep in "On-Mode Change"
   - Let the temperature sensor workaround run - should NOT beep

## Example Use Cases

### Bedroom Setup
- Use "Disable Beep" or "On-Mode Change" for minimal noise
- Beeps only for manual temperature adjustments

### Living Room Setup
- Use "On-Mode Change" for feedback on manual changes
- Silent during automatic operations

### Office Setup
- Use "Enable Beep" if you want full feedback
- Helpful to know when any setting changes

## Troubleshooting

### Fan Doesn't Beep
1. Check if beep switch entity is correct
2. Verify beep switch actually controls the fan's beep
3. Check automation logs for beep-related errors

### Fan Beeps Too Much
1. Switch from "Enable Beep" to "On-Mode Change"
2. Or use "Disable Beep" for complete silence

### Beeps During Workarounds
- This shouldn't happen with proper setup
- Check automation traces to debug

## Technical Details

The beep control integrates with:
- Smart thermostat state changes
- Temperature setpoint modifications  
- Manual on/off operations
- Excludes automatic workaround operations

The feature maintains beep state across:
- System restarts
- Automation reloads
- Mode changes 