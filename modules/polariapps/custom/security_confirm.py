"""
@cross-cutting
@module polariapps.custom.security_confirm

ct-8 — THE ONE HUMAN CONFIRMATION ON THE CONCRETE STEP (design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6, his
ruling 2026-09-18).

    *"Every item the analysis proposes for enforcement … carries its evidence … and the proposal is applied by
    a PERSON: the concrete step is a confirmation with a `confirmed_by` sub and the proposal's hash, never an
    automatic write; nothing widens itself and nothing flips to `enforce` on its own."*

`confirm_profile()` is that step, and it is deliberately the ONLY place in this arc where a proposal becomes a
ruling in bulk. It does four things, in this order, and refuses at the first that fails:

  1. VERIFIES THE PERSON — a Keycloak `sub` (401 without one) with an ADMIN_ROLES role (403 without one).
     A profile published by nobody accountable is not confirmed by publishing it.
  2. HASHES WHAT THEY SAW — `sha256` over the canonical JSON of the proposal: the caller's `proposed_profile`
     when they are confirming an analysis's suggestion, otherwise the profile ROW as it stands right now. The
     hash goes into every row's evidence, so a later reader can tell that what was agreed to has changed.
  3. RECORDS ONE `SecurityDecision` PER CLASS × VERB × GROUP as `confirmed`, through the same
     `security_decisions.confirm` one-subject path — same refusals, same `confirmed_by`, same timestamp.
  4. ONLY THEN calls the security module's existing concrete mark
     (`security.custom.security_observe.mark_prototype(manager, role, 'concreted', profile=…, by=<sub>)`)
     through a GUARDED import. That function is not changed by this slice and not owned by this module; an
     instance without the security module records its decisions and says the mark was unavailable.

WHAT THIS DOOR DOES NOT DO: it does not enforce, widen or flip a posture. Enforcement stays
`accessControl.app_permissions_gate` and its `POLARI_APP_PERMISSIONS=off|advisory|enforce` knob, which only a
person sets. Confirming a decision records that a person agreed with an analysis — nothing more, on purpose.

@consumers
  - polariapps.apps_api (POST /api/apps/security/confirm-profile) · polariapps.apps_selftest
"""

import hashlib
import json

from polariapps.custom.apps_roles import _rows
from polariapps.custom.security_decisions import confirm, converge
from polariapps.custom.security_subjects import ANY_GROUP
from polariapps.objects.apps_permissions._shared import ADMIN_ROLES, CRUDE_VERBS, caller_groups


def proposal_hash(proposal):
    """`sha256:<16 hex>` over the canonical JSON of what the person was shown. Short on purpose: it is a
    fingerprint to compare, not a secret, and it has to fit in a table cell."""
    blob = json.dumps(proposal, sort_keys=True, default=str)
    return 'sha256:' + hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


def _profile_row(manager, name):
    for row in _rows(manager, 'AppPermissionProfile'):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _loads(row, attr, default):
    try:
        text = getattr(row, attr, '') or ''
        value = json.loads(text) if text else default
        return value if isinstance(value, type(default)) else default
    except Exception:  # noqa: BLE001
        return default


def profile_proposal(manager, row):
    """The canonical shape of a profile proposal — what gets hashed when the caller sends no explicit one."""
    return {'profile': getattr(row, 'name', ''), 'app': getattr(row, 'app_name', ''),
            'groups': sorted(str(g).lstrip('/') for g in _loads(row, 'kc_groups_json', [])),
            'verbs': sorted(v for v in _loads(row, 'verbs_json', []) if v in CRUDE_VERBS),
            'extraClasses': sorted(str(c) for c in _loads(row, 'extra_classes_json', [])),
            'published': bool(getattr(row, 'published', True))}


def confirm_profile(manager, profile, user_info, role='', proposed_profile=None, classes=None, mark=True):
    """Confirm a whole published profile — the concrete step, done by a person (see the module docstring).

    Returns `{ok, profile, app, appVersion, proposalHash, confirmed: [...], refused: [...], securityMark}`.
    `securityMark` is the security module's answer to `mark_prototype(..., 'concreted')` when a `role` was
    given, or an honest `{'ok': False, 'why': …}` when the module is absent — this door never fakes it."""
    sub = str((user_info or {}).get('sub') or '') if isinstance(user_info, dict) else ''
    if not sub:
        return {'ok': False, 'status': 401,
                'error': 'sign in first — concreting a profile is a PERSON\'s confirmation, and a person here '
                         'is a Keycloak subject id'}
    groups, _sources = caller_groups(user_info)
    if not (set(ADMIN_ROLES) & set(groups)):
        return {'ok': False, 'status': 403,
                'error': 'administrators only (ADMIN_ROLES: ' + ', '.join(sorted(ADMIN_ROLES))
                         + ') — confirming what an analysis proposed is an administrative act'}
    row = _profile_row(manager, profile)
    if row is None:
        return {'ok': False, 'status': 404, 'error': f'no permission profile {profile!r}',
                'knownProfiles': sorted(getattr(r, 'name', '') for r in _rows(manager, 'AppPermissionProfile'))}
    app = getattr(row, 'app_name', '')
    if not app:
        return {'ok': False, 'status': 400,
                'error': f'profile {profile!r} names no app — a decision is recorded per app × version, so a '
                         'profile without an app has no version to be ruled for'}
    seen = proposed_profile if proposed_profile is not None else profile_proposal(manager, row)
    digest = proposal_hash(seen)
    converged = converge(manager, app, classes)
    if not converged.get('ok'):
        return converged
    version = converged['app_version']
    verbs = [v for v in _loads(row, 'verbs_json', []) if v in CRUDE_VERBS]
    holders = sorted(str(g).lstrip('/') for g in _loads(row, 'kc_groups_json', [])) or [ANY_GROUP]
    covered = sorted(set(converged['classes'])
                     | {str(c) for c in _loads(row, 'extra_classes_json', [])})
    confirmed, refused = [], []
    for cls in covered:
        for verb in verbs:
            for group in holders:
                result = confirm(manager, app, 'profile-verb', f'{cls}:{verb}@{group}', user_info,
                                 decision='confirmed', proposal_hash=digest, app_version_=version,
                                 classes=classes, note=f'confirmed with profile {profile}')
                if result.get('ok'):
                    confirmed.append(result['decision']['name'])
                else:
                    refused.append({'subject': f'{cls}:{verb}@{group}', 'error': result.get('error', ''),
                                    'status': result.get('status', 400)})
    security_mark = {'ok': False, 'why': 'no role given — the concrete mark belongs to a RolePrototype'}
    if mark and role:
        try:
            from security.custom.security_observe import mark_prototype
            security_mark = mark_prototype(manager, role, 'concreted', profile=profile, by=sub)
        except Exception as exc:  # noqa: BLE001
            security_mark = {'ok': False,
                             'why': f'the security module\'s concrete mark is unavailable '
                                    f'({exc.__class__.__name__}: {exc}) — the decisions above were still '
                                    'recorded'}
    return {'ok': True, 'profile': profile, 'app': app, 'appVersion': version, 'proposalHash': digest,
            'role': role, 'confirmed': confirmed, 'refused': refused, 'securityMark': security_mark,
            'note': 'this is the ONE human confirmation of what the analysis suggested: it records a `sub`, a '
                    'timestamp and the proposal\'s hash on every class × verb the profile covers, and then '
                    'calls the security module\'s existing concrete mark. Nothing here enforces or widens '
                    'anything — enforcement stays the app-permissions gate\'s posture knob, set by a person.'}
