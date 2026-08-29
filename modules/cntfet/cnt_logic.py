"""
@module cntfet.cnt_logic

fp-5 (FET_CELL_POWER_SILICON_PLAN §1): the cell library's LOGIC
face — boolean AST from the Liberty function, gate-level DAG,
truth table, transistor-level schematic graph with placement
hints, a SWITCH-LEVEL PROOF (the transistor netlist evaluated per
input vector against the boolean function — every combinational
cell proven or a NAMED counter-example), the step-through state
space, and the cdff state-transition graph derived from the
subckt description (no ngspice here — pure graph reasoning).

Reused (imported, not re-described): CELL_LIBRARY / COMBINATIONAL
/ fet_count from cnt_cell_library (the ONE source of truth for
devices and composition), and the cdff subckt text from
cnt_cells._SUBCKTS (parsed for its instance list).

Switch-level semantics (documented for the proof):
  - a device conducts iff (n and gate==1) or (p and gate==0);
    a device whose gate is unresolved (Z/X) does not conduct and
    is flagged;
  - nets joined by conducting devices form components (union-
    find); a component's DRIVERS are vdd (1), gnd (0) and any
    INPUT net carrying a value — so a transmission gate passes its
    source net's value (MUX2 is driven from A/B, not a rail);
  - driver value set {1} -> 1, {0} -> 0, both -> 'X' (contention),
    none -> 'Z' (floating);
  - internal nets that gate other devices (cmux2's `sb`) are
    resolved by fixed-point iteration: resolve, re-derive
    conduction, repeat until nothing changes;
  - composed cells are evaluated STAGE BY STAGE in compose order
    (each sub-cell's output net feeds the next), values reported
    per stage.

cells-2 (2026-08-27) — payload version 2 (additive, see
payload_contract):
  - MULTI-OUTPUT cells (cha, cfa): every evaluation carries
    `outputValues: {pin: value}` next to `output` (= the FIRST
    output, kept for v1 readers); the proof checks EVERY output
    against its own Liberty function; the gate DAG has one output
    node per output; truth-table rows carry `outputs`.
  - TRI-STATE (ctbuf): a cell's `three_state` expression is part
    of the boolean semantics — the EXPECTED output is 'Z' when it
    evaluates true (expected_output), so the floating vectors of a
    tri-state cell are proof PASSES, not failures.
  - STORAGE (clatch): switch_level_eval accepts `initial` net
    values. A component with NO driver (rails/inputs) takes the
    value STORED on its member nets ({1}->1, {0}->0, both->'X',
    none->'Z') — charge retention — and the fixed-point iteration
    re-derives conduction from there, so a closed inverter loop
    re-drives its own state from the rails. The latch proof is
    exhaustive over (G, D, Q_prev) with the storage nodes seeded
    from Q_prev (the cell's `state.nodes` map).

@consumers
  - cntfet.cnt_api ({action: cell-logic}) — wired by the integrator
  - cntfet.selftest_logic, cntfet.selftest_cells2
"""

import itertools
import json
import re

from cntfet.cnt_cell_library import (
    CELL_LIBRARY, COMBINATIONAL, MULTI_OUTPUT, SEQUENTIAL_CELLS,
    TRISTATE, fet_count as _fet_count,
)
from cntfet.cnt_cells import _SUBCKTS

LOGIC_PAYLOAD_VERSION = 2

VDD_NET = 'vddn'
GND_NET = '0'
#: the hand-subckt sequential cell (cnt_cells) — NOT in CELL_LIBRARY
SEQUENTIAL = ['cdff']


# ---------------------------------------------------------------
# 1. boolean AST
# ---------------------------------------------------------------

_TOKEN = re.compile(r'\s*(?:([A-Za-z_][A-Za-z0-9_]*)|([!*+^()]))')


def _tokenize(text):
    pos, out = 0, []
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(
                f'bad Liberty function near {text[pos:pos + 8]!r}')
        out.append(m.group(1) or m.group(2))
        pos = m.end()
    return out


class _Parser:
    """Liberty precedence: ! (unary)  >  *  (also juxtaposition)
    >  ^  >  +."""

    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def parse(self):
        node = self.p_or()
        if self.peek() is not None:
            raise ValueError(f'trailing token {self.peek()!r}')
        return node

    def p_or(self):
        args = [self.p_xor()]
        while self.peek() == '+':
            self.take()
            args.append(self.p_xor())
        return args[0] if len(args) == 1 \
            else {'op': 'or', 'args': args}

    def p_xor(self):
        args = [self.p_and()]
        while self.peek() == '^':
            self.take()
            args.append(self.p_and())
        return args[0] if len(args) == 1 \
            else {'op': 'xor', 'args': args}

    def p_and(self):
        args = [self.p_not()]
        while True:
            nxt = self.peek()
            if nxt == '*':
                self.take()
                args.append(self.p_not())
            elif nxt is not None and (nxt == '(' or nxt == '!'
                                      or nxt[0].isalpha()
                                      or nxt[0] == '_'):
                args.append(self.p_not())  # juxtaposition = AND
            else:
                break
        return args[0] if len(args) == 1 \
            else {'op': 'and', 'args': args}

    def p_not(self):
        if self.peek() == '!':
            self.take()
            return {'op': 'not', 'args': [self.p_not()]}
        return self.p_atom()

    def p_atom(self):
        tok = self.take()
        if tok == '(':
            node = self.p_or()
            if self.take() != ')':
                raise ValueError('unbalanced parentheses')
            return node
        if tok is None or not (tok[0].isalpha() or tok[0] == '_'):
            raise ValueError(f'unexpected token {tok!r}')
        return {'op': 'var', 'name': tok}


def boolean_ast(liberty_function):
    """Liberty function text -> AST dicts
    {op: 'and'|'or'|'xor'|'not', args: [...]} | {op: 'var', name}."""
    return _Parser(_tokenize(liberty_function)).parse()


def evaluate(ast, assignment):
    op = ast['op']
    if op == 'var':
        return int(bool(assignment[ast['name']]))
    vals = [evaluate(a, assignment) for a in ast['args']]
    if op == 'not':
        return 1 - vals[0]
    if op == 'and':
        return int(all(vals))
    if op == 'or':
        return int(any(vals))
    if op == 'xor':
        return sum(vals) % 2
    raise ValueError(f'unknown op {op}')


def expected_output(cell, output, vector):
    """cells-2: the boolean EXPECTATION for one output pin of one
    vector — 'Z' when the cell's three_state expression is true
    (tri-state semantics), else the pin's Liberty function."""
    ts = cell.get('three_state')
    if ts and evaluate(boolean_ast(ts), vector):
        return 'Z'
    return evaluate(boolean_ast(cell['liberty_functions'][output]),
                    vector)


def ast_vars(ast, acc=None):
    acc = [] if acc is None else acc
    if ast['op'] == 'var':
        if ast['name'] not in acc:
            acc.append(ast['name'])
    else:
        for a in ast['args']:
            ast_vars(a, acc)
    return acc


def ast_text(ast):
    op = ast['op']
    if op == 'var':
        return ast['name']
    if op == 'not':
        return '!' + ast_text(ast['args'][0])
    sym = {'and': '*', 'or': '+', 'xor': '^'}[op]
    return '(' + sym.join(ast_text(a) for a in ast['args']) + ')'


_GATE_OF = {'and': 'AND', 'or': 'OR', 'xor': 'XOR', 'not': 'NOT'}
_FOLD = {'and': 'NAND', 'or': 'NOR'}


def gate_dag(ast, cell_key=None, output=None, _into=None):
    """Gate-level DAG. NOT over and/or folds into NAND/NOR; every
    other node is kept faithful to the AST (INV = NOT, BUF = a
    bare variable, AOI21 = NOR over (AND, C)). cells-2: `output`
    names the output node (default: the cell's first output);
    `_into` = (nodes, edges, counter) appends a second output's
    tree to an existing DAG (cell_gate_dag)."""
    cell = CELL_LIBRARY.get(cell_key) if cell_key else None
    inputs = list(cell['inputs']) if cell else ast_vars(ast)
    output = output or (cell['output'] if cell else 'Y')
    if _into:
        nodes, edges, counter = _into
    else:
        nodes, edges = [], []
        counter = itertools.count(1)
        for name in inputs:
            nodes.append({'id': name, 'kind': 'input', 'gate': None,
                          'label': name, 'inputs': [], 'level': 0})

    def build(node):
        """returns (node_id, level)"""
        if node['op'] == 'var':
            return node['name'], 0
        op, args = node['op'], node['args']
        gate = _GATE_OF[op]
        if op == 'not' and args[0]['op'] in _FOLD:
            gate = _FOLD[args[0]['op']]
            args = args[0]['args']
        feeds = [build(a) for a in args]
        level = max(lv for _i, lv in feeds) + 1
        gid = f'g{next(counter)}'
        nodes.append({'id': gid, 'kind': 'gate', 'gate': gate,
                      'label': f'{gate}{len(feeds) if gate not in ("NOT", "BUF") else ""}',
                      'inputs': [i for i, _lv in feeds],
                      'level': level})
        for i, _lv in feeds:
            edges.append({'from': i, 'to': gid})
        return gid, level

    top_id, top_level = build(ast)
    if ast['op'] == 'var':
        gid = f'g{next(counter)}'
        nodes.append({'id': gid, 'kind': 'gate', 'gate': 'BUF',
                      'label': 'BUF', 'inputs': [top_id],
                      'level': 1})
        edges.append({'from': top_id, 'to': gid})
        top_id, top_level = gid, 1
    nodes.append({'id': output, 'kind': 'output', 'gate': None,
                  'label': output, 'inputs': [top_id],
                  'level': top_level + 1})
    edges.append({'from': top_id, 'to': output})
    return {'nodes': nodes, 'edges': edges}


def cell_gate_dag(cell_key):
    """cells-2: the cell's DAG with ONE output node PER OUTPUT
    (inputs shared, gate ids numbered across outputs). Single-
    output cells = gate_dag of their function."""
    cell = _cell(cell_key)
    if not cell.get('liberty_function'):
        return None
    dag = None
    into = None
    for out in cell['outputs']:
        ast = boolean_ast(cell['liberty_functions'][out])
        dag = gate_dag(ast, cell_key, output=out, _into=into)
        into = (dag['nodes'], dag['edges'], into[2] if into
                else itertools.count(
                    1 + sum(1 for n in dag['nodes']
                            if n['kind'] == 'gate')))
    return dag


def dag_values(dag, assignment):
    """Per-node logic value for one assignment (drives the
    interactive diagram)."""
    vals = {}
    for n in dag['nodes']:
        if n['kind'] == 'input':
            vals[n['id']] = int(bool(assignment[n['id']]))
    for n in sorted((n for n in dag['nodes'] if n['kind'] != 'input'),
                    key=lambda n: n['level']):
        ins = [vals[i] for i in n['inputs']]
        g = n['gate']
        if n['kind'] == 'output' or g == 'BUF':
            vals[n['id']] = ins[0]
        elif g == 'NOT':
            vals[n['id']] = 1 - ins[0]
        elif g == 'AND':
            vals[n['id']] = int(all(ins))
        elif g == 'NAND':
            vals[n['id']] = 1 - int(all(ins))
        elif g == 'OR':
            vals[n['id']] = int(any(ins))
        elif g == 'NOR':
            vals[n['id']] = 1 - int(any(ins))
        elif g == 'XOR':
            vals[n['id']] = sum(ins) % 2
    return vals


def _vectors(inputs):
    for bits in itertools.product((0, 1), repeat=len(inputs)):
        yield dict(zip(inputs, bits))


def truth_table(cell_key):
    """cells-2: rows carry `output` (first output, v1) AND
    `outputs: {pin: value}`; a tri-state cell's rows read 'Z'
    where its three_state holds."""
    cell = _cell(cell_key)
    rows = []
    for v in _vectors(cell['inputs']):
        outs = {o: expected_output(cell, o, v) for o in cell['outputs']}
        rows.append({'vector': v, 'output': outs[cell['output']],
                     'outputs': outs})
    return {'inputs': list(cell['inputs']), 'output': cell['output'],
            'outputs': list(cell['outputs']),
            'threeState': cell.get('three_state'),
            'rows': rows, 'count': len(rows)}


# ---------------------------------------------------------------
# 2. transistor-level schematic graph
# ---------------------------------------------------------------

def _cell(cell_key):
    if cell_key not in CELL_LIBRARY:
        raise KeyError(cell_key)
    return CELL_LIBRARY[cell_key]


def _stages(cell):
    out = []
    for idx, (sub, in_nets, out_net) in enumerate(cell.get('compose', [])):
        if isinstance(in_nets, str):
            in_nets = [in_nets]
        out.append((idx, sub, list(in_nets), out_net))
    return out


def _sub_ports(sub, in_nets, out_net):
    """port -> net for one compose stage; out_net may be a list for
    a multi-output sub-cell (wired in its declared output order)."""
    subcell = CELL_LIBRARY[sub]
    ports = dict(zip(subcell['inputs'], in_nets))
    outs = [out_net] if isinstance(out_net, str) else list(out_net)
    ports.update(dict(zip(subcell['outputs'], outs)))
    return ports


def flat_devices(cell_key, drive=1, prefix=''):
    """(id, type, drain, gate, source) tuples; composed cells are
    flattened with instance-prefixed internal nets (X0.mid)."""
    cell = _cell(cell_key)
    out = []
    if cell.get('compose'):
        for idx, sub, in_nets, out_net in _stages(cell):
            port_map = _sub_ports(sub, in_nets, out_net)
            inst = f'{prefix}X{idx}'
            for did, dtype, dr, gt, src in flat_devices(
                    sub, drive, prefix=inst + '.'):
                nets = []
                for n in (dr, gt, src):
                    local = _strip(n, inst + '.')
                    nets.append(port_map[local] if local in port_map
                                and n != local else n)
                out.append((did, dtype, *nets))
        return out
    for d_idx, (dtype, dr, gt, src) in enumerate(cell['devices']):
        for m in range(drive):
            did = f'{prefix}M{d_idx}' + (f'm{m}' if drive > 1 else '')
            out.append((did, dtype) + tuple(
                _local(n, prefix) for n in (dr, gt, src)))
    return out


def _local(net, prefix):
    return net if net in (VDD_NET, GND_NET) else prefix + net


def _strip(net, prefix):
    return net[len(prefix):] if net.startswith(prefix) else net


def _net_kind(net, cell):
    if net == VDD_NET:
        return 'vdd'
    if net == GND_NET:
        return 'gnd'
    if net in cell['inputs']:
        return 'input'
    if net in cell['outputs']:
        return 'output'
    return 'internal'


def _placement(devices, cell):
    """Layered placement: p network above the output row (y<0),
    n network below (y>0); depth = hops from the rail; columns by
    gate net (inputs in declared order, then internal gate nets)."""
    gate_nets = list(cell['inputs'])
    for _id, _t, _d, gt, _s in devices:
        if gt not in gate_nets:
            gate_nets.append(gt)
    col = {g: i for i, g in enumerate(gate_nets)}

    def depth_from(rail, dtype):
        depth = {rail: 0}
        frontier = [rail]
        while frontier:
            nxt = []
            for net in frontier:
                for did, t, dr, _g, src in devices:
                    if t != dtype:
                        continue
                    for a, b in ((dr, src), (src, dr)):
                        if a == net and b not in depth:
                            depth[b] = depth[net] + 1
                            nxt.append(b)
            frontier = nxt
        return depth

    dp, dn = depth_from(VDD_NET, 'p'), depth_from(GND_NET, 'n')
    hints = {}
    for did, t, dr, gt, src in devices:
        table = dp if t == 'p' else dn
        d = min(table.get(dr, 0), table.get(src, 0))
        y = -(d + 1) if t == 'p' else (d + 1)
        hints[did] = (col[gt], y)
    return hints, gate_nets


def netlist_graph(cell_key, drive=1, flatten=False):
    cell = _cell(cell_key)
    composed = []
    if cell.get('compose'):
        for idx, sub, in_nets, out_net in _stages(cell):
            composed.append({'sub_cell': sub, 'instance': f'X{idx}',
                             'ports': _sub_ports(sub, in_nets, out_net)})
        devices = flat_devices(cell_key, drive) if flatten else []
    else:
        devices = flat_devices(cell_key, drive)
    nets = []
    seen = []
    order = [VDD_NET] + list(cell['inputs']) + list(cell['outputs'])
    for n in order:
        seen.append(n)
    for _id, _t, dr, gt, src in devices:
        for n in (dr, gt, src):
            if n not in seen:
                seen.append(n)
    for c in composed:
        for n in c['ports'].values():
            if n not in seen:
                seen.append(n)
    if GND_NET not in seen:
        seen.append(GND_NET)
    for n in seen:
        nets.append({'id': n, 'kind': _net_kind(n, cell)})
    hints, gate_nets = _placement(devices, cell)
    dev_rows = []
    for did, t, dr, gt, src in devices:
        x, y = hints[did]
        dev_rows.append({'id': did, 'type': t, 'drain': dr,
                         'gate': gt, 'source': src,
                         'x_hint': x, 'y_hint': y})
    return {'cell': cell_key, 'drive': drive, 'nets': nets,
            'devices': dev_rows, 'composed': composed,
            'flattened': bool(flatten or not cell.get('compose')),
            'columns': gate_nets,
            'fet_count': _fet_count(cell_key, drive)}


# ---------------------------------------------------------------
# 3. switch-level evaluation + proof
# ---------------------------------------------------------------

def _conducts(dtype, gate_val):
    if gate_val == 1:
        return dtype == 'n'
    if gate_val == 0:
        return dtype == 'p'
    return False


def _components(nets, devices, values):
    parent = {n: n for n in nets}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    on = []
    unresolved_gates = []
    for did, t, dr, gt, src in devices:
        gv = values.get(gt)
        if gv in ('X', 'Z', None):
            unresolved_gates.append(did)
        if _conducts(t, gv):
            on.append(did)
            ra, rb = find(dr), find(src)
            if ra != rb:
                parent[ra] = rb
    return {n: find(n) for n in nets}, on, unresolved_gates


def _resolve(comp, nets, drivers, stored=None):
    """component -> value from the driver set. cells-2: a component
    with NO driver takes the value STORED on its members (charge
    retention: {1}->1, {0}->0, both->'X' (charge-sharing conflict),
    none->'Z')."""
    seen, kept = {}, {}
    for n in nets:
        if n in drivers:
            seen.setdefault(comp[n], set()).add(drivers[n])
        elif stored and stored.get(n) in (0, 1):
            kept.setdefault(comp[n], set()).add(stored[n])
    out = {}
    for n in nets:
        ds = seen.get(comp[n], set()) or kept.get(comp[n], set())
        if ds == {1}:
            out[n] = 1
        elif ds == {0}:
            out[n] = 0
        elif ds:
            out[n] = 'X'
        else:
            out[n] = 'Z'
    return out


def _paths(start, devices, on_ids, drivers):
    """BFS from the output over conducting devices; the path (device
    id list) to every driver net reached."""
    on = [d for d in devices if d[0] in on_ids]
    prev = {start: None}
    frontier = [start]
    while frontier:
        nxt = []
        for net in frontier:
            for did, _t, dr, _g, src in on:
                for a, b in ((dr, src), (src, dr)):
                    if a == net and b not in prev:
                        prev[b] = (net, did)
                        nxt.append(b)
        frontier = nxt
    paths = []
    for net in prev:
        if net in drivers and net != start:
            devs, cur = [], net
            while prev[cur] is not None:
                p_net, did = prev[cur]
                devs.append(did)
                cur = p_net
            paths.append({'to': net, 'value': drivers[net],
                          'devices': list(reversed(devs))})
    return paths


def _eval_flat(cell, devices, vector, max_iter=12, initial=None):
    """Fixed-point switch-level evaluation of ONE flat device list.
    Inputs and rails are the drivers; internal nets that gate other
    devices (cmux2's sb, cfa's cob) resolve iteratively. cells-2:
    `initial` = stored values of storage nodes before the vector is
    applied — they seed the first iteration's gate values and are
    what an undriven component retains (see _resolve)."""
    nets = [VDD_NET, GND_NET] + list(cell['inputs']) \
        + list(cell['outputs'])
    for _id, _t, dr, gt, src in devices:
        for n in (dr, gt, src):
            if n not in nets:
                nets.append(n)
    drivers = {VDD_NET: 1, GND_NET: 0}
    drivers.update({k: int(bool(vector[k])) for k in cell['inputs']})
    stored = {k: v for k, v in (initial or {}).items() if k in nets}
    values = dict(stored)
    values.update(drivers)
    on, unresolved = [], []
    for _ in range(max_iter):
        comp, on, unresolved = _components(nets, devices, values)
        resolved = _resolve(comp, nets, drivers, stored)
        new_values = dict(resolved)
        new_values.update(drivers)
        if new_values == values:
            break
        values = new_values
    y = cell['output']
    return {
        'output': values[y],
        'outputs': {o: values[o] for o in cell['outputs']},
        'nets': values,
        'conducting': on,
        'paths': _paths(y, devices, set(on), drivers),
        'unresolvedGates': unresolved,
    }


def _classify(val):
    return {'X': 'contention', 'Z': 'floating'}.get(val, 'driven')


def switch_level_eval(cell_key, vector, initial=None):
    """One input vector through the transistor netlist. Composed
    cells evaluate stage by stage (sub-cell outputs feed the next
    stage); every stage is reported. cells-2: `initial` = {net:
    0|1} stored on storage nodes before the vector (latches);
    `outputValues` = every output, `output` = the first."""
    cell = _cell(cell_key)
    vector = {k: int(bool(vector[k])) for k in cell['inputs']}
    if not cell.get('compose'):
        r = _eval_flat(cell, flat_devices(cell_key), vector,
                       initial=initial)
        return {'cell': cell_key, 'vector': vector,
                'output': r['output'], 'outputValues': r['outputs'],
                'status': _classify(r['output']),
                'statuses': {o: _classify(v)
                             for o, v in r['outputs'].items()},
                'nets': r['nets'], 'conducting': r['conducting'],
                'paths': r['paths'],
                'unresolvedGates': r['unresolvedGates'],
                'stages': []}
    net_vals = dict(vector)
    stages, conducting, nets_all = [], [], {}
    for idx, sub, in_nets, out_net in _stages(cell):
        subcell = CELL_LIBRARY[sub]
        ports = _sub_ports(sub, in_nets, out_net)
        sub_vec = {}
        for port, net in zip(subcell['inputs'], in_nets):
            v = net_vals.get(net, 'Z')
            sub_vec[port] = v
        if any(v in ('X', 'Z') for v in sub_vec.values()):
            out_v = 'X' if 'X' in sub_vec.values() else 'Z'
            stage_r = {'output': out_v,
                       'outputs': {o: out_v for o in subcell['outputs']},
                       'nets': {}, 'conducting': [],
                       'paths': [], 'unresolvedGates': []}
        else:
            stage_r = _eval_flat(subcell, flat_devices(sub), sub_vec)
        for o in subcell['outputs']:
            net_vals[ports[o]] = stage_r['outputs'][o]
        inst = f'X{idx}'
        stages.append({'sub_cell': sub, 'instance': inst,
                       'inputs': {n: net_vals.get(n, 'Z') for n in in_nets},
                       'ports': sub_vec,
                       'output_net': ports[subcell['output']],
                       'output': stage_r['output'],
                       'status': _classify(stage_r['output']),
                       'conducting': [f'{inst}.{d}'
                                      for d in stage_r['conducting']],
                       'paths': [dict(p, devices=[f'{inst}.{d}'
                                                  for d in p['devices']])
                                 for p in stage_r['paths']]})
        conducting.extend(stages[-1]['conducting'])
        for n, v in stage_r['nets'].items():
            if n not in (VDD_NET, GND_NET) and n not in subcell['inputs'] \
                    and n not in subcell['outputs']:
                nets_all[f'{inst}.{n}'] = v
    nets_all.update(net_vals)
    nets_all[VDD_NET], nets_all[GND_NET] = 1, 0
    outs = {o: net_vals.get(o, 'Z') for o in cell['outputs']}
    out = outs[cell['output']]
    # the paths reported are those of the stage driving the FIRST
    # output (v1 shape); per-stage paths stay in `stages`
    first_stage = next((s for s in stages
                        if s['output_net'] == cell['output']), None)
    return {'cell': cell_key, 'vector': vector, 'output': out,
            'outputValues': outs,
            'status': _classify(out),
            'statuses': {o: _classify(v) for o, v in outs.items()},
            'nets': nets_all,
            'conducting': conducting,
            'paths': first_stage['paths'] if first_stage
            else (stages[-1]['paths'] if stages else []),
            'unresolvedGates': [], 'stages': stages}


def prove_cell(cell_key):
    """cells-2: EVERY output is checked per vector (mismatches name
    the output); a tri-state cell's expected 'Z' vectors are
    counted in `expectedFloating` and PASS; library sequential
    cells (clatch) are proven over (inputs x previous state) —
    see prove_latch."""
    cell = CELL_LIBRARY.get(cell_key) if cell_key not in SEQUENTIAL \
        else {}
    if cell is None:
        raise KeyError(cell_key)
    if cell_key in SEQUENTIAL:
        return {'cell': cell_key, 'proven': None, 'vectors': 0,
                'mismatches': [], 'contention': [], 'floating': [],
                'note': 'sequential cell: no single boolean function '
                        'to prove against; see state_space'}
    if cell.get('sequential'):
        return prove_latch(cell_key)
    mismatches, contention, floating, expected_z = [], [], [], []
    n = 0
    for v in _vectors(cell['inputs']):
        n += 1
        got_all = switch_level_eval(cell_key, v)['outputValues']
        for out in cell['outputs']:
            want = expected_output(cell, out, v)
            got = got_all[out]
            if got == 'X':
                contention.append(dict(v, output=out) if len(
                    cell['outputs']) > 1 else v)
            elif got == 'Z' and want == 'Z':
                expected_z.append(v)
            elif got == 'Z':
                floating.append(dict(v, output=out) if len(
                    cell['outputs']) > 1 else v)
            if got != want:
                mismatches.append({'vector': v, 'output': out,
                                   'boolean': want, 'switch': got})
    proven = not mismatches and not contention and not floating
    fns = '; '.join(f'{o} = {cell["liberty_functions"][o]}'
                    for o in cell['outputs'])
    if proven:
        note = (f'all {n} vectors x {len(cell["outputs"])} output(s): '
                f'switch-level output equals {fns}; no contention, '
                f'no floating output'
                + (f'; {len(expected_z)} vector(s) Z as REQUIRED by '
                   f'three_state {cell["three_state"]}'
                   if cell.get('three_state') else ''))
    else:
        note = (f'{len(mismatches)} mismatch(es), {len(contention)} '
                f'contention, {len(floating)} floating vector(s) — '
                f'first counter-example: '
                f'{(mismatches or [{"vector": None}])[0]["vector"]}')
    return {'cell': cell_key, 'proven': proven, 'vectors': n,
            'outputs': list(cell['outputs']),
            'mismatches': mismatches, 'contention': contention,
            'floating': floating, 'expectedFloating': expected_z,
            'note': note}


# ---------------------------------------------------------------
# 3b. storage cells (clatch): seeded evaluation + exhaustive proof
# ---------------------------------------------------------------

def _seed_state(cell, q_prev):
    """initial net values for one previous state, from the cell's
    state.nodes map ('Q' = same as Q, '!Q' = complement)."""
    return {net: (q_prev if ref == 'Q' else 1 - q_prev)
            for net, ref in cell['state']['nodes'].items()}


def latch_eval(cell_key, vector, q_prev):
    """One (inputs, previous state) step of a library sequential
    cell: the storage nodes are seeded from q_prev, then the fixed
    point is found."""
    cell = _cell(cell_key)
    r = switch_level_eval(cell_key, vector,
                          initial=_seed_state(cell, q_prev))
    r['previousState'] = q_prev
    r['stored'] = _seed_state(cell, q_prev)
    return r


def _latch_expected(vector, q_prev):
    """transparent-high D latch: Q = D while G=1, holds while G=0."""
    return vector['D'] if vector['G'] else q_prev


def prove_latch(cell_key):
    """Exhaustive over (G, D, Q_prev): 8 seeded switch-level
    evaluations against the latch equation Q = G ? D : Q_prev."""
    cell = _cell(cell_key)
    q_pin = cell['state']['output']
    mismatches, contention, floating = [], [], []
    n = 0
    for v in _vectors(cell['inputs']):
        for q_prev in (0, 1):
            n += 1
            got = latch_eval(cell_key, v, q_prev)['outputValues'][q_pin]
            want = _latch_expected(v, q_prev)
            row = dict(v, Q_prev=q_prev)
            if got == 'X':
                contention.append(row)
            elif got == 'Z':
                floating.append(row)
            if got != want:
                mismatches.append({'vector': row, 'output': q_pin,
                                   'boolean': want, 'switch': got})
    proven = not mismatches and not contention and not floating
    note = (f'all {n} (G, D, Q_prev) cases: seeded switch-level Q '
            f'equals G ? D : Q_prev; no contention, no floating '
            f'output' if proven else
            f'{len(mismatches)} mismatch(es), {len(contention)} '
            f'contention, {len(floating)} floating — first: '
            f'{(mismatches or [{"vector": None}])[0]["vector"]}')
    return {'cell': cell_key, 'proven': proven, 'vectors': n,
            'outputs': [q_pin], 'mismatches': mismatches,
            'contention': contention, 'floating': floating,
            'expectedFloating': [], 'note': note,
            'semantics': 'storage nodes seeded from Q_prev via '
                         'state.nodes; undriven components retain '
                         'their stored value; fixed-point iteration'}


# ---------------------------------------------------------------
# 4. state space
# ---------------------------------------------------------------

def _cdff_instances():
    """Parse the cdff subckt from cnt_cells._SUBCKTS (the S4c hand
    topology) into its instance rows — description, not simulation."""
    body = _SUBCKTS.split('.subckt cdff', 1)[1].split('.ends cdff')[0]
    rows = []
    phase = None
    for line in body.splitlines()[1:]:
        line = line.strip()
        if line.startswith('*'):
            if 'master' in line:
                phase = 'master'
            elif 'slave' in line:
                phase = 'slave'
            continue
        if not line.startswith('X'):
            continue
        parts = line.split()
        name, sub = parts[0], parts[-1]
        nets = parts[1:-1]
        role = 'clock-inverter' if phase is None else phase
        rows.append({'instance': name, 'sub_cell': sub, 'nets': nets,
                     'role': role,
                     'kind': 'transmission-gate' if sub == 'ctg'
                     else 'inverter'})
    return rows


def _cdff_state_space():
    inst = _cdff_instances()
    tgs = {r['instance']: r for r in inst if r['sub_cell'] == 'ctg'}
    phases = [
        {'clk': 0, 'master': 'transparent', 'slave': 'holding',
         'conducting_tgs': [k for k, r in tgs.items()
                            if r['nets'][2] == 'clkb'],
         'blocked_tgs': [k for k, r in tgs.items()
                         if r['nets'][2] == 'clk'],
         'description': 'CLK=0: master input TG passes D to m1 '
                        '(the master follows D); the slave TG is '
                        'off and the slave feedback TG closes its '
                        'loop, so Q holds'},
        {'clk': 1, 'master': 'holding', 'slave': 'transparent',
         'conducting_tgs': [k for k, r in tgs.items()
                            if r['nets'][2] == 'clk'],
         'blocked_tgs': [k for k, r in tgs.items()
                         if r['nets'][2] == 'clkb'],
         'description': 'CLK=1: master input TG opens and its '
                        'feedback TG closes the master loop '
                        '(m1/m2 latched = the D sampled at the '
                        'edge); the slave TG passes m2 to s1 and '
                        'Q = D-at-edge'},
    ]
    transitions = []
    for q in (0, 1):
        for d in (0, 1):
            transitions.append({
                'from': f'Q={q}', 'input': {'D': d, 'CLK': 'rising'},
                'to': f'Q={d}',
                'kind': 'capture' if d != q else 'retain'})
    return {
        'kind': 'sequential',
        'states': ['Q=0', 'Q=1'],
        'transitions': transitions,
        'phases': phases,
        'latches': [
            {'name': 'master', 'nodes': ['m1', 'm2', 'm3'],
             'inverters': [r['instance'] for r in inst
                           if r['role'] == 'master'
                           and r['kind'] == 'inverter'],
             'input_tg': 'Xtgi', 'feedback_tg': 'Xtgf'},
            {'name': 'slave', 'nodes': ['s1', 'q', 's2'],
             'inverters': [r['instance'] for r in inst
                           if r['role'] == 'slave'
                           and r['kind'] == 'inverter'],
             'input_tg': 'Xtgs', 'feedback_tg': 'Xtgb'},
        ],
        'instances': inst,
        'description': 'positive-edge transmission-gate master-slave '
                       'DFF: 2 TG pairs + 5 inverters (18 FETs). On '
                       'the rising CLK edge the master freezes the D '
                       'it was following and the slave becomes '
                       'transparent, so Q takes that D; Q changes '
                       'only on rising edges.',
        'source': 'cnt_cells._SUBCKTS (cdff), parsed — not simulated',
    }


def _latch_state_space(cell_key):
    """clatch: states Q=0/1; from each state the three input
    situations — G=1,D=0 / G=1,D=1 (transparent: Q follows D) and
    G=0 (hold) — each transition carries its seeded switch-level
    evaluation so the step-through shows the conducting TG."""
    cell = _cell(cell_key)
    q_pin = cell['state']['output']
    transitions = []
    for q in (0, 1):
        for g, d in ((1, 0), (1, 1), (0, 0), (0, 1)):
            r = latch_eval(cell_key, {'D': d, 'G': g}, q)
            to = r['outputValues'][q_pin]
            if g == 0:
                kind = 'hold'
            else:
                kind = 'follow' if to != q else 'retain'
            transitions.append({
                'from': f'Q={q}', 'input': {'D': d, 'G': g},
                'to': f'Q={to}', 'kind': kind,
                'phase': 'transparent' if g else 'holding',
                'output': to, 'status': r['status'],
                'conducting': r['conducting'],
                'nets': {k: v for k, v in r['nets'].items()
                         if k in cell['state']['nodes'] or k == 'gb'}})
    phases = [
        {'G': 1, 'latch': 'transparent',
         'description': 'G=1: the input TG (n on G, p on gb) passes '
                        'D to m1; two inverters re-drive Q = D; the '
                        'feedback TG is off'},
        {'G': 0, 'latch': 'holding',
         'description': 'G=0: the input TG opens, the feedback TG '
                        '(n on gb, p on G) closes Q -> m1 and the '
                        'inverter pair holds Q from the rails'},
    ]
    return {'kind': 'sequential', 'cell': cell_key,
            'states': ['Q=0', 'Q=1'], 'transitions': transitions,
            'phases': phases,
            'latches': [{'name': 'loop',
                         'nodes': list(cell['state']['nodes']),
                         'input_tg': ['M2', 'M3'],
                         'feedback_tg': ['M8', 'M9'],
                         'inverters': [['M4', 'M5'], ['M6', 'M7']]}],
            'description': 'transparent-high D latch: G inverter + '
                           'input TG + 2 inverters + feedback TG (10 '
                           'FETs); Q follows D while G=1 and holds '
                           'while G=0',
            'source': 'CELL_LIBRARY[clatch] devices, switch-level '
                      'evaluated with the previous state seeded '
                      '(not simulated)'}


def state_space(cell_key):
    if cell_key in SEQUENTIAL:
        return _cdff_state_space()
    cell = _cell(cell_key)
    if cell.get('sequential'):
        return _latch_state_space(cell_key)
    steps = []
    for idx, v in enumerate(_vectors(cell['inputs'])):
        r = switch_level_eval(cell_key, v)
        booleans = {o: expected_output(cell, o, v)
                    for o in cell['outputs']}
        steps.append({'index': idx, 'vector': v,
                      'boolean': booleans[cell['output']],
                      'booleans': booleans,
                      'output': r['output'],
                      'outputValues': r['outputValues'],
                      'status': r['status'],
                      'conducting': r['conducting'],
                      'stages': [{'instance': s['instance'],
                                  'sub_cell': s['sub_cell'],
                                  'output': s['output']}
                                 for s in r['stages']]})
    return {'kind': 'combinational', 'inputs': list(cell['inputs']),
            'output': cell['output'], 'outputs': list(cell['outputs']),
            'steps': steps, 'count': len(steps)}


def step(cell_key, index):
    if cell_key in SEQUENTIAL:
        ss = _cdff_state_space()
        t = ss['transitions'][index % len(ss['transitions'])]
        return {'cell': cell_key, 'index': index, 'transition': t,
                'phases': ss['phases']}
    cell = _cell(cell_key)
    if cell.get('sequential'):
        ss = _latch_state_space(cell_key)
        t = ss['transitions'][index % len(ss['transitions'])]
        return {'cell': cell_key, 'index': index, 'transition': t,
                'phases': ss['phases']}
    vecs = list(_vectors(cell['inputs']))
    v = vecs[index % len(vecs)]
    r = switch_level_eval(cell_key, v)
    dag = cell_gate_dag(cell_key)
    r['index'] = index
    r['boolean'] = expected_output(cell, cell['output'], v)
    r['booleans'] = {o: expected_output(cell, o, v)
                     for o in cell['outputs']}
    r['dagValues'] = dag_values(dag, v)
    return r


# ---------------------------------------------------------------
# 5. reports
# ---------------------------------------------------------------

def _refusal(cell_key):
    return {'ok': False,
            'refusal': f'unknown cell {cell_key!r}; the library is '
                       f'{sorted(CELL_LIBRARY)} + {SEQUENTIAL}',
            'library': sorted(CELL_LIBRARY) + SEQUENTIAL}


def cell_logic_report(cell_key, drive=1):
    if cell_key in SEQUENTIAL:
        ss = _cdff_state_space()
        return {'ok': True, 'cell': cell_key, 'drive': 1,
                'function': 'DFF', 'inputs': ['D', 'CLK'],
                'output': 'Q', 'outputs': ['Q'], 'ast': None,
                'asts': None, 'gateDag': None,
                'truthTable': None, 'netlist': None,
                'proof': prove_cell(cell_key), 'stateSpace': ss,
                'fetCount': 18, 'sequential': True,
                'honesty': 'sequential: state graph parsed from the '
                           'cdff subckt; timing (setup/hold/clk->Q) '
                           'is cnt_sequential, not this module',
                'payloadVersion': LOGIC_PAYLOAD_VERSION}
    if cell_key not in CELL_LIBRARY:
        return _refusal(cell_key)
    cell = CELL_LIBRARY[cell_key]
    proof = prove_cell(cell_key)
    if cell.get('sequential'):
        return {
            'ok': True, 'cell': cell_key, 'drive': drive,
            'function': cell['function'],
            'inputs': list(cell['inputs']),
            'output': cell['output'], 'outputs': list(cell['outputs']),
            'libertyFunction': None, 'libertyFunctions': None,
            'threeState': None, 'unate': cell['unate'],
            'ast': None, 'asts': None, 'gateDag': None,
            'truthTable': None,
            'netlist': netlist_graph(cell_key, drive),
            'proof': proof, 'stateSpace': state_space(cell_key),
            'fetCount': _fet_count(cell_key, drive),
            'sequential': True,
            'honesty': ('library sequential cell: switch-level '
                        'proof over (G, D, Q_prev) with the storage '
                        'nodes seeded; timing (D->Q, setup, hold) is '
                        'cnt_sequential.characterize_latch. '
                        + ('PROVEN.' if proof['proven']
                           else 'NOT PROVEN: ' + proof['note'])),
            'payloadVersion': LOGIC_PAYLOAD_VERSION,
        }
    asts = {o: boolean_ast(cell['liberty_functions'][o])
            for o in cell['outputs']}
    return {
        'ok': True, 'cell': cell_key, 'drive': drive,
        'function': cell['function'], 'inputs': list(cell['inputs']),
        'output': cell['output'], 'outputs': list(cell['outputs']),
        'libertyFunction': cell['liberty_function'],
        'libertyFunctions': dict(cell['liberty_functions']),
        'threeState': cell.get('three_state'),
        'unate': cell['unate'],
        'ast': asts[cell['output']], 'asts': asts,
        'gateDag': cell_gate_dag(cell_key),
        'truthTable': truth_table(cell_key),
        'netlist': netlist_graph(cell_key, drive,
                                 flatten=bool(cell.get('compose'))),
        'proof': proof, 'stateSpace': state_space(cell_key),
        'fetCount': _fet_count(cell_key, drive),
        'sequential': False,
        'provenance': _cell_provenance(cell_key),
        'honesty': ('switch-level proof: ideal switches (a device '
                    'conducts iff its gate is at the controlling '
                    'level); no thresholds, no drive-fight '
                    'resolution, no timing. Composed cells are '
                    'proven stage by stage; every output is checked; '
                    "a tri-state cell's Z vectors are expected. "
                    + ('PROVEN.' if proof['proven']
                       else 'NOT PROVEN: ' + proof['note'])),
        'payloadVersion': LOGIC_PAYLOAD_VERSION,
    }


def library_logic_report():
    cells = []
    for key in COMBINATIONAL:
        p = prove_cell(key)
        c = CELL_LIBRARY[key]
        cells.append({'cell': key, 'function': c['function'],
                      'inputs': list(c['inputs']),
                      'outputs': list(c['outputs']),
                      'libertyFunction': c['liberty_function'],
                      'libertyFunctions': dict(c['liberty_functions']),
                      'threeState': c.get('three_state'),
                      'fetCount': _fet_count(key, 1),
                      'composed': bool(c.get('compose')),
                      'proven': p['proven'], 'vectors': p['vectors'],
                      'mismatches': p['mismatches'],
                      'contention': p['contention'],
                      'floating': p['floating'],
                      'expectedFloating': p.get('expectedFloating', [])})
    seq = {'cdff': _cdff_state_space()}
    seq_proofs = {}
    for key in SEQUENTIAL_CELLS:
        seq[key] = state_space(key)
        seq_proofs[key] = prove_cell(key)
    return {'ok': True, 'payloadVersion': LOGIC_PAYLOAD_VERSION,
            'combinational': cells,
            'allProven': all(c['proven'] for c in cells)
            and all(p['proven'] for p in seq_proofs.values()),
            'multiOutput': list(MULTI_OUTPUT), 'tristate': list(TRISTATE),
            'sequential': seq, 'sequentialProofs': seq_proofs,
            'library': sorted(CELL_LIBRARY) + SEQUENTIAL}


# ---------------------------------------------------------------
# 6. payload contract (read by the d3 components)
# ---------------------------------------------------------------

def payload_contract():
    return {
        'version': LOGIC_PAYLOAD_VERSION,
        'changelog': {
            '2': 'cells-2 (2026-08-27), ADDITIVE — every v1 key keeps '
                 'its v1 meaning; `output` is always the FIRST output. '
                 'New: outputs:[pin] and outputValues:{pin: value} on '
                 'every evaluation/step; truthTable rows.outputs and '
                 'top-level outputs/threeState; proof.outputs, '
                 'proof.expectedFloating and mismatches[].output; '
                 'gateDag with ONE output node per output; '
                 'cellLogicReport asts/libertyFunctions/threeState/'
                 'sequential; stateSpace.sequential for clatch (input '
                 '{D, G}, kind follow|retain|hold, phase); '
                 'switchLevel.initial (stored values) and '
                 "'Z' as an EXPECTED value where three_state holds; "
                 'libraryLogicReport multiOutput/tristate/'
                 'sequentialProofs.',
        },
        'ast': "{op:'and'|'or'|'xor'|'not', args:[ast]} | {op:'var', name}",
        'asts': '{outputPin: ast} (v2; ast = asts[output])',
        'gateDag': {
            'nodes': "[{id, kind:'input'|'output'|'gate', gate:"
                     "'AND'|'OR'|'NOT'|'NAND'|'NOR'|'XOR'|'BUF'|null,"
                     " label, inputs:[id], level:int}]",
            'edges': '[{from:id, to:id}]',
            'note': 'NOT over and/or folded into NAND/NOR; inputs '
                    'level 0; output = max gate level + 1; v2: one '
                    'output node PER OUTPUT pin (multi-output cells '
                    'share the input nodes, gate ids run on)',
        },
        'truthTable': "{inputs:[str], output:str, outputs:[str] (v2),"
                      " threeState:str|null (v2), rows:[{vector:{pin:0|1},"
                      " output:0|1|'Z', outputs:{pin:0|1|'Z'} (v2)}],"
                      " count:int}",
        'netlist': {
            'nets': "[{id, kind:'vdd'|'gnd'|'input'|'output'|'internal'}]",
            'devices': "[{id, type:'n'|'p', drain, gate, source, x_hint:int"
                       " (column = gate net index), y_hint:int (<0 p"
                       " network above the output row 0, >0 n network"
                       " below; |y| = 1 + hops from the rail)}]",
            'composed': "[{sub_cell, instance:'X<i>', ports:{port:net}}]",
            'flattened': 'bool — devices carry instance-prefixed ids '
                         "('X0.M1') and internal nets ('X0.mid')",
            'columns': '[gate net per x_hint column]',
            'fet_count': 'int',
        },
        'switchLevel': {
            'shape': "{cell, vector:{pin:0|1}, output:0|1|'X'|'Z',"
                     " outputValues:{pin: 0|1|'X'|'Z'} (v2),"
                     " status:'driven'|'contention'|'floating',"
                     " statuses:{pin: status} (v2),"
                     " nets:{net: 0|1|'X'|'Z'}, conducting:[deviceId],"
                     " paths:[{to:net, value, devices:[deviceId]}],"
                     " unresolvedGates:[deviceId],"
                     " stages:[{sub_cell, instance, inputs:{net:val},"
                     " ports:{port:val}, output_net, output, status,"
                     " conducting, paths}], previousState:0|1 (v2,"
                     " latch_eval only), stored:{net:0|1} (v2, latch_eval"
                     " only)}",
            'semantics': 'n conducts at gate=1, p at gate=0; drivers = '
                         'vdd(1), gnd(0) and INPUT nets (pass gates '
                         'pass their source value); {1}->1 {0}->0 '
                         "both->'X' none->'Z'; internal gate nets "
                         'resolved by fixed-point iteration. v2: an '
                         'optional `initial` {net: 0|1} seeds storage '
                         'nodes — a component with NO driver takes the '
                         'value stored on its members (charge '
                         "retention; conflicting stores -> 'X'); the "
                         "output of a tri-state cell is EXPECTED 'Z' "
                         'where its three_state expression holds',
        },
        'proof': "{cell, proven:bool|null, vectors:int, outputs:[pin]"
                 " (v2), mismatches:[{vector, output (v2), boolean,"
                 " switch}], contention:[vector], floating:[vector],"
                 " expectedFloating:[vector] (v2, tri-state Z vectors"
                 " that PASS), note, semantics (v2, latch only)}",
        'stateSpace': {
            'combinational': "{kind:'combinational', inputs, output,"
                             " outputs (v2), steps:[{index, vector,"
                             " boolean, booleans:{pin:val} (v2), output,"
                             " outputValues (v2), status,"
                             " conducting:[deviceId],"
                             " stages:[{instance, sub_cell, output}]}],"
                             " count}",
            'sequential': "{kind:'sequential', states:['Q=0','Q=1'],"
                          " transitions:[{from, input:{D, CLK:'rising'},"
                          " to, kind:'capture'|'retain'}], phases:[{clk,"
                          " master, slave, conducting_tgs, blocked_tgs,"
                          " description}], latches:[{name, nodes,"
                          " inverters, input_tg, feedback_tg}],"
                          " instances:[{instance, sub_cell, nets, role,"
                          " kind}], description, source}",
            'latch': "(v2, clatch) {kind:'sequential', cell,"
                     " states:['Q=0','Q=1'], transitions:[{from,"
                     " input:{D, G}, to, kind:'follow'|'retain'|'hold',"
                     " phase:'transparent'|'holding', output, status,"
                     " conducting:[deviceId], nets:{storageNet:val}}],"
                     " phases:[{G, latch, description}], latches:[{name,"
                     " nodes, input_tg, feedback_tg, inverters}],"
                     " description, source}",
        },
        'step': "switchLevel shape + {index, boolean, booleans (v2),"
                " dagValues:{nodeId: 0|1}} (combinational) | {cell,"
                " index, transition, phases} (cdff, clatch)",
        'cellLogicReport': "{ok, cell, drive, function, inputs, output,"
                           " outputs (v2), libertyFunction,"
                           " libertyFunctions:{pin:str} (v2),"
                           " threeState (v2), unate, ast, asts (v2),"
                           " gateDag, truthTable, netlist, proof,"
                           " stateSpace, fetCount, sequential:bool (v2),"
                           " honesty, payloadVersion}",
        'libraryLogicReport': "{ok, payloadVersion, combinational:[{cell,"
                              " function, inputs, outputs (v2),"
                              " libertyFunction, libertyFunctions (v2),"
                              " threeState (v2), fetCount, composed,"
                              " proven, vectors, mismatches, contention,"
                              " floating, expectedFloating (v2)}],"
                              " allProven (v2: includes the latch proof),"
                              " multiOutput:[cell] (v2), tristate:[cell]"
                              " (v2), sequential:{cdff: stateSpace, clatch:"
                              " stateSpace (v2)}, sequentialProofs:{clatch:"
                              " proof} (v2), library}",
        'refusal': "{ok:false, refusal:str, library:[cell]}",
    }


def to_json(payload):
    return json.dumps(payload, sort_keys=True)


def _cell_provenance(cell_key):
    """evidence: the cell's IP verdict + proof-of-freedom summary
    (seed-backed when no manager is at hand; click-through detailPath)."""
    from cntfet.cnt_device_viz import provenance
    return provenance(None, 'cell', cell_key)
