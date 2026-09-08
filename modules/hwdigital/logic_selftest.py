"""
Selftest — ncg-3: digital-logic no-code -> Verilog -> Verilator +
iCE40.

Run from polari-framework/:
    python3 -m hwdigital.logic_selftest

The python reference evaluator proves the seeded designs' semantics
(truth table + counter behavior); the generated self-checking bench
then proves REAL VERILATED LOGIC agrees with python on the same
seeded vectors; the REAL iCE40 leg (yosys synth_ice40 ->
nextpnr-ice40 -> icepack/icetime) produces an actual bitstream.
Tool legs skip honestly when oss-cad-suite is absent (containers).
"""

import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from hwdigital.custom import logic_verilog as lv
from hwdigital.logic_basis import SEED_LOGIC_DESIGNS, SEED_LOGIC_NODES
from hwdigital.logic_compile_seed import compile_logic_design
from hwdigital.custom.logic_sim import (LogicSimulator, design_specs,
                                 is_clocked, load_design)
from polariNoCode.graph_compilers import compile_with

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    mgr = SimpleNamespace(objectTables={
        'LogicBlockDesign': {}, 'LogicBlockNode': {},
        'GraphCompilerDefinition': {}})
    for seed in SEED_LOGIC_DESIGNS:
        mgr.objectTables['LogicBlockDesign'][seed['name']] = (
            SimpleNamespace(**seed))
    for seed in SEED_LOGIC_NODES:
        mgr.objectTables['LogicBlockNode'][seed['name']] = (
            SimpleNamespace(**seed))
    return mgr


def _reference_evaluator():
    print('python reference evaluator (the design semantics)')
    m = _mgr()
    specs = design_specs(m, 'demo-alarm-gate')
    sim = LogicSimulator(specs)
    table = []
    for door in (0, 1):
        for disarmed in (0, 1):
            for panic in (0, 1):
                sim.set_inputs(**{'alarm-door': door,
                                  'alarm-disarmed': disarmed,
                                  'alarm-panic': panic})
                table.append(sim.outputs()['alarm-out'])
    # (door & ~disarmed) | panic over the 8 rows above:
    check('alarm gate truth table exact',
          table == [0, 1, 0, 1, 1, 1, 0, 1], f'{table}')
    check('combinational design reports unclocked',
          not is_clocked(specs))

    specs = design_specs(m, 'demo-counter2')
    sim = LogicSimulator(specs)
    sim.set_inputs(**{'cnt2-en': 1})
    seen = [sim.outputs()['cnt2-q']]
    for _ in range(4):
        sim.step()
        seen.append(sim.outputs()['cnt2-q'])
    check('2-bit counter counts 0,1,2,3 and wraps to 0',
          seen == [0, 1, 2, 3, 0], f'{seen}')
    sim.set_inputs(**{'cnt2-en': 0})
    frozen = sim.step()['cnt2-counter']
    check('enable=0 freezes the counter', frozen == 0)

    cyc = _mgr()
    cyc.objectTables['LogicBlockNode']['loop-a'] = SimpleNamespace(
        name='loop-a', design_name='demo-alarm-gate', kind='buf',
        params_json='{}', inputs_json='["loop-b"]', description='')
    cyc.objectTables['LogicBlockNode']['loop-b'] = SimpleNamespace(
        name='loop-b', design_name='demo-alarm-gate', kind='buf',
        params_json='{}', inputs_json='["loop-a"]', description='')
    try:
        design_specs(cyc, 'demo-alarm-gate')
        LogicSimulator(design_specs(cyc, 'demo-alarm-gate'))
        caught = False
    except ValueError as exc:
        caught = 'cycle' in str(exc)
    check('combinational cycle is a plain error (suggests a dff)',
          caught)


def _compiler_seam():
    print('the registered compiler (artifact-only contract)')
    m = _mgr()
    row = SimpleNamespace(
        name='hwdigital-logic', domain='hwdigital',
        compiler_ref='hwdigital.logic_compile_seed:compile_logic_design',
        enabled=True)
    result = compile_with(row, {'manager': m,
                                'design_name': 'demo-counter2'})
    kinds = sorted(a['kind'] for a in result['artifacts'])
    check('compiler emits verilog + bench artifacts, no solution '
          'graph', result['definition'] is None
          and kinds == ['verilog', 'verilog-bench'])
    verilog = next(a['text'] for a in result['artifacts']
                   if a['kind'] == 'verilog')
    check('artifact carries its provenance header',
          'compiledBy: hwdigital-logic' in verilog
          and 'LogicBlockDesign demo-counter2' in verilog)
    check('clocked design gets clk + ACTIVE-LOW rst ports',
          'input  wire clk' in verilog and 'if (!rst)' in verilog)
    disabled = SimpleNamespace(name='hwdigital-logic', domain='x',
                               compiler_ref=row.compiler_ref,
                               enabled=False)
    try:
        compile_with(disabled, {'manager': m,
                                'design_name': 'demo-counter2'})
        refused = False
    except RuntimeError as exc:
        refused = 'disabled' in str(exc)
    check('disabled compiler row refuses (the knob)', refused)


def _review_regressions():
    print('review regressions (masked literals, identifier safety)')
    m = _mgr()
    # A design with NEGATIVE const + init: python masks (-1 @ w2 ->
    # 3); the rendered Verilog must carry the SAME masked bits, not
    # an invalid 2'h-1 literal.
    m.objectTables['LogicBlockDesign']['neg-lit'] = SimpleNamespace(
        name='neg-lit', display_name='negative literals',
        description='', target='sim', notes='')
    for seed in (
            {'name': 'neg-en', 'design_name': 'neg-lit',
             'kind': 'input', 'params_json': '{"width": 1}',
             'inputs_json': '[]', 'description': ''},
            {'name': 'neg-cnt', 'design_name': 'neg-lit',
             'kind': 'counter',
             'params_json': '{"width": 2, "init": -1}',
             'inputs_json': '["neg-en"]', 'description': ''},
            {'name': 'neg-k', 'design_name': 'neg-lit',
             'kind': 'const',
             'params_json': '{"width": 2, "value": -1}',
             'inputs_json': '[]', 'description': ''},
            {'name': 'neg-and', 'design_name': 'neg-lit',
             'kind': 'and', 'params_json': '{"width": 2}',
             'inputs_json': '["neg-cnt", "neg-k"]',
             'description': ''},
            {'name': 'neg-q', 'design_name': 'neg-lit',
             'kind': 'output', 'params_json': '{"width": 2}',
             'inputs_json': '["neg-and"]', 'description': ''}):
        m.objectTables['LogicBlockNode'][seed['name']] = (
            SimpleNamespace(**seed))
    design, _ = load_design(m, 'neg-lit')
    specs = design_specs(m, 'neg-lit')
    sim = LogicSimulator(specs)
    check('python masks negative init/const (-1 @ w2 -> 3)',
          sim.outputs()['neg-q'] == 3,
          f"q={sim.outputs()['neg-q']}")
    verilog = lv.render_module(design, specs)
    check('rendered Verilog carries the SAME masked literals '
          "(2'h3, never 2'h-1)",
          "2'h3" in verilog and "'h-" not in verilog)
    with tempfile.TemporaryDirectory() as td:
        bench = lv.run_bench(design, specs, td)
        check('verilated logic still agrees with python on the '
              'negative-literal design',
              bench['status'] in ('pass', 'skip-honest'),
              f"{bench['status']}: {bench['evidence'][:80]}")

    reserved = _mgr()
    reserved.objectTables['LogicBlockNode']['clk'] = SimpleNamespace(
        name='clk', design_name='demo-alarm-gate', kind='input',
        params_json='{"width": 1}', inputs_json='[]', description='')
    try:
        design_specs(reserved, 'demo-alarm-gate')
        refused = False
    except ValueError as exc:
        refused = 'reserved' in str(exc)
    check("a node named 'clk' is refused plainly (reserved port)",
          refused)

    colliding = _mgr()
    for name in ('alarm-x_y', 'alarm-x-y'):
        colliding.objectTables['LogicBlockNode'][name] = (
            SimpleNamespace(name=name,
                            design_name='demo-alarm-gate',
                            kind='input',
                            params_json='{"width": 1}',
                            inputs_json='[]', description=''))
    try:
        design_specs(colliding, 'demo-alarm-gate')
        refused = False
    except ValueError as exc:
        refused = 'sanitization' in str(exc)
    check('names colliding after kebab sanitization are refused '
          'naming both', refused)


def _verilated_and_synthesized():
    print('real tools: verilated bench + iCE40 synthesis')
    m = _mgr()
    for design_name in ('demo-alarm-gate', 'demo-counter2'):
        design, _ = load_design(m, design_name)
        specs = design_specs(m, design_name)
        with tempfile.TemporaryDirectory() as td:
            bench = lv.run_bench(design, specs, td)
            check(f'{design_name}: verilated logic agrees with '
                  f'python on every seeded vector',
                  bench['status'] in ('pass', 'skip-honest'),
                  f"{bench['status']}: {bench['evidence'][:90]}")
        with tempfile.TemporaryDirectory() as td:
            synth = lv.run_ice40_synth(design, specs, td)
            check(f'{design_name}: iCE40 synth+PnR+bitstream',
                  synth['status'] in ('pass', 'skip-honest'),
                  f"{synth['status']}: {synth['evidence'][:90]}")


def main():
    _reference_evaluator()
    _compiler_seam()
    _review_regressions()
    _verilated_and_synthesized()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
