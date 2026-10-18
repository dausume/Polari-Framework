"""
@module cmod.custom.task_plan_doors

fgm-3 doors, plain functions over a TaskPlanAPI (`cmod_task_plan_api` registers the routes and delegates here). Advised, never blocking.

GET  /api/missions/{name}/task-plan[?system=S][&run=R][&candidate=C][&solve=now][&view=tasks|agreement|triggers|shared-data|edits|designed-for]
        The Task Plan DERIVED now (nothing stored): {ok, name, mission, hardware_system, tier, run_basis, processors[], tasks[], triggers[], struct_bindings[], designed_for, also_runs_on[],
        agreement_counts, priority_rule, source, notes[]}. `system` defaults to the Hardware System that carries the Mission's board; `run` = a stored SolveRun name (default: the latest stored one);
        `solve=now` runs the attempt engine (cached) when no run is stored. With NO run the plan says so and the variants / pins / sense task are undetermined. With `view` the answer is the flat
        plain-words {ok, view, count, rows[]} for the page tables. 404 unknown Mission / system; 422 unknown run / candidate / view.
POST /api/missions/{name}/task-plan   body {system?, run?, candidate?, solve?: true}
        Derive and RECORD the plan (TaskPlan + Task / Trigger / Struct-binding rows; "Designed for" is written only the first time). -> 201 {ok, stored: true, plan}.
POST /api/task-plans/{plan}/also-runs-on   body {hardware, how_we_know?: resolver-valid|proven-on-twin|proven-on-hardware}
        Resolve the plan's SAME variants on another hardware through sol-0's recorded assignment and APPEND a row (a plan that is not recorded yet is derived and recorded first).
        -> 201 {ok, appended, row, also_runs_on[]}; 422 with sol-0's reason when the variants do not resolve there.
A correction of a Task is POST /api/firmware/overrides {target_class: "TaskDefinition", target_name: "<plan>:<task>", field, value, why}.
"""
import json

import falcon

from cmod.custom import task_plan as TP
from cmod.custom import task_plan_store as STORE

VIEWS = {'tasks': TP.task_rows, 'agreement': TP.agreement_rows, 'triggers': TP.trigger_rows, 'shared-data': TP.shared_rows, 'edits': TP.edit_rows, 'designed-for': TP.designed_rows}


def _body(request):
    try:
        return json.loads(request.bounded_stream.read() or b'{}')
    except Exception:  # noqa: BLE001
        return {}


def _who(request):
    ui = getattr(getattr(request, 'context', None), 'user_info', None) or {}
    return ui.get('preferred_username') or ui.get('sub') or ''


def _fail(response, status, text):
    response.status = status
    response.media = {'ok': False, 'error': text}


def _derive(api, name, system, run, candidate, solve_now, apply_edits=True):
    """-> (plan | None, status, error)."""
    run_arg = run or None
    if solve_now and not run:
        from cmod.custom import solve_doors as SD
        from cmod.custom import solve_record as REC
        if not (api.manager is not None and REC.rows(api.manager, name)):
            run_arg = SD.compute(name, None, None, None, {}, api.manager)
    try:
        return TP.derive_task_plan(name, system or None, solve_run=run_arg, candidate=candidate or None, manager=api.manager, apply_edits=apply_edits), None, ''
    except ValueError as e:
        return None, falcon.HTTP_404, str(e)
    except KeyError as e:
        return None, falcon.HTTP_422, e.args[0] if e.args else str(e)


def get_plan(api, request, response, name):
    p = request.params
    view = (p.get('view') or '').strip()
    if view and view not in VIEWS:
        return _fail(response, falcon.HTTP_422, 'no view %r (one of %s)' % (view, ', '.join(VIEWS)))
    plan, status, err = _derive(api, name, p.get('system'), p.get('run'), p.get('candidate'), p.get('solve') == 'now')
    if plan is None:
        return _fail(response, status, err)
    if view:
        rows = VIEWS[view](plan)
        response.media = {'ok': True, 'view': view, 'mission': plan['mission'], 'name': plan['name'], 'count': len(rows), 'rows': rows}
        return
    response.media = plan


def post_plan(api, request, response, name):
    if api.manager is None:
        return _fail(response, falcon.HTTP_422, 'no live manager on this server to record a Task Plan on')
    b = _body(request)
    run = b.get('run') or None
    if b.get('solve') and not run:       # the attempt engine runs now and its run is RECORDED, so the plan names a real SolveRun (and "also runs on" can read its assignment)
        from cmod.custom import solve_doors as SD
        from cmod.custom import solve_record as REC
        try:
            run = (REC.rows(api.manager, name) or [REC.store(api.manager, SD.compute(name, None, None, None, {}, api.manager), _who(request))])[-1].name
        except ValueError as e:
            return _fail(response, falcon.HTTP_404, str(e))
    plan, status, err = _derive(api, name, b.get('system'), run, b.get('candidate'), False, apply_edits=False)
    if plan is None:
        return _fail(response, status, err)
    STORE.store_plan(plan, api.manager, _who(request))
    out, status, err = _derive(api, name, plan['hardware_system'], run, b.get('candidate'), False)
    response.status = falcon.HTTP_201
    response.media = dict(out or plan, stored=True)


def post_also_runs_on(api, request, response, plan):
    if api.manager is None:
        return _fail(response, falcon.HTTP_422, 'no live manager on this server to record "also runs on" on')
    b = _body(request)
    row = STORE.plan_row(plan, api.manager)
    if row is None:
        mission, _c, system = plan.partition(':')
        p, status, err = _derive(api, mission, system, None, None, False, apply_edits=False)
        if p is None:
            return _fail(response, falcon.HTTP_404, 'no Task Plan %r (%s)' % (plan, err))
        if not p['candidate']:
            return _fail(response, falcon.HTTP_422, 'no Task Plan %r is recorded and no solve run exists to seed one (%s)' % (plan, p['run_basis']))
        STORE.store_plan(p, api.manager, _who(request))
    out, why, appended = STORE.check_also_runs_on(plan, b.get('hardware') or '', api.manager, b.get('how_we_know') or 'resolver-valid', who=_who(request))
    if out is None:
        return _fail(response, falcon.HTTP_422, why)
    response.status = falcon.HTTP_201 if appended else falcon.HTTP_200
    response.media = {'ok': True, 'appended': appended, 'row': out, 'also_runs_on': json.loads(STORE.plan_row(plan, api.manager).also_runs_on_json or '[]')}
