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

Sequential characterization (DFF setup/hold) is NOT here — that
is the lctime executor's job (AGPL, absent-by-default, D14) and
refuses honestly until wired.

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
from cntfet.cnt_characterization import _crossing, _sta_gate
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
}

DRIVES = (1, 2)


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


def _measure_arc_point(ngspice_path, workdir, osdi_path, cards,
                       subckts, cell_key, drive, pin, vdd,
                       slew_2080_s, load_f, tau):
    """One (slew, load) point for one input pin's arc: a full
    up/down pulse on `pin`, other inputs tied to the cell's
    non-controlling value. Returns the 4 NLDM numbers with the
    unate sense applied."""
    cell = CELL_LIBRARY[cell_key]
    positive = cell['unate'] == 'positive'
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
            tie = vdd if cell['noncontrolling'] else 0.0
            sources.append(
                f'vtie{other.lower()} {other.lower()}tie 0 '
                f'{tie:.6g}')
            nets.append(f'{other.lower()}tie')
    dut = (f'Xdut {" ".join(nets)} out vddnode '
           f'{subckt_name(cell_key, drive)}')
    netlist = '\n'.join([
        f'* {cell_key}_x{drive} arc {pin}', card_n, card_p,
        subckts,
        f'vdd vddnode 0 {vdd:.6g}', *sources, dut,
        f'Cload out 0 {load_f:.6e}',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {osdi_path}',
        f'tran {min(tau / 4.0, ramp / 8.0):.3e} {tstop:.3e}',
        f'wrdata arcpoint.dat v({pin.lower()}in) v(out)',
        'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'arcpoint.sp',
                       netlist)
    times, v_in, v_out = [], [], []
    with open(os.path.join(workdir, 'arcpoint.dat')) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 4:
                times.append(float(parts[0]))
                v_in.append(float(parts[1]))
                v_out.append(float(parts[3]))
    if not times or times[-1] < 0.95 * tstop:
        raise RuntimeError(
            f'arc transient TRUNCATED — '
            f'{(run.stdout + run.stderr)[-300:]}')
    half, lo20, hi80 = vdd / 2, 0.2 * vdd, 0.8 * vdd
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
    return vals


def _liberty_library(vdd, slews_s, loads_f, cell_blocks):
    """Multi-cell NLDM Liberty (ps/fF stated). cell_blocks:
    [{libertyName, function, unate, inputCap_f,
      arcs: {pin: tables[slew][load]{4 kinds}}}]."""
    def ps(x):
        return x * 1e12

    def ff(x):
        return x * 1e15

    idx1 = ', '.join(f'{ps(s):.5g}' for s in slews_s)
    idx2 = ', '.join(f'{ff(c):.5g}' for c in loads_f)
    kind_map = {'cell_rise': 'cell_rise_s',
                'cell_fall': 'cell_fall_s',
                'rise_transition': 'rise_transition_s',
                'fall_transition': 'fall_transition_s'}

    def values_rows(tables, kind):
        return ', \\\n                '.join(
            '"' + ', '.join(f'{ps(tables[si][li][kind]):.5g}'
                            for li in range(len(loads_f))) + '"'
            for si in range(len(slews_s)))

    def timing_block(tables, kind):
        return (f'          {kind} (tpl_{len(slews_s)}x'
                f'{len(loads_f)}) {{\n'
                f'            index_1 ("{idx1}");\n'
                f'            index_2 ("{idx2}");\n'
                f'            values ( \\\n                '
                f'{values_rows(tables, kind_map[kind])} );\n'
                '          }\n')

    out = [
        'library (polari_cnt) {\n'
        '  /* generated by cntfet.cnt_cell_library — executor '
        'polari-own-loop.\n'
        '     UNITS: time ps, capacitance fF. INTRINSIC-grade '
        '(S1 model, labeled\n'
        '     standin parasitics, 50/50 charge partition). NOT '
        'signoff (plan D1). */\n'
        '  delay_model : table_lookup;\n'
        '  time_unit : "1ps";\n'
        '  capacitive_load_unit (1, ff);\n'
        '  voltage_unit : "1V";\n'
        '  current_unit : "1uA";\n'
        '  pulling_resistance_unit : "1kohm";\n'
        '  leakage_power_unit : "1nW";\n'
        f'  nom_voltage : {vdd};\n'
        '  nom_temperature : 300;\n'
        '  nom_process : 1;\n'
        f'  lu_table_template (tpl_{len(slews_s)}x'
        f'{len(loads_f)}) {{\n'
        '    variable_1 : input_net_transition;\n'
        '    variable_2 : total_output_net_capacitance;\n'
        f'    index_1 ("{idx1}");\n'
        f'    index_2 ("{idx2}");\n  }}\n']
    for blk in cell_blocks:
        sense = ('positive_unate' if blk['unate'] == 'positive'
                 else 'negative_unate')
        out.append(f'  cell ({blk["libertyName"]}) {{\n')
        for pin in blk['arcs']:
            out.append(
                f'    pin ({pin}) {{\n'
                '      direction : input;\n'
                f'      capacitance : '
                f'{ff(blk["inputCap_f"]):.5g};\n    }}\n')
        out.append(
            '    pin (Y) {\n'
            '      direction : output;\n'
            f'      function : "{blk["function"]}";\n')
        for pin, tables in blk['arcs'].items():
            out.append(
                '      timing () {\n'
                f'        related_pin : "{pin}";\n'
                f'        timing_sense : {sense};\n'
                f'{timing_block(tables, "cell_rise")}'
                f'{timing_block(tables, "cell_fall")}'
                f'{timing_block(tables, "rise_transition")}'
                f'{timing_block(tables, "fall_transition")}'
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
    cells = cells or ['cinv', 'cnand2', 'cnor2', 'cbuf']
    unknown = [c for c in cells if c not in CELL_LIBRARY]
    if unknown:
        return {'ok': False,
                'error': f'unknown cells {unknown} — library has '
                         f'{sorted(CELL_LIBRARY)}; sequential '
                         f'cells (cdff) are the lctime '
                         f'executor\'s scope (not wired)'}
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
            for pin in cell['inputs']:
                tables = []
                for slew in slews_s:
                    row = []
                    for load in loads_f:
                        try:
                            row.append(_measure_arc_point(
                                ngspice_path, workdir,
                                compiled['osdiPath'], cards,
                                subckts, cell_key, drive, pin,
                                vdd, slew, load, tau))
                        except Exception as exc:
                            failures.append(
                                {'cell': cell_key,
                                 'drive': drive, 'pin': pin,
                                 'slew_s': slew, 'load_f': load,
                                 'error': str(exc)[:300]})
                            row.append(None)
                    tables.append(row)
                if all(all(pt is not None for pt in row)
                       for row in tables):
                    arcs[pin] = tables
            if arcs:
                blocks.append({
                    'cell': cell_key, 'drive': drive,
                    'libertyName': liberty_cell_name(cell_key,
                                                     drive),
                    'function': cell['liberty_function'],
                    'unate': cell['unate'],
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
                   'arcs': sorted(b['arcs'])} for b in blocks],
        'gridSlews_s': slews_s, 'gridLoads_f': loads_f,
        'monotone': monotone,
        'libertyBytes': len(liberty), 'libertyPath': lib_path,
        'staGate': sta, 'failures': failures,
        'executor': 'polari-own-loop',
        'honesty': 'combinational arcs only — DFF setup/hold = '
                   'lctime executor (absent by default, D14); '
                   'intrinsic-grade numbers, labeled standin '
                   'parasitics',
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
        for pin, tables in blk['arcs'].items():
            ok = all(
                tables[si][li]['cell_rise_s']
                <= tables[si][li + 1]['cell_rise_s'] + 1e-15
                and tables[si][li]['cell_fall_s']
                <= tables[si][li + 1]['cell_fall_s'] + 1e-15
                for si in range(len(tables))
                for li in range(len(tables[si]) - 1))
            out.append({'cell': blk['libertyName'], 'pin': pin,
                        'monotoneInLoad': ok})
    return out


def d11_crosscheck(manager, device, vdd=0.6, workdir=None,
                   slews_s=None, loads_f=None):
    """The MANDATORY D11 box: the SAME two-stage INV chain timed
    twice — ngspice transient (truth) vs OpenSTA through the
    emitted Liberty (the abstraction under test). Recorded side
    by side; tolerance stated, not silent. Refuses without
    `sta`."""
    if shutil.which('sta') is None \
            and shutil.which('opensta') is None:
        return {'ok': False,
                'refusal': 'OpenSTA not installed — D11 stays an '
                           'OPEN box (install parallaxsw/OpenSTA '
                           'or the openroad/opensta docker '
                           'wrapper)'}
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
    tcl = (f'read_liberty {char["libertyPath"]}\n'
           f'read_verilog {v_path}\n'
           'link_design chain\n'
           'create_clock -name vclk -period 1e6\n'
           'set_input_delay 0 -clock vclk [get_ports a]\n'
           'set_output_delay 0 -clock vclk [get_ports y]\n'
           f'set_input_transition {slew * 1e12:.6g} '
           '[get_ports a]\n'
           f'set_load {load * 1e15:.6g} [get_ports y]\n'
           'report_checks -path_delay max -digits 6\n'
           'exit\n')
    tcl_path = os.path.join(workdir, 'd11.tcl')
    with open(tcl_path, 'w') as fh:
        fh.write(tcl)
    sta_bin = shutil.which('sta') or shutil.which('opensta')
    sta_run = subprocess.run(
        [sta_bin, '-no_splash', '-exit', tcl_path],
        capture_output=True, text=True, timeout=180)
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
    return {'ok': True,
            'cells': SEED_CNT_CELLS,
            'drives': list(DRIVES),
            'sequential': {'cdff': 'demonstrated (S4c battery); '
                                   'setup/hold characterization '
                                   '= lctime executor, absent by '
                                   'default (D14)'},
            'source': 'CELL_LIBRARY (generated variants — '
                      'subckts are never hand-maintained twins)'}
