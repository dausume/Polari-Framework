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
Comprehensive tests for the API Profiler component.

Tests:
1. Analyze response with Polari typing
2. Nested structure analysis
3. Match against Polari API templates
4. Detect multiple object types
5. Create Polari class from profile
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

from polariApiProfiler.apiProfile import APIProfile
from polariApiProfiler.apiProfiler import APIProfiler
from polariApiProfiler.profileMatcher import ProfileMatcher
from polariApiProfiler import profileTemplates


class APIProfilerTypingTestCase(unittest.TestCase):
    """Test case for API profiler integration with Polari typing system."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are shared across all tests."""
        print("\n" + "="*70)
        print("Setting up API Profiler Test Suite")
        print("="*70)

        # Create a manager with server enabled
        cls.manager = managerObject(hasServer=True)

        # Get the Falcon app for testing
        cls.app = cls.manager.polServer.falconServer

        # Create test client
        cls.client = testing.TestClient(cls.app)

        # Create profiler and matcher instances
        cls.profiler = APIProfiler(manager=cls.manager)
        cls.matcher = ProfileMatcher(manager=cls.manager)

        print("✓ Manager created with server")
        print("✓ API Profiler components initialized")
        print("✓ Test client initialized")

    def setUp(self):
        """Set up before each test."""
        print(f"\n{'─'*70}")
        print(f"Running: {self._testMethodName}")
        print(f"{'─'*70}")

    # ============================================================================
    # TEST 1: Analyze response with Polari typing
    # ============================================================================

    def test_01_analyze_with_polari_typing(self):
        """Test that API profiler correctly uses Polari's polyTypedObject system."""
        print("\n[TEST] Analyzing response with Polari typing system")

        # Sample API response
        sample_response = {
            'id': 'user_123',
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': 30,
            'active': True,
            'tags': ['admin', 'developer'],
            'metadata': {'created': '2024-01-01', 'tier': 'premium'}
        }

        # Analyze the response
        profile, poly_typed_obj = self.profiler.analyze_response_with_polari_typing(
            sample_response,
            profile_name='TestUserProfile',
            display_name='Test User Profile'
        )

        # Verify profile was created
        self.assertIsNotNone(profile)
        self.assertEqual(profile.profileName, 'TestUserProfile')
        self.assertEqual(profile.sampleCount, 1)

        # Verify polyTypedObject was created
        self.assertIsNotNone(poly_typed_obj)
        self.assertEqual(poly_typed_obj.className, 'TestUserProfile')

        # Verify field signatures
        expected_fields = {'id', 'name', 'email', 'age', 'active', 'tags', 'metadata'}
        self.assertEqual(set(profile.fieldSignatures), expected_fields)

        # Verify polyTypedVars were created
        self.assertGreater(len(poly_typed_obj.polyTypedVars), 0)

        # Check specific type inference
        field_types = profile.get_field_types()
        self.assertIn('id', field_types)
        self.assertIn('age', field_types)

        print(f"✓ Profile created: {profile.profileName}")
        print(f"✓ Fields analyzed: {len(profile.fieldSignatures)}")
        print(f"✓ PolyTypedVars created: {len(poly_typed_obj.polyTypedVars)}")
        print(f"✓ Field types: {field_types}")

    def test_02_analyze_multiple_samples(self):
        """Test analyzing multiple samples to build robust typing."""
        print("\n[TEST] Analyzing multiple samples")

        samples = [
            {'id': 1, 'name': 'Item 1', 'price': 10.99, 'inStock': True},
            {'id': 2, 'name': 'Item 2', 'price': 20.50, 'inStock': False},
            {'id': 3, 'name': 'Item 3', 'price': 5.00, 'inStock': True, 'discount': 0.1}
        ]

        profile, poly_typed_obj = self.profiler.analyze_response_with_polari_typing(
            samples,
            profile_name='ProductProfile'
        )

        # Should have analyzed all samples
        self.assertEqual(profile.sampleCount, 3)

        # Should include fields from all samples
        self.assertIn('discount', profile.fieldSignatures)

        print(f"✓ Analyzed {profile.sampleCount} samples")
        print(f"✓ Total fields: {len(profile.fieldSignatures)}")

    # ============================================================================
    # TEST 2: Nested structure analysis
    # ============================================================================

    def test_03_nested_structure_analysis(self):
        """Test that nested structures are properly analyzed using extractSetTyping."""
        print("\n[TEST] Analyzing nested structure")

        nested_response = {
            'user': {
                'id': 'u123',
                'profile': {
                    'firstName': 'John',
                    'lastName': 'Doe',
                    'contacts': [
                        {'type': 'email', 'value': 'john@example.com'},
                        {'type': 'phone', 'value': '555-1234'}
                    ]
                }
            },
            'orders': [
                {'orderId': 'o1', 'total': 99.99},
                {'orderId': 'o2', 'total': 150.00}
            ]
        }

        profile, poly_typed_obj = self.profiler.analyze_response_with_polari_typing(
            nested_response,
            profile_name='NestedProfile'
        )

        # Check that nested fields are detected
        self.assertIn('user', profile.fieldSignatures)
        self.assertIn('orders', profile.fieldSignatures)

        # Check type analysis for nested structures
        field_types = profile.get_field_types()

        # User should be detected as dict type
        self.assertIn('user', field_types)
        user_type = field_types['user'].lower()
        self.assertTrue('dict' in user_type or 'object' in user_type)

        # Orders should be detected as list type
        self.assertIn('orders', field_types)
        orders_type = field_types['orders'].lower()
        self.assertTrue('list' in orders_type)

        print(f"✓ Nested fields detected")
        print(f"✓ User type: {field_types.get('user')}")
        print(f"✓ Orders type: {field_types.get('orders')}")

    # ============================================================================
    # TEST 3: Match against Polari API templates
    # ============================================================================

    def test_04_match_polari_api_response(self):
        """Test matching response against Polari CRUDE response template."""
        print("\n[TEST] Matching against Polari CRUDE response template")

        # Simulate a Polari CRUDE response
        polari_response = [
            {
                'class': 'TestObject',
                'data': [
                    {'id': 'abc123', 'name': 'Test 1', 'value': 42},
                    {'id': 'def456', 'name': 'Test 2', 'value': 100}
                ]
            }
        ]

        # Create template profile
        template = profileTemplates.POLARI_CRUDE_RESPONSE
        template_profile = APIProfile.from_dict(template, manager=self.manager)

        # Match against template
        matches = self.matcher.match_response_to_profiles(
            polari_response,
            [template_profile]
        )

        self.assertGreater(len(matches), 0)
        best_match = matches[0]

        print(f"✓ Match found: {best_match['profileName']}")
        print(f"✓ Confidence: {best_match['confidencePercent']}%")
        print(f"✓ Is match: {best_match['isMatch']}")

        # The response should match CRUDE template fairly well
        self.assertGreater(best_match['confidence'], 0.5)

    def test_05_match_error_response(self):
        """Test matching error response against error template."""
        print("\n[TEST] Matching error response")

        error_response = {
            'success': False,
            'error': 'Something went wrong'
        }

        # Create error template profile
        template = profileTemplates.POLARI_ERROR_RESPONSE
        template_profile = APIProfile.from_dict(template, manager=self.manager)

        matches = self.matcher.match_response_to_profiles(
            error_response,
            [template_profile]
        )

        self.assertGreater(len(matches), 0)
        best_match = matches[0]

        # Should be a high confidence match
        self.assertGreater(best_match['confidence'], 0.7)
        self.assertTrue(best_match['isMatch'])

        print(f"✓ Error response matched with {best_match['confidencePercent']}% confidence")

    def test_06_find_best_match_multiple_templates(self):
        """Test finding best match from multiple templates."""
        print("\n[TEST] Finding best match from multiple templates")

        # Paginated response
        paginated_response = {
            'data': [{'id': 1}, {'id': 2}],
            'page': 1,
            'total': 100,
            'per_page': 10
        }

        # Create multiple template profiles
        templates = [
            profileTemplates.POLARI_CRUDE_RESPONSE,
            profileTemplates.PAGINATION_RESPONSE,
            profileTemplates.REST_COLLECTION_RESPONSE
        ]
        template_profiles = [
            APIProfile.from_dict(t, manager=self.manager) for t in templates
        ]

        # Find best match
        best_match = self.matcher.find_best_match(
            paginated_response,
            template_profiles
        )

        self.assertIsNotNone(best_match)
        # Should match pagination template best
        self.assertEqual(best_match['profileName'], 'PaginationResponse')

        print(f"✓ Best match: {best_match['profileName']}")
        print(f"✓ Confidence: {best_match['confidencePercent']}%")

    # ============================================================================
    # TEST 4: Detect multiple object types
    # ============================================================================

    def test_07_detect_multiple_types_by_field(self):
        """Test detecting multiple types using type field."""
        print("\n[TEST] Detecting multiple types by field")

        mixed_response = [
            {'type': 'user', 'id': 'u1', 'name': 'John', 'email': 'john@test.com'},
            {'type': 'user', 'id': 'u2', 'name': 'Jane', 'email': 'jane@test.com'},
            {'type': 'product', 'id': 'p1', 'title': 'Widget', 'price': 9.99},
            {'type': 'product', 'id': 'p2', 'title': 'Gadget', 'price': 19.99},
            {'type': 'order', 'id': 'o1', 'total': 29.98, 'items': 2}
        ]

        detected = self.profiler.detect_object_types(
            mixed_response,
            type_field='type'
        )

        # Should detect 3 types
        self.assertEqual(len(detected), 3)

        # Verify types detected
        type_ids = [d['typeId'] for d in detected]
        self.assertIn('user', type_ids)
        self.assertIn('product', type_ids)
        self.assertIn('order', type_ids)

        # Check sample counts
        for d in detected:
            if d['typeId'] == 'user':
                self.assertEqual(d['sampleCount'], 2)
            elif d['typeId'] == 'product':
                self.assertEqual(d['sampleCount'], 2)
            elif d['typeId'] == 'order':
                self.assertEqual(d['sampleCount'], 1)

        print(f"✓ Detected {len(detected)} types")
        for d in detected:
            print(f"  - {d['typeId']}: {d['sampleCount']} samples, {len(d['fieldSignature'])} fields")

    def test_08_detect_types_by_signature(self):
        """Test detecting types by field signature clustering."""
        print("\n[TEST] Detecting types by signature")

        # Items with different field structures (no type field)
        mixed_response = [
            {'id': 1, 'username': 'john', 'email': 'john@test.com'},
            {'id': 2, 'username': 'jane', 'email': 'jane@test.com'},
            {'id': 101, 'sku': 'PROD1', 'price': 9.99, 'stock': 100},
            {'id': 102, 'sku': 'PROD2', 'price': 19.99, 'stock': 50}
        ]

        detected = self.profiler.detect_object_types(
            mixed_response,
            type_field=None,  # No type field, use signature
            similarity_threshold=0.5
        )

        # Should detect at least 2 distinct types
        self.assertGreaterEqual(len(detected), 2)

        print(f"✓ Detected {len(detected)} types by signature")
        for d in detected:
            print(f"  - {d['typeId']}: fields={d['fieldSignature']}")

    # ============================================================================
    # TEST 5: Create Polari class from profile
    # ============================================================================

    def test_09_profile_to_class_definition(self):
        """Test converting profile to createClassAPI format."""
        print("\n[TEST] Converting profile to class definition")

        # Create a profile first
        sample = {
            'id': 'item_1',
            'title': 'Test Item',
            'quantity': 5,
            'price': 29.99,
            'available': True
        }

        profile, poly_typed_obj = self.profiler.analyze_response_with_polari_typing(
            sample,
            profile_name='InventoryItem'
        )

        # Convert to class definition
        class_def = self.profiler.profile_to_class_definition(profile)

        # Verify structure
        self.assertIn('className', class_def)
        self.assertIn('classDisplayName', class_def)
        self.assertIn('variables', class_def)
        self.assertIn('registerCRUDE', class_def)
        self.assertIn('isStateSpaceObject', class_def)

        # Verify variables
        self.assertGreater(len(class_def['variables']), 0)
        var_names = [v['varName'] for v in class_def['variables']]
        self.assertIn('title', var_names)
        self.assertIn('quantity', var_names)
        self.assertIn('price', var_names)

        print(f"✓ Class definition created: {class_def['className']}")
        print(f"✓ Variables: {len(class_def['variables'])}")
        for v in class_def['variables']:
            print(f"  - {v['varName']}: {v['varType']}")

    def test_10_create_class_from_profile(self):
        """Test full flow: API response → Profile → Polari Class → CRUDE."""
        print("\n[TEST] Full flow: API → Profile → Polari Class")

        # Sample external API response
        external_response = [
            {'id': 'book_1', 'title': 'Python Guide', 'author': 'John Smith', 'pages': 350, 'price': 39.99},
            {'id': 'book_2', 'title': 'Data Science', 'author': 'Jane Doe', 'pages': 500, 'price': 49.99}
        ]

        # Create profile
        profile, poly_typed_obj = self.profiler.analyze_response_with_polari_typing(
            external_response,
            profile_name='ExternalBook',
            display_name='External Book'
        )

        print(f"  [1/4] Profile created: {profile.profileName}")

        # Convert to class definition
        class_def = self.profiler.profile_to_class_definition(profile)
        print(f"  [2/4] Class definition generated")

        # Use createClassAPI to create the class
        # Find the createClassAPI endpoint
        create_class_api = None
        for api in self.manager.polServer.customAPIsList:
            if hasattr(api, 'apiName') and api.apiName == '/createClass':
                create_class_api = api
                break

        self.assertIsNotNone(create_class_api, "createClassAPI should be registered")

        # Check if class already exists (from previous test runs)
        class_name = class_def['className']
        if class_name not in self.manager.objectTypingDict:
            # Create the class
            new_typing = create_class_api._createDynamicClass(
                className=class_def['className'],
                displayName=class_def['classDisplayName'],
                variables=class_def['variables'],
                registerCRUDE=True,
                isStateSpaceObject=True
            )
            print(f"  [3/4] Dynamic class created: {class_name}")
        else:
            print(f"  [3/4] Class already exists: {class_name}")

        # Verify class is registered
        self.assertIn(class_name, self.manager.objectTypingDict)

        # Check CRUDE endpoint exists
        result = self.client.simulate_get(f'/{class_name}')
        self.assertNotEqual(result.status_code, 404)
        print(f"  [4/4] CRUDE endpoint accessible: /{class_name}")

        print(f"✓ Full flow completed successfully")


class APIProfilerEndpointTestCase(unittest.TestCase):
    """Test case for API Profiler HTTP endpoints."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.manager = managerObject(hasServer=True)
        cls.app = cls.manager.polServer.falconServer
        cls.client = testing.TestClient(cls.app)

    def test_endpoint_templates_registered(self):
        """Test that /apiProfiler/templates endpoint is registered."""
        print("\n[TEST] Verifying templates endpoint")

        result = self.client.simulate_get('/apiProfiler/templates')

        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json.get('success'))
        self.assertIn('templates', result.json)
        self.assertIn('templateNames', result.json)

        print(f"✓ Templates endpoint accessible")
        print(f"✓ Template count: {len(result.json['templateNames'])}")

    def test_endpoint_build_profile(self):
        """Test /apiProfiler/buildProfile endpoint."""
        print("\n[TEST] Testing buildProfile endpoint")

        request_body = {
            'responseData': {
                'id': 'test_1',
                'name': 'Test Object',
                'value': 42
            },
            'profileName': 'EndpointTestProfile',
            'displayName': 'Endpoint Test Profile'
        }

        result = self.client.simulate_post(
            '/apiProfiler/buildProfile',
            body=json.dumps(request_body)
        )

        self.assertEqual(result.status_code, 201)
        self.assertTrue(result.json.get('success'))
        self.assertIn('profile', result.json)
        self.assertIn('polyTypedObject', result.json)

        print(f"✓ Profile built successfully")
        print(f"✓ Profile name: {result.json['profile']['profileName']}")

    def test_endpoint_match(self):
        """Test /apiProfiler/match endpoint."""
        print("\n[TEST] Testing match endpoint")

        request_body = {
            'responseData': {
                'success': False,
                'error': 'Test error message'
            },
            'includeTemplates': True
        }

        result = self.client.simulate_post(
            '/apiProfiler/match',
            body=json.dumps(request_body)
        )

        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json.get('success'))
        self.assertIn('matches', result.json)
        self.assertIn('summary', result.json)

        print(f"✓ Match endpoint successful")
        print(f"✓ Matches found: {len(result.json['matches'])}")

    def test_endpoint_detect_types(self):
        """Test /apiProfiler/detectTypes endpoint."""
        print("\n[TEST] Testing detectTypes endpoint")

        request_body = {
            'responseData': [
                {'type': 'A', 'id': 1, 'name': 'Item A1'},
                {'type': 'A', 'id': 2, 'name': 'Item A2'},
                {'type': 'B', 'id': 3, 'code': 'B1', 'value': 100}
            ],
            'typeField': 'type'
        }

        result = self.client.simulate_post(
            '/apiProfiler/detectTypes',
            body=json.dumps(request_body)
        )

        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json.get('success'))
        self.assertIn('detectedTypes', result.json)
        self.assertEqual(result.json['typeCount'], 2)

        print(f"✓ DetectTypes endpoint successful")
        print(f"✓ Types detected: {result.json['typeCount']}")


def run_tests():
    """Run all API Profiler tests."""
    print("\n" + "="*70)
    print("POLARI FRAMEWORK - API PROFILER TEST SUITE")
    print("="*70)
    print("\nTesting API Profiler components:")
    print("  • Integration with Polari typing system")
    print("  • Nested structure analysis")
    print("  • Profile matching against templates")
    print("  • Multiple object type detection")
    print("  • Class creation from profiles")
    print("  • REST API endpoints")
    print("="*70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(APIProfilerTypingTestCase))
    suite.addTests(loader.loadTestsFromTestCase(APIProfilerEndpointTestCase))

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
