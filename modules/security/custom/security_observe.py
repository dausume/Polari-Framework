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

_LAST = {}   # name -> when (a cheap in-process rate limit on the persist, not on the counting)


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
        rows = tables.get('SecurityEvent')
        name = event_name(control, action, target); now = _now()
        row = None
        if rows:
            row = next((r for r in rows.values() if getattr(r, 'name', '') == name), None)
        if row is not None:
            row.count = int(getattr(row, 'count', 0) or 0) + 1; row.last_seen = now; row.reason = reason or row.reason
            row.outcome = outcome; row.actor = actor or row.actor
        else:
            from security.objects.security.SecurityEvent import SecurityEvent
            fields = {'name': name, 'control': control, 'action': action, 'target': target, 'actor': actor, 'app': app, 'outcome': outcome,
                      'would_deny': would_deny, 'reason': reason, 'posture': _posture.posture(), 'count': 1, 'first_seen': now, 'last_seen': now, 'source': source}
            row = None
            try:
                from polariApiServer.seed_upsert import seed_upsert
                row = seed_upsert(manager, 'SecurityEvent', SecurityEvent, fields)
            except Exception:
                try:
                    row = SecurityEvent(manager=manager, **fields)
                except Exception:
                    row = None
            if row is None:
                # no full manager here (a test double, a degraded boot): still COUNT it, in the table, as a plain row
                import types
                row = types.SimpleNamespace(**fields)
                tables.setdefault('SecurityEvent', {})[name] = row
            elif rows is not None and not any(getattr(r, 'name', '') == name for r in rows.values()):
                rows[name] = row
        if save:
            last = _LAST.get(name, 0)
            if time.time() - last > 5 and hasattr(manager, 'persistTree'):
                _LAST[name] = time.time()
                try:
                    import threading
                    threading.Thread(target=manager.persistTree, daemon=True).start()
                except Exception:
                    pass
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
    rows = list(((getattr(manager, 'objectTables', None) or {}).get('SecurityEvent') or {}).values())
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

def _plain_row(tables, table, name, fields):
    """Upsert one row into `table` by name: a real treeObject through seed_upsert when a manager is there, else a plain
    row (a test double, a degraded boot) — either way the count is kept."""
    rows = tables.setdefault(table, {})
    row = next((r for r in rows.values() if getattr(r, 'name', '') == name), None)
    if row is not None:
        return row, False
    return None, True


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
            row = None
            try:
                from security.objects.security.PermissionObservation import PermissionObservation
                from polariApiServer.seed_upsert import seed_upsert
                row = seed_upsert(manager, 'PermissionObservation', PermissionObservation, fields)
            except Exception:
                row = None
            if row is None:
                import types
                row = types.SimpleNamespace(**fields)
            rows = tables.setdefault('PermissionObservation', {})
            if not any(getattr(r, 'name', '') == name for r in rows.values()):
                rows[name] = row
        if save and hasattr(manager, 'persistTree'):
            last = _LAST.get('obs:' + name, 0)
            if time.time() - last > 5:
                _LAST['obs:' + name] = time.time()
                try:
                    import threading
                    threading.Thread(target=manager.persistTree, daemon=True).start()
                except Exception:
                    pass
        return row
    except Exception:
        return None


OBS_KEYS = ('name', 'actor', 'groups', 'profiles', 'verb', 'class_name', 'app', 'verdict', 'count', 'first_seen', 'last_seen', 'posture')


def observations(manager):
    rows = list(((getattr(manager, 'objectTables', None) or {}).get('PermissionObservation') or {}).values())
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
