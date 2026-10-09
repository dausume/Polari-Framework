"""
@module grpcbridge.objects.mapping.HardwareInterfaceBinding

HardwareInterfaceBinding — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareInterfaceBinding(treeObject):
    """What it is: the tie between ONE Polari object row and the very specific hardware interface it corresponds to
    (grpc-j4, his ruling 2026-10-02): object class + object name ↔ a board instance ↔ an interface (a serial port, a
    twin's pty, later an SPI chip-select) on one bridge, plus the dense `instance_index` (0..n-1 per class per bridge)
    that rides the wire in ceil(log2 n) bits. The gRPC message carries these identifiers (`hardware_interface`); the
    wire struct never does — the bridge strips them going down and re-attaches them from THIS row coming up.
    Related concepts: `WireContract` (the index width it implies), `BoardInstance`, `HardwareBridgeDefinition`,
    GET /api/board/instances/<id>/interface (the chain an analysis walks).
    """

    @treeObjectInit
    def __init__(self, name: str = '', bridge_name: str = '', object_class: str = '', object_name: str = '',
                 board_instance: str = '', board_definition: str = '', interface_kind: str = 'serial', interface_name: str = '',
                 port: str = '', adapter: str = '', instance_index: int = 0, wire_version: int = 2, contract_hash_v2: str = '',
                 frames_seen: int = 0, last_sequence: int = 0, last_seen_at: str = '', refused_frames: int = 0,
                 gaps_seen: int = 0, frames_lost: int = 0, reconnects: int = 0, reboots: int = 0,
                 origin: str = 'person', notes: str = '', manager=None):
        self.name = name  # e.g. uno-pair/SimRigState/0
        self.bridge_name = bridge_name  # the HardwareBridgeDefinition this interface is served by
        self.object_class = object_class  # SimRigState
        self.object_name = object_name  # the row (its `name`) this interface IS: uno-twin-0
        self.board_instance = board_instance  # BoardInstance name (a twin: twin:arduino-uno-r3#0)
        self.board_definition = board_definition  # arduino-uno-r3 — the definition + its datasheet facts
        self.interface_kind = interface_kind  # serial | twin-pty | spi-csn (future)
        self.interface_name = interface_name  # usart0 — the MCU peripheral on the far end
        self.port = port  # /dev/serial/by-id/… | the twin's pty link
        self.adapter = adapter  # AdapterDefinition name when the host reaches it through one
        self.instance_index = instance_index  # dense 0..n-1 per (bridge, class) — assign_indexes renumbers
        self.wire_version = wire_version  # 2 = prelude (index + presence); 1 = an old firmware (no prelude)
        self.contract_hash_v2 = contract_hash_v2  # the WireContract hash this binding was last derived against
        self.frames_seen = frames_seen  # telemetry frames the server applied through this binding
        self.last_sequence = last_sequence
        self.last_seen_at = last_seen_at
        self.refused_frames = refused_frames  # frames whose index/port did not match (counted, never applied)
        # ucd-0e3 bridge lifecycle: additive, 0-default — PREPARED, not yet populated. The Java bridge keeps these
        # counters itself (SequenceTracker + SerialCdcPort.reconnects()) and prints them in its status line; neither
        # the gRPC Push path (HardwareInterface carries no such fields — the proto was deliberately left alone) nor
        # a log-line parser (none exists yet) stamps them onto this row today. Wiring one of those two is DEBT.
        self.gaps_seen = gaps_seen  # transport-loss events this binding's port observed (sequence > last + 1)
        self.frames_lost = frames_lost  # total frames implied missing by those gaps
        self.reconnects = reconnects  # times this binding's physical port was lost and reopened
        self.reboots = reboots  # times a NEW boot_session was seen on this binding (fresh device state)
        self.origin = origin  # seeded | person | installer
        self.notes = notes
