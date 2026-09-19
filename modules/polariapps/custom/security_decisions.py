"""
@cross-cutting
@module polariapps.custom.security_decisions

ct-8 — THE DECISION LEDGER (design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6).

`SecurityDecision` rows, converged the way `RoleAppBinding` is: idempotently, on every read, never overwriting
what a person decided. Four operations:

  converge(manager, app)         create the missing rows as `open`, mark `suggested` where the analysis has
                                 evidence, refresh that evidence — and NEVER touch a `confirmed` or `denied`
                                 row. Running it twice writes nothing the second time.
  bump_version(...)              carry a version's rulings forward as `inherited`; mark every subject the new
                                 version CHANGED as `stale`, so a release never ships on last release's
                                 rulings for something it changed.
  confirm(...)                   the human act: a Keycloak `sub`, an admin role, a proposal hash, a timestamp.
                                 Refused 401 without an identity and 403 without ADMIN_ROLES.
  decisions(...)                 the read behind GET /api/apps/security/decisions.

HIS RULING, WRITTEN INTO THE CODE (design §6): *"the proposal is applied by a PERSON … nothing widens itself
and nothing flips to enforce on its own."* So no function here ever writes `confirmed` or `denied` from
evidence. The strongest thing a derivation may say is `suggested`, and a published `AppPermissionProfile` is
a proposal, not a ruling — it becomes `confirmed` only where a `confirmed_by` sub is already recorded.

@consumers
  - polariapps.apps_api (/api/apps/security/decisions, .../confirm, .../bump)
  - polariapps.custom.security_coverage · polariapps.custom.security_confirm · polariapps.apps_selftest
"""

import json

from polariapps.custom.apps_roles import _find, _new_row, _now, _rows, _save
from polariapps.custom.security_subjects import (  # noqa: F401  (re-exported: the enumeration IS this ledger's input)
    ANY_GROUP, app_version, current_release, enumerate_subjects,
)
from polariapps.objects.apps_permissions._shared import ADMIN_ROLES, caller_groups
from polariapps.objects.apps_security._shared import (
    DECISION_KINDS, DECISION_STATES, HUMAN_STATES, decision_name,
)

DECISION_TABLE = 'SecurityDecision'

#: evidence keys a converge refresh must PRESERVE: they are the account of a version bump (who had ruled at
#: the previous version, and why this row must be re-ruled), not observations that can be recomputed.
CARRIED_EVIDENCE_KEYS = ('inherited_from', 'stale_because', 'confirmed_by_previously')


def _loads(row, attr, default):
    try:
        text = getattr(row, attr, '') or ''
        value = json.loads(text) if text else default
        return value if isinstance(value, type(default)) else default
    except Exception:  # noqa: BLE001
        return default


def _evidence(row):
    return _loads(row, 'evidence_json', {})


def _signature(evidence):
    """The comparable shape of a subject's evidence — what "the subject changed" means at a version bump.

    Counts and timestamps are deliberately EXCLUDED: an outbound edge seen 900 times instead of 400 is the
    same subject, while the same edge gaining a new class, a trigger changing its `run_as`, or a profile
    gaining a verb is a different thing to rule on."""
    if not isinstance(evidence, dict):
        return ''
    volatile = {'observed_count', 'count', 'last_seen', 'first_seen', 'fire_count', 'traces_opened',
                'edges_written', 'sample_trace_id', 'proposal_hash', 'confirmed_by_previously', 'closure',
                'inherited_from', 'why', 'detail'}
    return json.dumps({k: v for k, v in sorted(evidence.items()) if k not in volatile},
                      sort_keys=True, default=str)


def _rows_for(manager, app=None, version=None):
    out = []
    for row in _rows(manager, DECISION_TABLE):
        if app is not None and getattr(row, 'app', '') != app:
            continue
        if version is not None and getattr(row, 'app_version', '') != version:
            continue
        out.append(row)
    return out


def decision_dict(row):
    return {'name': getattr(row, 'name', ''), 'app': getattr(row, 'app', ''),
            'appVersion': getattr(row, 'app_version', ''), 'release': getattr(row, 'release', ''),
            'kind': getattr(row, 'kind', ''), 'subject': getattr(row, 'subject', ''),
            'state': getattr(row, 'state', ''), 'evidence': _evidence(row),
            'derivedFrom': getattr(row, 'derived_from', ''),
            'confirmedBy': getattr(row, 'confirmed_by', ''), 'confirmedAt': getattr(row, 'confirmed_at', '')}


# ------------------------------------------------------------------ converge

def converge(manager, app, classes=None, save=True, version=None):
    """Converge the enumerated subjects into `SecurityDecision` rows for the app's CURRENT version.

    Idempotent, like `ensure_bindings`: a missing subject becomes an `open` row; evidence moves `open` to
    `suggested`; a second pass reports everything as `kept`. The two rules that matter:

      * a `confirmed` or `denied` row is NEVER touched — not its state, not its evidence, not its hash. A
        person's ruling outranks a derivation, exactly as an `admin` RoleAppBinding outranks the manifest.
      * a `stale` row keeps its state even when evidence arrives. Stale means *this changed and must be
        re-ruled*; letting a fresh suggestion clear it would let a release ship on a ruling nobody re-made.

    `version` overrides the version the rows are written against. It exists for `bump_version`, which
    converges the enumeration onto the version being bumped TO — on a real instance the two are the same
    string, because a bump happens exactly when the manifest version changed.

    Returns `{ok, app, app_version, release, created, suggested, kept, skipped_human, sources}`."""
    from polariapps.objects.apps_security.SecurityDecision import SecurityDecision
    report = enumerate_subjects(manager, app, classes)
    if not report.get('ok'):
        return report
    version = version or report['app_version']
    release = report['release']
    out = {'ok': True, 'app': app, 'app_version': version, 'release': release,
           'created': [], 'suggested': [], 'kept': [], 'skipped_human': [],
           'classes': report['classes'], 'sources': report['sources']}
    for subject in report['subjects']:
        kind, subj = subject['kind'], subject['subject']
        name = decision_name(app, version, kind, subj)
        row = _find(manager, DECISION_TABLE, name)
        wanted_state = 'suggested' if subject['suggested'] else 'open'
        if row is None:
            _new_row(manager, DECISION_TABLE, SecurityDecision, {
                'name': name, 'app': app, 'app_version': version, 'release': release,
                'kind': kind, 'subject': subj, 'state': wanted_state,
                'evidence_json': json.dumps(subject['evidence'], default=str),
                'derived_from': subject['derived_from'], 'confirmed_by': '', 'confirmed_at': ''})
            out['created'].append(name)
            if wanted_state == 'suggested':
                out['suggested'].append(name)
            continue
        state = getattr(row, 'state', 'open')
        if state in HUMAN_STATES:
            out['skipped_human'].append(name)
            continue
        changed = False
        # A refresh brings today's evidence, but it must not erase WHY the row is inherited or stale: those
        # keys were written by the version bump and are the whole account of what was carried forward.
        merged = dict(subject['evidence'])
        previous = _evidence(row)
        for key in CARRIED_EVIDENCE_KEYS:
            if key in previous:
                merged[key] = previous[key]
        evidence = json.dumps(merged, default=str)
        if getattr(row, 'evidence_json', '') != evidence:
            row.evidence_json = evidence
            changed = True
        if subject['derived_from'] and getattr(row, 'derived_from', '') != subject['derived_from']:
            row.derived_from = subject['derived_from']
            changed = True
        if state in ('open', 'suggested') and state != wanted_state:
            row.state = wanted_state
            changed = True
            if wanted_state == 'suggested':
                out['suggested'].append(name)
        if release and getattr(row, 'release', '') != release:
            row.release = release
            changed = True
        if name not in out['suggested']:
            out['kept'].append(name)
        if changed and save:
            _save(manager, row)
    return out


# ------------------------------------------------------------------ the version bump

def changed_subjects(manager, app, old_version, classes=None):
    """Which subjects the CURRENT version changed, relative to the rows recorded at `old_version`.

    Two sources, as the design asks: the evidence DIFF (a trigger's `run_as`, a profile's verbs, a flow's
    classes — anything but counts and timestamps, see `_signature`), and the CLASS LIST diff, read from the
    old version's own `owner-policy` rows (one per class at that version) against the app's class list now.
    Every subject of a class that is new in this version counts as changed, because nobody has ever ruled on
    it in this app at all."""
    report = enumerate_subjects(manager, app, classes)
    if not report.get('ok'):
        return set()
    old_rows = {(getattr(r, 'kind', ''), getattr(r, 'subject', '')): r
                for r in _rows_for(manager, app, old_version)}
    old_classes = {subject for (kind, subject) in old_rows if kind == 'owner-policy'}
    new_classes = set(report['classes']) - old_classes
    changed = set()
    for subject in report['subjects']:
        key = (subject['kind'], subject['subject'])
        row = old_rows.get(key)
        if row is None:
            continue                                     # brand new subject: converge gives it a fresh `open` row
        if any(cls in subject['subject'] for cls in new_classes):
            changed.add(subject['subject'])
            continue
        if _signature(subject['evidence']) != _signature(_evidence(row)):
            changed.add(subject['subject'])
    return changed


def bump_version(manager, app, old_version, new_version, changed=None, classes=None, save=True):
    """Carry `old_version`'s rulings into `new_version` (design §6).

    Every row of the old version becomes a row of the new one: `inherited` when the subject is unchanged —
    keeping the confirmer's `sub` and timestamp, because that IS the ruling being carried — and `stale` when
    the subject changed, with the confirmer CLEARED, because a stale row is one nobody has ruled on in this
    version. Then `converge` runs so subjects that are new in this version appear as `open`.

    `changed` may be given (a caller who already knows what moved); when it is None it is computed by
    `changed_subjects` from the evidence diff plus the class-list diff."""
    from polariapps.objects.apps_security.SecurityDecision import SecurityDecision
    if not new_version or old_version == new_version:
        return {'ok': False, 'status': 400,
                'error': 'a bump needs two different versions (from=<old> to=<new>)'}
    if changed is None:
        changed = changed_subjects(manager, app, old_version, classes)
    changed = set(changed or ())
    release, _source = current_release(manager)
    out = {'ok': True, 'app': app, 'from': old_version, 'to': new_version,
           'inherited': [], 'stale': [], 'kept': []}
    for row in _rows_for(manager, app, old_version):
        kind, subject = getattr(row, 'kind', ''), getattr(row, 'subject', '')
        name = decision_name(app, new_version, kind, subject)
        if _find(manager, DECISION_TABLE, name) is not None:
            out['kept'].append(name)
            continue
        is_stale = subject in changed
        evidence = _evidence(row)
        evidence['inherited_from'] = old_version
        if is_stale:
            evidence['stale_because'] = 'the subject changed in this version — it must be re-ruled'
            if getattr(row, 'confirmed_by', ''):
                evidence['confirmed_by_previously'] = getattr(row, 'confirmed_by', '')
        _new_row(manager, DECISION_TABLE, SecurityDecision, {
            'name': name, 'app': app, 'app_version': new_version, 'release': release,
            'kind': kind, 'subject': subject, 'state': 'stale' if is_stale else 'inherited',
            'evidence_json': json.dumps(evidence, default=str),
            'derived_from': f'inherited:{old_version}',
            'confirmed_by': '' if is_stale else getattr(row, 'confirmed_by', ''),
            'confirmed_at': '' if is_stale else getattr(row, 'confirmed_at', '')})
        out['stale' if is_stale else 'inherited'].append(name)
    out['converged'] = converge(manager, app, classes, save=save, version=new_version)
    return out


# ------------------------------------------------------------------ the human act

def confirm(manager, app, kind, subject, user_info, decision='confirmed', proposal_hash='',
            app_version_=None, classes=None, note=''):
    """THE ONE HUMAN CONFIRMATION of one subject (his ruling, design §6).

    Refuses 401 without a Keycloak `sub` and 403 without an ADMIN_ROLES role: a ruling that nobody is
    accountable for is not a ruling. Records the `sub` ALONE (D18-1 — never a username), the timestamp, and
    the hash of the proposal the person was looking at, so what was agreed to can be shown to have changed
    since.

    The subject must EXIST in the enumeration: converge runs first, and a subject nothing enumerates is a 404
    naming the enumeration rather than a row invented to match the request."""
    if decision not in HUMAN_STATES:
        return {'ok': False, 'status': 400, 'error': f'decision must be one of {list(HUMAN_STATES)}'}
    if kind not in DECISION_KINDS:
        return {'ok': False, 'status': 400, 'error': f'kind must be one of {list(DECISION_KINDS)}'}
    sub = str((user_info or {}).get('sub') or '') if isinstance(user_info, dict) else ''
    if not sub:
        return {'ok': False, 'status': 401,
                'error': 'sign in first — a security decision records WHO confirmed it, and a person here is '
                         'a Keycloak subject id (nothing confirms itself)'}
    groups, _sources = caller_groups(user_info)
    if not (set(ADMIN_ROLES) & set(groups)):
        return {'ok': False, 'status': 403,
                'error': 'administrators only (ADMIN_ROLES: ' + ', '.join(sorted(ADMIN_ROLES))
                         + ') — confirming a security decision is an administrative act'}
    converged = converge(manager, app, classes, version=app_version_)
    if not converged.get('ok'):
        return converged
    version = app_version_ or converged['app_version']
    name = decision_name(app, version, kind, subject)
    row = _find(manager, DECISION_TABLE, name)
    if row is None:
        return {'ok': False, 'status': 404,
                'error': f'nothing enumerates {kind} {subject!r} for {app}@{version} — '
                         'GET /api/apps/security/decisions lists what this version owes a ruling on'}
    evidence = _evidence(row)
    if proposal_hash:
        evidence['proposal_hash'] = proposal_hash
    if note:
        evidence['note'] = note
    row.state = decision
    row.confirmed_by = sub
    row.confirmed_at = _now()
    row.evidence_json = json.dumps(evidence, default=str)
    _save(manager, row)
    return {'ok': True, 'decision': decision_dict(row),
            'note': 'a confirmation is a PERSON\'s act: it records their Keycloak sub and the hash of the '
                    'proposal they saw. Nothing here enforces anything — enforcement stays the '
                    'AppPermissionProfile gate\'s posture knob.'}


# ------------------------------------------------------------------ the read

def decisions(manager, app=None, kind=None, state=None, converge_first=True, classes=None):
    """The rows behind `GET /api/apps/security/decisions`, filtered by app / kind / state.

    `converge_first` keeps a read current with the app (the `RoleAppBinding` discipline), so the list a person
    rules from is never last boot's picture."""
    if kind and kind not in DECISION_KINDS:
        return {'ok': False, 'status': 400, 'error': f'kind must be one of {list(DECISION_KINDS)}'}
    if state and state not in DECISION_STATES:
        return {'ok': False, 'status': 400, 'error': f'state must be one of {list(DECISION_STATES)}'}
    converged = None
    if converge_first and app:
        converged = converge(manager, app, classes)
        if not converged.get('ok'):
            return converged
    rows = [decision_dict(r) for r in _rows_for(manager, app)]
    if kind:
        rows = [r for r in rows if r['kind'] == kind]
    if state:
        rows = [r for r in rows if r['state'] == state]
    rows.sort(key=lambda r: (r['app'], r['appVersion'], r['kind'], r['subject']))
    return {'ok': True, 'decisions': rows, 'kinds': list(DECISION_KINDS), 'states': list(DECISION_STATES),
            'appVersion': (converged or {}).get('app_version', ''),
            'sources': (converged or {}).get('sources', {}),
            'note': 'subjects are enumerated FROM THE APP, so an `open` row is a real gap, not silence; '
                    'only a person writes `confirmed` or `denied`'}
