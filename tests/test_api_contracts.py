"""
Module API contracts — in-process HTTP.

Builds a real Falcon app via managerObject(hasServer=True), wires a
module API endpoint, seeds its objectTable in memory, and asserts the
JSON contract through falcon.testing (no live server, no DB). This is the
layer that catches a broken route / response shape before deploy.

Run (in the backend container):
    python3 -m unittest tests.test_api_contracts -v
"""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falcon import testing
from objectTreeManagerDecorators import managerObject
from mathshapes.shape_api import MathShapesAPI
from mathshapes.shape_seed import SEED_MATH_SHAPES


def _seed_rows():
    return {i: SimpleNamespace(**dict(r))
            for i, r in enumerate(SEED_MATH_SHAPES)}


class MathShapesAPIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mgr = managerObject(hasServer=True)
        # Ensure the route exists (idempotent: falcon overrides on re-add).
        MathShapesAPI(polServer=cls.mgr.polServer, manager=cls.mgr)
        # Seed the in-memory table the API reads.
        cls.mgr.objectTables['MathShapeDefinition'] = _seed_rows()
        cls.client = testing.TestClient(cls.mgr.polServer.falconServer)

    def test_catalogue_contract(self):
        r = self.client.simulate_get('/api/shapes')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json.get('ok'))
        self.assertGreaterEqual(r.json.get('count', 0), 7)
        names = {s['name'] for s in r.json['shapes']}
        self.assertIn('unit-sphere', names)

    def test_properties_contract(self):
        r = self.client.simulate_get(
            '/api/shapes/unit-sphere/properties?resolution=20')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json.get('ok'))
        self.assertIn('volumeCm3', r.json)
        self.assertGreater(r.json['volumeCm3'], 0)

    def test_classify_contract(self):
        r = self.client.simulate_get('/api/shapes/unit-sphere/classify')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json.get('type'), 'sphere')

    def test_evaluate_contract(self):
        r = self.client.simulate_post(
            '/api/shapes/unit-sphere/evaluate', json={'x': 0, 'y': 0, 'z': 0})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json.get('inside'))

    def test_unknown_shape_404(self):
        r = self.client.simulate_get('/api/shapes/does-not-exist/properties')
        self.assertEqual(r.status_code, 404)
        self.assertFalse(r.json.get('ok'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
