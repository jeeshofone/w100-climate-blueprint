# W100 Smart Control - Testing Guide

This document describes the comprehensive testing approach for the W100 Smart Control integration, following HACS and Home Assistant best practices.

## Testing Structure

The testing follows Home Assistant and HACS standards with all tests located in the `tests/` directory:

```
tests/
├── conftest.py                          # Global test configuration and fixtures
├── pytest.ini                          # Pytest configuration
├── test_config_flow.py                  # Configuration flow tests
├── test_coordinator.py                  # Coordinator unit tests
├── test_climate.py                      # Climate entity tests
├── test_sensor.py                       # Sensor platform tests
├── test_switch.py                       # Switch platform tests
├── test_device_trigger.py               # Device trigger tests
├── test_integration.py                  # End-to-end integration tests
└── test_*.py                           # Additional test modules
```

## Test Infrastructure

### Dependencies

Testing dependencies are defined in `requirements_test.txt`:

- **pytest**: Core testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **pytest-homeassistant-custom-component**: Home Assistant testing utilities
- **homeassistant**: Home Assistant core for testing
- **Code quality tools**: black, isort, flake8, mypy

### Configuration

**pytest.ini** configuration:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --cov=custom_components.w100_smart_control --cov-report=term-missing --cov-report=html
asyncio_mode = auto
```

### Global Fixtures (conftest.py)

The `conftest.py` file provides comprehensive fixtures for testing:

- **mock_hass**: Mock Home Assistant instance
- **mock_config_entry**: Mock configuration entry
- **mock_entity_registry**: Mock entity registry
- **mock_device_registry**: Mock device registry
- **mock_mqtt**: Mock MQTT client
- **mock_climate_entity**: Mock climate entity states
- **mock_w100_devices**: Mock W100 device discovery
- **sample_config_data**: Sample configuration for testing

## Running Tests

### Local Testing

#### Using the Test Runner Script
```bash
# Run all tests with coverage
python run_tests.py --all

# Run tests only
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Run linting
python run_tests.py --lint

# Run type checking
python run_tests.py --type-check
```

#### Using pytest Directly
```bash
# Change to tests directory
cd tests

# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=../custom_components/w100_smart_control --cov-report=term-missing

# Run specific test file
python -m pytest test_config_flow.py -v

# Run specific test
python -m pytest test_config_flow.py::test_user_step_with_mqtt -v
```

### GitHub Actions

Tests run automatically in GitHub Actions:

#### Test Workflow (.github/workflows/test.yml)
- Runs on Python 3.11 and 3.12
- Installs dependencies and runs full test suite
- Generates coverage reports
- Runs code quality checks (black, isort, flake8, mypy)

#### Validation Workflow (.github/workflows/validate.yml)
- HACS validation using hacs/action
- Home Assistant Hassfest validation
- Breaking changes detection

#### Hassfest Workflow (.github/workflows/hassfest.yml)
- Home Assistant integration validation
- Manifest validation
- Breaking changes check

## Test Categories

### 1. Configuration Flow Tests

**File**: `test_config_flow.py`

Tests the multi-step configuration process:

```python
async def test_user_step_with_mqtt(config_flow, mock_mqtt_available):
    """Test user step when MQTT is available."""
    result = await config_flow.async_step_user({})
    assert result["step_id"] == "device_selection"

async def test_device_selection_valid_input(config_flow, mock_w100_devices):
    """Test device selection with valid input."""
    user_input = {"w100_device_name": "living_room_w100"}
    result = await config_flow.async_step_device_selection(user_input)
    assert result["step_id"] == "climate_selection"
```

**Coverage**:
- All configuration steps (user, device_selection, climate_selection, etc.)
- Input validation and error handling
- MQTT availability checking
- Device discovery and validation
- Entity selection and validation

### 2. Coordinator Tests

**File**: `test_coordinator.py`

Tests the core coordinator functionality:

```python
async def test_coordinator_setup(mock_hass, mock_config_entry):
    """Test coordinator setup."""
    coordinator = W100Coordinator(mock_hass, mock_config_entry)
    await coordinator.async_setup()
    assert coordinator.last_update_success

async def test_mqtt_message_handling(coordinator, mock_mqtt):
    """Test MQTT message handling."""
    await coordinator.async_handle_w100_action("toggle", "test_device")
    # Verify action was processed correctly
```

**Coverage**:
- Coordinator initialization and setup
- MQTT message handling and subscriptions
- Device state management
- Multi-device support
- Error handling and recovery

### 3. Entity Tests

**Files**: `test_climate.py`, `test_sensor.py`, `test_switch.py`

Tests individual entity platforms:

```python
async def test_climate_entity_hvac_mode(mock_hass, mock_coordinator):
    """Test climate entity HVAC mode setting."""
    entity = W100ClimateEntity(mock_coordinator, mock_config_entry, "climate.test", "test_device")
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    # Verify mode was set correctly

async def test_sensor_entity_state(mock_hass, mock_coordinator):
    """Test sensor entity state reporting."""
    sensor = W100HumiditySensor(mock_coordinator, mock_config_entry, "test_device")
    assert sensor.state == expected_humidity_value
```

**Coverage**:
- Entity initialization and setup
- State reporting and attributes
- Service calls and operations
- Device info and registry integration
- Error handling

### 4. Integration Tests

**File**: `test_integration.py`

Tests end-to-end functionality:

```python
async def test_complete_setup_flow(mock_hass):
    """Test complete integration setup."""
    # Test full setup from config entry to working entities
    entry = await setup_integration(mock_hass, sample_config)
    assert entry.state == ConfigEntryState.LOADED
    
    # Verify entities are created
    climate_entity = mock_hass.states.get("climate.w100_test")
    assert climate_entity is not None

async def test_w100_button_to_climate_action(mock_hass, integration_setup):
    """Test W100 button press results in climate action."""
    # Simulate W100 button press
    await simulate_mqtt_message("zigbee2mqtt/test_w100/action", {"action": "toggle"})
    
    # Verify climate entity state changed
    climate_state = mock_hass.states.get("climate.test")
    assert climate_state.state == "heat"
```

**Coverage**:
- Complete integration setup and teardown
- End-to-end functionality testing
- MQTT to climate entity communication
- Multi-device scenarios
- Error recovery and edge cases

## Mocking Strategy

### Home Assistant Components

```python
@pytest.fixture
def mock_hass():
    """Mock Home Assistant with essential services."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.states = Mock()
    hass.services = Mock()
    hass.services.has_service.return_value = True
    hass.services.async_call = AsyncMock()
    return hass
```

### MQTT Integration

```python
@pytest.fixture
def mock_mqtt():
    """Mock MQTT client for testing."""
    with patch('homeassistant.components.mqtt.async_get_mqtt') as mock:
        mqtt_client = Mock()
        mqtt_client.async_subscribe = AsyncMock()
        mqtt_client.async_publish = AsyncMock()
        mock.return_value = mqtt_client
        yield mqtt_client
```

### Entity Registry

```python
@pytest.fixture
def mock_entity_registry():
    """Mock entity registry for testing."""
    registry = Mock(spec=EntityRegistry)
    registry.entities = {}
    registry.async_get_or_create = Mock()
    return registry
```

## Coverage Requirements

### Minimum Coverage Targets
- **Overall**: 85% minimum
- **Configuration Flow**: 95% (critical user-facing code)
- **Coordinator**: 90% (core functionality)
- **Entities**: 85% (platform implementations)
- **Error Handling**: 95% (critical for reliability)

### Coverage Reporting

Coverage reports are generated in multiple formats:
- **Terminal**: Real-time coverage during test runs
- **HTML**: Detailed coverage report in `htmlcov/` directory
- **XML**: For CI/CD integration and codecov

```bash
# Generate coverage report
python -m pytest --cov=custom_components.w100_smart_control --cov-report=html

# View HTML report
open htmlcov/index.html
```

## Code Quality

### Automated Checks

All code quality checks run in GitHub Actions:

```bash
# Format checking
black --check --diff custom_components/

# Import sorting
isort --check-only --diff custom_components/

# Linting
flake8 custom_components/

# Type checking
mypy custom_components/ --ignore-missing-imports
```

### Pre-commit Hooks

Recommended pre-commit configuration:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

## Continuous Integration

### GitHub Actions Integration

Tests run automatically on:
- **Push** to main/develop branches
- **Pull requests** to main/develop
- **Scheduled** daily runs
- **Manual** workflow dispatch

### Test Matrix

Tests run on multiple Python versions:
- Python 3.11 (minimum supported)
- Python 3.12 (latest stable)

### Failure Handling

- Tests must pass on all Python versions
- Coverage must meet minimum thresholds
- Code quality checks must pass
- HACS validation must pass

## Best Practices

### Test Organization

1. **One test file per module**: Each component has its own test file
2. **Descriptive test names**: Test names clearly describe what is being tested
3. **Arrange-Act-Assert**: Clear test structure
4. **Proper mocking**: Mock external dependencies, test internal logic

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality properly."""
    result = await async_function()
    assert result == expected_value
```

### Fixture Usage

```python
def test_with_fixtures(mock_hass, mock_config_entry, mock_coordinator):
    """Use fixtures for consistent test setup."""
    # Test implementation using provided fixtures
```

### Error Testing

```python
async def test_error_handling():
    """Test error conditions explicitly."""
    with pytest.raises(ExpectedError):
        await function_that_should_fail()
```

## Debugging Tests

### Running Individual Tests

```bash
# Run single test with verbose output
python -m pytest test_config_flow.py::test_user_step_with_mqtt -v -s

# Run with debugging
python -m pytest test_config_flow.py::test_user_step_with_mqtt -v -s --pdb
```

### Test Output

```bash
# Capture print statements
python -m pytest -s

# Show local variables on failure
python -m pytest -l

# Stop on first failure
python -m pytest -x
```

## Maintenance

### Adding New Tests

1. Create test file in `tests/` directory
2. Import necessary fixtures from `conftest.py`
3. Follow naming conventions (`test_*.py`)
4. Add appropriate coverage
5. Update this documentation

### Updating Fixtures

1. Modify `conftest.py` for global fixtures
2. Add module-specific fixtures in test files
3. Ensure backward compatibility
4. Update dependent tests

### Performance Considerations

- Use appropriate mocking to avoid slow external calls
- Minimize fixture setup/teardown overhead
- Run tests in parallel when possible
- Profile slow tests and optimize

## Integration with HACS

### HACS Requirements

The testing setup meets all HACS requirements:
- ✅ Tests in `tests/` directory
- ✅ GitHub Actions for validation
- ✅ Proper Home Assistant integration testing
- ✅ Code quality checks
- ✅ Coverage reporting

### Validation

HACS validation includes:
- Repository structure validation
- Manifest validation
- Code quality checks
- Test execution verification

This comprehensive testing approach ensures the W100 Smart Control integration meets the highest standards for reliability, maintainability, and HACS compliance.