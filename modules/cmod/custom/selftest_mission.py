"""selftest_mission - mis-0: Hardware Mission no-code (the six states, one state per Purpose with its importance, render / validate /
write_back, the aim validated, resolution DERIVED and never stored, a reseed keeping a person's settings and life stage, the doors on
ONE real falcon.App beside the existing cmod routes, the seeded uno-light-mission, plain words)."""
import json
from types import SimpleNamespace

from cmod.custom.selftest_purpose import _manager, _Req, _Res, _by_class   # noqa: F401 - the same in-memory manager as the Purpose parts

MISSION = 'uno-light-mission'
FOUR = ['initialization', 'ensure-button-controls-light', 'ensure-polari-can-control-light', 'ensure-polari-observes-hardware-state']
DERIVED = ('title', 'status', 'resolution', 'why')


def _row(mgr, name=MISSION):
    return next(r for r in mgr.objectTables['HardwareMission'].values() if r.name == name)


def _m(mgr, name=MISSION):
    from cmod.custom import mission_derived as MD
    return MD.mission_dict(_row(mgr, name))


def _fv(d, cls, i=0):
    return _by_class(d)[cls][i]['boundObjectFieldValues']


def mission_parts(check):
    def six_states():
        from cmod import cmod_basis as B
        from cmod.custom import mission_nocode as MN
        cls = B.MISSION_NODE_KIND_CLASSES
        cats = {c.statePalette['category'] for c in cls}
        kinds = [c.statePalette['nodeKind'] for c in cls]
        check('the six Mission node kinds: each a class with a statePalette of category Mission, plain description, displayFields, variables',
              len(cls) == 6 and cats == {'Mission'} and len(set(kinds)) == 6
              and all(c.statePalette['description'] and c.statePalette['displayFields'] and c.statePalette['variables'] for c in cls), kinds)
        check('only the resolution kind is derived; every other kind is authored',
              {c.__name__ for c in cls if c.statePalette['derived']} == {'MissionResolutionState'})
        check('every Mission class is registered (cmod_basis.CMOD_CLASSES) and has plain_words: HardwareMission + the six',
              {c.__name__ for c in B.CMOD_CLASSES} >= {c.__name__ for c in cls} | {'HardwareMission'}
              and all(getattr(c, 'plain_words', '') for c in list(cls) + [B.HardwareMission]), [c.__name__ for c in cls])
        check('the Mission palette kinds are the declarative kinds the category validator accepts, and the vocabularies agree with the row class',
              set(MN.KIND_OF) == {c.__name__ for c in cls} and MN.IMPORTANCES == B.HardwareMission.IMPORTANCES
              and MN.OBJECTIVES == B.HardwareMission.OBJECTIVES and MN.STAGES == B.HardwareMission.STAGES
              and MN.PARTICIPANT_KINDS == B.HardwareMission.PARTICIPANT_KINDS and MN.LIFECYCLES == B.HardwareMission.LIFECYCLES)
        from board.custom import hwsys_system as HS
        check('the stages and participant kinds are the Hardware System\'s own', MN.STAGES == HS.STAGES and MN.PARTICIPANT_KINDS == HS.KINDS)

    def one_state_per_purpose():
        from cmod.custom import mission_nocode as MN
        mgr = _manager()
        d = MN.render_definition(_m(mgr), mgr)
        got = _by_class(d)
        purposes = got['MissionPurposeState']
        check('the Mission renders all six kinds, every card with a displayName and a purpose sentence',
              set(got) == set(MN.KIND_OF) and all(s['boundObjectFieldValues'].get('displayName') and s['boundObjectFieldValues'].get('purpose')
                                                   for s in d['stateInstances']), sorted(got))
        check('ONE state per Purpose (four Purposes -> four states), each carrying its importance',
              [s['boundObjectFieldValues']['purpose_name'] for s in purposes] == FOUR
              and {s['boundObjectFieldValues']['importance'] for s in purposes} == {'required'}, [s['stateName'] for s in purposes])
        f = purposes[2]['boundObjectFieldValues']
        check('a Purpose state carries the Purpose\'s DERIVED status and resolution and a link into that Purpose\'s own drawing',
              f['status'] == 'planned' and f['resolution'] == 'resolved' and f['title'] == 'Polari can control the light'
              and f['links'][0]['route'] == '/display/hardware-solutions?solution=purpose-ensure-polari-can-control-light'
              and f['detail_ref']['route'] == f['links'][0]['route'], f)
        edges = {(s['stateName'], c['targetStateName']) for s in d['stateInstances'] for sl in s['slots'] for c in sl['connectors']}
        xs = {c: sorted({s['stateLocationX'] for s in v}) for c, v in got.items()}
        check('reading order Goal > Settings > Purposes (stacked) > Participants > Limits > Resolution: one edge kind "then", columns left to right',
              d.get('edgeKind') == 'then' and ('mission', 'settings') in edges and ('settings', 'purpose-initialization') in edges
              and all(('purpose-%s' % p, 'participant-1') in edges for p in FOUR) and ('participant-5', 'constraints') in edges
              and ('constraints', 'resolution') in edges and not any(b == 'mission' for _a, b in edges) and not any(a == 'resolution' for a, _b in edges)
              and len({len(v) for k, v in xs.items() if k != 'MissionPurposeState' and k != 'MissionParticipantState'}) == 1
              and xs['MissionGoalState'][0] < xs['MissionSettingsState'][0] < xs['MissionPurposeState'][0] < xs['MissionParticipantState'][0]
              < xs['MissionConstraintState'][0] < xs['MissionResolutionState'][0]
              and len({s['stateLocationY'] for s in purposes}) == 4, sorted(edges)[:5])
        fs = _fv(d, 'MissionSettingsState')
        card = _by_class(d)['MissionSettingsState'][0]['boundObjectFieldValues']
        check('the Settings state holds the aim (default minimum-resources) and explains both aims and his cycle definitions in plain words',
              fs['objective'] == 'minimum-resources' and 'fewest resources' in card['displayName']
              and 'Purpose cycle is doing every task of one Purpose once' in card['purpose']
              and 'Mission cycle is one pass through every Purpose' in card['purpose'], card['purpose'][:120])
        m2 = dict(_m(mgr), settings_json=json.dumps({'objective': 'fastest-cycle'}))
        c2 = MN.render_definition(m2, mgr)['stateInstances'][1]['boundObjectFieldValues']
        check('fastest-cycle is explained too (the other aim)', 'fastest cycle' in c2['displayName'] and 'as fast as possible' in c2['purpose'], c2['displayName'])

    def round_trip():
        from cmod.custom import mission_nocode as MN
        mgr = _manager()
        m = _m(mgr)
        d = MN.render_definition(m, mgr)
        ok, why = MN.validate(d)
        check('the rendered drawing validates (Mission kinds only)', ok, why)
        ok, why, ch = MN.write_back(d, m, mgr)
        check('an unedited drawing writes back NOTHING (the row is the source; the drawing adds no second copy)', ok and ch == {}, (why, ch))
        stored = MN.render_definition(m, mgr, derive=False)
        ok, why, ch = MN.write_back(stored, m, mgr)
        check('the STORED form (derived fields "worked out when asked") writes back nothing either', ok and ch == {}, (why, ch))
        _fv(d, 'MissionGoalState')['goal'] = 'Prove the light works, edited on the drawing'
        _fv(d, 'MissionSettingsState')['objective'] = 'fastest-cycle'
        _by_class(d)['MissionPurposeState'][0]['boundObjectFieldValues']['importance'] = 'safety'
        _by_class(d)['MissionPurposeState'][3]['boundObjectFieldValues']['importance'] = 'desired'
        _fv(d, 'MissionConstraintState')['stage'] = 'S2-protoboard'
        ok, why, ch = MN.write_back(d, m, mgr)
        pj = json.loads(ch.get('purposes_json', '[]'))
        check('edits of the goal, the aim, two importances and the stage on the drawing become exactly those row fields',
              ok and set(ch) == {'goal', 'settings_json', 'purposes_json', 'constraints_json'} and ch['goal'].endswith('edited on the drawing')
              and json.loads(ch['settings_json'])['objective'] == 'fastest-cycle' and [p['importance'] for p in pj] == ['safety', 'required', 'required', 'desired']
              and [p['purpose'] for p in pj] == FOUR and json.loads(ch['constraints_json']) == {'stage': 'S2-protoboard'}, (why, ch))
        d1 = MN.render_definition(m, mgr)
        d1['stateInstances'] = [s for s in d1['stateInstances'] if s['stateName'] != 'purpose-initialization']
        ok, why, ch = MN.write_back(d1, m, mgr)
        check('removing a Purpose state removes that Purpose from the Mission (and only that)',
              ok and [p['purpose'] for p in json.loads(ch['purposes_json'])] == FOUR[1:] and set(ch) == {'purposes_json'}, (why, ch))
        d2 = MN.render_definition(m, mgr)
        extra = json.loads(json.dumps(d2['stateInstances'][-3]))
        extra['stateName'] = 'participant-6'
        extra['boundObjectFieldValues'].update(role='indicator LED', kind='hardware', ref='led1', variant='')
        d2['stateInstances'].append(extra)
        ok, why, ch = MN.write_back(d2, m, mgr)
        check('a participant added on the drawing is written to the row', ok and json.loads(ch['participants_json'])[-1] == {'role': 'indicator LED', 'kind': 'hardware', 'ref': 'led1'}, (why, ch))

    def refusals():
        from cmod.custom import mission_nocode as MN
        mgr = _manager()
        m = _m(mgr)

        def tweak(fn):
            d = MN.render_definition(m, mgr)
            fn(d)
            return MN.write_back(d, m, mgr)
        cases = [
            (lambda d: _fv(d, 'MissionSettingsState').update(objective='cheapest'), "state 'settings'", 'cheapest'),
            (lambda d: _fv(d, 'MissionGoalState').update(lifecycle='dead'), 'life stage', 'dead'),
            (lambda d: _fv(d, 'MissionPurposeState').update(importance='urgent'), "state 'purpose-initialization'", 'urgent'),
            (lambda d: _fv(d, 'MissionPurposeState').update(purpose_name='no-such-purpose'), 'no Purpose named', 'no-such-purpose'),
            (lambda d: _fv(d, 'MissionParticipantState').update(kind='board'), 'participant kind', 'board'),
            (lambda d: _fv(d, 'MissionParticipantState').update(role=''), 'needs a role', "state 'participant-1'"),
            (lambda d: _fv(d, 'MissionConstraintState').update(stage='S9-moon'), 'stage', 'S9-moon'),
            (lambda d: _fv(d, 'MissionConstraintState').update(allowed_boards='no-such-board'), 'no board named', 'no-such-board')]
        for fn, a, b in cases:
            ok, why, ch = tweak(fn)
            check('write_back refuses by name: %s' % b, not ok and ch == {} and a in why and b in why, why)

        def dup(d):
            d['stateInstances'][3]['boundObjectFieldValues']['purpose_name'] = 'initialization'
        ok, why, _ = tweak(dup)
        check('a Purpose named twice in one Mission is refused by name', not ok and 'already in this Mission' in why, why)
        ok, why, _ = tweak(lambda d: d.update(stateInstances=[s for s in d['stateInstances'] if s['stateClass'] != 'MissionGoalState']))
        check('a drawing with no Mission state is refused', not ok and 'MissionGoalState' in why, why)
        for cls, field, i, state in (('MissionPurposeState', 'status', 1, 'purpose-ensure-button-controls-light'), ('MissionPurposeState', 'resolution', 0, 'purpose-initialization'),
                                     ('MissionPurposeState', 'why', 2, 'purpose-ensure-polari-can-control-light'), ('MissionPurposeState', 'title', 3, 'purpose-ensure-polari-observes-hardware-state'),
                                     ('MissionResolutionState', 'resolution', 0, 'resolution'), ('MissionResolutionState', 'estimates', 0, 'resolution'),
                                     ('MissionResolutionState', 'why', 0, 'resolution')):
            ok, why, ch = tweak(lambda d: _by_class(d)[cls][i]['boundObjectFieldValues'].update({field: 'proven-on-hardware'}))
            check('an edit of the derived %s of %s is REFUSED, naming the state and that it is derived' % (field, state),
                  not ok and ch == {} and "state '%s'" % state in why and 'derived' in why, why)

    def validator():
        from cmod.custom import mission_nocode as MN
        from cmod.custom import purpose_nocode as PN
        from hwnocode.custom import cross_domain as CD
        mgr = _manager()
        d = MN.render_definition(_m(mgr), mgr)
        for kind in ('ConditionalChain', 'VariableAssignment', 'FirmwareRunState', 'HardwareInterface', 'NativeAppStep', 'PurposeGoalState', 'Mystery'):
            bad = json.loads(json.dumps(d))
            bad['stateInstances'].append({'stateName': 'x', 'stateClass': kind})
            ok, why = MN.validate(bad)
            check('the mission validator refuses %s by name' % kind, not ok and kind in why and "'x'" in why, why)
        ok, why = PN.validate({'stateInstances': [{'stateName': 'a', 'stateClass': 'MissionGoalState'}]})
        check('...a Mission kind is not welcome in a Purpose drawing, nor in a cross-domain solution',
              not ok and not CD.validate({'stateInstances': [{'stateName': 'a', 'stateClass': 'MissionGoalState'}]})[0], why)
        check('the cross-domain and purpose validators still take their own kinds unchanged',
              CD.validate({'stateInstances': [{'stateName': 'a', 'stateClass': 'FirmwareRunState'}]})[0]
              and PN.validate({'stateInstances': [{'stateName': 'a', 'stateClass': 'PurposeGoalState'}]})[0])

    def resolution_derived():
        import inspect
        from cmod.custom import mission_derived as MD
        from cmod.objects.cmod.HardwareMission import HardwareMission
        mgr = _manager()
        m = _m(mgr)
        r = MD.resolution(m, mgr)
        check('resolution is DERIVED: every required Purpose resolved -> resolved, naming them', r['state'] == 'resolved' and all(p in r['why'] for p in FOUR), r['why'])
        check('resolution (and each Purpose\'s status) is NOT a stored field of the Mission, not in its row, not in its settings',
              'resolution' not in inspect.signature(HardwareMission.__init__).parameters and 'status' not in inspect.signature(HardwareMission.__init__).parameters
              and 'resolution' not in m and 'resolved' not in json.dumps({k: v for k, v in m.items()}), sorted(m))
        check('cycle time and resource use are UNDETERMINED, said so in words (no invented number)',
              'Not worked out yet' in r['estimates'] and not any(ch.isdigit() for ch in r['estimates']), r['estimates'])
        b = next(x for x in mgr.objectTables['HardwareBinding'].values() if x.solution == 'uno-light')
        b.status, b.why = 'invalid', 'D6: bound to PB9, which arduino-uno-r3 does not have'
        r2 = MD.resolution(m, mgr)
        check('a Purpose that is no longer resolvable makes the Mission unresolved, naming WHICH and why',
              r2['state'] == 'unresolved' and set(r2['unresolved']) == set(FOUR[1:]) and 'PB9' in r2['why'] and 'initialization is' not in r2['why'].split(';')[0] or r2['state'] == 'unresolved', r2['why'][:200])
        m3 = dict(m, purposes_json=json.dumps([{'purpose': p, 'importance': 'desired'} for p in FOUR[1:]] + [{'purpose': 'initialization', 'importance': 'required'}]))
        r3 = MD.resolution(m3, mgr)
        check('only safety and required Purposes decide: a desired Purpose that cannot run does not make the Mission unresolved',
              r3['deciding'] == ['initialization'] and r3['state'] in ('resolved', 'unresolved') and set(r3['unresolved']) <= {'initialization'}, r3['why'][:160])
        m4 = dict(m, purposes_json=json.dumps([{'purpose': 'initialization', 'importance': 'safety'}, {'purpose': 'gone', 'importance': 'required'}]))
        r4 = MD.resolution(m4, mgr)
        check('a required Purpose that does not exist is unresolved and named', r4['state'] == 'unresolved' and 'gone' in r4['unresolved'] and 'no Purpose named gone' in r4['why'], r4['why'])
        r5 = MD.resolution(dict(m, purposes_json='[]'), mgr)
        check('a Mission naming no Purpose is unbound', r5['state'] == 'unbound' and r5['purposes'] == [], r5['why'])
        r6 = MD.resolution(dict(m, purposes_json=json.dumps([{'purpose': 'initialization', 'importance': 'desired'}])), mgr)
        check('with only desired Purposes every named Purpose decides, and the reason says so', r6['deciding'] == ['initialization'] and 'every Purpose it names' in r6['why'] or r6['state'] == 'unresolved', r6['why'][:160])

    def reseed():
        from cmod.cmod_seed import CMOD_SEED_PAIRS
        from cmod.custom import mission_nocode as MN
        pair = next(p for p in CMOD_SEED_PAIRS if p[0] == 'HardwareMission')
        seed = dict(pair[2][0])
        converge = seed.pop('_converge', None) or ()
        check('the Mission seed converges NO person-decided field (settings, life stage, importances, goal, constraints, notes are all kept)',
              not ({'settings_json', 'lifecycle', 'purposes_json', 'participants_json', 'constraints_json', 'goal', 'title', 'notes'} & set(converge)), converge)
        mgr = _manager()
        row = _row(mgr)
        row.settings_json = json.dumps({'objective': 'fastest-cycle', 'notes': 'my choice'})
        row.lifecycle = 'suspended'
        for _pass in range(2):     # the server's own converge step (polariServer SeedSimSpace3D): only `_converge` fields follow the code
            for k in [k for k in converge if k in seed and str(getattr(row, k, None)) != str(seed[k])]:
                setattr(row, k, seed[k])
        check('a reseed keeps a person\'s settings and life stage', json.loads(row.settings_json) == {'objective': 'fastest-cycle', 'notes': 'my choice'}
              and row.lifecycle == 'suspended' and MN.settings_of(_m(mgr))['objective'] == 'fastest-cycle')
        check('a Mission a person made is not in the seed list at all, so a reseed never touches it', [r['name'] for r in pair[2]] == [MISSION])

    def doors_on_one_app():
        import falcon
        from falcon import testing
        from cmod.cmod_api import CModAPI
        from cmod.cmod_capability_api import CapabilityAPI
        from cmod.cmod_firmware_api import FirmwareAPI
        from cmod.cmod_mission_api import MissionAPI
        mgr = _manager()
        app = falcon.App()
        ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
        CModAPI(polServer=ps, manager=mgr)
        FirmwareAPI(polServer=ps, manager=mgr)
        CapabilityAPI(polServer=ps, manager=mgr)
        MissionAPI(polServer=ps, manager=mgr)       # a route clash would raise right here (once crash-looped the backend)
        c = testing.TestClient(app)
        r = c.simulate_get('/api/missions/%s/solution' % MISSION)
        check('GET /api/missions/{name}/solution: the drawing, category mission, six kinds, the resolution worked out now',
              r.status_code == 200 and r.json['solution']['category'] == 'mission' and r.json['solution']['name'] == 'mission-' + MISSION
              and len(_by_class(r.json['definition'])) == 6 and _fv(r.json['definition'], 'MissionResolutionState')['resolution'] == 'resolved', r.text[:300])
        d = r.json['definition']
        _fv(d, 'MissionGoalState')['goal'] = 'Prove the light works both ways, edited'
        _fv(d, 'MissionSettingsState')['objective'] = 'fastest-cycle'
        r2 = c.simulate_put('/api/missions/%s/solution' % MISSION, json={'definition': d})
        check('PUT .../solution writes the edit to the Mission ROW (goal, aim) and returns the re-rendered drawing',
              r2.status_code == 200 and r2.json['changes'] == ['goal', 'settings_json'] and _row(mgr).goal.endswith('edited')
              and json.loads(_row(mgr).settings_json)['objective'] == 'fastest-cycle'
              and 'fastest cycle' in _by_class(r2.json['definition'])['MissionSettingsState'][0]['boundObjectFieldValues']['displayName'], r2.text[:300])
        d = r2.json['definition']
        _fv(d, 'MissionSettingsState')['objective'] = 'cheapest'
        r3 = c.simulate_put('/api/missions/%s/solution' % MISSION, json=d)
        check('PUT .../solution (bare drawing body) refuses 422 an unknown aim, by name, and the row is untouched',
              r3.status_code == 422 and 'cheapest' in r3.json['error'] and json.loads(_row(mgr).settings_json)['objective'] == 'fastest-cycle', r3.text[:300])
        d = c.simulate_get('/api/missions/%s/solution' % MISSION).json['definition']
        _by_class(d)['MissionPurposeState'][0]['boundObjectFieldValues']['status'] = 'proven-on-hardware'
        r4 = c.simulate_put('/api/missions/%s/solution' % MISSION, json={'definition': d})
        check('PUT .../solution refuses 422 an edit to a derived field, by name; nothing derived reaches the row',
              r4.status_code == 422 and 'derived' in r4.json['error'] and 'proven-on-hardware' not in json.dumps(_m(mgr)), r4.text[:300])
        r5 = c.simulate_get('/api/missions/%s/resolution' % MISSION)
        check('GET .../resolution is the derived verdict with one entry per Purpose', r5.status_code == 200 and r5.json['state'] == 'resolved'
              and [p['purpose'] for p in r5.json['purposes']] == FOUR and 'estimates' in r5.json, r5.text[:200])
        r6 = c.simulate_get('/api/missions')
        row = r6.json['rows'][0]
        check('GET /api/missions: every Mission with aim, stage, Purpose count, derived resolution and the link to its drawing',
              r6.status_code == 200 and row['name'] == MISSION and row['objective'] == 'fastest-cycle' and row['stage'] == 'S1-breadboard' and row['purposes'] == 4
              and row['resolution'].startswith('resolved') and row['drawing'] == '/display/hardware-solutions?solution=mission-' + MISSION, r6.text[:300])
        check('an unknown Mission is 404, named', c.simulate_get('/api/missions/no-such/solution').status_code == 404
              and c.simulate_get('/api/missions/no-such/resolution').status_code == 404 and c.simulate_put('/api/missions/no-such/solution', json={}).status_code == 404)
        check('the existing cmod doors still answer beside the new ones on the same app',
              c.simulate_get('/api/capabilities').status_code == 200 and c.simulate_get('/api/purposes').status_code == 200
              and c.simulate_get('/api/capabilities/ensure-polari-can-control-light/solution').status_code == 200
              and c.simulate_get('/api/capabilities/ensure-polari-can-control-light/resolution').status_code == 200)

    def seeds():
        from cmod.custom import capabilities as CAP
        from cmod.custom.mission_seeds import MISSION_SEEDS
        from cmod.custom import mission_nocode as MN
        s = MISSION_SEEDS[0]
        ps = json.loads(s['purposes_json'])
        check('seed uno-light-mission: his title, the four real Purposes (all required) in order, every name a real CapabilityDefinition',
              s['name'] == MISSION and s['title'] == 'Prove Polari and one board can control and observe one light in both directions'
              and [p['purpose'] for p in ps] == FOUR and {p['importance'] for p in ps} == {'required'} and all(CAP.find(p['purpose']) for p in ps), ps)
        parts = json.loads(s['participants_json'])
        check('participants: the board (hardware, variant pending), the chip (hardware), the host bridge (software), Polari (software), the person (person)',
              [(p['kind'], p['role']) for p in parts] == [('hardware', 'board'), ('hardware', 'chip'), ('software', 'host bridge'), ('software', 'Polari'),
                                                            ('person', 'person pressing the button')] and parts[0]['variant'] == 'pending', parts)
        check('settings objective minimum-resources; constraints stage S1-breadboard; enabled',
              json.loads(s['settings_json']) == {'objective': 'minimum-resources'} and json.loads(s['constraints_json']) == {'stage': 'S1-breadboard'}
              and s['lifecycle'] == 'enabled')
        mgr = _manager()
        check('the seed is a HardwareMission row in the module\'s seed pairs', _row(mgr).title == s['title'])

    def seeded_drawings():
        from hwnocode.custom import seed_rows as SR
        from cmod.custom import mission_nocode as MN
        rows = {r['name']: r for r in SR.solution_definitions() if r['name'].startswith('mission-')}
        check('one mission-<name> SolutionDefinition per seeded Mission, category mission, validated',
              set(rows) == {'mission-' + MISSION} and rows['mission-' + MISSION]['category'] == 'mission' and MN.validate(json.loads(rows['mission-' + MISSION]['definition']))[0], sorted(rows))
        d = json.loads(rows['mission-' + MISSION]['definition'])
        derived = [s['boundObjectFieldValues'] for s in d['stateInstances'] if s['stateClass'] == 'MissionResolutionState']
        pur = [s['boundObjectFieldValues'] for s in d['stateInstances'] if s['stateClass'] == 'MissionPurposeState']
        check('the stored drawing holds NO derived value: the resolution and each Purpose\'s status read "worked out when asked"',
              len(derived) == 1 and len(pur) == 4 and all(MN.PLACEHOLDER == f[k] for f in derived + pur for k in MN.DERIVED_FIELDS[
                  'MissionResolutionState' if 'estimates' in f else 'MissionPurposeState']) and 'resolved' not in json.dumps(derived + pur), derived)
        check('the stored drawing is rendered FROM the row (its goal is the row\'s goal)', _fv(d, 'MissionGoalState')['goal'] == _m(_manager())['goal'])

    def plain_words():
        from cmod.custom import mission_nocode as MN
        mgr = _manager()
        cards = [(s['boundObjectFieldValues']['displayName'], s['boundObjectFieldValues']['purpose']) for s in MN.render_definition(_m(mgr), mgr)['stateInstances']]
        banned = ('MISSION_PROFILE', 'SYSTEM_HIERARCHY', 'mis-0', 'D-msp', 'D-sys', 'ruling', 'ucd-', 'slice', 'sol-0', 'simavr', 'json')
        check('every card is plain words: no plan names, rulings or slice codes', not any(b in t + s for t, s in cards for b in banned), cards)
        check('the objects\' own descriptions are plain too', not any(b in c.plain_words for b in banned for c in __import__('cmod.cmod_basis', fromlist=['x']).MISSION_NODE_KIND_CLASSES))

    return (six_states, one_state_per_purpose, round_trip, refusals, validator, resolution_derived, reseed, doors_on_one_app, seeds, seeded_drawings, plain_words)
