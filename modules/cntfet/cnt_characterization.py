"""
@module cntfet.cnt_characterization

S5 first rung: standard-cell characterization with the Polari
schema ABOVE any executor (plan D11/D16 — no external tool defines
our data model). CellCharacterizationRun rows hold the sparse
slew x load grid and the measured NLDM-style tables; the EXECUTOR
is a field:

  polari-own-loop  built here (ngspice transients over the OSDI
                   card) — the plan's sanctioned fallback and the
                   S5 starting point
  charlib          gated executor, fork-pinned (dausume/CharLib +
                   dausume/PySpice), wiring = future work
  lctime           sequential arcs, AGPL — Dustin's D16 veto still
                   open; codeberg mirror pending his evening
                   window (no git actions during work hours)

Measurement definitions (recorded with every run — numbers without
definitions are not data):
  delay        input 50% crossing -> output 50% crossing
  transition   output 20% -> 80% (both slews reported as 20-80)
  input slew   the 20-80 time of the driving ramp
  grid         slews x loads, loads are EXPLICIT caps at the
               output (the FO reference point is the cell's own
               input capacitance ~ 2x device Cgg)

The Liberty NLDM emitter writes time in ps and capacitance in fF
(stated in the header). An OpenSTA acceptance gate runs when the
`sta` binary exists; its absence is a recorded refusal, never a
silent skip (D11 makes the SPICE-vs-STA cross-check MANDATORY
before any CPU work — that box stays unticked until OpenSTA is
installed).

@consumers
  - cntfet.cnt_api ({action: characterize})
  - cntfet.selftest_cntfet (honest-skip leg)
"""

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_cells import (
    PARASITIC_STANDIN_F, _cards, _pwl, _read_full, _run_ngspice,
    _SUBCKTS, _tau_estimate,
)
from cntfet.cnt_derive import resolve_components
from cntfet.cnt_osdi import compile_osdi, find_ngspice
from cntfet.cnt_vs_model import build_vs_params


class CellCharacterizationRun(treeObject):
    """One characterization pass of one cell — the D11/D16 schema
    every executor must emit into."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        cell: str = '',
        executor: str = 'polari-own-loop',
        vdd_v: float = 0.6,
        temperature_k: float = 300.0,
        slews_s_json: str = '[]',
        loads_f_json: str = '[]',
        input_cap_f: float = 0.0,
        tables_json: str = '{}',
        liberty_text: str = '',
        sta_gate_json: str = '{}',
        definitions_json: str = '{}',
        verdict: str = '',
        ran_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device = device
        self.cell = cell
        self.executor = executor
        self.vdd_v = vdd_v
        self.temperature_k = temperature_k
        self.slews_s_json = slews_s_json
        self.loads_f_json = loads_f_json
        self.input_cap_f = input_cap_f
        self.tables_json = tables_json
        self.liberty_text = liberty_text
        self.sta_gate_json = sta_gate_json
        self.definitions_json = definitions_json
        self.verdict = verdict
        self.ran_at = ran_at
        self.notes = notes


DEFINITIONS = {
    'delay': 'input 50% -> output 50%',
    'transition': 'output 20% -> 80% of VDD',
    'input_slew': '20-80 time of the driving ramp',
    'liberty_units': 'time ps, capacitance fF, voltage V',
}


def _crossing(times, volts, level, rising, t_from=0.0):
    for i in range(1, len(times)):
        if times[i] <= t_from:
            continue
        lo, hi = volts[i-1], volts[i]
        if rising and lo < level <= hi:
            frac = (level - lo) / (hi - lo)
            return times[i-1] + frac * (times[i] - times[i-1])
        if not rising and lo > level >= hi:
            frac = (lo - level) / (lo - hi)
            return times[i-1] + frac * (times[i] - times[i-1])
    return None


def _measure_point(ngspice_path, workdir, osdi_path, cards, vdd,
                   slew_2080_s, load_f, tau):
    """One (slew, load) grid point: a full up/down pulse through
    the inverter; returns rise/fall delay + output transitions."""
    ramp = slew_2080_s / 0.6  # full 0->VDD ramp for a 20-80 slew
    plateau = max(400.0 * tau, 20.0 * slew_2080_s)
    t1, t2 = plateau, 2.0 * plateau
    tstop = 3.0 * plateau
    pairs = [(0.0, 0.0), (t1, 0.0), (t1 + ramp, vdd),
             (t2, vdd), (t2 + ramp, 0.0), (tstop, 0.0)]
    card_n, card_p = cards
    netlist = '\n'.join([
        '* inverter characterization point', card_n, card_p,
        _SUBCKTS,
        f'vdd vddnode 0 {vdd:.6g}',
        f'vin in 0 {_pwl(pairs)}',
        'Xdut in out vddnode cinv',
        f'Cload out 0 {load_f:.6e}',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {osdi_path}',
        f'tran {min(tau / 4.0, ramp / 8.0):.3e} {tstop:.3e}',
        'wrdata charpoint.dat v(in) v(out)',
        'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'charpoint.sp',
                       netlist)
    times, v_in, v_out = [], [], []
    with open(os.path.join(workdir, 'charpoint.dat')) as fh:
        for line in fh:
            parts = line.split()
            # wrdata with two vectors: t v(in) t v(out)
            if len(parts) >= 4:
                times.append(float(parts[0]))
                v_in.append(float(parts[1]))
                v_out.append(float(parts[3]))
    if not times or times[-1] < 0.95 * tstop:
        raise RuntimeError(
            f'characterization transient TRUNCATED — '
            f'{(run.stdout + run.stderr)[-300:]}')
    half, lo20, hi80 = vdd / 2, 0.2 * vdd, 0.8 * vdd
    # input rising edge at ~t1 -> output FALLS
    t_in_rise = _crossing(times, v_in, half, True, t1 * 0.5)
    t_out_fall = _crossing(times, v_out, half, False, t1 * 0.5)
    tf_80 = _crossing(times, v_out, hi80, False, t1 * 0.5)
    tf_20 = _crossing(times, v_out, lo20, False, t1 * 0.5)
    # input falling edge at ~t2 -> output RISES
    t_in_fall = _crossing(times, v_in, half, False, t2 * 0.98)
    t_out_rise = _crossing(times, v_out, half, True, t2 * 0.98)
    tr_20 = _crossing(times, v_out, lo20, True, t2 * 0.98)
    tr_80 = _crossing(times, v_out, hi80, True, t2 * 0.98)
    if None in (t_in_rise, t_out_fall, tf_80, tf_20, t_in_fall,
                t_out_rise, tr_20, tr_80):
        raise RuntimeError('a crossing was never reached — grid '
                           'point outside the cell\'s working '
                           'range')
    return {
        'cell_fall_s': t_out_fall - t_in_rise,
        'cell_rise_s': t_out_rise - t_in_fall,
        'fall_transition_s': tf_20 - tf_80,
        'rise_transition_s': tr_80 - tr_20,
    }


def _liberty(cell, vdd, slews_s, loads_f, tables, input_cap_f):
    """Minimal NLDM Liberty: ps / fF (stated), 3x3 templates."""
    def ps(x):
        return x * 1e12

    def ff(x):
        return x * 1e15

    def table(kind):
        rows = []
        for si in range(len(slews_s)):
            vals = ', '.join(f'{ps(tables[si][li][kind]):.5g}'
                             for li in range(len(loads_f)))
            rows.append(f'        values("{vals}");'
                        if si == len(slews_s) - 1 else
                        f'        values("{vals}", \\')
        # Liberty wants one values() with row continuations:
        value_rows = ', \\\n                '.join(
            '"' + ', '.join(f'{ps(tables[si][li][kind]):.5g}'
                            for li in range(len(loads_f))) + '"'
            for si in range(len(slews_s)))
        return value_rows

    idx1 = ', '.join(f'{ps(s):.5g}' for s in slews_s)
    idx2 = ', '.join(f'{ff(c):.5g}' for c in loads_f)
    tpl = (f'    lu_table_template (tpl_{len(slews_s)}x'
           f'{len(loads_f)}) {{\n'
           '      variable_1 : input_net_transition;\n'
           '      variable_2 : total_output_net_capacitance;\n'
           f'      index_1 ("{idx1}");\n'
           f'      index_2 ("{idx2}");\n    }}\n')

    def timing_block(kind):
        return (f'          {kind} (tpl_{len(slews_s)}x'
                f'{len(loads_f)}) {{\n'
                f'            index_1 ("{idx1}");\n'
                f'            index_2 ("{idx2}");\n'
                f'            values ( \\\n                '
                f'{table(_KIND_MAP[kind])} );\n'
                '          }\n')

    return (
        'library (polari_cnt) {\n'
        '  /* generated by cntfet.cnt_characterization — '
        'executor polari-own-loop.\n'
        '     UNITS: time ps, capacitance fF. INTRINSIC-grade '
        'numbers (S1 model,\n'
        '     no junction parasitics beyond the labeled '
        'stand-ins); 50/50 charge\n'
        '     partition (delay-grade). NOT signoff (plan D1). */\n'
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
        f'{tpl}'
        f'  cell ({cell}) {{\n'
        '    pin (A) {\n'
        '      direction : input;\n'
        f'      capacitance : {ff(input_cap_f):.5g};\n'
        '    }\n'
        '    pin (Y) {\n'
        '      direction : output;\n'
        '      function : "(!A)";\n'
        '      timing () {\n'
        '        related_pin : "A";\n'
        '        timing_sense : negative_unate;\n'
        f'{timing_block("cell_rise")}'
        f'{timing_block("cell_fall")}'
        f'{timing_block("rise_transition")}'
        f'{timing_block("fall_transition")}'
        '      }\n'
        '    }\n'
        '  }\n'
        '}\n')


_KIND_MAP = {'cell_rise': 'cell_rise_s',
             'cell_fall': 'cell_fall_s',
             'rise_transition': 'rise_transition_s',
             'fall_transition': 'fall_transition_s'}


def _sta_gate(workdir, liberty_text):
    """OpenSTA acceptance: load the library, report a trivial
    path. Absent binary = recorded refusal (the D11 SPICE-vs-STA
    cross-check stays an OPEN box until then)."""
    sta = shutil.which('sta') or shutil.which('opensta')
    if not sta:
        return {'ran': False,
                'refusal': 'OpenSTA not installed — the MANDATORY '
                           'D11 SPICE-vs-STA cross-check remains '
                           'OPEN; install parallaxsw/OpenSTA'}
    lib_path = os.path.join(workdir, 'polari_cnt.lib')
    with open(lib_path, 'w') as fh:
        fh.write(liberty_text)
    script = os.path.join(workdir, 'gate.tcl')
    with open(script, 'w') as fh:
        fh.write(f'read_liberty {lib_path}\n'
                 'puts "LIBERTY-ACCEPTED"\nexit\n')
    run = subprocess.run([sta, '-no_splash', '-exit', script],
                         capture_output=True, text=True,
                         timeout=120)
    accepted = 'LIBERTY-ACCEPTED' in run.stdout
    return {'ran': True, 'accepted': accepted,
            'output': run.stdout[-500:] if not accepted else
            'LIBERTY-ACCEPTED'}


def characterize_inverter(manager, device, vdd=0.6, slews_s=None,
                          loads_f=None, workdir=None,
                          result_factory=None):
    """The own-loop executor: sparse grid over the INV cell."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    ngspice_path, why = find_ngspice()
    if ngspice_path is None:
        return {'ok': False, 'refusal': why}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}'}
    mat, geo = rows['material'], rows['geometry']
    gate, contact = rows['gate_stack'], rows['contact']
    transport = rows['transport']
    params = build_vs_params(
        {'diameter_nm': mat.diameter_nm, 'eg_ev': mat.eg_ev},
        {'lg_nm': geo.lg_nm},
        {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
        {'rc_ohm': contact.rc_ohm},
        {'vt0_v': transport.vt0_v, 'efsd_ev': transport.efsd_ev},
        device.temperature_k)
    p_n = {**params, 'ptype': 0}
    p_p = {**params, 'ptype': 1}
    tau = _tau_estimate(p_n, vdd)
    cgg_device = params['cinv_f_per_m'] * params['lg_m']
    input_cap = 2.0 * cgg_device + PARASITIC_STANDIN_F
    slews_s = slews_s or [2.0 * tau, 8.0 * tau, 32.0 * tau]
    loads_f = loads_f or [input_cap, 2.0 * input_cap,
                          4.0 * input_cap]
    workdir = workdir or tempfile.mkdtemp(prefix='cntfet-char-')
    os.makedirs(workdir, exist_ok=True)
    compiled = compile_osdi(workdir)
    if not compiled.get('ok'):
        return compiled
    cards = _cards(p_n, p_p)
    tables, failures = [], []
    for slew in slews_s:
        row = []
        for load in loads_f:
            try:
                row.append(_measure_point(
                    ngspice_path, workdir, compiled['osdiPath'],
                    cards, vdd, slew, load, tau))
            except Exception as exc:
                failures.append({'slew_s': slew, 'load_f': load,
                                 'error': str(exc)[:300]})
                row.append(None)
        tables.append(row)
    ok = not failures
    liberty_text = ''
    sta = {}
    if ok:
        monotone = all(
            tables[si][li]['cell_rise_s']
            <= tables[si][li + 1]['cell_rise_s'] + 1e-18
            for si in range(len(slews_s))
            for li in range(len(loads_f) - 1))
        liberty_text = _liberty('INV_CNT', vdd, slews_s, loads_f,
                                tables, input_cap)
        sta = _sta_gate(workdir, liberty_text)
    else:
        monotone = False
    stamp = datetime.now(timezone.utc).isoformat()
    verdict = ('characterized' if ok and monotone else
               'NON-MONOTONE-TABLES' if ok else
               'GRID-POINTS-FAILED')
    report = {
        'ok': ok and monotone, 'device': device.name,
        'cell': 'INV_CNT', 'executor': 'polari-own-loop',
        'vdd_v': vdd, 'slews_s': slews_s, 'loads_f': loads_f,
        'inputCap_f': input_cap, 'tables': tables,
        'failures': failures, 'verdict': verdict,
        'staGate': sta, 'definitions': DEFINITIONS,
        'libertyBytes': len(liberty_text),
        'honesty': 'intrinsic-grade + labeled stand-in '
                   'parasitics; 50/50 charge partition; NOT '
                   'signoff (D1). D11 SPICE-vs-STA composed-path '
                   'regression still OPEN'
                   + ('' if sta.get('ran') else
                      ' (OpenSTA absent)'),
        'workdir': workdir,
    }
    if result_factory is None:
        result_factory = CellCharacterizationRun
    row = result_factory(
        name=f'{device.name}-char-inv-'
             f'{stamp[11:19].replace(":", "")}',
        device=device.name, cell='INV_CNT',
        executor='polari-own-loop', vdd_v=vdd,
        temperature_k=device.temperature_k,
        slews_s_json=json.dumps(slews_s),
        loads_f_json=json.dumps(loads_f),
        input_cap_f=input_cap,
        tables_json=json.dumps(tables),
        liberty_text=liberty_text,
        sta_gate_json=json.dumps(sta),
        definitions_json=json.dumps(DEFINITIONS),
        verdict=verdict, ran_at=stamp,
        notes=report['honesty'], manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report
