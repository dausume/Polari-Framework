"""
@module odooconnect.odoo_scenario_engine

Scenario lifecycle (od-5): plan -> create -> seed -> run -> harvest ->
archive. THE guard: the base config must be mode=simulation — an
operations config is refused before anything else happens, so a
scenario can never touch real business data.

Division of labor (honest about capability): the backend drives DATA
through JSON-RPC (seed/run/harvest); DATABASE create/drop are host
operations, so create/archive return the exact `pol odoo` command as
an evidence-bearing suggestion instead of pretending.

Everything is receipted (OdooSyncReceipt, kind='scenario-<phase>').
Orders carry origin 'polari:<scenario>' so harvest reads back ONLY
this scenario's documents — deterministic runs, comparable harvests.
"""

import json
import time
import types

from odooconnect.odoo_client import OdooHandle
from odooconnect.odoo_sync import (
    _class_for, _ensure_external_ref_field, _named_row, _refuse,
    _write_receipt,
)

REF = 'x_polari_ref'


def _scenario_named(manager, name):
    return _named_row(manager, 'BusinessScenarioDefinition', name)


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except ValueError:
        return default


def derive_scenario_config(manager, scenario):
    """Transient config for the THROWAWAY database — inherits the base
    sim server/auth, never its db. Refuses operations bases."""
    base = _named_row(manager, 'OdooInstanceConfig',
                      getattr(scenario, 'instance_ref', ''))
    if base is None:
        return None, _refuse(
            f'scenario "{scenario.name}" names unknown instance '
            f'"{getattr(scenario, "instance_ref", "")}"')
    if getattr(base, 'mode', '') != 'simulation':
        return None, _refuse(
            f'scenario "{scenario.name}" is bound to '
            f'"{base.name}" (mode={getattr(base, "mode", "?")}) — '
            'scenarios run ONLY on simulation configs, ever',
            {'evidence': 'the sim/ops hard invariant '
                         '(ODOO_INTEGRATION_PLAN.md)',
             'knob': 'BusinessScenarioDefinition.instance_ref',
             'action': 'point the scenario at a mode=simulation '
                       'config (odoo-sim)'})
    return types.SimpleNamespace(
        name=f'{base.name}@{scenario.scenario_db}',
        base_url=getattr(base, 'base_url', ''),
        url_env=getattr(base, 'url_env', ''),
        db=getattr(scenario, 'scenario_db', ''),
        mode='simulation',
        auth_login=getattr(base, 'auth_login', ''),
        auth_password_env=getattr(base, 'auth_password_env', ''),
        push_enabled=True, read_only=False), None


def scenario_plan(manager, scenario):
    """Plan-first: the full step list BEFORE anything runs."""
    _, refusal = derive_scenario_config(manager, scenario)
    if refusal:
        return refusal
    driver = _loads(scenario, 'driver_spec_json', {})
    db = scenario.scenario_db
    mods = scenario.required_modules
    return {'ok': True, 'scenario': scenario.name,
            'assumptions': _loads(scenario, 'assumptions_json', []),
            'steps': [
                {'phase': 'create', 'runBy': 'pol CLI (host op)',
                 'command': f'pol odoo scenario-init {db} '
                            f'--modules {mods}'},
                {'phase': 'seed', 'runBy': 'backend RPC',
                 'what': 'partners + products + BOMs '
                         '(idempotent by x_polari_ref)'},
                {'phase': 'run', 'runBy': 'backend RPC',
                 'what': f'{driver.get("cycles", 0)} cycle(s): '
                         'purchase -> receive -> manufacture -> '
                         'sell -> deliver'},
                {'phase': 'harvest', 'runBy': 'backend RPC',
                 'what': 'P&L + throughput -> BusinessOutcome on '
                         'the economy tree'},
                {'phase': 'archive', 'runBy': 'pol CLI (host op)',
                 'command': f'pol odoo scenario-drop {db}'},
            ]}


def scenario_create_status(manager, scenario,
                           handle_factory=OdooHandle):
    """Probe the throwaway DB; when absent, the refusal carries the
    exact init command — the backend cannot create databases."""
    cfg, refusal = derive_scenario_config(manager, scenario)
    if refusal:
        return refusal
    out = handle_factory(cfg).authenticate()
    if out.get('ok'):
        return {'ok': True, 'scenario': scenario.name,
                'db': cfg.db, 'ready': True}
    out.setdefault('suggestion', {})
    out['suggestion'] = {
        'evidence': out.get('refusal', ''),
        'knob': 'pol odoo scenario-init',
        'action': f'pol odoo scenario-init {scenario.scenario_db} '
                  f'--modules {scenario.required_modules}'}
    out['ready'] = False
    return out


def _find_by_ref(handle, model, ref):
    out = handle.search_read(model, domain=[[REF, '=', ref]],
                             fields=['id'], limit=1)
    if not out.get('ok'):
        return out
    recs = out.get('result') or []
    return {'ok': True, 'result': recs[0]['id'] if recs else None}


def _upsert_by_ref(handle, model, ref, vals):
    found = _find_by_ref(handle, model, ref)
    if not found.get('ok'):
        return found
    vals = dict(vals)
    vals[REF] = ref
    if found['result']:
        out = handle.execute_kw(model, 'write',
                                [[found['result']], vals])
        if not out.get('ok'):
            return out
        return {'ok': True, 'result': found['result'],
                'action': 'updated'}
    out = handle.execute_kw(model, 'create', [vals])
    if not out.get('ok'):
        return out
    return {'ok': True, 'result': out['result'], 'action': 'created'}


def _variant_of(handle, tmpl_id):
    out = handle.search_read('product.template',
                             domain=[['id', '=', tmpl_id]],
                             fields=['product_variant_id'], limit=1)
    if not out.get('ok'):
        return out
    recs = out.get('result') or []
    if not recs or not recs[0].get('product_variant_id'):
        return _refuse(f'product template {tmpl_id} has no variant')
    return {'ok': True, 'result': recs[0]['product_variant_id'][0]}


def scenario_seed(manager, scenario, handle_factory=OdooHandle):
    """Partners + products + BOMs into the throwaway DB, idempotent
    by x_polari_ref. Returns the id map the driver runs on."""
    cfg, refusal = derive_scenario_config(manager, scenario)
    if refusal:
        return refusal
    handle = handle_factory(cfg)
    spec = _loads(scenario, 'seed_spec_json', {})
    for model in ('res.partner', 'product.template', 'mrp.bom'):
        ensured = _ensure_external_ref_field(handle, model, REF)
        if not ensured.get('ok'):
            return ensured
    ids = {'partners': {}, 'products': {}, 'variants': {},
           'boms': {}}
    actions = []
    for p in spec.get('partners', []):
        vals = {'name': p['name']}
        for rank in ('supplier_rank', 'customer_rank'):
            if p.get(rank):
                vals[rank] = p[rank]
        out = _upsert_by_ref(handle, 'res.partner', p['ref'], vals)
        if not out.get('ok'):
            return out
        ids['partners'][p['ref']] = out['result']
        actions.append(f'partner {p["ref"]}: {out["action"]}')
    for pr in spec.get('products', []):
        vals = {'name': pr['name'],
                'purchase_ok': bool(pr.get('purchase_ok')),
                'sale_ok': bool(pr.get('sale_ok')),
                'standard_price': pr.get('standard_price', 0.0),
                'list_price': pr.get('list_price', 0.0)}
        if pr.get('storable'):
            vals['is_storable'] = True
        out = _upsert_by_ref(handle, 'product.template', pr['ref'],
                             vals)
        if not out.get('ok'):
            return out
        ids['products'][pr['ref']] = out['result']
        variant = _variant_of(handle, out['result'])
        if not variant.get('ok'):
            return variant
        ids['variants'][pr['ref']] = variant['result']
        actions.append(f'product {pr["ref"]}: {out["action"]}')
    for bom in spec.get('boms', []):
        ref = f'bom-{bom["product_ref"]}'
        lines = [(0, 0, {'product_id': ids['variants'][l['ref']],
                         'product_qty': l['qty']})
                 for l in bom.get('lines', [])]
        found = _find_by_ref(handle, 'mrp.bom', ref)
        if not found.get('ok'):
            return found
        if found['result']:
            ids['boms'][bom['product_ref']] = found['result']
            actions.append(f'bom {ref}: kept')
            continue
        out = handle.execute_kw('mrp.bom', 'create', [{
            'product_tmpl_id': ids['products'][bom['product_ref']],
            'product_qty': bom.get('qty', 1.0), 'type': 'normal',
            'bom_line_ids': lines, REF: ref}])
        if not out.get('ok'):
            return out
        ids['boms'][bom['product_ref']] = out['result']
        actions.append(f'bom {ref}: created')
    receipt = {'ok': True, 'verb': 'scenario-seed',
               'scenario': scenario.name, 'db': cfg.db,
               'actions': actions, 'ids': ids,
               'created': [a for a in actions if 'created' in a],
               'updated': [a for a in actions if 'updated' in a],
               'skippedCount': len([a for a in actions
                                    if 'kept' in a]),
               'conflicts': []}
    receipt['receiptRow'] = _write_receipt(
        manager, 'scenario-seed', scenario, cfg, receipt)
    return receipt


def _validate_pickings(handle, order_model, order_id):
    """Receive/deliver: mark move quantities done, then validate."""
    out = handle.search_read(order_model,
                             domain=[['id', '=', order_id]],
                             fields=['picking_ids'], limit=1)
    if not out.get('ok'):
        return out
    pickings = (out.get('result') or [{}])[0].get('picking_ids', [])
    for pid in pickings:
        moves = handle.search_read(
            'stock.move', domain=[['picking_id', '=', pid]],
            fields=['product_uom_qty'])
        if not moves.get('ok'):
            return moves
        for mv in moves.get('result') or []:
            done = handle.execute_kw(
                'stock.move', 'write',
                [[mv['id']], {'quantity': mv['product_uom_qty'],
                              'picked': True}])
            if not done.get('ok'):
                return done
        val = handle.execute_kw('stock.picking', 'button_validate',
                                [[pid]])
        if not val.get('ok'):
            return val
    return {'ok': True, 'result': pickings}


def scenario_run(manager, scenario, handle_factory=OdooHandle):
    """Drive the cycles through Odoo's REAL business logic."""
    cfg, refusal = derive_scenario_config(manager, scenario)
    if refusal:
        return refusal
    handle = handle_factory(cfg)
    seeded = scenario_seed(manager, scenario,
                           handle_factory=handle_factory)
    if not seeded.get('ok'):
        return seeded
    ids = seeded['ids']
    driver = _loads(scenario, 'driver_spec_json', {})
    origin = f'polari:{scenario.name}'
    cycles = int(driver.get('cycles', 1))
    per = driver.get('per_cycle', {})
    log = []
    for cycle in range(1, cycles + 1):
        for po in per.get('purchases', []):
            lines = [(0, 0, {'product_id': ids['variants'][l['ref']],
                             'product_qty': l['qty'],
                             'price_unit': l['price_unit']})
                     for l in po.get('lines', [])]
            out = handle.execute_kw('purchase.order', 'create', [{
                'partner_id': ids['partners'][po['vendor_ref']],
                'origin': origin, 'order_line': lines}])
            if not out.get('ok'):
                return out
            po_id = out['result']
            for step in ('button_confirm',):
                ok = handle.execute_kw('purchase.order', step,
                                       [[po_id]])
                if not ok.get('ok'):
                    return ok
            ok = _validate_pickings(handle, 'purchase.order', po_id)
            if not ok.get('ok'):
                return ok
            log.append(f'cycle {cycle}: PO {po_id} received')
        for mo in per.get('manufacture', []):
            out = handle.execute_kw('mrp.production', 'create', [{
                'product_id': ids['variants'][mo['ref']],
                'product_qty': mo['qty'],
                'bom_id': ids['boms'][mo['ref']],
                'origin': origin}])
            if not out.get('ok'):
                return out
            mo_id = out['result']
            for step, args in (('action_confirm', [[mo_id]]),):
                ok = handle.execute_kw('mrp.production', step, args)
                if not ok.get('ok'):
                    return ok
            ok = handle.execute_kw('mrp.production', 'write',
                                   [[mo_id],
                                    {'qty_producing': mo['qty']}])
            if not ok.get('ok'):
                return ok
            # Odoo 18: component moves must be picked with their
            # quantities before mark-done, else the MO parks in
            # 'to_close' and nothing lands in stock.
            raw = handle.search_read(
                'stock.move',
                domain=[['raw_material_production_id', '=', mo_id]],
                fields=['product_uom_qty'])
            if not raw.get('ok'):
                return raw
            for mv in raw.get('result') or []:
                done = handle.execute_kw(
                    'stock.move', 'write',
                    [[mv['id']], {'quantity': mv['product_uom_qty'],
                                  'picked': True}])
                if not done.get('ok'):
                    return done
            ok = handle.execute_kw('mrp.production',
                                   'button_mark_done', [[mo_id]])
            if not ok.get('ok'):
                return ok
            state = handle.search_read('mrp.production',
                                       domain=[['id', '=', mo_id]],
                                       fields=['state'], limit=1)
            if not state.get('ok'):
                return state
            got = (state.get('result') or [{}])[0].get('state', '')
            if got != 'done':
                return _refuse(
                    f'MO {mo_id} ({mo["ref"]}) ended in state '
                    f'"{got}", not "done" — refusing to continue a '
                    'run whose production did not really happen')
            log.append(f'cycle {cycle}: MO {mo_id} '
                       f'{mo["ref"]} x{mo["qty"]} done')
        for so in per.get('sales', []):
            lines = [(0, 0, {'product_id': ids['variants'][l['ref']],
                             'product_uom_qty': l['qty'],
                             'price_unit': l['price_unit']})
                     for l in so.get('lines', [])]
            out = handle.execute_kw('sale.order', 'create', [{
                'partner_id': ids['partners'][so['customer_ref']],
                'origin': origin, 'order_line': lines}])
            if not out.get('ok'):
                return out
            so_id = out['result']
            ok = handle.execute_kw('sale.order', 'action_confirm',
                                   [[so_id]])
            if not ok.get('ok'):
                return ok
            ok = _validate_pickings(handle, 'sale.order', so_id)
            if not ok.get('ok'):
                return ok
            log.append(f'cycle {cycle}: SO {so_id} delivered')
    receipt = {'ok': True, 'verb': 'scenario-run',
               'scenario': scenario.name, 'db': cfg.db,
               'cycles': cycles, 'log': log,
               'created': log, 'updated': [], 'skippedCount': 0,
               'conflicts': []}
    receipt['receiptRow'] = _write_receipt(
        manager, 'scenario-run', scenario, cfg, receipt)
    return receipt


def scenario_harvest(manager, scenario, handle_factory=OdooHandle):
    """Read outcomes back and put NUMBERS on the economy tree."""
    cfg, refusal = derive_scenario_config(manager, scenario)
    if refusal:
        return refusal
    handle = handle_factory(cfg)
    origin = f'polari:{scenario.name}'
    pos = handle.search_read('purchase.order',
                             domain=[['origin', '=', origin]],
                             fields=['amount_untaxed'])
    if not pos.get('ok'):
        return pos
    sos = handle.search_read('sale.order',
                             domain=[['origin', '=', origin]],
                             fields=['amount_untaxed'])
    if not sos.get('ok'):
        return sos
    mos = handle.search_read('mrp.production',
                             domain=[['origin', '=', origin]],
                             fields=['product_id', 'product_qty',
                                     'state'])
    if not mos.get('ok'):
        return mos
    material_cost = round(sum(r['amount_untaxed']
                              for r in pos.get('result') or []), 2)
    revenue = round(sum(r['amount_untaxed']
                        for r in sos.get('result') or []), 2)
    made = {}
    for r in mos.get('result') or []:
        label = (r.get('product_id') or [0, ''])[1]
        made[label] = made.get(label, 0.0) + (
            r['product_qty'] if r.get('state') == 'done' else 0.0)
    pots = sum(q for n, q in made.items() if 'pot' in n.lower())
    molds = sum(q for n, q in made.items() if 'mold' in n.lower())
    spec = _loads(scenario, 'outcome_spec_json', {})
    metrics = {'revenue': revenue, 'material_cost': material_cost,
               'margin': round(revenue - material_cost, 2),
               'pots_made': pots, 'molds_made': molds,
               'purchaseOrders': len(pos.get('result') or []),
               'saleOrders': len(sos.get('result') or [])}
    outcome_row = ''
    model_name = spec.get('business_model', '')
    bm_cls = _class_for(manager, 'BusinessModelDefinition')
    bo_cls = _class_for(manager, 'BusinessOutcome')
    if bo_cls is not None and model_name:
        stamp = time.strftime('%Y%m%d-%H%M%S')
        outcome_row = f'{scenario.name}-harvest-{stamp}'
        summary = (f'{int(pots)} pots from {int(molds)} molds; '
                   f'revenue {revenue}, materials {material_cost}, '
                   f'margin {metrics["margin"]} (sim, v1 excludes '
                   'labor/energy/amortization)')
        bo_cls(manager=manager, name=outcome_row,
               business_model=model_name, summary=summary,
               outcome='succeeded' if metrics['margin'] > 0
               else 'mixed',
               evidence_json=json.dumps(
                   {'scenario': scenario.name, 'db': cfg.db,
                    'metrics': metrics,
                    'assumptions': _loads(scenario,
                                          'assumptions_json', [])}),
               notes='harvested by odoo_scenario_engine (od-5)')
        if bm_cls is not None and _named_row(
                manager, 'BusinessModelDefinition',
                model_name) is None:
            bm_cls(manager=manager, name=model_name,
                   scale=spec.get('business_model_scale',
                                  'one-person'),
                   unit_economics_json=json.dumps(metrics),
                   self_sustaining=False,
                   evidence_json=json.dumps([outcome_row]),
                   notes='created from scenario harvest (od-5); '
                         'self_sustaining stays False until real '
                         'costs are modeled')
    receipt = {'ok': True, 'verb': 'scenario-harvest',
               'scenario': scenario.name, 'db': cfg.db,
               'metrics': metrics, 'businessOutcomeRow': outcome_row,
               'created': [outcome_row] if outcome_row else [],
               'updated': [], 'skippedCount': 0, 'conflicts': []}
    receipt['receiptRow'] = _write_receipt(
        manager, 'scenario-harvest', scenario, cfg, receipt)
    return receipt


def scenario_archive_status(manager, scenario):
    """Archiving drops the DB — a host op; suggest, never pretend."""
    cfg, refusal = derive_scenario_config(manager, scenario)
    if refusal:
        return refusal
    return {'ok': True, 'scenario': scenario.name, 'db': cfg.db,
            'note': 'harvest receipts + BusinessOutcome rows persist '
                    'in Polari; the throwaway DB is dropped (with a '
                    'pg_dump receipt) by the CLI',
            'suggestion': {
                'evidence': 'database drop is a host operation',
                'knob': 'pol odoo scenario-drop',
                'action': f'pol odoo scenario-drop '
                          f'{scenario.scenario_db}'}}


def scenarios_catalog(manager):
    rows = []
    for s in getattr(manager, 'objectTables', {}).get(
            'BusinessScenarioDefinition', {}).values():
        rows.append({
            'name': getattr(s, 'name', ''),
            'displayName': getattr(s, 'display_name', ''),
            'instanceRef': getattr(s, 'instance_ref', ''),
            'scenarioDb': getattr(s, 'scenario_db', ''),
            'requiredModules': getattr(s, 'required_modules', ''),
            'assumptions': _loads(s, 'assumptions_json', []),
            'notes': getattr(s, 'notes', ''),
        })
    return {'ok': True,
            'scenarios': sorted(rows, key=lambda r: r['name'])}
