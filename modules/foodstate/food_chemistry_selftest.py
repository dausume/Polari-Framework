"""
Selftest for foodstate fsp-3 (first slice) — cited-constants
chemistry: Henderson–Hasselbalch speciation is exact algebra (sums
to 1; pH=pKa gives 50/50 on a monoprotic acid), TA is exact
stoichiometry, buffer capacity refuses (I5), and THE ACID CHAIN
runs end-to-end: tomato acid claims → chop → simmer → reduce
concentrates citric by exactly the stated mass ratio, and
speciation at a measured pH answers the state-184-style question.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m foodstate.food_chemistry_selftest
"""

import json
from types import SimpleNamespace

from foodstate.food_acid_seed import SEED_FOOD_ACID_CLAIMS
from foodstate.custom.food_chemistry import (
    CITED_PKA, buffer_capacity, ingredient_acidity, speciation,
    titratable_acidity,
)
from foodstate.custom.food_composition import build_composition_claim_seeds
from foodstate.food_ph_seed import SEED_FOOD_PH_CLAIMS
from foodstate.food_pspp_seed import SEED_FOOD_PROCESSES
from foodstate.custom.food_transforms import derive_transform

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


MANAGER = SimpleNamespace(objectTables={
    'PropertyClaim': _rows(build_composition_claim_seeds()
                           + SEED_FOOD_PH_CLAIMS
                           + SEED_FOOD_ACID_CLAIMS),
    'MaterialProcessDefinition': _rows(SEED_FOOD_PROCESSES),
})

# ── speciation algebra ────────────────────────────────────
mono = speciation('acetic', 4.756)
check('monoprotic at pH=pKa splits 50/50',
      mono['ok'] and abs(mono['species'][0]['fraction'] - 0.5)
      < 1e-6)
cit = speciation('citric', 4.31)
check('citric speciation ok at pH 4.31 (the measured-sauce '
      'example)', cit['ok'])
check('fractions sum to 1',
      abs(sum(s['fraction'] for s in cit['species']) - 1.0) < 1e-9)
check('at pH 4.31 citric is partially dissociated (some H3A, '
      'some H2A-)',
      0.02 < cit['fractionFullyProtonated'] < 0.5)
check('verified citation rides the payload',
      'Goldberg' in cit['citation'] and 'verified' in
      cit['citationStatus'])
check('unknown acid REFUSES naming the cited set',
      not speciation('oxalic', 3.0).get('ok'))
check('absurd pH refuses', not speciation('citric', 19).get('ok'))

# ── titratable acidity stoichiometry ─────────────────────
ta = titratable_acidity({'citric': 0.194, 'malic': 0.051})
expect_meq = (0.194 / 192.12 * 3 + 0.051 / 134.09 * 2) * 1000
check('TA meq arithmetic exact',
      ta['ok'] and abs(ta['meqPer100g'] - expect_meq) < 0.01)
check('as-citric conversion round-trips',
      abs(ta['asCitricGPer100g']
          - expect_meq / 1000 / 3 * 192.12) < 1e-4)
check('unknown acids named, not silently dropped',
      titratable_acidity({'citric': 0.1, 'quinic': 0.2})
      ['unknownAcids'] == ['quinic'])
check('buffer capacity REFUSES naming the unloaded model (I5)',
      not buffer_capacity().get('ok')
      and 'calibration' in buffer_capacity()['refusal'])

# ── the ingredient acidity report ─────────────────────────
rep = ingredient_acidity(MANAGER, 'tomato-raw')
check('tomato carries both cited acid claims',
      set(rep['organicAcids']) == {'citric', 'malic'})
check('TA computed from the claims',
      rep['titratableAcidity']['ok'])
check('speciation at the claimed pH (4.6 midpoint)',
      rep['speciationAtClaimedPh']['citric']['ok']
      and rep['speciationAtClaimedPh']['citric']['pH'] == 4.6)
no_acids = ingredient_acidity(MANAGER, 'chicken-breast-raw')
check('acid-less food refuses TA naming the D4 gap',
      not no_acids['titratableAcidity']['ok']
      and 'D4' in no_acids['titratableAcidity']['refusal'])

# ── THE ACID CHAIN: chop → simmer → reduce ────────────────
chop = derive_transform(MANAGER, 'food-chop',
                        'tomato-raw#as-defined', {})
check('chain step 1: chop ok', chop.get('ok'))


def overlay(*derived):
    claims = dict(MANAGER.objectTables['PropertyClaim'])
    n = len(claims) + 100000
    for d in derived:
        for c in d['claims']:
            claims[n] = SimpleNamespace(**c)
            n += 1
    return SimpleNamespace(objectTables={
        **MANAGER.objectTables, 'PropertyClaim': claims})


m2 = overlay(chop)
simmer = derive_transform(m2, 'food-simmer',
                          chop['outputState']['name'],
                          {'yield_percent': 70.0})
check('chain step 2: simmer ok', simmer.get('ok'))
m3 = overlay(chop, simmer)
reduce_ = derive_transform(m3, 'food-reduce',
                           simmer['outputState']['name'],
                           {'yield_percent': 57.143,
                            'output_state_name': 'sauce'})
check('chain step 3: reduce ok', reduce_.get('ok'))
citric_final = None
for c in reduce_.get('claims', []):
    if c['property_meaning_name'] == 'organic-acid-citric':
        citric_final = c['value']
check('citric concentrated by EXACTLY the overall mass ratio '
      '(0.194 × 100/40)',
      citric_final is not None
      and abs(citric_final - 0.194 / 0.40) < 0.001,
      f'got {citric_final}')
check('acid claims ride mass-balance evidence through the chain',
      any(c['property_meaning_name'] == 'organic-acid-citric'
          and c['evidence_method'] == 'mass-balance'
          for c in reduce_['claims']))
# the state-184-style question: measured pH on the sauce state
sauce_spec = speciation('citric', 4.31)
check('measured-pH speciation on the sauce answers the example',
      sauce_spec['ok'])

passed = sum(1 for _, ok in _results if ok)
print(f'\n{passed}/{len(_results)} checks passed')
if passed != len(_results):
    raise SystemExit(1)
