"""cmod_hdr4_selftest — ucd-hdr4: the Purpose task doors (POST /api/capabilities/{name}/tasks, DELETE .../tasks/{node}),
against a seeded manager and a REAL falcon.App (a route-template conflict crashes boot; an import proves nothing).

    PYTHONPATH=.:modules python3 tests/cmod_hdr4_selftest.py   # from polari-framework/
"""
import json
import sys
from types import SimpleNamespace

passed = total = 0


def check(label, ok, detail=''):
    global passed, total
    total += 1
    passed += bool(ok)
    print(('  ok   ' if ok else '  FAIL ') + label + ('' if ok else '  -> %r' % (detail,)))


def main():
    import falcon
    from falcon import testing
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    from cmod.cmod_firmware_api import FirmwareAPI
    from cmod.cmod_api import CModAPI
    from cmod.cmod_capability_api import CapabilityAPI
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None)
    for name, cls, seed_rows in CMOD_SEED_PAIRS:
        for row in seed_rows:
            o = cls(manager=mgr, **{k: v for k, v in row.items() if k != '_converge'})
            tables.setdefault(name, {})[o.id] = o
    app = falcon.App()
    ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
    for api in (CModAPI, FirmwareAPI, CapabilityAPI):     # every cmod door on ONE app: proves no route-template conflict
        api(polServer=ps, manager=mgr)
    c = testing.TestClient(app)
    G = 'uno-sim-rig-graph'
    P = 'temp-sensor-to-os'
    j = json.dumps

    def names():
        return next(p for p in c.simulate_get('/api/cmod/graphs/%s' % G).json['purposes'] if p['name'] == P)['task_names']

    check('routes registered on a real falcon.App (GET /api/capabilities still answers)',
          c.simulate_get('/api/capabilities').status_code == 200)
    before = names()
    check('seed: led is not in temp-sensor-to-os', 'led' not in before, before)
    r = c.simulate_post('/api/capabilities/%s/tasks' % P, body=j({'graph': G, 'node': 'led'}))
    check('POST adds the atom (200, added true, ref graph:node)', r.status_code == 200 and r.json['added'] and r.json['ref'] == G + ':led', r.json)
    check('the graph door now lists it in that Purpose', 'led' in names(), names())
    r = c.simulate_post('/api/capabilities/%s/tasks' % P, body=j({'graph': G, 'node': 'led'}))
    check('POST again is idempotent (added false, no duplicate ref)', r.status_code == 200 and r.json['added'] is False
          and names().count('led') == 1, r.json)
    r = c.simulate_post('/api/capabilities/nope/tasks', body=j({'graph': G, 'node': 'led'}))
    check('unknown Purpose -> 404', r.status_code == 404, r.status_code)
    r = c.simulate_post('/api/capabilities/%s/tasks' % P, body=j({'graph': G, 'node': 'no_such_atom'}))
    check('unknown node -> 422 naming it', r.status_code == 422 and 'no_such_atom' in r.json['error'], r.json)
    r = c.simulate_post('/api/capabilities/%s/tasks' % P, body=j({'graph': G}))
    check('missing node -> 400', r.status_code == 400, r.status_code)
    r = c.simulate_post('/api/capabilities/%s/tasks' % P, body=j({'graph': 'other-graph', 'node': 'led'}))
    check("another graph -> 422", r.status_code == 422, r.status_code)
    r = c.simulate_delete('/api/capabilities/%s/tasks/led' % P)
    check('DELETE removes it (removed true) and the graph door agrees', r.status_code == 200 and r.json['removed'] and 'led' not in names(), r.json)
    r = c.simulate_delete('/api/capabilities/%s/tasks/led' % P)
    check('DELETE again is idempotent (removed false)', r.status_code == 200 and r.json['removed'] is False, r.json)
    r = c.simulate_delete('/api/capabilities/nope/tasks/led')
    check('DELETE unknown Purpose -> 404', r.status_code == 404, r.status_code)
    check('seed task_names restored to the original', names() == before, names())
    print('%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
