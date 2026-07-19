"""
@module pspp.q_distribution

The Tier-2/3 Q-species engines (plan pspp-7), unblocked by the p.90
Figs 5.4/5.5 capture:

- q_glass_distribution: (cation family, MR) → Q0-Q4 fractions of the
  parent GLASS, interpolated from the Maekawa curves via the one
  generic dataset reader (bands + UNSUPPORTED extrapolation ride
  along for free).
- glass_to_solution_q: the Table 5.6 fixed reference mapping at the
  listed MRs ONLY — no general dissolution-kinetics law exists in the
  source, so between-MR queries refuse rather than guess.

Q-species are structural MOTIFS (Ch.5-8 review): these summaries
never replace an underlying network representation where one exists.
"""

from pspp.dataset_interpolation import read_dataset
from pspp.digitized_datasets import dataset_dict
from pspp.datasets_seed import SEED_DIGITIZED_DATASETS

_GLASS_DATASETS = {'Na': 'na-glass-q-distribution-vs-mr',
                   'K': 'k-glass-q-distribution-vs-mr'}
_TRANSFORM_DATASET = 'na-siloxonate-glass-to-solution-q'

#: p.103 Fig 5.12 caption — rides on every solution-side result.
_Q4_ARTIFACT_CAVEAT = (
    'liquid-state 29Si NMR Q4 peaks can be equipment artifacts '
    '(book p.103, Fig 5.12 caption) — treat solution Q4 values as '
    'suspect')


def _dataset(name, datasets=None):
    if datasets is not None:
        return datasets.get(name)
    for seed in SEED_DIGITIZED_DATASETS:
        if seed['name'] == name:
            return dataset_dict(seed)
    return None


def q_glass_distribution(cation, mr, datasets=None):
    """Q0-Q4 fractions of a (Na|K)-silicate glass at one MR.
    `datasets` may inject live rows ({name: dataset dict}); defaults
    to the seed transcriptions."""
    name = _GLASS_DATASETS.get(cation)
    if name is None:
        return {'ok': False,
                'refusal': f'no glass Q-distribution dataset for '
                           f'cation family {cation!r}',
                'suggestion': f'available: {sorted(_GLASS_DATASETS)} — '
                              'a new family needs its own digitized '
                              'curves (they do not transfer)'}
    dataset = _dataset(name, datasets)
    if dataset is None:
        return {'ok': False, 'refusal': f'dataset {name!r} not found',
                'suggestion': 'seed or restore the DigitizedDataset '
                              'row'}
    result = read_dataset(dataset, {'MR': mr})
    if result['ok']:
        result['cation'] = cation
        result['physicalState'] = 'glass'
    return result


def glass_to_solution_q(mr, datasets=None):
    """The Table 5.6 glass→solution depolymerization mapping at one of
    the LISTED MRs — both sides returned, artifact caveat attached."""
    dataset = _dataset(_TRANSFORM_DATASET, datasets)
    if dataset is None:
        return {'ok': False,
                'refusal': f'dataset {_TRANSFORM_DATASET!r} not found',
                'suggestion': 'seed or restore the DigitizedDataset '
                              'row'}
    glass = read_dataset(dataset, {'MR': mr, 'physical_state': 'glass'})
    if not glass['ok']:
        return glass
    solution = read_dataset(dataset,
                            {'MR': mr, 'physical_state': 'solution'})
    if not solution['ok']:
        return solution
    return {
        'ok': True,
        'MR': mr,
        'glass': glass['values'],
        'solution': solution['values'],
        'evidence': glass['evidence'],
        'assumptions': sorted(set(glass['assumptions'])
                              | {_Q4_ARTIFACT_CAVEAT}),
    }
