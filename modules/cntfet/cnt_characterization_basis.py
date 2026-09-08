"""
@module cntfet.cnt_characterization_basis

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
  - cntfet.cntfet_selftest (honest-skip leg)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_characterization/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.custom.cnt_cells import (
    PARASITIC_STANDIN_F, _cards, _pwl, _read_full, _run_ngspice,
    _SUBCKTS, _tau_estimate,
)
from cntfet.custom.cnt_derive import resolve_components
from cntfet.custom.cnt_osdi import compile_osdi, find_ngspice
from cntfet.custom.cnt_vs_model import build_vs_params

from cntfet.objects.cnt_characterization._shared import DEFINITIONS, _KIND_MAP, _crossing, _find_sta_local, _liberty, _measure_point, _sta_gate, find_sta, run_sta  # noqa: F401
from cntfet.objects.cnt_characterization.CellCharacterizationRun import CellCharacterizationRun  # noqa: F401

from cntfet.custom.cnt_cells import (
    PARASITIC_STANDIN_F, _cards, _pwl, _read_full, _run_ngspice,
    _SUBCKTS, _tau_estimate,
)
from cntfet.custom.cnt_vs_model import build_vs_params
from cntfet.custom.cnt_osdi import compile_osdi, find_ngspice
from datetime import datetime, timezone
import json
import os
from cntfet.custom.cnt_derive import resolve_components
import tempfile

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
