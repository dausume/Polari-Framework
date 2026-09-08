"""
@cross-cutting
@module scoring.epistemics_api
@tags @xc:bindings @xc:readSurfaces

HTTP read surfaces for the 2026-07-16 epistemics stack — term
proofs/manipulation patterns, term competition, credibility bases,
policy drafts + intent, venue patterns, legislation, data-gathering
credibility, and the source/trust layer (gov sources +
cross-validation). These modules previously had generic-CRUDE access
only; this treeObject routes their existing report/list/tally
functions (read-only, no new semantics) for the PSC frontend.
Self-registering (ScoringAPI/AuthorityAPI pattern).

@consumers
  - polariServer (instantiated beside AuthorityAPI)
  - PSC backend / frontend read views
@see scoring/authority_api.py (conventions), scoring/scoring_api.py
"""

from objectTreeDecorators import treeObject, treeObjectInit


class EpistemicsAPI(treeObject):
    """Read-only endpoints over the epistemics modules' existing
    report/list/tally functions."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/scoring/epistemics'
        if polServer is not None:
            add = polServer.falconServer.add_route
            # Term proofs
            add('/api/scoring/proofs', self, suffix='proofs')
            add('/api/scoring/proofs/{name}', self, suffix='proof')
            add('/api/scoring/proofs/{name}/by-basis', self,
                suffix='proof_by_basis')
            add('/api/scoring/manipulation-patterns', self,
                suffix='manipulation_patterns')
            # Term competition
            add('/api/scoring/term-competition/{concept}', self,
                suffix='term_competition')
            add('/api/scoring/term-competition/{concept}/proposals',
                self, suffix='term_proposals')
            add('/api/scoring/term-competition/{concept}/scope',
                self, suffix='term_scope')
            add('/api/scoring/terms/{name}/relations', self,
                suffix='term_relations')
            # Credibility
            add('/api/scoring/assertions/{name}/credibility', self,
                suffix='assertion_credibility')
            add('/api/scoring/assertions/{name}/by-basis', self,
                suffix='assertion_by_basis')
            add('/api/scoring/assertions/{name}/prioritized', self,
                suffix='assertion_prioritized')
            add('/api/scoring/contributors/{name}/standing', self,
                suffix='contributor_standing')
            add('/api/scoring/relevance', self, suffix='relevance')
            # Policy drafts + intent
            add('/api/scoring/drafts', self, suffix='drafts')
            add('/api/scoring/drafts/{name}/carryover', self,
                suffix='draft_carryover')
            add('/api/scoring/policies/{name}/intent', self,
                suffix='policy_intent')
            # Venue patterns
            add('/api/scoring/venue-patterns', self,
                suffix='venue_patterns')
            add('/api/scoring/venue-patterns/detect', self,
                suffix='venue_detect')
            # Legislation
            add('/api/scoring/legislation', self,
                suffix='legislation')
            add('/api/scoring/legislation/{name}/contributions',
                self, suffix='legislation_contributions')
            add('/api/scoring/legislation/{name}/burial', self,
                suffix='legislation_burial')
            add('/api/scoring/legislators/{name}/voting-record',
                self, suffix='legislator_voting_record')
            # Data gathering
            add('/api/scoring/gathering/{name}/credibility', self,
                suffix='gathering_credibility')
            add('/api/scoring/gathering/compare', self,
                suffix='gathering_compare')
            # Sources + trust
            add('/api/scoring/sources/glossary', self,
                suffix='sources_glossary')
            add('/api/scoring/sources/{name}/report', self,
                suffix='source_report')
            add('/api/scoring/sources/{name}/retrievals', self,
                suffix='source_retrievals')
            add('/api/scoring/providers/reliability', self,
                suffix='provider_reliability')
            add('/api/scoring/retrievals/sourcing', self,
                suffix='retrievals_sourcing')

    # ------------------------------------------------------------ #
    # Term proofs (scoring/term_proofs_basis.py)
    # ------------------------------------------------------------ #

    def on_get_proofs(self, request, response):
        from scoring.term_proofs_basis import _rows
        proofs = [{
            'name': getattr(row, 'name', ''),
            'status': getattr(row, 'status', ''),
            'proofKind': getattr(row, 'proof_kind', ''),
            'claim': getattr(row, 'claim', ''),
            'subjectTerm': getattr(row, 'subject_term', ''),
            'comparisonTerm': getattr(row, 'comparison_term', ''),
            'forConceptName': getattr(row, 'for_concept_name', ''),
            'manipulationPattern':
                getattr(row, 'manipulation_pattern', ''),
            'proposedBy': getattr(row, 'proposed_by', ''),
            'onBehalfOfGroup':
                getattr(row, 'on_behalf_of_group', ''),
        } for row in _rows(self.manager, 'TermProof')]
        response.media = {'ok': True, 'proofs': proofs}

    def on_get_proof(self, request, response, name):
        from scoring.term_proofs_basis import proof_reading
        result = proof_reading(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_manipulation_patterns(self, request, response):
        from scoring.term_proofs_basis import _rows
        patterns = [{
            'name': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'description': getattr(row, 'description', ''),
            'counterPresentation':
                getattr(row, 'counter_presentation', ''),
            'exposureCheck': getattr(row, 'exposure_check', ''),
            'computability': getattr(row, 'computability', ''),
            'proposedBy': getattr(row, 'proposed_by', ''),
            'notes': getattr(row, 'notes', ''),
        } for row in _rows(self.manager, 'DataManipulationPattern')]
        response.media = {'ok': True, 'patterns': patterns}

    # ------------------------------------------------------------ #
    # Term competition (scoring/term_competition_basis.py)
    # ------------------------------------------------------------ #

    def on_get_term_competition(self, request, response, concept):
        from scoring.term_competition_basis import term_competition_report
        result = term_competition_report(self.manager, concept)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_term_proposals(self, request, response, concept):
        from scoring.term_competition_basis import proposals_for
        proposals = [{
            'name': getattr(row, 'name', ''),
            'proposedTermName':
                getattr(row, 'proposed_term_name', ''),
            'forConceptName': getattr(row, 'for_concept_name', ''),
            'proposedByGroup':
                getattr(row, 'proposed_by_group', ''),
            'proposedBy': getattr(row, 'proposed_by', ''),
            'rationale': getattr(row, 'rationale', ''),
            'status': getattr(row, 'status', ''),
        } for row in proposals_for(self.manager, concept)]
        response.media = {'ok': True, 'concept': concept,
                          'proposals': proposals}

    def on_get_term_scope(self, request, response, concept):
        from scoring.term_competition_basis import scope_tally
        term = request.get_param('term')
        if not term:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "missing 'term' query param"}
            return
        response.media = scope_tally(self.manager, concept, term)

    def on_get_term_relations(self, request, response, name):
        from scoring.term_competition_basis import relations_for
        response.media = {'ok': True, 'term': name,
                          'relations': relations_for(self.manager,
                                                     name)}

    # ------------------------------------------------------------ #
    # Credibility (scoring/credibility_bases_basis.py +
    # scoring/assertion_credibility_basis.py)
    # ------------------------------------------------------------ #

    def on_get_assertion_credibility(self, request, response, name):
        from scoring.assertion_credibility_basis import (
            assertion_credibility_reading,
        )
        result = assertion_credibility_reading(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_assertion_by_basis(self, request, response, name):
        from scoring.credibility_bases_basis import (
            assertion_reading_by_basis,
        )
        result = assertion_reading_by_basis(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_proof_by_basis(self, request, response, name):
        from scoring.credibility_bases_basis import proof_reading_by_basis
        result = proof_reading_by_basis(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_assertion_prioritized(self, request, response, name):
        from scoring.credibility_bases_basis import (
            prioritized_assertion_stances,
        )
        result = prioritized_assertion_stances(
            self.manager, name,
            request.get_param('context_name') or '')
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_contributor_standing(self, request, response, name):
        from scoring.credibility_bases_basis import contributor_standing
        result = contributor_standing(
            self.manager, name,
            domain=request.get_param('domain') or '')
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_relevance(self, request, response):
        from scoring.credibility_bases_basis import qualification_relevance
        response.media = qualification_relevance(
            self.manager, request.get_param('context_name') or '')

    # ------------------------------------------------------------ #
    # Policy drafts + intent (scoring/policy_drafts_basis.py,
    # scoring/policy_intent_basis.py)
    # ------------------------------------------------------------ #

    def on_get_drafts(self, request, response):
        from scoring.term_proofs_basis import _rows
        drafts = [{
            'name': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'description': getattr(row, 'description', ''),
            'status': getattr(row, 'status', ''),
            'draftedBy': getattr(row, 'drafted_by', ''),
            'sponsoringGroup':
                getattr(row, 'sponsoring_group', ''),
            'jurisdictionSubjectName':
                getattr(row, 'jurisdiction_subject_name', ''),
            'textUrl': getattr(row, 'text_url', ''),
            'enactedPolicySubjectName':
                getattr(row, 'enacted_policy_subject_name', ''),
        } for row in _rows(self.manager, 'PolicyDraft')]
        response.media = {'ok': True, 'drafts': drafts}

    def on_get_draft_carryover(self, request, response, name):
        from scoring.policy_drafts_basis import draft_score_carryover
        result = draft_score_carryover(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_policy_intent(self, request, response, name):
        from scoring.policy_intent_basis import (
            current_intent, intent_chain, intent_suggestions,
        )
        current = current_intent(self.manager, name)
        if not current.get('ok'):
            response.status = '404 Not Found'
            response.media = current
            return
        chain = [{
            'name': getattr(row, 'name', ''),
            'intentText': getattr(row, 'intent_text', ''),
            'setBy': getattr(row, 'set_by', ''),
            'setAt': getattr(row, 'set_at', ''),
            'supersededBy': getattr(row, 'superseded_by', ''),
        } for row in intent_chain(self.manager, name)]
        result = {'ok': True, 'draft': name, 'current': current,
                  'chain': chain}
        # intent_suggestions takes an intent name — only callable
        # when a current intent exists.
        if current.get('intent'):
            result['suggestions'] = intent_suggestions(
                self.manager, current['intent'])
        response.media = result

    # ------------------------------------------------------------ #
    # Venue patterns (scoring/venue_patterns_basis.py)
    # ------------------------------------------------------------ #

    def on_get_venue_patterns(self, request, response):
        from scoring.term_proofs_basis import _rows
        patterns = [{
            'name': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'description': getattr(row, 'description', ''),
            'severityNote': getattr(row, 'severity_note', ''),
            'proposedBy': getattr(row, 'proposed_by', ''),
            'enabled': bool(getattr(row, 'enabled', True)),
            'notes': getattr(row, 'notes', ''),
        } for row in _rows(self.manager, 'VenueMismatchPattern')]
        response.media = {'ok': True, 'patterns': patterns}

    def on_get_venue_detect(self, request, response):
        from scoring.venue_patterns_basis import detect_patterns
        issue_name = request.get_param('issue_name')
        if not issue_name:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "missing 'issue_name' query "
                                       'param'}
            return
        result = detect_patterns(self.manager, issue_name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    # ------------------------------------------------------------ #
    # Legislation (scoring/legislation_basis.py)
    # ------------------------------------------------------------ #

    def on_get_legislation(self, request, response):
        from scoring.term_proofs_basis import _rows
        records = [{
            'name': getattr(row, 'name', ''),
            'billId': getattr(row, 'bill_id', ''),
            'title': getattr(row, 'title', ''),
            'jurisdictionSubjectName':
                getattr(row, 'jurisdiction_subject_name', ''),
            'legislature': getattr(row, 'legislature', ''),
            'status': getattr(row, 'status', ''),
            'declaredSubject':
                getattr(row, 'declared_subject', ''),
            'textUrl': getattr(row, 'text_url', ''),
            'entryMode': getattr(row, 'entry_mode', ''),
            'sourceName': getattr(row, 'source_name', ''),
            'retrievedAt': getattr(row, 'retrieved_at', ''),
        } for row in _rows(self.manager, 'LegislationRecord')]
        response.media = {'ok': True, 'legislation': records}

    def on_get_legislation_contributions(self, request, response,
                                         name):
        from scoring.legislation_basis import contributions_for
        result = contributions_for(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_legislation_burial(self, request, response, name):
        from scoring.legislation_basis import detect_burial_patterns
        kwargs = {}
        last_minute_days = request.get_param('last_minute_days')
        if last_minute_days is not None:
            try:
                kwargs['last_minute_days'] = int(last_minute_days)
            except ValueError:
                response.status = '400 Bad Request'
                response.media = {
                    'ok': False,
                    'error': "'last_minute_days' must be an int"}
                return
        overlap_threshold = request.get_param('overlap_threshold')
        if overlap_threshold is not None:
            try:
                kwargs['overlap_threshold'] = \
                    float(overlap_threshold)
            except ValueError:
                response.status = '400 Bad Request'
                response.media = {
                    'ok': False,
                    'error': "'overlap_threshold' must be a float"}
                return
        result = detect_burial_patterns(self.manager, name, **kwargs)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_legislator_voting_record(self, request, response,
                                        name):
        from scoring.legislation_basis import legislator_voting_record
        result = legislator_voting_record(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    # ------------------------------------------------------------ #
    # Data gathering (scoring/data_gathering_basis.py)
    # ------------------------------------------------------------ #

    def on_get_gathering_credibility(self, request, response, name):
        from scoring.data_gathering_basis import (
            gathering_credibility_profile,
        )
        result = gathering_credibility_profile(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_gathering_compare(self, request, response):
        from scoring.data_gathering_basis import (
            compare_gathering_solutions,
        )
        term_names = [t for t in (request.get_param('a'),
                                  request.get_param('b'))
                      if t]
        result = compare_gathering_solutions(self.manager,
                                             term_names)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    # ------------------------------------------------------------ #
    # Sources + trust (dmvdata/gov_sources_basis.py,
    # dmvdata/cross_validation_basis.py)
    # ------------------------------------------------------------ #

    def on_get_sources_glossary(self, request, response):
        from dmvdata.gov_sources_basis import source_glossary
        response.media = {'ok': True,
                          'glossary': source_glossary(self.manager)}

    def on_get_source_report(self, request, response, name):
        from dmvdata.gov_sources_basis import source_report
        result = source_report(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_source_retrievals(self, request, response, name):
        from dmvdata.gov_sources_basis import retrievals_for
        response.media = {'ok': True, 'source': name,
                          'retrievals': retrievals_for(self.manager,
                                                       name)}

    def on_get_provider_reliability(self, request, response):
        from dmvdata.cross_validation_basis import provider_reliability
        group_name = request.get_param('group_name')
        if not group_name:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "missing 'group_name' query "
                                       'param'}
            return
        result = provider_reliability(self.manager, group_name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_retrievals_sourcing(self, request, response):
        from dmvdata.cross_validation_basis import sourcing_credibility
        name = request.get_param('name')
        if not name:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "missing 'name' query param"}
            return
        result = sourcing_credibility(
            self.manager, name,
            subject=request.get_param('subject') or 'retrieval')
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result
