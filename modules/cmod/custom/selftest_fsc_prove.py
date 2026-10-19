"""
fsc-6 selftest parts (run from cmod_fsc_selftest): the PER-CONFIG PROOF mechanism, with the twin STUBBED (the real twin runs of the same scenarios are in board.board_light_selftest).

  - a Purpose's own scenario run for a config is stored with variant = that config, under its own scenario name; refused for a config that is not a built config of the Mission
  - the Purpose door takes such a run for a built config, refuses any other config, and the run never moves the Purpose's OWN status
  - with the four Purposes' runs present for the two sense variants, fsc_link reports exactly those two FINISHED and the scores door rows read `finished`; runs on uno-light alone prove nothing for them
  - `pol firmware prove`'s plan and dry run
"""
import json
from types import SimpleNamespace

UNO, LIGHT = 'arduino-uno-r3', 'uno-light-mission'
from cmod.custom.selftest_purpose import _manager  # noqa: E402

SENSE = ('uno-light', 'uno-light-sense-pcint')      # the two built configs these checks make finished (uno-light-sense-poll has the routes of uno-light: a duplicate)


def prove_parts(check):
    state = {}

    def stub_runs(mgr, configs, outcome='passed'):
        """Run each Purpose's own scenario for each config through ACC.run with the twin stubbed, store through the manager sink (as the door does)."""
        from cmod.custom import approach_profile_input as AI
        from cmod.custom import capabilities as CAP
        from firmwarefaults.custom import acceptance as ACC
        from firmwarefaults.custom import acceptance_config as AC
        from firmwarefaults.custom.sink import ManagerSink
        sink = ManagerSink(mgr, save=False)
        orig, out = AC.prove, []
        AC.prove = lambda sc, variant, mode: {'ok': outcome == 'passed', 'route': 'digital-twin', 'why': 'stubbed twin', 'frames_compared': 5, 'how': 'stub'}
        try:
            for i, p in enumerate(AI.purposes_of(AI.find_mission(LIGHT, mgr), mgr)):
                scen = CAP.find(p['purpose'])['acceptance_scenario']
                for c in configs:
                    out.append(ACC.run(scen, sink=sink, variant=c, manager=mgr))
        finally:
            AC.prove = orig
        return out

    def run_row():
        from firmwarefaults.custom import acceptance as ACC
        from firmwarefaults.custom import acceptance_config as AC
        from firmwarefaults.custom.sink import LocalSink
        orig = AC.prove
        AC.prove = lambda sc, variant, mode: {'ok': True, 'route': 'digital-twin', 'why': 'stubbed twin', 'frames_compared': 5, 'how': 'stub'}
        try:
            r = ACC.run('light-from-button-acceptance', sink=LocalSink(), variant='uno-light-sense-poll')
            own = ACC.run('light-from-button-acceptance', sink=LocalSink(), variant='uno-light')
        finally:
            AC.prove = orig
        check('fsc-6 RUN: a Purpose\'s own scenario run for a config keeps the scenario name and stores variant = the config (name carries it too): %s' % r['name'],
              r['scenario'] == 'light-from-button-acceptance' and r['variant'] == 'uno-light-sense-poll' and r['outcome'] == 'passed' and 'uno-light-sense-poll' in r['name']
              and json.loads(r['repro_json'])['variant'] == 'uno-light-sense-poll', r)
        check('fsc-6 RUN: with no variant (or the scenario\'s own) it is the old run: variant uno-light, name without a config', own['variant'] == 'uno-light' and own['name'].count('@') == 2, own['name'])
        bad = stub_runs(_manager(), ['uno-sim-rig'])[0]
        pc = run_pcint_scenario()
        check('fsc-6 RUN: a config that is not a built config of the Mission (uno-sim-rig has no button) is refused: outcome inapplicable, and the reason is in the run',
              bad['outcome'] == 'inapplicable' and 'not a built config of Mission' in bad['verdict_words'], bad['verdict_words'][:200])
        check('fsc-6 RUN: a scenario that is no Purpose\'s own (a route proof) is refused for a config', pc['outcome'] == 'inapplicable' and 'not the own acceptance scenario' in pc['verdict_words'], pc['verdict_words'][:200])

    def run_pcint_scenario():
        from firmwarefaults.custom import acceptance as ACC
        from firmwarefaults.custom.sink import LocalSink
        return ACC.run('light-pcint-button-acceptance', sink=LocalSink(), variant='uno-light-sense-poll')

    def door():
        import falcon
        from falcon import testing
        from cmod.cmod_capability_api import CapabilityAPI
        from cmod.custom import capabilities as CAP
        from cmod.custom.selftest_purpose import _manager
        mgr = _manager()
        state['mgr'] = mgr
        app = falcon.App()
        CapabilityAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
        c = testing.TestClient(app)
        runs = stub_runs(_manager(), ['uno-light-sense-poll'])
        keys = ('name', 'scenario', 'side', 'variant', 'outcome', 'verdict_words', 'observed_json', 'simulator_version', 'frames_seen', 'repro_json', 'ran_at', 'notes')
        body = {k: runs[1][k] for k in keys}          # ensure-button-controls-light's run for the sense-poll config
        cap = 'ensure-button-controls-light'
        before = CAP.derive_status(CAP.find(cap), manager=mgr)[0]
        r = c.simulate_post('/api/capabilities/%s/runs' % cap, body=json.dumps(body))
        after = CAP.derive_status(CAP.find(cap), manager=mgr)[0]
        check('fsc-6 DOOR: POST /api/capabilities/%s/runs takes a passed run for a BUILT config (uno-light-sense-poll) and stores it with that variant' % cap,
              r.status_code == 200 and r.json['ok'] and r.json['run']['variant'] == 'uno-light-sense-poll', r.text[:240])
        check('fsc-6 DOOR: …and it never moves the Purpose\'s OWN status (%s -> %s): a run of another config proves that config, not uno-light' % (before, after), before == after == 'planned')
        refused = c.simulate_post('/api/capabilities/%s/runs' % cap, body=json.dumps(dict(body, name='x', variant='uno-sim-rig')))
        check('fsc-6 DOOR: a run for a config that is not a built config of the Mission is refused 422 with the reason', refused.status_code == 422 and 'not a built config' in refused.json['error'], refused.text[:240])
        failed = c.simulate_post('/api/capabilities/%s/runs' % cap, body=json.dumps(dict(body, name='y', outcome='failed', ran_at='2999-01-01T00:00:00')))
        check('fsc-6 DOOR: a LATER FAILED run of a config leaves the Purpose\'s own status alone too', failed.status_code == 200 and CAP.derive_status(CAP.find(cap), manager=mgr)[0] == before)

    def finished():
        from cmod.custom import fsc_run as R
        from cmod.custom.selftest_purpose import _manager
        mgr = _manager()
        stub_runs(mgr, ['uno-light-unsensed'])
        b0 = R.build(LIGHT, mgr, [UNO])
        by0 = {r['link']['config']: r for r in b0['records'] if r['link']}
        check('fsc-6 FINISHED: all four Purposes proven on another config (uno-light-unsensed) proves NOTHING for the sense variants (no finished config; the reason names the config\'s own firmware)',
              b0['counts']['finished'] == 0 and all("no ScenarioRun of config %s's own firmware" % c in by0[c]['state_why'] for c in SENSE), b0['counts'])
        stub_runs(mgr, list(SENSE))
        b = R.build(LIGHT, mgr, [UNO])
        fin = {r['link']['config'] for r in b['records'] if r['state'] == 'finished'}
        by = {r['link']['config']: r for r in b['records'] if r['link']}
        check('fsc-6 FINISHED: with the four Purposes\' runs on each sense variant\'s own build, fsc_link reports exactly those two finished: %s (uno-button-clock stays plan)' % sorted(fin),
              fin == set(SENSE) and b['counts']['finished'] == 2 and by['uno-button-clock']['state'] == 'plan', by['uno-light']['state_why'][:240])
        import falcon
        from falcon import testing
        from cmod.cmod_fsc_api import FscAPI
        app = falcon.App()
        FscAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
        g = testing.TestClient(app).simulate_get('/api/firmware-scores', params={'mission': LIGHT, 'board': UNO, 'profile': 'fsc-fastest', 'scope': 'finished'})
        rows = g.json['rows'] if g.status_code == 200 else []
        check('fsc-6 SCORES: the scores door rows for the two sense variants read `finished` (scope=finished lists them): %s' % sorted(r['long_label'] for r in rows if r['state'] == 'finished'),
              g.status_code == 200 and {r['long_label'] for r in rows if r['state'] == 'finished'} == set(SENSE), g.text[:240])

    def plan_and_dry_run():
        import contextlib
        import io
        from cmod.custom import fsc_prove_cli as P
        steps, refused = P.plan('uno-light-sense-pcint', LIGHT)
        check('fsc-6 CLI: `pol firmware prove` plans the four Purposes of the Mission, each with its OWN acceptance scenario: %s' % [s['purpose'] for s in steps],
              not refused and [s['purpose'] for s in steps] == ['initialization', 'ensure-button-controls-light', 'ensure-polari-can-control-light', 'ensure-polari-observes-hardware-state']
              and all(s['scenario'].endswith('-acceptance') for s in steps), steps)
        _s, no = P.plan('uno-sim-rig', LIGHT)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = P.main(['uno-light-sense-poll', '--dry-run', '--json', '--api', 'https://example.invalid'])
        doc = json.loads(buf.getvalue())
        check('fsc-6 CLI: it refuses a config that is not a built config of the Mission, and --dry-run --json lists what would run and the door, running and pushing nothing',
              'not a built config' in no and code == 0 and doc['dry_run'] and doc['ok'] and len(doc['steps']) == 4 and doc['steps'][1]['door'].endswith('/api/capabilities/ensure-button-controls-light/runs')
              and not any('outcome' in s for s in doc['steps']), doc)

    return [run_row, door, finished, plan_and_dry_run]
