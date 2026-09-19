"""
security.custom.security_closure — THE CLOSURE (ct-4): what a grant REALLY reaches.

Design: AI-Notes/designs/CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6. ct-1 records the MAP (`CausalEdge`: one counted
row per cause → effect by means) and ct-2 fills in the remaining seams. This module is the READING of that map:
walk it from a set of start nodes and say everything reachable, grouped, with the evidence and with the coverage
block that keeps an empty answer honest.

    closure(manager, start_nodes, *, max_depth=None) -> the dict documented on `closure` below

THE THREE QUESTIONS the doors ask (security_api):

    ?profile=<name>   start = the profile's explicit class × verb grants.  implicit = reachable − explicit.
                      *what you are really granting when you publish that profile*
    ?event=<ref>      start = one event node.  *what an event permission means*: the solution it runs and as
                      whom, everything that solution writes, and what those writes trigger in turn
    ?role=<role>      start = the role's OBSERVED endpoints and objects (§17b's role-play recording), so the
                      permissions admin sees the transitive effects beside the direct ones

**"NOT TRACED", NEVER "NOTHING"** (design §2). Only a class that has been a `TraceTarget` has edges at all, so
every answer carries `coverage` (every class ever traced) and `not_traced` (the classes this answer touches that
never have been). A branch that is empty because nobody armed that class says so.

**NOTHING ENFORCES ITSELF** (design §6, his ruling 2026-09-18). This module only discloses: no row is written, no
profile widened, no mode flipped. The confirmation step belongs to a PERSON, and the per-app decision ledger that
records it is ct-8's.

THE DEFINER RULE. A trigger runs its solution as the DEFINER (`event_triggers.py`, `run_as`), so a class × verb
can be reachable from a grant only because somebody else's solution runs with somebody else's authority. The walk
carries that as a flavour on every path: a node is `definer_only` when EVERY path that reaches it crossed a
`solution-run` edge whose `run_as` is `definer`. That is the K in `verify`'s transitive verdict.
"""

#: a walk never follows more than this many hops when no `max_depth` is given — the map is class-level and small
#: (hundreds of rows), but a cycle-free bound is still stated rather than assumed.
MAX_HOPS = 32

#: the belt-and-braces ceiling on queue pops, so a pathological map cannot spin the door
_MAX_STEPS = 200000

EDGE_OUT = ('cause', 'effect', 'means', 'detail', 'count', 'first_seen', 'last_seen',
            'min_depth', 'max_depth', 'run_as', 'sample_trace_id', 'target')


# ---- the walk -------------------------------------------------------------------------------------------

def closure(manager, start_nodes, *, max_depth=None):
    """Walk `CausalEdge` from `start_nodes` (cause → effect, transitively, cycle-safe) and group what is reached.

    THE SIGNATURE IS STABLE — ct-8 calls it by lazy import (`security_trace.closure(...)`) and reads the keys
    below. `start_nodes` is any iterable of node strings in the design §2 vocabulary (`endpoint:…`,
    `object:Class:verb`, `event:…`, `solution:…`, `peer:…`, `external:…`); `max_depth` is HOPS from the start
    (None = MAX_HOPS).

    Returns::

        {'start':      [{'node', 'kind', 'seen'}],            the start set, and whether the map knows each
         'objects':    [{'node','class','verb','origin','definer_only','evidence'}],
         'events':     [{'node','event','origin','definer_only','evidence'}],
         'solutions':  [{'node','name','run_as','origin','definer_only','evidence'}],
         'peers':      [{'node','peer','means','classes','origin','definer_only','evidence'}],
         'external':   [{'node','system','name','wire','classes','origin','definer_only','evidence'}],
         'other':      [{'node','kind',…}],                   schedule / ai / boot nodes, said rather than dropped
         'edges':      [the distinct map rows the walk crossed],
         'coverage':   security_trace.coverage(manager),      every class that has EVER been a target
         'not_traced': [classes this answer touches that have never been traced],
         'counts':     {'objects','events','solutions','peers','external','edges','definer_only'},
         'max_depth':  the hop bound actually applied,
         'truncated':  True when the hop bound stopped the walk with work left}

    `evidence` is `{count, first_seen, last_seen, min_depth, sample_trace_id, target, seen}` — the counts behind
    the claim, the sample trace to look the instances up with (the journal), and the trace target that recorded
    it. `origin` is `observed` for a start node and `closure` for everything the walk found; a caller whose start
    set is DECLARED (a profile's grants) re-stamps its own start items `declared` — see `mark_origin`.
    """
    from security.custom.security_trace import coverage as _coverage, edges as _map_rows

    starts = [n for n in dict.fromkeys(str(x or '') for x in (start_nodes or [])) if n]
    start_set = set(starts)
    limit = MAX_HOPS if max_depth is None else max(0, int(max_depth))

    rows = _map_rows(manager)
    by_cause, by_effect = {}, {}
    for row in rows:
        by_cause.setdefault(row['cause'], []).append(row)
        by_effect.setdefault(row['effect'], []).append(row)

    # node -> {'depth': hops from the nearest start, 'clean': reached by a path with no definer hop,
    #          'definer': reached by a path that crossed one}
    seen = {n: {'depth': 0, 'clean': True, 'definer': False} for n in starts}
    crossed, frontier, steps, truncated = {}, [(n, 0, False) for n in starts], 0, False
    while frontier:
        steps += 1
        if steps > _MAX_STEPS:
            truncated = True
            break
        node, depth, via_definer = frontier.pop(0)
        if depth >= limit:
            if by_cause.get(node):
                truncated = True
            continue
        for row in by_cause.get(node, ()):
            effect = row['effect']
            crossed[row['name']] = row
            definer = via_definer or (row['means'] == 'solution-run'
                                      and str(row.get('run_as') or '') == 'definer')
            state = seen.get(effect)
            if state is None:
                seen[effect] = {'depth': depth + 1, 'clean': not definer, 'definer': definer}
                frontier.append((effect, depth + 1, definer))
                continue
            changed = False
            if depth + 1 < state['depth']:
                state['depth'] = depth + 1
                changed = True
            if not definer and not state['clean']:
                state['clean'] = True
                changed = True
            if definer and not state['definer']:
                state['definer'] = True
                changed = True
            if changed:
                frontier.append((effect, depth + 1, definer))

    out = {'start': [{'node': n, 'kind': n.partition(':')[0],
                      'seen': bool(by_cause.get(n) or by_effect.get(n))} for n in starts],
           'objects': [], 'events': [], 'solutions': [], 'peers': [], 'external': [], 'other': [],
           'edges': [{k: r.get(k, '') for k in EDGE_OUT} for r in sorted(
               crossed.values(), key=lambda r: (-int(r.get('count') or 0), r['cause'], r['effect']))],
           'coverage': _coverage(manager), 'max_depth': limit, 'truncated': truncated}

    for node, state in sorted(seen.items()):
        incoming = [r for r in by_effect.get(node, ()) if r['name'] in crossed]
        ev = _evidence(incoming or ([] if node not in start_set else by_cause.get(node, [])), state['depth'])
        item = {'node': node, 'origin': 'observed' if node in start_set else 'closure',
                'definer_only': bool(state['definer'] and not state['clean']), 'evidence': ev}
        kind, _, ref = node.partition(':')
        if kind == 'object':
            cls, _, verb = ref.partition(':')
            out['objects'].append({**item, 'class': cls, 'verb': verb or 'read'})
        elif kind == 'event':
            out['events'].append({**item, 'event': ref, 'run_as': _first(incoming, 'run_as')})
        elif kind == 'solution':
            out['solutions'].append({**item, 'name': ref, 'run_as': _first(incoming, 'run_as') or 'invoker'})
        elif kind == 'peer':
            name, _, means = ref.partition(':')
            out['peers'].append({**item, 'peer': name, 'means': means or 'send',
                                 'classes': _first(incoming, 'detail')})
        elif kind == 'external':
            system, _, name = ref.partition(':')
            out['external'].append({**item, 'system': system, 'name': name,
                                    'wire': _first(incoming, 'means'), 'classes': _first(incoming, 'detail')})
        else:
            out['other'].append({**item, 'kind': kind, 'ref': ref})

    out['not_traced'] = not_traced(out)
    out['counts'] = {k: len(out[k]) for k in ('objects', 'events', 'solutions', 'peers', 'external', 'edges')}
    out['counts']['definer_only'] = sum(
        1 for k in ('objects', 'events', 'solutions') for i in out[k] if i['definer_only'])
    return out


def _first(rows, key):
    return next((str(r.get(key) or '') for r in rows if r.get(key)), '')


def _evidence(rows, depth):
    """The counts behind one node's presence. `seen` False = the node is in the answer because it was ASKED for
    (a start node), not because the map has ever recorded it."""
    rows = list(rows or [])
    if not rows:
        return {'count': 0, 'first_seen': '', 'last_seen': '', 'min_depth': depth,
                'sample_trace_id': '', 'target': '', 'seen': False}
    stamps = [str(r.get('first_seen') or '') for r in rows if r.get('first_seen')]
    last = [str(r.get('last_seen') or '') for r in rows if r.get('last_seen')]
    return {'count': sum(int(r.get('count') or 0) for r in rows),
            'first_seen': min(stamps) if stamps else '', 'last_seen': max(last) if last else '',
            'min_depth': depth, 'sample_trace_id': _first(rows, 'sample_trace_id'),
            'target': _first(rows, 'target'), 'seen': True}


def classes_in(result):
    """Every CLASS this closure answer touches — from the object nodes, the `topic:` events, and the class lists
    a peer/external edge carries in `detail`."""
    out = set()
    for item in result.get('objects') or []:
        if item.get('class'):
            out.add(item['class'])
    for item in result.get('events') or []:
        ref = str(item.get('event') or '')
        if ref.startswith('topic:'):
            out.add(ref.split(':', 1)[1])
    for key in ('peers', 'external'):
        for item in result.get(key) or []:
            out |= {c.strip() for c in str(item.get('classes') or '').split(',') if c.strip()}
    return out


def not_traced(result):
    """The classes in this answer that have NEVER been a `TraceTarget` — design §2's "coverage, not silence":
    the answer for them is *not traced*, which is not the same as *nothing reaches them*."""
    traced = {str(c.get('class_name') or '') for c in (result.get('coverage') or [])}
    return sorted(c for c in classes_in(result) if c and c not in traced)


def mark_origin(result, nodes, origin):
    """Re-stamp the `origin` of the items whose node is in `nodes` (design §6: every proposed item carries its
    origin — `observed` | `closure` | `declared`). A profile's grants are DECLARED; a role's recorded acts are
    OBSERVED; everything the walk adds is CLOSURE."""
    wanted = {str(n) for n in (nodes or [])}
    for key in ('objects', 'events', 'solutions', 'peers', 'external', 'other'):
        for item in result.get(key) or []:
            if item.get('node') in wanted:
                item['origin'] = origin
    return result


# ---- the three start sets -------------------------------------------------------------------------------

def profile_start(manager, profile_name):
    """A published or draft `AppPermissionProfile` by name → its EXPLICIT class × verb grants as start nodes.

    Returns {'ok', 'profile', 'groups', 'verbs', 'classes', 'explicit': [[class, verb]], 'nodes'} or
    {'ok': False, 'refusal'}."""
    import json
    rows = (getattr(manager, 'objectTables', None) or {}).get('AppPermissionProfile', {}) or {}
    row = next((r for r in rows.values() if str(getattr(r, 'name', '')) == str(profile_name)), None)
    if row is None:
        have = sorted(str(getattr(r, 'name', '')) for r in rows.values())
        return {'ok': False, 'refusal': ('no AppPermissionProfile named %r on this instance%s'
                                         % (profile_name, (' — there is %s' % ', '.join(have)) if have else
                                            ' (no profiles at all yet)'))}

    def _loads(raw, default):
        try:
            parsed = json.loads(raw or '')
            return parsed if isinstance(parsed, type(default)) else default
        except (ValueError, TypeError):
            return default

    verbs = [str(v) for v in _loads(getattr(row, 'verbs_json', '[]'), [])]
    classes = {str(c) for c in _loads(getattr(row, 'extra_classes_json', '[]'), []) if c}
    app_name = str(getattr(row, 'app_name', '') or '')
    if app_name:
        try:                                    # the app's own classes, when the permissions model is present
            from polariapps.objects.apps_permissions._shared import classes_for_app
            classes |= {str(c) for c in classes_for_app(manager, app_name)}
        except Exception:                       # noqa: BLE001 — polariapps absent: the extra classes still stand
            pass
    explicit = [[c, v] for c in sorted(classes) for v in verbs]
    return {'ok': True, 'profile': str(getattr(row, 'name', '')), 'app': app_name,
            'published': bool(getattr(row, 'published', False)),
            'groups': [str(g).lstrip('/') for g in _loads(getattr(row, 'kc_groups_json', '[]'), [])],
            'verbs': verbs, 'classes': sorted(classes), 'explicit': explicit,
            'nodes': ['object:%s:%s' % (c, v) for c, v in explicit]}


def event_start(ref):
    """`daily-rollup` / `trigger:daily-rollup` / `topic:MealEntry` / a full `event:…` node → the start node."""
    ref = str(ref or '').strip()
    if not ref:
        return ''
    if ref.startswith('event:'):
        return ref
    if ref.startswith(('trigger:', 'topic:')):
        return 'event:%s' % ref
    return 'event:trigger:%s' % ref


def role_start(manager, role):
    """The role-play recording (§17b) → start nodes: every class × verb the role was OBSERVED acting on, and
    every endpoint it walked through. Reads the observation ledgers directly (never `review`, which calls back
    here for its own closure block)."""
    from security.custom.security_observe import ROLEPLAY_PREFIX, observations, usages
    role = str(role or '').strip().lower()
    marker = ROLEPLAY_PREFIX + role
    nodes = []
    for obs in observations(manager):
        if marker in str(obs.get('groups') or '').split(','):
            nodes.append('object:%s:%s' % (obs['class_name'], obs['verb']))
    for use in usages(manager, role, kind='endpoint'):
        nodes.append('endpoint:%s' % use['item'])
    for use in usages(manager, role, kind='object'):
        item = str(use.get('item') or '')
        nodes.append(item if item.startswith('object:') else 'object:%s:read' % item)
    return [n for n in dict.fromkeys(nodes) if n]


def target_start(manager):
    """With nothing asked for, the page's default: the ONE armed target's class × the verbs it opens on. '' when
    nothing is armed."""
    from security.custom.security_trace import TRACE_VERBS, _verbs_of, active_target
    row = active_target(manager)
    if row is None:
        return '', []
    cls = str(getattr(row, 'class_name', '') or '')
    verbs = _verbs_of(row) or list(TRACE_VERBS)
    return cls, ['object:%s:%s' % (cls, v) for v in verbs]


# ---- the two verdicts the review and the verify carry ---------------------------------------------------

def role_closure(manager, role, max_depth=None):
    """`review(role)`'s `closure` block: the same shape, started from what the role was observed doing."""
    nodes = role_start(manager, role)
    result = closure(manager, nodes, max_depth=max_depth)
    mark_origin(result, nodes, 'observed')
    result['start_kind'] = 'role'
    result['reading'] = reading(result, 'the role was observed at %d door(s)/act(s)' % len(nodes))
    return result


def transitive_verdict(manager, role, user, max_depth=None):
    """`verify(role, group)`'s SECOND verdict (design §6): *"the profile covers N of M transitively-touched
    class × verb pairs; K are reached only through triggers running as definer"*.

    `user` is the synthetic replay caller `verify` already builds (groups only, no identity — D18-1). Returns
    {'covered', 'total', 'definer_only', 'not_traced', 'uncovered', 'reading'}; nothing is written or widened."""
    result = role_closure(manager, role, max_depth=max_depth)
    try:
        from polariapps.objects.apps_permissions._shared import permission_verdict
    except Exception:                           # noqa: BLE001 — no permissions model: say so rather than guess
        return {'covered': 0, 'total': len(result['objects']), 'definer_only': 0,
                'not_traced': result['not_traced'], 'uncovered': [],
                'reading': 'the permissions model (polariapps) is not on this instance, so nothing can be '
                           'replayed against it — the transitive set is listed, unjudged'}
    covered, uncovered, definer_only = 0, [], 0
    for item in result['objects']:
        cls, verb = item.get('class') or '', item.get('verb') or ''
        if not cls or not verb:
            continue
        if item['definer_only']:
            definer_only += 1
        verdict = permission_verdict(manager, user, cls, verb)
        if verdict.get('allowed'):
            covered += 1
        else:
            uncovered.append({'class': cls, 'verb': verb, 'origin': item['origin'],
                              'definer_only': item['definer_only'], 'why': verdict.get('why', ''),
                              'count': item['evidence']['count']})
    total = len([i for i in result['objects'] if i.get('class') and i.get('verb')])
    return {'covered': covered, 'total': total, 'definer_only': definer_only,
            'not_traced': result['not_traced'], 'uncovered': uncovered,
            'reading': ('the profile covers %d of %d transitively-touched class × verb pair(s); %d %s reached '
                        'only through triggers running as definer%s'
                        % (covered, total, definer_only, 'is' if definer_only == 1 else 'are',
                           ('. %d class(es) in this answer have never been traced (%s) — "not traced", not '
                            '"nothing reaches them"' % (len(result['not_traced']), ', '.join(result['not_traced']))
                            if result['not_traced'] else '')))}


def reading(result, lead):
    counts = result['counts']
    return ('%s; the closure reaches %d class × verb pair(s), %d event(s), %d solution(s), %d peer edge(s) and '
            '%d external edge(s) over %d map row(s)%s'
            % (lead, counts['objects'], counts['events'], counts['solutions'], counts['peers'],
               counts['external'], counts['edges'],
               ('. NOT TRACED: %s — those classes have never been a TraceTarget, so the map cannot say what '
                'reaches them' % ', '.join(result['not_traced'])) if result['not_traced'] else ''))
