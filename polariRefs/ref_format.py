"""
@module polariRefs.ref_format

The reference format (xsim-1). Extends the existing binding objectRef
SHAPE (materialsScience/component_binding.py) with an optional authority
coordinate — bare refs stay valid and mean "local":

    { kind: 'objectRef',
      authority: {instance: 'b'} | {module: 'materialsScience'},   # opt
      className: 'MaterialScaleDefinition',
      name: ... | id: ...,                       # at least one
      path: 'last_result_json.percolationThreshold',              # opt
      schemaVersion: '<hash of owner SchemaStabilityProfile>' }    # opt

`authority.module` is preferred: the topology layer resolves WHICH
instance is authoritative right now, so refs survive module
reallocation. `schemaVersion` present + mismatched → hydration refuses
naming both versions (resolver.py).

Every parse failure is an honest refusal dict {error, suggestion}; no
exceptions escape parse_ref.
"""

import hashlib
import json
import os
from typing import Any, Dict, Optional, Tuple

_AUTHORITY_KINDS = ('instance', 'module')


def is_object_ref(value: Any) -> bool:
    return isinstance(value, dict) and value.get('kind') == 'objectRef'


def is_authority_ref(value: Any) -> bool:
    """An objectRef carrying the xsim authority coordinate — the ONLY
    shape polariRefs claims; bare refs stay on the untouched
    component_binding path."""
    return is_object_ref(value) and 'authority' in value


def local_identity() -> Dict[str, str]:
    """This process's instance identity (mirrors
    polariPeers.peers_api.instance_identity — duplicated 2 lines rather
    than importing falcon into every resolver caller)."""
    iid = (os.environ.get('POLARI_INSTANCE_ID') or 'a').strip()
    name = (os.environ.get('POLARI_INSTANCE_NAME') or f'polari-{iid}').strip()
    return {'instanceId': iid, 'instanceName': name}


def parse_ref(raw: Any) -> Tuple[bool, Optional[Dict], Optional[Dict]]:
    """Normalize a raw ref dict → (ok, normalized, refusal).

    normalized = {className, name, id, path, authority, schemaVersion}
    where authority is None (local / bare) or exactly one of
    {'instance': str} / {'module': str}."""
    if not is_object_ref(raw):
        return False, None, {
            'error': "not an objectRef (need a dict with "
                     "kind='objectRef')",
            'suggestion': {'knob': 'binding.kind',
                           'action': "use kind 'objectRef'"}}
    class_name = str(raw.get('className', '') or '')
    if not class_name:
        return False, None, {
            'error': 'objectRef without className',
            'suggestion': {'knob': 'binding.className',
                           'action': 'name the target class'}}
    name = str(raw.get('name', '') or '')
    obj_id = str(raw.get('id', '') or '')
    if not name and not obj_id:
        return False, None, {
            'error': f"objectRef to {class_name} names no row "
                     "(need 'name' or 'id')",
            'suggestion': {'knob': 'binding.name',
                           'action': 'point it at an existing row'}}
    authority = raw.get('authority')
    if authority is not None:
        if not isinstance(authority, dict):
            return False, None, {
                'error': f'authority must be a dict, got '
                         f'{type(authority).__name__}',
                'suggestion': {'knob': 'binding.authority',
                               'action': "{'instance': ...} or "
                                         "{'module': ...}"}}
        keys = sorted(authority)
        if len(keys) != 1 or keys[0] not in _AUTHORITY_KINDS:
            return False, None, {
                'error': f'authority must carry exactly one of '
                         f'{_AUTHORITY_KINDS}, got {keys}',
                'suggestion': {'knob': 'binding.authority',
                               'action': "{'instance': 'b'} or "
                                         "{'module': "
                                         "'materialsScience'}"}}
        coord = str(authority[keys[0]] or '')
        if not coord:
            return False, None, {
                'error': f"authority.{keys[0]} is empty",
                'suggestion': {'knob': f'binding.authority.{keys[0]}',
                               'action': 'name the instance/module'}}
        authority = {keys[0]: coord}
    return True, {'className': class_name, 'name': name, 'id': obj_id,
                  'path': str(raw.get('path', '') or ''),
                  'authority': authority,
                  'schemaVersion':
                      str(raw.get('schemaVersion', '') or '')}, None


def authority_key(authority: Optional[Dict], resolved_instance: str = ''
                  ) -> str:
    """Canonical identity-map key part for WHERE an object lives.
    Local (bare ref, or authority resolved to this instance) → 'local';
    otherwise 'instance:<x>'. Module authorities key by the instance the
    topology resolved them to (`resolved_instance`), so instance a row 5
    and instance b row 5 never collapse."""
    if authority is None:
        return 'local'
    if resolved_instance:
        return f'instance:{resolved_instance}'
    if 'instance' in authority:
        return f"instance:{authority['instance']}"
    return f"module:{authority['module']}"   # unresolved module authority


def schema_version_of(manager, class_name: str) -> str:
    """The class's local schema version: a short sha256 over the
    canonicalized SchemaStabilityProfile.field_summary_json (the
    hashable shape — no stored hash column exists). '' when the class
    has no stabilized profile here."""
    tables = getattr(manager, 'objectTables', None) or {}
    profiles = tables.get('SchemaStabilityProfile', {}) or {}
    rows = profiles.values() if isinstance(profiles, dict) else profiles
    for row in rows:
        if getattr(row, 'subject_class', '') != class_name:
            continue
        blob = getattr(row, 'field_summary_json', '') or ''
        try:
            canonical = json.dumps(json.loads(blob), sort_keys=True)
        except (TypeError, ValueError):
            canonical = blob
        if canonical in ('', '{}'):
            return ''
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]
    return ''
