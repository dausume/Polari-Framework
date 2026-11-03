"""cmod_coverage_selftest - bss-6 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b "Making it obvious what was tested"): the coverage of a Bench Solution's
topology, derived from its rows with no twin: the untested list first and complete, the strip's counts, the per-node rows, the events used / run, the
assertions exercised by a run that met its node, the page's tables all read doors that exist, the doors, the manifest. Pure: the runs are rows written as
node_run writes them.

    PYTHONPATH=.:modules python3 -m cmod.cmod_coverage_selftest      # from polari-framework/
"""
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
    R.upsert(m, 'BenchSolution', BS, title='UNO light on the desk', bench='home-bench', firmware_solution='uno-light', conditions='room')
    for a in SEED_ASSERTIONS:
        if a['variant'] == 'uno-light':
            R.upsert(m, 'CatomAssertion', a['name'], **{k: v for k, v in a.items() if k != 'name'})
    som = SEED_STRUCT_OBJECT_MAPS[0]
    R.upsert(m, 'StructObjectMap', som['name'], **{k: v for k, v in som.items() if k != 'name'})


def main():
    from cmod.custom import bench_topology as T
    from cmod.custom import config_rows as R
    from cmod.custom import topology_coverage as COV
    from cmod.cmod_coverage_api import CoverageAPI, events, runs, strip_rows
    m = _manager()
    _seed(m)
    v = T.view(m, BS)
    boot = next(n for n in v['nodes'] if n['kind'] == 'boot')
    press = '%s:press-PD2' % BS
    light = T.define(m, BS, 'light-on', 'light on', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 1}],
                     executions=[{'atom': 'apps/light.led_follow_state', 'isotope': 'drive-led:gpio-out'}])
    T.connect(m, BS, boot['name'], light['name'], 'trigger', '%s:command-uno-1-bridge' % BS)
    T.define(m, BS, 'light-off-again', '', light['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 0}], executions=['apps/light.led_toggle'])
    u0 = COV.untested(m, BS)
    check('BEFORE ANY RUN the untested list says it all: both state nodes never tested, boot never tested, the unused events (reset, the period), every assertion unexercised; '
          'the release is INERT (the firmware asserts nothing on it: no edge can end on it, bss-8), listed apart and not untested',
          any(w == '%s: never tested' % light['name'] for w in u0) and any(w == '%s: never tested' % boot['name'] for w in u0)
          and not any(w.startswith('event release-PD2') for w in u0) and any(w.startswith('event reset') for w in u0) and sum(w.startswith('assertion ') for w in u0) == 7
          and [e['event'].split(':', 1)[1] for e in COV.inert_events(m, BS)] == ['release-PD2'], u0)
    # a run as node_run writes it: light-on reached along the press path, led_on changed, PD6 read, frames left; a twin confirmation
    fp = light['fastest_path']['name']
    run = R.upsert(m, 'StructNodeRun', '%s#run1' % light['name'], node=light['name'], path=fp, outcome='reached', hex_sha256='b' * 64, engine='twin', step_s=62.5e-9,
                   step_set_by='drive-led:gpio-out (cycle: 0.0625 us, cited)', duration_s=2e-5, duration_set_by='measured', ran_at='2026-11-02T13:00:00+00:00', words='met')
    for i, e in enumerate(light['fastest_path']['edges'].split(','), 1):
        R.upsert(m, 'StructNodeRunEdge', '%s:%d' % (run['name'], i), run=run['name'], edge=e, order=i, outcome='met', met_cycle=10 * i,
                 collaterals='pin-level PD6: high at cycle 1600317, 0.020 ms after the stimulus ; frame uno-1-bridge: 120 bytes on the UART over the run' if i == 3 else '')
    R.upsert(m, 'StructNodeRunSignal', '%s:field:led_on' % run['name'], run=run['name'], kind='field', signal='led_on', first='0', last='1', changes=1)
    R.upsert(m, 'StructNodeConfirmation', '%s#conf1' % light['name'], node=light['name'], path=fp, by='twin', run=run['name'], hex_sha256='b' * 64, state='confirmed')
    R.upsert(m, 'StructNodeConfirmation', '%s#conf0' % light['name'], node=light['name'], path='old', by='twin', hex_sha256='a' * 64, state='voided', voided_why='the build changed')
    s = COV.strip(m, BS)
    check('THE STRIP after one reached run: light-on confirmed by twin, flashed and boot CROSSED by that run (confirmed-twin, bss-8), light-off-again never tested; 3 of 6 paths '
          'tested (the chain nodes\' own paths crossed); led_on covered, 6 fields never changed; assertions exercised = led_toggle / apply_command (led_on) + led_follow_state '
          '(PD6 read) + telemetry_send sends (frames) = 4 of 7',
          s['nodes_by_state']['confirmed-twin'] == 3 and s['nodes_by_state']['never-tested'] == 1 and s['paths_tested'] == 3 and s['paths'] == 6
          and s['fields_covered'] == ['led_on'] and len(s['fields_never_changed']) == 6 and (s['assertions_exercised'], s['assertions']) == (4, 7),
          {k: s[k] for k in ('nodes_by_state', 'paths_tested', 'paths', 'fields_covered', 'assertions_exercised', 'assertions')})
    u1 = COV.untested(m, BS)
    check('THE UNTESTED LIST after the run: light-on is confirmed by 1 of 2 paths (said), light-off-again never tested, the unexercised assertions named (seq, boot_session, '
          'the receive), light-on itself no longer "never tested"',
          any(w == '%s: confirmed by 1 of 2 paths' % light['name'] for w in u1) and any(w.endswith('light-off-again: never tested') for w in u1)
          and not any(w == '%s: never tested' % light['name'] for w in u1) and sum(w.startswith('assertion ') for w in u1) == 3, u1)
    ns = {n['node']: n for n in COV.nodes(m, BS)}
    check('PER NODE: light-on state confirmed-twin, 1 run, paths 1 / 2, confirmed by twin, 1 voided, collaterals 1 / 1 measured; light-off-again never-tested with 0 runs',
          ns[light['name']]['state'] == 'confirmed-twin' and ns[light['name']]['runs'] == 1 and (ns[light['name']]['paths_tested'], ns[light['name']]['paths']) == (1, 2)
          and ns[light['name']]['confirmed_by'] == 'twin' and ns[light['name']]['voided'] == 1 and ns[light['name']]['collaterals_measured'] == '1 / 1'
          and ns['%s:light-off-again' % BS]['state'] == 'never-tested', ns[light['name']])
    ev = {e['name'].split(':', 1)[1]: e for e in events(m, BS)}
    check('EVENTS: the press is used by an edge and was run; the command is used but never run; the release is neither',
          (ev['press-PD2']['used_by_an_edge'], ev['press-PD2']['ever_run']) == ('yes', 'yes') and (ev['command-uno-1-bridge']['used_by_an_edge'], ev['command-uno-1-bridge']['ever_run']) == ('yes', 'no')
          and (ev['release-PD2']['used_by_an_edge'], ev['release-PD2']['ever_run']) == ('no', 'no'), {k: (e['used_by_an_edge'], e['ever_run']) for k, e in ev.items()})
    sr = strip_rows(m, BS)
    check('THE STRIP AS ROWS for the table: the untested count first, then nodes, paths, fields, samples, assertions, the events by kind / source',
          [r['measure'] for r in sr][:6] == ['untested items', 'nodes', 'paths tested', 'struct fields covered', 'samples used', 'assertions exercised'] and sr[0]['value'] == len(u1)
          and any(r['measure'].startswith('events actuation / person') for r in sr) and sr[-1]['measure'] == 'the drawing' and sr[-1]['value'].endswith('bench-topology-%s' % BS), [r['measure'] for r in sr])
    from cmod.hardware_events_page import HARDWARE_EVENTS_PAGES
    import json
    page = HARDWARE_EVENTS_PAGES[0]
    pdef = json.loads(page['definition']) if isinstance(page.get('definition'), str) else page.get('definition', {})
    paths = set()

    def walk(x):
        if isinstance(x, dict):
            for k, val in x.items():
                if k == 'data_path' or k == 'dataPath':
                    paths.add(val)
                walk(val)
        elif isinstance(x, list):
            for i in x:
                walk(i)
    walk(pdef)
    tabs = [t['key'] for t in pdef.get('tabs', [])]
    check('THE PAGE: /display/hardware-events with the picker and six tabs (overview first); every table reads a door this module or the board module serves; the one '
          'chart (bss-10) reads the instruments arc\'s capture chart door',
          page.get('pageRoute') == 'hardware-events' and tabs == ['overview', 'nodes', 'events', 'runs', 'assertions', 'profiles']
          and all(p.startswith('/api/cmod/bench-topology/') or p.startswith('/api/board/bench-solutions') or p.startswith('/api/instruments/captures/') for p in paths)
          and any('/coverage/untested' in p for p in paths) and any('/runs/{scope:run}/captures' in p for p in paths), (tabs, sorted(paths)))
    api = CoverageAPI(polServer=None, manager=m)

    def call(method, *args):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        getattr(api, method)(None, resp, *args)
        return resp
    g = call('on_get', BS)
    un = call('on_get_untested', BS)
    nf = call('on_get_nodes', 'nope')
    check('DOORS: GET coverage -> the strip with the untested list; GET untested -> {rows: [{words}]}; unknown Bench Solution -> 404',
          g.media['ok'] and g.media['untested'] == u1 and un.media['rows'] == [{'words': w} for w in u1] and nf.status.startswith('404'), (nf.status, nf.media))
    from moduleService.manifests import conform
    rr = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with the new files listed', rr['ok'], rr.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
