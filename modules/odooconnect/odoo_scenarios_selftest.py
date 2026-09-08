"""
@module odooconnect.odoo_scenarios_selftest

od-5 selftests: the sim-only guard, plan-first shape, create/archive
honest suggestions, seed-spec coherence, and harvest math + economy-
tree rows over a canned handle. The FULL driver (purchase -> receive
-> manufacture -> sell) is proven live against a real throwaway DB —
faking Odoo's mrp/stock logic here would test the fake, not the code.

Run from polari-framework/: python3 -m odooconnect.odoo_scenarios_selftest
"""

import json
import types

from odooconnect.custom.odoo_scenario_engine import (
    derive_scenario_config, scenario_archive_status,
    scenario_create_status, scenario_harvest, scenario_plan,
    scenarios_catalog,
)
from odooconnect.odoo_scenarios_basis import SEED_BUSINESS_SCENARIOS

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _fake_typing(mgr, class_name):
    class Row:
        def __init__(self, manager=None, **kw):
            for k, v in kw.items():
                setattr(self, k, v)
            manager.objectTables.setdefault(class_name, {})[
                id(self)] = self
    return types.SimpleNamespace(getCreateMethod=lambda: Row)


def _mgr():
    mgr = types.SimpleNamespace(objectTables={}, objectTypingDict={})
    for cls in ('BusinessModelDefinition', 'BusinessOutcome',
                'OdooSyncReceipt'):
        mgr.objectTypingDict[cls] = _fake_typing(mgr, cls)
    mgr.objectTables['OdooInstanceConfig'] = {
        'sim': types.SimpleNamespace(
            name='odoo-sim', base_url='http://stub:1', db='odoo_sim',
            mode='simulation', url_env='', auth_login='stub',
            auth_password_env='X', push_enabled=True,
            read_only=False),
        'ops': types.SimpleNamespace(
            name='odoo-ops', base_url='http://stub:1', db='odoo_ops',
            mode='operations', url_env='', auth_login='stub',
            auth_password_env='X', push_enabled=False,
            read_only=True)}
    return mgr


def _scenario(**kw):
    base = {k: v for k, v in SEED_BUSINESS_SCENARIOS[0].items()}
    base.update(kw)
    return types.SimpleNamespace(**base)


class CannedHandle:
    """search_read answers from a canned {model: rows} dict."""

    def __init__(self, config, timeout=15, canned=None):
        self.config = config
        self.canned = canned if canned is not None else CANNED

    def authenticate(self):
        return {'ok': False,
                'refusal': 'odoo error: database "x" does not exist'}

    def search_read(self, model, domain=None, fields=None, **kw):
        return {'ok': True, 'result': self.canned.get(model, [])}


CANNED = {
    'purchase.order': [{'amount_untaxed': 242.1},
                       {'amount_untaxed': 242.1}],
    'sale.order': [{'amount_untaxed': 360.0},
                   {'amount_untaxed': 360.0}],
    'mrp.production': [
        {'product_id': [7, 'Wax-printed mold (planter)'],
         'product_qty': 3.0, 'state': 'done'},
        {'product_id': [8, 'Geopolymer planter pot'],
         'product_qty': 20.0, 'state': 'done'},
        {'product_id': [7, 'Wax-printed mold (planter)'],
         'product_qty': 3.0, 'state': 'done'},
        {'product_id': [8, 'Geopolymer planter pot'],
         'product_qty': 20.0, 'state': 'done'},
        {'product_id': [8, 'Geopolymer planter pot'],
         'product_qty': 99.0, 'state': 'confirmed'},
    ],
}


if __name__ == '__main__':
    print('== suite: the sim-only guard ==')
    mgr = _mgr()
    scn = _scenario()
    cfg, refusal = derive_scenario_config(mgr, scn)
    check('sim base accepted, db is the THROWAWAY',
          refusal is None and cfg.db == 'odoo_scn_wax_mold_goods_v1'
          and cfg.db != 'odoo_sim')
    _, refusal = derive_scenario_config(
        mgr, _scenario(instance_ref='odoo-ops'))
    check('operations base REFUSED outright',
          refusal is not None and 'simulation' in refusal['refusal'])
    check('refusal names the invariant + the knob',
          'invariant' in refusal['suggestion']['evidence']
          and 'instance_ref' in refusal['suggestion']['knob'])
    _, refusal = derive_scenario_config(
        mgr, _scenario(instance_ref='odoo-nope'))
    check('unknown base refused', refusal is not None)

    print('== suite: plan-first ==')
    plan = scenario_plan(mgr, scn)
    check('plan ok with 5 phases', plan.get('ok')
          and [s['phase'] for s in plan['steps']]
          == ['create', 'seed', 'run', 'harvest', 'archive'])
    check('assumptions surface in the plan (commercial buyer + '
          'working printer)',
          any('commercial supplier' in a for a in plan['assumptions'])
          and any('3D printer' in a for a in plan['assumptions']))
    check('host ops carry exact pol commands',
          'pol odoo scenario-init odoo_scn_wax_mold_goods_v1'
          in plan['steps'][0]['command']
          and 'pol odoo scenario-drop' in plan['steps'][4]['command'])

    print('== suite: create/archive honest suggestions ==')
    out = scenario_create_status(mgr, scn, handle_factory=CannedHandle)
    check('missing DB -> ready False + init suggestion',
          not out.get('ready')
          and 'scenario-init' in out['suggestion']['action']
          and scn.required_modules in out['suggestion']['action'])
    out = scenario_archive_status(mgr, scn)
    check('archive suggests the drop, promises receipt persistence',
          out.get('ok') and 'scenario-drop' in
          out['suggestion']['action'] and 'persist' in out['note'])

    print('== suite: seed-spec coherence ==')
    spec = json.loads(scn.seed_spec_json)
    refs = {p['ref'] for p in spec['products']}
    line_refs = {l['ref'] for b in spec['boms'] for l in b['lines']}
    check('every BOM line names a seeded product',
          line_refs <= refs)
    check('mold BOM consumes pellets; pot BOM amortizes the mold',
          any(l['ref'] == 'soy-wax-pellets' and l['qty'] == 0.35
              for b in spec['boms'] if b['product_ref'] ==
              'wax-mold-planter' for l in b['lines'])
          and any(l['ref'] == 'wax-mold-planter' and l['qty'] == 0.1
                  for b in spec['boms'] if b['product_ref'] ==
                  'geopolymer-planter-pot' for l in b['lines']))
    driver = json.loads(scn.driver_spec_json)
    sold = sum(l['qty'] for s in driver['per_cycle']['sales']
               for l in s['lines'])
    made = {m['ref']: m['qty']
            for m in driver['per_cycle']['manufacture']}
    check('driver makes what it sells (20 pots) + mold buffer',
          sold == made['geopolymer-planter-pot'] == 20.0
          and made['wax-mold-planter'] * 10 >= sold)

    print('== suite: harvest math + economy-tree rows ==')
    out = scenario_harvest(mgr, scn, handle_factory=CannedHandle)
    m = out.get('metrics', {})
    check('harvest ok', out.get('ok'), json.dumps(out)[:200])
    check('revenue/cost/margin computed (repinned cited prices)',
          m.get('revenue') == 720.0
          and m.get('material_cost') == 484.2
          and m.get('margin') == 235.8)
    check('only DONE manufacturing counts',
          m.get('pots_made') == 40.0 and m.get('molds_made') == 6.0)
    outcomes = list(mgr.objectTables.get('BusinessOutcome',
                                         {}).values())
    check('BusinessOutcome row created, positive margin = succeeded',
          len(outcomes) == 1 and outcomes[0].outcome == 'succeeded'
          and outcomes[0].business_model ==
          'wax-mold-goods-microbusiness')
    check('outcome evidence carries metrics + assumptions',
          'metrics' in outcomes[0].evidence_json
          and 'commercial supplier' in outcomes[0].evidence_json)
    models = list(mgr.objectTables.get('BusinessModelDefinition',
                                       {}).values())
    check('BusinessModelDefinition created, honestly NOT '
          'self-sustaining', len(models) == 1
          and models[0].self_sustaining is False)
    receipts = list(mgr.objectTables.get('OdooSyncReceipt',
                                         {}).values())
    check('harvest receipted',
          any(getattr(r, 'kind', '') == 'scenario-harvest'
              for r in receipts))

    print('== suite: catalog ==')
    mgr.objectTables['BusinessScenarioDefinition'] = {'s': scn}
    cat = scenarios_catalog(mgr)
    check('catalog lists the scenario with assumptions',
          cat.get('ok') and cat['scenarios'][0]['assumptions'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
