"""hwnocode.custom.selftest_app — ucd-app: the Hardware App's no-code definition `uno-light-app` (category 'hardware-app').
  * the validator accepts category hardware-app with the same posture (native-shell / bridge states only; compute refused by name);
  * six states, in order, every one on the runtime javafx-native, each with a plain-words purpose;
  * the interconnect is data: uno-light's Bridge state links to uno-light-app, uno-light-app's states link back, and every link
    resolves to a page that exists;
  * seeded as a SolutionDefinition row with category hardware-app.
Run by hwnocode_selftest.main()."""
import json
import re

STEPS = ['open-bundle', 'gate', 'detect-board', 'flash', 'host-bridge', 'sync-state']


def app_parts(check):
    return (lambda: _app(check), lambda: _links(check), lambda: _seed(check))


def _app(check):
    from hwnocode.custom import app_solution as AS, cross_domain as CD
    from hwnocode.custom.runtimes import runtime_for_kind
    d = AS.app_definition()
    states = d['stateInstances']
    check('uno-light-app has six states in order: open-bundle, gate, detect-board, flash, host-bridge, sync-state',
          [s['stateName'] for s in states] == STEPS, [s['stateName'] for s in states])
    check('every state runs on the runtime javafx-native (by kind and by field)',
          all(runtime_for_kind(s['stateClass']) == 'javafx-native' and s['boundObjectFieldValues']['runtime'] == 'javafx-native' for s in states))
    ok, why = CD.validate(d, 'hardware-app')
    check('category hardware-app accepts it', ok, why)
    check('…and the Cross-Domain category does NOT (the kinds differ)', not CD.validate(d)[0])
    bad = json.loads(json.dumps(d))
    bad['stateInstances'].append({'stateName': 'sneaky-math', 'stateClass': 'ConditionalChain', 'slots': []})
    ok2, why2 = CD.validate(bad, 'hardware-app')
    check('a compute state in a Hardware App is refused, naming it', not ok2 and 'sneaky-math' in why2 and 'ConditionalChain' in why2, why2)
    bad2 = json.loads(json.dumps(d))
    bad2['stateInstances'].append({'stateName': 'relay', 'stateClass': 'BackendStateChange', 'slots': []})
    ok3, why3 = CD.validate(bad2, 'hardware-app')
    check('a backend relay state is not a Hardware App kind, refused by name', not ok3 and 'relay' in why3, why3)
    bridge = json.loads(json.dumps(d))
    bridge['stateInstances'].append({'stateName': 'b', 'stateClass': 'HardwareInterface', 'slots': []})
    check('a bridge state (java-bridge) is allowed in a Hardware App', CD.validate(bridge, 'hardware-app')[0])
    purposes = [s['boundObjectFieldValues']['purpose'] for s in states]
    leaks = [x for p in purposes for x in re.findall(r'\.md\b|his ruling|ucd-|D-ucd|`', p)]
    check('each state carries a purpose in plain words (no plan names, rulings, slice codes)', all(len(p) > 40 for p in purposes) and not leaks, leaks)
    gate = purposes[1]
    check('the gate advises and stops only on a differing fingerprint; the flash step asks a person first',
          'differs' in gate and 'sha256' in gate and 'confirm' in purposes[3])
    detect = purposes[2]
    check('detect-board names the three USB identities', all(v in detect for v in ('2341:0043', '2341:0001', '2a03:0043')))
    # every connector chains the steps in order
    chain = [(s['stateName'], [c['targetStateName'] for sl in s['slots'] for c in sl.get('connectors') or []]) for s in states]
    check('the steps are chained in order', [c for _n, c in chain] == [[x] for x in STEPS[1:]] + [[]], chain)


def _routes():
    from hwnocode.hwnocode_page import SEED_HWNOCODE_PAGE_DISPLAYS
    from hwnocode.light_page import LIGHT_PAGES
    from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS
    from uno_core_demo.uno_core_demo_page import SEED_UNO_CORE_DEMO_PAGE_DISPLAYS
    return {p['pageRoute'] for pages in (SEED_HWNOCODE_PAGE_DISPLAYS, LIGHT_PAGES, SEED_CMOD_PAGE_DISPLAYS, SEED_BOARD_PAGE_DISPLAYS,
                                         SEED_UNO_CORE_DEMO_PAGE_DISPLAYS) for p in pages if p.get('pageRoute')}


def _links(check):
    from hwnocode.custom import app_solution as AS, light_solutions as LS
    pages = _routes()
    app = {s['stateName']: s['boundObjectFieldValues'] for s in AS.app_definition()['stateInstances']}
    light = {s['stateName']: s['boundObjectFieldValues'] for s in LS.light_definition()['stateInstances']}
    back = light['uno-light-bridge'].get('links') or []
    check('uno-light\'s Bridge state links to the Hardware App ("the Hardware App that runs this bridge")',
          any(l['route'] == '/display/hardware-solutions?solution=uno-light-app' and 'Hardware App' in l['label'] for l in back), back)
    want = {'open-bundle': '/display/uno-core-demo', 'flash': ['/display/firmware?solution=uno-light', '/display/c-canvas?graph=uno-light-graph'],
            'host-bridge': '/display/hardware-chain', 'sync-state': '/display/uno-core-demo'}
    for st, routes in want.items():
        got = [l['route'] for l in app[st].get('links') or []]
        routes = [routes] if isinstance(routes, str) else routes
        check('uno-light-app %s links to %s' % (st, ', '.join(routes)), all(r in got for r in routes), got)
    every = [l['route'] for v in list(app.values()) + list(light.values()) for l in (v.get('links') or [])] + \
            [v['detail_ref']['route'] for v in list(app.values()) + list(light.values()) if (v.get('detail_ref') or {}).get('route')]
    bad = [r for r in every if r.startswith('/display/') and r.split('?')[0][len('/display/'):] not in pages]
    check('every /display link in either solution resolves to a page that exists (%d links)' % len(every), every and not bad, bad)


def _seed(check):
    from hwnocode.custom import seed_rows as SR
    rows = {r['name']: r for r in SR.solution_definitions()}
    r = rows.get('uno-light-app')
    check('seeded: SolutionDefinition uno-light-app, category hardware-app', r is not None and r['category'] == 'hardware-app', r and r['category'])
    check('…its contract is one input (the bundle) and the definition parses', r and json.loads(r['definition'])['stateInstances']
          and json.loads(r['contract_json'])['inputs'][0]['name'] == 'bundle')
    check('the cross-domain uno-light is still category cross-domain', rows['uno-light']['category'] == 'cross-domain')
