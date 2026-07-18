"""
@cross-cutting
@module scoring.media_accuracy
@tags @xc:bindings

Media accountability (scr-15) — Dustin 2026-07-08: "media
accountability for accuracy to data". Outlets are subjects whose
FACTUAL CLAIMS are checked against the ingested data: the engine
already knows what the number actually was (same context + time
matching scores use), so accuracy is COMPUTED, not voted.

FactualClaim: one checkable statement an outlet published — the
statement text plus its checkable payload (term, subject, contexts,
claimed value) and the article evidence. Logged by contributors
(attributed, like everything else).

AccuracyPolicy: editable bands over relative error (the
AgreementPolicy idiom) — what counts as 'accurate' is a SETTING.

check_claim: measured value resolved through resolve_value_over_time
→ relative error → band, both numbers + the measured value's
provenance in the answer. No data = 'unverifiable', an honest refusal
naming what's missing.

outlet_accuracy: the contributor-record idiom for outlets — band
distribution, mean relative error, per-term breakdown. scr-16 reads
this as source quality.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api / scoring.group_bias
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.agreement_policy import classify_max
from scoring.scoring_engine import resolve_value_over_time


class FactualClaim(treeObject):
    """One checkable factual statement published by an outlet."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('claim-ledger-texas-lfpr').
        name: str = '',
        display_name: str = '',
        # ScoreSubject (kind 'media-outlet') that published the claim.
        outlet_name: str = '',
        # The statement as published, verbatim.
        statement: str = '',
        # The checkable payload: which measurement the statement is
        # about, in the scoring vocabulary.
        term_name: str = '',
        subject_name: str = '',
        context_names_json: str = '[]',
        claimed_value: float = None,
        claim_date: str = '',
        # The article itself (MediaEvidence names, JSON list).
        evidence_names_json: str = '[]',
        # Contributor who logged the claim.
        contributed_by: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.outlet_name = outlet_name
        self.statement = statement
        self.term_name = term_name
        self.subject_name = subject_name
        self.context_names_json = context_names_json
        self.claimed_value = claimed_value
        self.claim_date = claim_date
        self.evidence_names_json = evidence_names_json
        self.contributed_by = contributed_by
        self.provenance_id = provenance_id
        self.notes = notes


class AccuracyPolicy(treeObject):
    """Editable accuracy bands over relative error."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Ordered JSON list of {'label', 'max'} over |claimed −
        # measured| / |measured| (classify_max semantics).
        error_bands_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.error_bands_json = error_bands_json
        self.notes = notes


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r for r in _rows(manager, class_name)}


def _parse(text, fallback):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def _error_bands(manager, policy_name):
    policies = _rows(manager, 'AccuracyPolicy')
    wanted = policy_name or 'default-accuracy'
    row = next((p for p in policies
                if getattr(p, 'name', '') == wanted),
               policies[0] if policies else None)
    if row is None:
        return [], None
    return _parse(getattr(row, 'error_bands_json', '[]'), '[]'), \
        getattr(row, 'name', '')


def check_claim(manager, claim_name, policy_name=''):
    """One claim against the data: the measured value resolves through
    the SAME engine path scores use; the verdict is a banded relative
    error with both numbers and the measurement's provenance. Missing
    data = 'unverifiable' with the engine's own refusal — absence is
    named, never silently skipped."""
    claim = _by_name(manager, 'FactualClaim').get(claim_name)
    if claim is None:
        return {'ok': False,
                'error': f"no FactualClaim named '{claim_name}'",
                'knownClaims': sorted(
                    _by_name(manager, 'FactualClaim'))}
    claimed = getattr(claim, 'claimed_value', None)
    if claimed is None or claimed == '':
        return {'ok': False,
                'error': 'claim has no claimed_value — nothing to '
                         'check',
                'suggestion': {'knob': 'FactualClaim.claimed_value',
                               'action': 'record the number the '
                                         'outlet actually published'}}
    claimed = float(claimed)

    base = {
        'ok': True,
        'claim': claim_name,
        'outlet': getattr(claim, 'outlet_name', ''),
        'statement': getattr(claim, 'statement', ''),
        'term': getattr(claim, 'term_name', ''),
        'subject': getattr(claim, 'subject_name', ''),
        'claimedValue': claimed,
    }
    terms = _by_name(manager, 'ScoreTerm')
    term = terms.get(getattr(claim, 'term_name', ''))
    if term is None:
        return {**base, 'verdict': 'unverifiable',
                'reason': f"no ScoreTerm named "
                          f"'{getattr(claim, 'term_name', '')}' — the "
                          'metric this claim is about is not in the '
                          'vocabulary',
                'suggestion': {'knob': 'ScoreTerm',
                               'action': 'create the term, ingest '
                                         'its data, re-check'}}
    contexts = _by_name(manager, 'ScoreContext')
    required = _parse(
        getattr(claim, 'context_names_json', '[]'), '[]')
    values = [v for v in _rows(manager, 'ContextualizedValue')
              if getattr(v, 'term_name', '')
              == getattr(claim, 'term_name', '')
              and getattr(v, 'subject_name', '')
              == getattr(claim, 'subject_name', '')]
    ok, measured, meta = resolve_value_over_time(
        manager, values, required, contexts, term,
        {'allowInterpolation': True, 'allowExtrapolation': False})
    if not ok:
        return {**base, 'verdict': 'unverifiable',
                'reason': (meta or {}).get('error', 'no data'),
                'suggestion': (meta or {}).get('suggestion') or {
                    'knob': 'POST /api/scoring/ingest',
                    'action': 'ingest the measurement this claim is '
                              'about, then re-check'}}

    if measured == 0:
        relative_error = abs(claimed - measured)
        error_basis = 'absolute (measured value is 0)'
    else:
        relative_error = abs(claimed - measured) / abs(measured)
        error_basis = 'relative'
    bands, policy = _error_bands(manager, policy_name)
    return {
        **base,
        'verdict': classify_max(relative_error, bands) if bands
        else 'unclassified',
        'measuredValue': measured,
        'relativeError': round(relative_error, 6),
        'errorBasis': error_basis,
        'measuredSource': {k: v for k, v in (meta or {}).items()
                           if k in ('source', 'valueRow', 'provenance',
                                    'derived', 'fromRows', 'coverage')},
        'accuracyPolicy': policy,
        'note': 'the measured value resolved through the same '
                'context+time matching scores use; the band reads '
                'the error, both numbers stay shown',
    }


def outlet_accuracy(manager, outlet_name, policy_name=''):
    """One outlet's accuracy record over its checked claims."""
    subjects = _by_name(manager, 'ScoreSubject')
    outlet = subjects.get(outlet_name)
    if outlet is None:
        return {'ok': False,
                'error': f"no ScoreSubject named '{outlet_name}'"}
    claims = [c for c in _rows(manager, 'FactualClaim')
              if getattr(c, 'outlet_name', '') == outlet_name]
    if not claims:
        return {'ok': False,
                'error': f"no FactualClaim rows for '{outlet_name}'",
                'suggestion': {
                    'knob': 'FactualClaim',
                    'action': 'log the checkable statements this '
                              'outlet published (statement + term/'
                              'subject/contexts/claimed value)'}}

    checks, verdicts, errors, per_term = [], {}, [], {}
    for c in claims:
        result = check_claim(manager, getattr(c, 'name', ''),
                             policy_name)
        verdict = result.get('verdict', 'unverifiable') \
            if result.get('ok') else 'unverifiable'
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        term = getattr(c, 'term_name', '')
        per_term.setdefault(term, {'claims': 0, 'errors': []})
        per_term[term]['claims'] += 1
        if result.get('relativeError') is not None:
            errors.append(result['relativeError'])
            per_term[term]['errors'].append(result['relativeError'])
        checks.append({
            'claim': getattr(c, 'name', ''),
            'statement': getattr(c, 'statement', ''),
            'verdict': verdict,
            'claimedValue': result.get('claimedValue'),
            'measuredValue': result.get('measuredValue'),
            'relativeError': result.get('relativeError'),
            'reason': result.get('reason'),
        })
    checked = len(errors)
    return {
        'ok': True,
        'outlet': outlet_name,
        'displayName': getattr(outlet, 'display_name', '')
        or outlet_name,
        'claimsTotal': len(claims),
        'checked': checked,
        'unverifiable': verdicts.get('unverifiable', 0),
        'verdicts': verdicts,
        'meanRelativeError': round(sum(errors) / checked, 6)
        if checked else None,
        'perTerm': {
            term: {'claims': d['claims'],
                   'meanRelativeError': round(
                       sum(d['errors']) / len(d['errors']), 6)
                   if d['errors'] else None}
            for term, d in per_term.items()},
        'checks': checks,
        'note': 'accuracy is computed against ingested data, not '
                'voted; unverifiable claims are counted and named — '
                'an outlet is not penalized for what the data '
                'cannot yet check',
    }


SEED_ACCURACY_POLICIES = [{
    'name': 'default-accuracy',
    'display_name': 'Default accuracy bands',
    'description': 'Relative-error bands for claim checking: ≤0.5% '
                   'exact · ≤5% accurate · ≤15% close · above = '
                   'wrong. Edit this row to recalibrate every outlet '
                   'record.',
    'error_bands_json': json.dumps([
        {'label': 'exact', 'max': 0.005},
        {'label': 'accurate', 'max': 0.05},
        {'label': 'close', 'max': 0.15},
        {'label': 'wrong', 'max': 1e9},
    ]),
}]

SEED_MEDIA_OUTLETS = [
    {
        'name': 'demo-daily-ledger',
        'display_name': 'The Daily Ledger (demo)',
        'kind': 'media-outlet',
        'description': 'Demo outlet with an accurate record — its '
                       'claims check out against the 2022 data.',
    },
    {
        'name': 'demo-signal-times',
        'display_name': 'The Signal Times (demo)',
        'kind': 'media-outlet',
        'description': 'Demo outlet with a wrong claim and an '
                       'unverifiable one — exercises the honest '
                       'bands.',
    },
]

SEED_FACTUAL_CLAIMS = [
    {
        'name': 'claim-ledger-texas-lfpr',
        'display_name': 'Ledger: Texas LFPR 63.2%',
        'outlet_name': 'demo-daily-ledger',
        'statement': 'Texas labor force participation held at 63.2 '
                     'percent across 2022.',
        'term_name': 'labor-force-participation-rate',
        'subject_name': 'texas',
        'context_names_json': json.dumps(['state-texas', 'year-2022']),
        'claimed_value': 63.2,
        'claim_date': '2023-01-15',
        'contributed_by': 'demo-citizen-jane',
        'provenance_id': 'scr-15 demo — checks exact',
    },
    {
        'name': 'claim-ledger-dc-wage',
        'display_name': 'Ledger: DC minimum wage $17',
        'outlet_name': 'demo-daily-ledger',
        'statement': 'The District minimum wage reached seventeen '
                     'dollars in 2022.',
        'term_name': 'minimum-wage',
        'subject_name': 'washington-dc',
        'context_names_json': json.dumps(
            ['state-washington-dc', 'year-2022']),
        'claimed_value': 17.00,
        'claim_date': '2023-02-01',
        'contributed_by': 'demo-citizen-jane',
        'provenance_id': 'scr-15 demo — 17.00 vs 17.50 ≈ 2.9%, '
                         "'accurate'",
    },
    {
        'name': 'claim-signal-dc-union',
        'display_name': 'Signal: DC union participation 25%',
        'outlet_name': 'demo-signal-times',
        'statement': 'A quarter of the District workforce is now '
                     'unionized.',
        'term_name': 'union-participation',
        'subject_name': 'washington-dc',
        'context_names_json': json.dumps(
            ['state-washington-dc', 'year-2022']),
        'claimed_value': 25.0,
        'claim_date': '2023-03-10',
        'contributed_by': 'demo-research-group',
        'provenance_id': 'scr-15 demo — 25 vs 18.7 ≈ 34%, '
                         "'wrong'",
    },
    {
        'name': 'claim-signal-childcare',
        'display_name': 'Signal: childcare costs claim',
        'outlet_name': 'demo-signal-times',
        'statement': 'California childcare costs rose 12 percent.',
        'term_name': 'childcare-cost-index',
        'subject_name': 'california',
        'context_names_json': json.dumps(
            ['state-california', 'year-2022']),
        'claimed_value': 12.0,
        'claim_date': '2023-03-20',
        'contributed_by': 'demo-research-group',
        'provenance_id': 'scr-15 demo — no such term yet: '
                         "'unverifiable', honestly",
    },
]
