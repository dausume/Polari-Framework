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

scr-5 (assertions + policy accountability):
  GET  /api/scoring/policies/{name}/score?concept=…   assertion-
                                          weighted policy score
  GET  /api/scoring/assertions[?subject=…]            list
  GET  /api/scoring/assertions/{name}/suggestions     abstraction
                                          matching (suggestions only)
  GET  /api/scoring/assertions/{name}/validity        vote tally +
                                          suggested transition
  POST /api/scoring/assertions/{name}/transition      lifecycle move
                                          {to, by, note} — validated,
                                          history-appended
  GET  /api/scoring/concepts/{name}/specificity       conformance
                                          findings
  GET  /api/scoring/concepts/{name}/critical-contexts variance-scan
                                          suggestions
  GET  /api/scoring/contributors/{name}/record        track record

scr-6 (politicians + votes):
  GET  /api/scoring/politicians/{name}/score?concept=…[&timeframe=…]
                                          vote-weighted concept score
  GET  /api/scoring/cohorts/{name}/report?concept=…   cohort scores +
                                          per-policy vote cohesion
  POST /api/scoring/ingest-votes          any class (api-profiler
                                          output) → PolicyVote rows;
                                          create knobs never default
                                          on

scr-15 (media accuracy):
  GET  /api/scoring/claims/{name}/check     one claim vs the data
                                          (banded relative error;
                                          'unverifiable' honest)
  GET  /api/scoring/outlets/{name}/accuracy outlet accuracy record

scr-8 (worldview elections):
  GET  /api/scoring/elections/{name}/tally   mode-specific counts,
                                          winners, derived weights,
                                          refused ballots by name
  POST /api/scoring/elections/{name}/apply   CLOSED election →
                                          vote-derived member weights
                                          on its group (provenance-
                                          stamped; open = refusal)

Pure reads (plus the two explicit POSTs) — score definitions are
edited through standard CRUDE on ScoreTerm / ScoreContext /
ScoreSubject / ContextualizedValue / ScoreConcept / ScoreAssertion /
MediaEvidence / Contributor rows (object-coherence: the score IS its
objects).

@consumers
  - scoring-home frontend component
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.abstraction import suggest_scores_for_assertion
from scoring.assertions import tally_validity, transition_assertion
from scoring.contributors import contributor_record
from scoring.data_ingestion import ingest_from_class, ingest_records
from scoring.group_aggregation import (
    aggregate_group, all_groups_consensus, compare_groups,
)
from scoring.media_accuracy import check_claim, outlet_accuracy
from scoring.policy_scoring import score_policy
from scoring.policy_votes import ingest_votes_from_class
from scoring.politician_scoring import cohort_report, politician_score
from scoring.scoring_engine import score_concept
from scoring.specificity import (
    check_concept_specificity, suggest_critical_contexts,
)
from scoring.worldview_elections import apply_election, tally_election


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
            polServer.falconServer.add_route(
                '/api/scoring/groups/consensus', self,
                suffix='consensus')
            polServer.falconServer.add_route(
                '/api/scoring/groups/compare', self, suffix='compare')
            polServer.falconServer.add_route(
                '/api/scoring/groups/{name}/aggregate', self,
                suffix='aggregate')
            polServer.falconServer.add_route(
                '/api/scoring/policies/{name}/score', self,
                suffix='policy_score')
            polServer.falconServer.add_route(
                '/api/scoring/assertions', self, suffix='assertions')
            polServer.falconServer.add_route(
                '/api/scoring/assertions/{name}/suggestions', self,
                suffix='suggestions')
            polServer.falconServer.add_route(
                '/api/scoring/assertions/{name}/validity', self,
                suffix='validity')
            polServer.falconServer.add_route(
                '/api/scoring/assertions/{name}/transition', self,
                suffix='transition')
            polServer.falconServer.add_route(
                '/api/scoring/concepts/{name}/specificity', self,
                suffix='specificity')
            polServer.falconServer.add_route(
                '/api/scoring/concepts/{name}/critical-contexts',
                self, suffix='critical_contexts')
            polServer.falconServer.add_route(
                '/api/scoring/contributors/{name}/record', self,
                suffix='contributor_record')
            polServer.falconServer.add_route(
                '/api/scoring/politicians/{name}/score', self,
                suffix='politician_score')
            polServer.falconServer.add_route(
                '/api/scoring/cohorts/{name}/report', self,
                suffix='cohort_report')
            polServer.falconServer.add_route(
                '/api/scoring/ingest-votes', self,
                suffix='ingest_votes')
            polServer.falconServer.add_route(
                '/api/scoring/claims/{name}/check', self,
                suffix='claim_check')
            polServer.falconServer.add_route(
                '/api/scoring/outlets/{name}/accuracy', self,
                suffix='outlet_accuracy')
            polServer.falconServer.add_route(
                '/api/scoring/elections/{name}/tally', self,
                suffix='election_tally')
            polServer.falconServer.add_route(
                '/api/scoring/elections/{name}/apply', self,
                suffix='election_apply')

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

    def on_get_policy_score(self, request, response, name):
        concept = request.get_param('concept') or ''
        if not concept:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "query param 'concept' is "
                                       'required'}
            return
        statuses = tuple((request.get_param('statuses')
                          or 'confirmed').split(','))
        report = score_policy(
            self.manager, name, concept, include_statuses=statuses,
            evidence_policy=request.get_param('evidencePolicy') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_assertions(self, request, response):
        subject = request.get_param('subject') or ''
        table = (self.manager.objectTables or {}).get(
            'ScoreAssertion', {})
        rows = table.values() if isinstance(table, dict) else table
        out = []
        for row in rows:
            if subject and getattr(row, 'subject_name', '') != subject:
                continue
            def loads(attr, fallback='null'):
                try:
                    return json.loads(
                        getattr(row, attr, '') or fallback)
                except Exception:
                    return None
            out.append({
                'name': getattr(row, 'name', ''),
                'displayName': getattr(row, 'display_name', ''),
                'subject': getattr(row, 'subject_name', ''),
                'span': loads('span_json'),
                'intent': getattr(row, 'intent', ''),
                'type': getattr(row, 'assertion_type', ''),
                'direction': getattr(row, 'direction', ''),
                'strength': getattr(row, 'strength', None),
                'conceptName': getattr(row, 'concept_name', ''),
                'termName': getattr(row, 'term_name', ''),
                'dependsOn': getattr(row, 'depends_on_subject', ''),
                'evidence': loads('evidence_names_json', '[]'),
                'assertedBy': getattr(row, 'asserted_by', ''),
                'status': getattr(row, 'status', ''),
                'statusHistory': loads('status_history_json', '[]'),
            })
        response.media = {'ok': True, 'assertions': out}

    def on_get_suggestions(self, request, response, name):
        report = suggest_scores_for_assertion(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_validity(self, request, response, name):
        report = tally_validity(
            self.manager, name, request.get_param('policy') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_transition(self, request, response, name):
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        result = transition_assertion(
            self.manager, name, payload.get('to', ''),
            by=payload.get('by', ''), note=payload.get('note', ''))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_specificity(self, request, response, name):
        report = check_concept_specificity(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_critical_contexts(self, request, response, name):
        report = suggest_critical_contexts(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_contributor_record(self, request, response, name):
        report = contributor_record(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_politician_score(self, request, response, name):
        concept = request.get_param('concept') or ''
        if not concept:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "query param 'concept' is "
                                       'required'}
            return
        report = politician_score(
            self.manager, name, concept,
            timeframe_context=request.get_param('timeframe') or '',
            evidence_policy=request.get_param('evidencePolicy') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_cohort_report(self, request, response, name):
        concept = request.get_param('concept') or ''
        if not concept:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "query param 'concept' is "
                                       'required'}
            return
        report = cohort_report(
            self.manager, name, concept,
            policy_name=request.get_param('policy') or '',
            timeframe_context=request.get_param('timeframe') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_claim_check(self, request, response, name):
        report = check_claim(
            self.manager, name, request.get_param('policy') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_outlet_accuracy(self, request, response, name):
        report = outlet_accuracy(
            self.manager, name, request.get_param('policy') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_election_tally(self, request, response, name):
        report = tally_election(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_election_apply(self, request, response, name):
        result = apply_election(self.manager, name)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_ingest_votes(self, request, response):
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        result = ingest_votes_from_class(self.manager, payload)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_aggregate(self, request, response, name):
        report = aggregate_group(
            self.manager, name, request.get_param('policy') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_consensus(self, request, response):
        report = all_groups_consensus(
            self.manager, request.get_param('policy') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_compare(self, request, response):
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        report = compare_groups(
            self.manager, payload.get('names', []),
            payload.get('policy', ''))
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report
