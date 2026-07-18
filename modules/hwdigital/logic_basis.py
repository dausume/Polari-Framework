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
  - hwdigital.logic_sim (the reference evaluator / teaching trace)
  - hwdigital.logic_verilog (Verilog + bench + iCE40 generation)
  - hwdigital.logic_compile (the registered graph compiler)
  - hwdigital.logic_api (the knob surface)
  - polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit

NODE_KINDS = ('input', 'output', 'const', 'and', 'or', 'xor', 'nand',
              'nor', 'not', 'buf', 'mux2', 'dff', 'counter')
CLOCKED_KINDS = ('dff', 'counter')


class LogicBlockDesign(treeObject):
    """One digital design — the unit that compiles to a Verilog
    module, simulates behind Renode, and synthesizes for iCE40."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 description: str = '',
                 # 'ice40' is the synthesis target family (Dustin
                 # 2026-07-16); 'sim' designs skip the synth leg.
                 target: str = 'ice40',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.target = target
        self.notes = notes


class LogicBlockNode(treeObject):
    """One logic block on a design's diagram — a row, configurable
    at the row."""

    @treeObjectInit
    def __init__(self, name: str = '', design_name: str = '',
                 kind: str = 'and',
                 # JSON dict: width (default 1), value (const),
                 # init (dff/counter reset value).
                 params_json: str = '{}',
                 # JSON list of source node names, in port order.
                 inputs_json: str = '[]',
                 description: str = '', manager=None):
        self.name = name
        self.design_name = design_name
        self.kind = kind
        self.params_json = params_json
        self.inputs_json = inputs_json
        self.description = description


#: Demo designs, seeded as real content: the 2-bit counter that can
#: drive the LED grid's low pins, and a combinational alarm gate.
SEED_LOGIC_DESIGNS = [
    {
        'name': 'demo-counter2',
        'display_name': '2-bit counter',
        'description': 'Free-running 2-bit counter with a gated '
                       'enable — the smallest clocked design worth '
                       'synthesizing; its output can bind to LED '
                       'grid pins (ncg-6).',
        'target': 'ice40',
    },
    {
        'name': 'demo-alarm-gate',
        'display_name': 'alarm gate',
        'description': 'Combinational (door AND NOT disarmed) OR '
                       'panic — the truth-table teaching example.',
        'target': 'ice40',
    },
]

SEED_LOGIC_NODES = [
    # demo-counter2: counter enabled by an input pin.
    {'name': 'cnt2-en', 'design_name': 'demo-counter2',
     'kind': 'input', 'params_json': '{"width": 1}',
     'inputs_json': '[]', 'description': 'count enable'},
    {'name': 'cnt2-counter', 'design_name': 'demo-counter2',
     'kind': 'counter', 'params_json': '{"width": 2, "init": 0}',
     'inputs_json': '["cnt2-en"]', 'description': ''},
    {'name': 'cnt2-q', 'design_name': 'demo-counter2',
     'kind': 'output', 'params_json': '{"width": 2}',
     'inputs_json': '["cnt2-counter"]', 'description': 'count value'},
    # demo-alarm-gate: (door & ~disarmed) | panic.
    {'name': 'alarm-door', 'design_name': 'demo-alarm-gate',
     'kind': 'input', 'params_json': '{"width": 1}',
     'inputs_json': '[]', 'description': ''},
    {'name': 'alarm-disarmed', 'design_name': 'demo-alarm-gate',
     'kind': 'input', 'params_json': '{"width": 1}',
     'inputs_json': '[]', 'description': ''},
    {'name': 'alarm-panic', 'design_name': 'demo-alarm-gate',
     'kind': 'input', 'params_json': '{"width": 1}',
     'inputs_json': '[]', 'description': ''},
    {'name': 'alarm-not-disarmed', 'design_name': 'demo-alarm-gate',
     'kind': 'not', 'params_json': '{"width": 1}',
     'inputs_json': '["alarm-disarmed"]', 'description': ''},
    {'name': 'alarm-armed-door', 'design_name': 'demo-alarm-gate',
     'kind': 'and', 'params_json': '{"width": 1}',
     'inputs_json': '["alarm-door", "alarm-not-disarmed"]',
     'description': ''},
    {'name': 'alarm-trigger', 'design_name': 'demo-alarm-gate',
     'kind': 'or', 'params_json': '{"width": 1}',
     'inputs_json': '["alarm-armed-door", "alarm-panic"]',
     'description': ''},
    {'name': 'alarm-out', 'design_name': 'demo-alarm-gate',
     'kind': 'output', 'params_json': '{"width": 1}',
     'inputs_json': '["alarm-trigger"]', 'description': ''},
]
