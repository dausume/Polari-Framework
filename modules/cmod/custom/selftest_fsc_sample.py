"""
smp-0 / smp-1 selftest parts (run from cmod_fsc_selftest): THE CURATED SAMPLE. The twin is STUBBED here (the real twin runs of the same scenarios on the new builds are in board.board_light_selftest and
`pol firmware prove`); everything else is the real code: the Mission row, the solver's candidates, fsc_link, the doors, the CLI and the committed press-to-light records.

  - the Mission row carries the seven sample entries (S1..S5, F1, F2), seeded so a reseed converges them; every one names a config; S5's does not exist yet
  - the default scope is `sample`: the finished successes compete (best 100, worst 0), the failures listed are only F1 and F2; the other built configs are history, not failures; `all` / `plans` / `finished` keep their meaning
  - S5 (not built yet) is shown as `not built yet`, never as a failure
  - F2: a safety-critical failure from a MEASURED time against the Purpose's own deadline, without touching the real Purpose or Mission
  - the configs' derived routes (led_route), the page's new tab and table, the CLI's default
"""
import contextlib
import io
import json
from types import SimpleNamespace

UNO, LIGHT = 'arduino-uno-r3', 'uno-light-mission'
SUCCESS = ('uno-light', 'uno-light-all-pcint', 'uno-light-pwm-analog', 'uno-light-transistor')
OTHER_FINISHED = ('uno-light-sense-poll', 'uno-light-sense-pcint')     # the button-clock configs: built, finished, NOT in the sample - history


def stub_runs(mgr, configs, outcome='passed'):
    """The four Purposes' own acceptance scenarios for each config, stored through the manager sink with the twin stubbed (as the Purpose door stores them)."""
    from cmod.custom import approach_profile_input as AI
    from cmod.custom import capabilities as CAP
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom import acceptance_config as AC
    from firmwarefaults.custom.sink import ManagerSink
    sink = ManagerSink(mgr, save=False)
    orig = AC.prove
    AC.prove = lambda sc, variant, mode: {'ok': outcome == 'passed', 'route': 'digital-twin', 'why': 'stubbed twin', 'frames_compared': 5, 'how': 'stub'}
    try:
        for p in AI.purposes_of(AI.find_mission(LIGHT, mgr), mgr):
            scen = CAP.find(p['purpose'])['acceptance_scenario']
            for c in configs:
                ACC.run(scen, sink=sink, variant=c, manager=mgr)
    finally:
        AC.prove = orig


def sample_parts(check):
    state = {}

    def world():
        if 'mgr' not in state:
            from cmod.custom.selftest_purpose import _manager
            mgr = _manager()
            stub_runs(mgr, list(SUCCESS) + list(OTHER_FINISHED))
            state['mgr'] = mgr
        return state['mgr']

    def client():
        if 'c' not in state:
            import falcon
            from falcon import testing
            from cmod.cmod_fsc_api import FscAPI
            app = falcon.App()
            FscAPI(polServer=SimpleNamespace(falconServer=app, manager=world(), idList=[]), manager=world())
            state['c'] = testing.TestClient(app)
        return state['c']

    def get(path, **params):
        r = client().simulate_get(path, params=dict({'mission': LIGHT, 'board': UNO}, **params))
        return r.status_code, r.json

    # ------------------------------------------------------------------ the data
    def mission_row():
        from board.custom import variants as V
        from cmod import cmod_seed
        from cmod.custom import fsc_sample as SM
        from cmod.custom import mission_seeds as MS
        entries = SM.entries(MS.MISSION_SEEDS[0])
        check('smp-0 DATA: the light Mission row carries sample_solutions: S1..S5 (successes), F1, F2 (failures), in that order, each with a config, a device and a plain-words reason',
              [e['id'] for e in entries] == ['S1', 'S2', 'S3', 'S4', 'S5', 'F1', 'F2'] and [e['kind'] for e in entries] == ['success'] * 5 + ['failure'] * 2 and all(e['config'] and e['device'] and e['components'] and e['why'] for e in entries),
              [e['id'] for e in entries])
        check('smp-0 DATA: S1..S4, F1 and F2 name real firmware configs (board.custom.variants); S5 names one that does not exist yet (the hook for the ESP32-C3 build)',
              all(e['config'] in V.VARIANT_NAMES for e in entries if e['id'] != 'S5') and next(e['config'] for e in entries if e['id'] == 'S5') not in V.VARIANT_NAMES, [e['config'] for e in entries])
        pair = next(rows for n, _c, rows in cmod_seed.CMOD_SEED_PAIRS if n == 'HardwareMission')[0]
        check('smp-0 DATA: the seed CONVERGES the field (it is in the pair\'s _converge list, so a live server\'s existing row gets it at the next boot)', 'sample_solutions' in pair['_converge'], pair['_converge'])
        from cmod.objects.cmod.HardwareMission import HardwareMission
        import inspect
        check('smp-0 DATA: HardwareMission has the field (default an empty list), and a Mission with no sample reads as no entries and the `all` scope',
              'sample_solutions' in inspect.signature(HardwareMission.__init__).parameters and SM.entries({}) == [] and SM.entries({'sample_solutions': 'not json'}) == [] and SM.default_scope([]) == 'all'
              and SM.default_scope(entries) == 'sample')
        from cmod.custom import solve_inputs as SI
        row2 = dict(MS.MISSION_SEEDS[0], sample_solutions='[]')
        check('smp-0 DATA: the sample is not a solve input - the Mission row hashes the same with any sample_solutions (curating the sample never re-solves)',
              SI.sha({k: v for k, v in MS.MISSION_SEEDS[0].items() if k != 'sample_solutions'}) == SI.sha({k: v for k, v in row2.items() if k != 'sample_solutions'}))

    def routes():
        from board.custom import variants as V
        from cmod.custom import fsc_link as L
        want = {'uno-light': {'read-button': ['ext-interrupt'], 'drive-led': ['gpio-out'], 'sense-led-line': ['gpio-poll']},
                'uno-light-all-pcint': {'read-button': ['pin-change-interrupt'], 'drive-led': ['gpio-out'], 'sense-led-line': ['pin-change-interrupt']},
                'uno-light-pwm-analog': {'read-button': ['analog-threshold'], 'drive-led': ['pwm'], 'sense-led-line': ['gpio-poll']},
                'uno-light-transistor': {'read-button': ['ext-interrupt'], 'drive-led': ['transistor-switch'], 'sense-led-line': ['gpio-poll']},
                'uno-light-slow-loop': {'read-button': ['ext-interrupt'], 'drive-led': ['gpio-out'], 'sense-led-line': ['gpio-poll']}}
        got = {n: {j: r for j, r in L.config_routes(V.find(n)).items() if j in w} for n, w in want.items()}
        check('smp-1 ROUTES: each sample config\'s routes are DERIVED from its own knobs (button_route, sense_route, led_route): %s' % {n: {j: r[0] for j, r in g.items()} for n, g in got.items()}, got == want)
        cfgs = [V.resolve(V.find(n)) for n in want]
        cfg = {r['name']: V.render_config(r) for r in cfgs}
        plain = V.render_config(V.resolve(V.find('uno-light-unsensed')))
        check('smp-1 CONFIG: LED_ROUTE_PWM appears only in the PWM config (S3) and LOOP_DELAY_MS only in the slow-loop failure (F2) - every other build\'s board_config.h is unchanged by the new knobs',
              [n for n, t in cfg.items() if 'LED_ROUTE_PWM' in t] == ['uno-light-pwm-analog'] and [n for n, t in cfg.items() if 'LOOP_DELAY_MS' in t] == ['uno-light-slow-loop']
              and 'LED_ROUTE_PWM' not in plain and 'LOOP_DELAY_MS' not in plain)
        bad = []
        for label, extra in (('led_route unknown', {'led_route': 'laser'}), ('pwm on a pin that is not Timer0\'s', {'led_route': 'pwm', 'led_pin': 7}), ('loop delay too long', {'loop_delay_ms': 5000}),
                             ('loop delay on the light app', {'loop_delay_ms': 100})):
            base = V.find('uno-light-v2' if label.startswith('loop delay on') else 'uno-light')
            try:
                V.resolve(base, extra)
                bad.append(label)
            except V.VariantRefused:
                pass
        check('smp-1 KNOBS: an unknown led_route, a PWM LED off Timer0\'s pins, a loop delay over 2000 ms and a loop delay on an app without the code are each REFUSED (never fixed up)', not bad, bad)

    # ------------------------------------------------------------------ the scope
    def default_scope():
        code, d = get('/api/firmware-scores', profile='fsc-fastest')
        rows = [r for r in d['rows'] if r['state'] != 'failed']
        fails = [r for r in d['rows'] if r['state'] == 'failed']
        check('smp-0 SCOPE: with no scope given the scores door uses `sample` (this Mission carries one): %s' % d.get('scope'), code == 200 and d['scope'] == 'sample', d.get('scope'))
        check('smp-0 SCOPE: the compared set is the sample\'s finished successes - S1..S4, nothing else (no plan, no other built config): %s' % [r['label'][:2] for r in rows],
              [r['sample'] for r in sorted(rows, key=lambda r: r['sample'])] == ['S1', 'S2', 'S3', 'S4'] and all(r['state'] == 'finished' for r in rows), [(r['sample'], r['state']) for r in rows])
        check('smp-0 SCOPE: scores are COMPETITIVE over the four: the best reads 100 and the worst 0, rank 1..4 in order, labels wear the sample id (S1 ...)',
              [r['rank'] for r in rows] == [1, 2, 3, 4] and rows[0]['score'] == 100.0 and rows[-1]['score'] == 0.0 and all(a['score'] >= b['score'] for a, b in zip(rows, rows[1:]))
              and all(r['label'][:2] == r['sample'] for r in rows), [(r['rank'], r['score'], r['label'][:30]) for r in rows])
        check('smp-0 SCOPE: the failures listed are ONLY the sample\'s F rows - F1 (uno-light-unsensed) and F2 (uno-light-slow-loop) - and the door\'s failures[] agrees',
              sorted(r['sample'] for r in fails) == ['F1', 'F2'] and sorted(r['solution'] for r in fails) == ['uno-light-slow-loop', 'uno-light-unsensed']
              and sorted(f['config'] for f in d['failures']) == ['uno-light-slow-loop', 'uno-light-unsensed'], [(r['sample'], r['solution']) for r in fails])
        hist = {h['config']: h for h in d['history']}
        check('smp-0 SCOPE: the other built configs of the Mission are kept as HISTORY, named in history[] and NOT listed as failures: uno-light-pcint, -analog, -v2 (they fail a Purpose), the button-clock configs uno-light-sense-poll / -pcint (finished) and uno-button-clock (plan)',
              {'uno-light-pcint', 'uno-light-analog', 'uno-light-v2', 'uno-light-sense-pcint', 'uno-light-sense-poll', 'uno-button-clock'} <= set(hist) and not ({'uno-light-pcint', 'uno-light-analog', 'uno-light-v2'} & {r['solution'] for r in fails})
              and 'kept as history' in hist['uno-light-pcint']['words'] and all(h['config'] not in SUCCESS + ('uno-light-unsensed', 'uno-light-slow-loop') for h in d['history']), sorted(hist))
        check('smp-0 SCOPE: the set words name the sample and its members', 'curated sample' in d['set'] and 'S1' in d['set'] and 'S4' in d['set'], d['set'])
        code, t = get('/api/firmware-scores/top')
        check('smp-0 SCOPE: the top tab reads the sample too - every profile\'s top is a sample id at 100 and failed_count is 2 (F1, F2)',
              code == 200 and t['scope'] == 'sample' and all(r['top_solution'][:1] == 'S' and r['score'] == 100.0 and r['failed_count'] == 2 for r in t['rows']), t['rows'][0])

    def other_scopes():
        code, a = get('/api/firmware-scores', profile='fsc-fastest', scope='all')
        _c, b = get('/api/firmware-scores', profile='fsc-fastest', scope='both')
        _c, p = get('/api/firmware-scores', profile='fsc-fastest', scope='plans')
        _c, p2 = get('/api/firmware-scores', profile='fsc-fastest', scope='plan')
        _c, f = get('/api/firmware-scores', profile='fsc-fastest', scope='finished')
        n_all = len([r for r in a['rows'] if r['state'] != 'failed'])
        n_fail = len([r for r in a['rows'] if r['state'] == 'failed'])
        check('smp-0 SCOPE: scope=all is today\'s behaviour - every non-failed solution (%d: the finished and every plan) and every failure (%d: the four unfulfilled configs and F2), no history' % (n_all, n_fail),
              code == 200 and a['scope'] == 'all' and n_all > 100 and n_fail == 5 and a['history'] == [] and b['scope'] == 'all' and b['count'] == a['count'], (a['scope'], n_all, n_fail))
        pr = [r for r in p['rows'] if r['state'] != 'failed']
        check('smp-0 SCOPE: scope=plans is only the plans nobody finished (%d, all state plan, ranked 100 to 0), the old name `plan` still works, and nothing finished is in it' % len(pr),
              p['scope'] == 'plans' and pr and all(r['state'] == 'plan' for r in pr) and pr[0]['score'] == 100.0 and pr[-1]['score'] == 0.0 and p2['scope'] == 'plans' and p2['count'] == p['count'], (p['scope'], len(pr)))
        fin = sorted(r['long_label'] for r in f['rows'] if r['state'] == 'finished')
        check('smp-0 SCOPE: scope=finished is every finished config, the sample or not: %s' % fin, sorted(fin) == sorted(SUCCESS + ('uno-light-sense-pcint',)), fin)
        bad = client().simulate_get('/api/firmware-scores', params={'mission': LIGHT, 'scope': 'nope'})
        check('smp-0 SCOPE: an unknown scope is 422 and names the known ones (sample, all, plans, finished)', bad.status_code == 422 and all(w in bad.json['error'] for w in ('sample', 'all', 'plans', 'finished')), bad.text[:200])

    def not_built():
        code, d = get('/api/firmware-scores/sample')
        rows = {r['id']: r for r in d['rows']}
        check('smp-0 SAMPLE DOOR: GET /api/firmware-scores/sample lists the seven entries in order with their state: S1..S4 finished, S5 NOT BUILT YET, F1 and F2 failed: %s' % {k: v['state'] for k, v in rows.items()},
              code == 200 and [r['id'] for r in d['rows']] == ['S1', 'S2', 'S3', 'S4', 'S5', 'F1', 'F2'] and [rows[i]['state'] for i in ('S1', 'S2', 'S3', 'S4')] == ['finished'] * 4
              and rows['S5']['state'] == 'not built yet' and rows['F1']['state'] == 'failed' and rows['F2']['state'] == 'failed', {k: v['state'] for k, v in rows.items()})
        check('smp-0 SAMPLE DOOR: S5 is said to be "not built yet" in plain words and is never a failure (not in the failures, not scored), and the door says the history exists',
              'not a failure' in rows['S5']['outcome'] and rows['S5']['twin_only'] and 'c3-light-freertos' in rows['S5']['outcome'] and d['history'] and d['states'].get('not built yet') == 1, rows['S5'])
        _c, sc = get('/api/firmware-scores', profile='fsc-fastest')
        check('smp-0 SAMPLE DOOR: S5 is not in the scores door at all - neither ranked nor failed', not any('c3-light-freertos' in json.dumps(r) for r in sc['rows']))
        # a Mission with NO sample falls back to the whole set, and the sample door has no entries
        from cmod.custom import fsc_sample as SM
        check('smp-0 SAMPLE DOOR: a Mission with no sample has the `all` scope as its default (not an empty page)', SM.default_scope([]) == 'all')
        # the S5 hook: when a config of that name appears, the entry follows it (no code change)
        from cmod.custom import fsc_link as L
        orig = L.configs

        def with_c3(manager=None):
            rows_ = dict(orig(manager))
            rows_['c3-light-freertos'] = dict(rows_['uno-light-sense-poll'], name='c3-light-freertos')
            return rows_
        L.configs = with_c3
        try:
            from cmod.custom import fsc_run as R
            R._CACHE.clear()
            _c, d2 = get('/api/firmware-scores/sample')
            s5 = next(r for r in d2['rows'] if r['id'] == 'S5')
        finally:
            L.configs = orig
            from cmod.custom import fsc_run as R
            R._CACHE.clear()
        check('smp-0 SAMPLE DOOR: the S5 HOOK - once a config named c3-light-freertos exists the entry reads it (here a stand-in: it is built but not proven, so `built, not finished`, still not a failure): %s' % s5['state'],
              s5['state'] in ('built, not finished', 'built, not scored', 'finished'), s5)

    # ------------------------------------------------------------------ F2
    def safety_failure():
        from board.custom import press_latency as PL
        from cmod.custom import capabilities as CAP
        from cmod.custom import mission_derived as MD
        _c, d = get('/api/firmware-scores', profile='fsc-fastest')
        f2 = next(f for f in d['failures'] if f['config'] == 'uno-light-slow-loop')
        rec = PL.load('uno-light-slow-loop')
        check('smp-1 F2: the failure row says "misses the safety-critical deadline: X ms against Y ms" with the MEASURED time (%s ms, the worst of %d presses on the twin) and the Purpose\'s own 100 ms; kind safety-deadline, no score, no rank'
              % (rec['worst_ms'], len(rec['runs'])),
              f2['kind'] == 'safety-deadline' and f2['purpose'] == 'ensure-button-controls-light' and ('misses the safety-critical deadline: %s ms against 100 ms' % ('%.1f' % rec['worst_ms']).rstrip('0').rstrip('.')) in f2['reason']
              and f2['state'] == 'failed' and f2['rank'] is None and f2['measured_ms'] == rec['worst_ms'] and f2['deadline_ms'] == 100.0, f2['reason'][:200])
        check('smp-1 F2: the committed record is a real measurement: the slow loop is OVER the deadline (%s ms > 100 ms) and the fast uno-light build (S1), measured the same way, is far UNDER it (%s ms); each record names its hex sha256 and is sealed'
              % (rec['worst_ms'], PL.load('uno-light')['worst_ms']),
              rec['worst_ms'] > 100 and PL.load('uno-light')['worst_ms'] < 5 and len(rec['inputs']['hex_sha256']) == 64 and len(rec['record_sha256']) == 64 and len(rec['runs']) == PL.PHASES
              and all(r['latency_ms'] is not None for r in rec['runs']) and rec['schema'] == 'press-latency/1', rec['runs'])
        # the REAL Purpose is untouched: the deadline is 100 ms and NOT flagged; the safety flag lives on the sample entry only
        real = MD.capability('ensure-button-controls-light', None)
        crit = {c['key']: c for c in json.loads(real['criteria_json'])['criteria']}
        from cmod.custom import approach_profile_input as AI
        purposes = {p['purpose']: p for p in AI.purposes_of(AI.find_mission(LIGHT, world()), world())}
        check('smp-1 F2: the REAL Purpose and Mission are not changed - ensure-button-controls-light still states max_latency_ms 100 with NO safety_critical flag; the flag is the sample entry\'s own (FIRMWARE_SCORE_PROFILES_PLAN section 13)',
              crit['max_latency_ms']['value'] == 100 and 'safety_critical' not in crit['max_latency_ms'] and purposes['ensure-button-controls-light'].get('safety_critical') is False
              and 'safety_critical' not in json.dumps(json.loads(AI.find_mission(LIGHT, world())['purposes_json'])), crit['max_latency_ms'])
        # and the real Mission's own failure rule still works the way it did: the solver's failure of flagged real deadlines is unchanged (selftest failure_end_to_end)
        # the entry's judgement: with a faster record the sample entry is NOT a failure; with no record it says "not measured yet"
        orig = PL.load
        try:
            PL.load = lambda v, _o=orig: dict(_o(v), worst_ms=60.0) if v == 'uno-light-slow-loop' else _o(v)
            from cmod.custom import fsc_run as R
            R._CACHE.clear()
            _c, fast = get('/api/firmware-scores/sample')
            r_fast = next(r for r in fast['rows'] if r['id'] == 'F2')
            PL.load = lambda v, _o=orig: None if v == 'uno-light-slow-loop' else _o(v)
            R._CACHE.clear()
            _c, none_ = get('/api/firmware-scores/sample')
            r_none = next(r for r in none_['rows'] if r['id'] == 'F2')
        finally:
            PL.load = orig
            from cmod.custom import fsc_run as R
            R._CACHE.clear()
        check('smp-1 F2: a time UNDER the deadline is not a failure (the entry says it meets it), and with no measurement the entry says "not measured yet" and how to measure - it is never guessed',
              r_fast['state'] == 'meets its deadline' and 'not a failure' in r_fast['outcome'] and r_none['state'] == 'not measured yet' and 'press_latency measure' in r_none['outcome'], (r_fast['state'], r_none['state']))
        # the flag matters: the same time against an entry whose deadline is NOT flagged is no failure
        from cmod.custom import fsc_sample as SM
        ctx = {'by_name': {'ensure-button-controls-light': {'deadline_ms': {'value': 100}, 'deadline_key': 'max_latency_ms', 'safety_critical': False}}}
        ent = [{'id': 'F2', 'config': 'uno-light-slow-loop', 'kind': 'failure', 'safety_deadline': {'purpose': 'ensure-button-controls-light', 'key': 'max_latency_ms', 'safety_critical': False}}]
        rows_, notes_ = SM.safety_failures(ent, ctx, {'uno-light-slow-loop'}, {})
        check('smp-1 F2: D-fsc-1 holds for the entry - the same measured miss against a deadline NOT flagged safety-critical is no failure (it would only lower a deadline-fit score)', rows_ == [] and notes_ and notes_[0]['state'] == 'meets its deadline', notes_)

    def real_failures_unchanged():
        _c, a = get('/api/firmware-scores', profile='fsc-fastest', scope='all')
        k = {f['config']: f['kind'] for f in a['failures'] if f.get('config')}
        check('smp-0 SCOPE: in scope=all F1 keeps its fsc-0b reason (no sense line) and the four unfulfilled configs are still failures there: %s' % sorted(k),
              set(k) == {'uno-light-unsensed', 'uno-light-pcint', 'uno-light-analog', 'uno-light-v2', 'uno-light-slow-loop'} and k['uno-light-unsensed'] == 'purpose-unfulfilled' and k['uno-light-slow-loop'] == 'safety-deadline')

    def cli():
        from cmod.custom import fsc_cli as CLI

        def run(*argv):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = CLI.main(list(argv))
            return rc, buf.getvalue()
        orig = CLI.call

        def via_client(a, method, path, params=None, body=None):      # the CLI's own printing over the SAME doors, asked on the manager that holds the runs
            r = client().simulate_request(method=method, path=path, params=params or {})
            return r.status_code, r.json
        CLI.call = via_client
        try:
            rc, out = run('scores', '--mission', LIGHT, '--profile', 'fsc-fastest')
            rc2, out2 = run('scores', '--mission', LIGHT, '--profile', 'fsc-fastest', '--scope', 'all', '--limit', '3')
            rc3, out3 = run('scores', '--mission', LIGHT, '--profile', 'fsc-fastest', '--scope', 'nope')
        finally:
            CLI.call = orig
        check('smp-0 CLI: `pol firmware scores` defaults to the sample - it names the curated sample, prints S1.., lists F1 and F2 as FAILED and names the history', rc == 0 and 'curated sample' in out and 'S1 ·' in out
              and 'FAILED  F1 ·' in out and 'FAILED  F2 ·' in out and 'history:' in out and out.count('FAILED') == 2, out[:900])
        check('smp-0 CLI: --scope all is the old listing (every solution; the first rows are not limited to the sample) and an unknown scope is refused (exit 3)', rc2 == 0 and 'every non-failed solution' in out2 and rc3 == 3 and '[REFUSED]' in out3, (out2[:200], out3[:200]))

    return [mission_row, routes, default_scope, other_scopes, not_built, safety_failure, real_failures_unchanged, cli]
