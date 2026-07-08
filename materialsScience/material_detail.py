"""
@cross-cutting
@module materialsScience.material_detail
@tags @xc:bindings

ONE material's full picture — the per-material detail view's data
(Dustin 2026-07-07: "go into a material like paraffin wax to see what
its material properties are and what they mean, and context on how
they change per scenario … detail views for different levels PER
MATERIAL, not just abstract 'this exists at this level'").

Aggregates, by material name: the identity row, every property value
we hold (worksheet priors, thermal window, computed engine results on
scale rows), each value carrying its MEANING + scenario context from
the MaterialPropertyMeaning rows, the quantified blend effects the
material exerts as an additive, and per-level detail (what defines the
material at each level, parameters, results, lineage).

Scope (Dustin 2026-07-07): levels are the ones served by real engines
— L0 measured, L1 FEM, L4 DFT. L2/L3 stay out of view until their
engines land (they still appear if a material ever earns rows there).

Pure functions over manager.objectTables + the legacy JSON seeds — no
side effects.

@consumers
  - materialsScience.material_detail_api (GET /api/msci/materials/
    {name}/detail)
  - material-detail frontend component
@see /OVERLAP_MAP.md
"""

import json

from materialsScience.composite_search import load_legacy_seed_data
from materialsScience.materials_basis import SCALE_LEVEL_DETAILS
from materialsScience.property_meanings import meaning_index
from materialsScience.scale_presence import (
    require_scale_levels, scale_profile,
)

#: The levels the detail view features (Dustin 2026-07-07: FEM + DFT
#: first). Levels outside this set appear only when rows exist.
FOCUS_LEVELS = (0, 1, 4)


def _table_rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _find_by_name(manager, class_name, name):
    for row in _table_rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _parse(text, fallback='{}'):
    try:
        return json.loads(text or fallback)
    except Exception:
        return json.loads(fallback)


def _attach_meaning(entry, meanings):
    found = meanings.get(str(entry['key']).lower())
    if found:
        entry['label'] = found['label']
        entry['units'] = entry.get('units') or found['units']
        entry['meaning'] = found['meaning']
        entry['scenarioContext'] = found['scenarioContext']
    else:
        entry.setdefault('label', entry['key'])
        entry['meaning'] = None
        entry['scenarioContext'] = None
    return entry


def _detail_row(row):
    """One scale row, fully opened: parameters split from result."""
    params = _parse(getattr(row, 'parameters_json', '{}'))
    result = params.pop('result', None)
    return {
        'name': getattr(row, 'name', ''),
        'status': getattr(row, 'status', ''),
        'definitionClass': getattr(row, 'definition_class', ''),
        'definitionRef': getattr(row, 'definition_ref', ''),
        'derivedFrom': getattr(row, 'derived_from_name', ''),
        'derivationMethod': getattr(row, 'derivation_method', ''),
        'parameters': params,
        'result': result,
        'provenance': getattr(row, 'provenance_id', ''),
        'notes': getattr(row, 'notes', ''),
    }


def _result_properties(levels, meanings):
    """Scalar values inside stored engine results → property entries
    (the computed half of 'what are its properties')."""
    # Engine/run metadata is not a material property — it stays
    # visible in the level row's parameters, not the property list.
    skip = {'ok', 'engine', 'basis', 'xc'}
    entries = []
    for level in levels:
        for row in level['rows']:
            result = row.get('result') or {}
            engine = (row.get('parameters') or {}).get('engine', '')
            for key, value in result.items():
                if key in skip or isinstance(value, (dict, list)):
                    continue
                entries.append(_attach_meaning({
                    'key': key,
                    'value': value,
                    'units': '',
                    'source': (f"computed at L{level['level']}"
                               + (f' · {engine}' if engine else '')),
                    'sourceRow': row['name'],
                    'level': level['level'],
                    'provenance': row.get('provenance', ''),
                }, meanings))
    return entries


def _prior_properties(manager, name, meanings):
    """Worksheet-prior base properties from formulation searches whose
    base material is this one — honestly labeled priors."""
    entries = []
    for row in _table_rows(manager, 'FormulationSearchDefinition'):
        if getattr(row, 'base_material_name', '') != name:
            continue
        priors = _parse(getattr(row, 'base_properties_json', '{}'))
        for key, value in priors.items():
            entries.append(_attach_meaning({
                'key': key,
                'value': value,
                'units': '',
                'source': (f"worksheet prior (formulation search "
                           f"'{getattr(row, 'name', '')}')"),
                'sourceRow': getattr(row, 'name', ''),
                'level': 0,
                'provenance': 'MISSING_MATERIALS_DATA worksheet — '
                              'prior, not a measurement',
            }, meanings))
    return entries


def _thermal_block(manager, name, meanings):
    """Melt/smoke window as both a property pair and the processing
    scenario block."""
    profile = _find_by_name(manager, 'ThermalProcessingProfile', name)
    if profile is None:
        return None, []
    melts = bool(getattr(profile, 'melts', True))
    provenance = getattr(profile, 'provenance_note', '')
    block = {
        'melts': melts,
        'meltLowC': getattr(profile, 'melt_low_c', None),
        'meltHighC': getattr(profile, 'melt_high_c', None),
        'smokeLowC': getattr(profile, 'smoke_low_c', None),
        'smokeHighC': getattr(profile, 'smoke_high_c', None),
        'mfiNote': getattr(profile, 'mfi_note', ''),
        'provenance': provenance,
        'scenarioNote': ('Processing scenario: the whole blend must be '
                         'molten to extrude, and NO component may reach '
                         'its smoking point inside the melt window '
                         '(no-volatiles gate).'),
    }
    entries = []
    if melts:
        entries.append(_attach_meaning({
            'key': 'meltRange',
            'value': f"{block['meltLowC']}–{block['meltHighC']}",
            'units': '°C',
            'source': 'thermal processing profile',
            'level': 0,
            'provenance': provenance,
        }, meanings))
    else:
        entries.append(_attach_meaning({
            'key': 'meltRange',
            'value': 'does not melt in the processing range '
                     '(inert filler)',
            'units': '',
            'source': 'thermal processing profile',
            'level': 0,
            'provenance': provenance,
        }, meanings))
    entries.append(_attach_meaning({
        'key': 'smokePoint',
        'value': f"{block['smokeLowC']}–{block['smokeHighC']}",
        'units': '°C',
        'source': 'thermal processing profile',
        'level': 0,
        'provenance': provenance,
    }, meanings))
    return block, entries


def _legacy_blocks(identity, meanings):
    """The legacy-seed facts: descriptive raw-material identity and —
    the blend scenario — the quantified effects this material exerts
    as an additive (per wt%)."""
    raw_name = getattr(identity, 'raw_material_name', '')
    display = getattr(identity, 'display_name', '')
    try:
        legacy = load_legacy_seed_data()
    except Exception as e:
        return None, {'available': False,
                      'note': f'legacy seed data unreadable: {e}'}

    raw_facts = None
    for raw in legacy['raws']:
        if raw.get('name') in (raw_name, display) and raw_name:
            raw_facts = {k: raw.get(k) for k in (
                'materialType', 'physicalForm', 'particleSize',
                'purity', 'grade', 'processingNotes', 'canBeBase',
                'canBeAdditive') if raw.get(k) is not None}
            break

    additive = None
    for a in legacy['additives']:
        if a.get('name') in (raw_name, display) and raw_name:
            additive = a
            break
    if additive is None:
        return raw_facts, None

    effects = []
    for effect in legacy['effects']:
        if effect.get('additiveId') != additive.get('id'):
            continue
        entry = _attach_meaning({
            'key': effect.get('propertyName', ''),
            'value': None, 'units': effect.get('effectUnit', ''),
            'source': 'quantified additive effect',
            'provenance': effect.get('provenanceId', ''),
        }, meanings)
        effects.append({
            'property': effect.get('propertyName', ''),
            'label': entry['label'],
            'meaning': entry['meaning'],
            'intent': effect.get('intent', ''),
            'perWtPercent': effect.get('effectPerWeightPercent', 0.0),
            'unit': effect.get('effectUnit', ''),
            'normalizedStrength':
                effect.get('normalizedEffectStrength', None),
            'conditions': effect.get('testConditions', ''),
            'provenance': effect.get('provenanceId', ''),
        })
    return raw_facts, {
        'available': True,
        'additiveName': additive.get('name', ''),
        'note': ('Blend scenario: per wt% of this material added to a '
                 'formulation, each property moves as quantified below '
                 '(effectPerWeightPercent 0.0 = direction known, '
                 'magnitude not yet quantified — the search reports '
                 'that property as unpredictable).'),
        'effects': effects,
    }


def build_material_detail(manager, name):
    """The full per-material detail payload."""
    identity = _find_by_name(manager, 'MaterialsScienceMaterial', name)
    if identity is None:
        known = sorted(getattr(r, 'name', '')
                       for r in _table_rows(
                           manager, 'MaterialsScienceMaterial'))
        return {'ok': False,
                'error': f"no material identity '{name}'",
                'knownMaterials': known}

    meanings = meaning_index(manager)
    profile = scale_profile(manager, name)

    # Levels: the focus set plus anything actually earned elsewhere.
    shown = sorted(set(FOCUS_LEVELS)
                   | {lvl for lvl, rows in profile['levels'].items()
                      if rows})
    levels = []
    for level in shown:
        if level in profile['defined']:
            status = 'defined'
        elif level in profile['partial']:
            status = 'partial'
        else:
            status = 'missing'
        entry = {
            'level': level,
            **SCALE_LEVEL_DETAILS[level],
            'status': status,
            'rows': [_detail_row(r)
                     for r in profile['levels'].get(level, [])],
        }
        if status == 'missing':
            verdict = require_scale_levels(manager, name, [level])
            entry['earnHint'] = (verdict['suggestions'] or [None])[0]
        levels.append(entry)
    hidden = sorted(set(SCALE_LEVEL_DETAILS) - set(shown))

    thermal, thermal_props = _thermal_block(manager, name, meanings)
    raw_facts, blend_effects = _legacy_blocks(identity, meanings)
    properties = (_prior_properties(manager, name, meanings)
                  + thermal_props
                  + _result_properties(levels, meanings))

    suggestions = []
    unmatched = sorted({p['key'] for p in properties
                        if p['meaning'] is None})
    if unmatched:
        suggestions.append({
            'evidence': f"properties without a meaning row: "
                        f"{', '.join(unmatched)}",
            'knob': 'MaterialPropertyMeaning',
            'action': 'Create a MaterialPropertyMeaning row (or add '
                      'the key to an existing row\'s aliases_json) so '
                      'the detail view can explain it.',
        })

    return {
        'ok': True,
        'material': {
            'name': name,
            'displayName': getattr(identity, 'display_name', '') or name,
            'description': getattr(identity, 'description', ''),
            'kind': getattr(identity, 'material_kind', ''),
            'category': getattr(identity, 'category', ''),
            'tags': _parse(getattr(identity, 'tags_json', '[]'), '[]'),
            'elements': _parse(
                getattr(identity, 'element_symbols_json', '[]'), '[]'),
            'notes': getattr(identity, 'notes', ''),
        },
        'properties': properties,
        'thermal': thermal,
        'rawFacts': raw_facts,
        'blendEffects': blend_effects,
        'levels': levels,
        'hiddenLevels': {
            'levels': hidden,
            'note': ('mesoscale/atomistic views arrive with their '
                     'engines — out of view until then'),
        } if hidden else None,
        'suggestions': suggestions,
    }
