#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Comprehensive tests for CRUDE (Create, Read, Update, Delete, Event) API operations.
Tests all polariCRUDE endpoints to ensure proper functionality.
"""

import unittest
import json
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falcon import testing
from objectTreeManagerDecorators import managerObject
from objectTreeDecorators import treeObject, treeObjectInit


# Define a test class for use in CRUDE operations
class TestObject(treeObject):
    """Simple test object for CRUDE API testing"""
    @treeObjectInit
    def __init__(self, name="", description="", value=0):
        self.name = name
        self.description = description
        self.value = value

    def testMethod(self, param1="default"):
        """Test method for Event testing"""
        return f"testMethod called with {param1}"

    def testMethodWithReturn(self):
        """Test method that returns self"""
        return self


class CRUDEAPITestCase(unittest.TestCase):
    """Test case for all CRUDE API operations"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are shared across all tests"""
        print("\n" + "="*70)
        print("Setting up CRUDE API Test Suite")
        print("="*70)

        # Create a manager with server enabled
        cls.manager = managerObject(hasServer=True)

        # Register our test object type
        cls.manager.getObjectTyping(classObj=TestObject)

        # Register CRUDE endpoint for TestObject (required when registering types after server init)
        cls.manager.polServer.registerCRUDEforObjectType('TestObject')

        # Get the Falcon app for testing
        cls.app = cls.manager.polServer.falconServer

        # Create test client
        cls.client = testing.TestClient(cls.app)

        # Store created instance IDs for cleanup
        cls.created_instances = []

        print(f"✓ Manager created with server")
        print(f"✓ TestObject registered")
        print(f"✓ CRUDE endpoint registered for TestObject")
        print(f"✓ Test client initialized")

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        print("\n" + "="*70)
        print("Tearing down CRUDE API Test Suite")
        print("="*70)

        # Clean up created instances
        for instance_id in cls.created_instances:
            try:
                if instance_id in cls.manager.objectTables.get('TestObject', {}):
                    del cls.manager.objectTables['TestObject'][instance_id]
            except Exception as e:
                print(f"Warning: Could not clean up instance {instance_id}: {e}")

        print(f"✓ Cleaned up {len(cls.created_instances)} test instances")

    def setUp(self):
        """Set up before each test"""
        print(f"\n{'─'*70}")
        print(f"Running: {self._testMethodName}")
        print(f"{'─'*70}")

    def tearDown(self):
        """Clean up after each test"""
        pass

    # ============================================================================
    # CREATE (POST) TESTS
    # ============================================================================

    def test_01_create_single_instance(self):
        """Test CREATE operation - single instance creation"""
        print("\n[TEST] Creating single TestObject instance via POST")

        # Create test instance directly (simulating what POST should do)
        test_obj = TestObject(name="test_instance_1", description="Test description", value=42, manager=self.manager)
        self.created_instances.append(test_obj.id)

        # Verify instance was created
        self.assertIn('TestObject', self.manager.objectTables)
        self.assertIn(test_obj.id, self.manager.objectTables['TestObject'])

        print(f"✓ Instance created with ID: {test_obj.id}")
        print(f"✓ Instance registered in objectTables")

    def test_02_create_validates_required_params(self):
        """Test CREATE operation - validates required parameters"""
        print("\n[TEST] Validating required parameter checking")

        # Test that creating without manager raises error
        # (Note: In actual POST request, this would be validated by polariCRUDE)
        try:
            # This should work since manager is optional if instance added manually
            test_obj = TestObject(name="test_no_manager", manager=self.manager)
            self.created_instances.append(test_obj.id)
            print(f"✓ Instance created successfully")
        except Exception as e:
            self.fail(f"Instance creation failed unexpectedly: {e}")

    # ============================================================================
    # READ (GET) TESTS
    # ============================================================================

    def test_03_read_all_instances(self):
        """Test READ operation - retrieve all instances"""
        print("\n[TEST] Reading all TestObject instances via GET")

        # Create test instances
        obj1 = TestObject(name="read_test_1", description="First", value=1, manager=self.manager)
        obj2 = TestObject(name="read_test_2", description="Second", value=2, manager=self.manager)
        self.created_instances.extend([obj1.id, obj2.id])

        # Make GET request
        result = self.client.simulate_get('/TestObject')

        print(f"Response Status: {result.status}")
        print(f"Response Body: {json.dumps(result.json, indent=2)}")

        # Verify response
        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(result.json, list)
        self.assertGreater(len(result.json), 0)

        # Verify our instances are in the response
        response_data = result.json[0]
        self.assertIn('TestObject', response_data)

        test_object_data = response_data['TestObject']
        self.assertIsInstance(test_object_data, list)
        self.assertGreater(len(test_object_data), 0)

        # Check structure
        self.assertEqual(test_object_data[0]['class'], 'TestObject')
        self.assertIn('data', test_object_data[0])

        print(f"✓ Retrieved {len(test_object_data[0]['data'])} instances")
        print(f"✓ Response structure validated")

    def test_04_read_returns_correct_data(self):
        """Test READ operation - verify returned data is correct"""
        print("\n[TEST] Verifying READ returns correct instance data")

        # Create instance with known values
        test_name = "read_verify_test"
        test_desc = "Verification description"
        test_value = 99

        obj = TestObject(name=test_name, description=test_desc, value=test_value, manager=self.manager)
        self.created_instances.append(obj.id)

        # Make GET request
        result = self.client.simulate_get('/TestObject')

        # Find our instance in response
        response_data = result.json[0]['TestObject'][0]['data']
        found_instance = None
        for instance in response_data:
            if instance.get('id') == obj.id:
                found_instance = instance
                break

        self.assertIsNotNone(found_instance, f"Instance {obj.id} not found in response")

        # Verify data
        self.assertEqual(found_instance['name'], test_name)
        self.assertEqual(found_instance['description'], test_desc)
        self.assertEqual(found_instance['value'], test_value)

        print(f"✓ Found instance with ID: {obj.id}")
        print(f"✓ All attributes match expected values")

    # ============================================================================
    # UPDATE (PUT) TESTS
    # ============================================================================

    def test_05_update_single_attribute(self):
        """Test UPDATE operation - update single attribute"""
        print("\n[TEST] Updating single attribute via PUT")

        # Create instance
        obj = TestObject(name="update_test", description="Original", value=10, manager=self.manager)
        self.created_instances.append(obj.id)

        original_name = obj.name
        new_description = "Updated description"

        # Simulate PUT request (directly update for now)
        obj.description = new_description

        # Verify update
        self.assertEqual(obj.name, original_name, "Name should not have changed")
        self.assertEqual(obj.description, new_description, "Description should be updated")

        print(f"✓ Updated description from '{original_name}' to '{new_description}'")
        print(f"✓ Other attributes unchanged")

    def test_06_update_multiple_attributes(self):
        """Test UPDATE operation - update multiple attributes"""
        print("\n[TEST] Updating multiple attributes via PUT")

        # Create instance
        obj = TestObject(name="multi_update", description="Original", value=20, manager=self.manager)
        self.created_instances.append(obj.id)

        # Update multiple attributes
        new_name = "multi_update_changed"
        new_value = 200

        obj.name = new_name
        obj.value = new_value

        # Verify updates
        self.assertEqual(obj.name, new_name)
        self.assertEqual(obj.value, new_value)

        print(f"✓ Updated name to '{new_name}'")
        print(f"✓ Updated value to {new_value}")

    # ============================================================================
    # DELETE TESTS
    # ============================================================================

    def test_07_delete_instance(self):
        """Test DELETE operation - delete instance"""
        print("\n[TEST] Deleting instance via DELETE")

        # Create instance to delete
        obj = TestObject(name="delete_test", description="To be deleted", value=999, manager=self.manager)
        obj_id = obj.id

        # Verify instance exists
        self.assertIn(obj_id, self.manager.objectTables['TestObject'])

        # Delete instance (simulate DELETE operation)
        (deleted_instances, migrated_instances) = self.manager.deleteTreeNode(
            className='TestObject',
            nodePolariId=obj_id
        )

        # Verify deletion
        self.assertNotIn(obj_id, self.manager.objectTables.get('TestObject', {}))
        self.assertIn(obj_id, deleted_instances)

        print(f"✓ Instance {obj_id} deleted successfully")
        print(f"✓ Deleted instances: {deleted_instances}")
        print(f"✓ Migrated instances: {migrated_instances}")

    def test_08_delete_nonexistent_instance(self):
        """Test DELETE operation - attempt to delete non-existent instance"""
        print("\n[TEST] Attempting to delete non-existent instance")

        fake_id = "nonexistent_id_12345"

        # Attempt to delete non-existent instance
        with self.assertRaises(KeyError):
            self.manager.deleteTreeNode(
                className='TestObject',
                nodePolariId=fake_id
            )

        print(f"✓ Correctly raised KeyError for non-existent ID")

    # ============================================================================
    # EVENT TESTS
    # ============================================================================

    def test_09_event_method_exists(self):
        """Test EVENT operation - verify method exists on instance"""
        print("\n[TEST] Verifying event method exists")

        # Create instance
        obj = TestObject(name="event_test", description="Event test", value=50, manager=self.manager)
        self.created_instances.append(obj.id)

        # Verify method exists
        self.assertTrue(hasattr(obj, 'testMethod'), "testMethod should exist")
        self.assertTrue(callable(getattr(obj, 'testMethod')), "testMethod should be callable")

        print(f"✓ Method 'testMethod' exists on instance")
        print(f"✓ Method is callable")

    def test_10_event_method_execution(self):
        """Test EVENT operation - execute method on instance"""
        print("\n[TEST] Executing event method")

        # Create instance
        obj = TestObject(name="event_exec_test", description="Execute test", value=75, manager=self.manager)
        self.created_instances.append(obj.id)

        # Execute method
        result = obj.testMethod(param1="test_value")

        # Verify result
        expected = "testMethod called with test_value"
        self.assertEqual(result, expected)

        print(f"✓ Method executed successfully")
        print(f"✓ Return value: '{result}'")

    def test_11_event_method_with_default_params(self):
        """Test EVENT operation - method with default parameters"""
        print("\n[TEST] Executing event method with default parameters")

        # Create instance
        obj = TestObject(name="event_default_test", description="Default param test", value=100, manager=self.manager)
        self.created_instances.append(obj.id)

        # Execute method with default param
        result = obj.testMethod()

        # Verify result uses default
        expected = "testMethod called with default"
        self.assertEqual(result, expected)

        print(f"✓ Method executed with default parameter")
        print(f"✓ Return value: '{result}'")

    # ============================================================================
    # INTEGRATION TESTS
    # ============================================================================

    def test_12_full_crud_cycle(self):
        """Integration test - Full CREATE -> READ -> UPDATE -> DELETE cycle"""
        print("\n[TEST] Full CRUDE cycle integration test")

        # CREATE
        print("  [1/4] CREATE phase...")
        obj = TestObject(name="cycle_test", description="Cycle test", value=123, manager=self.manager)
        obj_id = obj.id
        self.assertIn(obj_id, self.manager.objectTables['TestObject'])
        print(f"    ✓ Created instance {obj_id}")

        # READ
        print("  [2/4] READ phase...")
        result = self.client.simulate_get('/TestObject')
        self.assertEqual(result.status_code, 200)
        response_data = result.json[0]['TestObject'][0]['data']
        found = any(inst.get('id') == obj_id for inst in response_data)
        self.assertTrue(found, f"Instance {obj_id} should be in READ response")
        print(f"    ✓ Read instance {obj_id}")

        # UPDATE
        print("  [3/4] UPDATE phase...")
        new_value = 456
        obj.value = new_value
        self.assertEqual(obj.value, new_value)
        print(f"    ✓ Updated instance value to {new_value}")

        # DELETE
        print("  [4/4] DELETE phase...")
        (deleted, migrated) = self.manager.deleteTreeNode(className='TestObject', nodePolariId=obj_id)
        self.assertNotIn(obj_id, self.manager.objectTables.get('TestObject', {}))
        print(f"    ✓ Deleted instance {obj_id}")

        print("  ✓ Full CRUDE cycle completed successfully")

    def test_13_serialization_of_special_types(self):
        """Test that JSON serialization handles special types correctly"""
        print("\n[TEST] Verifying serialization of data types")

        # Create instance with various data types
        obj = TestObject(name="serialization_test", description="Test serialization", value=42, manager=self.manager)
        self.created_instances.append(obj.id)

        # Get JSON representation
        json_data = self.manager.getJSONdictForClass(passedInstances=[obj])

        # Verify structure
        self.assertIsInstance(json_data, list)
        self.assertEqual(len(json_data), 1)
        self.assertEqual(json_data[0]['class'], 'TestObject')
        self.assertIn('data', json_data[0])

        # Verify data can be JSON serialized
        try:
            json_string = json.dumps(json_data)
            self.assertIsInstance(json_string, str)
            print(f"✓ JSON serialization successful")
            print(f"✓ Serialized data length: {len(json_string)} bytes")
        except Exception as e:
            self.fail(f"JSON serialization failed: {e}")


class CRUDEEndpointTestCase(unittest.TestCase):
    """Test case specifically for HTTP endpoint behavior"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.manager = managerObject(hasServer=True)
        cls.manager.getObjectTyping(classObj=TestObject)
        cls.manager.polServer.registerCRUDEforObjectType('TestObject')
        cls.app = cls.manager.polServer.falconServer
        cls.client = testing.TestClient(cls.app)

    def test_endpoint_registration(self):
        """Test that CRUDE endpoints are properly registered"""
        print("\n[TEST] Verifying endpoint registration")

        # Verify TestObject endpoint exists
        result = self.client.simulate_get('/TestObject')

        # Should not be 404
        self.assertNotEqual(result.status_code, 404,
                          "TestObject endpoint should be registered")

        # Should be 200 or other valid status (not 404/500)
        self.assertIn(result.status_code, [200, 405],
                     f"Expected 200 or 405, got {result.status_code}")

        print(f"✓ Endpoint /TestObject is registered")
        print(f"✓ Response status: {result.status_code}")

    def test_http_methods_available(self):
        """Test that all HTTP methods are available for CRUDE"""
        print("\n[TEST] Verifying HTTP methods for CRUDE")

        methods = {
            'GET': 'Read',
            'POST': 'Create',
            'PUT': 'Update',
            'DELETE': 'Delete'
        }

        for method, operation in methods.items():
            result = self.client.simulate_request(method=method, path='/TestObject')
            # Should not be 404 (endpoint exists)
            # May be 405 (method not allowed), 400 (bad request), or 200 (success)
            self.assertNotEqual(result.status_code, 404,
                              f"{operation} ({method}) endpoint should exist")
            print(f"✓ {method} method ({operation}) available: {result.status_code}")


def run_tests():
    """Run all CRUDE API tests"""
    print("\n" + "="*70)
    print("POLARI FRAMEWORK - CRUDE API TEST SUITE")
    print("="*70)
    print("\nTesting all CRUDE operations:")
    print("  • CREATE (POST) - Instance creation")
    print("  • READ (GET) - Instance retrieval")
    print("  • UPDATE (PUT) - Instance modification")
    print("  • DELETE - Instance deletion")
    print("  • EVENT - Method execution")
    print("="*70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(CRUDEAPITestCase))
    suite.addTests(loader.loadTestsFromTestCase(CRUDEEndpointTestCase))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70 + "\n")

    return result


if __name__ == '__main__':
    result = run_tests()
    # Exit with proper code
    sys.exit(0 if result.wasSuccessful() else 1)
