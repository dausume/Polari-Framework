"""
/createClass dynamic-class API — in-process HTTP.

The no-code core: POST a class definition at runtime and the framework
mints a real typed class (object typing + optional CRUDE). Tested through
falcon.testing against an in-process managerObject(hasServer=True).

Uses registerCRUDE=False to exercise the class-definition core without
the separate CRUDE-HTTP registration path (covered elsewhere).

Run (in the backend container):
    python3 -m unittest tests.test_createclass_api -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falcon import testing
from objectTreeManagerDecorators import managerObject


def _class_def(name, variables=None):
    return {'className': name, 'classDisplayName': name,
            'variables': variables or [{'varName': 'label', 'varType': 'str'},
                                       {'varName': 'weight', 'varType': 'float'}],
            'registerCRUDE': False}


class CreateClassAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mgr = managerObject(hasServer=True)
        cls.client = testing.TestClient(cls.mgr.polServer.falconServer)

    def test_create_new_class(self):
        r = self.client.simulate_post(
            '/createClass', json=_class_def('DynGizmoAlpha'))
        self.assertEqual(r.status_code, 201, msg=str(r.json))
        self.assertTrue(r.json.get('success'))
        self.assertEqual(r.json.get('className'), 'DynGizmoAlpha')
        self.assertEqual(r.json.get('apiEndpoint'), '/DynGizmoAlpha')
        self.assertIn('DynGizmoAlpha', self.mgr.objectTypingDict)

    def test_duplicate_class_conflicts(self):
        # ensure it exists first (order-independent), then re-create
        self.client.simulate_post('/createClass', json=_class_def('DynGizmoBeta'))
        r = self.client.simulate_post(
            '/createClass', json=_class_def('DynGizmoBeta'))
        self.assertEqual(r.status_code, 409)
        self.assertFalse(r.json.get('success'))

    def test_lowercase_class_rejected(self):
        r = self.client.simulate_post(
            '/createClass', json=_class_def('lowerbad'))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json.get('success'))

    def test_missing_classname_rejected(self):
        r = self.client.simulate_post('/createClass', json={'variables': []})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json.get('success'))

    def test_created_class_is_typed_and_instantiable(self):
        self.client.simulate_post('/createClass', json=_class_def('DynGizmoGamma'))
        self.assertIn('DynGizmoGamma', self.mgr.objectTypingDict)


if __name__ == '__main__':
    unittest.main(verbosity=2)
