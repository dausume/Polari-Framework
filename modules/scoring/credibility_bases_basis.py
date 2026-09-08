"""
@cross-cutting
@module scoring.credibility_bases_basis
@tags @xc:bindings

Credibility BASES (Dustin 2026-07-16): "accountability of
professional and impact based among other forms of distinct
credibility that is relevant per context" — a person impacted by an
issue may rebut a logically-valid proof from lived experience; a
company scientist may counter with a professional basis that CARRIES
its employer disclosure; an independent mathematician "proven to not
have background related to it" may weigh in methodologically. Each
speaks FROM a declared basis, and readings report the kinds
DISTINCTLY — never collapsed into one number (the comprehension-vote
lesson).

Plus the relevance layer (same session): "people to also be able to
vote for what kinds of professional, locality based and impact based
qualifications may be relevant so that people can more quickly see
and give priority to those inputs without being drowned out."
Relevance votes RANK the basis kinds/qualifiers per context;
prioritized readings ORDER stance groups by that ranking.
ANTI-DROWNING IS ORDERING, NEVER EXCLUSION — unranked kinds and
unattributed stances always appear after, never dropped.

Citizen-first: no basis is ever REQUIRED. A stance without a basis
link reads 'unattributed basis' — participation is never gated on
credentials; the basis layer adds visibility, not admission control.

Basis attribution attaches via LINKING ROWS (StanceBasis) — the
landed stance classes (ProofRebuttal/ProofVote/
AssertionCredibilityVote/TermRelationAssertion/TermScopeVote) are
untouched, and consumers not asking for bases see identical
readings.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (future basis-aware reading routes)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/credibility_bases/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.credibility_bases._shared import BASIS_KINDS, CLAIM_STATUSES, CLAIM_TRANSITIONS, SMALL_SAMPLE, STANCE_KINDS, _READING_NOTE, _append_history, _attester_unit, _basis_descriptor, _by_name, _context_chain, _contributor_exists, _group_by_basis, _insert, _latest_by_unit, _links_for, _persist, _prioritize, _rank_positions, _rows, _scope_covers, _stamp, _stance_entry, _stance_subject_contexts, _unit_key, apply_attestation_verdict, assertion_reading_by_basis, attestation_tally, contributor_standing, prioritized_assertion_stances, prioritized_stances, proof_reading_by_basis, qualification_relevance  # noqa: F401
from scoring.objects.credibility_bases.CredibilityClaim import CredibilityClaim  # noqa: F401
from scoring.objects.credibility_bases.ClaimAttestation import ClaimAttestation  # noqa: F401
from scoring.objects.credibility_bases.StanceBasis import StanceBasis  # noqa: F401
from scoring.objects.credibility_bases.QualificationRelevanceVote import QualificationRelevanceVote  # noqa: F401

import json

def create_claim(manager, name, contributor_name, basis_kind,
                 statement, qualifier='', domain_scope=None,
                 evidence_url='', affiliations=None,
                 declared_conflicts=None, independence_note='',
                 notes=''):
    if basis_kind not in BASIS_KINDS:
        return {'ok': False,
                'error': f"unknown basis kind '{basis_kind}'",
                'kinds': list(BASIS_KINDS)}
    if not _contributor_exists(manager, contributor_name):
        return {'ok': False,
                'error': f"'{contributor_name}' is not a Contributor "
                         'row — standing is accountable to a person',
                'suggestion': {'knob': 'Contributor',
                               'action': 'register the contributor '
                                         'first'}}
    if not (statement or '').strip():
        return {'ok': False,
                'error': 'a claim needs its statement — WHAT is the '
                         'credential / relation / competence'}
    if _by_name(manager, 'CredibilityClaim').get(name) is not None:
        return {'ok': False,
                'error': f"a CredibilityClaim named '{name}' "
                         'already exists'}
    claim = CredibilityClaim(
        name=name, contributor_name=contributor_name,
        basis_kind=basis_kind, qualifier=qualifier,
        domain_scope_json=json.dumps(list(domain_scope or [])),
        statement=statement, evidence_url=evidence_url,
        affiliations_json=json.dumps(list(affiliations or [])),
        declared_conflicts_json=json.dumps(
            list(declared_conflicts or [])),
        independence_note=independence_note, status='claimed',
        status_history_json='[]', notes=notes, manager=manager)
    _append_history(claim, 'claimed', by=contributor_name)
    _insert(manager, 'CredibilityClaim', claim)
    return {'ok': True, 'claim': name, 'status': 'claimed'}
def attest_claim(manager, name, claim_name, attester, supports,
                 rationale, on_behalf_of_group='', cast_at='',
                 notes=''):
    claim = _by_name(manager, 'CredibilityClaim').get(claim_name)
    if claim is None:
        return {'ok': False,
                'error': f"no CredibilityClaim named '{claim_name}'",
                'knownClaims': sorted(
                    _by_name(manager, 'CredibilityClaim'))}
    if attester == claim.contributor_name:
        return {'ok': False,
                'error': 'a claim cannot attest itself — attestation '
                         'is OTHERS vouching for (or disputing) the '
                         'standing'}
    if not _contributor_exists(manager, attester):
        return {'ok': False,
                'error': f"'{attester}' is not a Contributor row"}
    if not (rationale or '').strip():
        return {'ok': False,
                'error': 'attestations carry their rationale'}
    if _by_name(manager, 'ClaimAttestation').get(name) is not None:
        return {'ok': False,
                'error': f"a ClaimAttestation named '{name}' "
                         'already exists'}
    row = ClaimAttestation(
        name=name, claim_name=claim_name, attester=attester,
        on_behalf_of_group=on_behalf_of_group,
        supports=bool(supports), rationale=rationale,
        cast_at=_stamp(cast_at), notes=notes, manager=manager)
    _insert(manager, 'ClaimAttestation', row)
    return {'ok': True, 'attestation': name}
def attach_basis(manager, stance_kind, stance_name, claim_name,
                 at='', notes=''):
    if stance_kind not in STANCE_KINDS:
        return {'ok': False,
                'error': f"unknown stance kind '{stance_kind}'",
                'kinds': sorted(STANCE_KINDS)}
    table, actor_field, _link = STANCE_KINDS[stance_kind]
    stance = _by_name(manager, table).get(stance_name)
    if stance is None:
        return {'ok': False,
                'error': f"no {table} named '{stance_name}'",
                'known': sorted(_by_name(manager, table))}
    claim = _by_name(manager, 'CredibilityClaim').get(claim_name)
    if claim is None:
        return {'ok': False,
                'error': f"no CredibilityClaim named '{claim_name}'",
                'knownClaims': sorted(
                    _by_name(manager, 'CredibilityClaim'))}
    actor = getattr(stance, actor_field, '')
    if actor != claim.contributor_name:
        return {'ok': False,
                'error': f"the stance's actor is '{actor}' but the "
                         f"claim belongs to "
                         f"'{claim.contributor_name}' — no one "
                         'speaks from another person\'s credibility'}
    link_name = f'basis--{stance_kind}--{stance_name}'
    if _by_name(manager, 'StanceBasis').get(link_name) is not None:
        return {'ok': False,
                'error': f"stance '{stance_name}' already carries a "
                         'basis link — detach/re-link deliberately',
                'existing': link_name}
    link = StanceBasis(name=link_name, stance_kind=stance_kind,
                       stance_name=stance_name,
                       claim_name=claim_name,
                       attached_at=_stamp(at), notes=notes,
                       manager=manager)
    _insert(manager, 'StanceBasis', link)
    return {'ok': True, 'link': link_name}
def cast_relevance_vote(manager, name, context_name, basis_kind,
                        voter, relevant, rationale, qualifier='',
                        on_behalf_of_group='', cast_at='',
                        notes=''):
    if basis_kind not in BASIS_KINDS:
        return {'ok': False,
                'error': f"unknown basis kind '{basis_kind}'",
                'kinds': list(BASIS_KINDS)}
    if not _contributor_exists(manager, voter):
        return {'ok': False,
                'error': f"'{voter}' is not a Contributor row"}
    if not (rationale or '').strip():
        return {'ok': False,
                'error': 'relevance votes carry their rationale'}
    row = QualificationRelevanceVote(
        name=name, context_name=context_name,
        basis_kind=basis_kind, qualifier=qualifier, voter=voter,
        on_behalf_of_group=on_behalf_of_group,
        relevant=bool(relevant), rationale=rationale,
        cast_at=_stamp(cast_at), notes=notes, manager=manager)
    _insert(manager, 'QualificationRelevanceVote', row)
    return {'ok': True, 'vote': name}
