"""
@cross-cutting
@module scoring.scoring_seed
@tags @xc:bindings

Scoring seeds — two reference concepts:

1. 'labor-quality': the Democratic Political Scorecard's seeded Labor
   Quality model, verbatim (terms, weights, 2022 state data,
   normalization ranges from the scorecard's spreadsheet sample) —
   the PARITY PROOF that the generalized engine reproduces the
   original system's numbers.
2. 'demo-material-conductivity': the arbitrary-data demonstration —
   the SAME engine scoring materials, values pulled live through
   objectRef bindings into MaterialScaleDefinition rows (one resolves
   to a stored FEM result; one is honestly missing).

Idempotent-by-name, like every Polari seed.

@consumers
  - polariServer seed_pairs
@see /OVERLAP_MAP.md
"""

import json

_SCORECARD_PROV = ('political-scorecard-node labor-quality sample '
                   '(labor-quality-score-sample.ts / '
                   'LaborQualityDataInitializer) — 2022 state data, '
                   'spreadsheet normalization ranges')

SEED_SCORE_TERMS = [
    {
        'name': 'union-participation',
        'display_name': 'Union Participation',
        'description': 'Share of the state workforce in a union.',
        'category': 'labor', 'value_type': 'percentage', 'unit': '%',
        'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 0.0, 'max': 22.9}),
        'provenance_id': _SCORECARD_PROV,
    },
    {
        'name': 'labor-force-participation-rate',
        'display_name': 'Labor Force Participation Rate',
        'description': 'Share of working-age population in the labor '
                       'force.',
        'category': 'labor', 'value_type': 'percentage', 'unit': '%',
        'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 54.5, 'max': 70.1}),
        'provenance_id': _SCORECARD_PROV,
    },
    {
        'name': 'minimum-wage',
        'display_name': 'Minimum Wage',
        'description': 'State minimum wage compared to the federal '
                       'minimum.',
        'category': 'labor', 'value_type': 'currency', 'unit': '$/hr',
        'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 7.25, 'max': 17.50}),
        'provenance_id': _SCORECARD_PROV,
    },
    {
        'name': 'impoverished-workforce',
        'display_name': 'Impoverished Workforce',
        'description': 'Share of the workforce below the poverty line '
                       '— anti-competitive: lower is better, the '
                       'engine inverts at normalization.',
        'category': 'labor', 'value_type': 'percentage', 'unit': '%',
        'is_positive': False,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 5.0, 'max': 15.0}),
        'provenance_id': _SCORECARD_PROV,
    },
    {
        'name': 'thermal-conductivity-score',
        'display_name': 'Thermal Conductivity',
        'description': 'Effective thermal conductivity of the '
                       'material (demo: higher scores hotter-running '
                       'printable matrices).',
        'category': 'materials', 'value_type': 'rate', 'unit': 'W/m·K',
        'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 0.1, 'max': 1.0}),
        'provenance_id': 'demo — range spans the wax-composite band',
    },
]

_STATES = {
    'alabama': 'Alabama', 'california': 'California',
    'washington-dc': 'Washington DC', 'idaho': 'Idaho',
    'texas': 'Texas',
}

SEED_SCORE_CONTEXTS = [
    {
        'name': 'year-2022', 'display_name': '2022',
        'context_type': 'timeframe',
        'value_json': json.dumps(
            {'start': '2022-01-01', 'end': '2022-12-31'}),
    },
] + [
    {
        'name': f'state-{key}', 'display_name': label,
        'context_type': 'location',
        'value_json': json.dumps(
            {'granularity': 'state', 'state': label,
             'country': 'USA'}),
    }
    for key, label in _STATES.items()
]

SEED_SCORE_SUBJECTS = [
    {'name': key, 'display_name': label, 'kind': 'state',
     'description': f'{label} — labor-quality reference subject.'}
    for key, label in _STATES.items()
] + [
    {
        'name': 'beeswax-material', 'display_name': 'Beeswax',
        'kind': 'material',
        'object_ref_json': json.dumps(
            {'kind': 'objectRef',
             'className': 'MaterialsScienceMaterial',
             'name': 'beeswax'}),
        'description': 'Demo subject anchored to the live beeswax '
                       'identity.',
    },
    {
        'name': 'carnauba-material', 'display_name': 'Carnauba Wax',
        'kind': 'material',
        'object_ref_json': json.dumps(
            {'kind': 'objectRef',
             'className': 'MaterialsScienceMaterial',
             'name': 'carnauba-wax'}),
        'description': 'Demo subject whose conductivity value is '
                       'honestly missing (no executed L1 row).',
    },
]

#: 2022 raw state data, verbatim from the scorecard sample.
_STATE_DATA = {
    'alabama': {'union-participation': 5.1,
                'labor-force-participation-rate': 57.6,
                'minimum-wage': 7.25,
                'impoverished-workforce': 13.5},
    'california': {'union-participation': 16.4,
                   'labor-force-participation-rate': 62.7,
                   'minimum-wage': 16.00,
                   'impoverished-workforce': 8.9},
    'washington-dc': {'union-participation': 18.7,
                      'labor-force-participation-rate': 68.2,
                      'minimum-wage': 17.50,
                      'impoverished-workforce': 5.7},
    'idaho': {'union-participation': 22.9,
              'labor-force-participation-rate': 64.8,
              'minimum-wage': 7.25,
              'impoverished-workforce': 10.2},
    'texas': {'union-participation': 4.0,
              'labor-force-participation-rate': 63.2,
              'minimum-wage': 7.25,
              'impoverished-workforce': 12.8},
}

SEED_CONTEXTUALIZED_VALUES = [
    {
        'name': f'{term}@{state}-2022',
        'term_name': term,
        'subject_name': state,
        'context_names_json': json.dumps(
            [f'state-{state}', 'year-2022']),
        'pre_normalized_value': value,
        'source': 'scorecard 2022 sample data',
        'provenance_id': _SCORECARD_PROV,
    }
    for state, data in _STATE_DATA.items()
    for term, value in data.items()
] + [
    {
        # THE arbitrary-data seam, live: the raw value is the FEM
        # homogenization result persisted ON the wax-thermal-continuum
        # model row (msci-15: results live on the model).
        'name': 'thermal-conductivity@beeswax',
        'term_name': 'thermal-conductivity-score',
        'subject_name': 'beeswax-material',
        'context_names_json': '[]',
        'pre_normalized_value': None,
        'data_ref_json': json.dumps(
            {'kind': 'objectRef',
             'className': 'FEMModelDefinition',
             'name': 'wax-thermal-continuum',
             'path': 'last_result_json.effectiveK'}),
        'source': 'objectRef → wax-thermal-continuum FEM result '
                  '(resolved live at scoring time)',
        'provenance_id': 'msci FEM homogenization',
    },
    {
        # Honestly unresolvable until carnauba earns an executed L1
        # row — the score names the absence instead of guessing.
        'name': 'thermal-conductivity@carnauba',
        'term_name': 'thermal-conductivity-score',
        'subject_name': 'carnauba-material',
        'context_names_json': '[]',
        'pre_normalized_value': None,
        'data_ref_json': json.dumps(
            {'kind': 'objectRef',
             'className': 'MaterialScaleDefinition',
             'name': 'carnauba-wax@L1',
             'path': 'parameters_json.result.effectiveK'}),
        'source': 'objectRef → carnauba-wax@L1 (no such row yet — '
                  'absence is data)',
        'provenance_id': 'msci FEM homogenization (pending)',
    },
]

SEED_SCORE_CONCEPTS = [
    {
        'name': 'labor-quality',
        'display_name': 'Labor Quality',
        'description': 'The Democratic Political Scorecard reference '
                       'concept: union participation (w5) + labor '
                       'force participation (w2) + minimum wage (w8) '
                       '+ impoverished workforce (w6, inverted), '
                       'min-max normalized against the 2022 '
                       'spreadsheet ranges, weighted-mean, levelized '
                       'to the best state = 100.',
        'subject_kind': 'state',
        'term_weights_json': json.dumps([
            {'term': 'union-participation', 'weight': 5},
            {'term': 'labor-force-participation-rate', 'weight': 2},
            {'term': 'minimum-wage', 'weight': 8},
            {'term': 'impoverished-workforce', 'weight': 6},
        ]),
        'required_context_names_json': json.dumps(['year-2022']),
        'aggregation': 'weighted-mean',
        'levelize': True,
        'provenance_id': _SCORECARD_PROV,
    },
    {
        'name': 'demo-material-conductivity',
        'display_name': 'Material Conductivity (arbitrary-data demo)',
        'description': 'The same scoring engine over MATERIALS: '
                       'values resolve live through objectRef '
                       'bindings into MaterialScaleDefinition rows. '
                       'One subject scores from a real FEM result; '
                       'the other is honestly missing until its L1 '
                       'row is executed.',
        'subject_kind': 'material',
        'term_weights_json': json.dumps([
            {'term': 'thermal-conductivity-score', 'weight': 1},
        ]),
        'required_context_names_json': '[]',
        'aggregation': 'weighted-mean',
        'levelize': False,
        'provenance_id': 'demo',
    },
]
