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
  - grpcbridge.custom.java_bridge (the generator)
  - grpcbridge.java_bridge_api (the knob surface)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/java_bridge/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from grpcbridge.objects.java_bridge.HardwareBridgeDefinition import HardwareBridgeDefinition  # noqa: F401
