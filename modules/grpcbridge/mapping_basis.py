"""
@module grpcbridge.mapping_basis

The computer↔firmware MAPPING as data (grpc-j4 / brd-wire, his ruling 2026-10-02; GRPC_BRIDGE_PLAN.md §grpc-j4): the
INDEX of the mapping rows (one class per file under objects/mapping/) and their seeds.

Seeds (code-owned demonstrations, every value says why):
  * two EnumMappings — SimRigState.status ∈ {boot, ok, commanded, echoed, fault} (the words the UNO firmwares and the
    Renode twin report) and UnoAnalogState.status ∈ {boot, ok, fault};
  * two HardwareInterfaceBindings on ONE bridge, `uno-pair`: SimRigState rows uno-twin-0 / uno-twin-1 ↔ two simavr UNO
    twins (board instances twin:arduino-uno-r3#0 / #1, USART0 behind each twin's pty link) — two instances of one class
    on one bridge → a 1-bit instance index (index_width(2) == 1).
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
    _enum('SimRigState', 'status', ['boot', 'ok', 'commanded', 'echoed', 'fault'],
          'the status words the UNO firmwares (sim_rig, blink, echo) and the Renode twin report; fault is reserved for a '
          'firmware that detects one. Wire: 1 byte (0 = unknown) instead of a u16-prefixed string of up to 9 bytes.'),
    _enum('UnoAnalogState', 'status', ['boot', 'ok', 'fault'], 'the analog sweep reports boot → ok after 1 s.'),
]


def _bind(k):
    return {'name': '%s/SimRigState/%d' % (PAIR_BRIDGE, k), 'bridge_name': PAIR_BRIDGE, 'object_class': 'SimRigState',
            'object_name': 'uno-twin-%d' % k, 'board_instance': 'twin:arduino-uno-r3#%d' % k, 'board_definition': 'arduino-uno-r3',
            'interface_kind': 'twin-pty', 'interface_name': 'usart0', 'port': '/tmp/polari-uno-twin-%d-uart' % k, 'adapter': '',
            'instance_index': k, 'wire_version': 2, 'origin': 'seeded',
            'notes': 'the uno-pair demonstration: the SAME firmware built with instance_index %d, run in simavr twin #%d; '
                     'its USART0 reaches the host at the pty link (pol board twin uno up --tag %d)' % (k, k, k)}


SEED_HARDWARE_BINDINGS = [_bind(0), _bind(1)]

#: every mapping row class, in registration order
MAPPING_CLASSES = [HardwareInterfaceBinding, EnumMapping, WireContract]
