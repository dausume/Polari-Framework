"""
@module odooconnect.selftest_odoo_sync

od-4 selftests: pull idempotency + provenance, conflict honesty, push
idempotency via x_polari_ref (including the ensure-field path — the
stub starts WITHOUT the field), direction guards, gated ops pushes,
receipts. All against the shared stub server; no live Odoo.

Run from polari-framework/: python3 -m odooconnect.selftest_odoo_sync
"""

import json
import os
import types

from odooconnect.odoo_client import ops_confirm_phrase
from odooconnect.odoo_sync import (
    bindings_catalog, pull, push, receipts_catalog,
)
from odooconnect.stub_odoo import STATE, start_stub

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _fake_typing(mgr, class_name):
    """Mimic objectTypingDict[cls].getCreateMethod(): instances
    self-register into objectTables (the treeObject contract)."""
    class Row:
        def __init__(self, manager=None, **kw):
            for key, value in kw.items():
                setattr(self, key, value)
            manager.objectTables.setdefault(class_name, {})[
                id(self)] = self
    return types.SimpleNamespace(getCreateMethod=lambda: Row)


def _cfg(name, mode, push_enabled, read_only, base_url):
    return types.SimpleNamespace(
        name=name, base_url=base_url, db=f'odoo_{name.split("-")[-1]}',
        mode=mode, url_env='', auth_login='stub',
        auth_password_env='STUB_ODOO_PASS', push_enabled=push_enabled,
        read_only=read_only)


def _binding(**kw):
    base = dict(name='b', display_name='b', instance_ref='odoo-sim',
                odoo_model='res.partner', polari_class='SupplyNode',
                field_map_json='{"name": "display_name"}',
                direction='pull', external_ref_field='x_polari_ref',
                row_name_prefix='', defaults_json='{}')
    base.update(kw)
    return types.SimpleNamespace(**base)


def _mgr(url):
    mgr = types.SimpleNamespace(objectTables={}, objectTypingDict={})
    for cls in ('SupplyNode', 'WaxFeedstockDefinition',
                'OdooSyncReceipt'):
        mgr.objectTypingDict[cls] = _fake_typing(mgr, cls)
    mgr.objectTables['OdooInstanceConfig'] = {
        'sim': _cfg('odoo-sim', 'simulation', True, False, url),
        'ops': _cfg('odoo-ops', 'operations', False, True, url)}
    return mgr


def _rows(mgr, cls):
    return {getattr(r, 'name', ''): r
            for r in mgr.objectTables.get(cls, {}).values()}


if __name__ == '__main__':
    server, URL = start_stub()
    os.environ['STUB_ODOO_PASS'] = 'stub-pass'
    STATE.reset()

    print('== suite: pull — provenance + idempotency ==')
    mgr = _mgr(URL)
    partners = _binding(name='sim-partners', row_name_prefix='op')
    out = pull(mgr, partners, page_size=10)
    check('pull ok over 3 pages', out.get('ok')
          and out['pagesFetched'] == 3)
    check('25 rows created', len(out['created']) == 25
          and len(_rows(mgr, 'SupplyNode')) == 25)
    row = _rows(mgr, 'SupplyNode')['op-5']
    check('provenance carries instance:model:id@write_date',
          row.provenance_id ==
          'odoo:odoo-sim:res.partner:5@2026-07-28 00:00:05')
    check('field map applied', row.display_name == 'partner-05')
    out = pull(mgr, partners, page_size=10)
    check('re-pull is idempotent (25 skipped, 0 created)',
          out.get('ok') and out['skippedCount'] == 25
          and not out['created'] and not out['updated'])

    STATE.partners[4]['name'] = 'partner-05-renamed'
    STATE.partners[4]['write_date'] = '2026-07-28 02:00:00'
    out = pull(mgr, partners, page_size=10)
    check('newer write_date -> exactly one update',
          out.get('ok') and out['updated'] == ['op-5']
          and out['skippedCount'] == 24)
    check('update rewrote field + advanced provenance',
          row.display_name == 'partner-05-renamed'
          and row.provenance_id.endswith('@2026-07-28 02:00:00'))

    print('== suite: pull — conflict honesty ==')
    local = types.SimpleNamespace(name='op-9',
                                  provenance_id='hand-authored',
                                  display_name='mine')
    mgr.objectTables['SupplyNode']['local'] = local
    del mgr.objectTables['SupplyNode'][next(
        k for k, v in mgr.objectTables['SupplyNode'].items()
        if getattr(v, 'name', '') == 'op-9' and v is not local)]
    STATE.partners[8]['write_date'] = '2026-07-28 03:00:00'
    out = pull(mgr, partners, page_size=10)
    check('foreign-provenance row -> conflict, not overwrite',
          out.get('ok') and len(out['conflicts']) == 1
          and out['conflicts'][0]['row'] == 'op-9'
          and local.display_name == 'mine')

    print('== suite: guards + refusals ==')
    out = pull(mgr, _binding(direction='push'))
    check('pull on push-only binding refuses naming direction',
          not out.get('ok') and 'direction' in out['refusal'])
    out = pull(mgr, _binding(polari_class='NopeClass'))
    check('unknown class refuses naming POLARI_MODULES',
          not out.get('ok')
          and out['suggestion']['knob'] == 'POLARI_MODULES')
    out = pull(mgr, _binding(instance_ref='odoo-nope'))
    check('unknown instance refuses',
          not out.get('ok') and 'odoo-nope' in out['refusal'])
    out = push(mgr, _binding(direction='both'), row_names=[])
    check('push without explicit row_names refuses',
          not out.get('ok') and 'row_names' in out['refusal'])

    print('== suite: push — x_polari_ref idempotency ==')
    products = _binding(name='sim-products', direction='both',
                        odoo_model='product.template',
                        polari_class='WaxFeedstockDefinition',
                        row_name_prefix='odoo-product')
    Wax = mgr.objectTypingDict['WaxFeedstockDefinition']\
        .getCreateMethod()
    Wax(manager=mgr, name='beeswax-blend',
        display_name='Beeswax blend 60/40', provenance_id='local')
    Wax(manager=mgr, name='carnauba-hard',
        display_name='Carnauba hard wax', provenance_id='local')
    check('stub starts WITHOUT x_polari_ref',
          'x_polari_ref' not in STATE.product_fields)
    out = push(mgr, products,
               row_names=['beeswax-blend', 'carnauba-hard'])
    check('push ok; ensure-field path CREATED the ref field',
          out.get('ok') and out['refFieldEnsured'] == 'created'
          and 'x_polari_ref' in STATE.product_fields)
    check('2 created in odoo with refs', len(out['created']) == 2
          and {p['x_polari_ref'] for p in STATE.products}
          == {'beeswax-blend', 'carnauba-hard'})
    _rows(mgr, 'WaxFeedstockDefinition')['beeswax-blend']\
        .display_name = 'Beeswax blend 70/30'
    out = push(mgr, products, row_names=['beeswax-blend'])
    check('re-push updates by ref (no duplicate)',
          out.get('ok') and len(out['updated']) == 1
          and not out['created']
          and len([p for p in STATE.products
                   if p.get('x_polari_ref') == 'beeswax-blend']) == 1)
    check('odoo side got the edit',
          next(p for p in STATE.products
               if p.get('x_polari_ref') == 'beeswax-blend')['name']
          == 'Beeswax blend 70/30')
    check('missing rows reported, not invented',
          push(mgr, products,
               row_names=['ghost-row'])['missingRows'] == ['ghost-row'])

    print('== suite: push — the ops gate ==')
    ops_b = _binding(name='ops-products', direction='both',
                     instance_ref='odoo-ops',
                     odoo_model='product.template',
                     polari_class='WaxFeedstockDefinition')
    out = push(mgr, ops_b, row_names=['beeswax-blend'])
    check('ops push refuses (read_only row)',
          not out.get('ok') and 'read_only' in out['refusal'])
    mgr.objectTables['OdooInstanceConfig']['ops'].read_only = False
    out = push(mgr, ops_b, row_names=['beeswax-blend'])
    check('ops push refuses naming push_enabled',
          not out.get('ok') and 'push_enabled' in out['refusal'])
    mgr.objectTables['OdooInstanceConfig']['ops'].push_enabled = True
    out = push(mgr, ops_b, row_names=['beeswax-blend'])
    check('ops push still refuses without the typed phrase',
          not out.get('ok') and 'typed' in out['refusal'])
    out = push(mgr, ops_b, row_names=['beeswax-blend'],
               confirm=ops_confirm_phrase('odoo-ops'))
    check('knobs + typed phrase -> ops push lands',
          out.get('ok') and (out['created'] or out['updated']))

    print('== suite: receipts + catalogs ==')
    receipts = receipts_catalog(mgr)
    check('every run left a receipt row',
          receipts.get('ok') and len(receipts['receipts']) >= 6)
    kinds = {r['kind'] for r in receipts['receipts']}
    check('receipts cover pull AND push', kinds == {'pull', 'push'})
    one = next(r for r in receipts['receipts'] if r['kind'] == 'pull'
               and r['created'] == 25)
    check('receipt counts match the first pull',
          one['binding'] == 'sim-partners'
          and one['instance'] == 'odoo-sim')
    mgr.objectTables['OdooModelBinding'] = {
        'b': _binding(name='sim-partners')}
    cat = bindings_catalog(mgr)
    check('bindings catalog lists rows with direction + map',
          cat.get('ok') and cat['bindings'][0]['direction'] == 'pull'
          and json.loads(cat['bindings'][0]['fieldMap']))

    server.shutdown()
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
