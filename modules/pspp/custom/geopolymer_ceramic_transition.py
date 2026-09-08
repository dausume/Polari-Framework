"""
@module pspp.custom.geopolymer_ceramic_transition

mtt-2: the GEOPOLYMER -> HIGH-TEMPERATURE -> CERAMIC / GLASS pathway —
the same escalation story the ceramics ladder tells, but on the
MATERIALS side and, unusually, DATA-BACKED: the K-geopolymer thermal
conversion is a measured DigitizedDataset (Table 8.8, Perera &
Trautman 2005 — open porosity + XRD phases from ambient to 1400 C).

A geopolymer is not a dead-end: heated, it dehydrates, dehydroxylates,
then CRYSTALLIZES — amorphous to ~800 C, kalsilite major at 1000 C,
leucite major at 1200 C, distorted kalsilite to 1400 C with NO melting
(a Ca-pentamer fusing phase softens above 1400 C and would lower the
melting point toward the glass branch). So the SAME body climbs from
gel to refractory ceramic; the reaction_network already carries the
crystallization rules (kalsilite / leucite frameworks, the Kriven
route to leucite ceramic).

This reads the measured curve into thermal-conversion STAGES (each a
temperature, its open porosity, its XRD phases, and what is happening),
cites the crystallization rules that fire in each band, and marks the
GLASS branch honestly as above the measured range (specifics refuse).

@consumers
  - pspp.pspp_api (/api/pspp/ceramics/geopolymer-transition)
  - pspp.geopolymer_ceramic_transition_selftest
"""

from pspp.custom.dataset_interpolation import read_dataset
from pspp.digitized_datasets_basis import dataset_dict
from pspp.datasets_seed import SEED_DIGITIZED_DATASETS

_TRANSITION_DATASET = 'k-geopolymer-porosity-phases-vs-temperature'

#: Which stage a temperature belongs to, and the crystallization rule
#: (reaction_network) whose product first dominates there. Bands are
#: read FROM the measured phases, not invented.
_STAGE_BANDS = [
    (0, 1000, 'amorphous-geopolymer',
     'Cured geopolymer gel: still X-ray amorphous (major to 800 C). '
     'Free + some bound water leaves (dehydration, then '
     'dehydroxylation) — open porosity peaks near 500 C as water '
     'escapes.', None),
    (1000, 1200, 'crystallizing-kalsilite',
     'Crystallization: kalsilite (KAlSiO4, Si:Al=1) becomes the major '
     'phase at 1000 C — the amorphous poly(sialate) reorganizes into a '
     'ceramic framework; porosity falls as it densifies.',
     'kalsilite-framework-polycondensation'),
    (1200, 1250, 'ceramic-leucite',
     'Leucite (KAlSi2O6, Si:Al=2) becomes major — the higher-silica '
     'poly(sialate-siloxo) ceramic (the Kriven route to a pure leucite '
     'ceramic sinters here).',
     'leucite-framework-polycondensation'),
    (1250, 1401, 'ceramic-distorted-kalsilite',
     'Distorted kalsilite dominates to 1400 C with NO significant '
     'melting — a stable refractory ceramic. A Ca-pentamer '
     '(Ca8Si5O18) fusing phase softens above 1400 C and would lower '
     'the melting point toward vitrification.', None),
]

_GLASS_BRANCH = {
    'stage': 'glass-vitrification',
    'onsetC': 1400,
    'what': 'Above the measured range: the fusing Ca-pentamer phase '
            'softens >1400 C and lowers kalsilite melting (nominally '
            '~1750 C), opening a VITRIFICATION branch — melt then '
            'quench to a glass. Specifics (melt temperature, glass '
            'transition) are OUTSIDE Table 8.8 and refuse until a '
            'melt/quench dataset is entered.',
    'refuses': True,
}


def _dataset(datasets=None):
    if datasets is not None:
        return datasets.get(_TRANSITION_DATASET)
    for seed in SEED_DIGITIZED_DATASETS:
        if seed['name'] == _TRANSITION_DATASET:
            return dataset_dict(seed)
    return None


def _stage_for(temp_c):
    for lo, hi, stage, what, rule in _STAGE_BANDS:
        if lo <= temp_c < hi:
            return stage, what, rule
    return 'beyond-measured', 'above the Table 8.8 range', None


def transition_stages(datasets=None):
    """The geopolymer -> ceramic thermal-conversion ladder, read from
    the MEASURED Table 8.8 points: each temperature with its open
    porosity, XRD phases, the stage it belongs to, and the
    crystallization rule that dominates there. The glass branch is
    appended as an honest above-range refusal."""
    dataset = _dataset(datasets)
    if dataset is None:
        return {'ok': False,
                'refusal': f'dataset {_TRANSITION_DATASET!r} not found',
                'suggestion': 'seed/restore the Table 8.8 '
                              'DigitizedDataset row'}
    points = sorted(dataset.get('points', []),
                    key=lambda p: p.get('temperature_c', 0))
    if not points:
        return {'ok': False,
                'refusal': f'dataset {_TRANSITION_DATASET!r} has no '
                           'points',
                'suggestion': 'the transition needs the measured '
                              'porosity/phase points'}
    stages = []
    for p in points:
        temp = p.get('temperature_c')
        stage, what, rule = _stage_for(temp)
        stages.append({
            'temperatureC': temp,
            'stage': stage,
            'openPorosityPct': p.get('open_porosity_pct'),
            'xrdPhases': p.get('xrd_phases'),
            'whatHappens': what,
            'crystallizationRule': rule,
        })
    return {
        'ok': True,
        'material': 'K-geopolymer (cured 80C/24h)',
        'stages': stages,
        'glassBranch': _GLASS_BRANCH,
        'evidence': {
            'dataset': _TRANSITION_DATASET,
            'source': dataset.get('sourceReference'),
        },
        'assumptions': [
            'stages + porosity + XRD phases are MEASURED (Table 8.8, '
            'Perera & Trautman 2005) — not modeled',
            'the crystallization RULES are the reaction_network '
            'frameworks that dominate each band (kalsilite / leucite)',
            'the glass branch is above the measured range and refuses '
            'specifics',
            'this is ONE geopolymer (K-system); Na-systems crystallize '
            'to nepheline/albite analogues (see reaction_network)',
        ],
    }


def porosity_at(temp_c, datasets=None):
    """Open porosity at one temperature along the conversion — the
    generic dataset reader (bands + UNSUPPORTED extrapolation ride
    along; XRD phases are categorical so between-point phase queries
    refuse upstream)."""
    dataset = _dataset(datasets)
    if dataset is None:
        return {'ok': False,
                'refusal': f'dataset {_TRANSITION_DATASET!r} not found',
                'suggestion': 'seed/restore the Table 8.8 row'}
    # Read POROSITY only: the row also carries a categorical
    # xrd_phases column that cannot interpolate, and some temperatures
    # have phases but no measured porosity — a porosity-only view.
    porosity_view = dict(dataset)
    porosity_view['dependentVariables'] = ['open_porosity_pct']
    porosity_view['points'] = [
        {k: v for k, v in p.items() if k != 'xrd_phases'}
        for p in dataset.get('points', [])
        if p.get('open_porosity_pct') is not None]
    verdict = read_dataset(porosity_view, {'temperature_c': temp_c})
    if verdict.get('ok'):
        stage, what, rule = _stage_for(temp_c)
        verdict['stage'] = stage
        verdict['whatHappens'] = what
    return verdict
