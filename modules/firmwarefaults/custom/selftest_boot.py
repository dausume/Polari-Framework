"""firmwarefaults.custom.selftest_boot - fsc-0b: the boot Purpose `initialization` is provable. Its acceptance Scenario (initialization-acceptance), the pure judge and its negative
controls, the REAL simavr twin run of uno-light (skipped with a stated reason when this device has no twin), the ScenarioRun it writes, and the Purpose door accepting that run."""
import json
import os
from types import SimpleNamespace


def _frame(session, seq=1):
    return {'boot_session': session, 'seq': seq, 'led_on': False, 'toggles': 0}


def boot_parts(check):
    def judge_and_controls():
        from board.custom import light_boot_twin as LB
        good_a = [_frame(1)]
        good_b = [_frame(1), _frame(1, 2), _frame(2)]
        ok, why = LB.judge_boot(good_a, good_b)
        check('fsc-0b BOOT judge: a report inside the first 100 ms with boot_session, and after a reset the first report names a DIFFERENT session -> pass (%s)' % why[:90], ok)
        cases = {
            'no report at all in the first 100 ms (the first report is later than the bound)': LB.judge_boot([], good_b),
            'a report without boot_session': LB.judge_boot([{k: v for k, v in _frame(1).items() if k != 'boot_session'}], good_b),
            'a report after the reset without boot_session': LB.judge_boot(good_a, [_frame(1), {'seq': 2}]),
            'the first report after the reset names the SAME session': LB.judge_boot(good_a, [_frame(1), _frame(1, 2)]),
            'no reset in the stream (one session only)': LB.judge_boot(good_a, [_frame(1), _frame(1, 2)]),
            'a third session (more than one reset inside the window)': LB.judge_boot(good_a, [_frame(1), _frame(2), _frame(3)]),
        }
        for label, (passed, why) in cases.items():
            check('fsc-0b BOOT negative control (the judge must REJECT it): %s' % label, not passed, why)
        check('fsc-0b BOOT: the bound is the Purpose criterion max_latency_ms (100) = 1,600,000 cycles at 16 MHz and the reset lands at 200 ms',
              LB.BOUND_MS == 100 and LB.BOUND_CYCLES == 1600000 and LB.RESET_CYCLE == 3200000
              and [c for c in json.loads(_purpose()['criteria_json'])['criteria'] if c['key'] == 'max_latency_ms'][0]['value'] == LB.BOUND_MS)

    def _purpose():
        from cmod.custom import capabilities as CAP
        return CAP.find('initialization')

    def wiring():
        from firmwarefaults.custom import acceptance as ACC
        sc = ACC.find('initialization-acceptance')
        steps = ACC.steps_of('initialization-acceptance')
        check('fsc-0b BOOT wiring: the Purpose names initialization-acceptance, the Scenario is an acceptance Scenario on uno-light that names the Purpose back, with forcible steps (reset-at, assert-field-arrival)',
              _purpose()['acceptance_scenario'] == 'initialization-acceptance' and sc['capability'] == 'initialization' and sc['kind'] == 'acceptance' and sc['before_variant'] == 'uno-light'
              and [s['kind'] for s in steps] == ['reset-at', 'assert-field-arrival'] and all(s['forcible'] for s in steps) and ACC.BOOT_PROOFS == {'initialization-acceptance': 'uno-light'})
        src = open(os.path.join(os.path.dirname(__file__), '..', '..', 'board', 'custom', 'firmware', 'uno', 'apps', 'light.c')).read()
        contract = json.load(open(os.path.join(os.path.dirname(__file__), '..', '..', 'board', 'custom', 'contracts', 'LightState.v1.json')))
        check('fsc-0b BOOT: the v1 light firmware really mints and reports boot_session (atom boot_session_mint in light.c assigns state.boot_session; LightState.v1 carries the field)',
              'POLARI_NODE(boot_session_mint' in src and 'state.boot_session = (int64_t)boot_session_mint()' in src and 'boot_session' in json.dumps(contract))

    def twin():
        from board.custom import light_boot_twin as LB
        ready, why = LB.engine_ready()
        if not ready:
            check('fsc-0b BOOT twin run SKIPPED (no simavr twin on this device: %s)' % why[:80], True)
            return
        from firmwarefaults.custom import acceptance as ACC
        from firmwarefaults.custom import sink as S
        r = LB.prove()
        check('fsc-0b BOOT on the simavr twin (uno-light): %s' % r['why'][:200], r['ok'] and r['frames_compared'] >= 3, r)
        check('…every negative control built from the real runs was rejected by the same judge (%d controls: %s)' % (len(r['controls']), '; '.join(c['control'][:40] for c in r['controls'])),
              len(r['controls']) == 4 and not any(c['judged_ok'] for c in r['controls']))
        run = ACC.run('initialization-acceptance', 'digital-twin', sink=S.LocalSink())
        check('fsc-0b BOOT: ACC.run writes a ScenarioRun outcome passed on variant uno-light (measured on the simavr twin)', run['outcome'] == 'passed' and run['variant'] == 'uno-light' and run['frames_seen'] >= 3, (run['outcome'], run['verdict_words']))
        door(run)

    def door(run):
        import falcon
        from falcon import testing
        from cmod.cmod_capability_api import CapabilityAPI
        from cmod.custom import capabilities as CAP
        from cmod.custom.selftest_purpose import _manager
        mgr = _manager()
        app = falcon.App()
        CapabilityAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
        c = testing.TestClient(app)
        body = {k: run[k] for k in ('name', 'scenario', 'side', 'variant', 'outcome', 'verdict_words', 'observed_json', 'simulator_version', 'frames_seen', 'repro_json', 'ran_at', 'notes')}
        before = CAP.derive_status(CAP.find('initialization'), manager=mgr)[0]
        r = c.simulate_post('/api/capabilities/initialization/runs', body=json.dumps(body))
        check('fsc-0b BOOT door: POST /api/capabilities/initialization/runs stores the twin run (200) and the Purpose goes %s -> proven-on-twin' % before,
              r.status_code == 200 and r.json['ok'] and r.json['status'] == 'proven-on-twin' and before == 'planned', r.text[:240])
        bad = c.simulate_post('/api/capabilities/initialization/runs', body=json.dumps(dict(body, name='x', scenario='light-from-button-acceptance')))
        check('fsc-0b BOOT door: a run of another Purpose\'s Scenario is refused 422', bad.status_code == 422)

    return (judge_and_controls, wiring, twin)
