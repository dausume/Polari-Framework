"""
@module nutrition.shoptrip_analysis

N3 — the shopping-trip analyses (HOUSEHOLD_APP_PAGES.md §3.3):

  trip_checklist            the purchase event's lines (the generated
                            `purchase` CalendarEvent for the plan, or
                            the weekly purchase PROPOSAL when none is
                            generated yet) as a flat checklist in the
                            store's aisle order; estimated cost from
                            the best observed $/kg with its age;
                            `bought` when a put-away lot exists
  record_purchase_proposal  the "Bought it" form → ONE PriceObservation
                            proposal (never overwriting an existing
                            observation of the same name — said so)
                            + ONE PantryItem lot proposal (put-away:
                            grams via the weight priors, storage by
                            aisle prior, best-before via the staple's
                            shelf-life prior when one exists)

Nothing is written here — the no-code solution (GenerateEvent) or
the API writes; every number is derived from rows or a labelled
prior. Result dicts are flat (scalars + lists of flat records) so the
structured panel renders them without a JSON expander.
"""

import datetime as _dt
import json
from datetime import timedelta

from nutrition.market_analysis import best_price_per_kg, resolve_grams
from nutrition.shoptrip_basis import (
    AISLE_STORAGE_PRIOR, DEFAULT_AISLE_ORDER, UNKNOWN_AISLE,
)

#: a lot counts as "bought on this trip" when a shoptrip lot for the
#: food was acquired within this many days of the trip date (the form
#: defaults to today; the plan's shop day may differ by a few days).
BOUGHT_WINDOW_DAYS = 6
DEFAULT_PLAN = 'demo-alex-week'
DEFAULT_HOUSEHOLD = 'demo-household'
DEFAULT_LOCATION = 'demo-grocery'
LOT_PROVENANCE = 'shoptrip'


def _rows(manager, class_name):
    return list(((getattr(manager, 'objectTables', {}) or {}).get(class_name, {}) or {}).values())


def _named(manager, class_name, name):
    for r in _rows(manager, class_name):
        if getattr(r, 'name', '') == name:
            return r
    return None


def _today():
    return _dt.date.today()


def _date(value, default=None):
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    try:
        return _dt.datetime.fromisoformat(str(value)[:19]).date()
    except (TypeError, ValueError):
        return default


def _loads(value, default):
    if isinstance(value, (dict, list)):
        return value
    try:
        got = json.loads(value or '')
        return got if isinstance(got, type(default)) else default
    except (TypeError, ValueError):
        return default


def _quantity_text(grams):
    grams = float(grams or 0)
    if grams >= 1000:
        return f'{grams / 1000.0:.2f} kg'
    return f'{grams:.0f} g'


# ----------------------------------------------------------------
# aisle lookups
# ----------------------------------------------------------------

def aisle_order_for(manager, location, household=''):
    """(ordered labels, source) — the store's StoreAisleOrder row
    (household-specific wins over shared) or the convention prior."""
    shared, own = None, None
    for r in _rows(manager, 'StoreAisleOrder'):
        if getattr(r, 'location_name', '') != location:
            continue
        hh = getattr(r, 'household_name', '')
        if hh and hh == household:
            own = r
        elif not hh:
            shared = r
    row = own or shared
    if row is None:
        return list(DEFAULT_AISLE_ORDER), 'convention prior (no StoreAisleOrder row for this store)'
    order = [str(x) for x in _loads(getattr(row, 'aisle_order_json', '[]'), [])]
    if not order:
        return list(DEFAULT_AISLE_ORDER), f'convention prior (StoreAisleOrder {row.name} is empty)'
    return order, f'StoreAisleOrder {getattr(row, "name", "")}'


def food_aisles(manager):
    """{food: category} from FoodAisleCategory rows."""
    return {getattr(r, 'food_name', ''): (getattr(r, 'category', '') or UNKNOWN_AISLE)
            for r in _rows(manager, 'FoodAisleCategory') if getattr(r, 'food_name', '')}


# ----------------------------------------------------------------
# the purchase lines: generated event first, proposal second
# ----------------------------------------------------------------

def _purchase_event(manager, plan, event=None):
    if event:
        row = _named(manager, 'CalendarEvent', event)
        return row
    candidates = [e for e in _rows(manager, 'CalendarEvent')
                  if getattr(e, 'category', '') == 'purchase'
                  and getattr(e, 'linked_name', '') == plan
                  and getattr(e, 'status', 'planned') != 'cancelled']
    if not candidates:
        return None
    candidates.sort(key=lambda e: str(_loads(getattr(e, 'span', ''), {}).get('start', '')))
    return candidates[-1]


def _lines_for(manager, plan, household, event=None, today=None):
    """(lines, trip date, source text, error) — lines carry food /
    toBuyG / estCost / location / pricePerKg (the cal-4 shape)."""
    row = _purchase_event(manager, plan, event)
    if row is not None:
        payload = _loads(getattr(row, 'payload_json', ''), {})
        span = _loads(getattr(row, 'span', ''), {})
        trip = _date(span.get('start', ''), _today())
        return (list(payload.get('lines', []) or []), trip,
                f'CalendarEvent {getattr(row, "name", "")}', None)
    if event:
        return [], _today(), '', f"CalendarEvent '{event}' not found"
    from nutrition.purchase_analysis import weekly_purchase_proposal
    prop = weekly_purchase_proposal(manager, plan, household, None, today)
    if not prop.get('ok'):
        return [], _today(), '', prop.get('error', 'no purchase proposal')
    return (list(prop.get('lines', [])), _date(prop.get('purchaseDate'), _today()),
            'weekly purchase proposal (no purchase event generated yet)', None)


def _bought_lot(manager, household, food, trip, location, window_days):
    """The put-away lot that marks this line bought, or None."""
    for lot in _rows(manager, 'PantryItem'):
        if getattr(lot, 'household_name', '') != household \
                or getattr(lot, 'food_name', '') != food:
            continue
        prov = str(getattr(lot, 'provenance_id', '') or '')
        acquired = _date(getattr(lot, 'acquired_date', ''))
        if acquired is None:
            continue
        same_trip = (getattr(lot, 'source_location_name', '') == location
                     and acquired == trip)
        in_window = prov.startswith(LOT_PROVENANCE) \
            and abs((acquired - trip).days) <= int(window_days)
        if same_trip or in_window:
            return lot
    return None


def trip_checklist(manager, plan=DEFAULT_PLAN, location=None, event=None,
                   household='', today=None, bought_window_days=BOUGHT_WINDOW_DAYS):
    plan = plan or DEFAULT_PLAN
    plan_row = _named(manager, 'MealPlanDefinition', plan)
    household = household or (getattr(plan_row, 'household_name', '') if plan_row else '') \
        or DEFAULT_HOUSEHOLD
    lines, trip, source, error = _lines_for(manager, plan, household, event, today)
    if error:
        return {'ok': False, 'error': error, 'plan': plan, 'lines': []}
    # the store: stated, else the one most lines price best at, else the demo store
    if not location:
        counts = {}
        for l in lines:
            if l.get('location'):
                counts[l['location']] = counts.get(l['location'], 0) + 1
        location = max(counts, key=counts.get) if counts else DEFAULT_LOCATION
    store = _named(manager, 'SourceLocation', location)
    order, order_source = aisle_order_for(manager, location, household)
    rank = {label: i for i, label in enumerate(order)}
    aisles = food_aisles(manager)
    out, unknown, total, unpriced, bought_n = [], [], 0.0, 0, 0
    for l in lines:
        food = l.get('food', '')
        grams = float(l.get('toBuyG', 0) or 0)
        base = aisles.get(food, UNKNOWN_AISLE)
        idx = rank.get(base, len(order))
        aisle = base
        if base not in rank:
            if base != UNKNOWN_AISLE:
                aisle = f'{base} (not in this store\'s order)'
            unknown.append(food)
        best = best_price_per_kg(manager, food, today)
        per_kg = best['pricePerKg'] if best else l.get('pricePerKg')
        est = round(per_kg * grams / 1000.0, 2) if per_kg else None
        if est is None:
            unpriced += 1
        else:
            total += est
        lot = _bought_lot(manager, household, food, trip, location, bought_window_days)
        if lot is not None:
            bought_n += 1
        out.append({'aisle': aisle, 'aisleIndex': idx,
                    'food': food, 'quantity': _quantity_text(grams),
                    'grams': round(grams, 1), 'estCost': est,
                    'pricePerKg': per_kg,
                    'priceLocation': best['location'] if best else (l.get('location') or ''),
                    'priceAgeDays': best['ageDays'] if best else None,
                    'bought': lot is not None,
                    'lot': getattr(lot, 'name', '') if lot is not None else ''})
    out.sort(key=lambda r: (r['aisleIndex'], r['aisle'], r['food']))
    for i, r in enumerate(out, 1):
        r['step'] = i
    return {'ok': True, 'schema': 'shop-trip/1', 'plan': plan, 'household': household,
            'location': location,
            'store': getattr(store, 'display_name', '') or location,
            'tripDate': trip.isoformat(), 'source': source,
            'aisleOrder': ' → '.join(order), 'aisleOrderSource': order_source,
            'lines': out, 'lineCount': len(out), 'boughtCount': bought_n,
            'remainingCount': len(out) - bought_n, 'unpricedCount': unpriced,
            'estTotal': round(total, 2),
            'unknownAisleFoods': unknown,
            'boughtWindowDays': int(bought_window_days),
            'honesty': ('lines are the plan\'s shopping gap (the generated purchase event '
                        'when one exists, else the proposal); aisle order is the store\'s '
                        'StoreAisleOrder row or a US-grocery convention prior; foods without '
                        'a FoodAisleCategory row are NAMED and walk last; estimated cost = '
                        'best observed $/kg × grams (age shown); bought = a put-away lot '
                        f'from this store on the trip date or a shoptrip lot within '
                        f'{int(bought_window_days)} days')}


# ----------------------------------------------------------------
# "Bought it": one price observation + one put-away lot
# ----------------------------------------------------------------

def _shelf_days(manager, food, household):
    """The staple's shelf-life prior (BulkStaple.shelf_life_days) or 0."""
    for s in _rows(manager, 'BulkStaple'):
        if getattr(s, 'food_name', '') != food:
            continue
        if getattr(s, 'household_name', '') in ('', household):
            days = int(getattr(s, 'shelf_life_days', 0) or 0)
            if days > 0:
                return days, getattr(s, 'citation', '') or 'BulkStaple shelf_life_days'
    return 0, ''


def record_purchase_proposal(manager, food='', location=DEFAULT_LOCATION, price=0.0,
                             package_quantity=1.0, package_unit='lb', date=None,
                             household=DEFAULT_HOUSEHOLD, storage_state=''):
    food = str(food or '').strip()
    location = str(location or '').strip() or DEFAULT_LOCATION
    household = household or DEFAULT_HOUSEHOLD
    try:
        price = float(price or 0)
        qty = float(package_quantity or 0)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'price and package quantity must be numbers',
                'message': 'price and package quantity must be numbers',
                'priceProposals': [], 'lotProposals': [], 'proposals': []}
    unit = str(package_unit or 'lb').strip()
    when = _date(date) or _today()
    day = when.isoformat()
    problems = []
    if not food:
        problems.append('name the food (a FoodItem slug, e.g. chicken-breast-raw)')
    elif _named(manager, 'FoodItem', food) is None and _rows(manager, 'FoodItem'):
        problems.append(f"'{food}' is not a FoodItem on this node")
    if price <= 0:
        problems.append('price must be positive')
    if qty <= 0:
        problems.append('package quantity must be positive')
    if problems:
        return {'ok': False, 'error': '; '.join(problems), 'message': '; '.join(problems),
                'food': food, 'priceProposals': [], 'lotProposals': [], 'proposals': []}
    grams = resolve_grams(manager, food, qty, unit, household)
    grams_ok = bool(grams.get('ok'))
    g = float(grams.get('grams', 0) or 0) if grams_ok else 0.0
    per_kg = round(price / g * 1000.0, 2) if g > 0 else None

    po_name = f'{location}-{food}-{day}'
    existing_po = _named(manager, 'PriceObservation', po_name)
    price_proposals = []
    if existing_po is None:
        price_proposals.append({
            'name': po_name, 'food_name': food, 'location_name': location,
            'price': round(price, 2), 'currency': 'USD',
            'package_quantity': qty, 'package_unit': unit, 'observed_date': day,
            'is_prior': False, 'provenance_id': f'{LOT_PROVENANCE}:{location}:{day}',
            'notes': 'entered on the shopping-trip page'})
    price_status = ('kept the existing observation of the same name — never overwritten; '
                    'delete it on the market page to re-enter'
                    if existing_po is not None else 'new observation proposed')

    aisle = food_aisles(manager).get(food, UNKNOWN_AISLE)
    storage = storage_state or AISLE_STORAGE_PRIOR.get(aisle, 'pantry')
    shelf_days, shelf_cite = _shelf_days(manager, food, household)
    best_before = (when + timedelta(days=shelf_days)).isoformat() if shelf_days else ''
    lot_name = f'{household}-{food}-{day}-{location}'
    existing_lot = _named(manager, 'PantryItem', lot_name)
    lot_note = f'put away from the shopping trip at {location}'
    if best_before:
        lot_note += f'; best before ~{best_before} ({shelf_cite}, a prior)'
    if not grams_ok:
        lot_note += f'; grams unresolved: {grams.get("error", "")}'
    lot_proposals = []
    if existing_lot is None:
        lot_proposals.append({
            'name': lot_name, 'household_name': household, 'food_name': food,
            'quantity': qty, 'unit': unit, 'storage_state': storage,
            'acquired_date': day, 'source_location_name': location,
            'price_paid': round(price, 2), 'currency': 'USD', 'is_prior': False,
            'provenance_id': f'{LOT_PROVENANCE}:{location}:{day}', 'notes': lot_note})
    lot_status = ('a lot of the same name already exists — kept, not duplicated'
                  if existing_lot is not None else 'new lot proposed')
    # the plain words the "Bought it" form shows
    if existing_po is not None:
        message = (f'Price for {food} at {location} on {day} was already recorded '
                   f'(${float(getattr(existing_po, "price", 0) or 0):.2f}) — kept')
    else:
        message = f'Recorded ${price:.2f} for {food} at {location}'
    if existing_lot is not None:
        message += '; that lot was already put away — kept'
    elif grams_ok:
        message += f'; lot of {g:.0f} g put away in the {storage}'
    else:
        message += f'; lot of {qty:g} {unit} put away in the {storage} (grams unresolved)'
    return {'ok': True, 'schema': 'purchase-record/1', 'message': message,
            'food': food, 'location': location,
            'date': day, 'household': household, 'price': round(price, 2),
            'package': f'{qty:g} {unit}', 'grams': round(g, 1),
            'weightBasis': grams.get('basis', '') if grams_ok else 'unresolved',
            'pricePerKg': per_kg, 'aisle': aisle, 'storageState': storage,
            'storageSource': ('stated' if storage_state else f'aisle prior for {aisle}'),
            'bestBefore': best_before, 'bestBeforeSource': shelf_cite or 'no shelf-life prior for this food',
            'priceObservationName': po_name, 'priceObservationExists': existing_po is not None,
            'priceObservationStatus': price_status,
            'lotName': lot_name, 'lotExists': existing_lot is not None, 'lotStatus': lot_status,
            'priceProposals': price_proposals, 'lotProposals': lot_proposals,
            'proposals': price_proposals + lot_proposals,
            'honesty': ('two proposals, nothing written here: the observation is the price '
                        'as paid for the package (never overwriting one of the same name); '
                        'the lot is the put-away (grams via the weight priors, storage by '
                        'aisle prior, best-before from the staple shelf-life prior when one '
                        'exists) — the solution or the API writes them, deduped by name')}
