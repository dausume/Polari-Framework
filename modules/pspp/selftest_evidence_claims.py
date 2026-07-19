"""
Self-test for pspp-1 evidence + claims: the unified EvidenceMethod
vocabulary (superset contract with materialsScience DERIVATION_METHODS)
and claim validation/round-trip.

Run from polari-framework/:
    python3 -m pspp.selftest_evidence_claims
"""

import sys
from types import SimpleNamespace

from materialsScience.materials_basis import DERIVATION_METHODS
from pspp.evidence_methods import (
    EVIDENCE_METHOD_VOCAB, SEED_EVIDENCE_METHODS, evidence_identifiers,
    legacy_methods_covered, validate_evidence_method,
)
from pspp.claims import (
    canonical_subject, claim_summary, claims_for_subject, validate_claim,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_vocabulary():
    print('[evidence vocabulary]')
    check('every legacy DERIVATION_METHODS identifier is covered '
          '(unification contract)', legacy_methods_covered())
    check('new kinds present (estimated/interpolated/ml-prediction/'
          'unknown)', all(m in EVIDENCE_METHOD_VOCAB for m in
                          ('estimated', 'interpolated', 'ml-prediction',
                           'unknown')))
    check('every entry has category + description', all(
        e.get('category') and e.get('description')
        for e in EVIDENCE_METHOD_VOCAB.values()))
    check('seed rows mirror the vocabulary 1:1',
          sorted(r['name'] for r in SEED_EVIDENCE_METHODS)
          == evidence_identifiers())
    check("'unknown' does not pretend uncertainty is meaningful",
          EVIDENCE_METHOD_VOCAB['unknown'].get(
              'supports_uncertainty') is False)
    check('valid identifier verdict ok',
          validate_evidence_method('measured')['ok'])
    bad = validate_evidence_method('vibes')
    check('unknown identifier refused, suggestion names the vocabulary',
          bad['ok'] is False and 'measured' in bad['suggestion'])


def test_claims():
    print('[claims]')
    check("canonical subject is '<material>#as-defined' (invariant I1)",
          canonical_subject('beeswax') == 'beeswax#as-defined')

    good = {
        'name': 'beeswax#as-defined:thermalConductivity@L0',
        'subject_state_key': 'beeswax#as-defined',
        'evidence_method': 'literature',
        'provenance_id': 'Base Wax Properties notes',
    }
    check('literature claim with provenance validates',
          validate_claim(good)['ok'])

    noSubject = dict(good, subject_state_key='')
    check('claim without a subject state refused',
          validate_claim(noSubject)['ok'] is False)

    noProv = dict(good, provenance_id='', source_execution_id='')
    v = validate_claim(noProv)
    check('provenance-less claim refused naming required_provenance',
          v['ok'] is False and 'required_provenance' in v['refusal'])

    badMethod = dict(good, evidence_method='vibes')
    check('claim with unknown evidence method refused',
          validate_claim(badMethod)['ok'] is False)

    row = SimpleNamespace(
        name='beeswax#as-defined:thermalConductivity@L0',
        subject_state_key='beeswax#as-defined',
        property_meaning_name='thermalConductivity',
        scale_level=0, value=0.25, value_json='', units='W/m·K',
        evidence_method='literature',
        assumptions_json='["solid phase, room temperature"]',
        validity_json='{"temperatureC": [20, 40]}',
        source_execution_id='', confidence_json='',
        provenance_id='Base Wax Properties notes', notes='')
    summary = claim_summary(row)
    check('summary round-trips value + evidence + assumptions',
          summary['value'] == 0.25
          and summary['evidenceMethod'] == 'literature'
          and summary['assumptions'] == ['solid phase, room temperature']
          and summary['validity'] == {'temperatureC': [20, 40]})

    manager = SimpleNamespace(objectTables={'PropertyClaim': {
        row.name: row,
        'other': SimpleNamespace(
            name='other', subject_state_key='carnauba-wax#as-defined',
            property_meaning_name='shoreHardness', scale_level=0,
            value=80.0, value_json='', units='Shore A',
            evidence_method='estimated', assumptions_json='[]',
            validity_json='{}', source_execution_id='',
            confidence_json='', provenance_id='worksheet', notes=''),
    }})
    mine = claims_for_subject(manager, 'beeswax#as-defined')
    check('claims_for_subject filters to the one state',
          len(mine) == 1
          and mine[0]['property'] == 'thermalConductivity')


def main():
    test_vocabulary()
    test_claims()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
