"""
@module grpcbridge.objects.contract.GrpcExposure

Row class GrpcExposure of the grpcbridge module — one class per file (design §7), split
from contract_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GrpcExposure(treeObject):
    """THE KNOB: may this class be served over gRPC, and under which
    contract? One row per exposed class; nothing auto-enables."""

    @treeObjectInit
    def __init__(
        self,
        # '<className>-grpc-exposure' (unique key).
        name: str = '',
        subject_class: str = '',
        # KNOB: exposure on/off. Default False — enabling is a
        # human/API act, never automatic.
        enabled: bool = False,
        # 'PolariObjectSync.<Class>' — how clients find the service.
        service_name: str = '',
        # KNOB (read by grpc-3's transport MUX): where this class's
        # change notifications go: 'stomp' (default, byte-identical
        # to today) | 'grpc' | 'both' (dual-publish migration mode).
        transport_preference: str = 'stomp',
        # Monotonic contract version (matches ProtoContractVersion).
        proto_version: int = 0,
        # Hash of the stabilization field snapshot the proto was
        # generated FROM (wire-relevant parts only).
        contract_hash: str = '',
        # 'never-generated' | 'current' | 'stale' (schema deviated or
        # snapshot drifted since generation — regenerate is a knob).
        contract_status: str = 'never-generated',
        # The generated .proto text, stored ON the row.
        proto_text: str = '',
        generated_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_class = subject_class
        self.enabled = enabled
        self.service_name = service_name
        self.transport_preference = transport_preference
        self.proto_version = proto_version
        self.contract_hash = contract_hash
        self.contract_status = contract_status
        self.proto_text = proto_text
        self.generated_at = generated_at
        self.notes = notes
