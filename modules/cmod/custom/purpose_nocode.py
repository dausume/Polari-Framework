"""
@module cmod.custom.purpose_nocode

PURPOSE NO-CODE (fgm-1, FIRMWARE_GENERATION_MODULE_PLAN.md §8): a Purpose drawn as ONE no-code solution of category `purpose`,
a sentence a person reads left to right across eleven states:

    Purpose - Depends on - Participant - When - Then - Within - Polari must see - Done by - Proved by - Can it run here? - On each device

It is DECLARATIVE: the engine never executes it, and `validate` (the category validator in hwnocode.custom.cross_domain) refuses
every compute and runtime kind by name. The `CapabilityDefinition` row is the single source of truth. `render` draws the row;
`write_back` turns canvas edits back into row fields (it never holds a copy that could drift) and refuses an edit to a derived
state by name. The three derived states (proof status, resolution, per-device) are WORKED OUT on every render when asked
(`derive=True`); a seeded row renders them as "worked out when asked" so nothing derived is ever stored.
"""
import json

from polariNoCode import graph_builder as GB
from cmod.custom import purpose_text as T

CATEGORY = 'purpose'
SOLUTION_PREFIX = 'purpose-'
PLACEHOLDER = '(worked out when asked)'
LIFECYCLES = ('draft', 'enabled', 'suspended', 'retired')
PURPOSES_ROUTE = '/display/c-canvas'

#: reading order: (column, stateClass, kind, derived)
COLUMNS = [
    (1, 'PurposeGoalState', 'purpose-goal', False), (2, 'PurposeDependsState', 'purpose-depends', False),
    (3, 'PurposeParticipantState', 'purpose-participant', False), (4, 'PurposeTriggerState', 'purpose-trigger', False),
    (5, 'PurposeOutcomeState', 'purpose-outcome', False), (6, 'PurposeCriterionState', 'purpose-criterion', False),
    (7, 'PurposeObservesState', 'purpose-observes', False), (8, 'PurposeTasksState', 'purpose-tasks', False),
    (9, 'PurposeProofState', 'purpose-proof', True), (10, 'PurposeResolutionState', 'purpose-resolution', True),
    (11, 'PurposeObservedState', 'purpose-observed', True)]
KIND_OF = {cls: (col, kind, derived) for col, cls, kind, derived in COLUMNS}
#: the fields of each derived state that only the derivation may set
DERIVED_FIELDS = {'PurposeProofState': ('status', 'last_proof'), 'PurposeResolutionState': ('resolution', 'why'),
                  'PurposeObservedState': ('summary', 'devices')}
_COL_W, _ROW_H, _W, _H = 215, 125, 190, 96


def solution_name(purpose):
    return SOLUTION_PREFIX + purpose


def _j(text, default):
    try:
        v = json.loads(text) if isinstance(text, str) and text else default
    except Exception:  # noqa: BLE001
        return default
    return v if isinstance(v, type(default)) else default


def _task_refs(cap):
    tasks = _j(cap.get('tasks_by_runtime_json'), {})
    return [r for rt in ('c-device', 'java-bridge', 'python-backend', 'typescript-browser') for r in tasks.get(rt) or []]


def _goal_of(name, manager):
    from cmod.custom import capabilities as CAP
    rows = ((getattr(manager, 'objectTables', None) or {}).get('CapabilityDefinition', {}) or {}).values() if manager is not None else []
    hit = next((r for r in rows if getattr(r, 'name', '') == name), None)
    if hit is not None:
        return getattr(hit, 'goal', '')
    seed = CAP.find(name)
    return (seed or {}).get('goal', '')


def _node(name, cls, title, sentence, fields, links=()):
    f = dict(fields, displayName=title, purpose=sentence)
    if links:
        f['detail_ref'] = {'class': 'LinkTarget', 'name': links[0][0], 'route': links[0][1]}
        f['links'] = [{'label': a, 'route': b} for a, b in links]
    return {'name': name, 'cls': cls, 'fields': f}


def _states(cap, manager, derive):
    """[(stateName, stateClass, fields)] in reading order, columns in COLUMNS order."""
    from cmod.custom import purpose_derived as PD
    name = cap.get('name', '')
    crit = _j(cap.get('criteria_json'), {})
    out = []
    t, s = T.goal_card(cap)
    out.append(_node('purpose', 'PurposeGoalState', t, s, {'title': cap.get('title') or name, 'goal': cap.get('goal', ''),
                                                           'lifecycle': cap.get('lifecycle') or 'enabled'},
                     [('All the Purposes', PURPOSES_ROUTE)]))
    dep = cap.get('depends_on') or ''
    t, s = T.depends_card(cap, _goal_of(dep, manager) if dep else '')
    out.append(_node('depends', 'PurposeDependsState', t, s, {'depends_on': dep},
                     [('The Purpose it depends on', '/display/hardware-solutions?solution=%s' % solution_name(dep))] if dep else ()))
    for i, p in enumerate(_j(cap.get('participants_json'), []), 1):
        t, s = T.participant_card(p)
        out.append(_node('participant-%d' % i, 'PurposeParticipantState', t, s,
                         {k: str(p.get(k, '')) for k in ('role', 'kind', 'ref', 'variant')}))
    trig, outc = crit.get('trigger') or {}, crit.get('outcome') or {}
    t, s = T.trigger_card(trig)
    out.append(_node('trigger', 'PurposeTriggerState', t, s, {'kind': trig.get('kind', ''), 'what': trig.get('what', '')}))
    t, s = T.outcome_card(outc)
    out.append(_node('outcome', 'PurposeOutcomeState', t, s, {'what': outc.get('what', '')}))
    for i, c in enumerate(crit.get('criteria') or [], 1):
        t, s = T.criterion_card(c)
        out.append(_node('criterion-%d' % i, 'PurposeCriterionState', t, s,
                         {'key': str(c.get('key', '')), 'value': str(c.get('value', '')), 'unit': str(c.get('unit', ''))}))
    for i, o in enumerate(_j(cap.get('observes_json'), []), 1):
        t, s = T.observes_card(o)
        out.append(_node('observes-%d' % i, 'PurposeObservesState', t, s,
                         {k: str(o.get(k, '')) for k in ('item', 'kind', 'delivery')}))
    refs = _task_refs(cap)
    names = [r.rpartition(':')[2] for r in refs]
    t, s = T.tasks_card(names)
    out.append(_node('tasks', 'PurposeTasksState', t, s, {'tasks': ','.join(refs), 'count': str(len(refs))},
                     [('The firmware drawing', '%s?graph=%s' % (PURPOSES_ROUTE, cap.get('graph', '')))] if cap.get('graph') else ()))
    scen = cap.get('acceptance_scenario', '')
    if derive:
        from cmod.custom import capabilities as CAP
        status, last, _why, _pk = CAP.derive_status(cap, manager=manager)
        res, obs = PD.resolution(cap, manager), PD.observed_summary(cap, manager)
        t, s = T.proof_card(scen, status, last)
        out.append(_node('proof', 'PurposeProofState', t, s, {'scenario': scen, 'status': status, 'last_proof': last}))
        t, s = T.resolution_card(res['state'], res['why'])
        out.append(_node('resolution', 'PurposeResolutionState', t, s, {'resolution': res['state'], 'why': res['why']}))
        t, s = T.observed_card(obs['summary'])
        out.append(_node('observed', 'PurposeObservedState', t, s,
                         {'summary': obs['summary'], 'devices': ','.join(d['board_instance'] for d in obs['devices'])},
                         [('The light right now', '/display/uno-core-demo')]))
    else:
        t, s = T.proof_card(scen, PLACEHOLDER, '', derived=False)
        out.append(_node('proof', 'PurposeProofState', t, s, {'scenario': scen, 'status': PLACEHOLDER, 'last_proof': PLACEHOLDER}))
        t, s = T.resolution_card('', '', derived=False)
        out.append(_node('resolution', 'PurposeResolutionState', t, s, {'resolution': PLACEHOLDER, 'why': PLACEHOLDER}))
        t, s = T.observed_card('', derived=False)
        out.append(_node('observed', 'PurposeObservedState', t, s, {'summary': PLACEHOLDER, 'devices': PLACEHOLDER}))
    return out


def render_definition(cap, manager=None, derive=True):
    """The graph_builder definition of ONE Purpose: eleven columns left to right, a stack in a column when there are several
    participants / criteria / observed items; every state in a column points `then` at the first state of the next column."""
    nodes = _states(cap, manager, derive)
    cols = {}
    for n in nodes:
        cols.setdefault(KIND_OF[n['cls']][0], []).append(n)
    order = sorted(cols)
    states = []
    for ci, col in enumerate(order):
        nxt = cols[order[ci + 1]][0]['name'] if ci + 1 < len(order) else None
        for k, n in enumerate(cols[col]):
            _c, kind, derived = KIND_OF[n['cls']]
            st = GB.node(n['name'], n['cls'], dict(n['fields'], derived=derived), outs=[[nxt] if nxt else []])
            st['stateLocationX'], st['stateLocationY'] = 40 + _COL_W * ci, 60 + _ROW_H * k
            st['shapeType'] = st['stateSvgName'] = 'rectangle'
            st['layerName'] = 'rectangle-layer'
            st['backgroundColor'] = '#9E9E9E' if derived else '#00695C'
            st['slotRadius'] = 5
            st['stateSvgWidth'], st['stateSvgHeight'], st['cornerRadius'] = _W, _H, 8
            st['stateSvgRadius'] = None
            st['stateSvgSizeX'] = st['stateSvgSizeY'] = None
            st['runtime'] = ''
            states.append(st)
    d = GB.solution(solution_name(cap.get('name', '')), *states)
    d['edgeKind'] = 'then'
    try:
        from hwnocode.custom import solutions as S
        S._wire_connectors(d)
    except Exception:  # noqa: BLE001 - the canvas wiring ids are cosmetic; the drawing is still valid
        pass
    return d


def contract():
    return {'description': 'A Purpose drawn as a sentence: why a part is in the firmware, what starts it, what you will see, the bounds, '
                           'what Polari must see, the tasks, the proof, whether it can run here and what each device reports. '
                           'Declarative: nothing here is executed.',
            'inputs': [], 'returns': [], 'executionRights': 'definer'}


def render(cap, manager=None, derive=True):
    """The SolutionDefinition ROW dict for one Purpose (category 'purpose'); `definition` is the JSON of render_definition."""
    name = solution_name(cap.get('name', ''))
    return {'name': name, 'function_name': name.replace('-', '_'), 'target_runtime': 'python_backend',
            'definition': json.dumps(render_definition(cap, manager, derive)), 'contract_json': json.dumps(contract()),
            'category': CATEGORY}


def validate(definition):
    """(ok, why) — only the eleven Purpose kinds; compute and runtime kinds are refused by name (the category validator)."""
    from hwnocode.custom import cross_domain as CD
    return CD.validate(definition, CATEGORY)


# ---------------------------------------------------------------------------------------------------- write back
def _ref_exists(kind, ref, manager):
    if kind in ('host', 'polari'):
        return True
    from board.custom import board_object as BO
    t = BO.tables_from_manager(manager) if manager is not None else {}
    if not t.get('BoardDefinition'):          # a manager that holds no board rows yet: the seeded boards answer
        t = BO.seed_tables()
    table, key = ('BoardDefinition', BO.board_name(ref)) if kind == 'board' else ('SocDefinition', ref)
    return any(r.get('name') == key for r in t.get(table, []))


def _num(v):
    try:
        f = float(v)
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return v


def write_back(definition, cap, manager=None):
    """(ok, why, changes) — turn the drawing's edits into the row's fields. `changes` is {field: new value} for ONLY the fields that
    differ from `cap`; the caller writes them to the CapabilityDefinition row (the one source of truth) and re-renders. Refuses,
    naming the state: a non-Purpose kind (validate), an edit to a derived state, an unknown life stage / dependency /
    participant, and a change of the task list (tasks change through POST/DELETE /api/capabilities/{name}/tasks)."""
    ok, why = validate(definition)
    if not ok:
        return False, why, {}
    got = {}
    for s in definition.get('stateInstances') or []:
        got.setdefault(s.get('stateClass') or s.get('stateName'), []).append(s)
    fresh = {n['name']: n['fields'] for n in _states(cap, manager, True)}
    f = lambda s: dict(s.get('boundObjectFieldValues') or {})   # noqa: E731
    for cls, keys in DERIVED_FIELDS.items():
        for s in got.get(cls, []):
            for k in keys:
                v, mine = f(s).get(k), fresh.get(s.get('stateName'), {}).get(k)
                if v is not None and str(v) not in (PLACEHOLDER, str(mine)):
                    return False, ('refused: state %r (%s) is derived - its %s is worked out, never typed in (got %r, it is %r)'
                                   % (s.get('stateName'), KIND_OF[cls][1], k, v, mine)), {}
    changes = {}
    goal = got.get('PurposeGoalState')
    if not goal:
        return False, 'refused: the drawing has no Purpose state (PurposeGoalState); it is the one state that cannot be removed', {}
    g = f(goal[0])
    if g.get('lifecycle', cap.get('lifecycle')) not in LIFECYCLES:
        return False, 'refused: state %r - life stage %r is not one of %s' % (goal[0].get('stateName'), g.get('lifecycle'), ', '.join(LIFECYCLES)), {}
    for fld in ('title', 'goal', 'lifecycle'):
        if fld in g and g[fld] != (cap.get(fld) or ('enabled' if fld == 'lifecycle' else '')):
            changes[fld] = g[fld]
    for s in got.get('PurposeDependsState', [])[:1]:
        dep = f(s).get('depends_on', '')
        if dep and (dep == cap.get('name') or not (_goal_of(dep, manager) or _exists(dep, manager))):
            return False, 'refused: state %r - %r is not another Purpose' % (s.get('stateName'), dep), {}
        if dep != (cap.get('depends_on') or ''):
            changes['depends_on'] = dep
    parts = []
    for s in got.get('PurposeParticipantState', []):
        p = {k: str(f(s).get(k, '')) for k in ('role', 'kind', 'ref', 'variant')}
        if p['kind'] not in ('board', 'soc', 'host', 'polari'):
            return False, "refused: state %r - participant kind %r must be board, soc, host or polari" % (s.get('stateName'), p['kind']), {}
        if not _ref_exists(p['kind'], p['ref'], manager):
            return False, 'refused: state %r - there is no %s named %r' % (s.get('stateName'), p['kind'], p['ref']), {}
        parts.append({k: v for k, v in p.items() if v})
    if parts != _j(cap.get('participants_json'), []):
        changes['participants_json'] = json.dumps(parts)
    crit = _j(cap.get('criteria_json'), {})
    new = dict(crit)
    for cls, key, fields in (('PurposeTriggerState', 'trigger', ('kind', 'what')), ('PurposeOutcomeState', 'outcome', ('what',))):
        for s in got.get(cls, [])[:1]:
            val = {k: f(s).get(k, '') for k in fields}
            if any(val.values()) or key in crit:
                new[key] = val
    items = [{k: (_num(f(s).get(k, '')) if k == 'value' else f(s).get(k, '')) for k in ('key', 'value', 'unit') if f(s).get(k, '') != ''}
                       for s in got.get('PurposeCriterionState', [])]
    if items or 'criteria' in crit:
        new['criteria'] = items
    if new != crit:
        changes['criteria_json'] = json.dumps(new)
    obs = [{k: f(s).get(k, '') for k in ('item', 'kind', 'delivery') if f(s).get(k, '') != ''} for s in got.get('PurposeObservesState', [])]
    if obs != _j(cap.get('observes_json'), []):
        changes['observes_json'] = json.dumps(obs)
    for s in got.get('PurposeTasksState', [])[:1]:
        if f(s).get('tasks', '') != ','.join(_task_refs(cap)):
            return False, ('refused: state %r - the tasks are changed one at a time through POST/DELETE /api/capabilities/%s/tasks, '
                           'not by editing this card' % (s.get('stateName'), cap.get('name'))), {}
    for s in got.get('PurposeProofState', [])[:1]:
        scen = f(s).get('scenario', '')
        if scen != (cap.get('acceptance_scenario') or ''):
            changes['acceptance_scenario'] = scen
    return True, 'ok: %d field(s) changed' % len(changes), changes


def _exists(name, manager):
    from cmod.custom import capabilities as CAP
    rows = ((getattr(manager, 'objectTables', None) or {}).get('CapabilityDefinition', {}) or {}).values() if manager is not None else []
    return any(getattr(r, 'name', '') == name for r in rows) or CAP.find(name) is not None


def resolution(cap, manager=None):
    from cmod.custom import purpose_derived as PD
    return PD.resolution(cap, manager)


def observed_summary(cap, manager=None):
    from cmod.custom import purpose_derived as PD
    return PD.observed_summary(cap, manager)
