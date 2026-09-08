"""
Self-test for pspp-11 (data-only half): the CMC library must load
through EXISTING classes with zero schema changes — that absence of
new code IS the generality proof.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.cmc_library_selftest
"""

import sys

from pspp.cmc_library_seed import (
    SEED_CMC_PROCESS_DEFINITIONS, SEED_CMC_PROCESSING_STAGES,
    SEED_CMC_PROPERTY_MEANINGS,
)
from pspp.material_processes_basis import (
    EXECUTION_EFFECTS, MaterialProcessDefinition,
)
from pspp.material_states_basis import ProcessingStage
from materialsScience.property_meanings import (
    MaterialPropertyMeaning, PROPERTY_MEANING_VOCAB,
)
import inspect

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


def _fields(cls):
    return set(inspect.signature(cls.__init__).parameters) - {
        'self', 'manager'}


def test_zero_schema_changes():
    print('[generality proof: rows fit EXISTING classes]')
    meaningFields = _fields(MaterialPropertyMeaning)
    check('every CMC meaning uses only MaterialPropertyMeaning '
          'fields', all(set(r) <= meaningFields
                        for r in SEED_CMC_PROPERTY_MEANINGS))
    stageFields = _fields(ProcessingStage)
    check('every CMC stage uses only ProcessingStage fields', all(
        set(r) <= stageFields for r in SEED_CMC_PROCESSING_STAGES))
    processFields = _fields(MaterialProcessDefinition)
    check('every CMC process uses only MaterialProcessDefinition '
          'fields', all(set(r) <= processFields
                        for r in SEED_CMC_PROCESS_DEFINITIONS))


def test_content():
    print('[library content]')
    meaningNames = [r['name'] for r in SEED_CMC_PROPERTY_MEANINGS]
    check('load-bearing CMC descriptors present (interface, '
          'orientation, crack density, Weibull, coatings, '
          'oxidation)', all(n in meaningNames for n in (
              'interfaceShearStrength', 'orientationTensor',
              'matrixCrackDensity', 'fiberStrengthWeibullModulus',
              'coatingStack', 'oxidationRecessionDepth')))
    check('no collision with the existing shared vocabulary',
          not set(meaningNames) & set(PROPERTY_MEANING_VOCAB))
    check('CMC route stages chain preform -> coated -> infiltrated '
          '-> densified', [s['name'] for s in
                           SEED_CMC_PROCESSING_STAGES] == [
              'fiber-preform', 'coated-preform', 'infiltrated-green',
              'densified-composite'])
    check('structure-generating processes present (coating, CVI, '
          'PIP, melt infiltration, sintering)', all(
              any(p['name'] == n for p in SEED_CMC_PROCESS_DEFINITIONS)
              for n in ('fiber-coating', 'cvi-infiltration',
                        'pip-cycle', 'melt-infiltration',
                        'sintering')))
    check('all processes declare a valid execution effect (I2)', all(
        p['execution_effect'] in EXECUTION_EFFECTS
        for p in SEED_CMC_PROCESS_DEFINITIONS))
    check('every row cites its provenance (equations pending — I5)',
          all(r.get('provenance_id')
              for r in SEED_CMC_PROPERTY_MEANINGS
              + SEED_CMC_PROCESSING_STAGES
              + SEED_CMC_PROCESS_DEFINITIONS))


def main():
    test_zero_schema_changes()
    test_content()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
