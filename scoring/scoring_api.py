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
                                          breakdowns (nested concepts
                                          included), absences named
  POST /api/scoring/ingest                real data-series ingestion:
                                          explicit records, or ANY
                                          object class via a field
                                          mapping; honesty knobs
                                          (create_missing_subjects /
                                          overwrite) never default on

Pure reads — score definitions are edited through standard CRUDE on
ScoreTerm / ScoreContext / ScoreSubject / ContextualizedValue /
ScoreConcept rows (object-coherence: the score IS its objects).

@consumers
  - scoring-home frontend component
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.data_ingestion import ingest_from_class, ingest_records
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
            polServer.falconServer.add_route(
                '/api/scoring/ingest', self, suffix='ingest')

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

    def on_post_ingest(self, request, response):
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        if payload.get('source_class'):
            result = ingest_from_class(self.manager, payload)
        else:
            result = ingest_records(self.manager, payload)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result
