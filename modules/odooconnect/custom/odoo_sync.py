"""
@module odooconnect.custom.odoo_sync

Sync engine v1 (od-4): pull FREELY, push GATED. Every run returns a
receipt dict and (when the class is in the tree) writes an
OdooSyncReceipt row — what ran, which ids changed, nothing silent.

Pull provenance on every row: 'odoo:<instance>:<model>:<id>@<write_date>'.
Idempotent by deterministic row name '<prefix>-<odoo_id>':
  - same provenance            -> skipped
  - older provenance           -> fields updated, provenance advanced
  - row with FOREIGN provenance (locally authored / other source)
                               -> CONFLICT report row, never touched
Push idempotency: the Odoo-side x_polari_ref field (created on demand;
that creation is itself a guarded write) holds the Polari row name —
found -> write, absent -> create. NO retries anywhere: a retried
create could double-post; the refusal says what to check instead.

Duck-typed over manager.objectTables; class instantiation goes through
manager.objectTypingDict[<class>].getCreateMethod() (the CRUDE path) so
bindings can name ANY tree class — a class that is not in the tree
(module off) is an honest refusal, not an import error.
"""

import json
import time

from odooconnect.custom.odoo_client import OdooHandle

PULL_PAGE_SIZE = 200
PULL_MAX_PAGES = 50


def _refuse(refusal, suggestion=None):
    out = {'ok': False, 'refusal': refusal}
    if suggestion:
        out['suggestion'] = suggestion
    return out


def _named_row(manager, class_name, name):
    table = getattr(manager, 'objectTables', {}).get(class_name, {})
    for row in table.values():
        if getattr(row, 'name', None) == name:
            return row
    return None


def _config_for(manager, binding):
    ref = getattr(binding, 'instance_ref', '')
    cfg = _named_row(manager, 'OdooInstanceConfig', ref)
    if cfg is None:
        return None, _refuse(
            f'binding "{binding.name}" names unknown instance "{ref}"',
            {'evidence': 'no OdooInstanceConfig row with that name',
             'knob': 'OdooModelBinding.instance_ref',
             'action': 'point the binding at a seeded instance '
                       '(odoo-sim / odoo-ops)'})
    return cfg, None


def _class_for(manager, class_name):
    typing = getattr(manager, 'objectTypingDict', {}).get(class_name)
    if typing is None:
        return None
    try:
        return typing.getCreateMethod()
    except Exception:  # noqa: BLE001 — treat as not-instantiable
        return None


def _direction_guard(binding, verb):
    direction = getattr(binding, 'direction', 'pull')
    if verb == 'pull' and direction not in ('pull', 'both'):
        return _refuse(
            f'binding "{binding.name}" direction is "{direction}" — '
            'pull refused',
            {'evidence': 'directions are data, not suggestions',
             'knob': f'OdooModelBinding[{binding.name}].direction',
             'action': "set direction to 'pull' or 'both' deliberately"})
    if verb == 'push' and direction not in ('push', 'both'):
        return _refuse(
            f'binding "{binding.name}" direction is "{direction}" — '
            'push refused',
            {'evidence': 'directions are data, not suggestions',
             'knob': f'OdooModelBinding[{binding.name}].direction',
             'action': "set direction to 'push' or 'both' deliberately"})
    return None


def _row_prefix(binding):
    prefix = getattr(binding, 'row_name_prefix', '') or ''
    return prefix or getattr(binding, 'odoo_model', 'odoo').replace(
        '.', '-')


def _provenance(cfg, binding, rec):
    return (f'odoo:{getattr(cfg, "name", "")}:'
            f'{getattr(binding, "odoo_model", "")}:'
            f'{rec.get("id", "")}@{rec.get("write_date", "")}')


def _write_receipt(manager, kind, binding, cfg, receipt):
    """Best-effort receipt ROW; the returned dict is authoritative."""
    cls = _class_for(manager, 'OdooSyncReceipt')
    if cls is None:
        return ''
    stamp = time.strftime('%Y%m%d-%H%M%S')
    name = f'{binding.name}-{kind}-{stamp}'
    if _named_row(manager, 'OdooSyncReceipt', name) is not None:
        name = f'{name}-{int(time.time() * 1000) % 100000}'
    cls(manager=manager, name=name, kind=kind,
        binding_name=getattr(binding, 'name', ''),
        instance_ref=getattr(cfg, 'name', ''),
        created_count=len(receipt.get('created', [])),
        updated_count=len(receipt.get('updated', [])),
        skipped_count=receipt.get('skippedCount', 0),
        conflict_count=len(receipt.get('conflicts', [])),
        receipt_json=json.dumps(receipt, default=str),
        created_at=time.strftime('%Y-%m-%dT%H:%M:%S'))
    return name


def pull(manager, binding, handle_factory=OdooHandle,
         page_size=PULL_PAGE_SIZE, max_pages=PULL_MAX_PAGES):
    """Pull freely: Odoo records -> Polari rows with provenance."""
    refusal = _direction_guard(binding, 'pull')
    if refusal:
        return refusal
    cfg, refusal = _config_for(manager, binding)
    if refusal:
        return refusal
    class_name = getattr(binding, 'polari_class', '')
    cls = _class_for(manager, class_name)
    if cls is None:
        return _refuse(
            f'class "{class_name}" is not in the object tree — is its '
            'module enabled?',
            {'evidence': f'objectTypingDict has no "{class_name}"',
             'knob': 'POLARI_MODULES',
             'action': 'enable the owning module (or fix the '
                       'binding.polari_class)'})
    try:
        field_map = json.loads(getattr(binding, 'field_map_json', '{}'))
        defaults = json.loads(getattr(binding, 'defaults_json', '{}'))
    except ValueError as exc:
        return _refuse(f'binding "{binding.name}" carries invalid '
                       f'JSON: {exc}')

    handle = handle_factory(cfg)
    prefix = _row_prefix(binding)
    model = getattr(binding, 'odoo_model', '')
    fields = sorted(set(field_map) | {'write_date'})
    created, updated, conflicts = [], [], []
    skipped = 0
    pages = 0
    while pages < max_pages:
        out = handle.search_read(model, fields=fields, limit=page_size,
                                 offset=pages * page_size, order='id')
        if not out.get('ok'):
            out.setdefault('receipt', {'pagesFetched': pages})
            return out
        records = out.get('result') or []
        pages += 1
        for rec in records:
            prov = _provenance(cfg, binding, rec)
            row_name = f'{prefix}-{rec.get("id", "")}'
            mapped = {polari_f: rec.get(odoo_f)
                      for odoo_f, polari_f in field_map.items()}
            existing = _named_row(manager, class_name, row_name)
            if existing is None:
                cls(manager=manager, name=row_name,
                    provenance_id=prov, **{**defaults, **mapped})
                created.append(row_name)
                continue
            eprov = getattr(existing, 'provenance_id', '') or ''
            own = f'odoo:{cfg.name}:{model}:'
            if not eprov.startswith(own):
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
            for polari_f, value in mapped.items():
                setattr(existing, polari_f, value)
            existing.provenance_id = prov
            updated.append(row_name)
        if len(records) < page_size:
            break
    receipt = {'ok': True, 'verb': 'pull', 'binding': binding.name,
               'instance': cfg.name, 'model': model,
               'polariClass': class_name, 'created': created,
               'updated': updated, 'skippedCount': skipped,
               'conflicts': conflicts, 'pagesFetched': pages}
    receipt['receiptRow'] = _write_receipt(manager, 'pull', binding,
                                           cfg, receipt)
    return receipt


def _ensure_external_ref_field(handle, model, ref_field, confirm=''):
    """Make sure the x_polari_ref column exists on the Odoo model.
    Reading is free; CREATING it is a write and passes the guards."""
    out = handle.execute_kw(model, 'fields_get', [[ref_field]])
    if not out.get('ok'):
        return out
    if ref_field in (out.get('result') or {}):
        return {'ok': True, 'result': 'present'}
    model_ids = handle.execute_kw(
        'ir.model', 'search', [[['model', '=', model]]], confirm=confirm)
    if not model_ids.get('ok'):
        return model_ids
    if not model_ids.get('result'):
        return _refuse(f'odoo model "{model}" not found on the server')
    made = handle.execute_kw(
        'ir.model.fields', 'create',
        [{'name': ref_field, 'model': model,
          'model_id': model_ids['result'][0], 'ttype': 'char',
          'state': 'manual',
          'field_description': 'Polari external ref (od-4 idempotency '
                               'key)'}],
        confirm=confirm)
    if not made.get('ok'):
        return made
    return {'ok': True, 'result': 'created'}


def push(manager, binding, row_names=None, confirm='',
         handle_factory=OdooHandle):
    """Push GATED: named Polari rows -> Odoo, idempotent by
    x_polari_ref. The handle's data-driven guards (read_only,
    push_enabled, operations typed phrase) run on EVERY write."""
    refusal = _direction_guard(binding, 'push')
    if refusal:
        return refusal
    cfg, refusal = _config_for(manager, binding)
    if refusal:
        return refusal
    if not row_names:
        return _refuse(
            'push needs an explicit row_names list — pushing '
            '"everything" is not a thing',
            {'evidence': 'no rows named',
             'knob': 'row_names',
             'action': 'name the Polari rows to push, deliberately'})
    class_name = getattr(binding, 'polari_class', '')
    try:
        field_map = json.loads(getattr(binding, 'field_map_json', '{}'))
    except ValueError as exc:
        return _refuse(f'binding "{binding.name}" carries invalid '
                       f'JSON: {exc}')
    handle = handle_factory(cfg)
    model = getattr(binding, 'odoo_model', '')
    ref_field = getattr(binding, 'external_ref_field', 'x_polari_ref')

    ensured = _ensure_external_ref_field(handle, model, ref_field,
                                         confirm=confirm)
    if not ensured.get('ok'):
        return ensured

    created, updated, missing = [], [], []
    for row_name in row_names:
        row = _named_row(manager, class_name, row_name)
        if row is None:
            missing.append(row_name)
            continue
        vals = {odoo_f: getattr(row, polari_f, None)
                for odoo_f, polari_f in field_map.items()}
        vals[ref_field] = row_name
        found = handle.search_read(model, domain=[[ref_field, '=',
                                                   row_name]],
                                   fields=['id'], limit=1)
        if not found.get('ok'):
            return found
        if found.get('result'):
            odoo_id = found['result'][0]['id']
            out = handle.execute_kw(model, 'write',
                                    [[odoo_id], vals], confirm=confirm)
            if not out.get('ok'):
                return out
            updated.append({'row': row_name, 'odooId': odoo_id})
        else:
            out = handle.execute_kw(model, 'create', [vals],
                                    confirm=confirm)
            if not out.get('ok'):
                return out
            created.append({'row': row_name, 'odooId': out['result']})
    receipt = {'ok': True, 'verb': 'push', 'binding': binding.name,
               'instance': cfg.name, 'model': model,
               'externalRefField': ref_field,
               'refFieldEnsured': ensured.get('result'),
               'created': created, 'updated': updated,
               'skippedCount': 0, 'conflicts': [],
               'missingRows': missing}
    receipt['receiptRow'] = _write_receipt(manager, 'push', binding,
                                           cfg, receipt)
    return receipt


def bindings_catalog(manager):
    rows = []
    for b in getattr(manager, 'objectTables', {}).get(
            'OdooModelBinding', {}).values():
        rows.append({
            'name': getattr(b, 'name', ''),
            'displayName': getattr(b, 'display_name', ''),
            'instanceRef': getattr(b, 'instance_ref', ''),
            'odooModel': getattr(b, 'odoo_model', ''),
            'polariClass': getattr(b, 'polari_class', ''),
            'direction': getattr(b, 'direction', ''),
            'fieldMap': getattr(b, 'field_map_json', '{}'),
            'externalRefField': getattr(b, 'external_ref_field', ''),
            'notes': getattr(b, 'notes', ''),
        })
    return {'ok': True, 'bindings': sorted(rows,
                                           key=lambda r: r['name'])}


def receipts_catalog(manager, limit=50):
    rows = []
    for r in getattr(manager, 'objectTables', {}).get(
            'OdooSyncReceipt', {}).values():
        rows.append({
            'name': getattr(r, 'name', ''),
            'kind': getattr(r, 'kind', ''),
            'binding': getattr(r, 'binding_name', ''),
            'instance': getattr(r, 'instance_ref', ''),
            'created': getattr(r, 'created_count', 0),
            'updated': getattr(r, 'updated_count', 0),
            'skipped': getattr(r, 'skipped_count', 0),
            'conflicts': getattr(r, 'conflict_count', 0),
            'createdAt': getattr(r, 'created_at', ''),
        })
    rows.sort(key=lambda r: r['createdAt'], reverse=True)
    return {'ok': True, 'receipts': rows[:limit]}
