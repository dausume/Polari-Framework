"""
@module grpcbridge.mapping_basis

The computer↔firmware MAPPING as data (grpc-j4 / brd-wire, his ruling 2026-10-02; GRPC_BRIDGE_PLAN.md §grpc-j4): the
INDEX of the mapping rows (one class per file under objects/mapping/) and their seeds.

Seeds (code-owned demonstrations, every value says why):
  * four EnumMappings — SimRigState.status ∈ {boot, ok, commanded, echoed, fault} (the words the UNO firmwares and the
    Renode twin report), UnoAnalogState.status ∈ {boot, ok, fault}; ucd-0e1: ButtonClockState.status ∈ {idle,
    commanded, synced, snapshot} and ButtonClockEvent.kind ∈ {press, led_on, led_off, sense_rise, sense_fall, sync}
    (UNO_CORE_DEMO_PLAN.md §1/§5g — the button-clock demo's two new wire classes);
  * two HardwareInterfaceBindings on ONE bridge, `uno-pair`: SimRigState rows uno-twin-0 / uno-twin-1 ↔ two simavr UNO
    twins (board instances twin:arduino-uno-r3#0 / #1, USART0 behind each twin's pty link) — two instances of one class
    on one bridge → a 1-bit instance index (index_width(2) == 1);
  * ucd-0e1: SEED_BUTTON_CLOCK_BRIDGE — a HardwareBridgeDefinition dict (`button-clock`) exposing
    [ButtonClockState, ButtonClockEvent] (msg_type 1/2), source serial, baud 115200 — code-owned data a test
    constructs into the real row class, the same idiom as the bindings above (no bridge row is seeded live either:
    uno-pair has none; generation is always an explicit knob act, never automatic).
WireContract rows are DERIVED (wire_contract.derive) from the live exposure's field map + these rows — never seeded,
because the field order belongs to the server's contract ledger.

@consumers
  - polariServer (registration + seed, beside the other grpcbridge rows)
  - grpcbridge.custom.wire_contract (enum tables with no manager)
"""
import json

from grpcbridge.objects.mapping.HardwareInterfaceBinding import HardwareInterfaceBinding  # noqa: F401
from grpcbridge.objects.mapping.EnumMapping import EnumMapping  # noqa: F401
from grpcbridge.objects.mapping.WireContract import WireContract  # noqa: F401

PAIR_BRIDGE = 'uno-pair'


def _enum(cls, field, labels, notes):
    return {'name': '%s.%s' % (cls, field), 'object_class': cls, 'field': field, 'labels_json': json.dumps(labels),
            'unknown_label': 'unknown', 'wire_type': 'u8', 'origin': 'seeded', 'notes': notes}


SEED_ENUM_MAPPINGS = [
    _enum('ButtonClockEvent', 'kind', ['press', 'led_on', 'led_off', 'sense_rise', 'sense_fall', 'sync'],
          'ucd-0e1: one label per transition the device queues (UNO_CORE_DEMO_PLAN.md §1): a debounced D2 press, the LED '
          'actually changing (led_on/led_off), an edge independently sensed on D3 (sense_rise/sense_fall), or a SET_TIME '
          'applied (sync). Wire: 1 byte (0 = unknown).'),
    _enum('ButtonClockState', 'status', ['idle', 'commanded', 'synced', 'snapshot'],
          'ucd-0e1: idle (no command yet) | commanded (a PUT applied, not a time sync) | synced (SET_TIME applied) | '
          'snapshot (this frame answers a SNAPSHOT request). Wire: 1 byte (0 = unknown).'),
    _enum('SimRigState', 'status', ['boot', 'ok', 'commanded', 'echoed', 'fault'],
          'the status words the UNO firmwares (sim_rig, blink, echo) and the Renode twin report; fault is reserved for a '
          'firmware that detects one. Wire: 1 byte (0 = unknown) instead of a u16-prefixed string of up to 9 bytes.'),
    _enum('UnoAnalogState', 'status', ['boot', 'ok', 'fault'], 'the analog sweep reports boot → ok after 1 s.'),
    _enum('LightState', 'source', ['command', 'button'],
          'ucd-light: who made the last change to the light — command (a person asked from the screen) or button (the '
          'pushbutton on the board). Wire: 1 byte (0 = unknown).'),
    _enum('LightState', 'status', ['idle', 'active'],
          'ucd-light: idle until the light first changes after the board starts, then active. Wire: 1 byte (0 = unknown).'),
    # fgm-6a: LightStateV2 (a NEW class beside LightState): the same two enums + the board's answer to a command
    _enum('LightStateV2', 'source', ['command', 'button'],
          'fgm-6a: who made the last change to the light -- command or button. Wire: 1 byte (0 = unknown).'),
    _enum('LightStateV2', 'status', ['idle', 'active'],
          'fgm-6a: idle until the light first changes after the board starts, then active. Wire: 1 byte (0 = unknown).'),
    _enum('LightStateV2', 'last_command_result', ['applied', 'rejected-invalid', 'rejected-busy'],
          'fgm-6a (FIRMWARE_GENERATION_MODULE_PLAN.md 7.8.3): how the board answered the command named by last_command_id -- applied '
          '(done, or already done), rejected-invalid (malformed: no command number, no light value) or rejected-busy (the board could '
          'not take it now). Wire: 1 byte (0 = unknown, i.e. no command answered since the board started).'),
]


def _bind(k):
    return {'name': '%s/SimRigState/%d' % (PAIR_BRIDGE, k), 'bridge_name': PAIR_BRIDGE, 'object_class': 'SimRigState',
            'object_name': 'uno-twin-%d' % k, 'board_instance': 'twin:arduino-uno-r3#%d' % k, 'board_definition': 'arduino-uno-r3',
            'interface_kind': 'twin-pty', 'interface_name': 'usart0', 'port': '/tmp/polari-uno-twin-%d-uart' % k, 'adapter': '',
            'instance_index': k, 'wire_version': 2, 'origin': 'seeded',
            'notes': 'the uno-pair demonstration: the SAME firmware built with instance_index %d, run in simavr twin #%d; '
                     'its USART0 reaches the host at the pty link (pol board twin uno up --tag %d)' % (k, k, k)}


SEED_HARDWARE_BINDINGS = [_bind(0), _bind(1)]

#: ucd-0e1: the button-clock demo's bridge (HardwareBridgeDefinition fields, code-owned — a test constructs the real
#: row class from this dict the same way _bind()'s dicts become HardwareInterfaceBinding rows above). msg_type on the
#: wire is (index + 1) in exposed_classes_json: ButtonClockState=1, ButtonClockEvent=2.
BUTTON_CLOCK_BRIDGE = 'button-clock'
SEED_BUTTON_CLOCK_BRIDGE = {
    'name': '%s-hw-bridge' % BUTTON_CLOCK_BRIDGE, 'bridge_name': BUTTON_CLOCK_BRIDGE, 'source': 'serial',
    'serial_device': '/dev/ttyACM0', 'baud': 115200,
    'exposed_classes_json': json.dumps(['ButtonClockState', 'ButtonClockEvent']),
    'sim_rate_hz': 10, 'grpc_enabled': False, 'grpc_target': 'localhost:3002', 'device_id': 1,
    'last_generated_at': '', 'manifest_json': '{}', 'contract_hashes_json': '{}',
    'notes': 'ucd-0e1: the button-clock demo\'s bridge (UNO_CORE_DEMO_PLAN.md §3 "Bridge"); source=serial (the real '
             'device, not the internal simulation) at the kit\'s 115200 baud.',
}

#: ucd-light: the light test's bridge — ONE wire class (LightState = msg_type 1), source serial at the kit's 115200 baud.
LIGHT_BRIDGE = 'uno-light'
SEED_LIGHT_BRIDGE = {
    'name': '%s-bridge' % LIGHT_BRIDGE, 'bridge_name': LIGHT_BRIDGE, 'source': 'serial',
    'serial_device': '/dev/ttyACM0', 'baud': 115200,
    'exposed_classes_json': json.dumps(['LightState']),
    'sim_rate_hz': 10, 'grpc_enabled': False, 'grpc_target': 'localhost:3002', 'device_id': 1,
    'last_generated_at': '', 'manifest_json': '{}', 'contract_hashes_json': '{}',
    'notes': 'The light test\'s bridge: the board\'s serial link to Polari carries one struct, LightState, in both '
             'directions (the light\'s state up, the on/off command down).',
}

#: fgm-6a: the v2 light's bridge -- ONE wire class (LightStateV2 = msg_type 1), same serial link as the v1 light test. Opt-in: the
#: v1 bridge (uno-light) stays the default; this one is for a board running the uno-light-v2 firmware.
LIGHT_V2_BRIDGE = 'uno-light-v2'
SEED_LIGHT_V2_BRIDGE = {
    'name': '%s-bridge' % LIGHT_V2_BRIDGE, 'bridge_name': LIGHT_V2_BRIDGE, 'source': 'serial',
    'serial_device': '/dev/ttyACM0', 'baud': 115200,
    'exposed_classes_json': json.dumps(['LightStateV2']),
    'sim_rate_hz': 10, 'grpc_enabled': False, 'grpc_target': 'localhost:3002', 'device_id': 1,
    'last_generated_at': '', 'manifest_json': '{}', 'contract_hashes_json': '{}',
    'notes': 'fgm-6a: the v2 light\'s bridge -- one struct, LightStateV2, in both directions: the light\'s state up, the on/off command '
             '(with its command number) down, and the board\'s answer to the command (last_command_id / last_command_result) up.',
}

#: every mapping row class, in registration order
MAPPING_CLASSES = [HardwareInterfaceBinding, EnumMapping, WireContract]
