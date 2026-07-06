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

from materialsScience.materials_basis import SCALE_LEVELS


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
