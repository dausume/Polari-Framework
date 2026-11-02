"""cmod_confirmations_selftest - bss-3 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md): confirmations, edge checks, divergence proposals, manual test profiles and
play-from, on the real twin: a reached run writes a twin confirmation for its path and build; a confirmation of another build is voided (never deleted) with
why; a person attests; a hardware record is judged against the same requirements (accepted / refused with the field); an edge timing check too tight ->
checks-failed and no confirmation; a divergence proposes a node (basis proposed) with the reached values and an edge into it, once; a manual profile adds a
field to watch and names an unwired pin honestly; play-from marks the replayed edges; the doors; the manifest.

Needs the avr engines (a local polari-avr-twin or the prf-board-engines image).

    PYTHONPATH=.:modules python3 -m cmod.cmod_confirmations_selftest      # from polari-framework/
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
    from board.custom import light_twin
    from cmod.custom import bench_topology as T
    from cmod.custom import confirmations as C
    from cmod.custom import config_rows as R
    from cmod.custom import node_run as NR
    from cmod.cmod_confirmations_api import ConfirmationsAPI, add_check, add_profile
    ready, why = light_twin.engine_ready()
    check('the avr engines are reachable: %s' % why, ready, why)
    if not ready:
        print('\n%d/%d passed' % (passed, total))
        return 1
    m = _manager()
    _seed(m)
    v = T.view(m, BS)
    boot = next(n for n in v['nodes'] if n['kind'] == 'boot')
    press = '%s:press-PD2' % BS
    node = T.define(m, BS, 'light-on', 'light on', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 1}],
                    executions=[{'atom': 'apps/light.led_follow_state', 'isotope': 'drive-led:gpio-out'}])
    R.upsert(m, 'StructNodeConfirmation', '%s#conf1' % node['name'], node=node['name'], path='old', by='twin', hex_sha256='0' * 64, state='confirmed', words='an older build')
    out = NR.run(m, BS, node['name'])
    confs = C.of(m, node['name'])
    new = [c for c in confs if c['state'] == 'confirmed']
    old = [c for c in confs if c['state'] == 'voided']
    check('A REACHED run writes a TWIN CONFIRMATION for its path and build, and the confirmation of another build is VOIDED with why (never deleted)',
          out['run']['outcome'] == 'reached' and len(new) == 1 and new[0]['by'] == 'twin' and new[0]['run'] == out['run']['name'] and new[0]['hex_sha256'] == out['run']['hex_sha256']
          and len(old) == 1 and old[0]['voided_why'].startswith('the build changed'), [(c['state'], c['by'], c['voided_why'][:40]) for c in confs])
    att = C.attest(m, node['name'], 'a person at the bench', 'I saw the light come on')
    check('A PERSON\'s attestation is a confirmation by person, on the latest run\'s build', att['by'] == 'person' and att['hex_sha256'] == out['run']['hex_sha256'] and att['who'])
    hw = C.from_record(m, node['name'], '', {'hex_sha256': out['run']['hex_sha256'], 'source': 'a board log', 'fields': {'led_on': 1}, 'duration_s': 0.0012})
    try:
        C.from_record(m, node['name'], '', {'hex_sha256': out['run']['hex_sha256'], 'source': 'a board log', 'fields': {'led_on': 0}})
        refused = ''
    except R.ConfigRefused as e:
        refused = e.why
    check('A HARDWARE RECORD is judged against the SAME requirements: led_on = 1 -> a hardware confirmation; led_on = 0 -> refused naming the field',
          hw['by'] == 'hardware' and 'reached in 1.200 ms' in hw['words'] and refused == 'the record does not meet led_on exact 1 (record: 0)', (hw['words'], refused))
    edge = node['fastest_path']['edges'].split(',')[-1]
    add_check(m, BS, {'edge': edge, 'kind': 'timing', 'bound_s': 1e-6})
    o2 = NR.run(m, BS, node['name'])
    check('An EDGE CHECK too tight (reached within 1 us) -> checks-failed: the requirements were met but no new confirmation is written', o2['run']['outcome'] == 'checks-failed'
          and 'checks failed: reached in' in o2['edges'][-1]['words'] and len([c for c in C.of(m, node['name']) if c['state'] == 'confirmed']) == 3, (o2['run']['outcome'], o2['edges'][-1]['words'][-120:]))
    add_check(m, BS, {'edge': edge, 'kind': 'timing', 'bound_s': 0.1})
    try:
        add_check(m, BS, {'edge': edge, 'kind': 'field-tolerance', 'field': 'toggles'})
        tol = ''
    except R.ConfigRefused as e:
        tol = e.why
    check('A check\'s needs are refused in words: a tolerance check without a tolerance', tol.startswith('a field-tolerance check needs the field and a tolerance'), tol)
    T.define(m, BS, 'seven', '', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 7}], executions=['apps/light.led_toggle'])
    o3 = NR.run(m, BS, '%s:seven' % BS)
    o3b = NR.run(m, BS, '%s:seven' % BS)
    proposed = R.rows(m, 'StructNode', bench_solution=BS, basis='proposed')
    preq = R.rows(m, 'StructNodeRequirement', node=proposed[0]['name']) if proposed else []
    pedges = [e for e in R.rows(m, 'StructEdge', bench_solution=BS) if proposed and e['to_node'] == proposed[0]['name']]
    check('A DIVERGENCE proposes ONE node (basis proposed, unnamed) with the reached value led_on = 1, reached by the same press from boot; a second identical run proposes nothing new',
          o3['run']['outcome'] == 'diverged' and o3b['run']['outcome'] == 'diverged' and len(proposed) == 1 and proposed[0]['title'] == ''
          and [(q['field'], q['kind'], q['value']) for q in preq] == [('led_on', 'exact', '1')] and len(pedges) == 1 and pedges[0]['from_node'] == boot['name'] and pedges[0]['event'] == press,
          (len(proposed), preq, [e['name'] for e in pedges]))
    add_profile(m, BS, {'name': 'light-and-toggles', 'title': 'the light and the toggle count', 'items': [{'kind': 'field', 'signal': 'toggles', 'object_map': MAP}, {'kind': 'pin', 'signal': 'PB5'}]})
    o4 = NR.run(m, BS, node['name'], profile='light-and-toggles')
    sig = {s['signal']: s for s in o4['signals']}
    check('A MANUAL PROFILE adds a field to watch (toggles 0 -> 1 on the press) and names a pin the config does not wire, honestly',
          o4['run']['profile'] == 'light-and-toggles' and 'toggles' in sig and sig['toggles']['last'] == '1' and 'profile pins not wired in this config: PB5' in o4['run']['words'],
          (sorted(sig), o4['run']['words'][-80:]))
    o5 = NR.run(m, BS, node['name'], play_from=boot['name'])
    check('PLAY FROM boot: the flash and init edges are replayed silently (said), the press edge is the one watched',
          o5['run']['play_from'] == boot['name'] and o5['edges'][0]['words'].startswith('replayed silently') and o5['edges'][1]['words'].startswith('replayed silently')
          and not o5['edges'][2]['words'].startswith('replayed'), [e['words'][:40] for e in o5['edges']])
    api = ConfirmationsAPI(polServer=None, manager=m)

    def call(method, *args, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(api, method)(req, resp, *args)
        return resp
    g = call('on_get_confirmations', BS, 'light-on')
    bad = call('on_post_hardware_record', BS, 'light-on', body={'fields': {'led_on': 0}, 'source': 'x'})
    pr = call('on_get_profiles', BS)
    ck = call('on_post_checks', BS, body={'edge': 'nope', 'kind': 'timing', 'bound_s': 1})
    check('DOORS: GET confirmations (voided kept, marked); POST a failing hardware record -> 422 naming the field; GET profiles lists the manual one with its items; a check on an unknown edge -> 404',
          len(g.media['rows']) >= 4 and any(c['state'] == 'voided' for c in g.media['rows']) and bad.status.startswith('422') and 'led_on' in bad.media['error']
          and pr.media['rows'][0]['name'] == 'light-and-toggles' and len(pr.media['rows'][0]['items']) == 2 and ck.status.startswith('404'), (bad.status, ck.status))
    from moduleService.manifests import conform
    rr = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with the new rows and files listed', rr['ok'], rr.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
