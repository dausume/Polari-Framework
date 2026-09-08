"""
Self-test for mtt-2 sg-3/sg-4: the sol-gel stage route (drying fork)
and the points-empty provisional datasets whose refusals ARE the
data asks. Also guards seed-name uniqueness across every class the
sol-gel library concatenates into (idempotent-by-name safety).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.solgel_process_selftest
"""

import sys

from pspp.custom.dataset_interpolation import read_dataset
from pspp.datasets_seed import SEED_DIGITIZED_DATASETS
from pspp.digitized_datasets_basis import dataset_dict
from pspp.material_states_basis import SEED_PROCESSING_STAGES
from pspp.reaction_network_basis import (
    SEED_CHEMICAL_SPECIES, SEED_REACTION_RULES,
)
from pspp.custom.solgel_network import (
    SOLGEL_CHEMICAL_SPECIES, SOLGEL_REACTION_RULES,
)
from pspp.custom.solgel_process import (
    SOLGEL_DIGITIZED_DATASETS, SOLGEL_PROCESSING_STAGES,
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


def test_stages():
    print('[sg-4: the sol-gel state route]')
    stages = {s['name']: s for s in SOLGEL_PROCESSING_STAGES}
    check('route stages present',
          {'precursor-solution', 'hydrolyzing-sol', 'gel-point',
           'aging-gel', 'xerogel', 'aerogel', 'densified-gel-glass'}
          <= set(stages))
    check('all stages carry family sol-gel',
          all(s['material_family'] == 'sol-gel'
              for s in SOLGEL_PROCESSING_STAGES))
    check('drying FORK: xerogel and aerogel both branch off aging',
          stages['xerogel']['typical_prior_stage'] == 'aging-gel'
          and stages['aerogel']['typical_prior_stage'] == 'aging-gel')
    check('route is chained from the precursor solution',
          stages['hydrolyzing-sol']['typical_prior_stage']
          == 'precursor-solution'
          and stages['gel-point']['typical_prior_stage']
          == 'hydrolyzing-sol'
          and stages['aging-gel']['typical_prior_stage'] == 'gel-point')


def test_datasets_refuse_honestly():
    print('[sg-3: provisional datasets refuse until digitized]')
    for seed in SOLGEL_DIGITIZED_DATASETS:
        dataset = dataset_dict(seed)
        verdict = read_dataset(dataset, {
            (dataset['independentVariables'] or ['x'])[0]: 1.0})
        check(f"{seed['name']} refuses as provisional",
              verdict['ok'] is False
              and 'provisional' in (verdict.get('refusal') or ''))
        check(f"{seed['name']} records the qualitative shape + ask",
              bool(seed['qualitative_shape'])
              and 'DATA ASK' in seed['notes']
              and seed['points_json'] == '[]')


def test_seed_name_uniqueness():
    print('[idempotent-by-name safety: no collisions with existing '
          'seeds]')

    def names(rows):
        return {r['name'] for r in rows}
    check('species names unique vs existing inventory',
          not (names(SOLGEL_CHEMICAL_SPECIES)
               & names(SEED_CHEMICAL_SPECIES)))
    check('rule names unique vs existing library',
          not (names(SOLGEL_REACTION_RULES)
               & names(SEED_REACTION_RULES)))
    check('stage names unique vs existing vocabulary',
          not (names(SOLGEL_PROCESSING_STAGES)
               & names(SEED_PROCESSING_STAGES)))
    check('dataset names unique vs existing transcriptions',
          not (names(SOLGEL_DIGITIZED_DATASETS)
               & names(SEED_DIGITIZED_DATASETS)))
    check('sol-gel rules reuse the SHARED Q motif ledger (no '
          'duplicate Q species)',
          not any(s['name'].startswith('siloxonate-q')
                  for s in SOLGEL_CHEMICAL_SPECIES))


def main():
    test_stages()
    test_datasets_refuse_honestly()
    test_seed_name_uniqueness()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
