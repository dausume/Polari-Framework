"""
@cross-cutting
@module waxsupply.wax_analysis
@tags @xc:bindings

wax-1 analysis — catalog wax sources, filter to hydroponic-feasible
ones, recommend sources for a manufacturing use (molds / electronic
masks), and project yield. Duck-typed manager (stdlib-only selftests).
Flagged priors.

For MOLDS + ELECTRONIC MASKS the wax must hold fine detail and burn out
cleanly: hardness + a suitable melt point are the fit metrics — a
suitability score ranks harder, higher-melting waxes first for those
uses.

@consumers
  - waxsupply.wax_api; supplychain
@see /SALTWATER_FOOD_FOREST_SPEC.md (macroalgae wax additives)
"""

import json

#: Melt-point window (C) that's convenient for lost-wax + masking work.
IDEAL_MELT_MIN, IDEAL_MELT_MAX = 55.0, 90.0
PRIORS_NOTE = ('wax properties + yields are literature-range priors')


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _f(row, attr, default=0.0):
    value = getattr(row, attr, default)
    try:
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return float(default)


def _parse(text, fallback='[]'):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def _uses(source):
    return ([getattr(source, 'primary_use', '')]
            + _parse(getattr(source, 'secondary_uses_json', '[]')))


def _card(source, manager=None):
    ref = getattr(source, 'wax_material_ref', '')
    resolved = (manager is not None
                and _named(manager, 'MaterialsScienceMaterial', ref)
                is not None) if ref else False
    return {'name': getattr(source, 'name', ''),
            'displayName': getattr(source, 'display_name', ''),
            'sourceType': getattr(source, 'source_type', ''),
            'organism': getattr(source, 'organism', ''),
            'meltPointC': _f(source, 'melt_point_c', 0),
            'hardness': _f(source, 'hardness', 0),
            'hydroponicFeasibility':
                getattr(source, 'hydroponic_feasibility', ''),
            'primaryUse': getattr(source, 'primary_use', ''),
            'uses': _uses(source),
            'waxMaterialRef': ref, 'materialResolved': resolved}


def wax_catalog(manager):
    """Every wax source with its properties + material link."""
    out = [_card(s, manager) for s in _rows(manager, 'WaxSourceDefinition')]
    return {'ok': True, 'sources': out, 'count': len(out),
            'priorsFlagged': True, 'note': PRIORS_NOTE}


def hydroponic_wax_sources(manager):
    """Only the sources that actually grow in a hydroponic / food-forest
    system (easy or moderate) — the answer to 'wax from our systems'."""
    ok_levels = ('easy', 'moderate')
    out = [_card(s, manager) for s in _rows(manager, 'WaxSourceDefinition')
           if getattr(s, 'hydroponic_feasibility', '') in ok_levels]
    return {'ok': True, 'hydroponicSources': out, 'count': len(out),
            'note': 'sources feasible to grow in-system (easy/moderate); '
                    'harder ones (e.g. carnauba palm) need dwarf/'
                    'container culture. ' + PRIORS_NOTE}


def _mold_mask_suitability(source):
    """0-1 fit for molds / electronic masks: harder + a melt point in
    the workable window scores higher (holds detail, burns out clean)."""
    hardness = max(0.0, min(1.0, _f(source, 'hardness', 0.5)))
    melt = _f(source, 'melt_point_c', 60.0)
    if IDEAL_MELT_MIN <= melt <= IDEAL_MELT_MAX:
        melt_fit = 1.0
    else:
        # linear falloff outside the window
        gap = (IDEAL_MELT_MIN - melt if melt < IDEAL_MELT_MIN
               else melt - IDEAL_MELT_MAX)
        melt_fit = max(0.0, 1.0 - gap / 40.0)
    return round(0.7 * hardness + 0.3 * melt_fit, 3)


def wax_for_use(manager, use):
    """Rank wax sources for a manufacturing use. For mold/electronic-mask
    the ranking is the hardness+melt suitability; for others it's simply
    the sources that list the use, ordered by hardness."""
    sources = [s for s in _rows(manager, 'WaxSourceDefinition')
               if use in _uses(s)]
    if not sources:
        return {'ok': False, 'error': f"no wax source serves use '{use}'",
                'suggestion': {'knob': 'WaxSourceDefinition primary/'
                                       'secondary uses',
                               'action': 'tag a source with this use',
                               'evidence': 'no source lists it'}}
    detail = []
    for s in sources:
        card = _card(s, manager)
        card['suitability'] = _mold_mask_suitability(s) \
            if use in ('mold', 'electronic-mask') else \
            round(_f(s, 'hardness', 0.5), 3)
        detail.append(card)
    detail.sort(key=lambda c: c['suitability'], reverse=True)
    return {'ok': True, 'use': use, 'ranked': detail,
            'recommended': detail[0]['name'],
            'note': ('mold/mask ranked by hardness + melt-window fit'
                     if use in ('mold', 'electronic-mask')
                     else 'ranked by hardness') + '. ' + PRIORS_NOTE}


def wax_yield(manager, source_name, units=1.0, years=1.0):
    """Projected wax output (g) from `units` plants/kg over `years`."""
    source = _named(manager, 'WaxSourceDefinition', source_name)
    if source is None:
        return {'ok': False,
                'error': f"no WaxSourceDefinition named '{source_name}'"}
    per = _f(source, 'yield_g_per_year', 0.0)
    total = per * float(units) * float(years)
    return {'ok': True, 'source': source_name,
            'yieldBasis': getattr(source, 'yield_basis', ''),
            'units': float(units), 'years': float(years),
            'waxGramsPerYear': round(per * float(units), 2),
            'totalWaxGrams': round(total, 2),
            'primaryUse': getattr(source, 'primary_use', ''),
            'priorsFlagged': True, 'note': PRIORS_NOTE}
