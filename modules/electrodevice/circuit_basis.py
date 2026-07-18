"""
@module electrodevice.circuit_basis

ncg-4: CIRCUITS PROMOTED TO DATA. spice_run.py's hand-coded netlist
renderers become rows: a CircuitDefinition owns CircuitComponentDefinition
rows (components, pins wired by NET NAME) and CircuitNetDefinition
rows (the declared nets — documentation + drift visibility). The
netlist GENERATES from the rows (circuit_netlist), through the same
GraphCompilerDefinition seam as judicial forks and logic designs.

Standard promotion protocol per component kind (hwsim-5): parameters
come from an msci-derived device row (kind 'device' → the derived
subckt card, provenance attached) or an explicit value with the row
as its honest record. Net '0' is SPICE ground by convention.

@consumers
  - electrodevice.circuit_netlist (the generator/runner)
  - electrodevice.circuit_api (the knob surface)
  - polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit

COMPONENT_KINDS = ('vsource', 'resistor', 'capacitor', 'inductor',
                   'diode', 'led', 'device')


class CircuitDefinition(treeObject):
    """One circuit — the unit that renders to a netlist and runs."""

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '',
                 # JSON list of analyses, run in order. Shapes:
                 #   {'type': 'op'}
                 #   {'type': 'tran', 'args': '<step> <stop>',
                 #    'meas': '<full ngspice meas expression>'}
                 analyses_json: str = '[{"type": "op"}]',
                 # JSON list of 'print' probes for op analyses
                 # (one per line — table output defeats the parser).
                 probes_json: str = '[]',
                 notes: str = '', manager=None):
        self.name = name
        self.description = description
        self.analyses_json = analyses_json
        self.probes_json = probes_json
        self.notes = notes


class CircuitNetDefinition(treeObject):
    """One declared net. Components may reference undeclared nets —
    that is a SUGGESTION (declare or fix the typo), never a silent
    pass or a hard stop."""

    @treeObjectInit
    def __init__(self, name: str = '', circuit_name: str = '',
                 net: str = '', is_ground: bool = False,
                 description: str = '', manager=None):
        self.name = name
        self.circuit_name = circuit_name
        self.net = net
        self.is_ground = is_ground
        self.description = description


class CircuitComponentDefinition(treeObject):
    """One placed component. pins_json wires it: an ordered JSON
    list of net names (order = the SPICE element's node order)."""

    @treeObjectInit
    def __init__(self, name: str = '', circuit_name: str = '',
                 kind: str = 'resistor',
                 # kind-specific values: vsource {'dc': V},
                 # resistor {'ohms': R}, capacitor {'farads': C,
                 # 'ic': V?}, inductor {'henries': L},
                 # diode/led {'model': name?}.
                 params_json: str = '{}',
                 pins_json: str = '[]',
                 # kind 'device': the ElectronicDeviceDefinition row
                 # whose DERIVED card supplies the subckt (material
                 # provenance rides that card).
                 device_name: str = '',
                 description: str = '', manager=None):
        self.name = name
        self.circuit_name = circuit_name
        self.kind = kind
        self.params_json = params_json
        self.pins_json = pins_json
        self.device_name = device_name
        self.description = description


#: Seeded circuits: one LED branch exactly as the proven
#: fpga-pin-led grid drives it (the row-form regression target), and
#: the RC lowpass that PROMOTES THE CAPACITOR (t63 must land at RC).
SEED_CIRCUITS = [
    {
        'name': 'led-branch-row',
        'description': 'One fpga-pin-led branch AS ROWS: pin source '
                       '-> derived CNT sol-gel resistor -> LED -> '
                       'ground. Must reproduce the hand renderer\'s '
                       'proven leg current (2.6123 mA at 3.3 V).',
        'analyses_json': '[{"type": "op"}]',
        'probes_json': '["i(vvpin0)"]',
    },
    {
        'name': 'rc-lowpass-demo',
        'description': 'Capacitor promotion: 10k + 1uF, tau = 10 ms '
                       '— the measured 63% rise time must land on '
                       'RC.',
        'analyses_json': '[{"type": "tran", "args": "0.1m 60m", '
                         '"meas": "tran t63 when v(out)=2.086 '
                         'rise=1"}]',
        'probes_json': '[]',
    },
]

SEED_CIRCUIT_NETS = [
    {'name': 'led-net-pin0', 'circuit_name': 'led-branch-row',
     'net': 'pin0', 'description': 'FPGA pin (driven rail)'},
    {'name': 'led-net-mid0', 'circuit_name': 'led-branch-row',
     'net': 'mid0', 'description': 'resistor->LED junction'},
    {'name': 'led-net-gnd', 'circuit_name': 'led-branch-row',
     'net': '0', 'is_ground': True, 'description': 'ground'},
    {'name': 'rc-net-in', 'circuit_name': 'rc-lowpass-demo',
     'net': 'in', 'description': 'source rail'},
    {'name': 'rc-net-out', 'circuit_name': 'rc-lowpass-demo',
     'net': 'out', 'description': 'RC output'},
    {'name': 'rc-net-gnd', 'circuit_name': 'rc-lowpass-demo',
     'net': '0', 'is_ground': True, 'description': 'ground'},
]

SEED_CIRCUIT_COMPONENTS = [
    # led-branch-row (the device row is the SEEDED
    # cnt-solgel-led-resistor from electrodevice, derived live).
    {'name': 'vpin0', 'circuit_name': 'led-branch-row',
     'kind': 'vsource', 'params_json': '{"dc": 3.3}',
     'pins_json': '["pin0", "0"]', 'description': 'the FPGA pin'},
    {'name': 'rlimit0', 'circuit_name': 'led-branch-row',
     'kind': 'device', 'params_json': '{}',
     'pins_json': '["pin0", "mid0"]',
     'device_name': 'cnt-solgel-led-resistor',
     'description': 'derived CNT sol-gel current limiter'},
    {'name': 'dled0', 'circuit_name': 'led-branch-row',
     'kind': 'led', 'params_json': '{}',
     'pins_json': '["mid0", "0"]', 'description': 'indicator LED'},
    # rc-lowpass-demo.
    {'name': 'vin', 'circuit_name': 'rc-lowpass-demo',
     'kind': 'vsource', 'params_json': '{"dc": 3.3}',
     'pins_json': '["in", "0"]', 'description': ''},
    {'name': 'r1', 'circuit_name': 'rc-lowpass-demo',
     'kind': 'resistor', 'params_json': '{"ohms": 10000}',
     'pins_json': '["in", "out"]', 'description': ''},
    {'name': 'c1', 'circuit_name': 'rc-lowpass-demo',
     'kind': 'capacitor', 'params_json': '{"farads": 1e-6, "ic": 0}',
     'pins_json': '["out", "0"]', 'description': ''},
]
