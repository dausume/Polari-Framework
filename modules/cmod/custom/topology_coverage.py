"""
@module cmod.custom.topology_coverage

bss-6 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b "Making it obvious what was tested"): WHAT WAS TESTED, AND WHAT WAS NOT, for one Bench
Solution - derived on read from the topology's rows, never stored. The untested list comes first and an empty list is the only green.

    strip(manager, bs)        the coverage strip: nodes by confirmation state, events by kind / source with how many were ever run, struct fields covered
                              (changed by a run that met its node) vs never changed, samples declared vs used, paths tested per node, assertions exercised
    untested(manager, bs)     the untested list, in words, first: nodes never tested; nodes with only voided confirmations; nodes confirmed by one path when
                              others exist; blocked nodes and the field that blocks each; collaterals never measured; events never used by any edge;
                              assertions never exercised; proposed nodes not yet accepted
    nodes(manager, bs)        one row per node: title, state, runs, paths (tested / all), confirmations (live / voided), blocked words, the test card's gist
    assertions(manager, bs)   one row per CatomAssertion of the firmware's variant: exercised by which confirmed node's run, or not
"""
from cmod.custom import bench_events as E
from cmod.custom import bench_topology as T
from cmod.custom import catom_config as CF
from cmod.custom import config_rows as R

STATES = ('confirmed-hardware', 'confirmed-twin', 'confirmed-person', 'checks-failed', 'diverged', 'not-reached', 'blocked', 'voided', 'never-tested', 'proposed')


def _state(manager, node):
    from cmod.custom.bench_topology_nocode import _confirmation
    return _confirmation(manager, node)[0]


def _runs(manager, node):
    return sorted(R.rows(manager, 'StructNodeRun', node=node), key=lambda r: r['name'])


def _met_runs(manager, bs):
    """The runs that met their node (reached or checks-failed): what they changed is what was exercised."""
    out = []
    for n in R.rows(manager, 'StructNode', bench_solution=bs):
        out += [r for r in _runs(manager, n['name']) if r['outcome'] in ('reached', 'checks-failed')]
    return out


def _changed_fields(manager, runs):
    fields = set()
    for r in runs:
        for s in R.rows(manager, 'StructNodeRunSignal', run=r['name'], kind='field'):
            if s['changes'] > 0:
                fields.add(s['signal'])
    return fields


def nodes(manager, bs):
    out = []
    for n in sorted(R.rows(manager, 'StructNode', bench_solution=bs), key=lambda n: n['name']):
        runs = _runs(manager, n['name'])
        paths = R.rows(manager, 'StructNodePath', node=n['name'])
        tested_paths = {r['path'] for r in runs if r['outcome'] in ('reached', 'checks-failed')}
        if n['kind'] in ('flashed', 'boot'):   # bss-8: a chain node is tested by the runs that crossed it
            from cmod.custom.bench_topology_nocode import crossings
            crossed = crossings(manager, n)
            runs = [R.get(manager, 'StructNodeRun', r) for r in crossed]
            tested_paths = {p['name'] for p in paths} if crossed else set()
        confs = R.rows(manager, 'StructNodeConfirmation', node=n['name'])
        live = [c for c in confs if c['state'] == 'confirmed']
        cols = R.rows(manager, 'StructNodeCollateral', node=n['name'])
        measured = set()
        for r in runs:
            for e in R.rows(manager, 'StructNodeRunEdge', run=r['name']):
                for c in cols:
                    if '%s %s:' % (c['kind'], c['signal']) in e['collaterals'] and 'unmeasured' not in e['collaterals'].split('%s %s:' % (c['kind'], c['signal']))[1].split(';')[0]:
                        measured.add(c['name'])
        out.append({'node': n['name'], 'title': n['title'], 'kind': n['kind'], 'basis': n.get('basis', 'person'), 'state': _state(manager, n), 'runs': len(runs),
                    'last_outcome': runs[-1]['outcome'] if runs else '', 'paths_tested': len(tested_paths), 'paths': len(paths), 'confirmed_by': ', '.join(sorted({c['by'] for c in live})),
                    'voided': len(confs) - len(live), 'blocked': '; '.join(T.blocks(manager, n['name'])), 'collaterals_measured': '%d / %d' % (len(measured), len(cols)),
                    'stale': any(r['hex_sha256'] and c['hex_sha256'] and r['hex_sha256'] != c['hex_sha256'] for r in runs[-1:] for c in live)})
    return out


def assertions(manager, bs):
    ctx = CF.context(manager, bs)
    variant = E.variant_of(manager, ctx['firmware_solution'])
    met = _met_runs(manager, bs)
    changed = _changed_fields(manager, met)
    frames = any('frame' in e['collaterals'] and 'bytes on the UART' in e['collaterals'] and not e['collaterals'].split('bytes on the UART')[0].rstrip().endswith(' 0')
                 for r in met for e in R.rows(manager, 'StructNodeRunEdge', run=r['name']))
    commanded = False
    for r in met:
        for e in R.rows(manager, 'StructNodeRunEdge', run=r['name'], outcome='met'):
            ed = R.get(manager, 'StructEdge', e['edge'])
            ev = R.get(manager, 'HardwareEvent', ed['event']) if ed and ed.get('event') else None
            if ev and ev['source'] == 'polari':
                commanded = True
    out = []
    for a in E._assertions(manager, variant):
        if a['kind'] == 'changes-field':
            fields = {f.strip() for f in a.get('fields', '').split(',') if f.strip()}
            hit = sorted(fields & changed)
            out.append({'assertion': a['name'], 'atom': a['atom'], 'kind': a['kind'], 'exercised': bool(hit), 'how': ('fields %s changed in a run that met its node' % ', '.join(hit)) if hit else 'no run that met its node changed %s' % ', '.join(sorted(fields))})
        elif a['kind'] == 'sends-to-bridge':
            out.append({'assertion': a['name'], 'atom': a['atom'], 'kind': a['kind'], 'exercised': frames,
                        'how': 'frames left on the UART in a run that met its node' if frames else 'no run observed a frame leaving'})
        elif a['kind'] == 'receives-from-bridge':   # bss-8: exercised when a run met a node through a command edge (the frame arrived and was applied)
            out.append({'assertion': a['name'], 'atom': a['atom'], 'kind': a['kind'], 'exercised': commanded,
                        'how': 'a command frame arrived and its node was met' if commanded else 'no run met a node through a command edge'})
        elif a['kind'] == 'reads-field':
            pins = [p.strip() for p in a.get('pins', '').split(',') if p.strip()]
            seen = any(any('pin-level %s: high' % p in e['collaterals'] or 'pin-level %s: low' % p in e['collaterals'] for p in pins) for r in met for e in R.rows(manager, 'StructNodeRunEdge', run=r['name']))
            out.append({'assertion': a['name'], 'atom': a['atom'], 'kind': a['kind'], 'exercised': seen, 'how': 'its pin was read on the wire in a run that met its node' if seen else 'its pin %s was never measured' % ', '.join(pins)})
    return out


def strip(manager, bs):
    ns = nodes(manager, bs)
    by_state = {s: sum(1 for n in ns if n['state'] == s) for s in STATES}
    events = R.rows(manager, 'HardwareEvent', bench_solution=bs)
    edges = R.rows(manager, 'StructEdge', bench_solution=bs)
    used = {e['event'] for e in edges if e['event']}
    run_events = set()
    for n in ns:
        for r in _runs(manager, n['node']):
            for re_ in R.rows(manager, 'StructNodeRunEdge', run=r['name']):
                ed = R.get(manager, 'StructEdge', re_['edge'])
                if ed and ed['event'] and re_['outcome'] != 'skipped':
                    run_events.add(ed['event'])
    ev_rows = {}
    for ev in events:
        k = '%s / %s' % (ev['kind'], ev['source'])
        d = ev_rows.setdefault(k, {'kind_source': k, 'events': 0, 'used_by_an_edge': 0, 'ever_run': 0})
        d['events'] += 1
        d['used_by_an_edge'] += ev['name'] in used
        d['ever_run'] += ev['name'] in run_events
    maps = {q['object_map'] for n in ns for q in R.rows(manager, 'StructNodeRequirement', node=n['node'])}
    all_fields = set()
    import json
    for om in maps:
        som = R.get(manager, 'StructObjectMap', om)
        all_fields |= {f.get('field') for f in json.loads((som or {}).get('fields_json') or '[]') if f.get('field')}
    changed = _changed_fields(manager, _met_runs(manager, bs))
    samples = R.rows(manager, 'StructFieldSamples')
    used_samples = {(q['object_map'], q['field'], str(q['value'])) for n in ns for q in R.rows(manager, 'StructNodeRequirement', node=n['node']) if q['kind'] == 'exact'}
    declared = sum(len([v for v in s['values'].split(',') if v.strip()]) for s in samples)
    used_count = sum(1 for s in samples for v in s['values'].split(',') if v.strip() and (s['object_map'], s['field'], v.strip()) in used_samples)
    asr = assertions(manager, bs)
    return {'ok': True, 'bench_solution': bs, 'nodes_by_state': by_state, 'nodes': len(ns), 'events': sorted(ev_rows.values(), key=lambda d: d['kind_source']),
            'fields_covered': sorted(changed & all_fields), 'fields_never_changed': sorted(all_fields - changed), 'samples_declared': declared, 'samples_used': used_count,
            'paths_tested': sum(n['paths_tested'] for n in ns), 'paths': sum(n['paths'] for n in ns),
            'assertions_exercised': sum(1 for a in asr if a['exercised']), 'assertions': len(asr), 'untested': untested(manager, bs), 'inert_events': inert_events(manager, bs)}


def untested(manager, bs):
    words = []
    ns = nodes(manager, bs)
    for n in ns:
        if n['basis'] == 'proposed':
            words.append('%s: proposed from a divergence, not yet accepted or discarded' % n['node'])
        elif n['kind'] != 'root' and n['runs'] == 0:
            words.append('%s: never tested' % n['node'])
        elif n['voided'] and not n['confirmed_by'] and n['kind'] != 'root':
            words.append('%s: only voided confirmations (the build changed): test it again' % n['node'])
        elif n['confirmed_by'] and n['paths'] > n['paths_tested'] > 0:
            words.append('%s: confirmed by %d of %d paths' % (n['node'], n['paths_tested'], n['paths']))
        if n['blocked']:
            words.append('%s: blocked - %s' % (n['node'], n['blocked']))
        if n['collaterals_measured'] not in ('0 / 0',) and n['collaterals_measured'].split(' / ')[0] != n['collaterals_measured'].split(' / ')[1]:
            words.append('%s: collaterals measured %s' % (n['node'], n['collaterals_measured']))
        if n['stale']:
            words.append('%s: its latest run is on another build than its confirmation' % n['node'])
    used = {e['event'] for e in R.rows(manager, 'StructEdge', bench_solution=bs) if e['event']}
    for ev in R.rows(manager, 'HardwareEvent', bench_solution=bs):
        if ev['name'] not in used and not inert(manager, bs, ev):
            words.append('event %s (%s): no edge uses it' % (ev['name'].split(':', 1)[-1], ev['title']))
    for a in assertions(manager, bs):
        if not a['exercised']:
            words.append('assertion %s: %s' % (a['assertion'].split(':', 1)[-1], a['how']))
    return words


def inert(manager, bs, ev):
    """bss-8: an event the firmware's own claims predict NO struct change for (a release: 'the firmware asserts nothing on it') cannot end an edge - the
    rule (section 2) - so it is not untested; it is listed apart (inert_events) so nobody looks for the missing edge."""
    try:
        return not E.predicted(manager, bs, ev['name'])
    except R.ConfigRefused:
        return False


def inert_events(manager, bs):
    return [{'event': ev['name'], 'title': ev['title'], 'why': 'the firmware asserts no struct change on it: no edge can end on it (the rule); offered so a person sees it'}
            for ev in sorted(R.rows(manager, 'HardwareEvent', bench_solution=bs), key=lambda e: e['name']) if inert(manager, bs, ev)]
