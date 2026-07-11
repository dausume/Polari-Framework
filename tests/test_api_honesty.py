"""
Per-fix unit tests for the 2026-07-11 API-variant audit (Dustin: every
fix carries its own test, bundled in the one runner). Where
test_api_sweep asserts the GLOBAL invariant (zero 5xx anywhere), each
test here pins ONE repaired behavior — so a regression names the exact
endpoint and expectation instead of just tripping the sweep.

Runs in run_tests.py discovery; standalone:
    python3 -m unittest tests.test_api_honesty -v
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from objectTreeDecorators import treeObject, treeObjectInit
from tests.api_test_server import multipart, register_scratch, shared_server


class HonestyScratchObject(treeObject):
    """Scratch class for CRUDE refusal tests (distinct from the sweep's
    scratch class — the two modules share one server)."""
    @treeObjectInit
    def __init__(self, name="", value=0):
        self.name = name
        self.value = value


class CrudeRefusalTests(unittest.TestCase):
    """polariCRUDE write verbs refuse dishonest input with reasons —
    previously raw raises (500) or silent no-op 200s."""

    @classmethod
    def setUpClass(cls):
        cls.manager, cls.client = register_scratch(HonestyScratchObject)
        cls.url = '/HonestyScratchObject'

    def test_put_json_body_gets_415_not_crash(self):
        result = self.client.simulate_put(
            self.url, body='{"value": 1}',
            headers={'Content-Type': 'application/json'})
        self.assertEqual(result.status_code, 415)
        self.assertIn('multipart', result.json['error'])

    def test_put_empty_multipart_gets_400_not_silent_200(self):
        body, ctype = multipart({'unrelated': 'field'})
        result = self.client.simulate_put(
            self.url, body=body, headers={'Content-Type': ctype})
        self.assertEqual(result.status_code, 400)
        self.assertIn('polariId', result.json['error'])

    def test_put_unknown_polari_id_gets_404(self):
        body, ctype = multipart({
            'polariId': 'no-such-id',
            'updateData': json.dumps({'value': 2})})
        result = self.client.simulate_put(
            self.url, body=body, headers={'Content-Type': ctype})
        self.assertEqual(result.status_code, 404)

    def test_put_id_without_update_data_gets_400(self):
        row = HonestyScratchObject(name='hon-put', manager=self.manager)
        body, ctype = multipart({'polariId': row.id})
        result = self.client.simulate_put(
            self.url, body=body, headers={'Content-Type': ctype})
        self.assertEqual(result.status_code, 400)
        self.assertIn('updateData', result.json['error'])

    def test_post_empty_payload_gets_400_not_silent_200(self):
        body, ctype = multipart({'unrelated': 'field'})
        result = self.client.simulate_post(
            self.url, body=body, headers={'Content-Type': ctype})
        self.assertEqual(result.status_code, 400)
        self.assertIn('initParamSets', result.json['error'])

    def test_delete_without_target_gets_400_not_crash(self):
        body, ctype = multipart({'unrelated': 'field'})
        result = self.client.simulate_delete(
            self.url, body=body, headers={'Content-Type': ctype})
        self.assertEqual(result.status_code, 400)
        self.assertIn('targetInstance', result.json['error'])

    def test_delete_unknown_target_gets_404(self):
        body, ctype = multipart({
            'targetInstance': json.dumps({'id': 'no-such-id'})})
        result = self.client.simulate_delete(
            self.url, body=body, headers={'Content-Type': ctype})
        self.assertEqual(result.status_code, 404)

    def test_delete_json_body_gets_415_not_crash(self):
        result = self.client.simulate_delete(
            self.url, body='{}',
            headers={'Content-Type': 'application/json'})
        self.assertEqual(result.status_code, 415)


class LegacyPolariApiTests(unittest.TestCase):
    """The polariAPI touchpoint endpoints (/, /login, /register,
    /tempRegister) — previously 500 on EVERY method via the
    raise-after-status pattern + a phantom allowedMinAccess attr."""

    @classmethod
    def setUpClass(cls):
        cls.manager, cls.client = shared_server()

    def test_disallowed_verbs_refuse_405_with_reason(self):
        for method, path in (('GET', '/login'), ('GET', '/register'),
                             ('PUT', '/register'), ('POST', '/login'),
                             ('DELETE', '/tempRegister'), ('PUT', '/')):
            result = self.client.simulate_request(method=method, path=path)
            self.assertEqual(
                result.status_code, 405,
                f'{method} {path} -> {result.status_code}')
            self.assertIn('error', result.json,
                          f'{method} {path} lacks an honest reason')

    def test_event_verb_never_crashes(self):
        for path in ('/', '/login', '/register', '/tempRegister'):
            result = self.client.simulate_request(method='EVENT', path=path)
            self.assertLess(result.status_code, 500,
                            f'EVENT {path} -> {result.status_code}')


class RuntimeRegistrationTests(unittest.TestCase):
    """registerCRUDEforObjectType: the exclusion default is honored
    unless the caller explicitly overrides — previously an explicit
    registration was silently vetoed by a default nobody chose."""

    @classmethod
    def setUpClass(cls):
        cls.manager, cls.client = shared_server()

    def test_default_respects_exclusion_then_override_registers(self):
        class RegistrationProbeObject(treeObject):
            @treeObjectInit
            def __init__(self, name=""):
                self.name = name

        self.manager.getObjectTyping(classObj=RegistrationProbeObject)
        server = self.manager.polServer
        typing = self.manager.objectTypingDict['RegistrationProbeObject']
        # makeDefaultObjectTyping leaves the constructor default in
        # place — without the override the call is a (visible) no-op.
        if typing.excludeFromCRUDE:
            self.assertIsNone(
                server.registerCRUDEforObjectType('RegistrationProbeObject'))
        crude = server.registerCRUDEforObjectType(
            'RegistrationProbeObject', overrideExclusion=True)
        self.assertIsNotNone(crude)
        self.assertFalse(typing.excludeFromCRUDE)
        result = self.client.simulate_get('/RegistrationProbeObject')
        self.assertEqual(result.status_code, 200)
        # Idempotent: a second call returns the existing endpoint.
        again = server.registerCRUDEforObjectType(
            'RegistrationProbeObject', overrideExclusion=True)
        self.assertIs(again, crude)


class RepairedEndpointTests(unittest.TestCase):
    """The individually repaired custom endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.manager, cls.client = shared_server()

    def test_solution_code_unknown_solution_404s(self):
        # Crashed on every call reading polyTypedObject.instancesDict
        # (attribute that never existed).
        result = self.client.simulate_get('/solutionCode/no-such-solution')
        self.assertEqual(result.status_code, 404)
        self.assertFalse(result.json.get('success', True))

    def test_shape_export_unknown_shape_404s_not_502(self):
        result = self.client.simulate_post(
            '/api/shapes/no-such-shape/export', body='{}',
            headers={'Content-Type': 'application/json'})
        self.assertEqual(result.status_code, 404)
        self.assertIn('no MathShapeDefinition', result.json.get('error', ''))

    def test_api_profiler_post_to_id_route_refuses_400(self):
        # on_post lacked the {id} kwarg its route binds -> TypeError 500.
        for path in ('/apiDomain/some-id', '/apiEndpoint/some-id'):
            result = self.client.simulate_post(
                path, body='{}',
                headers={'Content-Type': 'application/json'})
            self.assertEqual(result.status_code, 400,
                             f'POST {path} -> {result.status_code}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
