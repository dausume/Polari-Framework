"""
@module hwfpga.fpga_basis

hwsim-3 (HARDWARE_SIMULATION_PLAN.md): the FPGA register map as DATA
— Dustin's directive made concrete: "polari has access to as many
knobs as possible … so that we can later make no-code states that can
allow no-code programming for these different components."

Every register of the Hardware Runtime map (hardware-architecture:
0x0000 Device ID … Commands/Config) is an OBJECT ROW. The Verilog
register block, the firmware C defines, and the Renode attachment are
all GENERATED from these rows — editing a row (a knob today, a
no-code state later) reprograms the component at every layer.

@consumers
  - hwfpga.fpga_verilog (the generators)
  - hwfpga.fpga_api (the knob surface)
  - polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class RegisterMapDefinition(treeObject):
    """One hardware register map (an FPGA block's programming model).
    Generation targets hang off THIS row; its registers are the
    RegisterDefinition rows naming it."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Where the block sits on the MCU bus (external FSMC space on the
        # STM32F4 rig (0x70000000 is unmapped on the Renode model) —
        # where a real external FPGA would live.
        base_address: int = 0x70000000,
        # Bus the generated slave speaks. 'axi4lite' is what Renode's
        # IntegrationLibrary drives; SPI transport rides later boards.
        bus: str = 'axi4lite',
        description: str = '',
        manager=None,
    ):
        self.name = name
        self.base_address = base_address
        self.bus = bus
        self.description = description


class RegisterDefinition(treeObject):
    """One register — one knob. access: 'const' (hardwired identity,
    e.g. Device ID), 'ro' (logic-driven, MCU reads), 'rw' (MCU/Polari
    write, logic obeys)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        map_name: str = '',
        offset: int = 0,
        register: str = '',
        access: str = 'rw',
        reset_value: int = 0,
        description: str = '',
        manager=None,
    ):
        self.name = name
        self.map_name = map_name
        self.offset = offset
        self.register = register
        self.access = access
        self.reset_value = reset_value
        self.description = description


class FpgaRegisterState(treeObject):
    """Digital twin of one rig's FPGA registers — the telemetry class
    the firmware streams after reading the (verilated) silicon, and
    the command surface: writing commands/config/mode_mux here reaches
    the FPGA through the bridge -> firmware -> bus write."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device_id: int = 0,
        version: int = 0,
        status: int = 0,
        faults: int = 0,
        commands: int = 0,
        config: int = 0,
        # THE MUX KNOB: selects which input source feeds STATUS[15:8]
        # (0 = sim counter, 1 = hardware pin stub) — a multiplexer's
        # select bits, exposed as a Polari field.
        mode_mux: int = 0,
        manager=None,
    ):
        self.name = name
        self.device_id = device_id
        self.version = version
        self.status = status
        self.faults = faults
        self.commands = commands
        self.config = config
        self.mode_mux = mode_mux


#: The Hardware Runtime map (hardware-architecture memory) as seed
#: rows — the standard programming model every Polari board shares.
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
]

SEED_FPGA_STATES = [
    {'name': 'renode-rig-fpga', 'device_id': 0, 'version': 0,
     'status': 0, 'faults': 0, 'commands': 0, 'config': 0,
     'mode_mux': 0},
]
