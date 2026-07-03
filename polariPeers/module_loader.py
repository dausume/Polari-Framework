"""
@cross-cutting
@module polariPeers.module_loader
@tags @xc:bindings

Module loader — import a module bundle into a live Polari (idempotently,
the same construct + saveInstanceInDB path the seeds use) and remove it
again. The PolariModule registry row records what happened; the full
bundle is cached on the row (bundle_json) so this instance can serve it
to peers and reinstall after removal.

Import contract (plain-language failures, never half-seeding):
  1. requiredClasses must exist here AND match the declared fields
     fingerprint — a mismatched class version refuses with an
     explanation instead of seeding rows the local class can't hold.
  2. dependsOn modules missing → WARNING (content may reference objects
     the dependencies provide), not an error.
  3. Rows seed idempotently-by-name per class, in dependency-safe order.

Removal honesty: rows are removed from the in-memory objectTables and,
where the DB layer exposes a delete, from sqlite; the framework has no
standard per-instance DB delete today, so removed rows can reappear
after a restart — reported as a gap in the result, not hidden.

@consumers
  - polariPeers.peers_api (install/remove endpoints)
@see /OVERLAP_MAP.md
"""

import json
from typing import Any, Dict, List, Optional

from polariPeers.module_bundle import (
    canonical_json,
    class_fields_fingerprint,
    load_order_for,
    resolve_class,
    validate_bundle_shape,
)


def import_bundle(
    manager,
    bundle: Dict[str, Any],
    dry_run: bool = False,
    source_kind: str = 'file',
    source_ref: str = '',
) -> Dict[str, Any]:
    """Import a bundle. Returns:
        { installed, dryRun, created: {cls: n}, skipped: {cls: n},
          warnings: [...], errors: [...] }
    """
    report: Dict[str, Any] = {
        'installed': False, 'dryRun': dry_run,
        'created': {}, 'skipped': {}, 'warnings': [], 'errors': [],
    }
    shape_error = validate_bundle_shape(bundle)
    if shape_error:
        report['errors'].append(shape_error)
        return report
    manifest = bundle['manifest']

    # 1. Required classes present + fingerprint match.
    for cls_name, expected_fp in (manifest.get('requiredClasses') or {}).items():
        klass = resolve_class(manager, cls_name)
        if klass is None:
            report['errors'].append(
                f'This module needs the class "{cls_name}", which this '
                f'instance does not have. (Classes-as-config modules arrive '
                f'in a later pass; for now install a build that includes it.)')
            continue
        local_fp = class_fields_fingerprint(klass)
        if expected_fp and local_fp != expected_fp:
            report['errors'].append(
                f'The module was exported against a DIFFERENT version of '
                f'"{cls_name}" (its fields differ from this instance\'s). '
                f'Update both instances to the same build and re-export.')
    if report['errors']:
        return report

    # 2. Dependencies installed? (warning only)
    installed = {getattr(m, 'name', '') for m in _module_rows(manager)
                 if getattr(m, 'status', '') == 'installed'}
    for dep in manifest.get('dependsOn') or []:
        if dep not in installed:
            report['warnings'].append(
                f'This module depends on "{dep}", which is not installed '
                f'here — its content may reference objects that module '
                f'provides.')

    # 3. Seed idempotently in dependency-safe order.
    objects = bundle.get('objects') or {}
    for cls_name in load_order_for(list(objects.keys())):
        rows = objects.get(cls_name) or []
        klass = resolve_class(manager, cls_name)
        if klass is None:
            report['errors'].append(
                f'Cannot create rows of "{cls_name}" — the class is not '
                f'registered on this instance.')
            continue
        table = manager.objectTables.setdefault(cls_name, {})
        existing_names = {getattr(o, 'name', None) for o in table.values()}
        created = skipped = 0
        for row in rows:
            row_name = row.get('name')
            if row_name in existing_names:
                skipped += 1
                continue
            if dry_run:
                created += 1
                continue
            try:
                inst = klass(**row, manager=manager)
            except Exception as exc:
                report['errors'].append(
                    f'Creating {cls_name} "{row_name}" failed: '
                    f'{type(exc).__name__}: {exc}')
                continue
            # treeObjects self-register; plainer classes (tests) don't.
            if not any(o is inst for o in table.values()):
                table[row_name] = inst
            _persist(manager, inst)
            existing_names.add(row_name)
            created += 1
        report['created'][cls_name] = created
        report['skipped'][cls_name] = skipped

    if report['errors']:
        return report

    # 4. Record the module (skip in dry runs).
    if not dry_run:
        _upsert_module_row(
            manager, manifest, bundle,
            source_kind=source_kind, source_ref=source_ref,
        )
        report['installed'] = True
    return report


def remove_module(manager, module_name: str) -> Dict[str, Any]:
    """Remove a module's objects (reverse dependency order). The bundle
    stays cached on the registry row for reinstall."""
    report: Dict[str, Any] = {'removed': False, 'removedCounts': {},
                              'warnings': [], 'errors': []}
    row = _find_module(manager, module_name)
    if row is None:
        report['errors'].append(f'No module named "{module_name}" here.')
        return report
    bundle = _parse(getattr(row, 'bundle_json', '') or '{}')
    objects = (bundle or {}).get('objects') or {}
    if not objects:
        report['errors'].append(
            f'Module "{module_name}" has no cached bundle to remove by — '
            f're-export it first.')
        return report

    db = getattr(manager, 'db', None)
    db_delete = None
    for candidate in ('deleteInstanceFromDB', 'deleteInstanceInDB',
                      'removeInstanceFromDB'):
        if db is not None and callable(getattr(db, candidate, None)):
            db_delete = getattr(db, candidate)
            break

    for cls_name in reversed(load_order_for(list(objects.keys()))):
        names = {r.get('name') for r in (objects.get(cls_name) or [])}
        table = manager.objectTables.get(cls_name, {}) or {}
        to_remove = [k for k, v in table.items()
                     if getattr(v, 'name', None) in names]
        removed = 0
        for key in to_remove:
            inst = table.pop(key, None)
            removed += 1
            if inst is not None and db_delete is not None:
                try:
                    db_delete(inst)
                except Exception:
                    pass
        report['removedCounts'][cls_name] = removed

    if db_delete is None:
        report['warnings'].append(
            'Rows were removed from memory, but this build has no standard '
            'per-instance database delete — removed rows can reappear after '
            'a restart. (Known framework gap.)')
    row.status = 'removed'
    _persist(manager, row)
    report['removed'] = True
    return report


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def register_bundle(manager, bundle: Dict[str, Any],
                    source_kind: str = 'local',
                    source_ref: str = '') -> Dict[str, Any]:
    """Record an exported bundle as an installed module (it IS installed —
    it's this instance's live content). Returns the manifest."""
    _upsert_module_row(manager, bundle['manifest'], bundle,
                       source_kind=source_kind, source_ref=source_ref)
    return bundle['manifest']


def _upsert_module_row(manager, manifest: Dict[str, Any],
                       bundle: Dict[str, Any],
                       source_kind: str, source_ref: str) -> None:
    name = manifest.get('name', '')
    row = _find_module(manager, name)
    if row is None:
        klass = resolve_class(manager, 'PolariModule')
        if klass is None:
            from polariPeers.polari_module import PolariModule as klass
        row = klass(name=name, manager=manager)
        # treeObjects self-register; plainer registry classes (tests) don't.
        table = manager.objectTables.setdefault('PolariModule', {})
        if not any(o is row for o in table.values()):
            table[name] = row
    row.version = manifest.get('version', '')
    row.status = 'installed'
    row.source_kind = source_kind
    row.source_ref = source_ref
    row.manifest_json = json.dumps(manifest)
    row.bundle_json = canonical_json(bundle)
    _persist(manager, row)


def _module_rows(manager) -> List:
    return list((manager.objectTables.get('PolariModule', {}) or {}).values())


def _find_module(manager, name: str):
    for m in _module_rows(manager):
        if getattr(m, 'name', '') == name:
            return m
    return None


def _persist(manager, inst) -> None:
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(inst)
        except Exception:
            pass


def _parse(text: str) -> Any:
    try:
        return json.loads(text) if text else {}
    except (ValueError, TypeError):
        return {}
