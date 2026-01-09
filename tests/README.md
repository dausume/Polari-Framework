# Polari Framework Test Suite

This directory contains the comprehensive test suite for the Polari Framework, including tests for all CRUDE (Create, Read, Update, Delete, Event) API operations.

## Test Organization

```
tests/
├── README.md              # This file
├── test_crude_api.py      # CRUDE API endpoint tests
└── (future test files)    # Additional test modules
```

## Running Tests

### Option 1: Using Docker (Recommended)

Run tests in an isolated Docker environment:

```bash
# Build and run tests
docker compose -f docker-compose.test.yml up --build

# Run tests and exit when complete
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Clean up after tests
docker compose -f docker-compose.test.yml down
```

### Option 2: Using Python Directly

Run tests locally on your machine:

```bash
# From the framework root directory
python3 run_tests.py

# Or run specific test file
python3 tests/test_crude_api.py

# Or use unittest discovery
python3 -m unittest discover -s tests -p "test*.py"
```

### Option 3: Run Individual Test Cases

```bash
# Run a specific test class
python3 -m unittest tests.test_crude_api.CRUDEAPITestCase

# Run a specific test method
python3 -m unittest tests.test_crude_api.CRUDEAPITestCase.test_01_create_single_instance
```

## Test Coverage

### CRUDE API Tests (`test_crude_api.py`)

Comprehensive tests for all CRUDE operations:

#### CREATE (POST) Tests
- ✓ Single instance creation
- ✓ Required parameter validation
- ✓ Invalid parameter rejection

#### READ (GET) Tests
- ✓ Retrieve all instances
- ✓ Verify returned data correctness
- ✓ JSON response structure validation

#### UPDATE (PUT) Tests
- ✓ Single attribute update
- ✓ Multiple attribute updates
- ✓ Validation of unchanged attributes

#### DELETE Tests
- ✓ Instance deletion
- ✓ Non-existent instance handling
- ✓ Cleanup verification

#### EVENT Tests
- ✓ Method existence verification
- ✓ Method execution
- ✓ Default parameter handling
- ✓ Return value validation

#### Integration Tests
- ✓ Full CRUDE cycle (Create → Read → Update → Delete)
- ✓ Special type serialization
- ✓ Endpoint registration
- ✓ HTTP method availability

## Test Structure

Each test follows this pattern:

```python
def test_XX_descriptive_name(self):
    """Test description"""
    print("\n[TEST] What this test does")

    # Arrange - Set up test data
    # Act - Perform the operation
    # Assert - Verify the results

    print(f"✓ What was verified")
```

## Writing New Tests

### Creating a New Test File

1. Create file in `tests/` directory with name `test_*.py`
2. Import required modules:
   ```python
   import unittest
   from objectTreeManagerDecorators import managerObject
   ```

3. Create test class inheriting from `unittest.TestCase`:
   ```python
   class MyTestCase(unittest.TestCase):
       @classmethod
       def setUpClass(cls):
           # One-time setup for all tests
           pass

       def test_something(self):
           # Individual test
           pass
   ```

### Test Best Practices

- **Naming**: Use descriptive test names: `test_XX_what_is_being_tested`
- **Documentation**: Add docstrings explaining what each test verifies
- **Isolation**: Each test should be independent and not rely on other tests
- **Cleanup**: Use `setUp()` and `tearDown()` methods for test cleanup
- **Assertions**: Use specific assertion methods (`assertEqual`, `assertIn`, etc.)
- **Output**: Add print statements to show test progress and results

### Example Test

```python
def test_01_create_instance(self):
    """Test creating a new instance"""
    print("\n[TEST] Creating test instance")

    # Create instance
    obj = TestObject(name="test", value=42, manager=self.manager)

    # Verify it was created
    self.assertIsNotNone(obj.id)
    self.assertIn(obj.id, self.manager.objectTables['TestObject'])

    print(f"✓ Instance created with ID: {obj.id}")
```

## Development vs Test Modes

### Development Mode (docker-compose.yml)
- Runs the application server (`initLocalhostPolariServer.py`)
- Exposes API endpoints
- **Does NOT run tests automatically**
- Used for development and debugging

```bash
# Start development server
docker compose up
```

### Test Mode (docker-compose.test.yml)
- Runs the test suite (`run_tests.py`)
- Exits after tests complete
- **Separate from development environment**
- Used for CI/CD and validation

```bash
# Run tests only
docker compose -f docker-compose.test.yml up --build
```

## Test Configuration Files

### `Dockerfile.test`
- Separate Dockerfile specifically for testing
- Based on same foundation as main Dockerfile
- Sets `DEPLOY_ENV=test`
- Runs `run_tests.py` by default

### `docker-compose.test.yml`
- Test-specific Docker Compose configuration
- Isolated from development environment
- Exits when tests complete
- Optional volume mount for test results

### `run_tests.py`
- Main test runner script
- Discovers all tests in `tests/` directory
- Runs all tests with verbose output
- Reports summary statistics
- Returns exit code (0 = success, 1 = failure)

## Continuous Integration

The test suite is designed to integrate with CI/CD pipelines:

```yaml
# Example CI configuration
test:
  script:
    - docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
  artifacts:
    paths:
      - test-results/
```

## Test Output

Tests produce detailed output:

```
======================================================================
POLARI FRAMEWORK - CRUDE API TEST SUITE
======================================================================

Testing all CRUDE operations:
  • CREATE (POST) - Instance creation
  • READ (GET) - Instance retrieval
  • UPDATE (PUT) - Instance modification
  • DELETE - Instance deletion
  • EVENT - Method execution
======================================================================

test_01_create_single_instance (tests.test_crude_api.CRUDEAPITestCase)
[TEST] Creating single TestObject instance via POST ... ok

...

======================================================================
TEST SUMMARY
======================================================================
Tests Run: 13
Successes: 13
Failures: 0
Errors: 0
======================================================================
```

## Troubleshooting

### Tests Fail to Import Modules

Ensure Python path includes the framework root:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### Docker Build Fails

Make sure you're in the framework root directory:

```bash
cd /path/to/polari-framework
docker compose -f docker-compose.test.yml up --build
```

### Tests Hang or Timeout

Check that no background processes are blocking:

```bash
# Clean up Docker containers
docker compose -f docker-compose.test.yml down
docker system prune
```

## Future Enhancements

Planned improvements to the test suite:

- [ ] Add code coverage reporting
- [ ] Add performance/load testing
- [ ] Add integration tests with frontend
- [ ] Add database persistence tests
- [ ] Add concurrent request tests
- [ ] Add security/authentication tests
- [ ] Generate HTML test reports
- [ ] Add test fixtures and factories

## Contributing

When adding new features to Polari Framework:

1. Write tests FIRST (TDD approach)
2. Ensure all existing tests pass
3. Add new tests for new functionality
4. Update this README if adding new test categories
5. Run full test suite before submitting changes

```bash
# Always run full test suite before committing
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

---

**Remember**: Tests are documentation. Write clear, descriptive tests that explain what the system should do.
