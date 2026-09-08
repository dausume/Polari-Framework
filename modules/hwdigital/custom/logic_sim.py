"""
@module hwdigital.custom.logic_sim

ncg-3: the pure-python REFERENCE EVALUATOR for LogicBlockNode designs
— the second implementation that keeps the Verilog generator honest
(the generated bench compares real verilated logic against THESE
values), and the slow-motion teaching trace for the frontend later.

Deterministic by construction: combinational nodes evaluate in
topological order (a combinational cycle is a plain error, never a
hang); clocked nodes (dff/counter) latch on step(). Reset state is
each clocked node's `init`.
"""

import json

from hwdigital.logic_basis import CLOCKED_KINDS, NODE_KINDS


def load_design(manager, design_name):
    """(design_row, ordered node rows) — plain errors on unknowns."""
    designs = (manager.objectTables or {}).get('LogicBlockDesign', {})
    design = next((d for d in designs.values()
                   if getattr(d, 'name', '') == design_name), None)
    if design is None:
        raise ValueError(f"no LogicBlockDesign named '{design_name}'")
    nodes = [n for n in (manager.objectTables or {}).get(
                 'LogicBlockNode', {}).values()
             if getattr(n, 'design_name', '') == design_name]
    if not nodes:
        raise ValueError(f"design '{design_name}' has no "
                         f'LogicBlockNode rows')
    return design, sorted(nodes, key=lambda n: getattr(n, 'name', ''))


def node_spec(node):
    """Normalize one row -> {name, kind, width, params, inputs}."""
    kind = getattr(node, 'kind', '')
    if kind not in NODE_KINDS:
        raise ValueError(f"node '{node.name}': unknown kind '{kind}' "
                         f'(kinds: {", ".join(NODE_KINDS)})')
    params = json.loads(getattr(node, 'params_json', '{}') or '{}')
    inputs = json.loads(getattr(node, 'inputs_json', '[]') or '[]')
    return {'name': node.name, 'kind': kind,
            'width': int(params.get('width', 1)), 'params': params,
            'inputs': inputs}


#: Identifiers the generated Verilog module claims for itself — a
#: node with one of these (post-sanitization) names would emit a
#: duplicate port while the python evaluator happily ran it.
RESERVED_IDENTS = frozenset({'clk', 'rst'})


def design_specs(manager, design_name):
    _, nodes = load_design(manager, design_name)
    specs = {s['name']: s for s in (node_spec(n) for n in nodes)}
    for s in specs.values():
        for src in s['inputs']:
            if src not in specs:
                raise ValueError(
                    f"node '{s['name']}' reads '{src}' which is not "
                    f'a node of this design')
    # Verilog identifier safety, validated at the SHARED entry so
    # both implementations refuse identically: kebab-case names
    # sanitize to underscores ('a-b' -> 'a_b'), so two names may
    # collide after sanitization, and 'clk'/'rst' are the module's
    # own ports.
    sanitized = {}
    for name in sorted(specs):
        ident = name.replace('-', '_')
        if ident in RESERVED_IDENTS:
            raise ValueError(
                f"node name '{name}' collides with the reserved "
                f"Verilog port '{ident}' — rename the node")
        sanitized.setdefault(ident, []).append(name)
    collisions = {ident: names for ident, names in sanitized.items()
                  if len(names) > 1}
    if collisions:
        detail = '; '.join(f'{names} -> {ident}'
                           for ident, names in sorted(
                               collisions.items()))
        raise ValueError(
            f'node names collide after kebab-to-underscore '
            f'sanitization ({detail}) — rename one of each pair')
    return specs


def is_clocked(specs):
    return any(s['kind'] in CLOCKED_KINDS for s in specs.values())


def _topo_order(specs):
    """Combinational evaluation order; clocked outputs are state (no
    dependency edge), so only comb edges can cycle."""
    order, state = [], {}
    def visit(name):
        mark = state.get(name)
        if mark == 'done':
            return
        if mark == 'visiting':
            raise ValueError(
                f'combinational cycle through {name!r} — insert a '
                f'dff to break it')
        state[name] = 'visiting'
        spec = specs[name]
        if spec['kind'] not in CLOCKED_KINDS:
            for src in spec['inputs']:
                visit(src)
        state[name] = 'done'
        order.append(name)
    for name in sorted(specs):
        visit(name)
    return order


class LogicSimulator:
    """Evaluate a design: set_inputs -> settle() (combinational) or
    step() (one clock). Values are ints masked to node width."""

    def __init__(self, specs):
        self.specs = specs
        self.order = _topo_order(specs)
        self.state = {name: int(s['params'].get('init', 0))
                      & self._mask(s)
                      for name, s in specs.items()
                      if s['kind'] in CLOCKED_KINDS}
        self.inputs = {name: 0 for name, s in specs.items()
                       if s['kind'] == 'input'}
        self.values = {}
        self.settle()

    @staticmethod
    def _mask(spec):
        return (1 << spec['width']) - 1

    def set_inputs(self, values=None, **kw):
        """Accepts a positional dict (safe for arbitrary keys — no
        ** splat, so a key named 'self' cannot collide) and/or
        keyword form for the existing callers."""
        merged = dict(values or {})
        merged.update(kw)
        for name, value in merged.items():
            if name not in self.inputs:
                raise ValueError(f'{name!r} is not an input node')
            if not isinstance(value, int):
                raise ValueError(
                    f'input {name!r} must be an integer (bit '
                    f'pattern), got {type(value).__name__}')
            self.inputs[name] = value
        self.settle()

    def _eval(self, spec):
        kind, mask = spec['kind'], self._mask(spec)
        # Sourceless kinds first — a clocked node's inputs may sit
        # LATER in the topo order (state breaks the cycle), so its
        # inputs are read at step() time, never here.
        if kind == 'input':
            return self.inputs[spec['name']] & mask
        if kind == 'const':
            return int(spec['params'].get('value', 0)) & mask
        if kind in CLOCKED_KINDS:
            return self.state[spec['name']] & mask
        ins = [self.values[src] for src in spec['inputs']]
        if kind in ('output', 'buf'):
            return ins[0] & mask
        if kind == 'not':
            return (~ins[0]) & mask
        if kind == 'mux2':
            a, b, sel = ins
            return (b if sel & 1 else a) & mask
        acc = ins[0]
        for v in ins[1:]:
            acc = (acc & v if kind in ('and', 'nand')
                   else acc | v if kind in ('or', 'nor')
                   else acc ^ v)
        if kind in ('nand', 'nor'):
            acc = ~acc
        return acc & mask

    def settle(self):
        for name in self.order:
            self.values[name] = self._eval(self.specs[name])
        return dict(self.values)

    def step(self):
        """One clock edge: clocked nodes latch, then re-settle."""
        nxt = {}
        for name, spec in self.specs.items():
            if spec['kind'] == 'dff':
                nxt[name] = self.values[spec['inputs'][0]] \
                    & self._mask(spec)
            elif spec['kind'] == 'counter':
                enabled = (self.values[spec['inputs'][0]] & 1
                           if spec['inputs'] else 1)
                nxt[name] = ((self.state[name] + enabled)
                             & self._mask(spec))
        self.state.update(nxt)
        return self.settle()

    def outputs(self):
        return {name: self.values[name]
                for name, s in self.specs.items()
                if s['kind'] == 'output'}
