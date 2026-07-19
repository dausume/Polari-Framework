"""
@module pspp.wax_states

pspp-11 WAX HALF: the existing waxprint world mapped onto the
MaterialState vocabulary — representation upgraded, behavior
UNCHANGED (the generality proof's other leg beside the CMC library).

Every WaxFeedstockDefinition already carries its route temperatures
(melt_point_c / safe_melt_min_c / safe_melt_max_c); the wax
ProcessingStage rows (wax-solid → wax-softened → wax-melt →
wax-superheated) were seeded in pspp-2. This module DERIVES the
four-state route per feedstock as VIRTUAL states (the implicit-
canonical idiom: real as subjects, row-less until something writes
to them) — zero writes, zero schema changes, waxprint untouched.
The superheated state exists precisely so refusals can cite it: it
is the state the melt gate refuses to enter.

@consumers
  - pspp.pspp_api (GET /api/pspp/wax-states)
"""

from pspp.state_resolution import state_key

#: (stage, phase, how the feedstock's own numbers bound it)
_ROUTE = (
    ('wax-solid', 'solid',
     lambda f: {'temperature_c_max': f['melt_point_c']},
     'Below melt onset — machinable regime.'),
    ('wax-softened', 'mixed',
     lambda f: {'temperature_c_min': f['melt_point_c'],
                'temperature_c_max': f['safe_melt_min_c']},
     'Inside the melt range — smears under cutters, too stiff to '
     'flow.'),
    ('wax-melt', 'liquid',
     lambda f: {'temperature_c_min': f['safe_melt_min_c'],
                'temperature_c_max': f['safe_melt_max_c']},
     'Fully molten inside the processing window — the printable '
     'state.'),
    ('wax-superheated', 'liquid',
     lambda f: {'temperature_c_min': f['safe_melt_max_c']},
     'Above the no-volatiles ceiling — REFUSED by the melt gate; '
     'exists so refusals can cite it.'),
)


def _get(row, key, default=None):
    return row.get(key, default) if isinstance(row, dict) \
        else getattr(row, key, default)


def _rows(manager, table):
    rows = (getattr(manager, 'objectTables', None) or {}).get(table, {})
    return list(rows.values()) if isinstance(rows, dict) else list(rows)


def feedstock_state_route(feedstock):
    """One feedstock's four-state route as virtual MaterialState
    payloads — every bound comes from the feedstock row itself."""
    f = {k: _get(feedstock, k) for k in
         ('name', 'display_name', 'wax_material_ref', 'melt_point_c',
          'safe_melt_min_c', 'safe_melt_max_c')}
    if not f['wax_material_ref']:
        return {'ok': False,
                'refusal': f"feedstock {f['name']!r} names no "
                           'wax_material_ref',
                'suggestion': 'set the materialsScience material ref '
                              'on the feedstock row'}
    material = f['wax_material_ref']
    states, previous = [], None
    for stage, phase, bounds, note in _ROUTE:
        key = state_key(material, f"{stage}--{f['name']}")
        states.append({
            'stateKey': key,
            'material': material,
            'stateName': f"{stage}--{f['name']}",
            'isCanonical': False,
            'processingStage': stage,
            'thermodynamicPhase': phase,
            'environmentalSnapshot': bounds(f),
            'parents': [previous] if previous else [],
            'producingExecution': '',
            'validationStatus': 'unvalidated',
            'virtual': True,
            'feedstock': f['name'],
            'note': note,
            'provenance': 'pspp-11 wax retrofit — derived from '
                          f"WaxFeedstockDefinition {f['name']!r}; "
                          'behavior unchanged, representation '
                          'upgraded',
        })
        previous = key
    return {'ok': True, 'feedstock': f['name'],
            'material': material, 'states': states,
            'note': 'virtual states (implicit-canonical idiom) — '
                    'no rows written; the melt gate already '
                    'enforces the superheated refusal'}


def wax_state_map(manager):
    """All feedstocks' routes — live rows win, waxprint seeds are the
    fallback (same pattern as every pspp view)."""
    feedstocks = _rows(manager, 'WaxFeedstockDefinition')
    if not feedstocks:
        try:
            from waxprint.waxprint_seed import SEED_FEEDSTOCKS
            feedstocks = SEED_FEEDSTOCKS
        except ImportError:
            return {'ok': False,
                    'refusal': 'no WaxFeedstockDefinition rows and '
                               'the waxprint module is not loaded',
                    'suggestion': 'pol modules get waxprint, or seed '
                                  'feedstock rows'}
    routes = [feedstock_state_route(f) for f in feedstocks]
    return {'ok': True,
            'routes': [r for r in routes if r.get('ok')],
            'refused': [r for r in routes if not r.get('ok')]}
