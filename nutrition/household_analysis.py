"""
@cross-cutting
@module nutrition.household_analysis
@tags @xc:bindings

nut-4 math — aggregate a HouseholdProfile's members into the household's
total nutrient demand over a period, with the per-member breakdown (so
a household sees WHO drives which need). Duck-typed manager; reuses
nut-3 nutrient_needs.

@consumers
  - nutrition.fulfillment_analysis, nutrition.household_api
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-4
"""

import json

from nutrition.person_analysis import nutrient_needs, PERIOD_DAYS


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


def _parse(text, fallback='[]'):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def household_needs(manager, household_name, period='week'):
    """Total household demand + per-member breakdown.

    Returns {'ok', 'household', 'period', 'memberCount',
    'totals': {nutrient: {amount, unit, plantAvailability}},
    'perMember': {person: {nutrient: amount}}, 'flaggedPriors',
    'calorieTargetPerDay'} or an honest refusal."""
    if period not in PERIOD_DAYS:
        return {'ok': False,
                'error': f"period must be one of {list(PERIOD_DAYS)}, "
                         f"got '{period}'"}
    household = _named(manager, 'HouseholdProfile', household_name)
    if household is None:
        return {'ok': False,
                'error': f"no HouseholdProfile named '{household_name}'"}
    members = _parse(getattr(household, 'member_names_json', '[]'))
    if not members:
        return {'ok': False,
                'error': f"household '{household_name}' has no members",
                'suggestion': {
                    'knob': 'HouseholdProfile.member_names_json',
                    'action': 'add PersonProfile names',
                    'evidence': 'demand is the sum of member needs'}}

    totals, per_member, priors = {}, {}, set()
    calorie_day = 0.0
    missing = []
    for member_name in members:
        person = _named(manager, 'PersonProfile', member_name)
        if person is None:
            missing.append(member_name)
            continue
        result = nutrient_needs(manager, person, period=period)
        if not result.get('ok'):
            return result
        calorie_day += result.get('calorieTargetPerDay', 0.0)
        priors.update(result.get('flaggedPriors', []))
        member_totals = {}
        for nutrient, spec in result['needs'].items():
            amount = spec['amount']
            member_totals[nutrient] = amount
            entry = totals.setdefault(
                nutrient, {'amount': 0.0, 'unit': spec['unit'],
                           'plantAvailability': spec['plantAvailability']})
            entry['amount'] = round(entry['amount'] + amount, 3)
        per_member[member_name] = member_totals
    if missing:
        return {'ok': False,
                'error': f"unknown members: {missing}",
                'suggestion': {
                    'knob': 'HouseholdProfile.member_names_json',
                    'action': 'create the missing PersonProfiles or '
                              'remove them from the household',
                    'evidence': 'every member must resolve to a '
                                'PersonProfile'}}
    return {'ok': True, 'household': household_name, 'period': period,
            'memberCount': len(members),
            'calorieTargetPerDay': round(calorie_day, 1),
            'totals': totals, 'perMember': per_member,
            'flaggedPriors': sorted(priors),
            'note': 'household demand = sum of member per-nutrient needs '
                    'over the period.'}
