"""
@module nutrition.purchase_analysis

cal-4 — the PURCHASE + COORDINATION analyses the no-code event
solutions call (through AnalysisCall) to propose events:

  weekly_purchase_proposal  the plan's priced shopping gap for the
                            week, MINUS what bulk staples in stock
                            already cover → one `purchase` event
  bulk_purchase_proposal    the staples on one cadence (1/3/6/12
                            months): demand over the period vs stock,
                            bulk $/kg vs best retail $/kg → savings,
                            shelf life vs cadence (refused by name
                            when the food would decay first) → one
                            `bulk-purchase` event
  coordinate_week           the ORDER Dustin asked for: purchase →
                            cooking pre-prep (batch sessions from the
                            prep scheduler, after the purchase that
                            supplies them) → meals → pre-meal prep
                            (short, right before each meal) — every
                            proposal an event dict GenerateEvent can
                            write, every rule NAMED

Every time-of-day here is a labeled PRIOR (a household overrides it
on its rows / the definition). Nothing is written by these functions
— they PROPOSE; the solution generates; the person can cancel.
"""

import math
from datetime import date, datetime, timedelta

from nutrition.market_analysis import best_price_per_kg, resolve_grams
from nutrition.pantry_analysis import (
    pantry_stock, plan_ingredient_demand, shopping_list,
)

#: slot-time PRIORS (D3) — shared with the meal EventDefinition seed.
SLOT_TIMES = {'breakfast': '08:00', 'brunch': '10:30', 'lunch': '12:30',
              'linner': '15:30', 'dinner': '18:30', 'snack': '15:00'}
PURCHASE_TIME = '10:00'      # weekly shop start prior
PURCHASE_MINUTES = 60
PREPREP_TIME = '15:00'       # batch-cooking session start prior
MEAL_PREP_MINUTES = 15       # the short pre-meal step prior
EXACT_UNITS = {'g': 1.0, 'kg': 1000.0, 'lb': 453.592, 'oz': 28.3495}
WEEKS_PER_MONTH = 52.0 / 12.0


def _rows(manager, class_name):
    return list(((getattr(manager, 'objectTables', {}) or {}).get(class_name, {}) or {}).values())


def _named(manager, class_name, name):
    for r in _rows(manager, class_name):
        if getattr(r, 'name', '') == name:
            return r
    return None


def _grams(manager, food, quantity, unit):
    unit = (unit or 'g').lower()
    if unit in EXACT_UNITS:
        return float(quantity) * EXACT_UNITS[unit]
    if unit in ('l', 'liter', 'litre'):
        return float(quantity) * 920.0  # oils/liquids prior ~0.92 kg/L; labeled
    try:
        got = resolve_grams(manager, food, quantity, unit)
        if isinstance(got, dict):
            return float(got.get('grams') or 0)
        return float(got or 0)
    except Exception:
        return 0.0


def _date(value, default=None):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:19]).date()
    except (TypeError, ValueError):
        return default


def _monday(d):
    return d - timedelta(days=d.weekday())


def _iso(d, hhmm=None):
    return f'{d.isoformat()}T{hhmm}' if hhmm else d.isoformat()


def _plus(hhmm, minutes):
    h, m = [int(x) for x in hhmm.split(':')[:2]]
    total = h * 60 + m + int(minutes)
    return f'{(total // 60) % 24:02d}:{total % 60:02d}'


def _minus(hhmm, minutes):
    return _plus(hhmm, -int(minutes))


# ----------------------------------------------------------------
# weekly purchase
# ----------------------------------------------------------------

def weekly_purchase_proposal(manager, plan, household='', purchase_date=None,
                             today=None):
    plan_row = plan if not isinstance(plan, str) else _named(manager, 'MealPlanDefinition', plan)
    if plan_row is None:
        return {'ok': False, 'error': f"MealPlanDefinition '{plan}' not found",
                'proposals': []}
    household = household or getattr(plan_row, 'household_name', '') or 'demo-household'
    pdate = _date(purchase_date) or _date(getattr(plan_row, 'start_date', '')) or date.today()
    shop = shopping_list(manager, plan_row, household, today)
    if not shop.get('ok'):
        return {'ok': False, 'error': shop.get('error', 'no shopping list'), 'proposals': []}
    staples = {getattr(s, 'food_name', ''): s for s in _rows(manager, 'BulkStaple')
               if getattr(s, 'household_name', '') in ('', household)}
    stock = pantry_stock(manager, household)
    stock_g = stock.get('stockG', {}) if isinstance(stock, dict) else {}
    lines, covered, unpriced, total = [], [], list(shop.get('unpricedFoods', [])), 0.0
    for line in shop.get('lines', []):
        food = line['food']
        if food in staples and stock_g.get(food, 0) > 0:
            covered.append({'food': food, 'haveG': round(stock_g.get(food, 0), 1),
                            'note': 'a bulk staple already in stock covers this week'})
            continue
        best = None
        for opt in line.get('options') or []:
            if best is None or opt['estCost'] < best['estCost']:
                best = opt
        est = round(best['estCost'], 2) if best else None
        if est is not None:
            total += est
        lines.append({'food': food, 'toBuyG': round(line['toBuyG'], 1),
                      'estCost': est, 'location': best['location'] if best else '',
                      'pricePerKg': best['pricePerKg'] if best else None})
    priced = [l for l in lines if l['estCost'] is not None]
    cost_text = (f'~${total:.2f}' if priced else 'unpriced') + \
        (' + unpriced' if priced and unpriced else '')
    title = (f"Groceries — {plan_row.name} ({len(lines)} item"
             f"{'s' if len(lines) != 1 else ''}, {cost_text})")
    proposal = {
        'name': f'purchase-{plan_row.name}-{pdate.isoformat()}',
        'title': title, 'category': 'purchase',
        'household_name': household,
        'person_name': getattr(plan_row, 'person_name', ''),
        'span': {'start': _iso(pdate, PURCHASE_TIME),
                 'end': _iso(pdate, _plus(PURCHASE_TIME, PURCHASE_MINUTES))},
        'all_day': False, 'color': '#1565c0',
        'linked_class': 'MealPlanDefinition', 'linked_name': plan_row.name,
        'payload_json': {'lines': lines, 'estTotal': round(total, 2),
                         'unpricedFoods': unpriced, 'bulkCovered': covered,
                         'purchaseTimePrior': PURCHASE_TIME},
    }
    return {'ok': True, 'schema': 'purchase-proposal/1', 'plan': plan_row.name,
            'household': household, 'purchaseDate': pdate.isoformat(),
            'lines': lines, 'estTotal': round(total, 2), 'unpricedFoods': unpriced,
            'bulkCovered': covered, 'proposals': [proposal],
            'honesty': ('the shopping gap is plan demand minus pantry stock; a '
                        'bulk staple in stock removes its line; costs come from '
                        'observed prices only (unpriced foods NAMED); the shop '
                        f'time {PURCHASE_TIME} is a prior')}


# ----------------------------------------------------------------
# bulk purchase on a cadence
# ----------------------------------------------------------------

def _weekly_demand(manager, household, food):
    """Grams/week of `food` across the household's plans (each plan's
    demand scaled to a week), or 0 when no plan uses it."""
    total_weeks, grams = 0.0, 0.0
    for plan in _rows(manager, 'MealPlanDefinition'):
        if getattr(plan, 'household_name', '') != household:
            continue
        demand = plan_ingredient_demand(manager, plan)
        if not demand.get('ok'):
            continue
        days = float(getattr(plan, 'days', 0) or 0) or 7.0
        grams += demand.get('demandG', {}).get(food, 0.0) * (7.0 / days)
        total_weeks += 1
    return grams / total_weeks if total_weeks else 0.0


def bulk_purchase_proposal(manager, household='demo-household', cadence_months=3,
                           purchase_date=None, today=None):
    cadence = int(cadence_months or 3)
    pdate = _date(purchase_date) or date.today()
    stock = pantry_stock(manager, household)
    stock_g = stock.get('stockG', {}) if isinstance(stock, dict) else {}
    weeks = cadence * WEEKS_PER_MONTH
    cadence_days = cadence * 30.4
    staples, refused, total, savings, unpriced_retail = [], [], 0.0, 0.0, []
    for s in _rows(manager, 'BulkStaple'):
        if getattr(s, 'household_name', '') not in ('', household):
            continue
        if int(getattr(s, 'cadence_months', 0) or 0) != cadence:
            continue
        food = getattr(s, 'food_name', '')
        shelf = float(getattr(s, 'shelf_life_days', 0) or 0)
        if shelf and cadence_days > shelf:
            refused.append({'food': food, 'why': (f'{cadence}-month cadence ({cadence_days:.0f} d) '
                                                  f'outlives the shelf life ({shelf:.0f} d, '
                                                  f'{getattr(s, "citation", "")})'),
                            'suggestion': f'set cadence_months to {max(1, int(shelf // 30.4))} or less'})
            continue
        weekly = float(getattr(s, 'weekly_demand_g', 0) or 0) or _weekly_demand(manager, household, food)
        need = weekly * weeks
        have = float(stock_g.get(food, 0) or 0)
        to_buy = max(0.0, need - have)
        pkg_g = _grams(manager, food, getattr(s, 'bulk_package_quantity', 0),
                       getattr(s, 'bulk_package_unit', 'g'))
        packages = int(math.ceil(to_buy / pkg_g)) if pkg_g > 0 and to_buy > 0 else 0
        bulk_per_kg = (float(getattr(s, 'bulk_price', 0) or 0) / (pkg_g / 1000.0)) if pkg_g > 0 else None
        retail = best_price_per_kg(manager, food, today)
        retail_per_kg = retail['pricePerKg'] if retail else None
        cost = round(packages * float(getattr(s, 'bulk_price', 0) or 0), 2)
        save = None
        if retail_per_kg is not None and bulk_per_kg is not None and packages:
            save = round((retail_per_kg - bulk_per_kg) * (packages * pkg_g / 1000.0), 2)
            savings += save
        elif retail_per_kg is None:
            unpriced_retail.append(food)
        total += cost
        staples.append({'food': food, 'cadenceMonths': cadence, 'weeklyDemandG': round(weekly, 1),
                        'needG': round(need, 1), 'haveG': round(have, 1), 'toBuyG': round(to_buy, 1),
                        'packages': packages, 'packageG': round(pkg_g, 1),
                        'bulkPricePerKg': round(bulk_per_kg, 2) if bulk_per_kg else None,
                        'retailPricePerKg': retail_per_kg, 'estCost': cost,
                        'estSavings': save, 'shelfLifeDays': shelf,
                        'location': getattr(s, 'bulk_location_name', ''),
                        'citation': getattr(s, 'citation', ''),
                        'confidence': getattr(s, 'confidence', '')})
    label = {1: 'monthly', 3: '3-month', 6: '6-month', 12: 'yearly'}.get(cadence, f'{cadence}-month')
    foods = [x['food'] for x in staples if x['packages']]
    title = (f"Bulk buy ({label}): {', '.join(foods) if foods else 'nothing needed'}"
             f" ~${total:.2f}" + (f", saves ~${savings:.2f}" if savings else ''))
    proposal = {
        'name': f'bulk-{cadence}m-{household}-{pdate.isoformat()}',
        'title': title, 'category': 'bulk-purchase', 'household_name': household,
        'span': {'start': pdate.isoformat()}, 'all_day': True, 'color': '#6a1b9a',
        'linked_class': 'BulkStaple', 'linked_name': staples[0]['food'] if staples else '',
        'payload_json': {'cadenceMonths': cadence, 'staples': staples, 'refused': refused,
                         'estTotal': round(total, 2), 'estSavings': round(savings, 2),
                         'unpricedRetail': unpriced_retail},
    }
    return {'ok': True, 'schema': 'bulk-proposal/1', 'household': household,
            'cadenceMonths': cadence, 'purchaseDate': pdate.isoformat(),
            'staples': staples, 'refused': refused, 'estTotal': round(total, 2),
            'estSavings': round(savings, 2), 'unpricedRetail': unpriced_retail,
            'proposals': [proposal] if staples else [],
            'honesty': ('demand = the household\'s plan demand scaled to the cadence '
                        '(or the row\'s weekly_demand_g override); savings = (best '
                        'retail $/kg − bulk $/kg) × kg bought, only where a retail '
                        'observation exists; shelf lives are transcribed FoodKeeper '
                        'priors — a cadence longer than the shelf life is REFUSED')}


# ----------------------------------------------------------------
# the week's coordination: purchase → pre-prep → meals → meal-prep
# ----------------------------------------------------------------

def coordinate_week(manager, plan=None, household='', week_start=None, today=None,
                    purchase_time=PURCHASE_TIME, preprep_time=PREPREP_TIME,
                    meal_prep_minutes=MEAL_PREP_MINUTES, plan_from_entry=None):
    from nutrition.workflow_analysis import derive_week_plan
    # `plan` may arrive as the changed object's name (a plan) or, when
    # a MealEntry changed, as that entry's plan_name (plan_from_entry).
    if isinstance(plan, str) and _named(manager, 'MealPlanDefinition', plan) is None \
            and plan_from_entry:
        plan = plan_from_entry
    if plan is None and plan_from_entry:
        plan = plan_from_entry
    plan_row = plan if not isinstance(plan, str) else _named(manager, 'MealPlanDefinition', plan)
    if plan_row is None:
        return {'ok': False, 'error': f"MealPlanDefinition '{plan}' not found", 'proposals': []}
    household = household or getattr(plan_row, 'household_name', '') or 'demo-household'
    start = _date(week_start) or _date(getattr(plan_row, 'start_date', '')) or date.today()
    rules = [
        'purchase on the Saturday before the plan week (the weekly purchase '
        'day prior), before any pre-prep it supplies',
        'pre-prep (batch cooking) the afternoon before the first meal it serves, '
        'never before the shop',
        'meals at their slot time (the entry\'s own time wins over the slot prior)',
        'pre-meal prep is SHORT: the meal-prep prior right before each meal',
    ]
    proposals = []
    # 1. purchase — the Saturday before the plan week (the weekly
    # purchase trigger's day, so the two proposals share a name and
    # dedupe to ONE event); a plan starting on a Sunday shops the
    # Saturday before it.
    purchase_day = start - timedelta(days=1)
    while purchase_day.weekday() != 5:
        purchase_day -= timedelta(days=1)
    purchase = weekly_purchase_proposal(manager, plan_row, household, purchase_day, today)
    if purchase.get('ok'):
        proposals.extend(purchase['proposals'])
    purchase_end = _plus(purchase_time, PURCHASE_MINUTES)
    # 2. pre-prep sessions from the prep scheduler
    week = derive_week_plan(manager, plan_row, household)
    sessions = week.get('sessions', []) if week.get('ok') else []
    for s in sessions:
        day = int(s.get('day', 1) or 1)
        serves = sorted({d for it in s.get('items', []) for d in (it.get('forDays') or [day])}) or [day]
        first = min(serves)
        prep_day = start + timedelta(days=first - 2)  # the afternoon before
        if prep_day < purchase_day:
            prep_day = purchase_day  # never before the shop that supplies it
        at = preprep_time
        if prep_day == purchase_day and at < purchase_end:
            at = purchase_end
        minutes = float(s.get('activeMin', 0) or 0) or 30.0
        foods = sorted({it.get('food', '') for it in s.get('items', [])})
        proposals.append({
            'name': f'preprep-{plan_row.name}-d{day}',
            'title': f"Pre-prep for days {','.join(str(d) for d in serves)}: {', '.join(foods)}",
            'category': 'pre-prep', 'household_name': household,
            'person_name': getattr(plan_row, 'person_name', ''),
            'span': {'start': _iso(prep_day, at), 'end': _iso(prep_day, _plus(at, minutes))},
            'all_day': False, 'color': '#ef6c00',
            'linked_class': 'MealPlanDefinition', 'linked_name': plan_row.name,
            'payload_json': {'sessionDay': day, 'servesDays': serves,
                             'items': s.get('items', []), 'activeMin': minutes,
                             'prePrepTimePrior': preprep_time},
        })
    # 3. meals + 4. short pre-meal prep (mlg-2: sized per person from
    # the pre-prep actually planned, bounded by the safety floor; an
    # EATING block is added so cooking and eating read apart)
    try:
        from nutrition import logistics_analysis as lg
    except ImportError:
        lg = None
    members = [m.person_name for m in _rows(manager, 'HouseholdMember')
               if getattr(m, 'household_name', '') == household] \
        or [getattr(plan_row, 'person_name', '')]
    for e in _rows(manager, 'MealEntry'):
        if getattr(e, 'plan_name', '') != plan_row.name:
            continue
        day = int(getattr(e, 'day_index', 1) or 1)
        mdate = start + timedelta(days=day - 1)
        slot = getattr(e, 'slot', '')
        at = getattr(e, 'time_hhmm', '') or SLOT_TIMES.get(slot, '12:00')
        prep_min, prep_fidelity, profiles = float(meal_prep_minutes), 'prior', {}
        eating_min = 30.0
        if lg is not None:
            for p in members:
                prof = lg.prep_time_profile(manager, e, p, week if week.get('ok') else None)
                if prof.get('ok'):
                    profiles[p] = {'finalPrepMin': prof['finalPrepMin'],
                                   'safetyAddedMin': prof['safetyAddedMin'],
                                   'fidelity': prof['fidelity']['finalPrep']}
            if profiles:
                # the block is sized for the FASTEST safe member; the
                # allocation (assign_work) decides who actually cooks
                fastest = min(profiles, key=lambda p: profiles[p]['finalPrepMin'])
                prep_min = profiles[fastest]['finalPrepMin']
                prep_fidelity = profiles[fastest]['fidelity']
            eating_min = max(lg._eating_minutes(manager, p, slot) for p in members)
        proposals.append({
            'name': f'mealprep-{e.name}',
            'title': f"Prep {slot}: {getattr(e, 'template_name', '')} (~{round(prep_min)} min)",
            'category': 'meal-prep', 'household_name': household,
            'person_name': getattr(plan_row, 'person_name', ''),
            'span': {'start': _iso(mdate, _minus(at, prep_min)), 'end': _iso(mdate, at)},
            'all_day': False, 'color': '#2e7d32',
            'linked_class': 'MealEntry', 'linked_name': e.name,
            'payload_json': {'mealTime': at, 'finalPrepMin': prep_min,
                             'fidelity': prep_fidelity, 'perPerson': profiles,
                             'slot': slot, 'day': day, 'workload_type': 'meal-prep'},
        })
        proposals.append({
            'name': f'eat-{e.name}',
            'title': f"Eat {slot}: {getattr(e, 'template_name', '')} (~{round(eating_min)} min)",
            'category': 'eating', 'household_name': household,
            'person_name': '',
            'span': {'start': _iso(mdate, at), 'end': _iso(mdate, _plus(at, eating_min))},
            'all_day': False, 'color': '#9e9d24',
            'linked_class': 'MealEntry', 'linked_name': e.name,
            'payload_json': {'eatingMin': eating_min, 'slot': slot, 'day': day,
                             'fidelity': 'estimate'},
        })
    # mlg-1/3/2b/4: timing verdicts, packing, dishes, the allocation.
    logistics = {}
    if lg is not None:
        try:
            timing = lg.meal_timing_check(manager, plan_row, start)
            logistics['timing'] = {'flaggedCount': timing.get('flaggedCount', 0),
                                   'flags': [{'entry': v['entry'], 'person': v['person'], 'flags': v['flags'],
                                              'suggestions': v['suggestions']}
                                             for v in timing.get('verdicts', []) if v['flags']],
                                   'posture': timing.get('posture', '')}
            port = lg.portability_plan(manager, plan_row, start)
            proposals.extend(port.get('proposals', []))
            logistics['portability'] = {'needs': port.get('needs', []), 'missingTools': port.get('missingTools', [])}
            dishes = lg.dish_plan(manager, plan_row, start, {'proposals': proposals})
            proposals.extend(dishes.get('proposals', []))
            logistics['dishes'] = {'totalMin': dishes.get('totalMin', 0), 'notes': dishes.get('notes', [])}
            work = lg.assign_work(manager, proposals, household)
            if work.get('ok'):
                by_event = {}
                for a in work['allocation']:
                    by_event.setdefault(a['event'], set()).update(a['assignees'])
                for p in proposals:
                    who = sorted(by_event.get(p['name'], []))
                    if who:
                        p['payload_json']['assignees'] = who
                        if len(who) == 1 and p['category'] != 'eating':
                            p['person_name'] = who[0]
                        p['title'] = f"{p['title']} · {', '.join(who)}"
                logistics['work'] = {'readout': work['readout'], 'unassigned': work['unassigned'],
                                     'totalPersonMinutes': work['totalPersonMinutes'],
                                     'pureMinimumPersonMinutes': work['pureMinimumPersonMinutes'],
                                     'minutesGivenUpForShares': work['minutesGivenUpForShares'],
                                     'purchaseVsDelivery': work['purchaseVsDelivery']}
            else:
                logistics['work'] = {'error': work.get('error')}
        except Exception as exc:  # the coordination must still answer
            logistics['error'] = f'{type(exc).__name__}: {exc}'
    proposals.sort(key=lambda p: p['span']['start'])
    timeline = [{'start': p['span']['start'], 'end': p['span'].get('end'),
                 'category': p['category'], 'title': p['title']} for p in proposals]
    return {'ok': True, 'schema': 'week-coordination/2', 'plan': plan_row.name,
            'household': household, 'weekStart': start.isoformat(),
            'rules': rules + [
                'meal-prep is sized per person from the planned pre-prep, never below the safety floor',
                'an eating block follows every meal (the person\'s eating-time prior)',
                'dinner ends the person\'s own spacing before their bedtime (default 2 h) — flagged, never blocked',
                'packed meals get a pack event before leaving and cold packs frozen the night before',
                'dishes go into unattended windows first, else after eating; cleanup counts as work',
                'every step is allocated to the fastest free, safe person within the household\'s shares',
            ],
            'proposals': proposals, 'timeline': timeline,
            'logistics': logistics,
            'counts': {c: sum(1 for p in proposals if p['category'] == c)
                       for c in ('purchase', 'pre-prep', 'meal-prep', 'eating', 'packing', 'cleanup')},
            'honesty': ('meals themselves are the MealEntry rows (the meal-plan-entry '
                        'layer); this proposes the purchase, the batch pre-prep '
                        'sessions the scheduler already minimizes, and a short '
                        'pre-meal prep block per meal — all times are labeled priors')}
