"""
@module odooconnect.odoo_orders_selftest

od-4b selftests: sale.order line explosion into ProductOrder rows
against the stub — product mapping ladder (x_polari_ref >
default_code > honest unmapped), volume m3->L with flagged 1.0
fallback, due_days from commitment_date with defaulted fallback,
state value-map, provenance idempotency + foreign-provenance
conflicts, receipts — and the SPLICE: the bizops order planner
answering over the pulled book.

Run from polari-framework/:
    python3 -m odooconnect.odoo_orders_selftest
"""

import os
import time
import types

from bizops.custom.bizops_planner import order_plan
from bizops.bizops_seed import (
    SEED_BUSINESS_PROFILES, SEED_BUSINESS_STAGES,
    SEED_PROCESS_WORKFLOWS,
)
from odooconnect.custom.odoo_orders import _due_days, pull_orders
from odooconnect.custom.stub_odoo import STATE, start_stub
from supplychain.sourcing_seed import (
    SEED_PRICE_CITATIONS, SEED_PRODUCT_FORMULAS,
    SEED_PRODUCT_REQUIREMENTS, SEED_SUPPLY_SOURCES,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []

#: Fixed 'now' for date math: 2026-07-28 12:00 local — the stub's
#: S00071 promises 2026-08-15, i.e. 18 days out.
NOW_TS = time.mktime(time.strptime('2026-07-28 12:00:00',
                                   '%Y-%m-%d %H:%M:%S'))


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _fake_typing(mgr, class_name):
    class Row:
        def __init__(self, manager=None, **kw):
            for key, value in kw.items():
                setattr(self, key, value)
            manager.objectTables.setdefault(class_name, {})[
                id(self)] = self
    return types.SimpleNamespace(getCreateMethod=lambda: Row)


def _cfg(url):
    return types.SimpleNamespace(
        name='odoo-sim', base_url=url, db='odoo_sim',
        mode='simulation', url_env='', auth_login='stub',
        auth_password_env='STUB_ODOO_PASS', push_enabled=True,
        read_only=False)


def _binding(**kw):
    base = dict(name='sim-sale-orders', display_name='orders',
                instance_ref='odoo-sim', odoo_model='sale.order',
                polari_class='ProductOrder', field_map_json='{}',
                direction='pull', external_ref_field='x_polari_ref',
                row_name_prefix='odoo-so',
                defaults_json='{"due_days": 30}')
    base.update(kw)
    return types.SimpleNamespace(**base)


def _seed_rows(seed_list):
    return {s['name']: types.SimpleNamespace(**s) for s in seed_list}


def _mgr(url):
    mgr = types.SimpleNamespace(objectTables={}, objectTypingDict={})
    for cls in ('ProductOrder', 'OdooSyncReceipt'):
        mgr.objectTypingDict[cls] = _fake_typing(mgr, cls)
    mgr.objectTables['OdooInstanceConfig'] = {'sim': _cfg(url)}
    return mgr


def _orders(mgr):
    return {getattr(r, 'name', ''): r
            for r in mgr.objectTables.get('ProductOrder',
                                          {}).values()}


if __name__ == '__main__':
    server, URL = start_stub()
    os.environ['STUB_ODOO_PASS'] = 'stub-pass'
    STATE.reset()

    print('== suite: helpers ==')
    check('due-days math: 2026-08-15 from the fixed now = 18 days',
          _due_days('2026-08-15 12:00:00', now_ts=NOW_TS) == 18)
    check('past promise dates floor at 0, never negative',
          _due_days('2026-07-01', now_ts=NOW_TS) == 0)
    check('no/garbled promise date -> None (caller defaults, '
          'noted)', _due_days(False) is None
          and _due_days('not-a-date') is None)

    print('== suite: pull-orders — explosion + honest mapping ==')
    mgr = _mgr(URL)
    out = pull_orders(mgr, _binding(), now_ts=NOW_TS)
    rows = _orders(mgr)
    check('pull ok: 4 lines over 3 orders -> 4 ProductOrder rows',
          out.get('ok') and len(out['created']) == 4
          and out['ordersSeen'] == 3, extra=str(out))
    pot = rows.get('odoo-so-71-711')
    check('x_polari_ref wins the mapping ladder: pot line -> '
          'geopolymer-mix',
          pot is not None
          and pot.product_item_ref == 'geopolymer-mix'
          and 'x_polari_ref' in pot.customer_note)
    check('volume mapped m3 -> L: 0.001 m3 = 1.0 L, no note',
          pot.unit_volume_l == 1.0 and 'volume unset'
          not in pot.notes)
    check('due_days derived from the order promise date (18)',
          pot.due_days == 18 and pot.quantity == 12
          and pot.status == 'accepted')
    shelf = rows.get('odoo-so-71-712')
    check('default_code is the second rung: shelf line -> '
          'shelf-std',
          shelf is not None
          and shelf.product_item_ref == 'shelf-std')
    check('missing volume -> flagged 1.0 fallback ON THE ROW and '
          'in the receipt',
          shelf.unit_volume_l == 1.0
          and 'volume unset' in shelf.notes
          and any(v['item'] == 'shelf-std'
                  for v in out['needsVolume']))
    trinket = rows.get('odoo-so-72-721')
    check('unmapped product still lands, honestly marked, receipt '
          'lists it',
          trinket is not None
          and trinket.product_item_ref == 'unmapped:Mystery trinket'
          and any(u['product'] == 'Mystery trinket'
                  for u in out['unmappedProducts']))
    check('draft order w/o promise date: status requested, '
          'due_days defaulted to 30 with the note',
          trinket.status == 'requested' and trinket.due_days == 30
          and 'no commitment_date' in trinket.notes)
    cancelled = rows.get('odoo-so-73-731')
    check('cancelled order maps to refused — kept on record, '
          'planner ignores it',
          cancelled is not None and cancelled.status == 'refused')
    check('receipt row written with kind pull-orders',
          any(getattr(r, 'kind', '') == 'pull-orders'
              for r in mgr.objectTables['OdooSyncReceipt'].values()))

    print('== suite: idempotency + conflicts ==')
    out2 = pull_orders(mgr, _binding(), now_ts=NOW_TS)
    check('re-run skips all 4 (same provenance), creates nothing',
          out2.get('ok') and out2['skippedCount'] == 4
          and not out2['created'] and not out2['updated'])
    STATE.sale_lines[0]['product_uom_qty'] = 15.0
    STATE.sale_lines[0]['write_date'] = '2026-07-28 03:00:00'
    out3 = pull_orders(mgr, _binding(), now_ts=NOW_TS)
    check('quantity edit in odoo advances provenance: 1 updated, '
          'qty now 15',
          out3.get('ok') and out3['updated'] == ['odoo-so-71-711']
          and _orders(mgr)['odoo-so-71-711'].quantity == 15)
    local = mgr.objectTypingDict['ProductOrder'].getCreateMethod()
    local(manager=mgr, name='odoo-so-99-999',
          provenance_id='biz-1', product_item_ref='geopolymer-mix',
          unit_volume_l=1.0, quantity=1, due_days=10,
          status='requested', notes='')
    STATE.sale_orders.append(
        {'id': 99, 'name': 'S00099', 'state': 'sale',
         'commitment_date': False,
         'date_order': '2026-07-28 09:00:00',
         'partner_id': [3, 'p'],
         'write_date': '2026-07-28 03:10:00'})
    STATE.sale_lines.append(
        {'id': 999, 'order_id': [99, 'S00099'],
         'product_id': [501, 'Self-watering pot 1L'],
         'product_uom_qty': 7.0, 'name': 'colliding line',
         'write_date': '2026-07-28 03:10:01'})
    out4 = pull_orders(mgr, _binding(), now_ts=NOW_TS)
    check('locally-authored row with the colliding name = '
          'CONFLICT, never touched',
          any(c['row'] == 'odoo-so-99-999'
              for c in out4['conflicts'])
          and _orders(mgr)['odoo-so-99-999'].quantity == 1)

    print('== suite: guards ==')
    bad = pull_orders(mgr, _binding(polari_class='SupplyNode'))
    check('non-ProductOrder binding refused toward /api/odoo/pull',
          not bad.get('ok') and 'pull' in
          bad['suggestion']['action'])
    push_only = pull_orders(mgr, _binding(direction='push'))
    check('direction guard still bites', not push_only.get('ok'))

    print('== suite: THE SPLICE — planner over the pulled book ==')
    mgr.objectTables.update({
        'SupplySourceProfile': _seed_rows(SEED_SUPPLY_SOURCES),
        'PriceCitation': _seed_rows(SEED_PRICE_CITATIONS),
        'ProductInputRequirement': _seed_rows(
            SEED_PRODUCT_REQUIREMENTS),
        'ProductFormula': _seed_rows(SEED_PRODUCT_FORMULAS),
        'BusinessStageDefinition': _seed_rows(SEED_BUSINESS_STAGES),
        'BusinessProfile': _seed_rows(SEED_BUSINESS_PROFILES),
        'ProcessWorkflowDefinition': _seed_rows(
            SEED_PROCESS_WORKFLOWS),
        'MoldLifecycleRecord': {},
        'ProductionRunRecord': {},
    })
    plan = order_plan(mgr, 'wax-mold-goods', horizon_days=30)
    check('planner runs on the PULLED registrar and answers all '
          'three questions',
          plan.get('ok') and plan.get('capacity')
          and plan.get('supply') and plan.get('reuse'))
    check('refused (cancelled-in-odoo) lines are NOT planned: '
          '4 of 5 lines considered',
          plan.get('ordersConsidered') == 4,
          extra=str(plan.get('ordersConsidered')))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    server.shutdown()
    raise SystemExit(1 if failed else 0)
