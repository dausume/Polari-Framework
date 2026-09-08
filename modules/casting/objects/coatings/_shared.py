"""@module casting.objects.coatings._shared — what the coatings row classes share (constants, seeds, helpers); split from coatings_basis.py (sap-2c)."""
from casting.custom.chain_analysis import (
    _process_temp, _stages_of, chain_report,
    shrink_compensation_report,
)
from casting.custom.wax_feasibility import _row_named, _rows
import json

COATING_PURPOSES = ('release', 'sealing', 'surface-finish')
SEED_MOLD_COATINGS = [
    {'name': 'jojoba-release', 'display_name': 'Jojoba oil release',
     'coating_material_ref': 'jojoba', 'purpose': 'release',
     'accessibility_tier': 'household', 'renewable': True,
     'max_service_temp_c': 150.0,
     'applies_to_mold_materials_json': json.dumps(
         ['geopolymer', 'carnauba-pellet', 'candelilla-pellet',
          'machinable-wax-block']),
     'is_prior': True, 'provenance_id': 'cast-8',
     'notes': "waxsupply's named mold release — a liquid wax ester "
              'from a drought-tolerant shrub; the renewable default '
              'for cures and ambient presses.'},
    {'name': 'beeswax-wash', 'display_name': 'Beeswax wash (thin)',
     'coating_material_ref': 'beeswax', 'purpose': 'sealing',
     'accessibility_tier': 'household', 'renewable': True,
     'max_service_temp_c': 60.0,
     'applies_to_mold_materials_json': json.dumps(['geopolymer']),
     'is_prior': True, 'provenance_id': 'cast-8',
     'notes': 'seals geopolymer pores for a cleaner surface; melts '
              'low — cure-stage only.'},
    {'name': 'graphite-dust', 'display_name': 'Graphite parting dust',
     'coating_material_ref': 'graphite', 'purpose': 'release',
     'accessibility_tier': 'common-industrial', 'renewable': False,
     'max_service_temp_c': 3000.0,
     'applies_to_mold_materials_json': json.dumps(
         ['fireclay-firebrick', 'earthenware-terracotta',
          'stoneware', 'mullite', 'alumina', 'cordierite',
          'dolomitic-basic-refractory', 'geopolymer']),
     'is_prior': True, 'provenance_id': 'cast-8',
     'notes': 'the metal-pour release — inert to any pour we can '
              'reach; bought, not grown (carried honestly).'},
]
_STRATEGY_OF = {
    'geopolymer': 'geopolymer-cast',
    'fireclay-firebrick': 'ceramic-fired',
    'earthenware-terracotta': 'ceramic-fired',
}
_WAX_KINDS = ('natural-wax', 'machinable-wax', 'wax-filament')
def _strategy_for(manager, mold_ref):
    if mold_ref in _STRATEGY_OF:
        return _STRATEGY_OF[mold_ref]
    # ANY fired ceramic mold rides the ceramic-fired priors — the
    # wizard selects the ceramic from data, so the map must not be
    # a hand-kept list.
    if _row_named(manager, 'CeramicSample', mold_ref) is not None:
        return 'ceramic-fired'
    feed = _row_named(manager, 'MasterFeedstockDefinition', mold_ref)
    if feed is not None:
        if getattr(feed, 'material_kind', '') in _WAX_KINDS:
            return 'wax-printed'
    return None
def resolve_release_coating(manager, mold_ref, process_temp_c):
    """Best applicable release coat: applies to this mold material,
    survives the process temp; RENEWABLE + most-local first. None +
    reason when nothing qualifies (a named absence, not a default)."""
    candidates = []
    for c in _rows(manager, 'MoldCoatingDefinition'):
        if getattr(c, 'purpose', '') != 'release':
            continue
        try:
            applies = json.loads(getattr(
                c, 'applies_to_mold_materials_json', '[]') or '[]')
        except (TypeError, ValueError):
            applies = []
        if mold_ref not in applies:
            continue
        if float(getattr(c, 'max_service_temp_c', 0.0) or 0.0) \
                < process_temp_c:
            continue
        candidates.append(c)
    if not candidates:
        return None, (f"no release coating applies to '{mold_ref}' "
                      f'at {process_temp_c:.0f}°C — a named absence '
                      f'(seed one or measure an alternative)')
    tier_rank = {'household': 0, 'common-industrial': 1,
                 'mined-nonlocal': 2, 'lab-reagent': 3}
    best = sorted(candidates, key=lambda c: (
        not getattr(c, 'renewable', False),
        tier_rank.get(getattr(c, 'accessibility_tier', ''), 9)))[0]
    return best, None
def chain_full_report(manager, chain_name):
    """The cast-8 composition: gates + shrink + economics +
    coatings, every number traceable to a row or a NAMED prior."""
    gates = chain_report(manager, chain_name)
    if not gates.get('ok'):
        return gates
    shrink = shrink_compensation_report(manager, chain_name)
    try:
        from supplychain.custom.mold_analysis import MOLD_STRATEGY_PRIORS
    except ImportError:
        MOLD_STRATEGY_PRIORS = {}
    economics, coatings, gaps = [], [], list(gates.get('gaps', []))
    total_mold_kg = 0.0
    for st in _stages_of(manager, chain_name):
        if getattr(st, 'stage_kind', 'cast') != 'cast':
            continue
        mold_ref = getattr(st, 'mold_material_ref', '')
        strategy = _strategy_for(manager, mold_ref)
        prior = MOLD_STRATEGY_PRIORS.get(strategy) if strategy \
            else None
        entry = {'stage': getattr(st, 'name', ''),
                 'moldMaterial': mold_ref, 'strategy': strategy}
        if prior:
            entry.update({
                'moldMassKg': prior['mold_mass_kg'],
                'cyclesEst': prior['cycles_est'],
                'massPerCastKg': round(prior['mold_mass_kg']
                                       / prior['cycles_est'], 4),
                'releasePerCastKg': prior['release_per_cast_kg'],
                'endOfLife': prior['end_of_life'],
                'basis': prior['basis']})
            total_mold_kg += prior['mold_mass_kg']
            if prior['release_per_cast_kg'] > 0:
                proc = _process_temp(manager, st)
                temp = proc.get('tempC', 25.0) if proc.get('ok') \
                    else 25.0
                coat, reason = resolve_release_coating(
                    manager, mold_ref, temp)
                if coat is not None:
                    coatings.append({
                        'stage': entry['stage'],
                        'coating': getattr(coat, 'name', ''),
                        'renewable': bool(getattr(coat, 'renewable',
                                                  False)),
                        'tier': getattr(coat, 'accessibility_tier',
                                        ''),
                        'evidence': f'release mandatory for '
                                    f'{strategy} '
                                    f"({prior['basis'][:60]}…); "
                                    f'survives {temp:.0f}°C'})
                else:
                    gaps.append(f"stage '{entry['stage']}': {reason}")
        else:
            gaps.append(f"stage '{entry['stage']}': no mold-economics "
                        f"prior for '{mold_ref}' (PLA masters burn "
                        f'out — no reuse strategy exists; named)')
        economics.append(entry)
    recycling = sorted({e['endOfLife'] for e in economics
                        if e.get('endOfLife')})
    return {'ok': True, 'chain': chain_name,
            'verdict': gates['verdict'], 'parity': gates['parity'],
            'stages': gates['stages'],
            'blockers': gates['blockers'],
            'findings': gates['findings'],
            'shrink': {'expectedFinalScale':
                       shrink.get('expectedFinalScale'),
                       'compensation': shrink.get('compensation')},
            'economics': economics,
            'totalMoldMassKg': round(total_mold_kg, 3),
            'releaseCoatings': coatings,
            'recyclingRoutes': recycling,
            'gaps': gaps,
            'note': 'economics ride supplychain.custom.mold_analysis '
                    'priors; reuse counting rides the existing '
                    'waxprint.MoldLifecycleRecord via '
                    'CastingRunRecord — bound, not rebuilt.'}
