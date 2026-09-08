"""
@module casting.objects.sprue.SprueSetInstance

Row class SprueSetInstance of the casting module — one class per file (design §7), split
from sprue_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SprueSetInstance(treeObject):
    """One strategy applied to one mold — generated rows + verdict.
    All geometry fields are DERIVED by sprue_geometry; re-application
    reconverges them (the derived-row rule from cast-1)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        mold_ref: str = '',
        strategy_ref: str = '',
        sprue_shape_names_json: str = '[]',
        vent_shape_names_json: str = '[]',
        # per-feature placement + WHY (evidence) — never bare
        # coordinates.
        placements_json: str = '[]',
        removability_score: float = 0.0,
        removability_json: str = '{}',
        # the two parity artifacts (see module header).
        sprued_body_shape_name: str = '',
        sprued_master_shape_name: str = '',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.mold_ref = mold_ref
        self.strategy_ref = strategy_ref
        self.sprue_shape_names_json = sprue_shape_names_json
        self.vent_shape_names_json = vent_shape_names_json
        self.placements_json = placements_json
        self.removability_score = removability_score
        self.removability_json = removability_json
        self.sprued_body_shape_name = sprued_body_shape_name
        self.sprued_master_shape_name = sprued_master_shape_name
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
