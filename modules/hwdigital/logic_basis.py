"""
@module hwdigital.logic_basis

ncg-3: the DIGITAL-LOGIC no-code level — logic diagrams as rows, the
way the register map already is (hwfpga). A design is a set of
LogicBlockNode rows (gates, flops, counters, MUXes) wired by name;
the Verilog module, the self-checking bench, and the iCE40 synthesis
all GENERATE from these rows. Authoring is row-editing (CRUDE/editor
today, D3 palette when the frontend node family lands with Dustin).

Semantics the generators and the python evaluator (logic_sim) share:
  * every node has ONE output, `width` bits wide (default 1);
    multi-input gates reduce elementwise across equal-width inputs.
  * inputs_json lists source NODE NAMES in port order.
  * 'mux2' inputs are [a, b, sel] — out = sel ? b : a.
  * clocked nodes ('dff', 'counter') make the design clocked; reset
    is ACTIVE-LOW (the house convention hwfpga set).
  * 'counter' increments every clock; an optional second input is an
    enable.

@consumers
  - hwdigital.custom.logic_sim (the reference evaluator / teaching trace)
  - hwdigital.custom.logic_verilog (Verilog + bench + iCE40 generation)
  - hwdigital.logic_compile_seed (the registered graph compiler)
  - hwdigital.logic_api (the knob surface)
  - polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/logic/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from hwdigital.objects.logic._shared import CLOCKED_KINDS, NODE_KINDS, SEED_LOGIC_DESIGNS, SEED_LOGIC_NODES  # noqa: F401
from hwdigital.objects.logic.LogicBlockDesign import LogicBlockDesign  # noqa: F401
from hwdigital.objects.logic.LogicBlockNode import LogicBlockNode  # noqa: F401
