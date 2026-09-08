"""
Selftest for cells-2 (2026-08-27): the NEXT set of CNT/Si standard
cells — XNOR2 / AND3 / OR3 / NAND4 / NOR4 / AOI22 / OAI22 / MUX4 /
XOR3, the MULTI-OUTPUT half and full adders (HA, FA = 28T mirror),
the tri-state buffer (TBUF, Z as an EXPECTED value) and the
transparent-high D latch (DLATCH: seeded switch-level state space
+ own-loop setup/hold/D->Q).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.cells2_selftest

Reuses selftest_cntfet's fake manager + seeding; the two
characterization legs run the REAL openvaf + ngspice + OpenSTA
(honest skip otherwise). Grids are kept SMALL on purpose (drive 1,
2 slews x 2 loads; latch bisection 4 iterations).
"""

import json
import re
import sys

from cntfet.custom import cnt_derive as cd
from cntfet.custom import cnt_logic as L
from cntfet import cnt_power_basis as cp
from cntfet import cntfet_selftest as st
from cntfet.cnt_cell_library_basis import (
    CELL_LIBRARY, COMBINATIONAL, DRIVES, MULTI_OUTPUT, SEED_CNT_CELLS,
    SEQUENTIAL_CELLS, TRISTATE, _liberty_library, cell_arcs,
    characterize_cells, fet_count, liberty_cell_name, library_report,
    subckt_text,
)
from cntfet.cnt_cell_scoring_seed import parse_liberty
from cntfet.custom.cnt_osdi import find_ngspice, find_openvaf
from cntfet.custom.cnt_sequential import characterize_latch

_results = []

#: cell -> FET count at x1 (the T counts stated in CELL_LIBRARY)
NEW_CELLS = {'cxnor2': 10, 'cand3': 8, 'cor3': 8, 'cnand4': 8,
             'cnor4': 8, 'caoi22': 8, 'coai22': 8, 'cmux4': 18,
             'cxor3': 20, 'cha': 16, 'cfa': 28, 'ctbuf': 8,
             'clatch': 10}
NEW_COMBINATIONAL = [c for c in NEW_CELLS if c != 'clatch']


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mid_delays(text):
    """{cellName: {'<out>:<pin>[|when]': (cell_rise, cell_fall)}} at
    the mid grid point, parsed from the emitted Liberty."""
    out = {}
    for blk in re.split(r'\n  cell \(', text)[1:]:
        cname = blk.split(')')[0]
        rows = out.setdefault(cname, {})
        for pin_blk in re.finditer(
                r'pin \((\w+)\) \{\n      direction : output;(.*?)'
                r'\n    \}', blk, re.S):
            opin, body = pin_blk.group(1), pin_blk.group(2)
            for m in re.finditer(
                    r'related_pin : "(\w+)";\s*timing_sense : \w+;'
                    r'(?:\s*when : "([^"]*)";)?\s*cell_rise[^;]*;'
                    r'[^;]*;\s*values \(\s*\\\n\s*(.*?) \);\s*\}'
                    r'\s*cell_fall[^;]*;[^;]*;\s*values \(\s*\\\n'
                    r'\s*(.*?) \);', body, re.S):
                def mid(vals):
                    rr = [r.strip().strip('"').split(', ')
                          for r in vals.split(', \\\n')]
                    return float(rr[len(rr) // 2][len(rr[0]) // 2])
                key = f'{opin}:{m.group(1)}' + (
                    f'|{m.group(2)}' if m.group(2) else '')
                rows[key] = (mid(m.group(3)), mid(m.group(4)))
    return out


def main():
    mgr = st._mgr()
    st._seed_all(mgr)
    mgr.objectTables.setdefault('CellCharacterizationRun', {})
    pfac = st._row_factory(mgr, 'CNTFETParameterRow')

    # ---- A. schema ---------------------------------------------------
    check('cells-2 schema: every cell carries outputs[] + '
          'liberty_functions{} (normalized), output = outputs[0], '
          'liberty_function = liberty_functions[output]; cha/cfa are '
          'the multi-output cells, ctbuf the tri-state, clatch '
          'sequential; the seed rows still cover every (cell, drive)',
          all(c['outputs'] and c['output'] == c['outputs'][0]
              and c['liberty_function']
              == c['liberty_functions'][c['output']]
              for c in CELL_LIBRARY.values())
          and CELL_LIBRARY['cha']['outputs'] == ['S', 'CO']
          and CELL_LIBRARY['cfa']['outputs'] == ['S', 'CO']
          and MULTI_OUTPUT == ['cha', 'cfa'] and TRISTATE == ['ctbuf']
          and SEQUENTIAL_CELLS == ['clatch']
          and CELL_LIBRARY['ctbuf']['three_state'] == '(!EN)'
          and CELL_LIBRARY['clatch']['sequential']
          and CELL_LIBRARY['clatch']['liberty_function'] is None
          and set(NEW_COMBINATIONAL) <= set(COMBINATIONAL)
          and 'clatch' not in COMBINATIONAL
          and len(SEED_CNT_CELLS) == len(CELL_LIBRARY) * len(DRIVES)
          and {f'{c}-x{d}' for c in NEW_CELLS for d in DRIVES}
          <= {r['name'] for r in SEED_CNT_CELLS}
          and any(r['name'] == 'cfa-x1' and 'CO = ' in r['notes']
                  for r in SEED_CNT_CELLS))
    check('cells-2 T counts: xnor2 10 (NAND2+OAI21), and3/or3 8, '
          'nand4/nor4 8, aoi22/oai22 8, mux4 18 (3 MUX2), xor3 20, '
          'ha 16, fa 28 (mirror), tbuf 8, latch 10 — each x drive',
          all(fet_count(c, d) == n * d
              for c, n in NEW_CELLS.items() for d in DRIVES),
          f'{[(c, fet_count(c, 1)) for c in NEW_CELLS]}')
    rendered = {(c, d): subckt_text(c, d)
                for c in NEW_CELLS for d in DRIVES}
    fa1, ha2, n4x4 = (rendered[('cfa', 1)], rendered[('cha', 2)],
                      rendered[('cnand4', 4)])
    check('cells-2 subckts render at x1/x2/x4: multi-output ports '
          'list EVERY output (cfa: A B CI S CO), composed multi-output '
          'cells wire one stage per output, stacks scale with drive',
          all(t.startswith(f'.subckt {c}_x{d} ')
              and t.endswith(f'.ends {c}_x{d}')
              for (c, d), t in rendered.items())
          and fa1.startswith('.subckt cfa_x1 A B CI S CO vddn')
          and fa1.count('cntp') == 14 and fa1.count('cntn') == 14
          and '.subckt cha_x2 A B S CO vddn' in ha2
          and 'X0 A B S vddn cxor2_x2' in ha2
          and 'X1 A B CO vddn cand2_x2' in ha2
          and n4x4.count('cntn') == 16 and 'Cmid3 mid3 0' in n4x4
          and '.subckt ctbuf_x1 A EN Y vddn' in rendered[('ctbuf', 1)]
          and '.subckt clatch_x1 D G Q vddn' in rendered[('clatch', 1)],
          f'fa={fa1[:80]!r} ha2={ha2!r}')
    arcs = {c: cell_arcs(c) for c in NEW_CELLS}
    check('cells-2 arcs: multi-output arcs are keyed <output>:<pin>|'
          '<when> (cha 6 = 4 S + 2 CO; cfa 18 = 12 S + 6 CO); mux4 12 '
          '`when` arcs; xor3 12 (4 minterms x 3 pins); aoi22/oai22 '
          'per-arc ties; nand4/nor4 tie hi/lo; tbuf ONE arc (A when '
          'EN); latch ONE (D when G)',
          [a['id'] for a in arcs['cha']]
          == ['S:A|!B', 'S:A|B', 'S:B|!A', 'S:B|A', 'CO:A|B', 'CO:B|A']
          and len(arcs['cfa']) == 18
          and sum(a['output'] == 'S' for a in arcs['cfa']) == 12
          and sum(a['output'] == 'CO' for a in arcs['cfa']) == 6
          and all(a['sense'] == 'positive' for a in arcs['cfa']
                  if a['output'] == 'CO')
          and len(arcs['cmux4']) == 12
          and all(a['when'] for a in arcs['cmux4'])
          and len(arcs['cxor3']) == 12
          and {a['id'] for a in arcs['caoi22']}
          == {'A|B*!C*!D', 'B|A*!C*!D', 'C|!A*!B*D', 'D|!A*!B*C'}
          and {a['id'] for a in arcs['coai22']}
          == {'A|!B*C*!D', 'B|!A*C*!D', 'C|A*!B*!D', 'D|A*!B*!C'}
          and all(a['ties'] == {o: 1 for o in 'ABCD' if o != a['pin']}
                  for a in arcs['cnand4'])
          and all(a['ties'] == {o: 0 for o in 'ABCD' if o != a['pin']}
                  for a in arcs['cnor4'])
          and [(a['id'], a['ties']) for a in arcs['ctbuf']]
          == [('A|EN', {'EN': 1})]
          and [a['id'] for a in arcs['clatch']] == ['D|G']
          and all(a['output'] == 'Y' for a in arcs['cxnor2']),
          json.dumps({c: [a['id'] for a in v] for c, v in arcs.items()}))

    # ---- B. logic: truth tables, proofs ------------------------------
    tt_ok = []
    for c in NEW_COMBINATIONAL:
        cell = CELL_LIBRARY[c]
        tt = L.truth_table(c)
        ok = tt['count'] == 2 ** len(cell['inputs']) and all(
            r['outputs'] == {o: L.expected_output(cell, o, r['vector'])
                             for o in cell['outputs']}
            and r['output'] == r['outputs'][cell['output']]
            for r in tt['rows'])
        # the switch-level netlist agrees with every row
        ok = ok and all(
            L.switch_level_eval(c, r['vector'])['outputValues']
            == r['outputs'] for r in tt['rows'])
        tt_ok.append((c, ok))
    check('cells-2 truth tables: every new combinational cell — rows '
          'carry outputs{} (v2) = expected_output per output, and the '
          'switch-level netlist reproduces every row',
          all(ok for _c, ok in tt_ok), str(tt_ok))
    tt_x3 = [r['output'] for r in L.truth_table('cxor3')['rows']]
    tt_xn = [r['output'] for r in L.truth_table('cxnor2')['rows']]
    tt_m4 = L.truth_table('cmux4')['rows']
    check('cells-2 truth tables by value: XNOR2 = [1,0,0,1]; XOR3 = '
          'odd parity; MUX4 picks A/B/C/D by (S1,S0)',
          tt_xn == [1, 0, 0, 1]
          and tt_x3 == [0, 1, 1, 0, 1, 0, 0, 1]
          and all(r['output'] == r['vector'][
              'ABCD'[2 * r['vector']['S1'] + r['vector']['S0']]]
              for r in tt_m4))
    proofs = {c: L.prove_cell(c) for c in NEW_CELLS}
    check('cells-2 proof: prove_cell PROVES every new cell (13/13), '
          'zero contention, zero unexpected floating',
          all(p['proven'] for p in proofs.values())
          and not any(p['contention'] or p['floating']
                      for p in proofs.values()),
          json.dumps({c: p['note'] for c, p in proofs.items()
                      if not p['proven']}))
    pha, pfa = proofs['cha'], proofs['cfa']
    r_fa = L.switch_level_eval('cfa', {'A': 1, 'B': 0, 'CI': 1})
    check('cells-2 multi-output proof: cha/cfa proofs list outputs '
          '[S, CO] and check every output per vector (8 vectors x 2); '
          'switch_level_eval carries outputValues (FA 1+0+1: S=0, '
          'CO=1) with output = S (first, v1); cfa resolves its '
          'internal !CO gate net by fixed-point iteration',
          pha['outputs'] == ['S', 'CO'] and pfa['outputs'] == ['S', 'CO']
          and pfa['vectors'] == 8 and pha['vectors'] == 4
          and r_fa['outputValues'] == {'S': 0, 'CO': 1}
          and r_fa['output'] == 0 and r_fa['status'] == 'driven'
          and r_fa['statuses'] == {'S': 'driven', 'CO': 'driven'}
          and r_fa['nets']['cob'] == 0 and r_fa['nets']['sb'] == 1
          and 'x 2 output(s)' in pfa['note'],
          json.dumps(r_fa['outputValues']))
    dag_fa = L.cell_gate_dag('cfa')
    out_nodes = [n for n in dag_fa['nodes'] if n['kind'] == 'output']
    in_nodes = [n for n in dag_fa['nodes'] if n['kind'] == 'input']
    dv = L.dag_values(dag_fa, {'A': 1, 'B': 1, 'CI': 0})
    check('cells-2 gate DAG: cfa has ONE output node per output (S, '
          'CO), inputs shared once, dagValues(1,1,0) = S 0 / CO 1',
          [n['id'] for n in out_nodes] == ['S', 'CO']
          and [n['id'] for n in in_nodes] == ['A', 'B', 'CI']
          and dv['S'] == 0 and dv['CO'] == 1
          and len({n['id'] for n in dag_fa['nodes']})
          == len(dag_fa['nodes']))
    ng = L.netlist_graph('cfa')
    kinds = {n['id']: n['kind'] for n in ng['nets']}
    ngh = L.netlist_graph('cha', flatten=True)
    check('cells-2 netlist graph: cfa nets S and CO are kind output, '
          'cob/sb internal, 28 device rows placed; cha composed ports '
          'map each stage to its own output net, flattens to 16',
          kinds['S'] == 'output' and kinds['CO'] == 'output'
          and kinds['cob'] == 'internal' and kinds['sb'] == 'internal'
          and len(ng['devices']) == 28
          and all('x_hint' in d and 'y_hint' in d for d in ng['devices'])
          and [c['ports']['Y'] for c in ngh['composed']] == ['S', 'CO']
          and len(ngh['devices']) == 16)

    # ---- C. tri-state ------------------------------------------------
    z0 = L.switch_level_eval('ctbuf', {'A': 0, 'EN': 0})
    z1 = L.switch_level_eval('ctbuf', {'A': 1, 'EN': 0})
    e0 = L.switch_level_eval('ctbuf', {'A': 0, 'EN': 1})
    e1 = L.switch_level_eval('ctbuf', {'A': 1, 'EN': 1})
    ptb = proofs['ctbuf']
    check('cells-2 tri-state: ctbuf Y = Z for both EN=0 vectors '
          '(status floating, no conducting path to Y), Y = A for EN=1 '
          '(rail-driven through the 4T stack), and the proof counts the '
          'two Z vectors as EXPECTED (expectedFloating), PROVEN',
          z0['output'] == 'Z' and z1['output'] == 'Z'
          and z0['status'] == 'floating' and not z0['paths']
          and e0['output'] == 0 and e1['output'] == 1
          and e1['paths'] and e1['paths'][0]['to'] == 'vddn'
          and len(e1['paths'][0]['devices']) == 2
          and ptb['proven'] and ptb['floating'] == []
          and len(ptb['expectedFloating']) == 2
          and L.truth_table('ctbuf')['threeState'] == '(!EN)'
          and 'Z as REQUIRED' in ptb['note'],
          json.dumps(ptb))

    # ---- D. latch ------------------------------------------------------
    ss = L.state_space('clatch')
    kinds_t = {(t['from'], t['input']['G'], t['input']['D'], t['to'],
                t['kind']) for t in ss['transitions']}
    hold = [t for t in ss['transitions'] if t['kind'] == 'hold']
    check('cells-2 latch state space: 2 states, 8 transitions — '
          'G=1 follows D (follow/retain), G=0 holds Q whatever D does '
          '(4 hold transitions), every transition driven (no Z)',
          ss['kind'] == 'sequential' and ss['states'] == ['Q=0', 'Q=1']
          and len(ss['transitions']) == 8 and len(hold) == 4
          and all(t['to'] == t['from'] for t in hold)
          and {('Q=0', 1, 1, 'Q=1', 'follow'),
               ('Q=1', 1, 0, 'Q=0', 'follow'),
               ('Q=0', 1, 0, 'Q=0', 'retain'),
               ('Q=1', 1, 1, 'Q=1', 'retain')} <= kinds_t
          and all(t['status'] == 'driven' for t in ss['transitions'])
          and len(ss['phases']) == 2,
          json.dumps(ss['transitions'], default=str)[:600])
    hold_1 = L.latch_eval('clatch', {'D': 0, 'G': 0}, 1)
    check('cells-2 latch proof: exhaustive (G, D, Q_prev) = 8 cases '
          'PROVEN with the storage nodes seeded; in hold (G=0, D=0, '
          'Q_prev=1) the feedback TG conducts, the input TG does not, '
          'and Q is re-driven from VDD by the inverter pair',
          proofs['clatch']['proven'] and proofs['clatch']['vectors'] == 8
          and hold_1['outputValues'] == {'Q': 1}
          and hold_1['previousState'] == 1
          and hold_1['stored'] == {'m1': 1, 'm2': 0, 'Q': 1}
          and 'M8' in hold_1['conducting']
          and 'M2' not in hold_1['conducting']
          and 'M3' not in hold_1['conducting']
          and hold_1['paths'] and hold_1['paths'][0]['to'] == 'vddn',
          json.dumps(hold_1, default=str)[:600])

    # ---- E. reports + contract ---------------------------------------
    lib_logic = L.library_logic_report()
    rep = L.cell_logic_report('cfa')
    rep_l = L.cell_logic_report('clatch')
    contract = L.payload_contract()
    try:
        json.dumps(lib_logic)
        json.dumps(rep)
        json.dumps(rep_l)
        ser = True
    except TypeError:
        ser = False
    check('cells-2 reports: library_logic_report allProven over the '
          f'{len(COMBINATIONAL)}-cell combinational set AND the latch; '
          'payload v2 with outputs/outputValues/asts documented; '
          'cfa + clatch reports serialise',
          ser and lib_logic['allProven']
          and len(lib_logic['combinational']) == len(COMBINATIONAL)
          and lib_logic['multiOutput'] == ['cha', 'cfa']
          and lib_logic['sequentialProofs']['clatch']['proven']
          and 'clatch' in lib_logic['sequential']
          and L.LOGIC_PAYLOAD_VERSION == 2 and contract['version'] == 2
          and 'outputValues' in contract['switchLevel']['shape']
          and 'asts' in contract and 'latch' in contract['stateSpace']
          and rep['outputs'] == ['S', 'CO']
          and set(rep['asts']) == {'S', 'CO'}
          and rep['libertyFunctions']['CO'] == '((A*B)+(CI*(A+B)))'
          and rep['output'] == 'S' and rep['proof']['proven']
          and rep_l['sequential'] and rep_l['proof']['proven']
          and rep_l['stateSpace']['kind'] == 'sequential'
          and rep_l['netlist']['fet_count'] == 10)
    lr = library_report()
    check('cells-2 library_report names the multi-output, tri-state '
          '(Z arc not a timing arc) and latch faces',
          set(lr['multiOutput']) == {'cha', 'cfa'}
          and 'NOT characterized' in lr['tristate']['ctbuf']['honesty']
          and 'characterize_latch' in lr['sequential']['clatch']
          and lr['arcs']['clatch'] == ['D|G'])

    # ---- F. power: leakage states run for every new cell -------------
    leak = {c: cp.cell_leakage_states(c, 1, 1e-9, 1e-9, None)
            for c in NEW_CELLS}
    n4 = {s['when']: s for s in leak['cnand4']['states']}
    check('cells-2 power: cell_leakage_states runs for EVERY new cell, '
          'contention-free; NAND4 all-low = 4 series off n devices -> '
          'stack factor 0.5^3 = 0.125 Ioff (vs 1 Ioff with one off); '
          'tri-state / latch floating states are reported as such',
          all(not any(s['contention'] for s in r['states'])
              for r in leak.values())
          and all(r['fet_count'] == NEW_CELLS[c] for c, r in leak.items())
          and abs(n4['!A*!B*!C*!D']['i_leak_a'] - 0.125e-9) < 1e-15
          and abs(n4['A*B*C*!D']['i_leak_a'] - 1e-9) < 1e-15
          and any(s['output'] is None for s in leak['ctbuf']['states'])
          and all(s['output'] in (0, 1) for s in leak['cfa']['states']),
          json.dumps({c: [s['contention'] for s in r['states']
                          if s['contention']] for c, r in leak.items()}))

    # ---- G. Liberty emitter: multi-output blocks parse back ----------
    def _pt(scale):
        return {'cell_rise_s': 5e-13 * scale, 'cell_fall_s': 5e-13 * scale,
                'rise_transition_s': 6e-13 * scale,
                'fall_transition_s': 6e-13 * scale,
                'energy_rise_j': 2e-18 * scale, 'energy_fall_j': 1e-18}
    blocks = [{'libertyName': 'HAX1', 'function': '((A*!B)+(!A*B))',
               'outputs': ['S', 'CO'],
               'functions': {'S': '((A*!B)+(!A*B))', 'CO': '(A*B)'},
               'inputs': ['A', 'B'], 'inputCap_f': 1e-17,
               'arcs': {'S:A|!B': {'pin': 'A', 'sense': 'positive',
                                   'when': '!B', 'output': 'S',
                                   'tables': [[_pt(1)] * 2] * 2},
                        'CO:A|B': {'pin': 'A', 'sense': 'positive',
                                   'when': 'B', 'output': 'CO',
                                   'tables': [[_pt(2)] * 2] * 2}}},
              {'libertyName': 'TBUFX1', 'function': '(A)',
               'outputs': ['Y'], 'functions': {'Y': '(A)'},
               'three_state': '(!EN)',
               'inputs': ['A', 'EN'], 'inputCap_f': 1e-17,
               'arcs': {'A|EN': {'pin': 'A', 'sense': 'positive',
                                 'when': 'EN', 'output': 'Y',
                                 'tables': [[_pt(1)] * 2] * 2}}},
              # v1-shaped block (no outputs key) must still emit pin (Y)
              {'libertyName': 'INVX1', 'function': '(!A)',
               'inputs': ['A'], 'inputCap_f': 1e-17,
               'arcs': {'A': {'pin': 'A', 'sense': 'negative',
                              'tables': [[_pt(1)] * 2] * 2}}}]
    text = _liberty_library(0.6, [1e-12, 2e-12], [1e-17, 2e-17], blocks)
    parsed = parse_liberty(text)
    ha_blk = text.split('cell (HAX1)')[1].split('cell (TBUFX1)')[0]
    check('cells-2 Liberty: one `pin (<out>) { direction : output; '
          'function ... }` block PER OUTPUT with only its own arcs '
          '(HAX1: S carries A|!B, CO carries A|B), TBUFX1 carries '
          'three_state : "(!EN)", a v1 block still emits pin (Y); '
          'parse_liberty reads the multi-output block back (HONESTLY: '
          'it keys arcs by related pin, so the S and CO arcs of the '
          'same pin collapse to the first — reported, see the '
          'integrator diff)',
          ha_blk.count('direction : output') == 2
          and 'pin (S) {\n      direction : output;\n      function : '
              '"((A*!B)+(!A*B))";' in ha_blk
          and 'pin (CO) {\n      direction : output;\n      function : '
              '"(A*B)";' in ha_blk
          and ha_blk.split('pin (CO)')[0].count('related_pin') == 2
          and ha_blk.split('pin (CO)')[1].count('related_pin') == 2
          and 'when : "!B";' in ha_blk.split('pin (CO)')[0]
          and 'when : "B";' in ha_blk.split('pin (CO)')[1]
          and 'three_state : "(!EN)";' in text
          and 'pin (Y) {\n      direction : output;\n      function : '
              '"(!A)";' in text
          and set(parsed['cells']) == {'HAX1', 'TBUFX1', 'INVX1'}
          # multi-output cells key arcs '<out>:<pin>|<when>' (no
          # collapse across S/CO); single-output keys are unchanged
          and set(parsed['cells']['HAX1']['arcs'])
          == {'S:A|!B', 'CO:A|B'}
          and all(len(t) == 6
                  for t in parsed['cells']['HAX1']['arcs'].values())
          and len(parsed['cells']['TBUFX1']['arcs']['A']) == 6,
          text[:1500])

    # ---- H. characterization (real ngspice + OpenSTA, small grid) ----
    device = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1')
    cd.derive_device(mgr, device, parameter_factory=pfac)
    ngspice_path, why_ng = find_ngspice()
    openvaf_path, why_va = find_openvaf()
    if ngspice_path is None or openvaf_path is None:
        check('cells-2: characterization legs honestly SKIPPED — '
              f'{why_ng or why_va}', True)
        check('cells-2: latch characterization honestly SKIPPED', True)
    else:
        from cntfet.custom.cnt_cells import _tau_estimate
        from cntfet.cnt_cell_library_basis import _device_params
        params, _err = _device_params(mgr, device)
        tau = _tau_estimate({**params, 'ptype': 0}, 0.6)
        cin = 2.0 * params['cinv_f_per_m'] * params['lg_m'] + 2e-18
        refused = characterize_cells(
            mgr, device, cells=['clatch'], drives=(1,),
            slews_s=[2.0 * tau, 8.0 * tau], loads_f=[cin, 4.0 * cin],
            result_factory=st._row_factory(mgr, 'CellCharacterizationRun'))
        cells_to_run = ['cxnor2', 'cnand4', 'caoi22', 'cfa', 'ctbuf']
        lib = characterize_cells(
            mgr, device, cells=cells_to_run, drives=(1,),
            slews_s=[2.0 * tau, 8.0 * tau], loads_f=[cin, 4.0 * cin],
            result_factory=st._row_factory(mgr, 'CellCharacterizationRun'))
        cells = {c['libertyName']: c for c in lib.get('cells', [])}
        text = open(lib['libertyPath']).read() if lib.get('ok') else ''
        fa_arcs = cells.get('FAX1', {}).get('arcs', [])
        check('cells-2 characterization (S1, x1, 2x2): XNOR2 + NAND4 + '
              'AOI22 + FA (BOTH outputs, 18 arcs) + TBUF (EN=1 arc '
              'only) in ONE Liberty — every arc measured, monotone in '
              'load, zero failures, staGate ACCEPTED; a sequential '
              'cell (clatch) is refused BY NAME from this sweep',
              lib.get('ok')
              and set(cells) == {'XNOR2X1', 'NAND4X1', 'AOI22X1',
                                 'FAX1', 'TBUFX1'}
              and len(fa_arcs) == 18
              and sum(a.startswith('S:') for a in fa_arcs) == 12
              and sum(a.startswith('CO:') for a in fa_arcs) == 6
              and cells['TBUFX1']['arcs'] == ['A|EN']
              and cells['NAND4X1']['arcs'] == ['A', 'B', 'C', 'D']
              and all(m['monotoneInLoad'] for m in lib['monotone'])
              and not lib['failures']
              and lib['staGate'].get('ran')
              and lib['staGate'].get('accepted')
              and not refused.get('ok')
              and 'characterize_latch' in refused.get('error', ''),
              f'cells={lib.get("cells")}, failures={lib.get("failures")}, '
              f'sta={lib.get("staGate")}, err={lib.get("error")}, '
              f'refused={refused}')
        mids = _mid_delays(text) if text else {}
        fa_mid = mids.get('FAX1', {})
        check('cells-2 Liberty (live): FAX1 emits pin (S) and pin (CO) '
              'blocks with their own timing arcs (12 + 6), TBUFX1 '
              'emits three_state and ONE timing arc under when "EN", '
              'parse_liberty still reads every cell, NAND4 fall '
              '(4-stack discharge) is slower than its rise at the mid '
              'point',
              text.count('pin (S) {') == 1 and text.count('pin (CO) {') == 1
              and sum(k.startswith('S:') for k in fa_mid) == 12
              and sum(k.startswith('CO:') for k in fa_mid) == 6
              and 'three_state : "(!EN)";' in text
              and list(mids.get('TBUFX1', {})) == ['Y:A|EN']
              and set(parse_liberty(text)['cells']) == set(cells)
              and mids['NAND4X1']['Y:A'][1] > mids['NAND4X1']['Y:A'][0],
              f'mids={mids}')
        if lib.get('ok'):
            print(f'  grid: slews={lib["gridSlews_s"]} loads={lib["gridLoads_f"]}')
            for cname, rows in mids.items():
                for key, (cr, cf) in rows.items():
                    print(f'    {cname} {key}: cell_rise={cr} ps, '
                          f'cell_fall={cf} ps')
        # latch: own-loop bisection against the G falling edge
        lat = characterize_latch(
            mgr, device, iters=4,
            result_factory=st._row_factory(mgr, 'CellCharacterizationRun'))
        check('cells-2 latch characterization (own-loop, 4-iteration '
              'bisection): setup/hold vs the G FALLING edge for D rise '
              'and fall, the transparent D->Q delay for both edges '
              '(positive), a `latch (IQ, IQN)` Liberty with '
              'setup_falling/hold_falling that OpenSTA accepts; the '
              'G->Q open arc is stated as NOT characterized',
              lat.get('ok') and lat['cell'] == 'DLATCHX1'
              and all(lat['setup'][e]['ok'] and lat['hold'][e]['ok']
                      for e in ('rise', 'fall'))
              and all(lat['dToQ'][e]['delay_s'] > 0
                      and lat['dToQ'][e]['transition_s'] > 0
                      for e in ('rise', 'fall'))
              and 'latch (IQ, IQN) { enable : "G"; data_in : "D"; }'
              in open(lat['libertyPath']).read()
              and 'timing_type : setup_falling;' in open(lat['libertyPath']).read()
              and lat['staGate'].get('accepted')
              and 'NOT characterized' in lat['honesty']
              and lat['transients'] >= 12,
              f'lat={ {k: v for k, v in lat.items() if k != "definitions"} }')
        if lat.get('ok'):
            print(f'  latch: transients={lat["transients"]} '
                  f'setup(ps) rise={lat["setup"]["rise"]["value_s"] * 1e12:.4g} '
                  f'fall={lat["setup"]["fall"]["value_s"] * 1e12:.4g}; '
                  f'hold(ps) rise={lat["hold"]["rise"]["value_s"] * 1e12:.4g} '
                  f'fall={lat["hold"]["fall"]["value_s"] * 1e12:.4g}; '
                  f'D->Q(ps) rise={lat["dToQ"]["rise"]["delay_s"] * 1e12:.4g} '
                  f'fall={lat["dToQ"]["fall"]["delay_s"] * 1e12:.4g}')

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
