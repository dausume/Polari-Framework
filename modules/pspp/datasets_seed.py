"""
@module pspp.datasets_seed

Geopolymer book Ch.5 transcriptions as DigitizedDataset seed rows —
the operational form of /PSPP_DIGITIZED_DATASETS.json at the suite
root (the transcription record with the full qualitative-claims list).
Transcribed 2026-07-18 from Dustin's page photographs; exact book
citation TO CONFIRM before this module goes to a public repo.

Tables 5.4/5.5/5.6 are exact transcriptions (zero digitization error).
Fig 5.20's markers carry printed value labels (reliable), but the
shared concentration is unstated → relative reference curves only.
Fig 5.22 is points-empty (angled photo) with status
provisional-low-confidence — the engine refuses it until a re-shoot,
which is the honest behavior, not a gap.
"""

import json

_BOOK = 'Geopolymer book Ch.5'

SEED_DIGITIZED_DATASETS = [
    {
        'name': 'na-silicate-solution-polymerization',
        'source_reference': f'{_BOOK}, Table 5.4, p.101 '
                            '(after Engler 1974)',
        'status': 'ready',
        'independent_variables_json': '["MR"]',
        'dependent_variables_json':
            '["molecular_weight", "polymerization_n"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol Na2O',
            'molecular_weight': 'g/mol of (SiO2)n',
            'polymerization_n': 'dimensionless'}),
        'source_conditions_json': json.dumps({
            'system': 'Na-silicate aqueous solution (equilibrium)',
            'note': 'p.101: equilibrium develops per composition; '
                    'rapid rearrangement on dilution or extra alkali; '
                    'equilibrium reached more quickly at lower MR.'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [0.48, 3.30]}',
        'digitization_method': 'exact table transcription from photo',
        'digitization_error': '',
        'points_json': json.dumps([
            {'MR': 0.48, 'molecular_weight': 60, 'polymerization_n': 1},
            {'MR': 1.01, 'molecular_weight': 90,
             'polymerization_n': 1.5},
            {'MR': 1.69, 'molecular_weight': 120, 'polymerization_n': 2},
            {'MR': 2.09, 'molecular_weight': 160,
             'polymerization_n': 2.6},
            {'MR': 2.62, 'molecular_weight': 265,
             'polymerization_n': 4.4},
            {'MR': 3.30, 'molecular_weight': 320,
             'polymerization_n': 5.3},
        ]),
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
    {
        'name': 'k-silicate-solution-polymerization',
        'source_reference': f'{_BOOK}, Table 5.5, p.101 '
                            '(after Engler 1974)',
        'status': 'ready',
        'independent_variables_json': '["MR"]',
        'dependent_variables_json':
            '["molecular_weight", "polymerization_n"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol K2O',
            'molecular_weight': 'g/mol of (SiO2)n',
            'polymerization_n': 'dimensionless'}),
        'source_conditions_json': json.dumps({
            'system': 'K-silicate aqueous solution (equilibrium)',
            'note': 'Steep jump n=5.3 -> 14.1 between MR 3.62 and '
                    '3.97 — interpolation in that interval carries a '
                    'wide honest band; same Engler equilibrium caveats '
                    'as Table 5.4.'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [0.60, 3.97]}',
        'digitization_method': 'exact table transcription from photo',
        'digitization_error': '',
        'points_json': json.dumps([
            {'MR': 0.60, 'molecular_weight': 60, 'polymerization_n': 1},
            {'MR': 1.75, 'molecular_weight': 90,
             'polymerization_n': 1.5},
            {'MR': 2.50, 'molecular_weight': 120, 'polymerization_n': 2},
            {'MR': 2.80, 'molecular_weight': 160,
             'polymerization_n': 2.6},
            {'MR': 3.31, 'molecular_weight': 265,
             'polymerization_n': 4.4},
            {'MR': 3.62, 'molecular_weight': 320,
             'polymerization_n': 5.3},
            {'MR': 3.97, 'molecular_weight': 848,
             'polymerization_n': 14.1},
        ]),
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
    {
        'name': 'na-siloxonate-glass-to-solution-q',
        'source_reference': f'{_BOOK}, Table 5.6, p.103',
        'status': 'ready',
        'independent_variables_json': '["MR", "physical_state"]',
        'dependent_variables_json': '["Q0", "Q1", "Q2", "Q3", "Q4"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol Na2O',
            'Q0-Q4': 'percent of Si sites'}),
        'source_conditions_json': json.dumps({
            'system': 'Na-siloxonate: parent glass vs its dissolution '
                      'solution',
            'note': 'Fixed reference mappings at the listed MRs ONLY '
                    '(no general kinetic law in source). Fig 5.12 '
                    'caption caveat: liquid-state 29Si NMR Q4 can be '
                    'an equipment artifact — note Q4=7% for MR 3.28 '
                    'solution.',
            'sum_anomaly': 'AS PRINTED, two solution rows do not sum '
                           'to 100%: MR 1.0 solution = 92, MR 2.0 '
                           'solution = 110 (photo re-checked, digits '
                           'confirmed). Glass rows all sum to 100. '
                           'Either the book rounds/omits minor '
                           'species or the book itself has a typo — '
                           'verify against another copy before '
                           'normalizing; do NOT silently rescale.'}),
        'interpolation_policy': 'none',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [1.0, 3.28]}',
        'digitization_method': 'exact table transcription from photo',
        'digitization_error': '',
        'points_json': json.dumps([
            {'MR': 1.0, 'physical_state': 'glass',
             'Q0': 1, 'Q1': 14, 'Q2': 68, 'Q3': 17, 'Q4': 0},
            {'MR': 1.0, 'physical_state': 'solution',
             'Q0': 20, 'Q1': 31, 'Q2': 41, 'Q3': 0, 'Q4': 0},
            {'MR': 1.33, 'physical_state': 'glass',
             'Q0': 0, 'Q1': 2, 'Q2': 52, 'Q3': 46, 'Q4': 0},
            {'MR': 1.33, 'physical_state': 'solution',
             'Q0': 12, 'Q1': 25, 'Q2': 58, 'Q3': 6, 'Q4': 0},
            {'MR': 2.0, 'physical_state': 'glass',
             'Q0': 0, 'Q1': 0, 'Q2': 13, 'Q3': 75, 'Q4': 12},
            {'MR': 2.0, 'physical_state': 'solution',
             'Q0': 0, 'Q1': 25, 'Q2': 60, 'Q3': 25, 'Q4': 0},
            {'MR': 3.28, 'physical_state': 'glass',
             'Q0': 0, 'Q1': 0, 'Q2': 2, 'Q3': 55, 'Q4': 43},
            {'MR': 3.28, 'physical_state': 'solution',
             'Q0': 1, 'Q1': 7, 'Q2': 33, 'Q3': 53, 'Q4': 7},
        ]),
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
    {
        'name': 'silicate-solution-viscosity-vs-temperature',
        'source_reference': f'{_BOOK}, Figure 5.20, p.110',
        'status': 'ready',
        'independent_variables_json':
            '["temperature_C", "series"]',
        'dependent_variables_json': '["viscosity_cP"]',
        'units_json': json.dumps({
            'temperature_C': 'degC', 'viscosity_cP': 'cP (mPa.s)'}),
        'source_conditions_json': json.dumps({
            'series': {'na': 'Na-silicate MR=2',
                       'k': 'K-silicate MR=2.2'},
            'note': 'SAME concentration both series but the value is '
                    'NOT stated on the page — relative reference '
                    'curves, not absolute predictions. p.110: K '
                    'silicate viscosity ~10x lower than Na at same '
                    'MR.'}),
        'interpolation_policy': 'log-linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"temperature_C": [5, 30]}',
        'digitization_method': 'printed point-value labels read from '
                               'photo (each marker labeled) — not a '
                               'curve trace',
        'digitization_error': 'labels exact; temperatures from axis '
                              'gridlines, est. +/-1 degC',
        'points_json': json.dumps([
            {'series': 'Na-silicate MR=2', 'temperature_C': 5,
             'viscosity_cP': 5000},
            {'series': 'Na-silicate MR=2', 'temperature_C': 10,
             'viscosity_cP': 4500},
            {'series': 'Na-silicate MR=2', 'temperature_C': 15,
             'viscosity_cP': 3000},
            {'series': 'Na-silicate MR=2', 'temperature_C': 20,
             'viscosity_cP': 2000},
            {'series': 'Na-silicate MR=2', 'temperature_C': 25,
             'viscosity_cP': 1500},
            {'series': 'Na-silicate MR=2', 'temperature_C': 30,
             'viscosity_cP': 1000},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 5,
             'viscosity_cP': 420},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 10,
             'viscosity_cP': 400},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 15,
             'viscosity_cP': 270},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 20,
             'viscosity_cP': 200},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 25,
             'viscosity_cP': 160},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 30,
             'viscosity_cP': 120},
        ]),
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
    {
        'name': 'na-siloxonate-solubility-vs-temperature',
        'source_reference': f'{_BOOK}, Figure 5.22, p.112',
        'status': 'provisional-low-confidence',
        'independent_variables_json':
            '["temperature_C", "series"]',
        'dependent_variables_json': '["solubility_g_per_L"]',
        'units_json': json.dumps({
            'temperature_C': 'degC', 'solubility_g_per_L': 'g/liter'}),
        'source_conditions_json': json.dumps({
            'series': {'mr1': 'MR=1 Na-metasilicate pentahydrate',
                       'mr2': 'MR=2 Na-disilicate, 17% water',
                       'mr33': 'MR=3.3 Na-trisilicate, 17% water'}}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': json.dumps({
            'temperature_C': [10, 90],
            'solubility_g_per_L': [300, 900]}),
        'digitization_method': 'angled-photo curve read — axes and '
                               'shape reliable, point values NOT; '
                               'RE-SHOOT REQUESTED',
        'digitization_error': 'est. +/-50 g/L, +/-5 degC',
        'points_json': '[]',
        'qualitative_shape': 'All three series rise with temperature '
                             'over 10-90 degC within 300-900 g/L; '
                             'MR=1 and MR=2 lie well above MR=3.3 and '
                             'cross mid-range; MR=3.3 stays lowest. '
                             'Points intentionally absent pending '
                             're-digitization.',
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
]
