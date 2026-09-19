"""
security.custom.security_tasks — TASKS AND NEEDS (ct-7; design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §8).

*"A person's needs are the union of the tasks their held roles perform, and a task's needs are the closure of the
doors it walks through."*

So an `ObservationSession` states a TASK — free text the role-player types when they start ("publish an article",
"reconcile last week's meals") and may change mid-session through the same door — and every act recorded while
that session is open carries it. `review(role)` then reads as

    tasks → doors → objects × verbs → closure per task

instead of a flat class list, and `verify(role, group)` says, per task, whether enforcing the profile would BREAK
it. That last line is the whole point of the slice: "the journalist loses 3 of 11 recorded acts" is a number;
"the journalist can no longer publish an article" is a decision a person can make.

HOW A TASK IS ATTACHED, and why it is not a column on its own row. The observation ledgers are COUNTED rows keyed
by the act (`groups|class|verb`, `role|kind|item`) — that is what keeps them small enough to read. Putting the task
in the key would multiply every row by the number of tasks that ever touch it and would renumber every existing
row; putting it in a plain `task` column would let the last task silently claim acts that belong to the one
before. So each row carries `tasks_json`, a `{task: count}` map: one row, every task that used it, with the
evidence of how often. The ceiling below is what stops a role-player's typo storm from growing a row without
bound; the overflow is COUNTED under `OVERFLOW_TASK`, never dropped in silence.

A task is TEXT A PERSON TYPED. It is not an identifier, it is never a person's name by policy (D18-1 keys people
by `sub` alone and a task is a job, not a who), and it is truncated, whitespace-collapsed and control-character
stripped before it is ever written to a row.
"""
import json

#: the longest task label a row will hold — a task is a phrase, not a paragraph
TASK_MAX = 120
#: how many distinct tasks one counted row may name before the rest are counted together
MAX_TASKS_PER_ROW = 24
#: where the overflow goes: counted, named, never silent
OVERFLOW_TASK = '(more tasks than this row lists)'
#: the bucket acts recorded outside any stated task fall into (the review shows it last, as itself)
NO_TASK = ''
#: how many tasks the review computes a full closure for (busiest first). A closure is a graph walk per task, and
#: a review is a page; the rest are listed with their doors and objects and say why the closure is absent.
MAX_TASK_CLOSURES = 12


def clean_task(task):
    """A task as it may be stored: one line, collapsed whitespace, no control characters, `TASK_MAX` long."""
    text = ' '.join(str(task or '').split())
    text = ''.join(ch for ch in text if ch.isprintable())
    return text[:TASK_MAX]


# ---- the {task: count} map on a counted observation row -------------------------------------------------

def tasks_of(row):
    """The `{task: count}` map of one observation row; `{}` when the column is absent or unreadable."""
    try:
        parsed = json.loads(str(getattr(row, 'tasks_json', '') or '{}'))
        if not isinstance(parsed, dict):
            return {}
        return {str(k): int(v or 0) for k, v in parsed.items()}
    except Exception:                       # noqa: BLE001 — an unreadable column is an empty one, never a raise
        return {}


def bump_task(row, task):
    """Count ONE occurrence of this act under `task`. No-op for an empty task (an act outside any session is not
    attributed to one); never raises into the recorder that called it."""
    task = clean_task(task)
    if not task or row is None:
        return None
    try:
        counts = tasks_of(row)
        if task not in counts and len(counts) >= MAX_TASKS_PER_ROW:
            task = OVERFLOW_TASK
        counts[task] = counts.get(task, 0) + 1
        row.tasks_json = json.dumps(counts)
        return counts
    except Exception:                       # noqa: BLE001
        return None


# ---- the session's own task ------------------------------------------------------------------------------

def session_tasks(row):
    """`[{task, at}]` — every task this session stated, in the order it stated them."""
    try:
        parsed = json.loads(str(getattr(row, 'tasks_json', '') or '[]'))
        return [t for t in parsed if isinstance(t, dict)] if isinstance(parsed, list) else []
    except Exception:                       # noqa: BLE001
        return []


def current_task(manager, role):
    """The task the OPEN session for `role` states right now, or `''`.

    The recorders call this on every act, so it is a scan of one small table and nothing else — no closure, no
    import of the permissions model, and never a raise: an act must be recorded even when the session table
    cannot be read."""
    try:
        from security.custom.security_observe import _all_rows
        role = str(role or '').strip().lower()
        if not role:
            return ''
        for row in _all_rows(manager, 'ObservationSession'):
            if getattr(row, 'role', '') == role and bool(getattr(row, 'active', False)):
                return clean_task(getattr(row, 'task', ''))
    except Exception:                       # noqa: BLE001
        return ''
    return ''


def state_task(manager, row, task, now):
    """Set the OPEN session's current task and append it to the session's history. Returns (changed, task)."""
    task = clean_task(task)
    if row is None or not task or clean_task(getattr(row, 'task', '')) == task:
        return False, clean_task(getattr(row, 'task', '')) if row is not None else ''
    history = session_tasks(row)
    history.append({'task': task, 'at': now})
    row.task = task
    row.tasks_json = json.dumps(history[-MAX_TASKS_PER_ROW:])
    return True, task


# ---- the review: tasks → doors → objects × verbs → closure ----------------------------------------------

DOOR_KINDS = ('app', 'page', 'component', 'action', 'endpoint', 'object')


def _closure_for(manager, nodes):
    """The closure of ONE task's recorded acts, defended. A review must still answer when the map cannot be
    walked (no `TraceTarget` has ever been armed, the module is half-loaded) — it says so rather than failing."""
    try:
        from security.custom.security_closure import closure, mark_origin, reading
        result = closure(manager, nodes)
        mark_origin(result, nodes, 'observed')
        result['reading'] = reading(result, 'this task was observed at %d door(s)/act(s)' % len(nodes))
        return result
    except Exception as exc:                # noqa: BLE001
        return {'objects': [], 'events': [], 'solutions': [], 'peers': [], 'external': [], 'other': [],
                'edges': [], 'coverage': [], 'not_traced': [], 'start': [],
                'counts': {'objects': 0, 'events': 0, 'solutions': 0, 'peers': 0, 'external': 0, 'edges': 0,
                           'definer_only': 0},
                'reading': 'the closure could not be computed for this task (%s: %s) — the doors and the acts '
                           'below stand on their own' % (type(exc).__name__, exc)}


def group_by_task(manager, observations, usages_, with_closure=True):
    """THE REVIEW's `tasks` block (design §8): the recorded acts grouped by the task that was stated.

    `observations` are the role's `PermissionObservation` dicts and `usages_` its `UsageObservation` dicts, both
    already filtered to the role by the caller. Returns a list, busiest task first, of::

        {'task', 'acts', 'usages', 'would_deny_today',
         'objects':  {Class: {verb: count}},
         'doors':    {kind: [{item, app, page, count}]},
         'nodes':    the closure start nodes this task contributes,
         'closure':  the closure of those nodes (or None with a `closure_why`),
         'reading'}

    The last entry is the UNATTRIBUTED bucket (`task` = '') whenever acts were recorded with no session task
    stated — it is shown as itself rather than folded into a task that did not do it."""
    buckets = {}

    def _bucket(task):
        return buckets.setdefault(task, {'task': task, 'acts': 0, 'usages': 0, 'would_deny_today': 0,
                                         'objects': {}, 'doors': {}, 'nodes': []})

    for obs in observations or []:
        total = int(obs.get('count') or 0)
        counts = dict(obs.get('tasks') or {})
        attributed = sum(int(v or 0) for v in counts.values())
        if total > attributed:
            counts[NO_TASK] = counts.get(NO_TASK, 0) + (total - attributed)
        for task, n in counts.items():
            if not n:
                continue
            b = _bucket(task)
            b['acts'] += int(n)
            cls, verb = obs.get('class_name') or '', obs.get('verb') or ''
            if cls and verb:
                b['objects'].setdefault(cls, {})[verb] = b['objects'].get(cls, {}).get(verb, 0) + int(n)
                node = 'object:%s:%s' % (cls, verb)
                if node not in b['nodes']:
                    b['nodes'].append(node)
            if obs.get('verdict') == 'would-deny':
                b['would_deny_today'] += int(n)

    for use in usages_ or []:
        total = int(use.get('count') or 0)
        counts = dict(use.get('tasks') or {})
        attributed = sum(int(v or 0) for v in counts.values())
        if total > attributed:
            counts[NO_TASK] = counts.get(NO_TASK, 0) + (total - attributed)
        for task, n in counts.items():
            if not n:
                continue
            b = _bucket(task)
            b['usages'] += int(n)
            kind = use.get('kind') or 'action'
            b['doors'].setdefault(kind, []).append({'item': use.get('item', ''), 'app': use.get('app', ''),
                                                    'page': use.get('page', ''), 'count': int(n)})
            if kind == 'endpoint' and use.get('item'):
                node = 'endpoint:%s' % use['item']
                if node not in b['nodes']:
                    b['nodes'].append(node)

    out = sorted(buckets.values(), key=lambda b: (b['task'] == NO_TASK, -(b['acts'] + b['usages']), b['task']))
    for index, bucket in enumerate(out):
        for kind in bucket['doors']:
            bucket['doors'][kind].sort(key=lambda d: (-int(d['count'] or 0), d['item']))
        if with_closure and index < MAX_TASK_CLOSURES and bucket['nodes']:
            bucket['closure'] = _closure_for(manager, bucket['nodes'])
            bucket['closure_why'] = ''
        else:
            bucket['closure'] = None
            bucket['closure_why'] = ('no acts to start from' if not bucket['nodes'] else
                                     'only the %d busiest tasks get a closure on one review (a closure is a walk '
                                     'of the map per task); ask for this one alone at '
                                     '/api/security/observe/closure?role=<role>' % MAX_TASK_CLOSURES)
        bucket['reading'] = _reading(bucket)
    return out


def _reading(bucket):
    if bucket['task'] == NO_TASK:
        lead = ('recorded with NO task stated — the session did not say what job was being done, so these acts '
                'belong to the role but to no particular need')
    else:
        lead = 'the task %r' % bucket['task']
    doors = sum(len(v) for v in bucket['doors'].values())
    tail = ''
    if bucket['closure'] is not None:
        counts = bucket['closure']['counts']
        tail = ('; it goes on to reach %d class × verb pair(s), %d event(s) and %d solution(s)'
                % (counts['objects'], counts['events'], counts['solutions']))
        if bucket['closure'].get('not_traced'):
            tail += (' — and %d class(es) here have never been traced (%s), so for those the answer is NOT '
                     'TRACED, not "nothing"' % (len(bucket['closure']['not_traced']),
                                                ', '.join(bucket['closure']['not_traced'])))
    return ('%s: %d act(s) on %d class(es) through %d door(s)%s'
            % (lead, bucket['acts'], len(bucket['objects']), doors, tail))


# ---- verify: which TASKS would break -----------------------------------------------------------------

def verify_tasks(manager, tasks, user, permission_verdict):
    """Per task, replay its recorded class × verb acts against the CURRENT profiles as `user`.

    A task BREAKS when any act it performed would now be denied — which is the sentence a person can act on
    ("the journalist can no longer publish an article"), rather than a count of orphaned verbs. Nothing here
    writes, widens or enforces: `verify` discloses, and the confirmation is ct-8's."""
    out = []
    for bucket in tasks or []:
        allowed, denied = [], []
        for cls, verbs in sorted(bucket['objects'].items()):
            for verb, count in sorted(verbs.items()):
                try:
                    verdict = permission_verdict(manager, user, cls, verb)
                except Exception as exc:    # noqa: BLE001 — one unanswerable act must not lose the rest
                    denied.append({'class': cls, 'verb': verb, 'count': count,
                                   'why': 'the permission model could not answer (%s: %s)'
                                          % (type(exc).__name__, exc)})
                    continue
                item = {'class': cls, 'verb': verb, 'count': count, 'why': verdict.get('why', ''),
                        'via': verdict.get('via', [])}
                (allowed if verdict.get('allowed') else denied).append(item)
        name = bucket['task'] or NO_TASK
        out.append({
            'task': name, 'acts': bucket['acts'], 'allowed': allowed, 'denied': denied,
            'breaks': bool(denied),
            'reading': (('%s would still work: all %d recorded class × verb act(s) are covered'
                         % (('the task %r' % name) if name else 'the acts with no task stated', len(allowed)))
                        if not denied else
                        ('%s would BREAK: %d of %d recorded class × verb act(s) would now be denied (%s)'
                         % (('the task %r' % name) if name else 'the acts with no task stated',
                            len(denied), len(denied) + len(allowed),
                            ', '.join('%s:%s' % (d['class'], d['verb']) for d in denied[:6])))),
        })
    out.sort(key=lambda t: (not t['breaks'], t['task'] == NO_TASK, t['task']))
    return out


HOW_TASKS = ('a task is free text the role-player states when they start a session (POST '
             '/api/security/observe/session {"role": ..., "task": "publish an article"}) and may change through '
             'the same door mid-session. Every act recorded while the session is open carries it, so a role reads '
             'as tasks → doors → objects × verbs → closure, and `verify` says which TASKS enforcement would break '
             'rather than only how many verbs it would take away. Acts recorded with no task stated are shown as '
             'themselves and never folded into a task that did not do them.')
