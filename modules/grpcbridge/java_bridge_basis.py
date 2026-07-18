"""
@module grpcbridge.java_bridge_basis

The Polari Hardware Bridge as DATA (object-coherence): one
HardwareBridgeDefinition row per bridge app that can be generated —
a lightweight headless Java program whose job is to let Polari talk
to hardware whenever it wants to (long-term an isle-app; for now
internal SIMULATION software — the generated app ships with a
built-in simulated-MCU source, and flipping `source` to 'serial'
later changes nothing else).

Generation is gated exactly like the contracts it embeds: every
exposed class must hold a CURRENT gRPC contract (grpc-1), which in
turn only exists for a STABILIZED schema.

@consumers
  - grpcbridge.java_bridge (the generator)
  - grpcbridge.java_bridge_api (the knob surface)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class HardwareBridgeDefinition(treeObject):
    """THE KNOB for one generatable bridge app. Nothing about it
    auto-runs — generation and download are explicit acts."""

    @treeObjectInit
    def __init__(
        self,
        # '<bridgeName>-hw-bridge' (unique key).
        name: str = '',
        bridge_name: str = '',
        # KNOB: where packets come from. 'simulated' (default — the
        # internal-simulation phase: a built-in synthetic MCU) |
        # 'serial' (the real device, /dev/ttyACM*).
        source: str = 'simulated',
        serial_device: str = '/dev/ttyACM0',
        baud: int = 115200,
        # Ordered JSON list of exposed class names; a class's
        # msg_type on the wire is (index + 1) in this list.
        exposed_classes_json: str = '[]',
        # Synthetic-source pacing (frames/sec) while simulating.
        sim_rate_hz: int = 10,
        # KNOB: forward decoded records to Polari over gRPC (needs
        # the grpc-2 server). Default off — the core app runs and
        # logs without any gRPC dependency at runtime.
        grpc_enabled: bool = False,
        grpc_target: str = 'localhost:3002',
        # Device identity stamped into outgoing packets.
        device_id: int = 1,
        # Generation bookkeeping (manifest, not the artifact — the
        # tarball is rebuilt deterministically at download time from
        # the same contracts).
        last_generated_at: str = '',
        manifest_json: str = '{}',
        contract_hashes_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.bridge_name = bridge_name
        self.source = source
        self.serial_device = serial_device
        self.baud = baud
        self.exposed_classes_json = exposed_classes_json
        self.sim_rate_hz = sim_rate_hz
        self.grpc_enabled = grpc_enabled
        self.grpc_target = grpc_target
        self.device_id = device_id
        self.last_generated_at = last_generated_at
        self.manifest_json = manifest_json
        self.contract_hashes_json = contract_hashes_json
        self.notes = notes
