"""
@module pspp.objects.digitized_datasets.DigitizedDataset

Row class DigitizedDataset of the pspp module — one class per file (design §7), split
from digitized_datasets_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DigitizedDataset(treeObject):
    """One digitized source table/figure with its full provenance."""

    @treeObjectInit
    def __init__(
        self,
        # Unique kebab-case key ('na-silicate-solution-polymerization').
        name: str = '',
        # Exact citation: book, table/figure number, page.
        source_reference: str = '',
        version: int = 1,
        # 'ready' | 'provisional-low-confidence' (engine refuses to
        # read low-confidence rows until re-digitized).
        status: str = 'ready',
        # JSON list — point keys that SELECT ('MR', 'temperature_C',
        # plus discrete selectors like 'series', 'physical_state').
        independent_variables_json: str = '[]',
        # JSON list — point keys the engine returns.
        dependent_variables_json: str = '[]',
        # JSON dict variable -> units string.
        units_json: str = '{}',
        # JSON dict — the conditions the source measured under, plus
        # source-stated caveats (the honesty payload).
        source_conditions_json: str = '{}',
        # 'linear' | 'log-linear' | 'none' (discrete lookup only).
        interpolation_policy: str = 'linear',
        # ALWAYS 'UNSUPPORTED' today (invariant I6) — the field exists
        # so a future policy is an explicit, reviewable change.
        extrapolation_policy: str = 'UNSUPPORTED',
        # JSON dict variable -> [min, max] the source supports.
        validity_domain_json: str = '{}',
        digitization_method: str = '',
        digitization_error: str = '',
        # JSON list of point dicts keyed by the variable names.
        points_json: str = '[]',
        # Prose fallback when points are honestly absent (angled-photo
        # reads waiting on a re-shoot).
        qualitative_shape: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.source_reference = source_reference
        self.version = version
        self.status = status
        self.independent_variables_json = independent_variables_json
        self.dependent_variables_json = dependent_variables_json
        self.units_json = units_json
        self.source_conditions_json = source_conditions_json
        self.interpolation_policy = interpolation_policy
        self.extrapolation_policy = extrapolation_policy
        self.validity_domain_json = validity_domain_json
        self.digitization_method = digitization_method
        self.digitization_error = digitization_error
        self.points_json = points_json
        self.qualitative_shape = qualitative_shape
        self.provenance_id = provenance_id
        self.notes = notes
