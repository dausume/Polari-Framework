"""@module pspp.objects.material_structure._shared — what the material_structure row classes share (constants, seeds, helpers); split from material_structure_basis.py (sap-2c)."""
import json

MANDATORY_DESCRIPTORS = (
    'bulkDensity', 'phaseFractions', 'totalPorosity', 'moistureState',
    'reactionExtent',
)
L2_DOMAIN_TYPES = (
    'gel-domain', 'capillary-pore', 'reaction-rim',
    'dissolution-front', 'fiber-interphase', 'microcrack-network',
    'grain-domain', 'phase-morphology',
)
def _rows(manager, table='ScaleStructureDefinition'):
    rows = (getattr(manager, 'objectTables', None) or {}).get(table, {})
    return list(rows.values()) if isinstance(rows, dict) else list(rows)
def structure_rows_for_state(manager, subject_state_key):
    return [r for r in _rows(manager)
            if getattr(r, 'state_key', '') == subject_state_key]
def descriptors_for_state(manager, subject_state_key, scale_level=None,
                          domain_type=None):
    """Merged {descriptor: {value, sourceRow, scaleLevel, domainType}}
    over one state's usable structure rows ('planned' is absent)."""
    merged = {}
    for r in structure_rows_for_state(manager, subject_state_key):
        if getattr(r, 'status', 'partial') == 'planned':
            continue
        if scale_level is not None and \
                getattr(r, 'scale_level', 0) != scale_level:
            continue
        if domain_type is not None and \
                getattr(r, 'domain_type', '') != domain_type:
            continue
        try:
            descriptors = json.loads(
                getattr(r, 'descriptors_json', '') or '{}')
        except Exception:
            descriptors = {}
        for key, value in descriptors.items():
            merged[key] = {
                'value': value,
                'sourceRow': getattr(r, 'name', ''),
                'scaleLevel': getattr(r, 'scale_level', 0),
                'domainType': getattr(r, 'domain_type', ''),
            }
    return merged
def structure_profile(manager, subject_state_key):
    """One state's structure at a glance: per-level rows, mandatory-
    core coverage, honest gaps."""
    rows = structure_rows_for_state(manager, subject_state_key)
    have = descriptors_for_state(manager, subject_state_key)
    return {
        'stateKey': subject_state_key,
        'rows': [{'name': getattr(r, 'name', ''),
                  'scaleLevel': getattr(r, 'scale_level', 0),
                  'domainType': getattr(r, 'domain_type', ''),
                  'status': getattr(r, 'status', 'partial')}
                 for r in rows],
        'mandatoryCore': {d: (d in have)
                          for d in MANDATORY_DESCRIPTORS},
        'descriptorsPresent': sorted(have),
    }
def require_descriptors(manager, subject_state_key, needed,
                        scale_level=None):
    """The structure gate (sibling of scale_presence.require_scale_
    levels): an engine declares what it reads; the refusal names the
    exact missing descriptor and the row to put it on."""
    have = descriptors_for_state(manager, subject_state_key,
                                 scale_level=scale_level)
    missing = [d for d in needed if d not in have]
    if not missing:
        return {'ok': True,
                'descriptors': {d: have[d] for d in needed}}
    where = (f'a ScaleStructureDefinition row for '
             f'{subject_state_key!r}'
             + (f' at L{scale_level}' if scale_level is not None
                else ''))
    return {
        'ok': False,
        'refusal': f'state {subject_state_key!r} is missing '
                   f'structure descriptors {missing}',
        'missing': missing,
        'suggestion': f'add {missing} to descriptors_json on {where} '
                      "(status 'defined' or 'partial' — 'planned' "
                      'counts as absent), with evidence for how each '
                      'value is known',
    }
