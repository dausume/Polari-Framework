"""security.custom.security_people — the BATCH half of the PII boundary's one door (his rule D18-1).

`GET /api/security/people/{sub}` resolves one subject id per Keycloak round trip. A table listing fifty actors
would make fifty of them, which is why §53 of TESTING_OWED listed "a batch form and a per-caller rate limit" as
owed before any page resolved names in bulk. This module is that half: the memory cache, the rate limit, and the
resolution of a LIST of subs. It decides no policy — who may ask about which sub is `SecurityAPI._may_see_people`.

THE CACHE IS THE ONE PLACE A NAME LIVES IN THE BACKEND, AND IT DIES WITH THE PROCESS.
It is a plain dict in this module's globals. It is never written to a Polari row, never persisted to the object
tree, never logged, never handed to `persistTree`, and never survives a restart of `prf-backend`. TTL is 300 s by
default (`POLARI_PEOPLE_CACHE_SECONDS`; 0 turns caching off entirely and every lookup goes back to Keycloak).
Keycloak remains the system of record: a rename shows up within one TTL, and a deleted account stops resolving
within one TTL. Nothing here relaxes the gate — a cached name is returned only to a caller who was allowed to ask
for that sub on THIS request.
"""
import os
import time

MAX_SUBS = 200                  # one request may ask about this many subs; more is a 400, not a slow answer
RATE_LIMIT_CALLS = 60           # per caller, per window
RATE_LIMIT_WINDOW = 60.0        # seconds

_CACHE = {}                     # sub -> {'display_name': str, 'username': str, 'expires': float}  (memory only)
_CALLS = {}                     # caller key -> [timestamps within the window]  (memory only)


def cache_seconds(env=None):
    """The TTL. 300 s by default; 0 (or a value that will not parse) means do not cache at all."""
    env = os.environ if env is None else env
    try:
        return max(0, int(env.get('POLARI_PEOPLE_CACHE_SECONDS', '300')))
    except (TypeError, ValueError):
        return 300


def cache_clear():
    """Forget every name held in memory. Called by the selftest; a person can do it by restarting the backend."""
    _CACHE.clear()


def cache_state():
    """{entries, ttl_seconds} — a count, never the names themselves."""
    return {'entries': len(_CACHE), 'ttl_seconds': cache_seconds()}


def rate_clear():
    _CALLS.clear()


def rate_ok(key, now=None):
    """(allowed, retry_after_seconds). A plain sliding window per caller — 60 calls a minute, in memory."""
    now = time.time() if now is None else now
    hits = [t for t in _CALLS.get(key or '', []) if now - t < RATE_LIMIT_WINDOW]
    if len(hits) >= RATE_LIMIT_CALLS:
        _CALLS[key or ''] = hits
        return False, int(RATE_LIMIT_WINDOW - (now - hits[0])) + 1
    hits.append(now)
    _CALLS[key or ''] = hits
    return True, 0


def _cached(sub, now):
    e = _CACHE.get(sub)
    if e and e['expires'] > now:
        return e
    if e:
        _CACHE.pop(sub, None)
    return None


def resolve(subs, env=None):
    """Resolve an ALREADY-PERMITTED list of subs → ({sub: display_name|null}, {'hits', 'misses', 'calls'}).

    A sub Keycloak does not know (or refuses to answer for) resolves to None — one bad sub never fails the batch.
    `kc_admin.get_user` is looked up on the module at call time so the selftest can monkeypatch it.
    """
    from security.custom import kc_admin
    ttl = cache_seconds(env)
    now = time.time()
    out, stats = {}, {'hits': 0, 'misses': 0, 'calls': 0}
    for sub in subs:
        sub = str(sub or '')
        if not sub or sub in out:
            continue
        hit = _cached(sub, now) if ttl else None
        if hit is not None:
            out[sub] = hit['display_name'] or None
            stats['hits'] += 1
            continue
        stats['misses'] += 1
        stats['calls'] += 1
        r = kc_admin.get_user(sub, env=env) if env is not None else kc_admin.get_user(sub)
        if not r.get('ok'):
            out[sub] = None                      # unknown, disabled, or Keycloak refused: null, never an error
            continue
        user = r.get('user') or {}
        name = kc_admin.display_name(user)
        out[sub] = name or None
        if ttl:
            _CACHE[sub] = {'display_name': name, 'username': user.get('username') or '', 'expires': now + ttl}
    return out, stats
