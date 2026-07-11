"""
Full API-variant sweep (Dustin 2026-07-11): boot the in-process server,
enumerate EVERY route actually registered on the falcon app (via
falcon.inspect — so endpoints added later are covered automatically,
no hand-maintained list), and exercise every method variant:

  1. No route may CRASH (5xx) on a well-formed-but-minimal request —
     endpoints must refuse dishonest input honestly (4xx + reason),
     never stack-trace.
  2. Every generated CRUDE GET-list variant must 200 with the standard
     envelope, for every registered class.
  3. The full CRUDE write protocol (multipart polariId/updateData/
     initParamSets/targetInstance) round-trips on a scratch class —
     the regression net for the protocol mismatch found 2026-07-11
     (frontend was PUTting REST-style /{Class}/{id}, which 404s).
  4. Field-profile variants respond for a real class.

Run standalone:  python3 -m unittest tests.test_api_sweep -v
Runs in the suite via run_tests.py (test*.py discovery).
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import falcon.inspect
from falcon import testing

from objectTreeManagerDecorators import managerObject
from objectTreeDecorators import treeObject, treeObjectInit


class SweepScratchObject(treeObject):
    """Scratch class for the CRUDE write-protocol round-trip."""
    @treeObjectInit
    def __init__(self, name="", note="", value=0):
        self.name = name
        self.note = note
        self.value = value


# Best-effort values for templated path params. Anything not listed
# gets GENERIC — handlers must answer an unknown id with an honest
# 4xx, so garbage is a legitimate probe value.
GENERIC_PARAM = 'sweep-probe'
PARAM_VALUES = {
    'className': 'SweepScratchObject',
    'class_name': 'SweepScratchObject',
    'profileName': GENERIC_PARAM,
    'module_name': 'simSpace',
    'moduleName': 'simSpace',
}

# Routes that may not be probed blindly (would hang/require external
# services even for a refusal). Keep SHORT and justified — every entry
# here is un-swept surface.
SKIP_ROUTES = ()

# Methods falcon fills in that are not real handler variants.
PSEUDO_RESPONDERS = ('method_not_allowed', 'options_responder',
                     'default_serve_static_file')


def _multipart(fields):
    boundary = 'sweep-boundary'
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; '
                     f'name="{name}"\r\n\r\n{value}\r\n')
    body = (''.join(parts) + f'--{boundary}--\r\n').encode()
    return body, f'multipart/form-data; boundary={boundary}'


class ApiSweepTestCase(unittest.TestCase):
    """Every registered route × every real method variant."""

    @classmethod
    def setUpClass(cls):
        print('\n' + '=' * 70)
        print('Setting up API Sweep Test Suite (in-process server)')
        print('=' * 70)
        cls.manager = managerObject(hasServer=True)
        cls.manager.getObjectTyping(classObj=SweepScratchObject)
        cls.manager.polServer.registerCRUDEforObjectType('SweepScratchObject', overrideExclusion=True)
        cls.app = cls.manager.polServer.falconServer
        cls.client = testing.TestClient(cls.app)
        cls.routes = cls._real_routes()
        print(f'✓ {len(cls.routes)} route/method variants discovered')

    @classmethod
    def _real_routes(cls):
        """(path, METHOD, responder_name, resource_repr) for every real
        responder on the app — straight from the router, no static
        route list to go stale."""
        info = falcon.inspect.inspect_app(cls.app)
        out = []
        for route in info.routes:
            for m in route.methods:
                if m.function_name in PSEUDO_RESPONDERS:
                    continue
                if m.method in ('OPTIONS', 'HEAD', 'WEBSOCKET'):
                    continue
                out.append((route.path, m.method, m.function_name,
                            route.class_name))
        return sorted(out)

    @classmethod
    def _fill_params(cls, path):
        filled = path
        while '{' in filled:
            start = filled.index('{')
            end = filled.index('}', start)
            param = filled[start + 1:end].split(':')[0]
            filled = (filled[:start]
                      + PARAM_VALUES.get(param, GENERIC_PARAM)
                      + filled[end + 1:])
        return filled

    def _probe(self, path, method):
        """Fire one minimal request. Mutating methods get an empty JSON
        object — endpoints must refuse it honestly, not crash."""
        kwargs = {}
        if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            kwargs['body'] = '{}'
            kwargs['headers'] = {'Content-Type': 'application/json'}
        return self.client.simulate_request(
            method=method, path=self._fill_params(path), **kwargs)

    def test_01_no_route_crashes(self):
        """Every route/method answers WITHOUT a 5xx (honest refusals
        are fine; stack traces are not)."""
        crashes = []
        for path, method, responder, resource in self.routes:
            if (path, method) in SKIP_ROUTES:
                continue
            try:
                result = self._probe(path, method)
                status = result.status_code
            except Exception as e:  # unhandled exception escaping falcon
                crashes.append((method, path, 'EXC', f'{type(e).__name__}: {e}'))
                continue
            if status >= 500:
                body = (result.text or '')[:200]
                crashes.append((method, path, status, body))
        if crashes:
            lines = '\n'.join(f'  {m} {p} -> {s} {b}'
                              for m, p, s, b in crashes)
            self.fail(
                f'{len(crashes)} route variant(s) crash instead of '
                f'refusing honestly:\n{lines}')
        print(f'✓ {len(self.routes)} route/method variants — zero 5xx')

    def test_02_all_crude_get_lists_respond(self):
        """Every generated CRUDE class endpoint (single-segment path
        bound to polariCRUDE) 200s with the standard envelope."""
        crude_paths = sorted({
            path for path, method, responder, resource in self.routes
            if resource == 'polariCRUDE' and method == 'GET'
            and '{' not in path and path.count('/') == 1})
        self.assertGreater(len(crude_paths), 50,
                           'CRUDE surface unexpectedly small — did class '
                           'registration change?')
        broken = []
        for path in crude_paths:
            result = self.client.simulate_get(path)
            if result.status_code != 200:
                broken.append((path, result.status_code))
                continue
            try:
                envelope = result.json
                cls_name = path.lstrip('/')
                assert isinstance(envelope, list)
                assert cls_name in envelope[0]
            except Exception as e:
                broken.append((path, f'bad envelope: {e}'))
        if broken:
            lines = '\n'.join(f'  GET {p} -> {s}' for p, s in broken)
            self.fail(f'{len(broken)} CRUDE GET variant(s) broken of '
                      f'{len(crude_paths)}:\n{lines}')
        print(f'✓ {len(crude_paths)} CRUDE GET-list variants respond')

    def test_03_crude_write_protocol_round_trip(self):
        """POST initParamSets → PUT polariId+updateData → DELETE
        targetInstance, all multipart — the real CRUDE write protocol."""
        # CREATE
        body, ctype = _multipart({'initParamSets': json.dumps(
            [{'name': 'sweep-row', 'note': 'created', 'value': 1}])})
        result = self.client.simulate_post(
            '/SweepScratchObject', body=body,
            headers={'Content-Type': ctype})
        self.assertLess(result.status_code, 300,
                        f'CRUDE POST refused: {result.status_code} '
                        f'{(result.text or "")[:200]}')
        table = self.manager.objectTables.get('SweepScratchObject', {})
        row = next((r for r in table.values()
                    if getattr(r, 'name', '') == 'sweep-row'), None)
        self.assertIsNotNone(row, 'POST initParamSets did not create the row')

        # UPDATE
        body, ctype = _multipart({
            'polariId': row.id,
            'updateData': json.dumps({'note': 'updated', 'value': 2})})
        result = self.client.simulate_put(
            '/SweepScratchObject', body=body,
            headers={'Content-Type': ctype})
        self.assertLess(result.status_code, 300,
                        f'CRUDE PUT refused: {result.status_code} '
                        f'{(result.text or "")[:200]}')
        self.assertEqual(row.note, 'updated',
                         'PUT updateData did not apply to the instance')

        # The REST-style per-id route must NOT exist — this pins the
        # protocol so a frontend regression is caught here, not live.
        rest_style = self.client.simulate_put(
            f'/SweepScratchObject/{row.id}', body='{}',
            headers={'Content-Type': 'application/json'})
        self.assertEqual(rest_style.status_code, 404,
                         'per-id REST route unexpectedly exists — CRUDE '
                         'protocol changed; update this test AND the '
                         'frontend services together')

        # DELETE
        body, ctype = _multipart({
            'targetInstance': json.dumps({'id': row.id})})
        result = self.client.simulate_delete(
            '/SweepScratchObject', body=body,
            headers={'Content-Type': ctype})
        self.assertLess(result.status_code, 300,
                        f'CRUDE DELETE refused: {result.status_code} '
                        f'{(result.text or "")[:200]}')
        table = self.manager.objectTables.get('SweepScratchObject', {})
        self.assertNotIn(row.id, table,
                         'DELETE targetInstance left the row behind')
        print('✓ CRUDE multipart write protocol round-trips '
              '(and per-id REST correctly 404s)')

    def test_04_field_profile_variants(self):
        """The per-class field-profile sub-routes respond."""
        listing = self.client.simulate_get(
            '/SweepScratchObject/field-profiles')
        self.assertEqual(listing.status_code, 200,
                         f'field-profiles listing: {listing.status_code}')
        single = self.client.simulate_get(
            '/SweepScratchObject/field-profile/nonexistent-profile')
        self.assertLess(single.status_code, 500,
                        'field-profile lookup crashes on unknown profile')
        print('✓ field-profile variants respond')


if __name__ == '__main__':
    unittest.main(verbosity=2)
