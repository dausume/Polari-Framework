"""
security.custom.security_owned — OWNER-DEFINED PERMISSIONS, the model half (op-0).

Design: AI-Notes/designs/OWNER_DEFINED_PERMISSIONS_DESIGN.md. His ask (2026-09-18): *"owner defined permissions
for some objects… Things like votes would likely be an owner defined permission, other people do not have the
permission to alter the data on their vote, they only have partial read access and only to the contents of the
vote and groups the vote corresponds to, not who specifically made that vote."*

Four calls, and nothing else is public:

    policy_for(manager, class_name)              -> the policy dict, or None (OPT-IN: None unless an ENABLED row)
    stamp_owner(manager, instance, user_info)    -> {'stamped'|'refused'|'skipped', 'why', ...} at create
    owner_verdict(manager, user_info, verb, inst)-> {'allowed', 'projected_fields', 'rule', 'why', 'knob'}
    project(instance_dict, fields)               -> the same dict narrowed to `fields` (+ 'id')

THE RULES THAT HOLD (op-0):
  * OPT-IN. A class with no enabled policy pays ONE dict lookup and behaves exactly as it did.
  * The CLASS gate decides first and is not touched here — owner-defined never widens what OTHERS may do
    beyond the class door. The one place it ADDS is the owner's floor on their OWN instance.
  * A person is their opaque Keycloak `sub` and nothing else (his rule D18-1). `actor_of()` is the resolution.
  * Security WARNS, never blocks, in a deployment: the CALLER (accessControl.owner_gate) reads the same
    off|advisory|enforce answer as the class gate. Nothing here refuses on its own; it only says what is true.

`frozen_when` GRAMMAR (op-0 supports the simple form only; op-2 widens it):

    <Class>.<field> in (value, value, …)          e.g.  VoteRecord.state in (tallied, certified)
    <Class>.<field> == value                      e.g.  Election.closed == true
    … [via <fk field>]                            e.g.  VoteRecord.state in (certified) via vote_record_id

  The related row is found in `<Class>`'s table by the value of a FOREIGN-KEY field on the instance. With no
  explicit `via`, the candidates tried in order are `<snake_case(Class)>_id`, `<lower(Class)>_id`,
  `<snake_case(Class)>` and `<lower(Class)>`; the value is matched against the related row's `id` and then its
  `name`. Values compare as lower-cased strings, so `certified`, `Certified` and `"certified"` are the same
  condition. A MALFORMED expression (or a missing class, field or fk) is NOT frozen — a policy typo must never
  silently lock every owner out of their own rows — and a SecurityEvent records it so the typo is visible.
"""
import json
import re

from security.custom.security_observe import _schedule_persist, actor_of, record  # noqa: F401  (record: bad frozen_when)

#: the policy columns, as the doors and the seed speak them
POLICY_KEYS = ('class_name', 'enabled', 'owner_verbs', 'others_verbs', 'others_fields', 'owner_visible',
               'owner_may_grant', 'grantable_verbs', 'grantee_kinds', 'frozen_when', 'transfer', 'anonymised',
               'owner_field', 'notes')

#: the column pairs: the policy dict's key -> the row's JSON-text column
_LIST_COLUMNS = {'owner_verbs': 'owner_verbs_json', 'others_verbs': 'others_verbs_json',
                 'others_fields': 'others_fields_json', 'grantable_verbs': 'grantable_verbs_json',
                 'grantee_kinds': 'grantee_kinds_json'}

_ADMIN_FALLBACK = frozenset({'admin', 'polari-admin'})


def _loads(raw, default):
    try:
        parsed = json.loads(raw or '')
        return parsed if isinstance(parsed, type(default)) else default
    except (ValueError, TypeError):
        return default


def _rows(manager, class_name):
    """Every row of the class — including the plain rows security_observe keeps for a manager that cannot
    construct tree objects (a test double). A double NEVER goes into the manager's own table: a foreign object
    there breaks the CRUDE view of the class ("PolyTyping for type SimpleNamespace could not be found")."""
    from security.custom.security_observe import _all_rows
    return _all_rows(manager, class_name)


def _admin(user_info):
    """Is the caller an administrator? The polariapps resolution when it is importable, its rule otherwise."""
    try:
        from polariapps.objects.apps_permissions._shared import caller_groups, ADMIN_ROLES
        groups, _ = caller_groups(user_info)
        return bool(ADMIN_ROLES & groups), sorted(ADMIN_ROLES & groups)
    except Exception:                                   # noqa: BLE001 — polariapps absent on this instance
        roles = set((user_info or {}).get('roles') or []) if isinstance(user_info, dict) else set()
        return bool(_ADMIN_FALLBACK & roles), sorted(_ADMIN_FALLBACK & roles)


# ---- the policy -------------------------------------------------------------------------------------------

def policy_for(manager, class_name):
    """The ENABLED policy for `class_name` as a plain dict, or None.

    None is the answer for every class on a stock instance: owner-defined permissions are opt-in per class, and
    a disabled row is the same as no row. One table lookup, one scan of a table that is empty on most
    instances — this runs on every CRUDE act."""
    if not class_name:
        return None
    for row in _rows(manager, 'OwnedClassPolicy'):
        if str(getattr(row, 'class_name', '') or getattr(row, 'name', '')) != str(class_name):
            continue
        if not bool(getattr(row, 'enabled', False)):
            return None
        pol = {'class_name': class_name,
               'enabled': True,
               'owner_visible': bool(getattr(row, 'owner_visible', False)),
               'owner_may_grant': bool(getattr(row, 'owner_may_grant', False)),
               'frozen_when': str(getattr(row, 'frozen_when', '') or ''),
               'transfer': str(getattr(row, 'transfer', 'nobody') or 'nobody'),
               'anonymised': bool(getattr(row, 'anonymised', False)),
               'owner_field': str(getattr(row, 'owner_field', 'owner') or 'owner'),
               'notes': str(getattr(row, 'notes', '') or '')}
        for key, column in _LIST_COLUMNS.items():
            pol[key] = [str(v) for v in _loads(getattr(row, column, '[]'), [])]
        return pol
    return None


def policies(manager):
    """Every policy row, enabled or not — what `GET /api/security/owned` answers."""
    out = []
    for row in _rows(manager, 'OwnedClassPolicy'):
        pol = {'class_name': str(getattr(row, 'class_name', '') or getattr(row, 'name', '')),
               'enabled': bool(getattr(row, 'enabled', False)),
               'owner_visible': bool(getattr(row, 'owner_visible', False)),
               'owner_may_grant': bool(getattr(row, 'owner_may_grant', False)),
               'frozen_when': str(getattr(row, 'frozen_when', '') or ''),
               'transfer': str(getattr(row, 'transfer', 'nobody') or 'nobody'),
               'anonymised': bool(getattr(row, 'anonymised', False)),
               'owner_field': str(getattr(row, 'owner_field', 'owner') or 'owner'),
               'notes': str(getattr(row, 'notes', '') or '')}
        for key, column in _LIST_COLUMNS.items():
            pol[key] = [str(v) for v in _loads(getattr(row, column, '[]'), [])]
        out.append(pol)
    out.sort(key=lambda p: p['class_name'])
    return out


def set_policy(manager, class_name, fields, by=''):
    """Set or replace one class's policy (the ADMIN door). Returns {'ok', 'policy'} or {'ok': False, 'refusal'}."""
    class_name = str(class_name or '').strip()
    if not class_name:
        return {'ok': False, 'refusal': 'a class name: the class whose instances get an owner'}
    fields = fields if isinstance(fields, dict) else {}
    transfer = str(fields.get('transfer', 'nobody') or 'nobody')
    from security.objects.security.OwnedClassPolicy import OwnedClassPolicy
    if transfer not in OwnedClassPolicy.TRANSFER_MODES:
        return {'ok': False, 'refusal': 'transfer: one of %s' % ', '.join(OwnedClassPolicy.TRANSFER_MODES)}
    bad = [v for v in (fields.get('owner_verbs') or []) if v not in OwnedClassPolicy.OWNER_VERBS]
    if bad:
        return {'ok': False, 'refusal': 'owner_verbs may only name %s (got %s) — `create` is the class door\'s '
                                        'business: an instance has no owner until it exists'
                                        % (', '.join(OwnedClassPolicy.OWNER_VERBS), ', '.join(bad))}
    row_fields = {
        'name': class_name, 'class_name': class_name,
        'enabled': bool(fields.get('enabled', True)),
        'owner_visible': bool(fields.get('owner_visible', False)),
        'owner_may_grant': bool(fields.get('owner_may_grant', False)),
        'frozen_when': str(fields.get('frozen_when', '') or ''),
        'transfer': transfer,
        'anonymised': bool(fields.get('anonymised', False)),
        'owner_field': str(fields.get('owner_field', 'owner') or 'owner'),
        'notes': str(fields.get('notes', '') or ''),
    }
    for key, column in _LIST_COLUMNS.items():
        default = ['read', 'update', 'delete'] if key == 'owner_verbs' else []
        row_fields[column] = json.dumps([str(v) for v in (fields.get(key) if isinstance(fields.get(key), list) else default)])
    tables = getattr(manager, 'objectTables', None)
    if tables is None:
        return {'ok': False, 'refusal': 'no manager'}
    existing = next((r for r in _rows(manager, 'OwnedClassPolicy')
                     if str(getattr(r, 'class_name', '') or getattr(r, 'name', '')) == class_name), None)
    if existing is not None:
        for key, value in row_fields.items():
            setattr(existing, key, value)
    else:
        from security.custom.security_observe import _new_row
        _new_row(manager, tables, 'OwnedClassPolicy', OwnedClassPolicy, row_fields)
    _schedule_persist(manager)
    record(manager, 'authz', 'set owned policy %s' % class_name, class_name,
           reason='owner-defined permissions %s' % ('enabled' if row_fields['enabled'] else 'disabled'),
           actor=by, outcome='allowed', would_deny=False, source='owner policy door')
    return {'ok': True, 'policy': policy_for(manager, class_name) or
            {**{k: row_fields.get(k) for k in ('class_name', 'enabled')}, 'note': 'stored but disabled'}}


# ---- the owner stamp --------------------------------------------------------------------------------------

def owner_of(manager, instance, policy=None):
    """The instance's owner `sub`, '' when there is none. `policy` saves the lookup when the caller has it."""
    if instance is None:
        return ''
    pol = policy or policy_for(manager, type(instance).__name__)
    field = (pol or {}).get('owner_field', 'owner')
    return str(getattr(instance, field, '') or '')


def stamp_owner(manager, instance, user_info):
    """Stamp `owner` on a NEWLY CREATED instance of an opted-in class. The one place an owner is written.

    Returns a stated outcome, never a bare bool:
      {'stamped': True,  'owner': <sub>, 'field': …, 'why': …}
      {'stamped': False, 'refused': True, 'why': …}    anonymous create on an owned class
      {'stamped': False, 'refused': False, 'why': …}   no policy, or the class has no owner column

    An instance with no owner has no owner-defined rule to apply, so an anonymous create on an owned class is
    REFUSED with the reason said out loud (design §2). The caller decides what a refusal costs — in advisory
    the act still runs; see accessControl.owner_gate."""
    if instance is None:
        return {'stamped': False, 'refused': False, 'why': 'no instance'}
    class_name = type(instance).__name__
    pol = policy_for(manager, class_name)
    if pol is None:
        return {'stamped': False, 'refused': False, 'rule': 'no-policy',
                'why': '%s is not an owned class — no OwnedClassPolicy row enables it' % class_name}
    field = pol['owner_field']
    if not hasattr(instance, field):
        return {'stamped': False, 'refused': False, 'rule': 'no-owner-column',
                'why': ('%s has an enabled OwnedClassPolicy but no `%s` attribute — the policy names the column '
                        'that holds the owner\'s Keycloak sub (owner_field); add the column to the class or point '
                        'the policy at the one it has' % (class_name, field))}
    sub = actor_of(user_info)
    if not sub:
        return {'stamped': False, 'refused': True, 'rule': 'anonymous-create',
                'why': ('%s is an owned class: every instance must have an owner, and this request carried no '
                        'identity (a Keycloak `sub`). Sign in, or disable the OwnedClassPolicy for %s.'
                        % (class_name, class_name)),
                'knob': 'OwnedClassPolicy[%s].enabled / POST /api/security/owned/%s' % (class_name, class_name)}
    setattr(instance, field, sub)
    return {'stamped': True, 'owner': sub, 'field': field, 'rule': 'owner-stamp',
            'why': 'owner set to the creator\'s Keycloak sub (D18-1: the sub alone, never a name)'}


# ---- frozen_when ------------------------------------------------------------------------------------------

_FROZEN_RE = re.compile(
    r'^\s*(?P<cls>[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*'
    r'(?:(?P<op_in>in)\s*\((?P<values>[^)]*)\)|(?P<op_eq>==|!=)\s*(?P<value>[^\s]+))\s*'
    r'(?:via\s+(?P<via>[A-Za-z_][A-Za-z0-9_]*)\s*)?$', re.IGNORECASE)


def _snake(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def _clean(value):
    return str(value or '').strip().strip('"').strip("'").lower()


def _related_row(manager, instance, related_class, via=''):
    """The row of `related_class` this instance points at, or None — see the module docstring's grammar."""
    candidates = [via] if via else [_snake(related_class) + '_id', related_class.lower() + '_id',
                                    _snake(related_class), related_class.lower()]
    rows = _rows(manager, related_class)
    if not rows:
        return None
    for field in candidates:
        if not field:
            continue
        key = getattr(instance, field, None)
        if key in (None, ''):
            continue
        key = str(key)
        for row in rows:
            if str(getattr(row, 'id', '')) == key or str(getattr(row, 'name', '')) == key:
                return row
    return None


def frozen(manager, instance, policy):
    """(is_frozen, why) for the policy's `frozen_when`. A malformed or unresolvable expression is NOT frozen."""
    expr = (policy or {}).get('frozen_when', '')
    if not expr:
        return False, ''
    match = _FROZEN_RE.match(expr)
    if not match:
        _bad_frozen(manager, policy, expr, 'the expression does not parse')
        return False, ''
    cls, field, via = match.group('cls'), match.group('field'), match.group('via') or ''
    row = _related_row(manager, instance, cls, via)
    if row is None:
        _bad_frozen(manager, policy, expr, 'no %s row could be resolved from this instance' % cls)
        return False, ''
    have = _clean(getattr(row, field, None))
    if match.group('op_in'):
        wanted = [_clean(v) for v in (match.group('values') or '').split(',') if _clean(v)]
        hit = have in wanted
        return hit, ('%s.%s is %s, one of (%s) — the owner keeps read and loses update/delete'
                     % (cls, field, have, ', '.join(wanted))) if hit else ''
    wanted = _clean(match.group('value'))
    hit = (have == wanted) if match.group('op_eq') == '==' else (have != wanted)
    return hit, ('%s.%s %s %s' % (cls, field, match.group('op_eq'), wanted)) if hit else ''


def _bad_frozen(manager, policy, expr, why):
    """A policy typo is visible, never silent — and it never freezes anything (it would lock owners out)."""
    try:
        record(manager, 'authz', 'bad frozen_when', str((policy or {}).get('class_name', '')),
               reason='frozen_when %r could not be evaluated: %s — treated as NOT frozen' % (expr, why),
               outcome='observed', would_deny=False, source='security_owned.frozen')
    except Exception:                                   # noqa: BLE001 — a ledger failure must not break a read
        pass


# ---- the verdict ------------------------------------------------------------------------------------------

def project(instance_dict, fields):
    """The serialised instance narrowed to `fields`. `id` always survives: a row a caller may see must stay
    addressable (an anonymised class suppresses the id in the BROADCAST instead — op-2, design §5)."""
    if not isinstance(instance_dict, dict):
        return instance_dict
    keep = set(fields or []) | {'id'}
    return {k: v for k, v in instance_dict.items() if k in keep}


def owner_verdict(manager, user_info, verb, instance, policy=None):
    """What this caller may do to THIS instance, evidence-bearing (design §3). The class gate has already run.

    {'allowed': bool,
     'projected_fields': [..] | None,      None = the whole row; a list = only these fields
     'rule': 'no-policy'|'admin'|'owner-floor'|'frozen'|'others-ceiling',
     'why': str, 'knob': str, 'class': str, 'verb': str, 'owned': bool}
    """
    class_name = type(instance).__name__ if instance is not None else ''
    pol = policy if policy is not None else policy_for(manager, class_name)
    base = {'class': class_name, 'verb': verb, 'owned': pol is not None}
    if pol is None:
        return {**base, 'allowed': True, 'projected_fields': None, 'rule': 'no-policy',
                'why': '%s is not an owned class — the class gate\'s answer stands' % (class_name or 'this class'),
                'knob': 'POST /api/security/owned/%s enables owner-defined permissions for it' % (class_name or '<Class>')}
    is_admin, via = _admin(user_info)
    if is_admin:
        return {**base, 'allowed': True, 'projected_fields': None, 'rule': 'admin', 'via': via,
                'why': 'admin role bypass (%s)' % ', '.join(via),
                'knob': 'ADMIN_ROLES (admin, polari-admin) — an administrator is outside the owner rules'}
    sub = actor_of(user_info)
    owner = owner_of(manager, instance, pol)
    knob = 'OwnedClassPolicy[%s]: owner_verbs / others_verbs / others_fields / frozen_when' % class_name
    if sub and owner and sub == owner:
        is_frozen, why_frozen = frozen(manager, instance, pol)
        if is_frozen and verb in ('update', 'delete'):
            return {**base, 'allowed': False, 'projected_fields': None, 'rule': 'frozen',
                    'why': 'you own this row, but it is frozen: %s' % why_frozen, 'knob': knob}
        if verb in pol['owner_verbs']:
            return {**base, 'allowed': True, 'projected_fields': None, 'rule': 'owner-floor',
                    'why': 'you own this row; owner_verbs grants %s' % ', '.join(pol['owner_verbs'] or [verb]),
                    'knob': knob, 'frozen': bool(is_frozen)}
        return {**base, 'allowed': False, 'projected_fields': None, 'rule': 'owner-floor',
                'why': 'you own this row, but owner_verbs is %s and does not include %s'
                       % (pol['owner_verbs'] or '[]', verb), 'knob': knob}
    # others' ceiling — never wider than the class door, which has already said yes to get here
    if verb not in pol['others_verbs']:
        return {**base, 'allowed': False, 'projected_fields': None, 'rule': 'others-ceiling',
                'why': ('this row belongs to somebody else and others_verbs is %s — %s is not among them'
                        % (pol['others_verbs'] or '[]', verb)),
                'knob': knob + (' (op-1 adds OwnerGrant: the owner sharing one instance)'
                                if pol['owner_may_grant'] else '')}
    fields = list(pol['others_fields'])
    if pol['owner_visible'] and pol['owner_field'] not in fields:
        fields.append(pol['owner_field'])
    return {**base, 'allowed': True, 'projected_fields': fields, 'rule': 'others-ceiling',
            'why': ('this row belongs to somebody else: others_verbs allows %s, and a read is projected to %s%s'
                    % (verb, fields or 'no fields at all',
                       '' if pol['owner_visible'] else ' (the owner column is dropped)')),
            'knob': knob}


def verdict_for_id(manager, user_info, class_name, object_id):
    """The door's answer for ONE instance by id: every verb, plus the fields the caller would see."""
    tables = getattr(manager, 'objectTables', None) or {}
    instance = (tables.get(class_name) or {}).get(object_id)
    if instance is None:
        instance = next((r for r in _rows(manager, class_name)
                         if str(getattr(r, 'id', '')) == str(object_id)
                         or str(getattr(r, 'name', '')) == str(object_id)), None)
    if instance is None:
        return {'ok': False, 'refusal': 'no %s instance %s on this instance of Polari' % (class_name, object_id)}
    pol = policy_for(manager, class_name)
    verdicts = {v: owner_verdict(manager, user_info, v, instance, policy=pol)
                for v in ('read', 'update', 'delete', 'events')}
    read = verdicts['read']
    return {'ok': True, 'class': class_name, 'id': str(object_id),
            'owned': pol is not None, 'policy': pol,
            'you_are_the_owner': bool(actor_of(user_info)) and actor_of(user_info) == owner_of(manager, instance, pol),
            'may': sorted(v for v, d in verdicts.items() if d['allowed']),
            'fields_you_see': read.get('projected_fields'),
            'verdicts': verdicts,
            'how': ('the class gate (AppPermissionProfile) decides first and is not shown here; these are the '
                    'OWNER rules for this one instance. `fields_you_see` null = the whole row.')}
