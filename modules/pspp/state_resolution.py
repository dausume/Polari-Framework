"""
@module pspp.state_resolution

THE one path from a material name to a state (plan invariant I1):
legacy name-based lookups resolve ONLY through the canonical state
unless the caller names another state — so properties from different
DAG branches can never silently mix.

The canonical '<material>#as-defined' state is IMPLICIT (virtual)
until a row is written for it — sync-on-need, the tech-tree-edge
idiom — so no boot backfill pass exists to drift. Existing consumers
(waxprint *_ref, aquaponics pots, material_detail) keep resolving by
material name unchanged: that path lands here and answers canonical.
"""

import json

from pspp.material_states import CANONICAL_STATE


def state_key(material_name, state_name=None):
    return f'{material_name}#{state_name or CANONICAL_STATE}'


def _rows(manager, table):
    rows = (getattr(manager, 'objectTables', None) or {}).get(table, {})
    return list(rows.values()) if isinstance(rows, dict) else list(rows)


def state_summary(row):
    def loads(attr, fallback):
        try:
            return json.loads(getattr(row, attr, '') or fallback)
        except Exception:
            return json.loads(fallback)
    return {
        'stateKey': getattr(row, 'name', ''),
        'material': getattr(row, 'material_name', ''),
        'stateName': getattr(row, 'state_name', ''),
        'isCanonical': bool(getattr(row, 'is_canonical', False)),
        'processingStage': getattr(row, 'processing_stage', ''),
        'thermodynamicPhase': getattr(row, 'thermodynamic_phase', ''),
        'parents': loads('parent_state_ids_json', '[]'),
        'producingExecution': getattr(row, 'producing_execution_id', ''),
        'validationStatus': getattr(row, 'validation_status',
                                    'unvalidated'),
        'virtual': False,
    }


def _virtual_canonical(material_name):
    """The implicit canonical state — real as a subject, row-less
    until something writes to it (absence is honest data)."""
    return {
        'stateKey': state_key(material_name),
        'material': material_name,
        'stateName': CANONICAL_STATE,
        'isCanonical': True,
        'processingStage': '',
        'thermodynamicPhase': '',
        'parents': [],
        'producingExecution': '',
        'validationStatus': 'unvalidated',
        'virtual': True,
    }


def material_states(manager, material_name):
    """All states of one material — explicit rows plus the implicit
    canonical when no explicit canonical row exists."""
    states = [state_summary(r)
              for r in _rows(manager, 'MaterialState')
              if getattr(r, 'material_name', '') == material_name]
    if not any(s['isCanonical'] or s['stateName'] == CANONICAL_STATE
               for s in states):
        states.insert(0, _virtual_canonical(material_name))
    return states


def resolve_state(manager, material_name, state_name=None):
    """Evidence-bearing resolution of (material, state?) → state.
    state_name None = canonical ONLY (invariant I1) — never a guess,
    never another branch."""
    materials = {getattr(m, 'name', '')
                 for m in _rows(manager, 'MaterialsScienceMaterial')}
    if material_name not in materials:
        return {
            'ok': False,
            'refusal': f'unknown material {material_name!r}',
            'suggestion': 'create the MaterialsScienceMaterial identity '
                          'row first — states belong to identities',
        }
    states = material_states(manager, material_name)
    wanted = state_name or CANONICAL_STATE
    for s in states:
        if s['stateName'] == wanted or s['stateKey'] == wanted:
            return {'ok': True, 'state': s,
                    'stateKey': s['stateKey']}
    return {
        'ok': False,
        'refusal': f'material {material_name!r} has no state '
                   f'{wanted!r}',
        'available': [s['stateName'] for s in states],
        'suggestion': 'name one of the available states, or create a '
                      'MaterialState row for the new state (with its '
                      'parent_state_ids naming where it branches from)',
    }


def branch_lineage(manager, subject_state_key, _seen=None):
    """Walk parent links root-ward from one state key — the ancestry
    a branch-scoped query is allowed to see. Cycle-safe."""
    _seen = _seen or set()
    if subject_state_key in _seen:
        return []
    _seen.add(subject_state_key)
    row = next((r for r in _rows(manager, 'MaterialState')
                if getattr(r, 'name', '') == subject_state_key), None)
    if row is None:
        return [subject_state_key]
    lineage = [subject_state_key]
    try:
        parents = json.loads(
            getattr(row, 'parent_state_ids_json', '') or '[]')
    except Exception:
        parents = []
    for p in parents:
        lineage += branch_lineage(manager, p, _seen)
    return lineage


def scale_definitions_for_state(manager, material_name, state_name=None):
    """MaterialScaleDefinition rows scoped to ONE state: rows with an
    empty state_key belong to the canonical state (which is how every
    pre-pspp-2 row keeps working with zero call-site edits)."""
    wanted_key = state_key(material_name, state_name)
    canonical = (state_name or CANONICAL_STATE) == CANONICAL_STATE
    out = []
    for r in _rows(manager, 'MaterialScaleDefinition'):
        if getattr(r, 'material_name', '') != material_name:
            continue
        row_state = getattr(r, 'state_key', '') or ''
        if (row_state == wanted_key) or (canonical and row_state == ''):
            out.append(r)
    return out
