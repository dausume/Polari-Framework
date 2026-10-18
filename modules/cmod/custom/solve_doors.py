"""
@module cmod.custom.solve_doors

The attempt engine's doors (sol-0), plain functions over a SolveAPI (`cmod_solve_api` registers the routes and delegates here). Advised, never blocking.

POST /api/missions/{name}/solve        body {boards?: [..]|"a,b", tiers?: [..], objective?: minimum-resources|fastest-cycle, limits?: {...}, store?: true}
                                       Runs the search and (store, the default) records a SolveRun row. -> {ok, stored, run{name, result_sha256, ...}, objective, counts, chosen, score_card[],
                                       trade_study[], assignment[], pruned{}, designed_for, also_runs_on[], does_not_run_on[], package_difference[], inputs{}, duration_s}
                                       404 unknown Mission; 422 an unknown board / tier / objective / limit (naming what is known).
GET  /api/missions/{name}/solve        the same search computed NOW, nothing stored (cached by its inputs): ?board=&tier=&objective=&prefer=&occupy=D6,D7&only_jobs=a,b
                                       &view=score-card|trade-study|assignment|pruned|designed-for returns the flat plain-words rows {ok, view, count, rows[]} for the page tables
GET  /api/missions/{name}/solve-runs   the recorded runs {ok, count, rows[]} (newest last)
GET  /api/missions/{name}/solve-runs/{run}   one run in full; ?replay=1 runs it again and says whether the result is identical
"""
import json

import falcon

from cmod.custom import solve as S
from cmod.custom import solve_record as REC
from cmod.custom import solve_report as R
from cmod.custom import solve_inputs as SI

_CACHE = {}


def _body(request):
    try:
        return json.loads(request.bounded_stream.read() or b'{}')
    except Exception:  # noqa: BLE001
        return {}


def _list(x):
    if isinstance(x, str):
        return [i.strip() for i in x.split(',') if i.strip()]
    return list(x) if x else None


def _who(request):
    ui = getattr(getattr(request, 'context', None), 'user_info', None) or {}
    return ui.get('preferred_username') or ui.get('sub') or ''


def compute(name, boards, tiers, objective, limits, manager):
    """The search, cached by (Mission row, knobs) so the page's five tables share one run. -> the result (internal handles kept)."""
    row = SI.mission_row(name, manager)
    key = SI.sha([row, boards, tiers, objective, limits])
    if key not in _CACHE:
        if len(_CACHE) > 6:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = S.solve(name, boards=boards, tiers=tiers, objective=objective, limits=limits, manager=manager)
    return _CACHE[key]


def _fail(response, status, text):
    response.status = status
    response.media = {'ok': False, 'error': text}


def _run_summary(res):
    out = {k: res[k] for k in ('mission', 'objective', 'secondary_objective', 'counts', 'chosen', 'result_sha256', 'duration_s', 'solver_version')}
    out['chosen_text'] = R.label(res['chosen_candidate']) if res['chosen_candidate'] else ''
    return out


#: the POST body's keys; anything else is REFUSED by name (a misplaced key was once silently ignored: `prefer` at the top level ran the default search)
POST_KEYS = ('boards', 'tiers', 'objective', 'limits', 'store', 'prefer', 'occupy', 'only_jobs')


def post_solve(api, request, response, name):
    body = _body(request)
    unknown = sorted(k for k in body if k not in POST_KEYS)
    if unknown:
        return _fail(response, falcon.HTTP_422, 'unknown key(s) %s in the solve body (known: %s; prefer / occupy / only_jobs may sit at the top level or inside limits)'
                     % (', '.join(unknown), ', '.join(POST_KEYS)))
    lim = dict(body.get('limits') or {})
    if body.get('prefer'):   # the same short forms the GET door takes, accepted at the top level too
        lim['prefer'] = body['prefer']
    if body.get('occupy'):
        lim['occupied'] = [{'pin': x, 'by': 'the request', 'why': 'occupied on request (occupy)', 'blocks': 'all'} for x in _list(body['occupy'])]
    if body.get('only_jobs'):
        lim['only_jobs'] = _list(body['only_jobs'])
    try:
        res = compute(name, _list(body.get('boards')), _list(body.get('tiers')), body.get('objective') or None, lim, api.manager)
    except ValueError as e:
        return _fail(response, falcon.HTTP_404, str(e))
    except KeyError as e:
        return _fail(response, falcon.HTTP_422, e.args[0] if e.args else str(e))
    row = REC.store(api.manager, res, _who(request)) if (api.manager is not None and body.get('store', True)) else None
    pub = S.public(res)
    response.status = falcon.HTTP_201 if row is not None else falcon.HTTP_200
    response.media = dict({k: pub[k] for k in ('mission', 'objective', 'secondary_objective', 'counts', 'chosen', 'score_card', 'trade_study', 'assignment', 'pruned', 'designed_for', 'also_runs_on',
                                               'does_not_run_on', 'package_difference', 'reference_wiring', 'inputs', 'duration_s', 'result_sha256', 'notes', 'hardware')},
                          ok=True, stored=row is not None, run=REC.as_dict(row) if row is not None else _run_summary(res))


def get_solve(api, request, response, name):
    p = request.params
    lim = {}
    if p.get('prefer'):
        lim['prefer'] = p['prefer']
    if p.get('occupy'):
        lim['occupied'] = [{'pin': x, 'by': 'the request', 'why': 'occupied on request (?occupy=)', 'blocks': 'all'} for x in _list(p['occupy'])]
    if p.get('only_jobs'):
        lim['only_jobs'] = _list(p['only_jobs'])
    view = p.get('view') or ''
    if view and view not in R.VIEWS:
        return _fail(response, falcon.HTTP_422, 'no view %r (one of %s)' % (view, ', '.join(R.VIEWS)))
    try:
        res = compute(name, _list(p.get('board')), _list(p.get('tier')), p.get('objective') or None, lim, api.manager)
    except ValueError as e:
        return _fail(response, falcon.HTTP_404, str(e))
    except KeyError as e:
        return _fail(response, falcon.HTTP_422, e.args[0] if e.args else str(e))
    if view:
        rows = R.view_rows(res, view)
        response.media = {'ok': True, 'view': view, 'mission': res['mission'], 'objective': res['objective'], 'count': len(rows), 'rows': rows}
        return
    pub = S.public(res)
    pub.pop('candidates', None)
    response.media = dict(pub, ok=True, stored=False)


def get_runs(api, request, response, name):
    try:
        SI.mission_row(name, api.manager)
    except ValueError as e:
        return _fail(response, falcon.HTTP_404, str(e))
    rows = [REC.as_dict(r) for r in REC.rows(api.manager, name)]
    response.media = {'ok': True, 'mission': name, 'count': len(rows), 'rows': rows}


def get_run(api, request, response, name, run):
    row = next((r for r in REC.rows(api.manager, name) if r.name == run), None)
    if row is None:
        return _fail(response, falcon.HTTP_404, 'no run %r of Mission %r (GET /api/missions/%s/solve-runs lists them)' % (run, name, name))
    out = REC.as_dict(row, full=True)
    if request.params.get('replay'):
        out['replay'] = REC.replay(row, api.manager)
    response.media = dict(out, ok=True)
