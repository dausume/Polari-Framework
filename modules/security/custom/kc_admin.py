"""
security.custom.kc_admin — the backend's SMALL Keycloak admin client (his ask 2026-09-18: self-claimable roles).

A role in Polari is a Keycloak GROUP: `caller_groups()` reads the `groups` claim, and `AppPermissionProfile.
kc_groups_json` holds bare group names. So "claim a role" means "put my Keycloak user into that group", and the
backend needs a credential that may do it.

It has one: the `polari-backend` client's SERVICE ACCOUNT. `pol-keycloak/startup_shells/configure_clients.sh`
enables `serviceAccountsEnabled` on it, patches the secret from `KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET`, and grants
the service account the realm-management roles `view-users`, `manage-users`, `view-realm`. The compose files pass
`POLARI_KEYCLOAK_ADMIN_URL` (the in-cluster URL, http://pol-keycloak:8080), `POLARI_KEYCLOAK_REALM` and that secret
to `prf-backend`. Verified live on the home stack 2026-09-18: the client_credentials grant answers, and the token
carries resource_access.realm-management = [view-realm, manage-users, view-users, query-groups, query-users].

Rules this module keeps:
  * urllib only — the backend takes no new dependency for six HTTP calls;
  * every call has a timeout and NEVER raises into the API: the answer is always a dict, `{'ok': False,
    'refusal': <a sentence a person can act on>}` when it could not be done;
  * nothing here decides POLICY. Whether a role may be claimed at all is `security.custom.security_claims`;
    this module only carries out a decision that was already made.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 10
_TOKEN = {'value': '', 'expires': 0.0}          # one cached service-account token per process

ADMIN_CLIENT_ID = 'polari-backend'
NO_SECRET = ('the backend has no Keycloak admin credential (KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET)')


def config(env=None):
    """{admin_url, realm, client_id, secret, issuer} — what the container was given."""
    env = os.environ if env is None else env
    return {
        'admin_url': (env.get('POLARI_KEYCLOAK_ADMIN_URL') or '').rstrip('/'),
        'realm': env.get('POLARI_KEYCLOAK_REALM') or 'Polari',
        # NOT POLARI_KEYCLOAK_ADMIN_CLIENT_ID: that one is `admin-cli` on the live stack, a PUBLIC client with no
        # service account ("Public client not allowed to retrieve service account", seen live 2026-09-18). The
        # credential we hold is the `polari-backend` client's secret, so the client id must be its own.
        'client_id': env.get('POLARI_KEYCLOAK_BACKEND_CLIENT_ID') or ADMIN_CLIENT_ID,
        'secret': env.get('KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET') or '',
        'issuer': (env.get('POLARI_KEYCLOAK_ISSUER_URI') or '').rstrip('/'),
    }


def configured(env=None):
    """(ok, refusal) — is there anything to talk to, with a credential?"""
    c = config(env)
    if not c['admin_url']:
        return False, 'this instance has no Keycloak (POLARI_KEYCLOAK_ADMIN_URL is unset)'
    if not c['secret']:
        return False, NO_SECRET
    return True, ''


def account_url(env=None):
    """The Keycloak account console for this realm — where a person manages their own login."""
    c = config(env)
    if c['issuer']:
        return c['issuer'] + '/account'
    if c['admin_url']:
        return f"{c['admin_url']}/realms/{c['realm']}/account"
    return ''


# ---- the one place an HTTP call happens (the selftest monkeypatches THIS) -------------------------------------------

def _http(method, url, headers=None, data=None, form=False):
    """One request. Returns (status, parsed-body-or-text). Never raises: a failure comes back as (0, str(exc))."""
    try:
        body = None
        hdrs = dict(headers or {})
        if data is not None:
            if form:
                body = urllib.parse.urlencode(data).encode()
                hdrs.setdefault('Content-Type', 'application/x-www-form-urlencoded')
            else:
                body = json.dumps(data).encode()
                hdrs.setdefault('Content-Type', 'application/json')
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            status = resp.getcode()
        if not raw:
            return status, None
        try:
            return status, json.loads(raw)
        except ValueError:
            return status, raw.decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode('utf-8', 'replace')[:400]
        except Exception:
            detail = ''
        return exc.code, detail
    except Exception as exc:
        return 0, f'{type(exc).__name__}: {exc}'


def _bad(status, body, what):
    return {'ok': False, 'status': status, 'refusal': f'Keycloak refused to {what} ({status}): {str(body)[:300]}'}


# ---- the service-account token --------------------------------------------------------------------------------------

def token(env=None, force=False):
    """(token, refusal). Cached until 30 s before it expires; client_credentials for the polari-backend client."""
    ok, why = configured(env)
    if not ok:
        return '', why
    now = time.time()
    if not force and _TOKEN['value'] and _TOKEN['expires'] > now:
        return _TOKEN['value'], ''
    c = config(env)
    status, body = _http('POST', f"{c['admin_url']}/realms/{c['realm']}/protocol/openid-connect/token",
                         data={'grant_type': 'client_credentials', 'client_id': c['client_id'], 'client_secret': c['secret']}, form=True)
    if status != 200 or not isinstance(body, dict) or not body.get('access_token'):
        hint = ''
        if status in (400, 401):
            hint = (' — check the client secret, and that serviceAccountsEnabled is on for '
                    f"the confidential client {c['client_id']} (pol-keycloak/startup_shells/configure_clients.sh "
                    'sets both; a PUBLIC client such as admin-cli can never do this)')
        return '', f'the backend could not get a Keycloak service-account token ({status}): {str(body)[:200]}{hint}'
    _TOKEN['value'] = body['access_token']; _TOKEN['expires'] = now + max(30, int(body.get('expires_in') or 60)) - 30
    return _TOKEN['value'], ''


def _admin(method, path, env=None, data=None):
    """One admin-API call, with the token. Returns (status, body, refusal)."""
    tok, why = token(env)
    if not tok:
        return 0, None, why
    c = config(env)
    status, body = _http(method, f"{c['admin_url']}/admin/realms/{c['realm']}{path}",
                         headers={'Authorization': 'Bearer ' + tok}, data=data)
    if status == 401:                                    # the cached token died mid-flight: one retry, fresh
        tok, why = token(env, force=True)
        if not tok:
            return status, body, why
        status, body = _http(method, f"{c['admin_url']}/admin/realms/{c['realm']}{path}",
                             headers={'Authorization': 'Bearer ' + tok}, data=data)
    return status, body, ''


# ---- groups ---------------------------------------------------------------------------------------------------------

def groups(env=None, search=''):
    """{ok, groups: [{id, name, path}]} — the realm's top-level groups."""
    q = ('?search=' + urllib.parse.quote(search)) if search else '?search='
    status, body, why = _admin('GET', '/groups' + q, env=env)
    if why:
        return {'ok': False, 'refusal': why}
    if status != 200 or not isinstance(body, list):
        return _bad(status, body, 'list the realm groups')
    return {'ok': True, 'groups': [{'id': g.get('id'), 'name': g.get('name'), 'path': g.get('path')} for g in body if isinstance(g, dict)]}


def find_group(name, env=None):
    """{ok, found: bool, group} — the realm group called `name` (exact, case-insensitive), or found=False."""
    name = (name or '').strip().lstrip('/')
    if not name:
        return {'ok': False, 'refusal': 'a group name is required'}
    r = groups(env=env, search=name)
    if not r.get('ok'):
        return r
    hit = next((g for g in r['groups'] if str(g.get('name') or '').lower() == name.lower()), None)
    return {'ok': True, 'found': hit is not None, 'group': hit}


def create_group(name, env=None):
    """{ok, created: bool, group} — make the top-level group if it is not there yet (idempotent)."""
    name = (name or '').strip().lstrip('/')
    if not name:
        return {'ok': False, 'refusal': 'a group name is required'}
    existing = find_group(name, env=env)
    if not existing.get('ok'):
        return existing
    if existing.get('found'):
        return {'ok': True, 'created': False, 'group': existing['group']}
    status, body, why = _admin('POST', '/groups', env=env, data={'name': name})
    if why:
        return {'ok': False, 'refusal': why}
    if status not in (201, 204, 409):
        return _bad(status, body, f'create the group {name}')
    after = find_group(name, env=env)
    if not after.get('ok') or not after.get('found'):
        return {'ok': False, 'refusal': f'Keycloak accepted the creation of {name} but the group is not readable back'}
    return {'ok': True, 'created': status != 409, 'group': after['group']}


# ---- one user, by sub (the PII boundary's single door) ---------------------------------------------------------------

def get_user(sub, env=None):
    """{ok, user: {id, username, first_name, last_name, enabled}} — the Keycloak account `sub`, read LIVE.

    This is the ONE place Polari may learn a person's name (his rule D18-1, 2026-09-18: names live in Keycloak and
    stay there). The answer is handed straight to the caller of `GET /api/security/people/{sub}` and is NEVER written
    into a Polari row, a log line or a cache. The service account already holds `view-users`.

    No e-mail is returned: the door exists so a page can show a human-readable name, not so Polari can hold contact
    details."""
    if not sub:
        return {'ok': False, 'refusal': 'no user id (a Keycloak `sub` is required)'}
    status, body, why = _admin('GET', f'/users/{urllib.parse.quote(str(sub))}', env=env)
    if why:
        return {'ok': False, 'refusal': why}
    if status == 404:
        return {'ok': False, 'status': 404, 'refusal': 'that user does not exist in this realm'}
    if status != 200 or not isinstance(body, dict):
        return _bad(status, body, 'read the user')
    return {'ok': True, 'user': {'id': body.get('id') or str(sub), 'username': body.get('username') or '',
                                 'first_name': body.get('firstName') or '', 'last_name': body.get('lastName') or '',
                                 'enabled': bool(body.get('enabled', True))}}


def display_name(user):
    """The name a page shows for a Keycloak account: "First Last", else the username, else ''."""
    if not isinstance(user, dict):
        return ''
    full = ' '.join(x for x in (user.get('first_name'), user.get('last_name')) if x).strip()
    return full or str(user.get('username') or '')


# ---- a user's groups ------------------------------------------------------------------------------------------------

def user_groups(sub, env=None):
    """{ok, groups: [{id, name, path}]} — the groups the Keycloak user `sub` is in."""
    if not sub:
        return {'ok': False, 'refusal': 'no user id (the caller has no `sub` claim)'}
    status, body, why = _admin('GET', f'/users/{urllib.parse.quote(str(sub))}/groups', env=env)
    if why:
        return {'ok': False, 'refusal': why}
    if status == 404:
        return {'ok': False, 'refusal': 'that user does not exist in this realm'}
    if status != 200 or not isinstance(body, list):
        return _bad(status, body, 'read the user\'s groups')
    return {'ok': True, 'groups': [{'id': g.get('id'), 'name': g.get('name'), 'path': g.get('path')} for g in body if isinstance(g, dict)]}


def add_user_to_group(sub, group_id, env=None):
    """{ok} — PUT the membership. Idempotent in Keycloak (a second PUT is still 204)."""
    if not sub or not group_id:
        return {'ok': False, 'refusal': 'a user id and a group id are required'}
    status, body, why = _admin('PUT', f'/users/{urllib.parse.quote(str(sub))}/groups/{urllib.parse.quote(str(group_id))}', env=env)
    if why:
        return {'ok': False, 'refusal': why}
    if status not in (200, 204):
        return _bad(status, body, 'add the user to the group')
    return {'ok': True, 'status': status}


def remove_user_from_group(sub, group_id, env=None):
    """{ok} — DELETE the membership. Idempotent."""
    if not sub or not group_id:
        return {'ok': False, 'refusal': 'a user id and a group id are required'}
    status, body, why = _admin('DELETE', f'/users/{urllib.parse.quote(str(sub))}/groups/{urllib.parse.quote(str(group_id))}', env=env)
    if why:
        return {'ok': False, 'refusal': why}
    if status not in (200, 204, 404):
        return _bad(status, body, 'remove the user from the group')
    return {'ok': True, 'status': status}
