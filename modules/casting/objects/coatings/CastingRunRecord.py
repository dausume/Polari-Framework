"""
@module casting.objects.coatings.CastingRunRecord

Row class CastingRunRecord of the casting module — one class per file (design §7), split
from coatings_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CastingRunRecord(treeObject):
    """One cast: which stage, which mold lifecycle row (the EXISTING
    waxprint.MoldLifecycleRecord — reuse lives there), which fill
    run, and what came out."""

    @treeObjectInit
    def __init__(self, name: str = '', stage_ref: str = '',
                 mold_lifecycle_ref: str = '', fill_run_ref: str = '',
                 outcome: str = '', defects_json: str = '[]',
                 is_prior: bool = True, notes: str = '',
                 provenance_id: str = '', manager=None):
        self.name = name
        self.stage_ref = stage_ref
        self.mold_lifecycle_ref = mold_lifecycle_ref
        self.fill_run_ref = fill_run_ref
        self.outcome = outcome
        self.defects_json = defects_json
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
