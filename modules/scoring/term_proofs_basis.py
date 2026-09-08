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

import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

PROOF_KINDS = ('sufficiency', 'robustness', 'subset',
               'misleading-contextualization')

#: Kinds that argue ABOUT a comparison term (sufficiency stands
#: alone: it argues a term meets a context's requirements).
COMPARATIVE_KINDS = ('robustness', 'subset',
                     'misleading-contextualization')

PROOF_STATUSES = ('draft', 'demonstrated', 'challenged', 'accepted',
                  'rejected', 'stale')

#: Validated lifecycle (the assertions idiom): rejected is terminal;
#: stale proofs may be re-demonstrated after their foundation moved.
PROOF_TRANSITIONS = {
    'draft': ('demonstrated',),
    'demonstrated': ('challenged', 'accepted', 'rejected', 'stale'),
    'challenged': ('demonstrated', 'accepted', 'rejected', 'stale'),
    'accepted': ('challenged', 'stale'),
    'rejected': (),
    'stale': ('demonstrated',),
}

REBUTTAL_KINDS = ('data', 'framing', 'generality')
REBUTTAL_STATUSES = ('open', 'answered', 'withdrawn', 'sustained')

VOTE_KINDS = ('validity', 'comprehension')
VALIDITY_CHOICES = ('valid', 'flawed')
COMPREHENSION_CHOICES = ('subject', 'comparison', 'neither')
VALIDITY_WEIGHTS = {'valid': 1.0, 'flawed': 0.0}

COMPUTABILITY = ('computable', 'partially-computable',
                 'judgment-only')

#: Below this many voting units a tally is a hint (scr-12a idiom).
SMALL_SAMPLE = 5

#: Aggregation-masking default: values at or below this count as the
#: concealed mass ('uncontested') — a knob per check call.
NEAR_ZERO = 0.05

#: Numeric agreement tolerance for demonstration re-runs.
RERUN_TOLERANCE = 1e-9

_READING_NOTE = ('a proof reading with evidence, not a truth '
                 'declaration')


class TermProof(treeObject):
    """One structured, re-runnable demonstration backing a term
    claim — accepted or rejected DEMOCRATICALLY, per context scope."""

    @treeObjectInit
    def __init__(self, name: str = '', proof_kind: str = '',
                 claim: str = '', subject_term: str = '',
                 comparison_term: str = '',
                 for_concept_name: str = '',
                 # ScoreContext names the proof claims validity for —
                 # acceptance is PER SCOPE, never silently wider.
                 context_scope_json: str = '[]',
                 # Ordered steps: {kind: 'reading'|'computation'|
                 # 'comparison', description, inputs: [value names or
                 # '$<stepIndex>' refs], operation?, threshold?,
                 # result}. Re-runnable by rerun_demonstration.
                 demonstration_json: str = '[]',
                 # DataManipulationPattern name, for
                 # misleading-contextualization proofs ('' otherwise).
                 manipulation_pattern: str = '',
                 depends_on_json: str = '[]',
                 status: str = 'draft',
                 # Append-only trail (the tamper-evidence idiom).
                 history_json: str = '[]',
                 proposed_by: str = '',
                 on_behalf_of_group: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.proof_kind = proof_kind
        self.claim = claim
        self.subject_term = subject_term
        self.comparison_term = comparison_term
        self.for_concept_name = for_concept_name
        self.context_scope_json = context_scope_json
        self.demonstration_json = demonstration_json
        self.manipulation_pattern = manipulation_pattern
        self.depends_on_json = depends_on_json
        self.status = status
        self.history_json = history_json
        self.proposed_by = proposed_by
        self.on_behalf_of_group = on_behalf_of_group
        self.notes = notes


class ProofRebuttal(treeObject):
    """A structured answer to a proof: challenge its DATA, its
    FRAMING, or its GENERALITY. Standing open rebuttals change how
    the proof reads."""

    @treeObjectInit
    def __init__(self, name: str = '', proof_name: str = '',
                 challenge_kind: str = '', rationale: str = '',
                 demonstration_json: str = '[]',
                 status: str = 'open', raised_by: str = '',
                 on_behalf_of_group: str = '', raised_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.proof_name = proof_name
        self.challenge_kind = challenge_kind
        self.rationale = rationale
        self.demonstration_json = demonstration_json
        self.status = status
        self.raised_by = raised_by
        self.on_behalf_of_group = on_behalf_of_group
        self.raised_at = raised_at
        self.notes = notes


class DataManipulationPattern(treeObject):
    """One recognizable shape of statistical manipulation — a
    VOTABLE catalog row (what counts as suspect framing is
    contestable), with the counter-presentation that exposes it and
    a computable exposure check where one honestly exists."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 description: str = '',
                 counter_presentation: str = '',
                 # 'module:function' for implemented checks, '' else.
                 exposure_check: str = '',
                 computability: str = 'judgment-only',
                 proposed_by: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.counter_presentation = counter_presentation
        self.exposure_check = exposure_check
        self.computability = computability
        self.proposed_by = proposed_by
        self.notes = notes


class ProofVote(treeObject):
    """One unit's vote on a proof — vote_kind 'validity' (is the
    demonstration correct) or 'comprehension' (which presentation
    gives the more accurate impression). Rows are immutable; the
    latest per (unit, kind) counts."""

    @treeObjectInit
    def __init__(self, name: str = '', proof_name: str = '',
                 voter: str = '', on_behalf_of_group: str = '',
                 vote_kind: str = '', choice: str = '',
                 rationale: str = '', cast_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.proof_name = proof_name
        self.voter = voter
        self.on_behalf_of_group = on_behalf_of_group
        self.vote_kind = vote_kind
        self.choice = choice
        self.rationale = rationale
        self.cast_at = cast_at
        self.notes = notes


# --------------------------------------------------------------- #
# shared helpers (term_competition idioms)
# --------------------------------------------------------------- #

def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return (list(table.values()) if isinstance(table, dict)
            else list(table))


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r
            for r in _rows(manager, class_name)}


def _persist(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass


def _insert(manager, class_name, row):
    table = manager.objectTables.setdefault(class_name, {})
    if not any(existing is row for existing in table.values()):
        table[row.name] = row
    _persist(manager, row)
    return row


def _stamp(at=''):
    return at or datetime.now(timezone.utc).isoformat()


def _append_history(proof, event, by='', note='', at=''):
    history = json.loads(proof.history_json or '[]')
    history.append({'event': event, 'by': by, 'note': note,
                    'at': _stamp(at)})
    proof.history_json = json.dumps(history)


def _unit_key(vote):
    """The counted unit: the group when the vote is a stance, else
    the individual (the credibility precedent)."""
    group = getattr(vote, 'on_behalf_of_group', '')
    return group or f'individual:{getattr(vote, "voter", "")}'


# --------------------------------------------------------------- #
# 1. Proof lifecycle
# --------------------------------------------------------------- #

def _dependency_closure(manager, start_names, extra_edges=None):
    """(closure set, cycle_found). Walks depends_on edges with a
    visited/in-stack pair so a CRUDE-edited cycle is DETECTED, never
    an infinite walk. extra_edges maps a not-yet-created name to its
    dependency list."""
    proofs = _by_name(manager, 'TermProof')
    extra_edges = extra_edges or {}
    closure, in_stack = set(), set()
    cycle = [False]

    def visit(name):
        if name in in_stack:
            cycle[0] = True
            return
        if name in closure:
            return
        in_stack.add(name)
        closure.add(name)
        if name in extra_edges:
            deps = extra_edges[name]
        else:
            row = proofs.get(name)
            deps = (json.loads(row.depends_on_json or '[]')
                    if row is not None else [])
        for dep in deps:
            visit(dep)
        in_stack.discard(name)

    for name in start_names:
        visit(name)
    return closure, cycle[0]


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


def transition_proof(manager, name, to_status, by='', note='',
                     at=''):
    """Validated lifecycle move, history appended."""
    proof = _by_name(manager, 'TermProof').get(name)
    if proof is None:
        return {'ok': False, 'error': f"no TermProof named '{name}'",
                'knownProofs': sorted(_by_name(manager, 'TermProof'))}
    allowed = PROOF_TRANSITIONS.get(proof.status, ())
    if to_status not in allowed:
        return {'ok': False,
                'error': f"'{proof.status}' cannot move to "
                         f"'{to_status}'",
                'allowed': list(allowed)}
    previous = proof.status
    proof.status = to_status
    _append_history(proof, f'{previous}->{to_status}', by=by,
                    note=note, at=at)
    _persist(manager, proof)
    return {'ok': True, 'proof': name, 'from': previous,
            'to': to_status}


# --------------------------------------------------------------- #
# 2. Re-runnable demonstrations
# --------------------------------------------------------------- #

_OPERATIONS = ('mean', 'median', 'count-at-or-below',
               'share-at-or-below', 'difference', 'count')


def _resolve_inputs(manager, inputs, prior_results):
    """Value names -> pre_normalized_value; '$N' -> step N's
    recomputed result. Returns (values, missing)."""
    values_by_name = _by_name(manager, 'ContextualizedValue')
    resolved, missing = [], []
    for ref in inputs:
        if isinstance(ref, str) and ref.startswith('$'):
            index = int(ref[1:])
            prior = prior_results.get(index)
            if prior is None:
                missing.append(ref)
            elif isinstance(prior, list):
                resolved.extend(prior)
            else:
                resolved.append(prior)
            continue
        row = values_by_name.get(ref)
        if row is None or getattr(row, 'pre_normalized_value',
                                  None) is None:
            missing.append(ref)
        else:
            resolved.append(float(row.pre_normalized_value))
    return resolved, missing


def _apply_operation(operation, values, threshold=None):
    if operation == 'mean':
        return sum(values) / len(values)
    if operation == 'median':
        ordered = sorted(values)
        mid = len(ordered) // 2
        return (ordered[mid] if len(ordered) % 2
                else (ordered[mid - 1] + ordered[mid]) / 2)
    if operation == 'count':
        return float(len(values))
    if operation == 'count-at-or-below':
        return float(sum(1 for v in values if v <= threshold))
    if operation == 'share-at-or-below':
        return (sum(1 for v in values if v <= threshold)
                / len(values))
    if operation == 'difference':
        return values[0] - values[1]
    raise ValueError(f"unknown demonstration operation "
                     f"'{operation}' — supported: "
                     f'{", ".join(_OPERATIONS)}')


def _agrees(recomputed, recorded):
    if isinstance(recomputed, list) and isinstance(recorded, list):
        return (len(recomputed) == len(recorded)
                and all(_agrees(a, b)
                        for a, b in zip(recomputed, recorded)))
    try:
        a, b = float(recomputed), float(recorded)
    except (TypeError, ValueError):
        return recomputed == recorded
    return abs(a - b) <= RERUN_TOLERANCE * max(1.0, abs(a), abs(b))


def rerun_demonstration(manager, proof_name):
    """Re-execute the proof's reading/computation steps against LIVE
    ContextualizedValues and report agreement/divergence with the
    recorded results — the cross-validation idiom applied to
    arguments. Divergence is surfaced per step, never hidden."""
    proof = _by_name(manager, 'TermProof').get(proof_name)
    if proof is None:
        return {'ok': False,
                'error': f"no TermProof named '{proof_name}'",
                'knownProofs': sorted(_by_name(manager, 'TermProof'))}
    steps = json.loads(proof.demonstration_json or '[]')
    if not steps:
        return {'ok': False,
                'error': 'the proof records no demonstration steps',
                'suggestion': {'knob': 'demonstration_json',
                               'action': 'record the ordered '
                                         'reading/computation steps '
                                         'so the proof is '
                                         're-runnable'}}
    prior_results, report, divergences = {}, [], []
    for index, step in enumerate(steps):
        kind = step.get('kind', '')
        recorded = step.get('result')
        entry = {'index': index, 'kind': kind,
                 'description': step.get('description', ''),
                 'recorded': recorded}
        if kind == 'comparison':
            # Comparisons juxtapose prior results — nothing to
            # recompute; the recorded framing is echoed for voters.
            entry.update({'recomputed': recorded, 'agrees': True})
            report.append(entry)
            continue
        values, missing = _resolve_inputs(
            manager, step.get('inputs', []), prior_results)
        if missing or not values:
            entry.update({'recomputed': None, 'agrees': False,
                          'missingInputs': missing})
            divergences.append(
                f'step {index}: inputs missing/valueless '
                f'({missing})')
            report.append(entry)
            continue
        if kind == 'reading':
            recomputed = values if len(values) > 1 else values[0]
        elif kind == 'computation':
            try:
                recomputed = _apply_operation(
                    step.get('operation', ''), values,
                    threshold=step.get('threshold'))
            except (ValueError, ZeroDivisionError, IndexError) as exc:
                entry.update({'recomputed': None, 'agrees': False,
                              'error': str(exc)})
                divergences.append(f'step {index}: {exc}')
                report.append(entry)
                continue
        else:
            entry.update({'recomputed': None, 'agrees': False,
                          'error': f"unknown step kind '{kind}'"})
            divergences.append(f"step {index}: unknown kind "
                               f"'{kind}'")
            report.append(entry)
            continue
        prior_results[index] = recomputed
        agrees = _agrees(recomputed, recorded)
        entry.update({'recomputed': recomputed, 'agrees': agrees})
        if not agrees:
            divergences.append(
                f'step {index}: recomputed {recomputed!r} vs '
                f'recorded {recorded!r}')
        report.append(entry)
    return {'ok': True, 'proof': proof_name,
            'agreement': not divergences, 'steps': report,
            'divergences': divergences}


# --------------------------------------------------------------- #
# 3. Rebuttals
# --------------------------------------------------------------- #

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


def resolve_rebuttal(manager, name, to_status, by='', note='',
                     at=''):
    rebuttal = _by_name(manager, 'ProofRebuttal').get(name)
    if rebuttal is None:
        return {'ok': False,
                'error': f"no ProofRebuttal named '{name}'"}
    if to_status not in REBUTTAL_STATUSES or to_status == 'open':
        return {'ok': False,
                'error': f"a rebuttal resolves to one of "
                         f"{[s for s in REBUTTAL_STATUSES if s != 'open']}"}
    rebuttal.status = to_status
    rebuttal.notes = (rebuttal.notes + f'\n[{_stamp(at)}] {by}: '
                      f'{to_status} — {note}').strip()
    _persist(manager, rebuttal)
    open_left = [r.name for r in _rows(manager, 'ProofRebuttal')
                 if r.proof_name == rebuttal.proof_name
                 and r.status == 'open']
    return {'ok': True, 'rebuttal': name, 'status': to_status,
            'openRebuttalsRemaining': open_left,
            'note': ('the proof stays challenged until an explicit '
                     'transition — resolving rebuttals never '
                     'auto-flips it' if not open_left else '')}


def standing_rebuttals(manager, proof_name):
    return [r for r in _rows(manager, 'ProofRebuttal')
            if getattr(r, 'proof_name', '') == proof_name
            and getattr(r, 'status', '') == 'open']


# --------------------------------------------------------------- #
# 4. The manipulation catalog + computable exposure checks
# --------------------------------------------------------------- #

def _pattern(name, display, description, counter, check='',
             computability='partially-computable', notes=''):
    return {'name': name, 'display_name': display,
            'description': description,
            'counter_presentation': counter,
            'exposure_check': check, 'computability': computability,
            'proposed_by': 'seed (Dustin 2026-07-16 design pass)',
            'notes': notes}


_UNBUILT = ('check designed in the revamp plan, not yet '
            'implemented — computability is honest about that')

SEED_MANIPULATION_PATTERNS = [
    _pattern('aggregation-masking', 'Aggregation masking',
             'A summary statistic conceals a distribution feature — '
             'the canonical case: a national average of race '
             'competitiveness hiding that close to a majority of '
             'races are uncontested.',
             'Show the distribution beside the summary: the share '
             'of underlying values at/near zero.',
             check='scoring.term_proofs_basis:check_aggregation_masking',
             computability='computable'),
    _pattern('outlier-driven-mean', 'Outlier-driven mean',
             'A mean pulled by extreme values presented where the '
             'typical case is the question.',
             'Show the median beside the mean; report their '
             'divergence.',
             check='scoring.term_proofs_basis:check_outlier_driven_mean',
             computability='computable'),
    _pattern('stale-vintage', 'Stale vintage presented as current',
             "Values from an old timeframe presented against a "
             'score scoped to a newer one.',
             "Show each value's timeframe beside the score's "
             'declared timeframe.',
             check='scoring.term_proofs_basis:check_stale_vintage',
             computability='computable'),
    _pattern('cherry-picked-timeframe', 'Cherry-picked timeframe',
             'A window chosen so the claim holds; adjacent windows '
             'invert it.',
             'Window-sensitivity: recompute over adjacent windows.',
             notes=_UNBUILT),
    _pattern('cherry-picked-geography', 'Cherry-picked geography',
             'A subset of jurisdictions presented as the scope.',
             "Coverage vs the context's declared scope.",
             notes=_UNBUILT),
    _pattern('denominator-switching', 'Denominator switching',
             'Per-capita vs absolute chosen to flatter the claim.',
             'Show both denominators side by side.',
             notes=_UNBUILT),
    _pattern('simpsons-paradox-exploitation',
             "Simpson's-paradox exploitation",
             'An aggregate trend presented where every subgroup '
             'trend reverses it.',
             'Aggregate-vs-subgroup trend comparison.',
             notes=_UNBUILT),
    _pattern('threshold-gaming', 'Threshold gaming',
             "A generous definition (e.g. of 'competitive') doing "
             'the work of the claim.',
             'Threshold-sensitivity: recompute under adjacent '
             'definitions.',
             notes=_UNBUILT),
    _pattern('conflated-proxy', 'Conflated proxy',
             'The term measures X but is presented as Y.',
             'State what the term actually measures beside the '
             'presented framing.',
             computability='judgment-only',
             notes='semantic judgment — no arithmetic check can '
                   'decide what a term "really" measures'),
    _pattern('uncertainty-suppression', 'Uncertainty suppression',
             'Point estimates presented where the margin of error '
             'swamps the claimed difference.',
             'Show the claimed delta beside the margin of error.',
             notes=_UNBUILT + '; needs MOE fields on '
                   'ContextualizedValue (recorded model gap)'),
    _pattern('base-rate-neglect', 'Base-rate neglect',
             "A percent change presented without its absolute base "
             "('doubled' from 1 to 2).",
             'Show the absolute base beside the percent change.',
             notes=_UNBUILT),
    _pattern('cumulative-annual-conflation',
             'Cumulative/annual conflation',
             'A multi-period total framed as a per-period figure.',
             'State the period length beside the figure.',
             notes=_UNBUILT),
    _pattern('seasonal-gaming', 'Seasonal/calendar gaming',
             'Comparing seasonally mismatched periods.',
             'Same-period-prior-year comparison.',
             notes=_UNBUILT),
    _pattern('percent-vs-points', 'Percent vs percentage points',
             'A percentage-point change presented as a percent '
             'change (or vice versa).',
             'State both formulations explicitly.',
             notes=_UNBUILT),
    _pattern('composition-shift-masking',
             'Composition-shift masking',
             "A rate 'improves' only because the population mix "
             'changed.',
             'Decompose: within-group rates beside the mix shift.',
             notes=_UNBUILT),
    _pattern('survivorship-filtering', 'Survivorship filtering',
             'Entities that exited are dropped from the trend.',
             "Panel coverage vs the context's entity roster.",
             notes=_UNBUILT),
    _pattern('goalpost-redefinition', 'Goalpost redefinition',
             "The term's definition changed mid-series.",
             'Definition-version discontinuity beside the series.',
             notes=_UNBUILT + '; needs definition/methodology '
                   'versioning on values (recorded model gap)'),
    _pattern('correlation-as-causation',
             'Correlation presented as causation',
             'A correlational reading framed as a causal claim.',
             'State the correlational nature and known confounders.',
             computability='judgment-only',
             notes='assertable with rationale; no computation can '
                   'settle causation from these rows'),
]


def _values_of(manager, term_name, context_name=''):
    rows = [v for v in _rows(manager, 'ContextualizedValue')
            if getattr(v, 'term_name', '') == term_name
            and getattr(v, 'pre_normalized_value', None) is not None]
    if context_name:
        rows = [v for v in rows if context_name in json.loads(
            getattr(v, 'context_names_json', '[]') or '[]')]
    return rows


def check_aggregation_masking(manager, summary_term,
                              distribution_term, concept_name='',
                              near_zero=NEAR_ZERO):
    """The canonical check: a summary statistic vs the mass of
    underlying values it does not show. NEUTRAL arithmetic only —
    the verdict belongs to the proof votes."""
    summary_rows = _values_of(manager, summary_term)
    distribution_rows = _values_of(manager, distribution_term)
    if not summary_rows:
        return {'ok': False,
                'error': f"no values under summary term "
                         f"'{summary_term}'",
                'suggestion': {'knob': 'ContextualizedValue',
                               'action': 'ingest the summary value '
                                         'first'}}
    if not distribution_rows:
        return {'ok': False,
                'error': f"no values under distribution term "
                         f"'{distribution_term}'",
                'suggestion': {'knob': 'ContextualizedValue',
                               'action': 'ingest the finer-grained '
                                         'values the summary '
                                         'aggregates'}}
    summary_value = float(summary_rows[0].pre_normalized_value)
    values = [float(v.pre_normalized_value)
              for v in distribution_rows]
    concealed = sum(1 for v in values if v <= near_zero)
    share = concealed / len(values)
    return {'ok': True, 'pattern': 'aggregation-masking',
            'summaryTerm': summary_term,
            'summaryValue': summary_value,
            'distributionTerm': distribution_term,
            'distributionCount': len(values),
            'massAtOrBelow': {'threshold': near_zero,
                              'count': concealed,
                              'share': round(share, 4)},
            'finding': (f'the summary reads {summary_value}; '
                        f'{concealed} of {len(values)} underlying '
                        f'values sit at or below {near_zero} — '
                        f'mass the summary alone does not show')}


def check_outlier_driven_mean(manager, term_name, context_name=''):
    """Mean-vs-median divergence over a term's sibling values."""
    rows = _values_of(manager, term_name, context_name)
    if len(rows) < 2:
        return {'ok': False,
                'error': f"fewer than two values under "
                         f"'{term_name}'"
                         + (f" in context '{context_name}'"
                            if context_name else ''),
                'suggestion': {'knob': 'ContextualizedValue',
                               'action': 'a divergence needs '
                                         'sibling values to '
                                         'compare'}}
    values = [float(v.pre_normalized_value) for v in rows]
    mean = _apply_operation('mean', values)
    median = _apply_operation('median', values)
    divergence = mean - median
    relative = (abs(divergence) / abs(median)) if median else None
    return {'ok': True, 'pattern': 'outlier-driven-mean',
            'term': term_name, 'count': len(values),
            'mean': round(mean, 6), 'median': round(median, 6),
            'divergence': round(divergence, 6),
            'relativeDivergence': (round(relative, 4)
                                   if relative is not None else None),
            'finding': (f'the mean is {round(mean, 4)} and the '
                        f'median is {round(median, 4)} over '
                        f'{len(values)} values — they diverge by '
                        f'{round(divergence, 4)}')}


def check_stale_vintage(manager, term_name, concept_name):
    """Value timeframes vs the concept's declared timeframe scope."""
    concept = _by_name(manager, 'ScoreConcept').get(concept_name)
    if concept is None:
        return {'ok': False,
                'error': f"no ScoreConcept named '{concept_name}'"}
    contexts = _by_name(manager, 'ScoreContext')
    required = json.loads(
        getattr(concept, 'required_context_names_json', '[]')
        or '[]')
    required_timeframes = [
        n for n in required
        if getattr(contexts.get(n), 'context_type', '')
        == 'timeframe']
    if not required_timeframes:
        return {'ok': False,
                'error': f"concept '{concept_name}' declares no "
                         'timeframe context — there is no vintage '
                         'to compare against',
                'suggestion': {
                    'knob': 'ScoreConcept.'
                            'required_context_names_json',
                    'action': 'declare the timeframe the score is '
                              'scoped to'}}
    rows = _values_of(manager, term_name)
    if not rows:
        return {'ok': False,
                'error': f"no values under term '{term_name}'"}
    matching, mismatched = [], []
    for row in rows:
        row_contexts = json.loads(
            getattr(row, 'context_names_json', '[]') or '[]')
        row_timeframes = [
            n for n in row_contexts
            if getattr(contexts.get(n), 'context_type', '')
            == 'timeframe']
        if any(t in required_timeframes for t in row_timeframes):
            matching.append(row.name)
        else:
            mismatched.append({'value': row.name,
                               'valueTimeframes': row_timeframes})
    return {'ok': True, 'pattern': 'stale-vintage',
            'term': term_name, 'concept': concept_name,
            'declaredTimeframes': required_timeframes,
            'matchingValueCount': len(matching),
            'mismatchedValues': mismatched,
            'finding': (f'{len(mismatched)} of {len(rows)} values '
                        f'carry timeframes outside the declared '
                        f'{required_timeframes}')}


# --------------------------------------------------------------- #
# 5. Proof votes — validity and comprehension, never conflated
# --------------------------------------------------------------- #

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


def _latest_by_unit(votes):
    latest = {}
    for vote in sorted(votes,
                       key=lambda v: getattr(v, 'cast_at', '')):
        latest[_unit_key(vote)] = vote
    return latest


def proof_reading(manager, proof_name):
    """Validity tally + comprehension tally, reported SEPARATELY;
    standing rebuttals and dependency staleness surfaced. A reading,
    not a truth declaration."""
    proof = _by_name(manager, 'TermProof').get(proof_name)
    if proof is None:
        return {'ok': False,
                'error': f"no TermProof named '{proof_name}'",
                'knownProofs': sorted(_by_name(manager, 'TermProof'))}
    votes = [v for v in _rows(manager, 'ProofVote')
             if getattr(v, 'proof_name', '') == proof_name]

    validity_latest = _latest_by_unit(
        [v for v in votes if v.vote_kind == 'validity'])
    validity_units = len(validity_latest)
    if validity_units:
        weight_sum = sum(VALIDITY_WEIGHTS[v.choice]
                         for v in validity_latest.values())
        validity_score = round(weight_sum / (validity_units + 1), 4)
    else:
        validity_score = None
    validity = {
        'units': validity_units,
        'score': validity_score,
        'byChoice': {c: sum(1 for v in validity_latest.values()
                            if v.choice == c)
                     for c in VALIDITY_CHOICES},
        'smallSample': validity_units < SMALL_SAMPLE,
    }
    if validity_score is None:
        validity['suggestion'] = {
            'knob': 'cast_proof_vote',
            'action': "no validity votes yet — vote_kind 'validity'"}

    comprehension_latest = _latest_by_unit(
        [v for v in votes if v.vote_kind == 'comprehension'])
    comp_units = len(comprehension_latest)
    by_choice = {c: sum(1 for v in comprehension_latest.values()
                        if v.choice == c)
                 for c in COMPREHENSION_CHOICES}
    leaders = [c for c, n in by_choice.items()
               if n == max(by_choice.values())] if comp_units else []
    comprehension = {
        'units': comp_units,
        'byChoice': by_choice,
        'leaning': (leaders[0] if len(leaders) == 1 else None),
        'smallSample': comp_units < SMALL_SAMPLE,
    }
    if not comp_units:
        comprehension['suggestion'] = {
            'knob': 'cast_proof_vote',
            'action': 'no comprehension votes yet — show both '
                      "presentations and ask (vote_kind "
                      "'comprehension')"}

    dependencies = json.loads(proof.depends_on_json or '[]')
    proofs = _by_name(manager, 'TermProof')
    shaky = [
        {'proof': dep,
         'status': getattr(proofs.get(dep), 'status', 'missing')}
        for dep in dependencies
        if getattr(proofs.get(dep), 'status', 'missing')
        != 'accepted']
    return {
        'ok': True, 'proof': proof_name, 'kind': proof.proof_kind,
        'status': proof.status, 'claim': proof.claim,
        'validity': validity, 'comprehension': comprehension,
        'standingRebuttals': [
            {'name': r.name, 'kind': r.challenge_kind,
             'rationale': r.rationale}
            for r in standing_rebuttals(manager, proof_name)],
        'dependenciesNotAccepted': shaky,
        'reading': _READING_NOTE,
    }


# --------------------------------------------------------------- #
# 6. Acceptance / rejection — explicit acts, suggestions returned
# --------------------------------------------------------------- #

def _acceptance_suggestions(proof):
    kind = proof.proof_kind
    if kind == 'sufficiency':
        return [{'knob': 'cast_scope_vote / apply_scope_verdict',
                 'action': f"support '{proof.subject_term}' meeting "
                           f'the scope criteria for '
                           f"'{proof.for_concept_name}', citing "
                           f"proof '{proof.name}'"}]
    if kind == 'subset':
        return [{'knob': 'assert_term_relation',
                 'action': f"assert 'logical-subset' between "
                           f"'{proof.subject_term}' and "
                           f"'{proof.comparison_term}', citing "
                           f"proof '{proof.name}'"}]
    if kind == 'robustness':
        return [{'knob': 'open_term_election',
                 'action': f'a legitimacy election between '
                           f"'{proof.subject_term}' and "
                           f"'{proof.comparison_term}' can now cite "
                           f'an accepted robustness demonstration'}]
    return [{'knob': 'open_term_election',
             'action': f'a comprehension-informed election between '
                       f"'{proof.subject_term}' and "
                       f"'{proof.comparison_term}' — the "
                       f'comprehension tally shows which '
                       f'presentation people found more accurate'}]


def accept_proof(manager, proof_name, by='', note='', at=''):
    """Accept — per the proof's recorded context scope only. Returns
    what the proof BACKS as suggestions; nothing is auto-applied."""
    proof = _by_name(manager, 'TermProof').get(proof_name)
    if proof is None:
        return {'ok': False,
                'error': f"no TermProof named '{proof_name}'"}
    moved = transition_proof(manager, proof_name, 'accepted', by=by,
                             note=note, at=at)
    if not moved['ok']:
        return moved
    return {'ok': True, 'proof': proof_name, 'status': 'accepted',
            'acceptedForScope': json.loads(
                proof.context_scope_json or '[]'),
            'scopeNote': 'acceptance holds for the recorded context '
                         'scope only — a wider scope needs its own '
                         'proof',
            'suggestions': _acceptance_suggestions(proof)}


def reject_proof(manager, proof_name, by='', note='', at=''):
    moved = transition_proof(manager, proof_name, 'rejected', by=by,
                             note=note, at=at)
    if not moved['ok']:
        return moved
    return {'ok': True, 'proof': proof_name, 'status': 'rejected',
            'suggestion': {
                'knob': 'propagate_staleness',
                'action': f'flip proofs that depended on '
                          f"'{proof_name}' to stale — foundations "
                          f'changed'}}


def propagate_staleness(manager, proof_name, reason='', at=''):
    """Explicit act: every proof whose dependency closure contains
    proof_name flips to 'stale — foundation changed' (deep chains
    handled; cycles cannot hang the walk)."""
    proofs = _by_name(manager, 'TermProof')
    if proof_name not in proofs:
        return {'ok': False,
                'error': f"no TermProof named '{proof_name}'"}
    flipped = []
    for candidate in proofs.values():
        if candidate.name == proof_name:
            continue
        if candidate.status in ('rejected', 'stale'):
            continue
        closure, _ = _dependency_closure(manager, [candidate.name])
        if proof_name in closure - {candidate.name}:
            previous = candidate.status
            candidate.status = 'stale'
            _append_history(
                candidate, f'{previous}->stale', by='system',
                note=reason or (f'foundation changed: '
                                f"'{proof_name}' is "
                                f'{proofs[proof_name].status}'),
                at=at)
            _persist(manager, candidate)
            flipped.append(candidate.name)
    return {'ok': True, 'foundation': proof_name,
            'flippedToStale': sorted(flipped)}


# --------------------------------------------------------------- #
# 7. The seeded worked example (synthetic demo data, framed as such)
# --------------------------------------------------------------- #

DEMO_PROVENANCE = ('SYNTHETIC ILLUSTRATIVE DEMO DATA — the '
                   'uncontested-races worked example from the '
                   'revamp plan, not a real measurement')

#: 50 per-state demo competitiveness values: 24 uncontested (0.0),
#: 26 contested spread high — mean ≈ 0.55 while near a majority of
#: races are uncontested. Deterministic by construction.
DEMO_STATE_VALUES = ([0.0] * 24
                     + [round(0.85 + 0.008 * i, 3)
                        for i in range(26)])
DEMO_MEAN = round(sum(DEMO_STATE_VALUES) / len(DEMO_STATE_VALUES), 6)

SEED_TERM_PROOFS = [
    {
        'name': 'proof-uncontested-races-masking',
        'proof_kind': 'misleading-contextualization',
        'claim': 'Per-state uncontested-race share is more accurate '
                 'to the electoral-accountability context than the '
                 'national average of race competitiveness: the '
                 'average conceals that 24 of 50 races are '
                 'uncontested.',
        'subject_term': 'demo-uncontested-share-per-state',
        'comparison_term': 'demo-avg-race-competitiveness',
        'for_concept_name': 'demo-electoral-accountability',
        'context_scope_json': '["demo-usa-2026"]',
        'demonstration_json': json.dumps([
            {'kind': 'reading',
             'description': 'read the published national average',
             'inputs': ['demo-avg-race-competitiveness@usa-2026'],
             'result': DEMO_MEAN},
            {'kind': 'reading',
             'description': 'read all 50 per-state competitiveness '
                            'values',
             'inputs': [f'demo-race-competitiveness@state-{i:02d}'
                        for i in range(50)],
             'result': DEMO_STATE_VALUES},
            {'kind': 'computation',
             'description': 'count races at or below the '
                            'uncontested threshold',
             'inputs': ['$1'], 'operation': 'count-at-or-below',
             'threshold': NEAR_ZERO, 'result': 24.0},
            {'kind': 'computation',
             'description': 'the concealed share',
             'inputs': ['$1'], 'operation': 'share-at-or-below',
             'threshold': NEAR_ZERO, 'result': 0.48},
            {'kind': 'comparison',
             'description': 'side by side: the average reads '
                            f'{DEMO_MEAN}; 24 of 50 races (48%) are '
                            'uncontested — mass the average alone '
                            'does not show',
             'inputs': ['$0', '$3'],
             'result': 'the two presentations of the same data'},
        ]),
        'manipulation_pattern': 'aggregation-masking',
        'depends_on_json': '[]',
        'status': 'draft',
        'history_json': json.dumps([
            {'event': 'created', 'by': 'seed', 'note': DEMO_PROVENANCE,
             'at': '2026-07-16T00:00:00+00:00'}]),
        'proposed_by': 'seed (Dustin worked example)',
        'on_behalf_of_group': '',
        'notes': DEMO_PROVENANCE,
    },
]
