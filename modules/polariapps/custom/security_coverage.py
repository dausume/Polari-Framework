"""
@cross-cutting
@module polariapps.custom.security_coverage

ct-8 — COVERAGE PER APP × VERSION (design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6).

His rulings 2026-09-18: *"track how many objects have any kind of security coverage and how much if any"* and
*"track security policy decisions of different types and how many have been covered per app, since security
must be worked on at a per-app basis and per each version release"*.

So coverage is counted in two currencies at once, because "how many objects" has two honest answers:

  DECISIONS  by kind × state — how many rulings this app version owes, and how many have been made.
  INSTANCES  the live row count under each class the app carries — so "23 MealEntry rows sit under a class
             nobody has ruled on" is visible, not only "one class is open".

`coverage` for an app version reads none / partial / full, exactly as the design says:

  full     no `open` and no `stale` rows of ANY kind — every subject has been ruled, inherited or suggested-
           and-confirmed. This is the only state a release gate may treat as covered.
  none     nothing has been ruled at all (no confirmed, denied or inherited row).
  partial  anything in between.

The totals sit on `/display/apps-security` as configured tables (no raw JSON, no new component) and the
release gate can cite them: a release carrying `stale` rows says so.

@consumers
  - polariapps.apps_api (GET /api/apps/security/coverage) · polariapps.apps_page · polariapps.apps_selftest
"""

from polariapps.custom.apps_roles import _rows
from polariapps.custom.security_decisions import DECISION_TABLE, converge
from polariapps.custom.security_subjects import app_row
from polariapps.objects.apps_permissions._shared import classes_for_app
from polariapps.objects.apps_security._shared import DECISION_KINDS, DECISION_STATES, UNRULED_STATES

#: states that mean somebody (or the previous version's somebody) HAS ruled
RULED_STATES = ('confirmed', 'denied', 'inherited')


def _empty_counts():
    return {state: 0 for state in DECISION_STATES}


def _level(counts):
    """none / partial / full for one app version's state counts (design §6)."""
    total = sum(counts.values())
    if not total:
        return 'none'
    if not any(counts[state] for state in UNRULED_STATES):
        return 'full'
    if not any(counts[state] for state in RULED_STATES):
        return 'none'
    return 'partial'


def instance_counts(manager, classes):
    """`{Class: live row count}` — the "how many objects" half of his ask, answered in rows of data.

    A class the instance carries no rows of counts 0 rather than being dropped: an empty class with an `open`
    owner policy is still an unruled class, and hiding it would flatter the coverage number."""
    tables = getattr(manager, 'objectTables', None) or {}
    return {cls: len(tables.get(cls, {}) or {}) for cls in sorted(classes)}


def coverage(manager, app=None, converge_first=True, classes=None):
    """Coverage per app × version, plus the totals across every app.

    `converge_first` (and a named `app`) refreshes the enumeration before counting, so the number a person
    reads is about the app as it is now — the `RoleAppBinding` discipline again. Asked about every app, it
    counts the rows as they stand; converging every app on one read would walk every manifest.

    Returns `{ok, apps: [{app, appVersion, release, coverage, byKind, byState, total, instances,
    instanceTotal, classes}], totals, levels}`."""
    if app and converge_first:
        converged = converge(manager, app, classes)
        if not converged.get('ok'):
            return converged
    buckets = {}
    for row in _rows(manager, DECISION_TABLE):
        name, version = getattr(row, 'app', ''), getattr(row, 'app_version', '')
        if app and name != app:
            continue
        bucket = buckets.setdefault((name, version), {
            'app': name, 'appVersion': version, 'release': getattr(row, 'release', ''),
            'byKind': {kind: _empty_counts() for kind in DECISION_KINDS},
            'byState': _empty_counts(), 'total': 0})
        kind, state = getattr(row, 'kind', ''), getattr(row, 'state', '')
        if kind in bucket['byKind'] and state in bucket['byState']:
            bucket['byKind'][kind][state] += 1
            bucket['byState'][state] += 1
            bucket['total'] += 1
    out = []
    for (name, _version), bucket in sorted(buckets.items()):
        known = set(classes) if (classes is not None and name == app) else set(classes_for_app(manager, name))
        counts = instance_counts(manager, known)
        bucket['coverage'] = _level(bucket['byState'])
        bucket['classes'] = sorted(known)
        bucket['instances'] = counts
        bucket['instanceTotal'] = sum(counts.values())
        bucket['unruled'] = {state: bucket['byState'][state] for state in UNRULED_STATES}
        bucket['appKnown'] = app_row(manager, name) is not None
        out.append(bucket)
    totals = _empty_counts()
    for bucket in out:
        for state, n in bucket['byState'].items():
            totals[state] += n
    return {'ok': True, 'app': app or '', 'apps': out, 'totals': totals,
            'appVersions': len(out), 'levels': list(('none', 'partial', 'full')),
            'kinds': list(DECISION_KINDS), 'states': list(DECISION_STATES),
            'note': 'full = no `open` and no `stale` rows of any kind; a release carrying `stale` rows is '
                    'shipping on last version\'s rulings for something this version changed'}
