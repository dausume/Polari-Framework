"""
@module cmod.custom.solve_record

sol-0: the RECORD of a run - a `SolveRun` row per run (inputs by sha256, objective, limits, a summary of every candidate, the chosen one in full, the pruned log, the duration)
and the REPLAY: run the same inputs again and the candidates, their order and the chosen plan must come out identical (`result_sha256`). The pure `solve()` stores nothing; a
door (POST /api/missions/{name}/solve) calls `store()`.
"""
import datetime
import json

from cmod.custom import solve_inputs as SI


def _j(x):
    return json.dumps(x, sort_keys=True, default=str)


def fields(res, who='', ran_at=None):
    chosen = res['chosen_candidate']
    seq = 1
    return {'mission': res['mission'], 'objective': res['objective'], 'secondary_objective': res['secondary_objective'], 'inputs_json': _j(res['inputs']), 'inputs_sha256': SI.sha(res['inputs']),
            'limits_json': _j(res['limits']), 'boards_json': _j(res['boards_asked'] or []), 'tiers_json': _j(res['tiers_asked'] or []), 'candidates_json': _j(res['summary'][:400]),
            'candidate_count': res['counts']['candidates'], 'chosen': chosen['id'] if chosen else '', 'chosen_json': _j(chosen) if chosen else '{}',
            'designed_for_json': _j({'designed_for': res['designed_for'], 'also_runs_on': res['also_runs_on'], 'does_not_run_on': res['does_not_run_on']}),
            'pruned_json': _j(res['pruned']), 'counts_json': _j(res['counts']), 'result_sha256': res['result_sha256'], 'solver_version': res['solver_version'],
            'duration_s': res['duration_s'], 'ran_at': ran_at or datetime.datetime.now().isoformat(timespec='seconds'), 'who': who, 'status': 'complete', 'notes': ''}


def rows(manager, mission=None):
    return sorted([r for r in ((getattr(manager, 'objectTables', None) or {}).get('SolveRun') or {}).values() if mission in (None, r.name.partition(':')[0])], key=lambda r: r.ran_at + r.name)


def store(manager, res, who=''):
    from cmod.cmod_basis import SolveRun
    f = fields(res, who)
    n = len(rows(manager, res['mission'])) + 1
    name = '%s:%s:%d' % (res['mission'], res['result_sha256'][:10], n)
    row = SolveRun(manager=manager, name=name, **f)
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        try:
            db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001 - a save failure is logged by the DB layer; the row stays in the tree
            pass
    return row


def as_dict(row, full=False):
    keys = ('name', 'mission', 'objective', 'secondary_objective', 'inputs_sha256', 'candidate_count', 'chosen', 'result_sha256', 'solver_version', 'duration_s', 'ran_at', 'who', 'status')
    d = {k: getattr(row, k, '') for k in keys}
    d['chosen_text'] = (json.loads(row.chosen_json or '{}').get('routes_text') or '') if row.chosen else ''
    d['counts'] = json.loads(row.counts_json or '{}')
    if full:
        for k in ('inputs_json', 'limits_json', 'boards_json', 'tiers_json', 'candidates_json', 'chosen_json', 'designed_for_json', 'pruned_json'):
            d[k[:-5]] = json.loads(getattr(row, k, '') or 'null')
    return d


def replay(row, manager=None, solver=None):
    """Re-run a recorded run from its recorded knobs. -> {same_result, same_inputs, result_sha256, recorded_sha256, differs}."""
    from cmod.custom import solve as S
    lim = json.loads(row.limits_json or '{}')
    res = (solver or S.solve)(row.mission, boards=json.loads(row.boards_json or '[]') or None, tiers=json.loads(row.tiers_json or '[]') or None, objective=row.objective, limits=lim, manager=manager)
    return {'same_result': res['result_sha256'] == row.result_sha256, 'same_inputs': SI.sha(res['inputs']) == row.inputs_sha256, 'result_sha256': res['result_sha256'], 'recorded_sha256': row.result_sha256,
            'differs': [] if res['result_sha256'] == row.result_sha256 else ['the candidates, their order or the pruned log changed - the inputs hash %s' % ('is the same: the code changed' if SI.sha(res['inputs']) == row.inputs_sha256 else 'also changed: an input changed')]}
