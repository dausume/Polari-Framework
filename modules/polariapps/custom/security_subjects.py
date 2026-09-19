"""
@cross-cutting
@module polariapps.custom.security_subjects

ct-8 — WHAT AN APP VERSION OWES A RULING ON (design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6).

The enumeration half of the decision ledger. His rule, written into the design: subjects are enumerated
**from the app, not from what happened to be observed**, so an `open` decision row is a REAL GAP rather than
silence. Eight kinds, each from a source that belongs to the app itself:

  profile-verb    every class the app carries × the five CRUDE verbs × the groups touching it
                  (`AppPermissionProfile` rows for the app + `PermissionObservation` groups where present;
                  `*` when nothing yet names a group — somebody still has to say who)
  owner-policy    every class, once — opted in to owner-defined permissions, or explicitly not
  trigger-run-as  every `EventTrigger` whose source/inputs/solution touch one of the app's classes
  flow-declared   every `app.flows` entry in the manifests of the app's modules (design §9), PLUS one
                  `flow:undeclared:…` subject per observed external system nothing declared (a finding)
  role-binding    every `app.roles` entry in those manifests, the app's personas, and any `RoleAppBinding`
                  that already names the app
  outbound        every observed `external:`/`peer:` `CausalEdge` whose cause is one of the app's classes
  inbound         every `InboundPolicy` row (ct-9 builds those rows; until then this is honestly empty)
  trace-coverage  every class, once — has it ever been a `TraceTarget`, and what does its closure reach

NO HARD DEPENDENCY ON THE SECURITY MODULE. Rows that live there (`PermissionObservation`, `OwnedClassPolicy`,
`TraceTarget`, `CausalEdge`, `InboundPolicy`) are read straight out of the manager's tables, and
`security.custom.security_trace.closure` is called through a guarded import that tolerates its absence. Every
kind reports the SOURCE it used in `sources`, so an instance without security enumerates the same subjects and
says which evidence was unavailable rather than pretending there was none.

@consumers
  - polariapps.custom.security_decisions (converge / bump / confirm)
  - polariapps.custom.security_coverage · polariapps.apps_selftest
"""

import json
import os

from polariapps.objects.apps_permissions._shared import CRUDE_VERBS, classes_for_app

#: the wildcard group: the class × verb needs a ruling and nothing yet says WHICH group should hold it
ANY_GROUP = '*'


def _tables(manager):
    return getattr(manager, 'objectTables', None) or {}


def _table_rows(manager, table):
    """Rows of a class, WITHOUT requiring the class to exist here. A table the instance does not carry is
    simply empty — that is how this module reads security's rows without importing security."""
    from polariapps.custom.apps_roles import _rows
    return _rows(manager, table)


def _json(row, attr, default):
    try:
        text = getattr(row, attr, '') or ''
        value = json.loads(text) if text else default
        return value if isinstance(value, type(default)) else default
    except Exception:  # noqa: BLE001
        return default


def _subject(kind, subject, evidence=None, derived_from='', suggested=False):
    return {'kind': kind, 'subject': subject, 'evidence': evidence or {},
            'derived_from': derived_from, 'suggested': bool(suggested)}


# ------------------------------------------------------------------ the app's version and release

def app_row(manager, app):
    for row in _table_rows(manager, 'PolariAppDefinition'):
        if getattr(row, 'name', '') == app:
            return row
    return None


def app_modules(manager, app):
    row = app_row(manager, app)
    if row is None:
        return []
    return [str(m).split('.')[0] for m in _json(row, 'modules_json', [])]


def _manifest(pkg):
    try:
        from moduleService import manifests
        manifest = manifests.load(pkg)
    except Exception:  # noqa: BLE001
        return None
    return manifest if isinstance(manifest, dict) else None


def app_version(manager, app):
    """`(version, source)` for a Polari-App — the unit security is worked on per (his ruling).

    A Polari-App is a CONFIGURATION OF MODULES, so it rarely has a manifest of its own. Three readings, in
    order, each stated in `source` so a coverage table never implies a version it invented:

      1. a module manifest whose id/package IS the app name -> its `version` (the Standard Polari App case);
      2. otherwise the app's MODULE SET: `pkg@version` for each module it carries, joined and digested as
         `set-<8 hex>`. A module version bump therefore changes the app version, which is exactly when last
         release's rulings must be re-examined;
      3. otherwise `unversioned` — an app whose modules carry no readable manifest still gets one coherent
         bucket to collect rulings in, rather than silently sharing one with a different version.
    """
    own = _manifest(app)
    if own and str(own.get('version') or '').strip():
        return str(own['version']).strip(), f'manifest:{app}'
    parts = []
    for pkg in sorted(set(app_modules(manager, app))):
        manifest = _manifest(pkg)
        version = str((manifest or {}).get('version') or '').strip()
        if version:
            parts.append(f'{pkg}@{version}')
    if parts:
        import hashlib
        digest = hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()[:8]
        return f'set-{digest}', 'module-set:' + ','.join(parts)
    return 'unversioned', 'no readable module manifest'


def current_release(manager):
    """`(release, source)` — the Polari CALENDAR TAG this instance is running (POLARI_VERSIONING_PLAN: one
    calendar tag per release, `ReleaseManifest` rows beneath it).

    `ReleaseManifest` is PLANNED, not built (it exists in AI-Notes/plans/POLARI_VERSIONING_PLAN.md and nowhere
    in the tree), so this reads a row of that class if some future slice ever lands one, then the
    `POLARI_RELEASE` knob, and otherwise answers '' — an unstamped release, which the coverage table shows as
    such rather than guessing."""
    rows = _table_rows(manager, 'ReleaseManifest')
    if rows:
        best = sorted(rows, key=lambda r: str(getattr(r, 'tag', '') or getattr(r, 'name', '')))[-1]
        tag = str(getattr(best, 'tag', '') or getattr(best, 'name', '') or '')
        if tag:
            return tag, 'ReleaseManifest'
    env = str(os.environ.get('POLARI_RELEASE', '') or '').strip()
    if env:
        return env, 'POLARI_RELEASE'
    return '', 'no release stamped (ReleaseManifest is planned, not built)'


# ------------------------------------------------------------------ per-kind collectors

def _groups_for(manager, app, classes):
    """`({class: {group: evidence}}, profiles)` — the groups that TOUCH the app's classes.

    Two sources, both the app's own: the `AppPermissionProfile` rows written for this app (what somebody
    intends), and the `PermissionObservation` rows recorded in dev (what actually happened). A class nothing
    names gets the `*` group, because "nobody has said who may do this" is itself a ruling that is missing."""
    touching, profiles = {}, []
    for row in _table_rows(manager, 'AppPermissionProfile'):
        if getattr(row, 'app_name', '') != app:
            continue
        published = bool(getattr(row, 'published', True))
        verbs = [v for v in _json(row, 'verbs_json', []) if v in CRUDE_VERBS]
        groups = [str(g).lstrip('/') for g in _json(row, 'kc_groups_json', [])] or [ANY_GROUP]
        covered = set(classes) | {str(c) for c in _json(row, 'extra_classes_json', [])}
        profiles.append({'name': getattr(row, 'name', ''), 'published': published,
                         'verbs': verbs, 'groups': groups})
        for cls in covered:
            for group in groups:
                entry = touching.setdefault(cls, {}).setdefault(group, {'profiles': [], 'verbs': [], 'observed': {}})
                entry['profiles'].append(getattr(row, 'name', ''))
                for verb in verbs:
                    if published and verb not in entry['verbs']:
                        entry['verbs'].append(verb)
    for row in _table_rows(manager, 'PermissionObservation'):
        cls = getattr(row, 'class_name', '')
        if cls not in classes:
            continue
        for group in [g.strip() for g in str(getattr(row, 'groups', '') or '').split(',') if g.strip()]:
            entry = touching.setdefault(cls, {}).setdefault(group, {'profiles': [], 'verbs': [], 'observed': {}})
            verb = getattr(row, 'verb', '')
            entry['observed'][verb] = entry['observed'].get(verb, 0) + int(getattr(row, 'count', 0) or 0)
    for cls in classes:
        # The `*` group means "nobody has said WHO may do this" — so it is added only where nothing else
        # names a group. A class a profile or an observation already reaches is ruled per real group; adding
        # `*` beside them would leave every app version with rulings nobody could ever sensibly make.
        if not touching.get(cls):
            touching.setdefault(cls, {})[ANY_GROUP] = {'profiles': [], 'verbs': [], 'observed': {}}
    return touching, profiles


def profile_verb_subjects(manager, app, classes):
    """`Class:verb@group` — the app's classes × the five verbs × the groups touching them.

    `suggested` when a PUBLISHED profile grants the verb to that group, or when dev observations recorded the
    act: the analysis has proposed something and carries its evidence. It is never `confirmed` here — a
    published profile is a proposal until a person confirms it with their `sub` (design §6)."""
    touching, _profiles = _groups_for(manager, app, classes)
    out = []
    for cls in sorted(classes):
        for group, evidence in sorted(touching.get(cls, {}).items()):
            for verb in CRUDE_VERBS:
                granted = verb in evidence['verbs']
                observed = int(evidence['observed'].get(verb, 0) or 0)
                out.append(_subject(
                    'profile-verb', f'{cls}:{verb}@{group}',
                    {'granted_by_published_profile': granted, 'observed_count': observed,
                     'profiles': sorted(set(evidence['profiles']))},
                    derived_from=('AppPermissionProfile:' + ','.join(sorted(set(evidence['profiles'])))
                                  if granted and evidence['profiles'] else
                                  ('PermissionObservation' if observed else '')),
                    suggested=granted or observed > 0))
    return out


def owner_policy_subjects(manager, classes):
    """One subject per class: is it opted in to owner-defined permissions, or explicitly not?

    An ABSENT `OwnedClassPolicy` row is `open`, never `suggested` — "nobody ever considered it" is exactly the
    gap this ledger exists to show (op-0's ruling is that owner-defined is opted in per class, so the default
    is a decision somebody should have taken knowingly)."""
    policies = {getattr(r, 'class_name', '') or getattr(r, 'name', ''): r
                for r in _table_rows(manager, 'OwnedClassPolicy')}
    out = []
    for cls in sorted(classes):
        row = policies.get(cls)
        out.append(_subject(
            'owner-policy', cls,
            {'policy_row': row is not None,
             'enabled': bool(getattr(row, 'enabled', False)) if row is not None else False,
             'owner_field': getattr(row, 'owner_field', '') if row is not None else ''},
            derived_from='OwnedClassPolicy' if row is not None else '',
            suggested=row is not None))
    return out


def trigger_subjects(manager, classes):
    """`trigger:<name>` for every `EventTrigger` whose source, inputs or solution touch one of the classes.

    The authority matters more than the trigger: `run_as=definer` (polariNoCode's D11 default) means the
    solution writes with the DEFINER's reach, not the caller's, which is precisely the implicit permission
    the closure of design §6 exists to make explicit. The evidence carries it so the person confirming sees
    what they are agreeing to."""
    solutions = {getattr(r, 'name', ''): r for r in _table_rows(manager, 'SolutionDefinition')}
    out = []
    for row in _table_rows(manager, 'EventTrigger'):
        name = getattr(row, 'name', '')
        if not name:
            continue
        haystack = ' '.join(str(getattr(row, f, '') or '') for f in
                            ('source_json', 'inputs_json', 'description', 'notes'))
        solution = solutions.get(getattr(row, 'solution_name', '') or '')
        if solution is not None:
            haystack += ' ' + ' '.join(str(v) for v in vars(solution).values())
        touched = sorted(c for c in classes if c in haystack)
        if not touched:
            continue
        out.append(_subject(
            'trigger-run-as', f'trigger:{name}',
            {'solution': getattr(row, 'solution_name', ''), 'run_as': getattr(row, 'run_as', ''),
             'enabled': bool(getattr(row, 'enabled', True)), 'touches': touched,
             'fire_count': int(getattr(row, 'fire_count', 0) or 0)},
            derived_from='EventTrigger', suggested=True))
    return out


def _app_flow_stanzas(manager, app):
    """`[(module, flow)]` from every module manifest's `app.flows` (design §9). The stanza MAY NOT EXIST yet —
    it is designed, and ct-8 does not build it; an absent stanza contributes nothing and is reported."""
    out = []
    for pkg in sorted(set(app_modules(manager, app))):
        manifest = _manifest(pkg)
        flows = ((manifest or {}).get('app') or {}).get('flows')
        if not isinstance(flows, list):
            continue
        for flow in flows:
            if isinstance(flow, dict):
                out.append((pkg, flow))
    return out


def observed_external(manager, classes):
    """`{subject: evidence}` for the `external:`/`peer:` edges of the causal map (Ledger A, ct-1/ct-3) whose
    CAUSE is one of the app's classes.

    `polariApiServer.outbound` exposes the wrapper's vocabulary (`SYSTEM_KINDS`, `MEANS`) but no registry of
    known SITES, so there is nothing to enumerate from it; the honest enumeration of what this app sends is
    the set of edges the wrapper actually recorded, plus — through the `flow-declared` kind — whatever the
    manifests declare. Stated rather than silently narrowed."""
    out = {}
    for row in _table_rows(manager, 'CausalEdge'):
        effect = str(getattr(row, 'effect', '') or '')
        if not (effect.startswith('external:') or effect.startswith('peer:')):
            continue
        cause = str(getattr(row, 'cause', '') or '')
        target = str(getattr(row, 'target', '') or '')
        cause_class = cause.split(':')[1] if cause.startswith('object:') and ':' in cause[7:] else ''
        if cause_class not in classes and target not in classes:
            continue
        means = str(getattr(row, 'means', '') or '')
        subject = effect + (':' + means if means else '')
        entry = out.setdefault(subject, {'count': 0, 'last_seen': '', 'classes': [], 'detail': '',
                                         'sample_trace_id': ''})
        entry['count'] += int(getattr(row, 'count', 0) or 0)
        entry['last_seen'] = max(entry['last_seen'], str(getattr(row, 'last_seen', '') or ''))
        entry['detail'] = str(getattr(row, 'detail', '') or '') or entry['detail']
        entry['sample_trace_id'] = str(getattr(row, 'sample_trace_id', '') or '') or entry['sample_trace_id']
        for cls in (cause_class, target):
            if cls in classes and cls not in entry['classes']:
                entry['classes'].append(cls)
    return out


def outbound_subjects(manager, classes):
    """`system:name:wire` per observed send out of the app's classes (design §5a's subject shape)."""
    return [_subject('outbound', subject, evidence, derived_from='CausalEdge (observed)', suggested=True)
            for subject, evidence in sorted(observed_external(manager, classes).items())]


def inbound_subjects(manager):
    """One subject per `InboundPolicy` row. ct-9 builds those rows from the middleware's dev observations;
    until then there are none, and `sources` says so rather than letting an empty list read as "nothing comes
    in"."""
    out = []
    for row in _table_rows(manager, 'InboundPolicy'):
        kind = str(getattr(row, 'source_kind', '') or 'source')
        source = str(getattr(row, 'source', '') or getattr(row, 'name', ''))
        out.append(_subject('inbound', f'inbound:{kind}:{source}',
                            {'state': getattr(row, 'state', ''), 'paths': _json(row, 'paths_json', [])},
                            derived_from='InboundPolicy', suggested=True))
    return out


def flow_subjects(manager, app, classes):
    """Declared flows (design §9) plus one `flow:undeclared:<system>` per observed external system that no
    manifest declares — the drift finding of §7, as a decision somebody has to rule on."""
    out, declared_systems = [], set()
    for pkg, flow in _app_flow_stanzas(manager, app):
        to = str(flow.get('to') or '')
        direction = str(flow.get('direction') or 'both')
        declared_systems.add(to)
        out.append(_subject('flow-declared', f'flow:{to}:{direction}',
                            {'module': pkg, 'classes': list(flow.get('classes') or [])},
                            derived_from='app.flows', suggested=True))
    for subject, evidence in sorted(observed_external(manager, classes).items()):
        system = subject.split(':')[1] if ':' in subject else subject
        if system in declared_systems:
            continue
        out.append(_subject('flow-declared', f'flow:undeclared:{system}',
                            dict(evidence, why='observed flowing, declared by no manifest (design §9 finding)'),
                            derived_from='CausalEdge (observed)', suggested=False))
    return out


def role_subjects(manager, app):
    """`role:<role>` — which roles this app belongs to: the manifests' `app.roles`, the app's own personas
    (§57's older fallback) and any `RoleAppBinding` that already names it."""
    out, seen = [], {}

    def _add(role, derived_from):
        role = str(role).strip()
        if not role or role in seen:
            return
        seen[role] = True
        out.append(_subject('role-binding', f'role:{role}', {'role': role},
                            derived_from=derived_from, suggested=True))

    for pkg in sorted(set(app_modules(manager, app))):
        for role in ((_manifest(pkg) or {}).get('app') or {}).get('roles') or []:
            _add(role, f'app.roles:{pkg}')
    row = app_row(manager, app)
    if row is not None:
        for persona in _json(row, 'personas_json', []):
            _add(persona, 'personas')
    for binding in _table_rows(manager, 'RoleAppBinding'):
        if app in _json(binding, 'apps_json', []):
            _add(getattr(binding, 'role', '') or getattr(binding, 'name', ''),
                 'RoleAppBinding:' + str(getattr(binding, 'source', '')))
    return out


def _closure_size(manager, class_name):
    """The reach of a class through Ledger A, when the security module offers it. `security_trace.closure` is
    ct-4's door and may not exist yet — its absence is not an error, it is simply less evidence."""
    try:
        import importlib
        # import_module, not `from security.custom import security_trace`: the leaf is resolved through
        # sys.modules, so ct-4's closure is picked up (or stood in for) wherever it actually lives.
        security_trace = importlib.import_module('security.custom.security_trace')
        closure = getattr(security_trace, 'closure', None)
        if closure is None:
            return None
        report = closure(manager, [f'object:{class_name}:read'])
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(report, dict):
        return None
    return {key: len(report.get(key) or []) for key in ('objects', 'events', 'solutions', 'peers', 'external')
            if isinstance(report.get(key), (list, tuple))}


def trace_subjects(manager, classes):
    """`trace:<Class>` — has this class ever been traced? A `TraceTarget` row is kept forever precisely so
    this can be answered as *not traced* instead of *nothing reaches it* (ct-1's coverage rule)."""
    targets = {getattr(r, 'class_name', '') or getattr(r, 'name', ''): r
               for r in _table_rows(manager, 'TraceTarget')}
    out = []
    for cls in sorted(classes):
        row = targets.get(cls)
        evidence = {'traced': row is not None,
                    'traces_opened': int(getattr(row, 'traces_opened', 0) or 0) if row is not None else 0,
                    'edges_written': int(getattr(row, 'edges_written', 0) or 0) if row is not None else 0,
                    'stopped_because': getattr(row, 'stopped_because', '') if row is not None else ''}
        reach = _closure_size(manager, cls) if row is not None else None
        if reach is not None:
            evidence['closure'] = reach
        out.append(_subject('trace-coverage', f'trace:{cls}', evidence,
                            derived_from='TraceTarget' if row is not None else '',
                            suggested=row is not None))
    return out


# ------------------------------------------------------------------ the enumeration itself

def enumerate_subjects(manager, app, classes=None):
    """Every subject the app version needs a ruling on — FROM THE APP, never only from what was observed.

    Returns `{ok, app, app_version, release, classes, subjects: [...], sources: {kind: what was read}}`.
    `sources` is the honest half: it names the table or stanza each kind came from, and says when one was
    absent, so an empty kind never reads as "there is nothing there"."""
    row = app_row(manager, app)
    if row is None:
        return {'ok': False, 'status': 404, 'error': f'no app {app!r}',
                'knownApps': sorted(getattr(r, 'name', '') for r in _table_rows(manager, 'PolariAppDefinition'))}
    known = set(classes) if classes is not None else set(classes_for_app(manager, app))
    version, version_source = app_version(manager, app)
    release, release_source = current_release(manager)
    subjects = (profile_verb_subjects(manager, app, known)
                + owner_policy_subjects(manager, known)
                + trigger_subjects(manager, known)
                + flow_subjects(manager, app, known)
                + role_subjects(manager, app)
                + outbound_subjects(manager, known)
                + inbound_subjects(manager)
                + trace_subjects(manager, known))
    flows = _app_flow_stanzas(manager, app)
    sources = {
        'profile-verb': 'AppPermissionProfile rows for this app + PermissionObservation groups'
                        + ('' if _table_rows(manager, 'PermissionObservation') else
                           ' (no observations recorded here — dev posture records them)'),
        'owner-policy': 'OwnedClassPolicy rows (absent row = open, by op-0\'s opt-in rule)',
        'trigger-run-as': 'EventTrigger rows whose source/inputs/solution name one of the classes'
                          + ('' if _table_rows(manager, 'EventTrigger') else ' (no triggers on this instance)'),
        'flow-declared': ('manifest app.flows (%d declared) + observed external systems nothing declares'
                          % len(flows)) + ('' if flows else
                                           ' — the app.flows stanza is designed (§9) and not yet written by any manifest'),
        'role-binding': 'manifest app.roles + the app\'s personas + RoleAppBinding rows naming the app',
        'outbound': 'CausalEdge external:/peer: edges caused by these classes; '
                    'polariApiServer.outbound exposes SYSTEM_KINDS/MEANS but no registry of known sites'
                    + ('' if _table_rows(manager, 'CausalEdge') else ' (the causal map is empty here)'),
        'inbound': 'InboundPolicy rows'
                   + ('' if _table_rows(manager, 'InboundPolicy') else
                      ' — none exist: the policy row itself is ct-9, so inbound is honestly unenumerated'),
        'trace-coverage': 'TraceTarget rows (+ security_trace.closure when the security module offers it)',
    }
    return {'ok': True, 'app': app, 'app_version': version, 'app_version_source': version_source,
            'release': release, 'release_source': release_source,
            'classes': sorted(known), 'subjects': subjects, 'sources': sources}
