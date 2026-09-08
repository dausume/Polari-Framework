"""
@module cntfet.custom.cnt_cells

S4c: the D10 minimal cell set DEMONSTRATED on the OSDI twin —
INV (proven at S4a), NAND2, BUF, and a transmission-gate
master-slave positive-edge DFF, each verified functionally in
ngspice:

  NAND2  stepped-PWL transient over all four input corners,
         sampled mid-plateau: 1101 -> out; only (1,1) pulls low
  BUF    two inverters; out follows in with full swing
  DFF    clk square wave + a D pattern async to it: Q must equal
         D-at-rising-edge after every edge, and HOLD while D
         changes mid-cycle

DEMONSTRATION is the claim — characterized cells (delay/energy/
Liberty tables, slew/load grids) are S5 work behind the plan's
CellCharacterizationRun schema (D11/D16); the microchip ladder's
cell rung stays 'unbuilt' until then. The 50/50 charge partition
note travels with the DFF timing (delay-grade dynamics).

@consumers
  - cntfet.cnt_api ({action: cells})
  - cntfet.cntfet_selftest (honest-skip leg)
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone

from cntfet.custom.cnt_charge import PARTITION_NOTE
from cntfet.custom.cnt_derive import resolve_components
from cntfet.custom.cnt_osdi import _model_card, compile_osdi, find_ngspice, run_ngspice
from cntfet.custom.cnt_vs_model import build_vs_params, vs_terminal_current


def _cards(p_n, p_p):
    card_n, _ = _model_card(p_n)
    card_p, _ = _model_card(p_p)
    return (card_n.replace('.model cntmod ', '.model cntn '),
            card_p.replace('.model cntmod ', '.model cntp '))


# Junction-parasitic STAND-IN capacitance on every cell node the
# S1 model leaves capacitance-free (drain/source junction parasitics
# are [VS2]/S2+ scope). Without it the NAND series-stack mid node
# and inverter-chain internals starve the integrator ("timestep too
# small", proven live 2026-08-21). 2 aF ~ half a device Cgg —
# small enough not to dominate, honest about being a stand-in.
PARASITIC_STANDIN_F = 2e-18

_SUBCKTS = f'''\
.subckt cinv in out vddn
Np out in vddn cntp
Nn out in 0 cntn
Cpar out 0 {PARASITIC_STANDIN_F:.0e}
.ends cinv
.subckt cnand2 a b out vddn
Npa out a vddn cntp
Npb out b vddn cntp
Nna out a mid cntn
Nnb mid b 0 cntn
Cmid mid 0 {PARASITIC_STANDIN_F / 2:.0e}
Cpar out 0 {PARASITIC_STANDIN_F:.0e}
.ends cnand2
.subckt cbuf in out vddn
X1 in m1 vddn cinv
X2 m1 out vddn cinv
.ends cbuf
* transmission gate: conducts when en=1 (enb = inverted enable)
.subckt ctg in out en enb
Nn out en in cntn
Np out enb in cntp
Cpar out 0 {PARASITIC_STANDIN_F / 2:.0e}
.ends ctg
* positive-edge master-slave TG DFF
.subckt cdff d clk q vddn
Xckb clk clkb vddn cinv
* master: transparent while clk=0
Xtgi d m1 clkb clk ctg
Xmi1 m1 m2 vddn cinv
Xmi2 m2 m3 vddn cinv
Xtgf m3 m1 clk clkb ctg
* slave: transparent while clk=1
Xtgs m2 s1 clk clkb ctg
Xsi1 s1 q vddn cinv
Xsi2 q s2 vddn cinv
Xtgb s2 s1 clkb clk ctg
.ends cdff
'''


def _pwl(pairs):
    return 'PWL(' + ' '.join(f'{t:.6e} {v:.6g}'
                             for t, v in pairs) + ')'


def _step_pattern(levels, plateau, rise):
    """PWL pairs holding each level for `plateau`, `rise` ramps."""
    pairs, t = [(0.0, levels[0])], 0.0
    for level in levels:
        pairs.append((t + rise, level))
        t += plateau
        pairs.append((t, level))
    return pairs


def _run_ngspice(ngspice_path, workdir, name, text):
    path = os.path.join(workdir, name)
    with open(path, 'w') as fh:
        fh.write(text)
    return run_ngspice(ngspice_path, workdir, path, timeout=600)


def _read_wrdata(workdir, name):
    times, volts = [], []
    with open(os.path.join(workdir, name)) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 2:
                times.append(float(parts[0]))
                volts.append(float(parts[1]))
    return times, volts


def _read_full(workdir, name, run, expected_tstop):
    """wrdata, REFUSING a truncated transient — an aborted ngspice
    run leaves a partial file and a nearest-point sampler would
    silently read stale values (caught live 2026-08-21: 'timestep
    too small' on the capacitance-free NAND mid node)."""
    times, volts = _read_wrdata(workdir, name)
    if not times or times[-1] < 0.95 * expected_tstop:
        reached = times[-1] if times else 0.0
        raise RuntimeError(
            f'transient TRUNCATED at {reached:.3e} of '
            f'{expected_tstop:.3e} s — '
            f'{(run.stdout + run.stderr)[-400:]}')
    return times, volts


def _sample_at(times, volts, t):
    best, best_dt = 0.0, None
    for ti, vi in zip(times, volts):
        dt = abs(ti - t)
        if best_dt is None or dt < best_dt:
            best, best_dt = vi, dt
    return best


def _tau_estimate(p_n, vdd):
    cgg = p_n['cinv_f_per_m'] * p_n['lg_m']
    ion = vs_terminal_current(vdd, vdd, p_n)['id_a']
    return max(cgg * vdd / max(ion, 1e-12),
               (p_n['rs_ohm'] + p_n['rd_ohm']) * cgg)


def run_cell_battery(manager, device, vdd=0.6, workdir=None,
                     result_factory=None):
    """NAND2 + BUF + DFF functional battery. Per-cell verdicts;
    the battery passes only if every cell does."""
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
    workdir = workdir or tempfile.mkdtemp(prefix='cntfet-cells-')
    os.makedirs(workdir, exist_ok=True)
    compiled = compile_osdi(workdir)
    if not compiled.get('ok'):
        return compiled
    card_n, card_p = _cards(p_n, p_p)
    tau = _tau_estimate(p_n, vdd)
    plateau = 200.0 * tau
    rise = 2.0 * tau
    tstep = tau / 4.0
    hi, lo = vdd, 0.0
    cells = {}

    # ---- NAND2: four corners, one stepped transient ---------------
    a_levels = [lo, lo, hi, hi]
    b_levels = [lo, hi, lo, hi]
    tstop = plateau * 4
    netlist = '\n'.join([
        '* nand2 truth table', card_n, card_p, _SUBCKTS,
        f'vdd vddnode 0 {vdd:.6g}',
        f'va a 0 {_pwl(_step_pattern(a_levels, plateau, rise))}',
        f'vb b 0 {_pwl(_step_pattern(b_levels, plateau, rise))}',
        'Xdut a b out vddnode cnand2',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {compiled["osdiPath"]}',
        f'tran {tstep:.3e} {tstop:.3e}',
        'wrdata nand2.dat v(out)', 'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'nand2.sp', netlist)
    try:
        times, volts = _read_full(workdir, 'nand2.dat', run, tstop)
        table = []
        for i in range(4):
            t_mid = plateau * i + 0.75 * plateau
            out = _sample_at(times, volts, t_mid)
            table.append({'a': a_levels[i] > 0,
                          'b': b_levels[i] > 0,
                          'out_v': out})
        expected = [True, True, True, False]
        got = [entry['out_v'] > vdd / 2 for entry in table]
        cells['nand2'] = {
            'verdict': 'works' if got == expected else 'FAILS',
            'truthTable': table,
            'note': 'only (1,1) pulls low; series n-stack / '
                    'parallel p'}
    except Exception as exc:
        cells['nand2'] = {'verdict': 'FAILS',
                          'error': f'{exc}; '
                                   f'{run.stderr[-500:]}'}

    # ---- NOR2: four corners (library-generated subckt) ------------
    # The subckt comes from cnt_cell_library's generator — the
    # battery and the characterization sweep share one topology
    # source (reinstall-dedup rule: no hand-maintained twins).
    from cntfet.cnt_cell_library_basis import subckt_text
    nor2_subckt = subckt_text('cnor2', 1)
    tstop = plateau * 4
    netlist = '\n'.join([
        '* nor2 truth table', card_n, card_p, nor2_subckt,
        f'vdd vddnode 0 {vdd:.6g}',
        f'va a 0 {_pwl(_step_pattern(a_levels, plateau, rise))}',
        f'vb b 0 {_pwl(_step_pattern(b_levels, plateau, rise))}',
        'Xdut a b out vddnode cnor2_x1',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {compiled["osdiPath"]}',
        f'tran {tstep:.3e} {tstop:.3e}',
        'wrdata nor2.dat v(out)', 'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'nor2.sp', netlist)
    try:
        times, volts = _read_full(workdir, 'nor2.dat', run, tstop)
        table = []
        for i in range(4):
            t_mid = plateau * i + 0.75 * plateau
            out = _sample_at(times, volts, t_mid)
            table.append({'a': a_levels[i] > 0,
                          'b': b_levels[i] > 0,
                          'out_v': out})
        expected = [True, False, False, False]
        got = [entry['out_v'] > vdd / 2 for entry in table]
        cells['nor2'] = {
            'verdict': 'works' if got == expected else 'FAILS',
            'truthTable': table,
            'note': 'high only at (0,0); series p-stack / '
                    'parallel n (the NAND2 mirror the D10 set '
                    'lacked)'}
    except Exception as exc:
        cells['nor2'] = {'verdict': 'FAILS',
                         'error': f'{exc}; '
                                  f'{run.stderr[-500:]}'}

    # ---- BUF: follows input with full swing -----------------------
    netlist = '\n'.join([
        '* buf follow', card_n, card_p, _SUBCKTS,
        f'vdd vddnode 0 {vdd:.6g}',
        f'vin in 0 {_pwl(_step_pattern([lo, hi, lo], plateau, rise))}',
        'Xdut in out vddnode cbuf',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {compiled["osdiPath"]}',
        f'tran {tstep:.3e} {plateau * 3:.3e}',
        'wrdata buf.dat v(out)', 'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'buf.sp', netlist)
    try:
        times, volts = _read_full(workdir, 'buf.dat', run, plateau * 3)
        samples = [_sample_at(times, volts,
                              plateau * i + 0.75 * plateau)
                   for i in range(3)]
        follows = (samples[0] < 0.1 * vdd
                   and samples[1] > 0.9 * vdd
                   and samples[2] < 0.1 * vdd)
        cells['buf'] = {'verdict': 'works' if follows else 'FAILS',
                        'samples_v': samples}
    except Exception as exc:
        cells['buf'] = {'verdict': 'FAILS',
                        'error': f'{exc}; {run.stderr[-500:]}'}

    # ---- DFF: capture on rising edge, hold otherwise --------------
    period = 8.0 * plateau
    n_cycles = 4
    clk_pairs = [(0.0, lo)]
    t = period / 2.0  # first rising edge at t = period/2
    for _ in range(n_cycles):
        clk_pairs += [(t, lo), (t + rise, hi),
                      (t + period / 2.0, hi),
                      (t + period / 2.0 + rise, lo)]
        t += period
    # D toggles at quarter-period offsets so each rising edge sees
    # a DIFFERENT value than the previous capture; D also changes
    # mid-high-phase to prove HOLD.
    d_expect = [True, False, True, True]
    d_pairs = [(0.0, lo)]
    for i, want in enumerate(d_expect):
        edge = period / 2.0 + i * period
        level = hi if want else lo
        d_pairs += [(edge - plateau, d_pairs[-1][1]),
                    (edge - plateau + rise, level),
                    (edge + plateau, level),
                    # mid-cycle flip AFTER capture (hold proof)
                    (edge + plateau + rise,
                     lo if want else hi)]
    tstop = period / 2.0 + n_cycles * period
    netlist = '\n'.join([
        '* tg master-slave dff', card_n, card_p, _SUBCKTS,
        f'vdd vddnode 0 {vdd:.6g}',
        f'vclk clk 0 {_pwl(clk_pairs)}',
        f'vd d 0 {_pwl(d_pairs)}',
        'Xdut d clk q vddnode cdff',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {compiled["osdiPath"]}',
        f'tran {tstep:.3e} {tstop:.3e}',
        'wrdata dff.dat v(q)', 'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'dff.sp', netlist)
    try:
        times, volts = _read_full(workdir, 'dff.dat', run, tstop)
        captures = []
        holds = []
        for i, want in enumerate(d_expect):
            edge = period / 2.0 + i * period
            # sampled well after the edge, before the next one
            q_after = _sample_at(times, volts,
                                 edge + 0.4 * period) > vdd / 2
            captures.append({'edge': i, 'expected': want,
                             'got': q_after})
            # hold: Q unchanged just before the NEXT edge even
            # though D flipped mid-cycle
            q_late = _sample_at(times, volts,
                                edge + 0.92 * period) > vdd / 2
            holds.append(q_late == want)
        capture_ok = all(c['expected'] == c['got']
                         for c in captures)
        cells['dff'] = {
            'verdict': 'works' if capture_ok and all(holds)
            else 'FAILS',
            'captures': captures, 'holds': holds,
            'topology': 'transmission-gate master-slave, '
                        'positive edge (2 TG pairs + 5 inv, '
                        '18 FETs)',
            'note': PARTITION_NOTE}
    except Exception as exc:
        cells['dff'] = {'verdict': 'FAILS',
                        'error': f'{exc}; {run.stderr[-500:]}'}

    all_ok = all(c.get('verdict') == 'works'
                 for c in cells.values())
    stamp = datetime.now(timezone.utc).isoformat()
    verdict = ('cell-set-demonstrated' if all_ok
               else 'CELL-BATTERY-FAILS')
    report = {
        'ok': all_ok, 'device': device.name, 'vdd_v': vdd,
        'cells': cells, 'verdict': verdict,
        'engine': f"ngspice OSDI ({compiled['compiler']})",
        'honesty': 'DEMONSTRATED, not characterized — Liberty '
                   'tables/slew-load grids are S5 behind the '
                   'CellCharacterizationRun schema (D11); the '
                   'microchip cell rung stays unbuilt until then',
        'workdir': workdir,
    }
    if result_factory is None:
        from cntfet.cnt_basis import CNTFETSimResult
        result_factory = CNTFETSimResult
    row = result_factory(
        name=f'{device.name}-cells-{stamp[11:19].replace(":", "")}',
        device=device.name, kind='cell-battery',
        engine=report['engine'],
        physics_fidelity='VS_MINIMAL+eq11-charge',
        inputs_json=json.dumps({'vdd_v': vdd}),
        series_json='[]',
        metrics_json=json.dumps({
            'cells': {k: v.get('verdict')
                      for k, v in cells.items()}}),
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
