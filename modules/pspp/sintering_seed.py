"""
@module pspp.sintering_seed

mtt-2 Part B: the sintering engine's calibration data as first-class
DigitizedDataset rows — provisional and REFUSING until real
densification curves are digitized (the pspp house rule: no invented
master curve, no invented activation energy). Each refusal names its
data ask, and the tech tree carries them as data gaps.

@consumers
  - polariServer.defClassList seeding (concatenated into the
    DigitizedDataset seeds)
"""

import json

_SINTER_PROVENANCE = ('mtt-2 sinter master-curve seed 2026-07-26 — '
                      'provisional; the MSC collapses real '
                      'densification runs, digitize to activate')

#: The Master Sintering Curve (Su & Johnson 1996): relative density vs
#: the log work-of-sintering, collapsed from >=2 heating-rate runs.
#: Points-empty + provisional -> the Θ->ρ mapping refuses until a real
#: curve is entered (alumina/zirconia are the textbook cases).
SEED_SINTERING_DATASETS = [
    {
        'name': 'alumina-densification-master-curve',
        'source_reference': 'Su & Johnson, "Master Sintering Curve" '
                            '(J. Am. Ceram. Soc. 1996) — alumina '
                            'densification; specific figure PENDING '
                            'digitization',
        'status': 'provisional-low-confidence',
        'independent_variables_json': '["log10Theta"]',
        'dependent_variables_json': '["relativeDensity"]',
        'units_json': json.dumps({
            'log10Theta': 'log10(s/K)',
            'relativeDensity': 'fraction of theoretical'}),
        'source_conditions_json': json.dumps({
            'system': 'alumina powder compact, pressureless sintering',
            'note': 'the MSC is material-specific and needs the fitted '
                    'apparent activation energy Q that collapses the '
                    'runs; both Q and the curve are the calibration'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{}',
        'digitization_method': 'NOT digitized — awaiting a straight-on '
                               'figure read',
        'points_json': '[]',
        'qualitative_shape':
            'A sigmoidal rise: relative density climbs from the green '
            'density (~0.5-0.6) through the intermediate stage and '
            'saturates near full density (~0.98-1.0) as log Θ '
            'increases. All heating-rate runs collapse onto this one '
            'curve when Q is chosen correctly — that collapse IS the '
            'calibration.',
        'notes': 'DATA ASK: digitize an alumina (or zirconia) '
                 'relative-density vs log Θ master curve AND record '
                 'its fitted activation energy Q — together they turn '
                 'the engine\'s Θ integral into a ρ prediction. Until '
                 'then relative_density() returns Θ and refuses ρ.',
    },
]

for _row in SEED_SINTERING_DATASETS:
    _row.setdefault('provenance_id', _SINTER_PROVENANCE)
