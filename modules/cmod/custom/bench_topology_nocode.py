"""
@module cmod.custom.bench_topology_nocode

bss-5 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b): A BENCH SOLUTION'S TOPOLOGY DRAWN ON THE ONE NO-CODE CANVAS, category `bench-topology`
(it mirrors cmod.custom.purpose_nocode): every `StructNode` is a `struct-node` box, every `StructEdge` a `hardware-event` box BETWEEN its two nodes
(node -> event -> node), columns by depth from the root (the fastest path's length), rows by order. DECLARATIVE: nothing here is executed; the category
validator refuses every compute and runtime kind. The rows are the single source of truth: `render` draws them (and keeps the SolutionDefinition row up
to date so the drawing page lists it); `write_back` turns a canvas edit into row fields - ONLY a node's title and a Hardware Event's title - and refuses
anything else by name (requirements, executions and edges change through the doors).

    solution_name(bs)                         'bench-topology-<bs>'
    render_definition(bs, manager)            the graph_builder definition
    render(bs, manager)                       the SolutionDefinition row dict (upserted into the manager's table when there is one)
    validate(definition)                      (ok, why) through hwnocode.custom.cross_domain
    write_back(definition, bs, manager)       (ok, why, changes)
    drawing_route(bs)                         '/display/hardware-solutions?solution=bench-topology-<bs>'
"""
import json

from polariNoCode import graph_builder as GB
from cmod.custom import bench_topology as T
from cmod.custom import config_rows as R
from cmod.custom import topology_palette as P

CATEGORY = 'bench-topology'
SOLUTION_PREFIX = 'bench-topology-'
BENCH_ROUTE = '/display/bench-solutions'
_COL_W, _ROW_H, _W, _H, _EW = 230, 120, 200, 96, 160


def solution_name(bs):
    return SOLUTION_PREFIX + bs


def drawing_route(bs):
    return '/display/hardware-solutions?solution=%s' % solution_name(bs)


def _confirmation(manager, node):
    from cmod.custom import confirmations as C
    confs = C.of(manager, node['name'])
    live = [c for c in confs if c['state'] == 'confirmed']
    if node['kind'] == 'root':
        return 'root', 'the hardware as delivered, plugged in'
    if node.get('basis') == 'proposed':
        return 'proposed', 'proposed from a run that diverged; accept, loosen and name it'
    if live:
        by = 'hardware' if any(c['by'] == 'hardware' for c in live) else 'twin' if any(c['by'] == 'twin' for c in live) else 'person'
        return 'confirmed-%s' % by, 'confirmed by %s (%d confirmation%s, %d voided)' % (by, len(live), '' if len(live) == 1 else 's', len(confs) - len(live))
    runs = sorted(R.rows(manager, 'StructNodeRun', node=node['name']), key=lambda r: r['name'])
    if runs:
        return runs[-1]['outcome'], 'last run %s: %s' % (runs[-1]['name'].split('#')[-1], runs[-1]['outcome']) + (' (older confirmations voided)' if confs else '')
    return 'never-tested', 'never tested' + (' (older confirmations voided)' if confs else '')


def _node_fields(manager, node):
    reqs = R.rows(manager, 'StructNodeRequirement', node=node['name'])
    words = '; '.join('%s %s %s' % (q['field'], {'exact': '=', 'range': 'in', 'set': 'in', 'written': 'written'}[q['kind']], q['value']) if q['kind'] != 'written' else '%s written' % q['field']
                      for q in reqs) or (node.get('notes') or '')
    state, cwords = _confirmation(manager, node)
    st = T.step_of(manager, node['name'])
    runs = R.rows(manager, 'StructNodeRun', node=node['name'])
    latest = sorted(runs, key=lambda r: r['name'])[-1]['name'] if runs else ''
    return state, {'title': node.get('title') or '', 'requirements': words, 'confirmation': cwords,
                   'step': ('%s by %s' % (T._s(st['step_s']), st['step_set_by'].split(' (')[0]) if st['step_s'] > 0 else st['step_set_by']),
                   'kind': node['kind'], 'basis': node.get('basis', 'person'), 'runs': str(len(runs)),
                   'bench_here': '%s?bench_solution=%s&node=%s%s' % (BENCH_ROUTE, node['bench_solution'], node['name'], ('&run=%s' % latest) if latest else '')}


def _depth(manager, bs):
    """node -> columns from the root (the fastest path's length; root 0; an unreachable node after the deepest)."""
    out = {}
    for n in R.rows(manager, 'StructNode', bench_solution=bs):
        if n['kind'] == 'root':
            out[n['name']] = 0
            continue
        p = next((x for x in R.rows(manager, 'StructNodePath', node=n['name']) if x['fastest']), None)
        out[n['name']] = p['length'] if p else -1
    deepest = max(out.values()) if out else 0
    return {k: (v if v >= 0 else deepest + 1) for k, v in out.items()}


def render_definition(bs, manager):
    T.root_chain(manager, bs)
    nodes = sorted(R.rows(manager, 'StructNode', bench_solution=bs), key=lambda n: n['name'])
    edges = sorted(R.rows(manager, 'StructEdge', bench_solution=bs), key=lambda e: e['name'])
    depth = _depth(manager, bs)
    outs = {n['name']: [e['name'] for e in edges if e['from_node'] == n['name']] for n in nodes}
    rows_in_col = {}
    states = []
    for n in nodes:
        state, fields = _node_fields(manager, n)
        col = 2 * depth[n['name']]
        k = rows_in_col[col] = rows_in_col.get(col, -1) + 1
        st = GB.node(n['name'], 'StructNodeState', fields, outs=[outs[n['name']]])
        st['stateLocationX'], st['stateLocationY'] = 40 + _COL_W * col, 60 + _ROW_H * k
        st['shapeType'] = st['stateSvgName'] = 'rectangle'
        st['layerName'] = 'rectangle-layer'
        st['backgroundColor'] = P.STATE_COLORS.get(state, P.AUTHORED_COLOR)
        st['slotRadius'] = 5
        st['stateSvgWidth'], st['stateSvgHeight'], st['cornerRadius'] = _W, _H, 8
        st['stateSvgRadius'] = None
        st['stateSvgSizeX'] = st['stateSvgSizeY'] = None
        st['runtime'] = ''
        st['confirmationState'] = state
        states.append(st)
    for e in edges:
        ev = R.get(manager, 'HardwareEvent', e['event']) if e['event'] else None
        fields = {'title': e.get('title') or (ev or {}).get('title') or e['kind'], 'kind': e['kind'], 'source': (ev or {}).get('source', ''), 'what': (ev or {}).get('what', ''),
                  'event': e['event']}
        col = 2 * depth.get(e['from_node'], 0) + 1
        k = rows_in_col[col] = rows_in_col.get(col, -1) + 1
        st = GB.node(e['name'], 'HardwareEventState', fields, outs=[[e['to_node']]])
        st['stateLocationX'], st['stateLocationY'] = 40 + _COL_W * col, 60 + _ROW_H * k
        st['shapeType'] = st['stateSvgName'] = 'rectangle'
        st['layerName'] = 'rectangle-layer'
        st['backgroundColor'] = P.EVENT_COLOR
        st['slotRadius'] = 5
        st['stateSvgWidth'], st['stateSvgHeight'], st['cornerRadius'] = _EW, 72, 8
        st['stateSvgRadius'] = None
        st['stateSvgSizeX'] = st['stateSvgSizeY'] = None
        st['runtime'] = ''
        states.append(st)
    d = GB.solution(solution_name(bs), *states)
    d['edgeKind'] = 'then'
    try:
        from hwnocode.custom import solutions as S
        S._wire_connectors(d)
    except Exception:  # noqa: BLE001 - the canvas wiring ids are cosmetic; the drawing is still valid
        pass
    return d


def contract():
    return {'description': 'A Bench Solution\'s Hardware Event topology: struct nodes (what the struct fields must be) and the hardware events between '
                           'them, from the moment the USB is plugged in. Declarative: nothing here is executed; a node is tested through its run door.',
            'inputs': [], 'returns': [], 'executionRights': 'definer'}


def render(bs, manager):
    name = solution_name(bs)
    row = {'name': name, 'function_name': name.replace('-', '_'), 'target_runtime': 'python_backend', 'definition': json.dumps(render_definition(bs, manager)),
           'contract_json': json.dumps(contract()), 'category': CATEGORY}
    if getattr(manager, 'objectTables', None) is not None:
        try:
            R.upsert(manager, 'SolutionDefinition', name, **{k: v for k, v in row.items() if k != 'name'})
        except R.ConfigRefused:
            pass
    return row


def validate(definition):
    from hwnocode.custom import cross_domain as CD
    return CD.validate(definition, CATEGORY)


def write_back(definition, bs, manager):
    """(ok, why, changes): ONLY titles come back from the drawing - a struct node's `title` -> StructNode.title, a trigger box's `title` -> its
    HardwareEvent.title. Any other changed field is refused by name: requirements, executions, collaterals and edges change through the doors."""
    ok, why = validate(definition)
    if not ok:
        return False, why, {}
    changes = {}
    for s in (definition or {}).get('stateInstances') or []:
        f = dict(s.get('boundObjectFieldValues') or {})
        if s.get('stateClass') == 'StructNodeState':
            node = R.get(manager, 'StructNode', s.get('stateName', ''))
            if node is None:
                return False, 'refused: state %r is not a node of %s (nodes are added through POST .../nodes)' % (s.get('stateName'), bs), {}
            _st, mine = _node_fields(manager, node)
            for k, v in f.items():
                if k == 'title':
                    if str(v) != node.get('title', ''):
                        R.upsert(manager, 'StructNode', node['name'], title=str(v))
                        changes[node['name']] = {'title': str(v)}
                elif k in mine and str(v) != str(mine[k]):
                    return False, ('refused: state %r - %s is derived from the rows (%r), it changes through the doors, not the drawing'
                                   % (s.get('stateName'), k, mine[k])), changes
        elif s.get('stateClass') == 'HardwareEventState':
            edge = R.get(manager, 'StructEdge', s.get('stateName', ''))
            if edge is None:
                return False, 'refused: state %r is not an edge of %s (edges are added through POST .../edges)' % (s.get('stateName'), bs), changes
            ev = R.get(manager, 'HardwareEvent', edge['event']) if edge['event'] else None
            if 'title' in f and ev is not None and str(f['title']) not in (ev.get('title', ''), edge.get('title', '')):
                R.upsert(manager, 'HardwareEvent', ev['name'], title=str(f['title']))
                R.upsert(manager, 'StructEdge', edge['name'], title=str(f['title']))
                changes[edge['name']] = {'title': str(f['title'])}
            for k in ('kind', 'source', 'what', 'event'):
                if k in f and str(f[k]) != str((ev or {}).get(k, edge.get(k, '')) if k != 'kind' else edge['kind']):
                    return False, 'refused: state %r - %s is the edge\'s own (%r); edges change through the doors' % (s.get('stateName'), k, edge.get(k, (ev or {}).get(k))), changes
    render(bs, manager)
    return True, 'ok: %d title%s written back' % (len(changes), '' if len(changes) == 1 else 's'), changes
