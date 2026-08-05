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

def _feed(name, display, kind, priority, tier, renewable, wax_ref,
          routes, density, strength, soften, melt, print_t, nozzle,
          layer, speed, removal, removal_t, removal_notes, notes):
    return {'name': name, 'display_name': display,
            'material_kind': kind, 'priority': priority,
            'accessibility_tier': tier, 'renewable': renewable,
            'wax_source_ref': wax_ref,
            'make_routes_json': _json.dumps(routes),
            'density_kg_m3': density,
            'compressive_strength_mpa': strength,
            'soften_temp_c': soften, 'melt_temp_c': melt,
            'claim_status': 'literature-approximate CONSERVATIVE '
                            'FLOOR — measure to replace',
            'print_temp_c': print_t, 'nozzle_diameter_mm': nozzle,
            'layer_height_mm': layer, 'print_speed_mm_s': speed,
            'removal_route': removal, 'removal_temp_c': removal_t,
            'removal_notes': removal_notes,
            'is_prior': True, 'provenance_id': 'cast-2b',
            'notes': notes}


#: The CORE FOCUS is the natural, locally-producible wax (grown or a
#: crop byproduct, printed on the waxprint auger extruder). The rest
#: meet the general 3D-printable/machinable criteria but are BOUGHT —
#: carried honestly as 'supported', never silently promoted.
SEED_MASTER_FEEDSTOCKS = [
    _feed('carnauba-pellet', 'Carnauba wax pellets (local chain)',
          'natural-wax', 'core', 'household', True, 'carnauba',
          ['auger-pellet-print'], 997.0, 2.0, 72.0, 82.0,
          110.0, 0.4, 0.2, 20.0, 'melt-out', 90.0,
          'melts clean and RECLAIMS — the lost-wax loop feeds itself',
          'THE core focus: hardest natural wax, waxsupply mold-rank '
          'top. Printed on the waxprint two-zone auger extruder.'),
    _feed('candelilla-pellet', 'Candelilla wax pellets (local chain)',
          'natural-wax', 'core', 'household', True, 'candelilla',
          ['auger-pellet-print'], 983.0, 1.2, 60.0, 70.0,
          105.0, 0.4, 0.2, 20.0, 'melt-out', 80.0,
          'melts clean and reclaims',
          'Core alternate: shrub wax, grows far more hydroponically '
          'than carnauba.'),
    _feed('machinable-wax-block', 'Machinable wax block (commercial)',
          'machinable-wax', 'supported', 'common-industrial', False,
          '', ['cnc'], 930.0, 5.0, 100.0, 116.0,
          0.0, 0.0, 0.0, 0.0, 'melt-out', 120.0,
          'melts out and reclaims; chips from machining remelt into '
          'new blocks',
          'Paraffin/LDPE blend sold for CNC — hard, high softening, '
          'excellent surface finish. Bought, not grown.'),
    _feed('wax-filament-fdm', 'Wax FDM filament (commercial, Voron)',
          'wax-filament', 'supported', 'common-industrial', False,
          '', ['fdm-voron'], 1000.0, 4.0, 45.0, 260.0,
          175.0, 0.4, 0.2, 30.0, 'melt-out', 270.0,
          'melts out near-residue-free at oven temps (MoldLay-class)',
          'Prints on a STANDARD Voron/cartesian FDM machine — no '
          'auger extruder needed. Soft at low temp: handle cool.'),
    _feed('pla-filament', 'PLA filament (commercial, Voron)',
          'pla', 'supported', 'common-industrial', False,
          '', ['fdm-voron'], 1240.0, 40.0, 60.0, 0.0,
          210.0, 0.4, 0.2, 80.0, 'burn-out', 500.0,
          'lost-PLA burnout ~500°C leaves ash traces (named); '
          'mechanical demold is the alternative for open molds',
          'Strong, ubiquitous, prints fast on a Voron. Tg 60°C = the '
          'structural ceiling — a hot mold cure can soften it (the '
          'cast-3 thermal gate checks this per chain).'),
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
        'objects': ['MoldDefinition', 'MasterFeedstockDefinition',
                    'MoldNestingChain', 'CastingStageDefinition'],
    }),
}]


def seed_casting(manager):
    """Converge feedstock + mold rows (seed_upsert semantics — a
    human's is_prior=False row is skipped loudly), then derive every
    mold's geometry. Never raises for one bad row."""
    from casting.casting_basis import (
        MasterFeedstockDefinition, MoldDefinition,
    )
    from casting.chain_basis import (
        CastingStageDefinition, MoldNestingChain,
    )
    from casting.chain_seed import (
        SEED_CASTING_STAGES, SEED_NESTING_CHAINS,
    )
    from casting.mold_geometry import derive_mold
    from composition.seed_upsert import upsert_seed_pairs

    upsert = upsert_seed_pairs(manager, [
        ('MasterFeedstockDefinition', MasterFeedstockDefinition,
         SEED_MASTER_FEEDSTOCKS),
        ('MoldDefinition', MoldDefinition, SEED_MOLDS),
        # chains before stages that name them (chain_ref).
        ('MoldNestingChain', MoldNestingChain, SEED_NESTING_CHAINS),
        ('CastingStageDefinition', CastingStageDefinition,
         SEED_CASTING_STAGES),
    ], tag='CastingSeed')
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
