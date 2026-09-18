"""
security.custom.security_claims — SELF-CLAIMABLE ROLES (his words, 2026-09-18):

    "I see no way, upon registering, to simply assign myself a role in the Polari interface. Or a way to go from
     Polari to Keycloak to grant oneself permissions that anyone can just self-claim. It should not be the case
     all roles can be taken by anyone, but self-proclaimable roles should be a thing, especially in dev mode."

A role IS a Keycloak group (the permission model reads the `groups` claim — polariapps…_shared.caller_groups), so
claiming a role = putting yourself into that group. This module is the POLICY half — which roles may be taken, and
by whom. `security.custom.kc_admin` is the mechanism half; it is never consulted about whether a claim is allowed.

The rule, one paragraph (D17-5 in ISLE_HARDENING_PLAN §17b):

  * DEV posture  — every RolePrototype row is claimable, in any state (prototype / concreted / enforced), unless an
    admin explicitly said no (`POST /api/security/observe/roles/<name> {"self_claimable": false}`, which lands in the
    knob's `claim_denied` list because a bool column cannot tell "never decided" from "decided no"). Plus whatever
    the knob's `claimable_groups` names. That is the whole point of a dev build: try the product as a journalist
    without finding an administrator first.
  * PRODUCTION   — only RolePrototype rows flagged `self_claimable: true`, plus the knob's `claimable_groups`.
    Nothing is claimable by default.
  * NEVER, in either posture — ADMIN_ROLES ({'admin', 'polari-admin'}), the Keycloak groups "Polari Administrators"
    and "Polari Developers", and any group whose name starts with `polari-` (those read as realm roles / built-in
    Polari groups) unless it is a RolePrototype the admin flagged claimable. Self-service stops at the point where
    it would hand somebody the keys.
  * The caller must be AUTHENTICATED. An anonymous caller gets nothing and claims nothing (401) — a claim has to be
    attached to a Keycloak `sub`.

Everything here is evidence-bearing: a refusal says which rule refused, so a person can act on it.

PII RULE (his, 2026-09-18) — Keycloak exists to keep personal data AWAY from Polari. Every row and event this arc
writes identifies the person ONLY by the opaque Keycloak `sub`: no preferred_username, no e-mail, no display name.
The `caller()` helper still reads a username because other callers want it for a UI echo, but nothing in this module
PERSISTS it, and `_record()` writes the sub.
"""
from moduleService import posture as _posture

from security.custom import kc_admin
from security.custom import security_observe as _observe

# groups that are the administration of the instance itself — never self-service, in any posture
NEVER_CLAIMABLE_GROUPS = ('Polari Administrators', 'Polari Developers')
# a name shaped like a Polari realm role / built-in group: reserved unless a prototype row deliberately opens it
RESERVED_PREFIX = 'polari-'


def _admin_roles():
    try:
        from polariapps.objects.apps_permissions._shared import ADMIN_ROLES
        return set(ADMIN_ROLES)
    except Exception:
        return {'admin', 'polari-admin'}


def caller(user_info):
    """(sub, username, groups) for the caller — ('', '', set()) when there is nobody."""
    if not isinstance(user_info, dict):
        return '', '', set()
    sub = str(user_info.get('sub') or '')
    username = str(user_info.get('preferred_username') or user_info.get('username') or sub or '')
    try:
        from polariapps.objects.apps_permissions._shared import caller_groups
        groups, _ = caller_groups(user_info)
    except Exception:
        groups = set(str(r) for r in (user_info.get('roles') or []))
        raw = user_info.get('raw_claims') or {}
        if isinstance(raw.get('groups'), list):
            groups |= {str(g).lstrip('/') for g in raw['groups']}
    return sub, username, set(groups)


def is_admin(user_info):
    _sub, _u, groups = caller(user_info)
    return bool(_admin_roles() & groups) or bool({g for g in groups} & set(NEVER_CLAIMABLE_GROUPS))


def forbidden_reason(role, flagged_prototypes=()):
    """Why this role may NEVER be self-claimed, or '' when the blanket bans do not touch it.
    `flagged_prototypes` = the prototype roles an admin explicitly flagged self_claimable: only those may carry a
    reserved `polari-*` name (a dev-posture free-for-all must not hand out realm-role-shaped groups)."""
    name = (role or '').strip()
    if not name:
        return 'a role name is required'
    low = name.lower()
    if low in {r.lower() for r in _admin_roles()}:
        return f'{name} is an administrator role — administrator roles are never self-claimable'
    if low in {g.lower() for g in NEVER_CLAIMABLE_GROUPS}:
        return f'{name} administers this instance — it is never self-claimable'
    if low.startswith(RESERVED_PREFIX) and low not in {str(n).lower() for n in flagged_prototypes}:
        return (f'{name} is a reserved Polari group name (it reads as a realm role); only a RolePrototype an admin '
                f'has flagged self_claimable can carry a {RESERVED_PREFIX}* name')
    return ''


def _prototype_claimable(p, dev, denied):
    """(claimable, why) for one RolePrototype dict, before the blanket bans."""
    if p['name'] in denied:
        return False, 'an administrator marked this role not self-claimable'
    if bool(p.get('self_claimable')):
        return True, 'flagged self_claimable'
    if dev:
        return True, 'dev posture: every prototype role is claimable unless an admin says otherwise'
    return False, 'production posture: only roles flagged self_claimable may be taken'


def claimable_roles(manager, user_info, env=None):
    """[{role, title, description, source, held, state, why}] — every role THIS caller may claim or release, plus the
    ones they already hold. Anonymous callers get an empty list (nothing is claimable without an identity)."""
    sub, _username, groups = caller(user_info)
    if not sub:
        return []
    dev = _posture.is_dev(env)
    denied = set(_observe.claim_denied_roles())
    protos = _observe.prototypes(manager)
    flagged = [p['name'] for p in protos if bool(p.get('self_claimable')) and p['name'] not in denied]
    out = []
    seen = set()
    for p in protos:
        ok, why = _prototype_claimable(p, dev, denied)
        if not ok:
            continue
        ban = forbidden_reason(p['name'], flagged)
        if ban:
            continue
        seen.add(p['name'])
        out.append({'role': p['name'], 'title': p.get('title') or p['name'], 'description': p.get('description') or '',
                    'source': 'prototype', 'state': p.get('state') or 'prototype', 'held': p['name'] in groups, 'why': why})
    for g in (_observe.claimable_groups() or []):
        if g in seen or forbidden_reason(g, flagged):
            continue
        seen.add(g)
        out.append({'role': g, 'title': g, 'description': 'a Keycloak group the operator opened for self-service',
                    'source': 'knob', 'state': '', 'held': g in groups, 'why': 'listed in the claimable_groups knob'})
    out.sort(key=lambda r: r['role'])
    return out


def may_claim(manager, user_info, role, env=None):
    """(allowed, why, entry) — the single decision the claim/release routes ask for."""
    sub, _u, _g = caller(user_info)
    if not sub:
        return False, 'sign in first: a role is claimed for a Keycloak account, and you have none here', None
    role = (role or '').strip().lstrip('/')
    denied = set(_observe.claim_denied_roles())
    ban = forbidden_reason(role, [p['name'] for p in _observe.prototypes(manager)
                                  if bool(p.get('self_claimable')) and p['name'] not in denied])
    if ban:
        return False, ban, None
    entry = next((r for r in claimable_roles(manager, user_info, env=env) if r['role'].lower() == role.lower()), None)
    if entry is None:
        where = 'dev' if _posture.is_dev(env) else 'production'
        return False, (f'{role} is not self-claimable on this instance ({where} posture). Roles become claimable by '
                       f'being a prototype role (dev), by being flagged self_claimable, or by being listed in the '
                       f'claimable_groups knob — an administrator does either.'), None
    return True, entry['why'], entry


def held_roles(user_info, manager=None, env=None):
    """The claimable roles the caller already holds, from the token's own groups (no Keycloak round trip)."""
    _sub, _u, groups = caller(user_info)
    return sorted(groups & {r['role'] for r in claimable_roles(manager, user_info, env=env)}) if manager is not None else sorted(groups)


# ---- carrying a decision out -----------------------------------------------------------------------------------------

REFRESH_NOTE = 'sign in again or refresh your session for the new group to appear in your token'


def claim(manager, user_info, role, env=None):
    """Put the caller into the role's Keycloak group, creating the group when a prototype role has none yet."""
    allowed, why, _entry = may_claim(manager, user_info, role, env=env)
    if not allowed:
        return {'ok': False, 'refusal': why, 'status': 403}
    ok, cfg_why = kc_admin.configured(env)
    if not ok:
        return {'ok': False, 'refusal': cfg_why, 'status': 503}
    sub, _username, _g = caller(user_info)
    role = role.strip().lstrip('/')
    g = kc_admin.create_group(role, env=env)              # idempotent: finds it, or makes it
    if not g.get('ok'):
        return {'ok': False, 'refusal': g.get('refusal', 'could not resolve the group'), 'status': 502}
    gid = (g.get('group') or {}).get('id')
    r = kc_admin.add_user_to_group(sub, gid, env=env)
    if not r.get('ok'):
        return {'ok': False, 'refusal': r.get('refusal', 'could not join the group'), 'status': 502}
    _record(manager, 'claim', role, sub)
    return {'ok': True, 'role': role, 'group_id': gid, 'group_created': bool(g.get('created')), 'why': why,
            'note': REFRESH_NOTE}


def release(manager, user_info, role, env=None):
    """Take the caller back out of the role's group. Only roles they could have claimed — releasing a role somebody
    else granted you is an administrator's business, not self-service."""
    allowed, why, _entry = may_claim(manager, user_info, role, env=env)
    if not allowed:
        return {'ok': False, 'refusal': why, 'status': 403}
    ok, cfg_why = kc_admin.configured(env)
    if not ok:
        return {'ok': False, 'refusal': cfg_why, 'status': 503}
    sub, _username, _g = caller(user_info)
    role = role.strip().lstrip('/')
    found = kc_admin.find_group(role, env=env)
    if not found.get('ok'):
        return {'ok': False, 'refusal': found.get('refusal', 'could not resolve the group'), 'status': 502}
    if not found.get('found'):
        return {'ok': True, 'role': role, 'group_id': '', 'released': False, 'note': f'there is no {role} group to leave'}
    gid = (found.get('group') or {}).get('id')
    r = kc_admin.remove_user_from_group(sub, gid, env=env)
    if not r.get('ok'):
        return {'ok': False, 'refusal': r.get('refusal', 'could not leave the group'), 'status': 502}
    _record(manager, 'release', role, sub)
    return {'ok': True, 'role': role, 'group_id': gid, 'released': True, 'note': REFRESH_NOTE}


def _record(manager, verb, role, sub):
    """Every claim and release is a SecurityEvent, so /api/security/events shows who took what (his rule: security
    is observable). Never raises — a ledger that fails must not lose the person their role.

    PII RULE (his, 2026-09-18): Keycloak exists to keep personal data AWAY from Polari, so the actor written here is
    the opaque Keycloak `sub` and NOTHING else — never preferred_username, never an e-mail, never a display name.
    Resolving a sub back to a person is Keycloak's job, and it stays Keycloak's job."""
    try:
        _observe.record(manager, 'role-claim', f'{verb} {role}', role, actor=str(sub or ''), outcome='allowed',
                        would_deny=False, source='self-claim',
                        reason=f'a signed-in account {verb}d the self-claimable role {role}')
    except Exception:
        pass


def how(manager, user_info, env=None):
    """The sentence the API hands back — what this is and what to do next."""
    dev = _posture.is_dev(env)
    return ('POST /api/security/roles/claim {"role": "<name>"} puts you in that Keycloak group; DELETE '
            '/api/security/roles/claim?role=<name> takes you back out. '
            + ('This instance is in DEV posture: every prototype role is claimable unless an administrator marked it '
               'otherwise. ' if dev else
               'This instance is in PRODUCTION posture: only roles an administrator flagged self_claimable (or listed '
               'in the claimable_groups knob) may be taken. ')
            + 'Administrator roles are never self-claimable. ' + REFRESH_NOTE + '.')
