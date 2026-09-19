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

THE PII BOUNDARY (his ruling D18-1, 2026-09-18) — Keycloak exists to keep personal data AWAY from Polari. Every
person in a row, an event or a log line here is identified ONLY by their opaque Keycloak subject id (`sub`): never a
preferred_username, never an e-mail, never a display name. The four ledgers keep their column NAME (`actor`) — it
now holds a sub. A name is resolved at RENDER time, once, through the single gated door
`GET /api/security/people/{sub}`, and is never cached back into the tree. `scrub_actor_pii()` clears rows written
before the rule existed.
"""
import re
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


# ---- the PII boundary (D18-1): a person is a Keycloak `sub` and nothing else -------------------------------------

#: the Keycloak subject id as Keycloak issues it — 8-4-4-4-12 hex. Anything else in an `actor` column is PII
#: (a username, an e-mail, a display name) written before the rule existed, and the scrub clears it.
SUB_RE = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')

#: the four ledgers whose `actor` column holds a person
PII_TABLES = ('PermissionObservation', 'SecurityEvent', 'ObservationSession', 'UsageObservation')


def looks_like_sub(value):
    """True when `value` is shaped like a Keycloak subject id (the only person-identifier Polari may store)."""
    return bool(SUB_RE.match(str(value or '').strip()))


def actor_of(user_info):
    """The ONE actor resolution in this module: the caller's opaque Keycloak `sub`, or '' when there is nobody.

    His rule D18-1 (2026-09-18): never preferred_username, never username, never e-mail — those live in Keycloak and
    stay there. A name for a `sub` is resolved live through GET /api/security/people/{sub}."""
    if not isinstance(user_info, dict):
        return ''
    return str(user_info.get('sub') or '')


_SCRUBBED = {'done': False, 'count': 0}


def scrub_actor_pii(manager, save=True):
    """One-shot, idempotent: clear every `actor` value in the four ledgers that is not a Keycloak `sub`.

    The live stack's rows were written before D18-1 and hold usernames from this week's role-play tests. A value that
    is empty stays empty; a value shaped like a sub is kept; anything else IS a name or an e-mail and is cleared to
    ''. Running it twice clears nothing the second time (the rows are already sub-only). Never raises."""
    n = 0
    try:
        if getattr(manager, 'objectTables', None) is None:
            return 0
        for table in PII_TABLES:
            for row in _all_rows(manager, table):
                value = str(getattr(row, 'actor', '') or '')
                if value and not looks_like_sub(value):
                    row.actor = ''
                    n += 1
        if n and save:
            _schedule_persist(manager)
    except Exception:
        return n
    return n


def scrub_actor_pii_once(manager):
    """Run the scrub once per process and say so in the log — the count is the proof it ran."""
    if _SCRUBBED['done']:
        return _SCRUBBED['count']
    _SCRUBBED['done'] = True                    # set FIRST: scrub_actor_pii reads the same tables, no re-entry
    n = scrub_actor_pii(manager)
    _SCRUBBED['count'] = n
    print('[security] PII scrub: %d actor values cleared (D18-1)' % n, flush=True)
    return n


def _ledger_rows(manager):
    return sum(len(_all_rows(manager, t)) for t in PII_TABLES)


def start_pii_scrub(manager, polServer=None, wait_s=300, rows_wait_s=120, tick=2.0):
    """Schedule the one-shot scrub for AFTER this module's rows are on the tree.

    The endpoint constructor runs while falcon's routes are built — Phase A/B of the lazy boot (restore + seeds) has
    not happened yet, so scrubbing there would walk an empty tree and clear nothing. This waits for the boot registry
    to stop calling `security` pending (and, when there is no registry, for rows to actually appear), then scrubs
    once. A daemon thread: it can never hold the boot up, and it never raises into it."""
    import threading

    def _run():
        start = time.time()
        while time.time() - start < wait_s:
            registry = getattr(polServer, 'bootRegistry', None)
            try:
                pending = bool(registry.is_data_pending('security')) if registry is not None else False
            except Exception:
                pending = False
            if not pending and (_ledger_rows(manager) or time.time() - start >= rows_wait_s):
                break
            time.sleep(tick)
        scrub_actor_pii_once(manager)

    t = threading.Thread(target=_run, name='security-pii-scrub', daemon=True)
    t.start()
    return t


def observable(control):
    return control in OBSERVED_CONTROLS


def event_name(control, action, target):
    return f"{control}|{action}|{target}"[:200]


def record(manager, control, action, target, reason='', actor='', app='', outcome='observed', would_deny=True, source='', save=True):
    """Count one decision into its SecurityEvent row (upsert by control|action|target). Never raises.

    `actor` is the caller's opaque Keycloak `sub` — D18-1: never a username, an e-mail or a display name. Callers
    resolve it with `actor_of(user_info)`; nothing else may be passed."""
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
        groups_s = ','.join(sorted(groups))
        # D18-1: the actor column holds the opaque Keycloak `sub` and NOTHING else. (It used to prefer
        # preferred_username → username → sub, which put a person's login name in a Polari row.)
        actor = actor_of(user_info)
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
                      'verdict': vd, 'count': 1, 'first_seen': now, 'last_seen': now, 'posture': _posture.posture(),
                      'tasks_json': '{}'}
            from security.objects.security.PermissionObservation import PermissionObservation
            row = _new_row(manager, tables, 'PermissionObservation', PermissionObservation, fields)
        if roleplay:
            # ct-7 (design §8): the act is attributed to the TASK the open session states, so the review can read
            # as tasks → doors → objects × verbs instead of as one flat class list.
            from security.custom.security_tasks import bump_task, current_task
            bump_task(row, current_task(manager, roleplay))
            _touch_session(manager, roleplay.strip().lower(), 'acts')
        if save:
            _schedule_persist(manager)
        return row
    except Exception:
        return None


#: ct-7's `tasks_json` is on the row and the CRUDE listing shows it, but the security door that is NAMED for
#: observations projected this tuple and left it out — so `/api/security/observations` answered `tasks_json:
#: null` for every row while `GET /PermissionObservation` answered the map (round-5 live proof, N-5). Both are
#: sent now: `tasks_json` is the column as stored, `tasks` is it parsed.
OBS_KEYS = ('name', 'actor', 'groups', 'profiles', 'verb', 'class_name', 'app', 'verdict', 'count', 'first_seen', 'last_seen', 'posture', 'tasks_json')


def observations(manager):
    from security.custom.security_tasks import tasks_of
    rows = _all_rows(manager, 'PermissionObservation')
    out = [{**{k: getattr(r, k, '') for k in OBS_KEYS}, 'tasks': tasks_of(r)} for r in rows]
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
        # D18-1: `actors` is a set of DISTINCT Keycloak subject ids — how many people, never who they are.
        out.append({'name': 'observed-' + '-'.join(groups)[:60], 'title': f"Observed: {', '.join(groups)}",
                    'description': f"derived from {d['acts']} observed act(s) by {len(d['actors'])} distinct Keycloak subject(s) between {d['first_seen']} and {d['last_seen']} in dev posture",
                    'app_name': '', 'kc_groups_json': _json.dumps(groups), 'verbs_json': _json.dumps(verbs), 'extra_classes_json': _json.dumps(sorted(d['classes'])),
                    'published': False, 'is_prior': False,
                    'notes': 'SUGGESTION from /api/security/observations — review the classes and verbs, narrow them, then create the AppPermissionProfile row; nothing is applied automatically',
                    'evidence': {'classes': d['classes'], 'acts': d['acts'], 'would_deny_today': d['would_deny'],
                                 'actors': sorted(d['actors']), 'actor_count': len(d['actors'])}})
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
    from security.custom.security_tasks import session_tasks
    rows = _all_rows(manager, 'ObservationSession')
    keys = ('name', 'role', 'actor', 'started_at', 'ended_at', 'active', 'note', 'acts', 'usages', 'task')
    out = [{**{k: getattr(r, k, '') for k in keys}, 'tasks': session_tasks(r)} for r in rows]
    if role:
        out = [s for s in out if s['role'] == role]
    if active is not None:
        out = [s for s in out if bool(s['active']) == active]
    out.sort(key=lambda s: s['started_at'] or '', reverse=True)
    return out


def start_session(manager, role, actor='', note='', task=''):
    """Open a role-play window, optionally stating the TASK being performed (ct-7, design §8).

    `actor` is the caller's Keycloak `sub` (D18-1) as the API resolves it — the API never takes it from the
    request body, so nobody can write a name into this column. `task` is free text ("publish an article"); it may
    be CHANGED mid-session by posting here again with the same role and a different task, which is why an already
    open session is not simply echoed back."""
    from security.custom.security_tasks import HOW_TASKS, clean_task, session_tasks, state_task
    role = (role or '').strip().lower()
    if not role:
        return {'ok': False, 'refusal': 'role required — the group you are acting as (journalist, operator, …)'}
    tables = getattr(manager, 'objectTables', None)
    if tables is None:
        return {'ok': False, 'refusal': 'no manager'}
    now = _now(); task = clean_task(task)
    for s in _all_rows(manager, 'ObservationSession'):
        if getattr(s, 'role', '') == role and getattr(s, 'actor', '') == actor and getattr(s, 'active', False):
            changed, current = state_task(manager, s, task, now)
            if changed:
                _schedule_persist(manager)
            return {'ok': True, 'session': getattr(s, 'name', ''), 'role': role, 'already_open': True,
                    'task': current, 'task_changed': changed, 'tasks': session_tasks(s),
                    'header': {'X-Polari-Roleplay': role},
                    'how': HOW_TASKS if task else 'post here again with a "task" to say what job you are doing'}
    from security.objects.security.ObservationSession import ObservationSession
    fields = {'name': f'{role}|{now}', 'role': role, 'actor': actor, 'started_at': now, 'ended_at': '', 'active': True, 'note': note, 'acts': 0, 'usages': 0,
              'task': task, 'tasks_json': _json.dumps([{'task': task, 'at': now}] if task else [])}
    row = _new_row(manager, tables, 'ObservationSession', ObservationSession, fields); _schedule_persist(manager)
    return {'ok': True, 'session': fields['name'], 'role': role, 'already_open': False, 'header': {'X-Polari-Roleplay': role},
            'task': task, 'task_changed': bool(task), 'tasks': session_tasks(row),
            'recording': recording_on(manager),
            'how': 'send the header on every request while acting as the role; the frontend posts its apps/pages/actions to /api/security/observe/usage. ' + HOW_TASKS}


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
USAGE_KEYS = ('name', 'role', 'kind', 'item', 'app', 'page', 'detail', 'actor', 'count', 'first_seen', 'last_seen', 'tasks_json')


def observe_usage(manager, role, kind, item, app='', page='', detail='', actor='', save=True):
    """Count one usage into its UsageObservation row (role × kind × item). Never raises.

    `actor` is the caller's opaque Keycloak `sub` (D18-1) — the API resolves it with `actor_of()`; a name never
    reaches this column."""
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
                      'count': 1, 'first_seen': now, 'last_seen': now, 'tasks_json': '{}'}
            row = _new_row(manager, tables, 'UsageObservation', UsageObservation, fields)
        if role:
            # ct-7: the DOOR this task walked through — the other half of tasks → doors → objects × verbs.
            from security.custom.security_tasks import bump_task, current_task
            bump_task(row, current_task(manager, role))
            _touch_session(manager, role, 'usages')
        if save:
            _schedule_persist(manager)
        return row
    except Exception:
        return None


def usages(manager, role=None, kind=None):
    from security.custom.security_tasks import tasks_of
    rows = _all_rows(manager, 'UsageObservation')
    out = [{**{k: getattr(r, k, '') for k in USAGE_KEYS}, 'tasks': tasks_of(r)} for r in rows]
    if role:
        out = [u for u in out if u['role'] == role]
    if kind:
        out = [u for u in out if u['kind'] == kind]
    out.sort(key=lambda u: (u['kind'], -int(u.get('count') or 0), u['item']))
    return out


# ---- the review: everything a role used, as the handoff to the permissions admin

def _role_closure(manager, role):
    """ct-4: `security_closure.role_closure`, defended. A review must still answer when the closure cannot be
    computed (no map, no trace target ever armed, the module half-loaded) — it says so instead of failing."""
    try:
        from security.custom.security_closure import role_closure
        return role_closure(manager, role)
    except Exception as exc:                    # noqa: BLE001 — the review is the important half
        return {'objects': [], 'events': [], 'solutions': [], 'peers': [], 'external': [], 'other': [],
                'edges': [], 'coverage': [], 'not_traced': [], 'start': [],
                'counts': {'objects': 0, 'events': 0, 'solutions': 0, 'peers': 0, 'external': 0, 'edges': 0,
                           'definer_only': 0},
                'reading': 'the closure could not be computed here (%s: %s) — the direct observations below '
                           'stand on their own' % (type(exc).__name__, exc)}


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
    # D18-1: who acted as the role is a set of DISTINCT Keycloak subject ids — resolve one to a name at render time
    # through GET /api/security/people/{sub}, never from a stored column.
    actors = sorted({a for a in ([o.get('actor') for o in obs] + [u.get('actor') for u in use] +
                                 [s.get('actor') for s in sessions(manager, role)]) if a})
    apps_of_objects = {}
    for o in obs:
        apps_of_objects.setdefault(o.get('app') or app_of_class(o['class_name']) or 'core', set()).add(o['class_name'])
    proposal = {'name': f'{role}', 'title': role.capitalize(), 'description': f'concreted from the role-play review of {role}: {len(objects)} object class(es), {len(by_kind.get("app", []))} app(s), {len(by_kind.get("page", []))} page(s), {len(by_kind.get("endpoint", []))} endpoint(s)',
                'app_name': '', 'kc_groups_json': _json.dumps([role]), 'verbs_json': _json.dumps(verbs), 'extra_classes_json': _json.dumps(sorted(objects)),
                'published': False, 'is_prior': False,
                'notes': 'PROPOSAL from /api/security/observe/review — the permissions admin reviews, narrows, creates the AppPermissionProfile row and publishes it; then /api/security/observe/verify replays the recording against it'}
    # ct-4 (design §6): the TRANSITIVE half of the handoff — what the role's recorded acts go on to reach,
    # through triggers, emitted events, nested solutions, broadcasts, peers and external systems. Never raises
    # and never widens anything: a closure is DISCLOSURE, and the class it cannot speak for says "not traced".
    closure = _role_closure(manager, role)
    # ct-7 (design §8): the same recording read as TASKS → doors → objects × verbs → closure per task. A person's
    # needs are the union of the tasks their roles perform, so this is the shape a profile is actually worked out
    # from; the flat lists below stay, because a task nobody stated still has to be visible.
    try:
        from security.custom.security_tasks import HOW_TASKS, group_by_task
        tasks = group_by_task(manager, obs, use)
        tasks_how = HOW_TASKS
    except Exception as exc:                    # noqa: BLE001 — the review is the important half
        tasks, tasks_how = [], ('the task grouping could not be computed here (%s: %s) — the flat lists below '
                                'stand on their own' % (type(exc).__name__, exc))
    return {'ok': True, 'role': role, 'sessions': sessions(manager, role), 'recording': recording_on(manager),
            'closure': closure, 'tasks': tasks, 'tasks_how': tasks_how,
            'actors': actors, 'actor_count': len(actors),
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
    # a synthetic caller for the replay: groups only, no identity at all (D18-1 — not even a fake username)
    user = {'sub': '', 'roles': [group], 'raw_claims': {'groups': [group]}}
    allowed = []; denied = []
    for o in obs:
        v = permission_verdict(manager, user, o['class_name'], o['verb'])
        (allowed if v.get('allowed') else denied).append({'class': o['class_name'], 'verb': o['verb'], 'count': o['count'], 'why': v.get('why', ''), 'via': v.get('via', [])})
    # ct-4 (design §6): the SECOND verdict — the same replay over the TRANSITIVE set, so the admin sees what
    # the profile covers of everything the role's acts reach, not only of what the role did directly. Nothing
    # here enforces or widens: the confirmation is a person's, and ct-8 is where it is recorded.
    try:
        from security.custom.security_closure import transitive_verdict
        transitive = transitive_verdict(manager, role, user)
    except Exception as exc:                    # noqa: BLE001 — the direct verdict must still answer
        transitive = {'covered': 0, 'total': 0, 'definer_only': 0, 'not_traced': [], 'uncovered': [],
                      'reading': 'the transitive verdict could not be computed here (%s: %s)'
                                 % (type(exc).__name__, exc)}
    # ct-7 (design §8): the THIRD verdict — which TASKS enforcement would break. "3 of 11 acts denied" is a
    # number; "the journalist can no longer publish an article" is a decision somebody can make.
    try:
        from security.custom.security_tasks import group_by_task, verify_tasks
        tasks = verify_tasks(manager, group_by_task(manager, obs, usages(manager, role), with_closure=False),
                             user, permission_verdict)
    except Exception as exc:                    # noqa: BLE001 — the direct verdict must still answer
        tasks = [{'task': '', 'acts': 0, 'allowed': [], 'denied': [], 'breaks': False,
                  'reading': 'the per-task verdict could not be computed here (%s: %s)'
                             % (type(exc).__name__, exc)}]
    broken = [t['task'] for t in tasks if t['breaks']]
    return {'ok': True, 'role': role, 'group': group, 'recorded_acts': len(obs), 'allowed': allowed, 'denied': denied,
            'tasks': tasks, 'tasks_broken': broken,
            'tasks_verdict': ('no task would break: every task this role was recorded performing is still covered'
                              if not broken else
                              '%d task(s) would BREAK under this profile: %s'
                              % (len(broken), ', '.join(repr(t) if t else '(acts with no task stated)'
                                                        for t in broken))),
            'verdict': ('the role can still do everything it was recorded doing' if obs and not denied else ('nothing recorded for this role yet' if not obs else f'{len(denied)} recorded act(s) would now be DENIED — the profile is narrower than the job')),
            'transitive': transitive,
            'how': 'after the admin publishes the AppPermissionProfile for the group, run this; every recorded class × verb is replayed through permission_verdict as a member of the group, and `transitive` replays everything those acts REACH (the closure) so a trigger running as definer is not a blind spot'}


# ---- PROTOTYPE ROLES + the role-play PERMISSION (his refinement 2026-09-16) --------------------------------------------
# A prototype role exists to be role-played: acting as it lets the person do anything (dev posture, observe) while the
# recording builds its template. The role-play permission is its OWN grant — KC groups named in the knob
# (`roleplay_groups`) may act as ANY role; admins always may; a dev instance with no list set lets everyone (it is a
# dev build on the person's own isle). It never applies to admin roles as a target: prototypes are non-admin by nature.

ROLE_STATES = ('prototype', 'concreted', 'enforced')
PROTO_KEYS = ('name', 'title', 'description', 'state', 'created_by', 'created_at', 'concreted_profile', 'concreted_at', 'verified_at', 'verified_verdict',
              'self_claimable')


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


def claimable_groups():
    """The knob's list of KC groups ANYONE signed in may claim for themselves (his ask 2026-09-18), beside the
    RolePrototype rows flagged `self_claimable`. None = the knob has never been set (an empty list is a deliberate
    "nothing extra"). Mirrors roleplay_groups_allowed() exactly — same file, same shape."""
    try:
        d = _json.load(open(_knob_path()))
        g = d.get('claimable_groups') if isinstance(d, dict) else None
        return [str(x).lstrip('/') for x in g] if isinstance(g, list) else None
    except Exception:
        return None


def set_claimable_groups(groups, by=''):
    p = _knob_path()
    try:
        d = _json.load(open(p))
        d = d if isinstance(d, dict) else {}
    except Exception:
        d = {}
    d['claimable_groups'] = [str(g).lstrip('/') for g in (groups or [])]; d['claimable_groups_changed_at'] = _now(); d['claimable_groups_by'] = by
    try:
        _os.makedirs(_os.path.dirname(p), exist_ok=True); tmp = p + '.tmp'; _json.dump(d, open(tmp, 'w')); _os.replace(tmp, p)
        return {'ok': True, 'claimable_groups': d['claimable_groups']}
    except Exception as exc:
        return {'ok': False, 'refusal': f'could not write the knob at {p}: {exc}'}


def people_viewers():
    """The knob's list of KC groups whose members may resolve ANY `sub` to a name through the one gated door
    `GET /api/security/people/{sub}` (D18-1). None = never set. Admins always may; everybody may look up their own
    sub. Nobody else resolves a name at all. Mirrors claimable_groups() exactly — same file, same shape."""
    try:
        d = _json.load(open(_knob_path()))
        g = d.get('people_viewers') if isinstance(d, dict) else None
        return [str(x).lstrip('/') for x in g] if isinstance(g, list) else None
    except Exception:
        return None


def set_people_viewers(groups, by=''):
    p = _knob_path()
    try:
        d = _json.load(open(p))
        d = d if isinstance(d, dict) else {}
    except Exception:
        d = {}
    d['people_viewers'] = [str(g).lstrip('/') for g in (groups or [])]; d['people_viewers_changed_at'] = _now(); d['people_viewers_by'] = by
    try:
        _os.makedirs(_os.path.dirname(p), exist_ok=True); tmp = p + '.tmp'; _json.dump(d, open(tmp, 'w')); _os.replace(tmp, p)
        return {'ok': True, 'people_viewers': d['people_viewers']}
    except Exception as exc:
        return {'ok': False, 'refusal': f'could not write the knob at {p}: {exc}'}


def claim_denied_roles():
    """The prototype roles an admin has EXPLICITLY marked un-claimable (`POST /api/security/observe/roles/<name>
    {"self_claimable": false}`). The row's own `self_claimable` column is a plain bool, so it cannot tell "never
    decided" from "decided no" — and dev posture needs that difference: there, everything is claimable UNLESS
    somebody said no. The explicit NOs live here, in the same knob file as the rest of the observe switches."""
    try:
        d = _json.load(open(_knob_path()))
        g = d.get('claim_denied') if isinstance(d, dict) else None
        return [str(x).strip().lower() for x in g] if isinstance(g, list) else []
    except Exception:
        return []


def set_claim_denied(name, denied, by=''):
    """Add/remove one role from the explicit-NO list. Returns the new list."""
    name = (name or '').strip().lower(); p = _knob_path()
    try:
        d = _json.load(open(p))
        d = d if isinstance(d, dict) else {}
    except Exception:
        d = {}
    cur = [str(x).strip().lower() for x in (d.get('claim_denied') or []) if str(x).strip()]
    cur = sorted(set(cur) | {name}) if denied else [x for x in cur if x != name]
    d['claim_denied'] = cur; d['claim_denied_changed_at'] = _now(); d['claim_denied_by'] = by
    try:
        _os.makedirs(_os.path.dirname(p), exist_ok=True); tmp = p + '.tmp'; _json.dump(d, open(tmp, 'w')); _os.replace(tmp, p)
        return {'ok': True, 'claim_denied': cur}
    except Exception as exc:
        return {'ok': False, 'refusal': f'could not write the knob at {p}: {exc}', 'claim_denied': cur}


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
    out = [{k: (bool(getattr(r, k, False)) if k == 'self_claimable' else getattr(r, k, '')) for k in PROTO_KEYS} for r in rows]
    if state:
        out = [p for p in out if p['state'] == state]
    out.sort(key=lambda p: p['name'])
    return out


def create_prototype(manager, name, title='', description='', by='', self_claimable=False):
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
              'concreted_profile': '', 'concreted_at': '', 'verified_at': '', 'verified_verdict': '', 'self_claimable': bool(self_claimable)}
    _new_row(manager, tables, 'RolePrototype', RolePrototype, fields); _schedule_persist(manager)
    return {'ok': True, 'role': fields, 'existed': False, 'next': f'act as it: POST /api/security/observe/session {{"role": "{name}"}} — then review at /api/security/observe/review?role={name}'}


def mark_prototype(manager, name, state, profile='', verdict='', self_claimable=None, by=''):
    """Move a prototype along its ladder, and/or set its SELF-CLAIMABLE flag. `self_claimable` is tri-state: None
    leaves it alone, True/False decides it (and records the explicit NO in the knob so dev posture honours it too)."""
    for r in _all_rows(manager, 'RolePrototype'):
        if getattr(r, 'name', '') == name:
            if state in ROLE_STATES:
                r.state = state
            if profile:
                r.concreted_profile = profile; r.concreted_at = _now()
            if verdict:
                r.verified_at = _now(); r.verified_verdict = verdict
            if self_claimable is not None:
                r.self_claimable = bool(self_claimable)
                set_claim_denied(name, not self_claimable, by=by)
            _schedule_persist(manager)
            return {'ok': True, 'role': {k: (bool(getattr(r, k, False)) if k == 'self_claimable' else getattr(r, k, '')) for k in PROTO_KEYS}}
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
