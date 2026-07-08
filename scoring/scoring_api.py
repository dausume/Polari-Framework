"""
@cross-cutting
@module scoring.scoring_api
@tags @xc:bindings

HTTP surface for context-based scoring (PeersAPI pattern —
self-registering falcon routes):

  GET /api/scoring/concepts               every ScoreConcept, summary
                                          form (terms, weights,
                                          subjects, contexts)
  GET /api/scoring/concepts/{name}/score  the full pipeline: ranked
                                          subjects w/ per-term
                                          breakdowns, absences named

Pure reads — score definitions are edited through standard CRUDE on
ScoreTerm / ScoreContext / ScoreSubject / ContextualizedValue /
ScoreConcept rows (object-coherence: the score IS its objects).

@consumers
  - scoring-home frontend component
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.scoring_engine import score_concept


class ScoringAPI(treeObject):
    """Context-based scoring endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/scoring'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/scoring/concepts', self, suffix='concepts')
            polServer.falconServer.add_route(
                '/api/scoring/concepts/{name}/score', self,
                suffix='score')

    def on_get_concepts(self, request, response):
        table = (self.manager.objectTables or {}).get('ScoreConcept', {})
        rows = table.values() if isinstance(table, dict) else table
        concepts = []
        for row in rows:
            def loads(attr):
                try:
                    return json.loads(getattr(row, attr, '') or '[]')
                except Exception:
                    return []
            concepts.append({
                'name': getattr(row, 'name', ''),
                'displayName': getattr(row, 'display_name', ''),
                'description': getattr(row, 'description', ''),
                'subjectKind': getattr(row, 'subject_kind', ''),
                'termWeights': loads('term_weights_json'),
                'requiredContexts':
                    loads('required_context_names_json'),
                'aggregation': getattr(row, 'aggregation', ''),
                'levelize': bool(getattr(row, 'levelize', True)),
            })
        response.media = {'ok': True, 'concepts': concepts}

    def on_get_score(self, request, response, name):
        report = score_concept(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
