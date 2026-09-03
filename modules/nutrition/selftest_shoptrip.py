"""
@module nutrition.selftest_shoptrip

N3 selftest (check() style, no server): a fake manager with a
purchase event of four lines across three aisle categories (+ one
food with no aisle) and one store order → the checklist walks the
store's order, the unknown aisle last and named, estimated cost from
seeded PriceObservations with age, `bought` only where a put-away lot
exists; the "Bought it" proposal → two rows (dedupe on re-submit);
the seeded solution through the REAL engine writes them; the page
seed is well-formed (rows sum to 12, ids unique, embeds/paths/forms
resolve to this feature's tables/routes/solutions).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_shoptrip
"""

import inspect
import json
import sys
from types import SimpleNamespace

from nutrition.fdc_seed import SEED_FDC_FOOD_ITEMS
from nutrition.market_basis import (
    SEED_PRICE_OBSERVATIONS, SEED_SOURCE_LOCATIONS, SEED_UNIT_WEIGHTS,
)
from nutrition.pantry_basis import PantryItem
from nutrition.purchase_basis import SEED_BULK_STAPLES
from nutrition.shoptrip_analysis import (
    record_purchase_proposal, trip_checklist,
)
from nutrition.shoptrip_api import ShoptripAPI
from nutrition.shoptrip_basis import (
    SEED_FOOD_AISLE_CATEGORIES, SEED_STORE_AISLE_ORDERS, SHOPTRIP_CLASSES,
    SHOPTRIP_SEED_PAIRS, FoodAisleCategory, StoreAisleOrder,
)
from nutrition.shoptrip_seed import (
    SEED_SHOPTRIP_ANALYSES, SEED_SHOPTRIP_PAGE_DISPLAYS, SEED_SHOPTRIP_SOLUTIONS,
    SEED_SHOPTRIP_TABLES, SEED_SHOPTRIP_TRIGGERS,
)
from polariApiServer import mealplan_pages_seed as mp
from polariNoCode import graph_builder as gb
from polariNoCode.graph_compilers import final_context_of

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []
TRIP_DAY = '2026-09-05'
STORE = 'test-store'


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}' + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list, prefix='r'):
    return {f'{prefix}{i}': SimpleNamespace(id=f'{prefix}{i}', **r) for i, r in enumerate(seed_list)}


class _DB:
    def saveInstanceInDB(self, inst):
        return True


def _manager():
    lines = [
        {'food': 'rice-white-raw', 'toBuyG': 1500.0, 'estCost': 4.3, 'location': 'demo-grocery', 'pricePerKg': 5.73},
        {'food': 'spinach-raw', 'toBuyG': 340.0, 'estCost': 2.99, 'location': 'demo-grocery', 'pricePerKg': 8.79},
        {'food': 'chicken-breast-raw', 'toBuyG': 900.0, 'estCost': 16.87, 'location': 'demo-farmers-market', 'pricePerKg': 18.74},
        {'food': 'tortilla-flour', 'toBuyG': 500.0, 'estCost': None, 'location': '', 'pricePerKg': None},
    ]
    event = {'name': 'purchase-demo-alex-week-2026-09-05', 'title': 'Groceries', 'category': 'purchase',
             'household_name': 'demo-household', 'person_name': 'demo-alex', 'status': 'planned',
             'span': json.dumps({'start': f'{TRIP_DAY}T10:00', 'end': f'{TRIP_DAY}T11:00'}),
             'linked_class': 'MealPlanDefinition', 'linked_name': 'demo-alex-week',
             'payload_json': json.dumps({'lines': lines, 'estTotal': 24.16}),
             'generated_by': 'weekly-purchase'}
    store_order = {'name': 'test-store-order', 'location_name': STORE, 'household_name': '',
                   'aisle_order_json': json.dumps(['meat', 'produce', 'dry-goods']),
                   'is_prior': False, 'provenance_id': 'selftest', 'notes': ''}
    spinach_lot = {'name': f'demo-household-spinach-raw-{TRIP_DAY}-{STORE}', 'household_name': 'demo-household',
                   'food_name': 'spinach-raw', 'quantity': 1.0, 'unit': 'bunch', 'storage_state': 'fridge',
                   'acquired_date': TRIP_DAY, 'source_location_name': STORE, 'price_paid': 2.49,
                   'currency': 'USD', 'is_prior': False, 'provenance_id': f'shoptrip:{STORE}:{TRIP_DAY}',
                   'notes': 'already put away'}
    tables = {
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS, 'f'),
        'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS, 'u'),
        'SourceLocation': _rows(SEED_SOURCE_LOCATIONS + [
            {'name': STORE, 'display_name': 'Test Store', 'kind': 'grocery', 'latitude': 0.0,
             'longitude': 0.0, 'region_label': '', 'address': '', 'household_name': '',
             'is_prior': False, 'provenance_id': '', 'notes': ''}], 'l'),
        'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS, 'p'),
        'PantryItem': _rows([spinach_lot], 'pi'),
        'BulkStaple': _rows(SEED_BULK_STAPLES, 'b'),
        'StoreAisleOrder': _rows(SEED_STORE_AISLE_ORDERS + [store_order], 'o'),
        'FoodAisleCategory': _rows(SEED_FOOD_AISLE_CATEGORIES, 'a'),
        'CalendarEvent': _rows([event], 'e'),
        'MealPlanDefinition': _rows([{'name': 'demo-alex-week', 'household_name': 'demo-household',
                                      'person_name': 'demo-alex', 'start_date': '2026-09-01', 'days': 3}], 'm'),
        'AnalysisDefinition': _rows(SEED_SHOPTRIP_ANALYSES, 'ad'),
        'SolutionDefinition': _rows(SEED_SHOPTRIP_SOLUTIONS, 'sd'),
        'EventTrigger': {}, 'TriggerFiring': {},
    }
    return SimpleNamespace(objectTables=tables, db=_DB())


def _fields(cls):
    return set(inspect.signature(cls.__init__).parameters) - {'self'}


def main():
    mgr = _manager()
    print('N3 shopping trip')

    # --- the basis -------------------------------------------------------
    cats = {r['category'] for r in SEED_FOOD_AISLE_CATEGORIES}
    foods = {r['food_name'] for r in SEED_FOOD_AISLE_CATEGORIES}
    check('FoodAisleCategory seeds cover every fsp-1 FoodItem (49) + the 2 grown foods, all labelled priors',
          {f['name'] for f in SEED_FDC_FOOD_ITEMS} <= foods and len(SEED_FOOD_AISLE_CATEGORIES) == 51
          and all(r['is_prior'] for r in SEED_FOOD_AISLE_CATEGORIES)
          and cats == {'produce', 'dairy', 'meat', 'seafood', 'dry-goods'},
          f'{len(SEED_FOOD_AISLE_CATEGORIES)} rows, cats={sorted(cats)}')
    demo = SEED_STORE_AISLE_ORDERS[0]
    check('demo-grocery store order is a labelled convention prior with an ordered aisle list',
          demo['location_name'] == 'demo-grocery' and demo['is_prior']
          and json.loads(demo['aisle_order_json'])[:3] == ['produce', 'bakery', 'dairy'])
    check('SHOPTRIP_CLASSES / SHOPTRIP_SEED_PAIRS export the two classes with their seeds',
          SHOPTRIP_CLASSES == [StoreAisleOrder, FoodAisleCategory]
          and [p[0] for p in SHOPTRIP_SEED_PAIRS] == ['StoreAisleOrder', 'FoodAisleCategory'])

    # --- the checklist ---------------------------------------------------
    cl = trip_checklist(mgr, 'demo-alex-week', STORE)
    order = [l['food'] for l in cl['lines']]
    check('checklist reads the generated purchase event (4 lines) in the STORE\'s order: '
          'meat → produce → dry-goods, the unknown-aisle food last and NAMED',
          cl['ok'] and cl['source'].startswith('CalendarEvent') and cl['tripDate'] == TRIP_DAY
          and order == ['chicken-breast-raw', 'spinach-raw', 'rice-white-raw', 'tortilla-flour']
          and cl['lines'][-1]['aisle'] == 'unknown' and cl['unknownAisleFoods'] == ['tortilla-flour']
          and cl['aisleOrderSource'] == 'StoreAisleOrder test-store-order',
          f'{order} src={cl.get("source")} {cl.get("aisleOrderSource")}')
    chicken = cl['lines'][0]
    # seeded: demo-grocery 11.98 / 2 lb = 13.21 $/kg beats the market's 8.50 / lb = 18.74
    check('estimated cost = BEST observed $/kg × grams (the grocery beats the market for chicken), '
          'with the observation\'s age and location — not the event\'s stale line price',
          chicken['pricePerKg'] == 13.21 and chicken['estCost'] == round(13.21 * 0.9, 2)
          and chicken['priceLocation'] == 'demo-grocery' and isinstance(chicken['priceAgeDays'], int),
          str(chicken))
    check('an unpriced food has estCost None and is counted; totals are flat scalars',
          cl['lines'][-1]['estCost'] is None and cl['unpricedCount'] == 1 and cl['lineCount'] == 4
          and cl['estTotal'] == round(sum(l['estCost'] for l in cl['lines'] if l['estCost']), 2)
          and all(not isinstance(v, dict) for v in cl.values()))
    check('bought is True only where a put-away lot exists (spinach), with the lot named',
          [l['bought'] for l in cl['lines']] == [False, True, False, False]
          and cl['lines'][1]['lot'].startswith('demo-household-spinach-raw')
          and cl['boughtCount'] == 1 and cl['remainingCount'] == 3)
    check('quantity text reads in kg above 1000 g and in g below',
          cl['lines'][2]['quantity'] == '1.50 kg' and cl['lines'][1]['quantity'] == '340 g')
    cl2 = trip_checklist(mgr, 'demo-alex-week', 'demo-grocery')
    check('the demo store (convention order) walks produce before meat before dry-goods',
          [l['food'] for l in cl2['lines']][:3] == ['spinach-raw', 'chicken-breast-raw', 'rice-white-raw']
          and cl2['aisleOrderSource'] == 'StoreAisleOrder demo-grocery-order')
    cl3 = trip_checklist(mgr, 'demo-alex-week', 'nowhere-store')
    check('a store without an order row falls back to the convention prior, said so',
          cl3['ok'] and 'convention prior' in cl3['aisleOrderSource'])
    bad = trip_checklist(mgr, 'demo-alex-week', STORE, event='no-such-event')
    check('a named event that does not exist is refused by name',
          not bad['ok'] and 'no-such-event' in bad['error'])

    # --- the "Bought it" proposal ---------------------------------------
    rp = record_purchase_proposal(mgr, 'chicken-breast-raw', STORE, 9.98, 2, 'lb', TRIP_DAY)
    check('proposal → one PriceObservation (name <location>-<food>-<date>) + one PantryItem lot',
          rp['ok'] and len(rp['priceProposals']) == 1 and len(rp['lotProposals']) == 1
          and rp['priceObservationName'] == f'{STORE}-chicken-breast-raw-{TRIP_DAY}'
          and rp['priceProposals'][0]['name'] == rp['priceObservationName']
          and rp['lotProposals'][0]['name'] == rp['lotName'], str(rp.get('error')))
    lot = rp['lotProposals'][0]
    check('the lot is the put-away: 2 lb → 907.2 g resolved, fridge by the meat aisle prior, '
          'price paid, source store, shoptrip provenance',
          rp['grams'] == 907.2 and rp['pricePerKg'] == 11.0 and lot['storage_state'] == 'fridge'
          and lot['price_paid'] == 9.98 and lot['source_location_name'] == STORE
          and lot['provenance_id'].startswith('shoptrip:') and lot['acquired_date'] == TRIP_DAY,
          str(lot))
    rp_rice = record_purchase_proposal(mgr, 'rice-white-raw', STORE, 12.49, 5, 'lb', TRIP_DAY)
    check('a staple with a shelf-life prior gets a best-before date (BulkStaple.shelf_life_days, cited)',
          rp_rice['ok'] and rp_rice['bestBefore'] > TRIP_DAY and rp_rice['bestBeforeSource']
          and rp_rice['storageState'] == 'pantry', str(rp_rice.get('bestBefore')))
    rp_bad = record_purchase_proposal(mgr, '', STORE, 0, 0, 'lb', TRIP_DAY)
    check('missing food / non-positive price or quantity are refused by name',
          not rp_bad['ok'] and 'food' in rp_bad['error'] and 'price' in rp_bad['error'])
    rp_unit = record_purchase_proposal(mgr, 'tofu-firm', STORE, 2.99, 1, 'block', TRIP_DAY)
    check('an unresolvable unit still proposes the lot (grams unresolved, said in notes) — approximate '
          'is fine, invisible is not',
          rp_unit['ok'] and rp_unit['weightBasis'] == 'unresolved' and rp_unit['pricePerKg'] is None
          and 'unresolved' in rp_unit['lotProposals'][0]['notes'])

    # --- the solution through the REAL engine -----------------------------
    sol = json.loads(SEED_SHOPTRIP_SOLUTIONS[0]['definition'])
    params = {'food': 'chicken-breast-raw', 'location': STORE, 'price': 9.98, 'package_quantity': 2,
              'package_unit': 'lb', 'date': TRIP_DAY, 'household': 'demo-household'}
    n_po, n_pi = len(mgr.objectTables['PriceObservation']), len(mgr.objectTables['PantryItem'])
    trace = gb.execute(sol, manager=mgr, params=params)
    ctx = final_context_of(trace) or {}
    made = ctx.get('_generated_events', [])
    check('"Bought it" solution (FormSubscription → record proposal → PriceObservation → lot → refresh) '
          'writes BOTH rows through the real engine and emits refreshDisplay',
          trace.status == 'completed'
          and len(mgr.objectTables['PriceObservation']) == n_po + 1
          and len(mgr.objectTables['PantryItem']) == n_pi + 1
          and [m['class'] for m in made] == ['PriceObservation', 'PantryItem']
          and all(m['created'] for m in made)
          and any(ev.get('name') == 'refreshDisplay' and ev.get('channel') == 'frontend'
                  for ev in ctx.get('_emitted_events', [])),
          f'{trace.status} {trace.error_summary} made={made}')
    rp2 = record_purchase_proposal(mgr, 'chicken-breast-raw', STORE, 10.50, 2, 'lb', TRIP_DAY)
    check('re-submitting the same food/store/date: the existing observation is KEPT (never '
          'overwritten, said so) and the lot is not duplicated',
          rp2['ok'] and rp2['priceObservationExists'] and rp2['priceProposals'] == []
          and 'never overwritten' in rp2['priceObservationStatus'] and rp2['lotExists']
          and rp2['lotProposals'] == [])
    trace2 = gb.execute(sol, manager=mgr, params=dict(params, price=10.50))
    check('running the solution again writes nothing (dedupe by name) and still completes',
          trace2.status == 'completed'
          and len(mgr.objectTables['PriceObservation']) == n_po + 1
          and len(mgr.objectTables['PantryItem']) == n_pi + 1, f'{trace2.status} {trace2.error_summary}')
    # the message the form shows (fix 2026-09-03: "Bought it" was silent)
    m1 = ctx.get('message')
    m2 = (final_context_of(trace2) or {}).get('message')
    check(f'the first "Bought it" says "Recorded $9.98 for chicken-breast-raw at {STORE}; lot of 907 g '
          'put away in the fridge" — context variable `message` + the refreshDisplay payload',
          m1 == f'Recorded $9.98 for chicken-breast-raw at {STORE}; lot of 907 g put away in the fridge'
          and any(ev.get('payload', {}).get('message') == m1 for ev in ctx.get('_emitted_events', [])), str(m1))
    check('the re-submit says the price was already recorded ($9.98) and the lot already put away — kept',
          m2 == f'Price for chicken-breast-raw at {STORE} on {TRIP_DAY} was already recorded ($9.98) — kept; '
                'that lot was already put away — kept', str(m2))
    check('a refused record\'s message IS its error',
          record_purchase_proposal(mgr, '', STORE, 0, 0)['message']
          == record_purchase_proposal(mgr, '', STORE, 0, 0)['error'])
    po = next(r for r in mgr.objectTables['PriceObservation'].values()
              if getattr(r, 'name', '') == rp['priceObservationName'])
    check('the kept observation still carries the FIRST price paid',
          float(po.price) == 9.98)
    cl4 = trip_checklist(mgr, 'demo-alex-week', STORE)
    check('after the put-away the checklist shows chicken bought too (2 of 4)',
          cl4['boughtCount'] == 2 and cl4['lines'][0]['bought'] and cl4['lines'][0]['lot'] == rp['lotName'])

    # --- the API ------------------------------------------------------------
    routes = []
    fake = SimpleNamespace(falconServer=SimpleNamespace(
        add_route=lambda path, res, suffix='': routes.append(path)))
    api = ShoptripAPI(polServer=fake)
    api.manager = mgr
    check('ShoptripAPI registers the checklist + bought routes under /api/mealplanning/shoptrip',
          routes == ['/api/mealplanning/shoptrip/checklist', '/api/mealplanning/shoptrip/bought'], str(routes))
    resp = SimpleNamespace(media=None)
    api.on_get_checklist(SimpleNamespace(params={'plan': 'demo-alex-week', 'location': STORE}), resp)
    check('GET checklist answers the aisle-ordered checklist',
          resp.media['ok'] and [l['food'] for l in resp.media['lines']] == order)
    resp = SimpleNamespace(media=None)
    body = {'food': 'spinach-raw', 'location': STORE, 'price': 2.49, 'package_quantity': 1,
            'package_unit': 'bunch', 'date': TRIP_DAY}
    api.on_post_bought(SimpleNamespace(get_media=lambda: body), resp)
    check('POST bought runs the seeded solution: the observation is new → written; the spinach '
          'lot already exists → NOT proposed again (lotExists, said so); the response says both',
          resp.media['ok'] and resp.media['writeStatus'] == 'completed'
          and [(w['class'], w['created']) for w in resp.media['written']] == [('PriceObservation', True)]
          and resp.media['lotExists'] and 'kept' in resp.media['lotStatus']
          and len(mgr.objectTables['PantryItem']) == n_pi + 1,
          f'{resp.media.get("written")} {resp.media.get("lotStatus")}')

    # --- the page seed -------------------------------------------------------
    page = SEED_SHOPTRIP_PAGE_DISPLAYS[0]
    rows = json.loads(page['definition'])['rows']
    items = [it for r in rows for it in r['items']]
    check('page mealplan/shoptrip: every row\'s items sum to 12 segments, one or two items per row (phone)',
          page['pageRoute'] == 'mealplan/shoptrip'
          and all(sum(it['rowSegmentsUsed'] for it in r['items']) == 12 for r in rows)
          and all(1 <= len(r['items']) <= 2 for r in rows))
    ids = [it['id'] for it in items]
    check('item ids unique', len(ids) == len(set(ids)))
    tables = {t['name']: t for t in SEED_SHOPTRIP_TABLES}
    embeds = [it for it in items if it.get('type') != 'form'
              and it['componentProps']['componentName'] == 'embeddedTable']
    check('every embeddedTable names one of THIS feature\'s tables with the class it renders',
          embeds and all(mp.EMBED_TARGETS.get(it['id'], ('', ''))[1] in tables
                         and tables[mp.EMBED_TARGETS[it['id']][1]]['source_class']
                         == it['componentProps']['inputs']['className'] for it in embeds))
    panels = [it for it in items if it.get('type') != 'form'
              and it['componentProps']['componentName'] == 'api-structured-panel']
    check('every api-structured-panel path is a route this API registers, and picks/hides so no '
          'JSON expander is left',
          panels and all(it['componentProps']['inputs']['path'].split('?')[0] in routes
                         and (it['componentProps']['inputs']['pick'] or it['componentProps']['inputs']['hideKeys'])
                         for it in panels))
    forms = [it for it in items if it.get('type') == 'form']
    check('the form links this feature\'s solution and carries the six purchase fields',
          len(forms) == 1 and forms[0]['item']['linkedSolutionName'] == SEED_SHOPTRIP_SOLUTIONS[0]['name']
          and {v['variableName'] for v in forms[0]['item']['extraVariables']}
          >= {'food', 'location', 'price', 'package_quantity', 'package_unit', 'date'})
    allowed = {'embeddedTable', 'embeddedGraph', 'embeddedCalendar', 'embeddedMap', 'api-structured-panel'}
    check('no raw JSON on the screen: only allowed components + the form',
          all(it.get('type') == 'form' or it['componentProps']['componentName'] in allowed for it in items))
    classes = {'StoreAisleOrder': StoreAisleOrder, 'FoodAisleCategory': FoodAisleCategory,
               'PantryItem': PantryItem}
    bad_cols = []
    for name, t in tables.items():
        cols = json.loads(t['definition'])['tableConfiguration']['columns']
        fields = _fields(classes[t['source_class']])
        bad_cols += [(name, c['name']) for c in cols if c['name'] not in fields]
    check('every table column exists on its class', not bad_cols, str(bad_cols))
    check('the PantryItem table is NOT a class default (mealplan-pantry-standard keeps that role)',
          not tables['shoptrip-pantry-lot-standard']['is_default_table'])
    check('analyses name this module\'s callables; triggers list is empty by design',
          all(a['callable_ref'].startswith('nutrition.shoptrip_analysis:') for a in SEED_SHOPTRIP_ANALYSES)
          and SEED_SHOPTRIP_TRIGGERS == [])

    print(f'\n{len(failures)} failure(s)')
    for f in failures:
        print('  -', f)
    print('PASS: N3 shopping trip holds together' if not failures else 'FAIL: see above')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
