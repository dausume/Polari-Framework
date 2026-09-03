"""
@cross-cutting
@module nutrition.market_analysis
@tags @xc:bindings

mpa-2 — market arithmetic over the market_basis rows:

  resolve_grams        purchased quantity ("2 lb", "3 each") →
                       grams: exact units convert, count units ride
                       UnitWeightPrior rows (approximate, LABELED;
                       household override rows win), anything else
                       REFUSES naming the missing prior.
  normalized_prices    every PriceObservation → price-per-kg with
                       location + age + the weight-basis label.
  price_report         per-food price compare across geolocations,
                       best price named with its store + age.
  purchased_item_report  "assign nutritional information and weight
                       approximately for things that are purchased":
                       one purchase → approx grams + per-item
                       nutrient amounts (per-100g × grams) with
                       provenance labels riding every step.
  export_price_references  mo-2: live observations → month-level
                       PriceReference rows (mealoptions), purchaser /
                       place / day stripped, upserted so a re-export
                       converges.
  advice               mo-2: the local-first price advice over the
                       PriceReference rows (or, when none are
                       published yet, over the live observations
                       aggregated on the fly — and it SAYS so).

@consumers
  - nutrition.pantry_analysis, mealplanning_api
  - nutrition.selftest_market
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-2,
     AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-2
"""

from datetime import date

from mealoptions.price_reference_analysis import (
    aggregate_references, price_advice,
)
from mealoptions.price_reference_basis import (
    CHAIN_KINDS, LOCAL_KINDS, PriceReference,
)
from nutrition.market_basis import EXACT_UNIT_GRAMS
from nutrition.person_analysis import _f, _rows


def resolve_grams(manager, food_name, quantity, unit,
                  household_name=''):
    """Approximate grams for `quantity` of `unit` of a food."""
    quantity = float(quantity or 0.0)
    unit = (unit or '').strip()
    if quantity <= 0:
        return {'ok': False, 'error': 'quantity must be positive'}
    if unit in EXACT_UNIT_GRAMS:
        return {'ok': True, 'grams': quantity * EXACT_UNIT_GRAMS[unit],
                'basis': 'exact-unit-conversion', 'unit': unit}
    shared, household = None, None
    for row in _rows(manager, 'UnitWeightPrior'):
        if (getattr(row, 'food_name', '') != food_name
                or getattr(row, 'unit_label', '') != unit):
            continue
        if getattr(row, 'household_name', '') == household_name \
                and household_name:
            household = row
        elif not getattr(row, 'household_name', ''):
            shared = row
    row = household or shared
    if row is None:
        return {'ok': False,
                'error': f'no weight prior for "{unit}" of '
                         f'"{food_name}" — add a UnitWeightPrior row '
                         f'(weigh one and record it; approximate is '
                         f'fine, invisible is not)'}
    return {'ok': True, 'grams': quantity * _f(row, 'grams', 0.0),
            'basis': ('household-override-prior' if household
                      else 'convention-prior'),
            'unit': unit, 'perUnitG': _f(row, 'grams', 0.0),
            'citation': getattr(row, 'citation', ''),
            'honesty': 'approximate by design — a labeled, tunable '
                       'prior, not a measurement'}


def _age_days(observed_date, today=None):
    if not observed_date:
        return None
    try:
        y, m, d = (int(x) for x in observed_date.split('-'))
        return ((today or date.today()) - date(y, m, d)).days
    except (ValueError, TypeError):
        return None


def normalized_prices(manager, food_name=None, today=None):
    """Every PriceObservation normalized to price-per-kg."""
    locations = {getattr(l, 'name', ''): l
                 for l in _rows(manager, 'SourceLocation')}
    out, refused = [], []
    for obs in _rows(manager, 'PriceObservation'):
        food = getattr(obs, 'food_name', '')
        if food_name is not None and food != food_name:
            continue
        grams = resolve_grams(manager, food,
                              _f(obs, 'package_quantity', 0.0),
                              getattr(obs, 'package_unit', ''))
        if not grams.get('ok'):
            refused.append({'observation': getattr(obs, 'name', ''),
                            'why': grams.get('error')})
            continue
        loc = locations.get(getattr(obs, 'location_name', ''))
        price = _f(obs, 'price', 0.0)
        # mo-2: live rows from before the typing fields read as
        # 'other' / '' (the class docstring's gotcha).
        ownership = (getattr(loc, 'ownership_kind', '') or 'other') \
            if loc else 'other'
        chain = (getattr(loc, 'chain_name', '') or '') \
            if loc and ownership in CHAIN_KINDS else ''
        entry = {
            'observation': getattr(obs, 'name', ''),
            'food': food,
            'location': getattr(obs, 'location_name', ''),
            'locationKind': getattr(loc, 'kind', '') if loc else '',
            'ownershipKind': ownership,
            'chainName': chain,
            'isLocal': ownership in LOCAL_KINDS,
            'region': getattr(loc, 'region_label', '') if loc else '',
            'latitude': _f(loc, 'latitude', 0.0) if loc else 0.0,
            'longitude': _f(loc, 'longitude', 0.0) if loc else 0.0,
            'price': price,
            'currency': getattr(obs, 'currency', 'USD'),
            'package': f'{_f(obs, "package_quantity", 0.0):g} '
                       f'{getattr(obs, "package_unit", "")}',
            'packageG': round(grams['grams'], 1),
            'pricePerKg': (round(price / grams['grams'] * 1000.0, 2)
                           if grams['grams'] > 0 else 0.0),
            'weightBasis': grams['basis'],
            'observedDate': getattr(obs, 'observed_date', ''),
            'ageDays': _age_days(getattr(obs, 'observed_date', ''),
                                 today),
            'isDemo': bool(getattr(obs, 'is_prior', False)),
        }
        out.append(entry)
    return {'ok': True, 'prices': sorted(
        out, key=lambda e: (e['food'], e['pricePerKg'])),
        'refused': refused}


def price_report(manager, food_name=None, today=None):
    """Per-food price comparison across locations, best named."""
    norm = normalized_prices(manager, food_name, today)
    by_food = {}
    for entry in norm['prices']:
        by_food.setdefault(entry['food'], []).append(entry)
    foods = []
    for food, entries in sorted(by_food.items()):
        best = min(entries, key=lambda e: e['pricePerKg'])
        foods.append({
            'food': food,
            'observationCount': len(entries),
            'bestPricePerKg': best['pricePerKg'],
            'bestLocation': best['location'],
            'bestObservedDate': best['observedDate'],
            'bestAgeDays': best['ageDays'],
            'spreadPerKg': round(
                max(e['pricePerKg'] for e in entries)
                - best['pricePerKg'], 2),
            'observations': entries,
        })
    return {'ok': True, 'schema': 'food-prices/1', 'foods': foods,
            'refused': norm['refused'],
            'honesty': 'prices are user-entered observations '
                       '(never scraped); count-unit packages ride '
                       'labeled approximate weight priors; age in '
                       'days is shown, staleness is the reader\'s '
                       'call'}


def best_price_per_kg(manager, food_name, today=None):
    """(pricePerKg, location, ageDays) or None — the pantry/cost
    engines' lookup."""
    report = price_report(manager, food_name, today)
    for food in report['foods']:
        if food['food'] == food_name:
            return {'pricePerKg': food['bestPricePerKg'],
                    'location': food['bestLocation'],
                    'ageDays': food['bestAgeDays']}
    return None


def purchased_item_report(manager, food_name, quantity, unit,
                          household_name='', today=None):
    """One purchase → approximate weight + assigned nutrition."""
    grams = resolve_grams(manager, food_name, quantity, unit,
                          household_name)
    if not grams.get('ok'):
        return grams
    contents = [c for c in _rows(manager, 'NutrientContent')
                if getattr(c, 'food_name', '') == food_name]
    nutrients = {}
    for c in contents:
        nutrients[getattr(c, 'nutrient_name', '')] = {
            'amount': round(_f(c, 'amount_per_100g', 0.0)
                            * grams['grams'] / 100.0, 3),
            'unit': getattr(c, 'unit', ''),
            'provenance': 'per-100g FDC value × approximate grams',
        }
    price = best_price_per_kg(manager, food_name, today)
    report = {
        'ok': True, 'schema': 'purchased-item/1',
        'food': food_name,
        'quantity': float(quantity), 'unit': unit,
        'approxGrams': round(grams['grams'], 1),
        'weightBasis': grams['basis'],
        'nutrients': nutrients,
        'nutrientNote': ('' if nutrients else
                         'no NutrientContent rows for this food — '
                         'nutrition unassigned, named honestly'),
        'honesty': 'weight is an approximate labeled prior; '
                   'nutrition = FDC per-100g × that weight — both '
                   'provenance-carrying, neither a measurement',
    }
    if 'citation' in grams:
        report['weightCitation'] = grams['citation']
    if price is not None:
        report['estimatedCost'] = round(
            price['pricePerKg'] * grams['grams'] / 1000.0, 2)
        report['costBasis'] = (f'best observed price at '
                               f'{price["location"]}'
                               + (f', {price["ageDays"]}d old'
                                  if price['ageDays'] is not None
                                  else ''))
    return report


# ── mo-2: month-level references + local-first advice ────────

def _reference_record(row):
    """One PriceReference row as a FLAT record (screens + advice)."""
    return {
        'name': getattr(row, 'name', ''),
        'food_name': getattr(row, 'food_name', ''),
        'month': getattr(row, 'month', ''),
        'source_type': getattr(row, 'source_type', 'other'),
        'chain_name': getattr(row, 'chain_name', '') or '',
        'region_label': getattr(row, 'region_label', 'unstated'),
        'currency': getattr(row, 'currency', 'USD'),
        'price_per_kg_median': _f(row, 'price_per_kg_median', 0.0),
        'price_per_kg_min': _f(row, 'price_per_kg_min', 0.0),
        'price_per_kg_max': _f(row, 'price_per_kg_max', 0.0),
        'sample_count': int(_f(row, 'sample_count', 0)),
        'weight_basis': getattr(row, 'weight_basis', 'exact'),
        'varies_by_vendor': bool(getattr(row, 'varies_by_vendor', False)),
        'notes': getattr(row, 'notes', ''),
    }


def price_references(manager, food_name=None):
    """Published PriceReference rows as flat records (optionally one
    food), sorted by food, month, median."""
    records = [_reference_record(r) for r in _rows(manager, 'PriceReference')
               if food_name is None
               or getattr(r, 'food_name', '') == food_name]
    records.sort(key=lambda r: (r['food_name'], r['month'],
                                r['price_per_kg_median']))
    return {'ok': True, 'schema': 'price-references/1',
            'count': len(records), 'references': records,
            'honesty': 'month-level aggregates; purchaser, place and '
                       'day were stripped before these rows were built'}


def export_price_references(manager, today=None):
    """Live PriceObservation rows → PriceReference rows (mealoptions),
    upserted so a re-export converges. Returns the counts + rows."""
    from composition.seed_upsert import upsert_seed_pairs
    norm = normalized_prices(manager, None, today)
    entries = norm['prices']
    undated = [e['observation'] for e in entries
               if not (e.get('observedDate') or '').strip()]
    rows = aggregate_references(entries, today)
    reports = upsert_seed_pairs(
        manager, [('PriceReference', PriceReference, rows)],
        tag='PriceReferenceExport')
    report = reports[0] if reports else {}
    return {
        'ok': True, 'schema': 'price-reference-export/1',
        'observationCount': len(entries),
        'referenceCount': len(rows),
        'inserted': len(report.get('inserted', [])),
        'updated': len(report.get('updated', [])),
        'unchanged': len(report.get('unchanged', [])),
        'skippedCustom': len(report.get('skipped_custom', [])),
        'errors': len(report.get('errors', [])),
        'skippedClass': bool(report.get('skipped', False)),
        'undatedObservations': len(undated),
        'refusedObservations': len(norm['refused']),
        'references': rows,
        'honesty': 'every reference is food × month × source type '
                   '(× chain only for chains) × coarse region; '
                   'purchaser, place and day stripped; undated '
                   'observations have no month and are left out',
    }


def advice(manager, food_name, local_preference_pct=10.0, month=None,
           today=None):
    """Local-first price advice: over the published PriceReference
    rows if any exist for the food, else over the live observations
    aggregated on the fly (and the honesty lines say which). `month`
    None = the latest month on file for the food."""
    published = [r for r in _rows(manager, 'PriceReference')
                 if getattr(r, 'food_name', '') == food_name]
    if published:
        result = price_advice(published, food_name, local_preference_pct,
                              month)
        result['basis'] = 'published PriceReference rows'
        result['honesty'].append(
            f'basis: {len(published)} published reference row(s) for '
            f'"{food_name}"')
        return result
    norm = normalized_prices(manager, food_name, today)
    rows = aggregate_references(norm['prices'], today)
    result = price_advice(rows, food_name, local_preference_pct, month)
    result['basis'] = 'live observations aggregated on the fly (unpublished)'
    result['honesty'].append(
        f'basis: NO published PriceReference rows for "{food_name}" — '
        f'this ranking aggregated {len(norm["prices"])} live '
        f'observation(s) on the fly; POST /api/mealplanning/prices/publish '
        f'to file the month\'s references')
    return result
