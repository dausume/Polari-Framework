"""
@module hwnocode.custom.placement

THE PLACEMENT RULE (HARDWARE_NOCODE_PLAN.md §2b — RULE 2 as code). Where a node runs is DERIVED, never typed in:

  1. c-atom / the glue kinds (class parser frame tick rule) / a HardwareSubgraph → `board`, and `twin` while no BoardInstance is
     attached (the simavr twin runs the SAME .hex a board is flashed with)
  2. engine state classes → `backend` (the Python engine); displays → `browser`
  3. EVERY edge that crosses board ⇄ backend passes through ONE hw-interface node (`bridge`: the generated Java bridge on the host
     carries the binding's frames up and the Commands down). Any other crossing is refused, naming the edge.
  4. a Python node on the device side is REFUSED with the reason (RULE 2: C, Verilog or SystemVerilog only on a device), naming
     the node, with the alternative: move it across the hw-interface to the backend.
  5. a Linux SoC (`linux-device`) may run Python (D-hn-6 ruled) — not an hn-0 target; refused here as unsupported, never guessed.

"Device side" = the nodes joined to a device node by connectors WITHOUT passing a hw-interface (the region the split cuts off).
Inside the referenced CGraph, a node of a kind cmod's glue does not own (an engine/Python kind) is refused the same way.
"""
import json

from hwnocode.custom.runtimes import runtime_for_kind

#: node kinds that ARE the device (rule 1)
DEVICE_KINDS = {'HardwareSubgraph': 'hardware-subgraph', 'CAtom': 'c-atom'}
#: the split point (rule 3)
SPLIT_KINDS = {'HardwareInterface': 'hw-interface'}
#: client-side state classes (TS engine / displays)
BROWSER_KINDS = {'EmitFrontendEvent', 'FormSubscription', 'ReactiveTransform'}
#: the kinds cmod's glue owns — C on the device (cmod.custom.graph.NODE_KINDS)
CMOD_KINDS = ('c-atom', 'class', 'parser', 'frame', 'tick', 'rule')
PLACEMENTS = ('board', 'twin', 'bridge', 'backend', 'browser', 'host-engine', 'linux-device')

GLUE_WHY = {
    'class': 'the class instance the frames carry — a static struct in polari_graph.c',
    'parser': 'the generated header\'s receiver (polari_rx_t + polari_rx_feed) — C',
    'frame': '<Class>_encode + _frame + the sequence counter into static buffers — C',
    'tick': 'an `if` on the uint32_t ms clock inside main() — C',
    'rule': 'a status rule evaluated in its tick — C',
}


class PlacementRefused(ValueError):
    pass


def state_class(s):
    return s.get('stateClass') or s.get('boundObjectClass') or ''


def edges_of(definition):
    """[(from_state, to_state)] from the output slots' connectors (the canvas's own wiring)."""
    out = []
    for s in definition.get('stateInstances') or []:
        for slot in s.get('slots') or []:
            if slot.get('isInput'):
                continue
            for c in slot.get('connectors') or []:
                t = c.get('targetStateName')
                if t:
                    out.append((s.get('stateName'), t))
    return out


def device_target(board_instance, manager=None):
    """('board' | 'twin', why). A twin:… instance, an empty one, or a BoardInstance row not present on this host → twin."""
    bi = str(board_instance or '')
    if not bi or bi.startswith('twin:'):
        return 'twin', ('the simavr twin — no BoardInstance attached (%s); the same .hex a board is flashed with'
                        % (bi or 'none named'))
    rows = ((getattr(manager, 'objectTables', None) or {}).get('BoardInstance') or {}).values() if manager is not None else []
    hit = next((r for r in rows if getattr(r, 'name', '') == bi), None)
    if hit is not None and str(getattr(hit, 'state', '')).startswith('board present'):
        return 'board', 'BoardInstance %s (%s)' % (bi, getattr(hit, 'state', ''))
    return 'twin', 'BoardInstance %s is not attached here — the simavr twin stands in (same .hex)' % bi


def _node(layer, node, kind, placement, language, why, refused=False, purpose=''):
    return {'layer': layer, 'node': node, 'kind': kind, 'placement': placement, 'language': language, 'why': why,
            'refused': bool(refused), 'runtime': runtime_for_kind(kind, placement, refused), 'purpose': purpose}


def place(definition, cgraph_rows=None, board_instance='', displays=(), manager=None, trigger=''):
    """→ {'nodes': [placement dicts, canvas order then the subgraph then the displays], 'refusals': [plain sentences],
    'edges': [...], 'counts': {placement: n}}. Never raises: `check()` turns refusals into PlacementRefused."""
    states = list(definition.get('stateInstances') or [])
    by = {s.get('stateName'): s for s in states}
    edges = [(a, b) for a, b in edges_of(definition) if a in by and b in by]
    where, where_why = device_target(board_instance, manager)
    adj = {n: set() for n in by}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    # the device side: flood from every device node, never through a split node
    device = set()
    origin = {}
    for s in states:
        name = s.get('stateName')
        if state_class(s) in DEVICE_KINDS and name not in device:
            stack = [name]
            device.add(name)
            origin[name] = name
            while stack:
                u = stack.pop()
                for v in adj[u]:
                    if v in device or state_class(by[v]) in SPLIT_KINDS:
                        continue
                    device.add(v)
                    origin[v] = origin[u]
                    stack.append(v)
    refusals, nodes = [], []
    for s in states:
        name, cls = s.get('stateName'), state_class(s)
        fv = s.get('boundObjectFieldValues') or {}
        if cls in DEVICE_KINDS:
            if cls == 'HardwareSubgraph':
                n_sub = len((cgraph_rows or {}).get('nodes') or [])
                why = ('references CGraph %s (D-hn-1: the hardware SUBGRAPH stays cmod\'s rows); expands into its %d nodes below; '
                       'rendered by cmod-glue — artifacts only, never run in the engine; on %s' % (fv.get('cgraph', '?'), n_sub, where_why))
            else:
                why = ('c-atom %s — C on the device (%s); in hn-0 a c-atom renders only inside a HardwareSubgraph\'s CGraph rows'
                       % (fv.get('atom', '?'), where_why))
            nodes.append(_node('solution', name, DEVICE_KINDS[cls], where, 'C', why, purpose=fv.get('purpose', '')))
        elif cls in SPLIT_KINDS:
            near = sorted(adj[name])
            dev_n = [x for x in near if x in device]
            back_n = [x for x in near if x not in device and state_class(by[x]) not in SPLIT_KINDS]
            why = ('THE SPLIT POINT: binding %s ties %s/%s to %s at %s on bridge %s; the generated Java bridge decodes frames UP and '
                   'routes Commands DOWN (device side: %s · backend side: %s)%s'
                   % (fv.get('binding', '?'), fv.get('object_class', '?'), fv.get('object_name', '?'), fv.get('board_instance', '?'),
                      fv.get('port', '?'), fv.get('bridge_name', '?'), ', '.join(dev_n) or 'none', ', '.join(back_n) or 'none',
                      (' — ' + fv['route_report']) if fv.get('route_report') else ''))
            nodes.append(_node('solution', name, 'hw-interface', 'bridge', 'Java (generated bridge)', why, purpose=fv.get('purpose', '')))
        elif name in device:
            dev = origin.get(name, '?')
            via = next(('%s → %s' % (a, b) for a, b in edges if {a, b} & {name} and (a in device and b in device)), '')
            msg = ('%s \'%s\' is on the DEVICE side (joined to %s by %s without crossing a hw-interface): Python never runs on a '
                   'microcontroller (RULE 2: C, Verilog or SystemVerilog only on a device) — move it across the hw-interface to the '
                   'backend, or write it in C as an atom (a person\'s job)' % (cls or '?', name, dev, via or 'an edge'))
            refusals.append(msg)
            nodes.append(_node('solution', name, cls, 'refused', 'Python', msg, refused=True, purpose=fv.get('purpose', '')))
        elif cls in BROWSER_KINDS:
            nodes.append(_node('solution', name, cls, 'browser', 'TypeScript (TS engine)', 'client-side state class → the browser\'s TS engine', purpose=fv.get('purpose', '')))
        else:
            why = 'engine state class %s → the Python engine on the backend' % (cls or '?')
            if trigger:
                why += ', fired by EventTrigger %s on each update of the bound row' % trigger
            nodes.append(_node('solution', name, cls, 'backend', 'Python (engine)', why, purpose=fv.get('purpose', '')))
    # rule 3, stated per edge: a device node wired straight to a backend node
    for a, b in edges:
        ka, kb = state_class(by[a]), state_class(by[b])
        if (ka in DEVICE_KINDS) != (kb in DEVICE_KINDS) and ka not in SPLIT_KINDS and kb not in SPLIT_KINDS:
            refusals.append('edge %s → %s crosses board ⇄ backend without a hw-interface (rule 3: the bridge is the only split '
                            'point — put a HardwareInterface node on this edge)' % (a, b))
    # inside the referenced CGraph: every node is C on the device, or refused
    g = (cgraph_rows or {}).get('graph') or {}
    for cn in sorted((cgraph_rows or {}).get('nodes') or [], key=lambda r: (int(r.get('order') or 0), r.get('instance', ''))):
        inst, kind = cn.get('instance', ''), cn.get('kind', '')
        if kind not in CMOD_KINDS:
            msg = ('CGraph %s node \'%s\' (kind %s) is a Python/engine node on the BOARD: RULE 2 — only C runs there (cmod-glue owns %s); '
                   'move it to the backend across the hw-interface' % (g.get('name', '?'), inst, kind or '?', ', '.join(CMOD_KINDS)))
            refusals.append(msg)
            nodes.append(_node('subgraph', inst, kind, 'refused', 'Python', msg, refused=True))
            continue
        if kind == 'c-atom':
            fn = str(cn.get('atom', '')).split('.')[-1]
            why = 'c-atom %s (%s, stage %s) — cmod-glue %s it in polari_graph.c; C on the ATmega328P (%s)' % (
                fn, cn.get('atom', ''), cn.get('stage', ''), 'copies (verbatim) + calls' if 'apps/' in str(cn.get('atom', '')) else 'calls',
                where_why)
        else:
            why = '%s — %s (%s)' % (kind, GLUE_WHY[kind], where_why)
        nodes.append(_node('subgraph', inst, kind, where, 'C', why))
    for d in displays or ():
        nodes.append(_node('display', d, 'display', 'browser', 'TypeScript (Angular)',
                           'DisplayDefinition %s: configured tables + a GraphDefinition chart → the dashboard renderer (no new component)' % d))
    counts = {}
    for n in nodes:
        counts[n['placement']] = counts.get(n['placement'], 0) + 1
    return {'nodes': nodes, 'refusals': refusals, 'edges': edges, 'counts': counts, 'device_side': sorted(device), 'target': where}


def check(report):
    if report['refusals']:
        raise PlacementRefused('; '.join(report['refusals']))
    return report


def summary(report):
    order = [p for p in PLACEMENTS + ('refused',) if p in report['counts']]
    return ', '.join('%s %d' % (p, report['counts'][p]) for p in order)


def backend_partition(definition, report, name):
    """The backend half as its own definition: the states placed `backend`, connectors to anything else dropped (the
    engine starts at its BackendStateChange entry either way; the partition makes the boundary explicit)."""
    keep = {n['node'] for n in report['nodes'] if n['layer'] == 'solution' and n['placement'] == 'backend'}
    states = []
    for s in definition.get('stateInstances') or []:
        if s.get('stateName') not in keep:
            continue
        c = json.loads(json.dumps(s))
        for slot in c.get('slots') or []:
            slot['connectors'] = [x for x in slot.get('connectors') or [] if x.get('targetStateName') in keep]
        states.append(c)
    return {'solutionName': name, 'stateInstances': [dict(s, index=i) for i, s in enumerate(states)]}
