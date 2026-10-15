"""selftest_purpose - fgm-1: Purpose no-code (the eleven states, render / validate / write_back, resolution and the per-device
observations DERIVED, the doors on ONE real falcon.App, the declared light Purposes, the retired pair, coverage)."""
import io
import json
from types import SimpleNamespace

CAN = 'ensure-polari-can-control-light'
NEW = ['initialization', 'ensure-button-controls-light', 'ensure-polari-observes-hardware-state', CAN]
OLD = ['light-from-polari', 'light-from-button']


def _manager():
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None)
    for name, cls, seed_rows in CMOD_SEED_PAIRS:
        for row in seed_rows:
            o = cls(manager=mgr, **{k: v for k, v in row.items() if k != '_converge'})
            tables.setdefault(name, {})[o.id] = o
    return mgr


def _row(mgr, name):
    return next(r for r in mgr.objectTables['CapabilityDefinition'].values() if r.name == name)


def _cap(mgr, name):
    from cmod.cmod_capability_api import CapabilityAPI
    return CapabilityAPI._d(_row(mgr, name))


class _Req:
    def __init__(self, ui, body):
        self.context = SimpleNamespace(user_info=ui)
        self.bounded_stream = io.BytesIO(json.dumps(body).encode())


class _Res:
    media = None
    status = '200 OK'


def _by_class(definition):
    out = {}
    for s in definition['stateInstances']:
        out.setdefault(s['stateClass'], []).append(s)
    return out


def purpose_parts(check):
    def eleven_states():
        from cmod import cmod_basis as B
        from cmod.custom import purpose_nocode as PN
        cats = {c.statePalette['category'] for c in B.PURPOSE_NODE_KIND_CLASSES}
        kinds = [c.statePalette['nodeKind'] for c in B.PURPOSE_NODE_KIND_CLASSES]
        check('the eleven Purpose node kinds: each a class with a statePalette of category Purpose, plain description, displayFields, variables',
              len(B.PURPOSE_NODE_KIND_CLASSES) == 11 and cats == {'Purpose'} and len(set(kinds)) == 11
              and all(c.statePalette['description'] and c.statePalette['displayFields'] and c.statePalette['variables']
                      for c in B.PURPOSE_NODE_KIND_CLASSES), kinds)
        check('the three derived kinds (proof, resolution, per-device) are marked derived in the palette; the eight authored are not',
              {c.__name__ for c in B.PURPOSE_NODE_KIND_CLASSES if c.statePalette['derived']}
              == {'PurposeProofState', 'PurposeResolutionState', 'PurposeObservedState'})
        check('every class is registered: cmod_basis.CMOD_CLASSES holds the eleven + PurposeObservation',
              {c.__name__ for c in B.CMOD_CLASSES} >= {c.__name__ for c in B.PURPOSE_NODE_KIND_CLASSES} | {'PurposeObservation'})
        d = PN.render_definition(_cap(_manager(), CAN), _manager())
        got = _by_class(d)
        check('ensure-polari-can-control-light renders all eleven kinds, every card with a displayName and a purpose sentence',
              set(got) == {c.__name__ for c in B.PURPOSE_NODE_KIND_CLASSES}
              and all(s['boundObjectFieldValues'].get('displayName') and s['boundObjectFieldValues'].get('purpose')
                      for s in d['stateInstances']), sorted(got))
        edges = {(s['stateName'], c['targetStateName']) for s in d['stateInstances'] for sl in s['slots'] for c in sl['connectors']}
        check('the reading order is one edge kind, "then", left to right (the first state has no incoming edge, the last no outgoing)',
              d.get('edgeKind') == 'then' and ('purpose', 'depends') in edges and ('tasks', 'proof') in edges and ('resolution', 'observed') in edges
              and not any(b == 'purpose' for _a, b in edges) and not any(a == 'observed' for a, _b in edges), sorted(edges)[:6])

    def round_trip():
        from cmod.custom import purpose_nocode as PN
        mgr = _manager()
        cap = _cap(mgr, CAN)
        d = PN.render_definition(cap, mgr)
        ok, why = PN.validate(d)
        check('the rendered drawing validates (Purpose kinds only)', ok, why)
        ok, why, ch = PN.write_back(d, cap, mgr)
        check('an unedited drawing writes back NOTHING (the row is the source; the drawing adds no second copy)', ok and ch == {}, (why, ch))
        got = _by_class(d)
        got['PurposeGoalState'][0]['boundObjectFieldValues']['goal'] = 'Polari switches the light, edited on the drawing'
        crit = got['PurposeCriterionState'][0]['boundObjectFieldValues']
        crit['value'] = '80'
        ok, why, ch = PN.write_back(d, cap, mgr)
        edited = json.loads(ch.get('criteria_json', '{}'))
        check('an edit of the goal and of a criterion on the drawing becomes exactly those row fields',
              ok and set(ch) == {'goal', 'criteria_json'} and ch['goal'].endswith('edited on the drawing')
              and edited['criteria'][0]['value'] == 80 and edited['trigger'] == json.loads(cap['criteria_json'])['trigger'], (why, ch))
        # the derived refusals, each named
        for cls, field, label, state in (('PurposeProofState', 'status', 'proof', 'proof'), ('PurposeResolutionState', 'resolution', 'resolution', 'resolution'),
                                         ('PurposeObservedState', 'summary', 'per-device', 'observed')):
            d2 = PN.render_definition(cap, mgr)
            _by_class(d2)[cls][0]['boundObjectFieldValues'][field] = 'proven-on-hardware'
            ok, why, ch = PN.write_back(d2, cap, mgr)
            check('an edit to the derived %s state is REFUSED, naming the state and that it is derived' % label,
                  not ok and ch == {} and "state '%s'" % state in why and 'derived' in why, why)
        d3 = PN.render_definition(cap, mgr)
        _by_class(d3)['PurposeTasksState'][0]['boundObjectFieldValues']['tasks'] = 'uno-light-graph:led'
        ok, why, _ = PN.write_back(d3, cap, mgr)
        check('a changed task list is refused, pointing at the membership doors', not ok and '/tasks' in why, why)
        for mutate, needle in ((lambda g: g['PurposeGoalState'][0]['boundObjectFieldValues'].update(lifecycle='dead'), 'life stage'),
                               (lambda g: g['PurposeParticipantState'][0]['boundObjectFieldValues'].update(ref='no-such-board'), 'no-such-board'),
                               (lambda g: g['PurposeDependsState'][0]['boundObjectFieldValues'].update(depends_on='nope'), 'nope')):
            d4 = PN.render_definition(cap, mgr)
            mutate(_by_class(d4))
            ok, why, _ = PN.write_back(d4, cap, mgr)
            check('write_back refuses by name: %s' % needle, not ok and needle in why, why)

    def validator():
        from cmod.custom import purpose_nocode as PN
        from hwnocode.custom import cross_domain as CD
        d = PN.render_definition(_cap(_manager(), CAN), None)
        for kind in ('ConditionalChain', 'VariableAssignment', 'FirmwareRunState', 'HardwareInterface', 'NativeAppStep', 'Mystery'):
            bad = json.loads(json.dumps(d))
            bad['stateInstances'].append({'stateName': 'x', 'stateClass': kind})
            ok, why = PN.validate(bad)
            check('the purpose validator refuses %s by name' % kind, not ok and kind in why and "'x'" in why, why)
        check('the cross-domain validator still takes its own kinds unchanged', CD.validate({'stateInstances': [{'stateName': 'a', 'stateClass': 'FirmwareRunState'}]})[0])
        ok, why = CD.validate({'stateInstances': [{'stateName': 'a', 'stateClass': 'PurposeGoalState'}]})
        check('...and a Purpose kind is not welcome in a cross-domain solution', not ok, why)

    def resolution_derived():
        import inspect
        from cmod.custom import purpose_derived as PD
        from cmod.objects.cmod.CapabilityDefinition import CapabilityDefinition
        mgr = _manager()
        cap = _cap(mgr, CAN)
        r = PD.resolution(cap, mgr)
        check('resolution is DERIVED: a valid binding exists -> resolved, naming the binding', r['state'] == 'resolved' and 'uno-light@arduino-uno-r3' in r['why'], r)
        check('resolution (and the per-device summary) is NOT a stored field of the Purpose',
              'resolution' not in inspect.signature(CapabilityDefinition.__init__).parameters and 'resolution' not in cap
              and 'observed' not in cap and 'fulfillment' not in cap, sorted(cap))
        b = next(x for x in mgr.objectTables['HardwareBinding'].values() if x.solution == 'uno-light')
        b.status, b.why = 'invalid', 'D6: bound to PB9, which arduino-uno-r3 does not have'
        r2 = PD.resolution(cap, mgr)
        check('the binding goes invalid -> blocked, with the binding\'s own reason', r2['state'] == 'blocked' and 'PB9' in r2['why'], r2)
        b.status, b.why = 'incomplete', 'D2: unbound (button)'
        check('an incomplete binding is blocked too, reason named', PD.resolution(cap, mgr)['state'] == 'blocked' and 'unbound' in PD.resolution(cap, mgr)['why'])
        b.status, b.why = 'valid', ''
        check('...and valid again -> resolved again (nothing was remembered)', PD.resolution(cap, mgr)['state'] == 'resolved')
        r3 = PD.resolution(dict(cap, graph='no-such-graph', tasks_by_runtime_json=json.dumps({'c-device': ['no-such-graph:x']})), mgr)
        check('a Purpose whose graph has no firmware solution is blocked on its missing task, never silently resolved', r3['state'] in ('blocked', 'unresolved') and r3['why'], r3)
        r4 = PD.resolution(dict(cap, tasks_by_runtime_json='{}'), mgr)
        check('a Purpose that names no tasks is unresolved', r4['state'] == 'unresolved', r4)
        mgr2 = _manager()
        sol = next(s for s in mgr2.objectTables['FirmwareSolution'].values() if s.graph == 'uno-light-graph')
        del mgr2.objectTables['FirmwareSolution'][sol.id]
        for k in [k for k, v in mgr2.objectTables['HardwareBinding'].items() if v.solution == 'uno-light']:
            del mgr2.objectTables['HardwareBinding'][k]
        r5 = PD.resolution(cap, None)
        check('with no live rows the pure seed answers the same (resolved), so a fresh checkout reads honestly', r5['state'] == 'resolved', r5)

    def observations():
        from cmod.cmod_capability_api import CapabilityAPI
        from cmod.custom import purpose_derived as PD
        mgr = _manager()
        api = CapabilityAPI(polServer=None, manager=mgr)
        none = PD.observed_summary(_cap(mgr, CAN), mgr)
        check('observed_summary with no reports: unknown, said plainly', none['weakest'] is None and none['summary'].startswith('unknown'), none)
        backend = {'preferred_username': 'service-account-polari-backend', 'sub': 'svc-1'}
        res = _Res()
        api.on_post_observations(_Req(backend, {'board_instance': 'uno-1', 'fulfillment': 'satisfied', 'health': 'healthy',
                                               'evidence': 'frame seq 41'}), res, CAN)
        check('PurposeObservation POST works for the backend path (the service account)', res.media.get('ok') and res.media['observation']['name'] == CAN + '@uno-1', res.media)
        res2 = _Res()
        api.on_post_observations(_Req(backend, {'board_instance': 'uno-2', 'fulfillment': 'at-risk', 'health': 'degraded', 'why': 'late frames'}), res2, CAN)
        res3 = _Res()
        api.on_post_observations(_Req(backend, {'board_instance': 'uno-1', 'fulfillment': 'satisfied', 'health': 'healthy', 'evidence': 'frame seq 90'}), res3, CAN)
        rows = [r for r in mgr.objectTables['PurposeObservation'].values()]
        check('a repeat observation of the same board is an upsert (one row per Purpose x board), keeping the newest evidence',
              len(rows) == 2 and next(r for r in rows if r.board_instance == 'uno-1').evidence == 'frame seq 90')
        s = PD.observed_summary(_cap(mgr, CAN), mgr)
        check('observed_summary = the WEAKEST device (uno-2: at-risk, degraded), every device listed', s['weakest']['board_instance'] == 'uno-2'
              and [d['board_instance'] for d in s['devices']] == ['uno-1', 'uno-2'] and 'at-risk' in s['summary'], s)
        res4 = _Res()
        api.on_post_observations(_Req({'sub': 'a-person', 'preferred_username': 'dustin'}, {'board_instance': 'uno-3', 'fulfillment': 'satisfied', 'health': 'healthy'}), res4, CAN)
        res5 = _Res()
        api.on_post_observations(_Req(None, {'board_instance': 'uno-3', 'fulfillment': 'satisfied', 'health': 'healthy'}), res5, CAN)
        check("a person's POST is REFUSED 403 (and so is an anonymous one); nothing is written",
              res4.status.startswith('403') and res5.status.startswith('403') and not res4.media['ok']
              and len(mgr.objectTables['PurposeObservation']) == 2, (res4.status, res5.status))
        res6 = _Res()
        api.on_post_observations(_Req(backend, {'board_instance': 'uno-3', 'fulfillment': 'great', 'health': 'healthy'}), res6, CAN)
        res7 = _Res()
        api.on_post_observations(_Req(backend, {'board_instance': 'uno-3', 'fulfillment': 'satisfied', 'health': 'healthy'}), res7, 'no-such-purpose')
        check('a word outside the scales is 400 and an unknown Purpose 404, both named', res6.status.startswith('400') and 'fulfillment' in res6.media['error']
              and res7.status.startswith('404'), (res6.status, res7.status))

    def doors_on_one_app():
        import falcon
        from falcon import testing
        from cmod.cmod_api import CModAPI
        from cmod.cmod_capability_api import CapabilityAPI
        from cmod.cmod_firmware_api import FirmwareAPI
        mgr = _manager()
        app = falcon.App()
        ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
        CModAPI(polServer=ps, manager=mgr)
        FirmwareAPI(polServer=ps, manager=mgr)
        CapabilityAPI(polServer=ps, manager=mgr)
        c = testing.TestClient(app)
        r = c.simulate_get('/api/capabilities/%s/solution' % CAN)
        check('GET /api/capabilities/{name}/solution: the drawing, category purpose, eleven kinds, derived states worked out now',
              r.status_code == 200 and r.json['solution']['category'] == 'purpose' and r.json['solution']['name'] == 'purpose-' + CAN
              and len(_by_class(r.json['definition'])) == 11
              and _by_class(r.json['definition'])['PurposeResolutionState'][0]['boundObjectFieldValues']['resolution'] == 'resolved', r.text[:300])
        d = r.json['definition']
        _by_class(d)['PurposeGoalState'][0]['boundObjectFieldValues']['goal'] = 'Polari switches the board light, edited'
        r2 = c.simulate_put('/api/capabilities/%s/solution' % CAN, json={'definition': d})
        check('PUT .../solution writes the edit to the Purpose ROW and returns the re-rendered drawing',
              r2.status_code == 200 and r2.json['changes'] == ['goal'] and _row(mgr, CAN).goal.endswith('edited'), r2.text[:300])
        _by_class(d)['PurposeProofState'][0]['boundObjectFieldValues']['status'] = 'proven-on-hardware'
        r3 = c.simulate_put('/api/capabilities/%s/solution' % CAN, json={'definition': d})
        check('PUT .../solution refuses 422 an edit to a derived state, by name, and the row is untouched',
              r3.status_code == 422 and 'derived' in r3.json['error'] and _row(mgr, CAN).status == 'planned', r3.text[:300])
        r4 = c.simulate_get('/api/capabilities/%s/resolution' % CAN)
        check('GET .../resolution is the derived verdict', r4.status_code == 200 and r4.json['state'] == 'resolved', r4.text[:200])
        r5 = c.simulate_post('/api/capabilities/%s/observations' % CAN, json={'board_instance': 'uno-1', 'fulfillment': 'satisfied', 'health': 'healthy'})
        check('POST .../observations over HTTP with no backend identity is 403', r5.status_code == 403, r5.text[:200])
        r6 = c.simulate_get('/api/capabilities/%s/observations' % CAN)
        check('GET .../observations: the summary and the devices', r6.status_code == 200 and r6.json['devices'] == [], r6.text[:200])
        r7 = c.simulate_get('/api/capabilities/no-such/solution')
        check('an unknown Purpose is 404, named', r7.status_code == 404)
        r8 = c.simulate_get('/api/purposes')
        rows = {x['name']: x for x in r8.json['rows']}
        check('GET /api/purposes: every Purpose with lifecycle, derived resolution + observed, and the link to its drawing',
              r8.status_code == 200 and rows[CAN]['drawing'] == '/display/hardware-solutions?solution=purpose-' + CAN
              and rows[CAN]['resolution'].startswith('resolved') and rows[CAN]['observed'].startswith('unknown')
              and rows['light-from-polari']['lifecycle'] == 'retired' and rows[CAN]['lifecycle'] == 'enabled', r8.text[:300])
        r9 = c.simulate_get('/api/capabilities')
        check('the existing doors still answer beside the new ones on the same app', r9.status_code == 200 and len(r9.json['capabilities']) == 16)

    def seeds():
        from cmod.custom import capabilities as CAP
        from cmod.custom.graph_seed import seed_graph
        from firmwarefaults.custom import acceptance as ACC
        for n in NEW:
            c = CAP.find(n)
            ok, why = CAP.validate(c)
            crit = json.loads(c['criteria_json'])
            check('seed %s: lifecycle enabled, goal, trigger + outcome + criteria, observes, participants (board with variant pending), validates' % n,
                  ok and c['lifecycle'] == 'enabled' and c['goal'] and crit['trigger']['what'] and crit['outcome']['what'] and crit['criteria']
                  and json.loads(c['observes_json']) and json.loads(c['participants_json'])[0] == {'role': 'board', 'kind': 'board', 'ref': 'arduino-uno-r3', 'variant': 'pending'}
                  and json.loads(c['participants_json'])[1]['ref'] == 'atmega328p', (why, n))
            check('seed %s depends on initialization (except initialization itself)' % n, c['depends_on'] == ('' if n == 'initialization' else 'initialization'))
        names = {r.rpartition(':')[2] for n in NEW for r in json.loads(CAP.find(n)['tasks_by_runtime_json'])['c-device']}
        nodes = {n['instance'] for n in seed_graph('uno-light-graph')['nodes']}
        live = [p for p in CAP.purposes_for_graph('uno-light-graph') if p.get('lifecycle') != 'retired']
        named = {r.rpartition(':')[2] for p in live for r in json.loads(p['tasks_by_runtime_json']).get('c-device', [])}
        check('coverage: every uno-light-graph atom is named by >= 1 NON-retired Purpose', nodes <= named and names == nodes, sorted(nodes - named))
        check('the old two are RETIRED and still listed (never deleted), with their acceptance Scenario names intact',
              all(CAP.find(n)['lifecycle'] == 'retired' and n in [p['name'] for p in CAP.purposes_for_graph('uno-light-graph')] for n in OLD)
              and CAP.find('light-from-polari')['acceptance_scenario'] == 'light-from-polari-acceptance')
        want = {'light-from-polari-acceptance': CAN, 'light-from-button-acceptance': 'ensure-button-controls-light',
                'ensure-polari-observes-hardware-state-acceptance': 'ensure-polari-observes-hardware-state'}
        check('the acceptance Scenarios are re-pointed (polari -> can-control, button -> button-controls) and the observes Purpose has its own',
              all(ACC.find(s)['capability'] == p and CAP.find(p)['acceptance_scenario'] == s for s, p in want.items()), want)
        check('initialization has NO acceptance Scenario (no existing step kind can check boot_session): planned, tracking only',
              CAP.find('initialization')['acceptance_scenario'] == '')
        summ = CAP.purpose_summary('uno-light-graph')
        check('purpose_summary: the three tested Purposes decide (planned until a run exists); the retired pair and initialization are listed, never decide',
              summ['purposes_total'] == 3 and summ['proof_status'] == 'planned'
              and {p['name'] for p in summ['purposes'] if p['retired']} == set(OLD), summ['proof_why'])
        st = {n: CAP.derive_status(CAP.find(n), None)[0] for n in NEW}
        check('derived status of the new Purposes with no recorded run: planned (nothing is faked proven)', set(st.values()) == {'planned'}, st)

    def seeded_drawings():
        from hwnocode.custom import seed_rows as SR
        from cmod.custom import purpose_nocode as PN
        rows = {r['name']: r for r in SR.solution_definitions() if r['name'].startswith('purpose-')}
        check('one purpose-<name> SolutionDefinition per declared Purpose, category purpose, validated',
              set(rows) == {'purpose-' + n for n in NEW} and all(r['category'] == 'purpose' and PN.validate(json.loads(r['definition']))[0] for r in rows.values()), sorted(rows))
        d = json.loads(rows['purpose-' + CAN]['definition'])
        derived = [s['boundObjectFieldValues'] for s in d['stateInstances'] if s['stateClass'] in ('PurposeProofState', 'PurposeResolutionState', 'PurposeObservedState')]
        check('the stored drawings hold NO derived value: the three derived states read "worked out when asked"',
              len(derived) == 3 and all(PN.PLACEHOLDER in json.dumps(f) for f in derived) and 'resolved' not in json.dumps(derived), derived)
        goal = _by_class(d)['PurposeGoalState'][0]['boundObjectFieldValues']
        from cmod.custom import capabilities as CAP
        check('the stored drawing is rendered FROM the row (its goal is the row\'s goal)', goal['goal'] == CAP.find(CAN)['goal'])

    def page_and_cards():
        from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS
        from cmod.custom import purpose_nocode as PN
        page = next(p for p in SEED_CMOD_PAGE_DISPLAYS if p['pageRoute'] == 'c-canvas')
        items = [it for row in json.loads(page['definition'])['rows'] for it in row['items']]
        inputs = next(it for it in items if it['id'] == 'c-canvas-capabilities')['componentProps']['inputs']
        cols = inputs['columns'].split(',')
        check('the Purposes table (c-canvas-capabilities) gains lifecycle, resolution, observed and a drawing link, read from the derived door',
              {'lifecycle', 'resolution', 'observed', 'drawing'} <= set(cols) and 'drawing:link' in inputs['columnFormats']
              and inputs['dataPath'] == '/api/purposes', inputs)
        import falcon
        from falcon import testing
        from cmod.cmod_capability_api import CapabilityAPI
        mgr0 = _manager()
        app0 = falcon.App()
        CapabilityAPI(polServer=SimpleNamespace(falconServer=app0, manager=mgr0, idList=[]), manager=mgr0)
        row0 = testing.TestClient(app0).simulate_get('/api/purposes').json['rows'][0]
        check('the door behind the table serves every column the table shows', set(cols) <= set(row0), sorted(set(cols) - set(row0)))
        cap = _cap(_manager(), CAN)
        cards = [(s['boundObjectFieldValues']['displayName'], s['boundObjectFieldValues']['purpose']) for s in PN.render_definition(cap, _manager())['stateInstances']]
        banned = ('FIRMWARE_GENERATION', 'fgm-', 'D-fgm', 'ruling', 'ucd-', 'slice')
        check('every card is plain words: no plan names, rulings or slice codes', not any(b in t + s for t, s in cards for b in banned), cards)

    return (eleven_states, round_trip, validator, resolution_derived, observations, doors_on_one_app, seeds, seeded_drawings, page_and_cards)
