"""
@module grpcbridge.contract_basis

gRPC exposure as DATA (object-coherence): one GrpcExposure row per
class that MAY be served over gRPC (THE KNOB — default off, never
auto-enabled), plus an immutable ProtoContractVersion history row per
generation so tag numbers stay append-only across versions (protobuf
wire compatibility: a field never changes tag; removed fields become
`reserved`).

The gate: a contract is only ever generated FROM a class's
schema-stabilization snapshot (see polariDataTyping.schema_stability)
— an OOPS that destabilizes the schema marks the exposure 'stale'.

@consumers
  - grpcbridge.proto_gen (the generator engine)
  - grpcbridge.contract_api (the knob surface)
  - polariDataTyping.schema_stability.record_deviation (stale hook)
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


class ProtoContractVersion(treeObject):
    """One immutable generation of a class's contract. Tag numbers are
    append-only across versions: regeneration reuses this row's
    field_map so a field keeps its tag forever; removed (or retyped)
    fields surrender their tag to `reserved`."""

    @treeObjectInit
    def __init__(
        self,
        # '<className>-proto-v<version>' (unique key).
        name: str = '',
        subject_class: str = '',
        version: int = 0,
        contract_hash: str = '',
        proto_text: str = '',
        # {'fields': {name: {tag, proto_type, comment}},
        #  'reserved': [tags]} — the tag-number ledger.
        field_map_json: str = '{}',
        generated_at: str = '',
        # 'initial' | 'schema-adapted' | 'manual-regenerate'.
        reason: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_class = subject_class
        self.version = version
        self.contract_hash = contract_hash
        self.proto_text = proto_text
        self.field_map_json = field_map_json
        self.generated_at = generated_at
        self.reason = reason
        self.notes = notes
