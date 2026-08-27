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

@consumers
  - cntfet.cnt_api ({action: cell-logic}) — wired by the integrator
  - cntfet.selftest_logic
"""

import itertools
import json
import re

from cntfet.cnt_cell_library import (
    CELL_LIBRARY, COMBINATIONAL, fet_count as _fet_count,
)
from cntfet.cnt_cells import _SUBCKTS

LOGIC_PAYLOAD_VERSION = 1

VDD_NET = 'vddn'
GND_NET = '0'
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


def gate_dag(ast, cell_key=None):
    """Gate-level DAG. NOT over and/or folds into NAND/NOR; every
    other node is kept faithful to the AST (INV = NOT, BUF = a
    bare variable, AOI21 = NOR over (AND, C))."""
    cell = CELL_LIBRARY.get(cell_key) if cell_key else None
    inputs = list(cell['inputs']) if cell else ast_vars(ast)
    output = cell['output'] if cell else 'Y'
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
    cell = _cell(cell_key)
    ast = boolean_ast(cell['liberty_function'])
    rows = [{'vector': v, 'output': evaluate(ast, v)}
            for v in _vectors(cell['inputs'])]
    return {'inputs': list(cell['inputs']), 'output': cell['output'],
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


def flat_devices(cell_key, drive=1, prefix=''):
    """(id, type, drain, gate, source) tuples; composed cells are
    flattened with instance-prefixed internal nets (X0.mid)."""
    cell = _cell(cell_key)
    out = []
    if cell.get('compose'):
        for idx, sub, in_nets, out_net in _stages(cell):
            subcell = CELL_LIBRARY[sub]
            port_map = dict(zip(subcell['inputs'], in_nets))
            port_map[subcell['output']] = out_net
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
    if net == cell['output']:
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
            subcell = CELL_LIBRARY[sub]
            ports = dict(zip(subcell['inputs'], in_nets))
            ports[subcell['output']] = out_net
            composed.append({'sub_cell': sub, 'instance': f'X{idx}',
                             'ports': ports})
        devices = flat_devices(cell_key, drive) if flatten else []
    else:
        devices = flat_devices(cell_key, drive)
    nets = []
    seen = []
    order = [VDD_NET] + list(cell['inputs']) + [cell['output']]
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


def _resolve(comp, nets, drivers):
    """component -> value from the driver set."""
    seen = {}
    for n in nets:
        if n in drivers:
            seen.setdefault(comp[n], set()).add(drivers[n])
    out = {}
    for n in nets:
        ds = seen.get(comp[n], set())
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


def _eval_flat(cell, devices, vector, max_iter=8):
    """Fixed-point switch-level evaluation of ONE flat device list.
    Inputs and rails are the drivers; internal nets that gate other
    devices (cmux2's sb) resolve iteratively."""
    nets = [VDD_NET, GND_NET] + list(cell['inputs']) + [cell['output']]
    for _id, _t, dr, gt, src in devices:
        for n in (dr, gt, src):
            if n not in nets:
                nets.append(n)
    drivers = {VDD_NET: 1, GND_NET: 0}
    drivers.update({k: int(bool(vector[k])) for k in cell['inputs']})
    values = dict(drivers)
    on, unresolved = [], []
    for _ in range(max_iter):
        comp, on, unresolved = _components(nets, devices, values)
        resolved = _resolve(comp, nets, drivers)
        new_values = dict(resolved)
        new_values.update(drivers)
        if new_values == values:
            break
        values = new_values
    y = cell['output']
    return {
        'output': values[y],
        'nets': values,
        'conducting': on,
        'paths': _paths(y, devices, set(on), drivers),
        'unresolvedGates': unresolved,
    }


def _classify(val):
    return {'X': 'contention', 'Z': 'floating'}.get(val, 'driven')


def switch_level_eval(cell_key, vector):
    """One input vector through the transistor netlist. Composed
    cells evaluate stage by stage (sub-cell outputs feed the next
    stage); every stage is reported."""
    cell = _cell(cell_key)
    vector = {k: int(bool(vector[k])) for k in cell['inputs']}
    if not cell.get('compose'):
        r = _eval_flat(cell, flat_devices(cell_key), vector)
        return {'cell': cell_key, 'vector': vector,
                'output': r['output'], 'status': _classify(r['output']),
                'nets': r['nets'], 'conducting': r['conducting'],
                'paths': r['paths'],
                'unresolvedGates': r['unresolvedGates'],
                'stages': []}
    net_vals = dict(vector)
    stages, conducting, nets_all = [], [], {}
    for idx, sub, in_nets, out_net in _stages(cell):
        subcell = CELL_LIBRARY[sub]
        sub_vec = {}
        for port, net in zip(subcell['inputs'], in_nets):
            v = net_vals.get(net, 'Z')
            sub_vec[port] = v
        if any(v in ('X', 'Z') for v in sub_vec.values()):
            out_v = 'X' if 'X' in sub_vec.values() else 'Z'
            stage_r = {'output': out_v, 'nets': {}, 'conducting': [],
                       'paths': [], 'unresolvedGates': []}
        else:
            stage_r = _eval_flat(subcell, flat_devices(sub), sub_vec)
        net_vals[out_net] = stage_r['output']
        inst = f'X{idx}'
        stages.append({'sub_cell': sub, 'instance': inst,
                       'inputs': {n: net_vals.get(n, 'Z') for n in in_nets},
                       'ports': sub_vec, 'output_net': out_net,
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
                    and n != subcell['output']:
                nets_all[f'{inst}.{n}'] = v
    nets_all.update(net_vals)
    nets_all[VDD_NET], nets_all[GND_NET] = 1, 0
    out = net_vals.get(cell['output'], 'Z')
    return {'cell': cell_key, 'vector': vector, 'output': out,
            'status': _classify(out), 'nets': nets_all,
            'conducting': conducting,
            'paths': stages[-1]['paths'] if stages else [],
            'unresolvedGates': [], 'stages': stages}


def prove_cell(cell_key):
    cell = CELL_LIBRARY.get(cell_key) if cell_key not in SEQUENTIAL \
        else {}
    if cell is None:
        raise KeyError(cell_key)
    if cell_key in SEQUENTIAL or not cell.get('liberty_function'):
        return {'cell': cell_key, 'proven': None, 'vectors': 0,
                'mismatches': [], 'contention': [], 'floating': [],
                'note': 'sequential cell: no single boolean function '
                        'to prove against; see state_space'}
    ast = boolean_ast(cell['liberty_function'])
    mismatches, contention, floating = [], [], []
    n = 0
    for v in _vectors(cell['inputs']):
        n += 1
        want = evaluate(ast, v)
        got = switch_level_eval(cell_key, v)['output']
        if got == 'X':
            contention.append(v)
        elif got == 'Z':
            floating.append(v)
        if got != want:
            mismatches.append({'vector': v, 'boolean': want,
                               'switch': got})
    proven = not mismatches and not contention and not floating
    if proven:
        note = (f'all {n} vectors: switch-level output equals '
                f'{cell["liberty_function"]}; no contention, no '
                f'floating output')
    else:
        note = (f'{len(mismatches)} mismatch(es), {len(contention)} '
                f'contention, {len(floating)} floating vector(s) — '
                f'first counter-example: '
                f'{(mismatches or [{"vector": None}])[0]["vector"]}')
    return {'cell': cell_key, 'proven': proven, 'vectors': n,
            'mismatches': mismatches, 'contention': contention,
            'floating': floating, 'note': note}


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


def state_space(cell_key):
    if cell_key in SEQUENTIAL:
        return _cdff_state_space()
    cell = _cell(cell_key)
    ast = boolean_ast(cell['liberty_function'])
    steps = []
    for idx, v in enumerate(_vectors(cell['inputs'])):
        r = switch_level_eval(cell_key, v)
        steps.append({'index': idx, 'vector': v,
                      'boolean': evaluate(ast, v),
                      'output': r['output'], 'status': r['status'],
                      'conducting': r['conducting'],
                      'stages': [{'instance': s['instance'],
                                  'sub_cell': s['sub_cell'],
                                  'output': s['output']}
                                 for s in r['stages']]})
    return {'kind': 'combinational', 'inputs': list(cell['inputs']),
            'output': cell['output'], 'steps': steps,
            'count': len(steps)}


def step(cell_key, index):
    if cell_key in SEQUENTIAL:
        ss = _cdff_state_space()
        t = ss['transitions'][index % len(ss['transitions'])]
        return {'cell': cell_key, 'index': index, 'transition': t,
                'phases': ss['phases']}
    cell = _cell(cell_key)
    vecs = list(_vectors(cell['inputs']))
    v = vecs[index % len(vecs)]
    r = switch_level_eval(cell_key, v)
    dag = gate_dag(boolean_ast(cell['liberty_function']), cell_key)
    r['index'] = index
    r['boolean'] = evaluate(boolean_ast(cell['liberty_function']), v)
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
                'output': 'Q', 'ast': None, 'gateDag': None,
                'truthTable': None, 'netlist': None,
                'proof': prove_cell(cell_key), 'stateSpace': ss,
                'fetCount': 18,
                'honesty': 'sequential: state graph parsed from the '
                           'cdff subckt; timing (setup/hold/clk->Q) '
                           'is cnt_sequential, not this module',
                'payloadVersion': LOGIC_PAYLOAD_VERSION}
    if cell_key not in CELL_LIBRARY:
        return _refusal(cell_key)
    cell = CELL_LIBRARY[cell_key]
    ast = boolean_ast(cell['liberty_function'])
    proof = prove_cell(cell_key)
    return {
        'ok': True, 'cell': cell_key, 'drive': drive,
        'function': cell['function'], 'inputs': list(cell['inputs']),
        'output': cell['output'],
        'libertyFunction': cell['liberty_function'],
        'unate': cell['unate'],
        'ast': ast, 'gateDag': gate_dag(ast, cell_key),
        'truthTable': truth_table(cell_key),
        'netlist': netlist_graph(cell_key, drive,
                                 flatten=bool(cell.get('compose'))),
        'proof': proof, 'stateSpace': state_space(cell_key),
        'fetCount': _fet_count(cell_key, drive),
        'honesty': ('switch-level proof: ideal switches (a device '
                    'conducts iff its gate is at the controlling '
                    'level); no thresholds, no drive-fight '
                    'resolution, no timing. Composed cells are '
                    'proven stage by stage. '
                    + ('PROVEN.' if proof['proven']
                       else 'NOT PROVEN: ' + proof['note'])),
        'payloadVersion': LOGIC_PAYLOAD_VERSION,
    }


def library_logic_report():
    cells = []
    for key in COMBINATIONAL:
        p = prove_cell(key)
        cells.append({'cell': key, 'function': CELL_LIBRARY[key]['function'],
                      'inputs': list(CELL_LIBRARY[key]['inputs']),
                      'libertyFunction': CELL_LIBRARY[key]['liberty_function'],
                      'fetCount': _fet_count(key, 1),
                      'composed': bool(CELL_LIBRARY[key].get('compose')),
                      'proven': p['proven'], 'vectors': p['vectors'],
                      'mismatches': p['mismatches'],
                      'contention': p['contention'],
                      'floating': p['floating']})
    return {'ok': True, 'payloadVersion': LOGIC_PAYLOAD_VERSION,
            'combinational': cells,
            'allProven': all(c['proven'] for c in cells),
            'sequential': {'cdff': _cdff_state_space()},
            'library': sorted(CELL_LIBRARY) + SEQUENTIAL}


# ---------------------------------------------------------------
# 6. payload contract (read by the d3 components)
# ---------------------------------------------------------------

def payload_contract():
    return {
        'version': LOGIC_PAYLOAD_VERSION,
        'ast': "{op:'and'|'or'|'xor'|'not', args:[ast]} | {op:'var', name}",
        'gateDag': {
            'nodes': "[{id, kind:'input'|'output'|'gate', gate:"
                     "'AND'|'OR'|'NOT'|'NAND'|'NOR'|'XOR'|'BUF'|null,"
                     " label, inputs:[id], level:int}]",
            'edges': '[{from:id, to:id}]',
            'note': 'NOT over and/or folded into NAND/NOR; inputs '
                    'level 0; output = max gate level + 1',
        },
        'truthTable': "{inputs:[str], output:str, rows:[{vector:{pin:0|1},"
                      " output:0|1}], count:int}",
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
                     " status:'driven'|'contention'|'floating',"
                     " nets:{net: 0|1|'X'|'Z'}, conducting:[deviceId],"
                     " paths:[{to:net, value, devices:[deviceId]}],"
                     " unresolvedGates:[deviceId],"
                     " stages:[{sub_cell, instance, inputs:{net:val},"
                     " ports:{port:val}, output_net, output, status,"
                     " conducting, paths}]}",
            'semantics': 'n conducts at gate=1, p at gate=0; drivers = '
                         'vdd(1), gnd(0) and INPUT nets (pass gates '
                         'pass their source value); {1}->1 {0}->0 '
                         "both->'X' none->'Z'; internal gate nets "
                         'resolved by fixed-point iteration',
        },
        'proof': "{cell, proven:bool|null, vectors:int, mismatches:"
                 "[{vector, boolean, switch}], contention:[vector],"
                 " floating:[vector], note}",
        'stateSpace': {
            'combinational': "{kind:'combinational', inputs, output,"
                             " steps:[{index, vector, boolean, output,"
                             " status, conducting:[deviceId],"
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
        },
        'step': "switchLevel shape + {index, boolean, dagValues:{nodeId:"
                " 0|1}} (combinational) | {cell, index, transition,"
                " phases} (cdff)",
        'cellLogicReport': "{ok, cell, drive, function, inputs, output,"
                           " libertyFunction, unate, ast, gateDag,"
                           " truthTable, netlist, proof, stateSpace,"
                           " fetCount, honesty, payloadVersion}",
        'libraryLogicReport': "{ok, payloadVersion, combinational:[{cell,"
                              " function, inputs, libertyFunction,"
                              " fetCount, composed, proven, vectors,"
                              " mismatches, contention, floating}],"
                              " allProven, sequential:{cdff: stateSpace},"
                              " library}",
        'refusal': "{ok:false, refusal:str, library:[cell]}",
    }


def to_json(payload):
    return json.dumps(payload, sort_keys=True)
