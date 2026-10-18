"""firmwarefaults.custom.selftest_routeproof - the route-proof door (POST /api/firmwarefaults/runs): accept / refuse cases on a real
falcon.App beside the firmwarefaults and cmod routes, the CLI's routing (stub _http), and the catalogue effect (a stored passing route
run lifts the route to proven-on-twin, a newer failing one takes it down, no Purpose status moves)."""
import argparse
import json
from types import SimpleNamespace


def _run(scenario, outcome='passed', at='2026-10-18T10:00:00', name=None):
    return {'name': name or '%s@digital-twin@%s' % (scenario, at), 'scenario': scenario, 'side': 'acceptance', 'outcome': outcome, 'ran_at': at,
            'verdict_words': outcome, 'repro_json': json.dumps({'mode': 'digital-twin', 'scenario': scenario})}


def routeproof_parts(check):
    def door():
        import falcon
        from falcon import testing
        from cmod.cmod_api import CModAPI
        from firmwarefaults.firmwarefaults_endpoints import construct_firmwarefaults_endpoints
        mgr = SimpleNamespace(objectTables={}, idList=[], db=None)
        app = falcon.App()
        srv = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
        construct_firmwarefaults_endpoints(srv)
        CModAPI(polServer=srv, manager=mgr)
        c = testing.TestClient(app)
        post = lambda body: c.simulate_post('/api/firmwarefaults/runs', body=json.dumps(body) if not isinstance(body, bytes) else body)
        check('the door adds on a real falcon.App beside the existing firmwarefaults and cmod routes',
              c.simulate_get('/api/firmwarefaults/runs').status_code == 200 and c.simulate_get('/api/firmwarefaults').status_code == 200)
        r = post(_run('light-pcint-button-acceptance'))
        j = r.json
        check('a route run (pcint button) is stored: 201, names its scenario and the variant it proves, and the catalogue rows that cite it',
              r.status_code == 201 and j['ok'] and j['scenario'] == 'light-pcint-button-acceptance' and j['variant'] == 'uno-light-pcint'
              and j['variant_rows'] == ['read-button:pin-change-interrupt'] and j['run']['variant'] == 'uno-light-pcint', r.text[:300])
        check('…the ScenarioRun row is in the object tree and GET /api/firmwarefaults/runs lists it',
              len(mgr.objectTables.get('ScenarioRun', {})) == 1
              and [x['name'] for x in c.simulate_get('/api/firmwarefaults/runs').json['runs']] == [j['run']['name']])
        for scen, row in (('light-analog-button-acceptance', 'read-button:analog-threshold'), ('sense-poll-line-acceptance', None),
                          ('sense-pcint-line-acceptance', None), ('sim-rig-pwm-duty-acceptance', 'drive-led:pwm'), ('light-v2-reboot-acceptance', None)):
            r = post(_run(scen))
            check('%s: accepted as a route proof' % scen, r.status_code == 201 and r.json['ok'] and (row is None or row in r.json['variant_rows']), r.text[:200])
        r = post(_run('light-pcint-button-acceptance'))
        check('the same run sent twice is one row (upsert by name)', r.status_code == 201 and len(mgr.objectTables['ScenarioRun']) == 6)
        before = len(mgr.objectTables['ScenarioRun'])
        refusals = [
            ('a Purpose\'s OWN scenario is refused, naming the Purpose and its door', _run('light-from-button-acceptance'), 'light-from-button'),
            ('an unknown scenario is refused by name', _run('no-such-acceptance'), 'no-such-acceptance'),
            ('a non-acceptance (fault) scenario is refused', _run('uart-residual-frame-loss'), 'uart-residual-frame-loss'),
            ('a run with no scenario is refused', {k: v for k, v in _run('x').items() if k != 'scenario'}, 'no scenario'),
            ('a run with no name is refused', dict(_run('light-pcint-button-acceptance'), name=''), 'no name'),
            ('a run with a bad outcome is refused', dict(_run('light-pcint-button-acceptance'), outcome='maybe'), 'outcome'),
            ('a run with no ran_at is refused', dict(_run('light-pcint-button-acceptance'), ran_at=''), 'ran_at'),
            ('an empty body is refused', {}, 'malformed'),
        ]
        for label, body, word in refusals:
            r = post(body)
            check(label, r.status_code == 422 and not r.json['ok'] and word in r.json['error'], r.text[:200])
        r = post(b'not json')
        check('a body that is not JSON is refused', r.status_code == 422 and not r.json['ok'], r.text[:200])
        check('…and no refused run was stored', len(mgr.objectTables['ScenarioRun']) == before)
        from firmwarefaults.custom import route_proof
        s, m = route_proof.accept(_run('light-pcint-button-acceptance'), None)
        check('no live manager: refused, nothing to store on', s == 422 and 'no live manager' in m['error'])

        # the catalogue effect, through the door
        from cmod.custom import isotope_variants as IV
        from cmod.custom import capabilities as CAP
        mgr2 = SimpleNamespace(objectTables={}, idList=[], db=None)
        srv2 = SimpleNamespace(falconServer=falcon.App(), manager=mgr2, idList=[])
        construct_firmwarefaults_endpoints(srv2)
        c2 = testing.TestClient(srv2.falconServer)
        vs = {v['name']: v for v in IV.variants()}
        v = vs['read-button:pin-change-interrupt']
        caps = {x['name']: dict(x) for x in CAP.SEED_CAPABILITIES}
        base = {n: CAP.derive_status(x, manager=mgr2)[:2] for n, x in caps.items()}
        check('catalogue: with no stored run the route stays at compiles', IV.status(v, mgr2)['status'] == 'compiles')
        c2.simulate_post('/api/firmwarefaults/runs', body=json.dumps(_run('light-pcint-button-acceptance', at='2026-10-18T11:00:00')))
        st = IV.status(v, mgr2)
        check('catalogue: a stored passing route run reads the route as proven-on-twin, naming the run', st['status'] == 'proven-on-twin' and 'ScenarioRun' in st['proof'], st)
        c2.simulate_post('/api/firmwarefaults/runs', body=json.dumps(_run('light-pcint-button-acceptance', 'failed', at='2026-10-18T12:00:00')))
        check('catalogue: a newer failing stored run takes it back down', IV.status(v, mgr2)['status'] == 'compiles')
        c2.simulate_post('/api/firmwarefaults/runs', body=json.dumps(_run('light-pcint-button-acceptance', at='2026-10-18T13:00:00')))
        check('catalogue: a still newer pass lifts it again; another route is untouched',
              IV.status(v, mgr2)['status'] == 'proven-on-twin' and IV.status(vs['read-button:analog-threshold'], mgr2)['status'] == 'compiles')
        check('no Purpose status moved (every Purpose reads exactly as before the route proofs)',
              {n: CAP.derive_status(x, manager=mgr2)[:2] for n, x in caps.items()} == base)

    def cli():
        from firmwarefaults.custom import faults_cli as CLI
        check('route_proof_refused: only the capability door\'s own "run names scenario" refusal routes on',
              CLI.route_proof_refused({'ok': False, 'error': "run names scenario 'a' but capability 'b''s acceptance_scenario is 'c'"})
              and not CLI.route_proof_refused({'ok': False, 'error': 'no capability named x'}) and not CLI.route_proof_refused({'ok': True}))
        calls = []
        orig, orig_run = CLI._http, None
        from firmwarefaults.custom import acceptance as ACC

        def fake_run(scenario, mode='digital-twin', manager=None, sink=None):
            row = _run(scenario)
            sink.upsert('ScenarioRun', row)
            return dict(row, result={})
        orig_run = ACC.run
        ACC.run = fake_run
        import os
        import tempfile
        old_home = os.environ.get('POLARI_FAULTS_HOME')
        os.environ['POLARI_FAULTS_HOME'] = tempfile.mkdtemp(prefix='routeproof-cli-')
        import io
        import contextlib

        def go(scenario, http):
            calls.clear()

            def stub(method, url, body=None):
                calls.append(url)
                return http(url)
            CLI._http = stub
            buf = io.StringIO()
            a = argparse.Namespace(scenario=scenario, hardware=False, both=True, before=False, after=False, natural=False, control=False,
                                   api='http://x', seconds=None, seed=None)
            with contextlib.redirect_stdout(buf):
                CLI.cmd_run(a)
            return buf.getvalue()
        try:
            def refuse_then_accept(url):
                if '/api/capabilities/' in url:
                    return {'ok': False, 'error': "run names scenario 'light-pcint-button-acceptance' but capability 'k''s acceptance_scenario is 'z'"}
                return {'ok': True, 'variant': 'uno-light-pcint', 'variant_rows': ['read-button:pin-change-interrupt']}
            out = go('light-pcint-button-acceptance', refuse_then_accept)
            check('CLI: a route scenario refused by the capability door is pushed to the route-proof door, and says so',
                  len(calls) == 2 and calls[1] == 'http://x/api/firmwarefaults/runs' and 'pushed as a route proof to http://x/api/firmwarefaults/runs' in out, (calls, out))
            out = go('light-from-button-acceptance', lambda url: {'ok': True, 'status': 'proven-on-twin'})
            check('CLI: a Purpose\'s own scenario goes to the capability door only', len(calls) == 1 and '/api/capabilities/ensure-button-controls-light/runs' in calls[0]
                  and 'route proof' not in out, (calls, out))
            out = go('light-pcint-button-acceptance', lambda url: {'ok': False, 'error': 'boom'})
            check('CLI: any other refusal is reported as not pushed, with no second push', len(calls) == 1 and 'NOT pushed' in out and 'boom' in out, (calls, out))
            out = go('light-pcint-button-acceptance', lambda url: {'ok': False, 'error': "run names scenario 'a' but capability 'b''s acceptance_scenario is 'c'"}
                     if '/api/capabilities/' in url else {'ok': False, 'error': 'route door said no'})
            check('CLI: a route door refusal is reported by its own words', 'NOT pushed' in out and 'route door said no' in out, out)
        finally:
            CLI._http = orig
            ACC.run = orig_run
            if old_home is None:
                os.environ.pop('POLARI_FAULTS_HOME', None)
            else:
                os.environ['POLARI_FAULTS_HOME'] = old_home

    return (door, cli)
