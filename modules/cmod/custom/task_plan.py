"""
@module cmod.custom.task_plan

fgm-3 (FIRMWARE_GENERATION_MODULE_PLAN.md section 9; SYSTEM_HIERARCHY_TERMINOLOGY.md section 8): THE TASK PLAN of a Hardware Mission on ONE Hardware System, DERIVED by code and editable by hand.

    Mission -> Purposes -> their graph's c-atoms + criteria  ->  Tasks grouped per processor and trigger (boot -> init; a button edge -> handle-button-press; a period -> relay-state;
    a command -> receive-command; an input line the Purposes need but no trigger covers -> sense), each Task's steps in graph order, its deadline / period from the Purpose criteria (or rt-0's labelled
    estimate), its context from its trigger and the runtime tier, its priority DEADLINE-MONOTONIC (importance breaks ties; still equal: the Mission's Purpose order, marked), its shared data from the
    atoms' own resources (`isr_shared` where an interrupt step and a loop step touch the same piece), and the variants / pins from a sol-0 candidate (the latest SolveRun, or one handed in).

The AGREEMENT CHECK compares each Task's context with the lane its atoms derive (`schedule_for`). A person's correction is a DerivedOverride (task_plan_edit) shown beside the derived value.
"Designed for" is written once (task_plan_store); "Also runs on" is appended with HOW WE KNOW. Pure Python: no engine. A manager only adds stored runs, stored plans and the people's corrections.

    python3 -m cmod.custom.task_plan derive <mission> [--system S] [--run R] [--solve] [--json]
"""
import json
import re

from cmod.custom import approach_profile_input as AI
from cmod.custom import task_plan_steps as ST

IMPORTANCE = AI.IMPORTANCE
TRIGGER_KIND = {'boot': 'boot', 'button': 'edge', 'edge': 'edge', 'period': 'period', 'command': 'command', 'message': 'message'}
TASK_NAME = {'boot': 'init', 'button': 'handle-button-press', 'period': 'relay-state', 'command': 'receive-command'}
TITLE = {'init': 'Set the board up', 'handle-button-press': 'Handle a button press', 'relay-state': 'Report the state', 'receive-command': 'Receive a command', 'sense': 'Sense the light line'}
#: the job that NOTICES each Purpose trigger (solve_inputs.TRIGGER_JOB, widened for the periodic report)
NOTICE_JOB = {'button': 'read-button', 'command': 'receive-command', 'period': 'report-state'}
INPUT_KINDS = ('digital-in', 'interrupt-in', 'pin-change-in', 'analog-in', 'comparator-in')
RULE = ('deadline-monotonic: a shorter deadline is a higher priority (1 is the highest); equal deadlines: the more important Purpose wins; still equal: the Mission\'s Purpose order (marked as a tie); '
        'a task that runs once at boot, or in an interrupt handler, has priority 0 (no scheduler orders it)')


def _j(s, default):
    try:
        v = json.loads(s) if isinstance(s, str) and s else s
        return default if v in (None, '') else v
    except ValueError:
        return default


def _num(qv):
    return float(qv['value']) if isinstance(qv, dict) and isinstance(qv.get('value'), (int, float)) else -1.0


def _qtext(qv):
    return '%s %s (%s)' % (qv['value'], qv.get('unit', ''), qv['kind']) if isinstance(qv, dict) and isinstance(qv.get('value'), (int, float)) else 'undetermined'


# ------------------------------------------------------------------ the inputs: Hardware System, solver candidate
def system_row(name, manager=None):
    """-> dict {name, title, participants[], boards[]} of a Hardware System (a live row, else the code-owned seed). Raises ValueError for an unknown one."""
    rows = ((getattr(manager, 'objectTables', None) or {}).get('HardwareSystem') or {}).values() if manager is not None else []
    hit = next((r for r in rows if getattr(r, 'name', '') == name), None)
    if hit is not None:
        d = {k: getattr(hit, k, '') for k in ('name', 'title', 'participants_json', 'boards_json', 'stage')}
    else:
        from board.custom import hardware_system as H
        from board.custom import hwsys_system as HS
        d = next((r for r in HS.rows(H.default_tables(manager)) if r['name'] == name), None)
        if d is None:
            raise ValueError('no Hardware System %r (known: %s)' % (name, ', '.join(r['name'] for r in HS.rows(H.default_tables(manager)))))
    return dict(d, participants=_j(d.get('participants_json'), []), boards=_j(d.get('boards_json'), []))


def default_system(board, manager=None):
    """The name of a Hardware System whose board is `board` (the Mission's own board participant), else the first system there is. '' when none."""
    from board.custom import hardware_system as H
    from board.custom import hwsys_system as HS
    rows = [dict(r) for r in HS.rows(H.default_tables(manager))]
    for r in rows:
        if 'BoardDefinition:%s' % board in _j(r.get('boards_json'), []):
            return r['name']
    return rows[0]['name'] if rows else ''


def processors_of(system, board):
    """[{name, board, role}] - the system's mcu chips (each Task runs on exactly ONE). A system with none gets the board itself, said."""
    out = []
    for p in system['participants']:
        ref = p.get('ref', '')
        if '(mcu)' in p.get('role', '') and ref.startswith('BoardComponent:'):
            _c, b, comp = ref.split(':', 2)
            out.append({'name': '%s:%s' % (b, comp), 'board': b, 'role': p['role']})
    return out or [{'name': board, 'board': board, 'role': 'the board (the system names no mcu chip)'}]


def resolve_run(mission, solve_run=None, candidate=None, manager=None):
    """-> (run dict {name, result_sha256, objective, ran_at} | None, candidate dict | None, basis text). `solve_run` = a SolveRun row, its name, or a solve() result dict; None = the latest stored run."""
    from cmod.custom import solve_record as REC
    run = None
    if isinstance(solve_run, dict):
        cand = solve_run.get('chosen_candidate')
        if candidate and cand and cand['id'] != candidate:
            cand = next((c for c in solve_run.get('candidates', []) if c['id'] == candidate), None)
            if cand is None:
                raise KeyError('no candidate %r in that run (the listed ones: %s)' % (candidate, ', '.join(c['id'] for c in solve_run.get('candidates', [])[:8])))
        return ({'name': 'computed now (%s)' % solve_run['result_sha256'][:10], 'result_sha256': solve_run['result_sha256'], 'objective': solve_run['objective'], 'ran_at': ''}, cand,
                'seeded from the attempt engine\'s run computed now (result sha256 %s, not stored)' % solve_run['result_sha256'][:12])
    if solve_run is not None and not isinstance(solve_run, str):
        run = solve_run
    elif solve_run:
        run = next((r for r in REC.rows(manager, mission) if r.name == solve_run), None) if manager is not None else None
        if run is None:
            raise KeyError('no stored run %r of Mission %r (GET /api/missions/%s/solve-runs lists them)' % (solve_run, mission, mission))
    elif manager is not None:
        rows = REC.rows(manager, mission)
        run = rows[-1] if rows else None
    if run is None:
        return None, None, ('NO solve run exists for Mission %s: the variants, the pins and the sense task are undetermined until the attempt engine has run '
                            '(POST /api/missions/%s/solve, or `pol capability solve mission %s`)' % (mission, mission, mission))
    chosen = _j(run.chosen_json, {})
    if candidate and run.chosen != candidate:
        raise KeyError('only the chosen candidate of a stored run is kept in full (%s); candidate %r is not it' % (run.chosen, candidate))
    if not chosen:
        return ({'name': run.name, 'result_sha256': run.result_sha256}, None, 'run %s found no candidate that could be placed' % run.name)
    return ({'name': run.name, 'result_sha256': run.result_sha256, 'objective': run.objective, 'ran_at': run.ran_at}, chosen,
            'seeded from solve run %s, candidate %s (%s)' % (run.name, chosen.get('id', '?'), chosen.get('routes_text', '')))


# ------------------------------------------------------------------ the derivation
def _importance(purposes):
    rank = {k: i for i, k in enumerate(IMPORTANCE)}
    return min((p['importance'] for p in purposes), key=lambda k: rank.get(k, 9), default='')


def _deadline(purposes):
    """(ms, basis) - the tightest deadline of the Purposes (a criterion), or (-1, why)."""
    best = None
    for p in purposes:
        v = _num(p.get('deadline_ms'))
        if v >= 0 and (best is None or v < best[0]):
            best = (v, p)
    if best is None:
        return -1.0, 'undetermined: no Purpose this task serves states a deadline'
    return best[0], '%s: Purpose %s, %s' % (best[1]['deadline_ms']['kind'], best[1]['purpose'], best[1]['deadline_key'])


def _assign_info(cand, purposes):
    """(routes, pins) of the candidate's assignment rows that serve any of `purposes`."""
    if not cand:
        return [], []
    names = {p['purpose'] for p in purposes}
    routes, pins = [], []
    for a in cand.get('assignment', []):
        if names & set(a.get('purposes') or []):
            if not any(r['job'] == a['job'] for r in routes):
                routes.append({'job': a['job'], 'route': a['route'], 'status': (cand.get('variant_status') or {}).get(a['job'], '')})
            pins.append({'role': a['role'], 'kind': a['kind'], 'job': a['job'], 'route': a['route'], 'pin': a['pin'], 'function': a['function']})
    return routes, pins


def _trigger(kind, purposes, cand, steps, task, tick):
    """The TaskTrigger dict of a Task."""
    what = '; '.join(dict.fromkeys(p['trigger'].get('what', '') for p in purposes if p['trigger'].get('what')))
    out = {'kind': kind, 'what': what, 'source': '', 'how': '', 'route': '', 'debounce_ms': -1.0, 'period_ms': -1.0, 'period_basis': '', 'notes': ''}
    pk = purposes[0]['trigger'].get('kind', '') if purposes else ''
    deb = [p for p in purposes if p.get('debounce_ms')]
    if deb:
        out['debounce_ms'] = _num(deb[0]['debounce_ms'])
        out['notes'] = 'debounce %s ms is %s; the budget left for the work is the deadline minus the debounce' % (int(out['debounce_ms']), deb[0]['debounce_ms']['basis'])
    isr = next((s for s in steps if s['lane'] == 'isr'), None)
    if kind == 'boot':
        out['how'] = 'once at boot, before the interrupts are enabled'
        return out
    if kind == 'period':
        per = next((p['period_ms'] for p in purposes if p.get('period_ms')), None)
        out['period_ms'] = _num(per)
        out['period_basis'] = per['basis'] if per else 'undetermined: no tick-fed task states a period'
        out['source'] = isr['instance'] if isr else ''
        out['how'] = 'every period, counted on the 1 ms tick'
        notice = NOTICE_JOB.get(pk)
    else:
        notice = NOTICE_JOB.get(pk)
    a = next((x for x in (cand or {}).get('assignment', []) if x['job'] == notice), None)
    if a is not None and kind != 'period':
        out['route'] = a['route']
        out['source'] = '%s (%s)' % (a['pin'], a['function'])
        out['how'] = 'interrupt' if 'interrupt' in a['route'] else 'polled in the main loop'
        if isr and 'interrupt' not in a['route']:
            out['notes'] = (out['notes'] + '; ' if out['notes'] else '') + ('the graph\'s atoms today implement the interrupt route (%s); the chosen route %s is %s' % (
                isr['instance'], a['route'], (cand.get('variant_status') or {}).get(notice, 'not yet built')))
    elif a is not None:
        out['route'] = a['route']
    elif isr:
        out['source'] = isr['instance']
        out['how'] = 'interrupt (from the graph; no solver candidate to say otherwise)'
    else:
        out['how'] = 'not stated (no solver candidate and no interrupt in the graph)'
    return out


def derive_task_plan(mission, hardware_system=None, solve_run=None, candidate=None, manager=None, spec=None, apply_edits=True):
    """-> the Task Plan of `mission` on `hardware_system` (see the module doc). `spec` (rt-0's normalised input) is for tests / synthetic Missions. Raises ValueError for an unknown Mission or system,
    KeyError for an unknown run or candidate."""
    from cmod.custom import task_plan_store as STORE
    spec = spec or AI.from_mission(mission, manager)
    mname = spec['mission']
    sysname = hardware_system or default_system(spec['board_ref'], manager)
    system = system_row(sysname, manager)
    run, cand, run_basis = resolve_run(mname, solve_run, candidate, manager)
    tier = (cand or {}).get('tier', '')
    procs = processors_of(system, spec['board_ref'])
    soc = ((cand or {}).get('hardware') or {}).get('soc', '')
    for p in procs:
        p['soc'] = soc if p['board'] == ((cand or {}).get('hardware') or {}).get('board') else ''
    plan_name = '%s:%s' % (mname, sysname)
    def ctx_of(kind, steps):
        """The context the Task's own atoms' lanes derive (init | loop | isr); with no scheduled atom to read, the trigger and the runtime tier decide (boot -> init; else the main loop / an RTOS thread)."""
        c = ST.lane_context(steps) or ('init' if kind == 'boot' else 'loop')
        return 'task' if c == 'loop' and tier in ('freertos', 'zephyr') else c

    groups, order = {}, []
    for p in spec['purposes']:
        if p.get('missing') or not p['graph']:
            continue
        key = (p['graph'], str(p['trigger'].get('kind', '')))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(p)
    tasks, triggers, bindings = [], [], []
    for graph, pkind in order:
        ps = groups[(graph, pkind)]
        kind = TRIGGER_KIND.get(pkind, 'message')
        tname = TASK_NAME.get(pkind, 'handle-%s' % re.sub(r'[^a-z0-9]+', '-', pkind.lower()).strip('-') or 'message')
        gproc = next((x for x in spec['processors'] if x['name'] == graph), {})
        proc = next((x for x in procs if x['board'] == gproc.get('board')), procs[0])
        steps = ST.graph_steps(graph, [i for p in ps for i in p['tasks']], kind if kind != 'edge' else 'edge', kind == 'boot')
        dl, dl_basis = _deadline(ps)
        trig = _trigger(kind, ps, cand, steps, tname, None)
        routes, pins = _assign_info(cand, ps)
        note = []
        if trig['notes']:
            note.append(trig['notes'])
        tasks.append({'task': tname, 'title': TITLE.get(tname, tname), 'graph': graph, 'processor': proc['name'], 'purposes': [p['purpose'] for p in ps], 'steps': steps,
                      'trigger': kind, 'trigger_what': trig['what'], 'deadline_ms': dl, 'deadline_basis': dl_basis, 'period_ms': trig['period_ms'], 'importance': _importance(ps),
                      'context': ctx_of(kind, steps), 'routes': routes, 'pins': pins, 'notes': '; '.join(note), '_trigger': trig})
    # an input line the Purposes need that no trigger above already covers -> its own Task (the sense task)
    covered = {NOTICE_JOB.get(k[1]) for k in order}
    by_p = {p['purpose']: p for p in spec['purposes']}
    for a in (cand or {}).get('assignment', []):
        if a['kind'] not in INPUT_KINDS or a['job'] in covered:
            continue
        ps = [by_p[n] for n in a.get('purposes', []) if n in by_p]
        if not ps:
            continue
        tname = 'sense' if 'sense' in a['role'] else a['job']
        graph = ps[0]['graph']
        gproc = next((x for x in spec['processors'] if x['name'] == graph), {})
        proc = next((x for x in procs if x['board'] == gproc.get('board')), procs[0])
        steps = _variant_steps(a['job'], a['route'], graph)
        boot_atoms = [s for s in steps if s['lane'] == 'init']
        steps = [s for s in steps if s['lane'] != 'init']
        for i, s in enumerate(steps, 1):
            s['n'] = i
        dl, dl_basis = _deadline(ps)
        trig = {'kind': 'edge', 'what': 'a change on the %s' % a['role'], 'source': '%s (%s)' % (a['pin'], a['function']), 'how': 'interrupt' if 'interrupt' in a['route'] else 'polled in the main loop',
                'route': a['route'], 'debounce_ms': -1.0, 'period_ms': -1.0, 'period_basis': '',
                'notes': 'this line is needed by %s; no Purpose names a task for it, so it is its own task%s' % (
                    ', '.join(p['purpose'] for p in ps), ('; %s belongs to the init task' % ', '.join(s['instance'] for s in boot_atoms)) if boot_atoms else '')}
        routes, pins = _assign_info(cand, [{'purpose': p['purpose']} for p in ps])
        routes = [r for r in routes if r['job'] == a['job']]
        pins = [x for x in pins if x['job'] == a['job']]
        status = (cand.get('variant_status') or {}).get(a['job'], '')
        tasks.append({'task': tname, 'title': TITLE.get(tname, tname), 'graph': graph, 'processor': proc['name'], 'purposes': [p['purpose'] for p in ps], 'steps': steps,
                      'trigger': 'edge', 'trigger_what': trig['what'], 'deadline_ms': dl, 'deadline_basis': dl_basis, 'period_ms': -1.0, 'importance': _importance(ps),
                      'context': ctx_of('edge', steps), 'routes': routes, 'pins': pins, 'notes': trig['notes'], '_trigger': trig,
                      '_route_note': 'the chosen route %s has status %s and no atoms are linked to it yet' % (a['route'], status or 'unknown') if not steps else ''})
    _priorities(tasks)
    plan_tasks = []
    for t in tasks:
        name = '%s:%s' % (plan_name, t['task'])
        ver, why = ST.agreement(t['context'], t['steps'], t.get('_route_note', ''), t['trigger'])
        row = {'name': name, 'plan': plan_name, 'task': t['task'], 'title': t['title'], 'processor': t['processor'], 'purposes': t['purposes'], 'steps': t['steps'],
               'steps_order': ','.join(s['instance'] for s in t['steps']), 'trigger': t['trigger'], 'trigger_what': t['trigger_what'], 'deadline_ms': t['deadline_ms'],
               'deadline_basis': t['deadline_basis'], 'period_ms': t['period_ms'], 'priority': t['priority'], 'priority_basis': t['priority_basis'], 'importance': t['importance'],
               'context': t['context'], 'routes': t['routes'], 'pins': t['pins'], 'agreement': ver, 'agreement_why': why, 'source': 'derived', 'notes': t['notes']}
        plan_tasks.append(row)
        triggers.append(dict(t['_trigger'], name=name, plan=plan_name, task=t['task']))
        bindings += [dict(b, plan=plan_name, task=t['task']) for b in ST.struct_bindings(t['graph'], name, t['steps'])]
    variants = dict((cand or {}).get('routes') or {})
    pins_all = [{'role': a['role'], 'kind': a['kind'], 'job': a['job'], 'route': a['route'], 'pin': a['pin'], 'function': a['function']} for a in (cand or {}).get('assignment', [])]
    hw = (cand or {}).get('hardware') or {}
    plan = {'ok': True, 'name': plan_name, 'mission': mname, 'hardware_system': sysname, 'processors': procs, 'tier': tier, 'candidate': (cand or {}).get('id', ''),
            'solve_run': (run or {}).get('name', ''), 'run_basis': run_basis, 'variants': variants, 'pins': pins_all, 'tasks': plan_tasks, 'triggers': triggers, 'struct_bindings': bindings,
            'priority_rule': RULE, 'source': 'derived', 'notes': []}
    plan['designed_for'] = {'hardware_system': sysname, 'processors': [p['name'] for p in procs], 'hardware': ('%s / %s' % (hw.get('board', ''), hw.get('package', ''))) if hw else '', 'package': hw.get('package', ''), 'tier': tier,
                            'variants': variants, 'pins': pins_all, 'solve_run': (run or {}).get('name', ''), 'result_sha256': (run or {}).get('result_sha256', ''), 'mission': mname,
                            'basis': 'the origin context of this Task Plan: written once, never changed (terminology section 8)' if cand else 'no solver candidate existed when this was derived'}
    plan['also_runs_on'] = []
    plan['designed_for_recorded'] = False
    if not cand:
        plan['notes'].append(run_basis)
        plan['notes'].append('With no candidate the runtime tier is undetermined; the contexts assume the bare-C main loop.')
    STORE.merge_stored(plan, manager)
    if apply_edits:
        from cmod.custom import task_plan_edit as ED
        ED.apply_edits(plan, manager)
    plan['agreement_counts'] = {v: sum(1 for t in plan['tasks'] if t['agreement'] == v) for v in ('agrees', 'disagrees', 'unchecked')}
    return plan


def _variant_steps(job, route, graph):
    """Steps of a job-only Task (no Purpose graph node): the atoms the chosen route is implemented by, with the lane any seeded graph gives them ('' when none schedules them).
    fgm-5b: an isotope's own atom (hal_sense_poll.hal_sense_read) is in no graph; it takes the lane of the shipped atom of the same function it replaces. A `called` atom of a route WITH an interrupt in it stays
    `called` (the interrupt is the task's entry); in a route with none (polling) it runs where its caller runs - the main loop."""
    from cmod.custom import isotope_variants as V
    v = next((x for x in V.variants(job=job) if x['route'] == route), None)
    atoms = _j((v or {}).get('implemented_by_json'), {}).get('atoms', [])
    found = []
    for a in atoms:
        lane, g = ST.lane_of_atom(a, graph)
        found.append([a, lane, g, ''])
    has_isr = any(f[1] == 'isr' for f in found)
    for f in found:
        if not f[1]:
            lane, g, why = ST.lane_of_equivalent(f[0], graph, follow_caller=not has_isr)
            if lane == 'called':
                why = 'called by the loop task; the interrupt of this route is the entry'
            f[1:] = [lane, g, why]
    steps = []
    for i, (a, lane, g, why) in enumerate(found, 1):
        steps.append({'n': i, 'instance': a.partition(':')[2], 'atom': a, 'lane': lane, 'role': why or (('lane read from graph %s' % g) if g else 'not scheduled in any graph')})
    return steps


def _priorities(tasks):
    """Deadline-monotonic; importance breaks ties; still equal -> the Mission's Purpose order (the list order), marked."""
    rank = {k: i for i, k in enumerate(IMPORTANCE)}
    live = [(i, t) for i, t in enumerate(tasks) if t['context'] not in ('init', 'isr')]
    key = lambda it: (it[1]['deadline_ms'] if it[1]['deadline_ms'] >= 0 else float('inf'), rank.get(it[1]['importance'], 9), it[0])   # noqa: E731
    live.sort(key=key)
    for n, (_i, t) in enumerate(live, 1):
        t['priority'] = n
        tie = [o for _j2, o in live if o is not t and key((0, o))[:2] == key((0, t))[:2]]
        t['priority_basis'] = ('deadline %s, importance %s%s' % (_fmt_ms(t['deadline_ms']), t['importance'] or 'none',
                                                                  ('; TIE with %s - ordered only by the Mission\'s Purpose order' % ', '.join(o['task'] for o in tie)) if tie else ''))
    for t in tasks:
        if t['context'] == 'init':
            t['priority'] = 0
            t['priority_basis'] = 'runs once at boot, before any scheduling'
        elif t['context'] == 'isr':
            t['priority'] = 0
            t['priority_basis'] = 'runs in an interrupt handler: the hardware, not a scheduler, orders it'


# ------------------------------------------------------------------ plain-words rows (page tables) and the CLI
def _fmt_ms(v):
    return 'undetermined' if v is None or v < 0 else ('%g ms' % v)


def task_rows(plan):
    rows = []
    for t in plan['tasks']:
        edits = {e['field']: e for e in t.get('edits', [])}
        rows.append({'task': t['task'], 'processor': t['processor'], 'trigger': '%s: %s' % (t['trigger'], t['trigger_what']), 'deadline': _fmt_ms(t['deadline_ms']),
                     'priority': ('%s (edited; derived %s)' % (t['priority'], edits['priority']['derived'])) if 'priority' in edits else str(t['priority']), 'importance': t['importance'],
                     'context': t['context'], 'steps': ' > '.join(s['instance'] for s in t['steps']) or 'none yet', 'agreement': t['agreement'], 'serves': ', '.join(t['purposes'])})
    return rows


def agreement_rows(plan):
    return [{'task': t['task'], 'context': t['context'], 'lanes_of_its_atoms': ', '.join('%s: %s' % (s['instance'], s['lane'] or 'none') for s in t['steps']) or 'no steps', 'verdict': t['agreement'],
             'why': t['agreement_why']} for t in plan['tasks']]


def trigger_rows(plan):
    return [{'task': t['task'], 'kind': t['kind'], 'what': t['what'], 'source': t['source'] or '-', 'how': t['how'], 'route': t['route'] or '-', 'debounce': _fmt_ms(t['debounce_ms']),
             'period': _fmt_ms(t['period_ms']), 'notes': t['notes'] or t['period_basis']} for t in plan['triggers']]


def shared_rows(plan):
    return [{'task': b['task'], 'shared_data': b['target'], 'kind': b['kind'], 'access': b['access'], 'touched_by': ', '.join(b['steps']), 'interrupt_and_loop': ('yes: ' + b['isr_vectors']) if b['isr_shared'] else 'no',
             'protected_today': b['atomic_today']} for b in plan['struct_bindings']]


def edit_rows(plan):
    out = []
    for t in plan['tasks']:
        for e in t.get('edits', []):
            out.append({'task': t['task'], 'field': e['field'], 'derived_value': e['derived'], 'edited_value': e['value'], 'who': e['who'] or 'an unauthenticated request', 'when': e['when'][:10], 'why': e['why'],
                        'still_current': e['flag'] or 'the derived value is unchanged since the edit'})
    return out or [{'task': '-', 'field': '-', 'derived_value': '-', 'edited_value': '-', 'who': '-', 'when': '-', 'why': 'no task has been edited by hand', 'still_current': '-'}]


def designed_rows(plan):
    d = plan['designed_for']
    rows = [{'what': 'Designed for', 'hardware': d.get('hardware') or d.get('hardware_system', ''), 'tier': d.get('tier') or 'undetermined',
             'detail': 'system %s; processors %s; routes %s' % (d.get('hardware_system', ''), ', '.join(d.get('processors', [])), ', '.join('%s via %s' % kv for kv in sorted((d.get('variants') or {}).items())) or 'undetermined (no solve run)'),
             'how_we_know': '%s' % ('recorded' if plan.get('designed_for_recorded') else 'not recorded yet (written once, at the first record)')}]
    for a in plan['also_runs_on']:
        rows.append({'what': 'Also runs on', 'hardware': a['hardware'], 'tier': a['tier'], 'detail': a.get('what_changed', ''), 'how_we_know': a['how_we_know']})
    return rows


def _print(plan):
    print('Task Plan %s - system %s, tier %s' % (plan['name'], plan['hardware_system'], plan['tier'] or 'undetermined'))
    print('  %s' % plan['run_basis'])
    print('  processors: %s' % ', '.join(p['name'] for p in plan['processors']))
    for t in plan['tasks']:
        print('  %-20s on %-22s trigger %-8s deadline %-9s priority %-2s importance %-9s context %-5s agreement %s' % (
            t['task'], t['processor'], t['trigger'], _fmt_ms(t['deadline_ms']), t['priority'], t['importance'], t['context'], t['agreement']))
        print('        steps: %s' % (' > '.join('%s[%s]' % (s['instance'], s['lane']) for s in t['steps']) or 'none yet'))
        print('        %s; %s' % (t['priority_basis'], t['agreement_why']))
        for e in t.get('edits', []):
            print('        EDITED %s: %s (derived %s) by %s on %s - %s %s' % (e['field'], e['value'], e['derived'], e['who'] or '?', e['when'][:10], e['why'], e['flag']))
    for b in plan['struct_bindings']:
        if b['isr_shared']:
            print('  shared with an interrupt: %s (%s) in %s' % (b['target'], b['isr_vectors'], b['task']))
    print('  Priority rule: %s' % plan['priority_rule'])
    for a in plan['also_runs_on']:
        print('  Also runs on: %s / %s - %s' % (a['hardware'], a['tier'], a['how_we_know']))


def main(argv=None):
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog='pol capability tasks')
    ap.add_argument('cmd', choices=['derive'])
    ap.add_argument('mission')
    ap.add_argument('--system', default='')
    ap.add_argument('--run', default='')
    ap.add_argument('--solve', action='store_true', help='run the attempt engine now (2 s warm, 12-17 s cold) and seed the plan from its chosen candidate')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    try:
        run = None
        if a.solve:
            from cmod.custom import solve as S
            run = S.solve(a.mission)
        plan = derive_task_plan(a.mission, a.system or None, solve_run=run or (a.run or None))
    except (ValueError, KeyError) as e:
        print('[REFUSED] %s' % (e.args[0] if e.args else e))
        return 3
    print(json.dumps(plan, indent=1, default=str)) if a.json else _print(plan)
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
