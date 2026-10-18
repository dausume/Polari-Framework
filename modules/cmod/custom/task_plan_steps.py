"""
@module cmod.custom.task_plan_steps

fgm-3: what a Task is MADE OF, read off the graph and the atoms - never typed. The graph's c-atom nodes of a Purpose become ordered steps; the interrupt that feeds a Task is the project ISR atom that
WRITES a global one of the Task's atoms touches (matched to the trigger kind); the shared data a Task touches comes from the atoms' own resource rows and the graph's field edges (an `isr_shared`
piece is one an interrupt step and a main-loop step both touch); the lane of every step is `cmod.custom.firmware.schedule_for` (the derived schedule - the AGREEMENT CHECK compares a Task's context with it).
"""
import json
import os
import re

from cmod.custom import code_interface as CI
from cmod.custom import firmware as FW
from cmod.custom.graph_seed import seed_graph

MODULES = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#: the interrupt vectors that can feed a Task of each trigger kind
ISR_FOR = {'edge': r'^(INT\d+|PCINT\d+)_vect$', 'command': r'^USART\d*_RX_vect$', 'period': r'^TIMER\d+_(COMPA|COMPB|OVF)_vect$'}
_CACHE = {}


def graph_names():
    d = os.path.join(MODULES, 'cmod', 'custom', 'graphs')
    return sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))


def graph_info(graph):
    """{nodes {instance: node}, edges, slots {task: slot}, project, atom_lane {atom ref: lane}} of one seeded graph (cached: seeds and committed manifests cannot change in a process)."""
    if graph not in _CACHE:
        g = seed_graph(graph) or {'nodes': [], 'edges': []}
        nodes = {n['instance']: n for n in g['nodes']}
        project = next((n['atom'].partition(':')[0] for n in g['nodes'] if n.get('atom')), 'uno')
        slots = {s['task']: s for s in FW.schedule_for(graph)}
        lane = {}
        for inst, n in nodes.items():
            if n.get('atom') and inst in slots:
                lane[n['atom']] = slots[inst]['lane']
        for s in slots.values():
            if s['lane'] == 'isr':
                lane['%s:%s' % (project, s['task'])] = 'isr'
        _CACHE[graph] = {'nodes': nodes, 'edges': g['edges'], 'slots': slots, 'project': project, 'atom_lane': lane}
    return _CACHE[graph]


def lane_of_atom(atom, graph):
    """(lane, graph it was read from) - the Mission's own graph first, then any other seeded graph that holds the atom; ('', '') when no graph schedules it."""
    order = [graph] + [g for g in graph_names() if g != graph]
    for g in order:
        lane = graph_info(g)['atom_lane'].get(atom)
        if lane:
            return lane, g
    return '', ''


def _resources(atom_ref):
    try:
        return CI.find_atom(atom_ref)[2].get('resources') or []
    except Exception:  # noqa: BLE001 - an atom with no manifest has no resources to read
        return []


def _called_by(info):
    out = {}
    for e in info['edges']:
        if e['kind'] == 'calls':
            out.setdefault(e['to_node'], []).append(e['from_node'])
    return out


def graph_steps(graph, instances, trigger_kind, boot):
    """[step dict] in graph order for the c-atom nodes named by a Task's Purposes (+ the feeding interrupt first). A boot Task keeps init-stage atoms; every other Task drops them (they belong to init)."""
    info = graph_info(graph)
    called = _called_by(info)
    nodes = [info['nodes'][i] for i in dict.fromkeys(instances) if i in info['nodes'] and info['nodes'][i].get('kind') == 'c-atom']
    nodes = [n for n in nodes if (n.get("stage") == "init") == boot]
    nodes.sort(key=lambda n: n.get('order', 0))
    steps = []
    for n in nodes:
        slot = info['slots'].get(n['instance'], {})
        lane = slot.get('lane') or n.get('stage') or 'loop'
        role = ('called by %s' % ', '.join(called.get(n['instance'], []))) if lane == 'called' and called.get(n['instance']) else {
            'init': 'runs once at boot', 'loop': 'runs every pass of the main loop'}.get(lane, lane)
        steps.append({'instance': n['instance'], 'atom': n['atom'], 'lane': lane, 'role': role})
    isr = feeding_isr(graph, steps, trigger_kind)
    if isr:
        steps.insert(0, isr)
    for i, s in enumerate(steps, 1):
        s['n'] = i
    return steps


def feeding_isr(graph, steps, trigger_kind):
    """The project ISR atom that feeds a Task of this trigger kind: its vector matches the kind and it WRITES a global one of the Task's own atoms touches. None when there is none."""
    rx = ISR_FOR.get(trigger_kind)
    if not rx or not steps:
        return None
    info = graph_info(graph)
    mine = {r['name'] for s in steps for r in _resources(s['atom']) if r['kind'] == 'global'}
    for task, slot in sorted(info['slots'].items(), key=lambda kv: kv[1]['order']):
        if slot['lane'] != 'isr' or not re.match(rx, slot.get('isr_vector') or ''):
            continue
        ref = '%s:%s' % (info['project'], task)
        if any(r['kind'] == 'global' and r['name'] in mine and r['access'] in ('w', 'rw') for r in _resources(ref)):
            return {'instance': slot['isr_vector'], 'atom': ref, 'lane': 'isr', 'role': 'the interrupt that feeds this task'}
    return None


def lane_context(steps):
    """The context the steps' own lanes derive: init | loop | isr | None (nothing scheduled to read). Called atoms follow whoever calls them; an interrupt that only FEEDS a loop task does not make it an ISR task."""
    lanes = [s['lane'] for s in steps if s.get('lane')]
    sched = [l for l in lanes if l not in ('called', 'isr')]
    if sched and all(l == 'init' for l in sched):
        return 'init'
    if any(l in ('loop', 'tick') for l in sched):
        return 'loop'
    if 'isr' in lanes and not sched:
        return 'isr'
    return None


def agreement(context, steps, route_note='', trigger=''):
    """-> (verdict, why): the Task's context against the lane its atoms derive. agrees | disagrees | unchecked - never a silent re-label."""
    want = lane_context(steps)
    ctx = 'loop' if context == 'task' else context
    if trigger == 'boot' and context != 'init':
        return 'disagrees', 'a boot task runs once, before the interrupts are enabled, but it is marked %s' % context
    if trigger and trigger != 'boot' and context == 'init':
        return 'disagrees', 'a %s task is started again and again, but it is marked init (runs once at boot)' % trigger
    lanes = ', '.join('%s (%s)' % (s['instance'], s['lane']) for s in steps if s.get('lane')) or 'none'
    if want is None:
        return 'unchecked', 'no step of this task is scheduled in any graph yet, so there is no lane to compare%s' % ((': ' + route_note) if route_note else '')
    if ctx == want:
        return 'agrees', 'marked %s; its atoms\' derived lanes say %s: %s' % (context, want, lanes)
    return 'disagrees', 'marked %s but its atoms\' derived lanes say %s: %s' % (context, want, lanes)


def struct_bindings(graph, task_name, steps):
    """[TaskStructBinding dict] - every global the steps touch (isr_shared when an interrupt step and another step touch the same one) + the graph's field edges into a class instance."""
    info = graph_info(graph)
    seen = {}
    for s in steps:
        for r in _resources(s['atom']):
            if r['kind'] != 'global':
                continue
            d = seen.setdefault(r['name'], {'steps': [], 'isr': set(), 'acc': set(), 'detail': r.get('detail', ''), 'atomic': []})
            d['steps'].append(s['instance'])
            d['acc'].add(r['access'])
            if s['lane'] == 'isr':
                d['isr'].add(s['instance'])
            if 'ATOMIC_BLOCK' in (r.get('detail') or ''):
                d['atomic'].append(s['instance'])
    out = []
    for name, d in sorted(seen.items()):
        others = [x for x in d['steps'] if x not in d['isr']]
        shared = bool(d['isr']) and bool(others)
        acc = 'rw' if len(d['acc'] - {''}) > 1 or 'rw' in d['acc'] else (next(iter(d['acc'] - {''}), ''))
        is_struct = bool(re.match(r'[A-Z]\w*_t,', d['detail']))
        out.append({'target': name + (' (%s, whole struct)' % d['detail'].split(',')[0] if is_struct else ''), 'kind': 'struct' if is_struct else 'global', 'access': acc, 'steps': d['steps'],
                    'isr_shared': shared, 'isr_vectors': ', '.join(sorted(d['isr'])),
                    'atomic_today': ('yes: inside ATOMIC_BLOCK in %s' % ', '.join(d['atomic'])) if d['atomic'] else ('no ATOMIC_BLOCK today' if shared else 'not applicable'),
                    'basis': 'the atoms\' resource rows (%s): %s' % (', '.join(d['steps']), d['detail'] or 'global')})
    instances = {s['instance'] for s in steps}
    for e in info['edges']:
        if e['kind'] == 'field' and e['from_node'] in instances:
            cls = re.search(r'class=(\w+)', (info['nodes'].get(e['to_node']) or {}).get('params', '') or '')
            out.append({'target': '%s.%s' % (cls.group(1) if cls else e['to_node'], e['to_port']), 'kind': 'struct-field', 'access': 'w', 'steps': [e['from_node']], 'isr_shared': False,
                        'isr_vectors': '', 'atomic_today': 'not applicable (no interrupt step touches it)',
                        'basis': 'the graph\'s field edge %s: %s.%s -> %s.%s' % (e['name'], e['from_node'], e['from_port'] or 'return', e['to_node'], e['to_port'])})
    for b in out:
        b['name'] = '%s:%s' % (task_name, b['target'])
    return out
