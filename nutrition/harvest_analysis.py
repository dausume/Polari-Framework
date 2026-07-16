"""
@cross-cutting
@module nutrition.harvest_analysis
@tags @xc:bindings

nut-2 math — turn a plant HARVEST into meal-nutrient yield. Duck-typed
manager (stdlib-only selftests).

harvest_mass_g: realized edible FRESH mass from the aqp-4 PlantParts'
volumes (× dry density → dry mass → fresh mass via fresh/dry ratio),
using aquaponics.plant_growth_simplified's realized per-part volumes
when a grow_result is supplied, else the aqp-4 mature_volume_cm3.
Which volume it used travels with the number.

harvest_nutrients: fresh mass × NutrientContent/100 g → per-nutrient
yield for one harvest, with prior flags carried. Honest refusal (naming
the knob) when a food has no NutrientContent rows.

This is the "analyze a plant's harvest in terms of nutrients for meals"
capability — and because the plant is the SAME one grown in the flowing
self-watering pot (aqp-1), a real grow run feeds real yields. See
aquaponics/plant_growth_simplified.py (2026-07-15) for what that grow
run now actually is — a distilled aggregate read pulling its constants
from the real per-plant model, not an independent simulation.

@consumers
  - nutrition.fulfillment_analysis (nut-5), nutrition.food_api
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-2
"""

import json


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


def _part_fresh_mass_g(part, food, volume_cm3):
    """Fresh edible mass of one part at a given volume."""
    density = _f(part, 'dry_density_g_cm3', 0.3)
    dry_mass = volume_cm3 * density
    ratio = _f(food, 'fresh_to_dry_ratio', 0.0)
    if ratio <= 0:
        dmf = _f(part, 'dry_matter_fraction', 0.12) or 0.12
        ratio = 1.0 / dmf
    fresh = dry_mass * ratio
    fresh *= (1.0 - _f(food, 'moisture_loss_fraction', 0.0))
    return fresh


def harvest_mass_g(manager, food_name, grow_result=None):
    """Realized fresh edible mass (g) of one harvest.

    grow_result: an aqp-8 grow() result; when given, uses each edible
    part's realized finalVolumeCm3, else the aqp-4 mature_volume_cm3."""
    food = _named(manager, 'FoodItem', food_name)
    if food is None:
        return {'ok': False,
                'error': f"no FoodItem named '{food_name}'"}
    edible = _parse(getattr(food, 'edible_parts_json', '[]'))
    if not edible:
        return {'ok': False,
                'error': f"FoodItem '{food_name}' lists no edible parts",
                'suggestion': {'knob': 'FoodItem.edible_parts_json',
                               'action': 'name the PlantPart(s) eaten',
                               'evidence': 'harvest mass needs the parts'}}
    realized = {}
    if grow_result and grow_result.get('perPart'):
        realized = {p['part']: p['finalVolumeCm3']
                    for p in grow_result['perPart']}

    total, breakdown = 0.0, []
    used_realized = False
    for part_name in edible:
        part = _named(manager, 'PlantPart', part_name)
        if part is None:
            continue
        if part_name in realized:
            volume = realized[part_name]
            used_realized = True
        else:
            volume = _f(part, 'mature_volume_cm3', 100.0)
        mass = _part_fresh_mass_g(part, food, volume)
        total += mass
        breakdown.append({'part': part_name,
                          'volumeCm3': round(volume, 2),
                          'freshMassG': round(mass, 2)})
    return {'ok': True, 'food': food_name,
            'freshMassG': round(total, 2),
            'perPart': breakdown,
            'volumeSource': 'aqp-8 realized grow' if used_realized
                            else 'aqp-4 mature volume',
            'preparation': getattr(food, 'preparation', 'raw')}


def harvest_nutrients(manager, food_name, grow_result=None):
    """Per-nutrient yield (in each nutrient's unit) for one harvest."""
    mass = harvest_mass_g(manager, food_name, grow_result=grow_result)
    if not mass.get('ok'):
        return mass
    contents = [c for c in _rows(manager, 'NutrientContent')
                if getattr(c, 'food_name', '') == food_name]
    if not contents:
        return {'ok': False,
                'error': f"FoodItem '{food_name}' has no NutrientContent",
                'suggestion': {
                    'knob': 'NutrientContent rows (food_name)',
                    'action': 'seed per-100g nutrient values for this '
                              'food',
                    'evidence': 'cannot compute meal nutrients without '
                                'the composition table'}}
    grams = mass['freshMassG']
    priors = []
    yields = {}
    for c in contents:
        nutrient = getattr(c, 'nutrient_name', '')
        per_harvest = _f(c, 'amount_per_100g', 0.0) * grams / 100.0
        yields[nutrient] = {'amount': round(per_harvest, 4),
                            'unit': getattr(c, 'unit', ''),
                            'per100g': _f(c, 'amount_per_100g', 0.0),
                            'isPrior': bool(getattr(c, 'is_prior', True))}
        if getattr(c, 'is_prior', True):
            priors.append(nutrient)
    return {'ok': True, 'food': food_name,
            'freshMassG': grams,
            'volumeSource': mass['volumeSource'],
            'preparation': mass['preparation'],
            'nutrients': yields, 'flaggedPriors': sorted(set(priors)),
            'note': 'per-harvest yield = fresh mass × per-100g content; '
                    'content values are USDA/literature priors.'}


def food_catalog(manager):
    """Every FoodItem with its headline nutrients (the browse view)."""
    out = []
    for food in _rows(manager, 'FoodItem'):
        name = getattr(food, 'name', '')
        contents = [c for c in _rows(manager, 'NutrientContent')
                    if getattr(c, 'food_name', '') == name]
        headline = sorted(
            ({'nutrient': getattr(c, 'nutrient_name', ''),
              'per100g': _f(c, 'amount_per_100g', 0.0),
              'unit': getattr(c, 'unit', '')} for c in contents),
            key=lambda x: x['per100g'], reverse=True)[:5]
        out.append({'name': name,
                    'displayName': getattr(food, 'display_name', ''),
                    'plant': getattr(food, 'plant_name', ''),
                    'preparation': getattr(food, 'preparation', 'raw'),
                    'topNutrients': headline})
    return {'ok': True, 'foods': out, 'count': len(out)}
