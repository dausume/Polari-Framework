"""
Selftest for cntfet.cnt_logic (fp-5: boolean AST, gate DAG, truth
tables, schematic graph, switch-level proof, state space).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_logic

Pure graph reasoning — no ngspice, no manager.
"""

import json
import sys

from cntfet import cnt_logic as L
from cntfet.cnt_cell_library import CELL_LIBRARY, COMBINATIONAL

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    # 1. AST
    ast = L.boolean_ast('(!(A*B))')
    check('AST of (!(A*B)) is not(and(A,B))',
          ast == {'op': 'not', 'args': [{'op': 'and', 'args': [
              {'op': 'var', 'name': 'A'}, {'op': 'var', 'name': 'B'}]}]},
          json.dumps(ast))
    ast_mux = L.boolean_ast('((A*!S)+(B*S))')
    check('AST precedence: ! binds tighter than * than +',
          ast_mux['op'] == 'or' and ast_mux['args'][0]['op'] == 'and'
          and ast_mux['args'][0]['args'][1]['op'] == 'not')

    # 2. gate DAG
    dag = L.gate_dag(L.boolean_ast('(!(A*B))'), 'cnand2')
    gates = [n for n in dag['nodes'] if n['kind'] == 'gate']
    outs = [n for n in dag['nodes'] if n['kind'] == 'output']
    check('cnand2 gate DAG: one NAND node with 2 inputs, one output',
          len(gates) == 1 and gates[0]['gate'] == 'NAND'
          and sorted(gates[0]['inputs']) == ['A', 'B'] and len(outs) == 1
          and outs[0]['inputs'] == [gates[0]['id']], json.dumps(dag))
    dag_inv = L.gate_dag(L.boolean_ast('(!A)'), 'cinv')
    dag_aoi = L.gate_dag(L.boolean_ast('(!((A*B)+C))'), 'caoi21')
    aoi_gates = sorted(n['gate'] for n in dag_aoi['nodes']
                       if n['kind'] == 'gate')
    dag_buf = L.gate_dag(L.boolean_ast('(A)'), 'cbuf')
    check('INV = NOT, AOI21 = NOR over AND, BUF = BUF; levels ordered',
          [n['gate'] for n in dag_inv['nodes'] if n['kind'] == 'gate']
          == ['NOT'] and aoi_gates == ['AND', 'NOR']
          and [n['gate'] for n in dag_buf['nodes'] if n['kind'] == 'gate']
          == ['BUF']
          and all(any(m['id'] == i and m['level'] < n['level']
                      for m in dag_aoi['nodes'])
                  for n in dag_aoi['nodes'] for i in n['inputs']))
    dv = L.dag_values(dag_aoi, {'A': 1, 'B': 1, 'C': 0})
    check('dag_values AOI21(1,1,0) -> Y=0', dv['Y'] == 0, str(dv))

    # 3. truth tables match evaluate() for every vector
    tt_ok = []
    for key in COMBINATIONAL:
        tt = L.truth_table(key)
        cell = CELL_LIBRARY[key]
        # cells-2: expected_output = the Liberty function, or 'Z'
        # where the cell's three_state holds (ctbuf)
        ok = tt['count'] == 2 ** len(tt['inputs']) and all(
            r['output'] == L.expected_output(cell, cell['output'],
                                             r['vector'])
            for r in tt['rows'])
        tt_ok.append((key, ok))
    check('truth tables of EVERY combinational cell (first output) '
          'match evaluate() for every vector',
          all(ok for _k, ok in tt_ok), str(tt_ok))
    tt_x = L.truth_table('cxor2')
    check('XOR2 truth table = [0,1,1,0]',
          [r['output'] for r in tt_x['rows']] == [0, 1, 1, 0])

    # 4. netlist graph
    ng = L.netlist_graph('cnand2')
    p_dev = [d for d in ng['devices'] if d['type'] == 'p']
    n_dev = [d for d in ng['devices'] if d['type'] == 'n']
    check('cnand2 netlist: 4 devices, p network on vdd, n stack to gnd',
          len(ng['devices']) == 4
          and all(d['source'] == 'vddn' and d['drain'] == 'Y' for d in p_dev)
          and any(d['source'] == '0' for d in n_dev)
          and any(d['drain'] == 'Y' for d in n_dev)
          and ng['fet_count'] == 4, json.dumps(ng))
    check('cnand2 placement hints: p above (y<0), n below (y>0), '
          'columns by gate net',
          all('x_hint' in d and 'y_hint' in d for d in ng['devices'])
          and all(d['y_hint'] < 0 for d in p_dev)
          and all(d['y_hint'] > 0 for d in n_dev)
          and {d['x_hint'] for d in ng['devices']} == {0, 1}
          and sorted(d['y_hint'] for d in n_dev) == [1, 2])
    kinds = {n['id']: n['kind'] for n in ng['nets']}
    check('cnand2 net kinds vdd/gnd/input/output/internal',
          kinds == {'vddn': 'vdd', '0': 'gnd', 'A': 'input',
                    'B': 'input', 'Y': 'output', 'mid': 'internal'},
          str(kinds))
    ng2 = L.netlist_graph('cnand2', drive=2)
    check('drive x2 doubles device rows', len(ng2['devices']) == 8
          and ng2['fet_count'] == 8)
    ngx = L.netlist_graph('cxor2')
    ngxf = L.netlist_graph('cxor2', flatten=True)
    check('cxor2 composed: 2 stages, flatten=True yields 10 devices '
          'with instance-prefixed internal nets',
          [c['sub_cell'] for c in ngx['composed']] == ['cnor2', 'caoi21']
          and ngx['composed'][1]['ports'] == {'A': 'A', 'B': 'B',
                                              'C': 'm1', 'Y': 'Y'}
          and len(ngxf['devices']) == 10 and ngxf['fet_count'] == 10
          and any(d['drain'] == 'X0.midp' for d in ngxf['devices'])
          and any(d['gate'] == 'm1' for d in ngxf['devices'])
          and all(d['id'].startswith('X') for d in ngxf['devices']),
          json.dumps(ngxf['devices']))

    # 5. switch level
    r = L.switch_level_eval('cinv', {'A': 0})
    check('INV A=0 -> Y=1 via the p device only',
          r['output'] == 1 and r['conducting'] == ['M0']
          and r['paths'] == [{'to': 'vddn', 'value': 1,
                              'devices': ['M0']}], json.dumps(r))
    outs = {}
    for a in (0, 1):
        for b in (0, 1):
            outs[(a, b)] = L.switch_level_eval('cnand2', {'A': a, 'B': b})
    r11 = outs[(1, 1)]
    check('NAND2 00/01/10 -> 1, 11 -> 0 with the two n devices in series',
          outs[(0, 0)]['output'] == 1 and outs[(0, 1)]['output'] == 1
          and outs[(1, 0)]['output'] == 1 and r11['output'] == 0
          and sorted(r11['conducting']) == ['M2', 'M3']
          and r11['paths'] == [{'to': '0', 'value': 0,
                                'devices': ['M2', 'M3']}],
          json.dumps(r11))
    mux_ok, mux_rows = True, []
    for a in (0, 1):
        for b in (0, 1):
            for s in (0, 1):
                rm = L.switch_level_eval('cmux2', {'A': a, 'B': b, 'S': s})
                want = b if s else a
                mux_rows.append((a, b, s, rm['output'], rm['status']))
                mux_ok &= rm['output'] == want and rm['status'] == 'driven'
                # the pass gate reaches the INPUT net, not a rail
                mux_ok &= any(p['to'] in ('A', 'B') for p in rm['paths'])
                mux_ok &= rm['nets']['sb'] == 1 - s
    check('MUX2 pass-gate cell: all 8 vectors driven from the selected '
          'INPUT net, no contention, sb resolved by iteration',
          mux_ok, str(mux_rows))

    # 6. proof of every combinational cell
    proofs = {k: L.prove_cell(k) for k in COMBINATIONAL}
    failed = {k: p for k, p in proofs.items() if not p['proven']}
    print('   proven:', [k for k, p in proofs.items() if p['proven']])
    check('prove_cell proves EVERY combinational cell, zero contention/'
          'floating', not failed and all(
              p['vectors'] == 2 ** len(CELL_LIBRARY[k]['inputs'])
              and not p['contention'] and not p['floating']
              for k, p in proofs.items()),
          json.dumps({k: p['note'] for k, p in failed.items()}))

    # 7. XOR2 composed stage by stage
    rx = L.switch_level_eval('cxor2', {'A': 1, 'B': 0})
    check('XOR2 composed evaluates stage by stage (NOR2 -> m1 -> AOI21)',
          [s['sub_cell'] for s in rx['stages']] == ['cnor2', 'caoi21']
          and rx['stages'][0]['output'] == 0
          and rx['stages'][0]['output_net'] == 'm1'
          and rx['stages'][1]['ports'] == {'A': 1, 'B': 0, 'C': 0}
          and rx['output'] == 1 and rx['nets']['m1'] == 0
          and all(d.startswith('X') for d in rx['conducting']),
          json.dumps(rx))

    # 8. state space
    ss = L.state_space('cnand2')
    check('combinational state space: 4 ordered steps with conducting sets',
          ss['count'] == 4 and [s['output'] for s in ss['steps']]
          == [1, 1, 1, 0] and all(s['conducting'] for s in ss['steps']))
    sd = L.state_space('cdff')
    check('cdff state space: 2 states, 4 rising-edge transitions '
          '(D=0/1 x Q=0/1)',
          sd['states'] == ['Q=0', 'Q=1'] and len(sd['transitions']) == 4
          and all(t['input']['CLK'] == 'rising'
                  and t['to'] == f"Q={t['input']['D']}"
                  for t in sd['transitions'])
          and {(t['from'], t['input']['D']) for t in sd['transitions']}
          == {('Q=0', 0), ('Q=0', 1), ('Q=1', 0), ('Q=1', 1)},
          json.dumps(sd['transitions']))
    check('cdff phases/latches parsed from the subckt (4 TGs, 5 inverters)',
          len(sd['phases']) == 2
          and sd['phases'][0]['conducting_tgs'] == ['Xtgi', 'Xtgb']
          and sd['phases'][1]['conducting_tgs'] == ['Xtgf', 'Xtgs']
          and len([i for i in sd['instances'] if i['kind'] == 'inverter'])
          == 5 and sd['latches'][0]['nodes'] == ['m1', 'm2', 'm3'],
          json.dumps(sd))
    st = L.step('cnand2', 3)
    check('step(cnand2, 3) = vector 11 with dagValues',
          st['vector'] == {'A': 1, 'B': 1} and st['output'] == 0
          and st['dagValues']['Y'] == 0 and st['boolean'] == 0)

    # 9. reports
    rep = L.cell_logic_report('cmux2')
    lib = L.library_logic_report()
    try:
        json.dumps(rep)
        json.dumps(lib)
        json.dumps(L.cell_logic_report('cdff'))
        json.dumps(L.payload_contract())
        ser = True
    except TypeError as exc:
        ser = False
        print('   not serialisable:', exc)
    check('reports JSON-serialisable with the contract keys',
          ser and set(rep) >= {'ok', 'cell', 'drive', 'function', 'inputs',
                               'output', 'ast', 'gateDag', 'truthTable',
                               'netlist', 'proof', 'stateSpace', 'fetCount',
                               'honesty'}
          and lib['allProven'] and 'cdff' in lib['sequential']
          # cells-2: payload v2 (additive; v1 keys keep their meaning)
          and L.LOGIC_PAYLOAD_VERSION == 2
          and L.payload_contract()['version'] == 2
          and '2' in L.payload_contract()['changelog'])
    bad = L.cell_logic_report('cnand99')
    check('unknown cell refuses, naming the library',
          bad['ok'] is False and 'cnand99' in bad['refusal']
          and 'cinv' in bad['library'] and 'cdff' in bad['library'])

    passed = sum(1 for _l, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
