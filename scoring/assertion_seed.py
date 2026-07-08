"""
@cross-cutting
@module scoring.assertion_seed
@tags @xc:bindings

scr-5 seeds — one complete policy-accountability story over the
labor-quality reference concept:

  policy-fair-wage-act (the scored policy)
    ├─ confirmed supports on minimum-wage      (official-record proof)
    ├─ confirmed harms on union-participation  (news proof; validity
    │    voting shows round 1 divisive → round 2 consensus)
    ├─ confirmed dependency on policy-labor-standards-2020
    ├─ confirmed decorative preamble           (excluded by assertion)
    ├─ asserted (unconfirmed) supports on impoverished-workforce
    │    — visible, never counted
    └─ UNBOUND generic intent — the abstraction-suggestion demo

Contributors: a pseudonymous individual, a disclosed lobby, a research
org — each with a computable track record.

Idempotent-by-name, like every Polari seed.

@consumers
  - polariServer seed_pairs
@see /OVERLAP_MAP.md
"""

import json

SEED_POLICY_SUBJECTS = [
    {
        'name': 'policy-fair-wage-act',
        'display_name': 'Fair Wage Act (demo)',
        'kind': 'policy',
        'description': 'Demo policy: raises the state minimum wage '
                       'to $15, phases small-business exemptions from '
                       'collective bargaining rules, funds workforce '
                       'poverty-reduction programs. Extends the 2020 '
                       'Labor Standards Act.',
    },
    {
        'name': 'policy-labor-standards-2020',
        'display_name': 'Labor Standards Act 2020 (demo)',
        'kind': 'policy',
        'description': 'Demo predecessor policy the Fair Wage Act '
                       'depends on — its score carries over through '
                       'the dependency assertion.',
    },
]

SEED_MEDIA_EVIDENCE = [
    {
        'name': 'evidence-fair-wage-hearing-record',
        'display_name': 'Fair Wage Act — committee hearing record',
        'kind': 'official-record',
        'url': 'https://example.org/hearings/fair-wage-act',
        'quote': 'Section 2 raises the hourly minimum to $15 '
                 'effective January 1.',
        'captured_date': '2024-03-12',
        'evidence_grade': 'official-record',
        'submitted_by': 'demo-labor-lobby',
        'provenance_id': 'demo committee record',
    },
    {
        'name': 'evidence-fair-wage-news',
        'display_name': 'Fair Wage Act — news analysis',
        'kind': 'article',
        'url': 'https://example.org/news/fair-wage-analysis',
        'quote': 'Analysts warn the small-business exemption in '
                 'Section 7 weakens collective bargaining coverage.',
        'captured_date': '2024-03-20',
        'evidence_grade': 'contemporaneous-report',
        'submitted_by': 'demo-citizen-jane',
        'outlet_name': 'demo-signal-times',
        'provenance_id': 'demo news article',
    },
    {
        'name': 'evidence-labor-standards-record',
        'display_name': 'Labor Standards Act 2020 — enrolled text',
        'kind': 'official-record',
        'url': 'https://example.org/laws/labor-standards-2020',
        'quote': 'Employers shall post schedules fourteen days in '
                 'advance.',
        'captured_date': '2020-06-01',
        'evidence_grade': 'official-record',
        'submitted_by': 'demo-research-group',
        'provenance_id': 'demo enrolled text',
    },
]

SEED_SCORE_ASSERTIONS = [
    {
        'name': 'assert-fair-wage-min-wage',
        'display_name': 'Section 2 raises the minimum wage',
        'subject_name': 'policy-fair-wage-act',
        'span_json': json.dumps(
            {'start': 41, 'end': 78,
             'quote': 'raises the state minimum wage to $15'}),
        'intent': 'raises the minimum wage for hourly workers',
        'assertion_type': 'score-impact',
        'direction': 'supports',
        'strength': 0.9,
        'term_name': 'minimum-wage',
        'evidence_names_json': json.dumps(
            ['evidence-fair-wage-hearing-record',
             'evidence-fair-wage-news']),
        'asserted_by': 'demo-labor-lobby',
        'status': 'confirmed',
        'status_history_json': json.dumps([
            {'from': 'asserted', 'to': 'confirmed',
             'by': 'demo-research-group',
             'note': 'uncontested — the text is explicit',
             'at': '2024-04-01T00:00:00+00:00'}]),
        'provenance_id': 'scr-5 demo',
    },
    {
        'name': 'assert-fair-wage-union-harm',
        'display_name': 'Section 7 exemption weakens bargaining',
        'subject_name': 'policy-fair-wage-act',
        'span_json': json.dumps(
            {'start': 84, 'end': 152,
             'quote': 'phases small-business exemptions from '
                      'collective bargaining rules'}),
        'intent': 'weakens union coverage in small firms',
        'assertion_type': 'score-impact',
        'direction': 'harms',
        'strength': 0.4,
        'term_name': 'union-participation',
        'evidence_names_json': json.dumps(['evidence-fair-wage-news']),
        'asserted_by': 'demo-citizen-jane',
        'status': 'confirmed',
        'status_history_json': json.dumps([
            {'from': 'asserted', 'to': 'under-review',
             'by': 'demo-labor-lobby',
             'note': 'disputed reading of Section 7',
             'at': '2024-04-02T00:00:00+00:00'},
            {'from': 'under-review', 'to': 'confirmed',
             'by': 'demo-research-group',
             'note': 'round 2 consensus among decisive voters',
             'at': '2024-04-10T00:00:00+00:00'}]),
        'provenance_id': 'scr-5 demo',
    },
    {
        'name': 'assert-fair-wage-dependency',
        'display_name': 'Extends the 2020 Labor Standards Act',
        'subject_name': 'policy-fair-wage-act',
        'span_json': json.dumps(
            {'start': 195, 'end': 232,
             'quote': 'Extends the 2020 Labor Standards Act'}),
        'intent': 'carries over labor standards protections',
        'assertion_type': 'dependency',
        'direction': 'supports',
        'strength': 0.5,
        'depends_on_subject': 'policy-labor-standards-2020',
        'evidence_names_json': json.dumps(
            ['evidence-fair-wage-hearing-record']),
        'asserted_by': 'demo-research-group',
        'status': 'confirmed',
        'provenance_id': 'scr-5 demo',
    },
    {
        'name': 'assert-fair-wage-preamble',
        'display_name': 'Preamble carries no score weight',
        'subject_name': 'policy-fair-wage-act',
        'span_json': json.dumps(
            {'start': 0, 'end': 40,
             'quote': 'Whereas the dignity of work sustains the '
                      'commonwealth…'}),
        'intent': 'decorative preamble',
        'assertion_type': 'decorative',
        'asserted_by': 'demo-citizen-jane',
        'status': 'confirmed',
        'provenance_id': 'scr-5 demo',
    },
    {
        'name': 'assert-fair-wage-poverty',
        'display_name': 'Funds poverty-reduction programs',
        'subject_name': 'policy-fair-wage-act',
        'span_json': json.dumps(
            {'start': 153, 'end': 194,
             'quote': 'funds workforce poverty-reduction programs'}),
        'intent': 'reduces working poverty',
        'assertion_type': 'score-impact',
        'direction': 'supports',
        'strength': 0.7,
        'term_name': 'impoverished-workforce',
        'evidence_names_json': '[]',
        'asserted_by': 'demo-labor-lobby',
        'status': 'asserted',
        'provenance_id': 'scr-5 demo — deliberately unconfirmed: '
                         'visible in the excluded list, never counted',
    },
    {
        'name': 'assert-fair-wage-generic',
        'display_name': 'Generic intent (unbound — suggestion demo)',
        'subject_name': 'policy-fair-wage-act',
        'intent': 'improves wages and labor conditions for hourly '
                  'workers',
        'assertion_type': 'score-impact',
        'direction': 'supports',
        'strength': 0.5,
        'asserted_by': 'demo-citizen-jane',
        'status': 'asserted',
        'provenance_id': 'scr-5 demo — run /suggestions to see '
                         'abstraction matching rank candidate '
                         'terms/concepts',
    },
    {
        'name': 'assert-labor-standards-lfpr',
        'display_name': 'Scheduling rules support participation',
        'subject_name': 'policy-labor-standards-2020',
        'span_json': json.dumps(
            {'start': 0, 'end': 60,
             'quote': 'Employers shall post schedules fourteen days '
                      'in advance'}),
        'intent': 'stable scheduling supports labor force '
                  'participation',
        'assertion_type': 'score-impact',
        'direction': 'supports',
        'strength': 0.6,
        'term_name': 'labor-force-participation-rate',
        'evidence_names_json': json.dumps(
            ['evidence-labor-standards-record']),
        'asserted_by': 'demo-research-group',
        'status': 'confirmed',
        'provenance_id': 'scr-5 demo',
    },
]

SEED_VALIDITY_VOTES = [
    # Round 1 on the disputed union-harm assertion: an exact tie —
    # divisive, the tally suggests another round.
    {
        'name': 'vote-union-harm-r1-jane',
        'assertion_name': 'assert-fair-wage-union-harm',
        'voter': 'demo-citizen-jane', 'round_number': 1,
        'vote': 'valid',
        'rationale': 'Section 7 text plainly narrows coverage.',
        'cast_date': '2024-04-03',
    },
    {
        'name': 'vote-union-harm-r1-lobby',
        'assertion_name': 'assert-fair-wage-union-harm',
        'voter': 'demo-labor-lobby', 'round_number': 1,
        'vote': 'invalid',
        'rationale': 'The exemption is temporary during phase-in.',
        'cast_date': '2024-04-03',
    },
    # Round 2: consensus among decisive voters; the lobby abstains
    # (participation gap, surfaced not hidden).
    {
        'name': 'vote-union-harm-r2-jane',
        'assertion_name': 'assert-fair-wage-union-harm',
        'voter': 'demo-citizen-jane', 'round_number': 2,
        'vote': 'valid',
        'rationale': 'Phase-in has no sunset clause.',
        'cast_date': '2024-04-09',
    },
    {
        'name': 'vote-union-harm-r2-research',
        'assertion_name': 'assert-fair-wage-union-harm',
        'voter': 'demo-research-group', 'round_number': 2,
        'vote': 'valid',
        'rationale': 'Comparable exemptions reduced coverage 3-5% in '
                     'peer states.',
        'evidence_names_json': json.dumps(
            ['evidence-labor-standards-record']),
        'cast_date': '2024-04-09',
    },
    {
        'name': 'vote-union-harm-r2-lobby',
        'assertion_name': 'assert-fair-wage-union-harm',
        'voter': 'demo-labor-lobby', 'round_number': 2,
        'vote': 'abstain',
        'rationale': 'No position after the sunset review.',
        'cast_date': '2024-04-09',
    },
]
