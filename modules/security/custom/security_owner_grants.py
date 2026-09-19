"""
security.custom.security_owner_grants — OWNER GRANTS, the per-instance half (op-1).

Design: AI-Notes/designs/OWNER_DEFINED_PERMISSIONS_DESIGN.md §2 (the row), §3 step 3 (the verdict), §6 (the
doors and the Sharing tab). `security_owned` says what a CLASS allows; this file says what ONE owner did with
ONE of their own instances, and never more than the class allowed.

    grants_for(manager, class_name, object_id)              -> the live grants (expired ones pruned), as dicts
    grant(manager, user_info, class_name, object_id, body)  -> {'ok', 'grant'} | {'ok': False, 'refusal', 'status'}
    revoke(manager, user_info, class_name, object_id, body) -> the same shape
    match(manager, user_info, class_name, object_id)        -> {'verbs', 'fields', 'ids'} for THIS caller
    sharing(manager, user_info, class_name, object_id)      -> the Sharing tab's whole answer (§6)

WHAT A GRANT CAN AND CANNOT DO. It cannot widen the class door: `crude_permission_gate` decided C × V for the
grantee's groups before any instance was resolved, and nothing here runs until that said yes. Inside that, a
grant restores a verb the class's `others_verbs` withheld, and widens a projected read by unioning its `fields`
with `others_fields`. It never touches the owner floor (the owner already has `owner_verbs`), and a grant to
YOURSELF is refused rather than stored, because it would be the owner floor written down twice.

EXPIRY is checked on every verdict, not only on the prune: a grant is dead the instant `valid_until` passes,
and the pruning that happens on the next read of the instance's grants is housekeeping, not the mechanism.

A person is their Keycloak `sub` and nothing else (D18-1). A group grant names a Keycloak GROUP; the two live
in separate columns so a screen can never shorten a group name as if it were a subject id — see OwnerGrant.
"""
import json
import time

from security.custom.security_observe import _schedule_persist, actor_of, looks_like_sub, record

#: the row's dedup key is class|id|kind|grantee — one row per grantee per instance, rewritten rather than doubled
GRANT_TABLE = 'OwnerGrant'
#: a grant body may not carry more fields than this; a projection is a named subset, not a second data model
MAX_GRANT_FIELDS = 100
#: the longest a single grant may be handed out for with no expiry stated — nothing is capped, but the answer
#: SAYS that an open-ended grant is open-ended, so nobody discovers it years later by accident
NO_EXPIRY_NOTE = 'no expiry: this grant stands until somebody revokes it'


def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _rows(manager, class_name=GRANT_TABLE):
    from security.custom.security_observe import _all_rows
    return _all_rows(manager, class_name)


def _loads(raw, default):
    try:
        parsed = json.loads(raw or '')
        return parsed if isinstance(parsed, type(default)) else default
    except (ValueError, TypeError):
        return default


def _parse_instant(value):
    """An ISO-8601 UTC instant as epoch seconds, or None when it is absent or unreadable.

    Unreadable is NOT "expired": a typo in `valid_until` must not silently revoke a grant the owner believes
    they made. It is reported by `grant()` at write time, which is where a person can still fix it."""
    text = str(value or '').strip()
    if not text:
        return None
    text = text.replace('Z', '+00:00')
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:                                   # noqa: BLE001
        return None


def expired(row, now=None):
    """(is_expired, why). '' or an unreadable instant is NOT expired — see `_parse_instant`."""
    raw = str(getattr(row, 'valid_until', '') or '').strip()
    if not raw:
        return False, ''
    ts = _parse_instant(raw)
    if ts is None:
        return False, 'valid_until %r could not be read as an instant — treated as NO expiry' % raw
    if ts <= (now if now is not None else time.time()):
        return True, 'expired at %s' % raw
    return False, ''


def grantee_of(row):
    """The design's single `grantee` value, read back out of the two columns that actually hold it."""
    kind = str(getattr(row, 'grantee_kind', '') or '')
    return str((getattr(row, 'grantee_sub', '') if kind == 'person' else getattr(row, 'grantee_group', '')) or '')


def grant_dict(row):
    ok_expired, why_expired = expired(row)
    return {
        'id': str(getattr(row, 'id', '') or ''),
        'name': str(getattr(row, 'name', '') or ''),
        'class_name': str(getattr(row, 'class_name', '') or ''),
        'object_id': str(getattr(row, 'object_id', '') or ''),
        'grantee_kind': str(getattr(row, 'grantee_kind', '') or ''),
        'grantee': grantee_of(row),
        'grantee_group': str(getattr(row, 'grantee_group', '') or ''),
        'grantee_sub': str(getattr(row, 'grantee_sub', '') or ''),
        'verbs': [str(v) for v in _loads(getattr(row, 'verbs_json', '[]'), [])],
        'fields': [str(f) for f in _loads(getattr(row, 'fields_json', '[]'), [])],
        'valid_until': str(getattr(row, 'valid_until', '') or ''),
        'granted_by': str(getattr(row, 'granted_by', '') or ''),
        'granted_at': str(getattr(row, 'granted_at', '') or ''),
        'expired': bool(ok_expired),
        'why': why_expired or (NO_EXPIRY_NOTE if not getattr(row, 'valid_until', '') else ''),
        'notes': str(getattr(row, 'notes', '') or ''),
    }


# ---- reads ------------------------------------------------------------------------------------------------

def _instance_rows(manager, class_name, object_id):
    return [r for r in _rows(manager)
            if str(getattr(r, 'class_name', '')) == str(class_name)
            and str(getattr(r, 'object_id', '')) == str(object_id)]


def _delete(manager, row):
    """Take one grant row out of the tree (or out of the test-double fallback). Never raises."""
    name = str(getattr(row, 'name', '') or '')
    try:
        manager.deleteTreeNode(className=GRANT_TABLE, nodePolariId=getattr(row, 'id', ''))
        return True
    except Exception:                                   # noqa: BLE001
        pass
    try:
        table = (getattr(manager, 'objectTables', None) or {}).get(GRANT_TABLE) or {}
        for key, value in list(table.items()):
            if value is row:
                table.pop(key, None)
                return True
    except Exception:                                   # noqa: BLE001
        pass
    try:
        from security.custom.security_observe import _FALLBACK
        _FALLBACK.get(id(getattr(manager, 'objectTables', None) or {}), {}).get(GRANT_TABLE, {}).pop(name, None)
        return True
    except Exception:                                   # noqa: BLE001
        return False


def prune_expired(manager, class_name='', object_id=''):
    """Drop every grant whose `valid_until` has passed. Returns the names dropped — evidence, not a count."""
    dropped = []
    for row in list(_rows(manager)):
        if class_name and str(getattr(row, 'class_name', '')) != str(class_name):
            continue
        if object_id and str(getattr(row, 'object_id', '')) != str(object_id):
            continue
        gone, why = expired(row)
        if not gone:
            continue
        name = str(getattr(row, 'name', '') or '')
        if _delete(manager, row):
            dropped.append(name)
            record(manager, 'authz', 'owner grant expired', name,
                   reason='%s — an expired grant decides nothing and is pruned on the next read' % why,
                   actor=str(getattr(row, 'granted_by', '') or ''), outcome='observed', would_deny=False,
                   source='security_owner_grants.prune_expired')
    if dropped:
        _schedule_persist(manager)
    return dropped


def grants_for(manager, class_name, object_id, prune=True):
    """Every LIVE grant on one instance, expired rows pruned first (design §2: expiry removes it)."""
    if prune:
        prune_expired(manager, class_name, object_id)
    out = [grant_dict(r) for r in _instance_rows(manager, class_name, object_id)]
    out = [g for g in out if not g['expired']]
    out.sort(key=lambda g: (g['grantee_kind'], g['grantee']))
    return out


def _caller_groups(user_info):
    try:
        from polariapps.objects.apps_permissions._shared import caller_groups
        groups, _ = caller_groups(user_info)
        return set(groups)
    except Exception:                                   # noqa: BLE001 — polariapps absent on this instance
        if not isinstance(user_info, dict):
            return set()
        raw = (user_info.get('raw_claims') or {}).get('groups') or user_info.get('groups') or user_info.get('roles') or []
        return {str(g).lstrip('/') for g in raw if str(g).strip()}


def match(manager, user_info, class_name, object_id):
    """What the grants on THIS instance give THIS caller: {'verbs', 'fields', 'ids', 'why'}.

    Empty verbs = no grant names them. Expired grants are skipped here too, so a grant stops deciding the
    instant it expires rather than at the next prune."""
    sub = actor_of(user_info)
    groups = _caller_groups(user_info)
    verbs, fields, ids, why = set(), [], [], []
    for row in _instance_rows(manager, class_name, object_id):
        gone, _ = expired(row)
        if gone:
            continue
        kind = str(getattr(row, 'grantee_kind', '') or '')
        if kind == 'person':
            if not sub or str(getattr(row, 'grantee_sub', '') or '') != sub:
                continue
        elif kind == 'group':
            if str(getattr(row, 'grantee_group', '') or '') not in groups:
                continue
        else:
            continue
        item = grant_dict(row)
        verbs |= set(item['verbs'])
        for f in item['fields']:
            if f not in fields:
                fields.append(f)
        ids.append(item['id'] or item['name'])
        why.append('%s grant to %s %s' % (item['class_name'], kind, item['grantee'][:8] if kind == 'person' else item['grantee']))
    return {'verbs': sorted(verbs), 'fields': fields, 'ids': ids, 'why': '; '.join(why)}


# ---- the write half ---------------------------------------------------------------------------------------

def _class_fields(manager, class_name):
    """The class's own field names, as the typing knows them — '' when this instance cannot say.

    A grant may only name fields the class HAS: a projection is a narrowing of a real row, and a grant naming
    `salary` on a class with no such column is a typo that would silently grant nothing."""
    typing = (getattr(manager, 'objectTypingDict', None) or {}).get(class_name)
    for attr in ('classAttributes', 'variables', 'fieldNames'):
        got = getattr(typing, attr, None)
        if isinstance(got, dict) and got:
            return set(got)
        if isinstance(got, (list, tuple, set)) and got:
            return {str(g) for g in got}
    inst = ((getattr(manager, 'objectTables', None) or {}).get(class_name) or {})
    for row in inst.values():
        return {k for k in vars(row) if not k.startswith('_')}
    for row in _rows(manager, class_name):
        return {k for k in vars(row) if not k.startswith('_')}
    return set()


def _refusal(why, status=400, **extra):
    return {'ok': False, 'refusal': why, 'status': status, **extra}


def may_grant(manager, user_info, class_name, instance, policy=None):
    """(allowed, why, policy) — may THIS caller write grants on THIS instance? The owner, or an administrator.

    The refusals are separate on purpose: "the class does not allow sharing at all" and "you are not the owner
    of this row" are different facts and a person acts on them differently."""
    from security.custom.security_owned import _admin, owner_of, policy_for
    pol = policy if policy is not None else policy_for(manager, class_name)
    if pol is None:
        return False, ('%s is not an owned class: no enabled OwnedClassPolicy names it, so no instance of it '
                       'has an owner and there is nobody to share it' % class_name), None
    if not pol.get('owner_may_grant'):
        return False, ('%s does not allow per-instance sharing: OwnedClassPolicy[%s].owner_may_grant is false '
                       '(a ballot is the design\'s example of a class that never has a grant)'
                       % (class_name, class_name)), pol
    is_admin, via = _admin(user_info)
    if is_admin:
        return True, 'admin role bypass (%s)' % ', '.join(via), pol
    sub = actor_of(user_info)
    if not sub:
        return False, 'sign in first: a grant is made BY an owner, and this request carries no Keycloak sub', pol
    owner = owner_of(manager, instance, pol)
    if not owner:
        return False, ('this instance carries no owner, so nobody can share it — it was created before the '
                       'policy was enabled, or while the gate was advisory and the create was anonymous'), pol
    if owner != sub:
        return False, 'only the OWNER of this row may share it, and this row belongs to somebody else', pol
    return True, 'you own this row and %s allows its owner to share it' % class_name, pol


def grant(manager, user_info, class_name, object_id, body):
    """Write ONE grant. Every bound the class set is checked here; the row class checks none of them."""
    from security.custom.security_owned import instance_of
    from security.objects.security.OwnerGrant import OwnerGrant
    body = body if isinstance(body, dict) else {}
    instance = instance_of(manager, class_name, object_id)
    if instance is None:
        return _refusal('no %s instance %s on this instance of Polari' % (class_name, object_id), 404)
    allowed, why, pol = may_grant(manager, user_info, class_name, instance, None)
    if not allowed:
        return _refusal(why, 403 if pol is not None else 400)

    kind = str(body.get('grantee_kind') or '').strip().lower()
    kinds = pol.get('grantee_kinds') or []
    if kind not in OwnerGrant.GRANTEE_KINDS:
        return _refusal('grantee_kind: one of %s' % ', '.join(OwnerGrant.GRANTEE_KINDS))
    if kind not in kinds:
        return _refusal('OwnedClassPolicy[%s].grantee_kinds is %s — this class does not allow a %s grant'
                        % (class_name, kinds or '[]', kind))
    grantee = str(body.get('grantee') or '').strip()
    if not grantee:
        return _refusal('grantee: the Keycloak GROUP name, or the person\'s Keycloak `sub` — never a username '
                        'and never an e-mail (his rule D18-1)')
    if kind == 'person':
        if not looks_like_sub(grantee):
            return _refusal('grantee %r is not a Keycloak subject id (8-4-4-4-12 hex). A person is shared with '
                            'by their `sub` alone — names and e-mails live in Keycloak and stay there (D18-1); '
                            'GET /api/security/people/{sub} resolves one for a screen at render time.' % grantee)
        if grantee == actor_of(user_info):
            return _refusal('a grant to YOURSELF is the owner floor written down twice — you already hold '
                            'owner_verbs %s on your own rows' % (pol.get('owner_verbs') or []))
    elif '/' in grantee or ' ' in grantee:
        return _refusal('grantee %r must be a plain Keycloak GROUP name (no slashes, no spaces) — a group path '
                        'is not a group name' % grantee)

    verbs = body.get('verbs')
    if not isinstance(verbs, list) or not verbs:
        return _refusal('verbs: a non-empty list ⊆ OwnedClassPolicy[%s].grantable_verbs %s'
                        % (class_name, pol.get('grantable_verbs') or []))
    verbs = [str(v).strip() for v in verbs if str(v).strip()]
    bad = [v for v in verbs if v not in (pol.get('grantable_verbs') or [])]
    if bad:
        return _refusal('verbs %s are not in OwnedClassPolicy[%s].grantable_verbs %s — an owner may only share '
                        'what the class made shareable' % (', '.join(bad), class_name, pol.get('grantable_verbs') or []))

    fields = body.get('fields') or []
    if not isinstance(fields, list):
        return _refusal('fields: a list of the class\'s own field names (an empty list = the class\'s '
                        'others_fields projection, unchanged)')
    fields = [str(f).strip() for f in fields if str(f).strip()]
    if len(fields) > MAX_GRANT_FIELDS:
        return _refusal('fields names %d columns; %d is the most one grant may carry' % (len(fields), MAX_GRANT_FIELDS))
    known = _class_fields(manager, class_name)
    if known:
        unknown = [f for f in fields if f not in known]
        if unknown:
            return _refusal('fields %s are not columns of %s — a grant narrows a real row, it cannot invent one'
                            % (', '.join(sorted(unknown)), class_name), 400, knownFields=sorted(known))
    if pol.get('anonymised') and pol.get('owner_field') in fields:
        return _refusal('%s is an ANONYMISED class: its owner column (%s) may not be granted to anybody — '
                        'hiding the owner is the whole point of the policy'
                        % (class_name, pol.get('owner_field')))

    valid_until = str(body.get('valid_until') or '').strip()
    if valid_until and _parse_instant(valid_until) is None:
        return _refusal('valid_until %r is not an ISO-8601 instant (2026-10-01T00:00:00Z). An unreadable expiry '
                        'is refused HERE rather than treated as "never expires" once the row is written'
                        % valid_until)
    if valid_until:
        gone, _ = expired(type('_probe', (), {'valid_until': valid_until})())
        if gone:
            return _refusal('valid_until %r is already in the past — that is a revoke, not a grant' % valid_until)

    by = actor_of(user_info)
    name = '%s|%s|%s|%s' % (class_name, object_id, kind, grantee)
    fields_row = {
        'name': name[:200], 'class_name': class_name, 'object_id': str(object_id),
        'grantee_kind': kind,
        'grantee_group': grantee if kind == 'group' else '',
        'grantee_sub': grantee if kind == 'person' else '',
        'verbs_json': json.dumps(sorted(set(verbs))),
        'fields_json': json.dumps(fields),
        'valid_until': valid_until,
        'granted_by': by, 'granted_at': _now(),
        'notes': str(body.get('notes') or '')[:400],
    }
    existing = next((r for r in _instance_rows(manager, class_name, object_id)
                     if str(getattr(r, 'name', '')) == fields_row['name']), None)
    replaced = existing is not None
    if replaced:
        for key, value in fields_row.items():
            setattr(existing, key, value)
        row = existing
    else:
        from security.custom.security_observe import _new_row
        row = _new_row(manager, getattr(manager, 'objectTables', None) or {}, GRANT_TABLE, OwnerGrant, fields_row)
    _schedule_persist(manager)
    from security.custom.security_owned import event_target
    record(manager, 'authz', 'owner grant %s' % ('replaced' if replaced else 'created'),
           event_target(manager, class_name, object_id, pol),
           reason='the owner shared this instance with a %s: verbs %s%s'
                  % (kind, ', '.join(sorted(set(verbs))), (' until %s' % valid_until) if valid_until else ' (no expiry)'),
           actor=by, outcome='allowed', would_deny=False, source='security_owner_grants.grant')
    return {'ok': True, 'created': not replaced, 'replaced': replaced, 'grant': grant_dict(row),
            'bounds': {'grantable_verbs': pol.get('grantable_verbs') or [],
                       'grantee_kinds': pol.get('grantee_kinds') or [],
                       'others_fields': pol.get('others_fields') or []},
            'how': ('a grant NEVER widens the class door: crude_permission_gate decides %s × verb for the '
                    'grantee\'s groups first, and this only narrows-then-restores inside that answer'
                    % class_name)}


def revoke(manager, user_info, class_name, object_id, body):
    """Take one grant back. The owner (or an administrator); the same authority that wrote it."""
    from security.custom.security_owned import event_target, instance_of
    body = body if isinstance(body, dict) else {}
    instance = instance_of(manager, class_name, object_id)
    if instance is None:
        return _refusal('no %s instance %s on this instance of Polari' % (class_name, object_id), 404)
    allowed, why, pol = may_grant(manager, user_info, class_name, instance, None)
    if not allowed:
        return _refusal(why, 403 if pol is not None else 400)
    kind = str(body.get('grantee_kind') or '').strip().lower()
    grantee = str(body.get('grantee') or '').strip()
    wanted = str(body.get('name') or body.get('id') or '').strip()
    if not wanted and not (kind and grantee):
        return _refusal('say WHICH grant: {"grantee_kind": "person"|"group", "grantee": "<sub or group>"}, or '
                        '{"name": "<the grant row\'s name>"}')
    target = None
    for row in _instance_rows(manager, class_name, object_id):
        item = grant_dict(row)
        if wanted and wanted in (item['name'], item['id']):
            target = row
            break
        if kind and grantee and item['grantee_kind'] == kind and item['grantee'] == grantee:
            target = row
            break
    if target is None:
        return _refusal('no such grant on %s %s — GET the same path lists the ones there are'
                        % (class_name, object_id), 404)
    item = grant_dict(target)
    _delete(manager, target)
    _schedule_persist(manager)
    record(manager, 'authz', 'owner grant revoked', event_target(manager, class_name, object_id, pol),
           reason='the owner took back the %s grant (verbs %s)' % (item['grantee_kind'], ', '.join(item['verbs'])),
           actor=actor_of(user_info), outcome='allowed', would_deny=False, source='security_owner_grants.revoke')
    return {'ok': True, 'revoked': item, 'remaining': grants_for(manager, class_name, object_id)}


# ---- the Sharing tab (design §6) --------------------------------------------------------------------------

#: the ONE configured table the Sharing tab renders. It is DATA, not a component: `class-rows-table` already
#: takes `className` / `columns` / `filterField` / `filterValue` / `columnFormats`, so a per-instance grants
#: table needs no Angular work — only a per-instance surface to hang it on, which is what op-1 could not find.
SHARING_TABLE_COLUMNS = ('grantee_kind,grantee_group,grantee_sub,verbs_json,fields_json,valid_until,'
                         'granted_by,granted_at,notes')
#: the two columns that hold a Keycloak `sub` and nothing else, so `person` (§54) is safe on both of them.
#: `grantee_group` is deliberately NOT one: the format shortens a cell to 8 characters, which would render
#: `household-members` as `househol`.
SHARING_TABLE_FORMATS = 'granted_by:person,grantee_sub:person'


def sharing_tab(class_name, object_id):
    """The configured table definition for one instance's Sharing tab — the same shape `module_pages_seed._table`
    emits, with the per-instance filter filled in. A frontend renders THIS; it does not build a grants view."""
    return {
        'id': 'owner-grants-%s' % str(object_id)[:40],
        'index': 0, 'type': 'component', 'rowSegmentsUsed': 12, 'gridColumnStart': None,
        'title': 'Sharing — who else this %s is shared with, and until when' % class_name,
        'visible': True, 'collapsed': False, 'cssClass': '',
        'componentProps': {'componentName': 'class-rows-table',
                           'inputs': {'className': GRANT_TABLE, 'columns': SHARING_TABLE_COLUMNS,
                                      'maxRows': 0, 'columnFormats': SHARING_TABLE_FORMATS,
                                      # class-rows-table's filter is an EXACT CRUDE match on one field, so the
                                      # per-instance scope is `object_id`, not a prefix of the composite name.
                                      'filterField': 'object_id',
                                      'filterValue': str(object_id)}},
        'item': None, 'nestedRows': [],
    }


def sharing(manager, user_info, class_name, object_id):
    """Everything the Sharing tab needs in ONE answer: the grants, the bounds, whether THIS caller may share,
    and the configured table that renders it (design §6 — no new component, nothing raw)."""
    from security.custom.security_owned import instance_of, policy_for
    instance = instance_of(manager, class_name, object_id)
    if instance is None:
        return _refusal('no %s instance %s on this instance of Polari' % (class_name, object_id), 404)
    pol = policy_for(manager, class_name)
    allowed, why, _pol = may_grant(manager, user_info, class_name, instance, pol)
    return {
        'ok': True, 'class': class_name, 'id': str(object_id),
        'owned': pol is not None,
        'show_tab': bool(pol and pol.get('owner_may_grant')),
        'you_may_share': bool(allowed), 'why': why,
        'grants': grants_for(manager, class_name, object_id),
        'yours': match(manager, user_info, class_name, object_id),
        'bounds': {'owner_may_grant': bool(pol and pol.get('owner_may_grant')),
                   'grantable_verbs': (pol or {}).get('grantable_verbs') or [],
                   'grantee_kinds': (pol or {}).get('grantee_kinds') or [],
                   'others_verbs': (pol or {}).get('others_verbs') or [],
                   'others_fields': (pol or {}).get('others_fields') or [],
                   'fields': sorted(_class_fields(manager, class_name))},
        'table': sharing_tab(class_name, object_id),
        'how': ('the Sharing tab is a CONFIGURED table over OwnerGrant filtered to this instance — `table` above '
                'is that definition, ready to render. A class whose policy forbids grants has no tab at all '
                '(`show_tab` false), which is why a ballot never shows one.'),
    }
