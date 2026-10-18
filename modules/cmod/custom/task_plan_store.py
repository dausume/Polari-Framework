"""
@module cmod.custom.task_plan_store

fgm-3: the Task Plan's rows and the two records it keeps honestly.

  DESIGNED FOR   the origin context (Hardware System, processors, tier, variants, pins, the solver run's sha256) is written ONCE - at the first record - and never changed: a later derive (another
                 candidate, another tier) still reports the stored one, and says so.
  ALSO RUNS ON   every other hardware the plan was carried to, each with HOW WE KNOW: resolver-valid (every checkable requirement met by sol-0's assignment; untested) < proven-on-twin < proven-on-hardware,
                 plus what had to change. `check_also_runs_on` resolves the SAME variants on another board from the run's own record and appends a row.

The Task rows hold the DERIVED values only; a person's edit is a DerivedOverride (task_plan_edit) and survives every re-record.
"""
import datetime
import json

HOW_WE_KNOW = ('resolver-valid', 'proven-on-twin', 'proven-on-hardware')
CLASSES = ('TaskPlan', 'TaskDefinition', 'TaskTrigger', 'TaskStructBinding')


def _j(s, default):
    try:
        v = json.loads(s) if isinstance(s, str) and s else s
        return default if v in (None, '') else v
    except ValueError:
        return default


def plan_row(name, manager):
    return next((r for r in ((getattr(manager, 'objectTables', None) or {}).get('TaskPlan') or {}).values() if getattr(r, 'name', '') == name), None) if manager is not None else None


def merge_stored(plan, manager):
    """Lay the stored record over a fresh derivation: the stored designed_for wins (immutable), the stored also-runs-on list is carried."""
    row = plan_row(plan['name'], manager)
    if row is None:
        return plan
    df = _j(row.designed_for_json, {})
    if df.get('tier'):
        if any(df.get(k) != plan['designed_for'].get(k) for k in ('hardware', 'tier', 'variants', 'pins', 'result_sha256')):
            plan['notes'].append('Designed for is the recorded origin context (%s, tier %s); this derivation used %s, tier %s - the record is never changed.' % (
                df.get('hardware') or df.get('hardware_system'), df.get('tier') or 'undetermined', plan['designed_for'].get('hardware') or plan['designed_for'].get('hardware_system'), plan['tier'] or 'undetermined'))
        plan['designed_for'] = df
        plan['designed_for_recorded'] = True
    plan['also_runs_on'] = _j(row.also_runs_on_json, [])
    return plan


def _register(manager, cls_name, obj):
    table = manager.objectTables.setdefault(cls_name, {})
    if getattr(obj, 'id', None) not in table:
        table[getattr(obj, 'id', None) or len(table)] = obj


def _upsert(manager, cls, cls_name, name, fields):
    row = next((r for r in (manager.objectTables.get(cls_name) or {}).values() if getattr(r, 'name', '') == name), None)
    if row is not None:
        for k, v in fields.items():
            setattr(row, k, v)
    else:
        row = cls(manager=manager, name=name, **fields)
        _register(manager, cls_name, row)
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        try:
            db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001 - a save failure is logged by the DB layer; the row stays in the tree
            pass
    return row


def store_plan(plan, manager, who=''):
    """Record a derived plan: upsert its TaskPlan row (designed_for + also_runs_on only on the FIRST write), its Task / Trigger / Struct-binding rows (derived values only). -> the TaskPlan row."""
    from cmod.cmod_basis import TaskPlan, TaskDefinition, TaskTrigger, TaskStructBinding
    now = datetime.datetime.now().isoformat(timespec='seconds')
    old = plan_row(plan['name'], manager)
    old_df = _j(old.designed_for_json, {}) if old is not None else {}
    first = not old_df.get('tier')       # an origin with no tier (no solver candidate yet) was never a context: it is not "written"
    df = dict(plan['designed_for'], recorded_at=now, recorded_by=who or '') if (first and plan['designed_for'].get('tier')) else (old_df if not first else {})
    fields = {'mission': plan['mission'], 'hardware_system': plan['hardware_system'], 'processors_json': json.dumps(plan['processors']), 'solve_run': plan['solve_run'], 'candidate': plan['candidate'],
              'tier': plan['tier'], 'variants_json': json.dumps(plan['variants'], sort_keys=True), 'pins_json': json.dumps(plan['pins']),
              'designed_for_json': json.dumps(df, sort_keys=True), 'also_runs_on_json': old.also_runs_on_json if old is not None else '[]', 'source': 'derived',
              'task_count': len(plan['tasks']), 'derived_at': now, 'who': who, 'notes': plan['run_basis']}
    row = _upsert(manager, TaskPlan, 'TaskPlan', plan['name'], fields)
    keep = {t['name'] for t in plan['tasks']}
    for t in plan['tasks']:
        _upsert(manager, TaskDefinition, 'TaskDefinition', t['name'], {
            'plan': plan['name'], 'task': t['task'], 'title': t['title'], 'processor': t['processor'], 'purposes_json': json.dumps(t['purposes']), 'steps_json': json.dumps(t.get('derived_steps', t['steps'])),
            'steps_order': t.get('derived_steps_order', t['steps_order']), 'trigger': t.get('derived_trigger', t['trigger']), 'trigger_what': t['trigger_what'],
            'deadline_ms': t.get('derived_deadline_ms', t['deadline_ms']), 'deadline_basis': t['deadline_basis'], 'period_ms': t['period_ms'], 'priority': t.get('derived_priority', t['priority']),
            'priority_basis': t['priority_basis'], 'importance': t['importance'], 'context': t.get('derived_context', t['context']), 'routes_json': json.dumps(t['routes']),
            'pins_json': json.dumps(t['pins']), 'agreement': t.get('derived_agreement', t['agreement']), 'agreement_why': t.get('derived_agreement_why', t['agreement_why']), 'source': 'derived', 'notes': t['notes']})
    for tr in plan['triggers']:
        _upsert(manager, TaskTrigger, 'TaskTrigger', tr['name'], {k: v for k, v in tr.items() if k != 'name'})
    for b in plan['struct_bindings']:
        _upsert(manager, TaskStructBinding, 'TaskStructBinding', b['name'], {'plan': b['plan'], 'task': b['task'], 'target': b['target'], 'kind': b['kind'], 'access': b['access'],
                                                                              'steps_json': json.dumps(b['steps']), 'isr_shared': b['isr_shared'], 'isr_vectors': b['isr_vectors'],
                                                                              'atomic_today': b['atomic_today'], 'basis': b['basis']})
    for cls_name in ('TaskDefinition', 'TaskTrigger', 'TaskStructBinding'):      # a task that is no longer derived is retired, never silently deleted
        for r in (manager.objectTables.get(cls_name) or {}).values():
            if getattr(r, 'plan', '') == plan['name'] and r.name not in keep and not any(r.name.startswith(k + ':') for k in keep):
                if cls_name == 'TaskDefinition':
                    r.source = 'retired'
                    r.notes = 'no longer derived by the latest record of this plan'
    return row


def set_also_runs_on(row, rows, manager):
    row.also_runs_on_json = json.dumps(rows)
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        try:
            db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001
            pass


def _run_record(plan_row_, manager):
    """The recorded SolveRun a stored plan was seeded from -> its designed_for_json dict ({designed_for, also_runs_on, does_not_run_on}), or None."""
    from cmod.custom import solve_record as REC
    run = next((r for r in REC.rows(manager, plan_row_.mission) if r.name == plan_row_.solve_run), None)
    return (_j(run.designed_for_json, {}), run) if run is not None else (None, None)


def check_also_runs_on(plan_name, hardware, manager, how_we_know='resolver-valid', result=None, who=''):
    """Resolve the plan's SAME variants on another hardware via sol-0's assignment and append a row. -> (row dict | None, why, appended bool).
    `hardware` = 'board / package' (or just a package or a board name). `result` = a solve() result when the plan's run is not stored. A hardware the same variants do not resolve on is REFUSED with sol-0's reason."""
    if how_we_know not in HOW_WE_KNOW:
        return None, 'how_we_know must be one of %s' % ', '.join(HOW_WE_KNOW), False
    row = plan_row(plan_name, manager)
    if row is None:
        return None, 'no stored Task Plan %r (record it first: POST /api/missions/<mission>/task-plan)' % plan_name, False
    rec, run = _run_record(row, manager)
    if rec is None and result is not None:
        rec = {'designed_for': result['designed_for'], 'also_runs_on': result['also_runs_on'], 'does_not_run_on': result['does_not_run_on']}
    if rec is None:
        return None, 'the plan was seeded from no stored solve run (%s), so there is no assignment to resolve against; run the attempt engine and record the plan again' % (row.solve_run or 'none'), False
    want = (hardware or '').strip().lower()
    if not want:
        return None, 'a hardware is required (for example "arduino-uno-r3 / atmega328p-32-tqfp")', False
    match = lambda h: want == h.lower() or want in h.lower()   # noqa: E731
    hit = next((x for x in rec.get('also_runs_on', []) if match(x['hardware']) and x['tier'] == row.tier), None)
    if hit is None:
        no = next((x for x in rec.get('does_not_run_on', []) if match(x['hardware'])), None)
        if no is not None:
            return None, '%s does not run it: %s' % (no['hardware'], no.get('why', '')), False
        return None, 'sol-0\'s run %s lists no hardware matching %r that resolves the same variants (known: %s)' % (row.solve_run, hardware, '; '.join(x['hardware'] for x in rec.get('also_runs_on', [])) or 'none'), False
    rows = _j(row.also_runs_on_json, [])
    old = next((x for x in rows if x['hardware'] == hit['hardware'] and x['tier'] == hit['tier']), None)
    if old is not None:
        return old, 'already recorded', False
    out = {'hardware': hit['hardware'], 'tier': hit['tier'], 'how_we_know': how_we_know, 'what_changed': hit.get('what_changed', ''), 'detail': hit.get('how_we_know', ''),
           'proof_of_the_routes': hit.get('proof_of_the_routes', ''), 'at': datetime.datetime.now().isoformat(timespec='seconds'), 'who': who,
           'solve_run': row.solve_run}
    rows.append(out)
    set_also_runs_on(row, rows, manager)
    return out, '', True
