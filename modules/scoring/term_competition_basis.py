"""
@cross-cutting
@module scoring.term_competition_basis
@tags @xc:bindings

Term Competition — the PSC termcompetition draft (Java README:
'term scope' = the valid terms for a Score's scientific context;
'purpose-equivalent terms' compete within that scope), finally built
in Polari (Dustin 2026-07-16):

  TermProposal          — a group's composite/computed term candidacy
                          for a Score, every composition entry CITED
                          to a specific source (uncited refused).
  TermRelationAssertion — asserted logical relations between terms:
                          logical-equivalent / purpose-equivalent /
                          logical-subset (related incorporated into
                          subject) / logically-exclusive-competing
                          ("this should be considered logically
                          identical/exclusive to another term — they
                          are competing terms for legitimacy") /
                          other. Confirmed relations may be
                          MATERIALIZED into ScoreTerm's long-dormant
                          equivalent_terms_json /
                          competitive_terms_json — suggestion first,
                          apply explicitly, never silent.
  context_fit           — validate a term is at least a closest match
                          to the Score's context: topic, time,
                          location (parent-chain aware), whatever
                          context kinds are declared.
  TermScopeVote         — vote on which terms even MEET CRITERIA for
                          consideration (the 'term scope' gate);
                          verdicts flip proposal status only through
                          an explicit act.
  legitimacy elections  — voting-based competitions for which
                          in-scope terms are most legitimate, riding
                          the EXISTING WorldviewElection machinery
                          (approval/sole/ranked-condorcet) at group
                          scale AND global scale. Applying an
                          election marks the winner 'elected' and
                          returns the concept-weight change as a
                          SUGGESTION — the concept row is the knob,
                          never auto-edited.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (future term-competition endpoints)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/term_competition/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.worldview_elections_basis import (ELECTION_MODES,
                                         WorldviewElection, _by_name,
                                         _parse, _rows, tally_election)

from scoring.objects.term_competition._shared import PROPOSAL_STATUSES, RELATION_KINDS, RELATION_STATUSES, RELATION_TRANSITIONS, SMALL_SAMPLE, _ELECTION_PREFIX, _ELECTION_SCALES, _MATERIALIZE_FIELD, _ancestors, _dimension_match, _fit_of, _insert, _persist, _tokenize, apply_scope_verdict, apply_term_election, context_fit, materialize_confirmed_relations, open_term_election, proposals_for, relations_for, scope_tally, term_competition_report, transition_term_relation  # noqa: F401
from scoring.objects.term_competition.TermProposal import TermProposal  # noqa: F401
from scoring.objects.term_competition.TermRelationAssertion import TermRelationAssertion  # noqa: F401
from scoring.objects.term_competition.TermScopeVote import TermScopeVote  # noqa: F401

from scoring.worldview_elections_basis import (ELECTION_MODES,
                                         WorldviewElection, _by_name,
                                         _parse, _rows, tally_election)
from datetime import datetime, timezone
import json

def propose_term(manager, name, proposed_term_name, for_concept_name,
                 proposed_by_group, proposed_by, composition,
                 rationale='', notes=''):
    """A group puts a composite/computed term in consideration for a
    Score. Every composition entry must cite its source — uncited
    compositions are refused (credibility starts at the citation)."""
    if _by_name(manager, 'TermProposal').get(name) is not None:
        return {'ok': False,
                'error': f"a TermProposal named '{name}' already "
                         'exists'}
    if _by_name(manager, 'ScoreConcept').get(
            for_concept_name) is None:
        return {'ok': False,
                'error': f"no ScoreConcept named "
                         f"'{for_concept_name}'",
                'knownConcepts': sorted(
                    _by_name(manager, 'ScoreConcept'))}
    if not isinstance(composition, list) or not composition:
        return {'ok': False,
                'error': 'composition must be a non-empty list of '
                         'cited entries'}
    uncited = [i for i, entry in enumerate(composition)
               if not isinstance(entry, dict)
               or not entry.get('source_name')
               or not entry.get('citation_url')]
    if uncited:
        return {'ok': False,
                'error': f'composition entries {uncited} lack '
                         f"'source_name' + 'citation_url' — "
                         'composite terms must be computed from '
                         'SPECIFIC CITED data sources',
                'suggestion': {
                    'knob': 'composition_json',
                    'action': 'cite each entry (source_name = a '
                              'registered source row, citation_url '
                              '= the specific product/table)'}}
    row = TermProposal(
        name=name, proposed_term_name=proposed_term_name,
        for_concept_name=for_concept_name,
        proposed_by_group=proposed_by_group,
        proposed_by=proposed_by,
        composition_json=json.dumps(composition),
        rationale=rationale, status='proposed', notes=notes,
        manager=manager)
    _insert(manager, 'TermProposal', row)
    return {'ok': True, 'proposal': name, 'status': 'proposed'}
def assert_term_relation(manager, name, subject_term, related_term,
                         relation, asserted_by,
                         on_behalf_of_group='', rationale='',
                         evidence_url='', notes=''):
    if relation not in RELATION_KINDS:
        return {'ok': False,
                'error': f"unknown relation '{relation}'",
                'relations': list(RELATION_KINDS)}
    if subject_term == related_term:
        return {'ok': False,
                'error': 'a term cannot relate to itself'}
    if not (rationale or '').strip():
        return {'ok': False,
                'error': 'a relation assertion needs a rationale — '
                         'the claim is contestable content, not a '
                         'label'}
    if relation == 'other' and not (notes or '').strip():
        return {'ok': False,
                'error': "relation 'other' requires notes describing "
                         'the logical consideration'}
    if _by_name(manager, 'TermRelationAssertion').get(
            name) is not None:
        return {'ok': False,
                'error': f"a TermRelationAssertion named '{name}' "
                         'already exists'}
    row = TermRelationAssertion(
        name=name, subject_term=subject_term,
        related_term=related_term, relation=relation,
        asserted_by=asserted_by,
        on_behalf_of_group=on_behalf_of_group,
        rationale=rationale, evidence_url=evidence_url,
        status='asserted', status_history_json='[]', notes=notes,
        manager=manager)
    _insert(manager, 'TermRelationAssertion', row)
    return {'ok': True, 'relation': name, 'status': 'asserted'}
def cast_scope_vote(manager, name, concept_name, term_name, voter,
                    eligible, on_behalf_of_group='', rationale='',
                    cast_at=''):
    if not voter:
        return {'ok': False,
                'error': 'scope votes are accountable — voter '
                         'required (pseudonyms ok)'}
    row = TermScopeVote(
        name=name, concept_name=concept_name, term_name=term_name,
        voter=voter, on_behalf_of_group=on_behalf_of_group,
        eligible=bool(eligible), rationale=rationale,
        cast_at=cast_at or datetime.now(timezone.utc).isoformat(
            timespec='seconds'),
        manager=manager)
    _insert(manager, 'TermScopeVote', row)
    return {'ok': True, 'vote': name}
