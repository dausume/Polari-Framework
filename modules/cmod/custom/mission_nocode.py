"""
@module cmod.custom.mission_nocode

HARDWARE MISSION NO-CODE (mis-0, MISSION_PROFILE_SOLVER_PLAN.md sections 2.1 and 5): a Hardware Mission drawn as ONE no-code solution of
category `mission`, a sentence a person reads left to right across six columns (it mirrors `purpose_nocode` one level up):

    Mission - Settings - Purposes (one state each, stacked) - Participants (one each) - Limits - Can it be done here?

It is DECLARATIVE: the engine never executes it, and `validate` (the category validator in hwnocode.custom.cross_domain) refuses
every compute and runtime kind by name. The `HardwareMission` row is the single source of truth. `render` draws the row;
`write_back` turns canvas edits back into row fields (the drawing never holds a copy that could drift) and refuses an edit to a
derived field by name. Each Purpose state carries its importance (STORED on the Mission) beside that Purpose's own status and
resolution (DERIVED from the Purpose, never stored on the Mission). The last state is worked out on every render when asked
(`derive=True`); a stored drawing renders it, and the derived fields, as "(worked out when asked)".
"""
import json

from polariNoCode import graph_builder as GB
from cmod.custom import mission_text as T
from cmod.custom import mission_derived as MD

CATEGORY = 'mission'
SOLUTION_PREFIX = 'mission-'
PLACEHOLDER = '(worked out when asked)'
LIFECYCLES = ('draft', 'enabled', 'suspended', 'retired')
IMPORTANCES = ('safety', 'required', 'important', 'desired')
OBJECTIVES = ('minimum-resources', 'fastest-cycle')
PARTICIPANT_KINDS = ('hardware', 'software', 'person')
STAGES = ('S1-breadboard', 'S2-protoboard', 'S3-pcb', 'S4-vendor-soc', 'S5-blcnc-soc')
DEFAULT_OBJECTIVE = 'minimum-resources'
MISSIONS_ROUTE = '/display/hardware-solutions'

#: reading order: (column, stateClass, kind, derived)
COLUMNS = [
    (1, 'MissionGoalState', 'mission-goal', False), (2, 'MissionSettingsState', 'mission-settings', False),
    (3, 'MissionPurposeState', 'mission-purpose', False), (4, 'MissionParticipantState', 'mission-participant', False),
    (5, 'MissionConstraintState', 'mission-constraint', False), (6, 'MissionResolutionState', 'mission-resolution', True)]
KIND_OF = {cls: (col, kind, derived) for col, cls, kind, derived in COLUMNS}
#: the fields of a state that only the derivation may set (a Purpose state is authored for its Purpose and importance only)
DERIVED_FIELDS = {'MissionPurposeState': ('title', 'status', 'resolution', 'why'),
                  'MissionResolutionState': ('resolution', 'why', 'estimates')}
_COL_W, _ROW_H, _W, _H = 215, 125, 190, 96


def solution_name(mission):
    return SOLUTION_PREFIX + mission


def _j(text, default):
    return MD._j(text, default)


def _node(name, cls, title, sentence, fields, links=()):
    f = dict(fields, displayName=title, purpose=sentence)
    if links:
        f['detail_ref'] = {'class': 'LinkTarget', 'name': links[0][0], 'route': links[0][1]}
        f['links'] = [{'label': a, 'route': b} for a, b in links]
    return {'name': name, 'cls': cls, 'fields': f}


def settings_of(m):
    s = _j(m.get('settings_json'), {})
    if s.get('objective') not in OBJECTIVES:
        s = dict(s, objective=DEFAULT_OBJECTIVE)
    return s


def _states(m, manager, derive):
    """[node] in reading order, columns in COLUMNS order."""
    name = m.get('name', '')
    out = []
    t, s = T.goal_card(m)
    out.append(_node('mission', 'MissionGoalState', t, s,
                     {'title': m.get('title') or name, 'goal': m.get('goal', ''), 'lifecycle': m.get('lifecycle') or 'enabled'},
                     [('All the Missions', MISSIONS_ROUTE)]))
    st = settings_of(m)
    t, s = T.settings_card(st)
    out.append(_node('settings', 'MissionSettingsState', t, s, {'objective': st['objective'], 'notes': st.get('notes', '')}))
    for row in MD.purpose_rows(m, manager):
        t, s = T.purpose_card(row, derive)
        f = {'purpose_name': row['purpose'], 'importance': row['importance']}
        if derive:
            f.update(title=row['title'], status=row['status'], resolution=row['resolution'], why=row['why'])
        else:
            f.update({k: PLACEHOLDER for k in DERIVED_FIELDS['MissionPurposeState']})
        out.append(_node('purpose-%s' % row['purpose'], 'MissionPurposeState', t, s, f,
                         [('This Purpose\'s own drawing', row['drawing'])] if row['known'] else ()))
    for i, p in enumerate(_j(m.get('participants_json'), []), 1):
        t, s = T.participant_card(p)
        out.append(_node('participant-%d' % i, 'MissionParticipantState', t, s, {k: str(p.get(k, '')) for k in ('role', 'kind', 'ref', 'variant')}))
    con = _j(m.get('constraints_json'), {})
    t, s = T.constraint_card(con)
    out.append(_node('constraints', 'MissionConstraintState', t, s,
                     {'stage': con.get('stage', ''), 'allowed_boards': ','.join(con.get('allowed_boards') or [])}))
    if derive:
        res = MD.resolution(m, manager)
        t, s = T.resolution_card(res['state'], res['why'])
        out.append(_node('resolution', 'MissionResolutionState', t, s,
                         {'resolution': res['state'], 'why': res['why'], 'estimates': res['estimates']}))
    else:
        t, s = T.resolution_card('', '', derive=False)
        out.append(_node('resolution', 'MissionResolutionState', t, s, {k: PLACEHOLDER for k in DERIVED_FIELDS['MissionResolutionState']}))
    return out


def render_definition(m, manager=None, derive=True):
    """The graph_builder definition of ONE Mission: six columns left to right (a stack where there are several Purposes /
    participants); every state in a column points `then` at the first state of the next column."""
    nodes = _states(m, manager, derive)
    cols = {}
    for n in nodes:
        cols.setdefault(KIND_OF[n['cls']][0], []).append(n)
    order = sorted(cols)
    states = []
    for ci, col in enumerate(order):
        nxt = cols[order[ci + 1]][0]['name'] if ci + 1 < len(order) else None
        for k, n in enumerate(cols[col]):
            _c, _kind, derived = KIND_OF[n['cls']]
            st = GB.node(n['name'], n['cls'], dict(n['fields'], derived=derived), outs=[[nxt] if nxt else []])
            st['stateLocationX'], st['stateLocationY'] = 40 + _COL_W * ci, 60 + _ROW_H * k
            st['shapeType'] = st['stateSvgName'] = 'rectangle'
            st['layerName'] = 'rectangle-layer'
            st['backgroundColor'] = '#9E9E9E' if derived else '#AD1457'
            st['slotRadius'] = 5
            st['stateSvgWidth'], st['stateSvgHeight'], st['cornerRadius'] = _W, _H, 8
            st['stateSvgRadius'] = None
            st['stateSvgSizeX'] = st['stateSvgSizeY'] = None
            st['runtime'] = ''
            states.append(st)
    d = GB.solution(solution_name(m.get('name', '')), *states)
    d['edgeKind'] = 'then'
    try:
        from hwnocode.custom import solutions as S
        S._wire_connectors(d)
    except Exception:  # noqa: BLE001 - the canvas wiring ids are cosmetic; the drawing is still valid
        pass
    return d


def contract():
    return {'description': 'A Hardware Mission drawn as a sentence: what it is for, what the solution aims at, the Purposes it needs and '
                           'how much each matters, who and what takes part, the limits, and whether it can be done with the hardware '
                           'there is. Declarative: nothing here is executed.',
            'inputs': [], 'returns': [], 'executionRights': 'definer'}


def render(m, manager=None, derive=True):
    """The SolutionDefinition ROW dict for one Mission (category 'mission'); `definition` is the JSON of render_definition."""
    name = solution_name(m.get('name', ''))
    return {'name': name, 'function_name': name.replace('-', '_'), 'target_runtime': 'python_backend',
            'definition': json.dumps(render_definition(m, manager, derive)), 'contract_json': json.dumps(contract()),
            'category': CATEGORY}


def validate(definition):
    """(ok, why) - only the six Mission kinds; compute and runtime kinds are refused by name (the category validator)."""
    from hwnocode.custom import cross_domain as CD
    return CD.validate(definition, CATEGORY)


# ---------------------------------------------------------------------------------------------------- write back
def _board_exists(ref, manager):
    from cmod.custom import purpose_nocode as PN
    return PN._ref_exists('board', ref, manager)


def write_back(definition, m, manager=None):
    """(ok, why, changes) - turn the drawing's edits into the row's fields. `changes` is {field: new value} for ONLY the fields that
    differ from `m`; the caller writes them to the HardwareMission row (the one source of truth) and re-renders. Refuses, naming the
    state: a non-Mission kind (validate), an edit to a derived field, an unknown life stage / aim / importance / Purpose / board /
    stage / participant kind, a Purpose named twice, and a drawing with no Mission state."""
    ok, why = validate(definition)
    if not ok:
        return False, why, {}
    got = {}
    for s in definition.get('stateInstances') or []:
        got.setdefault(s.get('stateClass') or s.get('stateName'), []).append(s)
    f = lambda s: dict(s.get('boundObjectFieldValues') or {})   # noqa: E731
    rows = {r['purpose']: r for r in MD.purpose_rows(m, manager)}
    res = MD.resolution(m, manager)
    fresh_res = {'resolution': res['state'], 'why': res['why'], 'estimates': res['estimates']}
    for cls, keys in DERIVED_FIELDS.items():
        for s in got.get(cls, []):
            if cls == 'MissionPurposeState':
                was = str(s.get('stateName', ''))[len('purpose-'):]
                if f(s).get('purpose_name', '') != was and was in rows:
                    continue     # the state was re-pointed at another Purpose: its old derived words are stale, not an edit
                mine_of = rows.get(f(s).get('purpose_name', ''), {})
            else:
                mine_of = fresh_res
            for k in keys:
                v, mine = f(s).get(k), mine_of.get(k)
                if v is not None and str(v) not in ('', PLACEHOLDER, str(mine)):
                    return False, ('refused: state %r (%s) is derived here - its %s is worked out, never typed in (got %r, it is %r)'
                                   % (s.get('stateName'), KIND_OF[cls][1], k, v, mine)), {}
    changes = {}
    goal = got.get('MissionGoalState')
    if not goal:
        return False, 'refused: the drawing has no Mission state (MissionGoalState); it is the one state that cannot be removed', {}
    g = f(goal[0])
    if g.get('lifecycle', m.get('lifecycle')) not in LIFECYCLES:
        return False, 'refused: state %r - life stage %r is not one of %s' % (goal[0].get('stateName'), g.get('lifecycle'), ', '.join(LIFECYCLES)), {}
    for fld in ('title', 'goal', 'lifecycle'):
        if fld in g and g[fld] != (m.get(fld) or ('enabled' if fld == 'lifecycle' else '')):
            changes[fld] = g[fld]
    for s in got.get('MissionSettingsState', [])[:1]:
        v = f(s)
        if v.get('objective', '') not in OBJECTIVES:
            return False, ('refused: state %r - aim %r is not one of %s' % (s.get('stateName'), v.get('objective'), ', '.join(OBJECTIVES))), {}
        old = _j(m.get('settings_json'), {})
        new = dict(old, objective=v['objective'])
        if v.get('notes', '') or 'notes' in old:
            new['notes'] = v.get('notes', '')
        if new != old:
            changes['settings_json'] = json.dumps(new)
    purposes, seen = [], set()
    for s in got.get('MissionPurposeState', []):
        v = f(s)
        pn, imp = str(v.get('purpose_name', '')), str(v.get('importance', ''))
        if not pn or MD.capability(pn, manager) is None:
            return False, 'refused: state %r - there is no Purpose named %r' % (s.get('stateName'), pn), {}
        if imp not in IMPORTANCES:
            return False, ('refused: state %r - importance %r must be one of %s' % (s.get('stateName'), imp, ', '.join(IMPORTANCES))), {}
        if pn in seen:
            return False, 'refused: state %r - Purpose %r is already in this Mission' % (s.get('stateName'), pn), {}
        seen.add(pn)
        purposes.append({'purpose': pn, 'importance': imp})
    if purposes != _j(m.get('purposes_json'), []):
        changes['purposes_json'] = json.dumps(purposes)
    parts = []
    for s in got.get('MissionParticipantState', []):
        p = {k: str(f(s).get(k, '')) for k in ('role', 'kind', 'ref', 'variant')}
        if p['kind'] not in PARTICIPANT_KINDS:
            return False, 'refused: state %r - participant kind %r must be hardware, software or person' % (s.get('stateName'), p['kind']), {}
        if not p['role']:
            return False, 'refused: state %r - a participant needs a role' % s.get('stateName'), {}
        parts.append({k: v for k, v in p.items() if v})
    if parts != _j(m.get('participants_json'), []):
        changes['participants_json'] = json.dumps(parts)
    for s in got.get('MissionConstraintState', [])[:1]:
        v = f(s)
        stage = str(v.get('stage', ''))
        if stage and stage not in STAGES:
            return False, 'refused: state %r - stage %r is not one of %s' % (s.get('stateName'), stage, ', '.join(STAGES)), {}
        boards = [b.strip() for b in str(v.get('allowed_boards', '')).split(',') if b.strip()]
        for b in boards:
            if not _board_exists(b, manager):
                return False, 'refused: state %r - there is no board named %r' % (s.get('stateName'), b), {}
        new = {}
        if stage:
            new['stage'] = stage
        if boards:
            new['allowed_boards'] = boards
        if new != _j(m.get('constraints_json'), {}):
            changes['constraints_json'] = json.dumps(new)
    return True, 'ok: %d field(s) changed' % len(changes), changes
