"""@module electrodevice.objects.circuit._shared — what the circuit row classes share (constants, seeds, helpers); split from circuit_basis.py (sap-2c)."""

COMPONENT_KINDS = ('vsource', 'resistor', 'capacitor', 'inductor',
                   'diode', 'led', 'device')
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
