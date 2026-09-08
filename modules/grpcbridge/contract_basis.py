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
  - grpcbridge.custom.proto_gen (the generator engine)
  - grpcbridge.contract_api (the knob surface)
  - polariDataTyping.schema_stability.record_deviation (stale hook)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/contract/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from grpcbridge.objects.contract.GrpcExposure import GrpcExposure  # noqa: F401
from grpcbridge.objects.contract.ProtoContractVersion import ProtoContractVersion  # noqa: F401
