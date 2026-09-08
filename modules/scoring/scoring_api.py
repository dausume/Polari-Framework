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

scr-12a (survival costs):
  GET  /api/scoring/survival/walkthrough  the wizard, generated from
                                          the editable CostCategory
                                          vocabulary
  POST /api/scoring/survival/submit       one household month →
                                          profile + engine-native
                                          values (gaps honest)
  GET  /api/scoring/survival/report?location=…[&month=…]
                                          area stats + subtotals by
                                          kind (pseudo-tax share)

scr-16 (per-group bias):
  GET  /api/scoring/groups/{name}/bias    stance skew vs consensus,
                                          assertion one-sidedness,
                                          vote-alignment read,
                                          source quality

scr-15 (media accuracy):
  GET  /api/scoring/claims/{name}/check     one claim vs the data
                                          (banded relative error;
                                          'unverifiable' honest)
  GET  /api/scoring/outlets/{name}/accuracy outlet accuracy record

scr-8 (worldview elections):
  GET  /api/scoring/elections                every WorldviewElection,
                                          summary form (group, mode,
                                          status, candidates, a live
                                          tally digest when ballots
                                          exist — same shape a browse/
                                          list UI needs, one round trip)
  GET  /api/scoring/elections/{name}/tally   mode-specific counts,
                                          winners, derived weights,
                                          refused ballots by name
  POST /api/scoring/elections/{name}/apply   CLOSED election →
                                          vote-derived member weights
                                          on its group (provenance-
                                          stamped; open = refusal)

Phase 4 (mechanism A — Group Display votes): vote on which Display
best EXPLAINS a score, distinct from scr-8's vote on term-weighting
worldviews. Reuses scr-8's tally engine by import.
  GET  /api/scoring/display-votes             every GroupDisplayVote,
                                          same summary+tally-digest
                                          shape as /elections
  GET  /api/scoring/display-votes/{name}/tally
                                          mode-specific counts,
                                          winners, refused ballots
  GET  /api/scoring/display-votes/{name}/displays
                                          the vote's candidate
                                          DisplayDefinitions resolved +
                                          their text content extracted
                                          (Phase 4b: so a PSC UI can
                                          show what each explanation
                                          actually SAYS, not just tally
                                          numbers) — unknown/missing
                                          candidates named honestly
  POST /api/scoring/display-votes/{name}/apply
                                          CLOSED vote → the elected
                                          Display recorded ON the
                                          vote row (singular winner
                                          required; ties refuse)

Mechanism C (logic-fork criterion votes): vote on which alternate
criterion a SPECIFIC decision point/fork inside a decision procedure
should use — distinct from mechanism A (whole Displays) and mechanism
B (whole worldview concepts). Reuses scr-8's tally engine by import.
  GET  /api/scoring/logic-fork-votes           every LogicForkVote,
                                          same summary+tally-digest
                                          shape as /elections
  GET  /api/scoring/logic-fork-votes/{name}/tally
                                          mode-specific counts,
                                          winners, refused ballots
  POST /api/scoring/logic-fork-votes/{name}/apply
                                          CLOSED vote → the elected
                                          criterion recorded ON the
                                          vote row (singular winner
                                          required; ties refuse) —
                                          does NOT auto-rewrite a live
                                          no-code SolutionDefinition
                                          graph (see logic_fork_vote.py)
  GET  /api/scoring/decision-procedures/{name}/resolved
                                          every known fork in this
                                          procedure + its resolved
                                          criterion (vote-derived if
                                          applied, else the incumbent
                                          default, else honestly
                                          unresolved) — a readable
                                          summary, not an executable
                                          graph rewrite

System-choice implications (2026-07-14): which criterion is actually
deployed where over time, and evidence-weighted claims that a system
choice affects a real-world score. SystemChoiceInForce rows and the
actual claims (plain ScoreAssertion, unchanged) are edited via
standard CRUDE, same as everything else — only the comparison read is
bespoke:
  GET  /api/scoring/system-choices/{fork}/outcomes?term=<name>
                                          groups jurisdictions by
                                          which criterion they
                                          currently deploy at this
                                          fork, reports each's
                                          outcome-term value + a
                                          per-group average — a RAW
                                          comparison, explicitly NOT
                                          a controlled-for-confounds
                                          causal estimate (see
                                          system_choice_implications.py)

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
from scoring.custom.abstraction import suggest_scores_for_assertion
from scoring.assertions_basis import tally_validity, transition_assertion
from scoring.contributors_basis import contributor_record
from scoring.custom.data_ingestion import ingest_from_class, ingest_records
from scoring.custom.group_aggregation import (
    aggregate_group, all_groups_consensus, compare_groups,
)
from scoring.group_bias_basis import group_bias_report
from scoring.media_accuracy_basis import check_claim, outlet_accuracy
from scoring.custom.policy_scoring import score_policy
from scoring.policy_votes_basis import ingest_votes_from_class
from scoring.custom.politician_scoring import cohort_report, politician_score
from scoring.custom.scoring_engine import score_concept
from scoring.custom.specificity import (
    check_concept_specificity, suggest_critical_contexts,
)
from scoring.survival_costs_basis import (
    submit_survival_profile, survival_report, survival_walkthrough,
)
from scoring.group_display_vote_basis import (
    apply_display_vote, tally_display_vote,
)
from scoring.logic_fork_vote_basis import (
    apply_logic_fork_vote, resolved_procedure_summary,
    tally_logic_fork_vote,
)
from scoring.system_choice_implications_basis import (
    compare_outcomes_by_system_choice,
)
from scoring.worldview_elections_basis import apply_election, tally_election


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
                '/api/scoring/groups/{name}/bias', self,
                suffix='group_bias')
            polServer.falconServer.add_route(
                '/api/scoring/survival/walkthrough', self,
                suffix='survival_walkthrough')
            polServer.falconServer.add_route(
                '/api/scoring/survival/submit', self,
                suffix='survival_submit')
            polServer.falconServer.add_route(
                '/api/scoring/survival/report', self,
                suffix='survival_report')
            polServer.falconServer.add_route(
                '/api/scoring/claims/{name}/check', self,
                suffix='claim_check')
            polServer.falconServer.add_route(
                '/api/scoring/outlets/{name}/accuracy', self,
                suffix='outlet_accuracy')
            polServer.falconServer.add_route(
                '/api/scoring/elections', self, suffix='elections')
            polServer.falconServer.add_route(
                '/api/scoring/elections/{name}/tally', self,
                suffix='election_tally')
            polServer.falconServer.add_route(
                '/api/scoring/elections/{name}/apply', self,
                suffix='election_apply')
            polServer.falconServer.add_route(
                '/api/scoring/display-votes', self,
                suffix='display_votes')
            polServer.falconServer.add_route(
                '/api/scoring/display-votes/{name}/tally', self,
                suffix='display_vote_tally')
            polServer.falconServer.add_route(
                '/api/scoring/display-votes/{name}/displays', self,
                suffix='display_vote_displays')
            polServer.falconServer.add_route(
                '/api/scoring/display-votes/{name}/apply', self,
                suffix='display_vote_apply')
            polServer.falconServer.add_route(
                '/api/scoring/logic-fork-votes', self,
                suffix='logic_fork_votes')
            polServer.falconServer.add_route(
                '/api/scoring/logic-fork-votes/{name}/tally', self,
                suffix='logic_fork_vote_tally')
            polServer.falconServer.add_route(
                '/api/scoring/logic-fork-votes/{name}/apply', self,
                suffix='logic_fork_vote_apply')
            polServer.falconServer.add_route(
                '/api/scoring/decision-procedures/{name}/resolved',
                self, suffix='decision_procedure_resolved')
            # ncg-2: cases advanced fork-by-fork through COMPILED
            # no-code graphs (the judicial seam client).
            polServer.falconServer.add_route(
                '/api/scoring/court-cases/create', self,
                suffix='court_case_create')
            polServer.falconServer.add_route(
                '/api/scoring/court-cases/{name}/advance', self,
                suffix='court_case_advance')
            polServer.falconServer.add_route(
                '/api/scoring/court-cases/{name}', self,
                suffix='court_case')
            polServer.falconServer.add_route(
                '/api/scoring/system-choices/{fork}/outcomes',
                self, suffix='system_choice_outcomes')

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

    def on_get_elections(self, request, response):
        table = (self.manager.objectTables or {}
                ).get('WorldviewElection', {})
        rows = table.values() if isinstance(table, dict) else table
        elections = []
        for row in rows:
            name = getattr(row, 'name', '')
            try:
                digest = json.loads(getattr(
                    row, 'candidate_concept_names_json', '') or '[]')
            except Exception:
                digest = []
            tally = tally_election(self.manager, name)
            elections.append({
                'name': name,
                'displayName': getattr(row, 'display_name', '') or name,
                'description': getattr(row, 'description', ''),
                'groupName': getattr(row, 'group_name', ''),
                'mode': getattr(row, 'mode', 'approval'),
                'status': getattr(row, 'status', 'open'),
                'opensDate': getattr(row, 'opens_date', ''),
                'closesDate': getattr(row, 'closes_date', ''),
                'explicitCandidates': digest,
                # A live tally digest so a browse/list UI can show
                # "N ballots, currently leading: X" in one round trip
                # — same tally_election() the dedicated endpoint uses,
                # just summarized; ok:false (no ballots yet, unknown
                # group) is honest, not an error, so it's carried as
                # 'tallyAvailable' rather than raising.
                'tallyAvailable': bool(tally.get('ok')),
                'ballotsCast': tally.get('ballotsCast', 0),
                'winners': tally.get('winners', []),
                'candidates': tally.get('candidates', digest),
            })
        response.media = {'ok': True, 'elections': elections}

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

    def on_get_survival_walkthrough(self, request, response):
        report = survival_walkthrough(self.manager)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_survival_submit(self, request, response):
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        result = submit_survival_profile(self.manager, payload)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_survival_report(self, request, response):
        location = request.get_param('location') or ''
        if not location:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "query param 'location' is "
                                       'required'}
            return
        report = survival_report(
            self.manager, location, request.get_param('month') or '')
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_group_bias(self, request, response, name):
        report = group_bias_report(
            self.manager, name,
            policy_name=request.get_param('policy') or '',
            agreement_policy=request.get_param('agreementPolicy')
            or '')
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

    def on_get_display_votes(self, request, response):
        table = (self.manager.objectTables or {}
                ).get('GroupDisplayVote', {})
        rows = table.values() if isinstance(table, dict) else table
        votes = []
        for row in rows:
            name = getattr(row, 'name', '')
            tally = tally_display_vote(self.manager, name)
            votes.append({
                'name': name,
                'displayName': getattr(row, 'display_name', '') or name,
                'description': getattr(row, 'description', ''),
                'groupName': getattr(row, 'group_name', ''),
                'conceptName': getattr(row, 'concept_name', ''),
                'mode': getattr(row, 'mode', 'approval'),
                'status': getattr(row, 'status', 'open'),
                'opensDate': getattr(row, 'opens_date', ''),
                'closesDate': getattr(row, 'closes_date', ''),
                'electedDisplayName':
                    getattr(row, 'elected_display_name', ''),
                'tallyAvailable': bool(tally.get('ok')),
                'ballotsCast': tally.get('ballotsCast', 0),
                'winners': tally.get('winners', []),
                'candidates': tally.get('candidates', []),
            })
        response.media = {'ok': True, 'displayVotes': votes}

    def on_get_display_vote_tally(self, request, response, name):
        report = tally_display_vote(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_display_vote_displays(self, request, response, name):
        votes = (self.manager.objectTables or {}).get(
            'GroupDisplayVote', {})
        rows = votes.values() if isinstance(votes, dict) else votes
        vote = next((v for v in rows
                    if getattr(v, 'name', '') == name), None)
        if vote is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no GroupDisplayVote named '{name}'"}
            return
        try:
            candidate_names = json.loads(getattr(
                vote, 'candidate_display_names_json', '') or '[]')
        except Exception:
            candidate_names = []
        displays_table = (self.manager.objectTables or {}
                          ).get('DisplayDefinition', {})
        displays_by_name = {
            getattr(r, 'name', ''): r
            for r in (displays_table.values()
                     if isinstance(displays_table, dict)
                     else displays_table)}
        resolved = []
        for cname in candidate_names:
            row = displays_by_name.get(cname)
            if row is None:
                resolved.append(
                    {'name': cname, 'found': False, 'items': []})
                continue
            try:
                definition = json.loads(
                    getattr(row, 'definition', '') or '{}')
            except Exception:
                definition = {}
            # Only 'text' items are extracted — the only DisplayItem
            # type this seed uses; anything else degrades to an empty
            # items list rather than guessing how to render it.
            items = [
                {'title': item.get('title', ''),
                 'body': item.get('item', '')}
                for r in definition.get('rows', [])
                for item in r.get('items', [])
                if item.get('type') == 'text'
            ]
            resolved.append({
                'name': cname,
                'found': True,
                'description': getattr(row, 'description', ''),
                'items': items,
            })
        response.media = {'ok': True, 'vote': name, 'displays': resolved}

    def on_post_display_vote_apply(self, request, response, name):
        result = apply_display_vote(self.manager, name)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_logic_fork_votes(self, request, response):
        table = (self.manager.objectTables or {}
                ).get('LogicForkVote', {})
        rows = table.values() if isinstance(table, dict) else table
        votes = []
        for row in rows:
            name = getattr(row, 'name', '')
            tally = tally_logic_fork_vote(self.manager, name)
            votes.append({
                'name': name,
                'displayName': getattr(row, 'display_name', '') or name,
                'description': getattr(row, 'description', ''),
                'decisionProcedure':
                    getattr(row, 'decision_procedure_name', ''),
                'fork': getattr(row, 'fork_name', ''),
                'mode': getattr(row, 'mode', 'sole'),
                'status': getattr(row, 'status', 'open'),
                'opensDate': getattr(row, 'opens_date', ''),
                'closesDate': getattr(row, 'closes_date', ''),
                'electedCriterionName':
                    getattr(row, 'elected_criterion_name', ''),
                'tallyAvailable': bool(tally.get('ok')),
                'ballotsCast': tally.get('ballotsCast', 0),
                'winners': tally.get('winners', []),
                'candidates': tally.get('candidates', []),
            })
        response.media = {'ok': True, 'logicForkVotes': votes}

    def on_get_logic_fork_vote_tally(self, request, response, name):
        report = tally_logic_fork_vote(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_logic_fork_vote_apply(self, request, response, name):
        result = apply_logic_fork_vote(self.manager, name)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_decision_procedure_resolved(self, request, response, name):
        report = resolved_procedure_summary(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    # --- ncg-2: court cases on the compiled-fork-graph seam ---

    def on_post_court_case_create(self, request, response):
        from scoring.court_case_basis import create_court_case
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        result = create_court_case(
            self.manager,
            payload.get('name', ''),
            payload.get('decision_procedure_name', ''),
            initial_context=payload.get('initial_context') or {},
            adjudicator_type=payload.get('adjudicator_type', 'judge'),
            adjudicator_name=payload.get('adjudicator_name', ''),
            jurisdiction_subject_name=payload.get(
                'jurisdiction_subject_name', ''),
            notes=payload.get('notes', ''))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_court_case_advance(self, request, response, name):
        from scoring.court_case_basis import advance_case
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        result = advance_case(
            self.manager, name, payload.get('determination'),
            supplied_by=payload.get('supplied_by', ''))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_court_case(self, request, response, name):
        from scoring.court_case_basis import case_report
        report = case_report(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_system_choice_outcomes(self, request, response, fork):
        term = request.get_param('term') or ''
        if not term:
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'error': "missing required query param 'term' — name "
                         'the outcome ScoreTerm to compare (e.g. '
                         '?term=rape-occurrence-rate)'}
            return
        report = compare_outcomes_by_system_choice(self.manager, fork, term)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

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
