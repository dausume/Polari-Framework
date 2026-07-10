"""
@module polariRefs.remote_hydration

xsim-3: the shared-DB peer rung (rung 3) — the CHEAP cross-instance
read. When instances share one object DB (POLARI_SHARED_OBJECT_DB),
instance a reads instance b's rows directly by `_instance_id` — no
network hop — permitted via an APPROVED PeerAgreement.

Hydration produces a GenericRemoteObject even when the class's module
is NOT installed locally (Dustin directive 2): field names come from
the class-shape-as-data ladder — local polyTyping when installed, the
peer's polyTypedObject / _dynamic_class_registry rows otherwise, raw
columns as the honest floor (provenance names which rung answered).
Read-only: writes refuse naming xsim-4 (automated remote writes under
the lease). Never a silent None.
"""

import hashlib
import json
from typing import Any, Dict, Optional

from polariRefs.ref_format import local_identity


class GenericRemoteObject:
    """A peer instance's row: typed field dict + provenance (owning
    instance, typing source, schemaVersion state). READ-ONLY until the
    lease-path write rung (xsim-4)."""

    def __init__(self, class_name: str, authority: str,
                 fields: Dict[str, Any], provenance: Dict):
        object.__setattr__(self, '_frozen', False)
        self.polariRefClassName = class_name
        self.polariRefAuthority = authority
        self.polariRefProvenance = provenance
        self.polariRefFields = dict(fields)
        for field, value in fields.items():
            if isinstance(field, str) and field.isidentifier() \
                    and not field.startswith('polariRef'):
                setattr(self, field, value)
        object.__setattr__(self, '_frozen', True)

    def __setattr__(self, name, value):
        if getattr(self, '_frozen', False):
            raise AttributeError(
                f'GenericRemoteObject({self.polariRefClassName} @ '
                f'{self.polariRefAuthority}) is read-only — remote '
                'writes are automated under the mutation lease '
                '(xsim-4), never attribute assignment')
        object.__setattr__(self, name, value)


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def _matches_instance(agreement_name: str, target: str) -> bool:
    candidate = (agreement_name or '').strip().lower()
    target = target.strip().lower()
    return candidate in (target, f'polari-{target}') \
        or target in (candidate, candidate.replace('polari-', ''))


def peer_agreement_allows(manager, target_instance: str) -> Dict:
    """Reads of a peer's rows require an APPROVED PeerAgreement naming
    that instance (any scope — 'peer-basic' suffices for reads)."""
    ident = local_identity()
    for agreement in _rows(manager, 'PeerAgreement'):
        if getattr(agreement, 'status', '') != 'approved':
            continue
        names = (getattr(agreement, 'requester_name', ''),
                 getattr(agreement, 'approver_name', ''))
        if any(_matches_instance(n, target_instance) for n in names):
            return {'ok': True,
                    'agreement': getattr(agreement, 'agreement_id', '')
                    or getattr(agreement, 'name', ''),
                    'scope': getattr(agreement, 'scope', '')}
    return {'ok': False,
            'error': f"no approved PeerAgreement with instance "
                     f"'{target_instance}' (this is "
                     f"'{ident['instanceId']}') — peer reads are "
                     'scoped, not open',
            'suggestion': {'knob': 'the peer join flow '
                                   '(/api/peers, PeerAgreement)',
                           'action': f'enroll instance '
                                     f"'{target_instance}' and approve "
                                     'the agreement'}}


def _peer_table(manager, table_name: str, target: str) -> Optional[Dict]:
    db = getattr(manager, 'db', None)
    if db is None or not hasattr(db, 'getAllInTableForInstance'):
        return None
    try:
        result = db.getAllInTableForInstance(table_name, target)
    except Exception as e:
        return {'ok': False, 'error': f'peer read failed: {e}'}
    return result if isinstance(result, dict) else None


def _find_peer_row(table: Dict, ref) -> Optional[Dict]:
    for row in table.get('rows') or []:
        fields = dict(zip(table.get('columns') or [], row))
        if ref['id'] and str(fields.get('id', '')) == ref['id']:
            return fields
        if ref['name'] and str(fields.get('name', '')) == ref['name']:
            return fields
    return None


def _peer_schema_version(manager, class_name: str,
                         target: str) -> Optional[str]:
    """The OWNER's schema version: hash of the peer's stabilized
    profile snapshot; None when unreadable/absent."""
    table = _peer_table(manager, 'SchemaStabilityProfile', target)
    if not (table and table.get('ok')):
        return None
    for row in table.get('rows') or []:
        fields = dict(zip(table.get('columns') or [], row))
        if fields.get('subject_class') != class_name:
            continue
        blob = fields.get('field_summary_json') or ''
        try:
            canonical = json.dumps(json.loads(blob), sort_keys=True)
        except (TypeError, ValueError):
            canonical = blob
        if canonical in ('', '{}'):
            return None
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]
    return None


def _field_names_for(manager, class_name: str, target: str):
    """Class-shape-as-data ladder → (field_names|None, source)."""
    for typing_row in getattr(manager, 'objectTyping', None) or []:
        if getattr(typing_row, 'className', '') == class_name:
            names = list(getattr(typing_row, 'variableNameList', '')
                         or []) or list(getattr(typing_row,
                                                'polyTypedVarsDict', {})
                                        or {})
            if names:
                return names, 'local-polyTyping'
    registry = _peer_table(manager, '_dynamic_class_registry', target)
    if registry and registry.get('ok'):
        for row in registry.get('rows') or []:
            fields = dict(zip(registry.get('columns') or [], row))
            if fields.get('className') == class_name:
                try:
                    variables = json.loads(fields.get('variables')
                                           or '[]')
                    names = [v.get('name') if isinstance(v, dict)
                             else str(v) for v in variables]
                    if names:
                        return names, 'peer-dynamic-class-registry'
                except (TypeError, ValueError):
                    pass
    return None, 'raw-columns'


def hydrate_shared_db(manager, ref, target_instance: str) -> Dict:
    """The rung-3 read. Returns {'ok', 'object', 'provenance'} /
    {'ok': False, 'refusal'} / {'ok': False, 'fallthrough': True}
    (shared DB unavailable — the resolver names the xsim-6 rung)."""
    probe = _peer_table(manager, ref['className'], target_instance)
    if probe is None:
        return {'ok': False, 'fallthrough': True}
    if not probe.get('ok'):
        if 'shared object DB is off' in probe.get('error', ''):
            return {'ok': False, 'fallthrough': True}
        return {'ok': False, 'refusal': {
            'error': probe.get('error'),
            'rung': 'shared-db-peer'}}
    allowed = peer_agreement_allows(manager, target_instance)
    if not allowed['ok']:
        return {'ok': False, 'refusal': allowed}
    row_fields = _find_peer_row(probe, ref)
    if row_fields is None:
        return {'ok': False, 'refusal': {
            'error': f"instance '{target_instance}' has no "
                     f"{ref['className']} "
                     f"'{ref['name'] or ref['id']}'",
            'rung': 'shared-db-peer',
            'suggestion': {'knob': 'binding.name / binding.authority',
                           'action': 'point at a row the owner '
                                     'actually holds'}}}
    provenance: Dict[str, Any] = {
        'rung': 'shared-db-peer',
        'owningInstance': target_instance,
        'agreement': allowed['agreement'],
        'readOnly': 'writes land with xsim-4 (lease path)'}
    if ref['schemaVersion']:
        owner_version = _peer_schema_version(
            manager, ref['className'], target_instance)
        if owner_version and owner_version != ref['schemaVersion']:
            return {'ok': False, 'refusal': {
                'error': f"schemaVersion mismatch for "
                         f"{ref['className']}: ref carries "
                         f"'{ref['schemaVersion']}', owner instance "
                         f"'{target_instance}' has '{owner_version}'",
                'suggestion': {
                    'knob': 'SchemaStabilityProfile (owner side)',
                    'action': 'restamp the ref from the owner or '
                              'restabilize there'}}}
        if not owner_version:
            provenance['schemaVersionUnverified'] = (
                f"owner '{target_instance}' has no stabilized profile "
                f"for {ref['className']}")
    field_names, typing_source = _field_names_for(
        manager, ref['className'], target_instance)
    provenance['typedFrom'] = typing_source
    if field_names:
        typed = {k: v for k, v in row_fields.items()
                 if k in field_names or k in ('id', 'name')}
        missing = [k for k in field_names if k not in row_fields]
        if missing:
            provenance['columnsMissingVsTyping'] = missing[:10]
    else:
        typed = dict(row_fields)
    remote = GenericRemoteObject(
        ref['className'], f'instance:{target_instance}', typed,
        provenance)
    return {'ok': True, 'object': remote, 'provenance': provenance}
