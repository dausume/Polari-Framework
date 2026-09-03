"""
@cross-cutting
@module nutrition.shoptrip_api
@tags @xc:bindings

N3 — the shopping-trip page's routes:

  GET  /api/mealplanning/shoptrip/checklist?plan=&location=&event=&household=
       the purchase lines in the store's aisle order (trip_checklist)
  POST /api/mealplanning/shoptrip/bought
       {food, location, price, package_quantity, package_unit, date,
        household?, storage_state?} → runs the seeded
       mealplan-shoptrip-bought solution through the engine (the SAME
       write path the page form uses): PriceObservation + PantryItem
       lot, deduped by name. Returns the proposal + what was written.

@consumers
  - polariServer (route registration, gated on nutrition)
  - the /display/mealplan/shoptrip page
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.shoptrip_analysis import (
    record_purchase_proposal, trip_checklist,
)

_SOLUTION = 'mealplan-shoptrip-bought'


class ShoptripAPI(treeObject):
    """The shopping-trip page's read + write routes."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/mealplanning/shoptrip'
        if polServer is not None:
            try:
                add = polServer.falconServer.add_route
                add('/api/mealplanning/shoptrip/checklist', self,
                    suffix='checklist')
                add('/api/mealplanning/shoptrip/bought', self,
                    suffix='bought')
            except Exception as exc:  # never break boot
                print(f'[ShoptripAPI] route registration failed: {exc}',
                      flush=True)

    def on_get_checklist(self, request, response):
        p = request.params
        kwargs = {'plan': p.get('plan') or None,
                  'location': p.get('location') or None,
                  'event': p.get('event') or None,
                  'household': p.get('household') or ''}
        if p.get('bought_window_days'):
            try:
                kwargs['bought_window_days'] = int(p['bought_window_days'])
            except ValueError:
                pass
        response.media = trip_checklist(self.manager, **{k: v for k, v in kwargs.items()
                                                         if v is not None})

    def on_post_bought(self, request, response):
        try:
            body = request.get_media() or {}
        except Exception:
            body = {}
        fields = {k: body.get(k) for k in ('food', 'location', 'price', 'package_quantity',
                                            'package_unit', 'date', 'household',
                                            'storage_state')}
        proposal = record_purchase_proposal(self.manager, **{k: v for k, v in fields.items()
                                                             if v is not None})
        if not proposal.get('ok'):
            response.media = proposal
            return
        response.media = {**proposal, **self._run_solution(fields)}

    # -- the write path: the seeded solution through the engine --------
    def _solution_definition(self):
        tables = getattr(self.manager, 'objectTables', {}) or {}
        for row in (tables.get('SolutionDefinition', {}) or {}).values():
            if getattr(row, 'name', '') == _SOLUTION:
                try:
                    return json.loads(getattr(row, 'definition', '') or '')
                except ValueError:
                    return None
        return None

    def _run_solution(self, fields):
        from polariNoCode import graph_builder as gb
        from polariNoCode.graph_compilers import final_context_of
        definition = self._solution_definition()
        if definition is None:
            return {'written': [], 'writeStatus': f"solution '{_SOLUTION}' is not seeded on "
                                                  "this node — nothing written"}
        params = {k: ('' if v is None else v) for k, v in fields.items()}
        params.setdefault('household', 'demo-household')
        try:
            trace = gb.execute(definition, manager=self.manager, params=params)
        except Exception as exc:
            return {'written': [], 'writeStatus': f'engine error: {type(exc).__name__}: {exc}'}
        ctx = final_context_of(trace) or {}
        written = [dict(s) for s in ctx.get('_generated_events', []) or []]
        return {'written': written, 'writeStatus': str(getattr(trace, 'status', '')),
                'writeError': getattr(trace, 'error_summary', '') or ''}
