"""
@module hwdigital.logic_compile_seed

ncg-3: the registered graph compiler ('hwdigital-logic') — the
circuit-world sibling of scoring's 'judicial-fork'. Domain rows in,
generated artifacts out, through the SAME GraphCompilerDefinition
seam (enable knob on the row, provenance on the artifacts). The C
side is COMPOSED, not reinvented: firmware talks to the design
through grpcbridge.custom.c_twin structs + hwfpga register defines — this
compiler only adds the HDL the diagram describes.

@consumers
  - hwdigital.logic_api (compile/download acts)
  - polariNoCode.graph_compilers (SEED_GRAPH_COMPILERS entry)
"""

from hwdigital.custom import logic_verilog as lv


def compile_logic_design(domain_rows):
    """Compiler-contract entry: {'manager', 'design_name'} ->
    {'definition': None, 'artifacts': [verilog, bench]}."""
    manager = domain_rows['manager']
    design_name = domain_rows['design_name']
    compiled = lv.compile_design(manager, design_name)
    header = (f'// compiledBy: hwdigital-logic (GraphCompiler seam)\n'
              f'// sourceRows: LogicBlockDesign {design_name} + its '
              f'LogicBlockNode rows\n')
    return {
        'definition': None,
        'artifacts': [
            {'kind': 'verilog', 'name': f'{design_name}.v',
             'text': header + compiled['verilog']},
            {'kind': 'verilog-bench', 'name': f'{design_name}_tb.v',
             'text': header + compiled['bench']},
        ],
        'clocked': compiled['clocked'],
    }


SEED_HWDIGITAL_COMPILER = {
    'name': 'hwdigital-logic',
    'domain': 'hwdigital',
    'compiler_ref': 'hwdigital.logic_compile_seed:compile_logic_design',
    'description': 'LogicBlockNode diagram rows -> synthesizable '
                   'Verilog + self-checking bench (python reference '
                   'evaluator supplies expected values); iCE40 is '
                   'the synthesis target family.',
    'enabled': True,
}
