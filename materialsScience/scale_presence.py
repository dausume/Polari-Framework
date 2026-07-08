"""
@cross-cutting
@module materialsScience.scale_presence
@tags @xc:bindings

Scale-presence PROFILES and GATES over the materials basis.

Piecemeal-first multi-scale means absence is data: these helpers answer
"at which scales is material X honestly defined?" and gate work that
needs specific levels, refusing with EVIDENCE + a suggestion pointing
at the exact knob (create/complete the MaterialScaleDefinition) — never
silently falling back (knobs-and-suggestions principle).

Pure functions over manager.objectTables — no I/O, easily testable.

@consumers
  - simulation stage gates (a stage declares required scale levels)
  - explainer panels (profile rendering)
@see /OVERLAP_MAP.md
"""

import json

from materialsScience.materials_basis import (
    SCALE_LEVELS, SCALE_LEVEL_DETAILS,
)


def _scale_rows(manager, material_name):
    table = (manager.objectTables or {}).get('MaterialScaleDefinition', {})
    rows = table.values() if isinstance(table, dict) else table
    return [r for r in rows if getattr(r, 'material_name', '') == material_name]


def scale_profile(manager, material_name):
    """{'levels': {0: [row, ...], ...}, 'defined': [...], 'partial': [...],
    'missing': [...]} — 'planned' rows count as missing (declared intent
    is not a definition)."""
    byLevel = {}
    for row in _scale_rows(manager, material_name):
        byLevel.setdefault(int(row.scale_level), []).append(row)

    defined, partial, missing = [], [], []
    for level in SCALE_LEVELS:
        rows = byLevel.get(level, [])
        statuses = {getattr(r, 'status', 'defined') for r in rows}
        if 'defined' in statuses:
            defined.append(level)
        elif 'partial' in statuses:
            partial.append(level)
        else:
            missing.append(level)
    return {'levels': byLevel, 'defined': defined,
            'partial': partial, 'missing': missing}


def require_scale_levels(manager, material_name, levels,
                         accept_partial=False):
    """Gate: can this work proceed for `material_name` needing `levels`?

    Returns an honest verdict — {'ok', 'material', 'required',
    'satisfied', 'blocking', 'suggestions'} — where each suggestion is
    conditional, evidence-bearing, and points at the knob:
    {'level', 'category', 'evidence', 'knob', 'action'}. Callers surface
    them; they NEVER auto-apply.
    """
    profile = scale_profile(manager, material_name)
    usable = set(profile['defined'])
    if accept_partial:
        usable |= set(profile['partial'])

    required = sorted(int(l) for l in levels)
    blocking = [l for l in required if l not in usable]
    suggestions = []
    for level in blocking:
        category = SCALE_LEVELS.get(level, str(level))
        hasPartial = level in profile['partial']
        suggestions.append({
            'level': level,
            'category': category,
            'evidence': (
                f"'{material_name}' has a PARTIAL level-{level} "
                f"({category}) definition — complete it (status: "
                f"'defined') to unblock this."
                if hasPartial else
                f"'{material_name}' has no level-{level} ({category}) "
                f"definition; it is defined at levels "
                f"{profile['defined'] or 'none'}."),
            'knob': 'MaterialScaleDefinition',
            'action': (
                f"Set status='defined' on the existing "
                f"'{material_name}@L{level}' row"
                if hasPartial else
                f"Create MaterialScaleDefinition "
                f"name='{material_name}@L{level}', scale_level={level}, "
                f"pointing definition_class/definition_ref at where the "
                f"{category} definition lives"),
        })
    return {
        'ok': not blocking,
        'material': material_name,
        'required': required,
        'satisfied': sorted(set(required) - set(blocking)),
        'blocking': blocking,
        'suggestions': suggestions,
    }


def _material_rows(manager):
    table = (manager.objectTables or {}).get(
        'MaterialsScienceMaterial', {})
    rows = table.values() if isinstance(table, dict) else table
    return sorted(rows, key=lambda r: getattr(r, 'name', ''))


def _row_summary(row):
    """The page-facing view of one scale row — enough to render a cell
    without another fetch."""
    params = {}
    try:
        params = json.loads(getattr(row, 'parameters_json', '{}') or '{}')
    except Exception:
        pass
    return {
        'name': getattr(row, 'name', ''),
        'status': getattr(row, 'status', ''),
        'derivationMethod': getattr(row, 'derivation_method', ''),
        'derivedFrom': getattr(row, 'derived_from_name', ''),
        'definitionClass': getattr(row, 'definition_class', ''),
        'definitionRef': getattr(row, 'definition_ref', ''),
        'hasResult': bool(params.get('result')),
        'provenance': getattr(row, 'provenance_id', ''),
        'notes': getattr(row, 'notes', ''),
    }


def presence_matrix(manager):
    """The full accountability matrix: every material identity x every
    scale level, with absence as first-class data.

    {'levels': [{'level', 'name', 'lengthRange', 'methods', 'earnedBy',
                 'engines', 'defined', 'partial', 'missing'}  (counts)],
     'materials': [{'name', 'displayName', 'category', 'tags',
                    'presence': {'<level>': {'status':
                        'defined'|'partial'|'missing', 'rows': [...]}}}]}

    'planned' rows count as missing (declared intent is not a
    definition) but their rows still travel so the pages can show WHAT
    was declared and what earning it takes.
    """
    materials = []
    counts = {lvl: {'defined': 0, 'partial': 0, 'missing': 0}
              for lvl in SCALE_LEVELS}
    for mat in _material_rows(manager):
        name = getattr(mat, 'name', '')
        profile = scale_profile(manager, name)
        presence = {}
        for level in SCALE_LEVELS:
            if level in profile['defined']:
                status = 'defined'
            elif level in profile['partial']:
                status = 'partial'
            else:
                status = 'missing'
            counts[level][status] += 1
            presence[str(level)] = {
                'status': status,
                'rows': [_row_summary(r)
                         for r in profile['levels'].get(level, [])],
            }
        try:
            tags = json.loads(getattr(mat, 'tags_json', '[]') or '[]')
        except Exception:
            tags = []
        materials.append({
            'name': name,
            'displayName': getattr(mat, 'display_name', '') or name,
            'category': getattr(mat, 'category', ''),
            'tags': tags,
            'presence': presence,
        })
    levels = []
    for level, detail in sorted(SCALE_LEVEL_DETAILS.items()):
        levels.append({'level': level, **detail, **counts[level]})
    return {'levels': levels, 'materials': materials}


def level_accountability(manager, level):
    """One level's page data: who is defined here (with their rows),
    who is partial, and — the accountability half — who is MISSING,
    each absence carrying the require_scale_levels suggestion (evidence
    + knob + action, never auto-applied).
    """
    level = int(level)
    if level not in SCALE_LEVELS:
        return {'ok': False,
                'error': f'no scale level {level} — levels are '
                         f'{sorted(SCALE_LEVELS)}'}
    defined, partial, missing = [], [], []
    for mat in _material_rows(manager):
        name = getattr(mat, 'name', '')
        profile = scale_profile(manager, name)
        entry = {'material': name,
                 'displayName': getattr(mat, 'display_name', '') or name,
                 'category': getattr(mat, 'category', ''),
                 'rows': [_row_summary(r)
                          for r in profile['levels'].get(level, [])]}
        if level in profile['defined']:
            defined.append(entry)
        elif level in profile['partial']:
            partial.append(entry)
        else:
            verdict = require_scale_levels(manager, name, [level])
            entry['suggestion'] = (verdict['suggestions'] or [None])[0]
            missing.append(entry)
    return {'ok': True, 'level': level,
            'detail': SCALE_LEVEL_DETAILS[level],
            'defined': defined, 'partial': partial, 'missing': missing}
