"""@module pspp.objects.benchmark_cases._shared — what the benchmark_cases row classes share (constants, seeds, helpers); split from benchmark_cases_basis.py (sap-2c)."""
from pspp.custom.progress_engine import cure_progress
from pspp.threshold_windows_basis import grade_composition_merged
import json
from pspp.custom.network_stepping import reachable_frameworks

_BM_PROVENANCE = ('pspp-V3 benchmark transcription '
                  '(PSPP_DIGITIZED_DATASETS.json benchmark_cases, '
                  '2026-07-19)')
SEED_BENCHMARK_CASES = [
    {
        'name': 'mk750-na-pss-mr182',
        'source_reference': 'Davidovits pp.183-185 (§8.4-8.5) + '
                            'Table 8.7 p.186',
        'inputs_json': json.dumps({
            'precursor': 'metakaolin MK-750 (Si:Al=1)',
            'activator': 'Na-silicate solution MR=1.82',
            'oxide_ratios': {'Na2O/SiO2': 0.28, 'SiO2/Al2O3': 4.02,
                             'H2O/Na2O': 17.2, 'Na2O/Al2O3': 1.1},
            'printed_formula': '1.1Na2O:4SiO2:Al2O3:17H2O, Si:Al=2, '
                               'Na-poly(sialate-siloxo)',
            'as_printed_discrepancy':
                'formula implies H2O/Na2O = 15.45 but the ratio list '
                'prints 17.20 — both kept, never reconciled silently',
            'slurry_viscosity': 'resin-like, 100-200 centipoise '
                                '(p.184)'}),
        'observed_outcomes_json': json.dumps({
            'ph_evolution': 'drastic drop pH 10.5-11 → ~7.5 neutral '
                            '(Zoulgami 2002, p.185)',
            'phases_after_750C':
                'nepheline (Si:Al=1) + albite (Si:Al=3) coexisting '
                '~50/50; bulk NaAlSi2O6 (Si:Al=2); nano-scale solid '
                'solution; XRD-crystalline only after >500C',
            'global_formula': 'Na4.54Al4.5Si9.04O27.11 ~ NaAlSi2O6',
            'duxson_2005a': 'above 500C nepheline + a not-well-'
                            'defined component instead of albite',
            'favier_2013_two_step':
                'step 1 (<15 min): Si:Al 2-3 at grain boundaries, '
                'solution still Q0-Q3; step 2: hardening, Si:Al=1 '
                'chemistry with only NaOH, no siloxonates'}),
        'window_family': 'na-k-pss',
        'cation': 'Na',
        'mr': 1.82,
        'observed_frameworks_json': json.dumps(
            ['framework-nepheline', 'framework-albite']),
        'measured_datasets_json': '[]',
        'use': 'The first PSPP validation case: ratios inside all '
               'four Table A windows; framework branching per the '
               'pp.184-189 mechanism.',
    },
    {
        'name': 'mk750-na-silicate-mr170-curing-series',
        'source_reference': 'Davidovits pp.177-179 (Fig 8.18)',
        'inputs_json': json.dumps({
            'recipe': 'Na-silicate MR=1.70 100g + MK-750 63.47g '
                      '(Na:Al=1), no mineral fillers',
            'procedure': 'planetary blender 300 RPM 10 min at 20C; '
                         'cast cylinders; oven 80C 15-20 min after '
                         'mixing start; covered during setting; '
                         'strength measured immediately after hot '
                         'demolding, no drying',
            'reactivity_reference': 'commercial MK-750 + Na-silicate: '
                                    'exotherm peak 35 min, hardening '
                                    'complete 60 min'}),
        'observed_outcomes_json': json.dumps({
            'strength_series': '2.83@1h → 5.66@2h → 6.80@4h, DIP '
                               '4.26@8h, plateau 6.90@20h (MPa)',
            'ph_mirror': 'pH anticorrelates with strength; dip = '
                         'alkaline depolymerization then '
                         're-polymerization; free water sustains the '
                         'equilibrium — drying stops it'}),
        'window_family': '',
        'cation': 'Na',
        'mr': 1.70,
        'observed_frameworks_json': '[]',
        'measured_datasets_json': json.dumps(
            ['mk750-strength-ph-vs-curing-time']),
        'use': 'Curing-kinetics benchmark: measured strength/pH '
               'series beside the (correctly refusing) predictors.',
    },
    {
        'name': 'mk750-k-silicate-kalsilite-mixture',
        'source_reference': 'Davidovits p.193 §8.6.1',
        'inputs_json': json.dumps({
            'recipe': 'MK-750 + K-silicate solution MR=1.80; solid '
                      'solution of K-PS (kaliophilite/kalsilite '
                      'type) + K-polysilicate; low-molecular '
                      'K-polysilicate neutralized with 4.9% Ca(OH)2 '
                      '(Dan Perera & Trautman 2005/2006)',
            'oxide_ratios': {'K2O/SiO2': 0.36, 'SiO2/Al2O3': 4.12,
                             'H2O/Al2O3': 16, 'K2O/Al2O3': 1.51}}),
        'observed_outcomes_json': json.dumps({
            'windows': 'sits inside ALL Table C claimed ranges AND '
                       'inside the p.193 preferred bands',
            'thermal_evolution': 'dataset k-geopolymer-porosity-'
                                 'phases-vs-temperature (Table 8.8)'}),
        'window_family': 'k-ps-kaliophilite',
        'cation': 'K',
        'mr': 1.80,
        'observed_frameworks_json': json.dumps(
            ['framework-kalsilite']),
        'measured_datasets_json': json.dumps(
            ['k-geopolymer-porosity-phases-vs-temperature']),
        'use': 'K-family window validation (the banded p.193 rows '
               'grade it ideal) + thermal phase-evolution benchmark.',
    },
]
for _row in SEED_BENCHMARK_CASES:
    _row.setdefault('provenance_id', _BM_PROVENANCE)
def _get(row, key, default=''):
    return row.get(key, default) if isinstance(row, dict) \
        else getattr(row, key, default)
def _loads(row, key, fallback):
    raw = _get(row, key, fallback) or fallback
    try:
        return raw if not isinstance(raw, str) else json.loads(raw)
    except Exception:
        return json.loads(fallback)
def _normalized_ratios(inputs):
    """As-printed alkali-specific ratio keys (Na2O/*, K2O/*, */Na2O)
    normalized to the window descriptors' M2O convention."""
    out = {}
    for key, value in (inputs.get('oxide_ratios') or {}).items():
        out[key.replace('Na2O', 'M2O').replace('K2O', 'M2O')] = value
    return out
def qualitative_inventory(cation):
    """What a MK-750 + (cation)-waterglass mix PRESENTS (amounts None
    — benchmarks state what was mixed, not Q percentages)."""
    ion = 'sodium-ion' if cation == 'Na' else 'potassium-ion'
    return {name: None for name in (
        'water', 'hydroxide-ion', ion, 'metakaolin-layer',
        'di-siloxonate', 'siloxonate-q1', 'siloxonate-q2')}
def benchmark_overlay(manager, case, windows=None, banded=None,
                      rules=None):
    """One case's measured-vs-predicted sections."""
    from pspp.custom.pspp_views import _seed_or_rows
    from pspp.reaction_windows_basis import SEED_REACTION_WINDOWS
    from pspp.threshold_windows_basis import SEED_THRESHOLD_WINDOWS
    from pspp.reaction_network_basis import SEED_REACTION_RULES

    inputs = _loads(case, 'inputs_json', '{}')
    observed = _loads(case, 'observed_outcomes_json', '{}')
    sections = []

    # 1. window grading — a real prediction with a real verdict.
    family = _get(case, 'window_family')
    ratios = _normalized_ratios(inputs)
    if family and ratios:
        grading = grade_composition_merged(
            windows if windows is not None else _seed_or_rows(
                manager, 'ReactionWindow', SEED_REACTION_WINDOWS),
            banded if banded is not None else _seed_or_rows(
                manager, 'ThresholdReactionWindow',
                SEED_THRESHOLD_WINDOWS),
            ratios, family)
        ok = grading.get('ok')
        sections.append({
            'aspect': 'windows',
            'measured': observed.get('windows',
                                     'case formed the product as '
                                     'printed'),
            'predicted': grading,
            'verdict': ('match' if ok and grading['overall']
                        in ('ideal', 'acceptable') else
                        'mismatch' if ok else 'refusal'),
        })

    # 2. framework reachability vs observed phases.
    cation = _get(case, 'cation')
    mr = _get(case, 'mr', 0.0)
    observedFw = _loads(case, 'observed_frameworks_json', '[]')
    if cation and observedFw:
        reach = reachable_frameworks(
            qualitative_inventory(cation),
            rules=rules if rules is not None else _seed_or_rows(
                manager, 'ReactionRule', SEED_REACTION_RULES),
            conditions={'MR': mr},
            windows=banded if banded is not None else _seed_or_rows(
                manager, 'ThresholdReactionWindow',
                SEED_THRESHOLD_WINDOWS),
            cation=cation)
        predicted = {f['framework']
                     for f in reach['reachableFrameworks']}
        sections.append({
            'aspect': 'frameworks',
            'measured': observedFw,
            'predicted': reach,
            'verdict': ('match' if set(observedFw) <= predicted
                        else 'mismatch'),
            'note': 'presence-only closure predicts which routes are '
                    'OPEN; observed phases must be a subset — '
                    'selection among open routes is competitive '
                    '(p.185) and stays unpredicted',
        })

    # 3. cure prediction beside the measured series (refusals ARE
    # the honest overlay where no law exists).
    measuredSets = _loads(case, 'measured_datasets_json', '[]')
    if mr:
        cure = cure_progress(manager, mr)
        sections.append({
            'aspect': 'cure',
            'measured': {'datasets': measuredSets,
                         **({'series': observed['strength_series']}
                            if 'strength_series' in observed else {})},
            'predicted': cure,
            'verdict': 'match' if cure.get('ok') else 'refusal',
        })

    # 4. everything else as-printed.
    covered = {'windows', 'strength_series'}
    recorded = {k: v for k, v in observed.items() if k not in covered}
    if recorded:
        sections.append({'aspect': 'recorded', 'measured': recorded,
                         'predicted': None, 'verdict': 'recorded'})

    return {'ok': True,
            'name': _get(case, 'name'),
            'source': _get(case, 'source_reference'),
            'use': _get(case, 'use'),
            'inputs': inputs,
            'sections': sections}
def benchmark_catalog(manager):
    from pspp.custom.pspp_views import _seed_or_rows
    cases = _seed_or_rows(manager, 'BenchmarkCase',
                          SEED_BENCHMARK_CASES)
    return {'ok': True, 'benchmarks': [
        {'name': _get(c, 'name'),
         'source': _get(c, 'source_reference'),
         'use': _get(c, 'use'),
         'windowFamily': _get(c, 'window_family'),
         'cation': _get(c, 'cation'), 'mr': _get(c, 'mr', 0.0)}
        for c in cases]}
def benchmark_overlay_by_name(manager, name):
    from pspp.custom.pspp_views import _seed_or_rows
    cases = _seed_or_rows(manager, 'BenchmarkCase',
                          SEED_BENCHMARK_CASES)
    case = next((c for c in cases if _get(c, 'name') == name), None)
    if case is None:
        return {'ok': False,
                'refusal': f'unknown benchmark case {name!r}',
                'suggestion': 'GET /api/pspp/benchmarks for the '
                              'catalog'}
    return benchmark_overlay(manager, case)
