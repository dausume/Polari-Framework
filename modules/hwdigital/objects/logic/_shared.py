"""@module hwdigital.objects.logic._shared — what the logic row classes share (constants, seeds, helpers); split from logic_basis.py (sap-2c)."""

NODE_KINDS = ('input', 'output', 'const', 'and', 'or', 'xor', 'nand',
              'nor', 'not', 'buf', 'mux2', 'dff', 'counter')
CLOCKED_KINDS = ('dff', 'counter')
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
