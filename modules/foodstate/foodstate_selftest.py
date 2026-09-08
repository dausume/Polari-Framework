"""
Selftest for foodstate fsp-0 (FOOD_STATE_PSPP_PLAN.md): the food
vocabulary + domain contracts as data, riding the pspp core with
ZERO pspp schema changes — the pspp-11 generality proof.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m foodstate.foodstate_selftest
"""

import json
import sys
import types

from foodstate.food_contracts_basis import (
    SEED_FOOD_DOMAIN_CONTRACTS, FoodDomainContract, contracts_report,
)
from foodstate.food_pspp_seed import (
    SEED_FOOD_EVIDENCE_METHODS, SEED_FOOD_PROCESSES, SEED_FOOD_STAGES,
)
from foodstate.food_api import vocabulary_report

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    tables = {'FoodDomainContract': {}, 'ProcessingStage': {},
              'MaterialProcessDefinition': {}, 'EvidenceMethod': {}}
    mgr = types.SimpleNamespace(objectTables=tables, db=None)
    for seed in SEED_FOOD_DOMAIN_CONTRACTS:
        row = types.SimpleNamespace(**seed)
        tables['FoodDomainContract'][id(row)] = row
    for seed in SEED_FOOD_STAGES:
        row = types.SimpleNamespace(**seed)
        tables['ProcessingStage'][id(row)] = row
    for seed in SEED_FOOD_PROCESSES:
        row = types.SimpleNamespace(**seed)
        tables['MaterialProcessDefinition'][id(row)] = row
    for seed in SEED_FOOD_EVIDENCE_METHODS:
        row = types.SimpleNamespace(**seed)
        tables['EvidenceMethod'][id(row)] = row
    return mgr


def main():
    # ---- zero-schema-change proof --------------------------------
    from pspp.material_states_basis import ProcessingStage
    from pspp.material_processes_basis import (
        EXECUTION_EFFECTS, MaterialProcessDefinition,
    )
    from pspp.evidence_methods_basis import EvidenceMethod
    check('generality proof: every food stage/process/method seed '
          'CONSTRUCTS the unmodified pspp class it targets (zero '
          'pspp schema changes)',
          all(hasattr(ProcessingStage(**{**s, 'manager': None}),
                      'material_family')
              for s in SEED_FOOD_STAGES)
          and all(hasattr(MaterialProcessDefinition(
              **{**p, 'manager': None}), 'execution_effect')
              for p in SEED_FOOD_PROCESSES)
          and all(hasattr(EvidenceMethod(**{**m, 'manager': None}),
                          'required_provenance')
                  for m in SEED_FOOD_EVIDENCE_METHODS))
    check('one new class only (FoodDomainContract — contracts-as-'
          'data, the fam-1 shell pattern); rows construct',
          all(hasattr(FoodDomainContract(**{**c, 'manager': None}),
                      'contract_json')
              for c in SEED_FOOD_DOMAIN_CONTRACTS))

    # ---- I2 discipline -------------------------------------------
    check('I2: every process DECLARES its effect; measurements are '
          'OBSERVATIONAL (pH/titration/aw attach claims, never '
          'states), cooking is TRANSFORMATIVE',
          all(p['execution_effect'] in EXECUTION_EFFECTS
              for p in SEED_FOOD_PROCESSES)
          and all(p['execution_effect'] == 'OBSERVATIONAL'
                  for p in SEED_FOOD_PROCESSES
                  if p['process_type'] == 'measurement')
          and all(p['execution_effect'] == 'TRANSFORMATIVE'
                  for p in SEED_FOOD_PROCESSES
                  if p['process_type'] in ('heating', 'preparation',
                                           'cooling',
                                           'biotransformation')))
    check('chop is the structure-only transform: conserves '
          'composition, changes particle size',
          any(p['name'] == 'food-chop'
              and 'composition' in json.loads(
                  p['output_state_schema_json']).get('conserves', [])
              for p in SEED_FOOD_PROCESSES))
    check('reduce concentrates solutes by mass balance (the tomato-'
          'sauce acid edge)',
          any(p['name'] == 'food-reduce'
              and 'organic-acids' in json.loads(
                  p['output_state_schema_json']).get('concentrates',
                                                     [])
              for p in SEED_FOOD_PROCESSES))
    check('no invented engines: every process row says it REFUSES '
          'until fsp-2 wires engines (I5)',
          all('REFUSES' in p['notes'] and json.loads(
              p['transformation_engine_refs_json']) == []
              for p in SEED_FOOD_PROCESSES))

    # ---- evidence methods ----------------------------------------
    check('the three added methods carry the ladder honesty: '
          'mass-balance derived, retention-factor cites R6, '
          'conditional-prediction requires conditions + confidence '
          'and is direction-only (D6)',
          {m['name'] for m in SEED_FOOD_EVIDENCE_METHODS}
          == {'mass-balance', 'retention-factor',
              'conditional-prediction'}
          and any('R6' in m['required_provenance']
                  for m in SEED_FOOD_EVIDENCE_METHODS
                  if m['name'] == 'retention-factor')
          and any('conditions' in m['required_provenance']
                  and 'confidence' in m['required_provenance']
                  for m in SEED_FOOD_EVIDENCE_METHODS
                  if m['name'] == 'conditional-prediction'))

    # ---- domain contracts ----------------------------------------
    rep = contracts_report(_mgr())
    doms = {c['domain'] for c in rep['contracts']}
    check('food-contracts/1: five domains incl. the D8 rename '
          '(physiological-functional-performance), ladder + '
          'boundary stated',
          rep['ok'] and len(rep['contracts']) == 5
          and doms == {'composition', 'structure', 'physical',
                       'chemical',
                       'physiological-functional-performance'}
          and 'REFUSE' in rep['ladder']
          and 'not medical advice' in rep['boundary'])
    check('every contract quantity carries quantity/unit/'
          'expected_provenance/why',
          all({'quantity', 'unit', 'expected_provenance', 'why'}
              <= set(q)
              for c in rep['contracts'] for q in c['contract']))
    check('the separation that matters: starch GRAMS in composition, '
          'gelatinization FRACTION in structure; protein grams vs '
          'denaturation fraction likewise',
          any(q['quantity'] == 'starch'
              for c in rep['contracts']
              if c['domain'] == 'composition'
              for q in c['contract'])
          and any(q['quantity'] == 'starch-gelatinization-fraction'
                  for c in rep['contracts']
                  if c['domain'] == 'structure'
                  for q in c['contract']))
    check('gastric-acid-response is conditional-prediction only, '
          'direction + conditions (D6: no magnitudes)',
          any(q['quantity'] == 'gastric-acid-response'
              and q['expected_provenance'] == 'conditional-prediction'
              and 'direction' in q['unit']
              for c in rep['contracts']
              if c['domain'] == 'physiological-functional-performance'
              for q in c['contract']))
    check('chemistry contract: pH + titratable acidity + buffer '
          'capacity present (buffer capacity stated as what the '
          'stomach works against)',
          any({'pH', 'titratable-acidity', 'buffer-capacity'}
              <= {q['quantity'] for q in c['contract']}
              for c in rep['contracts']
              if c['domain'] == 'chemical'))

    # ---- vocabulary report ---------------------------------------
    voc = vocabulary_report(_mgr())
    check('food-vocabulary/1: stages + processes + added methods '
          'served; substrate + refusal-until-fsp-2 stated',
          voc['ok'] and len(voc['stages']) == len(SEED_FOOD_STAGES)
          and len(voc['processes']) == len(SEED_FOOD_PROCESSES)
          and len(voc['addedEvidenceMethods']) == 3
          and 'zero-schema-change' in voc['substrate']
          and 'REFUSES' in voc['execution'])
    check('stage route chains to prepared-food and starts at '
          'raw-ingredient (the canonical #as-defined anchor)',
          any(s['name'] == 'raw-ingredient' for s in voc['stages'])
          and any(s['name'] == 'prepared-food'
                  for s in voc['stages'])
          and any('as-defined' in s['description']
                  for s in voc['stages']
                  if s['name'] == 'raw-ingredient'))

    passed = sum(1 for _l, okc in _results if okc)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
