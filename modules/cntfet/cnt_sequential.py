"""
@module cntfet.cnt_sequential

cell-2 (2026-08-26): SEQUENTIAL characterization of the S4c
transmission-gate master-slave DFF (cdff) — setup, hold and
clk->Q — behind the same CellCharacterizationRun schema as the
combinational sweep (plan D11/D16: the executor is a FIELD).

Two executors, one ladder:

  polari-own-loop  built here. Setup/hold are found by BISECTION
                   on the D-edge offset relative to the capturing
                   clock edge, each probe a full ngspice transient
                   of the OSDI twin (2 preamble cycles settle Q,
                   the third rising edge is the test edge, Q is
                   sampled 40% of a period later). The plan's
                   sanctioned exit path ("or our own loop", D16).
  lctime           AGPL-3.0-or-later; ABSENT BY DEFAULT behind the
                   D14 knob `CNTFET_LCTIME_ENABLED`. The knob and
                   the refusal ladder exist; the invocation is NOT
                   wired and nothing is vendored or pinned until
                   Dustin ratifies CHIP_COMPUTE_DISTRIBUTION_PLAN
                   §6 D14. Asking for it refuses with the exact
                   rung you are on.

Definitions (recorded with every run):
  setup    minimum D-before-CLK(50%) time for which Q captures the
           NEW value (pass/fail capture, not the 10%-degradation
           criterion — stated, not hidden)
  hold     minimum D-after-CLK(50%) time D must keep the captured
           value for Q to retain it (may be negative)
  clk->Q   CLK 50% -> Q 50%, at one declared (slew, load) point
  slew     the 20-80 ramp of every driven edge = 2 tau
  x1 only  the cdff subckt is the S4c hand topology; drive
           variants of sequential cells are cell-3+ scope

@consumers
  - cntfet.cnt_api ({action: characterize-sequential})
  - cntfet.cnt_cell_library (library_report -> lctime_status)
  - cntfet.selftest_cntfet
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

from cntfet.cnt_cells import (
    PARASITIC_STANDIN_F, _cards, _pwl, _run_ngspice, _SUBCKTS,
    _tau_estimate,
)
from cntfet.cnt_characterization import _crossing, _sta_gate, \
    find_sta, run_sta
from cntfet.cnt_osdi import compile_osdi, find_ngspice

LCTIME_KNOB = 'CNTFET_LCTIME_ENABLED'

DEFINITIONS = {
    'setup': 'min D-edge(50%) before CLK-edge(50%) such that Q '
             'captures the new value (pass/fail capture criterion)',
    'hold': 'min D-edge(50%) after CLK-edge(50%) such that Q keeps '
            'the captured value (negative allowed)',
    'clk_to_q': 'CLK 50% -> Q 50% at the declared slew/load point',
    'transition': 'Q 20% -> 80% of VDD',
    'search': 'bisection over the offset range, resolution = the '
              'final bracket width (reported)',
    'liberty_units': 'time ps, capacitance fF',
}


def lctime_status():
    """The D14 ladder, as data."""
    enabled = os.environ.get(LCTIME_KNOB, '').lower() in (
        '1', 'true', 'yes')
    binary = shutil.which('lctime')
    if not enabled:
        rung = 'absent-by-default'
    elif not binary:
        rung = 'knob-on-binary-absent'
    else:
        rung = 'knob-on-binary-present-invocation-unwired'
    return {'licence': 'AGPL-3.0-or-later', 'knob': LCTIME_KNOB,
            'enabled': enabled, 'binary': binary, 'rung': rung,
            'gate': 'CHIP_COMPUTE_DISTRIBUTION_PLAN §6 D14 — '
                    'ratification pending; nothing vendored or '
                    'pinned before it',
            'exitPath': 'polari-own-loop (cnt_sequential)'}


def _lctime_refusal():
    st = lctime_status()
    why = {
        'absent-by-default':
            f'lctime executor is ABSENT BY DEFAULT (AGPL, D14) — '
            f'set {LCTIME_KNOB}=1 only after ratification; the '
            f'own-loop executor answers the same question',
        'knob-on-binary-absent':
            f'{LCTIME_KNOB} is on but no `lctime` binary is on PATH '
            f'— it is separately installed, never vendored',
        'knob-on-binary-present-invocation-unwired':
            'knob on and binary found, but the lctime invocation is '
            'NOT wired: D14 ratification (Dustin) precedes any '
            'pin/adapter code',
    }[st['rung']]
    return {'ok': False, 'refusal': why, 'lctime': st,
            'executor': 'lctime'}


def _context(manager, device, vdd, workdir):
    from cntfet.cnt_cell_library import _device_params
    if not getattr(device, 'derived_at', ''):
        return None, {'ok': False,
                      'error': 'device never derived — POST '
                               '{"action": "derive"} first'}
    ngspice_path, why = find_ngspice()
    if ngspice_path is None:
        return None, {'ok': False, 'refusal': why}
    params, err = _device_params(manager, device)
    if err:
        return None, err
    p_n = {**params, 'ptype': 0}
    p_p = {**params, 'ptype': 1}
    workdir = workdir or tempfile.mkdtemp(prefix='cntfet-seq-')
    os.makedirs(workdir, exist_ok=True)
    compiled = compile_osdi(workdir)
    if not compiled.get('ok'):
        return None, compiled
    tau = _tau_estimate(p_n, vdd)
    cgg = params['cinv_f_per_m'] * params['lg_m']
    input_cap = 2.0 * cgg + PARASITIC_STANDIN_F
    plateau = 100.0 * tau
    return {
        'ngspice': ngspice_path, 'workdir': workdir,
        'osdi': compiled['osdiPath'], 'cards': _cards(p_n, p_p),
        'vdd': vdd, 'tau': tau, 'rise': 2.0 * tau,
        'plateau': plateau, 'period': 6.0 * plateau,
        'tstep': tau / 4.0, 'load_f': input_cap,
        'input_cap_f': input_cap, 'runs': 0,
    }, None


def _edge_pairs(t0, level0, level1, rise):
    return [(t0, level0), (t0 + rise, level1)]


def _clock_pairs(ctx, n_edges):
    P, rise = ctx['period'], ctx['rise']
    pairs = [(0.0, 0.0)]
    t = P / 2.0
    for _ in range(n_edges):
        pairs += [(t, 0.0), (t + rise, ctx['vdd']),
                  (t + P / 2.0, ctx['vdd']),
                  (t + P / 2.0 + rise, 0.0)]
        t += P
    return pairs


#: cells-2: the two sequential DUTs this module can drive. cdff is
#: the S4c hand subckt (cnt_cells); clatch is the library cell AS
#: DATA (cnt_cell_library, generated x1 subckt). The capturing edge
#: differs: cdff captures on the CLK RISING edge, the transparent-
#: high latch closes on the G FALLING edge.
_DUTS = {
    'cdff': {'ports': 'd clk q', 'subckt': 'cdff', 'clock': 'CLK',
             'capture_edge': 'rising', 'liberty': 'DFFX1'},
    'clatch': {'ports': 'd clk q', 'subckt': 'clatch_x1',
               'clock': 'G', 'capture_edge': 'falling',
               'liberty': 'DLATCHX1'},
}


def _dut_subckts(cell):
    if cell == 'cdff':
        return _SUBCKTS
    from cntfet.cnt_cell_library import subckt_text
    return subckt_text('clatch', 1)


def _capture_edge_time(ctx, cell):
    """The test edge after 2 preamble cycles: rising edges sit at
    P/2 + kP, falling edges at P + kP (see _clock_pairs)."""
    P = ctx['period']
    if _DUTS[cell]['capture_edge'] == 'rising':
        return P / 2.0 + 2 * P
    return P + 2 * P


def _transient(ctx, d_pairs, tstop, tag, cell='cdff'):
    dut = _DUTS[cell]
    netlist = '\n'.join([
        f'* {cell} {tag}', ctx['cards'][0], ctx['cards'][1],
        _dut_subckts(cell),
        f'vdd vddnode 0 {ctx["vdd"]:.6g}',
        f'vclk clk 0 {_pwl(_clock_pairs(ctx, 4))}',
        f'vd d 0 {_pwl(d_pairs)}',
        f'Xdut {dut["ports"]} vddnode {dut["subckt"]}',
        f'Cload q 0 {ctx["load_f"]:.6e}',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {ctx["osdi"]}',
        f'tran {ctx["tstep"]:.3e} {tstop:.3e}',
        'wrdata seq.dat v(q) v(clk) v(d)', 'quit', '.endc', '.end',
        ''])
    run = _run_ngspice(ctx['ngspice'], ctx['workdir'], 'seq.sp',
                       netlist)
    ctx['runs'] += 1
    times, v_q, v_clk, v_d = [], [], [], []
    with open(os.path.join(ctx['workdir'], 'seq.dat')) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 6:
                times.append(float(parts[0]))
                v_q.append(float(parts[1]))
                v_clk.append(float(parts[3]))
                v_d.append(float(parts[5]))
    if not times or times[-1] < 0.95 * tstop:
        raise RuntimeError(
            f'sequential transient TRUNCATED — '
            f'{(run.stdout + run.stderr)[-300:]}')
    return times, v_q, v_clk, v_d


def _probe(ctx, kind, d1, offset_s, cell='cdff'):
    """One capture probe. kind='setup': D goes d0->d1 at
    te-offset. kind='hold': D goes d0->d1 well before te and back
    to d0 at te+offset. Returns (captured_d1, waveform). cells-2:
    `cell` picks the DUT and its capturing edge (cdff: CLK rising;
    clatch: G falling — the latch closes)."""
    vdd, P, rise = ctx['vdd'], ctx['period'], ctx['rise']
    te = _capture_edge_time(ctx, cell)
    tstop = te + P  # = P/2 + 3P for cdff (unchanged)
    lv = {True: vdd, False: 0.0}
    d0 = not d1
    pairs = [(0.0, lv[d0])]
    if kind == 'setup':
        t_change = te - offset_s
        pairs += _edge_pairs(t_change, lv[d0], lv[d1], rise)
        pairs.append((tstop, lv[d1]))
    else:
        t_arrive = te - 40.0 * ctx['tau']
        t_leave = te + offset_s
        pairs += _edge_pairs(t_arrive, lv[d0], lv[d1], rise)
        pairs += _edge_pairs(t_leave, lv[d1], lv[d0], rise)
        pairs.append((tstop, lv[d0]))
    # PWL times must be monotone: clamp any preamble overlap
    fixed, last = [], -1.0
    for t, v in pairs:
        t = max(t, last + ctx['tstep'])
        fixed.append((t, v))
        last = t
    times, v_q, v_clk, v_d = _transient(
        ctx, fixed, tstop, f'{kind} d1={d1} off={offset_s}', cell)
    t_sample = te + 0.4 * P
    q_at = None
    for t, q in zip(times, v_q):
        if t <= t_sample:
            q_at = q
    captured = (q_at is not None) and ((q_at > vdd / 2) == d1)
    return captured, (times, v_q, v_clk, te, v_d)


def _bisect(ctx, kind, d1, lo, hi, iters=6, cell='cdff'):
    """Find the smallest offset in [lo, hi] that captures. Assumes
    monotone pass/fail (physical for a static latch); verifies the
    bracket ends first and refuses otherwise."""
    pass_hi, wave_hi = _probe(ctx, kind, d1, hi, cell)
    if not pass_hi:
        return {'ok': False,
                'refusal': f'{kind} (D {"rise" if d1 else "fall"}) '
                           f'does not capture even at offset '
                           f'{hi:.3e} s — DFF not functional at '
                           f'this bias, widen the bracket'}, None
    pass_lo, _ = _probe(ctx, kind, d1, lo, cell)
    if pass_lo:
        return {'ok': True, 'value_s': lo, 'resolution_s': None,
                'bound': 'at-or-below-bracket-low',
                'bracket_s': [lo, hi]}, wave_hi
    a, b = lo, hi
    for _ in range(iters):
        mid = 0.5 * (a + b)
        ok, _ = _probe(ctx, kind, d1, mid, cell)
        if ok:
            b = mid
        else:
            a = mid
    return {'ok': True, 'value_s': b, 'resolution_s': b - a,
            'bound': None, 'bracket_s': [lo, hi]}, wave_hi


def _d_to_q(ctx, wave, rising_q):
    """cells-2 (latch): the TRANSPARENT D -> Q delay from the far-
    offset setup probe (D edges while G=1, well before the closing
    edge): D 50% -> Q 50%, plus the Q 20-80 transition."""
    times, v_q, v_clk, te, v_d = wave
    vdd = ctx['vdd']
    t0 = te - 0.9 * ctx['period']
    t_d = _crossing(times, v_d, vdd / 2, rising_q, t0)
    t_q = _crossing(times, v_q, vdd / 2, rising_q, t0)
    a = _crossing(times, v_q, 0.2 * vdd, rising_q, t0)
    b = _crossing(times, v_q, 0.8 * vdd, rising_q, t0)
    if None in (t_d, t_q, a, b) or t_q < t_d:
        return None
    return {'delay_s': t_q - t_d, 'transition_s': abs(b - a)}


def _clk_to_q(ctx, wave, rising_q):
    times, v_q, v_clk, te = wave[:4]
    vdd = ctx['vdd']
    t_clk = _crossing(times, v_clk, vdd / 2, True, te * 0.98)
    t_q = _crossing(times, v_q, vdd / 2, rising_q, te * 0.98)
    a = _crossing(times, v_q, 0.2 * vdd, rising_q, te * 0.98)
    b = _crossing(times, v_q, 0.8 * vdd, rising_q, te * 0.98)
    if None in (t_clk, t_q, a, b):
        return None
    return {'delay_s': t_q - t_clk, 'transition_s': abs(b - a)}


def _liberty_dff(vdd, res, input_cap_f):
    def ps(x):
        return x * 1e12

    def ff(x):
        return x * 1e15

    def scalar(kind, value_s):
        return (f'        {kind} (scalar) {{ values '
                f'("{ps(value_s):.5g}"); }}\n')

    su, ho, cq = res['setup'], res['hold'], res['clkToQ']
    return (
        'library (polari_cnt_seq) {\n'
        '  /* generated by cntfet.cnt_sequential — executor '
        'polari-own-loop.\n'
        '     UNITS: time ps, capacitance fF. Scalar constraints at '
        'ONE declared\n'
        '     slew/load point (bisection, resolution recorded in '
        'the run row).\n'
        '     INTRINSIC-grade, x1 only. NOT signoff (plan D1). */\n'
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
        '  cell (DFFX1) {\n'
        '    ff (IQ, IQN) { next_state : "D"; clocked_on : "CLK"; }\n'
        '    pin (CLK) {\n'
        '      direction : input; clock : true;\n'
        f'      capacitance : {ff(input_cap_f):.5g};\n    }}\n'
        '    pin (D) {\n'
        '      direction : input;\n'
        f'      capacitance : {ff(input_cap_f):.5g};\n'
        '      timing () {\n'
        '        related_pin : "CLK";\n'
        '        timing_type : setup_rising;\n'
        f'{scalar("rise_constraint", su["rise"]["value_s"])}'
        f'{scalar("fall_constraint", su["fall"]["value_s"])}'
        '      }\n'
        '      timing () {\n'
        '        related_pin : "CLK";\n'
        '        timing_type : hold_rising;\n'
        f'{scalar("rise_constraint", ho["rise"]["value_s"])}'
        f'{scalar("fall_constraint", ho["fall"]["value_s"])}'
        '      }\n    }\n'
        '    pin (Q) {\n'
        '      direction : output;\n'
        '      function : "IQ";\n'
        '      timing () {\n'
        '        related_pin : "CLK";\n'
        '        timing_type : rising_edge;\n'
        '        timing_sense : non_unate;\n'
        f'{scalar("cell_rise", cq["rise"]["delay_s"])}'
        f'{scalar("cell_fall", cq["fall"]["delay_s"])}'
        f'{scalar("rise_transition", cq["rise"]["transition_s"])}'
        f'{scalar("fall_transition", cq["fall"]["transition_s"])}'
        '      }\n    }\n  }\n}\n')


def _sta_setup_check(workdir, lib_path, res):
    """OpenSTA consumes the constraint arcs: a reg->reg path under
    a real clock must report OUR setup number as its 'library
    setup time'. Refuses (never skips) without `sta`."""
    sta, where = find_sta()
    if not sta:
        return {'ran': False,
                'refusal': f'{where} — sequential constraint '
                           f'consumption unverified'}
    with open(os.path.join(workdir, 'reg2.v'), 'w') as fh:
        fh.write('module reg2 (clk, d, q);\n'
                 '  input clk, d; output q; wire w;\n'
                 '  DFFX1 u1 (.D(d), .CLK(clk), .Q(w));\n'
                 '  DFFX1 u2 (.D(w), .CLK(clk), .Q(q));\n'
                 'endmodule\n')
    run = run_sta(sta, workdir,
                  'read_liberty polari_cnt_seq.lib\n'
                  'read_verilog reg2.v\n'
                  'link_design reg2\n'
                  'create_clock -name clk -period 1000 '
                  '[get_ports clk]\n'
                  'report_checks -path_delay max -digits 6\n'
                  'exit\n',
                  files=('polari_cnt_seq.lib', 'reg2.v'), timeout=180)
    m = re.search(r'^\s*(-?[0-9]*\.?[0-9]+)\s+-?[0-9.]+\s+'
                  r'library setup time', run.stdout, re.M)
    if not m:
        return {'ran': True, 'accepted': False,
                'output': run.stdout[-600:] + run.stderr[-200:]}
    seen_ps = abs(float(m.group(1)))
    expect = res['setup']['rise']['value_s'] * 1e12
    expect_f = res['setup']['fall']['value_s'] * 1e12
    match = any(abs(seen_ps - e) <= 0.01 * max(1.0, abs(e)) + 1e-3
                for e in (expect, expect_f))
    return {'ran': True, 'accepted': match, 'where': where,
            'librarySetupTime_ps': seen_ps,
            'ourSetup_ps': {'rise': expect, 'fall': expect_f},
            'output': '' if match else run.stdout[-600:]}


def _liberty_latch(vdd, res, input_cap_f):
    """cells-2: the transparent-high latch as a Liberty `latch`
    group — setup/hold against the G FALLING edge (scalar, one
    point) and the transparent D -> Q combinational arc. The G -> Q
    (open) arc is NOT emitted: not characterized (stated)."""
    def ps(x):
        return x * 1e12

    def ff(x):
        return x * 1e15

    def scalar(kind, value_s):
        return (f'        {kind} (scalar) {{ values '
                f'("{ps(value_s):.5g}"); }}\n')

    su, ho, dq = res['setup'], res['hold'], res['dToQ']
    return (
        'library (polari_cnt_latch) {\n'
        '  /* generated by cntfet.cnt_sequential — executor '
        'polari-own-loop.\n'
        '     UNITS: time ps, capacitance fF. Transparent-high D '
        'latch (clatch,\n'
        '     CELL_LIBRARY x1): setup/hold vs the G FALLING edge '
        '(bisection),\n'
        '     D->Q = the transparent arc. G->Q (open) arc NOT '
        'characterized.\n'
        '     INTRINSIC-grade, NOT signoff (plan D1). */\n'
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
        '  cell (DLATCHX1) {\n'
        '    latch (IQ, IQN) { enable : "G"; data_in : "D"; }\n'
        '    pin (G) {\n'
        '      direction : input; clock : true;\n'
        f'      capacitance : {ff(input_cap_f):.5g};\n    }}\n'
        '    pin (D) {\n'
        '      direction : input;\n'
        f'      capacitance : {ff(input_cap_f):.5g};\n'
        '      timing () {\n'
        '        related_pin : "G";\n'
        '        timing_type : setup_falling;\n'
        f'{scalar("rise_constraint", su["rise"]["value_s"])}'
        f'{scalar("fall_constraint", su["fall"]["value_s"])}'
        '      }\n'
        '      timing () {\n'
        '        related_pin : "G";\n'
        '        timing_type : hold_falling;\n'
        f'{scalar("rise_constraint", ho["rise"]["value_s"])}'
        f'{scalar("fall_constraint", ho["fall"]["value_s"])}'
        '      }\n    }\n'
        '    pin (Q) {\n'
        '      direction : output;\n'
        '      function : "IQ";\n'
        '      timing () {\n'
        '        related_pin : "D";\n'
        '        timing_sense : positive_unate;\n'
        f'{scalar("cell_rise", dq["rise"]["delay_s"])}'
        f'{scalar("cell_fall", dq["fall"]["delay_s"])}'
        f'{scalar("rise_transition", dq["rise"]["transition_s"])}'
        f'{scalar("fall_transition", dq["fall"]["transition_s"])}'
        '      }\n    }\n  }\n}\n')


def characterize_latch(manager, device, vdd=0.6, workdir=None,
                       iters=6, result_factory=None):
    """cells-2: setup/hold of the transparent-high latch (clatch,
    CELL_LIBRARY x1) against the G FALLING edge + the transparent
    D->Q delay, by the SAME own-loop bisection as the DFF (the
    probe's capturing edge is data: _DUTS). One declared slew/load
    point; the G->Q open arc is a stated follow-up."""
    ctx, err = _context(manager, device, vdd, workdir)
    if err:
        return err
    tau = ctx['tau']
    lo, hi = -10.0 * tau, 40.0 * tau
    res = {'setup': {}, 'hold': {}, 'dToQ': {}}
    waves = {}
    for d1, label in ((True, 'rise'), (False, 'fall')):
        try:
            s, wave = _bisect(ctx, 'setup', d1, lo, hi, iters,
                              cell='clatch')
            if not s.get('ok'):
                return {**s, 'runs': ctx['runs'], 'cell': 'DLATCHX1'}
            res['setup'][label] = s
            waves[label] = wave
            h, _ = _bisect(ctx, 'hold', d1, lo, hi, iters,
                           cell='clatch')
            if not h.get('ok'):
                return {**h, 'runs': ctx['runs'], 'cell': 'DLATCHX1'}
            res['hold'][label] = h
        except Exception as exc:
            return {'ok': False, 'error': str(exc)[:400],
                    'runs': ctx['runs'], 'cell': 'DLATCHX1'}
    for label, rising in (('rise', True), ('fall', False)):
        dq = _d_to_q(ctx, waves[label], rising)
        if dq is None:
            return {'ok': False,
                    'error': f'D->Q {label}: a crossing was never '
                             f'reached at the far-offset probe',
                    'cell': 'DLATCHX1'}
        res['dToQ'][label] = dq
    liberty = _liberty_latch(vdd, res, ctx['input_cap_f'])
    lib_path = os.path.join(ctx['workdir'], 'polari_cnt_latch.lib')
    with open(lib_path, 'w') as fh:
        fh.write(liberty)
    gate = _sta_gate(ctx['workdir'], liberty)
    stamp = datetime.now(timezone.utc).isoformat()
    honesty = ('own-loop bisection at ONE slew/load point, x1 '
               'generated clatch subckt, pass/fail capture criterion '
               'against the G FALLING edge; D->Q = the transparent '
               'arc measured on the far-offset setup probe; the '
               'G->Q (open) arc is NOT characterized (follow-up); '
               'intrinsic-grade')
    report = {
        'ok': True, 'device': device.name, 'vdd_v': vdd,
        'cell': 'DLATCHX1', 'libraryCell': 'clatch',
        'executor': 'polari-own-loop',
        'point': {'slew_s': 0.6 * ctx['rise'],
                  'load_f': ctx['load_f'], 'tau_s': tau},
        'setup': res['setup'], 'hold': res['hold'],
        'dToQ': res['dToQ'],
        'bracket_s': [lo, hi], 'bisectionIters': iters,
        'transients': ctx['runs'],
        'libertyBytes': len(liberty), 'libertyPath': lib_path,
        'staGate': gate,
        'definitions': {**DEFINITIONS,
                        'setup': DEFINITIONS['setup'].replace(
                            'CLK-edge', 'G falling edge'),
                        'hold': DEFINITIONS['hold'].replace(
                            'CLK-edge', 'G falling edge'),
                        'd_to_q': 'D 50% -> Q 50% while G=1 '
                                  '(transparent)'},
        'honesty': honesty, 'workdir': ctx['workdir'],
    }
    if result_factory is None:
        from cntfet.cnt_characterization import (
            CellCharacterizationRun,
        )
        result_factory = CellCharacterizationRun
    row = result_factory(
        name=f'{device.name}-latch-{stamp[11:19].replace(":", "")}',
        device=device.name, cell='DLATCHX1',
        executor='polari-own-loop', vdd_v=vdd,
        slews_s_json=json.dumps([report['point']['slew_s']]),
        loads_f_json=json.dumps([ctx['load_f']]),
        input_cap_f=ctx['input_cap_f'],
        tables_json=json.dumps(res),
        liberty_text=liberty,
        sta_gate_json=json.dumps({'gate': gate}),
        definitions_json=json.dumps(report['definitions']),
        verdict='latch-characterized',
        ran_at=stamp, notes=honesty, manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report


def characterize_sequential(manager, device, vdd=0.6, workdir=None,
                            executor='polari-own-loop',
                            iters=6, result_factory=None):
    """Setup/hold/clk->Q of the cdff at one declared slew/load
    point. executor='lctime' walks the D14 ladder and refuses."""
    if executor == 'lctime':
        return _lctime_refusal()
    if executor != 'polari-own-loop':
        return {'ok': False,
                'error': f'unknown executor {executor!r} — '
                         f'polari-own-loop | lctime'}
    ctx, err = _context(manager, device, vdd, workdir)
    if err:
        return err
    tau = ctx['tau']
    lo, hi = -10.0 * tau, 40.0 * tau
    res = {'setup': {}, 'hold': {}, 'clkToQ': {}}
    waves = {}
    for d1, label in ((True, 'rise'), (False, 'fall')):
        try:
            s, wave = _bisect(ctx, 'setup', d1, lo, hi, iters)
            if not s.get('ok'):
                return {**s, 'runs': ctx['runs']}
            res['setup'][label] = s
            waves[label] = wave
            h, _ = _bisect(ctx, 'hold', d1, lo, hi, iters)
            if not h.get('ok'):
                return {**h, 'runs': ctx['runs']}
            res['hold'][label] = h
        except Exception as exc:
            return {'ok': False, 'error': str(exc)[:400],
                    'runs': ctx['runs']}
    for label, rising in (('rise', True), ('fall', False)):
        cq = _clk_to_q(ctx, waves[label], rising)
        if cq is None:
            return {'ok': False,
                    'error': f'clk->Q {label}: a crossing was never '
                             f'reached at the far-offset probe'}
        res['clkToQ'][label] = cq
    liberty = _liberty_dff(vdd, res, ctx['input_cap_f'])
    lib_path = os.path.join(ctx['workdir'], 'polari_cnt_seq.lib')
    with open(lib_path, 'w') as fh:
        fh.write(liberty)
    gate = _sta_gate(ctx['workdir'], liberty)
    consume = _sta_setup_check(ctx['workdir'], lib_path, res)
    stamp = datetime.now(timezone.utc).isoformat()
    honesty = ('own-loop bisection at ONE slew/load point, x1 '
               'S4c topology, pass/fail capture criterion (not '
               '10% degradation); intrinsic-grade; lctime absent '
               'by default (D14)')
    report = {
        'ok': True, 'device': device.name, 'vdd_v': vdd,
        'cell': 'DFFX1', 'executor': 'polari-own-loop',
        'point': {'slew_s': 0.6 * ctx['rise'],
                  'load_f': ctx['load_f'], 'tau_s': tau},
        'setup': res['setup'], 'hold': res['hold'],
        'clkToQ': res['clkToQ'],
        'bracket_s': [lo, hi], 'bisectionIters': iters,
        'transients': ctx['runs'],
        'libertyBytes': len(liberty), 'libertyPath': lib_path,
        'staGate': gate, 'staConstraintCheck': consume,
        'definitions': DEFINITIONS, 'honesty': honesty,
        'lctime': lctime_status(), 'workdir': ctx['workdir'],
    }
    if result_factory is None:
        from cntfet.cnt_characterization import (
            CellCharacterizationRun,
        )
        result_factory = CellCharacterizationRun
    row = result_factory(
        name=f'{device.name}-seq-{stamp[11:19].replace(":", "")}',
        device=device.name, cell='DFFX1',
        executor='polari-own-loop', vdd_v=vdd,
        slews_s_json=json.dumps([report['point']['slew_s']]),
        loads_f_json=json.dumps([ctx['load_f']]),
        input_cap_f=ctx['input_cap_f'],
        tables_json=json.dumps({'setup': res['setup'],
                                'hold': res['hold'],
                                'clkToQ': res['clkToQ']}),
        liberty_text=liberty,
        sta_gate_json=json.dumps({'gate': gate,
                                  'constraintCheck': consume}),
        definitions_json=json.dumps(DEFINITIONS),
        verdict='sequential-characterized',
        ran_at=stamp, notes=honesty, manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report
