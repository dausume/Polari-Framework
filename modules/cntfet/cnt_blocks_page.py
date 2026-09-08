"""
@module cntfet.cnt_blocks_page

The FUNCTIONAL-BLOCK rung of the microchip ladder (chip_basis rank
3, "counter -> ALU -> FSM"): blocks composed ONLY from the existing
standard cells (cnt_cell_library.CELL_LIBRARY at drive x1 + the
hand cdff of cnt_cells), described as DATA the way `compose`
describes a cell from cells — one level up.

What a block gets here (nothing is simulated in SPICE at this rung):
  - a structural netlist (instances + nets), a gate-level Verilog
    netlist over the Liberty cell names and a .subckt over the cell
    subckts for a future SPICE run;
  - a functional PROOF: every instance evaluated with cnt_logic's
    boolean evaluator (cdff = Q <= D on the rising clock), exhaustive
    over every input vector x every state, against the block's
    golden model (function_json); mismatches listed, never hidden;
  - a bounded state space shaped like cnt_logic's sequential
    stateSpace so `cell-logic-diagram` renders it via its `path`
    override;
  - TIMING through OpenSTA over the Verilog + the device's OWN
    Liberty (cnt_cell_scoring._latest_library_row, plus the
    sequential DFFX1 Liberty when a characterize_sequential run
    exists) — refused BY NAME when a cell the block uses is not in
    the run (the missing Liberty cells are listed) or `sta` is absent;
  - a POWER roll-up: static = sum over instances of the state-
    dependent leakage (cnt_power.cell_leakage_states) at each block
    input vector; dynamic = sum of mid-grid arc energies x activity
    x f; the block-scope budget check (area unknown -> stated);
  - a PROVENANCE roll-up: the worst of the device's proof and every
    distinct cell's proof (cnt_evidence.freedom_proof), gaps unioned,
    in the freedom_proof payload shape.

@consumers
  - cntfet.cnt_api (routes /api/cntfet/blocks, /api/cntfet/block/
    {key}, /api/cntfet/block/{key}/proof, /api/cntfet/block/{key}/
    logic — to be wired)
  - cntfet.blocks_selftest
"""

import itertools
import json
import os
import random
import re
import tempfile

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_cell_library_basis import (
    CELL_LIBRARY, fet_count as _cell_fet_count, liberty_cell_name,
    library_subckts, subckt_name,
)
from cntfet.custom.cnt_logic import boolean_ast, evaluate

#: the hand-subckt DFF (cnt_cells) — Liberty DFFX1 pins D, CLK, Q;
#: subckt ports d clk q vddn.
DFF_CELL = 'cdff'
DFF_LIBERTY = 'DFFX1'
DFF_INPUTS = ['D', 'CLK']
DFF_OUTPUTS = ['Q']
DFF_FETS = 18
BLOCK_PAYLOAD_VERSION = 1

DISCLAIMER = ('functional-block rung: switch/gate-level proof over the '
              'cell boolean functions (no SPICE at this rung); timing = '
              'OpenSTA over OUR Liberty (intrinsic-grade, NOT signoff); '
              'power = a roll-up of cell tables, no wires, no area')


# ---------------------------------------------------------------
# 1. the block as a row
# ---------------------------------------------------------------

class FunctionalBlock(treeObject):
    """One functional block as DATA: ports, instances (cell + drive +
    pin->net map), nets, clock, the golden model, and the verdict /
    timing / power / provenance fields the reports fill."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        inputs_json: str = '[]',
        outputs_json: str = '[]',
        state_bits: int = 0,
        instances_json: str = '[]',
        nets_json: str = '[]',
        clock: str = '',
        function_json: str = '{}',
        cell_count: int = 0,
        fet_count: int = 0,
        proven: bool = False,
        proof_json: str = '{}',
        timing_json: str = '{}',
        power_json: str = '{}',
        provenance_json: str = '{}',
        status: str = 'composed',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.inputs_json = inputs_json
        self.outputs_json = outputs_json
        self.state_bits = state_bits
        self.instances_json = instances_json
        self.nets_json = nets_json
        self.clock = clock
        self.function_json = function_json
        self.cell_count = cell_count
        self.fet_count = fet_count
        self.proven = proven
        self.proof_json = proof_json
        self.timing_json = timing_json
        self.power_json = power_json
        self.provenance_json = provenance_json
        self.status = status
        self.notes = notes
        self.is_prior = is_prior


# ---------------------------------------------------------------
# 2. the block library (instances are real cells at x1)
# ---------------------------------------------------------------

def _inst(name, cell, **ports):
    return {'inst': name, 'cell': cell, 'drive': 1, 'ports': ports}


def _reg4():
    """4-bit register with enable: per bit MUX2(A=Q, B=D, S=EN) ->
    DFF. Q_i(next) = EN ? D_i : Q_i."""
    inst = []
    for i in range(4):
        inst.append(_inst(f'm{i}', 'cmux2', A=f'Q{i}', B=f'D{i}',
                          S='EN', Y=f'n{i}'))
        inst.append(_inst(f'ff{i}', DFF_CELL, D=f'n{i}', CLK='CLK',
                          Q=f'Q{i}'))
    return {
        'display_name': 'REG4 — 4-bit register with enable',
        'description': '4-bit enable register: DFF + MUX2 feedback per '
                       'bit (the register-file building block). '
                       'Q <= EN ? D : Q on the rising CLK.',
        'inputs': ['D0', 'D1', 'D2', 'D3', 'EN', 'CLK'],
        'outputs': ['Q0', 'Q1', 'Q2', 'Q3'],
        'state': ['Q0', 'Q1', 'Q2', 'Q3'],
        'clock': 'CLK',
        'instances': inst,
        'function': {'kind': 'reg4', 'width': 4,
                     'next_state': 'EN ? D : Q', 'outputs': 'Q'},
    }


def _ctr4():
    """4-bit synchronous binary counter with enable + synchronous
    reset. Toggle chain from half adders: t0 = EN; HA_i(Q_i, t_i) ->
    S = Q_i ^ t_i, CO = t_{i+1}; d_i = AND2(S_i, !RST); TC = CO of
    the last HA (= EN & Q == 15)."""
    inst = [_inst('rinv', 'cinv', A='RST', Y='rstb')]
    for i in range(4):
        t_in = 'EN' if i == 0 else f't{i}'
        inst.append(_inst(f'ha{i}', 'cha', A=f'Q{i}', B=t_in,
                          S=f's{i}', CO=f't{i + 1}' if i < 3 else 'TC'))
        inst.append(_inst(f'a{i}', 'cand2', A=f's{i}', B='rstb',
                          Y=f'd{i}'))
        inst.append(_inst(f'ff{i}', DFF_CELL, D=f'd{i}', CLK='CLK',
                          Q=f'Q{i}'))
    return {
        'display_name': 'CTR4 — 4-bit synchronous counter (EN, RST)',
        'description': '4-bit synchronous binary counter: half-adder '
                       'toggle chain (S = Q ^ carry, CO = next carry), '
                       'synchronous reset via AND2 with !RST, 4 DFFs. '
                       'TC = terminal count (EN & Q == 15).',
        'inputs': ['EN', 'RST', 'CLK'],
        'outputs': ['Q0', 'Q1', 'Q2', 'Q3', 'TC'],
        'state': ['Q0', 'Q1', 'Q2', 'Q3'],
        'clock': 'CLK',
        'instances': inst,
        'function': {'kind': 'ctr4', 'width': 4,
                     'next_state': 'RST ? 0 : (Q + EN) mod 16',
                     'outputs': {'Q': 'state', 'TC': 'EN & Q == 15'}},
    }


def _fsm_traffic():
    """Moore FSM, 3 states: GREEN(00) -X=1-> YELLOW(01) -> RED(10)
    -X=1-> GREEN; X=0 holds GREEN / RED. Unused 11 -> GREEN (stated
    in the golden model). Outputs G, Y, R one-hot from the state."""
    inst = [
        _inst('i1', 'cinv', A='S1', Y='s1b'),
        _inst('i0', 'cinv', A='S0', Y='s0b'),
        _inst('ix', 'cinv', A='X', Y='xb'),
        _inst('g', 'cand2', A='s1b', B='s0b', Y='G'),
        _inst('y', 'cand2', A='s1b', B='S0', Y='Y'),
        _inst('r', 'cand2', A='S1', B='s0b', Y='R'),
        # s0' = GREEN & X ; s1' = YELLOW + (RED & !X)
        _inst('n0', 'cand2', A='G', B='X', Y='d0'),
        _inst('rh', 'cand2', A='R', B='xb', Y='rhold'),
        _inst('n1', 'cor2', A='Y', B='rhold', Y='d1'),
        _inst('ff0', DFF_CELL, D='d0', CLK='CLK', Q='S0'),
        _inst('ff1', DFF_CELL, D='d1', CLK='CLK', Q='S1'),
    ]
    return {
        'display_name': 'FSM-TRAFFIC — 3-state Moore traffic light',
        'description': 'Moore FSM: GREEN -(X)-> YELLOW -> RED -(X)-> '
                       'GREEN; X=0 holds GREEN/RED. State bits S1 S0 '
                       '(00 GREEN, 01 YELLOW, 10 RED, 11 unused -> '
                       'GREEN); outputs G/Y/R one-hot from the state.',
        'inputs': ['X', 'CLK'],
        'outputs': ['G', 'Y', 'R'],
        'state': ['S1', 'S0'],
        'clock': 'CLK',
        'instances': inst,
        'function': {
            'kind': 'fsm', 'state_bits': ['S1', 'S0'],
            'states': {'GREEN': [0, 0], 'YELLOW': [0, 1], 'RED': [1, 0],
                       'UNUSED': [1, 1]},
            'reset_state': 'GREEN',
            'transitions': {'GREEN': {'0': 'GREEN', '1': 'YELLOW'},
                            'YELLOW': {'0': 'RED', '1': 'RED'},
                            'RED': {'0': 'RED', '1': 'GREEN'},
                            'UNUSED': {'0': 'GREEN', '1': 'GREEN'}},
            'outputs': {'GREEN': {'G': 1, 'Y': 0, 'R': 0},
                        'YELLOW': {'G': 0, 'Y': 1, 'R': 0},
                        'RED': {'G': 0, 'Y': 0, 'R': 1},
                        'UNUSED': {'G': 0, 'Y': 0, 'R': 0}},
            'input': 'X',
        },
    }


def _alu4():
    """4-bit ALU. OP2 = arithmetic (OP0 = subtract: B ^ OP0, carry-in
    OP0), else logic by OP1:OP0 = AND / OR / XOR / NOT A. Ripple
    carry through 4 FAs; Y = MUX2(logic, arith, OP2); logic =
    MUX4(AND, OR, XOR, NOTA; S0 = OP0, S1 = OP1); CO = FA3 carry;
    Z = NOR4(Y)."""
    inst = []
    for i in range(4):
        inst.append(_inst(f'bx{i}', 'cxor2', A=f'B{i}', B='OP0',
                          Y=f'bs{i}'))
        inst.append(_inst(f'fa{i}', 'cfa', A=f'A{i}', B=f'bs{i}',
                          CI='OP0' if i == 0 else f'c{i}',
                          S=f'sum{i}', CO=f'c{i + 1}'))
        inst.append(_inst(f'and{i}', 'cand2', A=f'A{i}', B=f'B{i}',
                          Y=f'an{i}'))
        inst.append(_inst(f'or{i}', 'cor2', A=f'A{i}', B=f'B{i}',
                          Y=f'o{i}'))
        inst.append(_inst(f'xor{i}', 'cxor2', A=f'A{i}', B=f'B{i}',
                          Y=f'x{i}'))
        inst.append(_inst(f'not{i}', 'cinv', A=f'A{i}', Y=f'na{i}'))
        inst.append(_inst(f'lm{i}', 'cmux4', A=f'an{i}', B=f'o{i}',
                          C=f'x{i}', D=f'na{i}', S0='OP0', S1='OP1',
                          Y=f'lg{i}'))
        inst.append(_inst(f'ym{i}', 'cmux2', A=f'lg{i}', B=f'sum{i}',
                          S='OP2', Y=f'Y{i}'))
    # CO is an ARITHMETIC flag: gate the ripple carry with OP2 so the
    # logic ops (whose adder still sees carry-in = OP0) report CO = 0.
    inst.append(_inst('cog', 'cand2', A='c4', B='OP2', Y='CO'))
    inst.append(_inst('zf', 'cnor4', A='Y0', B='Y1', C='Y2', D='Y3',
                      Y='Z'))
    return {
        'display_name': 'ALU4 — 4-bit ALU (add/sub/and/or/xor/not)',
        'description': '4-bit ALU: ripple-carry add via 4 full adders, '
                       'subtract via XOR-conditioned B + carry-in, '
                       'bitwise AND/OR/XOR/NOT via cells, op select '
                       'MUX4 (logic op) + MUX2 (logic vs arithmetic); '
                       'outputs Y[3:0], carry-out CO (gated by OP2: 0 '
                       'on logic ops), zero flag Z '
                       '(NOR4). OP: 100 ADD, 101 SUB, 000 AND, 001 OR, '
                       '010 XOR, 011 NOT A (110/111 = ADD/SUB again).',
        'inputs': ['A0', 'A1', 'A2', 'A3', 'B0', 'B1', 'B2', 'B3',
                   'OP0', 'OP1', 'OP2'],
        'outputs': ['Y0', 'Y1', 'Y2', 'Y3', 'CO', 'Z'],
        'state': [],
        'clock': '',
        'instances': inst,
        'function': {
            'kind': 'alu4', 'width': 4,
            'ops': {'100': 'ADD', '101': 'SUB', '110': 'ADD',
                    '111': 'SUB', '000': 'AND', '001': 'OR',
                    '010': 'XOR', '011': 'NOTA'},
            'op_bits': ['OP2', 'OP1', 'OP0'],
            'arith': 'A + (B ^ sub) + sub, sub = OP0; CO = bit 4',
            'flags': {'Z': 'Y == 0'},
        },
    }


BLOCK_LIBRARY = {
    'reg4': _reg4(),
    'ctr4': _ctr4(),
    'alu4': _alu4(),
    'fsm-traffic': _fsm_traffic(),
}


def _cell_pins(cell_key):
    if cell_key == DFF_CELL:
        return list(DFF_INPUTS), list(DFF_OUTPUTS)
    cell = CELL_LIBRARY[cell_key]
    return list(cell['inputs']), list(cell['outputs'])


def block_fet_count(block_key):
    return sum(DFF_FETS if i['cell'] == DFF_CELL
               else _cell_fet_count(i['cell'], i['drive'])
               for i in BLOCK_LIBRARY[block_key]['instances'])


def block_cells(block_key):
    """{cell: instance count}, sorted."""
    counts = {}
    for i in BLOCK_LIBRARY[block_key]['instances']:
        counts[i['cell']] = counts.get(i['cell'], 0) + 1
    return dict(sorted(counts.items()))


def liberty_names_for(block_key):
    return sorted({DFF_LIBERTY if i['cell'] == DFF_CELL
                   else liberty_cell_name(i['cell'], i['drive'])
                   for i in BLOCK_LIBRARY[block_key]['instances']})


def generate(block_key):
    """The structural netlist: instances (each with the cell's pin ->
    net map) + nets classified input | output | state | internal |
    clock, with the driver / load bookkeeping and the consistency
    findings (undriven input pins, nets driven twice, unused
    outputs)."""
    if block_key not in BLOCK_LIBRARY:
        raise KeyError(block_key)
    blk = BLOCK_LIBRARY[block_key]
    drivers, loads, problems = {}, {}, []
    for i in blk['instances']:
        if i['cell'] != DFF_CELL and i['cell'] not in CELL_LIBRARY:
            problems.append(f'{i["inst"]}: unknown cell {i["cell"]}')
            continue
        ins, outs = _cell_pins(i['cell'])
        for pin in ins + outs:
            if pin not in i['ports']:
                problems.append(f'{i["inst"]} ({i["cell"]}): pin '
                                f'{pin} unconnected')
        for pin in ins:
            net = i['ports'].get(pin)
            if net:
                loads.setdefault(net, []).append(f'{i["inst"]}.{pin}')
        for pin in outs:
            net = i['ports'].get(pin)
            if net:
                drivers.setdefault(net, []).append(f'{i["inst"]}.{pin}')
    for p in blk['inputs']:
        drivers.setdefault(p, []).append('port')
    nets = []
    for net in sorted(set(drivers) | set(loads)):
        if net == blk['clock']:
            kind = 'clock'
        elif net in blk['inputs']:
            kind = 'input'
        elif net in blk['outputs']:
            kind = 'output'
        elif net in blk['state']:
            kind = 'state'
        else:
            kind = 'internal'
        d, l = drivers.get(net, []), loads.get(net, [])
        if not d:
            problems.append(f'net {net} has no driver (loads {l})')
        if len(d) > 1:
            problems.append(f'net {net} driven twice: {d}')
        if not l and kind == 'internal':
            problems.append(f'internal net {net} has no load')
        nets.append({'net': net, 'kind': kind, 'drivers': d, 'loads': l})
    for p in blk['outputs']:
        if not drivers.get(p) or drivers[p] == ['port']:
            problems.append(f'output {p} undriven')
    return {'block': block_key, 'inputs': list(blk['inputs']),
            'outputs': list(blk['outputs']), 'state': list(blk['state']),
            'clock': blk['clock'],
            'instances': [dict(i, ports=dict(i['ports']))
                          for i in blk['instances']],
            'nets': nets, 'cells': block_cells(block_key),
            'cellCount': len(blk['instances']),
            'fetCount': block_fet_count(block_key),
            'consistent': not problems, 'problems': problems}


def _vname(net):
    return re.sub(r'[^A-Za-z0-9_]', '_', net)


def verilog_netlist(block_key, liberty_names=True):
    """Gate-level Verilog: cells instantiated by Liberty name
    (`NAND2X1 U3 (.A(n1), .B(n2), .Y(n3));`), pin names from
    CELL_LIBRARY (cdff -> DFFX1 .D .CLK .Q)."""
    blk = BLOCK_LIBRARY[block_key]
    g = generate(block_key)
    mod = _vname(block_key)
    ports = blk['inputs'] + blk['outputs']
    lines = [f'// {blk["display_name"]} — generated by '
             f'cntfet.cnt_blocks_page (cells at x1)',
             f'module {mod} ({", ".join(_vname(p) for p in ports)});',
             '  input ' + ', '.join(_vname(p) for p in blk['inputs'])
             + ';',
             '  output ' + ', '.join(_vname(p) for p in blk['outputs'])
             + ';']
    wires = [n['net'] for n in g['nets'] if n['kind'] in ('internal',
                                                            'state')
             and n['net'] not in ports]
    if wires:
        lines.append('  wire ' + ', '.join(_vname(w) for w in wires)
                     + ';')
    for idx, i in enumerate(blk['instances']):
        if i['cell'] == DFF_CELL:
            cname = DFF_LIBERTY if liberty_names else DFF_CELL
        else:
            cname = liberty_cell_name(i['cell'], i['drive']) \
                if liberty_names else subckt_name(i['cell'], i['drive'])
        ins, outs = _cell_pins(i['cell'])
        conns = ', '.join(f'.{pin}({_vname(i["ports"][pin])})'
                          for pin in ins + outs)
        lines.append(f'  {cname} U{idx}_{_vname(i["inst"])} ({conns});')
    lines.append('endmodule')
    return '\n'.join(lines) + '\n'


def spice_netlist(block_key):
    """A .subckt over the cell subckts (X instances) — the cell
    subckts it needs are prepended (cdff from cnt_cells._SUBCKTS
    when used) so the text is a self-contained include for a future
    transient run."""
    from cntfet.custom.cnt_cells import _SUBCKTS
    blk = BLOCK_LIBRARY[block_key]
    cells = [c for c in block_cells(block_key) if c != DFF_CELL]
    parts = ['* ' + blk['display_name'] + ' — cntfet.cnt_blocks_page',
             library_subckts(cells, drives=(1,))]
    if DFF_CELL in block_cells(block_key):
        parts.append(_SUBCKTS)
    name = _vname(block_key)
    ports = ' '.join(blk['inputs'] + blk['outputs'])
    lines = [f'.subckt {name} {ports} vddn']
    for i in blk['instances']:
        ins, outs = _cell_pins(i['cell'])
        nets = ' '.join(i['ports'][p] for p in ins + outs)
        sub = DFF_CELL if i['cell'] == DFF_CELL \
            else subckt_name(i['cell'], i['drive'])
        lines.append(f'X{i["inst"]} {nets} vddn {sub}')
    lines.append(f'.ends {name}')
    parts.append('\n'.join(lines))
    return '\n'.join(parts) + '\n'


# ---------------------------------------------------------------
# 3. evaluation + proof
# ---------------------------------------------------------------

_AST_CACHE = {}


def _asts(cell_key):
    if cell_key not in _AST_CACHE:
        cell = CELL_LIBRARY[cell_key]
        _AST_CACHE[cell_key] = {
            o: boolean_ast(cell['liberty_functions'][o])
            for o in cell['outputs']}
    return _AST_CACHE[cell_key]


def _order(block_key):
    """Topological order of the combinational instances (DFF Q nets
    are known from the state). Raises on a combinational loop."""
    blk = BLOCK_LIBRARY[block_key]
    known = set(blk['inputs']) | set(blk['state'])
    pending = [i for i in blk['instances'] if i['cell'] != DFF_CELL]
    order = []
    while pending:
        progressed = False
        for i in list(pending):
            ins, outs = _cell_pins(i['cell'])
            if all(i['ports'][p] in known for p in ins):
                order.append(i)
                known.update(i['ports'][p] for p in outs)
                pending.remove(i)
                progressed = True
        if not progressed:
            raise ValueError(f'{block_key}: combinational loop through '
                             f'{[i["inst"] for i in pending]}')
    return order


def evaluate_block(block_key, inputs, state=None):
    """{outputs, next_state, nets, instances: {inst: {inputs, outputs}}}
    — combinational cells via their boolean functions (cnt_logic),
    cdff registered: next Q = D at the rising CLK."""
    blk = BLOCK_LIBRARY[block_key]
    nets = {}
    for p in blk['inputs']:
        nets[p] = int(bool(inputs[p]))
    state = state or {}
    for s in blk['state']:
        nets[s] = int(bool(state.get(s, 0)))
    per_inst = {}
    for i in _order(block_key):
        ins, outs = _cell_pins(i['cell'])
        assignment = {p: nets[i['ports'][p]] for p in ins}
        outv = {o: evaluate(ast, assignment)
                for o, ast in _asts(i['cell']).items()}
        for o in outs:
            nets[i['ports'][o]] = outv[o]
        per_inst[i['inst']] = {'cell': i['cell'], 'inputs': assignment,
                               'outputs': outv}
    next_state = {}
    for i in blk['instances']:
        if i['cell'] == DFF_CELL:
            d = nets[i['ports']['D']]
            next_state[i['ports']['Q']] = d
            per_inst[i['inst']] = {'cell': DFF_CELL,
                                   'inputs': {'D': d,
                                              'CLK': nets[blk['clock']]},
                                   'outputs': {'Q': nets[i['ports']['Q']]},
                                   'next': {'Q': d}}
    return {'outputs': {o: nets[o] for o in blk['outputs']},
            'next_state': next_state, 'nets': nets,
            'instances': per_inst}


def _bits_to_int(vec, names):
    """names LSB first."""
    return sum(int(vec[n]) << k for k, n in enumerate(names))


def _int_to_bits(value, names):
    return {n: (value >> k) & 1 for k, n in enumerate(names)}


def golden(block_key, inputs, state=None):
    """The golden model from function_json: (outputs, next_state)."""
    fn = BLOCK_LIBRARY[block_key]['function']
    state = state or {}
    kind = fn['kind']
    if kind == 'reg4':
        q = [f'Q{i}' for i in range(4)]
        nxt = {f'Q{i}': (int(inputs[f'D{i}']) if inputs['EN']
                         else int(state.get(f'Q{i}', 0)))
               for i in range(4)}
        return {k: int(state.get(k, 0)) for k in q}, nxt
    if kind == 'ctr4':
        q = [f'Q{i}' for i in range(4)]
        cur = _bits_to_int(state or {k: 0 for k in q}, q)
        nxt_val = 0 if inputs['RST'] else (cur + int(inputs['EN'])) % 16
        outs = {k: int(state.get(k, 0)) for k in q}
        outs['TC'] = int(bool(inputs['EN']) and cur == 15)
        return outs, _int_to_bits(nxt_val, q)
    if kind == 'fsm':
        bits = fn['state_bits']
        cur = [int(state.get(b, 0)) for b in bits]
        name = next(n for n, v in fn['states'].items() if v == cur)
        to = fn['transitions'][name][str(int(inputs[fn['input']]))]
        nxt = dict(zip(bits, fn['states'][to]))
        return dict(fn['outputs'][name]), nxt
    if kind == 'alu4':
        w = fn['width']
        a = _bits_to_int(inputs, [f'A{i}' for i in range(w)])
        b = _bits_to_int(inputs, [f'B{i}' for i in range(w)])
        code = ''.join(str(int(inputs[o])) for o in fn['op_bits'])
        op = fn['ops'][code]
        co = 0
        if op in ('ADD', 'SUB'):
            sub = 1 if op == 'SUB' else 0
            total = a + ((b ^ (2 ** w - 1)) if sub else b) + sub
            y, co = total % (2 ** w), total >> w
        elif op == 'AND':
            y = a & b
        elif op == 'OR':
            y = a | b
        elif op == 'XOR':
            y = a ^ b
        else:  # NOTA
            y = (~a) & (2 ** w - 1)
        outs = _int_to_bits(y, [f'Y{i}' for i in range(w)])
        outs['CO'] = co
        outs['Z'] = int(y == 0)
        return outs, {}
    raise ValueError(f'unknown golden kind {kind}')


def _vectors(names):
    for bits in itertools.product((0, 1), repeat=len(names)):
        yield dict(zip(names, bits))


def prove_block(block_key, max_mismatches=20):
    """Exhaustive: every input vector x every state (the clock input
    is held at 1 = the rising edge has happened; the cells see it
    only through the DFFs) against the golden model."""
    blk = BLOCK_LIBRARY[block_key]
    free = [p for p in blk['inputs'] if p != blk['clock']]
    states = list(_vectors(blk['state'])) if blk['state'] else [{}]
    mismatches, n = [], 0
    try:
        _order(block_key)
    except ValueError as exc:
        return {'block': block_key, 'proven': False, 'vectors': 0,
                'states': len(states), 'mismatches': [],
                'note': str(exc)}
    for st in states:
        for v in _vectors(free):
            inputs = dict(v)
            if blk['clock']:
                inputs[blk['clock']] = 1
            got = evaluate_block(block_key, inputs, st)
            exp_out, exp_next = golden(block_key, inputs, st)
            n += 1
            bad_out = {k: (exp_out[k], got['outputs'][k])
                       for k in exp_out if exp_out[k] != got['outputs'][k]}
            bad_next = {k: (exp_next[k], got['next_state'].get(k))
                        for k in exp_next
                        if exp_next[k] != got['next_state'].get(k)}
            if bad_out or bad_next:
                if len(mismatches) < max_mismatches:
                    mismatches.append({'inputs': v, 'state': st,
                                       'outputs': bad_out,
                                       'next_state': bad_next})
    proven = n > 0 and not mismatches
    return {'block': block_key, 'proven': proven, 'vectors': n,
            'inputVectors': 2 ** len(free), 'states': len(states),
            'freeInputs': free, 'mismatches': mismatches,
            'golden': blk['function'],
            'note': ('PROVEN: every instance evaluated through its '
                     'cell boolean function (cnt_logic), cdff = Q <= D '
                     'on the rising CLK; exhaustive over input x state'
                     if proven else
                     f'{len(mismatches)}+ mismatches vs the golden model')}


def state_space(block_key):
    """Bounded state graph shaped like cnt_logic's sequential
    stateSpace ({kind:'sequential', states, transitions:[{from, input,
    to, kind}], description}) — ctr4: the 16-ring + reset edges;
    fsm-traffic: the 3-state graph (+ the unused code's recovery);
    reg4: hold / load per state (inputs D collapsed to 'D=n')."""
    blk = BLOCK_LIBRARY[block_key]
    if not blk['state']:
        return {'kind': 'combinational', 'inputs': list(blk['inputs']),
                'outputs': list(blk['outputs']), 'count': 0,
                'description': 'combinational block — no state; see '
                               'the proof for the exhaustive vectors'}
    fn = blk['function']
    transitions, states = [], []

    def label(st):
        if fn['kind'] == 'fsm':
            bits = [st[b] for b in fn['state_bits']]
            return next(n for n, v in fn['states'].items()
                        if v == bits)
        return f'Q={_bits_to_int(st, blk["state"])}'

    for st in _vectors(blk['state']):
        states.append(label(st))
    if fn['kind'] == 'ctr4':
        for st in _vectors(blk['state']):
            for en, rst in ((1, 0), (0, 0), (1, 1)):
                inputs = {'EN': en, 'RST': rst, 'CLK': 1}
                r = evaluate_block(block_key, inputs, st)
                to = label(r['next_state'])
                kind = 'reset' if rst else ('count' if en else 'hold')
                transitions.append({'from': label(st),
                                    'input': {'EN': en, 'RST': rst,
                                              'CLK': 'rising'},
                                    'to': to, 'kind': kind,
                                    'output': r['outputs']})
        desc = ('16-state ring (EN=1 counts up, 15 -> 0), self loops '
                'while EN=0, every state -> Q=0 on RST=1 (synchronous)')
    elif fn['kind'] == 'fsm':
        for st in _vectors(blk['state']):
            for x in (0, 1):
                r = evaluate_block(block_key, {'X': x, 'CLK': 1}, st)
                to = label(r['next_state'])
                transitions.append({'from': label(st),
                                    'input': {'X': x, 'CLK': 'rising'},
                                    'to': to,
                                    'kind': 'hold' if to == label(st)
                                    else 'advance',
                                    'output': r['outputs']})
        desc = ('Moore traffic light: GREEN -(X=1)-> YELLOW -> RED '
                '-(X=1)-> GREEN; X=0 holds GREEN / RED; the unused '
                'code 11 recovers to GREEN')
    else:  # reg4
        for st in _vectors(blk['state']):
            cur = _bits_to_int(st, blk['state'])
            for en, dval in ((0, None), (1, (cur + 5) % 16), (1, cur)):
                d = _int_to_bits(dval if dval is not None else 0,
                                 [f'D{i}' for i in range(4)])
                r = evaluate_block(block_key, {**d, 'EN': en, 'CLK': 1},
                                   st)
                to = label(r['next_state'])
                transitions.append({'from': label(st),
                                    'input': {'EN': en,
                                              'D': dval if en else 'x',
                                              'CLK': 'rising'},
                                    'to': to,
                                    'kind': 'hold' if not en
                                    else ('load' if to != label(st)
                                          else 'retain')})
        desc = ('enable register: EN=0 holds every state; EN=1 loads '
                'D (shown: one load edge per state, D = Q+5 mod 16, '
                'plus the retain edge D = Q)')
    return {'kind': 'sequential', 'block': block_key,
            'states': states, 'transitions': transitions,
            'stateBits': list(blk['state']),
            'phases': [], 'latches': [], 'instances': [],
            'description': desc,
            'source': 'cnt_blocks.evaluate_block over the cell boolean '
                      'functions — bounded enumeration, not simulated'}


def block_logic(block_key):
    """The cell-logic-diagram payload for a block (the component's
    `path` override): inputs / outputs / stateSpace / proof."""
    if block_key not in BLOCK_LIBRARY:
        return _refusal(block_key)
    blk = BLOCK_LIBRARY[block_key]
    proof = prove_block(block_key)
    return {'ok': True, 'cell': block_key, 'block': block_key,
            'drive': 1, 'function': blk['display_name'],
            'inputs': list(blk['inputs']), 'output': blk['outputs'][0],
            'outputs': list(blk['outputs']),
            'ast': None, 'asts': None, 'gateDag': None,
            'truthTable': None, 'netlist': None,
            'proof': proof, 'stateSpace': state_space(block_key),
            'fetCount': block_fet_count(block_key),
            'sequential': bool(blk['state']),
            'honesty': DISCLAIMER,
            'payloadVersion': BLOCK_PAYLOAD_VERSION}


# ---------------------------------------------------------------
# 4. timing (OpenSTA)
# ---------------------------------------------------------------

def _liberty_sources(manager, device_name):
    """[(fileName, text, cellNames)] — the latest library run + the
    latest sequential (DFFX1) run when one exists."""
    from cntfet.cnt_cell_scoring_seed import _latest_library_row, parse_liberty
    out = []
    row = _latest_library_row(manager, device_name)
    if row is not None:
        out.append(('polari_cnt_lib.lib', row.liberty_text,
                    sorted(parse_liberty(row.liberty_text)['cells']),
                    row.name))
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        'CellCharacterizationRun') or {}
    seq = [r for r in (table.values() if isinstance(table, dict)
                       else table)
           if getattr(r, 'device', '') == device_name
           and getattr(r, 'cell', '') == DFF_LIBERTY
           and getattr(r, 'liberty_text', '')]
    if seq:
        r = max(seq, key=lambda r: getattr(r, 'ran_at', ''))
        out.append(('polari_cnt_seq.lib', r.liberty_text, [DFF_LIBERTY],
                    r.name))
    return out


_ARRIVAL = re.compile(r'^\s*(-?[0-9.]+)\s+data arrival time', re.M)
_SLACK = re.compile(r'^\s*(-?[0-9.]+)\s+slack \((MET|VIOLATED)\)', re.M)
_START = re.compile(r'^Startpoint: (\S+)', re.M)
_END = re.compile(r'^Endpoint: (\S+)', re.M)


def _parse_path(section):
    a, s = _ARRIVAL.search(section), _SLACK.search(section)
    st, en = _START.search(section), _END.search(section)
    if not (a and s):
        return None
    return {'start': st.group(1) if st else None,
            'end': en.group(1) if en else None,
            'arrival_ps': float(a.group(1)),
            'slack_ps': float(s.group(1)), 'met': s.group(2) == 'MET'}


def block_timing(manager, device_name, block_key, workdir=None,
                 clock_period_s=None):
    """OpenSTA over the gate-level Verilog + the device's own Liberty:
    critical path (start, end, arrival, slack), max-frequency
    estimate, hold worst; refuses BY NAME without a run, with the
    missing Liberty cells listed, or without `sta`."""
    from cntfet.cnt_characterization_basis import find_sta, run_sta
    if block_key not in BLOCK_LIBRARY:
        return _refusal(block_key)
    blk = BLOCK_LIBRARY[block_key]
    needed = liberty_names_for(block_key)
    libs = _liberty_sources(manager, device_name)
    if not libs:
        return {'ok': False, 'block': block_key, 'device': device_name,
                'refusal': f'no cell-library characterization run for '
                           f'"{device_name}" — POST {{"action": '
                           f'"characterize-cells"}} to /api/cntfet/'
                           f'devices/{device_name} first',
                'missingCells': needed}
    have = sorted({c for _f, _t, cells, _n in libs for c in cells})
    missing = [c for c in needed if c not in have]
    if missing:
        hint = ''
        if DFF_LIBERTY in missing:
            hint = (' — DFFX1 timing = {"action": '
                    '"characterize-sequential"} (cnt_sequential)')
        return {'ok': False, 'block': block_key, 'device': device_name,
                'refusal': f'the Liberty of "{device_name}" lacks '
                           f'{missing} which {block_key} uses{hint}',
                'missingCells': missing, 'availableCells': have,
                'runs': [n for _f, _t, _c, n in libs]}
    sta, where = find_sta()
    if not sta:
        return {'ok': False, 'block': block_key, 'device': device_name,
                'refusal': f'{where} — block timing needs OpenSTA',
                'sta': {'ran': False, 'refusal': where}}
    workdir = workdir or tempfile.mkdtemp(prefix=f'cnt-block-{block_key}-')
    os.makedirs(workdir, exist_ok=True)
    mod = _vname(block_key)
    vfile = f'{mod}.v'
    with open(os.path.join(workdir, vfile), 'w') as fh:
        fh.write(verilog_netlist(block_key))
    for fname, text, _c, _n in libs:
        with open(os.path.join(workdir, fname), 'w') as fh:
            fh.write(text)
    period_ps = (clock_period_s or 1e-9) * 1e12
    script = ''.join(f'read_liberty {f}\n' for f, _t, _c, _n in libs)
    script += f'read_verilog {vfile}\nlink_design {mod}\n'
    if blk['clock']:
        clk = _vname(blk['clock'])
        script += (f'create_clock -name clk -period {period_ps:g} '
                   f'[get_ports {clk}]\n'
                   f'set_input_delay 0 -clock clk '
                   f'[delete_from_list [all_inputs] [get_ports {clk}]]\n')
    else:
        script += (f'create_clock -name clk -period {period_ps:g}\n'
                   'set_input_delay 0 -clock clk [all_inputs]\n')
    script += ('set_output_delay 0 -clock clk [all_outputs]\n'
               'puts "=== MAX ==="\n'
               'report_checks -path_delay max -digits 3\n'
               'puts "=== MIN ==="\n'
               'report_checks -path_delay min -digits 3\n'
               'puts "=== WNS ==="\nreport_wns\n'
               'puts "=== TNS ==="\nreport_tns\n'
               'exit\n')
    run = run_sta(sta, workdir, script,
                  files=tuple([f for f, _t, _c, _n in libs] + [vfile]),
                  timeout=300)
    out = run.stdout or ''
    ok = run.returncode == 0 and '=== MAX ===' in out
    sections = re.split(r'=== (MAX|MIN|WNS|TNS) ===', out)
    parts = {sections[i]: sections[i + 1]
             for i in range(1, len(sections) - 1, 2)}
    max_path = _parse_path(parts.get('MAX', ''))
    min_path = _parse_path(parts.get('MIN', ''))
    wns = re.search(r'wns\s+(?:max\s+)?(-?[0-9.]+)', parts.get('WNS', ''))
    tns = re.search(r'tns\s+(?:max\s+)?(-?[0-9.]+)', parts.get('TNS', ''))
    fmax = None
    if max_path:
        # the path's own delay budget = period - slack
        used = period_ps - max_path['slack_ps']
        fmax = 1e12 / used if used > 0 else None
    accepted = ok and max_path is not None
    return {
        'ok': accepted, 'block': block_key, 'device': device_name,
        'refusal': None if accepted else
        f'OpenSTA did not report a path — {(out[-400:] + (run.stderr or "")[-300:])}',
        'clock': blk['clock'] or 'virtual',
        'clockPeriod_ps': period_ps,
        'criticalPath': max_path, 'holdWorst': min_path,
        'wns_ps': float(wns.group(1)) if wns else None,
        'tns_ps': float(tns.group(1)) if tns else None,
        'fmax_hz': fmax,
        'libertyCells': needed, 'runs': [n for _f, _t, _c, n in libs],
        'sta': {'ran': True, 'accepted': accepted, 'where': where,
                'output': out[-1200:] if not accepted else
                parts.get('MAX', '')[-1200:]},
        'workdir': workdir, 'verilog': vfile,
        'honesty': 'OpenSTA over OUR Liberty (intrinsic-grade NLDM, '
                   'no wire load, no derates) — NOT signoff',
    }


# ---------------------------------------------------------------
# 5. power roll-up
# ---------------------------------------------------------------

def _sample_vectors(block_key, limit=64, seed=1):
    blk = BLOCK_LIBRARY[block_key]
    free = [p for p in blk['inputs'] if p != blk['clock']]
    n_total = 2 ** (len(free) + len(blk['state']))
    if n_total <= limit:
        vecs = [(dict(v), dict(s)) for s in (list(_vectors(blk['state']))
                                              if blk['state'] else [{}])
                for v in _vectors(free)]
        return vecs, n_total, True
    rng = random.Random(seed)
    vecs = []
    for _ in range(limit):
        vecs.append(({p: rng.randint(0, 1) for p in free},
                     {s: rng.randint(0, 1) for s in blk['state']}))
    return vecs, n_total, False


def block_power(manager, device_name, block_key, activity=0.1, f_hz=1e9,
                knobs=None):
    """static: per input vector every instance's state-dependent
    leakage summed (mean/max over the vectors, count stated);
    dynamic: sum over instances of the mid-grid arc energy x activity
    x f (refused by name without a library run; instances without an
    energy table listed)."""
    from cntfet.cnt_device_viz_seed import device_model
    from cntfet.cnt_power_basis import (
        POWER_KNOBS, _dynamic_from_library, _twin_ioffs,
        cell_leakage_states, check_budget, SEED_POWER_BUDGETS,
    )
    from cntfet.cnt_cell_scoring_seed import _latest_library_row, parse_liberty
    if block_key not in BLOCK_LIBRARY:
        return _refusal(block_key)
    blk = BLOCK_LIBRARY[block_key]
    k = dict(POWER_KNOBS)
    k.update(knobs or {})
    k['activity'], k['f_hz'] = activity, f_hz
    id_fn, p, device, refusal = device_model(manager, device_name)
    if refusal is not None:
        return {**refusal, 'block': block_key}
    vdd = k['vdd_v']
    ioff_n, ioff_p = _twin_ioffs(id_fn, p, vdd)
    # per cell: {when -> W}; cdff = 18 FETs — its state leakage is
    # not a library table: approximate as 9 off devices x Ioff
    # (one per complementary pair), stated.
    tables = {}
    for cell in block_cells(block_key):
        if cell == DFF_CELL:
            continue
        rep = cell_leakage_states(cell, 1, ioff_n, ioff_p, k)
        tables[cell] = {s['when']: s['p_static_w'] for s in rep['states']}
    dff_static = vdd * 0.5 * (ioff_n + ioff_p) * (DFF_FETS // 2)
    vecs, n_total, exhaustive = _sample_vectors(block_key)
    per_vec, per_inst_mean = [], {}
    for v, st in vecs:
        inputs = dict(v)
        if blk['clock']:
            inputs[blk['clock']] = 1
        r = evaluate_block(block_key, inputs, st)
        total = 0.0
        for inst, info in r['instances'].items():
            if info['cell'] == DFF_CELL:
                w = dff_static
            else:
                order = CELL_LIBRARY[info['cell']]['inputs']
                when = '*'.join(('' if info['inputs'][i] else '!') + i
                                for i in order)
                w = tables[info['cell']][when]
            total += w
            per_inst_mean[inst] = per_inst_mean.get(inst, 0.0) + w
        per_vec.append(total)
    n = len(per_vec)
    static_mean = sum(per_vec) / n
    static_max = max(per_vec)
    # dynamic
    row = _latest_library_row(manager, device_name)
    dynamic, dyn_refusal, missing_energy = None, None, []
    if row is None:
        dyn_refusal = (f'no cell-library characterization run for '
                       f'"{device_name}" — POST {{"action": '
                       f'"characterize-cells"}} to /api/cntfet/devices/'
                       f'{device_name} first')
    else:
        parsed = parse_liberty(row.liberty_text)
        e_total, per_cell = 0.0, {}
        for i in blk['instances']:
            if i['cell'] == DFF_CELL:
                missing_energy.append(f'{i["inst"]} ({DFF_LIBERTY}: no '
                                      f'energy table in the sequential '
                                      f'run)')
                continue
            lib_name = liberty_cell_name(i['cell'], i['drive'])
            d, why = _dynamic_from_library(parsed, lib_name, vdd)
            if d is None:
                missing_energy.append(f'{i["inst"]} ({why})')
                continue
            e_total += d['e_dyn_j']
            per_cell.setdefault(lib_name, d)
        dynamic = {'e_dyn_total_j': e_total,
                   'p_dyn_w': activity * f_hz * e_total,
                   'perCellEnergy': per_cell,
                   'run': row.name,
                   'equation': 'P_dyn = activity x f x sum_i E_i '
                               '(mid-grid internal + 0.5 C_L Vdd^2 per '
                               'instance)'}
    dyn_w = dynamic['p_dyn_w'] if dynamic else None
    report = {
        'ok': True, 'block': block_key, 'device': device_name,
        'vdd_v': vdd, 'ioff_n_a': ioff_n, 'ioff_p_a': ioff_p,
        'vectors': {'evaluated': n, 'total': n_total,
                    'exhaustive': exhaustive,
                    'note': 'every input x state vector' if exhaustive
                    else f'deterministic sample of {n} of {n_total} '
                         f'(seed 1)'},
        'static_w': static_mean, 'static_max_w': static_max,
        'static_min_w': min(per_vec),
        'staticPerInstance_w': {i: w / n for i, w in per_inst_mean.items()},
        'dffStaticApprox': {'w': dff_static,
                            'note': f'cdff ({DFF_FETS} FETs) has no '
                                    f'state table — approximated as '
                                    f'{DFF_FETS // 2} off devices x '
                                    f'mean Ioff x Vdd'},
        'dynamic': dynamic, 'dynamic_refusal': dyn_refusal,
        'missingEnergy': missing_energy,
        'dynamic_w': dyn_w,
        'total_w': static_mean + dyn_w if dyn_w is not None else None,
        'activity': activity, 'f_hz': f_hz, 'knobs': k,
        'fetCount': block_fet_count(block_key),
    }
    budget = next((b for b in SEED_POWER_BUDGETS if b['scope'] == 'block'),
                  None)
    rows = (getattr(manager, 'objectTables', {}) or {}).get(
        'PowerBudget') or {}
    for b in (rows.values() if isinstance(rows, dict) else rows):
        if getattr(b, 'scope', '') == 'block':
            budget = b
    if budget is not None:
        chk = check_budget({'static_w': static_mean, 'dynamic_w': dyn_w,
                            'density_w_per_cm2': None,
                            'temperature_k': None}, budget)
        chk['note'] = ('block area is UNKNOWN at this rung (no layout) '
                       '— density / temperature limits are unevaluated, '
                       'not passed')
        report['budget'] = chk
    return report


# ---------------------------------------------------------------
# 6. provenance roll-up
# ---------------------------------------------------------------

def block_proof(manager, device_name, block_key, today=None):
    """freedom_proof payload shape for the block: status = worst over
    the device + every distinct cell; chain = one entry per governing
    record of each (tagged `via`); gaps = the union."""
    from cntfet import cnt_evidence_basis as ev
    if block_key not in BLOCK_LIBRARY:
        return _refusal(block_key)
    subjects = [('device', device_name)] + [
        ('cell', c) for c in block_cells(block_key)]
    chain, gaps, reasons, statuses, seen = [], [], [], [], set()
    parts = []
    for kind, name in subjects:
        pr = ev.freedom_proof(manager, kind, name, today)
        statuses.append(pr['status'])
        parts.append({'kind': kind, 'subject': name,
                      'status': pr['status'],
                      'ipVerdict': pr.get('ipVerdict'),
                      'gaps': pr.get('gaps', []),
                      'detailPath': pr.get('detailPath')})
        for g in pr.get('gaps', []):
            if g not in gaps:
                gaps.append(g)
        for r in pr.get('reasons', []):
            if r not in reasons:
                reasons.append(r)
        for c in pr.get('chain', []):
            key = (c['record'], kind if kind == 'device' else 'cell')
            if key in seen:
                for existing in chain:
                    if existing['record'] == c['record'] \
                            and existing['viaKind'] == key[1]:
                        existing['via'].append(name)
                continue
            seen.add(key)
            chain.append({**c, 'via': [name], 'viaKind': key[1]})
    status = ev._combine(statuses) if statuses else 'unknown'
    if status == 'proven-free':
        gaps = []
    verdicts = [c.get('verdict') for c in chain if c.get('verdict')]
    from cntfet import cnt_ip_basis as ip
    worst = ip.worst_verdict(verdicts) if verdicts else None
    return {'ok': True, 'subject_kind': 'block', 'subject': block_key,
            'device': device_name, 'status': status,
            'statusIndex': ev.STATUS_INDEX[status],
            'ipVerdict': worst, 'gate': ip.ip_gate(worst) if worst else None,
            'chain': chain, 'parts': parts, 'reasons': reasons,
            'gaps': gaps, 'rule_applied': ev.PROOF_RULES[status],
            'rules': ev.PROOF_RULES, 'expiry_rules': ev.EXPIRY_RULES,
            'evidenceCount': sum(len(c['evidence']) for c in chain),
            'verifiedCount': sum(1 for c in chain for e in c['evidence']
                                 if e['verified']),
            'cells': block_cells(block_key),
            'detailPath': f'/api/cntfet/block/{block_key}/proof'
                          f'?device={device_name}',
            'jurisdiction': ev.JURISDICTION, 'scope': ev.SCOPE_LINE,
            'disclaimer': ev.DISCLAIMER, 'reviewed_at': ev.REVIEWED_AT}


def block_provenance(manager, device_name, block_key, today=None):
    """The compact block (provenance_summary shape)."""
    from cntfet import cnt_evidence_basis as ev
    proof = block_proof(manager, device_name, block_key, today)
    if not proof.get('ok'):
        return proof
    evs = [e for c in proof['chain'] for e in c['evidence']]
    evs.sort(key=lambda e: (not e['satisfies'], not e['verified'],
                            e['name']))
    return {'ipVerdict': proof.get('ipVerdict'),
            'proofStatus': proof['status'],
            'evidenceCount': len(evs),
            'verifiedCount': sum(1 for e in evs if e['verified']),
            'topEvidence': [{'name': e['name'], 'kind': e['kind'],
                             'ref': e['ref'], 'proves': e['proves'],
                             'detailPath': e['detailPath']}
                            for e in evs[:3]],
            'gaps': proof.get('gaps', [])[:3],
            'parts': proof['parts'],
            'detailPath': proof['detailPath'],
            'jurisdiction': ev.JURISDICTION, 'scope': ev.SCOPE_LINE,
            'disclaimer': ev.DISCLAIMER}


# ---------------------------------------------------------------
# 7. reports + ladder
# ---------------------------------------------------------------

def _refusal(block_key):
    return {'ok': False, 'block': block_key,
            'refusal': f'unknown block {block_key!r}; the block library '
                       f'is {sorted(BLOCK_LIBRARY)}',
            'library': sorted(BLOCK_LIBRARY)}


def ladder_rung(block_key, proof, timing=None):
    """The chip_basis 'functional-block' rung / 'polari-blocks' node
    update dict: status composed | proven | timed."""
    status = 'composed'
    if proof.get('proven'):
        status = 'proven'
        if timing and timing.get('ok'):
            status = 'timed'
    metrics = {'cells': block_cells(block_key),
               'fet_count': block_fet_count(block_key),
               'proof_vectors': proof.get('vectors'),
               'proven': bool(proof.get('proven'))}
    if timing and timing.get('ok'):
        metrics['critical_path_ps'] = timing['criticalPath']['arrival_ps']
        metrics['fmax_hz'] = timing['fmax_hz']
    return {
        'level': 'functional-block', 'rank': 3, 'node': 'polari-blocks',
        'design': 'polari-cnt-ladder', 'status': status,
        'artifact_refs': [{'module': 'cntfet', 'class': 'FunctionalBlock',
                           'name': block_key}]
        + ([{'module': 'cntfet', 'class': 'CellCharacterizationRun',
             'name': r} for r in timing.get('runs', [])]
           if timing and timing.get('ok') else []),
        'artifact_classes': [{'module': 'cntfet', 'class': 'FunctionalBlock'}],
        'metrics': metrics,
        'plan_pointer': 'plan S6 (counter -> ALU -> FSM) — cnt_blocks',
        'notes': f'{block_key}: {status}'
                 + ('' if not timing or timing.get('ok')
                    else f'; timing refused: {timing.get("refusal")}'),
    }


def block_row(block_key):
    """The FunctionalBlock seed row for one block."""
    blk = BLOCK_LIBRARY[block_key]
    proof = prove_block(block_key)
    return {
        'name': block_key, 'display_name': blk['display_name'],
        'description': blk['description'],
        'inputs_json': json.dumps(blk['inputs']),
        'outputs_json': json.dumps(blk['outputs']),
        'state_bits': len(blk['state']),
        'instances_json': json.dumps(blk['instances']),
        'nets_json': json.dumps([n['net'] for n in
                                 generate(block_key)['nets']]),
        'clock': blk['clock'],
        'function_json': json.dumps(blk['function']),
        'cell_count': len(blk['instances']),
        'fet_count': block_fet_count(block_key),
        'proven': proof['proven'],
        'proof_json': json.dumps({k: proof[k] for k in
                                  ('proven', 'vectors', 'states',
                                   'mismatches', 'note')}),
        'timing_json': '{}', 'power_json': '{}', 'provenance_json': '{}',
        'status': 'proven' if proof['proven'] else 'composed',
        'notes': DISCLAIMER, 'is_prior': True,
    }


SEED_FUNCTIONAL_BLOCKS = [block_row(k) for k in
                          ('ctr4', 'alu4', 'fsm-traffic', 'reg4')]


def block_report(manager, device_name, block_key, workdir=None,
                 with_timing=True):
    if block_key not in BLOCK_LIBRARY:
        return _refusal(block_key)
    row = block_row(block_key)
    net = generate(block_key)
    proof = prove_block(block_key)
    timing = block_timing(manager, device_name, block_key, workdir) \
        if with_timing else {'ok': False, 'refusal': 'timing not requested'}
    power = block_power(manager, device_name, block_key)
    prov = block_provenance(manager, device_name, block_key)
    return {
        'ok': True, 'block': block_key, 'device': device_name,
        'row': row,
        'netlist': {'instances': net['instances'], 'nets': net['nets'],
                    'cells': net['cells'], 'cellCount': net['cellCount'],
                    'fetCount': net['fetCount'],
                    'consistent': net['consistent'],
                    'problems': net['problems'],
                    'libertyCells': liberty_names_for(block_key)},
        'verilog': verilog_netlist(block_key),
        'proof': proof, 'stateSpace': state_space(block_key),
        'timing': timing, 'power': power, 'provenance': prov,
        'ladder': ladder_rung(block_key, proof, timing),
        'honesty': DISCLAIMER, 'payloadVersion': BLOCK_PAYLOAD_VERSION,
    }


def library_blocks_report(manager, device_name):
    blocks = []
    for key in BLOCK_LIBRARY:
        pr = prove_block(key)
        blocks.append({'block': key,
                       'display_name': BLOCK_LIBRARY[key]['display_name'],
                       'inputs': BLOCK_LIBRARY[key]['inputs'],
                       'outputs': BLOCK_LIBRARY[key]['outputs'],
                       'stateBits': len(BLOCK_LIBRARY[key]['state']),
                       'cells': block_cells(key),
                       'fetCount': block_fet_count(key),
                       'libertyCells': liberty_names_for(key),
                       'proven': pr['proven'], 'vectors': pr['vectors'],
                       'mismatches': len(pr['mismatches']),
                       'detailPath': f'/api/cntfet/block/{key}'
                                     f'?device={device_name}'})
    return {'ok': True, 'device': device_name, 'blocks': blocks,
            'allProven': all(b['proven'] for b in blocks),
            'library': sorted(BLOCK_LIBRARY),
            'rung': {'level': 'functional-block', 'rank': 3,
                     'node': 'polari-blocks'},
            'honesty': DISCLAIMER, 'payloadVersion': BLOCK_PAYLOAD_VERSION}


# ---------------------------------------------------------------
# 8. page seed
# ---------------------------------------------------------------

def _component(item_id, index, segments, title, component, inputs):
    return {'id': item_id, 'index': index, 'type': 'component',
            'rowSegmentsUsed': segments, 'gridColumnStart': None,
            'title': title, 'visible': True, 'collapsed': False,
            'cssClass': '',
            'componentProps': {'componentName': component,
                               'inputs': inputs},
            'item': None, 'nestedRows': []}


def _row(index, items, min_height=320):
    return {'index': index, 'rowSegments': 12,
            'minRowHeight': min_height, 'maxRowHeight': 0,
            'autoHeight': True, 'cssClass': '', 'items': items}


def _blocks_page(device='cnt-aligned-s1'):
    rows = [
        _row(0, [
            _component('blocks-table', 0, 6, 'Functional blocks (rung 3)',
                       'class-rows-table',
                       {'className': 'FunctionalBlock',
                        'columns': 'name,display_name,cell_count,'
                                   'fet_count,state_bits,proven,status',
                        'maxRows': 0}),
            _component('blocks-library', 1, 6,
                       'Block library: proof per block, cells, FETs',
                       'api-structured-panel',
                       {'path': f'/api/cntfet/blocks?device={device}',
                        'pick': 'blocks', 'hideKeys': '', 'title': ''}),
        ], min_height=360),
    ]
    for i, key in enumerate(BLOCK_LIBRARY):
        blk = BLOCK_LIBRARY[key]
        items = [
            _component(f'blocks-{key}-report', 0, 4,
                       f'{blk["display_name"]}: netlist, proof, timing, '
                       f'power, ladder',
                       'api-structured-panel',
                       {'path': f'/api/cntfet/block/{key}?device={device}',
                        'pick': '', 'hideKeys': '', 'title': ''}),
            _component(f'blocks-{key}-proof', 1, 4,
                       f'{blk["display_name"]}: free to use? (device + '
                       f'every cell)', 'freedom-proof-panel',
                       {'path': f'/api/cntfet/block/{key}/proof'
                                f'?device={device}'}),
        ]
        if blk['state']:
            items.append(_component(
                f'blocks-{key}-states', 2, 4,
                f'{blk["display_name"]}: state space (step the edges)',
                'cell-logic-diagram',
                {'cell': key, 'drive': 1,
                 'path': f'/api/cntfet/block/{key}/logic'}))
        else:
            items.append(_component(
                f'blocks-{key}-power', 2, 4,
                f'{blk["display_name"]}: power roll-up',
                'api-structured-panel',
                {'path': f'/api/cntfet/block/{key}/power?device={device}',
                 'pick': '', 'hideKeys': '', 'title': ''}))
        rows.append(_row(i + 1, items, min_height=460))
    return {
        'name': 'cntfet-blocks',
        'description': 'Functional blocks (counter, ALU, FSM, register) '
                       'composed from the standard cells: netlist, '
                       'exhaustive proof, state space, OpenSTA timing, '
                       'power roll-up and proof-of-freedom per block.',
        'source_class': 'FunctionalBlock',
        'isPage': True, 'pageRoute': 'cntfet-blocks',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': rows}),
    }


SEED_BLOCK_PAGES = [_blocks_page()]

CURVE_BUILDERS = {}
SEED_CNT_BLOCK_GRAPHS = []
