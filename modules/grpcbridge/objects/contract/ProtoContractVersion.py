"""
@module grpcbridge.objects.contract.ProtoContractVersion

Row class ProtoContractVersion of the grpcbridge module — one class per file (design §7), split
from contract_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
