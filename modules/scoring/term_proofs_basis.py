"""
@cross-cutting
@module scoring.term_proofs_basis
@tags @xc:bindings

Democratic term proofs (Dustin 2026-07-16) — the evidence layer under
the Term Competition's democracy. A TermProof is a structured,
RE-RUNNABLE demonstration backing one of four claim kinds:

  sufficiency      what suffices for a term to qualify for a context
  robustness       one term is more robust than another
  subset           one term is a logical subset of another
  misleading-contextualization
                   one term is more accurate to the context — the
                   canonical case: a national AVERAGE of race
                   competitiveness hiding that near a majority of
                   races are UNCONTESTED; the proof IS the
                   side-by-side over the same data, the verdict is
                   a VOTE.

Design rules carried from the house precedents:
  * Demonstrations are DATA (ordered steps over named
    ContextualizedValues) and re-runnable — the cross-validation
    idiom applied to arguments (rerun agreement raises standing;
    divergence is surfaced, never hidden).
  * Rebuttals make proofs answerable (data / framing / generality);
    a proof with standing open rebuttals READS differently.
  * TWO vote kinds, never conflated: validity ('is the demonstration
    correct') and comprehension ('shown both presentations, which
    gives the more accurate impression'). A proof can be valid AND
    fail comprehension — that tension is information.
  * The manipulation catalog is votable rows (the VenueMismatchPattern
    idiom applied to statistics); computable exposure checks emit
    NEUTRAL ARITHMETIC findings — the word 'misleading' never appears
    in a check result; that verdict belongs to the votes.
  * Acceptance is an explicit act, per context scope, returning
    SUGGESTIONS for what the proof backs — never auto-applied.
  * Dependencies are recorded; a rejected/superseded foundation flips
    downstream proofs to 'stale — foundation changed', visibly.

@consumers
  - scoring.term_competition_basis (proofs back scope votes / relations /
    elections — bridged by suggestions, not writes)
  - polariServer.defClassList (auto-CRUDE + persistence)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/term_proofs/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.term_proofs._shared import COMPARATIVE_KINDS, COMPREHENSION_CHOICES, COMPUTABILITY, DEMO_MEAN, DEMO_PROVENANCE, DEMO_STATE_VALUES, NEAR_ZERO, PROOF_KINDS, PROOF_STATUSES, PROOF_TRANSITIONS, REBUTTAL_KINDS, REBUTTAL_STATUSES, RERUN_TOLERANCE, SEED_MANIPULATION_PATTERNS, SEED_TERM_PROOFS, SMALL_SAMPLE, VALIDITY_CHOICES, VALIDITY_WEIGHTS, VOTE_KINDS, _OPERATIONS, _READING_NOTE, _UNBUILT, _acceptance_suggestions, _agrees, _append_history, _apply_operation, _by_name, _dependency_closure, _insert, _latest_by_unit, _pattern, _persist, _resolve_inputs, _rows, _stamp, _unit_key, _values_of, accept_proof, check_aggregation_masking, check_outlier_driven_mean, check_stale_vintage, proof_reading, propagate_staleness, reject_proof, rerun_demonstration, resolve_rebuttal, standing_rebuttals, transition_proof  # noqa: F401
from scoring.objects.term_proofs.TermProof import TermProof  # noqa: F401
from scoring.objects.term_proofs.ProofRebuttal import ProofRebuttal  # noqa: F401
from scoring.objects.term_proofs.DataManipulationPattern import DataManipulationPattern  # noqa: F401
from scoring.objects.term_proofs.ProofVote import ProofVote  # noqa: F401

import json

def create_proof(manager, name, proof_kind, claim, subject_term,
                 for_concept_name, comparison_term='',
                 context_scope=None, demonstration=None,
                 manipulation_pattern='', depends_on=None,
                 proposed_by='', on_behalf_of_group='', notes='',
                 at=''):
    """Open a proof in 'draft'. Honest refusals throughout; cycles
    in the dependency graph are refused at creation."""
    if _by_name(manager, 'TermProof').get(name) is not None:
        return {'ok': False,
                'error': f"a TermProof named '{name}' already exists"}
    if proof_kind not in PROOF_KINDS:
        return {'ok': False,
                'error': f"unknown proof kind '{proof_kind}'",
                'kinds': list(PROOF_KINDS)}
    if not (claim or '').strip():
        return {'ok': False,
                'error': 'a proof needs its claim stated plainly'}
    terms = _by_name(manager, 'ScoreTerm')
    if subject_term not in terms:
        return {'ok': False,
                'error': f"unknown subject term '{subject_term}'",
                'knownTerms': sorted(terms)}
    if proof_kind in COMPARATIVE_KINDS:
        if not comparison_term:
            return {'ok': False,
                    'error': f"a {proof_kind} proof argues about a "
                             f'comparison term — name it'}
        if comparison_term not in terms:
            return {'ok': False,
                    'error': f"unknown comparison term "
                             f"'{comparison_term}'",
                    'knownTerms': sorted(terms)}
    elif comparison_term:
        return {'ok': False,
                'error': 'a sufficiency proof stands alone — no '
                         'comparison term'}
    if manipulation_pattern:
        patterns = _by_name(manager, 'DataManipulationPattern')
        if manipulation_pattern not in patterns:
            return {'ok': False,
                    'error': f'unknown manipulation pattern '
                             f"'{manipulation_pattern}'",
                    'knownPatterns': sorted(patterns)}
    depends_on = list(depends_on or [])
    if name in depends_on:
        return {'ok': False,
                'error': 'a proof cannot depend on itself'}
    proofs = _by_name(manager, 'TermProof')
    unknown_deps = [d for d in depends_on if d not in proofs]
    if unknown_deps:
        return {'ok': False,
                'error': f'unknown dependency proofs: {unknown_deps}',
                'knownProofs': sorted(proofs)}
    _, cyclic = _dependency_closure(manager, [name],
                                    extra_edges={name: depends_on})
    if cyclic:
        return {'ok': False,
                'error': 'the dependency graph would contain a '
                         'cycle — proofs must rest on foundations, '
                         'not on themselves'}
    proof = TermProof(
        name=name, proof_kind=proof_kind, claim=claim,
        subject_term=subject_term, comparison_term=comparison_term,
        for_concept_name=for_concept_name,
        context_scope_json=json.dumps(list(context_scope or [])),
        demonstration_json=json.dumps(list(demonstration or [])),
        manipulation_pattern=manipulation_pattern,
        depends_on_json=json.dumps(depends_on),
        status='draft', history_json='[]',
        proposed_by=proposed_by,
        on_behalf_of_group=on_behalf_of_group, notes=notes,
        manager=manager)
    _append_history(proof, 'created', by=proposed_by, at=at)
    _insert(manager, 'TermProof', proof)
    return {'ok': True, 'proof': name, 'status': 'draft'}
def raise_rebuttal(manager, name, proof_name, challenge_kind,
                   rationale, raised_by, on_behalf_of_group='',
                   demonstration=None, at='', notes=''):
    proofs = _by_name(manager, 'TermProof')
    proof = proofs.get(proof_name)
    if proof is None:
        return {'ok': False,
                'error': f"no TermProof named '{proof_name}'",
                'knownProofs': sorted(proofs)}
    if challenge_kind not in REBUTTAL_KINDS:
        return {'ok': False,
                'error': f"unknown challenge kind "
                         f"'{challenge_kind}'",
                'kinds': list(REBUTTAL_KINDS)}
    if not (rationale or '').strip():
        return {'ok': False,
                'error': 'a rebuttal needs its rationale — the WHY '
                         'is the point'}
    if _by_name(manager, 'ProofRebuttal').get(name) is not None:
        return {'ok': False,
                'error': f"a ProofRebuttal named '{name}' already "
                         'exists'}
    rebuttal = ProofRebuttal(
        name=name, proof_name=proof_name,
        challenge_kind=challenge_kind, rationale=rationale,
        demonstration_json=json.dumps(list(demonstration or [])),
        status='open', raised_by=raised_by,
        on_behalf_of_group=on_behalf_of_group,
        raised_at=_stamp(at), notes=notes, manager=manager)
    _insert(manager, 'ProofRebuttal', rebuttal)
    flipped = None
    if proof.status in ('demonstrated', 'accepted'):
        transition_proof(manager, proof_name, 'challenged',
                         by=raised_by,
                         note=f"rebuttal '{name}' raised "
                              f'({challenge_kind})', at=at)
        flipped = 'challenged'
    return {'ok': True, 'rebuttal': name, 'proofStatus': flipped
            or proof.status}
def cast_proof_vote(manager, proof_name, voter, vote_kind, choice,
                    rationale='', on_behalf_of_group='', cast_at='',
                    name=''):
    proofs = _by_name(manager, 'TermProof')
    if proofs.get(proof_name) is None:
        return {'ok': False,
                'error': f"no TermProof named '{proof_name}'",
                'knownProofs': sorted(proofs)}
    if vote_kind not in VOTE_KINDS:
        return {'ok': False,
                'error': f"unknown vote kind '{vote_kind}'",
                'kinds': list(VOTE_KINDS)}
    valid_choices = (VALIDITY_CHOICES if vote_kind == 'validity'
                     else COMPREHENSION_CHOICES)
    if choice not in valid_choices:
        return {'ok': False,
                'error': f"'{choice}' is not a {vote_kind} choice",
                'choices': list(valid_choices)}
    if not (voter or '').strip():
        return {'ok': False, 'error': 'votes carry attribution — '
                                      'name the voter'}
    unit = on_behalf_of_group or f'individual:{voter}'
    superseded = [v.name for v in _rows(manager, 'ProofVote')
                  if v.proof_name == proof_name
                  and v.vote_kind == vote_kind
                  and _unit_key(v) == unit]
    vote_name = name or (f'{proof_name}--{vote_kind}--'
                         f'{unit.replace("individual:", "")}'
                         f'-{len(superseded) + 1}')
    vote = ProofVote(name=vote_name, proof_name=proof_name,
                     voter=voter,
                     on_behalf_of_group=on_behalf_of_group,
                     vote_kind=vote_kind, choice=choice,
                     rationale=rationale, cast_at=_stamp(cast_at),
                     manager=manager)
    _insert(manager, 'ProofVote', vote)
    return {'ok': True, 'vote': vote_name, 'unit': unit,
            'supersedes': superseded[-1] if superseded else None}
