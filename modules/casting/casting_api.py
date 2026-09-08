"""
@cross-cutting
@module casting.casting_api
@tags @xc:bindings

HTTP surface for the casting module — the wizard front door:

  GET  /api/casting/capability          what this node can plan with
                                        (parts, targets, feedstocks).
  POST /api/casting/plan                {"partShape": ..,
                                        "targetMaterial": ..,
                                        "feedstock"?: ..} → the full
                                        nesting plan, every step with
                                        its verdict + viewable shapes.
  GET  /api/casting/plans               derived plans (summary).
  GET  /api/casting/chains/{name}/report  the composed chain report.

Rows are edited through CRUDE (object-coherence); the wizard only
derives.

@consumers the /casting page; Dustin's picker UI (his revision pass)
"""

import json

from casting.coatings_basis import chain_full_report
from casting.nesting_wizard_basis import plan_nesting
from casting.custom.wax_feasibility import _rows
from objectTreeDecorators import treeObject, treeObjectInit


class CastingAPI(treeObject):
    """casting endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/casting'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/casting/capability', self, suffix='capability')
            polServer.falconServer.add_route(
                '/api/casting/plan', self, suffix='plan')
            polServer.falconServer.add_route(
                '/api/casting/plans', self, suffix='plans')
            polServer.falconServer.add_route(
                '/api/casting/chains/{name}/report', self,
                suffix='chainreport')

    def on_get_capability(self, request, response):
        shapes = [getattr(s, 'name', '') for s in
                  _rows(self.manager, 'MathShapeDefinition')
                  if getattr(s, 'family', '') in
                  ('primitive', 'quadric', 'csg', 'imported-mesh')]
        response.media = {
            'ok': True,
            'parts': sorted(shapes)[:200],
            'targets': {
                'geopolymer': ['geopolymer'],
                'ceramics': sorted(getattr(r, 'name', '') for r in
                                   _rows(self.manager,
                                         'CeramicSample')),
                'metals': sorted(getattr(r, 'name', '') for r in
                                 _rows(self.manager,
                                       'CastingMaterialThermal'
                                       'Profile')),
                'galvanized': sorted(
                    __import__('casting.nesting_wizard_basis',
                               fromlist=['GALVANIZE_TARGETS']
                               ).GALVANIZE_TARGETS)},
            'feedstocks': sorted(getattr(r, 'name', '') for r in
                                 _rows(self.manager,
                                       'MasterFeedstockDefinition')),
            'note': 'POST /api/casting/plan {partShape, '
                    'targetMaterial, feedstock?} runs the whole '
                    'pipeline; every step returns viewable shapes.'}

    def on_post_plan(self, request, response):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except (TypeError, ValueError):
            body = {}
        part = body.get('partShape', '')
        target = body.get('targetMaterial', '')
        if not part or not target:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'partShape and '
                                       'targetMaterial required'}
            return
        result = plan_nesting(self.manager, part, target,
                              feedstock_name=body.get('feedstock')
                              or None)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_plans(self, request, response):
        plans = []
        for p in _rows(self.manager, 'NestingPlanDefinition'):
            plans.append({'name': getattr(p, 'name', ''),
                          'part': getattr(p, 'part_shape_ref', ''),
                          'target': getattr(p, 'target_material',
                                            ''),
                          'verdict': getattr(p, 'verdict', ''),
                          'chain': getattr(p, 'chain_ref', '')})
        response.media = {'ok': True, 'count': len(plans),
                          'plans': plans}

    def on_get_chainreport(self, request, response, name):
        result = chain_full_report(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result
