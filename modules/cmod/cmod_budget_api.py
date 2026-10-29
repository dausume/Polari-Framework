"""
@module cmod.cmod_budget_api

ipb-1/2 doors (INTERRUPT_POLL_BUDGET_PLAN.md): the polling + interrupt budget, two columns per hart (PC). Derived now, nothing stored.

GET  /api/missions/{name}/budget[?system=S][&variant=V][&view=harts|polls|interrupts|threads|derived|checks|links|suggestions]
        PLANNING: the budget of the Mission's Task Plan (solve=now cached; the plan's edits applied). `variant` = the cycle record to take numbers from
        (default: the Mission's own, e.g. uno-light; -1 everywhere when none). Without `view`: the whole system budget. With: {ok, view, count, rows[]}.
GET  /api/benches/{bench}/budget[?view=boards|harts|polls|interrupts|threads|derived|checks|links|suggestions]
        ANALYSING: the budget of the REAL boards on a bench - a board with a Mission gets that Mission's plan budget, any other its hart facts + empty columns.
POST /api/missions/{name}/budget/knobs | /api/benches/{bench}/budget/knobs   body {scan_deadline_ms?, harts?, poll_divider?: {atom: n}, expected_rate_hz?: {vector: hz}, hart_of?: {task: i}}
        -> 200 {ok, knobs}. PER PROCESS, not persisted (said in the rows' basis).
GET  /api/hart-facts?view=controllers|harts      ipb-0: the cited controller rows (RISC-V names canonical) and the per-processor hart facts.
404 unknown Mission / bench; 422 unknown view.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from board.custom import interrupt_controllers as IC
from cmod.custom import budget as BG
from cmod.custom import budget_suggest as SG


def _body(request):
    try:
        return json.loads(request.bounded_stream.read() or b'{}')
    except Exception:  # noqa: BLE001
        return {}


def _fail(response, status, text):
    response.status = status
    response.media = {'ok': False, 'error': text}


def _view(response, sb, view):
    if not view:
        response.media = sb
        return
    if view == 'suggestions':
        rows = SG.suggestions(sb)
    elif view in BG.VIEWS:
        rows = BG.VIEWS[view](sb)
    else:
        return _fail(response, falcon.HTTP_422, 'unknown view %r (one of %s)' % (view, ', '.join(list(BG.VIEWS) + ['suggestions'])))
    response.media = {'ok': True, 'view': view, 'count': len(rows), 'rows': rows}


class BudgetAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/missions/{name}/budget', self, suffix='mission')
            add('/api/missions/{name}/budget/knobs', self, suffix='mission_knobs')
            add('/api/benches/{bench}/budget', self, suffix='bench')
            add('/api/benches/{bench}/budget/knobs', self, suffix='bench_knobs')
            add('/api/hart-facts', self, suffix='facts')

    def on_get_mission(self, request, response, name):
        from cmod.custom import task_plan as TP
        system = request.get_param('system') or ''
        variant = request.get_param('variant')
        try:
            plan = BG._plan_for(name, system, self.manager)
        except ValueError as e:
            return _fail(response, falcon.HTTP_404, str(e))
        except KeyError as e:
            return _fail(response, falcon.HTTP_422, e.args[0] if e.args else str(e))
        sb = BG.system_budget(plan, variant if variant is not None else BG.default_variant(name), BG.knobs_for('mission', name))
        _view(response, sb, request.get_param('view') or '')

    def on_post_mission_knobs(self, request, response, name):
        try:   # ipb-8: an affinity / reason word outside the vocabulary is refused with words
            response.media = {'ok': True, 'mission': name, 'knobs': BG.set_knobs('mission', name, _body(request)), 'basis': 'per process, not persisted'}
        except ValueError as e:
            return _fail(response, falcon.HTTP_422, str(e))

    def on_get_bench(self, request, response, bench):
        sb = BG.bench_budget(bench, self.manager, BG.knobs_for('bench', bench))
        if sb is None:
            return _fail(response, falcon.HTTP_404, 'no bench %r' % bench)
        _view(response, sb, request.get_param('view') or '')

    def on_post_bench_knobs(self, request, response, bench):
        try:
            response.media = {'ok': True, 'bench': bench, 'knobs': BG.set_knobs('bench', bench, _body(request)), 'basis': 'per process, not persisted'}
        except ValueError as e:
            return _fail(response, falcon.HTTP_422, str(e))

    def on_get_facts(self, request, response):
        from board.custom import parallelism as PX
        view = request.get_param('view') or 'harts'
        if view == 'controllers':
            rows = IC.controller_rows()
        elif view == 'harts':
            rows = IC.hart_rows()
        elif view == 'parallelism':          # ipb-6: per-processor pipeline / issue / hw threads / vector / lockstep facts
            rows = PX.hart_rows()
        elif view == 'parallelism-kinds':    # ipb-6: the kinds, cited to the RISC-V book's sections
            rows = PX.kind_rows()
        elif view == 'tiers':                # ipb-8: the scheduler ladder bare-c -> freertos -> freertos-smp -> zephyr, cited
            rows = PX.tier_rows()
        else:
            return _fail(response, falcon.HTTP_422, 'view must be controllers, harts, parallelism, parallelism-kinds or tiers')
        response.media = {'ok': True, 'view': view, 'count': len(rows), 'rows': rows, 'uncited': IC.uncited_numbers() + PX.uncited_numbers()}
