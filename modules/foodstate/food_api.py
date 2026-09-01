"""
@module foodstate.food_api

fsp-0 read surface:
  GET /api/foodstate/contracts   — the five domain contracts + the
                                   honesty ladder + the boundary
  GET /api/foodstate/vocabulary  — food stages / processes / added
                                   evidence methods AS SEEDED (rows
                                   live in the pspp classes)
  GET /api/foodstate/ingredients        — the base-ingredient roster
                                          + per-ingredient coverage
  GET /api/foodstate/ingredients/{slug} — one ingredient's identity
                                          + its FDC-cited claims +
                                          NAMED contract gaps

Transform execution deliberately ABSENT until fsp-2 — the vocabulary
rows say so themselves.

@consumers
  - polariServer (route registration, gated on feature presence)
  - foodstate.selftest_foodstate (function level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from foodstate.food_composition import ingredient_report
from foodstate.food_contracts import contracts_report


def vocabulary_report(manager):
    tables = getattr(manager, 'objectTables', None) or {}

    def rows(cls, keep):
        out = []
        for row in (tables.get(cls) or {}).values():
            if keep(row):
                out.append(row)
        return out

    stages = [{'name': getattr(r, 'name', ''),
               'displayName': getattr(r, 'display_name', ''),
               'typicalPriorStage': getattr(r, 'typical_prior_stage',
                                            ''),
               'description': getattr(r, 'description', '')}
              for r in sorted(
                  rows('ProcessingStage',
                       lambda r: getattr(r, 'material_family', '')
                       == 'food'),
                  key=lambda r: getattr(r, 'name', ''))]
    procs = [{'name': getattr(r, 'name', ''),
              'displayName': getattr(r, 'display_name', ''),
              'processType': getattr(r, 'process_type', ''),
              'executionEffect': getattr(r, 'execution_effect', ''),
              'parameters': json.loads(
                  getattr(r, 'parameter_schema_json', '{}') or '{}'),
              'outputSchema': json.loads(
                  getattr(r, 'output_state_schema_json', '{}')
                  or '{}'),
              'notes': getattr(r, 'notes', '')}
             for r in sorted(
                 rows('MaterialProcessDefinition',
                      lambda r: getattr(r, 'material_family', '')
                      == 'food'),
                 key=lambda r: getattr(r, 'name', ''))]
    methods = [{'name': getattr(r, 'name', ''),
                'category': getattr(r, 'category', ''),
                'requiredProvenance': getattr(
                    r, 'required_provenance', '')}
               for r in rows('EvidenceMethod',
                             lambda r: getattr(r, 'name', '') in
                             ('mass-balance', 'retention-factor',
                              'conditional-prediction'))]
    return {'ok': True, 'schema': 'food-vocabulary/1',
            'stages': stages, 'processes': procs,
            'addedEvidenceMethods': methods,
            'substrate': ('rows in the pspp core classes '
                          '(ProcessingStage / '
                          'MaterialProcessDefinition / '
                          'EvidenceMethod) — the zero-schema-change '
                          'generality proof'),
            'execution': ('transform engines arrive in fsp-2 behind '
                          'I5 interfaces — running a food process '
                          'today REFUSES rather than inventing '
                          'numbers')}


class FoodStateAPI(treeObject):
    """The fsp-0 read surface."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/foodstate'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/foodstate/contracts', self, suffix='contracts')
            add('/api/foodstate/vocabulary', self,
                suffix='vocabulary')
            add('/api/foodstate/ingredients', self,
                suffix='ingredients')
            add('/api/foodstate/ingredients/{slug}', self,
                suffix='ingredient')

    def on_get_contracts(self, request, response):
        response.media = contracts_report(self.manager)

    def on_get_vocabulary(self, request, response):
        response.media = vocabulary_report(self.manager)

    def on_get_ingredients(self, request, response):
        response.media = ingredient_report(self.manager)

    def on_get_ingredient(self, request, response, slug):
        report = ingredient_report(self.manager, slug=slug)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
