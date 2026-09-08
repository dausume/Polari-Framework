"""
@module odooconnect.odoo_orders

od-4b: the ORDER REGISTRAR feed — Odoo sale.order (+ lines) pulled
into bizops ProductOrder rows so the order planner runs on the real
book, not hand-entered fixtures. The generic flat field-map pull
cannot express this shape, so the derivations live here, once:

  - LINE EXPLOSION: one ProductOrder row per sale.order.line (the
    line is the thing with a product and a quantity; the parent
    order contributes state and the promise date).
  - PRODUCT MAPPING, honestly: x_polari_ref (our own round-trip
    key) wins, then default_code (the merchant's SKU convention),
    else the row is still created with product_item_ref
    'unmapped:<name>' and the receipt lists it — the planner's
    per-order refusals then say exactly which recipes are missing.
  - unit_volume_l from Odoo product volume (m3 -> L); a missing
    volume falls back to 1.0 WITH a note on the row and a
    needsVolume entry in the receipt — never a silent guess.
  - due_days derived from commitment_date vs now (floor 0); no
    commitment_date -> the binding's defaults (or 30) plus a note.
  - state value-map: draft/sent -> requested, sale -> accepted,
    done -> done, cancel -> refused.

Provenance, idempotency, conflicts, and receipts reuse the od-4
discipline verbatim: rows are named '<prefix>-<order>-<line>',
same-provenance re-runs skip, foreign-provenance rows are conflict
reports never touched.

@consumers odooconnect.odoo_api (/api/odoo/pull-orders),
           bizops.custom.bizops_planner (reads the ProductOrder table)
"""

import json
import math
import time

from odooconnect.odoo_client import OdooHandle
from odooconnect.odoo_sync import (
    _class_for, _config_for, _direction_guard, _named_row,
    _row_prefix, _write_receipt,
)

#: sale.order.state -> bizops ORDER_STATUSES.
STATE_MAP = {'draft': 'requested', 'sent': 'requested',
             'sale': 'accepted', 'done': 'done', 'cancel': 'refused'}

ORDER_FIELDS = ['name', 'state', 'commitment_date', 'date_order',
                'partner_id', 'write_date']
LINE_FIELDS = ['order_id', 'product_id', 'product_uom_qty', 'name',
               'write_date']
PRODUCT_FIELDS = ['name', 'default_code', 'volume', 'x_polari_ref']


def _refuse(refusal, suggestion=None):
    out = {'ok': False, 'refusal': refusal}
    if suggestion:
        out['suggestion'] = suggestion
    return out


def _due_days(commitment_date, now_ts=None):
    """Whole days from now until the promise date, floored at 0;
    None when there is no promise date."""
    if not commitment_date:
        return None
    try:
        due_ts = time.mktime(time.strptime(
            str(commitment_date)[:19], '%Y-%m-%d %H:%M:%S'))
    except ValueError:
        try:
            due_ts = time.mktime(time.strptime(
                str(commitment_date)[:10], '%Y-%m-%d'))
        except ValueError:
            return None
    now_ts = time.time() if now_ts is None else now_ts
    return max(0, math.ceil((due_ts - now_ts) / 86400.0))


def _map_product(product_rec):
    """(item_ref, how) — x_polari_ref wins, then default_code, else
    an honest 'unmapped:' marker the receipt surfaces."""
    ref = (product_rec or {}).get('x_polari_ref') or ''
    if ref:
        return ref, 'x_polari_ref'
    code = (product_rec or {}).get('default_code') or ''
    if code:
        return code, 'default_code'
    name = (product_rec or {}).get('name') or 'unknown-product'
    return f'unmapped:{name}', 'unmapped'


def pull_orders(manager, binding, handle_factory=OdooHandle,
                now_ts=None):
    """Pull the sale-order book through a ProductOrder binding row.
    The binding must target polari_class ProductOrder — everything
    else about it (instance, prefix, defaults, direction) is data."""
    if getattr(binding, 'polari_class', '') != 'ProductOrder':
        return _refuse(
            f'binding "{binding.name}" targets '
            f'"{getattr(binding, "polari_class", "")}" — the order '
            'puller only fills ProductOrder',
            {'evidence': 'line explosion + state mapping are '
                         'ProductOrder-shaped derivations',
             'knob': 'OdooModelBinding.polari_class',
             'action': 'use /api/odoo/pull for flat field-map '
                       'bindings'})
    refusal = _direction_guard(binding, 'pull')
    if refusal:
        return refusal
    cfg, refusal = _config_for(manager, binding)
    if refusal:
        return refusal
    cls = _class_for(manager, 'ProductOrder')
    if cls is None:
        return _refuse(
            'ProductOrder is not in the object tree — is the bizops '
            'module enabled?',
            {'evidence': 'objectTypingDict has no "ProductOrder"',
             'knob': 'POLARI_MODULES',
             'action': 'enable bizops (it owns the order registrar)'})
    try:
        defaults = json.loads(getattr(binding, 'defaults_json', '{}'))
    except ValueError as exc:
        return _refuse(f'binding "{binding.name}" carries invalid '
                       f'JSON: {exc}')
    default_due = int(defaults.pop('due_days', 30))

    handle = handle_factory(cfg)
    orders = handle.search_read('sale.order', fields=ORDER_FIELDS,
                                order='id')
    if not orders.get('ok'):
        return orders
    lines = handle.search_read('sale.order.line', fields=LINE_FIELDS,
                               order='id')
    if not lines.get('ok'):
        return lines
    products = handle.search_read('product.product',
                                  fields=PRODUCT_FIELDS, order='id')
    if not products.get('ok'):
        return products
    orders_by_id = {o['id']: o for o in orders.get('result') or []}
    products_by_id = {p['id']: p for p in products.get('result') or []}

    prefix = _row_prefix(binding)
    created, updated, conflicts = [], [], []
    unmapped, needs_volume = [], []
    skipped = 0
    for line in lines.get('result') or []:
        order_ref = line.get('order_id')
        order_id = (order_ref[0] if isinstance(order_ref, (list, tuple))
                    else order_ref)
        order = orders_by_id.get(order_id)
        if order is None:
            continue
        product_ref = line.get('product_id')
        product_id = (product_ref[0]
                      if isinstance(product_ref, (list, tuple))
                      else product_ref)
        product = products_by_id.get(product_id)
        item_ref, mapped_by = _map_product(product)
        notes = []
        if mapped_by == 'unmapped':
            unmapped.append({'line': line.get('id'),
                             'product': (product or {}).get('name',
                                                            '?')})
            notes.append('product has no x_polari_ref/default_code '
                         '— map it in odoo or edit this row')
        volume_m3 = (product or {}).get('volume') or 0
        if volume_m3 > 0:
            unit_volume_l = round(volume_m3 * 1000.0, 3)
        else:
            unit_volume_l = 1.0
            needs_volume.append({'line': line.get('id'),
                                 'item': item_ref})
            notes.append('odoo product volume unset — planner '
                         'treats this as 1.0 L until it is')
        due = _due_days(order.get('commitment_date'), now_ts=now_ts)
        if due is None:
            due = default_due
            notes.append(f'no commitment_date — due_days defaulted '
                         f'to {default_due}')
        status = STATE_MAP.get(order.get('state', ''), 'requested')

        row_name = f'{prefix}-{order_id}-{line.get("id", "")}'
        prov = (f'odoo:{cfg.name}:sale.order.line:'
                f'{line.get("id", "")}@{line.get("write_date", "")}')
        fields = {
            'product_item_ref': item_ref,
            'variant_note': line.get('name') or '',
            'unit_volume_l': unit_volume_l,
            'quantity': int(line.get('product_uom_qty') or 0),
            'due_days': due,
            'status': status,
            'customer_note': f'odoo {order.get("name", "")} '
                             f'(mapped by {mapped_by})',
            'notes': '; '.join(notes),
        }
        existing = _named_row(manager, 'ProductOrder', row_name)
        if existing is None:
            cls(manager=manager, name=row_name, provenance_id=prov,
                **{**defaults, **fields})
            created.append(row_name)
            continue
        eprov = getattr(existing, 'provenance_id', '') or ''
        if not eprov.startswith(f'odoo:{cfg.name}:sale.order.line:'):
            conflicts.append({
                'row': row_name,
                'reason': 'existing row has foreign provenance — '
                          'not touched (delete or rename it '
                          'deliberately to re-adopt)',
                'existingProvenance': eprov})
            continue
        if eprov == prov:
            skipped += 1
            continue
        for field, value in fields.items():
            setattr(existing, field, value)
        existing.provenance_id = prov
        updated.append(row_name)

    receipt = {'ok': True, 'verb': 'pull-orders',
               'binding': binding.name, 'instance': cfg.name,
               'model': 'sale.order + sale.order.line',
               'polariClass': 'ProductOrder',
               'created': created, 'updated': updated,
               'skippedCount': skipped, 'conflicts': conflicts,
               'ordersSeen': len(orders_by_id),
               'unmappedProducts': unmapped,
               'needsVolume': needs_volume,
               'note': 'unmapped/volume-less lines were still '
                       'created, flagged on the row — the planner '
                       'answers honestly either way'}
    receipt['receiptRow'] = _write_receipt(manager, 'pull-orders',
                                           binding, cfg, receipt)
    return receipt
