"""cmod_bench_canvas_selftest - bss-5 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b): the UNO light topology drawn on the one no-code canvas from
its rows: a struct-node box per node, a hardware-event box per edge between its two nodes, columns by depth from the root, colours by confirmation state;
the two node kinds carry their palette as data; the category validator refuses a compute kind; write-back renames a node and an event's title, refuses an
edit to a derived field by name; the SolutionDefinition row is kept up to date; the doors; the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_bench_canvas_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0
BS = 'uno-light-on-desk'
MAP = 'LightState_t->LightState'


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _manager():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _seed(m):
    from cmod.custom import config_rows as R
    from cmod.custom.catom_assertions import SEED_ASSERTIONS, SEED_STRUCT_OBJECT_MAPS
    R.upsert(m, 'BenchConditions', 'room', ambient_min_c=18.0, ambient_max_c=30.0)
    R.upsert(m, 'BenchSolution', BS, bench='home-bench', firmware_solution='uno-light', conditions='room')
    for a in SEED_ASSERTIONS:
        if a['variant'] == 'uno-light':
            R.upsert(m, 'CatomAssertion', a['name'], **{k: v for k, v in a.items() if k != 'name'})
    som = SEED_STRUCT_OBJECT_MAPS[0]
    R.upsert(m, 'StructObjectMap', som['name'], **{k: v for k, v in som.items() if k != 'name'})


def main():
    from cmod.custom import bench_topology as T
    from cmod.custom import bench_topology_nocode as BN
    from cmod.custom import config_rows as R
    from cmod.objects.cmod import HardwareEventState, StructNodeState
    m = _manager()
    _seed(m)
    v = T.view(m, BS)
    boot = next(n for n in v['nodes'] if n['kind'] == 'boot')
    press = '%s:press-PD2' % BS
    T.define(m, BS, 'light-on', 'light on', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 1}],
             executions=[{'atom': 'apps/light.led_follow_state', 'isotope': 'drive-led:gpio-out'}])
    T.connect(m, BS, boot['name'], '%s:light-on' % BS, 'trigger', '%s:command-uno-1-bridge' % BS)
    R.upsert(m, 'StructNodeConfirmation', '%s:light-on#conf1' % BS, node='%s:light-on' % BS, by='twin', state='confirmed', hex_sha256='a' * 64)
    d = BN.render_definition(BS, m)
    st = {s['stateName']: s for s in d['stateInstances']}
    nodes = [s for s in d['stateInstances'] if s['stateClass'] == 'StructNodeState']
    evs = [s for s in d['stateInstances'] if s['stateClass'] == 'HardwareEventState']
    check('THE DRAWING: 4 struct-node boxes (plugged-in, flashed, boot, light-on) and 4 hardware-event boxes (flash, init, the press, the command), one per edge',
          len(nodes) == 4 and len(evs) == 4 and d['solutionName'] == 'bench-topology-%s' % BS, (len(nodes), len(evs)))
    pressbox = next(s for s in evs if s['boundObjectFieldValues']['event'] == press)
    check('node -> event -> node: boot\'s outputs are its two edges, the press box\'s output is light-on; the box says what happens, its kind, source and line',
          set(c['targetStateName'] for c in st[boot['name']]['slots'][1]['connectors']) == {s['stateName'] for s in evs if s['boundObjectFieldValues']['kind'] == 'trigger'}
          and pressbox['slots'][1]['connectors'][0]['targetStateName'] == '%s:light-on' % BS
          and (pressbox['boundObjectFieldValues']['title'], pressbox['boundObjectFieldValues']['source'], pressbox['boundObjectFieldValues']['what']) == ('press PD2', 'person', 'PD2'),
          pressbox['boundObjectFieldValues'])
    xs = {s['stateName']: s['stateLocationX'] for s in d['stateInstances']}
    check('COLUMNS BY DEPTH from the root: plugged-in < flash box < flashed < init box < boot < press box < light-on',
          xs['%s:plugged-in' % BS] < xs['%s:plugged-in->flashed' % BS] < xs['%s:flashed' % BS] < xs['%s:flashed->boot' % BS] < xs[boot['name']] < xs[pressbox['stateName']] < xs['%s:light-on' % BS], xs)
    lo = st['%s:light-on' % BS]
    check('COLOURS BY CONFIRMATION STATE and the words: light-on confirmed by twin (green), boot never tested, the root its own; the node card says requirements, step and the '
          'route to the bench at this node',
          lo['confirmationState'] == 'confirmed-twin' and st[boot['name']]['confirmationState'] == 'never-tested' and st['%s:plugged-in' % BS]['confirmationState'] == 'root'
          and lo['boundObjectFieldValues']['requirements'] == 'led_on = 1' and lo['boundObjectFieldValues']['step'].startswith('0.0625 us by drive-led:gpio-out')
          and lo['boundObjectFieldValues']['bench_here'] == '/display/bench-solutions?bench_solution=%s&node=%s:light-on' % (BS, BS), lo['boundObjectFieldValues'])
    check('THE PALETTE is data on the two kinds: struct-node and hardware-event, category Bench Topology, declarative',
          StructNodeState.statePalette['nodeKind'] == 'struct-node' and HardwareEventState.statePalette['nodeKind'] == 'hardware-event'
          and StructNodeState.statePalette['category'] == 'Bench Topology' and StructNodeState.statePalette['placement'] == 'declarative')
    ok, why = BN.validate(d)
    bad = dict(d, stateInstances=d['stateInstances'] + [{'stateName': 'x', 'stateClass': 'VariableAssignment', 'boundObjectFieldValues': {}}])
    ok2, why2 = BN.validate(bad)
    check('THE CATEGORY VALIDATOR: the drawing is declarative (ok); a compute kind is refused by name', ok and not ok2 and 'VariableAssignment' in why2 and 'compute' in why2, (why, why2))
    edited = json.loads(json.dumps(d))
    for s in edited['stateInstances']:
        if s['stateName'] == '%s:light-on' % BS:
            s['boundObjectFieldValues']['title'] = 'the light is on'
        if s['stateName'] == pressbox['stateName']:
            s['boundObjectFieldValues']['title'] = 'press the button'
    ok3, why3, ch = BN.write_back(edited, BS, m)
    check('WRITE-BACK: a renamed node and a renamed event box land on their rows (StructNode.title, HardwareEvent.title + the edge), nothing else',
          ok3 and ch == {'%s:light-on' % BS: {'title': 'the light is on'}, pressbox['stateName']: {'title': 'press the button'}}
          and R.get(m, 'StructNode', '%s:light-on' % BS)['title'] == 'the light is on' and R.get(m, 'HardwareEvent', press)['title'] == 'press the button', (why3, ch))
    edited2 = json.loads(json.dumps(BN.render_definition(BS, m)))
    for s in edited2['stateInstances']:
        if s['stateName'] == '%s:light-on' % BS:
            s['boundObjectFieldValues']['requirements'] = 'led_on = 0'
    ok4, why4, _ = BN.write_back(edited2, BS, m)
    check('WRITE-BACK refuses an edit to a derived field by name: requirements change through the doors, not the drawing',
          not ok4 and 'requirements is derived from the rows' in why4, why4)
    row = BN.render(BS, m)
    sd = R.get(m, 'SolutionDefinition', 'bench-topology-%s' % BS)
    check('THE SolutionDefinition ROW is kept up to date (category bench-topology) so the drawing page lists it; the route is said',
          row['category'] == 'bench-topology' and sd is not None and json.loads(sd['definition'])['solutionName'] == row['name']
          and BN.drawing_route(BS) == '/display/hardware-solutions?solution=bench-topology-%s' % BS, (row['category'], sd is not None))
    from cmod.cmod_bench_canvas_api import BenchCanvasAPI
    api = BenchCanvasAPI(polServer=None, manager=m)

    def call(method, *args, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(api, method)(req, resp, *args)
        return resp
    g = call('on_get', BS)
    p = call('on_put', BS, body={'definition': edited2})
    nf = call('on_get', 'nope')
    check('DOORS: GET canvas -> the solution, the definition and the route; PUT a refused edit -> 422 with the words; unknown Bench Solution -> 404',
          g.media['ok'] and g.media['route'].endswith('bench-topology-%s' % BS) and len(g.media['definition']['stateInstances']) == 8 and p.status.startswith('422')
          and 'derived' in p.media['error'] and nf.status.startswith('404'), (p.status, nf.status))
    from moduleService.manifests import conform
    rr = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with the new kinds and files listed', rr['ok'], rr.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
