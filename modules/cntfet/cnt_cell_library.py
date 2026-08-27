"""
@module cntfet.cnt_cell_library

S4d/S5b (Dustin 2026-08-25: "fully flesh out the cell stages and
their variants"): the cell library as DATA, not hardcoded
netlists. Each cell is a device-list row (function, inputs,
Liberty function, unateness, transistor topology) and each
VARIANT is a drive strength realized as N parallel devices per
position — so `cinv_x2` is generated, never hand-maintained.

Three capabilities ride the data:
  - subckt GENERATION per (cell, drive) — the S4c demonstrations
    and the characterization sweeps share one source of truth;
  - characterize_cells: the S5 own-loop executor generalized from
    INV to every combinational cell, per input-pin arc (the
    non-controlling tie is data), emitting ONE multi-cell NLDM
    Liberty;
  - the MANDATORY D11 SPICE-vs-STA composed-path cross-check: a
    two-stage INV chain timed by ngspice (transient truth) and by
    OpenSTA through the emitted Liberty — recorded side by side
    with a stated tolerance, refusing when `sta` is absent.

cell-2 (2026-08-26): AOI21/OAI21/MUX2 with PER-ARC ties and
Liberty `when` conditions, x4 drives, and energy-per-transition
tables (internal_power) integrated from the SAME transients.
Sequential characterization (DFF setup/hold/clk->Q) lives in
cnt_sequential (own-loop bisection; lctime = D14 ladder).

The ladder correspondence (cells -> the computers app's part
classes) is DESIGN, recorded in
AI-Notes/plans/CHIP_COMPUTE_DISTRIBUTION_PLAN.md — chip-4 stays
deferred code-wise (decision 4).

@consumers
  - cntfet.cnt_api ({action: cell-library | characterize-cells |
    d11-crosscheck})
  - cntfet.cnt_cells (generated subckts for the battery)
  - cntfet.selftest_cntfet
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_cells import (
    PARASITIC_STANDIN_F, _cards, _pwl, _run_ngspice,
    _tau_estimate,
)
from cntfet.cnt_characterization import _crossing, _sta_gate, \
    find_sta, run_sta
from cntfet.cnt_derive import resolve_components
from cntfet.cnt_osdi import compile_osdi, find_ngspice
from cntfet.cnt_vs_model import build_vs_params

#: The combinational library as data. devices: (type, drain,
#: gate, source) with 'vddn'/'0' rails and internal nets named
#: locally. midcaps: (net, fraction of the standin cap).
#: noncontrolling: the tie value for OTHER inputs while one pin's
#: arc is measured. unate: output edge sense per input edge.
CELL_LIBRARY = {
    'cinv': {
        'function': 'INV', 'inputs': ['A'], 'output': 'Y',
        'liberty_function': '(!A)', 'unate': 'negative',
        'devices': [('p', 'Y', 'A', 'vddn'),
                    ('n', 'Y', 'A', '0')],
        'midcaps': [('Y', 1.0)],
        'noncontrolling': None,
    },
    'cnand2': {
        'function': 'NAND2', 'inputs': ['A', 'B'], 'output': 'Y',
        'liberty_function': '(!(A*B))', 'unate': 'negative',
        'devices': [('p', 'Y', 'A', 'vddn'),
                    ('p', 'Y', 'B', 'vddn'),
                    ('n', 'Y', 'A', 'mid'),
                    ('n', 'mid', 'B', '0')],
        'midcaps': [('mid', 0.5), ('Y', 1.0)],
        'noncontrolling': 1,  # tie hi: series n conducts
    },
    'cnor2': {
        'function': 'NOR2', 'inputs': ['A', 'B'], 'output': 'Y',
        'liberty_function': '(!(A+B))', 'unate': 'negative',
        'devices': [('p', 'midp', 'A', 'vddn'),
                    ('p', 'Y', 'B', 'midp'),
                    ('n', 'Y', 'A', '0'),
                    ('n', 'Y', 'B', '0')],
        'midcaps': [('midp', 0.5), ('Y', 1.0)],
        'noncontrolling': 0,  # tie lo: series p conducts
    },
    'cbuf': {
        'function': 'BUF', 'inputs': ['A'], 'output': 'Y',
        'liberty_function': '(A)', 'unate': 'positive',
        'compose': [('cinv', 'A', 'm1'), ('cinv', 'm1', 'Y')],
        'devices': [], 'midcaps': [],
        'noncontrolling': None,
    },
    # ---- cell-2 (2026-08-26): richer combinationals. Cells whose
    # non-controlling tie DEPENDS on the pin under test carry an
    # explicit 'arcs' list instead of one 'noncontrolling' value:
    # {pin, ties{other: 0|1}, sense, when} — `when` is the Liberty
    # state-dependent condition, emitted verbatim.
    'caoi21': {
        # Y = !((A*B) + C)
        'function': 'AOI21', 'inputs': ['A', 'B', 'C'],
        'output': 'Y', 'liberty_function': '(!((A*B)+C))',
        'unate': 'negative',
        'devices': [('p', 'Y', 'A', 'midp'),
                    ('p', 'Y', 'B', 'midp'),
                    ('p', 'midp', 'C', 'vddn'),
                    ('n', 'Y', 'A', 'midn'),
                    ('n', 'midn', 'B', '0'),
                    ('n', 'Y', 'C', '0')],
        'midcaps': [('midp', 0.5), ('midn', 0.5), ('Y', 1.0)],
        'arcs': [
            {'pin': 'A', 'ties': {'B': 1, 'C': 0},
             'sense': 'negative', 'when': 'B*!C'},
            {'pin': 'B', 'ties': {'A': 1, 'C': 0},
             'sense': 'negative', 'when': 'A*!C'},
            {'pin': 'C', 'ties': {'A': 0, 'B': 0},
             'sense': 'negative', 'when': '!A*!B'},
        ],
    },
    'coai21': {
        # Y = !((A+B) * C)
        'function': 'OAI21', 'inputs': ['A', 'B', 'C'],
        'output': 'Y', 'liberty_function': '(!((A+B)*C))',
        'unate': 'negative',
        'devices': [('p', 'Y', 'A', 'midp'),
                    ('p', 'midp', 'B', 'vddn'),
                    ('p', 'Y', 'C', 'vddn'),
                    ('n', 'Y', 'A', 'midn'),
                    ('n', 'Y', 'B', 'midn'),
                    ('n', 'midn', 'C', '0')],
        'midcaps': [('midp', 0.5), ('midn', 0.5), ('Y', 1.0)],
        'arcs': [
            {'pin': 'A', 'ties': {'B': 0, 'C': 1},
             'sense': 'negative', 'when': '!B*C'},
            {'pin': 'B', 'ties': {'A': 0, 'C': 1},
             'sense': 'negative', 'when': '!A*C'},
            {'pin': 'C', 'ties': {'A': 1, 'B': 0},
             'sense': 'negative', 'when': 'A*!B'},
        ],
    },
    'cmux2': {
        # Y = S ? B : A — two transmission gates + the select
        # inverter (the S4c ctg topology, generated per drive).
        # The data path is PASSED, not driven from a rail: the
        # output charge on the A/B arcs comes from the input
        # driver, so the supply-energy tables for those arcs are
        # honestly ~0 (see energy note in the Liberty header).
        'function': 'MUX2', 'inputs': ['A', 'B', 'S'],
        'output': 'Y', 'liberty_function': '((A*!S)+(B*S))',
        'unate': 'non-unate',
        'devices': [('p', 'sb', 'S', 'vddn'),
                    ('n', 'sb', 'S', '0'),
                    ('n', 'Y', 'sb', 'A'),
                    ('p', 'Y', 'S', 'A'),
                    ('n', 'Y', 'S', 'B'),
                    ('p', 'Y', 'sb', 'B')],
        'midcaps': [('sb', 0.5), ('Y', 1.0)],
        'arcs': [
            {'pin': 'A', 'ties': {'S': 0, 'B': 0},
             'sense': 'positive', 'when': '!S'},
            {'pin': 'B', 'ties': {'S': 1, 'A': 0},
             'sense': 'positive', 'when': 'S'},
            {'pin': 'S', 'ties': {'A': 0, 'B': 1},
             'sense': 'positive', 'when': '!A*B'},
            {'pin': 'S', 'ties': {'A': 1, 'B': 0},
             'sense': 'negative', 'when': 'A*!B'},
        ],
    },
}

#: cell-2: x4 joins x1/x2 — still GENERATED (4 parallel devices per
#: position), never a hand twin.
DRIVES = (1, 2, 4)

COMBINATIONAL = ['cinv', 'cnand2', 'cnor2', 'cbuf', 'caoi21',
                 'coai21', 'cmux2']


def arc_id(arc):
    return arc['pin'] if not arc.get('when') \
        else f"{arc['pin']}|{arc['when']}"


def cell_arcs(cell_key):
    """The measurable input arcs of a cell as explicit specs. Cells
    with one non-controlling value get one arc per pin (every other
    pin tied to that value); cells with an 'arcs' list use it."""
    cell = CELL_LIBRARY[cell_key]
    if cell.get('arcs'):
        return [dict(a, id=arc_id(a)) for a in cell['arcs']]
    out = []
    for pin in cell['inputs']:
        ties = {o: (1 if cell['noncontrolling'] else 0)
                for o in cell['inputs'] if o != pin}
        out.append({'id': pin, 'pin': pin, 'ties': ties,
                    'sense': cell['unate'], 'when': None})
    return out


class CNTCellDefinition(treeObject):
    """One library cell VARIANT as a row (the no-code face of
    CELL_LIBRARY x DRIVES)."""

    @treeObjectInit
    def __init__(
        self,
        # 'cinv-x1', 'cnor2-x2', ...
        name: str = '',
        function: str = '',
        drive_strength: int = 1,
        fet_count: int = 0,
        inputs_json: str = '[]',
        output_pin: str = 'Y',
        liberty_function: str = '',
        unate: str = 'negative',
        # 'generated' (from CELL_LIBRARY) — a hand row would say
        # so here and the generator never touches it.
        origin: str = 'generated',
        status: str = 'defined',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.function = function
        self.drive_strength = drive_strength
        self.fet_count = fet_count
        self.inputs_json = inputs_json
        self.output_pin = output_pin
        self.liberty_function = liberty_function
        self.unate = unate
        self.origin = origin
        self.status = status
        self.notes = notes
        self.is_prior = is_prior


def fet_count(cell_key, drive):
    cell = CELL_LIBRARY[cell_key]
    if cell.get('compose'):
        return sum(fet_count(sub, drive)
                   for sub, _i, _o in cell['compose'])
    return len(cell['devices']) * drive


def _seed_cells():
    rows = []
    for key, cell in CELL_LIBRARY.items():
        for drive in DRIVES:
            rows.append({
                'name': f'{key}-x{drive}',
                'function': cell['function'],
                'drive_strength': drive,
                'fet_count': fet_count(key, drive),
                'inputs_json': json.dumps(cell['inputs']),
                'output_pin': cell['output'],
                'liberty_function': cell['liberty_function'],
                'unate': cell['unate'],
                'origin': 'generated', 'status': 'defined',
                'notes': '', 'is_prior': True,
            })
    return rows


SEED_CNT_CELLS = _seed_cells()


def subckt_name(cell_key, drive):
    return f'{cell_key}_x{drive}'


def subckt_text(cell_key, drive):
    """Generate one variant's subckt — drive xN = N parallel
    devices per position, standin caps scaled with N (they stand
    in for junction area, which scales with device count)."""
    cell = CELL_LIBRARY[cell_key]
    ports = ' '.join(cell['inputs'] + [cell['output'], 'vddn'])
    lines = [f'.subckt {subckt_name(cell_key, drive)} {ports}']
    if cell.get('compose'):
        for idx, (sub, in_net, out_net) in enumerate(
                cell['compose']):
            lines.append(f'X{idx} {in_net} {out_net} vddn '
                         f'{subckt_name(sub, drive)}')
    else:
        for d_idx, (dtype, dr, gt, src) in enumerate(
                cell['devices']):
            model = 'cntp' if dtype == 'p' else 'cntn'
            for m in range(drive):
                lines.append(
                    f'N{d_idx}m{m} {dr} {gt} {src} {model}')
        for net, frac in cell['midcaps']:
            cap = PARASITIC_STANDIN_F * frac * drive
            lines.append(f'C{net} {net} 0 {cap:.2e}')
    lines.append(f'.ends {subckt_name(cell_key, drive)}')
    return '\n'.join(lines)


def library_subckts(cells=None, drives=DRIVES):
    """Every requested variant's subckt text (compose targets
    included exactly once)."""
    cells = cells or list(CELL_LIBRARY)
    needed = []
    for key in cells:
        for sub, _i, _o in CELL_LIBRARY[key].get('compose', []):
            if sub not in needed and sub not in cells:
                needed.append(sub)
    out = []
    for key in needed + list(cells):
        for drive in drives:
            out.append(subckt_text(key, drive))
    return '\n'.join(out)


def liberty_cell_name(cell_key, drive):
    return f'{cell_key[1:].upper()}X{drive}'


def _sample_before(times, values, t):
    last = values[0]
    for ti, vi in zip(times, values):
        if ti > t:
            break
        last = vi
    return last


def _window_energy(times, i_vdd, vdd, t_a, t_b, t_edge):
    """Supply energy delivered over [t_a, t_b] with the STATE
    leakage subtracted — the static current before the edge
    (sampled at t_a) for the pre-edge part, the settled current
    after it (sampled at t_b) for the post-edge part; leakage
    differs between the two logic states and a single baseline
    over a 400-tau window swamps aJ-scale transitions (caught
    live). Trapezoid on the transient's own grid. ngspice's i(vdd)
    is positive INTO the source's + terminal, so delivered
    current = -i."""
    base_pre = _sample_before(times, i_vdd, t_a)
    base_post = _sample_before(times, i_vdd, t_b)
    e = 0.0
    for k in range(1, len(times)):
        if times[k] < t_a or times[k - 1] > t_b:
            continue
        base = base_pre if times[k] <= t_edge else base_post
        dt = times[k] - times[k - 1]
        e += 0.5 * ((base - i_vdd[k]) + (base - i_vdd[k - 1])) * dt
    return vdd * e


def _measure_arc_point(ngspice_path, workdir, osdi_path, cards,
                       subckts, cell_key, drive, arc, vdd,
                       slew_2080_s, load_f, tau, cell_cap_f=0.0):
    """One (slew, load) point for one arc: a full up/down pulse on
    the arc's pin, the other inputs tied per the arc spec. Returns
    the 4 NLDM delay/transition numbers with the arc's sense
    applied PLUS the energy per output transition from the SAME
    transient (cell-2): supply energy over each edge's window,
    leakage baseline subtracted, output-load CV^2 removed on the
    rising edge so the number is Liberty-internal (short-circuit +
    internal nodes)."""
    cell = CELL_LIBRARY[cell_key]
    pin = arc['pin']
    positive = arc['sense'] == 'positive'
    ramp = slew_2080_s / 0.6
    plateau = max(400.0 * tau, 20.0 * slew_2080_s)
    t1, t2 = plateau, 2.0 * plateau
    tstop = 3.0 * plateau
    pairs = [(0.0, 0.0), (t1, 0.0), (t1 + ramp, vdd),
             (t2, vdd), (t2 + ramp, 0.0), (tstop, 0.0)]
    card_n, card_p = cards
    nets = []
    sources = [f'vin {pin.lower()}in 0 {_pwl(pairs)}']
    for other in cell['inputs']:
        if other == pin:
            nets.append(f'{pin.lower()}in')
        else:
            tie = vdd if arc['ties'][other] else 0.0
            sources.append(
                f'vtie{other.lower()} {other.lower()}tie 0 '
                f'{tie:.6g}')
            nets.append(f'{other.lower()}tie')
    dut = (f'Xdut {" ".join(nets)} out vddnode '
           f'{subckt_name(cell_key, drive)}')
    netlist = '\n'.join([
        f'* {cell_key}_x{drive} arc {arc["id"]}', card_n, card_p,
        subckts,
        f'vdd vddnode 0 {vdd:.6g}', *sources, dut,
        f'Cload out 0 {load_f:.6e}',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {osdi_path}',
        f'tran {min(tau / 4.0, ramp / 8.0):.3e} {tstop:.3e}',
        f'wrdata arcpoint.dat v({pin.lower()}in) v(out) i(vdd)',
        'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'arcpoint.sp',
                       netlist)
    times, v_in, v_out, i_vdd = [], [], [], []
    with open(os.path.join(workdir, 'arcpoint.dat')) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 6:
                times.append(float(parts[0]))
                v_in.append(float(parts[1]))
                v_out.append(float(parts[3]))
                i_vdd.append(float(parts[5]))
    if not times or times[-1] < 0.95 * tstop:
        raise RuntimeError(
            f'arc transient TRUNCATED — '
            f'{(run.stdout + run.stderr)[-300:]}')
    # energy windows: edge 1 = input rise (t1..t2), edge 2 = input
    # fall (t2..tstop); each split at the input's 50% crossing for
    # the two-state leakage baseline
    half, lo20, hi80 = vdd / 2, 0.2 * vdd, 0.8 * vdd
    t_edge1 = _crossing(times, v_in, half, True, t1 * 0.5) or t1
    t_edge2 = _crossing(times, v_in, half, False, t2 * 0.98) or t2
    e_edge1 = _window_energy(times, i_vdd, vdd, 0.9 * t1,
                             0.98 * t2, t_edge1)
    e_edge2 = _window_energy(times, i_vdd, vdd, 0.98 * t2,
                             tstop, t_edge2)
    e_load = load_f * vdd * vdd
    if positive:
        supply_rise, supply_fall = e_edge1, e_edge2
    else:
        supply_fall, supply_rise = e_edge1, e_edge2
    internal_rise = supply_rise - e_load
    # a clamp is REPORTED only when it hides a real deficit (pass-
    # gate arcs: the load charge came from the input driver), not
    # the gate-coupling back-flow into VDD (Cgs of the p-devices on
    # an input edge — scales with the cell's OWN capacitance, i.e.
    # drive, seen live at x4: -2 aJ against a 7.5 aJ load)
    noise = 0.10 * e_load + 0.25 * cell_cap_f * vdd * vdd
    clamped = internal_rise < -noise or supply_fall < -noise
    energy = {'supply_energy_rise_j': supply_rise,
              'supply_energy_fall_j': supply_fall,
              'energy_rise_j': max(internal_rise, 0.0),
              'energy_fall_j': max(supply_fall, 0.0),
              'energy_clamped': clamped}
    t_in_rise = _crossing(times, v_in, half, True, t1 * 0.5)
    t_in_fall = _crossing(times, v_in, half, False, t2 * 0.98)
    if positive:
        # in rise -> out rise; in fall -> out fall
        t_out_r = _crossing(times, v_out, half, True, t1 * 0.5)
        r20 = _crossing(times, v_out, lo20, True, t1 * 0.5)
        r80 = _crossing(times, v_out, hi80, True, t1 * 0.5)
        t_out_f = _crossing(times, v_out, half, False, t2 * 0.98)
        f80 = _crossing(times, v_out, hi80, False, t2 * 0.98)
        f20 = _crossing(times, v_out, lo20, False, t2 * 0.98)
        vals = {'cell_rise_s': t_out_r - t_in_rise
                if None not in (t_out_r, t_in_rise) else None,
                'rise_transition_s': r80 - r20
                if None not in (r80, r20) else None,
                'cell_fall_s': t_out_f - t_in_fall
                if None not in (t_out_f, t_in_fall) else None,
                'fall_transition_s': f20 - f80
                if None not in (f20, f80) else None}
    else:
        # in rise -> out FALL; in fall -> out RISE
        t_out_f = _crossing(times, v_out, half, False, t1 * 0.5)
        f80 = _crossing(times, v_out, hi80, False, t1 * 0.5)
        f20 = _crossing(times, v_out, lo20, False, t1 * 0.5)
        t_out_r = _crossing(times, v_out, half, True, t2 * 0.98)
        r20 = _crossing(times, v_out, lo20, True, t2 * 0.98)
        r80 = _crossing(times, v_out, hi80, True, t2 * 0.98)
        vals = {'cell_fall_s': t_out_f - t_in_rise
                if None not in (t_out_f, t_in_rise) else None,
                'fall_transition_s': f20 - f80
                if None not in (f20, f80) else None,
                'cell_rise_s': t_out_r - t_in_fall
                if None not in (t_out_r, t_in_fall) else None,
                'rise_transition_s': r80 - r20
                if None not in (r80, r20) else None}
    if None in vals.values():
        raise RuntimeError('a crossing was never reached — grid '
                           'point outside the working range')
    vals.update(energy)
    return vals


def _liberty_library(vdd, slews_s, loads_f, cell_blocks):
    """Multi-cell NLDM Liberty (ps/fF stated; internal_power in
    aJ = uW*ps). cell_blocks: [{libertyName, function, inputs,
    inputCap_f, arcs: {arcId: {pin, sense, when,
    tables[slew][load]{4 timing kinds + energy}}}}]."""
    def ps(x):
        return x * 1e12

    def ff(x):
        return x * 1e15

    def aj(x):
        return x * 1e18

    idx1 = ', '.join(f'{ps(s):.5g}' for s in slews_s)
    idx2 = ', '.join(f'{ff(c):.5g}' for c in loads_f)
    kind_map = {'cell_rise': ('cell_rise_s', ps),
                'cell_fall': ('cell_fall_s', ps),
                'rise_transition': ('rise_transition_s', ps),
                'fall_transition': ('fall_transition_s', ps),
                'rise_power': ('energy_rise_j', aj),
                'fall_power': ('energy_fall_j', aj)}
    tpl = f'tpl_{len(slews_s)}x{len(loads_f)}'

    def values_rows(tables, key, conv):
        return ', \\\n                '.join(
            '"' + ', '.join(f'{conv(tables[si][li][key]):.5g}'
                            for li in range(len(loads_f))) + '"'
            for si in range(len(slews_s)))

    def table_block(tables, kind, template):
        key, conv = kind_map[kind]
        return (f'          {kind} ({template}) {{\n'
                f'            index_1 ("{idx1}");\n'
                f'            index_2 ("{idx2}");\n'
                f'            values ( \\\n                '
                f'{values_rows(tables, key, conv)} );\n'
                '          }\n')

    out = [
        'library (polari_cnt) {\n'
        '  /* generated by cntfet.cnt_cell_library — executor '
        'polari-own-loop.\n'
        '     UNITS: time ps, capacitance fF, internal_power aJ '
        '(uW x ps).\n'
        '     internal_power = supply energy per output '
        'transition from the SAME\n'
        '     transient, leakage baseline subtracted, output-load '
        'CV^2 removed on\n'
        '     the rising edge (Liberty-internal). Pass-gate arcs '
        '(MUX2 A/B) source\n'
        '     their output charge from the input driver, so their '
        'supply energy is\n'
        '     honestly ~0 (clamped at 0, flagged in the run '
        'report).\n'
        '     INTRINSIC-grade (S1 model, labeled standin '
        'parasitics, 50/50 charge\n'
        '     partition). NOT signoff (plan D1). */\n'
        '  delay_model : table_lookup;\n'
        '  time_unit : "1ps";\n'
        '  capacitive_load_unit (1, ff);\n'
        '  voltage_unit : "1V";\n'
        '  current_unit : "1uA";\n'
        '  pulling_resistance_unit : "1kohm";\n'
        '  leakage_power_unit : "1uW";\n'
        f'  nom_voltage : {vdd};\n'
        '  nom_temperature : 300;\n'
        '  nom_process : 1;\n'
        f'  lu_table_template ({tpl}) {{\n'
        '    variable_1 : input_net_transition;\n'
        '    variable_2 : total_output_net_capacitance;\n'
        f'    index_1 ("{idx1}");\n'
        f'    index_2 ("{idx2}");\n  }}\n'
        f'  power_lut_template (pwr_{tpl}) {{\n'
        '    variable_1 : input_transition_time;\n'
        '    variable_2 : total_output_net_capacitance;\n'
        f'    index_1 ("{idx1}");\n'
        f'    index_2 ("{idx2}");\n  }}\n']
    for blk in cell_blocks:
        out.append(f'  cell ({blk["libertyName"]}) {{\n')
        for pin in blk['inputs']:
            out.append(
                f'    pin ({pin}) {{\n'
                '      direction : input;\n'
                f'      capacitance : '
                f'{ff(blk["inputCap_f"]):.5g};\n    }}\n')
        out.append(
            '    pin (Y) {\n'
            '      direction : output;\n'
            f'      function : "{blk["function"]}";\n')
        for arc in blk['arcs'].values():
            sense = ('positive_unate' if arc['sense'] == 'positive'
                     else 'negative_unate')
            when = (f'        when : "{arc["when"]}";\n'
                    if arc.get('when') else '')
            tables = arc['tables']
            out.append(
                '      timing () {\n'
                f'        related_pin : "{arc["pin"]}";\n'
                f'        timing_sense : {sense};\n'
                f'{when}'
                f'{table_block(tables, "cell_rise", tpl)}'
                f'{table_block(tables, "cell_fall", tpl)}'
                f'{table_block(tables, "rise_transition", tpl)}'
                f'{table_block(tables, "fall_transition", tpl)}'
                '      }\n'
                '      internal_power () {\n'
                f'        related_pin : "{arc["pin"]}";\n'
                f'{when}'
                f'{table_block(tables, "rise_power", "pwr_" + tpl)}'
                f'{table_block(tables, "fall_power", "pwr_" + tpl)}'
                '      }\n')
        out.append('    }\n  }\n')
    out.append('}\n')
    return ''.join(out)


def _device_params(manager, device):
    rows, missing = resolve_components(manager, device)
    if missing:
        return None, {'ok': False,
                      'error': f'missing component rows: '
                               f'{missing}'}
    mat, geo = rows['material'], rows['geometry']
    gate = rows['gate_stack']
    contact = rows['contact']
    transport = rows['transport']
    params = build_vs_params(
        {'diameter_nm': mat.diameter_nm, 'eg_ev': mat.eg_ev},
        {'lg_nm': geo.lg_nm},
        {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
        {'rc_ohm': contact.rc_ohm},
        {'vt0_v': transport.vt0_v, 'efsd_ev': transport.efsd_ev},
        device.temperature_k)
    return params, None


def characterize_cells(manager, device, cells=None, drives=(1,),
                       vdd=0.6, slews_s=None, loads_f=None,
                       workdir=None, result_factory=None):
    """The S5 sweep: every requested combinational (cell, drive)
    variant, every input-pin arc, over the slew x load grid — ONE
    multi-cell Liberty + the OpenSTA gate. Sequential cells
    refuse by name (lctime executor, not wired)."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    ngspice_path, why = find_ngspice()
    if ngspice_path is None:
        return {'ok': False, 'refusal': why}
    cells = cells or list(COMBINATIONAL)
    unknown = [c for c in cells if c not in CELL_LIBRARY]
    if unknown:
        return {'ok': False,
                'error': f'unknown cells {unknown} — library has '
                         f'{sorted(CELL_LIBRARY)}; sequential '
                         f'cells (cdff) = {{action: '
                         f'characterize-sequential}} '
                         f'(cnt_sequential, D14 ladder)'}
    bad_drives = [d for d in drives if d not in DRIVES]
    if bad_drives:
        return {'ok': False,
                'error': f'drives {bad_drives} not generated — '
                         f'DRIVES = {list(DRIVES)}'}
    params, err = _device_params(manager, device)
    if err:
        return err
    p_n = {**params, 'ptype': 0}
    p_p = {**params, 'ptype': 1}
    tau = _tau_estimate(p_n, vdd)
    cgg_device = params['cinv_f_per_m'] * params['lg_m']
    input_cap = 2.0 * cgg_device + PARASITIC_STANDIN_F
    slews_s = slews_s or [2.0 * tau, 8.0 * tau, 32.0 * tau]
    loads_f = loads_f or [input_cap, 2.0 * input_cap,
                          4.0 * input_cap]
    workdir = workdir or tempfile.mkdtemp(prefix='cntfet-lib-')
    os.makedirs(workdir, exist_ok=True)
    compiled = compile_osdi(workdir)
    if not compiled.get('ok'):
        return compiled
    cards = _cards(p_n, p_p)
    subckts = library_subckts(cells, tuple(sorted(set(drives))))
    blocks, failures = [], []
    for cell_key in cells:
        cell = CELL_LIBRARY[cell_key]
        for drive in drives:
            arcs = {}
            for arc in cell_arcs(cell_key):
                tables = []
                for slew in slews_s:
                    row = []
                    for load in loads_f:
                        try:
                            row.append(_measure_arc_point(
                                ngspice_path, workdir,
                                compiled['osdiPath'], cards,
                                subckts, cell_key, drive, arc,
                                vdd, slew, load, tau,
                                cell_cap_f=input_cap * drive))
                        except Exception as exc:
                            failures.append(
                                {'cell': cell_key,
                                 'drive': drive, 'arc': arc['id'],
                                 'slew_s': slew, 'load_f': load,
                                 'error': str(exc)[:300]})
                            row.append(None)
                    tables.append(row)
                if all(all(pt is not None for pt in row)
                       for row in tables):
                    arcs[arc['id']] = {'pin': arc['pin'],
                                       'sense': arc['sense'],
                                       'when': arc.get('when'),
                                       'tables': tables}
            if arcs:
                blocks.append({
                    'cell': cell_key, 'drive': drive,
                    'libertyName': liberty_cell_name(cell_key,
                                                     drive),
                    'function': cell['liberty_function'],
                    'unate': cell['unate'],
                    'inputs': list(cell['inputs']),
                    'inputCap_f': input_cap * drive,
                    'arcs': arcs})
    if not blocks:
        return {'ok': False,
                'error': 'no arc survived the sweep',
                'failures': failures}
    liberty = _liberty_library(vdd, slews_s, loads_f, blocks)
    lib_path = os.path.join(workdir, 'polari_cnt_lib.lib')
    with open(lib_path, 'w') as fh:
        fh.write(liberty)
    sta = _sta_gate(workdir, liberty)
    stamp = datetime.now(timezone.utc).isoformat()
    monotone = _monotone_report(blocks)
    report = {
        'ok': True, 'device': device.name, 'vdd_v': vdd,
        'cells': [{'cell': b['cell'], 'drive': b['drive'],
                   'libertyName': b['libertyName'],
                   'arcs': sorted(b['arcs']),
                   'energy': _energy_summary(b)} for b in blocks],
        'gridSlews_s': slews_s, 'gridLoads_f': loads_f,
        'monotone': monotone,
        'libertyBytes': len(liberty), 'libertyPath': lib_path,
        'staGate': sta, 'failures': failures,
        'executor': 'polari-own-loop',
        'definitions': {
            'energy_per_transition':
                'supply energy over the edge window (VDD x '
                'integral of delivered current), leakage baseline '
                'subtracted; rising-output value minus C_load x '
                'VDD^2 = Liberty internal_power (aJ); negative '
                'internals clamp to 0 and are flagged '
                '(pass-gate arcs)'},
        'honesty': 'combinational arcs only — DFF setup/hold = '
                   '{action: characterize-sequential} (own-loop '
                   'bisection; lctime stays absent by default, '
                   'D14); intrinsic-grade numbers, labeled '
                   'standin parasitics',
        'workdir': workdir,
    }
    if result_factory is None:
        from cntfet.cnt_characterization import (
            CellCharacterizationRun,
        )
        result_factory = CellCharacterizationRun
    row = result_factory(
        name=f'{device.name}-lib-{stamp[11:19].replace(":", "")}',
        device=device.name, cell='library:' + ','.join(
            b['libertyName'] for b in blocks),
        executor='polari-own-loop',
        grid_json=json.dumps({'slews_s': slews_s,
                              'loads_f': loads_f,
                              'drives': list(drives)}),
        tables_json=json.dumps([{k: b[k] for k in
                                 ('cell', 'drive', 'libertyName')}
                                for b in blocks]),
        liberty_text=liberty,
        verdict='library-characterized' if not failures
        else 'library-characterized-with-failures',
        ran_at=stamp,
        notes=report['honesty'], manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report


def _monotone_report(blocks):
    """Delays must not DECREASE with load at fixed slew — the
    cheap physical sanity the INV run pinned, now per arc."""
    out = []
    for blk in blocks:
        for arc_key, arc in blk['arcs'].items():
            tables = arc['tables']
            ok = all(
                tables[si][li]['cell_rise_s']
                <= tables[si][li + 1]['cell_rise_s'] + 1e-15
                and tables[si][li]['cell_fall_s']
                <= tables[si][li + 1]['cell_fall_s'] + 1e-15
                for si in range(len(tables))
                for li in range(len(tables[si]) - 1))
            out.append({'cell': blk['libertyName'], 'pin': arc_key,
                        'monotoneInLoad': ok})
    return out


def _energy_summary(blk):
    """Per-arc energy at the mid-grid point (aJ) + the clamp flag —
    the report's readable face of the full tables."""
    out = {}
    for arc_key, arc in blk['arcs'].items():
        tables = arc['tables']
        mid = tables[len(tables) // 2][len(tables[0]) // 2]
        out[arc_key] = {
            'rise_aJ': mid['energy_rise_j'] * 1e18,
            'fall_aJ': mid['energy_fall_j'] * 1e18,
            'supplyRise_aJ': mid['supply_energy_rise_j'] * 1e18,
            'supplyFall_aJ': mid['supply_energy_fall_j'] * 1e18,
            'clamped': any(pt['energy_clamped']
                           for row in tables for pt in row)}
    return out


def d11_crosscheck(manager, device, vdd=0.6, workdir=None,
                   slews_s=None, loads_f=None):
    """The MANDATORY D11 box: the SAME two-stage INV chain timed
    twice — ngspice transient (truth) vs OpenSTA through the
    emitted Liberty (the abstraction under test). Recorded side
    by side; tolerance stated, not silent. Refuses without
    `sta`."""
    sta_bin, sta_where = find_sta()
    if sta_bin is None:
        return {'ok': False,
                'refusal': f'{sta_where} — D11 stays an OPEN box'}
    char = characterize_cells(
        manager, device, cells=['cinv'], drives=(1,), vdd=vdd,
        slews_s=slews_s, loads_f=loads_f, workdir=workdir,
        result_factory=_null_row)
    if not char.get('ok'):
        return char
    workdir = char['workdir']
    slews = char['gridSlews_s']
    loads = char['gridLoads_f']
    # mid-grid stimulus point, interpolable by both sides
    slew = slews[len(slews) // 2]
    load = loads[len(loads) // 2]
    ngspice_path, _ = find_ngspice()
    params, err = _device_params(manager, device)
    if err:
        return err
    p_n = {**params, 'ptype': 0}
    p_p = {**params, 'ptype': 1}
    tau = _tau_estimate(p_n, vdd)
    cards = _cards(p_n, p_p)
    subckts = library_subckts(['cinv'], (1,))
    compiled = compile_osdi(workdir)
    ramp = slew / 0.6
    plateau = max(400.0 * tau, 20.0 * slew)
    t1 = plateau
    tstop = 2.0 * plateau
    pairs = [(0.0, 0.0), (t1, 0.0), (t1 + ramp, vdd),
             (tstop, vdd)]
    netlist = '\n'.join([
        '* d11 composed path: inv -> inv', cards[0], cards[1],
        subckts,
        f'vdd vddnode 0 {vdd:.6g}',
        f'vin in 0 {_pwl(pairs)}',
        'X1 in w vddnode cinv_x1',
        'X2 w out vddnode cinv_x1',
        f'Cload out 0 {load:.6e}',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {compiled["osdiPath"]}',
        f'tran {min(tau / 4.0, ramp / 8.0):.3e} {tstop:.3e}',
        'wrdata d11.dat v(in) v(out)',
        'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'd11.sp', netlist)
    times, v_in, v_out = [], [], []
    with open(os.path.join(workdir, 'd11.dat')) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 4:
                times.append(float(parts[0]))
                v_in.append(float(parts[1]))
                v_out.append(float(parts[3]))
    if not times or times[-1] < 0.95 * tstop:
        return {'ok': False,
                'error': 'd11 SPICE transient truncated: '
                         + (run.stdout + run.stderr)[-300:]}
    half = vdd / 2
    t_in = _crossing(times, v_in, half, True, t1 * 0.5)
    t_out = _crossing(times, v_out, half, True, t1 * 0.5)
    if t_in is None or t_out is None:
        return {'ok': False,
                'error': 'd11 SPICE crossing never reached'}
    spice_delay_s = t_out - t_in
    # STA side: same chain through the Liberty
    verilog = ('module chain (a, y);\n'
               '  input a; output y; wire w;\n'
               '  INVX1 u1 (.A(a), .Y(w));\n'
               '  INVX1 u2 (.A(w), .Y(y));\n'
               'endmodule\n')
    v_path = os.path.join(workdir, 'chain.v')
    with open(v_path, 'w') as fh:
        fh.write(verilog)
    # A virtual clock + zero I/O delays make the a->y path a real
    # timing endpoint — bare report_checks -unconstrained answers
    # 'No paths found' for a clockless netlist (caught live).
    tcl = ('read_liberty polari_cnt_lib.lib\n'
           'read_verilog chain.v\n'
           'link_design chain\n'
           'create_clock -name vclk -period 1e6\n'
           'set_input_delay 0 -clock vclk [get_ports a]\n'
           'set_output_delay 0 -clock vclk [get_ports y]\n'
           f'set_input_transition {slew * 1e12:.6g} '
           '[get_ports a]\n'
           f'set_load {load * 1e15:.6g} [get_ports y]\n'
           'report_checks -path_delay max -digits 6\n'
           'exit\n')
    sta_run = run_sta(sta_bin, workdir, tcl,
                      files=('polari_cnt_lib.lib', 'chain.v'),
                      timeout=180)
    m = re.search(r'([0-9]*\.?[0-9]+)\s+data arrival time',
                  sta_run.stdout)
    if not m:
        return {'ok': False,
                'error': 'OpenSTA emitted no data arrival time',
                'staOutput': sta_run.stdout[-600:]
                + sta_run.stderr[-200:]}
    sta_delay_s = float(m.group(1)) * 1e-12  # library ps
    frac = (sta_delay_s - spice_delay_s) / spice_delay_s
    tolerance = 0.35
    return {
        'ok': True, 'device': device.name,
        'path': 'INVX1 -> INVX1 (rising input edge)',
        'stimulus': {'slew_s': slew, 'load_f': load,
                     'note': 'mid-grid point — inside the table, '
                             'no extrapolation'},
        'spiceDelay_s': spice_delay_s,
        'staDelay_s': sta_delay_s,
        'fractionalError': frac,
        'tolerance': tolerance,
        'verdict': 'D11-CROSSCHECK-PASS' if abs(frac) < tolerance
        else 'D11-CROSSCHECK-FAIL',
        'staWhere': sta_where,
        'honesty': 'STA interpolates the 2-input-cap-load point '
                   'for u1 from the table grid; tolerance is '
                   'stated (35%), the gap between transient '
                   'truth and NLDM abstraction is the recorded '
                   'quantity',
    }


def _null_row(**kwargs):
    import types
    return types.SimpleNamespace(**kwargs)


def library_report():
    """The cell library's no-code face."""
    from cntfet.cnt_sequential import lctime_status
    return {'ok': True,
            'cells': SEED_CNT_CELLS,
            'drives': list(DRIVES),
            'combinational': list(COMBINATIONAL),
            'arcs': {k: [a['id'] for a in cell_arcs(k)]
                     for k in COMBINATIONAL},
            'sequential': {'cdff': 'demonstrated (S4c battery); '
                                   'setup/hold/clk->Q = {action: '
                                   'characterize-sequential} '
                                   '(polari-own-loop bisection)',
                           'lctime': lctime_status()},
            'source': 'CELL_LIBRARY (generated variants — '
                      'subckts are never hand-maintained twins)'}
