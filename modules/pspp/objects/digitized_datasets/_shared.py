"""@module pspp.objects.digitized_datasets._shared — what the digitized_datasets row classes share (constants, seeds, helpers); split from digitized_datasets_basis.py (sap-2c)."""
import json

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
