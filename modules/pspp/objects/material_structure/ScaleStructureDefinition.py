"""
@module pspp.objects.material_structure.ScaleStructureDefinition

Row class ScaleStructureDefinition of the pspp module — one class per file (design §7), split
from material_structure_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ScaleStructureDefinition(treeObject):
    """One state's structure AT one scale level (and, at L2, one
    domain). The coherent owner of a state's structure is the set of
    rows sharing its state_key — same satellite idiom as scale
    definitions, so cross-scale transfer lineage (pspp-5) can cite
    individual rows."""

    @treeObjectInit
    def __init__(
        self,
        # Unique: '<state_key>@L<level>[-<domain>]'
        # ('metakaolin-gp#cured-solid@L2-capillary-pore').
        name: str = '',
        # MaterialState key this structure describes.
        state_key: str = '',
        scale_level: int = 0,
        # '' except (typically) L2 — one of L2_DOMAIN_TYPES or a new
        # coined type; multiple domain rows per state+level are the
        # DESIGN, not an anomaly.
        domain_type: str = '',
        # The length range this row speaks for (honesty about what
        # 'porosity' means HERE — invariant I8).
        characteristic_length_min_m: float = 0.0,
        characteristic_length_max_m: float = 0.0,
        # 'descriptor-summary' | 'field-ref' | 'network-graph-ref' |
        # 'particle-config-ref' — what representation backs this row.
        representation_type: str = 'descriptor-summary',
        # WHERE a non-summary representation lives (class + ref), like
        # MaterialScaleDefinition's definition home.
        representation_class: str = '',
        representation_ref: str = '',
        # The descriptors themselves (JSON dict). Mandatory core keys
        # per MANDATORY_DESCRIPTORS; absence of the rest is honest.
        descriptors_json: str = '{}',
        # 'defined' | 'partial' | 'planned' (gates treat planned as
        # absent — same status vocabulary as scale definitions).
        status: str = 'partial',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.state_key = state_key
        self.scale_level = scale_level
        self.domain_type = domain_type
        self.characteristic_length_min_m = characteristic_length_min_m
        self.characteristic_length_max_m = characteristic_length_max_m
        self.representation_type = representation_type
        self.representation_class = representation_class
        self.representation_ref = representation_ref
        self.descriptors_json = descriptors_json
        self.status = status
        self.provenance_id = provenance_id
        self.notes = notes
