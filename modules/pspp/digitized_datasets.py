"""
@module pspp.digitized_datasets

Digitized source figures/tables as DATA rows (plan invariant I6) —
loading a book figure is data entry, not a code change, and every
curve carries its citation. One generic engine
(pspp.dataset_interpolation) reads every row; extrapolation defaults
to UNSUPPORTED.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.dataset_interpolation (the one reader)
  - pspp.datasets_seed (geopolymer book Ch.5 transcriptions)
"""

import json

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


def dataset_dict(row):
    """One dataset row (or seed dict) as the plain-dict shape the
    interpolation engine consumes."""
    get = (row.get if isinstance(row, dict)
           else lambda k, d='': getattr(row, k, d))

    def loads(key, fallback):
        try:
            return json.loads(get(key, '') or fallback)
        except Exception:
            return json.loads(fallback)
    return {
        'name': get('name', ''),
        'sourceReference': get('source_reference', ''),
        'status': get('status', 'ready'),
        'independentVariables': loads('independent_variables_json', '[]'),
        'dependentVariables': loads('dependent_variables_json', '[]'),
        'units': loads('units_json', '{}'),
        'sourceConditions': loads('source_conditions_json', '{}'),
        'interpolationPolicy': get('interpolation_policy', 'linear'),
        'extrapolationPolicy': get('extrapolation_policy', 'UNSUPPORTED'),
        'validityDomain': loads('validity_domain_json', '{}'),
        'digitizationMethod': get('digitization_method', ''),
        'digitizationError': get('digitization_error', ''),
        'points': loads('points_json', '[]'),
        'qualitativeShape': get('qualitative_shape', ''),
        'notes': get('notes', ''),
    }


def dataset_index(manager):
    """{name: dataset dict} over the live rows."""
    rows = (getattr(manager, 'objectTables', None) or {}).get(
        'DigitizedDataset', {})
    rows = rows.values() if isinstance(rows, dict) else rows
    return {d['name']: d
            for d in (dataset_dict(r) for r in rows) if d['name']}
