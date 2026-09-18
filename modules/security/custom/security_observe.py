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

def _schedule_persist(manager, delay=None):
    """Persist the tree once per burst of changes (a rate limit that skipped the trailing increments lost counts
    across a restart — seen live 2026-09-16: 7 in memory, 4 on disk).

    The implementation moved to `polariApiServer.persist_debounce` (§51, 2026-09-17) so CRUDE writes get the same
    guarantee from the same code; this name stays as the module's local spelling of it."""
    from polariApiServer.persist_debounce import schedule_persist
    return schedule_persist(manager, delay=delay, reason='security observation')


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


def observe_permission(manager, user_info, class_name, verb, verdict=None, app='', save=True, roleplay=''):
    """Count one CRUDE act into its PermissionObservation row (groups × class × verb). Dev posture only — the caller
    checks; this never raises. `verdict` is permission_verdict()'s dict when the model ran, None when the gate is off.
    `roleplay` (the X-Polari-Roleplay header) attributes the act to the role being played as well."""
    try:
        tables = getattr(manager, 'objectTables', None)
        if tables is None:
            return None
        if not knob_state()['recording']:
            return None
        try:
            from polariapps.objects.apps_permissions._shared import caller_groups
            groups, _ = caller_groups(user_info)
        except Exception:
            groups = set((user_info or {}).get('roles') or []) if isinstance(user_info, dict) else set()
        groups = roleplay_groups(groups, roleplay)
        groups_s = ','.join(sorted(groups)); actor = ''
        if isinstance(user_info, dict):
            # the backend's jwt_validator hands the caller down as `username`; Keycloak's own claim is
            # `preferred_username`. Without the middle fallback the actor column showed the KC `sub` UUID.
            actor = (user_info.get('preferred_username')
                     or user_info.get('username')
                     or user_info.get('sub') or '')
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
            fields = {'name': name, 'actor': actor, 'groups': groups_s, 'profiles': profiles, 'verb': verb, 'class_name': class_name, 'app': app or app_of_class(class_name),
                      'verdict': vd, 'count': 1, 'first_seen': now, 'last_seen': now, 'posture': _posture.posture()}
            from security.objects.security.PermissionObservation import PermissionObservation
            row = _new_row(manager, tables, 'PermissionObservation', PermissionObservation, fields)
        if roleplay:
            _touch_session(manager, roleplay.strip().lower(), 'acts')
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


# ---- the recording knob + ROLE-PLAY (his asks 2026-09-16) ---------------------------------------------------------------
# "enable and disable that functionality on the fly" — a runtime knob, persisted beside the data, read on every act;
# "role-playing as a Journalist … it should show all of the apps and pages and functionality and objects used" — a
# session attributes everything to the role: objects × verbs (PermissionObservation), endpoints and the frontend's
# apps / pages / components / actions (UsageObservation). Review → hand to a permissions admin → enforce → VERIFY
# (replay the recorded acts against the enforced profiles: can the role still do its job?).

import json as _json
import os as _os

ROLEPLAY_PREFIX = 'roleplay:'


def _knob_path():
    base = _os.environ.get('POLARI_APP_DEBS_DIR', '/app/data/app-debs').rsplit('/app-debs', 1)[0]
    return _os.environ.get('POLARI_OBSERVE_KNOB', _os.path.join(base, 'security', 'observe.json'))


def knob_state():
    """{recording: bool, changed_at, by, source}. Default: recording ON whenever the posture is dev (nothing to turn on
    for a dev build); the knob file overrides either way; production never records."""
    st = {'recording': True, 'changed_at': '', 'by': '', 'source': 'default (dev = on)'}
    try:
        d = _json.load(open(_knob_path()))
        if isinstance(d, dict) and 'recording' in d:
            st.update({'recording': bool(d['recording']), 'changed_at': d.get('changed_at', ''), 'by': d.get('by', ''), 'source': 'knob'})
    except Exception:
        pass
    return st


def set_recording(on, by=''):
    p = _knob_path(); st = {'recording': bool(on), 'changed_at': _now(), 'by': by}
    try:
        _os.makedirs(_os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'; _json.dump(st, open(tmp, 'w')); _os.replace(tmp, p)
        return {**st, 'ok': True, 'path': p}
    except Exception as exc:
        return {**st, 'ok': False, 'refusal': f'could not write the knob at {p}: {exc}'}


def recording_on(manager=None, env=None):
    return _posture.is_dev(env) and knob_state()['recording']


def roleplay_groups(groups, roleplay):
    """The caller's groups plus the role-play marker: observations are attributed to BOTH (the real identity stays
    visible; the review filters by the role-play)."""
    g = set(groups or [])
    if roleplay:
        g.add(ROLEPLAY_PREFIX + roleplay.strip().lower())
    return g


# ---- sessions

def sessions(manager, role=None, active=None):
    rows = _all_rows(manager, 'ObservationSession')
    keys = ('name', 'role', 'actor', 'started_at', 'ended_at', 'active', 'note', 'acts', 'usages')
    out = [{k: getattr(r, k, '') for k in keys} for r in rows]
    if role:
        out = [s for s in out if s['role'] == role]
    if active is not None:
        out = [s for s in out if bool(s['active']) == active]
    out.sort(key=lambda s: s['started_at'] or '', reverse=True)
    return out


def start_session(manager, role, actor='', note=''):
    role = (role or '').strip().lower()
    if not role:
        return {'ok': False, 'refusal': 'role required — the group you are acting as (journalist, operator, …)'}
    tables = getattr(manager, 'objectTables', None)
    if tables is None:
        return {'ok': False, 'refusal': 'no manager'}
    now = _now()
    for s in _all_rows(manager, 'ObservationSession'):
        if getattr(s, 'role', '') == role and getattr(s, 'actor', '') == actor and getattr(s, 'active', False):
            return {'ok': True, 'session': getattr(s, 'name', ''), 'role': role, 'already_open': True, 'header': {'X-Polari-Roleplay': role}}
    from security.objects.security.ObservationSession import ObservationSession
    fields = {'name': f'{role}|{now}', 'role': role, 'actor': actor, 'started_at': now, 'ended_at': '', 'active': True, 'note': note, 'acts': 0, 'usages': 0}
    row = _new_row(manager, tables, 'ObservationSession', ObservationSession, fields); _schedule_persist(manager)
    return {'ok': True, 'session': fields['name'], 'role': role, 'already_open': False, 'header': {'X-Polari-Roleplay': role},
            'recording': recording_on(manager), 'how': 'send the header on every request while acting as the role; the frontend posts its apps/pages/actions to /api/security/observe/usage'}


def end_session(manager, role=None, name=None):
    ended = []
    for s in _all_rows(manager, 'ObservationSession'):
        if getattr(s, 'active', False) and ((name and getattr(s, 'name', '') == name) or (role and getattr(s, 'role', '') == role) or (not name and not role)):
            s.active = False; s.ended_at = _now(); ended.append(getattr(s, 'name', ''))
    if ended:
        _schedule_persist(manager)
    return {'ok': True, 'ended': ended}


def _touch_session(manager, role, field):
    for s in _all_rows(manager, 'ObservationSession'):
        if getattr(s, 'role', '') == role and getattr(s, 'active', False):
            setattr(s, field, int(getattr(s, field, 0) or 0) + 1)


# ---- usages (frontend apps / pages / components / actions; backend endpoints)

USAGE_KINDS = ('app', 'page', 'component', 'action', 'endpoint', 'object')
USAGE_KEYS = ('name', 'role', 'kind', 'item', 'app', 'page', 'detail', 'actor', 'count', 'first_seen', 'last_seen')


def observe_usage(manager, role, kind, item, app='', page='', detail='', actor='', save=True):
    """Count one usage into its UsageObservation row (role × kind × item). Never raises."""
    try:
        tables = getattr(manager, 'objectTables', None)
        if tables is None or kind not in USAGE_KINDS or not item:
            return None
        role = (role or '').strip().lower(); name = f'{role or "-"}|{kind}|{item}'[:200]; now = _now()
        row, new = _plain_row(tables, 'UsageObservation', name, None)
        if not new:
            row.count = int(getattr(row, 'count', 0) or 0) + 1; row.last_seen = now; row.actor = actor or row.actor
            if detail:
                row.detail = detail
        else:
            from security.objects.security.UsageObservation import UsageObservation
            fields = {'name': name, 'role': role, 'kind': kind, 'item': str(item)[:160], 'app': app, 'page': page, 'detail': str(detail)[:200], 'actor': actor,
                      'count': 1, 'first_seen': now, 'last_seen': now}
            row = _new_row(manager, tables, 'UsageObservation', UsageObservation, fields)
        if role:
            _touch_session(manager, role, 'usages')
        if save:
            _schedule_persist(manager)
        return row
    except Exception:
        return None


def usages(manager, role=None, kind=None):
    rows = _all_rows(manager, 'UsageObservation')
    out = [{k: getattr(r, k, '') for k in USAGE_KEYS} for r in rows]
    if role:
        out = [u for u in out if u['role'] == role]
    if kind:
        out = [u for u in out if u['kind'] == kind]
    out.sort(key=lambda u: (u['kind'], -int(u.get('count') or 0), u['item']))
    return out


# ---- the review: everything a role used, as the handoff to the permissions admin

def review(manager, role):
    role = (role or '').strip().lower(); marker = ROLEPLAY_PREFIX + role
    obs = [o for o in observations(manager) if marker in (o.get('groups') or '').split(',')]
    use = usages(manager, role)
    by_kind = {}
    for u in use:
        by_kind.setdefault(u['kind'], []).append({'item': u['item'], 'app': u['app'], 'page': u['page'], 'count': u['count'], 'last_seen': u['last_seen']})
    objects = {}
    for o in obs:
        objects.setdefault(o['class_name'], {})[o['verb']] = objects.get(o['class_name'], {}).get(o['verb'], 0) + int(o.get('count') or 0)
    verbs = sorted({o['verb'] for o in obs})
    apps_of_objects = {}
    for o in obs:
        apps_of_objects.setdefault(o.get('app') or app_of_class(o['class_name']) or 'core', set()).add(o['class_name'])
    proposal = {'name': f'{role}', 'title': role.capitalize(), 'description': f'concreted from the role-play review of {role}: {len(objects)} object class(es), {len(by_kind.get("app", []))} app(s), {len(by_kind.get("page", []))} page(s), {len(by_kind.get("endpoint", []))} endpoint(s)',
                'app_name': '', 'kc_groups_json': _json.dumps([role]), 'verbs_json': _json.dumps(verbs), 'extra_classes_json': _json.dumps(sorted(objects)),
                'published': False, 'is_prior': False,
                'notes': 'PROPOSAL from /api/security/observe/review — the permissions admin reviews, narrows, creates the AppPermissionProfile row and publishes it; then /api/security/observe/verify replays the recording against it'}
    return {'ok': True, 'role': role, 'sessions': sessions(manager, role), 'recording': recording_on(manager),
            'apps': by_kind.get('app', []), 'pages': by_kind.get('page', []), 'components': by_kind.get('component', []), 'actions': by_kind.get('action', []),
            'endpoints': by_kind.get('endpoint', []), 'objects': objects, 'objects_by_app': {k: sorted(v) for k, v in sorted(apps_of_objects.items())}, 'acts': sum(int(o.get('count') or 0) for o in obs),
            'would_deny_today': sum(int(o.get('count') or 0) for o in obs if o.get('verdict') == 'would-deny'),
            'proposed_profile': proposal,
            'handoff': 'give this review to the permissions admin: the objects × verbs become the AppPermissionProfile (kc_groups_json = the KC group the role maps to); the apps/pages/endpoints become the frontend + proxy allow-list for the group'}


# ---- verify after enforcement: can the role still do its job?

def verify(manager, role, group=None):
    """Replay every recorded act of the role against the CURRENT profiles as a member of `group` (default: the role
    name as the KC group). What would be DENIED is what enforcement breaks — fix the profile, or accept the removal."""
    role = (role or '').strip().lower(); group = (group or role).strip()
    marker = ROLEPLAY_PREFIX + role
    obs = [o for o in observations(manager) if marker in (o.get('groups') or '').split(',')]
    try:
        from polariapps.objects.apps_permissions._shared import permission_verdict
    except Exception:
        return {'ok': False, 'refusal': 'the permissions model (polariapps) is not on this instance; nothing to verify against'}
    user = {'preferred_username': f'verify:{group}', 'roles': [group], 'raw_claims': {'groups': [group]}}
    allowed = []; denied = []
    for o in obs:
        v = permission_verdict(manager, user, o['class_name'], o['verb'])
        (allowed if v.get('allowed') else denied).append({'class': o['class_name'], 'verb': o['verb'], 'count': o['count'], 'why': v.get('why', ''), 'via': v.get('via', [])})
    return {'ok': True, 'role': role, 'group': group, 'recorded_acts': len(obs), 'allowed': allowed, 'denied': denied,
            'verdict': ('the role can still do everything it was recorded doing' if obs and not denied else ('nothing recorded for this role yet' if not obs else f'{len(denied)} recorded act(s) would now be DENIED — the profile is narrower than the job')),
            'how': 'after the admin publishes the AppPermissionProfile for the group, run this; every recorded class × verb is replayed through permission_verdict as a member of the group'}


# ---- PROTOTYPE ROLES + the role-play PERMISSION (his refinement 2026-09-16) --------------------------------------------
# A prototype role exists to be role-played: acting as it lets the person do anything (dev posture, observe) while the
# recording builds its template. The role-play permission is its OWN grant — KC groups named in the knob
# (`roleplay_groups`) may act as ANY role; admins always may; a dev instance with no list set lets everyone (it is a
# dev build on the person's own isle). It never applies to admin roles as a target: prototypes are non-admin by nature.

ROLE_STATES = ('prototype', 'concreted', 'enforced')
PROTO_KEYS = ('name', 'title', 'description', 'state', 'created_by', 'created_at', 'concreted_profile', 'concreted_at', 'verified_at', 'verified_verdict')


def roleplay_groups_allowed():
    try:
        d = _json.load(open(_knob_path()))
        g = d.get('roleplay_groups') if isinstance(d, dict) else None
        return [str(x).lstrip('/') for x in g] if isinstance(g, list) else None
    except Exception:
        return None


def set_roleplay_groups(groups, by=''):
    p = _knob_path()
    try:
        d = _json.load(open(p))
        d = d if isinstance(d, dict) else {}
    except Exception:
        d = {}
    d['roleplay_groups'] = [str(g).lstrip('/') for g in (groups or [])]; d['roleplay_groups_changed_at'] = _now(); d['roleplay_groups_by'] = by
    try:
        _os.makedirs(_os.path.dirname(p), exist_ok=True); tmp = p + '.tmp'; _json.dump(d, open(tmp, 'w')); _os.replace(tmp, p)
        return {'ok': True, 'roleplay_groups': d['roleplay_groups']}
    except Exception as exc:
        return {'ok': False, 'refusal': f'could not write the knob at {p}: {exc}'}


def can_roleplay(user_info, env=None):
    """(allowed, why) — the role-play permission for this caller."""
    if not _posture.is_dev(env):
        return False, 'role-play exists only on a dev-posture instance'
    try:
        from polariapps.objects.apps_permissions._shared import caller_groups, ADMIN_ROLES
        groups, _ = caller_groups(user_info); admin = bool(ADMIN_ROLES & groups)
    except Exception:
        groups = set((user_info or {}).get('roles') or []) if isinstance(user_info, dict) else set(); admin = bool({'admin', 'polari-admin'} & groups)
    if admin:
        return True, 'admin'
    allowed = roleplay_groups_allowed()
    if allowed is None:
        return True, 'dev instance with no roleplay_groups set: everyone may role-play (set the list to restrict it)'
    hit = sorted(groups & set(allowed))
    return (True, f'granted by group(s) {", ".join(hit)}') if hit else (False, f'the role-play permission is granted to {allowed}; you are in {sorted(groups) or "no group"}')


def prototypes(manager, state=None):
    rows = _all_rows(manager, 'RolePrototype')
    out = [{k: getattr(r, k, '') for k in PROTO_KEYS} for r in rows]
    if state:
        out = [p for p in out if p['state'] == state]
    out.sort(key=lambda p: p['name'])
    return out


def create_prototype(manager, name, title='', description='', by=''):
    name = (name or '').strip().lower().replace(' ', '-')
    if not name or not all(c.isalnum() or c in '-_' for c in name):
        return {'ok': False, 'refusal': 'a role name: letters, digits, - or _ (journalist, data-scientist)'}
    try:
        from polariapps.objects.apps_permissions._shared import ADMIN_ROLES
        if name in ADMIN_ROLES:
            return {'ok': False, 'refusal': f'{name} is an admin role — prototypes are non-admin roles'}
    except Exception:
        pass
    tables = getattr(manager, 'objectTables', None)
    if tables is None:
        return {'ok': False, 'refusal': 'no manager'}
    for p in prototypes(manager):
        if p['name'] == name:
            return {'ok': True, 'role': p, 'existed': True}
    from security.objects.security.RolePrototype import RolePrototype
    fields = {'name': name, 'title': title or name.replace('-', ' ').title(), 'description': description, 'state': 'prototype', 'created_by': by, 'created_at': _now(),
              'concreted_profile': '', 'concreted_at': '', 'verified_at': '', 'verified_verdict': ''}
    _new_row(manager, tables, 'RolePrototype', RolePrototype, fields); _schedule_persist(manager)
    return {'ok': True, 'role': fields, 'existed': False, 'next': f'act as it: POST /api/security/observe/session {{"role": "{name}"}} — then review at /api/security/observe/review?role={name}'}


def mark_prototype(manager, name, state, profile='', verdict=''):
    for r in _all_rows(manager, 'RolePrototype'):
        if getattr(r, 'name', '') == name:
            if state in ROLE_STATES:
                r.state = state
            if profile:
                r.concreted_profile = profile; r.concreted_at = _now()
            if verdict:
                r.verified_at = _now(); r.verified_verdict = verdict
            _schedule_persist(manager)
            return {'ok': True, 'role': {k: getattr(r, k, '') for k in PROTO_KEYS}}
    return {'ok': False, 'refusal': f'no prototype role {name}'}


# ---- which app a class belongs to (the `app` column of the observations) ------------------------------------------------

_CLASS_APP = {}


def app_of_class(class_name):
    """The module (app) that registers `class_name`, from the core feature-import table; '' for core classes."""
    if not _CLASS_APP:
        try:
            from polariApiServer.feature_imports import FEATURE_IMPORT_BLOCKS
            from polariapps.objects.apps_permissions._shared import classes_for_module
            built = {}
            for feature in {f for f, _ in FEATURE_IMPORT_BLOCKS}:
                for c in classes_for_module(feature):
                    built.setdefault(c, feature)
            if built:
                _CLASS_APP.update(built)      # only a successful build counts as cached; a failed import retries next time
        except Exception:
            return ''
    return _CLASS_APP.get(class_name, '')
