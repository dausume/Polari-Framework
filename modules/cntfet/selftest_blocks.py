"""
Selftest for cntfet.cnt_blocks — the FUNCTIONAL-BLOCK rung (counter,
ALU, FSM, register) composed from the standard cells.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_blocks

Proofs are gate-level (no ngspice). Timing characterizes exactly the
ALU's cells on S1 (x1, 2x2 grid — real ngspice) and runs OpenSTA
over the gate-level Verilog; without ngspice / sta the timing legs
record the refusal and check it names its reason.
"""

import json
import sys
import tempfile
import time

from cntfet import cnt_blocks as b
from cntfet import cnt_derive as cd
from cntfet import selftest_cntfet as st
from cntfet.cnt_cell_library import (
    CELL_LIBRARY, characterize_cells, liberty_cell_name,
)
from cntfet.cnt_osdi import find_ngspice, find_openvaf
from cntfet.selftest_evidence import _mgr as _evidence_mgr

_results = []
DEV = 'cnt-aligned-s1'
SI = 'si-nmos-planar-90'


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _alu(a, bb, op):
    """op = 'ADD'|'SUB'|'AND'|'OR'|'XOR'|'NOTA' -> (Y, CO, Z)."""
    code = {'ADD': (1, 0, 0), 'SUB': (1, 0, 1), 'AND': (0, 0, 0),
            'OR': (0, 0, 1), 'XOR': (0, 1, 0), 'NOTA': (0, 1, 1)}[op]
    inputs = {f'A{i}': (a >> i) & 1 for i in range(4)}
    inputs.update({f'B{i}': (bb >> i) & 1 for i in range(4)})
    inputs['OP2'], inputs['OP1'], inputs['OP0'] = code
    o = b.evaluate_block('alu4', inputs)['outputs']
    y = sum(o[f'Y{i}'] << i for i in range(4))
    return y, o['CO'], o['Z']


def main():
    t0 = time.time()
    mgr = _evidence_mgr()
    mgr.objectTables.setdefault('CellCharacterizationRun', {})
    mgr.objectTables.setdefault('PowerBudget', {})
    mgr.objectTables.setdefault('FunctionalBlock', {})
    pfac = st._row_factory(mgr, 'CNTFETParameterRow')
    dev = cd.get_row(mgr, 'AlignedCNTFETDevice', DEV)
    res = cd.derive_device(mgr, dev, parameter_factory=pfac)
    check('blocks: S1 device derives', res.get('ok'), str(res.get('error')))
    try:
        from sifet.si_device import derive_si_device, get_row as si_get
        si_row = si_get(mgr, 'SiliconMOSFET', SI)
        si_res = derive_si_device(mgr, si_row) if si_row else {}
        check('blocks: Si pair (si-nmos-planar-90) derives',
              si_res.get('ok'), str(si_res.get('error')))
    except Exception as exc:  # the Si derive is a companion, not the DUT
        check('blocks: Si pair derives', False, str(exc)[:200])

    # ---- 1. netlists -----------------------------------------------
    gens = {k: b.generate(k) for k in b.BLOCK_LIBRARY}
    lib_cells = set(CELL_LIBRARY) | {b.DFF_CELL}
    check('blocks: four blocks (ctr4, alu4, fsm-traffic, reg4); every '
          'instance is a library cell at x1',
          set(b.BLOCK_LIBRARY) == {'ctr4', 'alu4', 'fsm-traffic', 'reg4'}
          and all(i['cell'] in lib_cells and i['drive'] == 1
                  for g in gens.values() for i in g['instances']))
    check('blocks: every net consistent — every input pin driven, no '
          'net driven twice, every output driven, no dangling internal',
          all(g['consistent'] for g in gens.values()),
          json.dumps({k: g['problems'] for k, g in gens.items()
                      if g['problems']}))
    for k, g in gens.items():
        print(f'      {k}: {g["cellCount"]} cells {g["cells"]} -> '
              f'{g["fetCount"]} FETs')
    check('blocks: fet_count = sum of the instances\' cell FET counts '
          '(cdff = 18); alu4 = 4 FA x 28 + ...',
          all(g['fetCount'] == b.block_fet_count(k)
              for k, g in gens.items())
          and gens['reg4']['fetCount'] == 4 * (6 + 18)
          and gens['ctr4']['fetCount'] == 2 + 4 * (16 + 6 + 18)
          and gens['fsm-traffic']['fetCount'] == 3 * 2 + 5 * 6 + 6 + 2 * 18
          and gens['alu4']['fetCount']
          == 4 * (10 + 28 + 6 + 6 + 10 + 2 + 18 + 6) + 6 + 8)

    # ---- 2. Verilog / SPICE ----------------------------------------
    lib_names = {liberty_cell_name(c, 1) for c in CELL_LIBRARY} | {
        b.DFF_LIBERTY}
    ok_v = True
    for k in b.BLOCK_LIBRARY:
        v = b.verilog_netlist(k)
        for line in v.splitlines():
            line = line.strip()
            if line.startswith(('//', 'module', 'input', 'output',
                                'wire', 'endmodule')) or not line:
                continue
            if line.split()[0] not in lib_names:
                ok_v = False
                print('      bad Verilog line:', line)
    check('blocks: the gate-level Verilog instantiates ONLY Liberty '
          'cell names (NAND2X1 style; DFFX1 .D .CLK .Q) with named '
          'port connections', ok_v
          and 'DFFX1 U9_ff0 (.D(d0), .CLK(CLK), .Q(S0));'
          in b.verilog_netlist('fsm-traffic')
          and 'FAX1 U1_fa0 (.A(A0), .B(bs0), .CI(OP0), .S(sum0), .CO(c1));'
          in b.verilog_netlist('alu4'))
    sp = b.spice_netlist('ctr4')
    check('blocks: the SPICE .subckt instantiates the cell subckts '
          '(X instances over cha_x1 / cand2_x1 / cdff) and carries them',
          '.subckt ctr4 EN RST CLK Q0 Q1 Q2 Q3 TC vddn' in sp
          and 'Xha0 Q0 EN s0 t1 vddn cha_x1' in sp
          and 'Xff0 d0 CLK Q0 vddn cdff' in sp
          and '.subckt cha_x1' in sp and '.subckt cdff' in sp)

    # ---- 3. proofs -------------------------------------------------
    proofs = {k: b.prove_block(k) for k in b.BLOCK_LIBRARY}
    for k, p in proofs.items():
        print(f'      {k}: proven={p["proven"]} vectors={p["vectors"]} '
              f'(inputs {p["inputVectors"]} x states {p["states"]})'
              + (f' mismatches {p["mismatches"][:2]}'
                 if p['mismatches'] else ''))
    check('blocks: ALL FOUR blocks prove exhaustively against their '
          'golden models (ctr4 16 states x 4, reg4 16 x 32, fsm 4 x 2, '
          'alu4 2048 vectors)',
          all(p['proven'] for p in proofs.values())
          and proofs['ctr4']['vectors'] == 64
          and proofs['reg4']['vectors'] == 512
          and proofs['fsm-traffic']['vectors'] == 8
          and proofs['alu4']['vectors'] == 2048)
    check('alu4: 7 + 9 = 0 with carry (CO=1, Z=1); 9 - 7 = 2 (CO=1, no '
          'borrow); 3 - 5 = 14 (CO=0 = borrow); 6 AND 3 = 2; 6 OR 3 = 7; '
          '6 XOR 3 = 5; NOT 0 = 15; logic ops never raise CO',
          _alu(7, 9, 'ADD') == (0, 1, 1) and _alu(9, 7, 'SUB') == (2, 1, 0)
          and _alu(3, 5, 'SUB') == (14, 0, 0)
          and _alu(6, 3, 'AND') == (2, 0, 0) and _alu(6, 3, 'OR') == (7, 0, 0)
          and _alu(6, 3, 'XOR') == (5, 0, 0)
          and _alu(0, 0, 'NOTA') == (15, 0, 0)
          and _alu(15, 15, 'AND') == (15, 0, 0))
    ss = b.state_space('ctr4')
    count = [t for t in ss['transitions'] if t['kind'] == 'count']
    ring = {t['from']: t['to'] for t in count}
    resets = [t for t in ss['transitions'] if t['kind'] == 'reset']
    check('ctr4 state space: 16 states, a 16-ring of count edges '
          '(Q=15 -> Q=0) + a reset edge from every state to Q=0 + hold '
          'self-loops; shaped like cnt_logic sequential stateSpace',
          ss['kind'] == 'sequential' and len(ss['states']) == 16
          and all(ring[f'Q={i}'] == f'Q={(i + 1) % 16}' for i in range(16))
          and len(resets) == 16 and all(t['to'] == 'Q=0' for t in resets)
          and all(t['from'] == t['to'] for t in ss['transitions']
                  if t['kind'] == 'hold')
          and all({'from', 'input', 'to'} <= set(t)
                  for t in ss['transitions'])
          and 'description' in ss)
    fs = b.state_space('fsm-traffic')
    edges = {(t['from'], t['input']['X']): t['to'] for t in fs['transitions']}
    check('fsm-traffic state space: GREEN -X-> YELLOW -> RED -X-> GREEN, '
          'X=0 holds GREEN/RED, the unused code recovers to GREEN',
          edges[('GREEN', 1)] == 'YELLOW' and edges[('GREEN', 0)] == 'GREEN'
          and edges[('YELLOW', 0)] == 'RED' and edges[('YELLOW', 1)] == 'RED'
          and edges[('RED', 1)] == 'GREEN' and edges[('RED', 0)] == 'RED'
          and edges[('UNUSED', 0)] == 'GREEN')
    rs = b.state_space('reg4')
    check('reg4 state space: hold (EN=0) keeps every state, load (EN=1) '
          'moves to D',
          all(t['to'] == t['from'] for t in rs['transitions']
              if t['kind'] == 'hold')
          and sum(t['kind'] == 'load' for t in rs['transitions']) == 16)
    lg = b.block_logic('ctr4')
    check('block_logic: the cell-logic-diagram payload (inputs, outputs, '
          'stateSpace.kind sequential, proof, fetCount) for the `path` '
          'override', lg['ok'] and lg['stateSpace']['kind'] == 'sequential'
          and lg['inputs'] == ['EN', 'RST', 'CLK'] and lg['proof']['proven'])

    # ---- 4. timing: refusals before any run ------------------------
    t_none = b.block_timing(mgr, DEV, 'alu4')
    check('timing: REFUSES by name without a library run (names the '
          'characterize-cells affordance + the missing cells)',
          not t_none['ok'] and 'characterize-cells' in t_none['refusal']
          and 'FAX1' in t_none['missingCells'])

    # ---- 5. timing: real characterization of the ALU cells --------
    ngspice_path, why_ng = find_ngspice()
    openvaf_path, why_va = find_openvaf()
    timing = None
    if ngspice_path is None or openvaf_path is None:
        check('timing: characterization honestly SKIPPED — '
              f'{why_ng or why_va}', True)
    else:
        from cntfet.cnt_cells import _tau_estimate
        from cntfet.cnt_cell_library import _device_params
        params, _err = _device_params(mgr, dev)
        tau = _tau_estimate({**params, 'ptype': 0}, 0.6)
        cin = 2.0 * params['cinv_f_per_m'] * params['lg_m'] + 2e-18
        alu_cells = [c for c in b.block_cells('alu4')]
        t1 = time.time()
        lib = characterize_cells(
            mgr, dev, cells=alu_cells, drives=(1,),
            slews_s=[2.0 * tau, 8.0 * tau], loads_f=[cin, 4.0 * cin],
            result_factory=st._row_factory(mgr, 'CellCharacterizationRun'))
        print(f'      characterize_cells({alu_cells}) x1 2x2: '
              f'{time.time() - t1:.0f} s, ok={lib.get("ok")}, '
              f'failures={len(lib.get("failures", []))}, '
              f'staGate={lib.get("staGate", {}).get("accepted")}')
        check('timing: exactly the ALU\'s cells characterized on S1 (x1, '
              '2x2) into ONE Liberty row', lib.get('ok')
              and {c['libertyName'] for c in lib['cells']}
              == set(b.liberty_names_for('alu4')), str(lib)[:300])
        t_ctr = b.block_timing(mgr, DEV, 'ctr4')
        check('timing: ctr4 refuses BY NAME — the Liberty lacks DFFX1 '
              '(and names characterize-sequential) + the toggle cells',
              not t_ctr['ok'] and 'DFFX1' in t_ctr['missingCells']
              and 'characterize-sequential' in t_ctr['refusal'],
              str(t_ctr)[:300])
        wd = tempfile.mkdtemp(prefix='cnt-blocks-alu4-')
        timing = b.block_timing(mgr, DEV, 'alu4', workdir=wd,
                                clock_period_s=1e-9)
        if timing.get('ok'):
            cp = timing['criticalPath']
            print(f'      alu4 OpenSTA: critical path {cp["start"]} -> '
                  f'{cp["end"]} arrival {cp["arrival_ps"]:.1f} ps, slack '
                  f'{cp["slack_ps"]:.1f} ps @ {timing["clockPeriod_ps"]:g} '
                  f'ps, fmax ~ {timing["fmax_hz"] / 1e9:.2f} GHz, hold '
                  f'worst {timing["holdWorst"]}, wns {timing["wns_ps"]}')
            check('timing: alu4 timed by a REAL OpenSTA run over the '
                  'Verilog + our Liberty — critical path from an A/B/OP '
                  'input to Y/CO/Z, arrival > 0, slack MET at 1 ns, fmax '
                  'estimated, hold path reported',
                  cp['arrival_ps'] > 0 and cp['met']
                  and cp['end'] and cp['start']
                  and timing['fmax_hz'] and timing['holdWorst'] is not None
                  and timing['wns_ps'] is not None
                  and timing['tns_ps'] is not None
                  and timing['sta']['accepted'])
        else:
            check('timing: alu4 OpenSTA refusal names its reason '
                  f'({timing.get("refusal", "")[:120]})',
                  'refusal' in timing and bool(timing['refusal']))

    # ---- 6. power roll-up ------------------------------------------
    pw = b.block_power(mgr, DEV, 'alu4')
    print(f'      alu4 power: static mean {pw["static_w"]:.3g} W max '
          f'{pw["static_max_w"]:.3g} W over {pw["vectors"]["evaluated"]}/'
          f'{pw["vectors"]["total"]} vectors; dynamic '
          f'{pw["dynamic_w"]} W ({pw["dynamic_refusal"] or "from run"})')
    check('power: alu4 static mean/max over a STATED sample (64 of 2048 '
          'vectors) = sum of per-instance state leakage; positive, '
          'max >= mean', pw['ok'] and pw['vectors']['evaluated'] == 64
          and pw['vectors']['total'] == 2048
          and not pw['vectors']['exhaustive']
          and 0 < pw['static_w'] <= pw['static_max_w']
          and len(pw['staticPerInstance_w']) == 34)
    pc = b.block_power(mgr, DEV, 'ctr4')
    check('power: ctr4 exhaustive (64 vectors) with the DFF leakage '
          'approximation STATED; dynamic refused by name or, with the '
          'ALU run, DFF energy listed as missing',
          pc['ok'] and pc['vectors']['exhaustive']
          and pc['vectors']['evaluated'] == 64
          and 'approximated' in pc['dffStaticApprox']['note']
          and (pc['dynamic_refusal'] or any('DFFX1' in m
                                            for m in pc['missingEnergy'])))
    if timing is not None:
        check('power: with the ALU run the dynamic roll-up = activity x f '
              'x sum(E_i) with every ALU instance covered',
              pw['dynamic'] is not None and not pw['missingEnergy']
              and pw['dynamic_w'] > 0
              and abs(pw['dynamic_w'] - 0.1 * 1e9
                      * pw['dynamic']['e_dyn_total_j']) < 1e-15)
    check('power: block-scope budget (block-density-100w-cm2) checked — '
          'density/temperature UNEVALUATED (area unknown), stated',
          pw.get('budget') and pw['budget']['budget']
          == 'block-density-100w-cm2'
          and all(c['pass'] is None for c in pw['budget']['checks'])
          and 'UNKNOWN' in pw['budget']['note'])

    # ---- 7. provenance roll-up ---------------------------------------
    pr_s1 = b.block_provenance(mgr, DEV, 'alu4')
    pf_s1 = b.block_proof(mgr, DEV, 'alu4')
    check('provenance: alu4 on S1 = encumbered (the device gap wins over '
          'the cells); the freedom_proof shape (status, chain, gaps, '
          'disclaimer) with a chain entry per record tagged `via`',
          pr_s1['proofStatus'] == 'encumbered'
          and pf_s1['status'] == 'encumbered' and pf_s1['gaps']
          and all({'record', 'evidence', 'via'} <= set(c)
                  for c in pf_s1['chain'])
          and 'NOT LEGAL ADVICE' in pf_s1['disclaimer']
          and pf_s1['parts'][0]['kind'] == 'device',
          json.dumps(pf_s1.get('parts'))[:300])
    pf_si = b.block_proof(mgr, SI, 'alu4')
    pr_si = b.block_provenance(mgr, SI, 'alu4')
    check('provenance: alu4 on si-nmos-planar-90 = proven-free (device '
          'AND every cell proven-free), gaps empty',
          pf_si['status'] == 'proven-free' and not pf_si['gaps']
          and pr_si['proofStatus'] == 'proven-free'
          and all(p['status'] == 'proven-free' for p in pf_si['parts']),
          json.dumps([(p['subject'], p['status']) for p in pf_si['parts']]))
    pf_ctr = b.block_proof(mgr, SI, 'ctr4')
    check('provenance: ctr4 includes the cdff cell in its parts',
          any(p['subject'] == 'cdff' for p in pf_ctr['parts']))

    # ---- 8. reports / seeds / ladder ---------------------------------
    rep = b.block_report(mgr, DEV, 'alu4', with_timing=timing is not None)
    try:
        json.dumps(rep)
        ser = True
    except TypeError as exc:
        ser = False
        print('      not serialisable:', exc)
    check('block_report: JSON-serialisable; row + netlist summary + '
          'proof + stateSpace + timing + power + provenance + ladder',
          ser and rep['ok'] and rep['row']['name'] == 'alu4'
          and rep['netlist']['fetCount'] == 358
          and rep['proof']['proven']
          and all(k in rep for k in ('timing', 'power', 'provenance',
                                     'ladder', 'stateSpace')))
    lad = rep['ladder']
    expect = 'timed' if timing and timing.get('ok') else 'proven'
    check(f'ladder: the functional-block rung dict says {expect!r} for '
          'alu4 (node polari-blocks, artifact ref FunctionalBlock/alu4)',
          lad['level'] == 'functional-block' and lad['node'] == 'polari-blocks'
          and lad['status'] == expect
          and {'module': 'cntfet', 'class': 'FunctionalBlock',
               'name': 'alu4'} in lad['artifact_refs'])
    lad_c = b.ladder_rung('ctr4', proofs['ctr4'],
                          b.block_timing(mgr, DEV, 'ctr4'))
    check('ladder: ctr4 = proven (timing refused, refusal carried in '
          'notes)', lad_c['status'] == 'proven'
          and 'refused' in lad_c['notes'])
    libr = b.library_blocks_report(mgr, DEV)
    check('library_blocks_report: four blocks, allProven, detail paths',
          len(libr['blocks']) == 4 and libr['allProven']
          and all(x['detailPath'].startswith('/api/cntfet/block/')
                  for x in libr['blocks']))
    seeds = b.SEED_FUNCTIONAL_BLOCKS
    row_keys = {'name', 'display_name', 'description', 'inputs_json',
                'outputs_json', 'state_bits', 'instances_json',
                'nets_json', 'clock', 'function_json', 'cell_count',
                'fet_count', 'proven', 'proof_json', 'timing_json',
                'power_json', 'provenance_json', 'status', 'notes',
                'is_prior'}
    probe = b.FunctionalBlock(**seeds[0])
    check('FunctionalBlock(**seed) constructs with every seed field',
          all(getattr(probe, k) == v for k, v in seeds[0].items()))
    check('SEED_FUNCTIONAL_BLOCKS: four rows whose keys are '
          'FunctionalBlock fields, proven=True, instances/nets JSON',
          len(seeds) == 4
          and all(set(s) <= row_keys for s in seeds)
          and all(s['proven'] for s in seeds)
          and all(json.loads(s['instances_json']) for s in seeds))
    page = b.SEED_BLOCK_PAGES[0]
    defn = json.loads(page['definition'])
    comps = [it['componentProps']['componentName']
             for r in defn['rows'] for it in r['items']]
    check('SEED_BLOCK_PAGES: /display/cntfet-blocks (route cntfet-blocks) '
          'uses only registered components; per-block report + '
          'freedom-proof-panel; sequential blocks get the '
          'cell-logic-diagram via its `path` override',
          page['pageRoute'] == 'cntfet-blocks' and page['isPage']
          and set(comps) <= {'class-rows-table', 'api-structured-panel',
                             'freedom-proof-panel', 'cell-logic-diagram'}
          and comps.count('freedom-proof-panel') == 4
          and comps.count('cell-logic-diagram') == 3
          and len(defn['rows']) == 5)
    check('exports: CURVE_BUILDERS empty, SEED_CNT_BLOCK_GRAPHS empty '
          '(no natural graph claimed)',
          b.CURVE_BUILDERS == {} and b.SEED_CNT_BLOCK_GRAPHS == [])

    n_pass = sum(1 for _l, ok in _results if ok)
    print(f'\n{n_pass}/{len(_results)} checks passed '
          f'({time.time() - t0:.0f} s)')
    return 0 if n_pass == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
