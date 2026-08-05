"""
@cross-cutting
@module casting.casting_seed
@tags @xc:bindings

cast-1 seeds — two demonstration molds over existing mathshapes seed
shapes (a quadric part and a primitive part, so both scale paths are
exercised live), plus the casting module's PolariModule identity row.
Seeding converges through composition.seed_upsert (the ten-strikes
defense: adding a field later reaches live rows), then DERIVES each
mold's geometry — derivation is part of seeding because the derived
rows are not data anyone types in.

@consumers
  - polariServer seed pass ([CastingSeed], after mathshapes seeds)
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-1)
"""

import json as _json

SEED_MOLDS = [
    {'name': 'demo-sphere-mold',
     'display_name': 'Demo mold: unit sphere',
     'part_shape_ref': 'unit-sphere', 'part_source': 'mathshape',
     'stock_margin_cm': 1.0, 'shrink_allowance_pct': 0.0,
     'parting_axis_hint': 'z', 'is_prior': True,
     'provenance_id': 'cast-1',
     'notes': 'the canonical inversion: a 4×4×4 stock block minus the '
              'unit sphere. Shrink 0 = solidification shrink not yet '
              'modelled (named, not assumed).'},
    {'name': 'pot-frustum-mold',
     'display_name': 'Demo mold: frustum pot body (+2% shrink)',
     'part_shape_ref': 'frustum-pot', 'part_source': 'mathshape',
     'stock_margin_cm': 2.0, 'shrink_allowance_pct': 2.0,
     'parting_axis_hint': 'z', 'is_prior': True,
     'provenance_id': 'cast-1',
     'notes': 'a primitive part with a declared 2% pattern-maker '
              'shrink — the cavity is oversized so the cast part '
              'lands on-size.'},
]

SEED_CASTING_MODULES = [{
    'name': 'Casting-Mold-Nesting',
    'version': '',
    'source_kind': 'file',
    'source_ref': 'casting',
    'status': 'installed',
    'manifest_json': _json.dumps({
        'displayName': 'Casting & Mold Nesting',
        'summary': 'Molds derived as negatives of math-defined parts '
                   '(stock DIFFERENCE part — the inversion every '
                   'casting stage applies), with declared shrink '
                   'allowance. Grows into nesting chains with derived '
                   'parity + thermal ordering, auto sprues, fill and '
                   'demold simulation (WAX_MOLD_NESTING_PLAN).',
        'objects': ['MoldDefinition'],
    }),
}]


def seed_casting(manager):
    """Converge MoldDefinition rows (seed_upsert semantics — a human's
    is_prior=False row is skipped loudly), then derive every mold's
    geometry. Returns the reports; never raises for one bad row."""
    from casting.casting_basis import MoldDefinition
    from casting.mold_geometry import derive_mold
    from composition.seed_upsert import upsert_seed_rows

    upsert = upsert_seed_rows(manager, 'MoldDefinition', MoldDefinition,
                              SEED_MOLDS, tag='CastingSeed')
    derivations = []
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'MoldDefinition', {}) or {}
    rows = table.values() if isinstance(table, dict) else table
    for mold in rows:
        r = derive_mold(manager, getattr(mold, 'name', ''))
        derivations.append({'mold': getattr(mold, 'name', ''),
                            'ok': bool(r.get('ok')),
                            'error': r.get('error', ''),
                            'reconverged': r.get('reconverged', []),
                            'volumeCheckOk':
                                (r.get('volumeCheck') or {}).get('ok')})
    return {'upsert': upsert, 'derivations': derivations}
