"""
@module cmod.custom.bench_topology

bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md sections 2-4): THE HARDWARE EVENT TOPOLOGY of one Bench Solution - nodes (end-state requirements),
edges, paths from the root, and what each node asks of the simulation. Rows are small and name each other; everything a person did not type is derived.

  root_chain(manager, bs)        the fixed first chain: plugged-in -(flash)-> flashed -(init)-> boot; boot's requirements = the fields the init lane writes
  define(manager, bs, slug, title, from_node, edge_kind, event, requirements, executions, collaterals)   a node, its rows and the edge that reaches it
  paths(manager, node)           every simple path root -> node as StructNodePath rows (fastest flagged); stale rows dropped
  blocks(manager, node)          words: exact requirements on samples-kind fields whose value is not declared
  step_of(manager, node)         {'step_s', 'step_set_by'}: the finest IsotopeStepRule among the node's executions
  view(manager, bs)              everything above for the pages and the canvas
"""
from cmod.custom import bench_events as E
from cmod.custom import catom_config as CF
from cmod.custom import config_rows as R
from cmod.custom import isotope_step_rules as S

MAX_PATHS = 64


def _slug(bs, slug):
    return '%s:%s' % (bs, slug)


def _edge(manager, bs, from_node, to_node, kind, event='', title=''):
    """'<from>-><to slug>', and ' via <event slug>' for a trigger, so two triggers into the same node are two edges."""
    name = '%s->%s' % (from_node, to_node.split(':')[-1]) + (' via %s' % event.split(':', 1)[-1] if kind == 'trigger' and event else '')
    return R.upsert(manager, 'StructEdge', name, title=title, bench_solution=bs, from_node=from_node, to_node=to_node, kind=kind, event=event)


def root_chain(manager, bs):
    ctx = CF.context(manager, bs)
    root, flashed, boot = _slug(bs, 'plugged-in'), _slug(bs, 'flashed'), _slug(bs, 'boot')
    R.upsert(manager, 'StructNode', root, title='plugged in', bench_solution=bs, kind='root',
             notes='the bridge sees the board\'s serial device; the bootloader answers; no structs yet')
    R.upsert(manager, 'StructNode', flashed, title='flashed', bench_solution=bs, kind='flashed',
             notes='the flash tool\'s verify complete; hex sha256 = Firmware Solution %r\'s build' % ctx['firmware_solution'])
    R.upsert(manager, 'StructNode', boot, title='boot', bench_solution=bs, kind='boot', notes='reset after the flash; the HAL\'s init done')
    _edge(manager, bs, root, flashed, 'flash', title='the USB flashes the firmware')
    _edge(manager, bs, flashed, boot, 'init', title='reset, then init')
    variant = E.variant_of(manager, ctx['firmware_solution'])
    for a in E._assertions(manager, variant):
        if a['kind'] == 'changes-field' and a.get('lane') == 'init':
            for f in [x.strip() for x in a.get('fields', '').split(',') if x.strip()]:
                R.upsert(manager, 'StructNodeRequirement', '%s:%s' % (boot, f), node=boot, object_map=a.get('object_map', ''), field=f, kind='written',
                         notes='written at init by %s (%s)' % (a['atom'], a['name']))
    return {'root': root, 'flashed': flashed, 'boot': boot}


def define(manager, bs, slug, title, from_node, edge_kind='trigger', event='', requirements=(), executions=(), collaterals=()):
    if R.get(manager, 'StructNode', from_node) is None:
        raise R.ConfigRefused('no node %r to start from' % from_node, status=404)
    if edge_kind == 'trigger' and R.get(manager, 'HardwareEvent', event) is None:
        raise R.ConfigRefused('no Hardware Event %r' % event, status=404)
    if not requirements:
        raise R.ConfigRefused('a node needs at least one requirement on a struct field')
    node = _slug(bs, slug)
    ctx = CF.context(manager, bs)
    A = {a['name']: a for a in E._assertions(manager, E.variant_of(manager, ctx['firmware_solution']))}
    R.upsert(manager, 'StructNode', node, title=title, bench_solution=bs, kind='state', collaterals='none')
    for cls in ('StructNodeRequirement', 'StructNodeExecution', 'StructNodeCollateral'):
        R.drop(manager, cls, node=node)
    for q in requirements:
        R.upsert(manager, 'StructNodeRequirement', '%s:%s' % (node, q['field']), node=node, object_map=q.get('object_map', ''), field=q['field'],
                 kind=q.get('kind', 'exact'), value=str(q.get('value', '')))
    derived = []
    for i, x in enumerate(executions, 1):
        x = {'atom': x} if isinstance(x, str) else x
        asser = x.get('assertion') or next((n for n, a in A.items() if a['atom'] == x['atom'] and a['kind'] == 'reads-field'), '')
        R.upsert(manager, 'StructNodeExecution', '%s:%d' % (node, i), node=node, order=i, atom=x['atom'], isotope=x.get('isotope', ''), assertion=asser)
        for a in A.values():   # a reads-field on this atom drives pins: a pin-level collateral; a sends-to-bridge: a frame collateral
            if a['atom'] != x['atom']:
                continue
            if a['kind'] == 'reads-field':
                derived += [dict(kind='pin-level', signal=p.strip(), engine='twin', bound='', source='derived', notes='from %s' % a['name']) for p in a.get('pins', '').split(',') if p.strip()]
            if a['kind'] == 'sends-to-bridge' and a.get('bridge'):
                derived.append(dict(kind='frame', signal=a['bridge'], engine='twin', bound='', source='derived', notes='from %s' % a['name']))
    rows = list(collaterals) + [d for d in derived if not any(c.get('kind') == d['kind'] and c.get('signal') == d['signal'] for c in collaterals)]
    for c in rows:
        R.upsert(manager, 'StructNodeCollateral', '%s:%s:%s' % (node, c['kind'], c['signal']), node=node, **{k: v for k, v in c.items() if k != 'name'})
    R.upsert(manager, 'StructNode', node, collaterals=('declared' if collaterals else 'derived') if rows else 'none')
    _edge(manager, bs, from_node, node, edge_kind, event=event if edge_kind == 'trigger' else '',
          title=(R.get(manager, 'HardwareEvent', event) or {}).get('title', '') if edge_kind == 'trigger' else edge_kind)
    all_paths(manager, bs)
    return node_view(manager, node)


def connect(manager, bs, from_node, to_node, kind='trigger', event=''):
    """A second (or later) edge into an existing node - another path to the same requirements. -> the node view with its paths re-derived."""
    for n in (from_node, to_node):
        if R.get(manager, 'StructNode', n) is None:
            raise R.ConfigRefused('no node %r' % n, status=404)
    if kind == 'trigger' and R.get(manager, 'HardwareEvent', event) is None:
        raise R.ConfigRefused('no Hardware Event %r' % event, status=404)
    _edge(manager, bs, from_node, to_node, kind, event=event if kind == 'trigger' else '',
          title=(R.get(manager, 'HardwareEvent', event) or {}).get('title', '') if kind == 'trigger' else kind)
    all_paths(manager, bs)
    return node_view(manager, to_node)


def all_paths(manager, bs):
    """A new edge changes the paths of every node below it: re-derive them all (cheap: a handful of nodes)."""
    for n in R.rows(manager, 'StructNode', bench_solution=bs):
        if n['kind'] != 'root':
            paths(manager, n['name'])


def paths(manager, node):
    n = R.get(manager, 'StructNode', node)
    if n is None:
        raise R.ConfigRefused('no node %r' % node, status=404)
    bs = n['bench_solution']
    edges = R.rows(manager, 'StructEdge', bench_solution=bs)
    into = {}
    for e in edges:
        into.setdefault(e['to_node'], []).append(e)
    found, stack = [], [(node, [])]
    while stack and len(found) < MAX_PATHS:
        cur, trail = stack.pop()
        if (R.get(manager, 'StructNode', cur) or {}).get('kind') == 'root':
            found.append(list(reversed(trail)))
            continue
        for e in into.get(cur, []):
            if e['from_node'] not in {x['from_node'] for x in trail} and e['from_node'] != node:
                stack.append((e['from_node'], trail + [e]))
    found.sort(key=lambda p: (len(p), ','.join(e['name'] for e in p)))
    R.drop(manager, 'StructNodePath', node=node)
    return [R.upsert(manager, 'StructNodePath', '%s#%d' % (node, i), node=node, edges=','.join(e['name'] for e in p), length=len(p), fastest=(i == 1))
            for i, p in enumerate(found, 1)]


def blocks(manager, node):
    words = []
    for q in R.rows(manager, 'StructNodeRequirement', node=node):
        if q['kind'] != 'exact':
            continue
        s = R.get(manager, 'StructFieldSamples', '%s:%s' % (q['object_map'], q['field']))
        if s is None or s['kind'] != 'samples':
            continue
        declared = [v.strip() for v in s['values'].split(',') if v.strip()]
        if not declared:
            words.append('%s has no declared samples: declare the values it is tested with' % q['field'])
        elif str(q['value']) not in declared:
            words.append('%s = %s is not a declared sample (declared: %s)' % (q['field'], q['value'], ', '.join(declared)))
    return words


def step_of(manager, node):
    best = None
    for x in R.rows(manager, 'StructNodeExecution', node=node):
        if not x['isotope']:
            continue
        r = S.rule_for(manager, x['isotope'])
        if r['step_s'] > 0 and (best is None or r['step_s'] < best[0]):
            best = (r['step_s'], '%s (%s: %s, %s)' % (x['isotope'], r['kind'], _s(r['step_s']), r['basis']))
    return {'step_s': best[0] if best else -1.0, 'step_set_by': best[1] if best else 'no execution with a known step rule'}


def _s(v):
    return '%.3g us' % (v * 1e6) if v < 1e-3 else '%.3g ms' % (v * 1e3)


def node_view(manager, node):
    n = R.get(manager, 'StructNode', node)
    if n is None:
        raise R.ConfigRefused('no node %r' % node, status=404)
    ps = sorted(R.rows(manager, 'StructNodePath', node=node), key=lambda p: p['name'])
    return dict(n, requirements=R.rows(manager, 'StructNodeRequirement', node=node), executions=sorted(R.rows(manager, 'StructNodeExecution', node=node), key=lambda x: x['order']),
                collateral_rows=R.rows(manager, 'StructNodeCollateral', node=node), paths=ps, fastest_path=next((p for p in ps if p['fastest']), None),
                blocked=blocks(manager, node), **step_of(manager, node))


def view(manager, bs):
    chain = root_chain(manager, bs)
    events = E.offered(manager, bs)
    nodes = [node_view(manager, n['name']) for n in sorted(R.rows(manager, 'StructNode', bench_solution=bs), key=lambda n: n['name'])]
    return {'ok': True, 'bench_solution': bs, 'root': chain['root'], 'nodes': nodes, 'edges': sorted(R.rows(manager, 'StructEdge', bench_solution=bs), key=lambda e: e['name']),
            'events': events}
