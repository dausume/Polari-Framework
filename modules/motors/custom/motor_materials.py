"""
@module motors.custom.motor_materials

COMPLETE MATERIAL ACCOUNTABILITY for a motor design (Dustin
2026-07-29: "a complete accountability of its physical materials
being used and being able to follow them to how they were derived
properties wise").

For every material slot of a design (rotor, stator, winding), the
trail runs the WHOLE chain:
  design slot -> catalog option (realization level + gates)
    -> each property VALUE with its per-value provenance tag + note
    -> the msci seam (the FEM homogenization models a mu_eff number
       came from, BY REFERENCE — object coherence, never copied)
    -> the powder row behind it (theoretical watermark if any)
    -> the supplychain derivation: dated cited prices (URL +
       observed_at + est flag), seeded recipes with components, and
       the cascaded make-vs-buy resolution (self-made intermediates
       named, energy exclusions stated)
    -> the mag-2r role verdicts the slot demands.

Nothing in the trail is invented: absent links say so ('no
citations', 'no recipes', 'no msci model') rather than vanishing.
"""

import json

from magnetics.custom.magnet_analysis import (
    gates_for, role_viability, _named, _rows,
)


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except ValueError:
        return default


def _property_trail(option):
    props = _loads(option, 'properties_json', {})
    return [{'property': name,
             'value': entry.get('value'),
             'unit': entry.get('unit', ''),
             'provenance': entry.get('provenance', ''),
             'note': entry.get('note', '')}
            for name, entry in sorted(props.items())]


def _msci_trail(manager, option):
    ref = getattr(option, 'msci_material_ref', '')
    if not ref:
        return {'msciMaterialRef': None,
                'note': 'no msci material row linked'}
    material = _named(manager, 'MaterialsScienceMaterial', ref)
    models = [
        {'name': getattr(m, 'name', ''),
         'displayName': getattr(m, 'display_name', ''),
         'physicsRef': getattr(m, 'physics_ref', ''),
         'description': getattr(m, 'description', '')}
        for m in _rows(manager, 'FEMModelDefinition')
        if getattr(m, 'name', '').startswith(ref)]
    return {'msciMaterialRef': ref,
            'materialFound': material is not None,
            'femModels': models,
            'note': ('mu_eff numbers derive from these FEM '
                     'homogenization runs (k<->mu analogy, linear '
                     'magnetostatics)' if models else
                     'msci row linked but no FEM model found on '
                     'this instance (materialsScience module '
                     'gated off?)')}


def _powder_trail(manager, option):
    ref = getattr(option, 'powder_ref', '')
    if not ref:
        return None
    powder = _named(manager, 'MagneticPowderDefinition', ref)
    if powder is None:
        return {'powderRef': ref, 'refusal': 'powder row missing'}
    return {'powderRef': ref,
            'isTheoretical': getattr(powder, 'is_theoretical',
                                     False),
            'propertyProvenance': getattr(
                powder, 'property_provenance', ''),
            'notes': getattr(powder, 'notes', '')}


def _supply_trail(manager, item_ref):
    if not item_ref:
        return {'itemRef': None,
                'note': 'no supplychain item linked — this option '
                        'is not a priced thing (reference rows, '
                        'derived composites without their own '
                        'listing)'}
    citations = []
    for c in _rows(manager, 'PriceCitation'):
        if getattr(c, 'item_ref', '') != item_ref:
            continue
        citations.append({
            'name': getattr(c, 'name', ''),
            'source': getattr(c, 'source_ref', ''),
            'price': getattr(c, 'price', 0.0),
            'currency': getattr(c, 'currency', 'USD'),
            'amount': getattr(c, 'amount', 0.0),
            'unit': getattr(c, 'amount_unit', ''),
            'observedAt': getattr(c, 'observed_at', ''),
            'url': getattr(c, 'citation_url', ''),
            'isEstimate': getattr(c, 'is_estimate', False),
            'note': getattr(c, 'citation_note', '')})
    recipes = []
    for f in _rows(manager, 'ProductFormula'):
        if getattr(f, 'product_item_ref', '') != item_ref:
            continue
        recipes.append({
            'name': getattr(f, 'name', ''),
            'displayName': getattr(f, 'display_name', ''),
            'components': _loads(f, 'components_json', []),
            'yieldFraction': getattr(f, 'yield_fraction', 1.0),
            'notes': getattr(f, 'notes', '')})
    trail = {'itemRef': item_ref,
             'citations': citations,
             'recipes': recipes}
    if not citations:
        trail['citationNote'] = 'no dated citations for this item'
    if not recipes:
        trail['recipeNote'] = 'no seeded make-recipe'
    try:
        from supplychain.custom.formula_analysis import (
            cascaded_cost, effective_unit_price,
        )
        eff = effective_unit_price(manager, item_ref)
        if eff is not None:
            trail['effectivePrice'] = {
                'usdPerKg': eff['normalized'], 'via': eff['via'],
                'source': eff.get('source', ''),
                'isEstimate': bool(eff.get('isEstimate'))}
            if eff['via'] == 'made':
                trail['effectivePrice']['madeIntermediates'] = \
                    eff.get('madeIntermediates', [])
        if recipes:
            formula = _named(manager, 'ProductFormula',
                             recipes[0]['name'])
            cc = cascaded_cost(manager, formula)
            if cc.get('ok'):
                trail['cascade'] = {
                    'usdPerKg': cc['usdPerKg'],
                    'breakdown': cc.get('breakdown', []),
                    'madeIntermediates': cc.get(
                        'madeIntermediates', []),
                    'note': 'energy for made intermediates '
                            'EXCLUDED-LOUD (v1 costing rule)'}
    except ImportError:
        trail['supplychainNote'] = ('supplychain module not '
                                    'enabled — pricing trail '
                                    'unavailable on this instance')
    return trail


#: role expectations per slot key (mirrors motor_designer).
_SLOT_ROLES = {'rotor_material': 'torque-magnet',
               'stator_material': 'magnetic-conductor',
               'winding_material': 'electric-conductor-power'}


def material_accountability(manager, design_name):
    """The full bill: every material slot of the design followed to
    how its properties were derived."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no MotorDesignDefinition named '
                           f'"{design_name}"'}
    params = _loads(design, 'params_json', {})
    # the winding is a real physical material even though torque
    # math only needs its MMF — default to the cited magnet wire.
    slots = {'rotor_material': params.get('rotor_material', ''),
             'stator_material': params.get('stator_material', ''),
             'winding_material': params.get(
                 'winding_material', 'opt-copper-magnet-wire')}
    out_slots = []
    for slot, material in slots.items():
        if not material:
            out_slots.append({'slot': slot,
                              'note': 'no material in this slot'})
            continue
        option = _named(manager, 'MagneticMaterialOption', material)
        if option is None:
            out_slots.append({'slot': slot, 'material': material,
                              'refusal': 'unknown catalog option'})
            continue
        gates = gates_for(manager, option)
        role_name = _SLOT_ROLES.get(slot, '')
        role = _named(manager, 'MaterialUseRole', role_name)
        verdict = (role_viability(manager, option, role)
                   if role is not None else None)
        # saliency-only rotors are magnetic conductors, not PMs —
        # report the role that actually applies.
        if (slot == 'rotor_material' and verdict is not None
                and verdict['verdict'] != 'viable'
                and float(params.get('saliency_ratio', 1.0)) > 1.0):
            alt = _named(manager, 'MaterialUseRole',
                         'magnetic-conductor')
            if alt is not None:
                verdict = role_viability(manager, option, alt)
                role_name = 'magnetic-conductor (saliency rotor)'
        out_slots.append({
            'slot': slot,
            'material': material,
            'displayName': getattr(option, 'display_name', ''),
            'family': getattr(option, 'family', ''),
            'realizationLevel': gates['realizationLevel'],
            'buyableCited': gates['buyableCited'],
            'recipeSeeded': gates['recipeSeeded'],
            'businessAllowed': gates['business']['allowed'],
            'watermark': gates['simulation']['watermark'],
            'role': {'name': role_name,
                     'verdict': (verdict or {}).get('verdict'),
                     'honestyNote': (verdict or {}).get(
                         'honestyNote', '')},
            'properties': _property_trail(option),
            'msci': _msci_trail(manager, option),
            'powder': _powder_trail(manager, option),
            'supply': _supply_trail(
                manager, getattr(option, 'item_ref', '')),
            'optionNotes': getattr(option, 'notes', ''),
        })
        # derived composites without their own listing: follow the
        # FILLER POWDER's supply trail for accountability (clearly
        # labeled — the composite's own cost gate stays honest).
        if not getattr(option, 'item_ref', ''):
            powder = _named(manager, 'MagneticPowderDefinition',
                            getattr(option, 'powder_ref', ''))
            powder_item = getattr(powder, 'item_ref', '') \
                if powder else ''
            if powder_item:
                out_slots[-1]['fillerSupply'] = {
                    'note': 'this option has no listing of its '
                            'own — the trail below follows its '
                            'FILLER powder feedstock',
                    **_supply_trail(manager, powder_item)}
    return {'ok': True, 'design': design_name,
            'displayName': getattr(design, 'display_name', ''),
            'ladderRung': getattr(design, 'ladder_rung', ''),
            'slots': out_slots,
            'buildRequirements': _loads(
                design, 'build_requirements_json', {}),
            'trailNote': 'every value above carries its provenance '
                         'tag; absent links are stated, never '
                         'hidden — the chain runs design slot -> '
                         'catalog option -> property provenance -> '
                         'msci FEM reference -> powder row -> '
                         'dated citations / recipes / cascaded '
                         'make-vs-buy'}
