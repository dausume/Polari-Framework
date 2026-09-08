"""@module hwfpga.objects.fpga._shared — what the fpga row classes share (constants, seeds, helpers); split from fpga_basis.py (sap-2c)."""

SEED_REGISTER_MAPS = [
    {'name': 'hardware-runtime', 'base_address': 0x70000000,
     'bus': 'axi4lite',
     'description': 'Common Polari Hardware Runtime register map: '
                    'identity + status + command/config, with the '
                    'sim/hardware input mode MUX.'},
]
SEED_REGISTERS = [
    {'name': 'hardware-runtime-device-id', 'map_name': 'hardware-runtime',
     'offset': 0x0000, 'register': 'DEVICE_ID', 'access': 'const',
     'reset_value': 0x504C0001,
     'description': "Identity ('PL' + board 1) — hardwired."},
    {'name': 'hardware-runtime-version', 'map_name': 'hardware-runtime',
     'offset': 0x0004, 'register': 'VERSION', 'access': 'const',
     'reset_value': 0x00010000,
     'description': 'Register-map version 1.0 — hardwired.'},
    {'name': 'hardware-runtime-status', 'map_name': 'hardware-runtime',
     'offset': 0x0008, 'register': 'STATUS', 'access': 'ro',
     'reset_value': 0,
     'description': 'Live status: [15:0] heartbeat counter '
                    '(liveness), [23:16] the MUX-selected input '
                    'byte.'},
    {'name': 'hardware-runtime-faults', 'map_name': 'hardware-runtime',
     'offset': 0x000C, 'register': 'FAULTS', 'access': 'ro',
     'reset_value': 0, 'description': 'Fault flags (none modeled yet '
                                      '— honest zero).'},
    {'name': 'hardware-runtime-commands', 'map_name': 'hardware-runtime',
     'offset': 0x0010, 'register': 'COMMANDS', 'access': 'rw',
     'reset_value': 0, 'description': 'Command word from the MCU / '
                                      'Polari.'},
    {'name': 'hardware-runtime-config', 'map_name': 'hardware-runtime',
     'offset': 0x0020, 'register': 'CONFIG', 'access': 'rw',
     'reset_value': 0, 'description': 'Configuration word.'},
    {'name': 'hardware-runtime-mode-mux', 'map_name': 'hardware-runtime',
     'offset': 0x0024, 'register': 'MODE_MUX', 'access': 'rw',
     'reset_value': 0,
     'description': 'Input-source select (a real multiplexer): bit0 '
                    '0=sim counter, 1=hardware input pins.'},
    # The 4x4 LED demo: one rw register, 16 output pins — added as a
    # ROW, no generator change (pins_out is the generic mechanism).
    {'name': 'hardware-runtime-led-matrix', 'map_name': 'hardware-runtime',
     'offset': 0x0030, 'register': 'LED_MATRIX', 'access': 'rw',
     'reset_value': 0, 'pins_out': 16,
     'description': '4x4 LED matrix: bit(row*4+col) lights LED '
                    '(row, col); the low 16 bits drive pins.'},
]
SEED_FPGA_STATES = [
    {'name': 'renode-rig-fpga', 'device_id': 0, 'version': 0,
     'status': 0, 'faults': 0, 'commands': 0, 'config': 0,
     'mode_mux': 0},
]
