"""
@module cmod.custom.retest

bss-4 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 7; cfg-4 merged here, D-bss-4): A CONFIGURATION OR ISOTOPE CHANGE = REBUILD, VOID THAT BUILD'S
CONFIRMATIONS, RE-TEST THE AFFECTED NODES FIRST. The rebuild happens by itself (node_run builds the Firmware Solution's current sources); the voiding
happens by itself (confirmations.confirm voids a node's confirmations of another build); this file orders the work and syncs the executions' isotopes:

    affected(manager, bs, catom)     the nodes whose executions belong to the catom's JOB (the isotope's job, else isotope_variants.job_atoms), fastest path first
    sync_isotopes(manager, bs)       every StructNodeExecution's `isotope` <- the Firmware Solution's CatomConfiguration for its job when that holds an
                                     IsotopeVariant route ('gpio-poll' -> 'read-button:gpio-poll'); a person's explicit isotope on the execution is kept
    retest(manager, bs, catom='')    run the affected nodes first, then every other state node, each from the root along its fastest path; -> the ordered
                                     outcomes, the confirmations voided along the way, the isotopes synced
"""
from cmod.custom import bench_topology as T
from cmod.custom import catom_config as CF
from cmod.custom import config_rows as R


def _job_of_atom(atom):
    """The isotope job an atom belongs to ('apps/light.led_toggle' -> 'read-button'), from the job seeds' atom lists; '' when none claims it."""
    from cmod.custom import isotope_variants as IV
    short = atom.split(':')[-1]
    for job in IV.jobs():
        names = IV.job_atoms(job).get('atoms', [])
        if any(n.split(':')[-1] == short for n in names):
            return job['name']
    return ''


def affected(manager, bs, catom):
    out = []
    for n in R.rows(manager, 'StructNode', bench_solution=bs):
        if n['kind'] != 'state':
            continue
        for x in R.rows(manager, 'StructNodeExecution', node=n['name']):
            job = _job_of_atom(x['atom'])
            if catom and catom in (job, x['atom'], x['atom'].split('.')[-1], x['isotope'].split(':')[0]):
                out.append(n['name'])
                break
    return sorted(set(out), key=lambda name: (next((p['length'] for p in R.rows(manager, 'StructNodePath', node=name) if p['fastest']), 99), name))


def sync_isotopes(manager, bs):
    ctx = CF.context(manager, bs)
    changed = []
    for n in R.rows(manager, 'StructNode', bench_solution=bs):
        for x in R.rows(manager, 'StructNodeExecution', node=n['name']):
            if x.get('notes', '').startswith('isotope: person'):
                continue
            job = x['isotope'].split(':')[0] if ':' in x['isotope'] else _job_of_atom(x['atom'])   # the job seeds list the HAL atoms; an app atom's job is its isotope's
            if not job:
                continue
            conf = R.get(manager, 'CatomConfiguration', '%s:%s' % (ctx['firmware_solution'], job))
            route = (conf or {}).get('isotope', '')
            if route and ':' not in route:
                route = '%s:%s' % (job, route)
            if route and route != x['isotope']:
                R.upsert(manager, 'StructNodeExecution', x['name'], isotope=route, notes='isotope: from CatomConfiguration %s' % conf['name'])
                changed.append({'execution': x['name'], 'from': x['isotope'], 'to': route})
    return changed


def retest(manager, bs, catom=''):
    from cmod.custom import node_run as NR
    synced = sync_isotopes(manager, bs)
    first = affected(manager, bs, catom) if catom else []
    rest = sorted([n['name'] for n in R.rows(manager, 'StructNode', bench_solution=bs) if n['kind'] == 'state' and n.get('basis') != 'proposed' and n['name'] not in first],
                  key=lambda name: (next((p['length'] for p in R.rows(manager, 'StructNodePath', node=name) if p['fastest']), 99), name))
    voided_before = sum(1 for c in R.rows(manager, 'StructNodeConfirmation', state='voided'))
    runs = []
    for name in first + rest:
        try:
            out = NR.run(manager, bs, name)
            runs.append({'node': name, 'affected': name in first, 'outcome': out['run']['outcome'], 'run': out['run']['name'], 'words': out['run']['words'][:160]})
        except R.ConfigRefused as e:
            runs.append({'node': name, 'affected': name in first, 'outcome': 'refused', 'run': '', 'words': e.why})
    voided = sum(1 for c in R.rows(manager, 'StructNodeConfirmation', state='voided')) - voided_before
    return {'ok': True, 'bench_solution': bs, 'catom': catom, 'affected_first': first, 'runs': runs, 'confirmations_voided': voided, 'isotopes_synced': synced,
            'words': '%d node%s re-tested (%d affected by %r first); %d confirmation%s of other builds voided; %d execution isotope%s synced from the configurations'
                     % (len(runs), '' if len(runs) == 1 else 's', len(first), catom or 'nothing named', voided, '' if voided == 1 else 's', len(synced), '' if len(synced) == 1 else 's')}


def run_all(manager, bs):
    """bss-8: EVERY state node by EVERY path, fastest first (the whole topology tested from the root), then the coverage's untested list - the only green is
    an empty one. -> {runs, reached, of, untested, words}."""
    from cmod.custom import node_run as NR
    from cmod.custom import topology_coverage as COV
    synced = sync_isotopes(manager, bs)
    names = sorted([n['name'] for n in R.rows(manager, 'StructNode', bench_solution=bs) if n['kind'] == 'state' and n.get('basis') != 'proposed'],
                   key=lambda name: (next((p['length'] for p in R.rows(manager, 'StructNodePath', node=name) if p['fastest']), 99), name))
    runs = []
    for name in names:
        for p in sorted(R.rows(manager, 'StructNodePath', node=name), key=lambda p: (not p['fastest'], p['length'], p['name'])):
            try:
                out = NR.run(manager, bs, name, path=p['name'])
                runs.append({'node': name, 'path': p['name'], 'length': p['length'], 'outcome': out['run']['outcome'], 'run': out['run']['name'],
                             'duration_s': out['run']['duration_s'], 'words': out['run']['words'][:200]})
            except R.ConfigRefused as e:
                runs.append({'node': name, 'path': p['name'], 'length': p['length'], 'outcome': 'refused', 'run': '', 'duration_s': -1.0, 'words': e.why})
    reached = sum(1 for r in runs if r['outcome'] == 'reached')
    untested = COV.untested(manager, bs)
    return {'ok': True, 'bench_solution': bs, 'runs': runs, 'reached': reached, 'of': len(runs), 'isotopes_synced': synced, 'untested': untested,
            'words': '%d of %d path run%s reached their node (%d node%s); %s' % (reached, len(runs), '' if len(runs) == 1 else 's', len(names), '' if len(names) == 1 else 's',
                                                                                 'nothing untested' if not untested else '%d untested item%s' % (len(untested), '' if len(untested) == 1 else 's'))}


def run_signals(manager, run):
    if R.get(manager, 'StructNodeRun', run) is None:
        raise R.ConfigRefused('no run %r' % run, status=404)
    return sorted(R.rows(manager, 'StructNodeRunSignal', run=run), key=lambda s: (s['kind'], s['signal']))


def run_edges(manager, run):
    if R.get(manager, 'StructNodeRun', run) is None:
        raise R.ConfigRefused('no run %r' % run, status=404)
    return sorted(R.rows(manager, 'StructNodeRunEdge', run=run), key=lambda e: e['order'])
