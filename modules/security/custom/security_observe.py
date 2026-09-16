"""
security.custom.security_observe — OBSERVE MODE (ISLE_HARDENING_PLAN §17, his rulings 2026-09-15).

A dev build is a version of an instance where security is deliberately NON-BLOCKING: every control still evaluates,
nothing is denied, and each would-have-been-denial becomes a WARNING a person and an API can see. One switch
(moduleService.posture.is_dev), one ledger (SecurityEvent rows), one contract (the two lists below).

    decide(manager, control, action, target, denied, reason, ...) -> (proceed: bool, outcome: str)
        denied=False                 -> (True, 'allowed')      nothing to record
        denied=True, production      -> (False, 'denied')     the caller refuses as before (and may record it)
        denied=True, dev, observable -> (True, 'observed')    the act RUNS; a SecurityEvent row counts it; the notice bar warns
        denied=True, dev, invariant  -> (False, 'denied')     the §16 invariants refuse even in dev

The contract is the point: OBSERVED_CONTROLS is what warns-but-never-blocks in dev; INVARIANT_CONTROLS is what still
refuses. A control not in either list is treated as an invariant (refuse) — new relaxations are added on purpose.
"""
import time

from moduleService import posture as _posture

# what warns but never blocks in dev (the list is the contract — §17)
OBSERVED_CONTROLS = ('authz', 'content', 'browser', 'trust-channel', 'certificate', 'peer-admission', 'posture-relaxation', 'tier')
# what still refuses even in dev: the six §16 invariants, dev variants on production routes, the ISO refusals that protect the person
INVARIANT_CONTROLS = ('ssh-password', 'upstream-interface', 'production-route', 'secret-export', 'firewall-upstream', 'root-shell-public',
                      'dev-variant-on-production', 'iso-headless-encryption')

_PERSIST = {'pending': False, 'lock': None}   # one trailing persist per burst: every count reaches disk, never one persist per act


def _schedule_persist(manager, delay=3.0):
    """Persist the tree once, `delay` seconds after the LAST change of a burst (a rate limit that skipped the trailing
    increments lost counts across a restart — seen live 2026-09-16: 7 in memory, 4 on disk)."""
    if not hasattr(manager, 'persistTree'):
        return
    import threading
    if _PERSIST['lock'] is None:
        _PERSIST['lock'] = threading.Lock()
    with _PERSIST['lock']:
        if _PERSIST['pending']:
            return
        _PERSIST['pending'] = True

    def run():
        with _PERSIST['lock']:
            _PERSIST['pending'] = False
        try:
            manager.persistTree()
        except Exception:
            pass
    t = threading.Timer(delay, run); t.daemon = True; t.start()


def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def observable(control):
    return control in OBSERVED_CONTROLS


def event_name(control, action, target):
    return f"{control}|{action}|{target}"[:200]


def record(manager, control, action, target, reason='', actor='', app='', outcome='observed', would_deny=True, source='', save=True):
    """Count one decision into its SecurityEvent row (upsert by control|action|target). Never raises."""
    try:
        tables = getattr(manager, 'objectTables', None)
        if tables is None:
            return None
        name = event_name(control, action, target); now = _now()
        row, _new = _plain_row(tables, 'SecurityEvent', name, None)
        if row is not None:
            row.count = int(getattr(row, 'count', 0) or 0) + 1; row.last_seen = now; row.reason = reason or row.reason
            row.outcome = outcome; row.actor = actor or row.actor
        else:
            from security.objects.security.SecurityEvent import SecurityEvent
            fields = {'name': name, 'control': control, 'action': action, 'target': target, 'actor': actor, 'app': app, 'outcome': outcome,
                      'would_deny': would_deny, 'reason': reason, 'posture': _posture.posture(), 'count': 1, 'first_seen': now, 'last_seen': now, 'source': source}
            row = _new_row(manager, tables, 'SecurityEvent', SecurityEvent, fields)
        if save:
            _schedule_persist(manager)
        return row
    except Exception:
        return None


def decide(manager, control, action, target, denied, reason='', actor='', app='', source='', env=None):
    """The one call every enforcement point makes. Returns (proceed, outcome)."""
    if not denied:
        return True, 'allowed'
    if _posture.is_dev(env) and observable(control):
        record(manager, control, action, target, reason=reason, actor=actor, app=app, outcome='observed', would_deny=True, source=source)
        return True, 'observed'
    record(manager, control, action, target, reason=reason, actor=actor, app=app, outcome='denied', would_deny=True, source=source)
    return False, 'denied'


def events(manager):
    rows = _all_rows(manager, 'SecurityEvent')
    keys = ('name', 'control', 'action', 'target', 'actor', 'app', 'outcome', 'would_deny', 'reason', 'posture', 'count', 'first_seen', 'last_seen', 'source')
    out = [{k: getattr(r, k, '') for k in keys} for r in rows]
    out.sort(key=lambda d: d.get('last_seen') or '', reverse=True)
    return out


def summary(manager, env=None):
    ev = events(manager)
    observed = [e for e in ev if e['outcome'] == 'observed']; denied = [e for e in ev if e['outcome'] == 'denied']
    per_control = {}
    for e in observed:
        per_control[e['control']] = per_control.get(e['control'], 0) + int(e.get('count') or 0)
    st = _posture.state(env)
    return {'posture': st['posture'], 'posture_source': st['source'], 'until': st['until'], 'expired': st['expired'],
            'observe': st['posture'] == 'dev', 'observed_events': len(observed), 'observed_actions': sum(int(e.get('count') or 0) for e in observed),
            'denied_events': len(denied), 'per_control': per_control, 'contract': {'observed': list(OBSERVED_CONTROLS), 'invariant': list(INVARIANT_CONTROLS)}}


# ---- permission observations (his ask 2026-09-15): in dev, log which roles/profiles perform which acts ----------------

_FALLBACK = {}   # id(manager) -> table -> name -> plain row: when the manager cannot construct the tree object (a test double)


def _plain_row(tables, table, name, fields):
    """Find the row named `name` in the manager's table (a real tree object) or among the fallback rows."""
    rows = tables.get(table) or {}
    row = next((r for r in rows.values() if getattr(r, 'name', '') == name), None)
    if row is None:
        row = _FALLBACK.get(id(tables), {}).get(table, {}).get(name)
    return row, row is None


def _new_row(manager, tables, table, cls, fields):
    """Construct the tree object the way every module API does (cls(manager=..., **fields) registers it in the
    manager's table and it persists with the tree). If the manager cannot construct one (a test double), keep a
    plain row in _FALLBACK — NEVER in the manager's table: a foreign object there breaks the CRUDE view of the class
    ("PolyTyping for type SimpleNamespace could not be found", seen live 2026-09-16)."""
    try:
        if getattr(manager, 'idList', None) is not None:
            return cls(manager=manager, **fields)
    except Exception:
        pass
    import types
    row = types.SimpleNamespace(**fields)
    _FALLBACK.setdefault(id(tables), {}).setdefault(table, {})[fields['name']] = row
    return row


def _all_rows(manager, table):
    tables = getattr(manager, 'objectTables', None) or {}
    rows = list((tables.get(table) or {}).values())
    seen = {getattr(r, 'name', '') for r in rows}
    return rows + [r for n, r in _FALLBACK.get(id(tables), {}).get(table, {}).items() if n not in seen]


def observe_permission(manager, user_info, class_name, verb, verdict=None, app='', save=True):
    """Count one CRUDE act into its PermissionObservation row (groups × class × verb). Dev posture only — the caller
    checks; this never raises. `verdict` is permission_verdict()'s dict when the model ran, None when the gate is off."""
    try:
        tables = getattr(manager, 'objectTables', None)
        if tables is None:
            return None
        try:
            from polariapps.objects.apps_permissions._shared import caller_groups
            groups, _ = caller_groups(user_info)
        except Exception:
            groups = set((user_info or {}).get('roles') or []) if isinstance(user_info, dict) else set()
        groups_s = ','.join(sorted(groups)); actor = ''
        if isinstance(user_info, dict):
            actor = user_info.get('preferred_username') or user_info.get('sub') or ''
        if verdict is None:
            vd = 'ungated' if user_info else 'unauthenticated'; profiles = ''
        elif verdict.get('allowed'):
            vd = 'admin' if 'admin' in str(verdict.get('why', '')) else 'granted-by-profile'; profiles = ','.join(verdict.get('via') or [])
        else:
            vd = 'would-deny' if user_info else 'unauthenticated'; profiles = ''
        name = f"{groups_s or '-'}|{class_name}|{verb}"[:200]; now = _now()
        row, new = _plain_row(tables, 'PermissionObservation', name, None)
        if not new:
            row.count = int(getattr(row, 'count', 0) or 0) + 1; row.last_seen = now; row.actor = actor or row.actor
            row.verdict = vd; row.profiles = profiles or row.profiles
        else:
            fields = {'name': name, 'actor': actor, 'groups': groups_s, 'profiles': profiles, 'verb': verb, 'class_name': class_name, 'app': app,
                      'verdict': vd, 'count': 1, 'first_seen': now, 'last_seen': now, 'posture': _posture.posture()}
            from security.objects.security.PermissionObservation import PermissionObservation
            row = _new_row(manager, tables, 'PermissionObservation', PermissionObservation, fields)
        if save:
            _schedule_persist(manager)
        return row
    except Exception:
        return None


OBS_KEYS = ('name', 'actor', 'groups', 'profiles', 'verb', 'class_name', 'app', 'verdict', 'count', 'first_seen', 'last_seen', 'posture')


def observations(manager):
    rows = _all_rows(manager, 'PermissionObservation')
    out = [{k: getattr(r, k, '') for k in OBS_KEYS} for r in rows]
    out.sort(key=lambda d: (d.get('groups') or '', d.get('class_name') or '', d.get('verb') or ''))
    return out


def derive_profiles(manager):
    """From the observations, ONE proposed AppPermissionProfile per role set: the classes it touched and the verbs it
    used, with the evidence (counts, first/last seen, what would have been denied today). A SUGGESTION in the shape
    the profile rows take — apply by creating the row (CRUDE create AppPermissionProfile), never applied here."""
    obs = observations(manager); by_group = {}
    for o in obs:
        g = o.get('groups') or ''
        if not g:
            continue          # unauthenticated acts derive nothing: no role to grant to
        d = by_group.setdefault(g, {'classes': {}, 'acts': 0, 'would_deny': 0, 'first_seen': o['first_seen'], 'last_seen': o['last_seen'], 'actors': set()})
        d['classes'].setdefault(o['class_name'], {}); d['classes'][o['class_name']][o['verb']] = d['classes'][o['class_name']].get(o['verb'], 0) + int(o.get('count') or 0)
        d['acts'] += int(o.get('count') or 0); d['would_deny'] += int(o.get('count') or 0) if o.get('verdict') == 'would-deny' else 0
        d['first_seen'] = min(d['first_seen'], o['first_seen']) if o['first_seen'] else d['first_seen']; d['last_seen'] = max(d['last_seen'], o['last_seen'])
        if o.get('actor'):
            d['actors'].add(o['actor'])
    import json as _json
    out = []
    for g, d in sorted(by_group.items()):
        groups = g.split(','); verbs = sorted({v for cv in d['classes'].values() for v in cv})
        out.append({'name': 'observed-' + '-'.join(groups)[:60], 'title': f"Observed: {', '.join(groups)}",
                    'description': f"derived from {d['acts']} observed act(s) by {len(d['actors'])} caller(s) between {d['first_seen']} and {d['last_seen']} in dev posture",
                    'app_name': '', 'kc_groups_json': _json.dumps(groups), 'verbs_json': _json.dumps(verbs), 'extra_classes_json': _json.dumps(sorted(d['classes'])),
                    'published': False, 'is_prior': False,
                    'notes': 'SUGGESTION from /api/security/observations — review the classes and verbs, narrow them, then create the AppPermissionProfile row; nothing is applied automatically',
                    'evidence': {'classes': d['classes'], 'acts': d['acts'], 'would_deny_today': d['would_deny'], 'actors': sorted(d['actors'])}})
    return out


def observe_notice(manager, env=None):
    """The notice-bar item for observe mode: present only in dev posture; counts what production would have denied."""
    st = _posture.state(env)
    if st['posture'] != 'dev':
        return []
    s = summary(manager, env)
    n = s['observed_actions']
    return [{'level': 'warning', 'code': 'observe-mode', 'host': '', 'days_left': None,
             'title': f"OBSERVE MODE — security warns, never blocks: {n} action(s) ran that production would deny" + (f" (until {st['until']})" if st['until'] else ''),
             'text': ('Every control still evaluates; each would-have-been-denial is a SecurityEvent (/api/security/events). '
                      'Peers are admitted at once, self-signed certificates are accepted, authorization refusals let the act through — all recorded. '
                      'Keep this instance on your own isle.'),
             'action': 'Review /api/security/events; pol deploy posture <node> production when the testing is done'}]
