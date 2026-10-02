"""
@module grpcbridge.objects.mapping.WireContract

WireContract — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class WireContract(treeObject):
    """What it is: the WIRE rules of one class on one bridge as data (grpc-j4), so the hash sees them: the field order
    (tag order), the enum tables in force, the instance-index width (0 bits for 1 instance, 1 for 2, ceil(log2 n)
    otherwise — a suggestion; the REPRESENTATION follows the packed_max_bits knob: packed bits, then an explicit index
    byte, then a 16-bit index, the version byte saying which), the presence mask, the prelude size, the wire version — and both hashes: `contract_hash_v1` (field →
    type, the schema watch; proto_gen.contract_hash) and `contract_hash_v2` (order + types + enums + index width +
    presence; what a firmware build, its header and the installer's compat compare). Derived from the exposure's
    field map + EnumMapping + HardwareInterfaceBinding rows by grpcbridge.custom.wire_contract.derive.
    Related concepts: `ProtoContractVersion`, `HardwareInterfaceBinding`, `EnumMapping`, `FirmwareBuild`.
    """

    @treeObjectInit
    def __init__(self, name: str = '', object_class: str = '', bridge_name: str = '', contract_version: int = 0,
                 field_order_json: str = '[]', enums_json: str = '{}', instance_count: int = 1, index_width: int = 0,
                 presence: str = 'mask', prelude_bytes: int = 0, wire_version: int = 2, contract_hash_v1: str = '',
                 contract_hash_v2: str = '', source: str = '', derived_at: str = '', notes: str = '', index_repr: str = 'none',
                 index_bytes: int = 0, suggested_index_width: int = 0, packed_max_bits: int = 4, manager=None):
        self.name = name  # e.g. SimRigState@uno-pair
        self.object_class = object_class
        self.bridge_name = bridge_name  # '' = no bridge (one instance, index width 0)
        self.contract_version = contract_version  # the ProtoContractVersion the order came from
        self.field_order_json = field_order_json  # [[field, proto_type], …] in TAG order — the wire order
        self.enums_json = enums_json  # {field: [labels…]} — 0 is the unknown slot
        self.instance_count = instance_count  # bindings of this class on this bridge
        self.index_width = index_width  # bits of instance_index in the prelude
        self.presence = presence  # mask (one bit per field)
        self.prelude_bytes = prelude_bytes  # ceil((index_width + fields) / 8)
        self.wire_version = wire_version
        self.contract_hash_v1 = contract_hash_v1
        self.contract_hash_v2 = contract_hash_v2
        self.source = source  # live (this server's exposure) | pinned (custom/contracts snapshot)
        self.derived_at = derived_at
        self.notes = notes  # the suggestion in plain words (computed width vs the representation the knob chose)
        # the index REPRESENTATION (his clarification 2026-10-02: "if we have 3 we should change, and if we have 20 we should
        # change what our plan is too"): none (1) | bits (packed, v2) | byte (explicit index byte, v3, n <= 256) | u16 (v4)
        self.index_repr = index_repr
        self.index_bytes = index_bytes  # explicit index bytes before the bitfield (byte: 1, u16: 2)
        self.suggested_index_width = suggested_index_width  # ceil(log2 n) — the suggestion
        self.packed_max_bits = packed_max_bits  # KNOB: the largest index packed into the bitfield (default 4 = 16 instances)
